#!/bin/bash

set -euo pipefail

STACK_NAME="torrent"
SERVICE_FOLDERS="qbittorrent qui"

for folder in $SERVICE_FOLDERS; do
	echo "Creating folder: $folder..."
	mkdir -p "/local-data/$folder"
done

mkdir -p /local-data/share/torrents/{books,tv,movies,music,whisparr}

echo "$STACK_NAME: migration complete."
