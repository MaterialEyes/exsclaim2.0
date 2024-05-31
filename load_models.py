from os import umask, makedirs
from exsclaim.utilities import download_file_from_google_drive

model_path = "./exsclaim/figures/checkpoints"
umask(0)
makedirs(model_path, mode=0o777, exist_ok=True)

download_file_from_google_drive('1ZodeH37Nd4ZbA0_1G_MkLKuuiyk7VUXR', f'{model_path}/classifier_model.pt')
download_file_from_google_drive('1Hh7IPTEc-oTWDGAxI9o0lKrv9MBgP4rm', f'{model_path}/object_detection_model.pt')
download_file_from_google_drive('1rZaxCPEWKGwvwYYa8jLINpUt20h0jo8y', f'{model_path}/text_recognition_model.pt')
download_file_from_google_drive('1B4_rMbP3a1XguHHX4EnJ6tSlyCCRIiy4', f'{model_path}/scale_bar_detection_model.pt')
download_file_from_google_drive('1oGjPG698LdSGvv3FhrLYh_1FhcmYYKpu', f'{model_path}/scale_label_recognition_model.pt')
