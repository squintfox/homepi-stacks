#!/bin/bash

set -euo pipefail

# Ensure required service data folders exist.
STACK_NAME="content"
SERVICE_FOLDERS="share radarr sonarr whisparr lidarr bazarr seerr prowlarr"

for folder in $SERVICE_FOLDERS; do
	echo "Creating folder: $folder..."
	mkdir -p "/local-data/$folder"
done

mkdir -p /local-data/share/media/{books,tv,movies,music,whisparr}

echo "$STACK_NAME: migration complete."
