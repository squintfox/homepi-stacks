#!/bin/bash

set -euo pipefail

STACK_NAME="auth"
SERVICE_FOLDERS="authelia"

for folder in $SERVICE_FOLDERS; do
  echo "Creating folder: $folder..."
  mkdir -p "/local-data/$folder"
done

echo "$STACK_NAME: migration complete."
