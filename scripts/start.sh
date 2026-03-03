#!/bin/bash
set -e

echo "ApplicationStart: Starting containers..."
cd /home/ubuntu/app

if [ -f scripts/image.env ]; then
  export $(grep -v '^#' scripts/image.env | xargs)
fi

sudo docker compose --env-file .env pull

sudo docker compose --env-file .env up -d

echo "Waiting for services to be healthy..."
sleep 30

sudo docker compose ps
