FROM python:3.11.9 AS base

ENV PYTHONUNBUFFERED=1
ARG ENV
ARG EXSCLAIM_GITHUB=MaterialEyes/exsclaim
ARG EXSCLAIM_GIT_REVISION

# Allows docker to cache installed dependencies between builds
COPY ./requirements requirements
RUN pip install -r requirements/base.txt
# FIXME: Not running when $ENV is dev
#RUN if [[ "$ENV" == "dev" ]]; then \
#    	wait 5s; \
#    	pip install -r requirements/dev.txt; \
#    fi
RUN pip install -r requirements/dev.txt

# Can't use -n "$EXSCLAIM_GIT_REVISION" because even if the revision has a value, it will run as if it doesn't
RUN if [ "$EXSCLAIM_GIT_REVISION" = "" ]; then \
		pip install "git+https://github.com/$EXSCLAIM_GITHUB.git" ;\
    else \
		pip install "git+https://github.com/$EXSCLAIM_GITHUB.git@$EXSCLAIM_GIT_REVISION" ;\
    fi

# Run the production server
# CMD newrelic-admin run-program gunicorn --bind 0.0.0.0:$PORT --access-logfile - config.wsgi:application

FROM python:3.11.9 AS prod

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