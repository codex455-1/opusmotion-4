#!/usr/bin/env python3
"""Procedural sound-effect library for the MI6 / KGB-archivist documentary short.

    python tools/make_sfx.py                # render everything -> audio/sfx/*.wav + index.json
    python tools/make_sfx.py --only key_    # render only names starting with the given prefixes
    python tools/make_sfx.py --plots        # additionally write spectrogram sheets to /tmp/verify/sfx_*.png

Deterministic: every sound seeds its own RNG from crc32(name).  48 kHz, stereo, 32-bit float.
One-shots are peak-normalised to -3 dBFS (their natural relative level is kept in
`gain_hint_db`); loops / ambiences are normalised to ~-30 LUFS and are exactly periodic.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
import zlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "audio"))
import sfxlib as S  # noqa: E402
from sfxlib import SR  # noqa: E402

OUT = ROOT / "audio" / "sfx"
INDEX: dict[str, dict] = {}
ONLY: list[str] | None = None
AUDIO: dict[str, np.ndarray] = {}  # kept for --plots


def G(name: str) -> np.random.Generator:
    return S.rng(zlib.crc32(name.encode()))


def wanted(name: str) -> bool:
    return ONLY is None or any(name.startswith(o) for o in ONLY)


def emit(name, x, desc, kind="oneshot", gain_hint_db=0.0, mix_hint_db=-14.0, lufs_target=-30.0,
         lead_thresh=-45.0, tail_thresh=-66.0, tail_fade=0.03, note=None, fade_in=None, peak_mode="sample", peak_at_end=False):
    """Finalise + write one sound. kind: oneshot | preroll (no lead trim, documented peak_time) | loop."""
    x = S.to_stereo(x).astype(np.float64)
    assert np.isfinite(x).all(), name
    if kind == "loop":
        x = x - x.mean(axis=0, keepdims=True)
        x = S.lufs_normalize(x, lufs_target, -3.0)
    else:
        x = S.dc_block(x, 8.0)
        if kind == "oneshot":
            x = S.trim_lead(x, lead_thresh, 0.0005)
        x = S.trim_tail(x, tail_thresh)
        x = S.fade(x, fade_in if fade_in is not None else (0.0004 if kind == "oneshot" else 0.004), tail_fade)
        x, _ = S.peak_normalize(x, -3.0)
    AUDIO[name] = x
    S.write_wav(OUT / f"{name}.wav", x)
    n = len(x)
    a = np.max(np.abs(x), axis=1)
    pk = float(np.max(a))
    onset = float(np.argmax(a > pk * 10 ** (-40 / 20)) / SR)
    if kind == "loop":
        peak_time = None
        jump = float(np.max(np.abs(x[0] - x[-1])))
        step99 = float(np.percentile(np.abs(np.diff(x, axis=0)), 99.5) + 1e-12)
        seam = round(jump / step99, 3)  # <= 1: the wrap-around step is no bigger than ordinary steps
    elif peak_at_end:
        peak_time = (n - S.n_of(tail_fade)) / SR  # last full-level sample: the hit lands here
        seam = None
    elif kind == "preroll" or peak_mode == "rms":
        env = S.rms_envelope(x, 0.1 if kind == "preroll" else 0.05)
        peak_time = float(np.argmax(env) / SR)
        seam = None
    else:
        peak_time = float(np.argmax(a) / SR)
        seam = None
    INDEX[name] = dict(
        name=name, file=f"{name}.wav", kind=kind, duration=round(n / SR, 4), samples=n,
        peak_dbfs=round(S.peak_db(x), 2), lufs=round(S.lufs(x), 2),
        onset_time=round(onset, 4), peak_time=None if peak_time is None else round(peak_time, 4),
        gain_hint_db=round(float(gain_hint_db), 2), mix_hint_db=mix_hint_db,
        hf_above_8k_db=round(S.hf_ratio_db(x, 8000), 1), centroid_hz=round(S.spectral_centroid(x)),
        loop=kind == "loop", seam_jump_vs_p99_step=seam, description=desc,
    )
    if note:
        INDEX[name]["note"] = note
    return x


# ============================================================================ helpers
def burst(g, n, shape, attack, tau, dur=None):
    """Shaped-noise burst with attack/decay envelope, padded to n samples (unit-RMS before envelope)."""
    m = n if dur is None else min(n, S.n_of(dur))
    x = S.shaped_noise(m, shape, g) * S.attack_decay(m, attack, tau)
    return S.pad_to(x, n)


def at(x, off, n):
    """Place x at `off` seconds inside a zero buffer of n samples."""
    out = np.zeros(n)
    i = S.n_of(off)
    if i < n:
        seg = x[: n - i]
        out[i:i + len(seg)] = seg
    return out


def unit(x):
    return x / (np.sqrt(np.mean(x ** 2)) + 1e-20)


def poisson_times(g, t0, t1, rate_fn):
    """Inhomogeneous Poisson process by sequential sampling (rate_fn: s -> events/s)."""
    t, out = t0, []
    while True:
        r = max(rate_fn(t), 1e-3)
        t += g.exponential(1.0 / r)
        if t >= t1:
            return out
        out.append(t)


NOISE_BP_SOFT = [(60, -30), (250, -6), (700, 0), (1500, -4), (2600, -16), (4000, -40), (8000, -70)]


# ============================================================================ KEYBOARD
KEY_F0 = [262, 214, 304, 236, 332, 248, 205, 283, 225, 318, 271, 241]
KEY_VEL = [1.00, .86, .93, .78, .97, .90, .82, 1.0, .88, .95, .80, .92]


def keyhit(g, kind, f0, vel, t60, gap, rel_level, ratio2, a2, char=None):
    """Press (bottom-out thock) + quieter upstroke `gap` s later. Returns stereo with a tiny wooden room."""
    n = S.n_of(gap + 0.30)
    if kind == "key":
        ratios, amps, t60r = [1, ratio2, 0.62, 2.35], [1.0, a2, 0.55, 0.09], [1, .55, 1.15, .30]
        tap_a, tap_lp, desk_f, desk_a, desk_t, drive, glide = 0.16, 2400, g.uniform(92, 124), 0.45, 0.085, 1.3, 0.10
        f_rel_mul, stab = 1.18, 0
    elif kind == "space":
        ratios, amps, t60r = [1, 1.38, 0.55, 2.05], [1.0, 0.40, 0.70, 0.07], [1, .60, 1.2, .30]
        tap_a, tap_lp, desk_f, desk_a, desk_t, drive, glide = 0.12, 1800, g.uniform(68, 90), 0.6, 0.12, 1.2, 0.14
        f_rel_mul, stab = 1.10, 0.20
    else:  # enter
        ratios, amps, t60r = [1, 1.5, 0.5, 2.2], [1.0, 0.5, 0.8, 0.10], [1, .6, 1.2, .30]
        tap_a, tap_lp, desk_f, desk_a, desk_t, drive, glide = 0.20, 2200, g.uniform(78, 100), 0.8, 0.13, 1.7, 0.12
        f_rel_mul, stab = 1.10, 0.30
    c = dict(desk=1.0, tap=1.0, lp=1.0, drive=1.0, glide=1.0)
    c.update(char or {})
    desk_a, tap_a, tap_lp, drive, glide = desk_a * c["desk"], tap_a * c["tap"], tap_lp * c["lp"], drive * c["drive"], glide * c["glide"]
    tap_shape = [(100, -20), (400, 0), (1200, 0), (tap_lp, -6), (tap_lp * 1.5, -30), (tap_lp * 3, -60)]
    body = S.modal([f0 * r for r in ratios], amps, [t60 * r for r in t60r], n, glide=glide, glide_tau=0.012,
                   attack=0.0011)
    desk = S.modal([desk_f], [desk_a], [desk_t], n, attack=0.0012)
    tap = burst(g, n, tap_shape, 0.0014, 0.0055, dur=0.04)
    press = body + desk + tap_a * vel ** 2 * tap
    if stab:  # soft second bottom-out of the stabiliser (no rattle)
        st = burst(g, n, [(60, -20), (200, 0), (600, -3), (1200, -24), (2400, -60)], 0.002, 0.012, dur=0.08)
        press += at(st, g.uniform(0.008, 0.013), n) * stab * 1.4
        press += at(S.modal([desk_f * 1.15], [stab * 1.2], [0.08], n, attack=0.0015), 0.010, n)
    press *= vel
    fr = f0 * f_rel_mul
    rel = S.modal([fr, fr * 1.5], [1.0, 0.35], [t60 * 0.38, t60 * 0.22], n, glide=0.05, attack=0.001)
    rel_tap = burst(g, n, [(100, -20), (500, 0), (1400, 0), (2200, -8), (3500, -40), (6000, -70)], 0.0012, 0.0045,
                    dur=0.04)
    release = (rel * 0.9 + 0.5 * rel_tap * 0.16) * rel_level * vel
    x = press + at(release, gap, n)
    x = S.sat(x, drive)
    x = S.lp(x, 4200, 4)
    x = S.dc_block(x, 20)
    y = S.reverb(x, "wood_room", wet=0.33, tail=0.12)
    return S.pan(S.mono(y), g.uniform(-0.04, 0.04)) * 0.0 + S.width(y, 0.8)


def gen_keys():
    perm = [5, 0, 8, 3, 11, 2, 7, 10, 1, 6, 9, 4]
    for i in range(12):
        name = f"key_thock_{i+1:02d}"
        if not wanted(name):
            continue
        g = G(name)
        f0 = 170 * (372 / 170) ** (perm[i] / 11) * g.uniform(0.985, 1.015)
        vel = KEY_VEL[i]
        rank = perm[i]  # neighbours in pitch differ in decay, desk resonance and 2nd-mode weight
        char = dict(desk=[0.6, 1.5, 1.0][rank % 3] * g.uniform(0.9, 1.1), tap=g.uniform(0.7, 1.5),
                    lp=g.uniform(0.75, 1.3), drive=g.uniform(0.85, 1.25), glide=g.uniform(0.7, 1.4))
        t60 = (0.105 + 0.05 * (rank % 2)) * g.uniform(0.94, 1.06)
        a2 = (0.28 if rank % 4 < 2 else 0.58) * g.uniform(0.9, 1.1)
        x = keyhit(g, "key", f0, vel, t60, g.uniform(0.072, 0.108), g.uniform(0.26, 0.40),
                   g.uniform(1.45, 1.68), a2, char)
        emit(name, x, f"Creamy lubed-linear thock (bottom-out ~{f0:.0f} Hz body, wooden desk) + soft release upstroke.",
             gain_hint_db=20 * np.log10(vel ** 1.3), mix_hint_db=-16)
    for i, f in enumerate([168, 142, 196]):
        name = f"key_space_{i+1:02d}"
        if not wanted(name):
            continue
        g = G(name)
        vel = [1.0, .88, .94][i]
        x = keyhit(g, "space", f, vel, [0.17, 0.2, 0.15][i], [0.098, 0.108, 0.088][i], [0.36, 0.30, 0.40][i], 1.38, 0.4,
                   dict(desk=g.uniform(0.8, 1.3), tap=g.uniform(0.8, 1.3), lp=g.uniform(0.85, 1.2)))
        emit(name, x, f"Spacebar thock: deeper ({f} Hz body), soft stabiliser, no rattle; upstroke follows.",
             gain_hint_db=20 * np.log10(vel ** 1.3), mix_hint_db=-15)
    for i, f in enumerate([172, 152]):
        name = f"key_enter_{i+1:02d}"
        if not wanted(name):
            continue
        g = G(name)
        vel = [1.0, .9][i]
        x = keyhit(g, "enter", f, vel, [0.2, 0.24][i], [0.102, 0.112][i], [0.40, 0.34][i], 1.5, 0.5)
        emit(name, x, f"Heavier, fuller Enter/line-end thock ({f} Hz body) with double soft bottom-out and upstroke.",
             gain_hint_db=20 * np.log10(vel ** 1.3), mix_hint_db=-13)


# ============================================================================ TEXT POPS
def pop_dry(g, f, attack, decay, glide=1.3, glide_tau=0.03, air=0.12, drive=1.5, tri=0.11, sub=0.4, n_extra=0.05):
    """Rounded low 'bloop': downward-gliding sine/triangle body + octave sub + gentle airy swell, saturated + low-passed."""
    n = S.n_of(decay * 1.5 + n_extra)
    t = S.tvec(n)
    tau = decay / 4.6
    ph = 2 * np.pi * (f * t + f * (glide - 1) * glide_tau * (1 - np.exp(-t / glide_tau)))
    env = S.rise(n, attack) * np.exp(-t / tau)
    body = np.sin(ph) - tri * np.sin(3 * ph) + 0.20 * np.sin(2 * ph + 0.6) * np.exp(-t / (tau * 0.5)) + sub * np.sin(0.5 * ph)
    body *= env
    swell_tau = 0.075
    aenv = S.rise(n, 0.06) * np.exp(-t / (swell_tau * (decay / 0.2) ** 0.5))
    airy = S.shaped_noise(n, [(200, -30), (700, -6), (1400, 0), (2500, -8), (4000, -30), (8000, -70)], g) * aenv
    x = body + air * airy
    x = S.sat(x, drive, asym=0.15)
    x = S.lp(x, 4000, 4)
    return S.dc_block(x, 20)


POP_PARAMS = [  # f, attack, decay, glide, glide_tau, air
    (310, 0.007, 0.22, 1.35, 0.030, 0.14),
    (385, 0.005, 0.17, 1.26, 0.025, 0.12),
    (445, 0.008, 0.26, 1.40, 0.035, 0.16),
    (520, 0.004, 0.14, 1.20, 0.020, 0.10),
    (610, 0.010, 0.30, 1.30, 0.040, 0.15),
    (350, 0.006, 0.19, 1.30, 0.028, 0.13),
]


def gen_pops():
    for i, (f, a, d, gl, gt, air) in enumerate(POP_PARAMS):
        name = f"text_pop_{i+1:02d}"
        if not wanted(name):
            continue
        g = G(name)
        x = pop_dry(g, f, a, d, gl, gt, air)
        y = S.reverb(x, "wood_room", wet=0.45, tail=0.25)
        y = S.reverb(S.mono(y), "hall", wet=0.03, dry=1.0, tail=0.3)
        y = S.width(y, 0.9)
        emit(name, y, f"Creamy rounded low pluck/bloop (~{f} Hz, quick downward glide, airy swell, warm saturation), tasteful room tail.",
             mix_hint_db=-14, gain_hint_db=-0.8 * (i % 3), tail_thresh=-50, tail_fade=0.08)
    soft = [(520, 700, 0.008, 0.028), (640, 560, 0.010, 0.034), (780, 820, 0.007, 0.026),
            (560, 480, 0.009, 0.040), (700, 900, 0.008, 0.030), (880, 640, 0.010, 0.036)]
    for i, (f, c, a, tau) in enumerate(soft):
        name = f"text_soft_{i+1:02d}"
        if not wanted(name):
            continue
        g = G(name)
        n = S.n_of(0.32)
        shape = [(c * 0.25, -40), (c * 0.5, -8), (c, 0), (c * 1.6, -9), (c * 2.6, -30), (c * 5, -70)]
        puff = burst(g, n, shape, a, tau)
        tone = S.modal([f], [0.22], [0.11], n, attack=0.006, glide=0.12, glide_tau=0.03)
        x = S.sat(puff * 0.7 + tone, 1.1)
        x = S.lp(x, 2400, 4)
        y = S.reverb(x, "wood_room", wet=0.30, tail=0.15)
        emit(name, y, "Very soft velvety puff/tick for caption phrases; energy kept 250-1500 Hz so it sits under a voice.",
             mix_hint_db=-22, gain_hint_db=-0.7 * (i % 3))


# ============================================================================ THUMPS / BOOMS
def gen_thumps_booms():
    cfg = [(56, 230, 0.26), (64, 270, 0.22), (50, 200, 0.30)]
    for i, (fs, fp, d) in enumerate(cfg):
        name = f"emph_thump_{i+1:02d}"
        if not wanted(name):
            continue
        g = G(name)
        n = S.n_of(0.55)
        sub = S.glide_sine(fs, n, 1.7, 0.035) * S.attack_decay(n, 0.004, 0.075)
        h2 = S.glide_sine(fs * 2, n, 1.5, 0.03) * S.attack_decay(n, 0.003, 0.04) * 0.30
        pop = S.pad_to(pop_dry(g, fp, 0.004, d, 1.3, 0.03, 0.08), n) * 0.5
        x = sub * 1.0 + h2 + pop
        x = S.lp(S.dc_block(x, 12), 3500, 4)
        y = S.reverb(x, "wood_room", wet=0.30, tail=0.12, send_hp=110)
        emit(name, y, f"Clean {fs} Hz sub thump (~250 ms, pitch-dropped) layered with a creamy {fp} Hz pop.",
             mix_hint_db=-9, tail_thresh=-55, tail_fade=0.06)
    for i, (f, dur, gl) in enumerate([(32, 2.4, 1.55), (44, 2.15, 1.5), (56, 1.9, 1.45)]):
        name = f"sub_boom_{i+1:02d}"
        if not wanted(name):
            continue
        g = G(name)
        n = S.n_of(dur + 0.6)
        t = S.tvec(n)
        a = [0.016, 0.012, 0.010][i]
        env = S.rise(n, a)
        fund = S.glide_sine(f, n, gl, 0.10) * env * np.exp(-t / (dur * 0.20))
        h2 = S.glide_sine(f * 2, n, gl, 0.10) * env * np.exp(-t / (dur * 0.16)) * 0.55
        h3 = S.glide_sine(f * 3, n, gl, 0.10) * env * np.exp(-t / (dur * 0.10)) * 0.28
        h4 = S.glide_sine(f * 4, n, gl, 0.10) * env * np.exp(-t / (dur * 0.06)) * 0.10
        body = S.lp(S.brown(n, g), 150, 2) * S.attack_decay(n, 0.012, dur * 0.12) * 0.22
        x = fund + h2 + h3 + h4 + body
        x = S.lp(S.dc_block(x, 10), 1400, 4)
        y = S.reverb(x, "dark_space", wet=0.30, tail=0.0, send_hp=80, send_lp=900, dry_fade=0)
        y = S.fade(y, 0, 0.55)
        emit(name, y, f"Cinematic sub drop, {f} Hz fundamental with 2nd-4th harmonics for small speakers, smooth attack, no distortion.",
             mix_hint_db=-10, tail_fade=0.5, peak_mode="rms",
             note=f"~{dur:.1f}s main body, tail fades out over the last 0.5 s; peak_time = 50 ms RMS maximum")


# ============================================================================ WHOOSHES / RISERS / SWELLS
def whoosh(g, dur, f0, f1, q0, q1, peak, direction, wide=0.55, ease="smooth", power=1.2, low=0.8):
    n = S.n_of(dur)
    fc = S.geom_sweep(f0, f1, n, ease)
    q = np.linspace(q0, q1, n)
    srcs = [unit(S.tv_biquad(S.pink(n, g), "bp", fc, q)) for _ in range(3)]
    lowp = unit(S.tv_biquad(S.brown(n, g), "lp", np.clip(fc * 0.45, 80, 900), 0.7))
    env = S.bell(n, peak, power)
    u = np.linspace(0, 1, n)
    # pan travels fully across the swoosh, centred on the peak
    p = direction * (2 * S.smoothstep((u - peak) * 1.1 + 0.5) - 1) * 0.85
    gl, gr = S.pan_gains(p)
    m = (srcs[0] + low * lowp) * env
    stereo = S.pan(m, p) * 0.8 + np.stack([srcs[1] * gl, srcs[2] * gr], axis=1) * env[:, None] * wide * 1.2
    stereo = S.lp(stereo, 4200, 4)
    return S.fade(stereo, 0.01, 0.03)


def gen_whooshes():
    cfg = [  # dur, f0, f1, q0, q1, peak, direction
        (0.70, 240, 1300, 1.2, 1.7, 0.55, +1),
        (1.00, 1200, 280, 1.2, 1.6, 0.50, -1),
        (0.85, 300, 1600, 1.1, 1.6, 0.60, -1),
        (1.30, 170, 950, 1.1, 1.5, 0.52, +1),
    ]
    for i, (d, f0, f1, q0, q1, pk, di) in enumerate(cfg):
        name = f"whoosh_soft_{i+1:02d}"
        if not wanted(name):
            continue
        g = G(name)
        x = whoosh(g, d, f0, f1, q0, q1, pk, di)
        emit(name, x, f"Smooth air whoosh ({'L->R' if di > 0 else 'R->L'}), band-passed pink noise sweeping {f0}->{f1} Hz, low-mid emphasis.",
             kind="preroll", mix_hint_db=-17, tail_fade=0.03,
             note="Designed to start from silence; align peak_time with the visual hit.")
    for i, (d, tail, f0, f1, fs, di) in enumerate([(1.05, 0.35, 140, 800, 44, +1), (1.30, 0.40, 110, 650, 38, -1)]):
        name = f"whoosh_deep_{i+1:02d}"
        if not wanted(name):
            continue
        g = G(name)
        base = whoosh(g, d, f0, f1, 0.7, 1.0, 0.50, di, wide=0.5, power=1.5, low=1.4)
        n = len(base)
        t = S.tvec(n)
        env = S.bell(n, 0.50, 1.6)
        sub = S.glide_sine(fs, n, 1.0, 1.0) * env
        sub = np.sin(2 * np.pi * np.cumsum(fs * (0.8 + 0.4 * np.linspace(0, 1, n) ** 1.5)) / SR) * env
        rumble = S.lp(S.brown(n, g), 180, 2) * env * 0.5
        x = base * 1.0 + np.stack([sub * 0.9 + rumble] * 2, axis=1)
        x = S.lp(x, 4500, 4)
        y = S.reverb(x, "dark_space", wet=0.22, tail=tail, send_hp=120, send_lp=1500)
        emit(name, y, f"Deep transition whoosh with {fs} Hz sub body and dark low-mid air sweep; dark reverb tail.",
             kind="preroll", mix_hint_db=-13, tail_fade=0.08,
             note="Starts from silence; peak_time is the body's maximum.")


def gen_risers():
    name = "riser_air_01"
    if wanted(name):
        g = G(name)
        dur = 3.5
        n = S.n_of(dur)
        u = np.linspace(0, 1, n)
        fc = S.geom_sweep(160, 3600, n, "in")
        q = 0.8 + 1.0 * u
        src = [unit(S.tv_biquad(S.pink(n, g), "bp", fc, q)) for _ in range(3)]
        lowsw = unit(S.tv_biquad(S.brown(n, g), "lp", S.geom_sweep(90, 520, n, "in"), 0.7))
        env = u ** 2.8
        flut = np.clip(1 + 0.07 * u * S.bp(S.white(n, g), 5, 16, 2), 0.8, 1.2)
        w = 0.2 + 0.6 * u
        k, s = np.sqrt(1 - w ** 2), w
        shared = src[0]
        left = (k * shared + s * src[1]) * env * flut
        right = (k * shared + s * src[2]) * env * flut
        sub = lowsw * (u ** 2.4) * 0.9
        x = np.stack([left + sub, right + sub], axis=1)
        x = S.lp(x, 5200, 4)
        y = S.reverb(x, "hall", wet=0.18, tail=1.5, dry_fade=0)[:n]
        y = S.fade(y, 0.05, 0.010)
        emit(name, y, "3.5 s non-tonal tension riser: pink noise with rising band-pass, low swell, widening stereo; cut at its peak.",
             kind="preroll", mix_hint_db=-18, tail_fade=0.010, tail_thresh=-120, peak_at_end=True,
             note="Ends at its maximum (hit lands on the final sample); peak_time ~ duration.")

    for i, (kind, ir) in enumerate([("warm", "dark_space"), ("air", "hall")]):
        name = f"reverse_swell_{i+1:02d}"
        if not wanted(name):
            continue
        g = G(name)
        n = S.n_of(1.5)
        m = S.n_of(0.4)
        if kind == "warm":
            src = burst(g, m, [(80, -20), (300, 0), (900, -2), (2000, -14), (4000, -50)], 0.003, 0.05)
            src += S.glide_sine(78, m, 1.3, 0.03) * S.attack_decay(m, 0.003, 0.09) * 0.9
        else:
            src = burst(g, m, [(200, -20), (700, -3), (1800, 0), (3200, -10), (5000, -40)], 0.003, 0.04)
        wet = S.convolve(src, S.ir_preset(ir))
        k0 = int(np.argmax(S.rms_envelope(wet[: S.n_of(0.5)], 0.01)))  # reversed clip ends exactly on the peak
        rev = wet[k0:k0 + n][::-1].copy()
        rev = S.lp(rev, 4800, 2)
        u = np.linspace(0, 1, n)[:, None]
        rev *= (0.05 + 0.95 * u ** 1.8)
        rev = S.fade(rev, 0.18, 0.012)
        emit(name, rev, f"1.5 s reverse-reverb swell ({kind}) building into a hit point at the final sample.",
             kind="preroll", mix_hint_db=-17, tail_fade=0.012, tail_thresh=-120, peak_at_end=True,
             note="Hit point = end of file; peak_time ~ duration. Place the file so its end lands on the visual hit.")


def gen_sheen():
    for i, (dur, f0, f1, di) in enumerate([(1.0, 900, 3000, +1), (1.5, 3200, 1100, -1)]):
        name = f"light_sweep_{i+1:02d}"
        if not wanted(name):
            continue
        g = G(name)
        n = S.n_of(dur)
        fc = S.geom_sweep(f0, f1, n)
        src = [S.tv_biquad(S.pink(n, g), "bp", fc, 1.4) for _ in range(2)]
        shimmer = np.clip(1 + 0.30 * S.bp(S.white(n, g), 8, 24, 2), 0.4, 1.6)
        d = (0.0005 + 0.0011 * np.sin(np.pi * np.linspace(0, 1, n))) * SR
        idx = np.arange(n) - d
        comb = [np.interp(idx, np.arange(n), s) for s in src]
        env = S.bell(n, 0.48, 1.5)
        u = np.linspace(0, 1, n)
        p = di * (2 * S.smoothstep(u) - 1) * 0.6
        gl, gr = S.pan_gains(p)
        L = (src[0] + 0.55 * comb[0]) * shimmer * env * gl
        R = (src[1] + 0.55 * comb[1]) * shimmer * env * gr
        x = S.lp(np.stack([L, R], axis=1), 4800, 4)
        emit(name, x, f"Very soft shimmering air sheen ({f0}->{f1} Hz band, comb-swept, no tones) for light sweeps.",
             kind="preroll", mix_hint_db=-20, tail_fade=0.05, note="Bell-shaped; peak near the middle.")


# ============================================================================ PAPER / DESK
def paper_slide(g, dur, f_lo, f_hi, peak, grain_hz, land):
    n = S.n_of(dur)
    v = S.bell(n, peak, 1.3)
    fc = f_lo + (f_hi - f_lo) * v
    y = unit(S.tv_biquad(S.pink(n, g), "bp", fc, 0.75))
    low = unit(S.lp(S.pink(n, g), 380, 2))
    grain = unit(S.bp(S.white(n, g), grain_hz * 0.5, grain_hz * 1.6, 2))
    m = np.clip(1 + 0.45 * grain, 0, None)
    env = v ** 1.2 * S.rise(n, 0.008)
    x = (y + 0.5 * low) * m * env
    if land:
        tap = S.modal([150, 310], [0.8, 0.3], [0.05, 0.03], n, attack=0.001) * 1.4
        x = x + at(S.pad_to(tap[: S.n_of(0.1)], n), dur - 0.06, n) * 0.35 + 0 * x
    x = S.lp(x, 3000, 4)
    return S.reverb(x, "wood_room", wet=0.22, tail=0.12, dry_fade=0.04)


def paper_fold(g, dur, clusters, tone_hz, level=1.0):
    n = S.n_of(dur)
    times, env = [], np.zeros(n)
    for c0, w, rate, amp in clusters:
        k = g.poisson(rate * w)
        times += list(np.clip(c0 + np.abs(g.normal(0, w / 2.0, k)), 0, dur - 0.02))
        e = S.bell(S.n_of(w * 1.6), 0.4, 1.0) * amp
        i = S.n_of(max(c0 - 0.02, 0))
        seg = e[: max(0, n - i)]
        env[i:i + len(seg)] += seg
    amps = g.exponential(1.0, len(times)) ** 1.3 * 0.55
    crack = S.grains(n, times, amps, g, dur=(0.002, 0.008), tau_ratio=0.3, lp_hz=(900, 3600))
    sw = unit(S.bp(S.pink(n, g), 350, tone_hz, 2)) * env * 0.35
    x = crack + sw
    x = S.lp(x, 3200, 4)
    return S.reverb(x * level, "wood_room", wet=0.18, tail=0.1, dry_fade=0.06)


def paper_flutter(g, dur, n_sheets, f_air):
    n = S.n_of(dur)
    air = unit(S.bp(S.pink(n, g), 250, f_air, 2)) * S.bell(n, 0.35, 1.4)
    flap_am = np.clip(1 + 0.55 * unit(S.bp(S.white(n, g), 9, 26, 2)), 0.1, None)
    x = air * flap_am * 0.55
    for k in range(n_sheets):
        t0 = 0.0 if k == 0 else g.uniform(0.04, dur * 0.4)
        fb = burst(g, n, [(100, -20), (500, 0), (1000, -1), (1800, -12), (3500, -50)], 0.006, 0.030, dur=0.2)
        x += at(fb, t0, n) * g.uniform(0.5, 0.9)
    for k in range(n_sheets):
        t0 = dur * (0.55 + 0.4 * k / max(1, n_sheets)) * g.uniform(0.9, 1.0)
        fl = S.modal([g.uniform(135, 190), g.uniform(300, 420)], [0.9, 0.3], [0.06, 0.04], n, attack=0.001)
        pat = burst(g, n, [(100, -20), (450, 0), (1100, -3), (2200, -20), (4000, -60)], 0.002, 0.012, dur=0.08)
        x += at(fl * 0.5 + pat * 0.55, t0, n) * g.uniform(0.5, 0.9) * (1 - 0.15 * k)
    x = S.lp(x, 3500, 4)
    return S.reverb(x, "wood_room", wet=0.25, tail=0.2, dry_fade=0.06)


def gen_paper():
    sl = [(0.45, 450, 2300, 0.30, 70, False), (0.62, 380, 1900, 0.35, 90, True),
          (0.33, 600, 2800, 0.28, 55, False), (0.64, 340, 1700, 0.40, 110, True)]
    for i, p in enumerate(sl):
        name = f"paper_slide_{i+1:02d}"
        if wanted(name):
            emit(name, paper_slide(G(name), *p), "Sheet/card sliding on a wooden desk: soft stick-slip friction texture"
                 + (", tiny landing tap." if p[-1] else "."), mix_hint_db=-18, lead_thresh=-28, fade_in=0.002)
    folds = [
        (0.50, [(0.0, 0.14, 55, 0.8), (0.22, 0.2, 70, 1.0)], 1400, "two bends"),
        (0.72, [(0.0, 0.25, 90, 1.0), (0.3, 0.3, 120, 1.0), (0.55, 0.12, 40, 0.6)], 1700, "crumpling scrap"),
        (0.42, [(0.0, 0.08, 40, 0.7), (0.15, 0.18, 60, 0.9)], 1200, "gentle fold + press"),
    ]
    for i, (d, cl, tone, what) in enumerate(folds):
        name = f"paper_fold_{i+1:02d}"
        if wanted(name):
            emit(name, paper_fold(G(name), d, cl, tone), f"Small paper scrap folded/crinkled ({what}): granular crackle + friction swish.",
                 mix_hint_db=-18)
    for i, (d, ns, fa) in enumerate([(1.15, 3, 1500), (1.35, 4, 1200)]):
        name = f"paper_flutter_{i+1:02d}"
        if wanted(name):
            emit(name, paper_flutter(G(name), d, ns, fa), f"{ns} sheets fluttering through the air and landing softly on wood.",
                 mix_hint_db=-17, lead_thresh=-28, fade_in=0.002)


def gen_pen():
    name = "pen_write_loop"
    if not wanted(name):
        return
    g = G(name)
    N = S.n_of(6.0)
    buf = np.zeros(N)
    t = 0.1
    while t < 5.55:
        for _ in range(g.integers(3, 7)):  # strokes of one word
            d = g.uniform(0.07, 0.17)
            m = S.n_of(d)
            fcen = g.uniform(800, 1700)
            s = S.bp(S.pink(m + 400, g), fcen * 0.5, fcen * 1.6, 2)[200:200 + m]
            s = unit(s)
            grain = np.clip(1 + 0.5 * unit(S.bp(S.white(m, g), 40, 160, 2)), 0, None)
            env = S.bell(m, g.uniform(0.3, 0.5), 0.9) * S.rise(m, 0.008)
            s = s * grain * env * g.uniform(0.45, 1.0)
            S.add_at(buf, s, S.n_of(t))
            t += d + g.uniform(0.012, 0.03)
            if t > 5.55:
                break
        S.add_at(buf, burst(g, S.n_of(0.04), [(100, -20), (500, 0), (1200, -6), (2500, -40)], 0.002, 0.008) * 0.25,
                 S.n_of(t - 0.01))
        t += g.uniform(0.14, 0.38)
    x = S.circ_conv(buf, S.ir_preset("cabin")) * 0.5 + S.to_stereo(buf) * 0.9
    # circular low-pass: zero-phase magnitude shaping keeps the loop seam intact
    X = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(N, 1 / SR)
    H = 1 / (1 + (f / 3000) ** 6)
    H *= (f / 250) ** 2 / (1 + (f / 250) ** 2)
    x = np.fft.irfft(X * H[:, None], N, axis=0)
    emit(name, x, "6 s pencil/pen writing on paper: soft scratchy strokes grouped in words with natural gaps; loops seamlessly.",
         kind="loop", mix_hint_db=-4)


def gen_stamp_redact():
    name = "stamp_01"
    if wanted(name):
        g = G(name)
        n = S.n_of(0.6)
        body = S.modal([95, 185, 370, 640], [1.0, 0.5, 0.22, 0.08], [0.14, 0.09, 0.06, 0.04], n, glide=0.12,
                       glide_tau=0.01, attack=0.0009)
        squish = burst(g, n, [(60, -20), (250, -2), (700, 0), (1400, -6), (2600, -30), (5000, -70)], 0.0012, 0.012, dur=0.1)
        paper = burst(g, n, [(300, -20), (900, 0), (1800, -3), (3000, -18), (5000, -60)], 0.0015, 0.008, dur=0.05)
        x = body + 0.45 * squish + 0.18 * paper
        x += at(S.modal([140], [0.2], [0.06], n, attack=0.002), 0.045, n)
        x = S.lp(S.sat(x, 1.2), 4200, 4)
        emit(name, S.reverb(x, "wood_room", wet=0.30, tail=0.2), "Rubber stamp thud on paper over a wooden desk: low body, rubber squish, soft paper pat.",
             mix_hint_db=-10)
    cfg = [(0.23, 1200, 2600, 100, 0.50), (0.27, 900, 2300, 140, 0.45), (0.31, 1100, 2900, 80, 0.55)]
    for i, (d, f0, f1, gh, rel) in enumerate(cfg):
        name = f"redact_swipe_{i+1:02d}"
        if not wanted(name):
            continue
        g = G(name)
        n = S.n_of(d)
        t = S.tvec(n)
        fc = S.geom_sweep(f0, f1, n)
        y = unit(S.tv_biquad(S.pink(n, g), "bp", fc, 0.8))
        grain = np.clip(1 + 0.35 * unit(S.bp(S.white(n, g), gh * 0.5, gh * 1.7, 2)), 0, None)
        env = (1 - np.exp(-t / 0.014)) * np.cos(0.5 * np.pi * np.clip((np.linspace(0, 1, n) - rel) / (1 - rel), 0, 1)) ** 2
        low = unit(S.lp(S.pink(n, g), 420, 2)) * 0.35
        x = (y + low) * grain * env
        lift = burst(g, n, [(300, -20), (1200, 0), (2200, -8), (3500, -40)], 0.001, 0.006, dur=0.03)
        x += at(lift, d - 0.035, n) * 0.35
        x = S.lp(x, 3300, 4)
        emit(name, S.reverb(x, "wood_room", wet=0.15, tail=0.08, dry_fade=0.03), "Felt-marker swipe 'fsst' (soft onset, rising band, grainy felt texture, tiny lift tick).",
             mix_hint_db=-16)


# ============================================================================ OBJECTS
STEEL_R = np.array([1.0, 1.59, 2.14, 2.30, 2.65, 2.92, 3.50, 4.06, 5.15])
STEEL_A = np.array([1.0, .8, .6, .5, .45, .4, .28, .22, .12])
STEEL_T = np.array([.45, .38, .32, .30, .26, .22, .18, .14, .10])


def gen_lids():
    for i, f0 in enumerate([410, 345]):
        name = f"metal_lid_{i+1:02d}"
        if not wanted(name):
            continue
        g = G(name)
        n = S.n_of(1.2)
        jit = g.uniform(0.985, 1.015, len(STEEL_R))

        def ring(v, fm=1.0):
            return S.modal(f0 * fm * STEEL_R * jit, STEEL_A * v, STEEL_T, n, attack=0.0008)

        def churn(v):
            return S.modal([106, 162], [0.9 * v, 0.35 * v], [0.20, 0.13], n, attack=0.0012)

        click = burst(g, n, [(200, -20), (900, 0), (2000, -3), (3500, -25), (6000, -60)], 0.001, 0.0035, dur=0.03)
        if i == 0:  # set down with two settling re-contacts
            x = ring(1.0) * 0.6 + churn(1.0) + 0.35 * click
            for t0, v, fm in [(0.038, 0.35, 1.01), (0.071, 0.16, 0.99)]:
                x += at(ring(v, fm)[: n] * 0.6 + churn(v) + 0.3 * v * click, t0, n)
        else:  # slides on, then seats
            sc = S.pad_to(unit(S.bp(S.pink(S.n_of(0.1), g), 500, 2400, 2)) * S.bell(S.n_of(0.1), 0.6), n) * 0.16
            x = sc + at(ring(0.8) * 0.6 + churn(0.9) + 0.3 * click, 0.10, n)
            x += at(ring(0.25, 1.02) * 0.6 + churn(0.3), 0.19, n)
        x = S.lp(S.sat(x, 1.15), 5000, 4)
        emit(name, S.reverb(x, "wood_room", wet=0.30, tail=0.3),
             f"Steel milk-churn lid ({f0} Hz plate modes, damped deep ring + hollow churn body) "
             + ("set down with two soft re-contacts." if i == 0 else "sliding on and seating."), mix_hint_db=-11)


def dirt(g, variant):
    """Soil: dull continuous granular bed + many overlapping low-passed crumbs + a few soft clods."""
    dur = [1.0, 0.7, 1.05][variant]
    n = S.n_of(dur)
    t = S.tvec(n)
    bed_shape = [(50, -24), (160, 0), (420, -2), (900, -10), (1800, -26), (3200, -50)]
    flick = np.clip(1 + 0.5 * unit(S.bp(S.white(n, g), 15, 70, 2)), 0.1, None)

    def dens(t0, tau):
        return np.where(t > t0, np.exp(-np.maximum(t - t0, 0) / tau), 0.0) * S.rise(n, 0.02)

    x = np.zeros(n)
    if variant == 0:  # scoop then pour
        sc = unit(S.lp(S.pink(S.n_of(0.2), g), 800, 2)) * S.bell(S.n_of(0.2), 0.4, 1.2) * 0.5
        x += S.pad_to(sc, n)
        t0, tau, r0, clods = 0.15, 0.40, 1100, [(0.22, 0.25), (0.37, 0.18)]
    elif variant == 1:  # shovelful thrown onto the ground
        t0, tau, r0, clods = 0.06, 0.22, 1300, [(0.06, 1.0), (0.13, 0.28)]
    else:  # big dump with two clumps
        t0, tau, r0, clods = 0.05, 0.50, 1000, [(0.12, 1.0), (0.45, 0.6), (0.7, 0.25)]
    bed = unit(S.shaped_noise(n, bed_shape, g)) * dens(t0, tau * 1.1) * flick * 0.55
    ts = poisson_times(g, t0, dur - 0.03, lambda tt: r0 * np.exp(-(tt - t0) / tau))
    crumbs = S.grains(n, ts, g.gamma(3.0, 0.12, len(ts)), g, dur=(0.003, 0.009), lp_hz=(180, 800))
    x += bed + crumbs * 0.8
    for tc, v in clods:
        f = g.uniform(78, 130)
        clump = S.modal([f, f * 1.7], [0.9 * v, 0.35 * v], [0.13, 0.08], n, attack=0.003)
        clump += burst(g, n, [(40, -20), (140, 0), (450, -6), (1000, -30)], 0.004, 0.03, dur=0.12) * 0.55 * v
        x += at(clump, tc, n) * 0.8
    x = S.lp(S.fade(x, 0, 0.2), 2600, 4)
    return S.reverb(x, "wood_room", wet=0.14, tail=0.15)


def gen_dirt():
    desc = ["Soil scooped by a shovel and poured: scoop friction then decaying granular fall.",
            "Shovelful of earth thrown onto the ground: dull thud then scattering crumbs.",
            "Heavy soil dump with two clumps landing and settling grains."]
    for i in range(3):
        name = f"dirt_{i+1:02d}"
        if wanted(name):
            emit(name, dirt(G(name), i), desc[i], mix_hint_db=-14)


def footstep(g, f_heel, vel, toe_gap, hall_wet):
    n = S.n_of(0.42)
    heel = S.modal([f_heel, f_heel * 1.9, f_heel * 0.55], [1.0, 0.35, 0.5], [0.06, 0.04, 0.09], n, glide=0.08,
                   glide_tau=0.01, attack=0.0009)
    click = burst(g, n, [(300, -20), (1200, 0), (2200, -4), (3200, -24), (6000, -60)], 0.0008, 0.003, dur=0.03)
    leather = burst(g, n, [(60, -20), (250, -2), (700, 0), (1400, -10), (3000, -40)], 0.0012, 0.012, dur=0.08)
    hl = heel + 0.28 * click + 0.55 * leather
    tf = f_heel * 1.3
    toe = S.modal([tf, tf * 1.7], [0.6, 0.25], [0.04, 0.03], n, attack=0.001)
    toe += burst(g, n, [(200, -20), (800, 0), (1600, -8), (3000, -40)], 0.001, 0.008, dur=0.05) * 0.5
    x = (hl + at(toe, toe_gap, n) * 0.34) * vel
    x = S.lp(S.sat(x, 1.2), 3800, 4)
    return S.reverb(x, "hall", wet=hall_wet, tail=1.5)


def gen_steps():
    cfg = [(150, 1.0, 0.105, 0.42), (178, 0.85, 0.095, 0.40), (132, 0.95, 0.115, 0.46), (165, 0.80, 0.100, 0.38)]
    for i, (f, v, tg, w) in enumerate(cfg):
        name = f"footstep_{i+1:02d}"
        if wanted(name):
            emit(name, footstep(G(name), f, v, tg, w), "Leather shoe step (heel strike then toe roll) on stone/wood in a reverberant hall.",
                 gain_hint_db=20 * np.log10(v), mix_hint_db=-14)


def gen_door():
    name = "door_heavy_01"
    if not wanted(name):
        return
    g = G(name)
    n = S.n_of(2.6)
    lever = S.modal([1250, 2050, 3000], [1.0, 0.5, 0.25], [0.020, 0.012, 0.008], n, attack=0.0006)
    lever += burst(g, n, [(300, -20), (1500, 0), (2800, -6), (4000, -30), (7000, -60)], 0.0007, 0.0035, dur=0.03) * 0.5
    latch = S.modal([880, 1500, 2350], [1.0, 0.5, 0.2], [0.03, 0.015, 0.01], n, attack=0.0006)
    latch += burst(g, n, [(300, -20), (1200, 0), (2400, -6), (4000, -40)], 0.0007, 0.004, dur=0.03) * 0.5
    t = S.tvec(n)
    i0, i1 = S.n_of(0.22), S.n_of(1.35)
    sw_env = np.zeros(n)
    sw_env[i0:i1] = S.bell(i1 - i0, 0.55, 1.3)
    air = S.lp(S.brown(n, g), 260, 2) * sw_env
    wood = S.lp(S.pink(n, g), 700, 2) * sw_env * np.clip(1 + 0.6 * unit(S.bp(S.white(n, g), 12, 45, 2)), 0, None) * 0.08
    thud = S.modal([62, 142, 235], [1.0, 0.5, 0.2], [0.30, 0.15, 0.08], n, attack=0.004) * 0.9
    thud += burst(g, n, [(40, -20), (150, 0), (500, -6), (1200, -30)], 0.003, 0.03, dur=0.12) * 0.5
    x = lever * 1.0 + at(latch, 0.075, n) * 0.85 + air * 0.22 + wood * 0.5 + at(thud, 1.36, n) * 0.9
    x = S.lp(S.dc_block(x, 12), 4200, 4)
    y = S.reverb(x, "hall", wet=0.30, tail=0.6)
    emit(name, y, "Heavy wooden door: handle/latch clicks, low air movement and soft wood friction, soft thud against the stop (no creak).",
         mix_hint_db=-11, tail_fade=0.15)


def gen_teacup():
    name = "teacup_01"
    if not wanted(name):
        return
    g = G(name)
    n = S.n_of(1.0)
    cup = S.modal([1180, 1930, 2860, 4100], [1.0, 0.55, 0.35, 0.12], [0.30, 0.22, 0.15, 0.09], n, attack=0.0005, g=None)
    saucer = S.modal([1520, 2480, 3400], [0.5, 0.3, 0.15], [0.16, 0.10, 0.07], n, attack=0.0005)
    knock = S.modal([410, 640], [0.5, 0.25], [0.03, 0.02], n, attack=0.001)
    clk = burst(g, n, [(300, -20), (1500, 0), (2500, -3), (4000, -18), (6000, -60)], 0.0007, 0.003, dur=0.03)
    x = cup * 0.6 + saucer * 0.5 + knock * 0.7 + 0.2 * clk
    x += at(cup * 0.25 + saucer * 0.2, 0.021, n)  # tiny second contact as it settles
    x = S.lp(x, 5200, 4)
    emit(name, S.reverb(x, "wood_room", wet=0.28, tail=0.3), "Porcelain teacup set onto its saucer: gentle low-passed clink with a short ring and a tiny settling contact.",
         mix_hint_db=-14)


def gen_ticks_markers():
    ticks = [(760, 0.012), (860, 0.010), (970, 0.014), (1090, 0.009)]
    for i, (f, t60) in enumerate(ticks):
        name = f"tick_{i+1:02d}"
        if not wanted(name):
            continue
        g = G(name)
        n = S.n_of(0.18)
        body = S.modal([f, f * 2.3], [1.0, 0.28], [t60 * 3, t60 * 2], n, attack=0.0005)
        tock = S.modal([f * 0.26], [0.5], [0.05], n, attack=0.0012)
        click = burst(g, n, [(300, -20), (1200, 0), (2400, -6), (3600, -30)], 0.0006, 0.0018, dur=0.02)
        x = S.lp(S.sat(body * 0.8 + tock + 0.25 * click, 1.1), 3400, 4)
        emit(name, S.reverb(x, "wood_room", wet=0.2, tail=0.08), f"Soft wooden/mechanical tick (~{f} Hz) for counters/odometers; pitch steps up with the index.",
             mix_hint_db=-20, gain_hint_db=-1.0 * (i % 2))
    for i, f in enumerate([190, 232, 272]):
        name = f"map_marker_{i+1:02d}"
        if not wanted(name):
            continue
        g = G(name)
        n = S.n_of(0.7)
        body = S.modal([f, f * 1.83, f * 0.5], [1.0, 0.35, 0.4], [0.09, 0.05, 0.12], n, glide=0.12, glide_tau=0.02,
                       attack=0.0012)
        click = burst(g, n, [(200, -20), (800, 0), (1600, -4), (2800, -24), (5000, -60)], 0.0012, 0.004, dur=0.03)
        airy = burst(g, n, [(300, -30), (900, -4), (1600, 0), (2800, -8), (4500, -40)], 0.03, 0.09) * 0.10
        airy = S.rise(n, 0.03) * airy
        bounce = at(S.modal([f * 1.05], [0.18], [0.05], n, attack=0.001), 0.062, n)
        x = S.lp(S.sat(body + 0.18 * click + bounce, 1.2) + airy, 4200, 4)
        emit(name, S.reverb(x, "wood_room", wet=0.35, tail=0.3), f"Map marker drop: low wooden tock (~{f} Hz) with a soft rebound and an airy tail.",
             mix_hint_db=-13, gain_hint_db=-0.8 * i)


# ============================================================================ LOOPS / AMBIENCES
def gen_ambiences():
    name = "room_archive"
    if wanted(name):
        g = G(name)
        N = S.n_of(30.0)
        rumble = S.correlated_pair(N, [(14, -60), (30, -10), (60, -2), (120, 0), (250, -6), (500, -17), (1000, -28), (4000, -42), (9000, -64)], g, 0.5)
        rumble *= S.mod_gain(N, 0.12, 2.0, g)[:, None]
        air = S.correlated_pair(N, [(150, -60), (600, -20), (1500, -8), (3000, -4), (5000, -16), (8000, -50)], g, 0.2)
        air *= S.mod_gain(N, 0.18, 3.0, g)[:, None]
        x = rumble + 0.16 * air
        emit(name, x, "30 s dark archive room tone: airy, faint low rumble, no hum tones; loops seamlessly.", kind="loop", mix_hint_db=-3)

    name = "room_london_night"
    if wanted(name):
        g = G(name)
        N = S.n_of(30.0)
        wash = S.correlated_pair(N, [(40, -60), (80, -18), (200, -4), (420, 0), (900, -6), (1800, -18), (4000, -42), (8000, -70)], g, 0.5)
        wash *= S.mod_gain(N, 0.10, 2.5, g)[:, None]
        rum = S.correlated_pair(N, [(25, -40), (50, -4), (90, 0), (180, -6), (400, -18), (900, -40)], g, 0.5)
        rum *= S.mod_gain(N, 0.15, 2.0, g)[:, None]
        wind = S.correlated_pair(N, [(60, -60), (200, -14), (500, 0), (1000, -4), (2200, -16), (4500, -45)], g, 0.2)
        wind *= S.mod_gain(N, 0.12, 6.0, g)[:, None] * 0.12
        beds = [S.correlated_pair(N, sh, g, 0.5) for sh in
                ([(80, -40), (180, 0), (320, -8), (700, -30)], [(120, -40), (350, 0), (650, -4), (1200, -30)],
                 [(250, -40), (700, 0), (1300, -4), (2200, -30)])]
        cars = np.zeros(N)
        passes = np.zeros((N, 3))
        for start, d in [(1.5, 5.0), (8.0, 4.0), (13.2, 6.0), (20.0, 4.5), (25.5, 4.0)]:
            m = S.n_of(d)
            e = S.bell(m, 0.5, 1.6)
            u = np.linspace(0, 1, m)
            w3 = np.stack([e * S.smoothstep(u) ** 1.2, e * 0.8, e * (1 - S.smoothstep(u)) ** 1.2], axis=1)
            for k in range(3):
                S.add_at(passes[:, k], w3[:, k], S.n_of(start))
        car = sum(beds[k] * passes[:, k:k + 1] for k in range(3))
        x = wash * 0.6 + rum * 0.9 + wind * 0.5 + car * 0.22
        emit(name, x, "30 s distant London night: far traffic rumble and slow passing-car swells, faint wind; no sirens/horns/voices; loops seamlessly.",
             kind="loop", mix_hint_db=-4)

    name = "wind_soft"
    if wanted(name):
        g = G(name)
        N = S.n_of(20.0)
        lo = S.correlated_pair(N, [(25, -40), (100, 0), (300, -3), (700, -12), (2000, -30), (5000, -60)], g, 0.25)
        lo *= np.stack([S.mod_gain(N, 0.15, 5.0, g), S.mod_gain(N, 0.15, 5.0, g)], axis=1)
        mid = S.correlated_pair(N, [(150, -40), (500, 0), (1000, -4), (2000, -14), (4000, -40), (8000, -70)], g, 0.2)
        mid *= np.stack([S.mod_gain(N, 0.2, 6.0, g), S.mod_gain(N, 0.2, 6.0, g)], axis=1)
        turb = S.mod_gain(N, 3.0, 1.5, g, lo_hz=0.8)[:, None]
        x = (lo + 0.45 * mid) * turb
        emit(name, x, "20 s soft wind: slowly gusting low/mid bands, wide stereo, no whistle; loops seamlessly.", kind="loop", mix_hint_db=-4)

    name = "steam_loop"
    if wanted(name):
        g = G(name)
        N = S.n_of(6.0)
        x = S.correlated_pair(N, [(100, -40), (350, -12), (800, -3), (1300, 0), (2200, -7), (3200, -20), (5000, -46), (8000, -80)], g, 0.3)
        x *= (S.mod_gain(N, 0.5, 1.6, g) * S.mod_gain(N, 40.0, 1.2, g, lo_hz=15))[:, None]
        emit(name, x, "6 s very soft steam/air hiss: low-passed (~4 kHz) pink-ish texture with slow breathing; loops seamlessly.", kind="loop", mix_hint_db=-8)

    name = "route_draw_loop"
    if wanted(name):
        g = G(name)
        N = S.n_of(4.0)
        a = S.correlated_pair(N, [(150, -30), (400, -8), (900, 0), (1800, -6), (3000, -16), (5000, -42), (9000, -70)], g, 0.3)
        b = S.correlated_pair(N, [(200, -30), (700, -4), (1400, 0), (2400, -8), (4000, -28), (7000, -60)], g, 0.3)
        u = np.arange(N) / N
        sweep = (0.5 + 0.5 * np.sin(2 * np.pi * (u * 1 + 0.2)))[:, None]
        grain = np.clip(1 + 0.30 * np.stack([S.periodic_random(N, 90, g, lo_hz=30) for _ in range(2)], axis=1), 0.2, None)
        x = (a * (1 - 0.6 * sweep) + 0.6 * b * sweep) * grain
        emit(name, x, "4 s soft friction/air texture for a line being drawn on a map; slow brightness drift, loops seamlessly.", kind="loop", mix_hint_db=-8)

    name = "train_loop"
    if wanted(name):
        g = G(name)
        N = S.n_of(10.0)
        rumble = S.correlated_pair(N, [(18, -40), (40, -6), (80, 0), (160, -3), (300, -10), (600, -20), (1500, -34), (4000, -55)], g, 0.5)
        rumble *= (S.mod_gain(N, 0.35, 2.2, g) * S.mod_gain(N, 7.0, 1.2, g, lo_hz=2))[:, None]
        roar = S.correlated_pair(N, [(150, -60), (350, -8), (600, 0), (1000, -4), (2000, -18), (4000, -45)], g, 0.4)
        roar *= S.mod_gain(N, 0.4, 2.0, g)[:, None]
        clacks = np.zeros(N)
        period = 10.0 / 11.0
        for k in range(11):
            for j, (off, v) in enumerate([(0.0, 1.0), (0.118, 0.72)]):
                v *= g.uniform(0.85, 1.0)
                m = S.n_of(0.4)
                th = S.modal([g.uniform(64, 74), g.uniform(105, 118), 175], [1.0, 0.6, 0.35], [0.09, 0.07, 0.05], m, attack=0.003)
                th += burst(g, m, [(60, -20), (250, 0), (700, -4), (1500, -20), (3000, -50)], 0.002, 0.008, dur=0.05) * 0.4
                th = S.lp(th, 1300, 4)
                S.add_at(clacks, th, S.n_of(k * period + off), gain=v)
        clack_st = S.circ_conv(clacks, S.ir_preset("cabin")) * 0.9
        rum_rms = np.sqrt(np.mean(rumble ** 2))
        clack_st *= 3.0 * rum_rms / (np.max(np.abs(clack_st)) + 1e-12)
        x = rumble + 0.30 * roar + clack_st
        emit(name, x, "10 s distant train-interior rumble with soft low rail clacks in pairs (11 pairs = 1.1/s); loops seamlessly.",
             kind="loop", mix_hint_db=-4)

    name = "boat_loop"
    if wanted(name):
        g = G(name)
        N = S.n_of(8.0)
        laps = np.zeros((N, 2))
        t = 0.2
        while t < 8.0:
            d = g.uniform(0.7, 1.0)
            m = S.n_of(d)
            fc = g.uniform(280, 700)
            nn = S.bp(S.pink(m + 200, g), fc * 0.5, fc * 2.2, 2)[100:100 + m]
            e = S.rise(m, 0.11) * np.exp(-S.tvec(m) / 0.22)
            lap = S.lp(unit(nn), 2200, 2) * e * g.uniform(0.6, 1.0)
            lap = S.fade(lap, 0, 0.1)
            p = g.uniform(-0.7, 0.7)
            S.add_at(laps, S.pan(lap, p), S.n_of(t))
            t += g.uniform(0.55, 1.0)
        bub = np.zeros(N)
        for tb in g.uniform(0, 8.0, 7):
            m = S.n_of(0.08)
            fb = g.uniform(260, 520)
            tt = S.tvec(m)
            bub_s = np.sin(2 * np.pi * np.cumsum(fb * (1 + 1.2 * tt / 0.08 * 0.5)) / SR) * S.attack_decay(m, 0.004, 0.03)
            S.add_at(bub, bub_s * g.uniform(0.05, 0.1), S.n_of(tb))
        eng = S.correlated_pair(N, [(18, -40), (45, 0), (90, -1), (160, -8), (320, -22), (800, -42), (2000, -60)], g, 0.6)
        eng *= (S.mod_gain(N, 14.0, 4.0, g, lo_hz=3) * S.mod_gain(N, 0.3, 2.5, g))[:, None]
        lap_rms = np.sqrt(np.mean(laps ** 2))
        x = laps / lap_rms * 1.0 + np.stack([bub, bub], axis=1) / lap_rms * 0.6 + eng * 0.55
        x = S.circ_conv(x, S.ir_preset("cabin")) * 0.3 + x
        emit(name, x, "8 s low water lapping on a hull with distant non-tonal engine rumble; loops seamlessly.",
             kind="loop", mix_hint_db=-4)

    name = "clock_tick_loop"
    if wanted(name):
        g = G(name)
        N = S.n_of(4.0)
        buf = np.zeros(N)
        for k in range(4):
            fm = 1.0 if k % 2 == 0 else 0.86
            m = S.n_of(0.4)
            tk = S.modal([780 * fm, 1450 * fm], [1.0, 0.35], [0.05, 0.03], m, attack=0.0008)
            tk += S.modal([190 * fm, 320 * fm], [1.2, 0.5], [0.14, 0.08], m, attack=0.0015)
            tk += burst(g, m, [(300, -20), (1200, 0), (2400, -6), (3500, -30)], 0.0008, 0.002, dur=0.03) * 0.25
            tk = S.lp(S.sat(tk, 1.15), 3500, 4)
            S.add_at(buf, tk, S.n_of(float(k)), gain=g.uniform(0.9, 1.0))
        x = S.circ_conv(buf, S.ir_preset("wood_room")) * 0.5 + S.to_stereo(buf)
        emit(name, x, "4 s soft deep clock tick/tock, 1 per second; loops seamlessly (tails wrap).", kind="loop", mix_hint_db=-8)


def gen_final():
    name = "final_hit_01"
    if not wanted(name):
        return
    g = G(name)
    n = S.n_of(4.0)
    t = S.tvec(n)
    env = S.rise(n, 0.008)
    sub = S.glide_sine(40, n, 1.55, 0.18) * env * np.exp(-t / 0.85) * 0.75
    h2 = S.glide_sine(80, n, 1.55, 0.18) * env * np.exp(-t / 0.50) * 0.40
    h3 = S.glide_sine(120, n, 1.55, 0.18) * env * np.exp(-t / 0.28) * 0.16
    thump = S.glide_sine(66, n, 1.45, 0.03) * S.attack_decay(n, 0.004, 0.10) * 1.25
    pop = S.pad_to(pop_dry(g, 160, 0.005, 0.30, 1.3, 0.035, 0.1), n) * 0.45
    air = S.lp(S.brown(n, g), 260, 2) * S.rise(n, 0.12) * np.exp(-t / 1.0) * 0.14
    x = S.lp(S.dc_block(sub + h2 + h3 + thump + pop + air, 10), 2500, 4)
    bloom = S.lp(S.pink(n, g), 700, 2) * S.attack_decay(n, 0.01, 0.12) * 0.25  # mid-low excitation for the tail
    y = S.to_stereo(x)
    send = S.to_stereo(x * 0.5 + bloom)
    tail_wet = S.convolve(S.hp(S.lp(send, 1200, 2), 90, 2), S.ir_preset("dark_space"))[:n]
    y = y + 0.6 * tail_wet
    y = S.fade(y, 0, 0.9)
    emit(name, y, "Deep final title hit: 40 Hz sub with harmonics, soft low thump + creamy pop, long dark reverb tail.",
         mix_hint_db=-8, tail_fade=0.9, peak_mode="rms", tail_thresh=-300)


# ============================================================================ plots
def make_plots():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy import signal
    import soundfile as sf
    vd = pathlib.Path("/tmp/verify")
    vd.mkdir(exist_ok=True)
    groups = {
        "keys": ["key_thock_01", "key_thock_05", "key_thock_09", "key_space_01", "key_enter_01", "key_thock_12"],
        "pops": ["text_pop_01", "text_pop_04", "text_pop_05", "text_soft_01", "text_soft_04", "emph_thump_01"],
        "boom": ["emph_thump_02", "sub_boom_01", "sub_boom_03", "final_hit_01", "whoosh_deep_01", "riser_air_01"],
        "air": ["whoosh_soft_01", "whoosh_soft_02", "whoosh_deep_02", "reverse_swell_01", "reverse_swell_02", "light_sweep_01"],
        "paper": ["paper_slide_01", "paper_slide_02", "paper_fold_02", "paper_flutter_01", "stamp_01", "redact_swipe_01"],
        "objects": ["metal_lid_01", "metal_lid_02", "dirt_01", "dirt_03", "footstep_01", "door_heavy_01"],
        "small": ["teacup_01", "tick_01", "tick_04", "map_marker_01", "map_marker_03", "light_sweep_02"],
        "loops_a": ["pen_write_loop", "route_draw_loop", "steam_loop", "clock_tick_loop", "train_loop", "boat_loop"],
        "loops_b": ["room_archive", "room_london_night", "wind_soft"],
    }
    for gname, names in groups.items():
        names = [n for n in names if (OUT / f"{n}.wav").exists()]
        if not names:
            continue
        rows = (len(names) + 1) // 2
        fig = plt.figure(figsize=(15, 3.4 * rows))
        gs = fig.add_gridspec(rows * 2, 2, height_ratios=[1, 2.6] * rows, hspace=0.45)
        for i, nm in enumerate(names):
            x, sr = sf.read(OUT / f"{nm}.wav")
            m = x.mean(axis=1)
            r, c = divmod(i, 2)
            axw = fig.add_subplot(gs[2 * r, c])
            ax = fig.add_subplot(gs[2 * r + 1, c])
            tt = np.arange(len(m)) / sr
            axw.plot(tt, x[:, 0], lw=0.4, color="#2b6cb0")
            axw.plot(tt, x[:, 1], lw=0.4, color="#c05621", alpha=0.6)
            axw.set_xlim(0, tt[-1])
            axw.set_ylim(-1, 1)
            ix = INDEX.get(nm) or json.loads((OUT / "index.json").read_text())["sounds"].get(nm, {})
            axw.set_title(f"{nm}  {tt[-1]:.2f}s  peak {ix.get('peak_dbfs')} dBFS  {ix.get('lufs')} LUFS  HF>8k {ix.get('hf_above_8k_db')} dB",
                          fontsize=9)
            nper = 1024 if tt[-1] < 2 else 4096
            f, t2, Sxx = signal.spectrogram(m, sr, nperseg=nper, noverlap=int(nper * 0.9), scaling="spectrum")
            Sdb = 10 * np.log10(Sxx[1:] + 1e-14)
            mx = Sdb.max()
            ax.pcolormesh(t2, f[1:], Sdb, vmin=mx - 80, vmax=mx, shading="auto", cmap="magma", rasterized=True)
            ax.set_yscale("log")
            ax.set_ylim(20, 20000)
            ax.axhline(8000, color="cyan", lw=0.6, ls="--")
            ax.set_xlabel("s")
        fig.savefig(vd / f"sfx_{gname}.png", dpi=80, bbox_inches="tight")
        plt.close(fig)
        print("plot", vd / f"sfx_{gname}.png")


# ============================================================================ QA
def qa():
    """Re-read the written files and check format, levels, onsets, HF energy, clicks and loop seams."""
    import soundfile as sf
    from scipy.ndimage import uniform_filter1d
    idx = json.loads((OUT / "index.json").read_text())["sounds"]
    bad = []
    for k, v in idx.items():
        info = sf.info(OUT / v["file"])
        x, sr = sf.read(OUT / v["file"], dtype="float64")
        if (sr, x.shape[1], info.subtype) != (48000, 2, "FLOAT") or not np.isfinite(x).all():
            bad.append((k, "format"))
        if v["kind"] != "loop" and abs(S.peak_db(x) + 3) > 0.05:
            bad.append((k, f"peak {S.peak_db(x):.2f}"))
        if v["kind"] == "loop" and abs(v["lufs"] + 30) > 0.5 and S.peak_db(x) < -3.05:
            bad.append((k, f"lufs {v['lufs']}"))
        if v["kind"] == "oneshot" and v["onset_time"] > 0.005:
            bad.append((k, f"onset {v['onset_time']*1000:.1f} ms"))
        if v["hf_above_8k_db"] > -35:
            bad.append((k, f"HF>8k {v['hf_above_8k_db']} dB"))
        if v["kind"] != "loop" and (abs(x[0]).max() > 1e-3 or abs(x[-1]).max() > 1e-3):
            bad.append((k, "non-zero first/last sample"))
        m = x.mean(axis=1)
        if v["loop"]:
            if v["seam_jump_vs_p99_step"] > 1.0:
                bad.append((k, f"seam {v['seam_jump_vs_p99_step']}"))
            m = np.concatenate([m[-4800:], m, m[:4800]])
        d2 = np.abs(np.diff(m, 2))
        r = np.where(d2 > 1e-4 * d2.max(), d2 / (uniform_filter1d(d2, 481) + 1e-7), 0)
        if not v["loop"]:
            r[: int(0.03 * sr)] = 0
        if r.max() > 25:
            bad.append((k, f"click ratio {r.max():.0f} at {np.argmax(r)/sr:.3f}s"))
    print(f"QA over {len(idx)} files: " + ("all checks passed" if not bad else f"{len(bad)} issue(s)"))
    for b in bad:
        print("  ", *b)
    return bad


# ============================================================================ main
def main():
    global ONLY
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="name prefixes to render")
    ap.add_argument("--plots", action="store_true", help="write spectrogram sheets to /tmp/verify/sfx_*.png")
    ap.add_argument("--plots-only", action="store_true")
    ap.add_argument("--qa", action="store_true", help="re-read written files and run format/level/click/loop checks")
    args = ap.parse_args()
    ONLY = args.only
    OUT.mkdir(parents=True, exist_ok=True)
    if args.plots_only:
        make_plots()
        return
    if args.qa:
        sys.exit(1 if qa() else 0)
    t0 = time.time()
    old = {}
    idx_path = OUT / "index.json"
    if ONLY and idx_path.exists():
        old = json.loads(idx_path.read_text()).get("sounds", {})
    for fn in (gen_keys, gen_pops, gen_thumps_booms, gen_whooshes, gen_risers, gen_sheen, gen_paper, gen_pen,
               gen_stamp_redact, gen_lids, gen_dirt, gen_steps, gen_door, gen_teacup, gen_ticks_markers,
               gen_ambiences, gen_final):
        t1 = time.time()
        fn()
        print(f"{fn.__name__:20s} {time.time()-t1:5.1f}s  (total {INDEX and len(INDEX)} sounds)")
    merged = {**old, **INDEX}
    ordered = {k: merged[k] for k in sorted(merged)}
    idx_path.write_text(json.dumps(dict(
        sample_rate=SR, channels=2, format="WAV float32",
        notes=dict(
            peak_time="seconds from file start of the moment to align with the visual hit (sample peak for one-shots; maximum of a 50-100 ms RMS envelope for booms, whooshes, risers, swells; null for loops)",
            onset_time="first moment the signal exceeds -40 dB re its peak (one-shots start within 5 ms)",
            gain_hint_db="natural level of this variation relative to its family (all one-shots are peak-normalised to -3 dBFS; apply this to keep natural variation)",
            mix_hint_db="suggested starting playback gain under a voice-over mix",
            loops="exactly periodic buffers: play with sample-accurate looping",
        ),
        sounds=ordered), indent=1))
    print(f"wrote {len(INDEX)} files, index has {len(ordered)} entries in {time.time()-t0:.1f}s")
    if args.plots:
        make_plots()
    qa()


if __name__ == "__main__":
    main()
