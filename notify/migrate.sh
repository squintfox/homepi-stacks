#!/bin/bash

set -euo pipefail

STACK_NAME="notify"
SERVICE_FOLDERS="ntfy/attachments mailrise"

for folder in $SERVICE_FOLDERS; do
	echo "Creating folder: $folder..."
	mkdir -p "/local-data/$folder"
done

cp -n ./default_files/mailrise/* /local-data/mailrise/

echo "$STACK_NAME: migration complete."
