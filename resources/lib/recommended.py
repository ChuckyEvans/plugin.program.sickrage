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
    return util.resolve_enum_label('rec_source') or 'TVmaze'


def _rec_pages():
    try:
        return int(util.resolve_enum_label('rec_pages') or _PAGES_DEFAULT)
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
    # Normalize selection and call the appropriate fetcher if available.
    src = (source or '').strip()
    if not src or src.lower() == 'tvmaze':
        return _fetch_tvmaze(fetch_latest=True)
    if src.lower() == 'episodate':
        return _fetch_episodate()
    # Both/All: combine TVmaze (newest) with Episodate (popularity) deduped
    if src.lower() in ('both', 'all'):
        tvmaze_shows = _fetch_tvmaze(fetch_latest=True)
        try:
            epid = _fetch_episodate()
            existing_names = set((s.get('name') or '').lower() for s in tvmaze_shows)
            existing_ids = set(str(s.get('id')) for s in tvmaze_shows if s.get('id'))
            for s in epid:
                name = (s.get('name') or '').lower()
                tid = str(s.get('_epid') or '')
                if name and name not in existing_names and tid not in existing_ids:
                    tvmaze_shows.append(s)
        except Exception:
            pass
        return tvmaze_shows

    # For other named sources (Trakt, TMDb, IMDb), try to call a matching fetcher
    fetcher_name = '_fetch_' + src.lower().replace(' ', '').replace('-', '')
    if fetcher_name in globals():
        try:
            return globals()[fetcher_name]()
        except Exception:
            pass

    # Unknown/unimplemented source: fallback to combined behaviour
    try:
        tvmaze_shows = _fetch_tvmaze(fetch_latest=True)
        epid = _fetch_episodate()
        existing_names = set((s.get('name') or '').lower() for s in tvmaze_shows)
        existing_ids = set(str(s.get('id')) for s in tvmaze_shows if s.get('id'))
        for s in epid:
            name = (s.get('name') or '').lower()
            tid = str(s.get('_epid') or '')
            if name and name not in existing_names and tid not in existing_ids:
                tvmaze_shows.append(s)
        return tvmaze_shows
    except Exception:
        return []


def _probe_tvmaze_last_page(max_probe=300):
    """Probe TVmaze to find the highest non-empty page index.
    Uses exponential/backoff then binary search. Caps at max_probe.
    Returns last page index (0-based) or 0 if unknown.
    """
    def page_has_data(p):
        try:
            url = 'https://api.tvmaze.com/shows?page=%d' % p
            req = urllib.request.urlopen(url, timeout=5)
            data = json.loads(req.read().decode('utf-8'))
            return bool(data)
        except Exception:
            return False

    # quick check
    if not page_has_data(0):
        return 0

    # exponential probe
    lo = 0
    hi = 1
    while hi <= max_probe and page_has_data(hi):
        lo = hi
        hi *= 2
    if hi > max_probe:
        hi = max_probe

    # binary search between lo and hi for last non-empty
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if page_has_data(mid):
            lo = mid
        else:
            hi = mid
    return lo


def _fetch_tvmaze(fetch_latest=False):
    shows = []
    pages = _rec_pages()
    dialog = xbmcgui.DialogProgress()
    dialog.create('SickRage Control', 'Loading recommendations...')

    page_range = range(pages)
    try:
        if fetch_latest:
            last = _probe_tvmaze_last_page()
            start = max(0, last - pages + 1)
            page_range = range(start, last + 1)
    except Exception:
        # fall back to first N pages
        page_range = range(pages)

    fetched = 0
    for idx, page in enumerate(page_range):
        if dialog.iscanceled():
            break
        try:
            dialog.update(
                int(100 * idx / max(1, len(list(page_range)))),
                'Fetching TVmaze catalogue (page %d)...' % (page + 1)
            )
        except Exception:
            pass
        try:
            url = 'https://api.tvmaze.com/shows?page=%d' % page
            req = urllib.request.urlopen(url, timeout=10)
            page_data = json.loads(req.read().decode('utf-8'))
            if not page_data:
                break
            shows.extend(page_data)
            fetched += len(page_data)
        except Exception as e:
            xbmc.log('SickRage recommended: TVmaze page %d failed: %s' % (page, str(e)), xbmc.LOGWARNING)
            break
    dialog.close()
    # If caller requested latest but results look very old, attempt updates-based fetch
    if fetch_latest:
        try:
            # compute average premiere year of fetched shows
            years = []
            for s in shows:
                p = s.get('premiered') or ''
                if p and len(p) >= 4 and p[:4].isdigit():
                    years.append(int(p[:4]))
            if years:
                avg = sum(years) / len(years)
                if avg < 2016:
                    xbmc.log('SickRage recommended: TVmaze page fetch returned old data (avg year=%s), switching to updates endpoint' % avg, xbmc.LOGNOTICE)
                    return _fetch_tvmaze_by_updates(pages)
        except Exception:
            pass
    return shows


def _fetch_tvmaze_by_updates(pages):
    """Fetch recent shows using TVmaze /updates/shows mapping to get newest IDs.
    Returns a list of show dicts up to ~pages * 60 items.
    """
    shows = []
    target = max(50, pages * 60)
    try:
        url = 'https://api.tvmaze.com/updates/shows'
        req = urllib.request.urlopen(url, timeout=10)
        data = json.loads(req.read().decode('utf-8'))
        # data is mapping id -> timestamp; sort by timestamp desc
        items = sorted(data.items(), key=lambda kv: int(kv[1] or 0), reverse=True)
        ids = [int(k) for k, _ in items[:target]]
        # fetch each show detail
        for sid in ids:
            try:
                sreq = urllib.request.urlopen('https://api.tvmaze.com/shows/%d' % sid, timeout=10)
                show = json.loads(sreq.read().decode('utf-8'))
                if show:
                    shows.append(show)
            except Exception:
                continue
    except Exception as e:
        xbmc.log('SickRage recommended: updates-based fetch failed: %s' % str(e), xbmc.LOGWARNING)
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


def _set_info(li, name='', summary='', rating=0, premiered='', year=0, network='', genres=None, status='', directors=None, cast=None, runtime=None, language=None, official=None, imdb=None):
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
        if runtime:
            try:
                tag.setDuration(int(runtime))
            except Exception:
                pass
        if language:
            try:
                tag.setCountries([language])
            except Exception:
                pass
        if official:
            try:
                tag.setTrailer(official)
            except Exception:
                pass
        if imdb:
            try:
                tag.setIMDBNumber(imdb)
            except Exception:
                pass
        # Cast/actors
        if cast:
            try:
                actors = cast if isinstance(cast, list) else [cast]
                tag.setCast([xbmc.Actor(name=a) for a in actors if a])
            except Exception:
                try:
                    tag.setCast(cast)
                except Exception:
                    pass
        # Directors (if available)
        if directors:
            try:
                # Some Kodi builds expose setDirector
                tag.setDirector(directors if isinstance(directors, list) else [directors])
            except Exception:
                pass
    except Exception:
        # Fallback for older Kodi builds
        info = {
            'title': name, 'plot': summary, 'rating': float(rating) if rating else 0.0,
            'premiered': premiered, 'year': year, 'studio': network,
            'genre': ', '.join(genres) if genres else '', 'status': status,
            'director': ', '.join(directors) if directors else '',
            'cast': cast if isinstance(cast, list) else ([cast] if cast else []),
        }
        if runtime:
            info['duration'] = int(runtime)
        if language:
            info['country'] = language
        if official:
            info['trailer'] = official
        if imdb:
            info['imdbnumber'] = imdb
        li.setInfo('video', info)


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
    crew_list = []

    if tvmaze_id:
        # TVmaze source — fetch by ID with embedded cast and crew for richer metadata
        try:
            req = urllib.request.urlopen(
                'https://api.tvmaze.com/shows/%s?embed=cast,crew' % tvmaze_id, timeout=10)
            show_data = json.loads(req.read().decode('utf-8'))
            cast_list = show_data.get('_embedded', {}).get('cast', [])
            crew_list = show_data.get('_embedded', {}).get('crew', [])
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
                        'https://api.tvmaze.com/shows/%s?embed=cast,crew' % tvmaze_id, timeout=10)
                    show_data = json.loads(req2.read().decode('utf-8'))
                    cast_list = show_data.get('_embedded', {}).get('cast', [])
                    crew_list = show_data.get('_embedded', {}).get('crew', [])
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
    runtime     = show_data.get('runtime') or show_data.get('averageRuntime') or ''
    language    = show_data.get('language') or ''
    official    = show_data.get('officialSite') or show_data.get('url') or ''
    externals   = show_data.get('externals') or {}
    imdb_id     = externals.get('imdb') or ''
    # Parse crew for directors/creators/writers
    directors = []
    creators = []
    writers = []
    for c in (crew_list or []):
        role = (c.get('type') or '').lower()
        person = (c.get('person') or {}).get('name')
        if not person:
            continue
        if 'director' in role:
            directors.append(person)
        elif 'writer' in role or 'writer' in (c.get('roles') or []):
            writers.append(person)
        elif 'creator' in role or 'creator' in (c.get('roles') or []):
            creators.append(person)

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
    if runtime:
        lines.append('Runtime: %s minutes' % runtime)
    if language:
        lines.append('Language: %s' % language)
    if official:
        lines.append('Official: %s' % official)
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
    # Crew lists
    if directors:
        lines.append('')
        lines.append('Directors:')
        lines.append('  ' + ', '.join(directors[:6]))
    if creators:
        lines.append('')
        lines.append('Creators:')
        lines.append('  ' + ', '.join(creators[:6]))
    if writers:
        lines.append('')
        lines.append('Writers:')
        lines.append('  ' + ', '.join(writers[:6]))
    if imdb_id:
        lines.append('')
        lines.append('IMDb: https://www.imdb.com/title/%s' % imdb_id)

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
        # Order by newest premiered first, then by highest rating.
        # Parse premiered to timestamp for robust comparisons; missing dates sort last.
        def _premiered_ts(s):
            p = s.get('premiered') or ''
            try:
                # expect YYYY-MM-DD
                t = time.strptime(p, '%Y-%m-%d')
                return int(time.mktime(t))
            except Exception:
                return 0

        candidates.sort(key=lambda s: (_premiered_ts(s), ((s.get('rating') or {}).get('average') or 0)), reverse=True)
    # Episodate: keep page-order (popularity rank)

    xbmcplugin.setContent(util.pluginId, 'tvshows')
    count = 0
    for show in candidates:
        if count >= 150:
            break

        name      = show.get('name', '')
        rating      = (show.get('rating') or {}).get('average') or 0
        premiered   = show.get('premiered') or ''
        year        = premiered[:4] if premiered else ''
        network     = ((show.get('network') or {}).get('name')
                       or (show.get('webChannel') or {}).get('name', ''))
        genres_list = show.get('genres') or []
        summary     = _strip_html(show.get('summary') or '')
        image       = (show.get('image') or {}).get('medium', '')
        tvdb_id     = str((show.get('externals') or {}).get('thetvdb', ''))
        tvmaze_id   = str(show.get('id', ''))
        runtime     = show.get('runtime') or show.get('averageRuntime') or ''
        language    = show.get('language') or ''
        official    = show.get('officialSite') or ''
        imdb_id     = (show.get('externals') or {}).get('imdb') or ''
        status      = show.get('status') or ''
        cast_names  = []

        score_str = ('  %s  [COLOR gray]%.1f/10[/COLOR]' % (_stars(rating), rating)) if rating else '  [COLOR gray]Unrated[/COLOR]'
        meta_parts = [p for p in [year, network] if p]
        # Build a richer label showing key meta inline
        label = name + score_str
        if meta_parts:
            label += '  [COLOR gray](%s)[/COLOR]' % ' · '.join(meta_parts)
        # append genres and status for quick glance
        extras = []
        if genres_list:
            extras.append('Genres: ' + ', '.join(genres_list[:4]))
        if status:
            extras.append(status)
        if runtime:
            extras.append('%s min' % runtime)
        if language:
            extras.append(language)
        if extras:
            label += '\n[COLOR gray]' + '  ·  '.join(extras) + '[/COLOR]'

        det_url  = _detail_url(tvmaze_id, tvdb_id, name)
        add_url  = util.getActionURL('showAddDirect', {'tvdbid': tvdb_id, 'name': name}) if tvdb_id else ''

        li = xbmcgui.ListItem(label=label)
        li.setProperty('IsPlayable', 'false')
        if image:
            try:
                cached_image = util.maybe_cache_image(image, subdir='poster_cache') or image
                li.setArt({'icon': cached_image, 'thumb': cached_image, 'poster': cached_image, 'fanart': cached_image})
                try:
                    li.setProperty('fanart_image', cached_image)
                    li.setProperty('Fanart_Image', cached_image)
                    li.setProperty('fanart', cached_image)
                    li.setProperty('thumb', cached_image)
                except Exception:
                    pass
            except Exception:
                # fall back to remote URL if caching fails
                li.setArt({'icon': image, 'thumb': image, 'poster': image, 'fanart': image})
        _set_info(li, name=name, summary=summary, rating=rating, premiered=premiered,
                  year=int(year) if year else 0, network=network, genres=genres_list,
                  status=status, cast=cast_names, runtime=runtime, language=language,
                  official=official, imdb=imdb_id)
        ctx = []
        if add_url:
            ctx.append(('Add to SickRage', 'RunPlugin(%s)' % add_url))
        # Directly open the detail page (full metadata + cast + trailer) on click
        ctx.append(('View Details & Trailer', 'Container.Update(%s)' % det_url))
        # Direct trailer search (YouTube) as a one-click action
        trailer_plugin = 'plugin://plugin.video.youtube/search/?q=' + urllib.parse.quote(name + ' official trailer')
        ctx.append(('Watch Trailer', 'RunPlugin(%s)' % trailer_plugin))
        li.addContextMenuItems(ctx, True)

        # Make the main item a folder so selecting it opens the detailed page
        xbmcplugin.addDirectoryItem(handle=util.pluginId, url=det_url, listitem=li, isFolder=True)
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
            url = 'https://api.tvmaze.com/shows/%s?embed=cast,crew' % tvmaze_id
            req = urllib.request.urlopen(url, timeout=10)
            show_data = json.loads(req.read().decode('utf-8'))
            cast_list = show_data.get('_embedded', {}).get('cast', [])
            crew_list = show_data.get('_embedded', {}).get('crew', [])
        except Exception as e:
            xbmc.log('SickRage recommended detail: fetch failed: ' + str(e), xbmc.LOGWARNING)

    # Parse crew in detail view for directors/creators/writers
    directors = []
    creators = []
    writers = []
    for c in (locals().get('crew_list') or []):
        role = (c.get('type') or '').lower()
        person = (c.get('person') or {}).get('name')
        if not person:
            continue
        if 'director' in role:
            directors.append(person)
        elif 'writer' in role or 'writer' in (c.get('roles') or []):
            writers.append(person)
        elif 'creator' in role or 'creator' in (c.get('roles') or []):
            creators.append(person)

    rating      = (show_data.get('rating') or {}).get('average') or 0
    premiered   = show_data.get('premiered') or ''
    year        = premiered[:4] if premiered else ''
    network     = ((show_data.get('network') or {}).get('name')
                   or (show_data.get('webChannel') or {}).get('name', ''))
    genres_list = show_data.get('genres') or []
    summary     = _strip_html(show_data.get('summary') or '')
    image       = (show_data.get('image') or {}).get('medium', '')
    status      = show_data.get('status') or ''
    runtime     = show_data.get('runtime') or show_data.get('averageRuntime') or ''
    language    = show_data.get('language') or ''
    official    = show_data.get('officialSite') or ''
    imdb_id     = (show_data.get('externals') or {}).get('imdb') or ''

    # URL for informational items — reloads this same page when clicked
    noop = _detail_url(tvmaze_id, tvdb_id, name)

    cast_names = [(entry.get('person') or {}).get('name', '') for entry in cast_list[:12]]
    cast_names = [a for a in cast_names if a]

    _info = dict(name=name, summary=summary, rating=rating, premiered=premiered,
                 year=int(year) if year else 0, network=network, genres=genres_list,
                 status=status, cast=cast_names, runtime=runtime, language=language,
                 official=official, imdb=imdb_id, directors=directors if 'directors' in locals() else None)

    # --- Header (title + rating + meta) ---
    score_str = ('%s  %.1f/10' % (_stars(rating), rating)) if rating else '[COLOR gray]No rating[/COLOR]'
    meta_parts = [p for p in [year, network, status] if p]
    header = '[B]' + name + '[/B]  ' + score_str
    if meta_parts:
        header += '  [COLOR gray](%s)[/COLOR]' % ' · '.join(meta_parts)

    li = xbmcgui.ListItem(label=header)
    if image:
        try:
            cached_image = util.maybe_cache_image(image, subdir='poster_cache') or image
            li.setArt({'icon': cached_image, 'thumb': cached_image, 'poster': cached_image, 'fanart': cached_image})
            try:
                li.setProperty('fanart_image', cached_image)
                li.setProperty('Fanart_Image', cached_image)
                li.setProperty('fanart', cached_image)
                li.setProperty('thumb', cached_image)
            except Exception:
                pass
        except Exception:
            li.setArt({'icon': image, 'thumb': image, 'poster': image, 'fanart': image})
    _set_info(li, **_info)
    xbmcplugin.addDirectoryItem(handle=util.pluginId, url=noop, listitem=li, isFolder=True)

    # --- Summary snippet (first 250 chars; full plot available via Info button) ---
    if summary:
        snippet = summary[:250] + ('...' if len(summary) > 250 else '')
        li = xbmcgui.ListItem(label='[COLOR gray]' + snippet + '[/COLOR]')
        _set_info(li, **_info)
        xbmcplugin.addDirectoryItem(handle=util.pluginId, url=noop, listitem=li, isFolder=True)

    # --- Metadata line item ---
    meta_items = []
    if genres_list:
        meta_items.append('Genres: ' + ', '.join(genres_list))
    if runtime:
        meta_items.append('Runtime: %s min' % runtime)
    if language:
        meta_items.append('Language: %s' % language)
    if official:
        meta_items.append('Official site')
    if meta_items:
        li = xbmcgui.ListItem(label='[COLOR gray]' + '  ·  '.join(meta_items) + '[/COLOR]')
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
        actor_url = ((entry.get('person') or {}).get('url') or '')
        if not actor:
            continue
        label = ('[B]' + character + '[/B]  [COLOR gray]—  ' + actor + '[/COLOR]') if character else actor
        # If TVmaze provides a person URL, make the item open that page directly.
        target_url = actor_url if actor_url else noop
        li = xbmcgui.ListItem(label=label)
        try:
            cached_actor = util.maybe_cache_image(actor_img, subdir='actor_cache') or (image)
            cached_fanart = util.maybe_cache_image(image, subdir='poster_cache') or image
            li.setArt({'icon': cached_actor or image, 'thumb': cached_actor or image, 'fanart': cached_fanart})
            try:
                li.setProperty('fanart_image', cached_actor or image)
                li.setProperty('Fanart_Image', cached_actor or image)
                li.setProperty('fanart', cached_fanart)
                li.setProperty('thumb', cached_actor or image)
            except Exception:
                pass
        except Exception:
            li.setArt({'icon': actor_img or image, 'thumb': actor_img or image, 'fanart': image})
        _set_info(li, **_info)
        xbmcplugin.addDirectoryItem(handle=util.pluginId, url=target_url, listitem=li, isFolder=False)

    # --- Divider ---
    sep = xbmcgui.ListItem(label='[COLOR gray]――――――――――――――――――――――――――[/COLOR]')
    xbmcplugin.addDirectoryItem(handle=util.pluginId, url=noop, listitem=sep, isFolder=True)

    # --- Watch Trailer (opens YouTube search) ---
    trailer_url = 'plugin://plugin.video.youtube/search/?q=' + urllib.parse.quote(name + ' official trailer')
    li = xbmcgui.ListItem(label='[COLOR cyan]▶  Watch Trailer on YouTube[/COLOR]')
    if image:
        try:
            cached_image = util.maybe_cache_image(image, subdir='poster_cache') or image
            li.setArt({'icon': cached_image, 'thumb': cached_image, 'fanart': cached_image})
            try:
                li.setProperty('fanart_image', cached_image)
                li.setProperty('Fanart_Image', cached_image)
                li.setProperty('fanart', cached_image)
                li.setProperty('thumb', cached_image)
            except Exception:
                pass
        except Exception:
            li.setArt({'icon': image, 'thumb': image, 'fanart': image})
    xbmcplugin.addDirectoryItem(handle=util.pluginId, url=trailer_url, listitem=li, isFolder=True)

    # --- Add to SickRage ---
    if tvdb_id:
        add_url = util.getActionURL('showAddDirect', {'tvdbid': tvdb_id, 'name': name})
        li = xbmcgui.ListItem(label='[COLOR green]+  Add to SickRage[/COLOR]')
        li.setArt({'icon': util.getIcon('showAdd')})
        xbmcplugin.addDirectoryItem(handle=util.pluginId, url=add_url, listitem=li, isFolder=False)

    xbmcplugin.endOfDirectory(util.pluginId, cacheToDisc=False)


