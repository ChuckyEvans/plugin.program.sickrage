import urllib
import urllib.request as urllibRequest
import base64
import socket
import json
import re

import resources.lib.util as util

socket.setdefaulttimeout(40)

class API:

    def getShowBanner(self, id):
        # Prefer external banner URL from the API (no auth) when available.
        try:
            show = self.getShow(id)
            try:
                util.log('API show fields for %s: poster=%s, image=%s, banner=%s' % (id, repr(show.get('poster')), repr(show.get('image')), repr(show.get('banner'))))
            except Exception:
                pass
            banner = show.get('banner') or show.get('show_banner') or show.get('poster') or ''
            if banner and isinstance(banner, str) and banner.startswith('http'):
                base = (util.plugin.getSetting('url') or '').strip().rstrip('/')
                if not base or not banner.startswith(base):
                    try:
                        return util.cache_image_url(banner, subdir='poster_cache', name='%s_banner' % id)
                    except Exception:
                        pass
        except Exception:
            pass
        return util.cache_poster_url(id, 'banner')

    def getShowPoster(self, id):
        # Prefer external poster URL from the API (no auth) when available.
        try:
            show = self.getShow(id)
            try:
                util.log('API show fields for %s: poster=%s, image=%s, banner=%s' % (id, repr(show.get('poster')), repr(show.get('image')), repr(show.get('banner'))))
            except Exception:
                pass
            poster = show.get('poster') or show.get('image') or ''
            if poster and isinstance(poster, str) and poster.startswith('http'):
                base = (util.plugin.getSetting('url') or '').strip().rstrip('/')
                if not base or not poster.startswith(base):
                    try:
                        return util.cache_image_url(poster, subdir='poster_cache', name='%s_poster' % id)
                    except Exception:
                        pass
            # Fallback: try TVmaze direct search to get a poster URL
            try:
                name = show.get('show_name') or show.get('name') or ''
                if name:
                    results = self.doSearchTVMazeDirect(name)
                    if results:
                        tm = results[0]
                        tm_poster = tm.get('poster')
                        if tm_poster:
                            util.log('Using TVmaze poster for %s: %s' % (id, tm_poster))
                            return util.cache_image_url(tm_poster, subdir='poster_cache', name='%s_tm_poster' % id)
            except Exception:
                pass
        except Exception:
            pass
        return util.cache_poster_url(id, 'poster')

    def getShowPosterThumbnail(self, id):
        # Try to use an external thumbnail if available via the API.
        try:
            show = self.getShow(id)
            try:
                util.log('API show fields for %s: poster_thumb=%s, thumbnail=%s, poster=%s' % (id, repr(show.get('poster_thumb')), repr(show.get('thumbnail')), repr(show.get('poster'))))
            except Exception:
                pass
            thumb = show.get('poster_thumb') or show.get('thumbnail') or show.get('poster') or ''
            if thumb and isinstance(thumb, str) and thumb.startswith('http'):
                base = (util.plugin.getSetting('url') or '').strip().rstrip('/')
                if not base or not thumb.startswith(base):
                    try:
                        return util.cache_image_url(thumb, subdir='poster_cache', name='%s_poster_thumb' % id)
                    except Exception:
                        pass
        except Exception:
            pass
        return util.cache_poster_url(id, 'poster_thumb')
    

    def request(self, cmd, params = {}):
        params['cmd'] = cmd
        base = (util.plugin.getSetting('url') or '').strip()
        key = (util.plugin.getSetting('key') or '').strip()
        if not base:
            raise Exception('SickRage base URL is not configured in addon settings.')
        if not re.match(r'^https?://', base):
            raise Exception('SickRage base URL must start with http:// or https://')
        if not key:
            raise Exception('SickRage API key is not configured in addon settings.')
        # normalize base to avoid duplicate slashes
        base = base.rstrip('/') + '/'
        url = base + 'api/' + key + '/?' + urllib.parse.urlencode(params)
        util.log('API: ' + url)
        req = urllibRequest.Request(url)
        user = util.plugin.getSetting('user')
        password = util.plugin.getSetting('password')
        if user and password:
            auth = base64.b64encode('{}:{}'.format(user, password).encode('utf-8')).decode('ascii')
            req.add_header("Authorization", "Basic %s" % auth)        
        try:
            result = json.load(urllibRequest.urlopen(req))
        except urllib.error.URLError as e:
            raise Exception('Cannot reach SickRage: ' + str(e.reason))
        except socket.timeout:
            raise Exception('Connection to SickRage timed out ({}s).'.format(socket.getdefaulttimeout()))
        except Exception as e:
            raise Exception('Request failed: ' + str(e))
        if result['result'] == 'denied':
            raise Exception('Access denied — check your API key in addon settings.')
        if result['result'] != 'success':
            msg = result.get('message') or result.get('result', 'Unknown error')
            util.log('API error: ' + str(result))
            raise Exception(msg)
        return result
    
    def getShow(self, id):
        result = self.request('show', {'tvdbid': id})
        return result['data']

    def showExists(self, id):
        try:
            self.getShow(id)
            return True
        except Exception:
            return False

    def getSeasons(self, id, params = {}):
        params['tvdbid'] = id
        result = self.request('show.seasons', params)
        return result['data']

    def getSeasonList(self, id, params = {}):
        params['tvdbid'] = id
        result = self.request('show.seasonlist', params)
        return result['data']

    def setShowPause(self, id, pause):
        return self.request('show.pause', {'tvdbid': id, 'pause': 1 if pause else 0})
    
    def doShowDelete(self, id):
        return self.request('show.delete', {'tvdbid': id})
        
    def getShows(self, params = {}):
        result = self.request('shows', params)
        return result['data']

    def getFuture(self, params = {}):
        result = self.request('future', params)
        return result['data']
        
    def getHistory(self, params = {}):
        result = self.request('history', params)
        return result['data']
        
    def getBacklog(self, params = {}):
        result = self.request('backlog', params)
        return result['data']
        
    def getFailed(self, params = {}):
        result = self.request('failed', params)
        return result['data']
        
    def doForceSearch(self):
        return self.request('sb.forcesearch')
    
    def doSearch(self, name, indexer):
        if indexer == 0:
            result = self.request('sb.searchindexers', {'name': name})
        elif indexer == 1:
            result = self.request('sb.searchtvdb', {'name': name})
        elif indexer == 2:
            result = self.request('sb.searchtvrage', {'name': name})
        else:
            return []
        data = result['data']
        if isinstance(data, list):
            return data
        return data.get('results', [])

    def doSearchTVMazeDirect(self, name):
        """Search TVmaze API directly (no SickRage needed). Returns results in same
        shape as sb.searchtvdb — each item has 'tvdbid', 'name', 'first_aired', etc.
        Falls back gracefully; returns [] on any error."""
        import urllib.request as _req
        import urllib.parse as _parse
        import json as _json
        try:
            url = 'https://api.tvmaze.com/search/shows?q=' + _parse.quote(name)
            raw = _req.urlopen(url, timeout=10).read().decode('utf-8')
            results = []
            for entry in _json.loads(raw):
                show = entry.get('show') or {}
                tvdb_id = (show.get('externals') or {}).get('thetvdb')
                if not tvdb_id:
                    continue  # skip shows with no TVDB crosslink
                results.append({
                    'tvdbid':     tvdb_id,
                    'indexerid':  tvdb_id,
                    'indexer':    1,
                    'name':       show.get('name', ''),
                    'first_aired': show.get('premiered') or '',
                    'network':    ((show.get('network') or {}).get('name')
                                   or (show.get('webChannel') or {}).get('name', '')),
                    'overview':   re.sub(r'<[^>]+>', '', show.get('summary') or ''),
                    'genres':     show.get('genres') or [],
                    'status':     show.get('status') or '',
                    'poster':     (show.get('image') or {}).get('medium', ''),
                })
            return results
        except Exception as e:
            raise Exception('TVmaze search failed: ' + str(e))
        
    def getRootDirs(self):
        result = self.request('sb.getrootdirs')
        return result['data']

    def getDefaults(self):
        result = self.request('sb.getdefaults')
        return result['data']

    def getIndexers(self):
        """Return a list of configured indexers.
        Try several SickRage API endpoints for compatibility, and fall back
        to addon cached data if available. Returns an empty list on failure.
        """
        candidates = ['sb.getindexers', 'indexers', 'sb.searchindexers']
        for cmd in candidates:
            try:
                if cmd == 'sb.searchindexers':
                    # searchindexers expects a name param; empty name may return all
                    res = self.request(cmd, {'name': ''})
                else:
                    res = self.request(cmd)
                data = res.get('data') if isinstance(res, dict) else None
                if not data:
                    continue
                # If data is dict, convert to list of entries for callers
                if isinstance(data, dict):
                    entries = []
                    for k, v in data.items():
                        title = v.get('title') or v.get('name') or k
                        enabled = bool(v.get('enabled') or v.get('configured'))
                        entries.append({'name': title, 'enabled': enabled, 'id': k})
                    return entries
                # If already list-shaped, try to normalize minimal fields
                if isinstance(data, list):
                    entries = []
                    for v in data:
                        title = v.get('title') or v.get('name') or v.get('provider') or v.get('id') or 'Unknown'
                        enabled = bool(v.get('enabled', True))
                        pid = v.get('id') or v.get('provider') or title
                        entries.append({'name': title, 'enabled': enabled, 'id': pid})
                    return entries
            except Exception as e:
                util.log('getIndexers: %s failed: %s' % (cmd, repr(e)))
                continue

        # fallback: use cached Jackett indexers stored in addon_data
        try:
            cached = util.read_addon_data('jackett_indexers.json', []) or []
            # convert cached shape to expected list (title -> name)
            out = []
            for e in cached:
                out.append({'name': e.get('title') or e.get('name') or 'Unknown', 'enabled': bool(e.get('enabled')), 'id': e.get('id')})
            return out
        except Exception as e:
            util.log('getIndexers: fallback read failed: %s' % repr(e))
            return []
        
    def doAddNewShow(self, id, indexer, location, status, flattenFolders, anime, sceneNumbered, quality):
        return self.request('show.addnew', {
            'indexerid': id,
            indexer + 'id': id,
            'location': location,
            'status': status,
            'flatten_folders': 0 if flattenFolders else 1,
            'anime': 1 if anime else 0,
            'scene': 1 if sceneNumbered else 0,
            'initial': quality
        })

    def doUpdateShow(self, id):
        return self.request('show.update', {'tvdbid': id})

    def doSetShowQuality(self, id, initial, archive=''):
        params = {'tvdbid': id, 'initial': initial}
        if archive:
            params['archive'] = archive
        return self.request('show.setquality', params)
        
    def doEpisodeSetStatus(self, id, season, episode, status):
        params = {
            'indexerid': id,
            'season': season,
            'status': status
        }
        if episode is not None:
            params['episode'] = episode
        return self.request('episode.setstatus', params)

    def doEpisodeSearch(self, id, season, episode):
        return self.request('episode.search', {
            'indexerid': id,
            'season': season,
            'episode': episode
        })
        