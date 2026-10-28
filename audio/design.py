import numpy as np, soundfile as sf, json, os, math
from scipy.signal import butter, sosfilt, lfilter, fftconvolve, resample_poly

SR = 48000
DUR = 68.6
N = int(SR * DUR)
rng = np.random.default_rng(1967)

def tarr(n): return np.arange(n, dtype=np.float64) / SR
def env_exp(n, tau): return np.exp(-tarr(n) / tau)
def noise(n): return rng.standard_normal(n)
def bp(x, lo, hi, order=2):
    lo = max(20, lo); hi = min(SR/2 - 200, hi)
    return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)
def lp(x, f, order=2): return sosfilt(butter(order, f, btype="low", fs=SR, output="sos"), x)
def hp(x, f, order=2): return sosfilt(butter(order, f, btype="high", fs=SR, output="sos"), x)
def peak(x, f, db, q=1.0):
    A = 10 ** (db / 40); w0 = 2 * math.pi * f / SR; al = math.sin(w0) / (2 * q)
    b = [1 + al * A, -2 * math.cos(w0), 1 - al * A]
    a = [1 + al / A, -2 * math.cos(w0), 1 - al / A]
    return lfilter(b, a, x)
def pan(x, p):
    p = max(-1, min(1, p)); a = (p + 1) * math.pi / 4
    return np.stack([x * math.cos(a), x * math.sin(a)], 1)

def add(buf, sig, t, gain=1.0, p=0.0, send=None, send_amt=0.0):
    i = int(round(t * SR))
    if i >= N: return
    if i < 0: sig = sig[-i:]; i = 0
    n = min(len(sig), N - i)
    if n <= 0: return
    s = sig[:n]
    if s.ndim == 1: s = pan(s, p)
    buf[i:i+n] += s * gain
    if send is not None and send_amt:
        send[i:i+n] += s * gain * send_amt

def fade(sig, a=0.005, b=0.02):
    n = len(sig); na = max(1, int(a*SR)); nb = max(1, int(b*SR))
    sig = sig.copy()
    if na < n: sig[:na] *= np.linspace(0, 1, na)[:, None] if sig.ndim == 2 else np.linspace(0, 1, na)
    if nb < n: sig[-nb:] *= np.linspace(1, 0, nb)[:, None] if sig.ndim == 2 else np.linspace(1, 0, nb)
    return sig

# ---------- instruments ----------
def thock(seed=0, f0=105, dur=.30, hard=.35):
    r = np.random.default_rng(seed); n = int(dur * SR); t = tarr(n)
    f = f0 * (0.72 + 0.28 * np.exp(-t * 38))
    ph = 2 * np.pi * np.cumsum(f) / SR
    sub = np.sin(ph) * np.exp(-t * 26) * .62
    body = (np.sin(2*np.pi*218*t + .3) * .22 + np.sin(2*np.pi*331*t) * .1) * np.exp(-t * 48)
    click = bp(r.standard_normal(n), 1400, 6800) * np.exp(-t * 240) * (.32 + hard*.5)
    cream = np.sin(2*np.pi*(520 + 160*np.exp(-t*70))*t) * np.exp(-t*95) * .18
    s = sub + body + click + cream
    s = lp(s, 7200)
    return fade(s, .001, .04) * r.uniform(.75, 1.0)

def text_air(seed=0, dur=.55, f=320):
    r = np.random.default_rng(seed); n = int(dur*SR); t = tarr(n)
    nz = bp(r.standard_normal(n), 260, 2600)
    e = np.sin(np.pi * np.clip(t/dur, 0, 1)) ** 2
    air = nz * e * .16
    low = np.sin(2*np.pi*f*t) * np.exp(-t*8) * .13
    shimmer = bp(r.standard_normal(n), 3400, 9000) * e * .035
    s = air + low + shimmer
    return fade(s, .05, .18)

def impact(seed=0, f0=48, dur=2.2, big=1.0):
    r = np.random.default_rng(seed); n = int(dur*SR); t = tarr(n)
    f = f0 * (0.55 + 0.45*np.exp(-t*7))
    ph = 2*np.pi*np.cumsum(f)/SR
    sub = np.sin(ph) * np.exp(-t*2.2) * .85
    crack = bp(r.standard_normal(n), 300, 2800) * np.exp(-t*55) * .18 * big
    body = np.sin(2*np.pi*(f0*2.7)*t) * np.exp(-t*12) * .10
    s = lp(sub + body, 520) + crack
    return fade(s, .002, .35) * big

def stamp(seed=0):
    r = np.random.default_rng(seed); n = int(.6*SR); t = tarr(n)
    slap = bp(r.standard_normal(n), 240, 2400) * np.exp(-t*70) * .28
    thud = np.sin(2*np.pi*92*t) * np.exp(-t*30) * .35
    return fade(slap + thud, .001, .08)

def shutter(seed=0):
    r = np.random.default_rng(seed); out = np.zeros(int(.35*SR))
    for k, dt in enumerate([0, .055, .11]):
        n = int(.05*SR); t = tarr(n)
        c = bp(r.standard_normal(n), 1800, 9000) * np.exp(-t*300) * (.3 if k < 2 else .2)
        i = int(dt*SR); out[i:i+n] += c[:len(out)-i]
    n2 = int(.2*SR); t2 = tarr(n2)
    out[-n2:] += bp(r.standard_normal(n2), 400, 1500) * np.exp(-t2*18) * .05
    return out

def whoosh(seed=0, dur=1.2, lo=180, hi=2400, rev=False):
    r = np.random.default_rng(seed); n = int(dur*SR); t = tarr(n)
    nz = bp(r.standard_normal(n), lo, hi)
    e = np.linspace(0, 1, n) ** 2 if rev else np.sin(np.pi * np.clip(t/dur, 0, 1)) ** 2
    if rev: e = e[::-1]
    return fade(nz * e * .24, .02, .15)

def ping(seed=0, f=1180, dur=1.5):
    n = int(dur*SR); t = tarr(n)
    s = (np.sin(2*np.pi*f*t) * .26 + np.sin(2*np.pi*f*1.5*t + .4) * .08) * np.exp(-t*4.2)
    return fade(s, .001, .2)

def jet(seed=0, dur=5.0, far=1.0):
    r = np.random.default_rng(seed); n = int(dur*SR); t = tarr(n)
    nz = bp(r.standard_normal(n), 40, 1400)
    e = np.sin(np.pi * np.clip(t/dur, 0, 1)) ** 1.4
    whine = (np.sin(2*np.pi*(420 + 24*np.sin(t*3))*t) * .018 + np.sin(2*np.pi*820*t)*.008) * e
    rumble = np.sin(2*np.pi*(52 - 10*t/dur)*t) * .12 * e
    return fade((nz*.22 + whine + rumble) * far, .2, .8)

def metal(seed=0, dur=.8):
    r = np.random.default_rng(seed); n = int(dur*SR); t = tarr(n)
    hit = bp(r.standard_normal(n), 700, 5200) * np.exp(-t*45) * .35
    ring = (np.sin(2*np.pi*392*t) + .6*np.sin(2*np.pi*587*t) + .3*np.sin(2*np.pi*941*t)) * np.exp(-t*11) * .10
    servo = bp(r.standard_normal(n), 90, 300) * np.exp(-t*7) * .12
    return fade(hit + ring + servo, .001, .1)

def chute(seed=0, dur=1.8):
    r = np.random.default_rng(seed); n = int(dur*SR); t = tarr(n)
    nz = bp(r.standard_normal(n), 180, 2200)
    flutter = .55 + .45*np.sin(2*np.pi*7.5*t + 1)
    e = np.minimum(1, t/.18) * np.exp(-t*1.1)
    return fade(nz * e * flutter * .18, .05, .3)

def radio(seed=0, dur=.5):
    r = np.random.default_rng(seed); n = int(dur*SR); t = tarr(n)
    st = bp(r.standard_normal(n), 900, 6000) * .035
    beep = (np.sin(2*np.pi*1040*t) * .09) * (np.exp(-t*30) + .5*np.exp(-np.maximum(t-.18,0)*30)*(t>.18))
    return fade(st + beep, .005, .05)

def tape_hum(dur):
    n = int(dur*SR); t = tarr(n)
    hum = (np.sin(2*np.pi*60*t)*.03 + np.sin(2*np.pi*120*t)*.012 + np.sin(2*np.pi*180*t)*.005)
    hiss = bp(rng.standard_normal(n), 2400, 9000) * .012
    flutter = .8 + .2*np.sin(2*np.pi*.6*t)
    return (hum + hiss) * flutter

def wind(dur, seed=0, gain=.14):
    r = np.random.default_rng(seed); n = int(dur*SR); t = tarr(n)
    nz = bp(r.standard_normal(n), 70, 1600)
    lfo = .45 + .3*np.sin(2*np.pi*.09*t) + .15*np.sin(2*np.pi*.037*t+1.2)
    return fade(nz * lfo * gain, .5, 1.0)

def seismo_tone(dur, seed=0):
    n = int(dur*SR); t = tarr(n)
    return (np.sin(2*np.pi*44*t) * .2 + np.sin(2*np.pi*58*t) * .08) * (0.5+0.5*np.sin(2*np.pi*.3*t))

# ---------- busses ----------
dry = np.zeros((N, 2)); send = np.zeros((N, 2)); vo = np.zeros((N, 2))

# ambience
room = wind(DUR, 11, .035); add(dry, room, 0, .55, 0, send, .2)
add(dry, wind(DUR, 12, .09), 0, .65, -0.1, send, .3)
add(dry, wind(DUR, 13, .06), 3.2, .5, 0.3, send, .2)
add(dry, tape_hum(DUR), 55.4, .55, 0, send, .15)

# engine pass
add(dry, jet(1, 5.6, .9), 3.4, .36, -.1, send, .45)
add(dry, jet(2, 4.5, .5), 61.8, .35, .25, send, .5)

# typing
for i in range(8):
    s = thock(100+i, 98 + (i%3)*7, .28, .5 if i==7 else .35)
    add(dry, s, .60 + i*.187, .8, -.08 + .02*(i%3), send, .10)
add(dry, text_air(3, .8, 280), 2.30, .55, .15, send, .15)

# title / scene beats
add(dry, impact(4, 44, 2.8, 1.0), 9.36, .72, 0, send, .55)
add(dry, whoosh(5, 1.4, 120, 900), 9.18, .5, 0, send, .3)
add(dry, stamp(6), 13.33, .62, -.12, send, .25)
add(dry, text_air(7, .7, 300), 13.70, .45, .2, send, .12)
add(dry, whoosh(8, 1.5, 300, 3200), 16.95, .33, .1, send, .35)
add(dry, shutter(9), 21.28, .55, .05, send, .25)
add(dry, whoosh(10, 1.2, 160, 1200), 25.12, .38, -.1, send, .4)
add(dry, ping(11, 980, 1.8), 28.28, .42, -.2, send, .55)
add(dry, whoosh(12, 1.8, 220, 2600, True), 32.60, .32, .1, send, .45)

# plan / drop
add(dry, metal(13, 1.0), 38.52, .6, -.2, send, .4)
add(dry, chute(14, 2.0), 39.48, .7, .2, send, .35)
add(dry, impact(15, 38, 1.6, .55), 41.82, .55, .1, send, .45)
add(dry, ping(16, 760, 2.2), 44.52, .28, -.1, send, .5)

# test
for i,tt in enumerate([47.55,49.05,50.55]):
    add(dry, radio(20+i, .35), tt, .5, .25, send, .35)
add(dry, whoosh(23, 2.6, 500, 5000, False), 51.1, .35, 0, send, .5)
add(dry, impact(24, 36, 4.2, 1.25), 53.80, .70, 0, send, .8)
add(dry, whoosh(25, .55, 200, 9000, True), 53.62, .32, 0, send, .6)
add(dry, impact(26, 28, 5.0, .9), 54.12, .52, .1, send, .7)
add(dry, seismo_tone(3.4, 27), 54.0, .55, 0, send, .4)

# signal / coda
add(dry, radio(30, .5), 57.52, .55, -.3, send, .4)
add(dry, ping(31, 1320, 2.4), 59.02, .45, .2, send, .6)
add(dry, impact(32, 52, 2.2, .45), 59.02, .45, 0, send, .5)
add(dry, whoosh(33, 2.0, 180, 1800), 62.05, .35, -.1, send, .5)
add(dry, impact(34, 32, 4.0, .8), 65.55, .7, 0, send, .65)
add(dry, wind(4.5, 35, .12), 64.0, .45, .2, send, .3)

# ---------- voice ----------
segs = json.load(open("vo/timing.json"))
starts = {"s01":.80,"s02":3.52,"s03":6.71,"s04":13.16,"s05":17.09,"s06":21.43,
          "s07":25.10,"s08":28.15,"s09":32.55,"s10":41.13,"s11":44.46,"s12":47.26,
          "s13":52.10,"s14":55.95,"s15":58.58,"s16":62.05}
voice = np.zeros(N)
for s in segs:
    s["start"] = starts[s["id"]]
    a, sr = sf.read(f"vo/{s['id']}.wav", dtype="float64")
    if a.ndim > 1: a = a.mean(1)
    if sr != SR: a = resample_poly(a, SR, sr)
    a = a / (np.max(np.abs(a)) + 1e-9) * .72
    i = int(s["start"] * SR); n = min(len(a), N-i)
    voice[i:i+n] += a[:n]

voice = hp(voice, 78)
voice = peak(voice, 190, -2.2, 1.1)
voice = peak(voice, 3300, 2.4, 1.0)
voice = peak(voice, 6200, -1.2, 1.2)
# de-ess
hi = bp(voice, 5200, 8800)
env = np.abs(hi); env = sosfilt(butter(2, 60, btype="low", fs=SR, output="sos"), env)
red = np.clip((env - .02) / .10, 0, 1) * .55
voice = voice - hi * red
# compression
env = np.abs(voice); env = sosfilt(butter(2, 28, btype="low", fs=SR, output="sos"), env)
env = np.maximum(env, 0)
gain = np.where(env > .09, (.09 / (env + 1e-9)) ** .55, 1.0)
gain = np.clip(gain, .45, 1.6)
voice = voice * gain
voice = np.tanh(voice * 1.45) / np.tanh(1.45)
voice = voice / (np.max(np.abs(voice)) + 1e-9) * .78
vo[:, 0] = voice; vo[:, 1] = voice
send[:, 0] += voice * .035; send[:, 1] += voice * .035

# ---------- reverb ----------
def make_ir(decay=2.4, predelay=.022, seed=9):
    r = np.random.default_rng(seed); n = int(decay * SR); t = tarr(n)
    ir = np.zeros((n, 2))
    for ch in range(2):
        nz = r.standard_normal(n)
        nz = lp(nz, 5200) * np.exp(-t * (3.2 / decay))
        ir[:, ch] = nz
    # early reflections
    for d, g in [(.017,.4),(.029,.3),(.043,.24),(.061,.18),(.083,.13),(.109,.09)]:
        i = int(d*SR)
        for ch in range(2):
            ir[i:i+int(.02*SR), ch] += g * r.standard_normal(int(.02*SR)) * np.exp(-tarr(int(.02*SR)) / .004)
    p = int(predelay*SR); ir = np.vstack([np.zeros((p,2)), ir])
    ir = ir / (np.sqrt(np.sum(ir**2, 0, keepdims=True)) + 1e-9)
    return ir

ir = make_ir(2.6)
wet = np.zeros((N, 2))
for ch in range(2):
    c = fftconvolve(send[:, ch], ir[:, ch])[:N]
    wet[:, ch] = hp(c, 160)
wet = wet / (np.max(np.abs(wet)) + 1e-9) * .30

# ---------- mix ----------
# gentle ducking of beds under voice
ve = np.abs(voice); ve = sosfilt(butter(2, 8, btype="low", fs=SR, output="sos"), ve)
duck = 1 - .52 * np.clip(ve / .07, 0, 1)
tt = np.arange(N) / SR
flash_protect = 1 - .34 * np.exp(-((tt - 54.15) / 1.15) ** 2)
mix = dry * (duck * flash_protect)[:, None] + wet * flash_protect[:, None] + vo

# bus glue + limiting
mix = hp(mix, 24)
env = np.max(np.abs(mix), axis=1)
env = sosfilt(butter(2, 4, btype="low", fs=SR, output="sos"), env)
gain = np.where(env > .32, (.32 / (env + 1e-9)) ** .35, 1.0)
mix *= np.clip(gain, .5, 1.0)[:, None]
mix = np.tanh(mix * 1.15) / np.tanh(1.15)
mix = mix / (np.max(np.abs(mix)) + 1e-9) * .92

os.makedirs("audio/out", exist_ok=True)
sf.write("audio/out/mix_raw.wav", mix, SR, subtype="PCM_24")
sf.write("audio/out/vo_only.wav", vo, SR, subtype="PCM_24")
sf.write("audio/out/sfx_only.wav", (dry + wet) * .9, SR, subtype="PCM_24")

report = {
    "duration": DUR,
    "peak": float(np.max(np.abs(mix))),
    "rms_dbfs": float(20*np.log10(np.sqrt(np.mean(mix**2)) + 1e-12)),
    "vo_rms_dbfs": float(20*np.log10(np.sqrt(np.mean(vo**2)) + 1e-12)),
}
json.dump(report, open("audio/out/report.json", "w"), indent=2)
print(report)
