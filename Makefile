.PHONY: install install-dev lint format test run

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -e ".[dev]"

lint:
	ruff check src scripts tests

format:
	ruff format src scripts tests

test:
	pytest tests/ -v

run:
	python -m github_top50
