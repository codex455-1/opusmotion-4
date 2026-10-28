"""S11 — End card: the FBI's verdict, the title, and where the notes are today."""
import skia
from engine import text as T
from engine.core import W, H, PAL, clamp, ease_out_cubic, ease_out_expo, smoothstep, lerp
from engine.gfx import paint, lin, rad
from . import timeline as TL
from .common import cue, Typed, dust


class S11:
    name = "end"

    def __init__(self):
        self.start = TL.LINE_END["L12"] + 0.20
        self.end = TL.DURATION + 0.01
        s = self.start
        q1 = "“The most complete and extensive"
        q2 = "intelligence ever received"
        q3 = "from any source.”"
        self.q = []
        t = s + 0.25
        for i, ln in enumerate((q1, q2, q3)):
            ty = Typed(ln, "mono", 34, W / 2, 800 + i * 56, t, cps=60, color=PAL["cream"], track=0.0, align="center",
                       seed=1201 + i, gain=-5, caret=(i == 2))
            self.q.append(ty)
            t = ty.t_end + 0.05
        self.attr = Typed("— FBI, ON THE MITROKHIN ARCHIVE", "mono", 20, W / 2, 1010, t + 0.03, cps=70, color=PAL["muted"],
                          track=0.16, align="center", seed=1211, gain=-10, caret=False)
        self.t_title = min(self.attr.t_end + 0.2, s + 2.4)
        cue(self.t_title - 0.02, "final_hit", -4, 0.0, var=0)
        cue(self.t_title, "text_pop", -10, 0.0, var=5)
        cue(s, "room_archive", -16, 0.0, dur=self.end - s, fade_in=0.4, fade_out=1.2, loop=True)

    def draw(self, c, t):
        c.drawRect(skia.Rect.MakeWH(W, H), paint(shader=lin((0, 0), (0, H), [(0.03, 0.032, 0.036, 1), (0.008, 0.008, 0.01, 1)])))
        qa = 1 - smoothstep(self.t_title - 0.1, self.t_title + 0.35, t)
        for ty in self.q:
            ty.draw(c, t, alpha=qa)
        self.attr.draw(c, t, alpha=qa)
        tp = ease_out_expo(clamp((t - self.t_title) / 1.1))
        if tp > 0:
            c.drawRect(skia.Rect.MakeWH(W, H), paint(shader=rad((540, 940), 700, [(1, 0.8, 0.55, 0.10 * tp), (1, 0.8, 0.55, 0)])))
            blur = (1 - tp) * 18
            T.draw(c, "sans_med", "THE", 26, W / 2, 820, paint(PAL["muted"], a=tp, blur=blur * 0.5), tracking=0.6, align="center")
            T.draw(c, "news", "Mitrokhin", 150, W / 2, 960 + (1 - tp) * 30, paint(PAL["cream"], a=tp, blur=blur), tracking=-0.01,
                   align="center")
            T.draw(c, "sans_med", "ARCHIVE", 30, W / 2, 1030, paint(PAL["cream"], a=tp, blur=blur * 0.5), tracking=0.62, align="center")
            c.drawLine(W / 2 - 160 * tp, 1080, W / 2 + 160 * tp, 1080, paint(PAL["red"], a=tp, stroke=2.5))
            sa = smoothstep(self.t_title + 0.4, self.t_title + 1.0, t)
            T.draw(c, "mono", "OPEN TO THE PUBLIC SINCE 2014", 21, W / 2, 1140, paint(PAL["cream"], a=0.85 * sa), tracking=0.2,
                   align="center")
            T.draw(c, "mono", "CHURCHILL ARCHIVES CENTRE · CAMBRIDGE", 21, W / 2, 1176, paint(PAL["muted"], a=sa), tracking=0.16,
                   align="center")
            fa = smoothstep(self.t_title + 0.8, self.t_title + 1.4, t)
            src = ["Sources: ISC, The Mitrokhin Inquiry Report (2000) · Andrew & Mitrokhin, The Sword and the Shield (1999)",
                   "G. Corera, The Spy in the Archive (2025) · BBC (1999) · AP (2014) · University of Cambridge (2014)",
                   "Illustrative reconstruction · Map data © OpenStreetMap contributors · Natural Earth"]
            for i, sl in enumerate(src):
                T.draw(c, "sans_light", sl, 17, W / 2, 1650 + i * 28, paint(PAL["muted"], a=0.75 * fa), align="center")
        dust(c, t, n=16, seed=41, region=(150, 600, 780, 700), alpha=0.25, size=(1.0, 3.0))
        fi = 1 - ease_out_cubic(clamp((t - self.start) / 0.3))
        if fi > 0:
            c.drawRect(skia.Rect.MakeWH(W, H), paint((0, 0, 0, 1), a=fi))
        fo = smoothstep(self.end - 0.6, self.end - 0.05, t)
        if fo > 0:
            c.drawRect(skia.Rect.MakeWH(W, H), paint((0, 0, 0, 1), a=fo))

    def post(self, t):
        return dict(bloom=0.30, bloom_thresh=0.7, halation=0.08, vignette=0.75, grain=0.045,
                    lift=(0.010, 0.010, 0.012), gain=(1.02, 1.0, 0.97), ca=0.0015)

    def mb(self, t):
        return 1
