FROM python:3.11.9-slim AS base
LABEL authors="Len Washington III"

ARG EXSCLAIM_GITHUB_USER=MaterialEyes
ARG EXSCLAIM_GITHUB_REPO=exsclaim2.0
# Can be a branch name, tag name, or commit
ARG EXSCLAIM_GITHUB_REVISION=main

ARG UID=1000
ARG GID=1000

SHELL ["/bin/bash", "-c"]

WORKDIR /usr/src/install

ADD https://github.com/$EXSCLAIM_GITHUB_USER/$EXSCLAIM_GITHUB_REPO/archive/$EXSCLAIM_GITHUB_REVISION.tar.gz exsclaim.tar.gz
RUN --mount=type=cache,target=/tmp/pip \
    tar -xzvf exsclaim.tar.gz && \
    pip install --upgrade pip --cache-dir=/tmp/pip && \
	pip install "./$EXSCLAIM_GITHUB_REPO-$EXSCLAIM_GITHUB_REVISION" --cache-dir=/tmp/pip

WORKDIR /usr/src/app

COPY --chown=$UID:$GID entrypoint.sh ./
COPY --chown=$UID:$GID query ./query
RUN chmod +x ./entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
CMD [ "python3", "-m", "exsclaim", "query", "/usr/src/app/query/exsclaim-query.json", "--caption_distributor", "--journal_scraper", "--figure_separator" ]

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

RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash
RUN ls -la /root/.nvm && \
    \. /root/.nvm/nvm.sh && \
    \. /root/.nvm/bash_completion && \
    nvm install v20.15.0 && \
    jupyter lab build

FROM python:3.11.9-slim AS pycharm
LABEL authors="Len Washington III"

WORKDIR /usr/src/requirements

COPY requirements.txt .
COPY jupyter_requirements.txt .
COPY dashboard/requirements.txt ./dash_requirements.txt
COPY fastapi/requirements.txt ./fastapi_requirements.txt

RUN apt update && apt install -y build-essential x11vnc xauth && \
    touch ~/.xinitrc && chmod +x ~/.xinitrc && \
    pip install pip==24.1 --root-user-action ignore --cache-dir /tmp/pip

RUN --mount=type=cache,target=/tmp/pip \
    pip install -r requirements.txt -r jupyter_requirements.txt -r dash_requirements.txt -r fastapi_requirements.txt \
    --root-user-action ignore --cache-dir /tmp/pip

ADD https://download.pytorch.org/models/fasterrcnn_resnet50_fpn_coco-258fb6c6.pth /root/.cache/torch/hub/checkpoints/fasterrcnn_resnet50_fpn_coco-258fb6c6.pth
RUN playwright install-deps && playwright install chromium

ENTRYPOINT ["xvfb-run", "python3"]

FROM python:3.12.5 AS make

WORKDIR /usr/src/app

COPY ./api ./api
COPY ./dashboard ./dashboard
COPY ./db ./db
COPY ./exsclaim ./exsclaim
COPY ./fastapi ./fastapi
COPY entrypoint.sh LICENSE Makefile MANIFEST.in pyproject.toml README.md requirements.txt setup.py ./

RUN apt update && apt install -y build-essential && \
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash && \
    . ~/.bashrc && \
    nvm install v22.11.0 && \
    make build

ENTRYPOINT ["/bin/bash", "-c"]
CMD ["cp -avru /usr/src/app/dist/* /usr/src/dist/"]