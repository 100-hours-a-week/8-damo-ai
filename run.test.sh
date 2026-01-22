#!/bin/bash

export PYTHONPATH=$(pwd)

poetry run pytest tests -v