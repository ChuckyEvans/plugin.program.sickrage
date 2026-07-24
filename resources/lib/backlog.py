import xbmcplugin
import xbmcgui
import urllib
import re

import resources.lib.util as util

def menu():
    shows = util.api.getBacklog()
    shows = sorted(shows, key = lambda show: re.sub(r'^(?i)(the)\s+', '', show['show_name']))

    for show in shows:
        url = util.getShowURL(show['indexerid'])
        for ep in show['episodes']:
            ep['show_name'] = show['show_name']
            listItem = xbmcgui.ListItem(
                label = util.formatEpisodeName(ep),
                iconImage = util.getIcon('wanted' if ep['status'] == 3 else 'qual')
            )
            # populate metadata for consistent display
            poster = util.api.getShowPoster(show['indexerid']) if show.get('indexerid') else ''
            try:
                try:
                    _poster = util.maybe_cache_image(poster, subdir='poster_cache') or util.getIcon('wanted')
                except Exception:
                    _poster = poster or util.getIcon('wanted')
                listItem.setArt({'icon': _poster})
            except Exception:
                pass
            util.set_video_info(listItem, name=util.formatEpisodeName(ep), summary=ep.get('overview',''), network=show.get('network',''), image=poster)
            listItem.addContextMenuItems([
                ('Refresh list', util.getContextCommand('refresh'))
            ], True)
            xbmcplugin.addDirectoryItem(
                handle = util.pluginId,
                url = url,
                listitem = listItem,
                isFolder = True
            )

    xbmcplugin.endOfDirectory(util.pluginId)        

