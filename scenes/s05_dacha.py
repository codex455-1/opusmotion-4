"""S5 — The dacha: notes buried in milk churns under the floor; twelve years pass; nobody caught him."""
import math
import skia
from engine import text as T
from engine.core import (W, H, PAL, clamp, lerp, mix, ease_out_cubic, ease_in_out_cubic, ease_out_expo,
                         ease_in_expo, ease_in_cubic, ease_out_back, smoothstep, hash01, noise1, Track)
from engine.gfx import paint, lin, rad, layer, xform, rrect, path_from_points
from . import timeline as TL
from .common import cue, Typed, dust
from . import props as P

GROUND = 1000


def churn_path(w=150, h=270):
    hw = w / 2
    p = skia.Path()
    p.moveTo(-hw * 0.42, -h)
    p.lineTo(hw * 0.42, -h)
    p.lineTo(hw * 0.42, -h * 0.84)
    p.cubicTo(hw * 0.44, -h * 0.74, hw, -h * 0.70, hw, -h * 0.56)    # shoulder
    p.lineTo(hw, -h * 0.05)
    p.quadTo(hw, 0, hw * 0.92, 0)
    p.lineTo(-hw * 0.92, 0)
    p.quadTo(-hw, 0, -hw, -h * 0.05)
    p.lineTo(-hw, -h * 0.56)
    p.cubicTo(-hw, -h * 0.70, -hw * 0.44, -h * 0.74, -hw * 0.42, -h * 0.84)
    p.close()
    return p


def metal_shader(x0, x1, tint=(0.74, 0.77, 0.80), k=1.0):
    stops = [0.0, 0.10, 0.27, 0.36, 0.55, 0.82, 0.94, 1.0]
    vals = [0.22, 0.42, 0.96, 0.70, 0.50, 0.24, 0.40, 0.28]
    cols = [(tint[0] * v * k, tint[1] * v * k, tint[2] * v * k, 1) for v in vals]
    return lin((x0, 0), (x1, 0), cols, stops)


def draw_churn(c, x, y, lid_open=0.0, fill=0.0, t=0.0, w=150, h=270, seed=0):
    with xform(c, tx=x, ty=y):
        c.drawOval(skia.Rect.MakeLTRB(-w * 0.62, -14, w * 0.62, 18), paint((0, 0, 0, 1), a=0.6, blur=12))
        body = churn_path(w, h)
        c.drawPath(body, paint(shader=metal_shader(-w / 2, w / 2)))
        # horizontal ribs
        for fy in (0.12, 0.42):
            yy = -h * fy
            c.drawLine(-w / 2, yy, w / 2, yy, paint((0, 0, 0, 1), a=0.35, stroke=5))
            c.drawLine(-w / 2, yy - 4, w / 2, yy - 4, paint((1, 1, 1, 1), a=0.25, stroke=2))
        # soil grime creeping up from the bottom
        c.save()
        c.clipPath(body, doAntiAlias=True)
        c.drawRect(skia.Rect.MakeLTRB(-w, -h * 0.45, w, 0),
                   paint(shader=lin((0, -h * 0.45), (0, 0), [(0.20, 0.13, 0.08, 0.0), (0.18, 0.11, 0.07, 0.75)])))
        c.restore()
        # handles
        for sg in (-1, 1):
            hp = skia.Path()
            hp.moveTo(sg * w * 0.30, -h * 0.72)
            hp.cubicTo(sg * w * 0.62, -h * 0.80, sg * w * 0.66, -h * 0.60, sg * w * 0.47, -h * 0.58)
            c.drawPath(hp, paint((0.25, 0.27, 0.3, 1), stroke=7))
            c.drawPath(hp, paint((0.9, 0.92, 0.95, 1), a=0.5, stroke=2))
        # opening + contents (visible when the lid lifts)
        if lid_open > 0.02:
            mouth = skia.Rect.MakeLTRB(-w * 0.21, -h - 10, w * 0.21, -h + 10)
            c.drawOval(mouth, paint((0.03, 0.03, 0.035, 1)))
            if fill > 0:
                for k in range(int(3 + fill * 6)):
                    rx = (hash01(seed, k) - 0.5) * w * 0.24
                    c.drawRRect(rrect(rx - 8, -h - 6 - k * 1.5, 16, 12, 5), paint((0.9, 0.87, 0.78, 1), a=0.9))
        # lid (lifts and tilts)
        lift = ease_out_cubic(lid_open) * 70
        with xform(c, tx=0, ty=-h - lift, rot=-lid_open * 18):
            lid = skia.Path()
            lid.addRoundRect(skia.Rect.MakeLTRB(-w * 0.26, -26, w * 0.26, 4), 10, 10)
            c.drawPath(lid, paint(shader=metal_shader(-w * 0.26, w * 0.26, k=1.05)))
            c.drawRRect(rrect(-w * 0.09, -42, w * 0.18, 18, 6), paint(shader=metal_shader(-w * 0.09, w * 0.09)))


def draw_house(c, t, night=0.0, snow=0.0, light=1.0):
    x0, x1, top = 290, 790, 700
    # logs
    face = skia.Rect.MakeLTRB(x0, top, x1, GROUND)
    c.drawRect(face, paint((0.30, 0.19, 0.11, 1)))
    for k in range(int((GROUND - top) / 22) + 1):
        yy = top + k * 22
        c.drawRect(skia.Rect.MakeLTRB(x0, yy, x1, yy + 22),
                   paint(shader=lin((0, yy), (0, yy + 22), [(0.42, 0.28, 0.16, 1), (0.30, 0.19, 0.11, 1), (0.16, 0.10, 0.06, 1)])))
    for xx in (x0, x1):  # log ends
        for k in range(int((GROUND - top) / 22)):
            c.drawCircle(xx, top + 11 + k * 22, 10, paint((0.48, 0.34, 0.2, 1)))
            c.drawCircle(xx, top + 11 + k * 22, 10, paint((0.15, 0.09, 0.05, 1), stroke=1.5))
    # roof
    roof = path_from_points([(x0 - 60, top + 6), (540, 470), (x1 + 60, top + 6), (x1 + 40, top + 24), (540, 500),
                             (x0 - 40, top + 24)], True)
    c.drawPath(roof, paint((0.13, 0.14, 0.16, 1)))
    gable = path_from_points([(x0 - 10, top), (540, 505), (x1 + 10, top)], True)
    c.drawPath(gable, paint((0.36, 0.24, 0.14, 1)))
    for k in range(10):
        xx = x0 + 20 + k * 48
        c.drawLine(xx, top, xx, max(505 + abs(xx - 540) * 0.72, 505), paint((0.2, 0.12, 0.07, 1), a=0.6, stroke=3))
    c.drawPath(roof, paint((0.7, 0.75, 0.85, 1), a=0.25 + 0.2 * (1 - night), stroke=2))
    if snow > 0:
        sp = path_from_points([(x0 - 62, top + 4), (540, 466), (x1 + 62, top + 4), (x1 + 50, top - 6), (540, 452),
                               (x0 - 50, top - 6)], True)
        c.drawPath(sp, paint((0.92, 0.94, 0.98, 1), a=snow))
    # carved window frame (blue-painted nalichnik) with warm light
    wx, wy, ww, wh = 470, 760, 140, 150
    glow = light * (0.4 + 0.6 * night)
    c.drawRect(skia.Rect.MakeLTRB(wx - 60, wy - 60, wx + ww + 60, wy + wh + 60),
               paint(shader=rad((wx + ww / 2, wy + wh / 2), 200, [(1, 0.7, 0.35, 0.35 * glow), (1, 0.6, 0.3, 0)])))
    c.drawRect(skia.Rect.MakeXYWH(wx, wy, ww, wh), paint((1.0, 0.78, 0.45, 1), a=0.25 + 0.75 * glow))
    c.drawLine(wx + ww / 2, wy, wx + ww / 2, wy + wh, paint((0.25, 0.35, 0.55, 1), stroke=7))
    c.drawLine(wx, wy + wh * 0.4, wx + ww, wy + wh * 0.4, paint((0.25, 0.35, 0.55, 1), stroke=7))
    c.drawRect(skia.Rect.MakeXYWH(wx - 10, wy - 10, ww + 20, wh + 20), paint((0.28, 0.40, 0.62, 1), stroke=14))
    crown = path_from_points([(wx - 26, wy - 18), (wx + ww / 2, wy - 64), (wx + ww + 26, wy - 18)], True)
    c.drawPath(crown, paint((0.28, 0.40, 0.62, 1)))
    c.drawRect(skia.Rect.MakeXYWH(wx - 24, wy + wh + 12, ww + 48, 14), paint((0.28, 0.40, 0.62, 1)))
    # night-time darkening of the facade (clipped to the house silhouette)
    sil = skia.Path(roof)
    sil.addRect(face)
    sil.addPath(gable)
    c.save()
    c.clipPath(sil, doAntiAlias=True)
    c.drawRect(skia.Rect.MakeLTRB(x0 - 70, 460, x1 + 70, GROUND), paint((0.02, 0.03, 0.06, 1), a=0.55 * night))
    c.restore()


def draw_birch(c, x, h, seed):
    c.drawLine(x, GROUND, x + (hash01(seed) - 0.5) * 30, GROUND - h, paint((0.80, 0.80, 0.78, 1), stroke=14))
    for k in range(9):
        yy = GROUND - h * (0.1 + 0.85 * hash01(seed, k))
        c.drawLine(x - 7, yy, x + 2 + hash01(seed, k, 2) * 6, yy + 2, paint((0.1, 0.1, 0.1, 1), stroke=3))
    c.drawCircle(x, GROUND - h - 30, 90, paint((0.12, 0.16, 0.12, 1), a=0.85, blur=30))


class S5:
    name = "dacha"

    def __init__(self):
        self.start = TL.LINE_START["L06"] - 0.20
        self.end = TL.LINE_START["L08"] - 0.20
        self.t_house = TL.word_time("L06", "house")
        self.t_buried = TL.word_time("L06", "buried")
        self.t_churns = TL.word_time("L06", "churns")
        self.t_under = TL.word_time("L06", "under")
        self.t_twelve = TL.word_time("L07", "twelve")
        self.t_nobody = TL.word_time("L07", "nobody")
        self.t_l7end = TL.LINE_END["L07"]
        s = self.start
        self.cam_y = Track([(s, 760.0), (self.t_buried - 0.1, 800.0), (self.t_churns, 1300.0, ease_in_out_cubic),
                            (self.t_twelve - 0.15, 1310.0), (self.t_twelve + 0.6, 1060.0, ease_in_out_cubic),
                            (self.end, 1080.0)])
        self.cam_s = Track([(s, 1.18), (self.t_buried - 0.1, 1.12), (self.t_churns, 1.22, ease_in_out_cubic),
                            (self.t_twelve - 0.15, 1.25), (self.t_twelve + 0.6, 0.86, ease_in_out_cubic),
                            (self.end, 0.84)])
        self.lid_t = [self.t_churns - 0.15, self.t_churns + 0.0, self.t_churns + 0.15]
        for i, lt in enumerate(self.lid_t):
            cue(lt + 0.9, "metal_lid", -9 - i, (i - 1) * 0.3, var=i % 2)
        cue(self.t_buried - 0.2, "whoosh_soft", -12, 0.0, var=1, align="peak", at=self.t_buried + 0.2)
        cue(self.t_buried, "dirt", -10, 0.0, var=0)
        cue(self.t_churns + 0.3, "dirt", -12, 0.2, var=1)
        cue(s, "wind_soft", -16, 0.0, dur=self.end - s + 0.3, fade_in=0.6, fade_out=0.8, loop=True)
        cue(self.t_twelve - 0.1, "clock_tick", -10, 0.0, dur=self.t_nobody - self.t_twelve + 0.5, fade_in=0.05,
            fade_out=0.3, loop=True)
        cue(self.t_twelve - 0.4, "reverse_swell", -12, 0.0, var=0, align="peak", at=self.t_twelve)
        cue(self.t_nobody + 0.05, "sub_boom", -12, 0.0, var=1)
        self.floor_lab = Typed("FLOORBOARDS", "mono_med", 22, 830, GROUND + 52, self.t_under, cps=30,
                               color=PAL["amber_lt"], track=0.14, seed=501, gain=-9, caret=False)
        # year odometer ticks
        k = 0
        for yr in range(1973, 1985):
            tt = lerp(self.t_twelve + 0.05, self.t_nobody - 0.05, (yr - 1973) / 11)
            cue(tt, "tick", -11, 0.0, var=k % 4)
            k += 1

    def draw(self, c, t):
        lt = t - self.start
        # time-lapse parameters
        tl = clamp((t - self.t_twelve) / (self.t_nobody - self.t_twelve))
        cycles = tl * 6
        night = 0.55 + 0.45 * math.sin(cycles * 2 * math.pi - 1.2) if 0 < tl < 1 else (0.7 if tl >= 1 else 0.55)
        night = clamp(night)
        snow = clamp(math.sin(tl * 12 * math.pi / 2.0) * 1.4) if 0 < tl < 1 else 0.0
        settle = smoothstep(self.t_nobody, self.t_nobody + 0.8, t)
        night = lerp(night, 0.85, settle)
        sky_top = mix((0.12, 0.17, 0.28, 1), (0.015, 0.02, 0.045, 1), night)
        sky_bot = mix((0.62, 0.45, 0.35, 1), (0.05, 0.07, 0.12, 1), night)
        cy, cs = self.cam_y(t), self.cam_s(t)
        c.save()
        c.translate(540, 1060)
        c.scale(cs, cs)
        c.translate(-540, -cy)
        # sky
        c.drawRect(skia.Rect.MakeLTRB(-600, -900, W + 600, GROUND), paint(shader=lin((0, 0), (0, GROUND), [sky_top, sky_bot])))
        for k in range(70):  # stars
            sx, sy = hash01(51, k) * (W + 600) - 300, hash01(52, k) * 900 - 200
            c.drawCircle(sx, sy, 1.2 + hash01(53, k) * 1.6, paint((1, 1, 1, 1), a=night * (0.4 + 0.6 * hash01(54, k))))
        c.drawCircle(820, 300, 34, paint((1, 0.97, 0.9, 1), a=0.25 + 0.6 * night, blur=2))
        c.drawCircle(820, 300, 90, paint((1, 0.95, 0.85, 1), a=0.12 * night, blur=40))
        for i, (bx, bh) in enumerate([(120, 620), (190, 520), (930, 580), (985, 660), (60, 480)]):
            draw_birch(c, bx, bh, i)
        draw_house(c, t, night=night, snow=snow, light=1 - 0.8 * settle)
        # ground & section cut
        c.drawRect(skia.Rect.MakeLTRB(-600, GROUND, W + 600, GROUND + 1400),
                   paint(shader=P.soil_tex().makeShader(skia.TileMode.kMirror, skia.TileMode.kMirror,
                                                        skia.SamplingOptions(skia.FilterMode.kLinear))))
        c.drawRect(skia.Rect.MakeLTRB(-600, GROUND, W + 600, GROUND + 1400),
                   paint(shader=lin((0, GROUND), (0, GROUND + 900), [(0, 0, 0, 0.1), (0, 0, 0, 0.75)])))
        c.drawRect(skia.Rect.MakeLTRB(-600, GROUND - 6, W + 600, GROUND + 8), paint((0.16, 0.22, 0.12, 1)))
        if snow > 0:
            c.drawRect(skia.Rect.MakeLTRB(-600, GROUND - 14, W + 600, GROUND + 2), paint((0.92, 0.94, 0.98, 1), a=snow))
        # floorboards cutaway under the house
        fb = smoothstep(self.t_buried - 0.2, self.t_buried + 0.3, t)
        c.drawRect(skia.Rect.MakeLTRB(290, GROUND, 790, GROUND + 26), paint((0.40, 0.27, 0.15, 1)))
        for k in range(10):
            c.drawLine(290 + k * 50, GROUND, 290 + k * 50, GROUND + 26, paint((0.15, 0.09, 0.05, 1), stroke=2))
        hl = smoothstep(self.t_under - 0.1, self.t_under + 0.3, t) * (1 - smoothstep(self.t_twelve - 0.3, self.t_twelve, t))
        if hl > 0:
            c.drawRect(skia.Rect.MakeLTRB(286, GROUND - 4, 794, GROUND + 30), paint(PAL["amber_lt"], a=0.9 * hl, stroke=2.5))
            self.floor_lab.draw(c, t, alpha=hl)
        # dug pit (section) + churns
        if fb > 0:
            pit = skia.Path()
            pit.moveTo(310, GROUND + 26)
            pit.cubicTo(295, GROUND + 200, 300, GROUND + 520, 350, GROUND + 565)
            pit.lineTo(730, GROUND + 565)
            pit.cubicTo(780, GROUND + 520, 785, GROUND + 200, 770, GROUND + 26)
            pit.close()
            c.drawPath(pit, paint((0.07, 0.045, 0.03, 1), a=0.85 * fb))
            dash = paint(PAL["amber_lt"], a=0.5 * fb, stroke=1.8)
            dash.setPathEffect(skia.DashPathEffect.Make([10, 8], -t * 25))
            c.drawPath(pit, dash)
            for i, x in enumerate((392, 540, 688)):
                rise = ease_out_expo(clamp((t - (self.t_buried + i * 0.12)) / 0.7))
                lid = smoothstep(self.lid_t[i], self.lid_t[i] + 0.3, t) * (1 - smoothstep(self.lid_t[i] + 0.75, self.lid_t[i] + 0.95, t))
                fill = clamp((t - self.lid_t[i]) / 0.8) + tl
                draw_churn(c, x, GROUND + 540 + (1 - rise) * 60, lid_open=lid, fill=fill, t=t, w=120, h=230, seed=i)
                # rolled notes dropping in
                for k in range(4):
                    dp = clamp((t - (self.lid_t[i] + 0.15 + k * 0.12)) / 0.45)
                    if 0 < dp < 1:
                        yy = lerp(GROUND - 120, GROUND + 310, ease_in_cubic(dp))
                        c.drawRRect(rrect(x - 10 + (k - 1.5) * 5, yy, 20, 13, 6), paint((0.93, 0.9, 0.8, 1), a=1 - dp * 0.5))
        c.restore()
        # year odometer during the time-lapse
        ya = smoothstep(self.t_twelve - 0.1, self.t_twelve + 0.25, t) * (1 - smoothstep(self.end - 0.35, self.end, t))
        if ya > 0:
            yr = 1972 + clamp((t - self.t_twelve) / (self.t_nobody - self.t_twelve)) * 12
            base = int(yr)
            frac = ease_in_out_cubic(yr - base) if yr < 1984 else 0.0
            for k, yy in ((0, 0.0), (1, 1.0)):
                v = min(base + k, 1984)
                dy = (k - frac) * 120
                a_ = ya * (1 - abs(k - frac))
                c.save()
                c.clipRect(skia.Rect.MakeLTRB(0, 1560, W, 1720))
                T.draw(c, "news", str(v), 150, 540, 1690 + dy, paint(PAL["cream"], a=a_), tracking=0.02, align="center")
                c.restore()
            T.draw(c, "mono", "1972 — 1984", 20, 540, 1752, paint(PAL["muted"], a=ya * 0.9), tracking=0.3, align="center")
        dust(c, t, n=24, seed=17, region=(0, 300, W, 1500), color=(0.9, 0.95, 1.0, 1), alpha=0.35 * snow, size=(1.5, 4),
             drift=(-8, 40))
        # exit: rise into the night sky (hand-off to the Europe map)
        ex = ease_in_cubic(clamp((t - (self.end - 0.45)) / 0.45))
        if ex > 0:
            c.drawRect(skia.Rect.MakeWH(W, H), paint((0.015, 0.02, 0.03, 1), a=ex))

    def post(self, t):
        return dict(bloom=0.36, bloom_thresh=0.72, halation=0.08, vignette=0.72, grain=0.05,
                    lift=(0.010, 0.013, 0.02), gain=(1.03, 1.0, 0.97), ca=0.0018)

    def mb(self, t):
        if self.t_buried - 0.1 < t < self.t_churns + 0.3 or self.t_twelve - 0.2 < t < self.t_twelve + 0.7:
            return 4
        return 1
