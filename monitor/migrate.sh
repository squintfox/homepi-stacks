#!/bin/bash

set -euo pipefail

# Ensure required service data folders exist.
STACK_NAME="monitor"
SERVICE_FOLDERS="beszel/data beszel/socket speedtest/config speedtest/postgres_db loggifly/config"

for folder in $SERVICE_FOLDERS; do
	echo "Creating folder: $folder..."
	mkdir -p "/local-data/$folder"
done

# copy default config files (if they don't exist)
cp -n ./default_files/loggifly/* /local-data/loggifly/config/

echo "$STACK_NAME: migration complete."
