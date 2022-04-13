FROM python:3.10.4-slim

ARG DEV_DEPS=0

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN python -m pip install --upgrade pip poetry
RUN poetry config virtualenvs.create false

WORKDIR /app

COPY ./pyproject.toml ./poetry.lock ./

RUN if [ $DEV_DEPS = 1 ] ; then \
    poetry install --no-interaction --no-ansi ; else \
    poetry install --no-dev --no-interaction --no-ansi ; fi

COPY . ./
   
