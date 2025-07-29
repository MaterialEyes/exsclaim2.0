FROM python:3.13.2 AS build
LABEL authors="Len Washington III"

ARG UID=1000
ARG GID=1000
ARG UNAME=exsclaim
ARG GNAME=exsclaim

ARG GECKODRIVER_VERSION=0.36
ARG CHROMEDRIVER_VERSION=138.0.7204.157
# This was added as a local PYPI server with all of the necessary packages installed on it to reduce the build time
ARG UV_DEFAULT_INDEX="https://pypi.org/simple"

SHELL ["/bin/bash", "-c"]

RUN --mount=type=cache,target=/tmp/pip \
	apt update && apt install -y build-essential make git cmake libfreetype6-dev libharfbuzz-dev && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    pip install --upgrade pip --cache-dir=/tmp/pip --root-user-action ignore

WORKDIR /opt/install

COPY ./ ./

RUN --mount=type=cache,target=/tmp/pip \
    . ~/.bashrc && \
    make install && \
    wget -o- https://storage.googleapis.com/chrome-for-testing-public/$CHROMEDRIVER_VERSION/linux64/chromedriver-linux64.zip && \
	unzip chromedriver-linux64.zip && \
	mv chromedriver-linux64/chromedriver /usr/local/bin && \
	wget -o- https://storage.googleapis.com/chrome-for-testing-public/$CHROMEDRIVER_VERSION/linux64/chrome-linux64.zip && \
	unzip chrome-linux64.zip -d /opt/chrome

FROM python:3.13.2-slim AS core
LABEL authors="Len Washington III"

ARG UID=1000
ARG GID=1000
ARG UNAME=exsclaim
ARG GNAME=exsclaim

ENV OLLAMA_MODELS=/opt/ollama
ENV CUDA_LAUNCH_BLOCKING=1

ENV FAST_API_PORT=8000
ENV FAST_API_URL=http://localhost:$FAST_API_PORT

ENV DASHBOARD_PORT=3000
ENV DASHBOARD_URL=http://localhost:$DASHBOARD_PORT

SHELL ["/bin/bash", "-c"]
HEALTHCHECK --interval=20s --timeout=4s --start-period=12s --retries=8 CMD docker-healthcheck
ENTRYPOINT ["docker-entrypoint"]
CMD exsclaim initialize_db;exsclaim ui --force_ollama --blocking

RUN groupadd -g $GID $GNAME && \
    useradd -lm -u $UID -g $GNAME -c "EXSCLAIM non-root user" --shell /bin/bash $UNAME && \
    usermod -aG $GID $UNAME && \
    mkdir -p /exsclaim/{logs,results}/ && \
    chown -R $UID:$GID /exsclaim && \
    apt update && \
    apt install -y curl ffmpeg libglib2.0-0 libnss3 libgconf-2-4 \
        libfontconfig1 libxcb1 libx11-6 libx11-xcb1 libxcomposite1 \
        libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 \
        libxrender1 libxss1 libxtst6 libpango1.0-0 libsm6 \
        libcairo2 libcups2 libdbus-1-3 libexpat1 libuuid1 libxkbcommon0 \
        libxshmfence1 libatk1.0-0 libatk-bridge2.0-0 libatspi2.0-0 libgbm1 \
        libasound2 libgdk-pixbuf2.0-0 libgtk-3-0 jq lsof nano && \
	mkdir -p $OLLAMA_MODELS && \
	curl -fsSL https://ollama.com/install.sh | sh && \
	chown -R ollama:ollama $OLLAMA_MODELS && \
	chmod -R 775 $OLLAMA_MODELS && \
	usermod -aG ollama $UNAME

WORKDIR /opt/exsclaim

COPY --chown=$UID:$GID docker-entrypoint docker-healthcheck /usr/local/bin/
COPY --chown=$UID:$GID query ./query
RUN chmod +x /usr/local/bin/docker-entrypoint && \
    chmod +x /usr/local/bin/docker-healthcheck && \
    chown -R $UID:$GID /opt/exsclaim

USER $UID

RUN echo -e '#!/bin/bash\n\nnohup ollama serve&\nOLLAMA_PID=$!\necho "Waiting for Ollama server to start..."\nwhile [ "$(ollama list | grep NAME)" == "" ]; do\n  sleep 1\ndone\nollama pull llama3.2\nkill $OLLAMA_PID' > pull_ollama_file && \
    chmod +x pull_ollama_file && \
    ./pull_ollama_file && \
    rm pull_ollama_file

COPY --from=build --chown=$UID:$GID /opt/install/dist/exsclaim* /opt/install/
COPY --from=build --chown=$UID:$GID /usr/local/bin /usr/local/bin
COPY --from=build --chown=$UID:$GID /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages

FROM core AS pycharm
LABEL authors="Len Washington III"

CMD ["python3"]

USER root

RUN apt update && apt install -y build-essential libxml2 cmake curl && \
    touch ~/.xinitrc && chmod +x ~/.xinitrc && \
    pip install ipython==9.2.0 pydevd==3.3.0 pydevd-pycharm~=252.21735.39 pytest==8.4.1 scipy-stubs==1.16.0.2 --root-user-action ignore --cache-dir /tmp/pip && \
    chmod -R 775 /opt && \
    chown -R exsclaim:root /opt && \
    mkdir -p /home/exsclaim/.cache/torch/hub/checkpoints/ && \
    curl --request GET \
    --url 'https://download.pytorch.org/models/fasterrcnn_resnet50_fpn_coco-258fb6c6.pth'\
    --output '/home/exsclaim/.cache/torch/hub/checkpoints/fasterrcnn_resnet50_fpn_coco-258fb6c6.pth'

USER $UID

FROM core AS jupyter

WORKDIR /opt/exsclaim

EXPOSE 8888
CMD ["jupyter", "notebook", "--allow-root", "--port=8888", "--ip=0.0.0.0"]

COPY jupyter_requirements.txt jupyter_extensions.txt ./
RUN pip install -r jupyter_requirements.txt --no-cache-dir && \
    pip install -r jupyter_extensions.txt --no-cache-dir && \
    pip install --upgrade notebook && \
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash && \
    ls -la /root/.nvm && \
    \. /root/.nvm/nvm.sh && \
    \. /root/.nvm/bash_completion && \
    nvm install v20.15.0 && \
    jupyter lab build
