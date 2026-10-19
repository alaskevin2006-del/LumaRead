#!/bin/sh
# Integration tests use a new dedicated database, never the production database.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
if [ "$(docker compose exec -T db psql -U lumaread -d postgres -tAc "SELECT count(*) FROM pg_database WHERE datname='lumaread_test'")" != 0 ]; then
    echo 'lumaread_test already exists; refusing to use or remove an unknown database.' >&2
    exit 1
fi
docker compose exec -T db createdb -U lumaread lumaread_test
trap 'docker compose exec -T db dropdb -U lumaread lumaread_test' EXIT
docker compose run --rm --no-deps -T -e "LUMA_TEST_PIP_INDEX=${LUMA_TEST_PIP_INDEX:-https://pypi.org/simple}" -v "$(pwd)/backend/tests:/app/tests:ro" --entrypoint sh api -c 'pip install --user --no-cache-dir --timeout 30 --retries 2 --index-url "${LUMA_TEST_PIP_INDEX:-https://pypi.org/simple}" pytest==9.1.1 && python -c '\''import os,pytest; os.environ["LUMA_TEST_DATABASE_URL"]=os.environ["LUMA_DATABASE_URL"].rsplit("/",1)[0]+"/lumaread_test"; raise SystemExit(pytest.main(["tests","-q","-p","no:cacheprovider"]))'\'''
