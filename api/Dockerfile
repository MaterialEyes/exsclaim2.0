FROM python:3.11 as base
ENV PYTHONUNBUFFERED 1
ARG ENV
ARG EXSCLAIM_GITHUB=MaterialEyes/exsclaim
ARG EXSCLAIM_GIT_REVISION

# Allows docker to cache installed dependencies between builds
COPY ./requirements requirements
RUN bash requirements/install_requirements.sh
RUN if [[ -n "$EXSCLAIM_GIT_REVISION" ]]; then \
		pip install "git+https://github.com/$EXSCLAIM_GITHUB.git@$EXSCLAIM_GIT_REVISION" ;\
    else \
		pip install "git+https://github.com/$EXSCLAIM_GITHUB.git" ;\
    fi
# pip install git+https://github.com/MaterialEyes/exsclaim.git

RUN pip install langchain langchain-community transformers openai

RUN apt update && apt install ffmpeg libsm6 libxext6 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libatspi2.0-0 libxcomposite1 libxdamage1 -y

COPY manage.py code/
COPY mkdocs.yml code/
COPY setup.cfg code/
COPY wait_for_postgres.py code/

WORKDIR /code

EXPOSE 8000

# Run the production server
# CMD newrelic-admin run-program gunicorn --bind 0.0.0.0:$PORT --access-logfile - config.wsgi:application

FROM base as prod
COPY . code
RUN pip list