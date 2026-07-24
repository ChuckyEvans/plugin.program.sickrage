import xbmc
import xbmcgui

import resources.lib.util as util


def action():
    showId = util.pluginArgs.get('id')
    if not showId:
        util.message('Show Status', 'Missing show parameter')
        return

    try:
        show = util.api.getShow(showId)
        showName = show.get('show_name', 'Show')
    except Exception:
        showName = 'Show'

    statuses = util.STATUS_OPTIONS
    # Use show metadata to detect current status and prefix it with a star
    try:
        currentStatus = (show.get('status') or '').lower()
    except Exception:
        currentStatus = None

    statusList = [('* ' if status == currentStatus else '') + status.title() for status in statuses]

    dialog = xbmcgui.Dialog()
    statusIndex = dialog.select('Set All Episodes Status — ' + showName, statusList)
    if statusIndex == -1:
        return

    status = statuses[statusIndex]

    try:
        seasons = util.api.getSeasonList(showId)
        if not seasons:
            util.message('Show Status', 'No seasons found for show')
            return

        failed = []
        updated = 0
        for season in seasons:
            try:
                episodes = util.api.getSeasons(showId, {'season': season})
                if not episodes:
                    continue
                for ep_num in episodes.keys():
                    result = util.api.doEpisodeSetStatus(showId, int(season), int(ep_num), status)
                    if result.get('result') == 'success':
                        updated += 1
                    else:
                        failed.append('%sx%s' % (season, ep_num))
                        util.log('showStatus: failed %sx%s: %s' % (season, ep_num, result))
            except Exception as e:
                util.log('showStatus: season %s error: %s' % (season, repr(e)))

        xbmc.executebuiltin('Container.Refresh')
        if failed:
            util.message('Show Status',
                         'Updated %d episodes; %d failed.' % (updated, len(failed)),
                         'Check the Kodi log for details.')
    except Exception as e:
        util.message('Show Status', 'Failed to set show status', str(e))
