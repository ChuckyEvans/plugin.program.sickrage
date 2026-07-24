#!/usr/bin/env python3
"""Push a validated Kodi addon `settings.xml` to a remote LibreELEC / Kodi device.

Usage:
  python tools/push_settings.py --host 192.168.8.250 --user root --src tmp_settings.xml

The script copies the local XML to `/storage/.kodi/userdata/addon_data/plugin.program.sickrage/settings.xml`
and sets permissions to 644. It validates the file contains an XML declaration and `setting` tags.
"""
import argparse
import subprocess
import sys
import os

DEST_PATH = '/storage/.kodi/userdata/addon_data/plugin.program.sickrage/settings.xml'


def validate(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            txt = f.read()
        if '<?xml' not in txt or '<setting' not in txt:
            return False, 'Missing XML declaration or <setting> tags'
        return True, None
    except Exception as e:
        return False, str(e)


def scp_copy(src, user, host, dest):
    target = f"{user}@{host}:{dest}"
    cmd = ['scp', src, target]
    subprocess.check_call(cmd)


def ssh_chmod(user, host, dest):
    cmd = ['ssh', f'{user}@{host}', 'chmod', '644', dest, '&&', 'sync']
    subprocess.check_call(cmd)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--host', required=True)
    p.add_argument('--user', default='root')
    p.add_argument('--src', required=True, help='Local validated settings.xml')
    args = p.parse_args()

    src = os.path.abspath(args.src)
    ok, err = validate(src)
    if not ok:
        print('Validation failed:', err, file=sys.stderr)
        sys.exit(2)

    try:
        scp_copy(src, args.user, args.host, DEST_PATH)
        ssh_chmod(args.user, args.host, DEST_PATH)
        print('Pushed', src, 'to', args.host)
    except subprocess.CalledProcessError as e:
        print('Command failed:', e, file=sys.stderr)
        sys.exit(3)


if __name__ == '__main__':
    main()
