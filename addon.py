import resources.lib.util as util
import xbmc
import os

# One-time safe migration: sanitize userdata `settings.xml` if needed.
# Create a marker file in addon_data to avoid repeating the migration.
try:
    try:
        addon_data = xbmc.translatePath('special://profile/addon_data/plugin.program.sickrage')
    except Exception:
        addon_data = os.path.join(xbmc.translatePath('special://profile'), 'addon_data', 'plugin.program.sickrage')
    marker = os.path.join(addon_data, '.migration_done')
    if not os.path.exists(marker):
        try:
            migrated = util.migrate_legacy_settings()
            # ensure addon_data exists and touch marker if migration occurred
            try:
                os.makedirs(addon_data, exist_ok=True)
                if migrated:
                    with open(marker, 'w') as f:
                        f.write('1')
                    xbmc.log('Sickrage addon: migration completed (marker created)', xbmc.LOGINFO)
            except Exception as e:
                xbmc.log('Sickrage addon: failed to write migration marker: %s' % repr(e), xbmc.LOGERROR)
        except Exception as e:
            xbmc.log('Sickrage addon: migration attempt failed: %s' % repr(e), xbmc.LOGERROR)
except Exception:
    # Best-effort only; do not prevent addon startup
    pass

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
        # providers/jackett UI removed
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
        elif action == 'playEpisode':
            try:
                showId = util.pluginArgs.get('id')
                season = util.pluginArgs.get('season')
                episode = util.pluginArgs.get('episode')
                if showId and season and episode:
                    ok = util.play_episode(showId, int(season), int(episode))
                    if not ok:
                        util.message('Playback', 'Episode file not found or cannot be played.')
                else:
                    util.message('Playback', 'Missing parameters for playEpisode')
            except Exception as e:
                util.message('Playback Error', str(e))
        elif action == 'showStats':
            try:
                import resources.lib.stats as stats
                stats.show_stats(util.pluginArgs.get('tvdbid') or util.pluginArgs.get('id'))
            except Exception as e:
                util.message('Stats', 'Failed to show stats', str(e))
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
        elif action == 'showDelete':
            try:
                import resources.lib.showDelete as showDelete
                showDelete.action()
            except Exception as e:
                util.message('Delete Show', 'Failed to delete show', str(e))
        elif action == 'showPauseToggle':
            try:
                import resources.lib.showPauseToggle as showPauseToggle
                showPauseToggle.action()
            except Exception as e:
                util.message('Pause Toggle', 'Failed to pause/unpause show', str(e))
        elif action == 'showStatus':
            try:
                import resources.lib.showStatus as showStatus
                showStatus.action()
            except Exception as e:
                util.message('Show Status', 'Failed to set show status', str(e))
        elif action == 'showSettings':
            try:
                import resources.lib.showSettings as showSettings
                showSettings.action()
            except Exception as e:
                util.message('Show Settings', 'Failed to open show settings', str(e))
        elif action == 'seasonStatus':
            try:
                import resources.lib.seasonStatus as seasonStatus
                seasonStatus.action()
            except Exception as e:
                util.message('Season Status', 'Failed to set season status', str(e))
        elif action == 'episodeStatus':
            try:
                import resources.lib.episodeStatus as episodeStatus
                episodeStatus.action()
            except Exception as e:
                util.message('Episode Status', 'Failed to set episode status', str(e))
        elif action == 'episodeSearch':
            try:
                showId = util.pluginArgs.get('id')
                season = util.pluginArgs.get('season')
                episode = util.pluginArgs.get('episode')
                if showId and season is not None and episode is not None:
                    result = util.api.doEpisodeSearch(showId, int(season), int(episode))
                    util.message('Manual Search', 'Search returned ' + result.get('result', 'unknown'))
                else:
                    util.message('Manual Search', 'Missing parameters for episode search')
            except Exception as e:
                util.message('Manual Search', 'Failed to start manual search', str(e))
        # providers actions removed
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
    
