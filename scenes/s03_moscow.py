"""S3 — The move: Lubyanka -> Yasenevo on a real Moscow street map, archive packets streaming."""
import math
import numpy as np
import skia
from engine import text as T
from engine.core import (W, H, PAL, clamp, lerp, mix, ease_out_cubic, ease_in_out_cubic, ease_out_expo,
                         ease_in_expo, ease_in_cubic, ease_out_back, smoothstep, Track, hash01)
from engine.gfx import paint, lin, rad, layer, path_from_points, trim_path, rrect
from . import timeline as TL
from .common import cue, Typed, pulse_marker, background, label_caps
from .mapview import load, MapCam, draw_map, bezier


class MapLabel:
    """Typed two-line label anchored to a projected map point."""

    def __init__(self, title, sub, t0, seed, side=1, color=PAL["cream"], accent=PAL["red"], dy=-70):
        self.title = Typed(title, "sans_semi", 34, 0, 0, t0 + 0.15, cps=22, color=color, track=0.16, seed=seed,
                           gain=-6, caret=False)
        self.sub = Typed(sub, "mono", 21, 0, 0, self.title.t_end + 0.05, cps=40, color=PAL["muted"], track=0.08,
                         seed=seed + 1, gain=-10, caret=False)
        self.t0, self.side, self.accent, self.dy = t0, side, accent, dy
        cue(t0, "map_marker", -6, 0.2 * side)

    def draw(self, c, t, x, y, alpha=1.0):
        if t < self.t0:
            return
        p = ease_out_cubic(clamp((t - self.t0) / 0.35))
        ex, ey = x + self.side * 46 * p, y + self.dy * p
        c.drawLine(x, y, ex, ey, paint(PAL["cream"], a=0.6 * alpha, stroke=1.6))
        lx = ex + self.side * 10
        al = "left" if self.side > 0 else "right"
        self.title.x, self.title.y, self.title.align = lx, ey - 4, al
        self.sub.x, self.sub.y, self.sub.align = lx, ey + 26, al
        self.title.draw(c, t, alpha)
        self.sub.draw(c, t, alpha)


class S3:
    name = "moscow"

    def __init__(self):
        self.start = TL.LINE_START["L04"] - 0.20
        self.end = TL.LINE_START["L05"] - 0.20
        img, meta = load("moscow_map")
        self.meta = meta
        self.lub = tuple(meta["points"]["lubyanka"])
        self.yas = tuple(meta["points"]["yasenevo"])
        self.t_1972 = TL.word_time("L04", "1972")
        self.t_moving = TL.word_time("L04", "moving")
        self.t_archive = TL.word_time("L04", "archive")
        self.t_hq = TL.word_time("L04", "headquarters")
        self.t_outside = TL.word_time("L04", "outside")
        mid = ((self.lub[0] + self.yas[0]) / 2, (self.lub[1] + self.yas[1]) / 2)
        self.route = bezier(self.lub, self.yas, bend=0.16, n=160)
        s = self.start
        self.cam_t = Track([(s, (self.lub[0], self.lub[1] + 60)), (self.t_moving - 0.1, (self.lub[0] - 30, self.lub[1] + 160)),
                            (self.t_hq + 0.2, (mid[0] - 10, mid[1] + 60), ease_in_out_cubic),
                            (self.end - 0.6, (mid[0] - 40, mid[1] + 180), ease_in_out_cubic),
                            (self.end, self.yas, ease_in_expo)])
        self.cam_h = Track([(s, 900.0), (self.t_moving - 0.1, 760.0), (self.t_hq + 0.2, 3500.0, ease_in_out_cubic),
                            (self.end - 0.6, 3250.0, ease_in_out_cubic), (self.end, 160.0, ease_in_expo)])
        self.cam_p = Track([(s, 16.0), (self.t_moving, 24.0), (self.t_hq + 0.2, 40.0, ease_in_out_cubic),
                            (self.end - 0.6, 46.0), (self.end, 30.0, ease_in_expo)])
        # yaw -19 deg turns the SSW route into a straight vertical line on the 9:16 frame
        self.cam_y = Track([(s, -6.0), (self.t_moving, -12.0), (self.t_hq + 0.2, -19.0, ease_in_out_cubic),
                            (self.end, -22.0)])
        self.l_lub = MapLabel("LUBYANKA", "KGB HQ · CENTRAL MOSCOW", s + 0.45, 301, side=1)
        self.l_yas = MapLabel("YASENEVO", "NEW FOREIGN INTEL. HQ", self.t_hq - 0.05, 311, side=1,
                              accent=PAL["amber"], dy=60)
        self.year = Typed("1972", "news", 120, 0, 0, self.t_1972 - 0.05, cps=9, color=PAL["cream"], track=0.02,
                          seed=321, gain=-3, caret=False)
        self.chip = Typed("1972  →  1982", "mono_med", 24, 250, 1690, self.t_archive, cps=24, color=PAL["cream"],
                          track=0.14, align="center", seed=331, gain=-9, caret=False)
        cue(s, "room_archive", -12, 0.0, dur=self.end - s + 0.4, fade_in=0.4, fade_out=0.6, loop=True)
        cue(self.t_moving - 0.05, "route_draw", -12, 0.0, dur=2.4, fade_in=0.1, fade_out=0.5, loop=True)
        cue(self.t_moving - 0.4, "whoosh_soft", -11, 0.0, var=2, align="peak", at=self.t_moving + 0.2)
        cue(self.t_outside, "text_pop", -9, 0.0, var=3)
        cue(self.end - 0.55, "whoosh_deep", -8, 0.0, var=1, align="peak", at=self.end)

    def cam(self, t):
        return MapCam(self.cam_t(t), self.cam_h(t), pitch=self.cam_p(t), yaw=self.cam_y(t), fov=34,
                      screen_offset=(0, 170))

    def draw(self, c, t):
        c.drawRect(skia.Rect.MakeWH(W, H), paint((0.02, 0.025, 0.03, 1)))
        cam = self.cam(t)
        arrive = ease_out_cubic(clamp((t - self.start) / 0.5))
        draw_map(c, "moscow_map", cam, alpha=arrive)
        # MKAD ring lights up at "outside"
        mk = smoothstep(self.t_outside - 0.1, self.t_outside + 0.6, t)
        if mk > 0:
            draw_map(c, "moscow_mkad", cam, alpha=0.8 * mk, fog_amt=0.0)
        # route
        rp = ease_in_out_cubic(clamp((t - self.t_moving) / 2.3))
        if rp > 0:
            sp, _ = cam.project(self.route)
            path = path_from_points([tuple(q) for q in sp])
            sub = trim_path(path, 0, rp)
            c.drawPath(sub, paint(PAL["amber"], a=0.35, stroke=16, blur=12))
            c.drawPath(sub, paint(PAL["amber_lt"], a=0.95, stroke=3.2))
            # archive packets streaming along the route
            n = 26
            for k in range(n):
                ph = ((t - self.t_moving) * 0.16 + k / n) % 1.0
                if ph > rp:
                    continue
                idx = ph * (len(self.route) - 1)
                i0 = int(idx)
                f = idx - i0
                uv = self.route[i0] * (1 - f) + self.route[min(i0 + 1, len(self.route) - 1)] * f
                q, w_ = cam.project([uv])
                if w_[0] <= 0:
                    continue
                sc = cam.scale_at(uv)
                sz = max(6.0, 13.0 * sc)
                x, y = q[0]
                fade = smoothstep(0, 0.04, ph) * (1 - smoothstep(0.96, 1.0, ph))
                c.save()
                c.translate(x, y)
                c.rotate(-20 + hash01(k) * 40)
                c.drawRect(skia.Rect.MakeXYWH(-sz, -sz * 0.7, sz * 2, sz * 1.4), paint(PAL["paper"], a=0.9 * fade))
                c.drawLine(-sz * 0.6, -sz * 0.2, sz * 0.6, -sz * 0.2, paint((0.3, 0.25, 0.2, 1), a=0.6 * fade, stroke=1))
                c.restore()
            # distance chip at the middle of the route
            if rp > 0.55:
                mq, _ = cam.project([self.route[len(self.route) // 2]])
                a_ = smoothstep(0.55, 0.75, rp)
                mx, my = mq[0]
                c.drawRRect(rrect(mx + 18, my - 22, 128, 40, 20), paint((0.02, 0.025, 0.03, 1), a=0.75 * a_))
                c.drawRRect(rrect(mx + 18, my - 22, 128, 40, 20), paint(PAL["amber"], a=0.8 * a_, stroke=1.5))
                T.draw(c, "mono_med", "≈ 20 KM", 20, mx + 82, my + 6, paint(PAL["amber_lt"], a=a_), tracking=0.08,
                       align="center")
        # markers + labels
        lq = cam.project([self.lub])[0][0]
        pulse_marker(c, lq[0], lq[1], t, self.start + 0.35, col=PAL["red"])
        self.l_lub.draw(c, t, lq[0], lq[1], alpha=1 - smoothstep(self.end - 0.8, self.end - 0.5, t))
        yq = cam.project([self.yas])[0][0]
        pulse_marker(c, yq[0], yq[1], t, self.t_hq - 0.1, col=PAL["amber"])
        self.l_yas.draw(c, t, yq[0], yq[1], alpha=1 - smoothstep(self.end - 0.5, self.end - 0.3, t))
        # big year, anchored above Lubyanka
        ya = (1 - smoothstep(self.t_moving + 0.2, self.t_moving + 0.7, t))
        if ya > 0:
            self.year.x, self.year.y, self.year.align = lq[0] - 40, lq[1] - 150, "right"
            self.year.draw(c, t, alpha=ya)
        # timeline chip with progress bar
        ca = smoothstep(self.t_archive - 0.1, self.t_archive + 0.3, t) * (1 - smoothstep(self.end - 0.5, self.end - 0.2, t))
        if ca > 0:
            self.chip.draw(c, t, alpha=ca)
            bp = ease_in_out_cubic(clamp((t - self.t_archive) / 3.2))
            c.drawRRect(rrect(250 - 140, 1716, 280, 4, 2), paint(PAL["cream"], a=0.15 * ca))
            c.drawRRect(rrect(250 - 140, 1716, 280 * bp, 4, 2), paint(PAL["amber_lt"], a=0.9 * ca))
        # dive flash into Yasenevo
        d = ease_in_cubic(clamp((t - (self.end - 0.3)) / 0.3))
        if d > 0:
            c.drawRect(skia.Rect.MakeWH(W, H), paint((0.04, 0.035, 0.03, 1), a=d))

    def post(self, t):
        return dict(bloom=0.34, bloom_thresh=0.7, halation=0.07, vignette=0.75, grain=0.045,
                    lift=(0.008, 0.013, 0.02), gain=(1.02, 1.0, 0.98), ca=0.002)

    def mb(self, t):
        if t > self.end - 0.6 or t - self.start < 0.3:
            return 5
        if self.t_moving < t < self.t_hq + 0.4:
            return 3
        return 1
