#!/bin/bash

set -euo pipefail

STACK_NAME="files"
SERVICE_FOLDERS="filebrowser"

for folder in $SERVICE_FOLDERS; do
	echo "Creating folder: $folder..."
	mkdir -p "/local-data/$folder"
done

# copy default config files (if they don't exist)
cp -n ./default_files/* /local-data/filebrowser/

echo "$STACK_NAME: migration complete."
