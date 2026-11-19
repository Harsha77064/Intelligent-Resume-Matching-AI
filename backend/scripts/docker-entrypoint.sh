#!/bin/sh
# Container start-up. Hosting platforms (Render, Railway, Fly) often mount the persistent
# disk owned by root, which the unprivileged "matchpoint" user can't write to. When started
# as root, hand the data folder to that user, then drop root and run the command as it.
set -e
DATA_DIR="${DATA_DIR:-/data}"
APP_UID=10001

if [ "$(id -u)" = "0" ]; then
    mkdir -p "$DATA_DIR"
    if [ "$(stat -c %u "$DATA_DIR")" != "$APP_UID" ]; then
        chown -R "$APP_UID:$APP_UID" "$DATA_DIR" \
            || echo "warning: could not change the owner of $DATA_DIR" >&2
    fi
    exec setpriv --reuid="$APP_UID" --regid="$APP_UID" --clear-groups "$@"
fi
exec "$@"
