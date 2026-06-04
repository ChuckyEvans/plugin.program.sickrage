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
        url = util.plugin.getSetting('url') + 'showPoster/?show=' + str(id) + '&which=banner'
        return url

    def getShowPoster(self, id):
        url = util.plugin.getSetting('url') + 'showPoster/?show=' + str(id) + '&which=poster'
        return url
    
    def getShowPosterThumbnail(self, id):
        url = util.plugin.getSetting('url') + 'showPoster/?show=' + str(id) + '&which=poster_thumb'
        return url
    

    def request(self, cmd, params = {}):
        params['cmd'] = cmd
        url = util.plugin.getSetting('url') + 'api/' + util.plugin.getSetting('key') + '/?' + urllib.parse.urlencode(params)
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
        return self.request('episode.setstatus', {
            'indexerid': id,
            'season': season,
            'episode': episode,
            'status': status
        })
        