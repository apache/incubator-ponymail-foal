#!/usr/bin/env bash

# Try to change to correct directory:
cd $(dirname "$0") || exit 1

FILE=main.py

test -r $FILE || { echo "Must be run from the directory containing $FILE!"; exit 1; }

# plugin revision (for updating HTML)
PLUGINS_REV=$(git log -1 --pretty=%h -- plugins)

echo $PLUGINS_REV

perl -0pe "s/^PONYMAIL_PLUGIN_VERSION = '[^']*'/PONYMAIL_PLUGIN_VERSION = '$PLUGINS_REV'/smg" \
  ${FILE} > ${FILE}.tmp && mv ${FILE}.tmp ${FILE}
