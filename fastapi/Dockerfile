FROM exsclaim/base AS dev

ENV PORT=80
ARG UNAME=exsclaim
ENV EXSCLAIM_DEBUG=true

WORKDIR /usr/src/app

COPY ./api ./api
COPY ./requirements.txt ./

RUN pip install -r requirements.txt
USER root

RUN mkdir -p /exsclaim/{logs,results}/
RUN chown -R $UNAME:$UNAME /exsclaim

USER $UNAME

ENTRYPOINT fastapi dev api/main.py --host 0.0.0.0 --port $PORT --reload
HEALTHCHECK --interval=30s --timeout=15s --start-period=20s --retries=4 CMD curl -f http://localhost/healthcheck || exit 1

EXPOSE $PORT

FROM dev AS prod
ENTRYPOINT fastapi run api/main.py --host 0.0.0.0 --port $PORT
ENV EXSCLAIM_DEBUG=false