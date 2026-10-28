"""S8 — MI6 smuggles him and his family out (Nov 1992): train, minibus, boat... London. The notes followed."""
import math
import numpy as np
import skia
from engine import text as T
from engine.core import (W, H, PAL, clamp, lerp, mix, ease_out_cubic, ease_in_out_cubic, ease_out_expo,
                         ease_in_expo, ease_in_cubic, ease_out_back, smoothstep, hash01, Track)
from engine.gfx import paint, lin, rad, path_from_points, trim_path, rrect, path_point
from . import timeline as TL
from .common import cue, Typed
from .mapview import MapCam, draw_map, bezier
from . import europe as E


class S8:
    name = "exfil"

    def __init__(self):
        self.start = TL.LINE_START["L10"] - 0.20
        self.end = TL.LINE_START["L11"] - 0.20
        self.t_mi6 = TL.word_time("L10", "mi6")
        self.t_smug = TL.word_time("L10", "smuggled")
        self.t_family = TL.word_time("L10", "family")
        self.t_russia = TL.word_time("L10", "russia")
        self.t_notes = TL.word_time("L10", "notes")
        self.t_fol = TL.word_time("L10", "followed")
        mos, vil, kla, sea, lon = (E.city(k) for k in ("moscow", "vilnius", "klaipeda", "sea", "london"))
        self.pts = dict(mos=mos, vil=vil, kla=kla, sea=sea, lon=lon)
        self.legs = [("TRAIN", bezier(mos, vil, 0.06, 90)), ("MINIBUS", bezier(vil, kla, -0.12, 40)),
                     ("BOAT", bezier(kla, sea, 0.10, 40)), ("", bezier(sea, lon, -0.18, 120))]
        self.route = np.concatenate([l[1] if i == 0 else l[1][1:] for i, l in enumerate(self.legs)])
        lens = [np.linalg.norm(np.diff(l[1], axis=0), axis=1).sum() for l in self.legs]
        self.cum = np.cumsum([0] + lens) / sum(lens)
        s = self.start
        self.r0, self.r1 = self.t_smug - 0.05, self.t_russia + 0.75
        balt = ((mos[0] + kla[0]) / 2, (mos[1] + kla[1]) / 2)
        wide = ((balt[0] * 0.40 + lon[0] * 0.60), (balt[1] * 0.5 + lon[1] * 0.5) + 60)
        self.cam_t = Track([(s, (balt[0] + 60, balt[1] + 40)), (self.t_family, (balt[0] - 40, balt[1] + 40), ease_in_out_cubic),
                            (self.r1, wide, ease_in_out_cubic), (self.end - 0.45, (wide[0] - 60, wide[1])),
                            (self.end, lon, ease_in_expo)])
        self.cam_h = Track([(s, 1500.0), (self.t_family, 1450.0), (self.r1, 3500.0, ease_in_out_cubic),
                            (self.end - 0.45, 3350.0), (self.end, 140.0, ease_in_expo)])
        self.cam_p = Track([(s, 30.0), (self.r1, 26.0, ease_in_out_cubic), (self.end, 22.0)])
        self.chip = Typed("MI6 EXFILTRATION  ·  NOVEMBER 1992", "mono_med", 23, W / 2, 1700, self.t_mi6 + 0.05, cps=36,
                          color=PAL["cream"], track=0.14, align="center", seed=801, gain=-8, caret=False)
        self.tag_l = E.Tag("LONDON", "MI6 HEADQUARTERS", self.r1 - 0.25, 811, dx=40, dy=-80, size=30)
        cue(s, "wind_soft", -18, 0.0, dur=self.end - s, fade_in=0.3, fade_out=0.4, loop=True)
        cue(self.r0, "train_loop", -10, -0.1, dur=(self.r1 - self.r0) * self.cum[1] + 0.3, fade_in=0.15, fade_out=0.3, loop=True)
        cue(self.r0 + (self.r1 - self.r0) * self.cum[2], "boat_loop", -12, 0.1, dur=(self.r1 - self.r0) * (self.cum[3] - self.cum[2]) + 0.5,
            fade_in=0.1, fade_out=0.3, loop=True)
        cue(self.r0 + (self.r1 - self.r0) * self.cum[3] - 0.2, "whoosh_deep", -11, 0.0, var=0, align="peak",
            at=self.r0 + (self.r1 - self.r0) * 0.92)
        cue(self.r1 - 0.25, "map_marker", -6, -0.2, var=1)
        cue(self.t_notes - 0.05, "paper_flutter", -12, 0.0, var=1)
        cue(self.end - 0.5, "whoosh_deep", -9, 0.0, var=1, align="peak", at=self.end)

    def cam(self, t):
        return MapCam(self.cam_t(t), self.cam_h(t), pitch=self.cam_p(t), yaw=-4.0, fov=34, screen_offset=(0, 170))

    def draw(self, c, t):
        c.drawRect(skia.Rect.MakeWH(W, H), paint((0.015, 0.02, 0.03, 1)))
        cam = self.cam(t)
        draw_map(c, "europe", cam, alpha=ease_out_cubic(clamp((t - self.start) / 0.35)), fog=(0.015, 0.02, 0.03))
        rp = ease_in_out_cubic(clamp((t - self.r0) / (self.r1 - self.r0)))
        path, sp = E.screen_path(cam, self.route)
        # leg styling: solid for land/sea, dashed for the final leg to Britain
        for i, (mode, pts) in enumerate(self.legs):
            a0, a1 = self.cum[i], self.cum[i + 1]
            if rp <= a0:
                continue
            lp = clamp((rp - a0) / (a1 - a0))
            lpath, lsp = E.screen_path(cam, pts)
            sub = trim_path(lpath, 0, lp)
            c.drawPath(sub, paint(PAL["amber"], a=0.3, stroke=14, blur=10))
            st = paint(PAL["amber_lt"], a=0.95, stroke=3.0)
            if i == 3:
                st.setPathEffect(skia.DashPathEffect.Make([12, 10], 0))
            if i == 2:
                st.setPathEffect(skia.DashPathEffect.Make([2, 7], 0))
            c.drawPath(sub, st)
            if mode and lp > 0.3:
                (mx, my), _ = path_point(lpath, 0.5)
                a_ = smoothstep(0.3, 0.6, lp) * (1 - smoothstep(self.end - 0.6, self.end - 0.3, t))
                wd = T.text_width("mono_med", mode, 22, 0.14) + 28
                c.drawRRect(rrect(mx - wd / 2, my + 16, wd, 38, 19), paint((0.015, 0.02, 0.03, 1), a=0.8 * a_))
                c.drawRRect(rrect(mx - wd / 2, my + 16, wd, 38, 19), paint(PAL["amber"], a=0.7 * a_, stroke=1.5))
                T.draw(c, "mono_med", mode, 22, mx, my + 42, paint(PAL["amber_lt"], a=a_), tracking=0.14, align="center")
        # the family: three dots travelling together
        if 0 < rp < 1:
            for k in range(3):
                (hx, hy), _ = path_point(path, max(0.0, rp - k * 0.012))
                c.drawCircle(hx, hy, 7.5 - k * 1.2, paint(PAL["cream"]))
            (hx, hy), _ = path_point(path, rp)
            c.drawCircle(hx, hy, 24, paint(PAL["amber"], a=0.3, blur=10))
        for key, t0 in (("mos", self.start + 0.1), ("vil", self.r0 + 0.2), ("kla", self.r0 + 0.6)):
            E.city_dot(c, cam, self.pts[key], t, t0, col=PAL["cream"], r=5.5, alpha=0.9)
        lxy = E.city_dot(c, cam, self.pts["lon"], t, self.r1 - 0.25, col=PAL["red"], r=8)
        if lxy:
            self.tag_l.draw(c, t, *lxy, alpha=1 - smoothstep(self.end - 0.45, self.end - 0.2, t))
        # the notes follow: paper flecks travelling the same route
        if t > self.t_notes - 0.1:
            for k in range(22):
                ph = (t - (self.t_notes - 0.1)) * 0.55 - k * 0.035
                if not (0 < ph < 1):
                    continue
                (px, py), (tx, ty) = path_point(path, ph)
                ang = math.degrees(math.atan2(ty, tx)) + (hash01(k) - 0.5) * 50
                c.save()
                c.translate(px + (hash01(k, 2) - 0.5) * 14, py + (hash01(k, 3) - 0.5) * 14)
                c.rotate(ang)
                c.drawRect(skia.Rect.MakeXYWH(-9, -6, 18, 12), paint(PAL["paper"], a=0.95))
                c.drawLine(-6, -2, 6, -2, paint((0.3, 0.25, 0.2, 1), a=0.6, stroke=1))
                c.restore()
        ca = smoothstep(self.t_mi6, self.t_mi6 + 0.3, t) * (1 - smoothstep(self.end - 0.6, self.end - 0.3, t))
        if ca > 0:
            self.chip.draw(c, t, alpha=ca)
        ex = ease_in_cubic(clamp((t - (self.end - 0.28)) / 0.28))
        if ex > 0:
            c.drawRect(skia.Rect.MakeWH(W, H), paint((0.02, 0.03, 0.045, 1), a=ex))

    def post(self, t):
        return dict(bloom=0.36, bloom_thresh=0.7, halation=0.07, vignette=0.7, grain=0.045, exposure=1.22,
                    lift=(0.010, 0.014, 0.022), gain=(1.0, 1.0, 1.0), ca=0.002)

    def mb(self, t):
        if self.r0 < t < self.r1 + 0.2 or t > self.end - 0.5:
            return 4
        return 1
