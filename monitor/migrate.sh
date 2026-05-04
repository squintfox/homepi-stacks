#!/bin/bash

set -euo pipefail

# Ensure required service data folders exist.
STACK_NAME="monitor"
SERVICE_FOLDERS="beszel/data beszel/socket speedtest/config speedtest/postgres_db"

for folder in $SERVICE_FOLDERS; do
	echo "Creating folder: $folder..."
	mkdir -p "/local-data/$folder"
done

echo "$STACK_NAME: migration complete."
