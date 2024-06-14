"""Functions for downloading from Google Drive

Adapted from `this StackOverflow <https://stackoverflow.com/questions/38511444/>`_
"""
from bs4 import BeautifulSoup
from requests import Session, Response


__all__ = ["download_file_from_google_drive", "get_confirm_token", "save_response_content"]


def download_file_from_google_drive(file_id:str, destination:str):
    URL = "https://drive.usercontent.google.com/download"
    session = Session()
    params = {"id": file_id, "export": "download", "confirm":"t"}
    response = session.get(URL, params=params, stream=True)
    token = get_confirm_token(response)
    if token:
        params |= token
        response2 = session.get(URL, params=params, stream=True)
        response = response2
    save_response_content(response, destination)


def get_confirm_token(response:Response) -> dict | None:
    for header, value in response.headers.items():
        if header == "Content-Type":
            if value == "application/octet-stream":
                return None
            if value.startswith("text/html"):
                break
    else:
        return None

    # Need to press the Download anyway button
    soup = BeautifulSoup(response.text, "html.parser")
    form = soup.select_one("form#download-form")
    return {_input["name"]: _input["value"] for _input in form.find_all("input", attrs={"type": "hidden"})}


def save_response_content(response, destination):
    CHUNK_SIZE = 32_768
    with open(destination, "wb") as f:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
