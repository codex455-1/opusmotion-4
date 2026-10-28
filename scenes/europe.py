"""Shared Europe-map helpers (S6 break-up, S8 exfiltration)."""
import math
import numpy as np
import skia
from engine import text as T
from engine.core import W, H, PAL, clamp, ease_out_cubic, ease_out_back, smoothstep
from engine.gfx import paint, path_from_points, trim_path, rrect
from .mapview import load, MapCam, draw_map, bezier
from .common import Typed, cue


def meta():
    return load("europe")[1]


def city(name):
    return tuple(meta()["cities"][name])


def poly_path(pts, offset=(0.0, 0.0)):
    return path_from_points([(p[0] + offset[0], p[1] + offset[1]) for p in pts], closed=True)


def draw_in_map(c, cam, fn):
    """Run fn(c) with the canvas in map-pixel space (perspective applied)."""
    c.save()
    c.concat(cam.matrix())
    fn(c)
    c.restore()


def screen_path(cam, pts):
    sp, w = cam.project(pts)
    return path_from_points([tuple(q) for q in sp]), sp


def city_dot(c, cam, uv, t, t0, col=PAL["cream"], r=6.0, alpha=1.0):
    if t < t0:
        return None
    (x, y), = cam.project([uv])[0]
    p = ease_out_back(clamp((t - t0) / 0.3), 2.0)
    c.drawCircle(x, y, r * 2.6 * p, paint(col, a=0.18 * alpha, blur=8))
    c.drawCircle(x, y, r * p, paint(col, a=alpha))
    return x, y


class Tag:
    """Small typed map tag: title + sub, with a leader to the anchor."""

    def __init__(self, title, sub, t0, seed, dx=40, dy=-60, size=26, color=PAL["cream"], gain=-8):
        self.t0, self.dx, self.dy = t0, dx, dy
        self.title = Typed(title, "sans_semi", size, 0, 0, t0 + 0.12, cps=26, color=color, track=0.14, seed=seed,
                           gain=gain, caret=False)
        self.sub = Typed(sub, "mono", size * 0.72, 0, 0, self.title.t_end + 0.03, cps=40, color=PAL["muted"],
                         track=0.08, seed=seed + 1, gain=gain - 4, caret=False) if sub else None
        self.size = size

    def draw(self, c, t, x, y, alpha=1.0, strike=0.0):
        if t < self.t0 or alpha <= 0:
            return
        p = ease_out_cubic(clamp((t - self.t0) / 0.3))
        ex, ey = x + self.dx * p, y + self.dy * p
        c.drawLine(x, y, ex, ey, paint(PAL["cream"], a=0.55 * alpha, stroke=1.5))
        al = "left" if self.dx >= 0 else "right"
        lx = ex + (8 if self.dx >= 0 else -8)
        self.title.x, self.title.y, self.title.align = lx, ey - 2, al
        self.title.draw(c, t, alpha)
        if self.sub:
            self.sub.x, self.sub.y, self.sub.align = lx, ey + self.size * 0.95, al
            self.sub.draw(c, t, alpha)
        if strike > 0:
            wd = self.title.width()
            x0 = lx if al == "left" else lx - wd
            c.drawLine(x0 - 4, ey - self.size * 0.33, x0 - 4 + (wd + 8) * ease_out_cubic(strike), ey - self.size * 0.33,
                       paint(PAL["red"], a=alpha, stroke=3.2))
