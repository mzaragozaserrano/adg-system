#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/frontend"

NODE_DIR="$ROOT/.tools/node"
NODE_VERSION="v22.22.0"
NODE_BIN="$NODE_DIR/bin"

ensure_node() {
  if command -v npm >/dev/null 2>&1; then
    return
  fi
  if [ -x "$NODE_BIN/npm" ]; then
    export PATH="$NODE_BIN:$PATH"
    return
  fi

  echo "npm no encontrado. Instalando Node.js portable en .tools/node ..."
  mkdir -p "$ROOT/.tools"
  ARCHIVE="$ROOT/.tools/node.tar.xz"
  curl -fsSL "https://nodejs.org/dist/${NODE_VERSION}/node-${NODE_VERSION}-linux-x64.tar.xz" -o "$ARCHIVE"
  tar -xf "$ARCHIVE" -C "$ROOT/.tools"
  mv "$ROOT/.tools/node-${NODE_VERSION}-linux-x64" "$NODE_DIR"
  rm -f "$ARCHIVE"
  export PATH="$NODE_BIN:$PATH"
}

ensure_node

if [ ! -d "node_modules" ]; then
  npm install
fi

echo ""
echo "Iniciando frontend en http://localhost:5173"
echo ""
npm run dev -- --host 0.0.0.0
