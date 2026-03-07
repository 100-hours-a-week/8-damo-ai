#!/bin/bash
set -e

echo "AfterInstall: Setting up environment..."

# Create .env file if not exists
if [ ! -f "/home/ubuntu/app/.env" ]; then
    echo "Creating .env file..."
    if [ -f "/home/ubuntu/app_backup/.env" ]; then
        sudo cp /home/ubuntu/app_backup/.env /home/ubuntu/app/.env
    fi
fi

# login ECR
echo "AfterInstall: Logging in to ECR..."
source /home/ubuntu/app/scripts/image.env
aws ecr get-login-password --region ap-northeast-2 | \
  sudo docker login --username AWS --password-stdin \
  "${ECR_REGISTRY}"

# Set proper permissions
sudo chown -R ubuntu:ubuntu /home/ubuntu/app
sudo chmod +x /home/ubuntu/app/scripts/*.sh
