FROM python:3.12-slim

WORKDIR /code

ARG REQUIREMENTS_FILE=requirements.txt

COPY ${REQUIREMENTS_FILE} /code/requirements.txt

RUN pip install --no-cache-dir -r /code/requirements.txt

COPY . .

EXPOSE 8000
EXPOSE 8501