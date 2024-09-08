import requests
from src.ai_ocr_client.response_be import BeResponse
from streamlit.runtime.uploaded_file_manager import UploadedFile
from typing import Union, List, Optional


class BeRequest:
    def __init__(self, ip: str = "127.0.0.1", port: int = 5000, protocol: str = "http"):
        self._url = f"{protocol}://{ip}:{port}"

    def get(self, path: str) -> dict:
        response = requests.get(f"{self._url}/{path}")
        return BeResponse(response=response).json()

    def post(self, path: str, payload: Union[dict, List[dict], None], images: Optional[List[UploadedFile]] = None,
             image_name: Optional[str] = None) -> dict:
        if images is not None:
            images = [("images", image) for image in images]
            response = BeResponse(response=requests.post(f"{self._url}/{path}", files=images))
        elif image_name is not None:
            response = BeResponse(response=requests.post(f"{self._url}/{path}?image_name={image_name}", json=payload))
        else:
            response = BeResponse(response=requests.post(f"{self._url}/{path}", json=payload))

        if response.is_error():
            raise RuntimeError("Something went wrong with the post request...")
        else:
            return response.json()
