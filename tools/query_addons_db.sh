#!/bin/sh
DB=/storage/.kodi/userdata/Database/Addons33.db
if [ ! -f "$DB" ]; then echo "DB missing: $DB"; exit 0; fi
echo "=== count/min/max ==="
sqlite3 "$DB" "SELECT count(*), min(addonID), max(addonID) FROM addons;"
echo "=== plugin.* rows ==="
sqlite3 "$DB" "SELECT addonID,name,version FROM addons WHERE addonID LIKE 'plugin.%' LIMIT 200;"
echo "=== sickrage lookup ==="
sqlite3 "$DB" "SELECT addonID,name,version FROM addons WHERE addonID='plugin.program.sickrage' OR addonID LIKE '%sickrage%';"
