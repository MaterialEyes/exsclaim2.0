#!/usr/bin/env bash

if [[ $ENV == 'dev' ]];
then
    pip install -r requirements/local.txt
elif [[ $ENV == 'prod' ]];
then
    pip install -r requirements/production.txt
else
    echo ENV should be dev or prod, was $ENV
fi