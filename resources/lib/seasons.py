import xbmcplugin
import xbmcgui
import urllib

import resources.lib.util as util

def menu():
    showId   = util.pluginArgs['id']
    seasons  = sorted(util.api.getSeasonList(showId), reverse=True)
    poster   = util.api.getShowPoster(showId)

    for season in seasons:
        label = ('[B]Season %d[/B]' % season) if season > 0 else '[B]Extras[/B]'
        url   = util.pluginURL + '?' + urllib.parse.urlencode({
            'vf': 'episodes', 'id': showId, 'season': season
        })
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': poster, 'thumb': poster})
        li.addContextMenuItems([
            ('Refresh list', util.getContextCommand('refresh'))
        ], True)
        xbmcplugin.addDirectoryItem(handle=util.pluginId, url=url, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(util.pluginId)

