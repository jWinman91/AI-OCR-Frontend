from requests import Response


class BeResponse:
    response: Response
    response_json: dict

    def __init__(self, response: Response):
        self.response = response

    def is_error(self) -> bool:
        return not self.response.status_code == 200

    def reason(self):
        return self.response.reason

    def json(self):
        return self.response.json()
