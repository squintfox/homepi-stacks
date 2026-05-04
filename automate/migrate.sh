#!/bin/bash

set -euo pipefail

# Ensure required service data folders exist.
STACK_NAME="automate"
SERVICE_FOLDERS="homeassistant/config homeassistant/postgres_db homeassistant/mosquitto/config homeassistant/mosquitto/data homeassistant/mosquitto/log"

for folder in $SERVICE_FOLDERS; do
	echo "Creating folder: $folder..."
	mkdir -p "/local-data/$folder"
done

echo "$STACK_NAME: migration complete."
