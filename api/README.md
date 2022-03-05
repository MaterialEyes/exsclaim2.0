# exsclaim-ui

[![Build Status](https://travis-ci.org/materialeyes/exsclaim-ui.svg?branch=master)](https://travis-ci.org/materialeyes/exsclaim-ui)
[![Built with](https://img.shields.io/badge/Built_with-Cookiecutter_Django_Rest-F7B633.svg)](https://github.com/11th-Hour-Data-Science/cookiecutter-django-rest)

API for handling EXSCLAIM results. Check out the project's [documentation](http://materialeyes.github.io/exsclaim-ui/).

# Prerequisites

- [Docker](https://docs.docker.com/docker-for-mac/install/)  

# Local Development

Start the dev server for local development:
```bash
docker-compose up
```
When you first start or make changes to a model, you must run:
```bash
docker-compose run --rm web python manage.py makemigrations exsclaim
docker-compose run --rm web python manage.py migrate
```


Run a command inside the docker container:

```bash
docker-compose run --rm web [command]
```
