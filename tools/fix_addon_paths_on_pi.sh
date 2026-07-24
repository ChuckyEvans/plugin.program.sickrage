#!/bin/sh
set -e
PKGDIR=/storage/.kodi/addons/plugin.program.sickrage
cd "$PKGDIR"
# Move files that include backslashes in their names into proper directories
find . -maxdepth 2 -type f -name '*\\*' -print0 | while IFS= read -r -d '' f; do
  new=$(echo "$f" | sed 's#\\#/#g' | sed 's#^\./##')
  dir=$(dirname "$new")
  mkdir -p "$dir"
  echo mv -v "$f" "$new"
  mv -v "$f" "$new"
done
# Remove any zero-byte files that represent directory entries like 'resources\\language\\'
find . -maxdepth 2 -type f -size 0 -name '*\\' -print0 | while IFS= read -r -d '' f; do
  newdir=$(echo "$f" | sed 's#\\#/#g' | sed 's#^\./##')
  echo "Creating directory: $newdir"
  mkdir -p "$newdir"
  rm -f "$f"
done
# Fix ownership and permissions
chown -R root:root "$PKGDIR"
chmod -R a+rX "$PKGDIR"
# Restart Kodi
if command -v systemctl >/dev/null 2>&1; then systemctl restart kodi || true; fi
killall -9 kodi.bin || true
sleep 6
# Tail log
echo "--- kodi.log after fix ---"
tail -n 300 /storage/.kodi/temp/kodi.log || true
# List resources directory
echo "--- resources tree ---"
ls -la "$PKGDIR/resources" || true
ls -la "$PKGDIR/resources/lib" || true
