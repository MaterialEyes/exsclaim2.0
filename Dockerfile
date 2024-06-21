FROM python:3.11.9
LABEL authors="Len Washington III"

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install -r requirements.txt

RUN apt update && apt install ffmpeg libsm6 libxext6 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2\
     libatspi2.0-0 libxcomposite1 libxdamage1 libbz2-dev -y
RUN playwright install-deps && playwright install chromium

# region You can comment out this region if you don't need Jupyter capabilities in your Docker image/container
COPY jupyter_requirements.txt ./
RUN pip install -r jupyter_requirements.txt
RUN jupyter contrib nbextension install
RUN jupyter nbextension enable execute_time/ExecuteTime && \
	jupyter nbextension enable toc2/main
EXPOSE 8888
# endregion

COPY app.py ./
COPY load_models.py ./

#CMD ["python3", "-m", "exsclaim", "/usr/src/app/query/nature-ESEM.json", "--caption_distributor", "--journal_scraper", "--figure_separator"]
CMD ["jupyter", "notebook", "--no-browser", "--allow-root", "--port=8888", "--ip=0.0.0.0"]