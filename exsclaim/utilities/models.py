"""Code for loading models from checkpoints saved in GoogleDrive

Model names are mapped to googleids in model_names_to_google_ids."""
from .download import download_file_from_google_drive
from aiohttp import ClientSession
from asyncio import Lock
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from torch import load, nn
from typing import Literal

__all__ = ["download_model_checkpoint", "load_model_from_checkpoint", "model_names_to_googleids"]


"""Stores the Google Drive file IDs of default neural network checkpoints replace these if you wish to change a model"""
model_names_to_googleids:dict[str, str] = {
    "classifier_model.pt": "16BxXXGJyHfMtzhDEufIwMkcDoBftZosh",
    "object_detection_model.pt": "1HbzvNvhPcvUKh_RCddjKIvdRFt6T4PEH",
    "text_recognition_model.pt": "1p9miOnR_dUxO5jpIv1hKtsZQuFHAaQpX",
    "scale_bar_detection_model.pt": "11Kfu9xEbjG0Mw2u0zCJlKy_4C6K21qqg",
    "scale_label_recognition_model.pt": "1AND30sQpSrph2CGl86k2aWNqNp-0vLnR",
}


async def download_model_checkpoint(file_path:Path, exsclaim_domain:str = "https://api.exsclaim-dev.materialeyes.org"):
	"""Downloads a model from the EXSCLAIM servers. The name of the file_path object should match with the name in the server, and the file_path is where it'll be stored."""
	async with ClientSession() as session:
		url = f"{exsclaim_domain.rstrip('/')}/checkpoints/{file_path.name}"
		async with session.get(url) as response:
			match response.status:
				case 200:
					...
				case 404:
					raise FileNotFoundError(f"{url} [404] - {await response.text()}")
				case 503:
					raise ConnectionError(f"{url} [503] - Something is wrong with the EXSCLAIM server and checkpoints cannot be downloaded at this time. Please try again later.")
				case _:
					raise ConnectionError(f"{url} [{response.status}] - Unknown error from the EXSCLAIM server.")

			hash_digest = response.headers["X-Sha256-Hash"].upper()
			hash_obj = sha256()

			buffer = BytesIO()
			buffer_size = 1_024

			async for bytes_ in response.content.iter_chunked(buffer_size):
				buffer.write(bytes_)
				hash_obj.update(bytes_)

	received_digest = hash_obj.hexdigest().upper()

	if received_digest != hash_digest:
		raise ValueError(f"The hash of {file_path.name} ({received_digest}) does not match the expected hash from the server ({hash_digest}).")

	file_path.parent.mkdir(parents=True, exist_ok=True)

	with open(file_path, 'wb') as file:
		file.write(buffer.getvalue())


# FIXME: Convert all usages of this to async
async def load_model_from_checkpoint(model:nn.Module, model_name: Literal["classifier_model.pt", "object_detection_model.pt",
                                "text_recognition_model.pt", "scale_bar_detection_model.pt", "scale_label_recognition_model.pt"],
                               cuda:bool, device) -> nn.Module:
    """load checkpoint weights into model"""
    checkpoints_path = Path(__file__).parent.parent / "figures" / "checkpoints"
    checkpoint = checkpoints_path / model_name
    model.to(device)

    # download the model if isn't already
    if not checkpoint.is_file():
        checkpoints_path.mkdir(exist_ok=True)
        file_id = model_names_to_googleids[model_name]
        await download_file_from_google_drive(file_id, checkpoint)

    if cuda:
        model.load_state_dict(load(checkpoint))
        model = model.cuda()
    else:
        model.load_state_dict(load(checkpoint, map_location="cpu"))

    model.lock = Lock()

    return model
