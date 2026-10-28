"""Word-synced kinetic captions (two-tier: light italic lead + large key line, serif emphasis)."""
import skia
from engine import text as T
from engine.core import W, PAL, clamp, ease_out_cubic, ease_out_expo, ease_in_cubic, lerp, mix
from engine.gfx import paint, layer
from . import timeline as TL

STYLE = {
    "lead": dict(font="sans_light_it", size=46, color=PAL["muted"], track=0.0, gap=16),
    "key": dict(font="sans_semi", size=82, color=PAL["cream"], track=-0.022, gap=6),
}
EMPH_FONT = "serif_it"
EMPH_SCALE = 1.22
MAX_W = 930
CAP_Y = 360          # vertical centre of caption block (default)


def _emph_color(k):
    return {"amber": PAL["amber_lt"], "red": PAL["red"], "teal": PAL["teal"]}.get(k, PAL["cream"])


class Group:
    def __init__(self, lid, a, b, rows):
        self.lid = lid
        ws = TL.words(lid)
        for w in ws:
            w["w"] = TL.DISPLAY.get(w["w"].strip(",.").lower(), w["w"])
        self.words = ws[a:b]
        self.idx = list(range(a, b))
        self.rows = []
        k = 0
        for style, n in rows:
            self.rows.append((style, list(range(k, k + n))))
            k += n
        assert k == len(self.words), (lid, a, b, k, len(self.words))
        self.t_in = self.words[0]["s"] - 0.10
        self.t_last = self.words[-1]["e"]
        self.layout = None

    def text(self):
        return " / ".join(" ".join(self.words[i]["w"] for i in r) for _, r in self.rows)

    def _layout(self):
        if self.layout is not None:
            return self.layout
        emph = TL.EMPH.get(self.lid, {})
        lines = []  # list of (style, [(word_i, font, size, color, x, width)], height)
        for style, ids in self.rows:
            st = STYLE[style]
            size = st["size"]
            # fit: shrink key rows, wrap if still too wide
            def measure(ids_, size_):
                items, x = [], 0.0
                sp = T.text_width(st["font"], " ", size_) * (0.9 if style == "key" else 1.0)
                for i in ids_:
                    li = self.idx[i]
                    is_e = li in emph and style != "lead"
                    serif = is_e and emph[li][1]
                    f = EMPH_FONT if serif else st["font"]
                    sz = size_ * (EMPH_SCALE if serif else 1.0)
                    tr = 0.0 if serif else st["track"]
                    wd = T.text_width(f, self.words[i]["w"], sz, tr)
                    col = _emph_color(emph[li][0]) if is_e else st["color"]
                    items.append([i, f, sz, col, x, wd, tr, is_e])
                    x += wd + sp
                return items, x - sp
            items, wsum = measure(ids, size)
            if wsum > MAX_W and style == "key":
                size2 = max(size * MAX_W / wsum, 66)
                items, wsum = measure(ids, size2)
                if wsum > MAX_W:
                    # wrap into two balanced rows
                    best = None
                    for cut in range(1, len(ids)):
                        a_, wa = measure(ids[:cut], size)
                        b_, wb = measure(ids[cut:], size)
                        sc = max(wa, wb)
                        if best is None or sc < best[0]:
                            best = (sc, cut)
                    cut = best[1]
                    for part in (ids[:cut], ids[cut:]):
                        it, ws_ = measure(part, size)
                        lines.append((style, it, ws_, size))
                    continue
                size = size2
            elif wsum > MAX_W:
                size2 = size * MAX_W / wsum
                items, wsum = measure(ids, size2)
                size = size2
            lines.append((style, items, wsum, size))
        # vertical stacking
        heights = []
        for style, items, wsum, size in lines:
            heights.append(size * (1.06 if style == "key" else 1.25))
        total = sum(heights)
        self.layout = (lines, heights, total)
        return self.layout

    def draw(self, canvas, t, t_out, cy=CAP_Y, alpha=1.0):
        lines, heights, total = self._layout()
        out_p = clamp((t - t_out) / 0.28)
        if out_p >= 1:
            return
        y = cy - total / 2
        for (style, items, wsum, size), hgt in zip(lines, heights):
            base = y + hgt * 0.80
            x0 = W / 2 - wsum / 2
            for (i, f, sz, col, x, wd, tr, is_e) in items:
                w = self.words[i]
                p = clamp((t - (w["s"] - 0.07)) / 0.34)
                if p <= 0:
                    continue
                e = ease_out_expo(p)
                a = ease_out_cubic(p) * alpha * (1 - ease_in_cubic(out_p))
                settle = clamp((t - w["s"]) / 0.55)
                c = mix(PAL["dim"] if style == "key" else PAL["dim"], col, ease_out_cubic(settle))
                dy = (1 - e) * 22 - ease_in_cubic(out_p) * 26
                blur = (1 - e) * 9 + ease_in_cubic(out_p) * 8
                sc = 0.94 + 0.06 * e
                s = T.shape(f, w["w"], sz, tr)
                cx = x0 + x + wd / 2
                canvas.save()
                canvas.translate(cx, base + dy)
                canvas.scale(sc, sc)
                blob = s.blob(0, None, -wd / 2, 0)
                if blob is not None:
                    # soft dark backing for legibility over imagery
                    canvas.drawTextBlob(blob, 0, 3, paint((0, 0, 0, 1), a=0.55 * a, blur=14 + blur))
                    if is_e:
                        canvas.drawTextBlob(blob, 0, 0, paint(c, a=0.35 * a, blur=10 + blur))
                    canvas.drawTextBlob(blob, 0, 0, paint(c, a=a, blur=blur * 0.6))
                canvas.restore()
            y += hgt


GROUPS = [Group(*g) for g in TL.CAPTIONS]

# per-group vertical position overrides (scene composition needs)
CAP_POS = {}


def draw_captions(canvas, t):
    for gi, g in enumerate(GROUPS):
        nxt = GROUPS[gi + 1].t_in if gi + 1 < len(GROUPS) else 1e9
        # hold until the next group starts (if same/adjacent line) or 0.45 s after the last word
        t_out = min(nxt - 0.12, g.t_last + 0.75) if nxt - g.t_last < 1.6 else g.t_last + 0.75
        if t < g.t_in - 0.05 or t > t_out + 0.3:
            continue
        g.draw(canvas, t, t_out, cy=CAP_POS.get(gi, CAP_Y))


def caption_events():
    """(time, kind) for sound design: one soft 'cream' tick per caption row, emphasis thumps."""
    ev = []
    for g in GROUPS:
        lines, _, _ = g._layout()
        for style, items, _, _ in lines:
            first = items[0][0]
            ev.append((g.words[first]["s"] - 0.06, "row_" + style))
            for it in items:
                if it[7]:
                    ev.append((g.words[it[0]]["s"] - 0.05, "emph"))
    return sorted(ev)
