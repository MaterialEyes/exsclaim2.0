FROM python:3.11.9 AS base

WORKDIR /usr/src/app

SHELL ["/bin/bash", "-c"]

COPY requirements.txt ./exsclaim-install/
COPY ./exsclaim ./exsclaim-install/exsclaim
COPY ./setup.py ./exsclaim-install/
COPY ./README.md ./exsclaim-install/
RUN pip install ./exsclaim-install --no-cache-dir

FROM python:3.11.9 AS prod
ENV TZ="America/Chicago"

WORKDIR /usr/src/app

COPY ./entrypoint.sh ./
RUN chmod +x ./entrypoint.sh
COPY ./load_models.py ./

RUN apt update && apt install ffmpeg libsm6 libxext6 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2\
     libatspi2.0-0 libxcomposite1 libxdamage1 libbz2-dev -y

# region Configures the timezone
RUN apt install -yq tzdata && \
    ln -fs "/usr/share/zoneinfo/$TZ" /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata
# endregion

ENTRYPOINT ["./entrypoint.sh"]
CMD [ "exsclaim", "/usr/src/app/query/nature-ESEM.json", "--caption_distributor", "--journal_scraper", "--figure_separator" ]

COPY --from=base /usr/local/bin/exsclaim /usr/local/bin/exsclaim
COPY --from=base /usr/local/bin/playwright /usr/local/bin/playwright

COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

RUN playwright install-deps && playwright install chromium

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

RUN playwright install-deps && playwright install chromium

RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash
RUN ls -la /root/.nvm && \
    \. /root/.nvm/nvm.sh && \
    \. /root/.nvm/bash_completion && \
    nvm install v20.15.0 && \
    jupyter lab build
