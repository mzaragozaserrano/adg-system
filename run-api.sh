#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
export PYTHONPATH=.

mkdir -p data uploads exports

echo "Iniciando API Validador ADG en http://localhost:8000"
PYTHONPATH=. uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
