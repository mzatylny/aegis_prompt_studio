FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN addgroup --system aegis \
    && adduser --system --ingroup aegis --home /home/aegis aegis
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --upgrade pip setuptools \
    && pip install .
COPY --chown=aegis:aegis .streamlit ./.streamlit

EXPOSE 8000 8501
USER aegis
CMD ["streamlit", "run", "src/aegis_prompt_studio/ui.py", "--server.address=0.0.0.0"]
