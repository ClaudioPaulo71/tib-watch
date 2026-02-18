#!/bin/bash

# Update code
git pull origin main

# Define docker compose command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="docker compose"
fi

# Build and deploy with production config
# We use -f to merge the base config with the prod override
$DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.prod.yml up -d --build --remove-orphans

# Prune unused images to save space
docker image prune -f
