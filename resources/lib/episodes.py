import xbmcplugin
import xbmcgui
import urllib

import resources.lib.util as util

# Colour + symbol per episode status
_STATUS_STYLE = {
    'Downloaded': '[COLOR green]\u2713[/COLOR]',
    'Snatched':   '[COLOR cyan]\u2193[/COLOR]',
    'Wanted':     '[COLOR orange]\u25cf[/COLOR]',
    'Skipped':    '[COLOR gray]\u2014[/COLOR]',
    'Ignored':    '[COLOR gray]\u00d7[/COLOR]',
    'Archived':   '[COLOR gold]\u2606[/COLOR]',
    'Failed':     '[COLOR red]\u2715[/COLOR]',
    'Unaired':    '[COLOR gray]\u25a1[/COLOR]',
}

def menu():
    showId     = util.pluginArgs['id']
    season     = int(util.pluginArgs['season'])
    episodes   = util.api.getSeasons(showId, {'season': season})
    poster     = util.api.getShowPoster(showId)

    for epNum in sorted(episodes.keys(), key=int, reverse=True):
        ep     = episodes[epNum]
        status = ep.get('status', '')
        sym    = _STATUS_STYLE.get(status, '[COLOR gray]?[/COLOR]')
        label  = '%s  %s  [COLOR gray]%s[/COLOR]  %s' % (
            sym,
            ('%02d' % int(epNum)),
            status,
            ep.get('name', ''),
        )

        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': poster, 'thumb': poster})
        li.addContextMenuItems([
            ('Set Episode Status', util.getContextCommand('episodeStatus',
                [showId, season, epNum, status])),
            ('Set Season Status',  util.getContextCommand('seasonStatus',
                [showId, season])),
            ('Manual Search',      util.getContextCommand('episodeSearch',
                [showId, season, epNum])),
            ('Refresh list',       util.getContextCommand('refresh')),
        ], True)
        xbmcplugin.addDirectoryItem(handle=util.pluginId, url=None,
                                    listitem=li, isFolder=False)

    xbmcplugin.endOfDirectory(util.pluginId)

