"""
SickRage icon — Timon-style cartoon meerkat.
Big head, wide grin, huge eyes, confident sentry pose.
Draws at 2× (512) then lanczos-down to 256 for clean edges.
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import math

S   = 512
OUT = 256
CX  = S // 2

def ell(d, cx, cy, rw, rh, fill, outline=None, lw=2):
    d.ellipse([cx - rw, cy - rh, cx + rw, cy + rh],
              fill=fill, outline=outline, width=lw)

def make():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # ── Sky gradient  (deep violet → warm amber at horizon) ─────────────────
    sky = Image.new("RGBA", (S, S))
    sd  = ImageDraw.Draw(sky)
    for y in range(S):
        t  = y / S
        r  = int(40  + t * (230 - 40))
        g  = int(20  + t * (120 - 20))
        b  = int(90  + t * (40  - 90))
        sd.line([(0, y), (S, y)], fill=(r, g, b, 255))
    img = Image.alpha_composite(img, sky)

    # ── Stars ────────────────────────────────────────────────────────────────
    import random; random.seed(42)
    d = ImageDraw.Draw(img)
    for _ in range(55):
        sx = random.randint(4, S - 4)
        sy = random.randint(4, S // 2)
        br = random.randint(160, 255)
        r  = random.choice([1, 1, 2, 2, 2, 3])
        d.ellipse([sx-r, sy-r, sx+r, sy+r], fill=(br, br, br+10, br))

    # ── Ground ───────────────────────────────────────────────────────────────
    GY = 430
    for y in range(GY, S):
        t = (y - GY) / (S - GY)
        d.line([(0, y), (S, y)],
               fill=(int(170 + t*30), int(120 + t*15), int(55 - t*15), 255))
    # horizon ridge
    d.ellipse([-60, GY - 18, S + 60, GY + 18], fill=(150, 108, 48))

    # ── Colour palette ───────────────────────────────────────────────────────
    TAN      = (210, 170, 95)    # main fur
    TAN_D    = (145, 100, 42)    # dark patches / back
    CREAM    = (240, 215, 155)   # belly / face centre
    EAR_IN   = (215, 130, 80)    # inner ear pink
    PATCH    = (42,  26,  8)     # dark eye rings
    SCLERA   = (248, 235, 200)   # white of eye
    IRIS     = (60,  130, 60)    # green iris (Timon-ish)
    PUPIL    = (10,   8,   4)
    NOSE     = (68,  38,  18)
    TOOTH    = (255, 252, 235)
    OUTLINE  = (60,  35,  8)     # general dark outline
    ANT      = (195, 220, 255, 240)

    foot_y   = GY + 2

    # ── Drop shadow ──────────────────────────────────────────────────────────
    shd = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(shd).ellipse([CX-54, foot_y-8, CX+54, foot_y+14],
                                fill=(0, 0, 0, 80))
    shd = shd.filter(ImageFilter.GaussianBlur(18))
    img = Image.alpha_composite(img, shd)
    d   = ImageDraw.Draw(img)

    # ── TAIL (Timon's long thin curve, dark tip) ──────────────────────────────
    # Bezier from behind left hip, arching up and curling right at top
    def bezier4(p0, p1, p2, p3, t):
        mt = 1 - t
        x  = mt**3*p0[0] + 3*mt**2*t*p1[0] + 3*mt*t**2*p2[0] + t**3*p3[0]
        y  = mt**3*p0[1] + 3*mt**2*t*p1[1] + 3*mt*t**2*p2[1] + t**3*p3[1]
        return (int(x), int(y))

    P0 = (CX - 45, foot_y - 90)
    P1 = (CX - 90, foot_y - 220)
    P2 = (CX - 20, foot_y - 320)
    P3 = (CX + 50, foot_y - 280)

    tail_pts = [bezier4(P0, P1, P2, P3, i / 34) for i in range(35)]
    for i, (tx, ty) in enumerate(tail_pts):
        t   = i / 34
        w   = max(3, int(10 - t * 6))
        col = TAN_D if t > 0.80 else TAN
        d.ellipse([tx-w, ty-w, tx+w, ty+w], fill=col)

    # ── Legs (cartoon stubby) ─────────────────────────────────────────────────
    leg_top = foot_y - 80
    for side in [-1, 1]:
        lx = CX + side * 18
        # thigh
        d.line([(lx, leg_top), (lx + side*4, foot_y - 24)],
               fill=TAN, width=22)
        # shin
        d.line([(lx + side*4, foot_y - 24), (lx + side*8, foot_y)],
               fill=CREAM, width=16)
        # big cartoon foot (3 toes)
        ell(d, lx + side*10, foot_y + 6, 18, 9, TAN_D)
        for ci in range(3):
            ox = (ci - 1) * 9
            d.ellipse([lx + side*9 + ox - 4, foot_y + 8,
                       lx + side*9 + ox + 4, foot_y + 18], fill=TAN_D)

    # ── Body (Timon slim, slight taper) ──────────────────────────────────────
    body_cy  = leg_top - 58
    bw, bh   = 56, 68

    ell(d, CX,      body_cy,      bw+2,  bh+2,  OUTLINE)   # outline
    ell(d, CX,      body_cy,      bw,    bh,    TAN)
    ell(d, CX-32,   body_cy,      18,    bh-8,  TAN_D)      # left shading
    ell(d, CX+32,   body_cy,      18,    bh-8,  TAN_D)      # right shading
    ell(d, CX,      body_cy + 6,  28,    bh-20, CREAM)      # belly

    # ── Arms / hands (Timon has long skinny arms) ─────────────────────────────
    shoulder_y = body_cy - 34
    for side in [-1, 1]:
        sx = CX + side * 44
        ex = CX + side * 68
        ey = shoulder_y + 60
        d.line([(sx, shoulder_y), (ex, ey)], fill=TAN, width=16)
        ell(d, ex, ey + 8,  14, 10, TAN_D, outline=OUTLINE, lw=2)
        ell(d, ex, ey + 8,   8,  6, CREAM)

    # ── Neck ─────────────────────────────────────────────────────────────────
    neck_b = body_cy - bh + 12
    neck_t = neck_b - 22
    d.line([(CX - 14, neck_b), (CX - 10, neck_t)], fill=TAN,   width=28)
    d.line([(CX + 14, neck_b), (CX + 10, neck_t)], fill=TAN,   width=28)
    d.line([(CX,      neck_b), (CX,      neck_t)], fill=CREAM, width=14)

    # ── HEAD (cartoon big round head — Timon's defining shape) ───────────────
    head_cy = neck_t - 52
    hw, hh  = 60, 54

    # outline
    ell(d, CX, head_cy, hw+3, hh+3, OUTLINE)
    # main head
    ell(d, CX, head_cy, hw,   hh,   TAN)
    # forehead highlight (lighter)
    ell(d, CX, head_cy - 16, 38, 24, (TAN[0]+18, TAN[1]+14, TAN[2]+8))
    # face centre cream
    ell(d, CX, head_cy + 10, 36, 32, CREAM)

    # ── Big cartoon ears ─────────────────────────────────────────────────────
    for side in [-1, 1]:
        ex = CX + side * 56
        ey = head_cy - 22
        ell(d, ex, ey, 22, 20, OUTLINE)
        ell(d, ex, ey, 20, 18, TAN)
        ell(d, ex, ey, 12, 11, EAR_IN)

    # ── Dark eye patches (Timon's raccoon rings) ──────────────────────────────
    for side in [-1, 1]:
        ex = CX + side * 22
        ey = head_cy - 6
        # big dark ring
        ell(d, ex, ey, 19, 16, PATCH)
        # sclera
        ell(d, ex, ey, 13, 13, SCLERA)
        # iris
        ell(d, ex, ey,  9,  9, IRIS)
        # pupil
        ell(d, ex + side*2, ey + 1, 5, 5, PUPIL)
        # bright catchlight — makes eyes sparkle
        ell(d, ex + side*3, ey - 3, 3, 3, (255, 255, 255, 240))
        ell(d, ex - side*1, ey + 4, 2, 2, (255, 255, 255, 160))

    # ── Eyebrows (expressive — slightly raised = alert sentry look) ───────────
    for side in [-1, 1]:
        ex = CX + side * 22
        ey = head_cy - 24
        d.arc([ex - 14, ey - 6, ex + 14, ey + 8],
              start=200 if side == -1 else 340,
              end  =340 if side == -1 else 200 + 360,
              fill=OUTLINE, width=5)

    # ── Nose ─────────────────────────────────────────────────────────────────
    ell(d, CX, head_cy + 20, 10, 7, NOSE, outline=OUTLINE, lw=2)
    # nostrils
    ell(d, CX - 4, head_cy + 19, 3, 2, (20, 10, 4))
    ell(d, CX + 4, head_cy + 19, 3, 2, (20, 10, 4))

    # ── Big Timon grin (wide cheeky smile) ────────────────────────────────────
    mouth_y = head_cy + 32
    # jaw shape
    d.arc([CX - 28, mouth_y - 14, CX + 28, mouth_y + 14],
          start=14, end=166, fill=OUTLINE, width=5)
    # teeth strip
    d.arc([CX - 22, mouth_y - 12, CX + 22, mouth_y + 8],
          start=16, end=164, fill=TOOTH, width=8)
    # tooth dividers
    for xo in [-8, 0, 8]:
        d.line([(CX + xo, mouth_y - 4), (CX + xo, mouth_y + 2)],
               fill=OUTLINE, width=2)
    # cheek blush
    for side in [-1, 1]:
        bx = CX + side * 36
        by = head_cy + 20
        blush = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ImageDraw.Draw(blush).ellipse([bx-12, by-7, bx+12, by+7],
                                      fill=(230, 90, 90, 80))
        blush = blush.filter(ImageFilter.GaussianBlur(5))
        img = Image.alpha_composite(img, blush)
        d   = ImageDraw.Draw(img)

    # ── TV Antenna (Timon-style, perky V on head) ─────────────────────────────
    atop  = head_cy - hh - 4
    # base stem
    d.line([(CX, atop), (CX, atop - 22)], fill=ANT, width=6)
    # left prong
    d.line([(CX, atop - 22), (CX - 26, atop - 58)], fill=ANT, width=5)
    ell(d, CX - 28, atop - 62, 9, 9, ANT, outline=(150, 180, 255, 200), lw=2)
    # right prong
    d.line([(CX, atop - 22), (CX + 26, atop - 58)], fill=ANT, width=5)
    ell(d, CX + 28, atop - 62, 9, 9, ANT, outline=(150, 180, 255, 200), lw=2)
    # signal pulse arcs from right ball
    for radius in [14, 22]:
        d.arc([CX + 28 - radius, atop - 62 - radius,
               CX + 28 + radius, atop - 62 + radius],
              start=-70, end=50,
              fill=(ANT[0], ANT[1], ANT[2], 90), width=2)

    # ── "SICKRAGE" label ──────────────────────────────────────────────────────
    label = "SICKRAGE"
    font  = None
    for size in [46, 42, 38]:
        for fname in ["arialbd.ttf", "arial.ttf",
                      "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"]:
            try:
                font = ImageFont.truetype(fname, size)
                break
            except Exception:
                pass
        if font:
            break
    if not font:
        font = ImageFont.load_default()

    bbox = d.textbbox((0, 0), label, font=font)
    tw   = bbox[2] - bbox[0]
    tx   = (S - tw) // 2
    ty   = S - 62

    # text glow layer
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(glow).text((tx, ty), label, font=font,
                              fill=(255, 230, 80, 120))
    glow = glow.filter(ImageFilter.GaussianBlur(6))
    img  = Image.alpha_composite(img, glow)
    d    = ImageDraw.Draw(img)

    d.text((tx + 3, ty + 3), label, font=font, fill=(0, 0, 0, 200))  # shadow
    d.text((tx,     ty    ), label, font=font, fill=(255, 228, 100, 255))

    # ── Scale to output size ──────────────────────────────────────────────────
    out = img.resize((OUT, OUT), Image.LANCZOS)

    # ── Rounded corners ───────────────────────────────────────────────────────
    mask = Image.new("L", (OUT, OUT), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, OUT-1, OUT-1],
                                           radius=34, fill=255)
    out.putalpha(mask)

    out.save("icon.png")
    print("Saved icon.png (%dx%d)" % out.size)


make()
