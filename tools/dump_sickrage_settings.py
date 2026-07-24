import resources.lib.util as util

keys = ['url','key','user','password','dateFormat','timeFormat','rec_source','rec_pages']
for k in keys:
    try:
        util.log('dump_setting: %s => %r' % (k, util.plugin.getSetting(k)))
    except Exception as e:
        try:
            util.log('dump_setting: %s error %r' % (k, e))
        except Exception:
            pass
