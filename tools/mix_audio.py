"""Final sound mix: narration + frame-locked SFX cues -> audio/mix.wav (48 kHz stereo, -14 LUFS, -1 dBTP).

Cues come from the scene modules themselves (scenes.common.CUES) plus caption-appearance events,
so every key thock, pop and whoosh lands on the frame that triggers it.
"""
import json, pathlib, sys
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly, fftconvolve

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audio import sfxlib as X  # noqa: E402
from scenes import SCENES, timeline as TL, captions  # noqa: E402,F401  (importing scenes registers cues)
from scenes.common import CUES  # noqa: E402

SR = 48000
N = int(round((TL.DURATION + 0.2) * SR))
IDX = json.loads((ROOT / "audio/sfx/index.json").read_text())["sounds"]
_cache = {}

# category trims (dB) applied on top of each cue's gain, tuned by measuring the mix balance
TRIM = {"key": -5.0, "text": -2.0, "amb": 2.0, "impact": 0.0, "move": -1.0, "obj": -1.0}
CAT = {"key_thock": "key", "key_space": "key", "key_enter": "key", "text_pop": "text", "text_soft": "text",
       "room_archive": "amb", "room_london_night": "amb", "wind_soft": "amb", "train_loop": "amb", "boat_loop": "amb",
       "steam": "amb", "route_draw": "amb", "pen_write": "amb", "clock_tick": "amb",
       "sub_boom": "impact", "final_hit": "impact", "emph_thump": "impact",
       "whoosh_soft": "move", "whoosh_deep": "move", "riser_air": "move", "reverse_swell": "move", "light_sweep": "move"}


def resolve(name, var):
    for cand in (f"{name}_{var + 1:02d}", name, f"{name}_loop", f"{name}_01"):
        if cand in IDX:
            return cand
    raise KeyError(name)


def load(key):
    if key not in _cache:
        x, sr = sf.read(ROOT / "audio/sfx" / IDX[key]["file"], dtype="float32", always_2d=True)
        assert sr == SR
        _cache[key] = x
    return _cache[key]


def pan_st(x, p):
    gl, gr = np.cos((p + 1) * np.pi / 4), np.sin((p + 1) * np.pi / 4)
    out = x.copy()
    out[:, 0] *= gl * 1.4142
    out[:, 1] *= gr * 1.4142
    return out


def place(bus, x, t0, gain_db):
    s = int(round(t0 * SR))
    g = 10 ** (gain_db / 20)
    a, b = max(s, 0), min(s + len(x), len(bus))
    if b > a:
        bus[a:b] += x[a - s:b - s] * g


def build_sfx():
    buses = {k: np.zeros((N, 2), np.float32) for k in ("key", "text", "amb", "impact", "move", "obj")}
    cues = list(CUES)
    for t, kind in captions.caption_events():
        if kind == "emph":
            cues.append(dict(t=t, name="text_pop", gain=-15.0, pan=0.0, var=int(t * 7) % 6))
        else:
            cues.append(dict(t=t, name="text_soft", gain=-13.0 if kind == "row_key" else -16.0, pan=0.0,
                             var=int(t * 11) % 6))
    for cu in cues:
        key = resolve(cu["name"], cu.get("var", 0))
        info = IDX[key]
        x = load(key)
        cat = CAT.get(cu["name"], "obj")
        gain = cu["gain"] + info.get("gain_hint_db", 0.0) + TRIM[cat]
        if cu.get("loop") or info.get("loop"):
            dur = cu.get("dur", info["duration"])
            n = int(dur * SR)
            reps = int(np.ceil(n / len(x))) + 1
            off = int((hash(cu["name"]) % 997) / 997 * len(x))
            y = np.tile(x, (reps, 1))[off:off + n].copy()
            y = X.fade(y, cu.get("fade_in", 0.3), cu.get("fade_out", 0.5))
        else:
            y = x
        t0 = cu["t"]
        if cu.get("align") == "peak" and info.get("peak_time") is not None:
            t0 = cu["at"] - info["peak_time"]
        place(buses[cat], pan_st(y, float(cu.get("pan", 0.0))), t0, gain)
    return buses, len(cues)


def voice():
    v = np.zeros(N, np.float32)
    man = json.loads((ROOT / "audio/vo/vo_manifest.json").read_text())
    for lid in sorted(man):
        a, sr = sf.read(ROOT / f"audio/vo/{lid}.wav", dtype="float32")
        a = resample_poly(a, SR, sr).astype(np.float32)
        a = X.fade(a, 0.004, 0.02)
        s = int(round(TL.LINE_START[lid] * SR))
        v[s:s + len(a)] += a[: max(0, min(len(a), N - s))]
    # voice chain: clean low end, add body + presence, gentle de-ess, smooth compression, tiny room
    v = X.hp(v, 70, order=2)
    v = X.biquad(v, "lowshelf", 170, gain_db=1.8)
    v = X.biquad(v, "peak", 320, q=1.0, gain_db=-1.2)
    v = X.biquad(v, "peak", 3400, q=0.9, gain_db=1.6)
    v = X.biquad(v, "highshelf", 9000, gain_db=0.8)
    sib = X.bp(v, 5200, 9500, order=2)
    env_s = X.rms_envelope(sib, 0.006)[: len(v)]
    over = np.clip(20 * np.log10(env_s + 1e-9) + 32, 0, None)          # dB above de-ess threshold
    v = v - sib * (1 - 10 ** (-np.minimum(over * 0.6, 7) / 20))
    env = X.rms_envelope(v, 0.012)[: len(v)]
    lvl = 20 * np.log10(env + 1e-9)
    thr, ratio = -24.0, 2.6
    gr_db = np.where(lvl > thr, (lvl - thr) * (1 - 1 / ratio), 0.0)
    # smooth the gain (attack 8 ms / release 140 ms)
    g = np.empty_like(gr_db)
    a_at, a_rel = np.exp(-1 / (0.008 * SR)), np.exp(-1 / (0.14 * SR))
    acc = 0.0
    for i in range(0, len(gr_db), 32):
        target = gr_db[i]
        coef = a_at if target > acc else a_rel
        acc = target + (acc - target) * coef ** 32
        g[i:i + 32] = acc
    v = v * 10 ** (-g / 20)
    room = X.ir_preset("cabin")
    wet = fftconvolve(v, room[:, 0] if room.ndim == 2 else room)[: len(v)]
    v = v + wet * 0.06
    return np.stack([v, v], 1).astype(np.float32)


def limiter(x, ceiling_db=-1.2, look=0.004, release=0.08):
    """Look-ahead peak limiter using a 4x-oversampled (true-peak-ish) detector."""
    from scipy.ndimage import minimum_filter1d
    c = 10 ** (ceiling_db / 20)
    up = resample_poly(x, 4, 1, axis=0)
    pk = np.abs(up).max(1)[: len(x) * 4].reshape(-1, 4).max(1)[: len(x)]
    need = np.minimum(1.0, c / np.maximum(pk, 1e-9))
    la = int(look * SR)
    gmin = minimum_filter1d(np.pad(need, (0, la), constant_values=1.0), size=la + 1, origin=-(la // 2))[: len(x)]
    rel = np.exp(-1 / (release * SR))
    g = np.empty_like(gmin)
    acc = 1.0
    for i in range(0, len(gmin), 16):
        target = gmin[i:i + 16].min()
        acc = target if target < acc else target + (acc - target) * rel ** 16
        g[i:i + 16] = acc
    return x * g[:, None]


def main():
    vo = voice()
    buses, ncues = build_sfx()
    sfx = sum(buses.values())
    # sidechain ducking of SFX under the voice (impacts barely ducked)
    env = X.rms_envelope(vo[:, 0], 0.05)[:N]
    e = np.clip((20 * np.log10(env + 1e-9) + 42) / 18, 0, 1)
    sm = np.empty_like(e)
    acc = 0.0
    for i in range(0, len(e), 64):
        tgt = e[i]
        k = np.exp(-64 / (0.03 * SR)) if tgt > acc else np.exp(-64 / (0.45 * SR))
        acc = tgt + (acc - tgt) * k
        sm[i:i + 64] = acc
    duck = 10 ** (-5.5 * sm / 20)
    duck_imp = 10 ** (-2.0 * sm / 20)
    sfx_d = (sfx - buses["impact"]) * duck[:, None] + buses["impact"] * duck_imp[:, None]
    mix = vo + sfx_d
    import pyloudnorm as pyln
    meter = pyln.Meter(SR)
    for _ in range(3):
        L = meter.integrated_loudness(mix)
        mix = mix * 10 ** ((-14.0 - L) / 20)
        mix = limiter(mix, -1.2)
    L = meter.integrated_loudness(mix)
    Lv = meter.integrated_loudness(vo * 10 ** ((-14.0 - L) / 20))
    up = resample_poly(mix, 4, 1, axis=0)
    tp = 20 * np.log10(np.abs(up).max() + 1e-12)
    mix = X.fade(mix, 0.01, 0.6)
    sf.write(ROOT / "audio/mix.wav", mix.astype(np.float32), SR, subtype="FLOAT")
    for k, b in buses.items():
        sf.write(ROOT / f"build/stem_{k}.wav", b.astype(np.float32), SR, subtype="FLOAT")
    sf.write(ROOT / "build/stem_vo.wav", vo.astype(np.float32), SR, subtype="FLOAT")
    lv = {k: round(meter.integrated_loudness(b * 10 ** ((-14.0 - L) / 20)), 1) if np.abs(b).max() > 1e-6 else None
          for k, b in buses.items()}
    print(f"cues={ncues} integrated={L:.2f} LUFS truepeak~{tp:.2f} dBTP duration={len(mix) / SR:.2f}s")
    print("bus loudness (LUFS, pre-duck, at master gain):", lv, "voice:", round(meter.integrated_loudness(vo), 1))


if __name__ == "__main__":
    main()
