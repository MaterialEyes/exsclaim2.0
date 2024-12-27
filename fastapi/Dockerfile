FROM exsclaim/base AS dev

ENV PORT=80
ARG UNAME=exsclaim
ENV EXSCLAIM_DEBUG=true

WORKDIR /usr/src/app
SHELL ["/bin/bash", "-c"]

COPY ./api ./api
COPY ./requirements.txt ./

RUN useradd -ms /bin/bash $UNAME
RUN --mount=type=cache,target=/tmp/pip \
    pip install -r requirements.txt --cache-dir /tmp/pip && \
    apt update && apt install -y curl

USER root

RUN mkdir -p /exsclaim/{logs,results}/
RUN chown -R $UNAME:root /exsclaim

#USER $UNAME

ENTRYPOINT fastapi dev api/main.py --host 0.0.0.0 --port $PORT --reload
HEALTHCHECK --interval=10s --timeout=15s --start-period=5s --retries=6 CMD curl -f http://localhost:$PORT/healthcheck || exit 1

EXPOSE $PORT

FROM dev AS prod
ENTRYPOINT fastapi run api/main.py --host 0.0.0.0 --port $PORT
ENV EXSCLAIM_DEBUG=false