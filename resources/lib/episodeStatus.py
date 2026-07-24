import xbmc
import xbmcgui

import resources.lib.util as util


def action():
    showId = util.pluginArgs.get('id')
    season = util.pluginArgs.get('season')
    episode = util.pluginArgs.get('episode')
    currentStatus = (util.pluginArgs.get('status') or '').lower()

    if not showId or season is None or episode is None:
        util.message('Episode Status', 'Missing show/season/episode parameters')
        return

    statuses = util.STATUS_OPTIONS
    statusList = []
    for status in statuses:
        statusList.append(('* ' if status == currentStatus else '') + status.title())

    dialog = xbmcgui.Dialog()
    statusIndex = dialog.select('Episode Status', statusList)
    if statusIndex == -1:
        return

    status = statuses[statusIndex]
    if status == currentStatus:
        return

    try:
        result = util.api.doEpisodeSetStatus(showId, int(season), int(episode), status)
        if result.get('result') == 'success':
            xbmc.executebuiltin('Container.Refresh')
        else:
            util.message('Episode Status', 'Failed to set status', result.get('message', 'Unknown error'))
    except Exception as e:
        util.message('Episode Status', 'Failed to set status', str(e))

