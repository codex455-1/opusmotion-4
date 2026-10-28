"""S7 — The British gave him a cup of tea."""
import math
import skia
from engine import text as T
from engine.core import (W, H, PAL, clamp, lerp, mix, ease_out_cubic, ease_in_out_cubic, ease_out_expo,
                         ease_in_cubic, ease_out_back, smoothstep, hash01, noise1)
from engine.gfx import paint, lin, rad, layer, xform, rrect, path_from_points
from . import timeline as TL
from .common import cue, Typed, background, dust, light_cone
from . import props as P


def steam(c, t, x, y, n=4, height=520, alpha=1.0, seed=0):
    for k in range(n):
        pts = []
        ph = t * (0.55 + 0.1 * k) + k * 1.7
        for i in range(26):
            u = i / 25
            sway = noise1(u * 2.2 - t * 0.8 + k * 3.1, seed + k) * 48 * u + math.sin(u * 5 + ph) * 14 * u
            pts.append((x + (k - (n - 1) / 2) * 26 + sway, y - u * height))
        p = path_from_points(pts)
        a = alpha * (0.10 + 0.04 * math.sin(ph))
        c.drawPath(p, paint((1, 0.97, 0.92, 1), a=a, stroke=26, blur=18))
        c.drawPath(p, paint((1, 0.98, 0.95, 1), a=a * 0.8, stroke=7, blur=6))


def teacup(c, t, pour=1.0):
    # saucer
    c.drawOval(skia.Rect.MakeLTRB(-330, -40, 330, 120), paint((0, 0, 0, 1), a=0.6, blur=26))
    c.drawOval(skia.Rect.MakeLTRB(-320, -70, 320, 90), paint(shader=lin((0, -70), (0, 90), [(0.97, 0.96, 0.93, 1), (0.70, 0.68, 0.64, 1)])))
    c.drawOval(skia.Rect.MakeLTRB(-320, -70, 320, 90), paint((0.17, 0.30, 0.55, 1), stroke=7))   # blue band
    c.drawOval(skia.Rect.MakeLTRB(-300, -60, 300, 76), paint((0.80, 0.64, 0.30, 1), a=0.9, stroke=2))  # gilt line
    c.drawOval(skia.Rect.MakeLTRB(-170, -32, 170, 40), paint((0, 0, 0, 1), a=0.22, blur=10))
    # cup body
    body = skia.Path()
    body.moveTo(-200, -300)
    body.cubicTo(-200, -120, -160, -10, 0, -6)
    body.cubicTo(160, -10, 200, -120, 200, -300)
    body.close()
    c.drawPath(body, paint(shader=lin((-200, 0), (200, 0), [(0.62, 0.60, 0.57, 1), (0.98, 0.97, 0.95, 1), (0.92, 0.91, 0.88, 1),
                                                           (0.55, 0.53, 0.50, 1)], [0.0, 0.32, 0.55, 1.0])))
    c.save()
    c.clipPath(body, doAntiAlias=True)
    c.drawRect(skia.Rect.MakeLTRB(-220, -250, 220, -232), paint((0.17, 0.30, 0.55, 1)))
    c.drawRect(skia.Rect.MakeLTRB(-220, -226, 220, -222), paint((0.80, 0.64, 0.30, 1)))
    c.drawLine(-120, -280, -140, -60, paint((1, 1, 1, 1), a=0.55, stroke=14, blur=8))
    c.restore()
    # handle
    hd = skia.Path()
    hd.moveTo(190, -250)
    hd.cubicTo(300, -260, 310, -120, 175, -110)
    c.drawPath(hd, paint((0.55, 0.53, 0.5, 1), stroke=30))
    c.drawPath(hd, paint((0.95, 0.94, 0.92, 1), stroke=20))
    # rim + tea
    c.drawOval(skia.Rect.MakeLTRB(-200, -330, 200, -270), paint((0.98, 0.97, 0.95, 1)))
    c.drawOval(skia.Rect.MakeLTRB(-186, -324, 186, -276), paint(shader=rad((-40, -306), 200, [(0.62, 0.32, 0.10, 1), (0.30, 0.12, 0.04, 1)])))
    c.drawOval(skia.Rect.MakeLTRB(-120, -318, 20, -300), paint((1, 0.9, 0.75, 1), a=0.35, blur=6))
    c.drawOval(skia.Rect.MakeLTRB(-200, -330, 200, -270), paint((0.80, 0.64, 0.30, 1), a=0.9, stroke=2.5))


class S7:
    name = "tea"

    def __init__(self):
        self.start = TL.LINE_START["L09"] - 0.20
        self.end = TL.LINE_START["L10"] - 0.20
        self.t_gave = TL.word_time("L09", "gave")
        self.t_cup = TL.word_time("L09", "cup")
        self.t_tea = TL.word_time("L09", "tea")
        self.land = self.t_cup - 0.05
        cue(self.land, "teacup", -6, 0.05, var=0)
        cue(self.start, "room_archive", -14, 0.0, dur=self.end - self.start + 0.3, fade_in=0.3, fade_out=0.4, loop=True)
        cue(self.t_gave, "steam", -18, 0.0, dur=self.end - self.t_gave + 0.2, fade_in=0.4, fade_out=0.4, loop=True)
        cue(self.end - 0.4, "whoosh_soft", -12, 0.0, var=3, align="peak", at=self.end)
        self.label = Typed("BRITISH EMBASSY  ·  24 MARCH 1992", "mono", 22, W / 2, 1720, self.t_tea + 0.05, cps=34,
                           color=PAL["muted"], track=0.18, align="center", seed=701, gain=-11, caret=False)

    def draw(self, c, t):
        background(c, t, top=(0.07, 0.05, 0.035, 1), bottom=(0.02, 0.015, 0.012, 1), light=(560, 1000),
                   light_col=PAL["amber_lt"], light_r=1000, light_a=0.30, haze=0.03, seed=5)
        lt = t - self.start
        # table
        wt = P.wood_tex(seed=9, tint=(0.34, 0.21, 0.12))
        m = skia.Matrix()
        m.setAll(1.2, 0.3, -200, 0, 0.6, 1050, 0, 0.0003, 1)
        c.drawRect(skia.Rect.MakeLTRB(-200, 1050, W + 200, H + 100),
                   paint(shader=wt.makeShader(skia.TileMode.kMirror, skia.TileMode.kMirror,
                                              skia.SamplingOptions(skia.FilterMode.kLinear), m)))
        c.drawRect(skia.Rect.MakeLTRB(-200, 1050, W + 200, H + 100),
                   paint(shader=lin((0, 1050), (0, H), [(0, 0, 0, 0.6), (0, 0, 0, 0.15), (0, 0, 0, 0.8)], [0, 0.3, 1])))
        c.drawRect(skia.Rect.MakeWH(W, H), paint(shader=rad((540, 1250), 700, [(1, 0.72, 0.42, 0.25), (1, 0.7, 0.4, 0.0)])))
        # cup slides in and lands
        arrive = ease_out_expo(clamp((t - (self.land - 0.55)) / 0.6))
        x = lerp(1250, 540, arrive)
        rot = lerp(10, 0, arrive)
        push = 1.0 + 0.05 * clamp(lt / 3.0)
        c.save()
        c.translate(540, 1100)
        c.scale(push, push)
        c.translate(-540, -1100)
        with xform(c, tx=x, ty=1360, rot=rot, s=1.05):
            teacup(c, t)
        sa = smoothstep(self.land, self.land + 0.6, t)
        steam(c, t, x - 20, 1360 - 330 * 1.05, n=4, height=560, alpha=sa)
        c.restore()
        dust(c, t, n=24, seed=21, region=(100, 500, 880, 1000), alpha=0.35, size=(1.2, 4.0))
        self.label.draw(c, t)
        light_cone(c, (540, -50), 1300, 560, a=0.05, blur=60)
        fi = 1 - ease_out_cubic(clamp(lt / 0.35))
        if fi > 0:
            c.drawRect(skia.Rect.MakeWH(W, H), paint((0.10, 0.07, 0.04, 1), a=fi))
        ex = ease_in_cubic(clamp((t - (self.end - 0.3)) / 0.3))
        if ex > 0:
            c.drawRect(skia.Rect.MakeWH(W, H), paint((0.015, 0.02, 0.03, 1), a=ex))

    def post(self, t):
        return dict(bloom=0.30, bloom_thresh=0.78, halation=0.09, vignette=0.7, grain=0.048,
                    lift=(0.016, 0.012, 0.01), gain=(1.05, 0.99, 0.92), ca=0.0016)

    def mb(self, t):
        return 4 if self.land - 0.6 < t < self.land + 0.1 else 1
