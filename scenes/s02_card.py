"""S2 — Vasili Mitrokhin, KGB archivist: personnel index card typed in, fingerprint inks in."""
import functools
import math
import numpy as np
import skia
from engine import text as T
from engine.core import (W, H, PAL, clamp, lerp, mix, ease_out_cubic, ease_in_out_cubic, ease_out_expo,
                         ease_in_cubic, ease_out_back, smoothstep, noise1, hash01)
from engine.gfx import paint, lin, rad, layer, xform, rrect, np_to_image, paper_image, fbm
from . import timeline as TL
from .common import cue, Typed, background, dust

CARD_W, CARD_H = 900, 600


@functools.lru_cache(maxsize=None)
def fingerprint_img(size=300, seed=4):
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    x = (xx - size * 0.5) / (size * 0.5)
    y = (yy - size * 0.55) / (size * 0.5)
    warp = (fbm((size, size), base=60, octaves=3, seed=seed) - 0.5) * 0.25
    r = np.sqrt((x / 0.78) ** 2 + (y / 1.0) ** 2) + warp
    ang = np.arctan2(y, x)
    f = r + 0.06 * np.sin(2 * ang + 1.3) + 0.03 * np.sin(5 * ang)
    ridges = 0.5 + 0.5 * np.sin(f * 2 * np.pi * 15)
    ridges = np.clip((ridges - 0.42) * 3.2, 0, 1)
    breaks = np.clip((fbm((size, size), base=7, octaves=2, seed=seed + 1) - 0.30) * 4, 0, 1)
    mask = np.clip((1.02 - np.sqrt((x / 0.80) ** 2 + (y / 0.98) ** 2)) * 7, 0, 1)
    ink = ridges * breaks * mask * (0.75 + 0.25 * fbm((size, size), base=30, octaves=2, seed=seed + 2))
    col = np.array([0.10, 0.11, 0.17])
    rgba = np.zeros((size, size, 4), np.float32)
    rgba[..., :3] = col[None, None, :] * ink[..., None]
    rgba[..., 3] = ink
    return np_to_image(rgba)


@functools.lru_cache(maxsize=None)
def portrait_img(w=230, h=290):
    """Halftone head-and-shoulders silhouette (deliberately anonymous, not a likeness)."""
    surf = skia.Surface(w, h)
    c = surf.getCanvas()
    c.clear(skia.Color4f(0.86, 0.83, 0.76, 1))
    # tonal study: background gradient, head, shoulders, lit from the left
    img = np.zeros((h, w), np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    bg = 0.18 + 0.14 * (yy / h)
    head = ((xx - w * 0.5) / 56) ** 2 + ((yy - h * 0.38) / 72) ** 2 < 1
    neck = (np.abs(xx - w * 0.5) < 24) & (yy > h * 0.5) & (yy < h * 0.68)
    sh = ((xx - w * 0.5) / 125) ** 2 + ((yy - h * 1.04) / 95) ** 2 < 1
    shade_head = 0.12 + 0.42 * np.clip((xx - w * 0.36) / (w * 0.42), 0, 1) ** 1.4
    tone = bg.copy()
    tone[sh] = 0.88                                   # dark suit
    shirt = sh & (np.abs(xx - w * 0.5) < 30 - (yy - h * 0.72) * 0.0) & (yy < h * 0.95)
    tone[shirt] = 0.10
    tie = sh & (np.abs(xx - w * 0.5) < 8) & (yy > h * 0.74)
    tone[tie] = 0.75
    tone[neck] = 0.30 + 0.25 * (xx[neck] / w)
    tone[head] = shade_head[head]
    hair = head & (yy < h * 0.25 + 6 * np.sin(xx / 9.0))
    tone[hair] = 0.82
    for ex in (-26, 26):                              # spectacles: two thin rings + bridge
        ring = np.abs(np.sqrt((xx - w * 0.5 - ex) ** 2 + (yy - h * 0.38) ** 2) - 15) < 2.6
        tone[ring] = 0.9
    bridge = (np.abs(yy - h * 0.38) < 2) & (np.abs(xx - w * 0.5) < 11)
    tone[bridge] = 0.9
    tone = np.clip(tone + (fbm((h, w), base=20, octaves=2, seed=9) - 0.5) * 0.08, 0, 1)
    p = paint((0.12, 0.11, 0.12, 1))
    step = 6.0
    for gy in np.arange(step / 2, h, step):
        for gx in np.arange(step / 2 + (step / 2 if int(gy / step) % 2 else 0), w, step):
            d = tone[int(min(gy, h - 1)), int(min(gx, w - 1))]
            rr = step * 0.62 * math.sqrt(d)
            if rr > 0.3:
                c.drawCircle(gx, gy, rr, p)
    return surf.makeImageSnapshot()


class S2:
    name = "card"

    def __init__(self):
        L3 = TL.LINE_START["L03"]
        self.start = TL.LINE_START["L03"] - 0.30
        self.end = TL.LINE_START["L04"] - 0.20
        self.t_name = TL.word_time("L03", "vasili")
        self.t_arch = TL.word_time("L03", "archivist")
        x0 = 0  # card-local coordinates (origin top-left of card)
        fx = 330
        t = self.start + 0.35
        self.header = Typed("КГБ СССР  ·  ПЕРВОЕ ГЛАВНОЕ УПРАВЛЕНИЕ", "typewriter", 21, 40, 62, t, cps=40,
                            color=(0.25, 0.20, 0.18, 1), track=0.08, seed=201, gain=-8, caret=False)
        rows = [("ФАМИЛИЯ", "МИТРОХИН", "SURNAME"), ("ИМЯ", "ВАСИЛИЙ НИКИТИЧ", "NAME"),
                ("РОД.", "1922", "BORN"), ("ОТДЕЛ", "АРХИВ  ·  ПГУ", "ARCHIVE, FOREIGN INTEL.")]
        self.fields = []
        tt = self.t_name - 0.05
        for i, (k, v, en) in enumerate(rows):
            y = 168 + i * 92
            lab = Typed(k, "typewriter", 22, fx, y, tt, cps=38, color=(0.45, 0.38, 0.33, 1), track=0.1,
                        seed=210 + i, gain=-9, caret=False)
            val = Typed(v, "typewriter", 34 if i == 0 else 29, fx + 150, y, lab.t_end + 0.04, cps=24,
                        color=(0.10, 0.09, 0.09, 1), track=0.04, seed=220 + i, gain=-4, caret=(i == 3))
            sub = Typed(en, "mono", 15, fx + 150, y + 26, val.t_end + 0.02, cps=60, color=(0.45, 0.42, 0.38, 1),
                        track=0.08, seed=230 + i, sound=False, caret=False)
            self.fields.append((lab, val, sub))
            tt = val.t_end + 0.06
        self.t_print = self.t_arch - 0.1
        cue(self.t_print, "stamp", -8, 0.15)
        cue(self.start, "paper_slide", -10, 0.0, var=1)
        cue(self.end - 0.32, "whoosh_soft", -10, -0.2, var=1, align="peak", at=self.end)

    def draw(self, c, t):
        lt = t - self.start
        background(c, t, top=(0.06, 0.055, 0.05, 1), bottom=(0.015, 0.014, 0.013, 1), light=(400, 900),
                   light_col=PAL["amber_lt"], light_r=1200, light_a=0.16, haze=0.03, seed=3)
        # camera: arrives from extreme close-up on paper grain, settles, drifts; exits with a push-through
        arrive = ease_out_expo(clamp(lt / 1.1))
        exit_p = ease_in_cubic(clamp((t - (self.end - 0.32)) / 0.32))
        s = lerp(3.2, 1.1, arrive) * (1 + 0.035 * clamp(lt / 4.0)) * (1 + exit_p * 0.6)
        rot = lerp(-6.0, -2.2, arrive)
        cx, cy = W / 2, 1060
        alpha = 1 - exit_p
        with layer(c, alpha=alpha, blur=exit_p * 14):
            c.save()
            c.translate(cx, cy)
            c.rotate(rot)
            c.scale(s, s)
            c.translate(-CARD_W / 2, -CARD_H / 2)
            # shadow + card
            c.drawRRect(rrect(14, 26, CARD_W, CARD_H, 10), paint((0, 0, 0, 1), a=0.6, blur=30))
            card = rrect(0, 0, CARD_W, CARD_H, 8)
            c.save()
            c.clipRRect(card, doAntiAlias=True)
            pimg = paper_image(900, 600, 5, tint=(0.93, 0.90, 0.82))
            c.drawImage(pimg, 0, 0)
            # ruled lines
            for i in range(5):
                y = 186 + i * 92
                c.drawLine(fx := 330, y + 12, CARD_W - 40, y + 12, paint((0.55, 0.62, 0.72, 1), a=0.35, stroke=1.2))
            c.drawLine(30, 96, CARD_W - 30, 96, paint(PAL["red"], a=0.7, stroke=2.0))
            c.drawLine(30, 101, CARD_W - 30, 101, paint(PAL["red"], a=0.5, stroke=1.0))
            # warm lamp falloff across the card
            c.drawRect(skia.Rect.MakeWH(CARD_W, CARD_H),
                       paint(shader=rad((200, 120), 900, [(1, 0.9, 0.7, 0.10), (0, 0, 0, 0.0), (0, 0, 0, 0.22)],
                                        [0, 0.6, 1])))
            c.restore()
            # photo + paperclip
            ph_x, ph_y = 44, 140
            c.drawRect(skia.Rect.MakeXYWH(ph_x + 4, ph_y + 6, 230, 290), paint((0, 0, 0, 1), a=0.35, blur=6))
            c.drawImage(portrait_img(), ph_x, ph_y)
            c.drawRect(skia.Rect.MakeXYWH(ph_x, ph_y, 230, 290), paint((1, 1, 1, 1), a=0.25, stroke=2))
            clip = skia.Path()
            clip.addRoundRect(skia.Rect.MakeXYWH(ph_x + 150, ph_y - 30, 34, 110), 17, 17)
            clip.addRoundRect(skia.Rect.MakeXYWH(ph_x + 157, ph_y - 18, 20, 80), 10, 10)
            c.drawPath(clip, paint((0.2, 0.2, 0.22, 1), a=0.5, stroke=4.5, blur=2))
            c.drawPath(clip, paint((0.78, 0.80, 0.84, 1), stroke=3.2))
            c.drawPath(clip, paint((1, 1, 1, 1), a=0.6, stroke=1.0))
            # text
            self.header.draw(c, t)
            for lab, val, sub in self.fields:
                lab.draw(c, t)
                val.draw(c, t)
                sub.draw(c, t, alpha=0.9)
            # fingerprint inks in
            fp = ease_out_cubic(clamp((t - self.t_print) / 0.25))
            if fp > 0:
                img = fingerprint_img()
                p = skia.Paint()
                p.setAlphaf(0.78 * fp)
                p.setBlendMode(skia.BlendMode.kMultiply)
                c.save()
                c.translate(CARD_W - 105, CARD_H - 112)
                c.rotate(12)
                sc = 0.46 * (1.0 + (1 - fp) * 0.12)
                c.scale(sc, sc)
                c.drawImage(img, -150, -150, skia.SamplingOptions(skia.FilterMode.kLinear), p)
                c.restore()
                T.draw(c, "typewriter", "ОТПЕЧАТОК", 14, CARD_W - 150, CARD_H - 22,
                       paint((0.4, 0.35, 0.32, 1), a=0.8 * fp), tracking=0.12)
            c.restore()
        dust(c, t, n=22, seed=12, region=(80, 600, 920, 1100), alpha=0.3, size=(1.0, 4.0))

    def post(self, t):
        return dict(bloom=0.22, bloom_thresh=0.82, halation=0.06, vignette=0.7, grain=0.05,
                    lift=(0.014, 0.012, 0.012), gain=(1.03, 0.99, 0.94), ca=0.0016)

    def mb(self, t):
        lt = t - self.start
        return 5 if lt < 0.7 or t > self.end - 0.35 else 1
