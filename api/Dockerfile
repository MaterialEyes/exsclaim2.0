FROM python:3.11 as base
ENV PYTHONUNBUFFERED 1
ARG ENV
ARG EXSCLAIM_GITHUB=MaterialEyes/exsclaim
ARG EXSCLAIM_GIT_REVISION

# Allows docker to cache installed dependencies between builds
COPY ./requirements requirements
RUN bash requirements/install_requirements.sh

# Can't use -n "$EXSCLAIM_GIT_REVISION" because even if the revision has a value, it will run as if it doesn't
RUN if [ "$EXSCLAIM_GIT_REVISION" = "" ]; then \
		pip install "git+https://github.com/$EXSCLAIM_GITHUB.git" ;\
    else \
		pip install "git+https://github.com/$EXSCLAIM_GITHUB.git@$EXSCLAIM_GIT_REVISION" ;\
    fi

RUN apt update && apt install ffmpeg libsm6 libxext6 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libatspi2.0-0 libxcomposite1 libxdamage1 -y

COPY manage.py code/
COPY mkdocs.yml code/
COPY setup.cfg code/
COPY wait_for_postgres.py code/

COPY ./apps code/
COPY ./config code/
COPY ./docs code/

WORKDIR /code

EXPOSE 8000

# Run the production server
# CMD newrelic-admin run-program gunicorn --bind 0.0.0.0:$PORT --access-logfile - config.wsgi:application

FROM base as prod
COPY . code
RUN pip list