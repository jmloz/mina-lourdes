#!/usr/bin/env bash
# Arranque de Mina Lourdes en Linux / macOS.
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: no se encontró python3. Instale Python 3.11 o superior." >&2
  exit 1
fi

# Crea (o repara) el entorno virtual.
if [ ! -x .venv/bin/python ]; then
  rm -rf .venv
  python3 -m venv .venv
fi

.venv/bin/python -m pip install -q -r requirements.txt
exec .venv/bin/python run.py
