#!/bin/bash

set -euo pipefail

# Ensure required service data folders exist.
STACK_NAME="listen"
SERVICE_FOLDERS="audiobookshelf/metadata audiobookshelf/config audiobookshelf/audiobooks audiobookshelf/podcasts"

for folder in $SERVICE_FOLDERS; do
	echo "Creating folder: $folder..."
	mkdir -p "/local-data/$folder"
done

echo "$STACK_NAME: migration complete."
