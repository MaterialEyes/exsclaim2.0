FROM python:3.11.9
LABEL authors="Len Washington III"

WORKDIR /usr/src/app

COPY requirements.txt ./
COPY jupyter_requirements.txt ./
RUN pip install -r requirements.txt
RUN pip install -r jupyter_requirements.txt

RUN apt update && apt install ffmpeg libsm6 libxext6 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2\
     libatspi2.0-0 libxcomposite1 libxdamage1 libbz2-dev -y
RUN playwright install-deps && playwright install chromium

RUN jupyter contrib nbextension install
RUN jupyter nbextension enable execute_time/ExecuteTime && \
	jupyter nbextension enable toc2/main

COPY app.py ./
COPY load_models.py ./

EXPOSE 8888

CMD ["python3", "app.py"]
