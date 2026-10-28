"""sfxlib - small numpy/scipy DSP toolkit for procedurally synthesised sound effects.

Conventions
-----------
* sample rate is 48 kHz, audio is float64 in memory, shape (n,) mono or (n, 2) stereo;
* every filter works along axis 0 so mono and stereo arrays are interchangeable;
* nothing here uses global random state: callers pass a numpy Generator.
"""
from __future__ import annotations

import numpy as np
from scipy import signal
from scipy.signal import fftconvolve

SR = 48000
LN1000 = 6.907755278982137  # ln(10**3): time constant -> T60


# --------------------------------------------------------------------------- basics
def rng(seed) -> np.random.Generator:
    return np.random.default_rng(seed)


def n_of(sec: float, sr: int = SR) -> int:
    return int(round(sec * sr))


def tvec(n: int, sr: int = SR) -> np.ndarray:
    return np.arange(n) / sr


def db(x) -> float:
    return 20.0 * np.log10(max(float(x), 1e-12))


def undb(d):
    return 10.0 ** (np.asarray(d) / 20.0)


def mono(x: np.ndarray) -> np.ndarray:
    return x if x.ndim == 1 else x.mean(axis=1)


def to_stereo(x: np.ndarray) -> np.ndarray:
    return np.stack([x, x], axis=1) if x.ndim == 1 else x


def pad_to(x: np.ndarray, n: int) -> np.ndarray:
    if len(x) >= n:
        return x[:n]
    shape = (n - len(x),) + x.shape[1:]
    return np.concatenate([x, np.zeros(shape)], axis=0)


def mix(layers, n: int | None = None, sr: int = SR) -> np.ndarray:
    """Sum (array, offset_seconds[, gain]) layers; layers may be mono or stereo."""
    items = []
    for l in layers:
        arr, off = l[0], l[1]
        g = l[2] if len(l) > 2 else 1.0
        items.append((arr, n_of(off, sr), g))
    stereo = any(a.ndim == 2 for a, _, _ in items)
    total = n if n is not None else max(o + len(a) for a, o, _ in items)
    out = np.zeros((total, 2) if stereo else total)
    for a, o, g in items:
        if o >= total:
            continue
        seg = a[: total - o]
        if stereo and seg.ndim == 1:
            seg = to_stereo(seg)
        out[o:o + len(seg)] += g * seg
    return out


def add_at(buf: np.ndarray, x: np.ndarray, pos: int, wrap: bool = True, gain: float = 1.0):
    """Add x into buf at sample index pos, wrapping around the end (for seamless loops)."""
    n = len(buf)
    pos %= n
    m = len(x)
    if m > n:
        x, m = x[:n], n
    first = min(m, n - pos)
    buf[pos:pos + first] += gain * x[:first]
    if first < m:
        if wrap:
            buf[: m - first] += gain * x[first:]


# --------------------------------------------------------------------------- envelopes
def rise(n: int, attack: float, sr: int = SR) -> np.ndarray:
    """Raised-cosine 0 -> 1 ramp over `attack` seconds, then 1."""
    a = max(1, n_of(attack, sr))
    env = np.ones(n)
    k = min(a, n)
    env[:k] = np.sin(0.5 * np.pi * np.arange(k) / a) ** 2
    return env


def exp_decay(n: int, tau: float, sr: int = SR) -> np.ndarray:
    return np.exp(-tvec(n, sr) / tau)


def attack_decay(n: int, attack: float, tau: float, sr: int = SR) -> np.ndarray:
    return rise(n, attack, sr) * exp_decay(n, tau, sr)


def bell(n: int, peak: float = 0.5, power: float = 1.0) -> np.ndarray:
    """Smooth 0 -> 1 -> 0 envelope with the maximum at fraction `peak` of the length."""
    u = np.linspace(0.0, 1.0, n)
    up = np.sin(0.5 * np.pi * np.clip(u / max(peak, 1e-6), 0, 1)) ** 2
    dn = np.cos(0.5 * np.pi * np.clip((u - peak) / max(1 - peak, 1e-6), 0, 1)) ** 2
    return np.where(u < peak, up, dn) ** power


def smoothstep(u):
    u = np.clip(u, 0.0, 1.0)
    return u * u * (3 - 2 * u)


def fade(x: np.ndarray, fade_in: float = 0.0, fade_out: float = 0.0, sr: int = SR) -> np.ndarray:
    """Raised-cosine fades (seconds)."""
    x = x.copy()
    n = len(x)
    a, b = min(n, n_of(fade_in, sr)), min(n, n_of(fade_out, sr))
    if a > 0:
        r = np.sin(0.5 * np.pi * np.arange(a) / a) ** 2
        x[:a] *= r if x.ndim == 1 else r[:, None]
    if b > 0:
        r = np.cos(0.5 * np.pi * np.arange(b) / b) ** 2
        # last sample reaches exactly 0
        r = np.cos(0.5 * np.pi * (np.arange(b) + 1) / b) ** 2
        x[n - b:] *= r if x.ndim == 1 else r[:, None]
    return x


def geom_sweep(f0: float, f1: float, n: int, ease: str = "smooth") -> np.ndarray:
    """Per-sample frequency curve f0 -> f1 on a logarithmic scale."""
    u = np.linspace(0, 1, n)
    if ease == "smooth":
        u = smoothstep(u)
    elif ease == "in":
        u = u ** 2
    elif ease == "out":
        u = 1 - (1 - u) ** 2
    return f0 * (f1 / f0) ** u


# --------------------------------------------------------------------------- filters
def _sos(kind: str, f, order: int, sr: int):
    nyq = sr / 2 - 1
    if kind == "bp":
        f = (max(f[0], 1.0), min(f[1], nyq))
        return signal.butter(order, f, btype="bandpass", fs=sr, output="sos")
    f = min(max(f, 1.0), nyq)
    return signal.butter(order, f, btype="lowpass" if kind == "lp" else "highpass", fs=sr, output="sos")


def lp(x, f, order: int = 4, sr: int = SR):
    return signal.sosfilt(_sos("lp", f, order, sr), x, axis=0)


def hp(x, f, order: int = 2, sr: int = SR):
    return signal.sosfilt(_sos("hp", f, order, sr), x, axis=0)


def bp(x, f_lo, f_hi, order: int = 2, sr: int = SR):
    return signal.sosfilt(_sos("bp", (f_lo, f_hi), order, sr), x, axis=0)


def dc_block(x, fc: float = 8.0, sr: int = SR):
    return hp(x, fc, order=1, sr=sr)


def biquad_coeffs(kind: str, f: float, q: float = 0.7071, gain_db: float = 0.0, sr: int = SR):
    """RBJ audio-EQ-cookbook biquad coefficients (b, a), a0 normalised to 1."""
    f = min(max(f, 5.0), sr / 2 - 100)
    w0 = 2 * np.pi * f / sr
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / (2 * q)
    A = 10 ** (gain_db / 40)
    if kind == "lp":
        b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]
        a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "hp":
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]
        a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "bp":  # constant 0 dB peak gain
        b = [alpha, 0, -alpha]
        a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "notch":
        b = [1, -2 * cw, 1]
        a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "peak":
        b = [1 + alpha * A, -2 * cw, 1 - alpha * A]
        a = [1 + alpha / A, -2 * cw, 1 - alpha / A]
    elif kind == "lowshelf":
        s = 2 * np.sqrt(A) * alpha
        b = [A * ((A + 1) - (A - 1) * cw + s), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - s)]
        a = [(A + 1) + (A - 1) * cw + s, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - s]
    elif kind == "highshelf":
        s = 2 * np.sqrt(A) * alpha
        b = [A * ((A + 1) + (A - 1) * cw + s), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - s)]
        a = [(A + 1) - (A - 1) * cw + s, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - s]
    else:
        raise ValueError(kind)
    b, a = np.array(b, float), np.array(a, float)
    return b / a[0], a / a[0]


def biquad(x, kind: str, f: float, q: float = 0.7071, gain_db: float = 0.0, sr: int = SR):
    b, a = biquad_coeffs(kind, f, q, gain_db, sr)
    return signal.lfilter(b, a, x, axis=0)


def tv_biquad(x: np.ndarray, kind: str, fc, q=0.9, block: int = 64, sr: int = SR) -> np.ndarray:
    """Biquad with per-sample centre-frequency / Q curves, updated every `block` samples.

    State is carried across blocks (DF2T), which is smooth for slow sweeps.
    """
    x = np.asarray(x, float)
    n = len(x)
    fc = np.broadcast_to(np.asarray(fc, float), (n,))
    q = np.broadcast_to(np.asarray(q, float), (n,))
    y = np.empty(n)
    zi = np.zeros(2)
    for s in range(0, n, block):
        e = min(n, s + block)
        m = (s + e) // 2
        b, a = biquad_coeffs(kind, fc[m], q[m], 0.0, sr)
        y[s:e], zi = signal.lfilter(b, a, x[s:e], zi=zi)
    return y


def onepole_lp(x, f: float, sr: int = SR):
    a = 1 - np.exp(-2 * np.pi * f / sr)
    return signal.lfilter([a], [1, -(1 - a)], x, axis=0)


# --------------------------------------------------------------------------- noise
def interp_db(f: np.ndarray, pts) -> np.ndarray:
    hz = np.log2(np.array([p[0] for p in pts], float))
    dbv = np.array([p[1] for p in pts], float)
    return np.interp(np.log2(np.maximum(f, 1e-3)), hz, dbv)


def shaped_noise(n: int, shape, g: np.random.Generator, sr: int = SR) -> np.ndarray:
    """Gaussian-ish noise of length n with a prescribed magnitude spectrum, unit RMS.

    shape: list of (hz, dB) points (log-frequency interpolation, held outside the
    range) or a callable f_hz -> dB.  The result is exactly periodic over n samples,
    so long textures made this way loop seamlessly.
    """
    f = np.fft.rfftfreq(n, 1.0 / sr)
    d = shape(f) if callable(shape) else interp_db(f, shape)
    mag = 10 ** (d / 20)
    spec = (g.standard_normal(len(f)) + 1j * g.standard_normal(len(f))) * mag
    spec[0] = 0
    if n % 2 == 0:
        spec[-1] = spec[-1].real
    x = np.fft.irfft(spec, n)
    return x / (np.sqrt(np.mean(x ** 2)) + 1e-20)


PINK = [(20, 5.0), (20000, -25.0)]  # -3 dB/oct reference (20 Hz..20 kHz)


def pink(n: int, g, sr: int = SR):
    return shaped_noise(n, lambda f: -10 * np.log10(np.maximum(f, 20) / 1000.0), g, sr)


def brown(n: int, g, sr: int = SR):
    return shaped_noise(n, lambda f: -20 * np.log10(np.maximum(f, 20) / 1000.0), g, sr)


def white(n: int, g):
    x = g.standard_normal(n)
    return x / (np.std(x) + 1e-20)


def periodic_random(n: int, hi_hz: float, g, lo_hz: float = 0.0, sr: int = SR) -> np.ndarray:
    """Smooth zero-mean unit-std random curve that is periodic over n samples."""
    hi_hz = max(hi_hz, 2.5 * sr / n)
    f = np.fft.rfftfreq(n, 1.0 / sr)
    mag = 1.0 / (1.0 + (f / hi_hz) ** 4)
    if lo_hz > 0:
        mag *= (f / lo_hz) ** 2 / (1.0 + (f / lo_hz) ** 2)
    spec = (g.standard_normal(len(f)) + 1j * g.standard_normal(len(f))) * mag
    spec[0] = 0
    x = np.fft.irfft(spec, n)
    return x / (np.std(x) + 1e-20)


def mod_gain(n: int, hi_hz: float, depth_db: float, g, lo_hz: float = 0.0, sr: int = SR) -> np.ndarray:
    """Periodic amplitude modulator expressed in dB (+-depth_db ~ 1 sigma)."""
    return 10 ** (depth_db * periodic_random(n, hi_hz, g, lo_hz, sr) / 20)


def correlated_pair(n: int, shape, g, corr: float = 0.35, sr: int = SR):
    """Two noise channels of the given spectrum with inter-channel correlation ~corr."""
    m = shaped_noise(n, shape, g, sr)
    a = shaped_noise(n, shape, g, sr)
    b = shaped_noise(n, shape, g, sr)
    k, s = np.sqrt(corr), np.sqrt(1 - corr)
    return np.stack([k * m + s * a, k * m + s * b], axis=1)


# --------------------------------------------------------------------------- synthesis
def modal(freqs, amps, t60s, n: int, sr: int = SR, phases=None, attack: float = 0.0006,
          glide: float = 0.0, glide_tau: float = 0.012, g: np.random.Generator | None = None) -> np.ndarray:
    """Sum of exponentially damped sinusoids.

    t60s are the 60 dB decay times (s); `glide` is the fractional initial pitch
    excess that relaxes with time constant `glide_tau` (a soft "thock" pitch dip).
    """
    t = tvec(n, sr)
    out = np.zeros(n)
    atk = rise(n, attack, sr)
    for i, (f, a, t60) in enumerate(zip(freqs, amps, t60s)):
        if f >= sr / 2 - 200:
            continue
        ph = 2 * np.pi * (f * t + f * glide * glide_tau * (1 - np.exp(-t / glide_tau)))
        ph0 = phases[i] if phases is not None else (g.uniform(0, 2 * np.pi) if g is not None else 0.0)
        out += a * np.exp(-t * LN1000 / t60) * np.sin(ph + ph0)
    return out * atk


def glide_sine(f_end: float, n: int, start_ratio: float = 1.5, tau: float = 0.05, sr: int = SR, phase: float = 0.0):
    t = tvec(n, sr)
    ph = 2 * np.pi * (f_end * t + f_end * (start_ratio - 1) * tau * (1 - np.exp(-t / tau)))
    return np.sin(ph + phase)


def sat(x, drive: float = 1.0, asym: float = 0.0):
    """Soft tanh saturation with unit small-signal gain (asym adds even harmonics)."""
    if asym:
        y = (np.tanh(drive * x + asym) - np.tanh(asym)) / (drive * (1 - np.tanh(asym) ** 2))
    else:
        y = np.tanh(drive * x) / drive
    return y


def grains(n: int, times_s, amps, g, dur=(0.003, 0.010), tau_ratio: float = 0.35,
           lp_hz=(300, 1500), sr: int = SR, attack: float = 0.0006) -> np.ndarray:
    """Granular texture: short low-passed noise bursts (crackle / soil / paper)."""
    out = np.zeros(n)
    for t0, a in zip(times_s, amps):
        d = g.uniform(*dur)
        m = max(8, n_of(d, sr))
        seg = g.standard_normal(m)
        seg = onepole_lp(seg, float(np.exp(g.uniform(np.log(lp_hz[0]), np.log(lp_hz[1])))), sr)
        seg *= attack_decay(m, attack, d * tau_ratio, sr)
        i = n_of(t0, sr)
        if i < n:
            e = min(n, i + m)
            out[i:e] += a * seg[: e - i]
    return out


# --------------------------------------------------------------------------- stereo
def pan_gains(p):
    p = np.clip(p, -1.0, 1.0)
    th = (p + 1) * np.pi / 4
    return np.cos(th), np.sin(th)


def pan(x: np.ndarray, p) -> np.ndarray:
    """Constant-power pan of a mono signal; p in [-1, 1] scalar or per-sample."""
    gl, gr = pan_gains(p)
    return np.stack([x * gl * np.sqrt(2), x * gr * np.sqrt(2)], axis=1) * np.sqrt(0.5) * np.sqrt(2) * 0.7071


def width(x: np.ndarray, w: float) -> np.ndarray:
    """Mid/side width: 0 = mono, 1 = unchanged, >1 wider."""
    x = to_stereo(x)
    m = 0.5 * (x[:, 0] + x[:, 1])
    s = 0.5 * (x[:, 0] - x[:, 1]) * w
    return np.stack([m + s, m - s], axis=1)


def decorrelate(x: np.ndarray, g, ms: float = 14.0, sr: int = SR, amount: float = 1.0) -> np.ndarray:
    """Mono -> stereo using two short random-phase all-pass filters (adds air, keeps mono sum solid)."""
    n = len(x)
    out = []
    L = n_of(ms / 1000.0, sr)
    for _ in range(2):
        spec = np.exp(1j * g.uniform(-np.pi, np.pi, L // 2 + 1))
        spec[0] = 1
        ir = np.fft.irfft(spec, L) * np.hanning(2 * L)[L:] * 1.0
        ir[0] += 0.0
        ir /= np.sqrt(np.sum(ir ** 2))
        out.append(fftconvolve(x, ir)[:n])
    ap = np.stack(out, axis=1)
    return (1 - amount) * to_stereo(x) + amount * ap


# --------------------------------------------------------------------------- reverb
def make_ir(rt=(0.3, 0.25, 0.15), predelay: float = 0.0, er_n: int = 8, er_span: float = 0.02,
            er_ratio: float = 0.35, hf_cut: float = 6000.0, build: float = 0.01,
            band_gains=(1.0, 1.0, 0.7), xover=(250.0, 2000.0), length: float | None = None,
            seed: int = 1, sr: int = SR) -> np.ndarray:
    """Procedural stereo impulse response, unit energy.

    rt: RT60 (s) for the low / mid / high bands; early reflections are sparse
    low-passed taps inside `er_span`; the tail is band-wise exponentially decaying
    noise (independent for L and R => natural decorrelation).
    """
    g = rng(seed)
    L = n_of((length if length else max(rt) * 1.12) + predelay + 0.05, sr)
    t = tvec(L, sr)
    pre = n_of(predelay, sr)
    ir = np.zeros((L, 2))
    for c in range(2):
        w = g.standard_normal(L)
        bands = [lp(w, xover[0], 4, sr), bp(w, xover[0], xover[1], 2, sr), hp(w, xover[1], 4, sr)]
        tail = sum(bg * b * np.exp(-t * LN1000 / r) for bg, b, r in zip(band_gains, bands, rt))
        tail = lp(tail, hf_cut, 2, sr) * (1 - np.exp(-t / build))
        er = np.zeros(L)
        times = np.sort(g.uniform(0.0015, er_span, er_n))
        for ti in times:
            er[n_of(ti, sr)] += g.choice([-1, 1]) * np.exp(-ti / (er_span * 0.7)) * g.uniform(0.6, 1.0)
        er = onepole_lp(er, 3200, sr)
        k = n_of(0.06, sr)
        er *= np.sqrt(er_ratio * np.sum(tail[:k] ** 2) / (np.sum(er ** 2) + 1e-20))
        sig = tail + er
        ir[pre:, c] = sig[: L - pre]
    ir /= np.sqrt(np.sum(ir ** 2) / 2)
    # fade the very end so truncation cannot click
    return fade(ir, 0.0, min(0.15, 0.1 * L / sr), sr)


_IR_CACHE: dict = {}


def ir_preset(name: str, sr: int = SR) -> np.ndarray:
    """Named IRs: wood_room (small, warm), cabin (tight, dull), hall (medium), dark_space (large, dark)."""
    if name in _IR_CACHE:
        return _IR_CACHE[name]
    presets = {
        # small wooden room: ~0.3 s, warm, tight reflections
        "wood_room": dict(rt=(0.34, 0.26, 0.12), predelay=0.0, er_n=9, er_span=0.022, er_ratio=0.5,
                          hf_cut=3800, build=0.008, seed=11),
        "cabin": dict(rt=(0.22, 0.14, 0.06), predelay=0.0, er_n=7, er_span=0.012, er_ratio=0.6,
                      hf_cut=2600, build=0.004, seed=12),
        # medium stone/wood hall: ~1.9 s
        "hall": dict(rt=(2.3, 1.9, 1.0), predelay=0.016, er_n=14, er_span=0.06, er_ratio=0.25,
                     hf_cut=4500, build=0.025, band_gains=(1.1, 1.0, 0.6), seed=13),
        # dark large space: ~4.5 s, low-mid bloom, little air
        "dark_space": dict(rt=(5.2, 4.2, 1.6), predelay=0.03, er_n=10, er_span=0.09, er_ratio=0.12,
                           hf_cut=1700, build=0.06, band_gains=(1.3, 0.9, 0.35), xover=(180.0, 1200.0), seed=14),
    }
    _IR_CACHE[name] = make_ir(sr=sr, **presets[name])
    return _IR_CACHE[name]


def convolve(x: np.ndarray, ir: np.ndarray) -> np.ndarray:
    """Convolve mono/stereo x with a stereo IR; returns (n+m-1, 2)."""
    xs = to_stereo(x)
    irs = ir if ir.ndim == 2 else to_stereo(ir)
    return np.stack([fftconvolve(xs[:, c], irs[:, c]) for c in range(2)], axis=1)


def reverb(x: np.ndarray, ir: np.ndarray | str, wet: float = 0.25, dry: float = 1.0, tail: float | None = None,
           sr: int = SR) -> np.ndarray:
    """Dry + convolved wet. Output length = len(x) + tail (default: whole IR)."""
    if isinstance(ir, str):
        ir = ir_preset(ir, sr)
    xs = to_stereo(x)
    w = convolve(xs, ir)
    total = len(xs) + (len(ir) if tail is None else n_of(tail, sr))
    out = np.zeros((total, 2))
    out[: len(xs)] += dry * xs
    m = min(total, len(w))
    out[:m] += wet * w[:m]
    return out


def circ_conv(x: np.ndarray, ir: np.ndarray) -> np.ndarray:
    """Circular convolution (periodic buffers): keeps loops seamless."""
    n = len(x)
    xs = to_stereo(x)
    irs = ir if ir.ndim == 2 else to_stereo(ir)
    if len(irs) >= n:
        irs = irs[: n - 1]
    out = np.zeros((n, 2))
    for c in range(2):
        H = np.fft.rfft(irs[:, c], n)
        out[:, c] = np.fft.irfft(np.fft.rfft(xs[:, c]) * H, n)
    return out


# --------------------------------------------------------------------------- analysis / levels
def peak_db(x: np.ndarray) -> float:
    return db(np.max(np.abs(x)))


def rms_envelope(x: np.ndarray, win: float = 0.02, sr: int = SR) -> np.ndarray:
    m = mono(x) ** 2
    k = max(1, n_of(win, sr))
    c = np.convolve(m, np.ones(k) / k, mode="same")
    return np.sqrt(np.maximum(c, 0))


def peak_normalize(x: np.ndarray, target_db: float = -3.0) -> tuple[np.ndarray, float]:
    p = np.max(np.abs(x))
    g = undb(target_db) / max(p, 1e-12)
    return x * g, db(g)


def lufs(x: np.ndarray, sr: int = SR) -> float:
    """Integrated loudness (ITU-R BS.1770 via pyloudnorm); pads very short material with silence."""
    import pyloudnorm as pyln
    xs = to_stereo(x).astype(np.float64)
    if len(xs) < sr:
        xs = np.concatenate([xs, np.zeros((sr - len(xs), 2))])
    v = pyln.Meter(sr).integrated_loudness(xs)
    return float(v)


def lufs_normalize(x: np.ndarray, target: float = -30.0, peak_cap_db: float = -3.0, sr: int = SR):
    cur = lufs(x, sr)
    g = undb(target - cur)
    y = x * g
    if peak_db(y) > peak_cap_db:
        y, _ = peak_normalize(x, peak_cap_db)
    return y


def hf_ratio_db(x: np.ndarray, above: float = 8000.0, sr: int = SR) -> float:
    """Energy above `above` Hz relative to total energy (dB)."""
    m = mono(x)
    S = np.abs(np.fft.rfft(m)) ** 2
    f = np.fft.rfftfreq(len(m), 1 / sr)
    return 10 * np.log10(S[f >= above].sum() / (S.sum() + 1e-30) + 1e-30)


def spectral_centroid(x: np.ndarray, sr: int = SR) -> float:
    m = mono(x)
    S = np.abs(np.fft.rfft(m)) ** 2
    f = np.fft.rfftfreq(len(m), 1 / sr)
    return float((S * f).sum() / (S.sum() + 1e-30))


# --------------------------------------------------------------------------- loops / trimming
def trim_lead(x: np.ndarray, thresh_db: float = -45.0, keep: float = 0.0005, sr: int = SR) -> np.ndarray:
    """Drop leading silence: start `keep` s before the first sample above peak+thresh_db."""
    a = np.max(np.abs(to_stereo(x)), axis=1)
    thr = a.max() * undb(thresh_db)
    idx = int(np.argmax(a > thr))
    start = max(0, idx - n_of(keep, sr))
    return x[start:]


def trim_tail(x: np.ndarray, thresh_db: float = -66.0, min_len: float = 0.05, sr: int = SR) -> np.ndarray:
    a = np.max(np.abs(to_stereo(x)), axis=1)
    thr = a.max() * undb(thresh_db)
    nz = np.nonzero(a > thr)[0]
    end = int(nz[-1]) + 1 if len(nz) else len(x)
    return x[: max(end, n_of(min_len, sr))]


def loopify(x: np.ndarray, n: int, xfade: float, sr: int = SR) -> np.ndarray:
    """Make x (length >= n + xfade) loop seamlessly over n samples with an equal-power crossfade."""
    k = n_of(xfade, sr)
    assert len(x) >= n + k, "need n + xfade samples"
    out = x[:n].copy()
    u = np.arange(k) / k
    w_in, w_out = np.sin(0.5 * np.pi * u), np.cos(0.5 * np.pi * u)
    if x.ndim == 2:
        w_in, w_out = w_in[:, None], w_out[:, None]
    out[:k] = x[:k] * w_in + x[n:n + k] * w_out
    return out


def write_wav(path, x: np.ndarray, sr: int = SR):
    import soundfile as sf
    sf.write(str(path), to_stereo(x).astype(np.float32), sr, subtype="FLOAT")
