"""S10 — Melita Norwood: a grandmother in Bexleyheath, unmasked at 87, who passed Tube Alloys secrets to Moscow."""
import math
import skia
from engine import text as T
from engine.core import (W, H, PAL, clamp, lerp, mix, ease_out_cubic, ease_in_out_cubic, ease_out_expo,
                         ease_in_expo, ease_in_cubic, ease_out_back, smoothstep, hash01, noise1)
from engine.gfx import paint, lin, rad, layer, xform, rrect, paper_image, path_from_points, trim_path, np_to_image, fbm
from . import timeline as TL
from .common import cue, Typed, dust, redaction
import functools
import numpy as np


@functools.lru_cache(maxsize=None)
def brick_img(w=640, h=520):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    bh, bw = 18.0, 46.0
    row = np.floor(yy / bh)
    off = (row % 2) * bw / 2
    mortar = ((yy % bh) < 2.2) | (((xx + off) % bw) < 2.2)
    n = fbm((h, w), base=8, octaves=2, seed=31)
    tone = 0.75 + 0.25 * fbm((h, w), base=30, octaves=2, seed=32)
    var = np.array([[hash01(int(r), int(c)) for c in range(int(w / bw) + 2)] for r in range(int(h / bh) + 1)], np.float32)
    bv = var[row.astype(int), ((xx + off) / bw).astype(int)]
    base = np.stack([0.42 + 0.10 * bv, 0.20 + 0.05 * bv, 0.14 + 0.03 * bv], -1) * (tone * (0.85 + 0.3 * n))[..., None]
    base[mortar] = np.array([0.42, 0.40, 0.36]) * (0.8 + 0.2 * n[mortar])[..., None]
    return np_to_image(np.concatenate([np.clip(base, 0, 1), np.ones((h, w, 1))], -1).astype(np.float32))


def house(c, t, glow=1.0):
    """1930s semi-detached at dusk: brick, white bay window, tiled hip roof, hedge, gate, street lamp."""
    x0, x1, top, bot = 250, 830, 760, 1240
    c.drawRect(skia.Rect.MakeLTRB(x0, top, x1, bot), paint(shader=brick_img().makeShader(
        skia.TileMode.kRepeat, skia.TileMode.kRepeat, skia.SamplingOptions(skia.FilterMode.kLinear))))
    roof = path_from_points([(x0 - 40, top + 10), (x0 + 90, 560), (x1 - 90, 560), (x1 + 40, top + 10)], True)
    c.drawPath(roof, paint(shader=lin((0, 560), (0, top), [(0.20, 0.13, 0.11, 1), (0.30, 0.17, 0.13, 1)])))
    for k in range(9):
        yy = 575 + k * 22
        c.drawLine(x0 + 60 - k * 12, yy, x1 - 60 + k * 12, yy, paint((0.08, 0.05, 0.04, 1), a=0.5, stroke=2))
    c.drawRect(skia.Rect.MakeLTRB(x1 - 170, 500, x1 - 120, 600), paint((0.33, 0.17, 0.12, 1)))
    c.drawRect(skia.Rect.MakeLTRB(x1 - 176, 492, x1 - 114, 506), paint((0.25, 0.14, 0.1, 1)))
    # bay window (two storeys) with warm light and net curtains
    for (wy, wh) in ((800, 170), (1010, 190)):
        bx0, bx1 = 300, 560
        c.drawRect(skia.Rect.MakeLTRB(bx0 - 14, wy - 14, bx1 + 14, wy + wh + 14), paint((0.90, 0.88, 0.84, 1)))
        c.drawRect(skia.Rect.MakeLTRB(bx0, wy, bx1, wy + wh),
                   paint(shader=lin((0, wy), (0, wy + wh), [(1.0, 0.80, 0.50, 1), (0.85, 0.55, 0.30, 1)]), a=0.35 + 0.65 * glow))
        for k in range(1, 4):
            xx = bx0 + (bx1 - bx0) * k / 4
            c.drawLine(xx, wy, xx, wy + wh, paint((0.92, 0.9, 0.86, 1), stroke=8))
        c.drawLine(bx0, wy + wh * 0.3, bx1, wy + wh * 0.3, paint((0.92, 0.9, 0.86, 1), stroke=6))
        for k in range(26):  # net curtain folds
            xx = bx0 + 6 + k * 10
            c.drawLine(xx, wy + wh * 0.32, xx, wy + wh - 4, paint((1, 0.97, 0.9, 1), a=0.18, stroke=4))
        c.drawRect(skia.Rect.MakeLTRB(bx0 - 60, wy - 60, bx1 + 60, wy + wh + 60),
                   paint(shader=rad(((bx0 + bx1) / 2, wy + wh / 2), 260, [(1, 0.7, 0.4, 0.22 * glow), (1, 0.7, 0.4, 0)])))
    # front door + porch
    c.drawRect(skia.Rect.MakeLTRB(640, 1010, 760, 1240), paint((0.10, 0.20, 0.17, 1)))
    c.drawRect(skia.Rect.MakeLTRB(662, 1030, 738, 1110), paint((1.0, 0.78, 0.45, 1), a=0.55 * glow))
    c.drawCircle(735, 1140, 5, paint((0.85, 0.7, 0.35, 1)))
    porch = path_from_points([(615, 1000), (700, 950), (785, 1000)], True)
    c.drawPath(porch, paint((0.22, 0.13, 0.1, 1)))
    # upper window right
    c.drawRect(skia.Rect.MakeLTRB(625, 820, 775, 950), paint((0.9, 0.88, 0.84, 1)))
    c.drawRect(skia.Rect.MakeLTRB(637, 832, 763, 938), paint((0.12, 0.14, 0.2, 1)))
    c.drawLine(700, 832, 700, 938, paint((0.9, 0.88, 0.84, 1), stroke=6))
    # dusk shading on the facade (clipped to the building)
    sil = skia.Path(roof)
    sil.addRect(skia.Rect.MakeLTRB(x0, top, x1, bot))
    c.save()
    c.clipPath(sil, doAntiAlias=True)
    c.drawRect(skia.Rect.MakeLTRB(x0 - 50, 480, x1 + 50, bot), paint(shader=lin((x0, 0), (x1, 0), [(0.02, 0.03, 0.07, 0.15), (0.02, 0.03, 0.07, 0.55)])))
    c.restore()
    # hedge + low wall + gate
    hedge = skia.Path()
    hedge.moveTo(0, 1250)
    for k in range(28):
        hedge.quadTo(k * 40 + 20, 1170 + (hash01(k, 4) - 0.5) * 30, (k + 1) * 40, 1210 + (hash01(k, 5) - 0.5) * 20)
    hedge.lineTo(W, 1330)
    hedge.lineTo(0, 1330)
    hedge.close()
    c.save()
    c.clipRect(skia.Rect.MakeLTRB(0, 0, 600, H))
    c.drawPath(hedge, paint((0.06, 0.11, 0.07, 1)))
    c.restore()
    c.save()
    c.clipRect(skia.Rect.MakeLTRB(800, 0, W, H))
    c.drawPath(hedge, paint((0.06, 0.11, 0.07, 1)))
    c.restore()
    c.drawRect(skia.Rect.MakeLTRB(0, 1300, W, 1350), paint((0.30, 0.22, 0.18, 1)))
    for k in range(6):
        c.drawLine(612 + k * 34, 1210, 612 + k * 34, 1330, paint((0.85, 0.83, 0.78, 1), a=0.8, stroke=6))
    c.drawLine(605, 1220, 790, 1220, paint((0.85, 0.83, 0.78, 1), a=0.8, stroke=6))
    # pavement
    c.drawRect(skia.Rect.MakeLTRB(0, 1350, W, H), paint(shader=lin((0, 1350), (0, H), [(0.10, 0.10, 0.11, 1), (0.03, 0.03, 0.035, 1)])))
    # street lamp (sodium)
    c.drawLine(940, 1500, 940, 700, paint((0.08, 0.08, 0.09, 1), stroke=14))
    c.drawLine(940, 712, 880, 712, paint((0.08, 0.08, 0.09, 1), stroke=8))
    c.drawCircle(872, 724, 14, paint((1.0, 0.72, 0.35, 1)))
    c.drawCircle(872, 724, 120, paint((1.0, 0.62, 0.28, 1), a=0.25, blur=50))
    pool = skia.Path()
    pool.addOval(skia.Rect.MakeLTRB(620, 1380, 1180, 1560))
    c.drawPath(pool, paint((1.0, 0.6, 0.3, 1), a=0.15, blur=40))


class S10:
    name = "norwood"

    def __init__(self):
        self.start = TL.LINE_START["L12"] - 0.20
        self.end = TL.LINE_END["L12"] + 0.20
        self.t_nor = TL.word_time("L12", "norwood")
        self.t_unm = TL.word_time("L12", "unmasked")
        self.t_who = TL.word_time("L12", "who")
        self.t_atomic = TL.word_time("L12", "atomic")
        self.t_secrets = TL.word_time("L12", "secrets")
        self.t_moscow = TL.word_time("L12", "moscow")
        self.cut = self.t_who - 0.25
        cx = 120
        y0 = 1330
        t0 = self.start + 0.55
        self.lines = []
        spec = [("NORWOOD, Melita", "typewriter", 44, PAL["cream"], 22),
                ("BEXLEYHEATH  ·  SOUTH-EAST LONDON", "mono", 22, PAL["muted"], 40),
                ("KGB CODENAME:  HOLA", "mono_med", 26, PAL["cream"], 34),
                ("UNMASKED:  SEPTEMBER 1999  ·  AGED 87", "mono_med", 26, PAL["cream"], 34)]
        ys = [y0 + 70, y0 + 116, y0 + 176, y0 + 226]
        starts = [t0, None, None, self.t_unm - 0.1]
        for i, ((txt, f, sz, col, cps), yy) in enumerate(zip(spec, ys)):
            st = starts[i] if starts[i] is not None else self.lines[-1].t_end + 0.06
            self.lines.append(Typed(txt, f, sz, cx + 40, yy, st, cps=cps, color=col, track=0.06 if f != "typewriter" else 0.02,
                                    seed=1001 + i, gain=-5 if i == 0 else -8, caret=(i == 3)))
        self.card_y = y0
        cue(self.start, "room_london_night", -12, 0.0, dur=self.cut - self.start + 0.4, fade_in=0.3, fade_out=0.4, loop=True)
        cue(self.start + 0.35, "paper_slide", -9, 0.0, var=2)
        cue(self.cut - 0.2, "whoosh_soft", -11, 0.0, var=1, align="peak", at=self.cut)
        cue(self.cut + 0.05, "paper_slide", -8, 0.1, var=3)
        cue(self.t_atomic - 0.05, "redact_swipe", -9, -0.1, var=0)
        cue(self.t_atomic + 0.25, "redact_swipe", -11, 0.1, var=1)
        cue(self.t_secrets - 0.05, "reverse_swell", -10, 0.0, var=1, align="peak", at=self.t_moscow)
        cue(self.t_moscow - 0.02, "sub_boom", -5, 0.0, var=0)
        cue(self.t_moscow, "emph_thump", -8, 0.2, var=0)
        self.doc_lines = [Typed("MOST SECRET", "typewriter", 24, 200, 820, self.cut + 0.15, cps=30, color=PAL["red"], track=0.2,
                                seed=1101, gain=-9, caret=False),
                          Typed("TUBE ALLOYS", "typewriter", 58, 200, 900, self.cut + 0.45, cps=18, color=(0.12, 0.11, 0.1, 1),
                                track=0.08, seed=1102, gain=-4, caret=False),
                          Typed("Britain's atomic bomb project", "mono", 22, 200, 945, self.cut + 1.1, cps=40,
                                color=(0.35, 0.32, 0.28, 1), track=0.04, seed=1103, gain=-11, caret=False)]
        self.dest = Typed("MOSCOW", "sans_semi", 40, 0, 0, self.t_moscow - 0.02, cps=24, color=PAL["red"], track=0.22,
                          seed=1111, gain=-6, caret=False)

    def draw(self, c, t):
        lt = t - self.start
        if t < self.cut:
            # dusk suburb + dossier card
            c.drawRect(skia.Rect.MakeWH(W, H), paint(shader=lin((0, 0), (0, 1300), [(0.05, 0.06, 0.12, 1), (0.30, 0.22, 0.30, 1)])))
            push = 1.0 + 0.05 * clamp(lt / 4.0)
            c.save()
            c.translate(540, 1000)
            c.scale(push, push)
            c.translate(-540, -980)
            house(c, t)
            c.restore()
            dust(c, t, n=18, seed=31, region=(600, 600, 480, 600), color=(1, 0.75, 0.45, 1), alpha=0.3)
            ca = ease_out_expo(clamp((t - (self.start + 0.3)) / 0.8))
            cy = lerp(H + 50, self.card_y, ca)
            with xform(c, tx=0, ty=cy - self.card_y):
                c.drawRRect(rrect(100 + 10, self.card_y + 16, 880, 300, 14), paint((0, 0, 0, 1), a=0.6, blur=26))
                c.drawRRect(rrect(100, self.card_y, 880, 300, 14), paint((0.03, 0.035, 0.05, 1), a=0.88))
                c.drawRRect(rrect(100, self.card_y, 880, 300, 14), paint(PAL["cream"], a=0.2, stroke=1.5))
                c.drawRect(skia.Rect.MakeXYWH(100, self.card_y, 8, 300), paint(PAL["red"]))
                for ln in self.lines:
                    ln.draw(c, t)
                hola = self.lines[2]
                if t > hola.t_end:
                    hp = ease_out_cubic(clamp((t - hola.t_end) / 0.3))
                    x1 = hola.x + hola.width()
                    c.drawLine(x1 - T.text_width("mono_med", "HOLA", 26, 0.06), hola.y + 8, x1 - (1 - hp) * 60, hola.y + 8,
                               paint(PAL["red"], stroke=3))
            fi = 1 - ease_out_cubic(clamp(lt / 0.35))
            if fi > 0:
                c.drawRect(skia.Rect.MakeWH(W, H), paint((0.03, 0.035, 0.05, 1), a=fi))
        else:
            # Tube Alloys document -> Moscow
            lc = t - self.cut
            c.drawRect(skia.Rect.MakeWH(W, H), paint(shader=lin((0, 0), (0, H), [(0.05, 0.045, 0.04, 1), (0.012, 0.01, 0.01, 1)])))
            c.drawRect(skia.Rect.MakeWH(W, H), paint(shader=rad((420, 1000), 900, [(1, 0.8, 0.55, 0.16), (1, 0.8, 0.55, 0)])))
            arrive = ease_out_expo(clamp(lc / 0.7))
            mp = ease_in_cubic(clamp((t - self.t_moscow + 0.15) / 0.6))
            with xform(c, tx=0, ty=(1 - arrive) * 400 - mp * 60, rot=-2.5 + mp * -1.5, cx=540, cy=1150, s=1.0 - mp * 0.04):
                c.drawRect(skia.Rect.MakeXYWH(150 + 12, 720 + 22, 780, 980), paint((0, 0, 0, 1), a=0.6, blur=30))
                c.drawImageRect(paper_image(780, 980, 21, tint=(0.93, 0.90, 0.82)), skia.Rect.MakeXYWH(150, 720, 780, 980),
                                skia.SamplingOptions(skia.FilterMode.kLinear))
                for d in self.doc_lines:
                    d.draw(c, t)
                c.drawLine(200, 980, 880, 980, paint((0.2, 0.18, 0.16, 1), a=0.6, stroke=1.5))
                from scenes import props as P
                P.typed_lines(c, 200, 1030, 420, 16, size=15, gap=2.0, seed=77, col=(0.15, 0.13, 0.12, 1))
                for k in range(6):
                    rp = clamp((t - (self.t_atomic - 0.05 + k * 0.09)) / 0.2)
                    redaction(c, 200 + (k % 2) * 40, 1060 + k * 92, 260 + hash01(k, 3) * 150, 22, rp, col=(0.03, 0.03, 0.035, 1))
                # atom linework draws itself
                ap = ease_in_out_cubic(clamp((t - (self.cut + 0.6)) / 1.4))
                ax, ay = 760, 1240
                for k in range(3):
                    orbit = skia.Path()
                    orbit.addOval(skia.Rect.MakeLTRB(ax - 120, ay - 42, ax + 120, ay + 42))
                    m = skia.Matrix()
                    m.setRotate(k * 60, ax, ay)
                    orbit.transform(m)
                    c.drawPath(trim_path(orbit, 0, ap), paint((0.15, 0.2, 0.35, 1), a=0.85, stroke=2.4))
                    if ap > 0.9:
                        e_ang = (t * 2.2 + k * 2.1)
                        ex, ey = ax + math.cos(e_ang) * 120, ay + math.sin(e_ang) * 42
                        ex2 = ax + (ex - ax) * math.cos(math.radians(k * 60)) - (ey - ay) * math.sin(math.radians(k * 60))
                        ey2 = ay + (ex - ax) * math.sin(math.radians(k * 60)) + (ey - ay) * math.cos(math.radians(k * 60))
                        c.drawCircle(ex2, ey2, 6, paint(PAL["red"], a=0.9))
                c.drawCircle(ax, ay, 14 * ap, paint(PAL["red"], a=0.9))
            # secrets flow to Moscow: a red thread leaves the frame
            if t > self.t_secrets - 0.1:
                fp = ease_in_out_cubic(clamp((t - (self.t_secrets - 0.1)) / 0.8))
                pth = skia.Path()
                pth.moveTo(760, 1240)
                pth.cubicTo(900, 1040, 820, 820, 1000, 660)
                sub = trim_path(pth, 0, fp)
                c.drawPath(sub, paint(PAL["red"], a=0.35, stroke=16, blur=12))
                c.drawPath(sub, paint(PAL["red"], stroke=4))
                if fp > 0.95:
                    c.drawCircle(1000, 660, 9, paint(PAL["red"]))
                self.dest.x, self.dest.y, self.dest.align = 985, 622, "right"
                self.dest.draw(c, t)
                T.draw(c, "mono", "1940s", 20, 985, 654, paint(PAL["muted"], a=smoothstep(self.t_moscow, self.t_moscow + 0.3, t)),
                       tracking=0.2, align="right")
            fi = 1 - ease_out_cubic(clamp(lc / 0.25))
            if fi > 0:
                c.drawRect(skia.Rect.MakeWH(W, H), paint((0.03, 0.035, 0.05, 1), a=fi))
        ex = ease_in_cubic(clamp((t - (self.end - 0.3)) / 0.3))
        if ex > 0:
            c.drawRect(skia.Rect.MakeWH(W, H), paint((0, 0, 0, 1), a=ex))

    def post(self, t):
        if t < self.cut:
            return dict(bloom=0.40, bloom_thresh=0.66, halation=0.09, vignette=0.74, grain=0.05,
                        lift=(0.010, 0.012, 0.022), gain=(1.03, 0.99, 0.97), ca=0.0018)
        return dict(bloom=0.28, bloom_thresh=0.8, halation=0.08, vignette=0.72, grain=0.05,
                    lift=(0.014, 0.012, 0.012), gain=(1.03, 0.99, 0.94), ca=0.0016)

    def mb(self, t):
        if self.start < t < self.start + 0.9 or self.cut < t < self.cut + 0.7:
            return 4
        return 1
