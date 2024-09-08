import pandas as pd
import streamlit as st

from loguru import logger

from src.ai_ocr_client.request_be import BeRequest


class AiOcrFrontend:
    request_be: BeRequest
    text: str

    def __init__(self, ip: str = "127.0.0.1", port: int = 5000, protocol: str = "http") -> None:
        self._request_be = BeRequest(ip, port, protocol)
        st.session_state["configured_models"] = st.session_state.get("configured_models",
                                                                     self._request_be.get("get_all_unmodified_models"))
        st.session_state["uploaded_images"] = st.session_state.get("uploaded_images", [])

    def build_upload_widget(self) -> None:
        with st.container(border=True):
            uploaded_images = st.file_uploader("Uploade alle Bilder hier...", accept_multiple_files=True)
            upload_button = st.button("Upload images", key="upload")

            if type(uploaded_images) is not list:
                uploaded_images = [uploaded_images]

            if len(uploaded_images) > 0 and upload_button:
                success = self._request_be.post("upload_images", None, images=uploaded_images)
                logger.info(success)

                st.session_state["uploaded_images"] = [image.name for image in uploaded_images]

            if len(st.session_state["uploaded_images"]) > 0:
                st.write(f"Successfully uploaded {len(st.session_state['uploaded_images'])} file(s).")

    def build_page(self) -> None:
        self.build_upload_widget()
        self.build_run_ocr()

    def build_run_ocr(self) -> None:
        with st.container(border=True):
            model_name = st.radio("Wähle eine Modell aus 👉", key="model_choser_0",
                                  options=st.session_state["configured_models"].keys())
            prompt = st.text_area("Prompt", placeholder="Schreibe hier welche Messgröße extrahiert werden soll...")
            temperature = st.slider("Temperature", 0, 1, 0)
            top_p = st.number_input("Top p", 0., 1., 0.1)

            payload = {
                "prompt": prompt,
                "model_name": model_name,
                "parameters": {
                    "temperature": temperature,
                    "top_p": top_p
                }
            }
            uploaded_images = st.session_state["uploaded_images"]

            run_ocr_button = st.button("Run OCR")

            if run_ocr_button and len(prompt) == 0:
                st.toast("No prompt given.")
                return

            if run_ocr_button and len(uploaded_images) == 0:
                st.toast("No images uploaded.")
                return

            if run_ocr_button:
                dfs = []

                progress_text = "OCR in progress. Please wait."
                progress_bar = st.progress(0, text=progress_text)
                for i, image_name in enumerate(uploaded_images):
                    json_output = self._request_be.post("recognize_values", payload=payload, image_name=image_name)
                    print(i, image_name, json_output)
                    dfs.append(pd.DataFrame(json_output, index=[i]))

                    progress_bar.progress((i + 1) / len(st.session_state["uploaded_images"]), text=progress_text)

                df = pd.concat(dfs)

                progress_bar.empty()
                st.dataframe(df)

                st.session_state["uploaded_images"] = []


ai_ocr_frontend = AiOcrFrontend()
ai_ocr_frontend.build_page()
