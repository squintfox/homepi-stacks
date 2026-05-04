#!/bin/bash

set -euo pipefail

# Ensure required service data folders exist.
STACK_NAME="deploy"
SERVICE_FOLDERS="semaphore/postgres_db"

for folder in $SERVICE_FOLDERS; do
	echo "Creating folder: $folder..."
	mkdir -p "/local-data/$folder"
done

echo "$STACK_NAME: migration complete."
