FROM exsclaim/base AS prod
ARG UID=1000
ARG GID=1000

WORKDIR /usr/src/app

COPY --chown=$UID:$GID entrypoint.sh load_models.py ./
RUN chmod +x ./entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
CMD [ "python3", "-m", "exsclaim", "query", "/usr/src/app/query/nature-ESEM.json", "--caption_distributor", "--journal_scraper", "--figure_separator" ]

COPY --chown=$UID:$GID query ./query

FROM python:3.11.9 AS jupyter-base

WORKDIR /usr/src/app

COPY jupyter_requirements.txt jupyter_extensions.txt ./
RUN pip install -r jupyter_requirements.txt --no-cache-dir
RUN pip install -r jupyter_extensions.txt --no-cache-dir
RUN pip install --upgrade notebook

EXPOSE 8888

FROM prod AS jupyter

WORKDIR /usr/src/app

CMD ["jupyter", "notebook", "--allow-root", "--port=8888", "--ip=0.0.0.0"]

COPY --from=jupyter-base /usr/local/bin/jupyter /usr/local/bin/jupyter
COPY --from=jupyter-base /usr/local/bin/jupyter-* /usr/local/bin/
COPY --from=jupyter-base /usr/local/share/jupyter /usr/local/share/jupyter
COPY --from=jupyter-base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash
RUN ls -la /root/.nvm && \
    \. /root/.nvm/nvm.sh && \
    \. /root/.nvm/bash_completion && \
    nvm install v20.15.0 && \
    jupyter lab build
