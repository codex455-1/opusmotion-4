"""Perspective map rendering: a baked map texture viewed through a 3D camera (homography)."""
import functools
import json
import math
import pathlib
import numpy as np
import skia
from engine.core import W, H
from engine.gl import perspective, look_at

CACHE = pathlib.Path(__file__).resolve().parents[1] / "build/cache"


@functools.lru_cache(maxsize=None)
def load(name):
    img = skia.Image.open(str(CACHE / f"{name}.png")).withDefaultMipmaps()
    meta = json.loads((CACHE / f"{name}.json").read_text())
    return img, meta


class MapCam:
    """target (u,v) in map px; view_h = map px spanned vertically at the target (pitch 0); pitch/yaw deg."""

    def __init__(self, target, view_h, pitch=0.0, yaw=0.0, fov=32.0, screen_offset=(0.0, 0.0)):
        self.target, self.view_h, self.pitch, self.yaw, self.fov = target, view_h, pitch, yaw, fov
        self.off = screen_offset
        d = view_h / (2 * math.tan(math.radians(fov) / 2))
        th, ph = math.radians(pitch), math.radians(yaw)
        T = np.array([target[0], -target[1], 0.0])
        eye = T + d * np.array([math.sin(th) * math.sin(ph), -math.sin(th) * math.cos(ph), math.cos(th)])
        # screen-up is the camera's horizontal forward direction (valid for pitch 0 too)
        up = np.array([-math.sin(ph), math.cos(ph), 0.0])
        V = look_at(eye, T, up)
        P = perspective(fov, W / H, d * 0.05, d * 20)
        M = P @ V
        M3 = M[[0, 1, 3]][:, [0, 1, 3]].astype(np.float64)
        M3[:, 1] *= -1  # world Y = -v
        S = np.array([[W / 2, 0, W / 2 + self.off[0]], [0, -H / 2, H / 2 + self.off[1]], [0, 0, 1]], np.float64)
        self.Hm = S @ M3
        self.dist = d
        self.eye = eye

    def matrix(self):
        h = self.Hm / self.Hm[2, 2]
        m = skia.Matrix()
        m.setAll(*[float(x) for x in h.flatten()])
        return m

    def project(self, pts):
        p = np.asarray(pts, np.float64).reshape(-1, 2)
        ph = np.concatenate([p, np.ones((len(p), 1))], 1) @ self.Hm.T
        w = ph[:, 2:3]
        return ph[:, :2] / w, w[:, 0]

    def scale_at(self, uv):
        """Screen pixels per map pixel at a map location (for sizing markers)."""
        a, _ = self.project([uv, (uv[0] + 10, uv[1])])
        return float(np.linalg.norm(a[1] - a[0]) / 10)


def draw_map(c, name, cam, alpha=1.0, fog=(0.02, 0.025, 0.03), fog_amt=0.85):
    img, meta = load(name)
    c.save()
    c.concat(cam.matrix())
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(alpha)
    c.drawImage(img, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear), p)
    c.restore()
    if cam.pitch > 5 and fog_amt > 0:
        # atmospheric depth: the far edge of the tilted map dissolves into haze
        horizon = cam.project([(cam.target[0] + math.sin(math.radians(cam.yaw)) * cam.view_h * 3,
                                cam.target[1] - math.cos(math.radians(cam.yaw)) * cam.view_h * 3)])[0][0][1]
        top = max(-200.0, min(float(horizon), H * 0.6))
        f = skia.Paint()
        f.setShader(skia.GradientShader.MakeLinear(
            [skia.Point(0, top), skia.Point(0, top + H * 0.45)],
            [skia.Color4f(*fog, fog_amt * alpha).toColor(), skia.Color4f(*fog, 0).toColor()]))
        c.drawRect(skia.Rect.MakeLTRB(0, -10, W, top + H * 0.45), f)
        c.drawRect(skia.Rect.MakeLTRB(0, -10, W, top), skia.Paint(Color4f=skia.Color4f(*fog, fog_amt * alpha)))


def bezier(p0, p1, bend=0.18, n=120):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    nrm = np.array([-d[1], d[0]])
    ctrl = (p0 + p1) / 2 + nrm * bend
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * ctrl + t ** 2 * p1
