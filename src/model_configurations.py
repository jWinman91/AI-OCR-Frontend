import streamlit as st

from streamlit_js_eval import streamlit_js_eval
from typing import Union, List

from src.ai_ocr_client.request_be import BeRequest


class ModelConfig:
    def __init__(self, ip: str = "127.0.0.1", port: int = 5000, protocol: str = "http"):
        self._request_be = BeRequest(ip, port, protocol)
        self._all_model_types = [
            "llama_cpp",
            "open_ai"
        ]
        st.session_state["configured_models"] = st.session_state.get("configured_models",
                                                                     self._request_be.get("get_all_unmodified_models"))

    def create_options(self, default_value: Union[str, None] = None) -> List[str]:
        if default_value is None:
            return self._all_model_types
        else:
            self._all_model_types.remove(default_value)
            self._all_model_types = [default_value] + self._all_model_types
            return self._all_model_types

    def build_form(self, form_name: str, default_values: Union[dict, None] = None) -> None:
        if default_values is None:
            default_values = {}

        model_wrapper = st.selectbox("Choose a model type: ", key=f"model_wrapper_{form_name}",
                                     options=self.create_options(default_values.get("model_wrapper", None)))
        config_dict = {
            "model_wrapper": model_wrapper
        }

        if form_name is not None:
            with st.form(form_name):
                if model_wrapper == "llama_cpp":
                    config_dict["repo_id"] = st.text_input("Repository ID", default_values.get("repo_id", None))
                    config_dict["file_name"] = st.text_input("file name", default_values.get("file_name", None))
                    config_dict["clip_model_name"] = st.text_input("clip model name",
                                                                   default_values.get("clip_model_name", None))

                    config_dict["construct_params"] = {"n_gpu_layers": -1}
                    construct_params = default_values.get("construct_params", {})
                    config_dict["construct_params"]["n_ctx"] = st.number_input("Context tokens", 0, 10_000,
                                                                               construct_params.get("n_ctx", None), 1)
                elif model_wrapper == "open_ai":
                    config_dict["model_name"] = st.text_input("Model name", default_values.get("model_name", None))
                    config_dict["openai_api_key"] = st.text_input("API key", None)

                form_button = st.form_submit_button('Update model')

                if form_button:
                    print(config_dict)
                    print(form_name)
                    self._request_be.post("insert_model", payload={
                        "model_name": form_name,
                        "config_dict": config_dict
                    })
                    st.session_state["configured_models"] = self._request_be.get("get_all_unmodified_models")

    def build_config(self, default_name: Union[str, None] = None, default_config: Union[dict, None] = None):
        models_container = st.container(border=True)
        with models_container:
            model_name = st.text_input("Model name", default_name)
            self.build_form(model_name, default_values=default_config)

            if model_name in st.session_state["configured_models"]:
                delete = st.button("Delete model", type="primary", key=default_name)
                if delete:
                    self._request_be.post("delete_models", payload=[model_name])
                    st.session_state["configured_models"] = self._request_be.get("get_all_models")
                    streamlit_js_eval(js_expressions="parent.window.location.reload()")


model_config = ModelConfig(port=5000)
for key, value in st.session_state["configured_models"].items():
    model_config.build_config(key, value)
model_config.build_config()
