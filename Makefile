.PHONY: install test evaluate lint security quality api ui docker

install:
	python -m pip install -r requirements.txt

test:
	pytest --cov=src/aegis_prompt_studio --cov-report=term-missing

evaluate:
	aegis evaluate --min-precision 0.90 --min-recall 0.90 --min-f1 0.90

lint:
	ruff check .

security:
	bandit -r src -q
	pip-audit --local --skip-editable

quality: lint test evaluate security

api:
	uvicorn aegis_prompt_studio.api:app --reload --port 8000

ui:
	streamlit run src/aegis_prompt_studio/ui.py

docker:
	docker compose up --build
