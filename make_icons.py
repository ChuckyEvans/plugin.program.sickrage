"""
Flat icon set for SickRage — Kodi 21 Estuary style.
Dark navy bg + coloured symbol, each colour reinforcing meaning:
  blue   = navigation (shows, quality, settings)
  purple = scheduled/time (upcoming)
  indigo = past (history)
  gold   = special/recommended (recommended, star)
  green  = positive/done (downloaded, showAdd)
  cyan   = in-progress (snatched, soon)
  amber  = attention/search (wanted, today)
  gray   = neutral/future (later)
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import math, os

S  = 256
CX = S // 2

# ── palette ──────────────────────────────────────────────────────────────────
BG     = (16, 20, 34, 255)
WHITE  = (238, 242, 255, 255)
BLUE   = ( 72, 152, 240, 255)
PURPLE = (160,  90, 240, 255)
INDIGO = (100, 110, 240, 255)
GOLD   = (255, 205,  45, 255)
GREEN  = ( 58, 200, 110, 255)
CYAN   = ( 50, 210, 220, 255)
AMBER  = (240, 160,  35, 255)
GRAY   = (148, 155, 170, 255)
RED    = (220,  68,  68, 255)


# ── helpers ──────────────────────────────────────────────────────────────────

def canvas():
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    bg  = Image.new('RGBA', (S, S), BG)
    # subtle top-edge highlight
    hi = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(hi).rectangle([0, 0, S, 6], fill=(255, 255, 255, 18))
    bg = Image.alpha_composite(bg, hi)
    img = Image.alpha_composite(img, bg)
    return img


def mask_round(img, r=32):
    m = Image.new('L', (S, S), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, S-1, S-1], radius=r, fill=255)
    img.putalpha(m)
    return img


def glow_layer(img, col, strength=40):
    g = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse(
        [CX-70, CX-70, CX+70, CX+70],
        fill=(col[0], col[1], col[2], strength))
    g = g.filter(ImageFilter.GaussianBlur(30))
    return Image.alpha_composite(img, g)


def ell(d, cx, cy, rx, ry, fill, outline=None, lw=0):
    d.ellipse([cx-rx, cy-ry, cx+rx, cy+ry], fill=fill,
              outline=outline, width=lw)


def ring(d, cx, cy, r_out, r_in, fill):
    d.ellipse([cx-r_out, cy-r_out, cx+r_out, cy+r_out], fill=fill)
    d.ellipse([cx-r_in,  cy-r_in,  cx+r_in,  cy+r_in],  fill=BG)


def star_pts(cx, cy, r_out, r_in, n=5, rot=-90):
    pts = []
    for i in range(n * 2):
        r   = r_out if i % 2 == 0 else r_in
        ang = math.radians(rot + i * 180 / n)
        pts.append((cx + r*math.cos(ang), cy + r*math.sin(ang)))
    return pts


def font(size):
    for f in ['arialbd.ttf', 'arial.ttf', 'DejaVuSans-Bold.ttf', 'DejaVuSans.ttf']:
        try:
            return ImageFont.truetype(f, size)
        except Exception:
            pass
    return ImageFont.load_default()


def centered_text(d, img_w, y, text, fnt, fill):
    bbox = d.textbbox((0, 0), text, font=fnt)
    x = (img_w - (bbox[2] - bbox[0])) // 2 - bbox[0]
    d.text((x, y - bbox[1]), text, font=fnt, fill=fill)


def save(img, name):
    img = mask_round(img)
    path = os.path.join('resources', 'icons', name + '.png')
    img.save(path)
    print('  ' + path)


# ── SHOWS — TV monitor with coloured EQ bars ─────────────────────────────────
def make_shows():
    img = canvas(); img = glow_layer(img, BLUE); d = ImageDraw.Draw(img)
    # bezel
    d.rounded_rectangle([CX-76, CX-60, CX+76, CX+40], radius=10, fill=(30, 42, 80))
    d.rounded_rectangle([CX-76, CX-60, CX+76, CX+40], radius=10,
                        fill=None, outline=BLUE, width=3)
    # screen (dark)
    d.rounded_rectangle([CX-62, CX-48, CX+62, CX+26], radius=5, fill=(10, 15, 30))
    # EQ bars (signal strength metaphor for "shows available")
    bars = [(CYAN, 14), (GREEN, 22), (GOLD, 32), (AMBER, 42)]
    for i, (col, h) in enumerate(bars):
        bx = CX - 38 + i * 26
        d.rounded_rectangle([bx-9, CX+24-h, bx+9, CX+24], radius=3, fill=col)
    # stand
    d.polygon([(CX-14, CX+40), (CX+14, CX+40),
               (CX+22, CX+64), (CX-22, CX+64)], fill=(30, 42, 80))
    d.rounded_rectangle([CX-34, CX+62, CX+34, CX+72], radius=4, fill=BLUE)
    # antenna
    d.line([CX, CX-60, CX-22, CX-92], fill=WHITE, width=5)
    ell(d, CX-24, CX-95, 6, 6, WHITE)
    d.line([CX, CX-60, CX+22, CX-92], fill=WHITE, width=5)
    ell(d, CX+24, CX-95, 6, 6, WHITE)
    save(img, 'shows')


# ── RECOMMENDED — 5-point gold star ─────────────────────────────────────────
def make_recommended():
    img = canvas(); img = glow_layer(img, GOLD, 50); d = ImageDraw.Draw(img)
    # outer halo
    d.polygon(star_pts(CX, CX, 94, 44), fill=(GOLD[0], GOLD[1], GOLD[2], 50))
    # main star
    d.polygon(star_pts(CX, CX, 82, 36), fill=GOLD)
    # inner shine spot
    d.polygon(star_pts(CX-4, CX-8, 32, 14), fill=(255, 238, 160, 180))
    save(img, 'recommended')


# ── UPCOMING — calendar with a clock ────────────────────────────────────────
def make_upcoming():
    img = canvas(); img = glow_layer(img, PURPLE); d = ImageDraw.Draw(img)
    # body
    d.rounded_rectangle([CX-70, CX-62, CX+70, CX+70], radius=12, fill=(28, 22, 52))
    d.rounded_rectangle([CX-70, CX-62, CX+70, CX+70], radius=12,
                        fill=None, outline=PURPLE, width=3)
    # header bar
    d.rounded_rectangle([CX-70, CX-62, CX+70, CX-22], radius=12,
                        fill=(PURPLE[0], PURPLE[1], PURPLE[2], 200))
    d.rectangle([CX-70, CX-38, CX+70, CX-22], fill=(PURPLE[0], PURPLE[1], PURPLE[2], 200))
    # binding clips
    for bx in [CX-36, CX+36]:
        d.rounded_rectangle([bx-7, CX-74, bx+7, CX-50], radius=5,
                             fill=(16, 20, 34), outline=WHITE, width=2)
    # clock face inside body
    ell(d, CX, CX+14, 38, 38, (24, 18, 48))
    ell(d, CX, CX+14, 34, 34, (24, 18, 48), outline=PURPLE, lw=2)
    # clock hands
    d.line([CX, CX+14, CX, CX-14], fill=WHITE, width=4)      # 12
    d.line([CX, CX+14, CX+22, CX+14], fill=CYAN, width=3)    # 3
    ell(d, CX, CX+14, 4, 4, WHITE)
    save(img, 'upcoming')


# ── HISTORY — clock face with backward arrow ─────────────────────────────────
def make_history():
    img = canvas(); img = glow_layer(img, INDIGO); d = ImageDraw.Draw(img)
    # clock ring
    ring(d, CX, CX, 86, 68, INDIGO)
    # hour ticks
    for i in range(12):
        ang = math.radians(i * 30 - 90)
        r1  = 64 if i % 3 == 0 else 67
        r2  = 74
        w   = 4 if i % 3 == 0 else 2
        d.line([(CX + r1*math.cos(ang), CX + r1*math.sin(ang)),
                (CX + r2*math.cos(ang), CX + r2*math.sin(ang))],
               fill=WHITE, width=w)
    # hands  (10:10 classic position)
    for ang_deg, length, width, col in [
        (300-90, 42, 6, WHITE),   # hour  → 10
        ( 60-90, 56, 4, INDIGO),  # minute → 2
    ]:
        ang = math.radians(ang_deg)
        d.line([(CX, CX), (CX + length*math.cos(ang), CX + length*math.sin(ang))],
               fill=col, width=width)
    ell(d, CX, CX, 6, 6, WHITE)
    # counterclockwise arrow arc outside ring
    for a in range(195, 345):
        ang = math.radians(a)
        r = 96
        ell(d, CX + r*math.cos(ang), CX + r*math.sin(ang), 3, 3,
            (INDIGO[0], INDIGO[1], INDIGO[2], 180))
    # arrowhead
    t = math.radians(195)
    ax, ay = CX + 96*math.cos(t), CX + 96*math.sin(t)
    d.polygon([(ax, ay),
               (ax + 12*math.cos(t+0.5), ay + 12*math.sin(t+0.5)),
               (ax + 12*math.cos(t-0.5), ay + 12*math.sin(t-0.5))],
              fill=INDIGO)
    save(img, 'history')


# ── SETTINGS — 10-tooth gear ─────────────────────────────────────────────────
def make_settings():
    img = canvas(); img = glow_layer(img, GRAY); d = ImageDraw.Draw(img)
    N = 10
    pts = []
    for i in range(N * 4):
        ang = math.radians(i * 360 / (N * 4) - 90)
        r   = 82 if (i % 4) < 2 else 66
        pts.append((CX + r*math.cos(ang), CX + r*math.sin(ang)))
    d.polygon(pts, fill=(50, 58, 88))
    d.polygon(pts, fill=None, outline=GRAY, width=2)
    ell(d, CX, CX, 28, 28, BG, outline=GRAY, lw=2)
    # inner crosshairs
    d.line([CX-14, CX, CX+14, CX], fill=GRAY, width=3)
    d.line([CX, CX-14, CX, CX+14], fill=GRAY, width=3)
    save(img, 'settings')


# ── TODAY — warm sun ─────────────────────────────────────────────────────────
def make_today():
    img = canvas(); img = glow_layer(img, AMBER, 55); d = ImageDraw.Draw(img)
    # rays
    for i in range(12):
        ang = math.radians(i * 30)
        r1  = 56 if i % 2 == 0 else 52
        r2  = 82 if i % 2 == 0 else 74
        w   = 7  if i % 2 == 0 else 4
        d.line([(CX + r1*math.cos(ang), CX + r1*math.sin(ang)),
                (CX + r2*math.cos(ang), CX + r2*math.sin(ang))],
               fill=AMBER, width=w)
    ell(d, CX, CX, 50, 50, AMBER)
    # inner glow
    ell(d, CX-10, CX-12, 20, 16, (255, 240, 180, 140))
    save(img, 'today')


# ── SOON — clock (coming soon) ───────────────────────────────────────────────
def make_soon():
    img = canvas(); img = glow_layer(img, CYAN); d = ImageDraw.Draw(img)
    ring(d, CX, CX, 90, 68, CYAN)
    for i in range(12):
        ang = math.radians(i * 30 - 90)
        r1  = 64 if i % 3 == 0 else 68
        r2  = 76
        d.line([(CX + r1*math.cos(ang), CX + r1*math.sin(ang)),
                (CX + r2*math.cos(ang), CX + r2*math.sin(ang))],
               fill=WHITE, width=4 if i % 3 == 0 else 2)
    # 10:10 hands
    d.line([CX, CX, CX + 40*math.cos(math.radians(300-90)),
                    CX + 40*math.sin(math.radians(300-90))], fill=WHITE, width=6)
    d.line([CX, CX, CX + 54*math.cos(math.radians(60-90)),
                    CX + 54*math.sin(math.radians(60-90))], fill=WHITE, width=4)
    ell(d, CX, CX, 6, 6, WHITE)
    save(img, 'soon')


# ── LATER — calendar with forward arrow ──────────────────────────────────────
def make_later():
    img = canvas(); img = glow_layer(img, GRAY); d = ImageDraw.Draw(img)
    d.rounded_rectangle([CX-70, CX-66, CX+70, CX+72], radius=12, fill=(28, 32, 50))
    d.rounded_rectangle([CX-70, CX-66, CX+70, CX+72], radius=12,
                        fill=None, outline=GRAY, width=3)
    d.rounded_rectangle([CX-70, CX-66, CX+70, CX-26], radius=12, fill=(50, 55, 75))
    d.rectangle([CX-70, CX-42, CX+70, CX-26], fill=(50, 55, 75))
    for bx in [CX-36, CX+36]:
        d.rounded_rectangle([bx-7, CX-78, bx+7, CX-54], radius=5,
                             fill=BG, outline=WHITE, width=2)
    # dot grid 3x2
    for row in range(2):
        for col in range(3):
            gx = CX - 38 + col * 38
            gy = CX - 2  + row * 34
            ell(d, gx, gy, 9, 9, (GRAY[0], GRAY[1], GRAY[2], 160))
    # large forward arrow
    ax = CX + 2
    d.polygon([(ax-2, CX+16), (ax+42, CX+16), (ax+42, CX+2),
               (ax+64, CX+26), (ax+42, CX+50), (ax+42, CX+36), (ax-2, CX+36)],
              fill=(GRAY[0], GRAY[1], GRAY[2], 200))
    save(img, 'later')


# ── WANTED — magnifying glass ────────────────────────────────────────────────
def make_wanted():
    img = canvas(); img = glow_layer(img, AMBER); d = ImageDraw.Draw(img)
    # glass ring
    ring(d, CX-14, CX-16, 62, 44, AMBER)
    # handle
    ang = math.radians(45)
    for t in range(38):
        r   = 56 + t
        px  = (CX-14) + r * math.cos(ang)
        py  = (CX-16) + r * math.sin(ang)
        ell(d, px, py, 11, 11, AMBER)
    save(img, 'wanted')


# ── SNATCHED — download arrow ────────────────────────────────────────────────
def make_snatched():
    img = canvas(); img = glow_layer(img, CYAN); d = ImageDraw.Draw(img)
    # shaft
    d.rectangle([CX-12, CX-68, CX+12, CX+14], fill=CYAN)
    # arrowhead
    d.polygon([(CX-44, CX+12), (CX, CX+62), (CX+44, CX+12)], fill=CYAN)
    # base bar
    d.rounded_rectangle([CX-58, CX+68, CX+58, CX+82], radius=5, fill=CYAN)
    save(img, 'snatched')


# ── DOWNLOADED — circle + checkmark ─────────────────────────────────────────
def make_downloaded():
    img = canvas(); img = glow_layer(img, GREEN, 50); d = ImageDraw.Draw(img)
    ell(d, CX, CX, 86, 86, GREEN)
    # tick — thick, bold
    pts = [CX-42, CX+4, CX-14, CX+38, CX+48, CX-28]
    d.line(pts[:4], fill=BG, width=18)
    d.line(pts[2:], fill=BG, width=18)
    # rounded caps
    ell(d, CX-42, CX+4,  9, 9, BG)
    ell(d, CX-14, CX+38, 9, 9, BG)
    ell(d, CX+48, CX-28, 9, 9, BG)
    save(img, 'downloaded')


# ── SHOW-ADD — plus in circle ────────────────────────────────────────────────
def make_show_add():
    img = canvas(); img = glow_layer(img, GREEN, 50); d = ImageDraw.Draw(img)
    ell(d, CX, CX, 86, 86, GREEN)
    d.rectangle([CX-10, CX-52, CX+10, CX+52], fill=BG)
    d.rectangle([CX-52, CX-10, CX+52, CX+10], fill=BG)
    save(img, 'showAdd')


# ── QUALITY — HD badge ───────────────────────────────────────────────────────
def make_quality():
    img = canvas(); img = glow_layer(img, BLUE); d = ImageDraw.Draw(img)
    # badge background
    d.rounded_rectangle([CX-84, CX-40, CX+84, CX+40], radius=16, fill=(26, 48, 92))
    d.rounded_rectangle([CX-84, CX-40, CX+84, CX+40], radius=16,
                        fill=None, outline=BLUE, width=3)
    # H
    lx = CX - 56
    d.rectangle([lx,    CX-24, lx+14, CX+24], fill=WHITE)
    d.rectangle([lx+14, CX-8,  lx+38, CX+8 ], fill=WHITE)
    d.rectangle([lx+38, CX-24, lx+52, CX+24], fill=WHITE)
    # D
    rx = CX + 14
    d.rectangle([rx, CX-24, rx+14, CX+24], fill=WHITE)
    d.ellipse([rx+6, CX-24, rx+52, CX+24], fill=WHITE)
    d.ellipse([rx+16, CX-16, rx+44, CX+16], fill=(26, 48, 92))
    save(img, 'quality')


# ── main ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    os.makedirs(os.path.join('resources', 'icons'), exist_ok=True)
    print('Generating icons...')
    make_shows()
    make_recommended()
    make_upcoming()
    make_history()
    make_settings()
    make_today()
    make_soon()
    make_later()
    make_wanted()
    make_snatched()
    make_downloaded()
    make_show_add()
    make_quality()
    print('Done.')
