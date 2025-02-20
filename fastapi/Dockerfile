FROM exsclaim/base AS dev

ENV EXSCLAIM_DEBUG=true
ENV PYTHONBUFFERED=1

ARG UID=1000
ARG GID=1000
ARG UNAME=exsclaim
ARG GNAME=exsclaim

WORKDIR /usr/src/app
SHELL ["/bin/bash", "-c"]

COPY ./api ./api
COPY ./requirements.txt ./

USER root

RUN --mount=type=cache,target=/tmp/pip \
	pip install -r requirements.txt --cache-dir /tmp/pip && \
	apt update && apt install -y curl && \
    chown -R $UID:$GID ./api

USER $UID

ENTRYPOINT ["fastapi", "dev", "api/main.py", "--host", "0.0.0.0", "--port", "80", "--reload"]
HEALTHCHECK --interval=10s --timeout=15s --start-period=5s --retries=6 CMD curl -f http://localhost:/healthcheck || exit 1

EXPOSE $PORT

FROM dev AS prod
ENTRYPOINT fastapi run api/main.py --host 0.0.0.0 --port $PORT
ENV EXSCLAIM_DEBUG=false