#!/bin/bash

set -euo pipefail

# Ensure required service data folders exist.
STACK_NAME="recipes"
SERVICE_FOLDERS="mealie/data mealie/postgres_db"

for folder in $SERVICE_FOLDERS; do
	echo "Creating folder: $folder..."
	mkdir -p "/local-data/$folder"
done

echo "$STACK_NAME: migration complete."
