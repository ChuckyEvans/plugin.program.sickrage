import xbmc
import xbmcgui

from operator import itemgetter

import resources.lib.util as util

def _handle_error(context, e):
    import traceback
    xbmc.log('Sickrage %s error: ' % context + traceback.format_exc(), xbmc.LOGERROR)
    xbmcgui.Dialog().ok('SickRage Error', str(e))

def action():
    try:
        _action()
    except Exception as e:
        _handle_error('showAdd', e)

def directAction():
    """Add a show directly from the Recommended list — TVDB ID already known, skip search."""
    try:
        tvdbid = util.pluginArgs.get('tvdbid')
        name = util.pluginArgs.get('name', 'Unknown Show')
        if not tvdbid:
            util.message('Error', 'No show ID provided.')
            return
        _addShowFromMatch({'tvdbid': int(tvdbid), 'name': name})
    except Exception as e:
        _handle_error('showAddDirect', e)

def _action():
    
    # Get the name
    
    keyboard = xbmc.Keyboard('', 'Search for...', False)
    keyboard.doModal()
    if not keyboard.isConfirmed():
        return
    searchName = keyboard.getText() 

    # Get indexer to use

    indexers      = ['TheTVDB', 'TVmaze (direct)']
    indexer_icons = ['', '']
    dialog = xbmcgui.Dialog()
    indexerIndex = dialog.select('Search Source', indexers)
    if indexerIndex == -1:
        return

    # Do the search

    if indexerIndex == 1:
        # TVmaze direct — hits api.tvmaze.com, results include tvdbid crosslink
        matches = util.api.doSearchTVMazeDirect(searchName)
    else:
        matches = util.api.doSearch(searchName, 1)  # TVDB via SickRage

    if not matches:
        util.message('Search Results', 'No matching shows found.')
        return

    matchList = []
    for show in matches:
        source = 'TVmaze' if indexerIndex == 1 else 'TheTVDB'
        matchList.append(show['name'] + ' - ' + util.formatDate(show.get('first_aired', '')) + '  [' + source + ']')
    dialog = xbmcgui.Dialog()
    matchIndex = dialog.select('Search Results', matchList)
    if matchIndex == -1:
        return
    show = matches[matchIndex]

    _addShowFromMatch(show)


def _addShowFromMatch(show):
    """Handle the add/update dialogs given a show dict with at least 'tvdbid' and 'name'."""
    dialog = xbmcgui.Dialog()

    # Check if show already exists
    showId = show.get('tvdbid') or show.get('tvrageid')
    if showId and util.api.showExists(showId):
        choice = dialog.yesno(
            'Show Already Exists',
            '[B]' + show['name'] + '[/B] is already in your SickRage library.\n\nUpdate it? You can change quality and status settings.'
        )
        if not choice:
            return

        defaults = util.api.getDefaults()

        statuses = ['wanted', 'skipped', 'archived', 'ignored']
        statusList = [('* ' if s == defaults['status'] else '') + s.title() for s in statuses]
        statusIndex = dialog.select('Episode Status', statusList)
        if statusIndex == -1:
            return
        status = statuses[statusIndex]

        qualities = [
            'sdtv|sddvd',
            'hdtv|hdwebdl|hdbluray',
            'fullhdtv|fullhdwebdl|fullhdbluray',
            'hdtv|fullhdtv|hdwebdl|fullhdwebdl|hdbluray|fullhdbluray',
            'sdtv|sddvd|hdtv|fullhdtv|hdwebdl|fullhdwebdl|hdbluray|fullhdbluray|unknown'
        ]
        qualityList = ['SD', 'HD720p', 'HD1080p', 'HD', 'Any']
        defaultQuality = '|'.join(defaults['initial'])
        try:
            qualityList[qualities.index(defaultQuality)] = '* ' + qualityList[qualities.index(defaultQuality)]
        except Exception:
            pass
        qualityIndex = dialog.select('Quality', qualityList)
        if qualityIndex == -1:
            return
        quality = qualities[qualityIndex]

        util.api.doUpdateShow(showId)
        util.api.doSetShowQuality(showId, quality)
        util.message('Show Updated', show['name'] + ' has been updated with the new settings.')
        return

    # Get the parent directory
    
    rootDirs = util.api.getRootDirs()
    if not rootDirs:
        util.message('Error', 'There are no root directories defined!')
        return

    dirs = []
    for rootDir in rootDirs:
        dirs.append(('* ' if rootDir['default'] == 1 else '') + rootDir['location'])

    dirIndex = dialog.select('Parent Folder', dirs)
    if dirIndex == -1:
        return
    location = rootDirs[dirIndex]['location']

    # Get show options
    
    defaults = util.api.getDefaults()
    
    # ... initial status
    
    statuses = ['wanted', 'skipped', 'archived', 'ignored']
    statusList = []
    for status in statuses:
        statusList.append(('* ' if status == defaults['status'] else '') + status.title())
    statusIndex = dialog.select('Initial Episode Status', statusList)
    if statusIndex == -1:
        return
    status = statuses[statusIndex]

    # ... flatten folders

    # no way for user to cancel this (looks like No/False)!
    flattenFolders = dialog.yesno('Flatten Folders', 'Flatten season folders?', 'Default: ' + 'Yes' if defaults['flatten_folders'] else 'No')

    # ... anime

    anime = dialog.yesno('Anime', 'Is this show an Anime?')
    
    # ... scene numbering

    sceneNumbered = dialog.yesno('Scene Numbering', 'Is this show scene numbered?')
    
    # ... quality
    
    qualities = [
        'sdtv|sddvd',
        'hdtv|hdwebdl|hdbluray',
        'fullhdtv|fullhdwebdl|fullhdbluray',
        'hdtv|fullhdtv|hdwebdl|fullhdwebdl|hdbluray|fullhdbluray',
        'sdtv|sddvd|hdtv|fullhdtv|hdwebdl|fullhdwebdl|hdbluray|fullhdbluray|unknown'
    ]
    qualityList = [
        'SD',
        'HD720p',
        'HD1080p',
        'HD',
        'Any'
    ]
    defaultQuality = '|'.join(defaults['initial'])
    try:
        qualityList[qualities.index(defaultQuality)] = '* ' + qualityList[qualities.index(defaultQuality)]
    except Exception:
        pass
    qualityIndex = dialog.select('Quality', qualityList)
    if qualityIndex == -1:
        return
    quality = qualities[qualityIndex]
    
    # Add the show!
    
    if 'tvdbid' in show:
        indexerid = show['tvdbid']
        indexer = 'tvdb'
    elif 'tvrageid' in show:
        indexerid = show['tvrageid']
        indexer = 'tvrage'
    else:
        indexerid = None
    try:
        util.api.doAddNewShow(indexerid, indexer, location, status, flattenFolders, anime, sceneNumbered, quality)
        util.message('Add Show', 'The show has been added.', 'It may take a moment before it appears in the list.')
        xbmc.executebuiltin('Container.Refresh')
    except Exception as e:
        if 'already exists' in str(e).lower():
            util.message('Already in Library', '[B]' + show['name'] + '[/B] is already in your SickRage library.')
        else:
            raise
        
