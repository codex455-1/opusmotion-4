"""Skia drawing helpers: paints, gradients, soft layers, procedural textures."""
import contextlib
import functools
import numpy as np
import skia
from .core import W, H


def c4(rgba, a=None):
    r, g, b = rgba[0], rgba[1], rgba[2]
    al = rgba[3] if len(rgba) > 3 else 1.0
    if a is not None:
        al = al * a
    return skia.Color4f(r, g, b, max(0.0, min(1.0, al)))


def cint(rgba, a=None):
    return c4(rgba, a).toColor()


def paint(color=(1, 1, 1, 1), a=None, stroke=None, cap="round", join="round", blur=0.0,
          shader=None, blend=None, aa=True, image_filter=None):
    p = skia.Paint(AntiAlias=aa)
    p.setColor4f(c4(color, a))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeCap({"round": skia.Paint.kRound_Cap, "butt": skia.Paint.kButt_Cap,
                        "square": skia.Paint.kSquare_Cap}[cap])
        p.setStrokeJoin({"round": skia.Paint.kRound_Join, "miter": skia.Paint.kMiter_Join,
                         "bevel": skia.Paint.kBevel_Join}[join])
    if blur > 0.05:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if shader is not None:
        p.setShader(shader)
    if blend is not None:
        p.setBlendMode(blend)
    if image_filter is not None:
        p.setImageFilter(image_filter)
    return p


def lin(p0, p1, colors, pos=None, alpha=1.0):
    return skia.GradientShader.MakeLinear([skia.Point(*p0), skia.Point(*p1)],
                                          [cint(c, alpha) for c in colors], pos)


def rad(c, r, colors, pos=None, alpha=1.0, matrix=None):
    if matrix is not None:
        return skia.GradientShader.MakeRadial(skia.Point(*c), max(r, 0.01), [cint(x, alpha) for x in colors],
                                              pos, skia.TileMode.kClamp, 0, matrix)
    return skia.GradientShader.MakeRadial(skia.Point(*c), max(r, 0.01), [cint(x, alpha) for x in colors], pos)


@contextlib.contextmanager
def layer(canvas, alpha=1.0, blur=0.0, bounds=None, blend=None, color_filter=None):
    """Offscreen layer with opacity / gaussian blur applied on restore."""
    if alpha >= 0.999 and blur < 0.05 and blend is None and color_filter is None:
        canvas.save()
        try:
            yield
        finally:
            canvas.restore()
        return
    p = skia.Paint()
    p.setAlphaf(max(0.0, min(1.0, alpha)))
    if blur >= 0.05:
        p.setImageFilter(skia.ImageFilters.Blur(blur, blur, skia.TileMode.kDecal))
    if blend is not None:
        p.setBlendMode(blend)
    if color_filter is not None:
        p.setColorFilter(color_filter)
    canvas.saveLayer(skia.Rect(*bounds) if bounds else None, p)
    try:
        yield
    finally:
        canvas.restore()


@contextlib.contextmanager
def xform(canvas, tx=0.0, ty=0.0, s=1.0, rot=0.0, cx=0.0, cy=0.0, sx=None, sy=None):
    canvas.save()
    canvas.translate(tx + cx, ty + cy)
    if rot:
        canvas.rotate(rot)
    if s != 1.0 or sx is not None or sy is not None:
        canvas.scale(sx if sx is not None else s, sy if sy is not None else s)
    canvas.translate(-cx, -cy)
    try:
        yield
    finally:
        canvas.restore()


def rrect(x, y, w, h, r):
    return skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r)


def path_from_points(pts, closed=False):
    p = skia.Path()
    if len(pts) == 0:
        return p
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    if closed:
        p.close()
    return p


def trim_path(path, t0, t1):
    """Return the sub-path between fractions t0..t1 of total length."""
    meas = skia.PathMeasure(path, False)
    out = skia.Path()
    total = 0.0
    lens = []
    while True:
        L = meas.getLength()
        lens.append(L)
        total += L
        if not meas.nextContour():
            break
    if total <= 0:
        return out
    a, b = t0 * total, t1 * total
    meas = skia.PathMeasure(path, False)
    acc = 0.0
    for L in lens:
        s, e = max(a - acc, 0.0), min(b - acc, L)
        if e > s:
            meas.getSegment(s, e, out, True)
        acc += L
        meas.nextContour()
    return out


def path_point(path, t):
    """Position and tangent at fraction t along the first contour."""
    meas = skia.PathMeasure(path, False)
    L = meas.getLength()
    res = meas.getPosTan(max(0.0, min(1.0, t)) * L)
    if not res:
        return (0.0, 0.0), (1.0, 0.0)
    pos, tan = res
    return (pos.x(), pos.y()), (tan.x(), tan.y())


# --- numpy <-> skia -----------------------------------------------------------
def np_to_image(arr):
    """arr: HxWx4 uint8 premultiplied RGBA or float32 [0,1] (premultiplied)."""
    if arr.dtype != np.uint8:
        arr = (np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)
    arr = np.ascontiguousarray(arr)
    return skia.Image.fromarray(arr, colorType=skia.ColorType.kRGBA_8888_ColorType,
                                alphaType=skia.AlphaType.kPremul_AlphaType)


def surface(w=W, h=H):
    info = skia.ImageInfo.Make(w, h, skia.ColorType.kRGBA_F16_ColorType, skia.AlphaType.kPremul_AlphaType)
    return skia.Surface.MakeRaster(info)


def surface8(w=W, h=H):
    return skia.Surface(w, h)


def snapshot_f32(surf):
    img = surf.makeImageSnapshot()
    arr = img.toarray(colorType=skia.ColorType.kRGBA_F32_ColorType)
    return arr


# --- procedural textures ----------------------------------------------------
def _value_noise(shape, scale, rng):
    h, w = shape
    gh, gw = int(h / scale) + 3, int(w / scale) + 3
    g = rng.random((gh, gw)).astype(np.float32)
    ys = np.arange(h, dtype=np.float32) / scale
    xs = np.arange(w, dtype=np.float32) / scale
    y0 = ys.astype(int)
    x0 = xs.astype(int)
    fy = ys - y0
    fx = xs - x0
    fy = fy * fy * (3 - 2 * fy)
    fx = fx * fx * (3 - 2 * fx)
    a = g[y0][:, x0]
    b = g[y0][:, x0 + 1]
    c = g[y0 + 1][:, x0]
    d = g[y0 + 1][:, x0 + 1]
    top = a + (b - a) * fx[None, :]
    bot = c + (d - c) * fx[None, :]
    return top + (bot - top) * fy[:, None]


def fbm(shape, base=64.0, octaves=5, seed=0, gain=0.5):
    rng = np.random.default_rng(seed)
    out = np.zeros(shape, np.float32)
    amp, tot, sc = 1.0, 0.0, base
    for _ in range(octaves):
        out += amp * _value_noise(shape, max(sc, 1.0), rng)
        tot += amp
        amp *= gain
        sc /= 2
    return out / tot


@functools.lru_cache(maxsize=16)
def paper_image(w, h, seed=1, tint=(0.918, 0.886, 0.816), grain=0.06, fibers=True, stain=0.10):
    """Warm paper with fibres, mottling and faint stains. Returned as an opaque skia.Image."""
    rng = np.random.default_rng(seed)
    mott = fbm((h, w), base=180, octaves=5, seed=seed)
    fine = fbm((h, w), base=6, octaves=2, seed=seed + 7)
    v = 1.0 + (mott - 0.5) * stain + (fine - 0.5) * grain
    if fibers:
        n = int(w * h / 900)
        fib = np.zeros((h, w), np.float32)
        ys = rng.integers(0, h, n)
        xs = rng.integers(0, w, n)
        ln = rng.integers(3, 14, n)
        ang = rng.random(n) * np.pi
        for k in range(n):
            for s in range(ln[k]):
                yy = int(ys[k] + np.sin(ang[k]) * s)
                xx = int(xs[k] + np.cos(ang[k]) * s)
                if 0 <= yy < h and 0 <= xx < w:
                    fib[yy, xx] += 1
        v -= np.clip(fib, 0, 1) * 0.035
    rgb = np.stack([v * tint[0], v * tint[1], v * tint[2]], -1)
    # darker, slightly warmer edges
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ex = np.minimum(xx, w - 1 - xx) / (0.08 * w)
    ey = np.minimum(yy, h - 1 - yy) / (0.08 * h)
    edge = np.clip(np.minimum(ex, ey), 0, 1) ** 0.6
    rgb *= (0.86 + 0.14 * edge)[..., None]
    rgb[..., 2] *= (0.95 + 0.05 * edge)
    a = np.ones((h, w, 1), np.float32)
    return np_to_image(np.concatenate([np.clip(rgb, 0, 1), a], -1))


@functools.lru_cache(maxsize=8)
def noise_image(w, h, seed=3, base=40.0, octaves=4, lo=0.0, hi=1.0):
    n = fbm((h, w), base=base, octaves=octaves, seed=seed)
    n = lo + (hi - lo) * n
    arr = np.stack([n, n, n, np.ones_like(n)], -1)
    return np_to_image(arr)


def draw_image_rect(canvas, img, x, y, w, h, alpha=1.0, blend=None, sampling=None):
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(alpha)
    if blend is not None:
        p.setBlendMode(blend)
    canvas.drawImageRect(img, skia.Rect.MakeXYWH(x, y, w, h),
                         sampling or skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear), p)
