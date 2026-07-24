import sys
import os

# Ensure the addon's root is on sys.path so `import resources` works when Kodi
# executes this script directly.
addon_root = os.path.join('/storage', '.kodi', 'addons', 'plugin.program.sickrage')
if addon_root not in sys.path:
    sys.path.insert(0, addon_root)

import resources.lib.util as util

# Run the migration helper in the addon context
try:
    util.log('run_migrate_sickrage: starting')
    res = util.migrate_legacy_settings()
    util.log('run_migrate_sickrage: migrate_legacy_settings returned %r' % (res,))
except Exception as e:
    try:
        util.log('run_migrate_sickrage: exception %s' % repr(e))
    except Exception:
        pass
