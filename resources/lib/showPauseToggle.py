import sys
import xbmc

import resources.lib.util as util


def action():
    showId = util.pluginArgs.get('id') or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not showId:
        util.message('Pause Toggle', 'Missing show parameter')
        return

    try:
        show = util.api.getShow(showId)
        current = show.get('paused', 0)
        util.api.setShowPause(showId, current == 0)
        xbmc.executebuiltin('Container.Refresh')
    except Exception as e:
        util.message('Pause Toggle', 'Failed to pause/unpause show', str(e))