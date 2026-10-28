"""S9 — London: MI6 at Century House, hundreds of names, and one of them in a quiet suburb (Bexleyheath)."""
import functools
import math
import numpy as np
import skia
from engine import text as T
from engine.core import (W, H, PAL, clamp, lerp, mix, ease_out_cubic, ease_in_out_cubic, ease_out_expo,
                         ease_in_expo, ease_in_cubic, ease_out_back, smoothstep, hash01, Track)
from engine.gfx import paint, lin, rad, layer, rrect, np_to_image, path_from_points
from engine import gl as G
from . import timeline as TL
from .common import cue, Typed, register_typing, pulse_marker, redaction
from .mapview import load, MapCam, draw_map, CACHE
from . import europe as E


@functools.lru_cache(maxsize=None)
def city_assets():
    d = np.load(CACHE / "london_bldg.npz")
    mesh = G.Mesh(d["pos"], d["nrm"], d["col"])
    img, meta = load("london_core")
    x0, y0, ppk, w, h = meta["x0"], meta["y0"], meta["ppk"], meta["w"], meta["h"]
    tl = (x0, -y0, 0.0)
    tr = (x0 + w / ppk, -y0, 0.0)
    bl = (x0, -(y0 + h / ppk), 0.0)
    br = (x0 + w / ppk, -(y0 + h / ppk), 0.0)
    arr = img.toarray(colorType=skia.ColorType.kRGBA_8888_ColorType)
    plane = G.TexPlane([tl, tr, bl, br], arr)
    return mesh, plane


@functools.lru_cache(maxsize=None)
def renderer():
    return G.Renderer3D(W, H, samples=4)


ROWS = ["AGENT", "CONTACT", "SOURCE", "AGENT", "AGENT", "CONTACT", "SOURCE", "AGENT", "CONTACT", "AGENT", "SOURCE",
        "AGENT", "CONTACT", "AGENT"]


class S9:
    name = "london"

    def __init__(self):
        self.start = TL.LINE_START["L11"] - 0.20
        self.end = TL.LINE_START["L12"] - 0.20
        self.t_inside = TL.word_time("L11", "inside")
        self.t_hundreds = TL.word_time("L11", "hundreds")
        self.t_one = TL.word_time("L11", "one")
        self.t_quiet = TL.word_time("L11", "quiet")
        self.t_suburb = TL.word_time("L11", "suburb")
        self.t_2d = self.t_one - 0.35          # 3D city -> 2D Greater London map
        s = self.start
        self.eye = Track([(s, (-1.35, -3.6, 2.7)), (self.t_2d, (-0.42, -1.05, 0.52), ease_in_out_cubic),
                          (self.t_2d + 0.4, (-0.40, -1.0, 1.4), ease_in_cubic)])
        self.tgt = Track([(s, (0.05, 0.4, 0.0)), (self.t_2d, (0.05, 0.28, 0.04), ease_in_out_cubic)])
        m = load("london_wide")[1]
        self.cen2 = tuple(m["points"]["century"])
        self.bex = tuple(m["points"]["bexleyheath"])
        mid = ((self.cen2[0] + self.bex[0]) / 2, (self.cen2[1] + self.bex[1]) / 2)
        self.c2t = Track([(self.t_2d, self.cen2), (self.t_quiet, (mid[0], mid[1] + 60), ease_in_out_cubic),
                          (self.t_suburb + 0.3, (self.bex[0] - 20, self.bex[1] + 80), ease_in_out_cubic),
                          (self.end - 0.35, (self.bex[0] - 10, self.bex[1] + 40)), (self.end, self.bex, ease_in_expo)])
        self.c2h = Track([(self.t_2d, 420.0), (self.t_quiet, 2600.0, ease_in_out_cubic),
                          (self.t_suburb + 0.3, 1300.0, ease_in_out_cubic), (self.end - 0.35, 1150.0),
                          (self.end, 110.0, ease_in_expo)])
        self.c2p = Track([(self.t_2d, 38.0), (self.t_quiet, 30.0), (self.end, 36.0)])
        self.tag_c = E.Tag("CENTURY HOUSE", "MI6 HQ · 1966–1994", self.t_inside - 0.05, 901, dx=-40, dy=-90, size=30)
        self.tag_b = E.Tag("BEXLEYHEATH", "SOUTH-EAST LONDON", self.t_suburb - 0.05, 911, dx=40, dy=-90, size=34)
        self.tag_l = E.Tag("CENTRAL LONDON", None, self.t_2d + 0.2, 921, dx=-40, dy=60, size=22)
        # the name index: rows type in, list scrolls ever faster
        self.rows = []
        tt = self.t_hundreds - 0.1
        for i in range(len(ROWS)):
            idx = f"№ {137 + i * 41 % 900:04d}"
            times = [tt + k * 0.022 for k in range(len(idx))]
            if i < 6:
                register_typing(idx, times, gain=-11, pan=0.1, seed=950 + i)
            self.rows.append((tt, idx, ROWS[i], 0.35 + 0.5 * hash01(i, 77)))
            if i < 7:
                cue(tt + 0.12, "redact_swipe", -16, 0.05, var=i % 3)
            tt += max(0.06, 0.16 - i * 0.012)
        cue(s, "room_london_night", -9, 0.0, dur=self.end - s + 0.5, fade_in=0.6, fade_out=0.8, loop=True)
        cue(self.t_inside - 0.05, "map_marker", -7, -0.2, var=0)
        cue(self.t_2d - 0.1, "whoosh_soft", -9, 0.2, var=0, align="peak", at=self.t_2d + 0.25)
        cue(self.t_suburb - 0.05, "emph_thump", -7, 0.2, var=2)
        cue(self.t_suburb - 0.02, "map_marker", -5, 0.2, var=2)
        cue(self.end - 0.45, "whoosh_deep", -9, 0.0, var=0, align="peak", at=self.end)

    def city_frame(self, t):
        mesh, plane = city_assets()
        r = renderer()
        eye, tgt = np.array(self.eye(t)), np.array(self.tgt(t))
        V = G.look_at(eye, tgt, (0, 0, 1))
        P = G.perspective(38, W / H, 0.02, 30.0)
        mvp = P @ V
        r.begin()
        dist = float(np.linalg.norm(eye - tgt))
        fog = dict(fogc=(0.018, 0.028, 0.045), fogNear=dist * 0.9, fogFar=dist * 2.6, eye=tuple(eye))
        r.draw_plane(plane, mvp, alpha=1.0, **fog)
        hl = smoothstep(self.t_inside - 0.2, self.t_inside + 0.4, t)
        r.draw_mesh(mesh, mvp, material="city", ldir=(-0.5, 0.6, 0.65), lcol=(0.30, 0.36, 0.48),
                    skyc=(0.42, 0.48, 0.60), winc=(1.0, 0.72, 0.40), winAmt=1.4, hl=(0.0, 0.0), hlR=0.045,
                    hlAmt=hl, hlc=(1.0, 0.36, 0.24), wscale=1000.0, **fog)
        img = r.end()
        return img, mvp

    def draw(self, c, t):
        c.drawRect(skia.Rect.MakeWH(W, H), paint((0.018, 0.028, 0.045, 1)))
        k2 = smoothstep(self.t_2d, self.t_2d + 0.45, t)
        if k2 < 1:
            img, mvp = self.city_frame(min(t, self.t_2d + 0.45))
            with layer(c, alpha=1 - k2, blur=k2 * 10):
                c.drawImage(np_to_image(img), 0, 0)
                # Century House beacon + label
                q = G.project([(0.0, 0.0, 0.082)], mvp)[0][0]
                if t > self.t_inside - 0.1:
                    c.drawLine(q[0], q[1], q[0], q[1] - 40, paint(PAL["red"], a=0.8, stroke=2))
                    pulse_marker(c, q[0], q[1] - 40, t, self.t_inside - 0.1, col=PAL["red"], r=8)
                    self.tag_c.draw(c, t, q[0], q[1] - 40)
            # name index panel
            pa = smoothstep(self.t_hundreds - 0.25, self.t_hundreds + 0.1, t) * (1 - k2)
            if pa > 0:
                x0, y0, wd, hh = 140, 1330, 800, 430
                c.drawRRect(rrect(x0, y0, wd, hh, 18), paint((0.01, 0.015, 0.025, 1), a=0.72 * pa))
                c.drawRRect(rrect(x0, y0, wd, hh, 18), paint(PAL["cream"], a=0.18 * pa, stroke=1.5))
                T.draw(c, "mono_med", "INDEX OF NAMES  ·  KGB AGENTS & CONTACTS", 19, x0 + 30, y0 + 44,
                       paint(PAL["muted"], a=pa), tracking=0.12)
                c.save()
                c.clipRect(skia.Rect.MakeXYWH(x0, y0 + 64, wd, hh - 74))
                n_vis = sum(1 for r_ in self.rows if t >= r_[0])
                scroll = max(0, n_vis - 7) * 56
                sm = scroll  # rows animate individually; list offset eases toward target
                for i, (rt, idx, tag, wfrac) in enumerate(self.rows):
                    if t < rt:
                        continue
                    yy = y0 + 110 + i * 56 - sm
                    ap = ease_out_cubic(clamp((t - rt) / 0.2)) * pa
                    T.draw(c, "mono", idx, 22, x0 + 30, yy, paint(PAL["cream"], a=0.8 * ap), tracking=0.06,
                           n=int(len(idx) * clamp((t - rt) / 0.12)) or None)
                    redaction(c, x0 + 170, yy - 20, (wd - 380) * wfrac + 120, 26, clamp((t - rt - 0.1) / 0.18),
                              col=(0.0, 0.0, 0.0, 0.95 * ap))
                    c.drawRect(skia.Rect.MakeXYWH(x0 + 170, yy - 20, ((wd - 380) * wfrac + 120) * clamp((t - rt - 0.1) / 0.18), 26),
                               paint(PAL["cream"], a=0.10 * ap, stroke=1))
                    T.draw(c, "mono_med", tag, 18, x0 + wd - 30, yy, paint(PAL["red"] if tag == "AGENT" else PAL["muted"], a=ap),
                           tracking=0.14, align="right")
                c.restore()
                c.drawRect(skia.Rect.MakeXYWH(x0, y0 + 64, wd, 60),
                           paint(shader=lin((0, y0 + 64), (0, y0 + 124), [(0.01, 0.015, 0.025, 0.95 * pa), (0.01, 0.015, 0.025, 0)])))
        if k2 > 0:
            cam = MapCam(self.c2t(t), self.c2h(t), pitch=self.c2p(t), yaw=8.0, fov=34, screen_offset=(0, 170))
            with layer(c, alpha=k2):
                draw_map(c, "london_wide", cam, alpha=1.0, fog=(0.018, 0.028, 0.045))
                q = cam.project([self.cen2])[0][0]
                pulse_marker(c, q[0], q[1], t, self.t_2d + 0.1, col=PAL["red"], r=7, alpha=0.7)
                self.tag_l.draw(c, t, q[0], q[1], alpha=1 - smoothstep(self.t_suburb, self.t_suburb + 0.3, t))
                if t > self.t_suburb - 0.1:
                    b = cam.project([self.bex])[0][0]
                    drop = ease_out_back(clamp((t - (self.t_suburb - 0.1)) / 0.4), 1.6)
                    by = b[1] - (1 - drop) * 160
                    # map pin
                    pin = skia.Path()
                    pin.addCircle(b[0], by - 44, 20)
                    pin.moveTo(b[0] - 17, by - 34)
                    pin.lineTo(b[0], by)
                    pin.lineTo(b[0] + 17, by - 34)
                    pin.close()
                    c.drawOval(skia.Rect.MakeLTRB(b[0] - 18, b[1] - 6, b[0] + 18, b[1] + 6), paint((0, 0, 0, 1), a=0.6 * drop, blur=4))
                    c.drawPath(pin, paint(PAL["red"]))
                    c.drawCircle(b[0], by - 44, 7, paint(PAL["cream"]))
                    c.drawCircle(b[0], b[1], 60 * drop, paint(PAL["red"], a=0.15, blur=20))
                    self.tag_b.draw(c, t, b[0] + 10, by - 50, alpha=1 - smoothstep(self.end - 0.35, self.end - 0.15, t))
        fi = 1 - ease_out_cubic(clamp((t - self.start) / 0.4))
        if fi > 0:
            c.drawRect(skia.Rect.MakeWH(W, H), paint((0.02, 0.03, 0.045, 1), a=fi))
        ex = ease_in_cubic(clamp((t - (self.end - 0.25)) / 0.25))
        if ex > 0:
            c.drawRect(skia.Rect.MakeWH(W, H), paint((0.03, 0.035, 0.05, 1), a=ex))

    def post(self, t):
        return dict(bloom=0.45, bloom_thresh=0.62, halation=0.08, vignette=0.75, grain=0.045,
                    lift=(0.006, 0.012, 0.024), gain=(1.0, 1.0, 1.02), ca=0.002)

    def mb(self, t):
        if t > self.end - 0.45 or self.t_2d - 0.1 < t < self.t_2d + 0.5:
            return 3
        return 1
