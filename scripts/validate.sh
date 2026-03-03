#!/bin/bash
set -e

echo "ValidateService: Checking application health..."
cd /home/ubuntu/app

if ! sudo docker compose ps | grep -qi "running\|Up"; then
    echo "ERROR: Containers are not running properly"
    exit 1
fi

sleep 10

echo "ValidateService: Application is running successfully"
