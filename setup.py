from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in tag_workflow/__init__.py
from tag_workflow import __version__ as version

setup(
	name="tag_workflow",
	version=version,
	description="App to cater for custom development",
	author="SourceFuse",
	author_email="shadab.sutar@sourcefuse.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
