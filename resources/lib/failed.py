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

