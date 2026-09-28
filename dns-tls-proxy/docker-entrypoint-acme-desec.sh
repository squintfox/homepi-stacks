#!/bin/sh

set -eu

acme.sh --set-default-ca --server letsencrypt
acme.sh --register-account -m "$LE_EMAIL" || true
if [ ! -f /certs/nginx.crt ] || [ ! -f /certs/nginx.key ]; then
  acme.sh --issue --dns dns_desec -d "$LE_DOMAIN" --dnssleep "$LE_DNS_SLEEP" --keylength ec-256
  acme.sh --install-cert -d "$LE_DOMAIN" --ecc --fullchain-file /certs/nginx.crt --key-file /certs/nginx.key --reloadcmd "docker kill -s HUP proxy"
fi
while :; do
  acme.sh --cron --home /acme.sh
  sleep 12h
done
