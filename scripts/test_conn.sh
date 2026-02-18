#!/bin/bash

CONTAINER_NAME="tib_watch_app"

echo "--- Checking /etc/resolv.conf ---"
docker exec $CONTAINER_NAME cat /etc/resolv.conf

echo -e "\n--- Testing Google (8.8.8.8) Connectivity (Ping) ---"
docker exec $CONTAINER_NAME ping -c 3 8.8.8.8 || echo "PING FAILED"

echo -e "\n--- Testing DNS Resolution (google.com) ---"
docker exec $CONTAINER_NAME curl -I https://google.com || echo "CURL GOOGLE FAILED"

echo -e "\n--- Testing Auth0 Connectivity ---"
# We grep the domain from .env to be safe
AUTH0_DOMAIN=$(grep AUTH0_DOMAIN .env | cut -d '=' -f2)
if [ -z "$AUTH0_DOMAIN" ]; then
    echo "AUTH0_DOMAIN not found in .env"
else
    echo "Trying to reach: $AUTH0_DOMAIN"
    docker exec $CONTAINER_NAME curl -I https://$AUTH0_DOMAIN || echo "CURL AUTH0 FAILED"
fi
