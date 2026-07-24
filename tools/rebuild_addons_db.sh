#!/bin/sh
set -e
DB=/storage/.kodi/userdata/Database/Addons33.db
TS=$(date +%s)
BACKUP=${DB}.bak.${TS}
OUT=/storage/.kodi/temp/kodi.log
echo "Backing up $DB -> $BACKUP"
if [ -f "$DB" ]; then mv "$DB" "$BACKUP"; fi
sync
# restart Kodi
if command -v systemctl >/dev/null 2>&1; then systemctl restart kodi || true; fi
killall -9 kodi.bin || true
sleep 8
echo "=== tail after restart ==="
tail -n 300 "$OUT" || true
echo "=== DB file list ==="
ls -l "$DB" || true
if [ -f "$DB" ]; then
  echo "=== sqlite schema for addons ==="
  sqlite3 "$DB" ".schema addons" || true
  echo "=== lookup sickrage rows ==="
  sqlite3 "$DB" "SELECT addonID, name, version FROM addons WHERE addonID LIKE '%sickrage%' OR addonID='plugin.program.sickrage';" || true
fi
echo "=== jsonrpc Addons.GetAddons (program) ==="
curl -s -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","id":1,"method":"Addons.GetAddons","params":{"properties":["enabled","name","version","addonid"],"type":"program"}}' http://127.0.0.1:8080/jsonrpc || true
