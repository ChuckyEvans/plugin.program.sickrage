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
        episodes = util.api.getSeasons(showId, {'season': season})
        if not episodes:
            util.message('Season Status', 'No episodes found for season')
            return

        failed = []
        updated = 0
        for ep_num in episodes.keys():
            result = util.api.doEpisodeSetStatus(showId, int(season), int(ep_num), status)
            if result.get('result') == 'success':
                updated += 1
            else:
                failed.append(str(ep_num))
                util.log('seasonStatus: failed episode %s: %s' % (ep_num, result))

        xbmc.executebuiltin('Container.Refresh')
        if failed:
            util.message('Season Status',
                         'Updated %d episodes; %d failed.' % (updated, len(failed)),
                         'Check the Kodi log for details.')
    except Exception as e:
        util.message('Season Status', 'Failed to set season status', str(e))

