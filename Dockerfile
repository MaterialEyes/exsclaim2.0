FROM python:3.11.8
LABEL authors="Len Washington III"

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install -r requirements.txt
RUN pip install jupyter==1.0.0 jupyter_contrib_nbextensions==0.7.0

RUN apt update && apt install ffmpeg libsm6 libxext6 -y

COPY run_exsclaim.py ./
COPY load_models.py ./