from setuptools import setup, find_packages
from pathlib import Path
from os import system

# build with python setup.py bdist_wheel
# upload to testpypi w/ python3 -m twine upload --repository testpypi dist/*

here = Path(__file__).parent.resolve()
with open(here / "exsclaim" / "version.py") as f:
	# version will be loaded in from the minimal version file
	exec(f.read())


def install_playwright_dependencies():
	from sys import platform
	if "linux" in platform:
		system("apt update && apt install ffmpeg libsm6 libxext6 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libatspi2.0-0 libxcomposite1 libxdamage1 -y")

	system("playwright install-deps && playwright install chromium")


def write_version():
	"""
	Inspired by numpy's gitversion.py which dynamically writes the __version__, as well as git information for logging.
	"""
	from subprocess import Popen, PIPE
	from os.path import dirname, join

	git_hash = "None"

	try:
		p = Popen(["git", "log", "-1", "--format=\"%H\""],
				  stdout=PIPE,
				  stderr=PIPE,
				  cwd=dirname(__file__))
	except FileNotFoundError:
		pass
	else:
		out, err = p.communicate()
		if p.returncode == 0:
			git_hash = out.decode("utf-8").strip()

	with open(here / "exsclaim" / "version.py", 'w', encoding="utf-8") as f:
		f.write(f'version = "{version}"\n'
				'__version__ = version\n'
				'full_version = version\n\n'
				f'git_revision = {git_hash}\n' # Quotes are included in git_hash
				'release = "b" not in version\n'
				'short_version = version.split("b")[0]')


with open(here / "README.md", "r") as fh:
	long_description = fh.read()

with open(here / "requirements.txt", "r") as f:
	install_requires = list(f.read().splitlines())

url = "https://github.com/MaterialEyes/exsclaim2.0"

setup(
	name="exsclaim",
	version=version,
	author="Eric Schwenker, Trevor Spreadbury, Weixin Jiang, Maria Chan",
	author_email="developer@materialeyes.org",
	description="EXSCLAIM! is a library for the automatic EXtraction, Separation, and Caption-based natural Language Annotation of IMages from scientific figures.",
	long_description=long_description,
	long_description_content_type="text/markdown",
	url=url,
	packages=find_packages(),
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
			'exsclaim=exsclaim.__main__:main',
		],
	},
	python_requires='>=3.10',
	project_urls={
		"Documentation": f"{url}/wiki",
		"Source": url,
		"Issue Tracker": f"{url}/issues",
	},
)

write_version()
install_playwright_dependencies()
