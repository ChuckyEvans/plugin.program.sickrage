import xbmcplugin
import xbmcgui
import urllib
import re

import resources.lib.util as util

def menu():
    releases = util.api.getFailed()
    releases = sorted(releases, key = lambda release: re.sub(r'^(?i)(the)\s+', '', release['show_name']))
    
    for release in releases:
        listItem = xbmcgui.ListItem(
            label = str(release['release'])
        )
        # populate metadata
        poster = util.api.getShowPoster(release.get('indexerid') or release.get('tvdbid') or '') if release.get('indexerid') else ''
        try:
            if poster:
                try:
                    _poster = util.maybe_cache_image(poster, subdir='poster_cache') or poster
                except Exception:
                    _poster = poster
                listItem.setArt({'icon': _poster, 'thumb': _poster})
        except Exception:
            pass
        util.set_video_info(listItem, name=release.get('show_name') or release.get('release'), summary=release.get('overview',''), image=poster)
        listItem.addContextMenuItems([
            #('Delete', util.getContextCommand('failedDelete', [release['release']])),
            ('Refresh list', util.getContextCommand('refresh'))
        ], True)
        xbmcplugin.addDirectoryItem(
            handle = util.pluginId,
            url = None,
            listitem = listItem,
            isFolder = False
        )

    xbmcplugin.endOfDirectory(util.pluginId)

