#!/bin/sh

set -eu

cat >/etc/nginx/nginx.conf <<EOF
user  nginx;
worker_processes  auto;
worker_rlimit_nofile  15000;
pid  /var/run/nginx.pid;
include /usr/share/nginx/modules/*.conf;

events {
    worker_connections  2048;
    multi_accept on;
    use epoll;
}

stream {
    upstream dns {
        zone dns 64k;
        server ${DNS_UPSTREAM_HOST}:${DNS_UPSTREAM_PORT};
    }

    server {
        listen ${DNS_TLS_PORT} ssl;
        ssl_certificate ${DNS_TLS_CERT};
        ssl_certificate_key ${DNS_TLS_KEY};
        proxy_pass dns;

        ssl_protocols TLSv1.3;
        ssl_prefer_server_ciphers on;
        ssl_ciphers ECDH+AESGCM:ECDH+CHACHA20:ECDH+AES256:ECDH+AES128:!aNULL:!SHA1:!AESCCM;
        ssl_conf_command Options PrioritizeChaCha;
        ssl_conf_command Ciphersuites TLS_AES_256_GCM_SHA384:TLS_AES_128_GCM_SHA256:TLS_CHACHA20_POLY1305_SHA256;
        ssl_ecdh_curve secp384r1;
        ssl_session_timeout 10m;
        ssl_session_cache shared:SSL:10m;
        ssl_session_tickets off;
    }
}
EOF

exec nginx -g "daemon off;"
