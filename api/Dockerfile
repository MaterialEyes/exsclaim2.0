FROM exsclaim/base AS base

# Allows docker to cache installed dependencies between builds
COPY ./requirements requirements
RUN pip install -r requirements/base.txt

# Run the production server
# CMD newrelic-admin run-program gunicorn --bind 0.0.0.0:$PORT --access-logfile - config.wsgi:application

FROM python:3.11.9 AS prod
ENV PYTHONUNBUFFERED=1

RUN apt update && apt install ffmpeg libsm6 libxext6 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libatspi2.0-0 libxcomposite1 libxdamage1 -y

WORKDIR /code

COPY manage.py ./
COPY mkdocs.yml ./
COPY setup.cfg ./

COPY ./apps ./apps
COPY ./config ./config
COPY ./docs ./docs

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=15s --start-period=20s --retries=4 CMD curl -f http://localhost:8000 || exit 1

COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /usr/local/bin/playwright /usr/local/bin/playwright
COPY --from=base /usr/local/bin/exsclaim /usr/local/bin/exsclaim

RUN playwright install-deps && playwright install chromium

FROM prod AS dev
RUN pip install -r requirements/dev.txt
