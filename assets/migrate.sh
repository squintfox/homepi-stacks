#!/bin/bash

set -euo pipefail

# Ensure required service data folders exist.
STACK_NAME="assets"
SERVICE_FOLDERS="snipe-it/storage snipe-it/logs snipe-it/backups snipe-it/mysql_db"

for folder in $SERVICE_FOLDERS; do
	echo "Creating folder: $folder..."
	mkdir -p "/local-data/$folder"
done

echo "$STACK_NAME: migration complete."
