#!/usr/bin/env bash

if [[ $ENV == 'dev' ]];
then
    pip install -r requirements/local.txt --no-cache-dir
elif [[ $ENV == 'prod' ]];
then
    pip install -r requirements/production.txt --no-cache-dir
else
    echo ENV should be dev or prod, was "$ENV"
fi