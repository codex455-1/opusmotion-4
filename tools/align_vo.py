"""Word timing for the narration: Whisper word timestamps aligned to the script's display words.

Writes audio/vo/words.json: {line_id: [{"w": display_word, "s": start, "e": end}, ...]} with times
relative to the start of each line's WAV.
"""
import difflib, json, pathlib, re
import numpy as np, soundfile as sf, librosa
from faster_whisper import WhisperModel

ROOT = pathlib.Path(__file__).resolve().parents[1]
lines = json.loads((ROOT / "audio/narration.json").read_text())


def display_words(text):
    text = re.sub(r"\[([^\]]+)\]\(/[^)]*/\)", r"\1", text)  # strip phoneme markup
    text = text.replace("...", " ")
    return [w for w in text.split() if w]


def norm(w):
    w = w.lower().replace("’", "'")
    w = re.sub(r"[^a-z0-9']", "", w)
    return {"mi6": "mi6", "eightyseven": "87", "1992": "1992", "1972": "1972"}.get(w, w)


model = WhisperModel("small.en", device="cpu", compute_type="int8", cpu_threads=2)
out = {}
for ln in lines:
    a, sr = sf.read(ROOT / f"audio/vo/{ln['id']}.wav")
    y = librosa.resample(a.astype(np.float32), orig_sr=sr, target_sr=16000)
    segs, _ = model.transcribe(y, word_timestamps=True, beam_size=5,
                               initial_prompt="Vasili Mitrokhin, KGB, MI6, Melita Norwood.")
    ww = [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]
    disp = display_words(ln["text"])
    a_tok = [norm(w) for w in disp]
    b_tok = [norm(w[0]).replace("-", "") for w in ww]
    times = [None] * len(disp)
    sm = difflib.SequenceMatcher(a=a_tok, b=b_tok, autojunk=False)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            times[blk.a + k] = (ww[blk.b + k][1], ww[blk.b + k][2])
    # fill unmatched words by interpolation between known neighbours
    known = [i for i, t in enumerate(times) if t]
    dur = len(a) / sr
    for i in range(len(disp)):
        if times[i]:
            continue
        prev = max([k for k in known if k < i], default=None)
        nxt = min([k for k in known if k > i], default=None)
        s0 = times[prev][1] if prev is not None else 0.0
        s1 = times[nxt][0] if nxt is not None else dur
        span = [j for j in range(len(disp)) if (prev is None or j > prev) and (nxt is None or j < nxt)]
        k = span.index(i)
        st = s0 + (s1 - s0) * k / len(span)
        times[i] = (st, st + (s1 - s0) / len(span))
    out[ln["id"]] = [{"w": w, "s": round(t[0], 3), "e": round(t[1], 3)} for w, t in zip(disp, times)]
    print(ln["id"], " | ".join(f"{w}@{t[0]:.2f}" for w, t in zip(disp, times)))
(ROOT / "audio/vo/words.json").write_text(json.dumps(out, indent=1))
