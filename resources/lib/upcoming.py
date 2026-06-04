import xbmcplugin
import xbmcgui
import urllib
import re
import functools

import resources.lib.util as util

_SECTION_LABELS = {
    0: ('[COLOR green]\u25cf  TODAY[/COLOR]',  'today'),
    1: ('[COLOR cyan]\u25cf  SOON[/COLOR]',    'soon'),
    2: ('[COLOR gray]\u25cf  LATER[/COLOR]',   'later'),
}

def menu():
    shows = util.api.getFuture()

    sections = [
        (0, sorted(shows.get('today', []), key=functools.cmp_to_key(compareAirDate))),
        (1, sorted(shows.get('soon',  []), key=functools.cmp_to_key(compareAirDate))),
        (2, sorted(shows.get('later', []), key=functools.cmp_to_key(compareAirDate))),
    ]

    for when, group in sections:
        if not group:
            continue
        header_label, icon_name = _SECTION_LABELS[when]
        sep = xbmcgui.ListItem(label=header_label)
        sep.setArt({'icon': util.getIcon(icon_name), 'thumb': util.getIcon(icon_name)})
        xbmcplugin.addDirectoryItem(handle=util.pluginId, url='', listitem=sep, isFolder=False)
        for show in group:
            addShow(when, show)

    xbmcplugin.endOfDirectory(util.pluginId, cacheToDisc=False)

def addShow(when, show):
    airs = show['airs'].split(' ') if show.get('airs') else []
    day  = airs[0] if len(airs) > 0 else ''
    time = airs[1] if len(airs) > 1 else ''
    ampm = airs[2] if len(airs) > 2 else None

    if when == 0:
        time_str = util.formatTime(time, ampm) if time else ''
        when_col = 'green'
    elif when == 1:
        time_str = (day + ' ' + util.formatTime(time, ampm)).strip() if time else day
        when_col = 'cyan'
    else:
        time_str = util.formatDate(show['airdate'])
        if time:
            time_str += ', ' + (day + ' ' + util.formatTime(time, ampm)).strip()
        when_col = 'gray'

    ep_label  = util.formatEpisodeName(show)
    time_part = ('[COLOR %s]%s[/COLOR]  ' % (when_col, time_str)) if time_str else ''
    label     = time_part + ep_label

    icon = util.getIcon(['today', 'soon', 'later'][when])
    url  = util.getShowURL(show['tvdbid'])
    li   = xbmcgui.ListItem(label=label)
    li.setArt({'icon': icon, 'thumb': icon})
    li.addContextMenuItems([('Refresh list', util.getContextCommand('refresh'))], True)
    xbmcplugin.addDirectoryItem(handle=util.pluginId, url=url, listitem=li, isFolder=True)


def compareAirDate(showA, showB):
    # compare date
    if showA['airdate'] < showB['airdate']:
        return -1
    elif showA['airdate'] > showB['airdate']:
        return 1
    else:
        # compare AM/PM
        airsA = showA['airs'].split(' ') if showA.get('airs') else []
        airsB = showB['airs'].split(' ') if showB.get('airs') else []
        ampmA = airsA[2] if len(airsA) > 2 else ''
        ampmB = airsB[2] if len(airsB) > 2 else ''
        if ampmA < ampmB:
            return -1
        elif ampmA > ampmB:
            return 1
        else:
            # compare time
            timeA = airsA[1].rjust(5) if len(airsA) > 1 else ''
            timeB = airsB[1].rjust(5) if len(airsB) > 1 else ''
            if timeA < timeB:
                return -1
            elif timeA > timeB:
                return 1
            else:
                return 0
