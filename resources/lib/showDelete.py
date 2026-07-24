import sys
import xbmc
import xbmcgui

import resources.lib.util as util


def action():
    showId = util.pluginArgs.get('id') or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not showId:
        util.message('Delete Show', 'Missing show parameter')
        return

    try:
        show = util.api.getShow(showId)
        showName = show.get('show_name', showId)
    except Exception as e:
        util.message('Delete Show', 'Unable to load show', str(e))
        return

    dialog = xbmcgui.Dialog()
    if dialog.yesno('Delete Show', 'Are you sure you want to delete ' + showName + '?'):
        try:
            result = util.api.doShowDelete(showId)
            if result.get('result') == 'success':
                xbmc.executebuiltin('Container.Refresh')
            else:
                util.message('Delete Show', 'Failed to delete show', result.get('message', 'Unknown error'))
        except Exception as e:
            util.message('Delete Show', 'Failed to delete show', str(e))
