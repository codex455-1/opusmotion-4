"""Keyboard library from real recordings.

Source: "Keyboard Soundpack #1" by unicaegames (OpenGameArt, CC0), Cherry KC 1000 keyboard recorded with a
Shure SM7B: https://opengameart.org/content/keyboard-soundpack-1-typing-and-single-keystrokes
Download the zip and unzip it to /tmp/keys/pack, then run this script; it writes audio/keys/*.wav + index.json.

Processing: trim to the transient, gentle clean-up EQ (rumble cut, slightly softened top end), a touch of the film's
small-room reverb for cohesion, 48 kHz stereo. Spacebar/enter are derived from the fullest presses by pitching down.
"""
import json, pathlib, sys
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audio import sfxlib as X  # noqa: E402

SRC = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/keys/pack/Single Keys")
OUT = ROOT / "audio/keys"
OUT.mkdir(parents=True, exist_ok=True)
SR = 48000
ROOM = X.ir_preset("cabin")


def load(n):
    x, sr = sf.read(SRC / f"keypress-{n:03d}.wav", dtype="float64", always_2d=True)
    x = resample_poly(x.mean(1), 160, 147)  # 44.1k -> 48k
    return x


def prep(x, pitch=1.0, lp_hz=9000.0, length=0.20):
    pk = np.abs(x).max()
    on = max(0, int(np.argmax(np.abs(x) > pk * 0.08)) - int(0.0015 * SR))
    x = x[on:]
    if pitch != 1.0:  # pitch/speed down by resampling (deeper, slightly longer)
        up = int(round(pitch * 100))
        x = resample_poly(x, 100, up)
    x = x[: int(length * SR / min(pitch, 1.0))]
    x = X.hp(x, 90, order=2)
    x = X.biquad(x, "highshelf", 6500, gain_db=-3.0)
    x = X.lp(x, lp_hz, order=2)
    x = X.fade(x, 0.0008, 0.04)
    st = X.reverb(np.stack([x, x], 1), ROOM, wet=0.10, tail=0.08, send_hp=200)
    return st


def centroid(x):
    S = np.abs(np.fft.rfft(x))
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return float((S * f).sum() / S.sum())


raw = {n: load(n) for n in range(1, 33) if n != 20}  # 020 is truncated at the start
peak_db = {n: 20 * np.log10(np.abs(x).max()) for n, x in raw.items()}
cen = {n: centroid(x) for n, x in raw.items()}
index = {}


def emit(name, x, gain_hint, desc):
    x = x / np.abs(x).max() * 10 ** (-3 / 20)
    sf.write(OUT / f"{name}.wav", x.astype(np.float32), SR, subtype="FLOAT")
    index[name] = dict(name=name, file=f"{name}.wav", kind="oneshot", duration=round(len(x) / SR, 3),
                       peak_time=0.0, gain_hint_db=round(gain_hint, 2), loop=False, description=desc)


# regular keys: all presses within a sensible velocity range; keep half of the natural level spread
med = np.median(list(peak_db.values()))
keys = sorted(n for n in raw if -14 <= peak_db[n] <= -2)
for i, n in enumerate(keys):
    emit(f"key_{i + 1:02d}", prep(raw[n]), np.clip((peak_db[n] - med) * 0.5, -3, 3),
         f"recorded keypress (source #{n:03d})")
# spacebar: three fullest, darkest presses pitched down ~12% and slightly duller
loud_dark = sorted((n for n in raw if peak_db[n] > -8), key=lambda n: cen[n])
for i, n in enumerate(loud_dark[:3]):
    emit(f"key_space_{i + 1:02d}", prep(raw[n], pitch=1.13, lp_hz=6500, length=0.24), -1.0,
         f"spacebar, derived from source #{n:03d}")
for i, n in enumerate(loud_dark[3:5]):
    emit(f"key_enter_{i + 1:02d}", prep(raw[n], pitch=1.07, lp_hz=7500, length=0.24), 0.0,
         f"enter key, derived from source #{n:03d}")
(OUT / "index.json").write_text(json.dumps(dict(source="OpenGameArt 'Keyboard Soundpack #1' by unicaegames (CC0)",
                                                sounds=index), indent=1))
print(len(index), "key sounds;", "regular:", len(keys))
