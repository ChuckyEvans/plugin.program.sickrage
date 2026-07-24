import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / 'build'
OUT_DIR.mkdir(exist_ok=True)
ZIP_NAME = OUT_DIR / 'plugin.program.sickrage.zip'

EXCLUDE_DIRS = {'.git', 'backups', 'build', '__pycache__', '.venv', 'tmp_backup_extract', 'tools'}
EXCLUDE_FILES = {'.DS_Store', 'kodi.log'}

def should_include(path: Path):
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return False
    if path.name in EXCLUDE_FILES:
        return False
    return True

with zipfile.ZipFile(ZIP_NAME, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(ROOT):
        root_path = Path(root)
        # skip excluded dirs
        dirs[:] = [d for d in dirs if should_include(root_path / d)]
        for f in files:
            fp = root_path / f
            if not should_include(fp):
                continue
            # write relative path
            arcname = fp.relative_to(ROOT)
            zf.write(fp, arcname)

print('Wrote', ZIP_NAME)
