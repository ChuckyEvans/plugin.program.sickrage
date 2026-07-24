import xbmcplugin
import xbmcgui
import urllib

import resources.lib.util as util

def menu():
    showId   = util.pluginArgs['id']
    seasons  = sorted(util.api.getSeasonList(showId), reverse=True)
    poster   = util.api.getShowPoster(showId)

    # Show header: poster + metadata (SickRage primary, enrich with TVmaze if possible)
    try:
        show_meta = util.api.getShow(showId)
    except Exception:
        show_meta = {}
    tvdb = show_meta.get('tvdbid') or showId
    # attempt TVmaze lookup by TVDB id for richer metadata
    tvmaze_data = None
    try:
        if tvdb:
            import urllib.request, urllib.parse, json
            url = 'https://api.tvmaze.com/lookup/shows?thetvdb=%s' % str(tvdb)
            req = urllib.request.urlopen(url, timeout=6)
            tvmaze_data = json.loads(req.read().decode('utf-8'))
    except Exception:
        tvmaze_data = None

    # Compose header info
    title = show_meta.get('show_name') or (tvmaze_data and tvmaze_data.get('name')) or ''
    summary = show_meta.get('overview') or (tvmaze_data and util.strip_html(tvmaze_data.get('summary') or ''))
    network = show_meta.get('network') or (tvmaze_data and ((tvmaze_data.get('network') or {}).get('name') or (tvmaze_data.get('webChannel') or {}).get('name')))
    status = show_meta.get('status') or (tvmaze_data and tvmaze_data.get('status'))
    premiered = show_meta.get('first_aired') or (tvmaze_data and (tvmaze_data.get('premiered') or ''))
    genres = show_meta.get('genre') or (tvmaze_data and tvmaze_data.get('genres') or [])

    # header list item
    header_label = '[B]' + (title or 'Show') + '[/B]'
    if status:
        header_label += '  [COLOR gray](%s)[/COLOR]' % status
    li = xbmcgui.ListItem(label=header_label)
    try:
        if poster:
            try:
                _poster = util.maybe_cache_image(poster, subdir='poster_cache') or poster
            except Exception:
                _poster = poster
            li.setArt({'icon': _poster, 'thumb': _poster, 'poster': _poster})
    except Exception:
        pass
    util.set_video_info(li, name=title, summary=summary, premiered=premiered, network=network, status=status, genres=genres, image=poster)
    xbmcplugin.addDirectoryItem(handle=util.pluginId, url=util.getShowURL(showId), listitem=li, isFolder=True)

    for season in seasons:
        label = ('[B]Season %d[/B]' % season) if season > 0 else '[B]Extras[/B]'
        url   = util.pluginURL + '?' + urllib.parse.urlencode({
            'vf': 'episodes', 'id': showId, 'season': season
        })
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': poster, 'thumb': poster})
        li.addContextMenuItems([
            ('Set Season Status', util.getActionContextCommand('seasonStatus', {'id': showId, 'season': season})),
            ('Set Show Status',   util.getActionContextCommand('showStatus',   {'id': showId})),
            ('Configure Show Settings', util.getActionContextCommand('showSettings', {'id': showId})),
            ('Refresh list',      util.getContextCommand('refresh'))
        ], True)
        xbmcplugin.addDirectoryItem(handle=util.pluginId, url=url, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(util.pluginId)

