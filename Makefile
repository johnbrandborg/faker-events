test:
	tox -e py

lint:
	tox -e flake8

build: clean
	python setup.py sdist bdist_wheel

publish:
	twine upload dist/*

dev:
	pip install -e .[dev]

clean:
	rm -rf build dist

.PHONY: test build release dev clean
