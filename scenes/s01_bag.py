"""S1 — The bag. Doorway silhouette -> smash zoom -> bag close-up -> cutaway reveals the KGB notes."""
import math
import skia
from engine import text as T
from engine.core import (W, H, PAL, clamp, lerp, mix, ease_out_cubic, ease_in_out_cubic, ease_out_expo,
                         ease_in_expo, ease_in_cubic, ease_out_back, smoothstep, noise1)
from engine.gfx import xpath, paint, lin, rad, layer, xform, path_from_points, rrect
from . import timeline as TL
from .common import cue, Typed, Callout, background, dust, light_cone
from . import props as P

DOOR_X, DOOR_Y0, DOOR_Y1, DOOR_W = 540, 610, 1150, 270
COOL = (0.80, 0.88, 0.95, 1.0)


def figure_path():
    """Old man in a flat cap and overcoat, holding a bag. Feet at (0,0), height ~300."""
    p = skia.Path()
    p.addCircle(0, -262, 17)                                # head
    cap = skia.Path()
    cap.addOval(skia.Rect.MakeLTRB(-25, -284, 23, -268))     # cap brim
    cap.addOval(skia.Rect.MakeLTRB(-18, -296, 18, -270))
    p.addPath(cap)
    coat = skia.Path()
    coat.moveTo(-14, -246)
    coat.cubicTo(-46, -240, -52, -214, -50, -190)            # left shoulder
    coat.lineTo(-58, -64)
    coat.lineTo(-30, -58)
    coat.lineTo(30, -58)
    coat.lineTo(58, -64)
    coat.lineTo(50, -190)
    coat.cubicTo(52, -214, 46, -240, 14, -246)
    coat.close()
    p.addPath(coat)
    return p


def legs_path(phase):
    p = skia.Path()
    s = math.sin(phase) * 7
    p.addRoundRect(skia.Rect.MakeLTRB(-24 + s, -66, -6 + s, 0), 4, 4)
    p.addRoundRect(skia.Rect.MakeLTRB(6 - s, -66, 24 - s, 0), 4, 4)
    return p


def bag_small(phase):
    p = skia.Path()
    sw = math.sin(phase * 0.5) * 3
    p.addRoundRect(skia.Rect.MakeLTRB(46 + sw, -112, 92 + sw, -70), 6, 6)
    p.addRect(skia.Rect.MakeLTRB(52, -140, 56, -110))
    return p


class S1:
    name = "bag"

    def __init__(self):
        self.start = 0.0
        L1, L2 = TL.LINE_START["L01"], TL.LINE_START["L02"]
        self.t_with = TL.word_time("L01", "with")
        self.t_saus = TL.word_time("L01", "sausages")
        self.t_under = TL.word_time("L02", "under")
        self.t_secrets = TL.word_time("L02", "secrets")
        self.t_kgb = TL.word_time("L02", "kgb")
        self.end = TL.LINE_START["L03"] - 0.30
        self.cut = self.t_with - 0.22            # wide -> close-up
        self.door_t0 = L1 + 0.15
        self.walk_t0 = self.door_t0 + 0.75
        # slate
        self.slate1 = Typed("24 MARCH 1992", "mono_med", 34, W / 2, 1600, 0.12, cps=17, track=0.28,
                            align="center", seed=101, gain=-3.0, color=PAL["cream"])
        self.slate2 = Typed("A BRITISH EMBASSY  ·  THE BALTICS", "mono", 22, W / 2, 1648, self.slate1.t_end + 0.1,
                            cps=30, track=0.22, align="center", seed=102, gain=-7.0, color=PAL["muted"], caret=False)
        # sounds
        cue(self.door_t0 + 0.05, "door_heavy", -6, 0.0)
        cue(self.door_t0, "room_archive", -8, 0.0, dur=self.end + 0.5, fade_in=0.6, fade_out=1.0, loop=True)
        for k in range(4):
            cue(self.walk_t0 + 0.12 + k * 0.52, "footstep", -10 + k * 1.2, -0.05, var=k % 4)
        cue(self.cut - 0.25, "whoosh_soft", -6, 0.2, var=0, align="peak", at=self.cut)
        cue(self.cut + 0.18, "emph_thump", -9, 0.0, var=0)
        self.land = self.cut + 0.20
        cue(self.t_saus - 0.02, "text_pop", -8, 0.1, var=2)
        cue(self.t_under - 0.1, "light_sweep", -9, 0.0, var=0)
        cue(self.t_under + 0.05, "riser_air", -14, 0.0, align="peak", at=self.t_kgb + 0.15)
        cue(self.t_kgb, "sub_boom", -6, 0.0, var=0)
        self.c1 = Callout((430, 1178), (370, 960), "SALAMI · BREAD", self.t_under + 0.55, sub="ON TOP",
                          accent=PAL["amber"], seed=111, align="right")
        self.c2 = Callout((660, 1330), (770, 1650), "TYPED NOTES", self.t_secrets + 0.05,
                          sub="FROM KGB FILES", accent=PAL["red"], seed=112, align="left")
        self.dive_t0 = self.end - 0.55
        cue(self.dive_t0 + 0.05, "whoosh_deep", -8, 0.0, var=0, align="peak", at=self.end)

    # ------------------------------------------------------------------------------------
    def draw_wide(self, c, t):
        L1 = TL.LINE_START["L01"]
        door = ease_in_out_cubic(clamp((t - self.door_t0) / 1.25))
        # camera: slow push + smash zoom into the doorway before the cut
        smash = ease_in_expo(clamp((t - (self.cut - 0.30)) / 0.30))
        s = 1.0 + 0.05 * clamp(t / 4.5) + smash * 1.9
        c.save()
        c.translate(DOOR_X, 900)
        c.scale(s, s)
        c.translate(-DOOR_X, -900)
        # back wall
        c.drawRect(skia.Rect.MakeLTRB(-200, -200, W + 200, DOOR_Y1),
                   paint(shader=lin((0, 0), (0, DOOR_Y1), [(0.035, 0.04, 0.05, 1), (0.07, 0.075, 0.085, 1)])))
        for sx in (-1, 1):  # wall panels
            for k in range(2):
                x0 = DOOR_X + sx * (230 + k * 200)
                r = skia.Rect.MakeLTRB(min(x0, x0 + sx * 150), 520, max(x0, x0 + sx * 150), 1060)
                c.drawRect(r, paint((1, 1, 1, 1), a=0.035, stroke=2))
        c.drawRect(skia.Rect.MakeLTRB(-200, 1080, W + 200, DOOR_Y1), paint((0, 0, 0, 1), a=0.35))  # skirting
        # floor
        c.drawRect(skia.Rect.MakeLTRB(-200, DOOR_Y1, W + 200, H + 200),
                   paint(shader=lin((0, DOOR_Y1), (0, H), [(0.05, 0.05, 0.055, 1), (0.015, 0.016, 0.02, 1)])))
        for k in range(-9, 10):  # tile seams converging to the door
            c.drawLine(DOOR_X + k * 28, DOOR_Y1, DOOR_X + k * 300, H + 200, paint((1, 1, 1, 1), a=0.025, stroke=1.5))
        for k in range(1, 9):
            yy = DOOR_Y1 + (H - DOOR_Y1) * (k / 8) ** 1.8
            c.drawLine(-200, yy, W + 200, yy, paint((1, 1, 1, 1), a=0.02, stroke=1.2))
        # doorway light
        x0, x1 = DOOR_X - DOOR_W / 2, DOOR_X + DOOR_W / 2
        open_w = DOOR_W * door
        if door > 0:
            c.save()
            c.clipRect(skia.Rect.MakeLTRB(x0, DOOR_Y0, x1, DOOR_Y1))
            c.drawRect(skia.Rect.MakeLTRB(x0, DOOR_Y0, x1, DOOR_Y1),
                       paint(shader=lin((0, DOOR_Y0), (0, DOOR_Y1), [(0.95, 0.98, 1.0, 1), (0.78, 0.84, 0.90, 1)]),
                             a=1.0))
            c.drawRect(skia.Rect.MakeLTRB(x0, DOOR_Y1 - 70, x1, DOOR_Y1), paint((0.55, 0.6, 0.66, 1), a=0.6))
            c.restore()
            # spill on the floor + glossy reflection
            spill = path_from_points([(DOOR_X - open_w / 2, DOOR_Y1), (DOOR_X + open_w / 2, DOOR_Y1),
                                      (DOOR_X + open_w * 1.9, H + 100), (DOOR_X - open_w * 1.9, H + 100)], True)
            c.drawPath(spill, paint(shader=lin((0, DOOR_Y1), (0, H), [COOL, (COOL[0], COOL[1], COOL[2], 0)]),
                                    a=0.32 * door, blur=10))
            refl = path_from_points([(DOOR_X - open_w / 2, DOOR_Y1), (DOOR_X + open_w / 2, DOOR_Y1),
                                     (DOOR_X + open_w / 2 * 0.9, DOOR_Y1 + 330), (DOOR_X - open_w / 2 * 0.9, DOOR_Y1 + 330)],
                                    True)
            c.drawPath(refl, paint(shader=lin((0, DOOR_Y1), (0, DOOR_Y1 + 330), [COOL, (COOL[0], COOL[1], COOL[2], 0)]),
                                   a=0.28 * door, blur=14))
            c.drawRect(skia.Rect.MakeLTRB(-400, -400, W + 400, H + 400),
                       paint(shader=rad((DOOR_X, 880), 560, [COOL, (COOL[0], COOL[1], COOL[2], 0)]), a=0.22 * door))
            # volumetric shafts spilling from the doorway into the hazy room
            for k, (dx, a_) in enumerate(((-0.55, 0.05), (0.0, 0.07), (0.6, 0.045))):
                shaft = path_from_points([(DOOR_X - open_w / 2 + 20, DOOR_Y0 + 40), (DOOR_X + open_w / 2 - 20, DOOR_Y0 + 40),
                                          (DOOR_X + open_w * (1.4 + dx), H), (DOOR_X - open_w * (1.4 - dx), H)], True)
                c.drawPath(shaft, paint(shader=lin((0, DOOR_Y0), (0, H), [COOL, (COOL[0], COOL[1], COOL[2], 0)]),
                                        a=a_ * door * (0.8 + 0.2 * math.sin(t * 0.7 + k)), blur=36))
        # door leaves (swing inward: visible width shrinks)
        for sgn in (-1, 1):
            leaf_w = DOOR_W / 2 * (1 - door * 0.92)
            lx = x0 if sgn < 0 else x1 - leaf_w
            r = skia.Rect.MakeLTRB(lx, DOOR_Y0, lx + leaf_w, DOOR_Y1)
            c.drawRect(r, paint((0.10, 0.075, 0.06, 1)))
            c.drawRect(skia.Rect.MakeLTRB(lx + leaf_w * 0.18, DOOR_Y0 + 40, lx + leaf_w * 0.82, DOOR_Y0 + 250),
                       paint((1, 1, 1, 1), a=0.05, stroke=2))
            c.drawRect(skia.Rect.MakeLTRB(lx + leaf_w * 0.18, DOOR_Y0 + 290, lx + leaf_w * 0.82, DOOR_Y1 - 50),
                       paint((1, 1, 1, 1), a=0.05, stroke=2))
        # architrave
        c.drawRect(skia.Rect.MakeLTRB(x0 - 26, DOOR_Y0 - 26, x1 + 26, DOOR_Y1), paint((0.16, 0.15, 0.14, 1),
                                                                                         stroke=14))
        c.drawRect(skia.Rect.MakeLTRB(x0 - 40, DOOR_Y0 - 60, x1 + 40, DOOR_Y0 - 34), paint((0.14, 0.13, 0.12, 1)))
        # the man
        if t > self.walk_t0 - 0.4:
            wp = clamp((t - self.walk_t0) / 2.6)
            phase = max(0.0, t - self.walk_t0) * 6.0
            app = ease_out_cubic(clamp((t - (self.walk_t0 - 0.4)) / 0.6))
            fs = 1.0 + 0.32 * ease_in_out_cubic(wp)
            fy = DOOR_Y1 + 120 * ease_in_out_cubic(wp) - abs(math.sin(phase)) * 3
            fx = DOOR_X - 6 + noise1(t * 0.5, 4) * 3
            body = skia.Path(figure_path())
            body.addPath(legs_path(phase if 0 < wp < 1 else 0))
            body.addPath(bag_small(phase))
            m = skia.Matrix()
            m.setScale(fs, fs)
            m.postTranslate(fx, fy)
            fig = xpath(body, m)
            # long shadow toward the camera
            ms = skia.Matrix()
            ms.setAll(fs * 1.4, 0, fx, 0, -fs * 2.6, fy, 0, 0, 1)
            sh = xpath(body, ms)
            c.drawPath(sh, paint((0.0, 0.0, 0.0, 1), a=0.72 * app * door, blur=9))
            c.drawPath(fig, paint((0.012, 0.012, 0.016, 1), a=app))
            c.drawPath(fig, paint(COOL, a=0.22 * app, stroke=2.0, blur=4))   # light wrap rim
        dust(c, t, n=30, seed=7, region=(DOOR_X - 360, 560, 720, 900), color=COOL, alpha=0.35 * door,
             size=(1.0, 3.5), drift=(4, -6))
        c.restore()
        # slate
        sa = 1 - smoothstep(self.cut - 0.6, self.cut - 0.2, t)
        self.slate1.draw(c, t, alpha=sa)
        self.slate2.draw(c, t, alpha=sa)
        # flash at the smash cut
        if smash > 0:
            c.drawRect(skia.Rect.MakeWH(W, H), paint(COOL, a=0.5 * smash ** 2))

    # ------------------------------------------------------------------------------------
    def draw_close(self, c, t):
        lt = t - self.cut
        background(c, t, top=(0.05, 0.04, 0.035, 1), bottom=(0.012, 0.01, 0.01, 1), light=(330, 820),
                   light_col=PAL["amber_lt"], light_r=1250, light_a=0.18, haze=0.035, seed=2)
        dive = ease_in_expo(clamp((t - self.dive_t0) / (self.end - self.dive_t0)))
        push = 1.0 + 0.07 * ease_out_cubic(clamp(lt / 6.0)) + dive * 3.6
        settle = ease_out_expo(clamp(lt / 0.9))
        cx, cy = 540, 1210
        focus = (lerp(540, 470, dive), lerp(1210, 1290, dive))
        c.save()
        c.translate(focus[0], focus[1])
        c.scale(push, push)
        c.translate(-focus[0], -focus[1])
        c.translate(0, (1 - settle) * 70)
        c.drawRect(skia.Rect.MakeLTRB(-400, 500, W + 400, 1500),
                   paint(shader=rad((560, 1120), 620, [(0.95, 0.62, 0.36, 0.16), (0.9, 0.6, 0.35, 0.0)])))
        # table top
        table_y = 1480
        c.save()
        c.clipRect(skia.Rect.MakeLTRB(-400, table_y - 40, W + 400, H + 400))
        wt = P.wood_tex()
        m = skia.Matrix()
        m.setAll(1.1, 0.35, -300, 0, 0.55, table_y - 40, 0, 0.00025, 1)
        c.drawRect(skia.Rect.MakeLTRB(-400, table_y - 40, W + 400, H + 400),
                   paint(shader=wt.makeShader(skia.TileMode.kMirror, skia.TileMode.kMirror,
                                              skia.SamplingOptions(skia.FilterMode.kLinear), m)))
        c.drawRect(skia.Rect.MakeLTRB(-400, table_y - 40, W + 400, H + 400),
                   paint(shader=lin((0, table_y - 40), (0, H), [(0, 0, 0, 0.45), (0, 0, 0, 0.1), (0, 0, 0, 0.8)],
                                    [0, 0.25, 1])))
        c.drawRect(skia.Rect.MakeLTRB(-400, table_y - 40, W + 400, H + 400),
                   paint(shader=rad((420, table_y + 40), 720, [(1, 0.75, 0.45, 0.30), (1, 0.7, 0.4, 0.0)])))
        c.restore()
        c.drawLine(-400, table_y - 40, W + 400, table_y - 40, paint((1, 0.85, 0.65, 1), a=0.18, stroke=2))
        # contact shadow
        c.drawOval(skia.Rect.MakeLTRB(cx - 360, table_y - 30, cx + 380, table_y + 46), paint((0, 0, 0, 1), a=0.75,
                                                                                            blur=26))
        open_amt = ease_out_back(clamp((t - self.t_saus + 0.05) / 0.5), 1.8)
        reveal = ease_in_out_cubic(clamp((t - self.t_under) / 1.5))
        glow = smoothstep(self.t_secrets - 0.2, self.t_kgb + 0.3, t)
        squash = 1 - 0.03 * math.sin(clamp((t - self.land) / 0.35) * math.pi) * (t > self.land)
        with xform(c, tx=cx, ty=table_y - 8, sx=1.0 / squash ** 0.5, sy=squash):
            P.draw_bag(c, t, reveal=reveal, open_amt=open_amt,
                       inside=lambda cc: P.bag_inside(cc, glow=glow))
        dust(c, t, n=26, seed=9, region=(120, 700, 840, 800), alpha=0.35, size=(1.2, 4.5))
        self.c1.draw(c, t)
        self.c2.draw(c, t)
        c.restore()
        # lamp cone from upper left
        light_cone(c, (250, -50), 1500, 520, a=0.05, blur=60)

    def draw(self, c, t):
        if t < self.cut:
            self.draw_wide(c, t)
        else:
            self.draw_close(c, t)
            fade_in = 1 - clamp((t - self.cut) / 0.25)
            if fade_in > 0:
                c.drawRect(skia.Rect.MakeWH(W, H), paint(COOL, a=0.45 * fade_in ** 2))
        d = clamp((t - (self.end - 0.18)) / 0.18)
        if d > 0:
            c.drawRect(skia.Rect.MakeWH(W, H), paint(PAL["paper"], a=d ** 2 * 0.9))

    def post(self, t):
        if t < self.cut:
            return dict(bloom=0.42, bloom_thresh=0.72, halation=0.05, vignette=0.75, grain=0.05,
                        lift=(0.010, 0.013, 0.02), gain=(0.97, 1.0, 1.04), ca=0.0022)
        return dict(bloom=0.30, bloom_thresh=0.78, halation=0.08, vignette=0.70, grain=0.048,
                    lift=(0.016, 0.012, 0.01), gain=(1.04, 0.99, 0.93), ca=0.0018)

    def mb(self, t):
        if self.cut - 0.32 < t < self.cut + 0.3:
            return 5
        if t > self.dive_t0:
            return 5
        return 1
