"""Generate narration line-by-line with Kokoro (bf_emma, British G2P).

Each line is rendered several times at slightly different speeds; takes with NaNs or
silence are rejected (this CPU occasionally produces NaN frames) and the take with the
best UTMOS naturalness score is kept. Writes audio/vo/<id>.wav (24 kHz) + vo_manifest.json.
"""
import json, sys, pathlib, numpy as np, soundfile as sf, torch, librosa
from kokoro import KPipeline

ROOT = pathlib.Path(__file__).resolve().parents[1]
lines = json.loads((ROOT / "audio/narration.json").read_text())
only = set(sys.argv[1:])
pipe = KPipeline(lang_code="b", repo_id="hexgrad/Kokoro-82M")
voice = pipe.load_voice("bf_emma")
mos = torch.hub.load("/tmp/tts/SpeechMOS", "utmos22_strong", source="local", trust_repo=True)

def utmos(a):
    y = librosa.resample(a, orig_sr=24000, target_sr=16000)
    with torch.no_grad():
        return float(mos(torch.from_numpy(y).unsqueeze(0), 16000))

man_path = ROOT / "audio/vo/vo_manifest.json"
manifest = json.loads(man_path.read_text()) if man_path.exists() else {}
for ln in lines:
    if only and ln["id"] not in only:
        continue
    best = None
    for speed in (0.94, 0.98, 1.0):
        for attempt in range(3):
            a = np.concatenate([r.audio.numpy() for r in pipe(ln["text"], voice=voice, speed=speed)])
            if np.isfinite(a).all() and np.abs(a).max() > 0.05:
                break
        else:
            continue
        s = utmos(a)
        print(f'{ln["id"]} speed={speed} dur={len(a)/24000:.2f}s utmos={s:.3f}', flush=True)
        if best is None or s > best[0]:
            best = (s, speed, a)
    s, speed, a = best
    sf.write(ROOT / f'audio/vo/{ln["id"]}.wav', a, 24000)
    manifest[ln["id"]] = {"speed": speed, "utmos": round(s, 3), "dur": round(len(a) / 24000, 3), "text": ln["text"]}
    man_path.write_text(json.dumps(manifest, indent=1))
print("total", sum(v["dur"] for v in manifest.values()))
