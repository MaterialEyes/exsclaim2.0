FROM python:3.8 as base
ENV PYTHONUNBUFFERED 1
ARG ENV

# Allows docker to cache installed dependencies between builds
COPY ./requirements requirements
RUN bash requirements/install_requirements.sh

COPY manage.py code/
COPY mkdocs.yml code/
COPY setup.cfg code/
COPY wait_for_postgres.py code/

WORKDIR /code

EXPOSE 8000

# Run the production server
#CMD newrelic-admin run-program gunicorn --bind 0.0.0.0:$PORT --access-logfile - config.wsgi:application

FROM base as prod
COPY . code