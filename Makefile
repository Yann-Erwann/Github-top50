.PHONY: install install-dev lock lock-check lint format test audit security run

install:
	python -m pip install .

install-dev:
	python -m pip install uv
	python -m uv lock --check
	python -m uv sync --frozen --extra dev

lock:
	python -m uv lock --upgrade

lock-check:
	python -m uv lock --check

lint:
	python -m uv run --frozen --extra dev ruff check src scripts tests

format:
	python -m uv run --frozen --extra dev ruff format src scripts tests

test:
	python -m uv run --frozen --extra dev pytest -v

audit:
	python -m uv run --frozen --extra dev pip-audit

security:
	python -m uv run --frozen --extra dev bandit -q -r src scripts

run:
	python -m uv run --frozen python -m github_top50
