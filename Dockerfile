FROM python:3.11.9 AS base
LABEL authors="Len Washington III"
ENV TZ="America/Chicago"

WORKDIR /usr/src/app

COPY requirements.txt ./exsclaim-install/
COPY ./exsclaim ./exsclaim-install/exsclaim
COPY ./setup.py ./exsclaim-install/
COPY ./README.md ./exsclaim-install/
RUN pip install ./exsclaim-install

RUN apt update && apt install ffmpeg libsm6 libxext6 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2\
     libatspi2.0-0 libxcomposite1 libxdamage1 libbz2-dev -y
RUN playwright install-deps && playwright install chromium

# region Configures the timezone
RUN apt install -yq tzdata && \
    ln -fs "/usr/share/zoneinfo/$TZ" /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata
# endregion

# region You can comment out this region if you don't need Jupyter capabilities in your Docker image/container
COPY jupyter_requirements.txt ./
RUN pip install -r jupyter_requirements.txt
RUN jupyter contrib nbextension install
RUN jupyter nbextension enable execute_time/ExecuteTime && \
	jupyter nbextension enable toc2/main
EXPOSE 8888
# endregion

COPY load_models.py ./
COPY entrypoint.sh ./

FROM base AS prod

WORKDIR /usr/src/app

COPY --from=base /usr/src/app/entrypoint.sh .
COPY --from=base /usr/src/app/load_models.py .
# FIXME: This folder is not being removed between the stages
RUN rm -rf /usr/src/app/exsclaim-install

RUN chmod +x ./entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
CMD ["exsclaim", "/usr/src/app/query/nature-ESEM.json", "--caption_distributor", "--journal_scraper", "--figure_separator"]
# CMD ["jupyter", "notebook", "--no-browser", "--allow-root", "--port=8888", "--ip=0.0.0.0"]
