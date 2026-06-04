import xbmc

import resources.lib.util as util

result = util.api.doForceSearch()
util.settings.message("Force Search", "Force search returned " + result['result'])
