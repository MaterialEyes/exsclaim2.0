FROM postgres:latest
LABEL authors="Len Washington III"

ENV POSTGRES_USER=exsclaim
ENV POSTGRES_PASSWORD=exsclaimtest!9700
ENV POSTGRES_DB=exsclaim
ENV POSTGRES_PORT=5432
ENV TZ=America/Chicago
ENV PGTZ=${TZ}

COPY setup/*.sql /docker-entrypoint-initdb.d

HEALTHCHECK --interval=5s --timeout=60s --start-period=10s --retries=12 CMD /usr/bin/pg_isready -d $POSTGRES_DB -U $POSTGRES_USER -p $POSTGRES_PORT

EXPOSE "$POSTGRES_PORT"