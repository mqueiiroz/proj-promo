#!/bin/sh
set -eu
umask 077

: "${DB_HOST:?Configure DB_HOST no Cron Job.}"
: "${DB_NAME:?Configure DB_NAME no Cron Job.}"
: "${DB_USER:?Configure DB_USER no Cron Job.}"
: "${DB_PASSWORD:?Configure DB_PASSWORD no Cron Job.}"
: "${AWS_REGION:?Configure AWS_REGION no Cron Job.}"
: "${S3_BUCKET_NAME:?Configure S3_BUCKET_NAME no Cron Job.}"
: "${AWS_ACCESS_KEY_ID:?Configure AWS_ACCESS_KEY_ID no Cron Job.}"
: "${AWS_SECRET_ACCESS_KEY:?Configure AWS_SECRET_ACCESS_KEY no Cron Job.}"

export PGHOST="$DB_HOST" PGPORT="${DB_PORT:-5432}" PGDATABASE="$DB_NAME" PGUSER="$DB_USER"
export PGPASSWORD="$DB_PASSWORD" PGSSLMODE=require PGCONNECT_TIMEOUT=15

pasta=$(mktemp -d)
arquivo="$pasta/backup.dump"
trap 'rm -f -- "$arquivo"; rmdir -- "$pasta"' EXIT
trap 'exit 1' HUP INT TERM

chave="postgresql/proj-promo/$(date -u +%Y%m%dT%H%M%SZ).dump"
pg_dump --no-password --format=custom --schema=public --no-owner --no-privileges --file="$arquivo"
unset PGPASSWORD DB_PASSWORD
pg_restore --list "$arquivo" > /dev/null

aws s3api put-object --region "$AWS_REGION" --bucket "$S3_BUCKET_NAME" --key "$chave" \
    --body "$arquivo" --server-side-encryption AES256 --checksum-algorithm SHA256 > /dev/null
printf 'Backup enviado ao S3: %s\n' "$chave"
