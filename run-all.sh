#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

chmod +x run-api.sh run-frontend.sh

echo "Iniciando Validador ADG..."
echo "  API:      http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo ""
echo "Pulsa Ctrl+C para detener ambos servicios."
echo ""

trap 'kill 0' EXIT

./run-api.sh &
./run-frontend.sh
