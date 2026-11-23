#!/bin/sh
set -eu

umask 077

: "${SOURCE_DATABASE_URL:?Set SOURCE_DATABASE_URL to the direct production PostgreSQL URL.}"
: "${STAGING_DATABASE_URL:?Set STAGING_DATABASE_URL to a separate, empty staging database.}"

# Require TLS for both hosted database connections. An explicit sslmode value
# in a connection URL still takes precedence and must be reviewed separately.
PGSSLMODE=${PGSSLMODE:-require}
export PGSSLMODE

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

# Use database OID and the connected server address/port as well as the name.
# This catches the same database reached through different connection URLs.
database_identity() {
    psql "$1" -X -v ON_ERROR_STOP=1 -Atc \
        "SELECT current_database() || '|' || (SELECT oid::text FROM pg_database WHERE datname = current_database()) || '|' || COALESCE(inet_server_addr()::text, 'local') || '|' || COALESCE(inet_server_port()::text, 'local')"
}

source_identity=$(database_identity "$SOURCE_DATABASE_URL")
staging_identity=$(database_identity "$STAGING_DATABASE_URL")

assert_tls_connection() {
    ssl_enabled=$(psql "$1" -X -v ON_ERROR_STOP=1 -Atc \
        "SELECT ssl::text FROM pg_stat_ssl WHERE pid = pg_backend_pid()")
    if [ "$ssl_enabled" != "true" ]; then
        printf '%s\n' 'A database connection is not using TLS. Refusing to continue.' >&2
        exit 1
    fi
}

assert_tls_connection "$SOURCE_DATABASE_URL"
assert_tls_connection "$STAGING_DATABASE_URL"

if [ "$source_identity" = "$staging_identity" ]; then
    printf '%s\n' 'Source and staging resolve to the same PostgreSQL database. Aborting.' >&2
    exit 1
fi

staging_database_name=$(psql "$STAGING_DATABASE_URL" -X -v ON_ERROR_STOP=1 -Atc \
    "SELECT current_database()")
case "$staging_database_name" in
    postgres|template0|template1)
        printf '%s\n' 'Refusing to restore into a PostgreSQL system database.' >&2
        exit 1
        ;;
esac

# A restore target must be genuinely fresh, not merely free of public tables.
# Check relations and non-default schemas so views, sequences and other
# pre-existing objects cannot be overwritten or collide with the restore.
staging_relation_count=$(psql "$STAGING_DATABASE_URL" -X -v ON_ERROR_STOP=1 -Atc \
    "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname NOT IN ('pg_catalog', 'information_schema') AND n.nspname NOT LIKE 'pg_toast%' AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')")
staging_schema_count=$(psql "$STAGING_DATABASE_URL" -X -v ON_ERROR_STOP=1 -Atc \
    "SELECT count(*) FROM pg_namespace WHERE nspname NOT IN ('pg_catalog', 'information_schema', 'public') AND nspname NOT LIKE 'pg_toast%'")
staging_function_count=$(psql "$STAGING_DATABASE_URL" -X -v ON_ERROR_STOP=1 -Atc \
    "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname NOT IN ('pg_catalog', 'information_schema') AND n.nspname NOT LIKE 'pg_toast%'")
staging_type_count=$(psql "$STAGING_DATABASE_URL" -X -v ON_ERROR_STOP=1 -Atc \
    "SELECT count(*) FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace WHERE n.nspname NOT IN ('pg_catalog', 'information_schema') AND n.nspname NOT LIKE 'pg_toast%'")

if [ "$staging_relation_count" != "0" ] || [ "$staging_schema_count" != "0" ] \
    || [ "$staging_function_count" != "0" ] || [ "$staging_type_count" != "0" ]; then
    printf '%s\n' 'The staging database is not empty. Use a newly created isolated database; this script will not overwrite existing objects.' >&2
    exit 1
fi

# pg_dump must be at least as new as the source server major version.
source_version_num=$(psql "$SOURCE_DATABASE_URL" -X -v ON_ERROR_STOP=1 -Atc \
    "SHOW server_version_num")
source_major=$((source_version_num / 10000))
client_version=$(pg_dump --version | awk '{print $3}')
client_major=${client_version%%.*}
if [ "$client_major" -lt "$source_major" ]; then
    printf 'PostgreSQL client major version %s is older than source server major version %s. Install a matching or newer client.\n' \
        "$client_major" "$source_major" >&2
    exit 1
fi

backup_file=${BACKUP_FILE:-"$PWD/rollnexa-restore-drill-$(date +%Y%m%d-%H%M%S).dump"}
backup_directory=$(dirname "$backup_file")
mkdir -p "$backup_directory"
if [ -e "$backup_file" ]; then
    printf '%s\n' 'The requested backup file already exists. Choose a new BACKUP_FILE path; existing backups are never overwritten.' >&2
    exit 1
fi

printf '%s\n' 'Creating a custom-format PostgreSQL backup over TLS...'
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
pg_restore --no-owner --no-acl --exit-on-error --single-transaction \
    --dbname="$STAGING_DATABASE_URL" "$backup_file"

table_counts() {
    database_url=$1
    count_queries=$(psql "$database_url" -X -v ON_ERROR_STOP=1 -Atc \
        "SELECT format('SELECT %L, count(*) FROM %I.%I;', schemaname || '.' || tablename, schemaname, tablename) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema') AND schemaname NOT LIKE 'pg_toast%' ORDER BY schemaname, tablename")
    printf '%s\n' "$count_queries" | psql "$database_url" -X -v ON_ERROR_STOP=1 -At
}

source_counts=$(table_counts "$SOURCE_DATABASE_URL")
staging_counts=$(table_counts "$STAGING_DATABASE_URL")

if [ "$source_counts" != "$staging_counts" ]; then
    printf '%s\n' 'Restored table row counts do not match the source database.' >&2
    printf '%s\n' 'Count manifests were not printed because they may reveal database structure.' >&2
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
printf '%s\n' 'Source and staging database identities are distinct.'
printf 'Backup archive: %s\n' "$backup_file"
printf 'SHA-256: %s\n' "$checksum"
printf '%s\n' 'Table row counts: matched'
