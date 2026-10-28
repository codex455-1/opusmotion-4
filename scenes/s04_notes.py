"""S4 — Every day he read the files, copied tiny notes by hand, and hid them in his shoes."""
import math
import skia
from engine import text as T
from engine.core import (W, H, PAL, clamp, lerp, mix, ease_out_cubic, ease_in_out_cubic, ease_out_expo,
                         ease_in_expo, ease_in_cubic, ease_out_back, smoothstep, hash01, noise1, Track)
from engine.gfx import paint, lin, rad, layer, xform, rrect, paper_image, path_from_points
from . import timeline as TL
from .common import cue, Typed, background, dust, light_cone, register_typing
from . import props as P

HAND_LINES = ["Лондон, 1972", "агент — тех. документы", "связь через тайник", "Центр: оценка высокая"]


def draw_file(c, t, flips, x, y, w=760, h=520):
    """Open manila case file seen from above; pages flip at the given times."""
    # back cover
    c.drawRRect(rrect(x + 10, y + 18, w, h, 10), paint((0, 0, 0, 1), a=0.6, blur=24))
    c.drawRRect(rrect(x, y, w, h, 10), paint((0.64, 0.50, 0.32, 1)))
    c.drawRRect(rrect(x, y, w, h, 10), paint(shader=lin((x, y), (x + w, y + h),
                                                        [(1, 0.9, 0.7, 0.10), (0, 0, 0, 0.0), (0, 0, 0, 0.3)])))
    # spine
    c.drawLine(x + w / 2, y + 8, x + w / 2, y + h - 8, paint((0.25, 0.18, 0.1, 1), a=0.6, stroke=3))
    # pages (right side) with typed text
    pimg = paper_image(360, 500, 8, tint=(0.94, 0.91, 0.84))
    for side in (0, 1):
        px = x + 14 if side == 0 else x + w / 2 + 6
        c.drawImageRect(pimg, skia.Rect.MakeXYWH(px, y + 12, w / 2 - 20, h - 24),
                        skia.SamplingOptions(skia.FilterMode.kLinear))
        P.typed_lines(c, px + 26, y + 70, w / 2 - 80, 14, size=13, gap=2.2, seed=40 + side + 3 * sum(t > f for f in flips))
        if side == 0:
            T.draw(c, "typewriter", "СОВЕРШЕННО СЕКРЕТНО", 15, px + 26, y + 44, paint(PAL["red"], a=0.85), tracking=0.1)
    # flipping page (right -> left), drawn as a foreshortened sheet
    for f in flips:
        p = clamp((t - f) / 0.42)
        if 0 < p < 1:
            e = ease_in_out_cubic(p)
            ang = e * math.pi
            cx = x + w / 2
            pw = (w / 2 - 20) * math.cos(ang)
            shade = 0.75 + 0.25 * abs(math.cos(ang))
            lift = math.sin(ang) * 26
            r = skia.Rect.MakeLTRB(min(cx, cx + pw), y + 12 - lift * 0.3, max(cx, cx + pw), y + h - 12 + lift * 0.3)
            c.drawRect(r.makeOffset(8, 12), paint((0, 0, 0, 1), a=0.25 * math.sin(ang), blur=14))
            c.drawImageRect(pimg, r, skia.SamplingOptions(skia.FilterMode.kLinear),
                            paint((1, 1, 1, 1), a=1.0))
            c.drawRect(r, paint((0, 0, 0, 1), a=(1 - shade)))


def shoe_path():
    """Men's oxford, side view, toe pointing right. Origin at the ground below the heel-to-toe midpoint."""
    p = skia.Path()
    p.moveTo(-250, -14)
    p.lineTo(-250, -70)
    p.cubicTo(-258, -150, -230, -190, -190, -196)     # heel counter up to collar
    p.cubicTo(-150, -200, -110, -168, -60, -160)      # collar dip
    p.cubicTo(-10, -170, 40, -196, 80, -178)          # tongue / laces
    p.cubicTo(150, -150, 230, -110, 268, -62)         # vamp down to the toe
    p.cubicTo(290, -36, 282, -12, 250, -8)            # toe cap
    p.lineTo(-250, -8)
    p.close()
    return p


def sole_path():
    p = skia.Path()
    p.moveTo(-262, -20)
    p.lineTo(262, -20)
    p.cubicTo(300, -22, 300, 6, 256, 6)
    p.lineTo(-180, 6)
    p.lineTo(-180, 14)
    p.lineTo(-262, 14)
    p.close()
    return p


def draw_shoe(c, t, xray=0.0, note_p=0.0):
    sole = sole_path()
    upper = shoe_path()
    c.drawOval(skia.Rect.MakeLTRB(-300, 0, 310, 40), paint((0, 0, 0, 1), a=0.7, blur=18))
    c.drawPath(sole, paint((0.08, 0.05, 0.03, 1)))
    c.drawPath(sole, paint((0.55, 0.40, 0.25, 1), a=0.5, stroke=2))
    # leather upper
    c.save()
    c.clipPath(upper, doAntiAlias=True)
    c.drawPaint(paint(shader=lin((0, -200), (0, 0), [(0.22, 0.12, 0.07, 1), (0.10, 0.05, 0.03, 1)])))
    c.drawPaint(paint(shader=rad((40, -170), 260, [(1, 0.8, 0.6, 0.25), (1, 0.8, 0.6, 0.0)])))
    sheen = skia.Path()
    sheen.moveTo(-200, -150)
    sheen.cubicTo(-80, -150, 120, -150, 240, -70)
    c.drawPath(sheen, paint((1, 0.9, 0.8, 1), a=0.25, stroke=12, blur=8))
    # toe cap seam + broguing
    tc = skia.Path()
    tc.moveTo(150, -150)
    tc.cubicTo(165, -100, 160, -40, 150, -10)
    c.drawPath(tc, paint((0.04, 0.02, 0.01, 1), a=0.7, stroke=3))
    for k in range(9):
        yy = -140 + k * 15
        c.drawCircle(160 + math.sin(k * 0.4) * 4, yy, 2.2, paint((0.03, 0.015, 0.01, 1), a=0.8))
    # quarter seam
    qs = skia.Path()
    qs.moveTo(-40, -162)
    qs.cubicTo(-30, -110, -60, -50, -90, -12)
    c.drawPath(qs, paint((0.04, 0.02, 0.01, 1), a=0.6, stroke=3))
    st = paint((0.75, 0.6, 0.42, 1), a=0.5, stroke=1.5)
    st.setPathEffect(skia.DashPathEffect.Make([6, 5], 0))
    welt = skia.Path()
    welt.moveTo(-246, -22)
    welt.lineTo(262, -22)
    c.drawPath(welt, st)
    c.drawPath(upper, paint((0, 0, 0, 1), a=0.5, stroke=26, blur=14))
    c.restore()
    # laces
    for k in range(4):
        x0 = -20 + k * 24
        c.drawLine(x0, -176 + k * 3, x0 + 26, -160 + k * 4, paint((0.85, 0.80, 0.70, 1), a=0.8, stroke=3))
    c.drawPath(upper, paint((1, 0.85, 0.7, 1), a=0.15, stroke=2, blur=1))
    if xray > 0:
        # technical section: interior cavity + where the note rests
        cav = skia.Path()
        cav.moveTo(-230, -30)
        cav.cubicTo(-238, -140, -200, -175, -170, -178)
        cav.cubicTo(-120, -165, -60, -150, 0, -150)
        cav.cubicTo(100, -150, 200, -100, 240, -40)
        cav.lineTo(240, -30)
        cav.close()
        c.save()
        c.clipPath(upper, doAntiAlias=True)
        c.drawPath(cav, paint((0.02, 0.02, 0.025, 1), a=0.9 * xray))
        dash = paint(PAL["amber_lt"], a=0.85 * xray, stroke=2)
        dash.setPathEffect(skia.DashPathEffect.Make([10, 7], -t * 30))
        c.drawPath(cav, dash)
        c.drawLine(-230, -34, 236, -34, paint(PAL["amber_lt"], a=0.5 * xray, stroke=1.5))  # insole
        c.restore()


def draw_scrap(c, w, h, write_p, t, seed=0):
    """Small torn note with Cyrillic handwriting being written (write_p 0..1 over all lines)."""
    pth = skia.Path()
    pth.moveTo(0, 0)
    for k in range(12):
        pth.lineTo(w * (k + 1) / 12, (hash01(seed, k) - 0.5) * 6)
    pth.lineTo(w, h)
    for k in range(12):
        pth.lineTo(w - w * (k + 1) / 12, h + (hash01(seed, k, 3) - 0.5) * 6)
    pth.close()
    c.drawPath(pth, paint((0, 0, 0, 1), a=0.5, blur=10))
    c.save()
    c.clipPath(pth, doAntiAlias=True)
    c.drawImageRect(paper_image(300, 200, 12, tint=(0.95, 0.93, 0.86)), skia.Rect.MakeWH(w, h),
                    skia.SamplingOptions(skia.FilterMode.kLinear))
    for k in range(5):
        c.drawLine(10, 40 + k * 34, w - 10, 40 + k * 34, paint((0.55, 0.65, 0.8, 1), a=0.25, stroke=1))
    n = len(HAND_LINES)
    pen = None
    for i, line in enumerate(HAND_LINES):
        lp = clamp(write_p * n - i)
        if lp <= 0:
            continue
        s = T.shape("hand", line, 26)
        reveal = s.width * lp
        y = 36 + i * 34
        c.save()
        c.clipRect(skia.Rect.MakeLTRB(14, y - 30, 14 + reveal, y + 10))
        c.drawTextBlob(s.blob(), 14, y, paint((0.10, 0.12, 0.25, 1), a=0.9))
        c.restore()
        if 0 < lp < 1:
            pen = (14 + reveal, y - 6 + math.sin(t * 40) * 2.5)
    c.restore()
    return pen


class S4:
    name = "notes"

    def __init__(self):
        self.start = TL.LINE_START["L05"] - 0.20
        self.end = TL.LINE_START["L06"] - 0.20
        self.t_files = TL.word_time("L05", "files")
        self.t_and = TL.word_time("L05", "and")
        self.t_copied = TL.word_time("L05", "copied")
        self.t_hidden = TL.word_time("L05", "hidden")
        self.t_shoes = TL.word_time("L05", "shoes")
        s = self.start
        self.flips = [s + 0.35, s + 0.95, s + 1.45, self.t_files + 0.1]
        for f in self.flips:
            cue(f, "paper_slide", -9, 0.1, var=int(f * 10) % 4)
        self.cut_b = self.t_and - 0.15
        self.cut_c = self.t_hidden - 0.25
        self.write_t0, self.write_t1 = self.t_copied - 0.05, self.cut_c - 0.1
        cue(self.write_t0, "pen_write", -8, 0.1, dur=self.write_t1 - self.write_t0, fade_in=0.05, fade_out=0.15,
            loop=True)
        cue(self.cut_b - 0.25, "whoosh_soft", -12, 0.3, var=3, align="peak", at=self.cut_b)
        cue(self.cut_c - 0.05, "paper_fold", -8, 0.0, var=0)
        cue(self.cut_c + 0.35, "paper_fold", -10, 0.0, var=1)
        cue(self.t_shoes - 0.05, "emph_thump", -10, 0.0, var=1)
        cue(self.end - 0.35, "whoosh_soft", -10, 0.0, var=0, align="peak", at=self.end)
        # day counter ticks
        self.day_t0, self.day_t1 = s + 0.25, self.cut_b
        k = 0
        tt = self.day_t0
        while tt < self.day_t1:
            cue(tt, "tick", -16, 0.25, var=k % 4)
            k += 1
            tt += 0.11
        self.label = Typed("ПЕРВОЕ ГЛАВНОЕ УПРАВЛЕНИЕ · ДЕЛО", "mono", 19, 160, 700, s + 0.3, cps=50,
                           color=PAL["muted"], track=0.12, seed=401, gain=-12, caret=False)

    def draw(self, c, t):
        background(c, t, top=(0.05, 0.045, 0.04, 1), bottom=(0.015, 0.013, 0.012, 1), light=(420, 1000),
                   light_col=PAL["amber_lt"], light_r=1100, light_a=0.20, haze=0.03, seed=4)
        # desk wood
        wt = P.wood_tex(seed=7, tint=(0.30, 0.19, 0.11))
        m = skia.Matrix()
        m.setScale(1.6, 1.6)
        c.drawRect(skia.Rect.MakeWH(W, H), paint(shader=wt.makeShader(skia.TileMode.kMirror, skia.TileMode.kMirror,
                                                                      skia.SamplingOptions(skia.FilterMode.kLinear), m),
                                                 a=0.55))
        c.drawRect(skia.Rect.MakeWH(W, H), paint(shader=rad((470, 1050), 1000, [(0, 0, 0, 0), (0, 0, 0, 0.75)])))
        lt = t - self.start
        # camera: A (file) -> B (scrap, slide right + zoom) -> C (fold + shoe)
        if t < self.cut_c:
            bp = ease_in_out_cubic(clamp((t - self.cut_b) / 0.6))
            s = lerp(1.24 + 0.04 * clamp(lt / 2), 1.75, bp)
            fx, fy = lerp(540, 860, bp), lerp(1010, 1250, bp)
            c.save()
            c.translate(540, 1180)
            c.scale(s, s)
            c.translate(-fx, -fy)
            draw_file(c, t, self.flips, 160, 760)
            self.label.draw(c, t)
            # day counter
            dp = clamp((t - self.day_t0) / (self.day_t1 - self.day_t0))
            day = int(1 + ease_in_cubic(dp) * 4382)
            da = 1 - smoothstep(self.cut_b - 0.15, self.cut_b + 0.15, t)
            T.draw(c, "mono", "ДЕНЬ / DAY", 18, 920, 690, paint(PAL["muted"], a=0.9 * da), tracking=0.14, align="right")
            T.draw(c, "mono_semi", f"{day:04d}", 54, 920, 748, paint(PAL["cream"], a=da), tracking=0.06, align="right")
            # scrap of paper beside the file
            arrive = ease_out_expo(clamp((t - (self.cut_b - 0.3)) / 0.8))
            if arrive > 0:
                with xform(c, tx=lerp(1200, 690, arrive), ty=1150, rot=lerp(14, -4, arrive)):
                    wp = clamp((t - self.write_t0) / (self.write_t1 - self.write_t0))
                    pen = draw_scrap(c, 330, 200, wp, t)
                    if pen:
                        # pen nib
                        px, py = pen
                        nib = path_from_points([(px, py), (px + 16, py - 46), (px + 30, py - 40)], True)
                        c.drawPath(nib, paint((0.75, 0.68, 0.45, 1)))
                        c.drawLine(px + 22, py - 44, px + 120, py - 300, paint((0.08, 0.08, 0.09, 1), stroke=16))
                        c.drawLine(px + 22, py - 44, px + 120, py - 300, paint((1, 1, 1, 1), a=0.2, stroke=3, blur=2))
            c.restore()
        else:
            # C: the note folds and drops into the shoe (technical section view)
            lc = t - self.cut_c
            c.drawRect(skia.Rect.MakeWH(W, H), paint((0.02, 0.02, 0.022, 1), a=ease_out_cubic(clamp(lc / 0.3)) * 0.85))
            c.drawRect(skia.Rect.MakeWH(W, H), paint(shader=rad((540, 1150), 720, [(1, 0.78, 0.5, 0.16), (1, 0.78, 0.5, 0.0)]),
                                                     a=ease_out_cubic(clamp(lc / 0.4))))
            # blueprint grid
            ga = ease_out_cubic(clamp(lc / 0.4)) * 0.06
            for k in range(0, W, 60):
                c.drawLine(k, 0, k, H, paint(PAL["cream"], a=ga, stroke=1))
            for k in range(0, H, 60):
                c.drawLine(0, k, W, k, paint(PAL["cream"], a=ga, stroke=1))
            shoe_in = ease_out_expo(clamp((lc - 0.25) / 0.7))
            exit_p = ease_in_cubic(clamp((t - (self.end - 0.4)) / 0.4))
            sx, sy = lerp(520, 520, shoe_in), lerp(1750, 1330, shoe_in) + exit_p * 760
            xr = smoothstep(self.t_shoes - 0.3, self.t_shoes + 0.2, t)
            with xform(c, tx=sx, ty=sy, s=1.62):
                draw_shoe(c, t, xray=xr)
                # folded note travelling into the shoe
                fold = clamp(lc / 0.55)
                drop = ease_in_out_cubic(clamp((lc - 0.45) / 0.65))
                nx = lerp(40, -120, drop)
                ny = lerp(-560, -70, drop)
                nw = lerp(150, 46, ease_out_cubic(fold))
                nh = lerp(90, 30, ease_out_cubic(fold))
                c.drawRect(skia.Rect.MakeXYWH(nx - nw / 2 + 4, ny - nh / 2 + 6, nw, nh), paint((0, 0, 0, 1), a=0.4, blur=6))
                c.drawRect(skia.Rect.MakeXYWH(nx - nw / 2, ny - nh / 2, nw, nh), paint((0.93, 0.90, 0.82, 1)))
                c.drawLine(nx - nw / 2, ny, nx + nw / 2, ny, paint((0.4, 0.35, 0.3, 1), a=0.6, stroke=1.2))
                c.drawLine(nx, ny - nh / 2, nx, ny + nh / 2, paint((0.4, 0.35, 0.3, 1), a=0.4 * fold, stroke=1.2))
            if xr > 0.5:
                a_ = smoothstep(0.5, 1.0, xr) * (1 - exit_p)
                T.draw(c, "mono_med", "NOTE  →  INSIDE THE SHOE", 24, 540, 1640, paint(PAL["amber_lt"], a=a_),
                       tracking=0.14, align="center")
        dust(c, t, n=20, seed=14, region=(80, 600, 920, 1100), alpha=0.25, size=(1.0, 4.0))

    def post(self, t):
        return dict(bloom=0.28, bloom_thresh=0.78, halation=0.07, vignette=0.72, grain=0.05,
                    lift=(0.014, 0.012, 0.012), gain=(1.03, 0.99, 0.94), ca=0.0016)

    def mb(self, t):
        if self.cut_b - 0.1 < t < self.cut_b + 0.6 or self.cut_c < t < self.cut_c + 1.1 or t > self.end - 0.4:
            return 4
        return 1
