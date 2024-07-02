#!/bin/bash

$LOCAL_VERSION=$(exsclaim -v | sed 's/EXSCLAIM! v//g')
echo "$LOCAL_VERSION"

GIT_VERSION=$(curl -s https://raw.githubusercontent.com/MaterialEyes/exsclaim2.0/exsclaim2_for_spin/exsclaim/version.py | sed 's/version = //g' | sed 's/"//g')
if [ "$GIT_VERSION" != "$LOCAL_VERSION" ]; then
	# The local version not is up-to-date and needs to be upgraded.
	pip install --upgrade git+"https://github.com/MaterialEyes/exsclaim2.0@$GIT_VERSION"
fi

python3 -m "$@"