"""
SickRage — meerkat on sentry duty.
Draws at 2x (512) then scales to 256 for natural anti-aliasing.
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import math, os

S = 512          # working size
OUT = 256        # output size
CX  = S // 2


def c(col, alpha=255):
    """Return RGBA tuple, optionally overriding alpha."""
    if len(col) == 3:
        return col + (alpha,)
    return col[:3] + (alpha,)


def ell(d, cx, cy, rw, rh, fill, outline=None, lw=0):
    d.ellipse([cx-rw, cy-rh, cx+rw, cy+rh],
              fill=fill, outline=outline, width=lw)


def make():
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))

    # ── Sky: warm Kalahari dusk ──────────────────────────────────────────────
    sky = Image.new('RGBA', (S, S))
    sd  = ImageDraw.Draw(sky)
    for y in range(S):
        t = y / S
        # deep indigo top → amber horizon
        r = int(22  + t * (210 - 22))
        g = int(18  + t * (105 - 18))
        b = int(68  + t * (48  - 68))
        sd.line([(0, y), (S, y)], fill=(r, g, b, 255))
    img = Image.alpha_composite(img, sky)

    # ── Stars ────────────────────────────────────────────────────────────────
    import random; random.seed(7)
    d = ImageDraw.Draw(img)
    for _ in range(60):
        sx = random.randint(6, S-6)
        sy = random.randint(6, S//3)
        br = random.randint(150, 255)
        r  = random.choice([1, 1, 2, 2, 3])
        d.ellipse([sx-r, sy-r, sx+r, sy+r], fill=(br, br, br, br))

    # ── Ground ───────────────────────────────────────────────────────────────
    GY = 420   # ground line
    for y in range(GY, S):
        t = (y - GY) / (S - GY)
        r = int(155 + t * 25)
        g = int(112 + t * 12)
        b = int(52  - t * 10)
        d.line([(0, y), (S, y)], fill=(r, g, b, 255))
    # ground horizon ridge
    d.ellipse([-40, GY-14, S+40, GY+14], fill=(148, 104, 44))

    # ── Meerkat palette ──────────────────────────────────────────────────────
    FUR      = (192, 154, 88)
    FUR_D    = (132,  96, 42)    # dark back / shading
    FUR_L    = (222, 192, 130)   # light belly / face
    EYE_RING = ( 38,  24,  8)
    EYE_WHT  = (238, 222, 192)
    EYE_PUP  = ( 12,   8,   4)
    NOSE_C   = ( 58,  34,  14)
    EAR_I    = (210, 135,  85)
    CLAW     = ( 88,  60,  24)
    SHADOW   = (  0,   0,   0,  70)

    foot_y = GY - 4

    # ── Drop shadow ──────────────────────────────────────────────────────────
    shd = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(shd).ellipse([CX-55, foot_y-10, CX+55, foot_y+16], fill=SHADOW)
    shd = shd.filter(ImageFilter.GaussianBlur(14))
    img = Image.alpha_composite(img, shd)
    d   = ImageDraw.Draw(img)

    # ── TAIL: thick S-curve, dark-tipped ─────────────────────────────────────
    # Draw as a series of circles along a bezier-like path
    tail_pts = []
    for i in range(38):
        t  = i / 37
        # cubic bezier: start behind left hip, sweep up and curve right
        bx = (CX - 38 + int(-28 * (1-t)**3 + 14 * 3*(1-t)**2*t
              + 18 * 3*(1-t)*t**2 + -8 * t**3))
        by = (foot_y - 18 + int(-160 * t + 40 * math.sin(t * math.pi)))
        tail_pts.append((bx, by))
    for i, (tx, ty) in enumerate(tail_pts):
        t   = i / 37
        w   = max(4, 14 - int(t * 8))
        col = FUR_D if t > 0.78 else FUR
        d.ellipse([tx-w, ty-w, tx+w, ty+w], fill=col)

    # ── Legs ─────────────────────────────────────────────────────────────────
    leg_top = foot_y - 76
    for side in [-1, 1]:
        lx = CX + side * 14
        # upper leg
        d.line([(lx, leg_top), (lx + side*3, foot_y - 18)], fill=FUR, width=18)
        # lower leg (slightly lighter)
        d.line([(lx + side*3, foot_y-18), (lx + side*5, foot_y)],
               fill=FUR_L, width=14)
        # foot
        ell(d, lx + side*7, foot_y + 4, 14, 7, FUR_D)
        # claws
        for ci in range(3):
            ox = (ci - 1) * 7
            ell(d, lx + side*6 + ox, foot_y + 9, 3, 5, CLAW)

    # ── Body ─────────────────────────────────────────────────────────────────
    body_cy = leg_top - 56
    bw, bh  = 52, 64

    # back layer (dark)
    ell(d, CX,     body_cy, bw,   bh,   FUR_D)
    # main fur
    ell(d, CX,     body_cy, bw-4, bh-2, FUR)
    # side shading left
    ell(d, CX-30, body_cy, 22, bh-10,
        (FUR_D[0], FUR_D[1], FUR_D[2], 120))
    # side shading right
    ell(d, CX+30, body_cy, 22, bh-10,
        (FUR_D[0], FUR_D[1], FUR_D[2], 120))
    # belly highlight
    ell(d, CX, body_cy+4, 22, bh-16, FUR_L)

    # ── Arms / paws ───────────────────────────────────────────────────────────
    shoulder_y = body_cy - 30
    for side in [-1, 1]:
        sx  = CX + side * 38
        ex  = CX + side * 58
        ey  = shoulder_y + 52
        # upper arm
        d.line([(sx, shoulder_y), (ex, ey)], fill=FUR, width=18)
        # paw
        ell(d, ex, ey + 6, 12, 9, FUR_D)
        # paw detail
        ell(d, ex, ey + 6, 7, 5, FUR_L)

    # ── Neck ─────────────────────────────────────────────────────────────────
    neck_base = body_cy - bh + 8
    neck_top  = neck_base - 28
    d.line([(CX, neck_base), (CX, neck_top)], fill=FUR,   width=30)
    d.line([(CX, neck_base), (CX, neck_top)], fill=FUR_L, width=14)

    # ── Head ─────────────────────────────────────────────────────────────────
    head_cy = neck_top - 42
    hw, hh  = 46, 42

    ell(d, CX, head_cy, hw,   hh,   FUR_D)   # shadow layer
    ell(d, CX, head_cy, hw-2, hh-2, FUR)
    # forehead highlight
    ell(d, CX, head_cy-12, 28, 18, FUR_L)
    # snout / muzzle
    ell(d, CX, head_cy+16, 20, 14, FUR_L)

    # ── Ears ─────────────────────────────────────────────────────────────────
    for side in [-1, 1]:
        ex = CX + side * 40
        ey = head_cy - 26
        ell(d, ex, ey, 16, 14, FUR_D)
        ell(d, ex, ey,  9,  8, EAR_I)

    # ── Eye patches (the defining meerkat feature) ────────────────────────────
    for side in [-1, 1]:
        ex = CX + side * 18
        ey = head_cy - 4
        ell(d, ex, ey, 16, 13, EYE_RING)          # dark ring
        ell(d, ex, ey, 10, 10, EYE_WHT)           # white sclera
        ell(d, ex + side*2, ey + 1, 6, 6, EYE_PUP)  # pupil
        ell(d, ex + side*3, ey - 2, 2, 2,         # catchlight
            (255, 255, 255, 210))

    # ── Nose & mouth ─────────────────────────────────────────────────────────
    ell(d, CX, head_cy + 18, 7, 5, NOSE_C)
    d.arc([CX-10, head_cy+18, CX+10, head_cy+32],
          start=12, end=168, fill=NOSE_C, width=3)

    # ── TV Antenna ───────────────────────────────────────────────────────────
    ANT   = (190, 215, 255, 230)
    ax    = CX
    abase = head_cy - hh + 2
    # stem
    d.line([(ax, abase), (ax, abase-18)], fill=ANT, width=5)
    # left prong
    d.line([(ax, abase-18), (ax-22, abase-48)], fill=ANT, width=4)
    ell(d, ax-24, abase-52, 7, 7, ANT)
    # right prong
    d.line([(ax, abase-18), (ax+22, abase-48)], fill=ANT, width=4)
    ell(d, ax+24, abase-52, 7, 7, ANT)
    # small signal rings around right ball (like a signal pulse)
    for r in [12, 18]:
        d.arc([ax+24-r, abase-52-r, ax+24+r, abase-52+r],
              start=-60, end=60,
              fill=(ANT[0], ANT[1], ANT[2], 100), width=2)

    # ── "SICKRAGE" text ──────────────────────────────────────────────────────
    label = 'SICKRAGE'
    for size, bold in [(44, True), (40, False)]:
        for fname in ['arialbd.ttf', 'arial.ttf', 'DejaVuSans-Bold.ttf',
                      'DejaVuSans.ttf']:
            try:
                font = ImageFont.truetype(fname, size); break
            except Exception:
                font = None
        if font:
            break
    if not font:
        font = ImageFont.load_default()

    bbox = d.textbbox((0, 0), label, font=font)
    tw   = bbox[2] - bbox[0]
    tx   = (S - tw) // 2
    ty   = S - 62
    # shadow
    d.text((tx+2, ty+2), label, font=font, fill=(0, 0, 0, 180))
    # glow
    d.text((tx-1, ty-1), label, font=font,
           fill=(255, 200, 80, 60))
    # main
    d.text((tx, ty), label, font=font, fill=(255, 225, 140, 255))

    # ── Scale down 2x → 1x (natural anti-aliasing) ───────────────────────────
    out = img.resize((OUT, OUT), Image.LANCZOS)

    # ── Rounded corners ───────────────────────────────────────────────────────
    mask = Image.new('L', (OUT, OUT), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, OUT-1, OUT-1], radius=34, fill=255)
    out.putalpha(mask)

    out.save('icon.png')
    print('icon.png saved (%dx%d)' % out.size)


make()

from PIL import Image, ImageDraw, ImageFilter
import math

SIZE = 256
img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# ── Background: deep dusk sky gradient ─────────────────────────────────────
bg = Image.new('RGBA', (SIZE, SIZE))
bg_d = ImageDraw.Draw(bg)
for y in range(SIZE):
    t = y / SIZE
    r = int(20  + t * (80  - 20))
    g = int(10  + t * (45  - 10))
    b = int(40  + t * (20  - 40))
    bg_d.line([(0, y), (SIZE, y)], fill=(r, g, b, 255))
img = Image.alpha_composite(img, bg)
d = ImageDraw.Draw(img)

# ── Stars ───────────────────────────────────────────────────────────────────
import random
random.seed(42)
for _ in range(55):
    sx = random.randint(4, 252)
    sy = random.randint(4, 110)
    br = random.randint(160, 255)
    r  = random.choice([1, 1, 1, 2])
    d.ellipse([sx-r, sy-r, sx+r, sy+r], fill=(br, br, br, br))

# ── Ground: sandy desert strip ──────────────────────────────────────────────
ground_y = 196
for y in range(ground_y, SIZE):
    t = (y - ground_y) / (SIZE - ground_y)
    r = int(160 + t * 20)
    g = int(110 + t * 15)
    b = int(50  + t * 10)
    d.line([(0, y), (SIZE, y)], fill=(r, g, b, 255))

# Small ground texture bumps
for bx in [30, 70, 120, 170, 210, 240]:
    d.ellipse([bx-12, ground_y-4, bx+12, ground_y+2], fill=(155, 105, 45, 180))

# ── Helper: smooth ellipse ──────────────────────────────────────────────────
def ell(cx, cy, rw, rh, fill, outline=None, lw=0):
    d.ellipse([cx-rw, cy-rh, cx+rw, cy+rh], fill=fill,
              outline=outline, width=lw)

# ── Meerkat colour palette ───────────────────────────────────────────────────
FUR        = (185, 145,  90, 255)   # warm tan
FUR_DARK   = (140, 100,  50, 255)   # darker tan for shading
FUR_BELLY  = (210, 175, 120, 255)   # light belly
NOSE       = ( 60,  35,  20, 255)
EYE_RING   = ( 45,  30,  10, 255)   # dark patch around eye
EYE_WHITE  = (240, 230, 200, 255)
EYE_PUPIL  = ( 20,  15,   8, 255)
EYE_SHINE  = (255, 255, 255, 220)
EAR_INNER  = (220, 150, 100, 255)
CLAW       = (100,  70,  30, 255)
SHADOW     = (  0,   0,   0,  60)

cx = SIZE // 2        # horizontal centre
foot_y = ground_y - 2

# ── Shadow ───────────────────────────────────────────────────────────────────
shadow = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
sd = ImageDraw.Draw(shadow)
sd.ellipse([cx-28, foot_y-6, cx+28, foot_y+8], fill=SHADOW)
shadow = shadow.filter(ImageFilter.GaussianBlur(6))
img = Image.alpha_composite(img, shadow)
d = ImageDraw.Draw(img)

# ── Tail ─────────────────────────────────────────────────────────────────────
# Thick curved tail going back-left and up
tail_pts = []
for i in range(30):
    t  = i / 29
    tx = cx - 18 + int(-22 * t + 6 * math.sin(t * math.pi))
    ty = foot_y - int(t * 62) + int(10 * math.sin(t * math.pi * 1.5))
    tail_pts.append((tx, ty))
for i in range(len(tail_pts) - 1):
    w = max(2, 7 - i // 5)
    d.line([tail_pts[i], tail_pts[i+1]], fill=FUR_DARK, width=w)

# ── Legs ─────────────────────────────────────────────────────────────────────
leg_top = foot_y - 36
# left leg
d.line([(cx-8, leg_top), (cx-10, foot_y)], fill=FUR, width=9)
d.line([(cx-8, leg_top), (cx-10, foot_y)], fill=FUR_DARK, width=3)
# right leg
d.line([(cx+8, leg_top), (cx+10, foot_y)], fill=FUR, width=9)
d.line([(cx+8, leg_top), (cx+10, foot_y)], fill=FUR_DARK, width=3)

# feet / claws
for fx, flip in [(cx-13, -1), (cx+13, 1)]:
    for cl in range(3):
        ox = flip * (cl - 1) * 4
        d.ellipse([fx+ox-3, foot_y-3, fx+ox+3, foot_y+5], fill=CLAW)

# ── Body ─────────────────────────────────────────────────────────────────────
body_top = leg_top - 54
body_mid = leg_top - 28
# main body — solid fur colour
ell(cx, body_mid, 24, 30, FUR)
# side shading (darker on sides for 3D look)
ell(cx - 16, body_mid, 10, 26, (FUR_DARK[0], FUR_DARK[1], FUR_DARK[2], 140))
ell(cx + 16, body_mid, 10, 26, (FUR_DARK[0], FUR_DARK[1], FUR_DARK[2], 140))
# light belly highlight
ell(cx, body_mid + 2, 10, 20, FUR_BELLY)

# ── Arms / forepaws ──────────────────────────────────────────────────────────
# Meerkats hold arms slightly out when alert
arm_shoulder = body_mid - 14
# left arm — slightly forward
d.line([(cx-18, arm_shoulder), (cx-30, arm_shoulder+22)], fill=FUR, width=7)
ell(cx-31, arm_shoulder+24, 5, 4, FUR_DARK)   # paw
# right arm
d.line([(cx+18, arm_shoulder), (cx+30, arm_shoulder+22)], fill=FUR, width=7)
ell(cx+31, arm_shoulder+24, 5, 4, FUR_DARK)

# ── Neck ─────────────────────────────────────────────────────────────────────
neck_base = body_top + 4
neck_top  = body_top - 10
d.line([(cx, neck_base), (cx, neck_top)], fill=FUR, width=16)
d.line([(cx, neck_base), (cx, neck_top)], fill=FUR_BELLY, width=8)

# ── Head ─────────────────────────────────────────────────────────────────────
head_cy = neck_top - 22
ell(cx, head_cy, 22, 20, FUR)
# forehead highlight
ell(cx, head_cy - 4, 13, 9, FUR_BELLY)
# chin / snout muzzle area
ell(cx, head_cy + 8, 10, 7, FUR_BELLY)

# ── Ears ─────────────────────────────────────────────────────────────────────
for ex, flip in [(cx - 19, -1), (cx + 19, 1)]:
    ell(ex, head_cy - 14, 9, 8, FUR_DARK)           # outer ear
    ell(ex + flip*1, head_cy - 14, 5, 4, EAR_INNER) # inner

# ── Eye patches (dark rings characteristic of meerkat) ───────────────────────
for ex in [cx - 9, cx + 9]:
    ell(ex, head_cy - 2, 8, 7, EYE_RING)
    ell(ex, head_cy - 2, 5, 5, EYE_WHITE)
    ell(ex, head_cy - 2, 3, 3, EYE_PUPIL)
    ell(ex + 1, head_cy - 3, 1, 1, EYE_SHINE)

# ── Nose ─────────────────────────────────────────────────────────────────────
ell(cx, head_cy + 9, 4, 3, NOSE)

# ── Mouth ────────────────────────────────────────────────────────────────────
d.arc([cx-5, head_cy+8, cx+5, head_cy+16], start=10, end=170, fill=NOSE, width=2)

# ── TV antenna on head (SickRage motif) ──────────────────────────────────────
ANTENNA = (200, 220, 255, 230)
ant_base_x, ant_base_y = cx, head_cy - 20
# left prong
d.line([(ant_base_x, ant_base_y),
        (ant_base_x - 10, ant_base_y - 22)], fill=ANTENNA, width=2)
d.ellipse([ant_base_x-13, ant_base_y-26,
           ant_base_x-7,  ant_base_y-20], fill=ANTENNA)
# right prong
d.line([(ant_base_x, ant_base_y),
        (ant_base_x + 10, ant_base_y - 22)], fill=ANTENNA, width=2)
d.ellipse([ant_base_x+7,  ant_base_y-26,
           ant_base_x+13, ant_base_y-20], fill=ANTENNA)
# base stem
d.line([(ant_base_x, ant_base_y),
        (ant_base_x, ant_base_y - 6)], fill=ANTENNA, width=3)

# ── "SICKRAGE" text label ─────────────────────────────────────────────────────
try:
    from PIL import ImageFont
    font_lg = ImageFont.truetype("arial.ttf", 20)
    font_sm = ImageFont.truetype("arial.ttf", 11)
except Exception:
    font_lg = ImageFont.load_default()
    font_sm = font_lg

# Drop shadow then white text
TEXT_COLOR  = (255, 240, 180, 255)
TEXT_SHADOW = (0, 0, 0, 180)
label = "SICKRAGE"
# measure
bbox = d.textbbox((0, 0), label, font=font_lg)
tw = bbox[2] - bbox[0]
tx = (SIZE - tw) // 2
ty = SIZE - 32
d.text((tx+1, ty+1), label, font=font_lg, fill=TEXT_SHADOW)
d.text((tx, ty), label, font=font_lg, fill=TEXT_COLOR)

# ── Rounded-corner mask ───────────────────────────────────────────────────────
mask = Image.new('L', (SIZE, SIZE), 0)
mask_d = ImageDraw.Draw(mask)
mask_d.rounded_rectangle([0, 0, SIZE-1, SIZE-1], radius=32, fill=255)
img.putalpha(mask)

img.save('icon.png')
print('icon.png written (%dx%d)' % img.size)
