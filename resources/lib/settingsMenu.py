import xbmc
import xbmcgui
import xbmcplugin
import urllib.parse

import resources.lib.util as util


# Use centralized enum choices from util to avoid duplication and keep settings in sync
def _choices_for(key):
    try:
        return util.ENUM_CHOICES.get(key, [])
    except Exception:
        return []


def _add_item(label, key, icon='settings'):
    url = util.pluginURL + '?' + urllib.parse.urlencode({'action': 'editSetting', 'key': key})
    li = xbmcgui.ListItem(label=label)
    li.setArt({'icon': util.getIcon(icon), 'thumb': util.getIcon(icon)})
    xbmcplugin.addDirectoryItem(util.pluginId, url, li, isFolder=False)


def _current(key):
    try:
        val = util.plugin.getSetting(key) or ''
        # If this is a known enum, map numeric index -> label for display
        try:
            if key in _CHOICES and val.isdigit():
                idx = int(val)
                opts = _CHOICES[key]
                if 0 <= idx < len(opts):
                    val = opts[idx]
        except Exception:
            pass
        util.log('settingsMenu: current %s => %r' % (key, val))
        return val
    except Exception as e:
        util.log('settingsMenu: error reading setting %s: %s' % (key, repr(e)))
        return ''


def menu():
    try:
        util.log('settingsMenu.menu: pluginId=%r' % (util.pluginId,))
    except Exception:
        pass
    # Migration and normalization disabled to avoid breaking the native
    # addon settings dialog. Keep this location reserved for a user-triggered
    # migration in future (do not run automatically).
    try:
        # no-op
        pass
    except Exception:
        pass
    # If pluginId is not provided by Kodi, fall back to 0 to avoid crashes
    handle = util.pluginId if util.pluginId is not None else 0
    xbmcplugin.addDirectoryItem(handle, util.pluginURL, xbmcgui.ListItem(label='[COLOR gray]Edit the addon settings below[/COLOR]'), isFolder=False)
    _add_item('SickRage URL  [COLOR gray]%s[/COLOR]' % (_current('url') or 'not set'), 'url')
    _add_item('SickRage API Key  [COLOR gray]%s[/COLOR]' % ('set' if _current('key') else 'not set'), 'key')
    # Jackett/provider settings removed from UI (managed externally)
    _add_item('Username  [COLOR gray]%s[/COLOR]' % (_current('user') or 'not set'), 'user')
    _add_item('Password  [COLOR gray]%s[/COLOR]' % ('set' if _current('password') else 'not set'), 'password')
    _add_item('Date format  [COLOR gray]%s[/COLOR]' % (_current('dateFormat') or 'M/D/Y'), 'dateFormat')
    _add_item('Time format  [COLOR gray]%s[/COLOR]' % (_current('timeFormat') or 'AM/PM'), 'timeFormat')
    _add_item('Recommendation source  [COLOR gray]%s[/COLOR]' % (_current('rec_source') or 'TVmaze'), 'rec_source')
    _add_item('Recommendation pages  [COLOR gray]%s[/COLOR]' % (_current('rec_pages') or '5'), 'rec_pages')
    # Migration helper
    _add_item('Migrate legacy settings', 'migrateSettings')
    # Fallback editor entry
    _add_item('Open fallback settings editor (safe)', 'openFallbackSettings')
    try:
        xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
    except Exception:
        try:
            xbmcplugin.endOfDirectory(util.pluginId or 0, cacheToDisc=False)
        except Exception:
            util.log('settingsMenu.menu: endOfDirectory failed')


def open_settings_dialog():
    """Fallback settings editor shown from the plugin when Kodi's native
    addon settings dialog is unavailable or broken."""
    dialog = xbmcgui.Dialog()
    addon = util.plugin
    changed = False

    # Helper to read current value safely
    def _cur(k):
        try:
            return addon.getSetting(k) or ''
        except Exception:
            return ''

    # Text fields
    url = dialog.input('SickRage URL', _cur('url'))
    if url is not None:
        addon.setSetting('url', url)
        changed = True

    key = dialog.input('SickRage API Key', _cur('key'), isPassword=True)
    if key is not None:
        addon.setSetting('key', key)
        changed = True

    # Jackett/provider configuration removed from fallback editor

    # Enums: dateFormat, timeFormat, rec_source, rec_pages
    df = _cur('dateFormat') or 'M/D/Y'
    df_opt = ['M/D/Y', 'D/M/Y']
    try:
        df_opt = _choices_for('dateFormat') or df_opt
        pre = df_opt.index(df) if df in df_opt else 0
        sel = dialog.select('Date format', df_opt, preselect=pre)
        if sel >= 0:
            # store numeric index (Kodi expects indices in userdata)
            addon.setSetting('dateFormat', str(sel))
            changed = True
    except Exception:
        pass

    tf = _cur('timeFormat') or 'AM/PM'
    tf_opt = ['AM/PM', '24 Hour']
    try:
        tf_opt = _choices_for('timeFormat') or tf_opt
        pre = tf_opt.index(tf) if tf in tf_opt else 0
        sel = dialog.select('Time format', tf_opt, preselect=pre)
        if sel >= 0:
            addon.setSetting('timeFormat', str(sel))
            changed = True
    except Exception:
        pass

    rs = _cur('rec_source') or 'TVmaze'
    rs_opt = _choices_for('rec_source') or ['TVmaze', 'Episodate']
    try:
        pre = rs_opt.index(rs) if rs in rs_opt else 0
        sel = dialog.select('Recommendation source', rs_opt, preselect=pre)
        if sel >= 0:
            addon.setSetting('rec_source', str(sel))
            changed = True
    except Exception:
        pass

    rp = _cur('rec_pages') or '5'
    rp_opt = _choices_for('rec_pages') or ['3', '5', '8', '10']
    try:
        pre = rp_opt.index(rp) if rp in rp_opt else 1
        sel = dialog.select('Recommendation pages', rp_opt, preselect=pre)
        if sel >= 0:
            addon.setSetting('rec_pages', str(sel))
            changed = True
    except Exception:
        pass

    if changed:
        xbmc.executebuiltin('Container.Refresh')
        xbmcgui.Dialog().notification('SickRage', 'Settings saved', xbmcgui.NOTIFICATION_INFO, 2000)

def edit_setting(key):
    if not key:
        menu()
        return

    dialog = xbmcgui.Dialog()
    current = _current(key)

    if key in ('dateFormat', 'timeFormat', 'rec_source', 'rec_pages'):
        options = _choices_for(key) or []
        try:
            # current may be a label or numeric index; prefer numeric mapping
            if current.isdigit():
                index = int(current) if int(current) < len(options) else 0
            else:
                index = options.index(current)
        except ValueError:
            index = 0
        selected = dialog.select('Edit ' + key, options, preselect=index)
        if selected >= 0:
            # store numeric index
            util.plugin.setSetting(key, str(selected))
    # jackett settings removed
    elif key in ('key', 'jackett_key', 'password'):
        keyboard = xbmc.Keyboard(current, 'Edit ' + key, True)
        keyboard.doModal()
        if keyboard.isConfirmed():
            util.plugin.setSetting(key, keyboard.getText())
    else:
        keyboard = xbmc.Keyboard(current, 'Edit ' + key, False)
        keyboard.doModal()
        if keyboard.isConfirmed():
            util.plugin.setSetting(key, keyboard.getText())

    xbmc.executebuiltin('Container.Refresh')


def handle_action(action):
    if action == 'openFallbackSettings':
        open_settings_dialog()
    elif action == 'migrateSettings':
        try:
            util.migrate_legacy_settings()
            xbmcgui.Dialog().notification('SickRage', 'Migration attempted', xbmcgui.NOTIFICATION_INFO, 2000)
        except Exception as e:
            util.log('settingsMenu: migrateSettings failed: %s' % repr(e))
            xbmcgui.Dialog().notification('SickRage', 'Migration failed', xbmcgui.NOTIFICATION_ERROR, 2000)
    else:
        menu()