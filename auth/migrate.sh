#!/bin/bash

set -euo pipefail

STACK_NAME="auth"
SERVICE_FOLDERS="keycloak"

for folder in $SERVICE_FOLDERS; do
  echo "Creating folder: $folder..."
  mkdir -p "/local-data/$folder"
  # Set permissions to allow read/write/execute for all users because keycloak needs access 
  # to these folders 
  chmod 777 "/local-data/$folder"
done

echo "$STACK_NAME: migration complete."
