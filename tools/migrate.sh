#!/bin/bash

set -euo pipefail

# Ensure required service data folders exist.
STACK_NAME="tools"
SERVICE_FOLDERS="stirling-pdf/tessdata stirling-pdf/configs stirling-pdf/logs stirling-pdf/pipeline"

for folder in $SERVICE_FOLDERS; do
	echo "Creating folder: $folder..."
	mkdir -p "/local-data/$folder"
done

echo "$STACK_NAME: migration complete."
