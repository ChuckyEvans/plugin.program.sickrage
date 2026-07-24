import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmc
import urllib
from urllib.parse import urlparse
import pprint
import sys
import os
import shutil
import xml.etree.ElementTree as ET
import re

plugin = xbmcaddon.Addon(id = 'plugin.program.sickrage')

import resources.lib.sickrage as sickrage

def log(obj):
    if not isinstance(obj, str):
        msg = pprint.pformat(obj)
    else:
        msg = str(obj)
    xbmc.log('Sickrage plugin: ' + msg, xbmc.LOGINFO)

def getShowURL(id):    
    return pluginURL + '?' + urllib.parse.urlencode({
        'vf': 'seasons',
        'id': id
    })
    
# Status choices surfaced by the episode/season/show status popups.
# These lower-case strings match what the SickRage episode.setstatus API expects.
STATUS_OPTIONS = ['wanted', 'skipped', 'archived', 'ignored', 'failed']


def getContextCommand(cmd, args = []):
    # The refresh command can run a built-in directly; no script needed.
    if cmd == 'refresh':
        return 'Container.Refresh'

    cmd = 'XBMC.RunScript(special://home/addons/plugin.program.sickrage/resources/lib/' + cmd + '.py'
    if args:
        args = [str(i) for i in args]
        cmd = cmd + ', ' + ', '.join(args)
    cmd = cmd + ')'
    return cmd


def getActionContextCommand(action, params = None):
    """Return a context-menu command string that runs an addon action via RunPlugin."""
    return 'RunPlugin(%s)' % getActionURL(action, params or {})

def getIcon(name):
    return os.path.join(iconDir, name + '.png')


def _poster_cache_dir():
    """Return directory used for cached show poster images."""
    d = os.path.join(_addon_data_dir(), 'poster_cache')
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d


def _auth_for_url(base_url):
    """Return (url_with_auth, headers) for SickRage web UI requests.
    Embeds credentials into the URL when possible; callers that need headers
    can add the returned dict as well."""
    user = plugin.getSetting('user') or ''
    password = plugin.getSetting('password') or ''
    if not user or not password:
        return base_url, {}
    try:
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(base_url)
        netloc = '%s:%s@%s' % (user, password, parsed.netloc)
        auth_url = urlunparse((parsed.scheme, netloc, parsed.path,
                               parsed.params, parsed.query, parsed.fragment))
        return auth_url, {}
    except Exception:
        return base_url, {}


def cache_poster_url(show_id, which='poster'):
    """Fetch a showPoster image with Basic Auth and return a local file path.
    Kodi's image loader cannot send auth headers, so we download the image
    through Python and cache it in addon_data/poster_cache."""
    import urllib.request as _req
    import urllib.error as _err
    import base64
    cache_file = os.path.join(_poster_cache_dir(), '%s_%s.jpg' % (show_id, which))
    try:
        if os.path.exists(cache_file):
            # refresh if older than 7 days
            age = __import__('time').time() - os.path.getmtime(cache_file)
            if age < 604800:
                return cache_file
    except Exception:
        pass
    # Build SickRage showPoster API URL and use generic image cacher so
    # we get consistent auth handling and filename hashing.
    base = (plugin.getSetting('url') or '').strip().rstrip('/') + '/'
    url = base + 'showPoster/?show=%s&which=%s&api=1' % (show_id, which)
    try:
        return cache_image_url(url, subdir='poster_cache', name='%s_%s' % (show_id, which))
    except Exception as e:
        log('cache_poster_url failed: %s' % repr(e))
    except _err.HTTPError as e:
        log('cache_poster_url HTTP %s for %s' % (e.code, url))
    except Exception as e:
        log('cache_poster_url failed: %s' % repr(e))
    # fallback: return original URL (will likely 401, but no crash)
    return url


def cache_image_url(url, subdir='image_cache', name=None, max_age_seconds=604800):
    """Download an image URL and cache it under addon_data/<subdir>.
    If the remote host matches the configured SickRage base URL, attach
    Basic Auth headers. Returns local filesystem path on success or
    raises on error.
    """
    import urllib.request as _req
    import urllib.error as _err
    import hashlib
    from urllib.parse import urlparse

    # ensure cache dir
    d = os.path.join(_addon_data_dir(), subdir)
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass

    # Determine filename (hash of url, preserve extension when possible)
    parsed = urlparse(url)
    path = parsed.path or ''
    ext = os.path.splitext(path)[1] or '.img'
    if name:
        fname = re.sub(r'[^A-Za-z0-9_.-]', '_', name) + ext
    else:
        h = hashlib.sha1(url.encode('utf-8')).hexdigest()
        fname = h + ext

    cache_file = os.path.join(d, fname)
    try:
        if os.path.exists(cache_file):
            age = __import__('time').time() - os.path.getmtime(cache_file)
            if age < max_age_seconds:
                return cache_file
    except Exception:
        pass

    req = _req.Request(url)
    # If we need to authenticate to the SickRage host, add Basic Auth and
    # use an opener that preserves the Authorization header across redirects.
    opener = None
    try:
        base = (plugin.getSetting('url') or '').strip().rstrip('/')
        if base:
            bhost = urlparse(base).netloc
            if parsed.netloc == bhost:
                user = plugin.getSetting('user') or ''
                password = plugin.getSetting('password') or ''
                if user and password:
                    import base64 as _b64
                    auth = _b64.b64encode(('%s:%s' % (user, password)).encode('utf-8')).decode('ascii')
                    req.add_header('Authorization', 'Basic %s' % auth)

                    # Build opener that preserves Authorization on redirects
                    class _PreserveAuthRedirect(_req.HTTPRedirectHandler):
                        def redirect_request(self, req2, fp, code, msg, headers, newurl):
                            newreq = _req.HTTPRedirectHandler.redirect_request(self, req2, fp, code, msg, headers, newurl)
                            if newreq is None:
                                return None
                            if req2.get_header('Authorization'):
                                newreq.add_header('Authorization', req2.get_header('Authorization'))
                            return newreq

                    opener = _req.build_opener(_PreserveAuthRedirect)
    except Exception:
        opener = None

    try:
        if opener:
            resp = opener.open(req, timeout=20)
            data = resp.read()
        else:
            with _req.urlopen(req, timeout=20) as resp:
                data = resp.read()
        if data:
            with open(cache_file, 'wb') as f:
                f.write(data)
            return cache_file
        raise Exception('empty response')
    except _err.HTTPError as e:
        log('cache_image_url HTTP %s for %s' % (e.code, url))
        raise
    except Exception as e:
        log('cache_image_url failed: %s' % repr(e))
        raise


def maybe_cache_image(value, subdir='image_cache'):
    """If `value` looks like a remote URL, download/cache and return local path.
    Otherwise return `value` unchanged.
    """
    try:
        if not value or not isinstance(value, str):
            return value
        if value.startswith('http://') or value.startswith('https://'):
            try:
                return cache_image_url(value, subdir=subdir)
            except Exception:
                return value
    except Exception:
        pass
    return value


def getFolderURL(vf):
    params = {'vf': vf}
    url = pluginURL + '?' + urllib.parse.urlencode(params)
    return url

def getActionURL(action, params = {}):
    params['action'] = action
    url = pluginURL + '?' + urllib.parse.urlencode(params)
    return url
    
def getKWArguments(argv):
    if not argv:
        return {}
    if argv.startswith('?'):
        argv = argv[1:]
    #log('argv is now ' + argv)
    #args = urlparse.parse.parse_qs(argv)
    args = urllib.parse.parse_qs(argv)
    #log(args)
    newArgs = {}
    for key, val in args.items():
        #log('key=' + key)
        if len(val) == 1:
            newArgs[key] = val[0]
        else:
            newArgs[key] = val
    return newArgs

def message(header, line1, line2=None, line3=None):
    dialog = xbmcgui.Dialog()
    msg = line1
    if line2:
        msg += '\n' + line2
    if line3:
        msg += '\n' + line3
    dialog.ok(header, msg)

def formatDate(date):
    # assumes YYYY-MM-DD
    if not date:
        return ''
    date = date.split('-')
    fmt = resolve_enum_label('dateFormat') or plugin.getSetting('dateFormat')
    if fmt == 'M/D/Y':
        return date[1] + '/' + date[2] + '/' + date[0]
    elif fmt == 'D/M/Y':
        return date[2] + '/' + date[1] + '/' + date[0]
    else:
        return '?'

def formatTime(time, ampm = None):
    # assumes 'HH:MM' or 'HH:MM', 'AM'
    time = time.split(':')
    time[0] = int(time[0])
    if not ampm:
        if time[0] > 12:
            ampm = 'PM'
            time[0] = time[0] - 12
        else:
            ampm = 'AM'
            if time[0] == 0:
                time[0] = 12
    time[0] = str(time[0])
    fmt = resolve_enum_label('timeFormat') or plugin.getSetting('timeFormat')
    if fmt == 'AM/PM':
        return time[0] + ':' + time[1] + ' ' + ampm
    elif fmt == '24 Hour':
        # if we converted to 12-hour above, convert back to 24-hour
        try:
            h = int(time[0])
            if ampm == 'PM' and h < 12:
                h += 12
            if ampm == 'AM' and h == 12:
                h = 0
            return str(h).zfill(2) + ':' + time[1]
        except Exception:
            return '?'
    else:
        return '?'
        
def formatDateTime(dateTime):
    # assumes YYYY-MM-DD HH:MM
    dateTime = dateTime.split(' ')
    date = formatDate(dateTime[0])
    time = formatTime(dateTime[1])
    return date + ', ' + time

def formatEpisodeName(show):
    out = show['show_name'] + ' - ' + str(show['season']) + 'x' + ('%02d' % show['episode'])
    if 'ep_name' in show:
        out = out + ' - ' + show['ep_name']
    return out


def strip_html(text):
    """Remove simple HTML tags from a string."""
    try:
        return re.sub(r'<[^>]+>', '', text or '').strip()
    except Exception:
        return text or ''

def isInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

pluginURL = sys.argv[0]
if pluginURL.endswith('.py'):
    pluginId = None
    pluginArgs = sys.argv[1:]
else:
    pluginId = int(sys.argv[1])
    pluginArgs = getKWArguments(sys.argv[2])
    
api = sickrage.API()
iconDir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'icons')

log(sys.argv)
#log('iconDir: ' + iconDir)
#log('pluginURL: ' + pluginURL)
#log('pluginId: ' + str(pluginId))
log(pluginArgs)


# Central enum choices mapping (kept in-sync with resources/settings.xml)
ENUM_CHOICES = {
    'dateFormat': ['M/D/Y', 'D/M/Y'],
    'timeFormat': ['AM/PM', '24 Hour'],
    'rec_source': ['TVmaze', 'Episodate', 'Trakt', 'TMDb', 'IMDb', 'Both', 'All'],
    'rec_pages': ['3', '5', '8', '10'],
}


def resolve_enum_label(key):
    """Return the human-readable label for an enum-style setting.
    Handles both numeric indices stored by Kodi and legacy label strings.
    """
    try:
        raw = plugin.getSetting(key)
    except Exception:
        raw = None
    if raw is None:
        return None
    raw = str(raw).strip()
    opts = ENUM_CHOICES.get(key)
    if not opts:
        return raw
    # If stored as index
    if raw.isdigit():
        try:
            idx = int(raw)
            if 0 <= idx < len(opts):
                return opts[idx]
        except Exception:
            pass
    # If stored as label
    if raw in opts:
        return raw
    # Fallback: unknown value, return as-is
    return raw


def resolve_enum_index(key):
    """Return a numeric index (string) for an enum-style setting.
    If the stored value is a label, converts to index; if already numeric, returns it.
    """
    try:
        raw = plugin.getSetting(key)
    except Exception:
        raw = None
    if raw is None:
        return None
    raw = str(raw).strip()
    opts = ENUM_CHOICES.get(key)
    if not opts:
        return raw
    if raw.isdigit():
        return raw
    if raw in opts:
        try:
            return str(opts.index(raw))
        except Exception:
            return raw
    return raw


def _addon_data_dir():
    try:
        # Kodi 19+ uses xbmcvfs.translatePath; xbmc.translatePath was removed in Kodi 21.
        import xbmcvfs
        p = xbmcvfs.translatePath('special://profile/addon_data/plugin.program.sickrage')
    except Exception:
        try:
            p = xbmc.translatePath('special://profile/addon_data/plugin.program.sickrage')
        except Exception:
            p = os.path.join(os.path.expanduser('~'), '.kodi', 'userdata', 'addon_data', 'plugin.program.sickrage')
    return os.path.abspath(p)


def read_addon_data(filename, default=None):
    """Read JSON data from addon_data; returns `default` on error."""
    path = os.path.join(_addon_data_dir(), filename)
    try:
        if not os.path.exists(path):
            return default
        with open(path, 'r', encoding='utf-8') as fp:
            import json
            return json.load(fp)
    except Exception:
        return default


def write_addon_data(filename, data):
    """Write JSON-serialisable data to addon_data; returns True on success."""
    path = os.path.join(_addon_data_dir(), filename)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fp:
            import json
            json.dump(data, fp)
        return True
    except Exception as e:
        log('write_addon_data failed: %s' % repr(e))
        return False


def set_video_info(li, **kwargs):
    """Populate a ListItem's info tags and art from provided metadata.
    Accepts keys: name, summary, rating, premiered, year, network, genres,
    status, directors, runtime, language, official, imdb, image
    """
    try:
        name = kwargs.get('name') or ''
        summary = kwargs.get('summary') or ''
        rating = kwargs.get('rating') or 0
        premiered = kwargs.get('premiered') or ''
        year = kwargs.get('year') or (premiered[:4] if premiered else 0)
        network = kwargs.get('network') or ''
        genres = kwargs.get('genres') or []
        status = kwargs.get('status') or ''
        directors = kwargs.get('directors') or None
        runtime = kwargs.get('runtime') or None
        language = kwargs.get('language') or None
        official = kwargs.get('official') or None
        imdb = kwargs.get('imdb') or None
        image = kwargs.get('image') or ''

        if image:
            try:
                # Cache remote images (posters/fanart) for Kodi to load locally
                cached = maybe_cache_image(image, subdir='poster_cache') or image
                li.setArt({'icon': cached, 'thumb': cached, 'poster': cached})
            except Exception:
                pass

        try:
            tag = li.getVideoInfoTag()
            if name:
                tag.setTitle(name)
            if summary:
                tag.setPlot(summary)
                tag.setPlotOutline(summary[:200])
            if rating:
                tag.setRating(float(rating))
            if premiered:
                try:
                    tag.setFirstAired(premiered)
                except Exception:
                    pass
            if year:
                try:
                    tag.setYear(int(year))
                except Exception:
                    pass
            if network:
                try:
                    tag.setStudios([network])
                except Exception:
                    pass
            if genres:
                try:
                    tag.setGenres(genres if isinstance(genres, list) else [genres])
                except Exception:
                    pass
            if status:
                try:
                    tag.setTvShowStatus(status)
                except Exception:
                    pass
            if directors:
                try:
                    tag.setDirector(directors if isinstance(directors, list) else [directors])
                except Exception:
                    pass
            # fallback to setInfo for older builds
        except Exception:
            li.setInfo('video', {
                'title': name,
                'plot': summary,
                'rating': float(rating) if rating else 0.0,
                'premiered': premiered,
                'year': year,
                'studio': network,
                'genre': ', '.join(genres) if genres else '',
                'status': status,
                'director': ', '.join(directors) if directors else '',
            })
    except Exception:
        # Never raise from UI helper
        return


def get_episode_file(showId, season, episode):
    """Best-effort: try to resolve a local file path for an episode from SickRage data.
    Returns a filesystem path string or None."""
    try:
        eps = api.getSeasons(showId, {'season': season})
        ep = eps.get(str(episode)) if isinstance(eps, dict) else None
        if not ep:
            return None
        # common keys that may contain path
        candidates = [
            ep.get('location'), ep.get('file'), ep.get('path'), ep.get('filename'),
            ep.get('full_path'), ep.get('absolute_path'), ep.get('episode_file')
        ]
        # some APIs return a list under 'files'
        files = ep.get('files') or ep.get('file_list') or None
        if files and isinstance(files, list):
            for f in files:
                if isinstance(f, dict):
                    p = f.get('path') or f.get('filename') or f.get('full_path')
                else:
                    p = f
                if p:
                    candidates.append(p)
        for p in candidates:
            if not p:
                continue
            try:
                # path may be URL; prioritize local files
                if p.startswith('file://'):
                    p2 = p[7:]
                else:
                    p2 = p
                if os.path.exists(p2):
                    return p2
            except Exception:
                continue
    except Exception:
        return None
    return None


def _kodi_library_episode_file(showId, season, episode):
    """Find a matching episode file in Kodi's own video library by TVDB id or show name."""
    import json
    try:
        show_meta = api.getShow(showId)
        tvdb_id = str(show_meta.get('tvdbid') or showId)
        show_name = show_meta.get('show_name', '')
    except Exception:
        tvdb_id = str(showId)
        show_name = ''

    try:
        shows_query = {
            'jsonrpc': '2.0',
            'method': 'VideoLibrary.GetTVShows',
            'params': {'properties': ['title', 'uniqueid', 'imdbnumber']},
            'id': 1
        }
        resp = xbmc.executeJSONRPC(json.dumps(shows_query))
        shows_result = json.loads(resp)
        tvshows = shows_result.get('result', {}).get('tvshows', [])
        target_showid = None
        for show in tvshows:
            if show_name and show.get('title') == show_name:
                target_showid = show.get('tvshowid')
                break
            uids = show.get('uniqueid') or {}
            if isinstance(uids, dict) and uids.get('tvdb') == tvdb_id:
                target_showid = show.get('tvshowid')
                break
            if str(show.get('imdbnumber', '')) == tvdb_id:
                target_showid = show.get('tvshowid')
                break
        if target_showid is None:
            return None

        eps_query = {
            'jsonrpc': '2.0',
            'method': 'VideoLibrary.GetEpisodes',
            'params': {
                'tvshowid': target_showid,
                'season': int(season),
                'properties': ['file', 'episode']
            },
            'id': 1
        }
        resp = xbmc.executeJSONRPC(json.dumps(eps_query))
        eps_result = json.loads(resp)
        episodes = eps_result.get('result', {}).get('episodes', [])
        for ep in episodes:
            if int(ep.get('episode', -1)) == int(episode):
                return ep.get('file')
    except Exception as e:
        log('kodi_library_episode_file failed: %s' % repr(e))
    return None


def play_episode(showId, season, episode):
    """Attempt to play the episode file using Kodi player.
    Falls back to Kodi's video library, then opens the TV Shows window.
    Returns True if playback or navigation was started."""
    try:
        path = get_episode_file(showId, season, episode)
        if not path:
            path = _kodi_library_episode_file(showId, season, episode)
        if path:
            xbmc.Player().play(path)
            return True
    except Exception as e:
        log('play_episode playback failed: %s' % repr(e))

    # Nothing to play — open Kodi's TV Shows library so the user can play it there
    try:
        xbmc.executebuiltin('ActivateWindow(Videos,TVShowTitles,return)')
        return True
    except Exception:
        return False


def get_latest_downloaded(showId):
    """Return (season, episode) for the most-recent downloaded episode for a show, or None."""
    try:
        # get seasons list
        seasons = api.getSeasonList(showId)
        # seasons may be a list or dict; build numeric list
        s_list = []
        if isinstance(seasons, dict):
            for k in seasons.keys():
                try:
                    s_list.append(int(k))
                except Exception:
                    continue
        elif isinstance(seasons, list):
            for s in seasons:
                try:
                    s_list.append(int(s))
                except Exception:
                    continue
        s_list = sorted([s for s in s_list if s is not None], reverse=True)
        for s in s_list:
            eps = api.getSeasons(showId, {'season': s})
            # eps expected to be dict keyed by episode number
            if not isinstance(eps, dict):
                continue
            # iterate episodes in reverse to find latest
            for en in sorted(eps.keys(), key=lambda x: int(x), reverse=True):
                ep = eps.get(en)
                if not ep:
                    continue
                st = ep.get('status') or ep.get('status_text') or ''
                if isinstance(st, str) and st.lower() == 'downloaded' or st == 'Downloaded':
                    return (s, int(en))
        return None
    except Exception:
        return None


# Jackett/provider UI removed; related helpers were deleted to avoid stale settings usage.


def migrate_legacy_settings():
    """Safely migrate legacy/malformed settings stored as labels to
    numeric indices for enum-type settings. This is defensive and will
    back up the userdata settings.xml before writing.
    """
    try:
        addon_data = xbmc.translatePath('special://profile/addon_data/plugin.program.sickrage')
    except Exception:
        addon_data = os.path.join(xbmc.translatePath('special://profile'), 'addon_data', 'plugin.program.sickrage')

    settings_path = os.path.join(addon_data, 'settings.xml')
    # Use the central enum choices mapping
    enum_choices = ENUM_CHOICES

    def _map_value(key, raw):
        if raw is None:
            return None
        raw = str(raw).strip()
        opts = enum_choices.get(key)
        # If the raw value matches a known label (even if numeric), return its index
        if opts and raw in opts:
            try:
                return str(opts.index(raw))
            except Exception:
                pass
        # If it's a numeric string that doesn't match a label, assume it's already an index
        if raw.isdigit():
            return raw
        if not opts:
            return raw
        try:
            idx = opts.index(raw)
            return str(idx)
        except ValueError:
            return None

    # First, try to normalize via the addon API (preferred)
    changed = False
    for k in enum_choices.keys():
        try:
            cur = plugin.getSetting(k)
        except Exception:
            cur = None
        mapped = _map_value(k, cur)
        if mapped is not None and mapped != cur:
            try:
                plugin.setSetting(k, mapped)
                log('migrate_legacy_settings: set %s -> %s via API' % (k, mapped))
                changed = True
            except Exception as e:
                log('migrate_legacy_settings: failed setSetting %s: %s' % (k, repr(e)))

    # If API route didn't change values (or values unreadable), try editing userdata settings.xml
    if os.path.exists(settings_path):
        try:
            tree = ET.parse(settings_path)
            root = tree.getroot()
        except Exception as e:
            log('migrate_legacy_settings: failed parse %s: %s' % (settings_path, repr(e)))
            return changed

        # Backup original
        try:
            backup = settings_path + '.bak'
            shutil.copy2(settings_path, backup)
            log('migrate_legacy_settings: backed up %s -> %s' % (settings_path, backup))
        except Exception as e:
            log('migrate_legacy_settings: backup failed: %s' % repr(e))

        updated = False
        for s in root.findall('.//setting'):
            sid = s.get('id') or s.get('name')
            if not sid:
                continue
            if sid in enum_choices:
                # value might be in text or attribute
                raw = s.text if s.text and s.text.strip() else s.get('value') or s.get('default')
                mapped = _map_value(sid, raw)
                if mapped is not None and (s.text or '').strip() != mapped:
                    s.text = mapped
                    # remove malformed default attribute if present
                    if 'default' in s.attrib:
                        try:
                            del s.attrib['default']
                        except Exception:
                            pass
                    updated = True
                    log('migrate_legacy_settings: updated %s -> %s in XML' % (sid, mapped))

        if updated:
            try:
                # Write atomically to avoid truncation/corruption on device
                tmp_path = settings_path + '.tmp'
                tree.write(tmp_path, encoding='utf-8', xml_declaration=True)
                # validate written XML by re-parsing
                try:
                    ET.parse(tmp_path)
                except Exception as e:
                    log('migrate_legacy_settings: validation failed: %s' % repr(e))
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
                    return changed
                # replace original
                try:
                    shutil.move(tmp_path, settings_path)
                except Exception:
                    # fallback to copy
                    shutil.copy2(tmp_path, settings_path)
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
                log('migrate_legacy_settings: wrote sanitized settings.xml')
                # write marker so we don't repeatedly mutate settings
                try:
                    marker = os.path.join(addon_data, '.migration_done')
                    with open(marker, 'w', encoding='utf-8') as mf:
                        mf.write(str(int(__import__('time').time())))
                except Exception:
                    pass
                # Attempt to notify Kodi to reload settings (best-effort)
                try:
                    xbmc.executebuiltin('Notification(SickRage,migration completed,2000)')
                except Exception:
                    pass
                return True
            except Exception as e:
                log('migrate_legacy_settings: write failed: %s' % repr(e))
                return changed

    return changed


# NOTE: do NOT run migration at import time — call `migrate_legacy_settings()`
# explicitly from a safe lifecycle point (for example via the migration UI)
# to avoid using xbmc APIs during addon import where they may be unavailable.