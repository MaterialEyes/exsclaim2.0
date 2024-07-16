FROM exsclaim/base AS base

USER root
RUN playwright install-deps && playwright install chromium
USER $UNAME

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

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=15s --start-period=20s --retries=4 CMD curl -f http://localhost:8000 || exit 1
#ENTRYPOINT ["./manage.py", "migrate", "&&", "./manage.py", "runserver", "0.0.0.0:8000"]

#COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
#COPY --from=base /usr/local/bin/playwright /usr/local/bin/playwright
#COPY --from=base /usr/local/bin/exsclaim /usr/local/bin/exsclaim

FROM base AS dev
RUN pip install -r requirements/dev.txt
