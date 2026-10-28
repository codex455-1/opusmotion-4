"""Shared scene toolkit: atmosphere, typed text (with synced SFX cues), callouts, markers."""
import math
import functools
import numpy as np
import skia
from engine import text as T
from engine.core import (W, H, PAL, clamp, lerp, mix, hash01, noise1, ease_out_cubic, ease_out_expo,
                         ease_in_out_cubic, ease_in_cubic, ease_out_back, smoothstep)
from engine.gfx import paint, lin, rad, layer, rrect, path_from_points, trim_path, np_to_image, fbm

# ---------------------------------------------------------------------------------------------
# SFX cue registry. Every scene registers its sounds at import time with absolute times so the
# audio mix is frame-locked to the picture.  (time, name, gain_db, pan)
# ---------------------------------------------------------------------------------------------
CUES = []


def cue(t, name, gain=0.0, pan=0.0, **kw):
    CUES.append(dict(t=float(t), name=name, gain=gain, pan=pan, **kw))


# ---------------------------------------------------------------------------------------------
# Typing: humanised per-character reveal times + thock cues
# ---------------------------------------------------------------------------------------------
def type_times(text, t0, cps=16.0, seed=0, jitter=0.35):
    """Reveal time for each character. Spaces/punctuation get natural micro-pauses."""
    out, t = [], t0
    base = 1.0 / cps
    for i, ch in enumerate(text):
        out.append(t)
        r = hash01(seed, i)
        d = base * (1 + (r - 0.5) * 2 * jitter)
        if ch in " ·—-":
            d *= 1.35
        if ch in ",.:;":
            d *= 2.2
        t += d
    return out


def register_typing(text, times, gain=-4.0, pan=0.0, seed=0):
    for i, (ch, tt) in enumerate(zip(text, times)):
        if ch == " ":
            cue(tt, "key_space", gain - 1.5, pan, var=int(hash01(seed, i, 3) * 3))
        elif ch == "\n":
            cue(tt, "key_enter", gain, pan, var=int(hash01(seed, i, 5) * 2))
        else:
            cue(tt, "key_thock", gain + (hash01(seed, i, 7) - 0.5) * 2.5, pan + (hash01(seed, i, 9) - 0.5) * 0.12,
                var=int(hash01(seed, i, 11) * 12))


class Typed:
    """A single line of text that types itself in, with a soft ink-settle per glyph and a caret."""

    def __init__(self, txt, font, size, x, y, t0, cps=16.0, color=PAL["cream"], track=0.0, align="left",
                 seed=0, sound=True, gain=-4.0, pan=0.0, caret=True, ink=False):
        self.txt, self.font, self.size, self.x, self.y = txt, font, size, x, y
        self.color, self.track, self.align, self.caret, self.ink = color, track, align, caret, ink
        self.times = type_times(txt, t0, cps, seed)
        self.t0 = t0
        self.t_end = self.times[-1] if self.times else t0
        self.shaped = T.shape(font, txt, size, track)
        # map glyph -> char index (cluster)
        self.gtime = [self.times[min(c, len(self.times) - 1)] for c in self.shaped.clusters]
        if sound:
            register_typing(txt, self.times, gain, pan, seed)

    def width(self):
        return self.shaped.width

    def draw(self, canvas, t, alpha=1.0, color=None, dx=0.0, dy=0.0):
        if t < self.t0 - 0.01 or alpha <= 0:
            return
        s = self.shaped
        x = self.x + dx
        if self.align == "center":
            x -= s.width / 2
        elif self.align == "right":
            x -= s.width
        col = color or self.color
        n = 0
        for gi, gt in enumerate(self.gtime):
            if t >= gt:
                n = gi + 1
        if n == 0:
            return
        # settled glyphs in one blob; the newest glyph gets an ink "press" (slightly bold+bright)
        last_t = self.gtime[n - 1]
        p_new = clamp((t - last_t) / 0.09)
        blob = s.blob(0, n - 1) if n > 1 else None
        if blob is not None:
            canvas.drawTextBlob(blob, x, self.y + dy, paint(col, a=alpha))
        b2 = s.blob(n - 1, n)
        if b2 is not None:
            a2 = alpha * (0.4 + 0.6 * ease_out_cubic(p_new))
            canvas.drawTextBlob(b2, x, self.y + dy - (1 - p_new) * 1.5, paint(col, a=a2))
        if self.caret and t < self.t_end + 0.6:
            blink = 1.0 if t < self.t_end + 0.05 else (1.0 if int((t - self.t_end) * 3.2) % 2 == 0 else 0.0)
            cx = x + (s.xs[n - 1] + s.adv[n - 1] if n <= len(s.xs) else s.width) + 3
            asc = self.size * 0.74
            canvas.drawRect(skia.Rect.MakeXYWH(cx, self.y + dy - asc, max(2.0, self.size * 0.07), asc * 1.12),
                            paint(col, a=alpha * 0.85 * blink))


# ---------------------------------------------------------------------------------------------
# Atmosphere
# ---------------------------------------------------------------------------------------------
@functools.lru_cache(maxsize=4)
def _haze_tex(seed=0):
    n = fbm((480, 270), base=90, octaves=5, seed=seed)
    arr = np.stack([n, n, n, np.ones_like(n)], -1).astype(np.float32)
    return np_to_image(arr)


def background(canvas, t, top=PAL["ink2"], bottom=PAL["ink"], light=(540, 700), light_col=None, light_r=1100,
               light_a=0.22, haze=0.05, seed=0):
    canvas.drawRect(skia.Rect.MakeWH(W, H), paint(shader=lin((0, 0), (0, H), [top, bottom])))
    if light_col is not None and light_a > 0:
        canvas.drawRect(skia.Rect.MakeWH(W, H),
                        paint(shader=rad(light, light_r, [light_col, (light_col[0], light_col[1], light_col[2], 0)],
                                         alpha=light_a)))
    if haze > 0:
        img = _haze_tex(seed)
        p = skia.Paint()
        p.setAlphaf(haze)
        p.setBlendMode(skia.BlendMode.kScreen)
        dx = math.sin(t * 0.07) * 40
        canvas.drawImageRect(img, skia.Rect.MakeXYWH(-80 + dx, -80, W + 160, H + 160),
                             skia.SamplingOptions(skia.FilterMode.kLinear), p)


def dust(canvas, t, n=40, seed=1, region=(0, 0, W, H), color=PAL["amber_lt"], alpha=0.5, size=(1.5, 5.0),
         drift=(6, -10)):
    x0, y0, w, h = region
    for i in range(n):
        r1, r2, r3, r4 = (hash01(seed, i, k) for k in range(4))
        px = x0 + (r1 * w + t * drift[0] * (0.5 + r3) + noise1(t * 0.3 + i, seed) * 30) % w
        py = y0 + (r2 * h + t * drift[1] * (0.5 + r4)) % h
        sz = lerp(size[0], size[1], r3 ** 2)
        tw = 0.5 + 0.5 * math.sin(t * (0.8 + r4 * 1.7) + i)
        blur = sz * (0.6 + 1.6 * r4)  # depth of field: bigger = closer = blurrier
        canvas.drawCircle(px, py, sz, paint(color, a=alpha * (0.25 + 0.75 * tw) * (0.4 + 0.6 * r1), blur=blur))


def light_cone(canvas, apex, base_y, half_w, col=PAL["amber_lt"], a=0.10, blur=40):
    p = path_from_points([(apex[0] - 30, apex[1]), (apex[0] + 30, apex[1]), (apex[0] + half_w, base_y),
                          (apex[0] - half_w, base_y)], closed=True)
    canvas.drawPath(p, paint(shader=lin(apex, (apex[0], base_y), [col, (col[0], col[1], col[2], 0.0)], alpha=a),
                             blur=blur))


# ---------------------------------------------------------------------------------------------
# Callouts / labels / markers
# ---------------------------------------------------------------------------------------------
class Callout:
    """Leader line from an anchor point to a typed label. Line draws, dot pops, label types."""

    def __init__(self, anchor, elbow, label, t0, sub=None, color=PAL["cream"], accent=PAL["amber"], size=28,
                 align="left", seed=0, gain=-7.0):
        self.anchor, self.elbow, self.t0 = anchor, elbow, t0
        self.color, self.accent, self.align = color, accent, align
        lw = T.text_width("mono_med", label, size, 0.06)
        if sub:
            lw = max(lw, T.text_width("mono", sub, size * 0.72, 0.04))
        d = 1 if align == "left" else -1
        self.end = (elbow[0] + d * (lw + 18), elbow[1])
        lx = elbow[0] + d * 6
        # label sits on the horizontal run of the leader; sub-label hangs below it
        self.label = Typed(label, "mono_med", size, lx, elbow[1] - size * 0.42, t0 + 0.38, cps=26,
                           color=color, track=0.06, align=align, seed=seed, gain=gain, caret=False)
        self.sub = None
        if sub:
            self.sub = Typed(sub, "mono", size * 0.72, lx, elbow[1] + size * 1.02,
                             self.label.t_end + 0.05, cps=34, color=PAL["muted"], track=0.04, align=align,
                             seed=seed + 1, gain=gain - 3, caret=False)
        cue(t0, "text_soft", gain - 2)

    def draw(self, canvas, t, alpha=1.0):
        if t < self.t0 or alpha <= 0:
            return
        p = ease_out_cubic(clamp((t - self.t0) / 0.42))
        pts = [self.anchor, self.elbow, self.end]
        path = path_from_points(pts)
        sub = trim_path(path, 0, p)
        canvas.drawPath(sub, paint(self.color, a=0.75 * alpha, stroke=2.0))
        dp = ease_out_back(clamp((t - self.t0) / 0.3))
        canvas.drawCircle(*self.anchor, 14 * dp, paint(self.accent, a=0.25 * alpha, blur=6))
        canvas.drawCircle(*self.anchor, 5.5 * dp, paint(self.accent, a=alpha))
        self.label.draw(canvas, t, alpha)
        if self.sub:
            self.sub.draw(canvas, t, alpha)


def pulse_marker(canvas, x, y, t, t0, col=PAL["red"], r=9, alpha=1.0):
    if t < t0:
        return
    p = ease_out_back(clamp((t - t0) / 0.35), 2.0)
    for k in range(2):
        ph = ((t - t0) * 0.7 + k * 0.5) % 1.0
        canvas.drawCircle(x, y, r + ph * 46, paint(col, a=alpha * 0.55 * (1 - ph) ** 2, stroke=2.0))
    canvas.drawCircle(x, y, r * 2.4 * p, paint(col, a=0.22 * alpha, blur=10))
    canvas.drawCircle(x, y, r * p, paint(col, a=alpha))
    canvas.drawCircle(x, y, r * 0.38 * p, paint(PAL["cream"], a=alpha))


def label_caps(canvas, txt, x, y, size=26, color=PAL["cream"], a=1.0, track=0.22, align="left", font="sans_med"):
    T.draw(canvas, font, txt, size, x, y, paint(color, a=a), tracking=track, align=align)


def redaction(canvas, x, y, w, h, p, col=(0.02, 0.02, 0.025, 1.0)):
    """Marker-style redaction bar that swipes in left->right (p in 0..1)."""
    if p <= 0:
        return
    ww = w * ease_out_cubic(p)
    pth = skia.Path()
    pth.addRoundRect(skia.Rect.MakeXYWH(x, y, ww, h), h * 0.18, h * 0.18)
    canvas.drawPath(pth, paint(col))
