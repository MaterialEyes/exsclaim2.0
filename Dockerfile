FROM python:3.11.8
LABEL authors="Len Washington III"

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY exsclaim ./
COPY run_exsclaim.py ./
COPY load_models.py ./