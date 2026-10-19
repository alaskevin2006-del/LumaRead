#!/bin/sh
# Copy a certificate from an administrator-selected source. Never edit its source.
set -eu
cd /opt/lumaread
. ./deploy/certificate-source.env
test -r "$LUMA_CERT_SOURCE/fullchain.pem"
test -r "$LUMA_CERT_SOURCE/privkey.pem"
openssl x509 -in "$LUMA_CERT_SOURCE/fullchain.pem" -checkend 3600 -noout
mkdir -p certs
chmod 700 certs
if ! cmp -s "$LUMA_CERT_SOURCE/fullchain.pem" certs/fullchain.pem || ! cmp -s "$LUMA_CERT_SOURCE/privkey.pem" certs/privkey.pem; then
    install -m 600 "$LUMA_CERT_SOURCE/privkey.pem" certs/privkey.pem.new
    install -m 644 "$LUMA_CERT_SOURCE/fullchain.pem" certs/fullchain.pem.new
    mv certs/privkey.pem.new certs/privkey.pem
    mv certs/fullchain.pem.new certs/fullchain.pem
    if docker compose ps --status running --services | grep -qx gateway; then
        docker compose exec -T gateway caddy reload --config /etc/caddy/Caddyfile --force
    fi
fi
