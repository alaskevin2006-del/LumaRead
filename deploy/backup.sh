#!/bin/sh
# Run on the deployment host. Stops only LumaRead writers for a consistent backup.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
umask 077
stamp=$(date -u +%Y%m%dT%H%M%SZ)
target="$(pwd)/backups/$stamp"
mkdir -p "$target"
docker compose stop api worker cleanup
trap 'docker compose up -d api worker cleanup' EXIT
docker compose exec -T db pg_dump -U lumaread -d lumaread -Fc > "$target/database.dump"
docker compose run --rm --no-deps -T --entrypoint tar api czf - -C /data/media . > "$target/media.tar.gz"
cp .env "$target/deployment.env"
docker compose images > "$target/images.txt"
printf '%s\n' "$target"
