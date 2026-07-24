import xbmcgui

import resources.lib.util as util


def action():
    showId = util.pluginArgs.get('id')
    if not showId:
        util.message('Show Settings', 'Missing show parameter')
        return

    try:
        show = util.api.getShow(showId)
    except Exception:
        show = {}

    # Quality options match those used when adding shows
    qualities = [
        'sdtv|sddvd',
        'hdtv|hdwebdl|hdbluray',
        'fullhdtv|fullhdwebdl|fullhdbluray',
        'hdtv|fullhdtv|hdwebdl|fullhdwebdl|hdbluray|fullhdbluray',
        'sdtv|sddvd|hdtv|fullhdtv|hdwebdl|fullhdwebdl|hdbluray|fullhdbluray|unknown'
    ]
    qualityList = ['SD', 'HD720p', 'HD1080p', 'HD', 'Any']

    # Attempt to detect current quality from show metadata
    current_quality = ''
    try:
        # API may provide 'quality' or 'initial' fields
        current_quality = show.get('quality') or '|'.join(show.get('initial') or []) or ''
    except Exception:
        current_quality = ''

    try:
        if current_quality:
            idx = qualities.index(current_quality)
            qualityList[idx] = '* ' + qualityList[idx]
    except Exception:
        pass

    dialog = xbmcgui.Dialog()
    qidx = dialog.select('Select Quality', qualityList)
    if qidx == -1:
        return

    quality = qualities[qidx]
    try:
        util.api.doSetShowQuality(showId, quality)
        xbmcgui.Dialog().notification('SickRage', 'Show settings saved', xbmcgui.NOTIFICATION_INFO, 2000)
        xbmc.executebuiltin('Container.Refresh')
    except Exception as e:
        util.message('Show Settings', 'Failed to save settings', str(e))
