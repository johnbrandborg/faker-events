test:
	@pytest

lint:
	@flake8

build: clean
	@python setup.py sdist bdist_wheel

publish:
	@twine upload dist/*

dev:
	@pip install -e .[dev]

clean:
	@find . -name '__pycache__' | xargs rm -fr
	@rm -rf build dist

help:
	@echo "\
Targets\n\
------------------------------------------------------------------------\n\
 test:		Perform unit testing on the source code\n\
 lint:		Perform quality checks on the source code\n\
 build:		Creates the Python Package\n\
 publish:	Uploads the Python Package to PyPi\n\
 dev:		Installs all requirements and testing requirements\n\
 clean:		Removes built Python Packages and cached byte code\n\
 help:		Displays the help menu with all the targets\n";

.DEFAULT_GOAL := help
.PHONY: test build release dev clean help
