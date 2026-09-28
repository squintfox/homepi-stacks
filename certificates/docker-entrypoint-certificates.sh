#!/bin/sh

set -eu

DOMAIN_LIST_FILE="/run/config/certificates_acme_domain_list"
# letsencrypt_test for staging, letsencrypt for production
acme.sh --set-default-ca --server letsencrypt
acme.sh --register-account -m "$LE_EMAIL"s
[ -f "$DOMAIN_LIST_FILE" ]

while IFS= read -r domain || [ -n "$domain" ]; do
  # Skip empty lines and comments.
  case "$domain" in
    ""|\#*) continue ;;
  esac

  cert_dir="/certs/$domain"
  cert_file="$cert_dir/cert.crt"
  key_file="$cert_dir/cert.key"
  mkdir -p "$cert_dir"

  if [ ! -f "$cert_file" ] || [ ! -f "$key_file" ]; then
    acme.sh --issue --debug 2 --dns dns_desec -d "$domain" --dnssleep "$LE_DNS_SLEEP" --keylength ec-256
  else
    set +e
    acme.sh --renew --debug 2 -d "$domain" --ecc --dnssleep "$LE_DNS_SLEEP"
    renew_rc=$?
    set -e
    if [ "$renew_rc" -ne 0 ] && [ "$renew_rc" -ne "$LE_RENEW_SKIP_RC" ]; then
      echo "Renew failed for $domain with exit code $renew_rc" >&2
      exit "$renew_rc"
    fi
  fi

  acme.sh --install-cert --debug 2 -d "$domain" --ecc --fullchain-file "$cert_file" --key-file "$key_file"
done < "$DOMAIN_LIST_FILE"

chmod 755 /certs
find /certs -type d -exec chmod 755 {} \;

chmod -R a+r /certs
