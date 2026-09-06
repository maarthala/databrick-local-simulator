#!/bin/bash
set -e

echo "===== Docker Cleanup Script ====="
echo

# 1️⃣ Remove containers starting with stack-
echo "Removing containers with names starting with 'stack-'..."
STACK_CONTAINERS=$(docker ps -a --filter "name=^stack-" -q)

if [ -n "$STACK_CONTAINERS" ]; then
    echo "Found containers:"
    docker ps -a --filter "name=^stack-"
    docker rm -f $STACK_CONTAINERS
    echo "Containers removed successfully."
else
    echo "No containers found with name starting with 'stack-'."
fi
echo

# 2️⃣ Remove images starting with stack-
echo "Removing images with repository starting with 'stack-'..."
STACK_IMAGES=$(docker images --format "{{.Repository}}:{{.Tag}} {{.ID}}" | awk '$1 ~ /^stack-/ {print $2}')

if [ -n "$STACK_IMAGES" ]; then
    echo "Found images:"
    docker images --format "{{.Repository}}:{{.Tag}} {{.ID}}" | awk '$1 ~ /^stack-/'
    docker rmi -f $STACK_IMAGES
    echo "Images removed successfully."
else
    echo "No images found with repository starting with 'stack-'."
fi
echo

# 3️⃣ Remove dangling images
echo "Removing dangling images (<none>)..."
DANGLING_IMAGES=$(docker images -f dangling=true -q)

if [ -n "$DANGLING_IMAGES" ]; then
    echo "Found dangling images:"
    docker images -f dangling=true
    docker rmi -f $DANGLING_IMAGES
    echo "Dangling images removed successfully."
else
    echo "No dangling images found."
fi
echo

echo "===== Docker Cleanup Completed ====="
# 4️⃣ Remove volumes starting with stack-
echo "Removing volumes with names starting with 'stack-'..."
STACK_VOLUMES=$(docker volume ls --format "{{.Name}}")

if [ -n "$STACK_VOLUMES" ]; then
    echo "Found volumes:"
    echo "$STACK_VOLUMES"
    docker volume rm $STACK_VOLUMES
    echo "Volumes removed successfully."
else
    echo "No volumes found with name starting with 'stack-'."
fi
echo