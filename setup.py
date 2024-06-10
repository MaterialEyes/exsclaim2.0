from setuptools import setup
from pathlib import Path
from os import system

# build with python setup.py bdist_wheel
# upload to testpypi w/ python3 -m twine upload --repository testpypi dist/*

here = Path(__file__).parent.resolve()

with open(here / "README.md", "r") as fh:
	long_description = fh.read()

with open(here / "requirements.txt", "r") as f:
	install_requires = list(f.read().splitlines())

setup(
	name="exsclaim",
	version="2.0.2b0",
	author=('Eric Schwenker','Trevor Spreadbury','Weixin Jiang','Maria Chan'),
	author_email="developer@materialeyes.org",
	description="EXSCLAIM! is a library for the automatic EXtraction, Separation, and Caption-based natural Language Annotation of IMages from scientific figures.",
	long_description=long_description,
	long_description_content_type="text/markdown",
	url="https://github.com/MaterialEyes/exsclaim",
	packages=setuptools.find_packages(),
	install_requires=install_requires,
	package_data={
		'exsclaim': ['figures/config/yolov3_default_master.cfg',
					 'figures/config/yolov3_default_subfig.cfg',
					 'figures/config/scale_label_reader.json',
					 'figures/scale/corpus.txt',
					 'captions/models/characterization.yml',
					 'captions/models/patterns.yml',
					 'captions/models/reference.yml',
					 'captions/models/rules.yml',
					 'tests/data/nature_test.json',
					 'ui/static/*',
					 'ui/static/style/*',
					 'ui/static/scripts/*',
					 'ui/home/templates/exsclaim/*',
					 'ui/results/templates/exsclaim/*',
					 'ui/query/templates/exsclaim/*',
					 'utilities/database.ini',
					 'tests/data/images/pipeline/*',
					 'tests/data/nature_articles/*',
					 'tests/data/nature_search.html',
					 'tests/data/images/scale_bar_test_images/*',
					 'tests/data/images/scale_label_test_images/*',
					 'tests/data/nature_closed_expected.json']
	},
	classifiers=[
		"Development Status :: 4 - Beta",
		"Intended Audience :: Science/Research",
		"Topic :: Scientific/Engineering :: Image Processing",
		"Programming Language :: Python :: 3",
		"License :: OSI Approved :: MIT License",
		"Operating System :: OS Independent",
	],
	entry_points={
		'console_scripts': [
			'exsclaim=exsclaim.command_line:main',
		],
	},
	python_requires='>=3.10',
	project_urls={
		'Documentation': 'https://github.com/MaterialEyes/exsclaim/wiki',
		'Source': 'https://github.com/MaterialEyes/exsclaim',
		'Tracker': 'https://github.com/MaterialEyes/exsclaim/issues',
	},
)


def download_file_from_google_drive(_id:str, destination:str | Path):
	system(f"gdown https://docs.google.com/uc?id={_id} -O {destination}")


def download_models():
	from site import getsitepackages

	models_path = Path(getsitepackages()[0]) / "exsclaim" / "figures" / "checkpoints"
	models_path.mkdir(exist_ok=True)
	for _id, destination in (
			('1ZodeH37Nd4ZbA0_1G_MkLKuuiyk7VUXR', 'classifier_model.pt'),
			('1Hh7IPTEc-oTWDGAxI9o0lKrv9MBgP4rm', 'object_detection_model.pt'),
			('1rZaxCPEWKGwvwYYa8jLINpUt20h0jo8y', 'text_recognition_model.pt'),
			('1B4_rMbP3a1XguHHX4EnJ6tSlyCCRIiy4', 'scale_bar_detection_model.pt'),
			('1oGjPG698LdSGvv3FhrLYh_1FhcmYYKpu', 'scale_label_recognition_model.pt'),
	):
		download_file_from_google_drive(_id, models_path / destination)