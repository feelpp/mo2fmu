#!/bin/bash
# Quick check script - Run all code quality checks with uv
# Usage: ./check.sh

set -e

VENV=".venv-mo2fmu"

echo "🔍 Running code quality checks with uv..."
echo ""

echo "1️⃣  Checking imports and formatting with ruff..."
uv run --python $VENV ruff check src/python tests || { echo "❌ ruff check failed. Run 'make format' to fix."; exit 1; }
echo "✅ ruff check passed"
echo ""

echo "2️⃣  Checking code formatting with Black..."
uv run --python $VENV black --check src/python tests || { echo "❌ Black check failed. Run 'make format' to fix."; exit 1; }
echo "✅ Black check passed"
echo ""

echo "3️⃣  Running flake8..."
uv run --python $VENV flake8 src/python tests || { echo "❌ flake8 check failed."; exit 1; }
echo "✅ flake8 passed"
echo ""

echo "4️⃣  Running mypy type checking..."
uv run --python $VENV mypy src/python || { echo "❌ mypy check failed."; exit 1; }
echo "✅ mypy passed"
echo ""

echo "5️⃣  Running tests..."
uv run --python $VENV pytest tests/ || { echo "❌ tests failed."; exit 1; }
echo "✅ tests passed"
echo ""

echo "🎉 All checks passed! Ready to commit."
