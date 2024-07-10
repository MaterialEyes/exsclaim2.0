FROM python:3.11.9 AS base
LABEL authors="Len Washington III"

ARG EXSCLAIM_GITHUB=MaterialEyes/exsclaim
ARG EXSCLAIM_GIT_REVISION

WORKDIR /usr/src/app

# Allows docker to cache installed dependencies between builds
COPY ./requirements.txt ./
RUN pip install -r requirements.txt

RUN if [ "$EXSCLAIM_GIT_REVISION" = "" ]; then \
		pip install "git+https://github.com/$EXSCLAIM_GITHUB.git" ;\
    else \
		pip install "git+https://github.com/$EXSCLAIM_GITHUB.git@$EXSCLAIM_GIT_REVISION" ;\
    fi

FROM python:3.11.9 AS dev

ENV PYTHONUNBUFFERED=1
ENV PORT=80
ENV TZ="America/Chicago"

WORKDIR /usr/src/app

RUN apt update && apt install ffmpeg libsm6 libxext6 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libatspi2.0-0 libxcomposite1 libxdamage1 -y

COPY ./api ./api

RUN mkdir /results
RUN mkdir /logs

# region Configures the timezone
RUN apt install -yq tzdata && \
    ln -fs "/usr/share/zoneinfo/$TZ" /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata
# endregion

ENTRYPOINT ["fastapi"]
CMD ["dev", "api/main.py", "--host", "0.0.0.0", "--port", "80", "--reload"]
HEALTHCHECK --interval=15s --timeout=15s --start-period=20s --retries=4 CMD curl -f http://localhost/healthcheck || exit 1
EXPOSE 80

COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY --from=base /usr/local/bin/fastapi /usr/local/bin/fastapi
COPY --from=base /usr/local/bin/playwright /usr/local/bin/playwright
COPY --from=base /usr/local/bin/exsclaim /usr/local/bin/exsclaim

RUN playwright install-deps && playwright install chromium

FROM dev AS prod
CMD ["run", "api/main.py", "--host", "0.0.0.0", "--port", "80"]
