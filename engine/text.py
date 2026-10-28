"""Typography: HarfBuzz shaping + Skia glyph runs, with per-glyph access for animation."""
import functools
import pathlib
import skia
import uharfbuzz as hb
from .gfx import xpath

FONT_DIR = pathlib.Path(__file__).resolve().parents[1] / "assets" / "fonts"
FONTS = {
    "sans": "Inter-Regular.ttf",
    "sans_light": "Inter-Light.ttf",
    "sans_med": "Inter-Medium.ttf",
    "sans_semi": "Inter-SemiBold.ttf",
    "sans_bold": "Inter-Bold.ttf",
    "sans_it": "Inter-Italic.ttf",
    "sans_light_it": "Inter-LightItalic.ttf",
    "serif": "InstrumentSerif-Regular.ttf",
    "serif_it": "InstrumentSerif-Italic.ttf",
    "news": "Newsreader-Display.ttf",
    "news_text": "Newsreader-Text.ttf",
    "mono": "IBMPlexMono-Regular.ttf",
    "mono_med": "IBMPlexMono-Medium.ttf",
    "mono_semi": "IBMPlexMono-SemiBold.ttf",
    "typewriter": "PTM55FT.ttf",
    "hand": "BadScript-Regular.ttf",
    "hand2": "Caveat-Medium.ttf",
    "cond": "Oswald-Medium.ttf",
}


@functools.lru_cache(maxsize=None)
def typeface(name):
    return skia.Typeface.MakeFromFile(str(FONT_DIR / FONTS[name]))


@functools.lru_cache(maxsize=None)
def _hb_font(name):
    blob = hb.Blob.from_file_path(str(FONT_DIR / FONTS[name]))
    face = hb.Face(blob)
    font = hb.Font(face)
    return font, face.upem


@functools.lru_cache(maxsize=None)
def skfont(name, size):
    f = skia.Font(typeface(name), size)
    f.setSubpixel(True)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    f.setHinting(skia.FontHinting.kNone)
    f.setLinearMetrics(True)
    return f


class Shaped:
    """A shaped line: glyph ids, x offsets (px), char cluster per glyph, total advance."""

    __slots__ = ("name", "size", "text", "gids", "xs", "ys", "clusters", "width", "adv")

    def __init__(self, name, size, text, gids, xs, ys, clusters, width, adv):
        self.name, self.size, self.text = name, size, text
        self.gids, self.xs, self.ys, self.clusters, self.width, self.adv = gids, xs, ys, clusters, width, adv

    @property
    def font(self):
        return skfont(self.name, self.size)

    def blob(self, start=0, end=None, dx=0.0, dy=0.0):
        end = len(self.gids) if end is None else end
        if end <= start:
            return None
        b = skia.TextBlobBuilder()
        pts = [skia.Point(self.xs[i] + dx, self.ys[i] + dy) for i in range(start, end)]
        b.allocRunPos(self.font, self.gids[start:end], pts)
        return b.make()

    def glyph_blob(self, i, dx=0.0, dy=0.0):
        return self.blob(i, i + 1, dx, dy)

    def glyph_path(self, i):
        p = self.font.getPath(self.gids[i])
        if p is None:
            return skia.Path()
        return xpath(p, skia.Matrix.Translate(self.xs[i], self.ys[i]))


@functools.lru_cache(maxsize=4096)
def shape(name, text, size, tracking=0.0, features=("kern", "liga")):
    """Shape `text` with HarfBuzz. tracking is in em units (e.g. 0.12 = 12% em)."""
    font, upem = _hb_font(name)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    feats = {f: True for f in features}
    hb.shape(font, buf, feats)
    scale = size / upem
    x = 0.0
    gids, xs, ys, cl, adv = [], [], [], [], []
    track = tracking * size
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        gids.append(info.codepoint)
        xs.append(x + pos.x_offset * scale)
        ys.append(-pos.y_offset * scale)
        cl.append(info.cluster)
        a = pos.x_advance * scale + track
        adv.append(a)
        x += a
    width = x - (track if gids else 0.0)
    return Shaped(name, size, text, gids, xs, ys, cl, width, adv)


def text_width(name, text, size, tracking=0.0):
    return shape(name, text, size, tracking).width


def metrics(name, size):
    m = skfont(name, size).getMetrics()
    return m.fAscent, m.fDescent, m.fCapHeight, m.fXHeight


def draw(canvas, name, text, size, x, y, paint, tracking=0.0, align="left", n=None):
    """Draw a single line. align: left|center|right. n limits visible glyphs (typing)."""
    s = shape(name, text, size, tracking)
    if align == "center":
        x -= s.width / 2
    elif align == "right":
        x -= s.width
    b = s.blob(0, n)
    if b is not None:
        canvas.drawTextBlob(b, x, y, paint)
    return s


def wrap(name, text, size, max_w, tracking=0.0):
    words = text.split(" ")
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if text_width(name, trial, size, tracking) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines
