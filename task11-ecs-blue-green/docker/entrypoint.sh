#!/bin/bash
set -e

umask 0002

ASSETS_PATH="/home/frappe/frappe-bench/sites/assets"
BAKED_PATH="/home/frappe/frappe-bench/assets"

echo "Checking Frappe assets symlink..."

mkdir -p "$(dirname "$ASSETS_PATH")"

if [ -L "$ASSETS_PATH" ]; then
    if [ "$(readlink "$ASSETS_PATH")" != "$BAKED_PATH" ]; then
        echo "ERROR: Existing assets symlink has an unexpected target."
        exit 1
    fi
elif [ -e "$ASSETS_PATH" ]; then
    if [ -d "$ASSETS_PATH" ] && [ -z "$(find "$ASSETS_PATH" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
        rmdir "$ASSETS_PATH"
    else
        echo "ERROR: Assets path exists and contains data. Refusing to delete it."
        exit 1
    fi
fi

if [ ! -L "$ASSETS_PATH" ]; then
    if ! ln -s "$BAKED_PATH" "$ASSETS_PATH" 2>/dev/null; then
        if [ ! -L "$ASSETS_PATH" ] || [ "$(readlink "$ASSETS_PATH")" != "$BAKED_PATH" ]; then
            echo "ERROR: Could not safely create assets symlink."
            exit 1
        fi
    fi
fi

echo "Assets symlink is ready."

exec "$@"
