.PHONY: install test lint api ui docker

install:
	python -m pip install -r requirements.txt

test:
	pytest

lint:
	ruff check .

api:
	uvicorn aegis_prompt_studio.api:app --reload --port 8000

ui:
	streamlit run src/aegis_prompt_studio/ui.py

docker:
	docker compose up --build
