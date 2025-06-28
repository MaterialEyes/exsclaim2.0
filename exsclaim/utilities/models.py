"""Code for loading models from checkpoints saved in GoogleDrive

Model names are mapped to googleids in model_names_to_google_ids."""
from .download import download_file_from_google_drive
from asyncio import Lock
from torch import load, nn
from pathlib import Path
from typing import Literal

__all__ = ["load_model_from_checkpoint", "model_names_to_googleids"]


"""Stores the Google Drive file IDs of default neural network checkpoints replace these if you wish to change a model"""
model_names_to_googleids:dict[str, str] = {
    "classifier_model.pt": "16BxXXGJyHfMtzhDEufIwMkcDoBftZosh",
    "object_detection_model.pt": "1HbzvNvhPcvUKh_RCddjKIvdRFt6T4PEH",
    "text_recognition_model.pt": "1p9miOnR_dUxO5jpIv1hKtsZQuFHAaQpX",
    "scale_bar_detection_model.pt": "11Kfu9xEbjG0Mw2u0zCJlKy_4C6K21qqg",
    "scale_label_recognition_model.pt": "1AND30sQpSrph2CGl86k2aWNqNp-0vLnR",
}


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
