import xbmcgui
import resources.lib.util as util


def show_stats(tvdbid):
    if not tvdbid:
        xbmcgui.Dialog().ok('Show Stats', 'No show id provided')
        return
    try:
        show = util.api.getShow(tvdbid) or {}
    except Exception:
        show = {}
    title = show.get('show_name') or show.get('name') or ('Show ' + str(tvdbid))
    seasons = util.api.getSeasonList(tvdbid) or []
    total = 0
    counts = {}
    try:
        # seasons may be list or dict
        keys = []
        if isinstance(seasons, dict):
            keys = seasons.keys()
        elif isinstance(seasons, list):
            keys = seasons
        for s in keys:
            eps = util.api.getSeasons(tvdbid, {'season': s}) or {}
            for en, ep in eps.items():
                total += 1
                st = (ep.get('status') or '').strip()
                counts[st] = counts.get(st, 0) + 1
    except Exception:
        pass

    lines = ['Stats for: %s' % title, 'Total episodes: %d' % total]
    for k, v in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        lines.append('%s: %d' % (k or 'Unknown', v))

    xbmcgui.Dialog().textviewer('Show Stats', '\n'.join(lines))
