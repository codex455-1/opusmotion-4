"""Master timeline: narration placement, absolute word times and caption groups."""
import json
import pathlib
from engine.core import FPS

ROOT = pathlib.Path(__file__).resolve().parents[1]
_MAN = json.loads((ROOT / "audio/vo/vo_manifest.json").read_text())
_WORDS = json.loads((ROOT / "audio/vo/words.json").read_text())

# Pause *before* each line (seconds). Tuned for breathing room at story turns.
GAPS = {
    "L01": 0.95,   # opening dateline types first
    "L02": 0.25,
    "L03": 0.45,
    "L04": 0.30,
    "L05": 0.30,
    "L06": 0.25,
    "L07": 0.30,
    "L08": 0.55,
    "L09": 0.35,
    "L10": 0.40,
    "L11": 0.35,
    "L12": 0.40,
}
TAIL = 5.2  # end card after the last line

LINE_START, LINE_END = {}, {}
_t = 0.0
for lid in sorted(_MAN):
    _t += GAPS[lid]
    LINE_START[lid] = _t
    LINE_END[lid] = _t + _MAN[lid]["dur"]
    _t = LINE_END[lid]
DURATION = round((_t + TAIL) * FPS) / FPS
NFRAMES = int(round(DURATION * FPS))


def words(lid):
    """Absolute-time words for a line."""
    s0 = LINE_START[lid]
    return [dict(w=w["w"], s=w["s"] + s0, e=w["e"] + s0) for w in _WORDS[lid]]


def word_time(lid, idx_or_text, which="s"):
    ws = words(lid)
    if isinstance(idx_or_text, int):
        return ws[idx_or_text][which]
    key = idx_or_text.lower()
    for w in ws:
        if w["w"].lower().strip(",.?!") .startswith(key):
            return w[which]
    raise KeyError(f"{idx_or_text} not in {lid}")


# Caption groups: (line, first_word, last_word_exclusive, rows) where rows are
# [(style, n_words)] consuming the group's words in order. styles: lead | key | keyx (emphasis)
# Per-word emphasis is marked with a list of word indices (relative to the line) in EMPH.
CAPTIONS = [
    ("L01", 0, 10, [("lead", 7), ("key", 3)]),           # In 1992, an old man walked into / a British embassy
    ("L01", 10, 16, [("lead", 5), ("key", 1)]),          # with a scruffy bag of / sausages.
    ("L02", 0, 9, [("lead", 4), ("key", 5)]),            # Under the meat, were / the secrets of the KGB.
    ("L03", 0, 5, [("key", 2), ("lead", 3)]),            # Vasili Mitrokhin. / A KGB archivist.
    ("L04", 0, 13, [("lead", 8), ("key", 5)]),           # In 1972, he was put in charge of / moving the KGB's spy archive,
    ("L04", 13, 19, [("lead", 4), ("key", 2)]),          # to a new headquarters / outside Moscow.
    ("L05", 0, 6, [("lead", 2), ("key", 4)]),            # Every day, / he read the files.
    ("L05", 6, 16, [("lead", 6), ("key", 4)]),           # And copied tiny notes by hand / hidden in his shoes.
    ("L06", 0, 13, [("lead", 7), ("key", 3), ("key", 3)]),  # At his country house, he buried them / in milk churns, / under the floor.
    ("L07", 0, 5, [("key", 2), ("key", 3)]),             # Twelve years. / Nobody caught him.
    ("L08", 0, 10, [("lead", 5), ("key", 5)]),           # When the Soviet Union fell, / he tried the Americans first.
    ("L08", 10, 15, [("lead", 4), ("key", 1)]),          # They didn't take him / seriously.
    ("L09", 0, 8, [("lead", 4), ("key", 4)]),            # The British gave him / a cup of tea.
    ("L10", 0, 10, [("lead", 4), ("key", 6)]),           # Then MI6 smuggled him / and his family out of Russia.
    ("L10", 10, 13, [("key", 3)]),                       # The notes followed.
    ("L11", 0, 5, [("lead", 2), ("key", 3)]),            # Inside were / hundreds of names.
    ("L11", 5, 14, [("lead", 5), ("key", 4)]),           # One of them lived in / a quiet London suburb.
    ("L12", 0, 7, [("key", 2), ("lead", 5)]),            # Melita Norwood. / A grandmother, unmasked at eighty-seven
    ("L12", 7, 16, [("lead", 4), ("key", 5)]),           # who had passed Britain's / atomic bomb secrets to Moscow.
]

# Display substitutions for caption text
DISPLAY = {"eighty-seven": "87"}

# words rendered in the serif-italic emphasis face: {line: {word_index: colour_key}}
EMPH = {
    "L01": {15: ("amber", True)},     # sausages
    "L02": {8: ("red", False)},       # KGB
    "L05": {15: ("amber", True)},     # shoes
    "L06": {9: ("amber", True)},      # churns
    "L08": {14: ("red", True)},       # seriously
    "L09": {7: ("amber", True)},      # tea
    "L11": {13: ("teal", True)},      # suburb
    "L12": {13: ("red", True)},       # secrets
}
