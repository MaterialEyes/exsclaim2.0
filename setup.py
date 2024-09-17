from os.path import dirname
from os import system
from pathlib import Path
from setuptools import setup
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.install import install as _install
from subprocess import Popen, PIPE
from sys import platform

# build with python setup.py bdist_wheel
# upload to testpypi w/ python3 -m twine upload --repository testpypi dist/*


class CustomBuildCommand(_build_py):
	def run(self):
		here = Path(__file__).parent.resolve()
		version_dct = dict()
		with open(here / "exsclaim" / "version.py") as f:
			# version will be loaded in from the minimal version file
			exec(original_version := f.read(), globals(), version_dct)
		version = version_dct['version']

		here = Path(__file__).parent.resolve()

		# Inspired by numpy's gitversion.py which dynamically writes the __version__, as well as git information for logging.
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
					f'git_revision = {git_hash}\n'  # Quotes are included in git_hash
					'release = "b" not in version\n'
					'short_version = version.split("b")[0]')

		super().run()
		with open(here / "exsclaim" / "version.py", 'w', encoding="utf-8") as f:
			f.write(original_version)

		# TODO: Set up code to build exsclaim_ui_components
		# Maybe use the dashboard dockerfile to build, it should be compatible


class CustomInstallCommand(_install):
	def run(self):
		super().run()
		if self.distribution.script_name == "setup.py":
			if "linux" in platform:
				system(
					"apt update && apt install ffmpeg libsm6 libxext6 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libatspi2.0-0 libxcomposite1 libxdamage1 -y")

			system("exsclaim install-deps")
		else:
			print("Skipping install tasks during build.")


setup(
	cmdclass={
		"build_py": CustomBuildCommand,
		"install": CustomInstallCommand
	},
)
