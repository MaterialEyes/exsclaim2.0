FROM python:3.11.9 AS base

WORKDIR /usr/src/app

COPY requirements.txt ./exsclaim-install/
COPY ./exsclaim ./exsclaim-install/exsclaim
COPY ./setup.py ./exsclaim-install/
COPY ./README.md ./exsclaim-install/
RUN pip install ./exsclaim-install --no-cache-dir

# region You can comment out this region if you don't need Jupyter capabilities in your Docker image/container
COPY jupyter_requirements.txt ./
RUN pip install -r jupyter_requirements.txt --no-cache-dir
RUN jupyter contrib nbextension install
RUN jupyter nbextension enable execute_time/ExecuteTime && \
	jupyter nbextension enable toc2/main
EXPOSE 8888
# endregion

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
CMD ["jupyter", "notebook", "--no-browser", "--allow-root", "--port=8888", "--ip=0.0.0.0"]

COPY --from=base /usr/local/bin/exsclaim /usr/local/bin/exsclaim
COPY --from=base /usr/local/bin/playwright /usr/local/bin/playwright
COPY --from=base /usr/local/bin/jupyter /usr/local/bin/jupyter
COPY --from=base /usr/local/bin/jupyter-* /usr/local/bin/

COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

RUN playwright install-deps && playwright install chromium
