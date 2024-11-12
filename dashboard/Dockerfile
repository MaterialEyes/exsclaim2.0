FROM python:3.11.9 AS py-base
LABEL authors="Len Washington III"

WORKDIR /usr/src/app

COPY requirements.txt ./dashboard/__init__.py ./dashboard/__main__.py ./

RUN pip install -r requirements.txt
RUN python3 -m cookiecutter https://github.com/plotly/dash-component-boilerplate.git --no-input \
    project_name="EXSCLAIM UI Components" \
    author_name="Material Eyes" \
    author_email=developer@materialeyes.org \
    github_org=MaterialEyes \
    description="A UI for EXSCLAIM" \
    use_async=False \
    license="MIT License" \
    publish_on_npm=false \
    install_dependencies=true


FROM node:current AS node-base

 # set the working direction
WORKDIR /usr/src/app

COPY --from=py-base /usr/src/app /usr/src/app
COPY --from=py-base /usr/local/lib /usr/local/lib
COPY --from=py-base /usr/local/bin /usr/local/bin

COPY ./package.json ./
RUN npm install

WORKDIR /usr/src/app/exsclaim_ui_components
COPY ./src/components ./src/lib/components
COPY ./src/services ./src/lib/services
COPY ./src/index.js ./src/lib/index.js
COPY ./src/webpack.config.js ./

RUN npm install react-docgen
RUN dash-generate-components ./src/lib/components exsclaim_ui_components -p package-info.json
RUN npm run build:js

FROM python:3.11.9-slim AS py-prod

ENV PORT=8080
ENV DEBUG=true

WORKDIR /usr/src/app

COPY ./dashboard ./
COPY --from=py-base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=node-base /usr/src/app/exsclaim_ui_components/setup.py /usr/src/app/exsclaim_ui_components/setup.py
COPY --from=node-base /usr/src/app/exsclaim_ui_components/package.json /usr/src/app/exsclaim_ui_components/package.json
COPY --from=node-base /usr/src/app/exsclaim_ui_components/README.md  /usr/src/app/exsclaim_ui_components/README.md
COPY --from=node-base /usr/src/app/exsclaim_ui_components/MANIFEST.in  /usr/src/app/exsclaim_ui_components/MANIFEST.in
COPY --from=node-base /usr/src/app/exsclaim_ui_components/LICENSE  /usr/src/app/exsclaim_ui_components/LICENSE
COPY --from=node-base /usr/src/app/exsclaim_ui_components/exsclaim_ui_components /usr/src/app/exsclaim_ui_components/exsclaim_ui_components

RUN pip install ./exsclaim_ui_components

ENTRYPOINT ["python3", "main.py"]
