import xbmcplugin
import xbmcgui
import urllib
import re

import resources.lib.util as util

def _shows_url(filter_mode=None):
    params = {'vf': 'shows'}
    if filter_mode:
        params['filter'] = filter_mode
    return util.pluginURL + '?' + urllib.parse.urlencode(params)

def menu():
    filter_mode = util.pluginArgs.get('filter', 'all')

    # Add show button - always first
    url = util.getActionURL('showAdd')
    listItem = xbmcgui.ListItem(label='[COLOR green]\u002b  Add Show...[/COLOR]')
    listItem.setArt({'icon': util.getIcon('showAdd'), 'thumb': util.getIcon('showAdd')})
    listItem.addContextMenuItems([('Refresh list', util.getContextCommand('refresh'))], True)
    xbmcplugin.addDirectoryItem(handle=util.pluginId, url=url, listitem=listItem, isFolder=False)

    # Filter selector
    for fkey, flabel in [('all', 'All Shows'), ('active', 'Active Only'), ('ended', 'Ended Only')]:
        if fkey == filter_mode:
            label = '[B]\u25b6  ' + flabel + '[/B]'
        else:
            label = '[COLOR gray]   ' + flabel + '[/COLOR]'
        li = xbmcgui.ListItem(label=label)
        xbmcplugin.addDirectoryItem(handle=util.pluginId, url=_shows_url(fkey), listitem=li, isFolder=True)

    all_shows = sorted(util.api.getShows().values(), key=lambda show: (
        1 if show['status'] == 'Ended' else 0,
        re.sub(r'^(the)\s+', '', show['show_name'], flags=re.IGNORECASE).lower()
    ))

    if filter_mode == 'active':
        active_shows = [s for s in all_shows if s['status'] != 'Ended']
        ended_shows = []
    elif filter_mode == 'ended':
        active_shows = []
        ended_shows = [s for s in all_shows if s['status'] == 'Ended']
    else:
        active_shows = [s for s in all_shows if s['status'] != 'Ended']
        ended_shows = [s for s in all_shows if s['status'] == 'Ended']

    def add_show(show):
        name    = show['show_name']
        paused  = show.get('paused', 0)
        ended   = show['status'] == 'Ended'
        network = show.get('network', '')
        quality = show.get('quality', '')

        if paused:
            label = '[COLOR gray]\u23f8  ' + name + '[/COLOR]'
        elif ended:
            label = '[COLOR gray]' + name + '[/COLOR]'
        else:
            label = '[COLOR white]' + name + '[/COLOR]'

        meta = []
        if ended:
            meta.append('[COLOR orange]Ended[/COLOR]')
        if paused:
            meta.append('[COLOR gray]Paused[/COLOR]')
        if network:
            meta.append('[COLOR gray]' + network + '[/COLOR]')
        if meta:
            label += '  ' + '  \u00b7  '.join(meta)

        show_url = util.getShowURL(show['tvdbid'])
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon':  util.api.getShowPoster(show['tvdbid']),
                   'thumb': util.api.getShowPoster(show['tvdbid'])})
        li.addContextMenuItems([
            ('Delete show',          util.getContextCommand('showDelete',     [show['tvdbid']])),
            (('Unpause' if paused else 'Pause') + ' show',
                                     util.getContextCommand('showPauseToggle',[show['tvdbid']])),
            ('Force search',         util.getContextCommand('showsSearch')),
            ('Refresh list',         util.getContextCommand('refresh'))
        ], True)
        xbmcplugin.addDirectoryItem(handle=util.pluginId, url=show_url,
                                    listitem=li, isFolder=True)

    for show in active_shows:
        add_show(show)

    if filter_mode == 'all' and active_shows and ended_shows:
        sep = xbmcgui.ListItem(label='[COLOR gray]――――――――  Ended  ――――――――[/COLOR]')
        xbmcplugin.addDirectoryItem(handle=util.pluginId, url=_shows_url(), listitem=sep, isFolder=True)

    for show in ended_shows:
        add_show(show)

    xbmcplugin.endOfDirectory(util.pluginId, cacheToDisc=False)

