from collections.abc import Callable

import pandas as pd
import time
import streamlit as st

from loguru import logger
from typing import Union

from src.ai_ocr_client.request_be import BeRequest


class AiOcrFrontend:
    request_be: BeRequest
    temperature: float
    top_p: float

    def __init__(self, ip: str = "127.0.0.1", port: int = 5000, protocol: str = "http") -> None:
        self._request_be = BeRequest(ip, port, protocol)
        self._temperature = 0.1
        self._top_p = 0.1

        st.session_state["configured_models"] = st.session_state.get("configured_models",
                                                                     self._request_be.get("get_all_unmodified_models"))
        st.session_state["uploaded_images"] = st.session_state.get("uploaded_images", [])
        st.session_state["df"] = st.session_state.get("df", None)
        st.session_state["pot_suggestions"] = st.session_state.get("pot_suggestions", None)

    def build_upload_widget(self) -> None:
        with st.form("Upload_widget", clear_on_submit=True):
            uploaded_images = st.file_uploader("Upload your images here...", accept_multiple_files=True)
            upload_button = st.form_submit_button("Upload images")

            if len(uploaded_images) > 0 and upload_button:
                success = self._request_be.post("upload_images", None, images=uploaded_images)
                logger.info(f"Upload successful: {success}.")

                st.session_state["uploaded_images"] = [image.name for image in uploaded_images]

            if len(st.session_state["uploaded_images"]) > 0:
                with st.container(border=True):
                    uploaded_images_str = "\n".join([f"- {image}" for image in st.session_state["uploaded_images"]])
                st.success(f"Successfully uploaded the following files:\n{uploaded_images_str}.")
                st.session_state["df"] = None

    @staticmethod
    @st.cache_data
    def convert_df(df: pd.DataFrame):
        # IMPORTANT: Cache the conversion to prevent computation on every rerun
        return df.to_csv().encode("utf-8")

    def build_page(self) -> None:
        self.build_upload_widget()
        self.build_run_ocr()
        self.build_run_plot()

    def build_run_ocr_form(self) -> Union[pd.DataFrame, None]:
        with st.form("ocr_form"):
            model_name = st.radio("Choose a model 👉", key="model_choser_0",
                                  options=st.session_state["configured_models"].keys())
            placeholder = "Describe which characters shall be extracted. Give context about the image, if necessary..."
            prompt = st.text_area("Prompt", placeholder=placeholder)
            temperature = st.slider("Temperature", 0., 1., 0., step=0.01)
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

            run_ocr_button = st.form_submit_button("Run OCR")

            if run_ocr_button and model_name is None:
                st.toast("No model selected. Configure a model first!")
                return None

            if run_ocr_button and len(prompt) == 0:
                st.toast("No prompt given.")
                return None

            if run_ocr_button and len(uploaded_images) == 0:
                st.toast("No images uploaded.")
                return None

            if run_ocr_button:
                dfs = []
                progress_text = "OCR in progress. Please wait."
                progress_bar = st.progress(0, text=progress_text)
                for i, image_name in enumerate(uploaded_images):
                    t0 = time.time()
                    json_output = self._request_be.post("recognize_values", payload=payload, image_name=image_name)
                    logger.info(f"image name: {image_name}, output: {json_output}")
                    logger.info(f"Process duration for {i}th image: {time.time() - t0} sec.")
                    dfs.append(pd.DataFrame(json_output, index=[i]))

                    progress_bar.progress((i + 1) / len(st.session_state["uploaded_images"]), text=progress_text)
                progress_bar.empty()

                st.session_state["uploaded_images"] = []

                return pd.concat(dfs)

            return None

    def build_run_plot_form(self) -> Callable | None:
        with (st.form("plot_form")):
            meta_data_df = {
                "dtypes": {col_name: dtype.name for col_name, dtype in st.session_state["df"].dtypes.to_dict().items()},
                "describe": st.session_state["df"].describe().to_dict()
            }
            if st.session_state.get("plot_suggestions", None) is None:
                plot_suggestion_payload = {
                    "meta_data_df": meta_data_df,
                    "parameters": {
                        "temperature": self._temperature,
                        "top_p": self._top_p
                    }
                }
                response_json = self._request_be.post("plot_suggestions", payload=plot_suggestion_payload)
                st.session_state["plot_suggestions"] = response_json["list_of_suggestions"]

            plot_suggestion = st.radio("Choose a plot suggestion 👉", key="plot_suggestion", index=None,
                                       options=st.session_state["plot_suggestions"])
            custom = st.text_area("Custom plot suggestion", height=68)
            if custom is not None:
                plot_suggestion = custom
            model_name = st.radio("Choose a model 👉", key="model_choser_2",
                                  options=st.session_state["configured_models"].keys())
            temperature_plot = st.slider("Temperature", 0., 1., 0., step=0.01)
            top_p_plot = st.number_input("Top p", 0., 1., 0.1)

            plot_payload = {
                "meta_data_df": meta_data_df,
                "prompt_suggestion": plot_suggestion,
                "model_name": model_name,
                "parameters": {
                    "temperature": temperature_plot,
                    "top_p": top_p_plot
                }
            }

            run_plot_button = st.form_submit_button("Run Plot")

            if run_plot_button and model_name is None:
                st.toast("No model selected. Configure a model first!")
                return None

            if run_plot_button and plot_suggestion is None:
                st.toast("No plot suggestion selected.")
                return None

            if run_plot_button:
                response = self._request_be.post("plot_code", payload=plot_payload)
                code = response["code"]
                prompt_check = response["prompt_check"]
                code_check = response["code_check"]

                if not prompt_check:
                    st.error("Prompt contains malicious behaviour that can't be executed.")
                    return None

                if not code_check and code is not None:
                    st.error("Code contains malicious behaviour that can't be executed.")
                    return None

                localdict = {}
                def plot(df):
                    pass
                exec(code, globals(), localdict)
                return localdict["plot"]

            return None

    def build_run_plot(self) -> None:
        if st.session_state["df"] is not None:
            with st.container(border=True):
                plot_func = self.build_run_plot_form()

            with st.container(border=True):
                if plot_func is not None:
                    df = st.session_state["df"].copy()
                    fig, ax = plot_func(df)
                    st.pyplot(fig)

    def build_run_ocr(self) -> None:
        with st.container(border=True):
            df = self.build_run_ocr_form()
            st.session_state["df"] = df if df is not None else st.session_state["df"]

            if st.session_state["df"] is not None:
                st.dataframe(st.session_state["df"].head())
                st.download_button(
                    label="Download data as CSV",
                    data=self.convert_df(st.session_state["df"]),
                    file_name="df_ai_ocr.csv",
                    mime="text/csv"
                )


ai_ocr_frontend = AiOcrFrontend()
ai_ocr_frontend.build_page()
