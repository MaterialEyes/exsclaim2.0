FROM python:3.13.11-slim AS core
LABEL authors="Len Washington III"

ARG UID=1000
ARG GID=1000
ARG UNAME=exsclaim
ARG GNAME=exsclaim

# This was added as a local PYPI server with all of the necessary packages installed on it to reduce the build time
ARG UV_DEFAULT_INDEX="https://pypi.org/simple"
ARG CHROMEDRIVER_VERSION="144.0.7559.96"

ENV OLLAMA_MODELS=/opt/ollama
ENV CUDA_LAUNCH_BLOCKING=1

ENV FAST_API_PORT=8000
ENV FAST_API_URL=http://localhost:$FAST_API_PORT

ENV DASHBOARD_PORT=3000
ENV DASHBOARD_URL=http://localhost:$DASHBOARD_PORT

ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright

SHELL ["/bin/bash", "-c"]
HEALTHCHECK --interval=20s --timeout=4s --start-period=12s --retries=8 CMD docker-healthcheck
ENTRYPOINT ["docker-entrypoint"]
CMD exsclaim initialize_db; exsclaim ui --force_ollama --blocking

WORKDIR /opt/install

COPY ./requirements.txt /opt/install/requirements.txt

RUN --mount=type=cache,target=/tmp/pip \
	groupadd -g $GID $GNAME && \
    useradd -lm -u $UID -g $GNAME -c "EXSCLAIM non-root user" --shell /bin/bash $UNAME && \
    usermod -aG $GID $UNAME && \
    mkdir -p /exsclaim/{logs,results}/ && \
    chown -R $UID:$GID /exsclaim && \
    apt update && \
    apt install -y --no-install-recommends curl ffmpeg unzip libglib2.0-0 libnss3 \
        libfontconfig1 libxcb1 libx11-6 libx11-xcb1 libxcomposite1 \
        libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 \
        libxrender1 libxss1 libxtst6 libsm6 \
        libcairo2 libcups2 libdbus-1-3 libexpat1 libuuid1 libxkbcommon0 \
        libxshmfence1 libatk1.0-0 libatk-bridge2.0-0 libatspi2.0-0 libgbm1 \
        libasound2 libgdk-pixbuf-xlib-2.0-0 libgtk-3-0 jq lsof nano \
        libdrm2 libnspr4 xvfb fonts-noto-color-emoji fonts-unifont \
        libfreetype6 xfonts-scalable fonts-liberation fonts-ipafont-gothic \
        fonts-wqy-zenhei fonts-tlwg-loma-otf fonts-freefont-ttf zstd build-essential \
	make git cmake libfreetype6-dev libharfbuzz-dev && \
	curl -fsSL https://ollama.com/install.sh | sh && \
	usermod -aG ollama $UNAME && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    pip install --upgrade pip --cache-dir=/tmp/pip --root-user-action ignore && \
    . ~/.bashrc && \
    uv pip install --system --native-tls -r /opt/install/requirements.txt && \
    playwright install --with-deps chromium && \
    curl -o chromedriver-linux64.zip https://storage.googleapis.com/chrome-for-testing-public/$CHROMEDRIVER_VERSION/linux64/chromedriver-linux64.zip && \
	unzip -p chromedriver-linux64.zip chromedriver-linux64/chromedriver > /usr/local/bin/chromedriver && \
	curl -o chrome-linux64.zip https://storage.googleapis.com/chrome-for-testing-public/$CHROMEDRIVER_VERSION/linux64/chrome-linux64.zip && \
	unzip chrome-linux64.zip -d /opt/chrome && \
	apt clean && \
    rm chrome*-linux64.zip && \
	rm -rf /var/lib/apt/lists/*

COPY ./ ./
COPY --chown=$UID:$GID docker-entrypoint docker-healthcheck /usr/local/bin/
COPY --chown=$UID:$GID query ./query

RUN --mount=type=cache,target=/tmp/pip \
    chmod +x /usr/local/bin/docker-entrypoint && \
    chmod +x /usr/local/bin/docker-healthcheck && \
    . ~/.bashrc && \
    make install && \
    apt clean && \
	rm -rf /var/lib/apt/lists/* && \
    mkdir -p /opt/exsclaim && \
    chmod 775 /opt/{exsclaim,ollama} && \
    chown $UID:$GID /opt/exsclaim

WORKDIR /opt/exsclaim

USER $UID

FROM core AS pycharm
LABEL authors="Len Washington III"

CMD ["python3"]

USER root

RUN touch ~/.xinitrc && chmod +x ~/.xinitrc && \
    pip install ipython==9.2.0 pydevd==3.3.0 pydevd-pycharm pytest==8.4.1 scipy-stubs==1.16.0.2 yappi==1.6.10 trio==0.32.0 faker==40.1.0 --root-user-action ignore --cache-dir /tmp/pip && \
    chmod -R 775 /opt && \
    chown -R exsclaim:root /opt && \
    mkdir -p /home/exsclaim/.cache/torch/hub/checkpoints/ && \
    curl --request GET \
    --url 'https://download.pytorch.org/models/fasterrcnn_resnet50_fpn_coco-258fb6c6.pth' \
    --output '/home/exsclaim/.cache/torch/hub/checkpoints/fasterrcnn_resnet50_fpn_coco-258fb6c6.pth'

USER $UID

FROM core AS with-ollama

RUN mkdir -p $OLLAMA_MODELS && \
	chown -R ollama:ollama $OLLAMA_MODELS && \
	chmod -R 775 $OLLAMA_MODELS && \
    echo -e '#!/bin/bash\n\nnohup ollama serve&\nOLLAMA_PID=$!\necho "Waiting for Ollama server to start..."\nwhile [ "$(ollama list | grep NAME)" == "" ]; do\n  sleep 1\ndone\nollama pull llama3.2\nkill $OLLAMA_PID' > pull_ollama_file && \
    chmod +x pull_ollama_file && \
    ./pull_ollama_file && \
    rm pull_ollama_file

FROM core AS jupyter

WORKDIR /opt/exsclaim

EXPOSE 8888
CMD ["jupyter", "notebook", "--allow-root", "--port=8888", "--ip=0.0.0.0"]

COPY jupyter/jupyter_requirements.txt jupyter/jupyter_extensions.txt ./
RUN pip install -r jupyter_requirements.txt --no-cache-dir && \
    pip install -r jupyter_extensions.txt --no-cache-dir && \
    pip install --upgrade notebook && \
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash && \
    ls -la /root/.nvm && \
    \. /root/.nvm/nvm.sh && \
    \. /root/.nvm/bash_completion && \
    nvm install v20.15.0 && \
    jupyter lab build
