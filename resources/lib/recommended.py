import xbmcplugin
import xbmcgui
import xbmc
import xbmcvfs
import os
import json
import time
import re
import urllib.request
import urllib.parse

import resources.lib.util as util

# Cache TVmaze show index for 30 days (resilience — stale data beats no data)
_CACHE_TTL = 30 * 86400
# How many pages to fetch from TVmaze (250 shows per page); overridden by setting
_PAGES_DEFAULT = 5

# Genre display name → list of TVmaze genre strings to match (case-insensitive)
_GENRES = [
    ('Action',          ['Action']),
    ('Adventure',       ['Adventure']),
    ('Animation',       ['Animation', 'Anime', 'Children']),
    ('Comedy',          ['Comedy']),
    ('Crime & Thriller',['Crime', 'Legal', 'Mystery', 'Thriller']),
    ('Documentary',     ['Documentary', 'History', 'Nature']),
    ('Drama',           ['Drama', 'Family', 'Romance']),
    ('Fantasy',         ['Fantasy']),
    ('Horror',          ['Horror', 'Supernatural']),
    ('Science Fiction', ['Science-Fiction', 'Sci-Fi']),
    ('Sport',           ['Sports']),
    ('War & Western',   ['War', 'Western']),
]


def _strip_html(text):
    return re.sub(r'<[^>]+>', '', text or '').strip()


def _rec_source():
    """Return 'TVmaze' or 'Episodate' from addon settings."""
    return util.plugin.getSetting('rec_source') or 'TVmaze'


def _rec_pages():
    try:
        return int(util.plugin.getSetting('rec_pages') or _PAGES_DEFAULT)
    except Exception:
        return _PAGES_DEFAULT


def _cache_file():
    profile = xbmcvfs.translatePath(util.plugin.getAddonInfo('profile'))
    source  = _rec_source().lower()
    return os.path.join(profile, 'tvmaze_index_%s.json' % source)


def _load_cache():
    try:
        f = _cache_file()
        if os.path.exists(f):
            with open(f) as fp:
                stored = json.load(fp)
            if time.time() - stored.get('ts', 0) < _CACHE_TTL:
                return stored.get('shows', [])
    except Exception:
        pass
    return None


def _save_cache(shows):
    try:
        f = _cache_file()
        os.makedirs(os.path.dirname(f), exist_ok=True)
        with open(f, 'w') as fp:
            json.dump({'ts': time.time(), 'shows': shows}, fp)
    except Exception as e:
        xbmc.log('SickRage recommended: cache save failed: ' + str(e), xbmc.LOGWARNING)


def _fetch_catalogue():
    source = _rec_source()
    if source == 'Episodate':
        return _fetch_episodate()
    return _fetch_tvmaze()


def _fetch_tvmaze():
    shows  = []
    pages  = _rec_pages()
    dialog = xbmcgui.DialogProgress()
    dialog.create('SickRage Control', 'Loading recommendations...')
    for page in range(pages):
        if dialog.iscanceled():
            break
        dialog.update(
            int(100 * page / pages),
            'Fetching TVmaze catalogue (%d/%d)...' % (page + 1, pages)
        )
        try:
            url = 'https://api.tvmaze.com/shows?page=%d' % page
            req = urllib.request.urlopen(url, timeout=10)
            page_data = json.loads(req.read().decode('utf-8'))
            if not page_data:
                break
            shows.extend(page_data)
        except Exception as e:
            xbmc.log('SickRage recommended: TVmaze page %d failed: %s' % (page, str(e)), xbmc.LOGWARNING)
            break
    dialog.close()
    return shows


def _fetch_episodate():
    """Fetch from episodate.com most-popular-shows (free, no key, popularity-ranked).
    Normalises to same shape as TVmaze show dicts so the rest of the code is source-agnostic."""
    shows  = []
    pages  = min(_rec_pages(), 8)  # Episodate caps around 8 useful pages
    dialog = xbmcgui.DialogProgress()
    dialog.create('SickRage Control', 'Loading recommendations (Episodate)...')
    for page in range(1, pages + 1):
        if dialog.iscanceled():
            break
        dialog.update(
            int(100 * (page - 1) / pages),
            'Fetching Episodate catalogue (%d/%d)...' % (page, pages)
        )
        try:
            url = 'https://www.episodate.com/api/most-popular-shows?page=%d' % page
            req = urllib.request.urlopen(url, timeout=10)
            data = json.loads(req.read().decode('utf-8'))
            for s in data.get('tv_shows') or []:
                shows.append({
                    'id':        None,       # no TVmaze ID
                    '_epid':     s.get('id'),  # episodate internal id
                    'name':      s.get('name', ''),
                    'status':    s.get('status', ''),
                    'premiered': s.get('start_date', ''),
                    'genres':    [],
                    'rating':    {'average': 0},
                    'network':   {'name': s.get('network', '')},
                    'webChannel': None,
                    'image':     {'medium': s.get('image_thumbnail_path', '')},
                    'summary':   '',
                    'externals': {'thetvdb': None},
                    '_source':   'episodate',
                })
        except Exception as e:
            xbmc.log('SickRage recommended: Episodate page %d failed: %s' % (page, str(e)), xbmc.LOGWARNING)
            break
    dialog.close()
    return shows


def _get_catalogue():
    cached = _load_cache()
    if cached is not None:
        return cached
    shows = _fetch_catalogue()
    if shows:
        _save_cache(shows)
    return shows


def clear_cache():
    """Delete the on-disk catalogue cache so next visit fetches fresh data."""
    try:
        f = _cache_file()
        if os.path.exists(f):
            os.remove(f)
    except Exception as e:
        xbmc.log('SickRage recommended: cache clear failed: ' + str(e), xbmc.LOGWARNING)


def _library_ids():
    ids = set()
    try:
        for show in util.api.getShows().values():
            tid = show.get('tvdbid')
            if tid:
                ids.add(int(tid))
    except Exception:
        pass
    return ids


def _show_matches_genre(show, genre_tags):
    show_genres = [g.lower() for g in (show.get('genres') or [])]
    return any(tag.lower() in show_genres for tag in genre_tags)


def _detail_url(tvmaze_id, tvdb_id, name):
    return util.pluginURL + '?' + urllib.parse.urlencode({
        'vf': 'recommended_detail',
        'tvmazeid': str(tvmaze_id),
        'tvdbid': str(tvdb_id),
        'name': name,
    })


def _stars(rating):
    if not rating:
        return ''
    filled = int(round(rating / 2))
    return '[COLOR gold]' + '★' * filled + '[/COLOR][COLOR gray]' + '★' * (5 - filled) + '[/COLOR]'


def _stars_plain(rating):
    """Star string without colour tags, for plain-text dialogs."""
    if not rating:
        return ''
    filled = int(round(rating / 2))
    return '★' * filled + '☆' * (5 - filled)


def _set_info(li, name='', summary='', rating=0, premiered='', year=0, network='', genres=None, status=''):
    """Set video metadata using Kodi 21's InfoTagVideo API (setInfo is deprecated)."""
    try:
        tag = li.getVideoInfoTag()
        tag.setTitle(name)
        tag.setPlot(summary)
        tag.setPlotOutline(summary[:200] if summary else '')
        if rating:
            tag.setRating(float(rating))
        if premiered:
            tag.setFirstAired(premiered)
        if year:
            tag.setYear(int(year))
        if network:
            tag.setStudios([network])
        if genres:
            tag.setGenres(genres if isinstance(genres, list) else [genres])
        if status:
            tag.setTvShowStatus(status)
    except Exception:
        # Fallback for older Kodi builds
        li.setInfo('video', {
            'title': name, 'plot': summary, 'rating': float(rating) if rating else 0.0,
            'premiered': premiered, 'year': year, 'studio': network,
            'genre': ', '.join(genres) if genres else '', 'status': status,
        })


# ---------------------------------------------------------------------------
# Entry points called from addon.py
# ---------------------------------------------------------------------------

def menu():
    genre = util.pluginArgs.get('genre', '')
    if not genre:
        _menu_genres()
    else:
        _menu_shows(genre)


def detail():
    tvmaze_id = util.pluginArgs.get('tvmazeid', '')
    tvdb_id   = util.pluginArgs.get('tvdbid', '')
    name      = util.pluginArgs.get('name', 'Unknown Show')
    _menu_detail(tvmaze_id, tvdb_id, name)


def show_info_dialog(tvmaze_id, tvdb_id, name):
    """Popup dialog: metadata textviewer then add/update/trailer action menu.
    Works for both TVmaze (tvmaze_id known) and Episodate (tvmaze_id empty —
    falls back to TVmaze name search to resolve metadata + TVDB crosslink)."""
    show_data = {}
    cast_list = []

    if tvmaze_id:
        # TVmaze source — fetch by ID
        try:
            req = urllib.request.urlopen(
                'https://api.tvmaze.com/shows/%s?embed=cast' % tvmaze_id, timeout=10)
            show_data = json.loads(req.read().decode('utf-8'))
            cast_list = show_data.get('_embedded', {}).get('cast', [])
        except Exception as e:
            xbmc.log('SickRage recommended info: fetch failed: ' + str(e), xbmc.LOGWARNING)
    else:
        # Episodate source — search TVmaze by name to resolve metadata + TVDB ID
        try:
            url = 'https://api.tvmaze.com/search/shows?q=' + urllib.parse.quote(name)
            results = json.loads(urllib.request.urlopen(url, timeout=10).read().decode('utf-8'))
            if results:
                show_data = results[0].get('show') or {}
                tvdb_id   = str((show_data.get('externals') or {}).get('thetvdb') or tvdb_id or '')
                tvmaze_id = str(show_data.get('id', ''))
                if tvmaze_id:
                    req2 = urllib.request.urlopen(
                        'https://api.tvmaze.com/shows/%s?embed=cast' % tvmaze_id, timeout=10)
                    show_data = json.loads(req2.read().decode('utf-8'))
                    cast_list = show_data.get('_embedded', {}).get('cast', [])
        except Exception as e:
            xbmc.log('SickRage recommended info: Episodate crosslink failed: ' + str(e), xbmc.LOGWARNING)

    rating      = (show_data.get('rating') or {}).get('average') or 0
    premiered   = show_data.get('premiered') or ''
    year        = premiered[:4] if premiered else ''
    status      = show_data.get('status') or ''
    network     = ((show_data.get('network') or {}).get('name')
                   or (show_data.get('webChannel') or {}).get('name', ''))
    genres_list = show_data.get('genres') or []
    summary     = _strip_html(show_data.get('summary') or '')

    lib_ids    = _library_ids()
    tvdb_int   = int(tvdb_id) if tvdb_id else None
    in_library = tvdb_int is not None and tvdb_int in lib_ids

    # Build plain-text info block
    lines = []
    if rating:
        lines.append('%s   %.1f / 10' % (_stars_plain(rating), rating))
    meta = [p for p in [year, network, status] if p]
    if meta:
        lines.append('  ·  '.join(meta))
    if genres_list:
        lines.append('Genres:  ' + ', '.join(genres_list))
    if summary:
        lines.append('')
        lines.append(summary)
    if cast_list:
        lines.append('')
        lines.append('Cast:')
        for entry in cast_list[:8]:
            actor     = (entry.get('person') or {}).get('name', '')
            character = (entry.get('character') or {}).get('name', '')
            if actor:
                lines.append('  ' + (actor + '  as  ' + character if character else actor))

    info_text = '\n'.join(lines) if lines else 'No information available.'

    dialog = xbmcgui.Dialog()
    dialog.textviewer(name, info_text)

    # Action menu
    options = []
    if tvdb_id:
        options.append('Update from indexer' if in_library else 'Add to SickRage')
    options.append('Watch Trailer on YouTube')

    heading = ('%s   %.1f/10' % (name, rating)) if rating else name
    choice  = dialog.select(heading, options)
    if choice < 0:
        return

    selected = options[choice]
    if selected == 'Add to SickRage':
        import resources.lib.showAdd as showAdd
        util.pluginArgs['tvdbid'] = tvdb_id
        util.pluginArgs['name']   = name
        showAdd.directAction()
        xbmc.executebuiltin('Container.Refresh')
    elif selected == 'Update from indexer':
        try:
            util.api.doUpdateShow(tvdb_int)
            dialog.ok(name, 'Queued for update from the indexer.')
        except Exception as e:
            dialog.ok('Error', str(e))
    elif selected == 'Watch Trailer on YouTube':
        trailer_url = ('plugin://plugin.video.youtube/search/?q='
                       + urllib.parse.quote(name + ' official trailer'))
        xbmc.executebuiltin('RunPlugin(' + trailer_url + ')')


# ---------------------------------------------------------------------------
# Genre folder list
# ---------------------------------------------------------------------------

def _menu_genres():
    source = _rec_source()

    # -- Data source indicator + settings shortcut --
    li = xbmcgui.ListItem(label='[COLOR gray]Data source: [/COLOR][B]%s[/B]  [COLOR gray](change in Settings)[/COLOR]' % source)
    li.setArt({'icon': util.getIcon('settings' if source == 'TVmaze' else 'settings')})
    settings_url = 'RunAddon(plugin.program.sickrage)'  # triggers settings from menu click
    xbmcplugin.addDirectoryItem(
        handle=util.pluginId,
        url=util.getActionURL('openSettings'),
        listitem=li, isFolder=False)

    # -- Refresh catalogue --
    li = xbmcgui.ListItem(label='[COLOR gray]↻  Refresh catalogue[/COLOR]')
    xbmcplugin.addDirectoryItem(
        handle=util.pluginId,
        url=util.getActionURL('refreshRecommended'),
        listitem=li, isFolder=False)

    # -- Separator --
    sep = xbmcgui.ListItem(label='[COLOR gray]──────────────────────────[/COLOR]')
    xbmcplugin.addDirectoryItem(handle=util.pluginId, url=util.pluginURL, listitem=sep, isFolder=False)

    li = xbmcgui.ListItem(label='[B]Top Rated[/B]  [COLOR gray](all genres)[/COLOR]')
    li.setArt({'icon': util.getIcon('wanted')})
    url = util.pluginURL + '?' + urllib.parse.urlencode({'vf': 'recommended', 'genre': 'All'})
    xbmcplugin.addDirectoryItem(handle=util.pluginId, url=url, listitem=li, isFolder=True)

    for display_name, _ in _GENRES:
        li = xbmcgui.ListItem(label=display_name)
        url = util.pluginURL + '?' + urllib.parse.urlencode({'vf': 'recommended', 'genre': display_name})
        xbmcplugin.addDirectoryItem(handle=util.pluginId, url=url, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(util.pluginId, cacheToDisc=False)


# ---------------------------------------------------------------------------
# Show list for a genre
# ---------------------------------------------------------------------------

def _menu_shows(genre):
    source    = _rec_source()
    lib_ids   = _library_ids()
    all_shows = _get_catalogue()
    is_episodate = source == 'Episodate'

    genre_tags = None
    for display_name, tags in _GENRES:
        if display_name == genre:
            genre_tags = tags
            break

    candidates = []
    for show in all_shows:
        rating = (show.get('rating') or {}).get('average') or 0
        # TVmaze: require rating. Episodate: no ratings, accept all.
        if not is_episodate and not rating:
            continue
        if genre_tags and not _show_matches_genre(show, genre_tags):
            continue
        tvdb_id = (show.get('externals') or {}).get('thetvdb')
        if tvdb_id and int(tvdb_id) in lib_ids:
            continue
        candidates.append(show)

    if not is_episodate:
        candidates.sort(key=lambda s: (
            -((s.get('rating') or {}).get('average') or 0),
            s.get('premiered') or '9999'
        ))
    # Episodate: keep page-order (popularity rank)

    xbmcplugin.setContent(util.pluginId, 'tvshows')
    count = 0
    for show in candidates:
        if count >= 150:
            break

        name      = show.get('name', '')
        rating    = (show.get('rating') or {}).get('average') or 0
        premiered = show.get('premiered') or ''
        year      = premiered[:4] if premiered else ''
        network   = ((show.get('network') or {}).get('name')
                     or (show.get('webChannel') or {}).get('name', ''))
        genres_list = show.get('genres') or []
        summary   = _strip_html(show.get('summary') or '')
        image     = (show.get('image') or {}).get('medium', '')
        tvdb_id   = str((show.get('externals') or {}).get('thetvdb', ''))
        tvmaze_id = str(show.get('id', ''))

        score_str = ('  %s  [COLOR gray]%.1f/10[/COLOR]' % (_stars(rating), rating)) if rating else '  [COLOR gray]Unrated[/COLOR]'
        meta_parts = [p for p in [year, network] if p]
        label = name + score_str
        if meta_parts:
            label += '  [COLOR gray](%s)[/COLOR]' % ' · '.join(meta_parts)

        det_url  = _detail_url(tvmaze_id, tvdb_id, name)
        add_url  = util.getActionURL('showAddDirect', {'tvdbid': tvdb_id, 'name': name}) if tvdb_id else ''
        info_url = util.getActionURL('recommendedInfo', {'tvmazeid': tvmaze_id, 'tvdbid': tvdb_id, 'name': name})

        li = xbmcgui.ListItem(label=label)
        li.setProperty('IsPlayable', 'false')
        if image:
            li.setArt({'icon': image, 'thumb': image, 'poster': image})
        _set_info(li, name=name, summary=summary, rating=rating, premiered=premiered,
                  year=int(year) if year else 0, network=network, genres=genres_list,
                  status=show.get('status', ''))
        ctx = []
        if add_url:
            ctx.append(('Add to SickRage', 'RunPlugin(%s)' % add_url))
        ctx.append(('Cast & Trailer', 'Container.Update(%s)' % det_url))
        li.addContextMenuItems(ctx, True)

        xbmcplugin.addDirectoryItem(handle=util.pluginId, url=info_url, listitem=li, isFolder=False)
        count += 1

    xbmcplugin.endOfDirectory(util.pluginId, cacheToDisc=False)


# ---------------------------------------------------------------------------
# Detail page: summary, cast, trailer, add button
# ---------------------------------------------------------------------------

def _menu_detail(tvmaze_id, tvdb_id, name):
    show_data = {}
    cast_list = []
    if tvmaze_id:
        try:
            url = 'https://api.tvmaze.com/shows/%s?embed=cast' % tvmaze_id
            req = urllib.request.urlopen(url, timeout=10)
            show_data = json.loads(req.read().decode('utf-8'))
            cast_list = show_data.get('_embedded', {}).get('cast', [])
        except Exception as e:
            xbmc.log('SickRage recommended detail: fetch failed: ' + str(e), xbmc.LOGWARNING)

    rating      = (show_data.get('rating') or {}).get('average') or 0
    premiered   = show_data.get('premiered') or ''
    year        = premiered[:4] if premiered else ''
    network     = ((show_data.get('network') or {}).get('name')
                   or (show_data.get('webChannel') or {}).get('name', ''))
    genres_list = show_data.get('genres') or []
    summary     = _strip_html(show_data.get('summary') or '')
    image       = (show_data.get('image') or {}).get('medium', '')

    # URL for informational items — reloads this same page when clicked
    noop = _detail_url(tvmaze_id, tvdb_id, name)

    _info = dict(name=name, summary=summary, rating=rating, premiered=premiered,
                 year=int(year) if year else 0, network=network, genres=genres_list)

    # --- Header (title + rating + meta) ---
    score_str = ('%s  %.1f/10' % (_stars(rating), rating)) if rating else '[COLOR gray]No rating[/COLOR]'
    meta_parts = [p for p in [year, network] if p]
    header = '[B]' + name + '[/B]  ' + score_str
    if meta_parts:
        header += '  [COLOR gray](%s)[/COLOR]' % ' · '.join(meta_parts)

    li = xbmcgui.ListItem(label=header)
    if image:
        li.setArt({'icon': image, 'thumb': image, 'poster': image})
    _set_info(li, **_info)
    xbmcplugin.addDirectoryItem(handle=util.pluginId, url=noop, listitem=li, isFolder=True)

    # --- Summary snippet (first 250 chars; full plot available via Info button) ---
    if summary:
        snippet = summary[:250] + ('...' if len(summary) > 250 else '')
        li = xbmcgui.ListItem(label='[COLOR gray]' + snippet + '[/COLOR]')
        _set_info(li, **_info)
        xbmcplugin.addDirectoryItem(handle=util.pluginId, url=noop, listitem=li, isFolder=True)

    # --- Cast ---
    if cast_list:
        sep = xbmcgui.ListItem(label='[COLOR gray]――――――――  Cast  ――――――――[/COLOR]')
        xbmcplugin.addDirectoryItem(handle=util.pluginId, url=noop, listitem=sep, isFolder=True)

    for entry in cast_list[:12]:
        actor     = (entry.get('person') or {}).get('name', '')
        character = (entry.get('character') or {}).get('name', '')
        actor_img = ((entry.get('person') or {}).get('image') or {}).get('medium', '')
        if not actor:
            continue
        label = ('[B]' + character + '[/B]  [COLOR gray]—  ' + actor + '[/COLOR]') if character else actor
        li = xbmcgui.ListItem(label=label)
        li.setArt({'icon': actor_img or image, 'thumb': actor_img or image})
        _set_info(li, **_info)
        xbmcplugin.addDirectoryItem(handle=util.pluginId, url=noop, listitem=li, isFolder=True)

    # --- Divider ---
    sep = xbmcgui.ListItem(label='[COLOR gray]――――――――――――――――――――――――――[/COLOR]')
    xbmcplugin.addDirectoryItem(handle=util.pluginId, url=noop, listitem=sep, isFolder=True)

    # --- Watch Trailer (opens YouTube search) ---
    trailer_url = 'plugin://plugin.video.youtube/search/?q=' + urllib.parse.quote(name + ' official trailer')
    li = xbmcgui.ListItem(label='[COLOR cyan]▶  Watch Trailer on YouTube[/COLOR]')
    if image:
        li.setArt({'icon': image, 'thumb': image})
    xbmcplugin.addDirectoryItem(handle=util.pluginId, url=trailer_url, listitem=li, isFolder=True)

    # --- Add to SickRage ---
    if tvdb_id:
        add_url = util.getActionURL('showAddDirect', {'tvdbid': tvdb_id, 'name': name})
        li = xbmcgui.ListItem(label='[COLOR green]+  Add to SickRage[/COLOR]')
        li.setArt({'icon': util.getIcon('showAdd')})
        xbmcplugin.addDirectoryItem(handle=util.pluginId, url=add_url, listitem=li, isFolder=False)

    xbmcplugin.endOfDirectory(util.pluginId, cacheToDisc=False)


