"""Code for loading models from checkpoints saved in GoogleDrive

Model names are mapped to googleids in model_names_to_google_ids."""
import os
from .download import download_file_from_google_drive
from torch import load
from pathlib import Path


__ALL__ = ["load_model_from_checkpoint", "models_to_googleids"]


# stores the google drive file IDs of default neural network checkpoints
# replace these if you wish to change a model
model_names_to_googleids = {
    "classifier_model.pt": "16BxXXGJyHfMtzhDEufIwMkcDoBftZosh",
    "object_detection_model.pt": "1HbzvNvhPcvUKh_RCddjKIvdRFt6T4PEH",
    "text_recognition_model.pt": "1p9miOnR_dUxO5jpIv1hKtsZQuFHAaQpX",
    "scale_bar_detection_model.pt": "11Kfu9xEbjG0Mw2u0zCJlKy_4C6K21qqg",
    "scale_label_recognition_model.pt": "1AND30sQpSrph2CGl86k2aWNqNp-0vLnR",
}


def load_model_from_checkpoint(model, model_name, cuda, device):
    """load checkpoint weights into model"""
    checkpoints_path = Path(__file__).parent.parent / "figures" / "checkpoints"
    checkpoint = checkpoints_path / model_name
    model.to(device)

    # download the model if isn't already
    if not os.path.isfile(checkpoint):
        os.makedirs(checkpoints_path, exist_ok=True)
        file_id = model_names_to_googleids[model_name]
        download_file_from_google_drive(file_id, checkpoint)

    if cuda:
        model.load_state_dict(load(checkpoint))
        model = model.cuda()
    else:
        model.load_state_dict(load(checkpoint, map_location="cpu"))

    return model
