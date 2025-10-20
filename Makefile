.PHONY: help venv install install-dev clean clean-all lint format type-check test test-cov all-checks build publish

# Unset VIRTUAL_ENV to avoid uv warnings
unexport VIRTUAL_ENV

help:
	@echo "Available targets:"
	@echo "  venv          - Create virtual environment with uv"
	@echo "  install       - Install package in editable mode with uv"
	@echo "  install-dev   - Install package with all development dependencies"
	@echo "  clean         - Remove build artifacts and cache files"
	@echo "  clean-all     - Remove build artifacts, caches, and virtual environment"
	@echo "  lint          - Run linting (flake8, ruff)"
	@echo "  format        - Format code (black, isort)"
	@echo "  format-check  - Check code formatting without making changes"
	@echo "  type-check    - Run type checking (mypy)"
	@echo "  test          - Run tests"
	@echo "  test-cov      - Run tests with coverage report"
	@echo "  all-checks    - Run all checks (format-check, lint, type-check, test)"
	@echo "  build         - Build distribution packages with uv"
	@echo "  publish       - Publish to PyPI (requires TWINE_USERNAME and TWINE_PASSWORD)"
	@echo "  publish-test  - Publish to TestPyPI"

venv:
	@echo "Creating virtual environment with uv..."
	uv venv .venv-mo2fmu
	@echo "✅ Virtual environment created at .venv-mo2fmu"
	@echo "To install dependencies, run: make install-dev"

install: venv
	uv pip install --python .venv-mo2fmu -e .

install-dev: venv
	uv pip install --python .venv-mo2fmu -e ".[all]"

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf src/**/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/ .pytest_cache/
	@echo "✅ Cleaned build artifacts and caches"

clean-all: clean
	rm -rf .venv-mo2fmu
	@echo "✅ Removed virtual environment"

lint:
	@echo "Running flake8..."
	uv run --python .venv-mo2fmu flake8 src/python tests
	@echo "Running ruff..."
	uv run --python .venv-mo2fmu ruff check src/python tests

format:
	@echo "Organizing imports and formatting..."
	uv run --python .venv-mo2fmu ruff check --fix src/python tests
	@echo "Running black..."
	uv run --python .venv-mo2fmu black src/python tests

format-check:
	@echo "Checking imports and formatting..."
	uv run --python .venv-mo2fmu ruff check src/python tests
	@echo "Checking black..."
	uv run --python .venv-mo2fmu black --check src/python tests

type-check:
	@echo "Running mypy..."
	uv run --python .venv-mo2fmu mypy src/python

test:
	uv run --python .venv-mo2fmu pytest tests/

test-cov:
	uv run --python .venv-mo2fmu pytest --cov=feelpp.mo2fmu --cov-report=term-missing --cov-report=html tests/

all-checks: format-check lint type-check test
	@echo "✅ All checks passed!"

build: clean
	uv build --python .venv-mo2fmu

publish: build
	uv run --python .venv-mo2fmu twine upload dist/*

publish-test: build
	uv run --python .venv-mo2fmu twine upload --repository testpypi dist/*
