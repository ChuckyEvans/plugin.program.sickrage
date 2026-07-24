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

    try:
        show_meta = util.api.getShow(showId)
    except Exception:
        show_meta = {}
    title = show_meta.get('show_name') or ''
    summary = show_meta.get('overview') or ''
    network = show_meta.get('network') or ''
    show_status = show_meta.get('status') or ''
    premiered = show_meta.get('first_aired') or ''
    genres = show_meta.get('genre') or []

    xbmcplugin.setContent(util.pluginId, 'episodes')

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
        try:
            _poster = util.maybe_cache_image(poster, subdir='poster_cache') or poster
        except Exception:
            _poster = poster
        li.setArt({'icon': _poster, 'thumb': _poster})
        # populate metadata for episode
        ep_name = ep.get('name', '')
        util.set_video_info(li, name=ep_name or label, summary=ep.get('overview',''), premiered=ep.get('first_aired',''), image=poster)
        status_url = util.getActionURL('episodeStatus', {'id': showId, 'season': season, 'episode': epNum, 'status': status})
        # play action when downloaded
        play_url = ''
        if status.lower() == 'downloaded':
            li.setProperty('IsPlayable', 'true')
            try:
                li.setLabel(label + '  [COLOR green]▶[/COLOR]')
            except Exception:
                pass
            play_url = util.getActionURL('playEpisode', {'id': showId, 'season': season, 'episode': epNum})

        ctx_items = [
            ('Play Episode',       'RunPlugin(%s)' % play_url) if play_url else None,
            ('Set Episode Status', 'RunPlugin(%s)' % status_url),
            ('Set Season Status',  util.getActionContextCommand('seasonStatus', {'id': showId, 'season': season})),
            ('Manual Search',      util.getActionContextCommand('episodeSearch', {'id': showId, 'season': season, 'episode': epNum})),
            ('Refresh list',       util.getContextCommand('refresh')),
        ]
        # remove the play-episode row if this episode isn't downloaded
        ctx_items = [item for item in ctx_items if item]

        li.addContextMenuItems(ctx_items, True)
        # downloaded items play directly; otherwise selecting opens the status dialog
        item_url = play_url if play_url else status_url
        xbmcplugin.addDirectoryItem(handle=util.pluginId, url=item_url,
                                    listitem=li, isFolder=False)

    xbmcplugin.endOfDirectory(util.pluginId)

