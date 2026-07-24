import xbmc
import xbmcgui

import resources.lib.util as util


def action():
    showId = util.pluginArgs.get('id')
    season = util.pluginArgs.get('season')

    if not showId or season is None:
        util.message('Season Status', 'Missing show or season parameter')
        return

    statuses = util.STATUS_OPTIONS
    # Avoid prefetching episodes to compute a uniform season status — keep UI responsive
    statusList = [status.title() for status in statuses]

    dialog = xbmcgui.Dialog()
    statusIndex = dialog.select('Season Status', statusList)
    if statusIndex == -1:
        return

    status = statuses[statusIndex]

    try:
        # Use backend bulk operation where supported: pass episode=None to set whole season
        result = util.api.doEpisodeSetStatus(showId, int(season), None, status)
        if result.get('result') == 'success':
            xbmc.executebuiltin('Container.Refresh')
        else:
            util.message('Season Status', 'Failed to set season status', str(result))
    except Exception as e:
        util.message('Season Status', 'Failed to set season status', str(e))

