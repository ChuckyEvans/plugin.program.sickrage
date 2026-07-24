#!/bin/sh
set -e
python3 - <<'PY'
import os, shutil
root='/storage/.kodi/addons/plugin.program.sickrage'
for dirpath, dirnames, filenames in os.walk(root, topdown=False):
    # process files
    for name in filenames:
        if '\\' in name:
            parts=[p for p in name.split('\\') if p!='']
            if not parts:
                continue
            src=os.path.join(dirpath,name)
            dest=os.path.join(dirpath,*parts)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            print('mv',src,'->',dest)
            shutil.move(src,dest)
    # process directories with backslashes
    for name in dirnames:
        if '\\' in name:
            parts=[p for p in name.split('\\') if p!='']
            if not parts:
                continue
            src=os.path.join(dirpath,name)
            dest=os.path.join(dirpath,*parts)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            try:
                shutil.move(src,dest)
                print('mv',src,'->',dest)
            except Exception as e:
                print('skip',src,e)
PY
# fix perms and restart Kodi
chown -R root:root /storage/.kodi/addons/plugin.program.sickrage || true
chmod -R a+rX /storage/.kodi/addons/plugin.program.sickrage || true
if command -v systemctl >/dev/null 2>&1; then systemctl restart kodi || true; fi
killall -9 kodi.bin || true
sleep 6
echo '--- kodi.log after python fix ---'
tail -n 300 /storage/.kodi/temp/kodi.log || true
ls -la /storage/.kodi/addons/plugin.program.sickrage/resources || true
ls -la /storage/.kodi/addons/plugin.program.sickrage/resources/lib || true
