import xbmcplugin
import xbmcgui
import urllib
import re

import resources.lib.util as util

_STATUS_STYLE = {
    'Downloaded': ('[COLOR green]\u2713  Downloaded[/COLOR]', 'downloaded'),
    'Snatched':   ('[COLOR cyan]\u2193  Snatched[/COLOR]',   'snatched'),
    'Failed':     ('[COLOR red]\u2715  Failed[/COLOR]',       'wanted'),
}

def menu():
    history = util.api.getHistory()
    shows   = {}

    for show in history:
        uId = str(show['tvdbid']) + '-' + str(show['season']) + '-' + str(show['episode'])
        if (not uId in shows) or (show['status'] == 'Downloaded'):
            shows[uId] = show

    shows = sorted(shows.values(), key=lambda s: s['date'], reverse=True)

    for show in shows:
        status           = show.get('status', '')
        style, icon_name = _STATUS_STYLE.get(status, (
            '[COLOR gray]' + status + '[/COLOR]', 'wanted'))

        dt_str = util.formatDateTime(show['date'])
        ep_str = util.formatEpisodeName(show)
        label  = style + '  [COLOR gray]' + dt_str + '[/COLOR]  ' + ep_str

        url  = util.getShowURL(show['tvdbid'])
        li   = xbmcgui.ListItem(label=label)
        icon = util.getIcon(icon_name)
        li.setArt({'icon': icon, 'thumb': icon})
        li.addContextMenuItems([
            ('Refresh list', util.getContextCommand('refresh'))
        ], True)
        xbmcplugin.addDirectoryItem(handle=util.pluginId, url=url, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(util.pluginId, cacheToDisc=False)
