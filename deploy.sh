#!/bin/bash

# Update code
git pull origin main

# Build and deploy with production config
# We use -f to merge the base config with the prod override
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build --remove-orphans

# Prune unused images to save space
docker image prune -f
