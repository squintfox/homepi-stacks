#!/bin/bash

set -euo pipefail

# Ensure required service data folders exist.
STACK_NAME="homepage"
SERVICE_FOLDERS="homepage"

for folder in $SERVICE_FOLDERS; do
	echo "Creating folder: $folder..."
	mkdir -p "/local-data/$folder"
done

# copy default config files (if they don't exist)
cp -n ./default_files/* /local-data/homepage/

echo "$STACK_NAME: migration complete."
