#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
export PYTHONPATH=.

find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

if [ ! -d ".venv" ]; then
    echo "Creando entorno virtual..."
    if python3 -m venv .venv 2>/dev/null; then
        :
    else
        echo "Aviso: no se pudo crear .venv (instala python3-venv)."
        echo "Usando Python del sistema..."
        USE_SYSTEM=1
    fi
fi

if [ "${USE_SYSTEM:-}" != "1" ]; then
    source .venv/bin/activate
    pip install -q -r requirements.txt
else
    pip3 install --user --break-system-packages -q -r requirements.txt 2>/dev/null || true
fi

echo ""
echo "Iniciando Validador ADG en http://localhost:8501"
echo ""
PYTHONPATH=. streamlit run app.py
