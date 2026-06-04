import resources.lib.util as util

try:
    if 'vf' in util.pluginArgs:
        vf = util.pluginArgs['vf']
        if vf == 'shows':
            import resources.lib.shows as shows
            shows.menu()
        elif vf == 'recommended':
            import resources.lib.recommended as recommended
            recommended.menu()
        elif vf == 'recommended_detail':
            import resources.lib.recommended as recommended
            recommended.detail()
        elif vf == 'upcoming':
            import resources.lib.upcoming as upcoming
            upcoming.menu()
        elif vf == 'history':
            import resources.lib.history as history
            history.menu()
        elif vf == 'backlog':
            import resources.lib.backlog as backlog
            backlog.menu()
        elif vf == 'failed':
            import resources.lib.failed as failed
            failed.menu()
        elif vf == 'seasons':
            import resources.lib.seasons as seasons
            seasons.menu()
        elif vf == 'episodes':
            import resources.lib.episodes as episodes
            episodes.menu()
        elif vf == 'shows_ended':
            # Legacy bookmark alias — redirect to ended filter
            import resources.lib.shows as shows
            util.pluginArgs = {'vf': 'shows', 'filter': 'ended'}
            shows.menu()
        else:
            util.log('invalid folder "' + vf + '"')
            import resources.lib.main as main
            main.menu()
    elif 'action' in util.pluginArgs:
        action = util.pluginArgs['action']
        if action == 'showAdd':
            import resources.lib.showAdd as showAdd
            showAdd.action()
        elif action == 'showAddDirect':
            import resources.lib.showAdd as showAdd
            showAdd.directAction()
        elif action == 'recommendedInfo':
            import resources.lib.recommended as recommended
            recommended.show_info_dialog(
                util.pluginArgs.get('tvmazeid', ''),
                util.pluginArgs.get('tvdbid', ''),
                util.pluginArgs.get('name', 'Unknown Show')
            )
        elif action == 'openSettings':
            util.plugin.openSettings()
        elif action == 'refreshRecommended':
            import resources.lib.recommended as recommended
            recommended.clear_cache()
            import xbmcgui
            xbmcgui.Dialog().notification('SickRage', 'Catalogue cache cleared — reopen Recommended to refresh.', xbmcgui.NOTIFICATION_INFO, 3000)
        elif action == 'forceSearch':
            import xbmcgui
            dialog = xbmcgui.Dialog()
            if dialog.yesno('Force Episode Search', 'Start a forced search for missing episodes now?'):
                util.api.doForceSearch()
                util.message('Force Search', 'SickRage is now searching for missing episodes.')
        else:
            util.log('invalid action "' + action + '"')
    else:
        import resources.lib.main as main
        main.menu()

except IOError as ioe:
    util.message('Error', '%s' % ioe)
except Exception as e:
    import traceback, xbmc
    xbmc.log('Sickrage addon error: ' + traceback.format_exc(), xbmc.LOGERROR)
    util.message('SickRage Error', str(e))
    
