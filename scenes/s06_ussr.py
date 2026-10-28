"""S6 — 1991: the Soviet Union falls apart; he tries the Americans first (Riga, Vilnius). Not taken seriously."""
import math
import numpy as np
import skia
from engine import text as T
from engine.core import (W, H, PAL, clamp, lerp, mix, ease_out_cubic, ease_in_out_cubic, ease_out_expo,
                         ease_in_expo, ease_in_cubic, ease_out_back, smoothstep, hash01, Track)
from engine.gfx import paint, lin, rad, path_from_points, trim_path, rrect
from . import timeline as TL
from .common import cue, Typed
from .mapview import MapCam, draw_map, bezier
from . import europe as E


class S6:
    name = "ussr"

    def __init__(self):
        self.start = TL.LINE_START["L08"] - 0.20
        self.end = TL.LINE_START["L09"] - 0.20
        self.t_soviet = TL.word_time("L08", "soviet")
        self.t_fell = TL.word_time("L08", "fell")
        self.t_tried = TL.word_time("L08", "tried")
        self.t_amer = TL.word_time("L08", "americans")
        self.t_they = TL.word_time("L08", "they")
        self.t_ser = TL.word_time("L08", "seriously")
        m = E.meta()
        self.m = m
        self.mos, self.riga, self.vil = E.city("moscow"), E.city("riga"), E.city("vilnius")
        balt = ((self.riga[0] + self.vil[0]) / 2, (self.riga[1] + self.vil[1]) / 2)
        overview = (self.mos[0] - 120, self.mos[1] - 160)
        s = self.start
        self.cam_t = Track([(s, overview), (self.t_fell + 0.4, (overview[0] - 60, overview[1])),
                            (self.t_amer + 0.1, (balt[0] + 120, balt[1] + 40), ease_in_out_cubic),
                            (self.end, (balt[0] + 60, balt[1] + 10))])
        self.cam_h = Track([(s, 2700.0), (self.t_fell + 0.4, 2500.0), (self.t_amer + 0.1, 880.0, ease_in_out_cubic),
                            (self.end - 0.35, 820.0), (self.end, 420.0, ease_in_expo)])
        self.cam_p = Track([(s, 18.0), (self.t_fell + 0.4, 22.0), (self.t_amer + 0.1, 34.0, ease_in_out_cubic),
                            (self.end, 36.0)])
        self.cam_y = Track([(s, 4.0), (self.end, -6.0)])
        # republic drift directions (away from Moscow)
        self.drift = {}
        for iso, polys in m["soviet"].items():
            pts = np.concatenate([np.array(p) for p in polys])
            cen = pts.mean(0)
            d = cen - np.array(self.mos)
            n = np.linalg.norm(d) + 1e-6
            self.drift[iso] = d / n * (0 if iso == "RUS" else 26 + 18 * hash01(len(iso), ord(iso[0])))
        self.trail = np.concatenate([bezier(self.mos, self.riga, 0.10, 80), bezier(self.riga, self.vil, -0.25, 40)[1:]])
        self.tag_r = E.Tag("U.S. EMBASSY", "RIGA", self.t_amer - 0.1, 601, dx=46, dy=-70)
        self.tag_v = E.Tag("U.S. EMBASSY", "VILNIUS", self.t_amer + 0.15, 611, dx=46, dy=64)
        self.year = Typed("1991", "news", 96, 0, 0, self.t_fell - 0.05, cps=10, color=PAL["cream"], seed=621, gain=-5,
                          caret=False)
        cue(s, "wind_soft", -18, 0.0, dur=self.end - s, fade_in=0.4, fade_out=0.5, loop=True)
        cue(self.t_fell - 0.02, "sub_boom", -7, 0.0, var=2)
        cue(self.t_fell + 0.05, "paper_flutter", -14, 0.0, var=0)
        cue(self.t_tried - 0.2, "whoosh_soft", -11, -0.2, var=1, align="peak", at=self.t_tried + 0.3)
        cue(self.t_tried, "route_draw", -14, 0.0, dur=1.0, fade_in=0.05, fade_out=0.3, loop=True)
        cue(self.t_ser - 0.04, "redact_swipe", -7, -0.15, var=0)
        cue(self.t_ser + 0.10, "redact_swipe", -9, 0.15, var=1)
        cue(self.end - 0.4, "whoosh_soft", -11, 0.0, var=2, align="peak", at=self.end)

    def cam(self, t):
        return MapCam(self.cam_t(t), self.cam_h(t), pitch=self.cam_p(t), yaw=self.cam_y(t), fov=34,
                      screen_offset=(0, 160))

    def draw(self, c, t):
        c.drawRect(skia.Rect.MakeWH(W, H), paint((0.015, 0.02, 0.03, 1)))
        cam = self.cam(t)
        arrive = ease_out_cubic(clamp((t - self.start) / 0.45))
        draw_map(c, "europe", cam, alpha=arrive, fog=(0.015, 0.02, 0.03))
        brk = ease_out_expo(clamp((t - self.t_fell) / 1.1))
        red = 1 - smoothstep(self.t_fell, self.t_fell + 0.9, t)

        rep_a = arrive * (1 - smoothstep(self.t_tried, self.t_amer, t))

        def republics(cc):
            if rep_a <= 0:
                return
            for iso, polys in self.m["soviet"].items():
                off = tuple(self.drift[iso] * brk)
                for pts in polys:
                    p = E.poly_path(pts, off)
                    cc.drawPath(p, paint(mix((0.24, 0.07, 0.06, 1), (0.11, 0.12, 0.13, 1), 1 - red), a=0.92 * rep_a))
                    cc.drawPath(p, paint(mix(PAL["cream"], PAL["red"], red), a=(0.35 + 0.4 * brk * (1 - red)) * rep_a,
                                         stroke=2.2))
            if red > 0:
                for pts in self.m["ussr"]:
                    p = E.poly_path(pts)
                    cc.drawPath(p, paint(PAL["red"], a=0.35 * red * arrive, stroke=26, blur=18))
                    cc.drawPath(p, paint(PAL["red"], a=0.9 * red * arrive, stroke=4))
        E.draw_in_map(c, cam, republics)
        # USSR wordmark, letters scatter on "fell"
        ua = arrive * (1 - smoothstep(self.t_fell + 0.2, self.t_fell + 0.9, t))
        if ua > 0:
            ux, uy = W / 2 + 60, 1380
            for i, ch in enumerate("USSR"):
                dx = (i - 1.5) * 92 + (hash01(i, 7) - 0.5) * 160 * brk
                dy = (hash01(i, 9) - 0.5) * 120 * brk
                T.draw(c, "sans_semi", ch, 92, ux + dx, uy + dy, paint(PAL["red"], a=ua), align="center")
        ya = smoothstep(self.t_fell - 0.1, self.t_fell + 0.2, t) * (1 - smoothstep(self.t_tried + 0.2, self.t_tried + 0.6, t))
        if ya > 0:
            self.year.x, self.year.y, self.year.align = W / 2, 1600, "center"
            self.year.draw(c, t, alpha=ya)
        # Moscow
        E.city_dot(c, cam, self.mos, t, self.start + 0.2, col=PAL["red"])
        # his trail to the Baltic embassies
        tp = ease_in_out_cubic(clamp((t - self.t_tried) / 1.4))
        if tp > 0:
            path, sp = E.screen_path(cam, self.trail)
            sub = trim_path(path, 0, tp)
            dash = paint(PAL["cream"], a=0.85, stroke=2.6)
            dash.setPathEffect(skia.DashPathEffect.Make([3, 9], 0))
            c.drawPath(sub, dash)
            from engine.gfx import path_point
            (hx, hy), _ = path_point(path, tp)
            c.drawCircle(hx, hy, 9, paint(PAL["amber_lt"]))
            c.drawCircle(hx, hy, 22, paint(PAL["amber"], a=0.25, blur=8))
        strike = ease_out_cubic(clamp((t - self.t_ser) / 0.3))
        for uv, tag, td in ((self.riga, self.tag_r, self.t_amer - 0.1), (self.vil, self.tag_v, self.t_amer + 0.15)):
            xy = E.city_dot(c, cam, uv, t, td, col=PAL["cream"], r=7)
            if xy:
                tag.draw(c, t, *xy, alpha=1 - smoothstep(self.end - 0.35, self.end - 0.1, t), strike=strike)
                if strike > 0:
                    x, y = xy
                    k = 13 * ease_out_back(strike)
                    c.drawLine(x - k, y - k, x + k, y + k, paint(PAL["red"], stroke=4))
                    c.drawLine(x - k, y + k, x + k, y - k, paint(PAL["red"], stroke=4))
        # exit: warm light bloom into the tea scene
        ex = ease_in_cubic(clamp((t - (self.end - 0.3)) / 0.3))
        if ex > 0:
            c.drawRect(skia.Rect.MakeWH(W, H), paint((0.10, 0.07, 0.04, 1), a=ex))

    def post(self, t):
        return dict(bloom=0.34, bloom_thresh=0.7, halation=0.07, vignette=0.75, grain=0.045,
                    lift=(0.008, 0.012, 0.02), gain=(1.0, 1.0, 1.0), ca=0.002)

    def mb(self, t):
        if self.t_tried < t < self.t_amer + 0.4 or t > self.end - 0.4 or self.t_fell < t < self.t_fell + 0.5:
            return 4
        return 1
