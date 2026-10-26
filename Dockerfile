FROM python:3.12.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /code

ARG REQUIREMENTS_FILE=requirements.txt
ARG INSTALL_LANGSMITH=false

COPY ${REQUIREMENTS_FILE} /code/requirements.txt
COPY requirements-langsmith.lock /code/requirements-langsmith.lock

RUN addgroup --system app && adduser --system --ingroup app app \
    && pip install --no-cache-dir --require-hashes -r /code/requirements.txt \
    && if [ "$INSTALL_LANGSMITH" = "true" ]; then \
         pip install --no-cache-dir --require-hashes -r /code/requirements-langsmith.lock; \
       fi

COPY . .

USER app

EXPOSE 8000
EXPOSE 8501
