# from os.path import dirname
from pathlib import Path
from re import search
from setuptools import setup
from setuptools.command.build_py import build_py
from subprocess import Popen, PIPE

# build with python setup.py bdist_wheel
# upload to testpypi w/ python3 -m twine upload --repository testpypi dist/*


class CustomBuildCommand(build_py):
	def run(self):
		here = Path(__file__).parent.resolve()
		with open(here / "exsclaim" / "version.py") as f:
			# version will be loaded in from the minimal version file
			version_info = f.read()

		version_number = search(r"_?_?version_?_?\s*=\s*['\"]([\d.b]+)['\"]", version_info)
		version = version_number.group(1) if version_number else "None"

		here = Path(__file__).parent.resolve()

		# Inspired by numpy's gitversion.py which dynamically writes the __version__, as well as git information for logging.
		git_hash = "None"

		try:
			p = Popen(["git", "log", "-1", "--format=\"%H\""],
					  stdout=PIPE,
					  stderr=PIPE,
					  cwd=here)# dirname(__file__)
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
			f.write(version_info)


setup(
	cmdclass={
		"build_py": CustomBuildCommand,
	},
)
