#!/bin/bash

set -euo pipefail

STACK_NAME="usenet"

echo "Creating folder: sabnzbd..."
mkdir -p /local-data/sabnzbd
mkdir -p /local-data/share/usenet/incomplete
mkdir -p /local-data/share/usenet/complete/{books,tv,movies,music,whisparr}

echo "$STACK_NAME: migration complete."
