#!/bin/sh
set -e
PKG=plugin.program.sickrage
TMPBK=/storage/.kodi/addons/${PKG}.tempbak
OUTLOG=/storage/.kodi/temp/kodi.log
# Stop Kodi and ensure clean state
if [ -d /storage/.kodi/addons/${PKG} ]; then
  mv /storage/.kodi/addons/${PKG} ${TMPBK}
fi
# restart Kodi to force removal from registry
if command -v systemctl >/dev/null 2>&1; then
  systemctl restart kodi || true
fi
killall -9 kodi.bin || true
sleep 6
# capture log lines after removal
echo "--- after removal ---"
tail -n 200 ${OUTLOG} || true
# move addon back
if [ -d ${TMPBK} ]; then
  mv ${TMPBK} /storage/.kodi/addons/${PKG}
fi
# restart Kodi to force detection
if command -v systemctl >/dev/null 2>&1; then
  systemctl restart kodi || true
fi
killall -9 kodi.bin || true
sleep 6
# capture log lines after re-add
echo "--- after re-add ---"
tail -n 400 ${OUTLOG} || true
# invoke plugin and capture runtime logs
/usr/bin/kodi-send --action='RunPlugin(plugin://plugin.program.sickrage/)' || true
sleep 2
echo "--- after RunPlugin ---"
tail -n 200 ${OUTLOG} || true
