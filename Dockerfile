FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install .
COPY .streamlit ./.streamlit

EXPOSE 8000 8501
CMD ["streamlit", "run", "src/aegis_prompt_studio/ui.py", "--server.address=0.0.0.0"]
