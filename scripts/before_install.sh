#!/bin/bash
set -e

echo "BeforeInstall: Stopping existing containers..."
if [ -d "/home/ubuntu/app" ]; then
    cd /home/ubuntu/app
    sudo docker compose down || true
    sudo docker system prune -f || true

    echo "BeforeInstall: Creating backup of current app..."
    if [ -d "/home/ubuntu/app_backup" ]; then
        sudo rm -rf /home/ubuntu/app_backup
    fi
    sudo cp -r /home/ubuntu/app /home/ubuntu/app_backup
else
    echo "BeforeInstall: No existing app found, creating directory..."
fi

mkdir -p /home/ubuntu/app

echo "BeforeInstall: Creating .env from AWS Parameter Store..."
aws ssm get-parameter --name '/damo/ai/PROD_ENV' --with-decryption --query 'Parameter.Value' --output text > /home/ubuntu/app/.env
chmod 600 /home/ubuntu/app/.env
echo "BeforeInstall: .env file created"
