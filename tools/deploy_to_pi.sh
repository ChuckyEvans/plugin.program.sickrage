#!/bin/sh
set -e
PKG=plugin.program.sickrage
if [ -d /storage/.kodi/addons/${PKG} ]; then mv /storage/.kodi/addons/${PKG} /storage/.kodi/addons/${PKG}.bak || true; fi
rm -rf /storage/.kodi/addons/${PKG}
mkdir -p /storage/.kodi/addons/${PKG}
cd /storage/.kodi/addons/${PKG}
unzip -o /tmp/plugin.program.sickrage-2.2.1.zip
chown -R root:root /storage/.kodi/addons/${PKG}
chmod -R a+rX /storage/.kodi/addons/${PKG}
sync
if command -v systemctl >/dev/null 2>&1; then systemctl restart kodi || true; fi
killall -9 kodi.bin || true
sleep 6
/usr/bin/kodi-send --action='RunPlugin(plugin://plugin.program.sickrage/)'
sleep 2
tail -n 200 /storage/.kodi/temp/kodi.log
