# EXSCLAIM UI

Implements a user interface for viewing results from the [exsclaim](https://github.com/MaterialEyes/exsclaim) pipeline.


## Installation and Usage

This project is implemented using React for its front-end, Django for its API, and Postgres for its database. Each of these are built in their own Docker containers which are orchestrated using [Docker Compose](https://docs.docker.com/compose/install/). Therefore the prerequisites are Docker and Docker Compose. 

To start the project, in the project root directory: `docker-compose up`. If changes have been made to the API models, you must run: 
```bash
docker-compose run --rm api python manage.py makemigrations exsclaim
docker-compose run --rm api python manage.py migrate
```

You can then navigate to http://localhost:3000 to view the dashboard. Any changes should be reflected once saved. You can explore the API at http://localhost:8000/api/v1/

Data added to the database will persist between runs unless you remove the postgres container. 

## Seeding the database

For development and testing, it is useful to have a small amount of pre-populated data. 