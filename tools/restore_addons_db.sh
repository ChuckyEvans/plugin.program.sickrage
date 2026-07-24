#!/bin/sh
set -e
DB=/storage/.kodi/userdata/Database/Addons33.db
BAK=/storage/.kodi/userdata/Database/Addons33.db.bak.1784040183
if [ ! -f "$BAK" ]; then
  echo "ERROR: backup not found: $BAK"
  exit 1
fi
NOW=$(date +%s)
if [ -f "$DB" ]; then
  cp -a "$DB" "${DB}.before_restore.${NOW}"
fi
cp -a "$BAK" "$DB"
sync
chown root:root "$DB" || true
chmod 644 "$DB" || true
echo "Restored $BAK -> $DB (backup saved as ${DB}.before_restore.${NOW})"
if command -v systemctl >/dev/null 2>&1; then
  systemctl restart kodi || true
fi
killall -9 kodi.bin || true
sleep 6
echo "--- kodi.log tail ---"
grep -n -E "CAddonMgr::FindAddons|plugin.program.sickrage|Unable to find plugin" /storage/.kodi/temp/kodi.log || true
tail -n 200 /storage/.kodi/temp/kodi.log || true
