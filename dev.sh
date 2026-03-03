#!/bin/bash

export PYTHONPATH=$PYTHONPATH:$(pwd)
# python gateway/main.py
faststream run gateway.main:app --workers 1 --port 8080
