#!/usr/bin/env bash
set -euo pipefail

backup=""
cleanup() {
  rm -f .env
  if [[ -n "$backup" ]]; then
    mv "$backup" .env
  fi
}
trap cleanup EXIT

if [[ -e .env ]]; then
  backup=".env.gov01-backup"
  [[ ! -e "$backup" ]] || { echo "Refusing to overwrite temporary env backup" >&2; exit 1; }
  mv .env "$backup"
fi

umask 077
cp .env.example .env
nonce="$(date +%s)-$$"
cat >> .env <<EOF
SECRET_KEY=ci-generated-placeholder-$nonce
ENCRYPTION_KEY_MASTER=ci-generated-placeholder-$nonce
DB_USER=ci_user
DB_PASSWORD=ci_password
RABBITMQ_USER=ci_user
RABBITMQ_PASSWORD=ci_password
RABBITMQ_URL=amqp://ci_user:ci_password@rabbitmq:5672/
PROMETEO_API_KEY=ci-placeholder
PROMETEO_ENV=testing
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=ci_user
MINIO_SECRET_KEY=ci_password
OPENAI_API_KEY=ci-placeholder
FLOWER_BASIC_AUTH=ci_user:ci_password
EOF

docker compose --project-name conciliador-financiero-ci config --quiet
