#!/bin/sh
set -eu

umask 077

: "${SOURCE_DATABASE_URL:?Set SOURCE_DATABASE_URL to the direct production PostgreSQL URL.}"
: "${STAGING_DATABASE_URL:?Set STAGING_DATABASE_URL to a separate, empty staging database.}"

for command_name in pg_dump pg_restore psql; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        printf 'Required PostgreSQL client tool is missing: %s\n' "$command_name" >&2
        exit 1
    fi
done

if [ "$SOURCE_DATABASE_URL" = "$STAGING_DATABASE_URL" ]; then
    printf '%s\n' 'Source and staging connection strings must be different.' >&2
    exit 1
fi

source_identity=$(psql "$SOURCE_DATABASE_URL" -X -v ON_ERROR_STOP=1 -Atc \
    "SELECT current_database() || '@' || COALESCE(inet_server_addr()::text, 'local') || ':' || COALESCE(inet_server_port()::text, 'local')")
staging_identity=$(psql "$STAGING_DATABASE_URL" -X -v ON_ERROR_STOP=1 -Atc \
    "SELECT current_database() || '@' || COALESCE(inet_server_addr()::text, 'local') || ':' || COALESCE(inet_server_port()::text, 'local')")

if [ "$source_identity" = "$staging_identity" ]; then
    printf '%s\n' 'Source and staging resolve to the same PostgreSQL database. Aborting.' >&2
    exit 1
fi

staging_table_count=$(psql "$STAGING_DATABASE_URL" -X -v ON_ERROR_STOP=1 -Atc \
    "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'")
if [ "$staging_table_count" != "0" ]; then
    printf '%s\n' 'The staging database is not empty. Use a new isolated database; this script will not overwrite existing tables.' >&2
    exit 1
fi

backup_file=${BACKUP_FILE:-"$PWD/rollnexa-restore-drill-$(date +%Y%m%d-%H%M%S).dump"}
backup_directory=$(dirname "$backup_file")
mkdir -p "$backup_directory"
if [ -e "$backup_file" ]; then
    printf '%s\n' 'The requested backup file already exists. Choose a new BACKUP_FILE path; existing backups are never overwritten.' >&2
    exit 1
fi

printf '%s\n' 'Creating a custom-format PostgreSQL backup...'
pg_dump --format=custom --serializable-deferrable --no-owner --no-acl \
    --file="$backup_file" "$SOURCE_DATABASE_URL"
pg_restore --list "$backup_file" >/dev/null

if command -v sha256sum >/dev/null 2>&1; then
    checksum=$(sha256sum "$backup_file" | awk '{print $1}')
elif command -v shasum >/dev/null 2>&1; then
    checksum=$(shasum -a 256 "$backup_file" | awk '{print $1}')
else
    printf '%s\n' 'Neither sha256sum nor shasum is available.' >&2
    exit 1
fi

printf '%s\n' 'Restoring into the isolated, empty staging database...'
pg_restore --no-owner --no-acl --exit-on-error --dbname="$STAGING_DATABASE_URL" "$backup_file"

table_counts() {
    database_url=$1
    count_queries=$(psql "$database_url" -X -v ON_ERROR_STOP=1 -Atc \
        "SELECT format('SELECT %L, count(*) FROM %I.%I;', tablename, schemaname, tablename) FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
    printf '%s\n' "$count_queries" \
        | psql "$database_url" -X -v ON_ERROR_STOP=1 -At
}

source_counts=$(table_counts "$SOURCE_DATABASE_URL")
staging_counts=$(table_counts "$STAGING_DATABASE_URL")

if [ "$source_counts" != "$staging_counts" ]; then
    printf '%s\n' 'Restored table row counts do not match the source database.' >&2
    printf '%s\n' 'Source and staging count manifests were not printed because they may reveal database structure.' >&2
    exit 1
fi

if [ -f backend/manage.py ]; then
    (
        cd backend
        DATABASE_URL="$STAGING_DATABASE_URL" python manage.py migrate --check
        DATABASE_URL="$STAGING_DATABASE_URL" python manage.py verify_biometric_restore
    )
else
    printf '%s\n' 'Django project not found at ./backend; migration and biometric-key checks must be run from the backend environment.' >&2
    exit 1
fi

printf '\n%s\n' 'PostgreSQL backup and isolated restore verification passed.'
printf 'Source database identity: %s\n' "$source_identity"
printf 'Staging database identity: %s\n' "$staging_identity"
printf 'Backup archive: %s\n' "$backup_file"
printf 'SHA-256: %s\n' "$checksum"
printf 'Table row counts: matched\n'
