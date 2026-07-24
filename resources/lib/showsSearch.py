import xbmc

import resources.lib.util as util


def action():
    result = util.api.doForceSearch()
    util.message("Force Search", "Force search returned " + result.get('result', 'unknown'))
    xbmc.executebuiltin('Container.Refresh')
