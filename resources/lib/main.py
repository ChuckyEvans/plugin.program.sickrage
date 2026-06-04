import xbmcplugin
import xbmcgui
import urllib

import resources.lib.util as util

def menu():

    def add_item(label, vf=None, action=None, icon=None, is_folder=True, params={}):
            if vf:
                p = dict(params)
                p['vf'] = vf
                url = util.pluginURL + '?' + urllib.parse.urlencode(p)
            elif action:
                url = util.getActionURL(action, dict(params))
            else:
                url = util.pluginURL
            li = xbmcgui.ListItem(label=label)
            if icon:
                li.setArt({'icon': util.getIcon(icon), 'thumb': util.getIcon(icon)})
            xbmcplugin.addDirectoryItem(
                handle=util.pluginId, url=url, listitem=li, isFolder=is_folder)

    add_item('[B]Shows[/B]',         vf='shows',       icon='shows')
    add_item('[B]Recommended[/B]',   vf='recommended', icon='recommended')
    add_item('[B]Upcoming[/B]',      vf='upcoming',    icon='upcoming')
    add_item('[B]History[/B]',       vf='history',     icon='history')
    add_item('Force Episode Search', action='forceSearch', icon='wanted', is_folder=False)

    xbmcplugin.endOfDirectory(util.pluginId, cacheToDisc=False)

