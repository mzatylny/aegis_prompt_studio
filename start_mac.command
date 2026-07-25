#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .

if [ ! -f ".env" ]; then
  cp .env.example .env
fi

uvicorn aegis_prompt_studio.api:app --host 127.0.0.1 --port 8000 > /tmp/aegis_prompt_api.log 2>&1 &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT INT TERM

streamlit run src/aegis_prompt_studio/ui.py --server.port=8501

