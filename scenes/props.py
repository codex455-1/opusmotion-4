"""Hand-built vector props with procedural materials (bag, food, paper, shoe, house...)."""
import functools
import math
import numpy as np
import skia
from engine import text as T
from engine.core import PAL, clamp, lerp, mix, hash01, ease_out_cubic
from engine.gfx import xpath, paint, lin, rad, np_to_image, fbm, path_from_points, layer, rrect


# ---------------------------------------------------------------------------------------------
# Procedural material textures (cached skia Images)
# ---------------------------------------------------------------------------------------------
@functools.lru_cache(maxsize=None)
def leather_tex(w=720, h=640, seed=11):
    big = fbm((h, w), base=120, octaves=4, seed=seed)
    pores = fbm((h, w), base=3.0, octaves=2, seed=seed + 1)
    crack = np.abs(fbm((h, w), base=26, octaves=3, seed=seed + 2) - 0.5)
    crack = np.clip(1 - crack * 22, 0, 1) ** 3
    scuff = np.clip((fbm((h, w), base=14, octaves=4, seed=seed + 3) - 0.66) * 6, 0, 1)
    v = 0.80 + (big - 0.5) * 0.28 + (pores - 0.5) * 0.20 - crack * 0.16
    base = np.array([0.44, 0.25, 0.13])
    rgb = v[..., None] * base[None, None, :]
    rgb = rgb + scuff[..., None] * 0.35 * np.array([0.20, 0.15, 0.10]) * (0.5 + 0.5 * pores[..., None])
    return np_to_image(np.concatenate([np.clip(rgb, 0, 1), np.ones((h, w, 1))], -1).astype(np.float32))


@functools.lru_cache(maxsize=None)
def wood_tex(w=1400, h=700, seed=5, tint=(0.36, 0.22, 0.13)):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = fbm((h, w), base=180, octaves=4, seed=seed) * 60
    rings = np.sin((yy + warp) / 7.0 + fbm((h, w), base=40, octaves=3, seed=seed + 1) * 6)
    streak = fbm((h // 8 + 1, w), base=30, octaves=4, seed=seed + 2)
    streak = np.repeat(streak, 8, axis=0)[:h]
    v = 0.72 + rings * 0.07 + (streak - 0.5) * 0.35
    planks = (np.abs(((yy / 175.0) % 1.0) - 0.0) < 0.008).astype(np.float32)
    v -= planks * 0.25
    rgb = v[..., None] * np.array(tint)[None, None, :]
    return np_to_image(np.concatenate([np.clip(rgb, 0, 1), np.ones((h, w, 1))], -1).astype(np.float32))


@functools.lru_cache(maxsize=None)
def soil_tex(w=1200, h=900, seed=21):
    n1 = fbm((h, w), base=50, octaves=5, seed=seed)
    n2 = fbm((h, w), base=4, octaves=2, seed=seed + 1)
    yy = np.mgrid[0:h, 0:w][0].astype(np.float32) / h
    strata = np.sin(yy * 38 + n1 * 5) * 0.06
    stones = np.clip((fbm((h, w), base=9, octaves=2, seed=seed + 2) - 0.70) * 9, 0, 1)
    v = 0.55 + (n1 - 0.5) * 0.5 + (n2 - 0.5) * 0.25 + strata
    base = np.array([0.26, 0.17, 0.11])
    rgb = v[..., None] * base * (1 - 0.35 * yy[..., None])
    rgb = rgb * (1 - stones[..., None]) + stones[..., None] * np.array([0.40, 0.36, 0.31]) * v[..., None]
    return np_to_image(np.concatenate([np.clip(rgb, 0, 1), np.ones((h, w, 1))], -1).astype(np.float32))


def tex_shader(img, sx=1.0, sy=1.0, tx=0.0, ty=0.0):
    m = skia.Matrix()
    m.setScale(sx, sy)
    m.postTranslate(tx, ty)
    return img.makeShader(skia.TileMode.kMirror, skia.TileMode.kMirror,
                          skia.SamplingOptions(skia.FilterMode.kLinear), m)


# ---------------------------------------------------------------------------------------------
# Food
# ---------------------------------------------------------------------------------------------
def capsule_path(x0, y0, x1, y1, r):
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
    L = math.hypot(x1 - x0, y1 - y0)
    p = skia.Path()
    p.addRoundRect(skia.Rect.MakeXYWH(-r, -r, L + 2 * r, 2 * r), r, r)
    m = skia.Matrix()
    m.setRotate(ang)
    m.postTranslate(x0, y0)
    return xpath(p, m), ang, L


def salami(c, x0, y0, x1, y1, r, seed=0, light=(-0.5, -1.0)):
    path, ang, L = capsule_path(x0, y0, x1, y1, r)
    # body: radial-ish shading across the width via a rotated linear gradient
    nx, ny = -math.sin(math.radians(ang)), math.cos(math.radians(ang))
    g = lin((x0 - nx * r, y0 - ny * r), (x0 + nx * r, y0 + ny * r),
            [(0.62, 0.24, 0.17, 1), (0.47, 0.13, 0.10, 1), (0.22, 0.05, 0.04, 1)], [0.0, 0.45, 1.0])
    c.drawPath(path, paint(shader=g))
    # casing texture: pale fat speckles
    c.save()
    c.clipPath(path, doAntiAlias=True)
    for i in range(int(L * r / 55)):
        u, v = hash01(seed, i, 1), hash01(seed, i, 2) * 2 - 1
        px = x0 + (x1 - x0) * u + nx * v * r * 0.85
        py = y0 + (y1 - y0) * u + ny * v * r * 0.85
        s = 1.2 + hash01(seed, i, 3) * 2.6
        c.drawCircle(px, py, s, paint((0.93, 0.78, 0.70, 1), a=0.35 + 0.3 * hash01(seed, i, 4), blur=0.8))
    # wrinkles of the casing
    for k in range(7):
        u = (k + 0.5) / 7 + (hash01(seed, k, 9) - 0.5) * 0.05
        px, py = x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
        c.drawLine(px - nx * r, py - ny * r, px + nx * r * 0.2, py + ny * r * 0.2,
                   paint((0.15, 0.03, 0.02, 1), a=0.25, stroke=2.0, blur=1.2))
    # specular streak
    c.drawLine(x0 - nx * r * 0.45 + (x1 - x0) * 0.05, y0 - ny * r * 0.45 + (y1 - y0) * 0.05,
               x1 - nx * r * 0.45 - (x1 - x0) * 0.08, y1 - ny * r * 0.45 - (y1 - y0) * 0.08,
               paint((1, 0.93, 0.85, 1), a=0.55, stroke=r * 0.16, blur=r * 0.08))
    c.restore()
    # string tie at the end
    ex, ey = x1 + (x1 - x0) / L * r * 0.7, y1 + (y1 - y0) / L * r * 0.7
    c.drawLine(ex - nx * r * 0.35, ey - ny * r * 0.35, ex + nx * r * 0.35, ey + ny * r * 0.35,
               paint((0.82, 0.72, 0.55, 1), stroke=4.0))
    c.drawLine(ex, ey, ex + (x1 - x0) / L * 26 + nx * 8, ey + (y1 - y0) / L * 26 + ny * 8,
               paint((0.82, 0.72, 0.55, 1), stroke=2.5))


def bread(c, x0, y0, x1, y1, r, seed=3):
    path, ang, L = capsule_path(x0, y0, x1, y1, r)
    nx, ny = -math.sin(math.radians(ang)), math.cos(math.radians(ang))
    g = lin((x0 - nx * r, y0 - ny * r), (x0 + nx * r, y0 + ny * r),
            [(0.86, 0.60, 0.30, 1), (0.66, 0.38, 0.15, 1), (0.30, 0.15, 0.06, 1)], [0.0, 0.5, 1.0])
    c.drawPath(path, paint(shader=g))
    c.save()
    c.clipPath(path, doAntiAlias=True)
    for k in range(5):
        u = 0.14 + k * 0.17
        px, py = x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
        dx, dy = (x1 - x0) / L, (y1 - y0) / L
        a = (px - nx * r * 0.7 - dx * 18, py - ny * r * 0.7 - dy * 18)
        b = (px + nx * r * 0.1 + dx * 22, py + ny * r * 0.1 + dy * 22)
        c.drawLine(*a, *b, paint((0.98, 0.86, 0.62, 1), a=0.8, stroke=7, blur=2.5))
        c.drawLine(a[0] + nx * 4, a[1] + ny * 4, b[0] + nx * 4, b[1] + ny * 4, paint((0.3, 0.14, 0.05, 1), a=0.5,
                                                                                     stroke=2.5, blur=1.5))
    c.restore()


# ---------------------------------------------------------------------------------------------
# Paper
# ---------------------------------------------------------------------------------------------
CYR_LINES = [
    "СОВЕРШЕННО СЕКРЕТНО", "ПГУ КГБ СССР · АРХИВ", "Дело № 4417 / агентурное", "резидентура: Лондон",
    "источник — «ХОЛА»", "материалы переданы через связника", "встреча состоялась 14.VI", "оценка: ценный",
    "получено: технические документы", "направлено в Центр", "операция продолжается", "конспиративная квартира",
]


def typed_lines(c, x, y, w, n, size=11, gap=1.7, seed=0, col=(0.12, 0.11, 0.10, 1), a=0.85, font="typewriter"):
    for i in range(n):
        s = CYR_LINES[int(hash01(seed, i) * len(CYR_LINES))]
        ww = T.text_width(font, s, size)
        if ww > w:
            s = s[: max(4, int(len(s) * w / ww))]
        T.draw(c, font, s, size, x + (hash01(seed, i, 2) - 0.5) * 1.5, y + i * size * gap, paint(col, a=a))


def paper_stack(c, x, y, w, h, n=11, seed=0, kraft_every=3, top=46):
    """Stack of envelopes/pages (x,y = top-left of the front edge) with a perspective top sheet."""
    # top sheet seen slightly from above, with typed Cyrillic lines
    tp = path_from_points([(x + 18, y - top), (x + w - 18, y - top), (x + w, y), (x, y)], True)
    c.drawPath(tp, paint(shader=lin((0, y - top), (0, y), [(0.97, 0.94, 0.86, 1), (0.88, 0.84, 0.75, 1)])))
    c.save()
    c.clipPath(tp, doAntiAlias=True)
    for i in range(6):
        yy = y - top + 9 + i * (top - 12) / 6
        sq = 0.86 + 0.14 * (i / 6)
        x0 = x + 30 + (1 - sq) * w * 0.5
        ln = (w - 70) * sq * (0.55 + 0.45 * hash01(seed, i, 40))
        c.drawLine(x0, yy, x0 + ln, yy, paint((0.15, 0.13, 0.12, 1), a=0.55, stroke=2.2 * sq))
    c.restore()
    th = h / n
    for i in range(n):
        yy = y + i * th
        off = (hash01(seed, i) - 0.5) * 10
        is_kraft = i % kraft_every == 0
        col = (0.70, 0.55, 0.36, 1) if is_kraft else (0.90, 0.86, 0.77, 1)
        c.drawRRect(rrect(x + off, yy, w, th * 0.92, 2.5), paint(col))
        c.drawLine(x + off + 3, yy + th * 0.92, x + off + w - 3, yy + th * 0.92,
                   paint((0, 0, 0, 1), a=0.35, stroke=1.2))
        if not is_kraft:
            for k in range(3):
                c.drawLine(x + off + 4, yy + th * (0.28 + k * 0.22), x + off + w - 4, yy + th * (0.28 + k * 0.22),
                           paint((0.6, 0.56, 0.48, 1), a=0.55, stroke=0.8))
    # light on the top edge, occlusion at the bottom
    c.drawRect(skia.Rect.MakeXYWH(x - 6, y, w + 12, h),
               paint(shader=lin((0, y), (0, y + h), [(1, 1, 1, 0.10), (0, 0, 0, 0), (0, 0, 0, 0.35)], [0, 0.5, 1])))


# ---------------------------------------------------------------------------------------------
# The scruffy bag
# ---------------------------------------------------------------------------------------------
def bag_body_path(w=640, h=430):
    p = skia.Path()
    bw, tw = w / 2, w / 2 - 46
    p.moveTo(-tw, -h)
    p.cubicTo(-tw * 0.5, -h + 18, tw * 0.5, -h + 18, tw, -h)          # sagging top edge
    p.cubicTo(bw + 26, -h * 0.55, bw + 14, -60, bw - 6, -34)           # bulging right side
    p.quadTo(bw - 10, 0, bw - 48, 0)
    p.cubicTo(bw * 0.4, 8, -bw * 0.4, 8, -bw + 48, 0)                  # bottom
    p.quadTo(-bw + 10, 0, -bw + 6, -34)
    p.cubicTo(-bw - 14, -60, -bw - 26, -h * 0.55, -tw, -h)
    p.close()
    return p


def draw_bag(c, t, reveal=0.0, open_amt=0.0, w=640, h=430, food=True, inside=None):
    """Bag with local origin at bottom-centre. reveal 0..1 sweeps a cutaway from top to bottom.
    inside(c) draws the cutaway content (called with clip applied)."""
    body = bag_body_path(w, h)
    tw = w / 2 - 46
    # handles (behind food, in front of back wall)
    for sgn in (-1, 1):
        hp = skia.Path()
        hx0, hx1 = sgn * 205, sgn * 70
        hp.moveTo(hx0, -h + 10)
        hp.cubicTo(sgn * 215, -h - 170, sgn * 60, -h - 175, hx1, -h + 12)
        c.drawPath(hp, paint((0.10, 0.06, 0.035, 1), stroke=30, cap="butt"))
        c.drawPath(hp, paint((0.30, 0.18, 0.10, 1), stroke=22, cap="butt"))
        c.drawPath(hp, paint((0.62, 0.44, 0.30, 1), a=0.45, stroke=4, blur=2))
    # opening (dark interior) + food poking out
    lip = skia.Path()
    lip.addOval(skia.Rect.MakeLTRB(-tw + 8, -h - 22 - open_amt * 14, tw - 8, -h + 26))
    c.drawPath(lip, paint(shader=lin((0, -h - 30), (0, -h + 26), [(0.16, 0.09, 0.05, 1), (0.03, 0.018, 0.012, 1)])))
    c.drawPath(lip, paint((0.62, 0.42, 0.26, 1), a=0.55, stroke=5, blur=1.5))
    if food:
        lift = open_amt * 26
        bread(c, -170, -h + 4 - lift * 0.6, 60, -h - 96 - lift, 38)
        salami(c, -40, -h + 12 - lift * 0.4, 150, -h - 120 - lift, 33, seed=1)
        salami(c, 70, -h + 14 - lift * 0.5, 235, -h - 70 - lift * 0.9, 30, seed=2)
        salami(c, -230, -h + 10 - lift * 0.3, -110, -h - 60 - lift * 0.8, 27, seed=3)
    # front face of the bag: leather + light
    c.save()
    c.clipPath(body, doAntiAlias=True)
    lt = leather_tex()
    c.drawPaint(paint(shader=tex_shader(lt, 1.0, 1.0, -w / 2 - 40, -h - 60)))
    c.drawPaint(paint(shader=lin((-w / 2, -h), (w / 2, 0), [(1, 0.85, 0.65, 0.16), (0, 0, 0, 0.0), (0, 0, 0, 0.62)],
                                 [0.0, 0.42, 1.0])))
    c.drawPaint(paint(shader=rad((-w * 0.2, -h * 0.74), w * 0.62, [(1, 0.84, 0.62, 0.30), (1, 0.8, 0.6, 0.0)])))
    # broad specular sheen following the bulge
    sheen = skia.Path()
    sheen.moveTo(-w / 2 + 40, -h * 0.82)
    sheen.cubicTo(-w * 0.30, -h * 0.98, w * 0.05, -h * 0.98, w * 0.22, -h * 0.86)
    c.drawPath(sheen, paint((1, 0.9, 0.75, 1), a=0.22, stroke=34, blur=22))
    c.drawPath(sheen, paint((1, 0.95, 0.85, 1), a=0.18, stroke=8, blur=5))
    # inner edge shadow (thickness / roundness)
    c.drawPath(body, paint((0, 0, 0, 1), a=0.65, stroke=46, blur=22))
    # creases and seams
    c.drawPath(_crease(-200, -330, -120, -40, 30), paint((0.06, 0.03, 0.02, 1), a=0.55, stroke=5, blur=3))
    c.drawPath(_crease(-194, -330, -114, -40, 30), paint((0.9, 0.7, 0.5, 1), a=0.12, stroke=3, blur=2))
    c.drawPath(_crease(150, -360, 210, -90, -26), paint((0.06, 0.03, 0.02, 1), a=0.5, stroke=5, blur=3))
    c.drawPath(_crease(40, -250, -20, -70, 18), paint((0.06, 0.03, 0.02, 1), a=0.35, stroke=4, blur=3))
    seam = skia.Path()
    seam.moveTo(-w / 2 + 30, -160)
    seam.cubicTo(-w / 6, -150, w / 6, -150, w / 2 - 30, -160)
    c.drawPath(seam, paint((0.05, 0.03, 0.02, 1), a=0.7, stroke=3))
    st = paint((0.80, 0.68, 0.50, 1), a=0.55, stroke=1.8)
    st.setPathEffect(skia.DashPathEffect.Make([9, 7], t * 0))
    seam2 = skia.Path()
    seam2.moveTo(-w / 2 + 30, -150)
    seam2.cubicTo(-w / 6, -140, w / 6, -140, w / 2 - 30, -150)
    c.drawPath(seam2, st)
    # brass zip pull
    c.drawRRect(rrect(tw - 90, -h + 14, 18, 42, 5), paint((0.55, 0.42, 0.18, 1)))
    c.drawRRect(rrect(tw - 87, -h + 18, 6, 30, 3), paint((1, 0.9, 0.6, 1), a=0.6))
    # bottom occlusion
    c.drawPaint(paint(shader=lin((0, -90), (0, 0), [(0, 0, 0, 0), (0, 0, 0, 0.55)])))
    c.restore()
    # edge rim light
    c.drawPath(body, paint((1, 0.8, 0.6, 1), a=0.18, stroke=2.5, blur=1.5))

    if reveal > 0:
        # cutaway: front face becomes a technical section, top -> bottom
        y_cut = -h - 40 + (h + 60) * reveal
        c.save()
        c.clipRect(skia.Rect.MakeLTRB(-w, -h - 200, w, y_cut))
        c.clipPath(body, doAntiAlias=True)
        c.drawPaint(paint((0.05, 0.035, 0.03, 1), a=0.96))
        # wall thickness hatch
        if inside is not None:
            inside(c)
        c.restore()
        c.save()
        c.clipRect(skia.Rect.MakeLTRB(-w, -h - 200, w, y_cut))
        dash = paint(PAL["amber_lt"], a=0.85, stroke=2.2)
        dash.setPathEffect(skia.DashPathEffect.Make([14, 9], -t * 40))
        c.drawPath(body, dash)
        c.restore()
        if reveal < 1:
            c.drawLine(-w / 2 - 40, y_cut, w / 2 + 40, y_cut, paint(PAL["amber_lt"], a=0.9, stroke=2.5))
            c.drawLine(-w / 2 - 40, y_cut, w / 2 + 40, y_cut, paint(PAL["amber"], a=0.6, stroke=14, blur=12))


def _crease(x0, y0, x1, y1, bend):
    p = skia.Path()
    p.moveTo(x0, y0)
    p.quadTo((x0 + x1) / 2 + bend, (y0 + y1) / 2, x1, y1)
    return p


def bag_inside(c, glow=0.0, h=430, w=640):
    """Contents in section view: food on top, KGB notes hidden underneath."""
    salami(c, -230, -h + 60, 30, -h + 40, 30, seed=4)
    salami(c, -10, -h + 66, 230, -h + 82, 28, seed=5)
    bread(c, -220, -h + 128, 200, -h + 120, 36, seed=6)
    # cloth / newspaper layer
    cl = skia.Path()
    cl.moveTo(-262, -h + 178)
    for k in range(9):
        cl.quadTo(-262 + k * 62 + 31, -h + 168 + (k % 2) * 16, -262 + (k + 1) * 62, -h + 178)
    cl.lineTo(262, -h + 196)
    cl.lineTo(-262, -h + 196)
    cl.close()
    c.drawPath(cl, paint((0.55, 0.52, 0.46, 1)))
    for k in range(5):
        c.drawLine(-240 + k * 100, -h + 186, -180 + k * 100, -h + 186, paint((0.2, 0.2, 0.2, 1), a=0.5, stroke=1.2))
    # the notes
    paper_stack(c, -235, -h + 250, 470, 150, n=11, seed=7, top=44)
    if glow > 0:
        c.drawRect(skia.Rect.MakeXYWH(-300, -h + 170, 600, 280),
                   paint(shader=rad((0, -h + 280), 330, [(1.0, 0.45, 0.30, 0.55), (1.0, 0.3, 0.2, 0.0)]),
                         a=glow, blend=skia.BlendMode.kScreen))
