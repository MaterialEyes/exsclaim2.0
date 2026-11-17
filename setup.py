from contextlib import suppress
from pathlib import Path
from setuptools import setup
from setuptools.command.build_py import build_py

import re
import subprocess

# build with python setup.py bdist_wheel
# upload to testpypi w/ python3 -m twine upload --repository testpypi dist/*


class CustomBuildCommand(build_py):
	def run(self):
		here = Path(__file__).parent.resolve()
		with open(here / "exsclaim" / "version.py") as f:
			# version will be loaded in from the minimal version file
			version_info = f.read()

		version_regex = re.compile(r"_?_?version_?_?\s*=\s*['\"]([\d.b]+)['\"]")
		version_number = version_regex.search(version_info)
		version = version_number.group(1) if version_number else None
		if version is None:
			raise ValueError("Could not find version number in exsclaim/version.py")

		here = Path(__file__).parent.resolve()

		# Inspired by numpy's gitversion.py which dynamically writes the __version__, as well as git information for logging.
		git_hash = None

		with suppress(FileNotFoundError):
			p = subprocess.Popen(
				["git", "log", "-1", '--format="%H"'],
				stdout=subprocess.PIPE,
				stderr=None,
				cwd=here
			)

			out, err = p.communicate()
			if p.returncode == 0:
				git_hash = out.decode("utf-8").strip()

		if git_hash is None:
			import os
			git_hash = os.getenv("GITHUB_SHA")
			if isinstance(git_hash, str):
				git_hash = f'"{git_hash.strip()}"'

		new_version_file = []
		with open(here / "exsclaim" / "version.py", 'r', encoding="utf-8") as f:
			for line in f:
				if version_regex.match(line.strip()):
					new_version_file.append(f'version = "{version}"\n')
					new_version_file.append(f'__version__ = "{version}"\n')
					new_version_file.append(f'full_version = "{version}"\n\n')
					new_version_file.append(f"git_revision = {git_hash}\n")	# Quotes are included in git_hash
					new_version_file.append(f"is_release = {'b' not in version}\n")
					new_version_file.append(f'short_version = "{version.split("b")[0]}"\n\n')
				else:
					new_version_file.append(line)

		with open(here / "exsclaim" / "version.py", 'w', encoding="utf-8") as f:
			f.writelines(new_version_file)

		super().run()


setup(
	cmdclass={
		"build_py": CustomBuildCommand,
	},
)
