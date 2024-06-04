FROM python:3.11.8
LABEL authors="Len Washington III"

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install -r requirements.txt
RUN pip install jupyter==1.0.0 jupyter_contrib_nbextensions==0.7.0 jupyter_nbextensions_configurator==0.6.3

RUN apt update && apt install ffmpeg libsm6 libxext6 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libatspi2.0-0 libxcomposite1 libxdamage1 -y
RUN playwright install-deps && playwright install chromium

COPY run_exsclaim.py ./
COPY load_models.py ./