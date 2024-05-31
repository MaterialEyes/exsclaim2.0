"""Functions for downloading from Google Drive

Adapted from `this StackOverflow <https://stackoverflow.com/questions/38511444/>`_
"""
from requests import Session, Response


__ALL__ = ["download_file_from_google_drive", "get_confirm_token", "save_response_content"]


def download_file_from_google_drive(file_id:str, destination:str):
    URL = "https://docs.google.com/uc?export=download"
    session = Session()
    response = session.get(URL, params={"id": file_id}, stream=True)
    token = get_confirm_token(response)
    if token:
        params = {"id": file_id, "confirm": token}
        response = session.get(URL, params=params, stream=True)
    save_response_content(response, destination)


def get_confirm_token(response:Response):
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            return value
    return None


def save_response_content(response, destination):
    CHUNK_SIZE = 32_768
    with open(destination, "wb") as f:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
