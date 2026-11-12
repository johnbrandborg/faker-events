test:
	python3 -m pytest

test_report:
	python3 -m pytest --cov-report=xml

lint:
	python3 -m ruff check .

type_check:
	python3 -m ty check

format:
	python3 -m ruff format .
	python3 -m ruff check --fix .

install:
	python3 -m pip install -e ".[dev]"

build:
	python3 -m build

clean:
	rm -rf build dist .coverage .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

help:
	@printf "Targets: install format lint type_check test test_report build clean\n"

.DEFAULT_GOAL := help
.PHONY: test test_report lint type_check format install build clean help
