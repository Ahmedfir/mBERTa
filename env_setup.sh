#!/bin/bash -l
which python3
python3 -m pip install --user virtualenv
python3 -m venv env
. ./env/bin/activate
python3 -m pip install -r requirements.txt
