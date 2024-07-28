from pathlib import Path
from exsclaim import __file__ as exsclaim_path # The absolute file path to .../site-packages/exsclaim/__init__.py
from exsclaim.utilities import download_file_from_google_drive


def main():
	model_path = Path(exsclaim_path).parent / "figures" / "checkpoints"
	model_path.mkdir(mode=0o777, exist_ok=True)

	for file_id, file in (
		("1ZodeH37Nd4ZbA0_1G_MkLKuuiyk7VUXR", "classifier_model.pt"),
		("1Hh7IPTEc-oTWDGAxI9o0lKrv9MBgP4rm", "object_detection_model.pt"),
		("1rZaxCPEWKGwvwYYa8jLINpUt20h0jo8y", "text_recognition_model.pt"),
		("1B4_rMbP3a1XguHHX4EnJ6tSlyCCRIiy4", "scale_bar_detection_model.pt"),
		("1oGjPG698LdSGvv3FhrLYh_1FhcmYYKpu", "scale_label_recognition_model.pt"),
	):
		download_file_from_google_drive(file_id, model_path / file)


if __name__ == "__main__":
	main()
