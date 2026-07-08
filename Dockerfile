FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /code

ARG REQUIREMENTS_FILE=requirements.txt

COPY ${REQUIREMENTS_FILE} /code/requirements.txt

RUN addgroup --system app && adduser --system --ingroup app app \
    && pip install --no-cache-dir -r /code/requirements.txt

COPY . .

USER app

EXPOSE 8000
EXPOSE 8501
