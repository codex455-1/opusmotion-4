"""Timing, easing and small math helpers shared by every scene."""
import math
import numpy as np

W, H = 1080, 1920
FPS = 30


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def mix(a, b, t):
    return tuple(lerp(x, y, t) for x, y in zip(a, b))


def remap(x, a, b, c=0.0, d=1.0):
    """Map x from [a,b] to [c,d], clamped."""
    if b == a:
        return d if x >= b else c
    return lerp(c, d, clamp((x - a) / (b - a)))


def prog(t, start, dur):
    return clamp((t - start) / dur) if dur > 0 else float(t >= start)


# --- easing -----------------------------------------------------------------
def linear(t):
    return t


def ease_out_cubic(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in_cubic(t):
    t = clamp(t)
    return t ** 3


def ease_in_out_cubic(t):
    t = clamp(t)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_out_expo(t):
    t = clamp(t)
    return 1.0 if t >= 1 else 1 - 2 ** (-10 * t)


def ease_in_expo(t):
    t = clamp(t)
    return 0.0 if t <= 0 else 2 ** (10 * t - 10)


def ease_in_out_expo(t):
    t = clamp(t)
    if t <= 0 or t >= 1:
        return t
    return 2 ** (20 * t - 10) / 2 if t < 0.5 else (2 - 2 ** (-20 * t + 10)) / 2


def ease_out_quint(t):
    t = clamp(t)
    return 1 - (1 - t) ** 5


def ease_in_out_sine(t):
    t = clamp(t)
    return -(math.cos(math.pi * t) - 1) / 2


def ease_out_back(t, s=1.4):
    t = clamp(t)
    c3 = s + 1
    return 1 + c3 * (t - 1) ** 3 + s * (t - 1) ** 2


def smoothstep(a, b, x):
    t = clamp((x - a) / (b - a)) if b != a else float(x >= b)
    return t * t * (3 - 2 * t)


def spring(t, freq=4.5, damp=5.5):
    """Critically-ish damped spring settling from 0 to 1 (overshoots slightly)."""
    if t <= 0:
        return 0.0
    return 1 - math.exp(-damp * t) * math.cos(freq * 2 * math.pi * t * 0.25)


class Track:
    """Keyframe track: [(time, value, easing_into_this_key), ...] with scalar or tuple values."""

    def __init__(self, keys):
        self.keys = sorted(keys, key=lambda k: k[0])

    def __call__(self, t):
        ks = self.keys
        if t <= ks[0][0]:
            return ks[0][1]
        if t >= ks[-1][0]:
            return ks[-1][1]
        for i in range(1, len(ks)):
            if t <= ks[i][0]:
                t0, v0 = ks[i - 1][0], ks[i - 1][1]
                t1, v1 = ks[i][0], ks[i][1]
                ease = ks[i][2] if len(ks[i]) > 2 else ease_in_out_cubic
                u = ease((t - t0) / (t1 - t0))
                if isinstance(v0, tuple):
                    return tuple(lerp(a, b, u) for a, b in zip(v0, v1))
                return lerp(v0, v1, u)
        return ks[-1][1]


def hash01(*args):
    """Deterministic pseudo-random in [0,1) from integers/floats."""
    h = 0
    for a in args:
        h = (h * 1000003) ^ int(a * 7919 + 0.5) if isinstance(a, float) else (h * 1000003) ^ int(a)
        h &= 0xFFFFFFFF
    h ^= h >> 16
    h = (h * 0x45D9F3B) & 0xFFFFFFFF
    h ^= h >> 16
    return (h & 0xFFFFFF) / float(0x1000000)


def noise1(x, seed=0):
    """Smooth 1D value noise in [-1, 1]."""
    i = math.floor(x)
    f = x - i
    a = hash01(i, seed) * 2 - 1
    b = hash01(i + 1, seed) * 2 - 1
    u = f * f * (3 - 2 * f)
    return a + (b - a) * u


def hex2rgb(h, a=1.0):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, a)


# Palette ("archive noir")
PAL = {
    "ink": hex2rgb("#07090D"),
    "ink2": hex2rgb("#0E1218"),
    "char": hex2rgb("#161A21"),
    "paper": hex2rgb("#EAE2D0"),
    "paper_dk": hex2rgb("#CDBF A4".replace(" ", "")),
    "cream": hex2rgb("#F3ECDD"),
    "muted": hex2rgb("#8E8B84"),
    "dim": hex2rgb("#55565A"),
    "red": hex2rgb("#D23A2E"),
    "red_dk": hex2rgb("#7E1E18"),
    "amber": hex2rgb("#E9A64E"),
    "amber_lt": hex2rgb("#FFD59A"),
    "teal": hex2rgb("#6FA3A8"),
    "night": hex2rgb("#142230"),
    "steel": hex2rgb("#9AA6AE"),
}
