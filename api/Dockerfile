FROM exsclaim/base AS base

ENV PORT=8000

# Allows docker to cache installed dependencies between builds
WORKDIR /code
COPY ./requirements requirements
RUN pip install -r requirements/base.txt

# Run the production server
# CMD newrelic-admin run-program gunicorn --bind 0.0.0.0:$PORT --access-logfile - config.wsgi:application

COPY manage.py ./
COPY mkdocs.yml ./
COPY setup.cfg ./

COPY ./apps ./apps
COPY ./config ./config
COPY ./docs ./docs

EXPOSE $PORT
HEALTHCHECK --interval=15s --timeout=15s --start-period=20s --retries=4 CMD curl -f http://localhost:$PORT || exit 1
ENTRYPOINT ./manage.py migrate && ./manage.py runserver 0.0.0.0:$PORT


FROM base AS dev
RUN pip install -r requirements/dev.txt
