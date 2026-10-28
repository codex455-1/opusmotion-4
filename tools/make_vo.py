"""Narration generation with Kokoro-82M (bf_emma voice, British G2P).

Step 1 (gen):   python tools/make_vo.py gen L05      -> takes at several speeds in /tmp/tts/takes
Step 2 (pick):  python tools/make_vo.py pick         -> UTMOS-score takes, keep best per line in audio/vo/
Generation runs one line per fresh process: on this CPU torch occasionally emits NaN audio once other
models share the process, so takes are isolated and any non-finite/silent take is rejected and retried.
"""
import json, sys, pathlib, subprocess
import numpy as np, soundfile as sf

ROOT = pathlib.Path(__file__).resolve().parents[1]
TAKES = pathlib.Path("/tmp/tts/takes"); TAKES.mkdir(parents=True, exist_ok=True)
LINES = {l["id"]: l for l in json.loads((ROOT / "audio/narration.json").read_text())}
SPEEDS = (0.94, 0.98, 1.0)

def gen(line_id):
    from kokoro import KPipeline
    pipe = KPipeline(lang_code="b", repo_id="hexgrad/Kokoro-82M")
    voice = pipe.load_voice("bf_emma")
    for sp in SPEEDS:
        for attempt in range(4):
            a = np.concatenate([r.audio.numpy() for r in pipe(LINES[line_id]["text"], voice=voice, speed=sp)])
            if np.isfinite(a).all() and np.abs(a).max() > 0.05:
                sf.write(TAKES / f"{line_id}_{sp}.wav", a, 24000); print(line_id, sp, "ok", len(a) / 24000, flush=True); break
            print(line_id, sp, "rejected non-finite take", flush=True)

def pick():
    import torch, librosa
    mos = torch.hub.load("/tmp/tts/SpeechMOS", "utmos22_strong", source="local", trust_repo=True)
    man = {}
    for lid, ln in LINES.items():
        scored = []
        for sp in SPEEDS:
            f = TAKES / f"{lid}_{sp}.wav"
            if not f.exists(): continue
            a, _ = sf.read(f)
            y = librosa.resample(a.astype(np.float32), orig_sr=24000, target_sr=16000)
            with torch.no_grad(): s = float(mos(torch.from_numpy(y).unsqueeze(0), 16000))
            print(lid, sp, round(s, 3), flush=True)
            scored.append((s, sp, a))
        # pacing matters (film must stay under 70 s): take the fastest take within 0.03 MOS of the best
        top = max(x[0] for x in scored)
        s, sp, a = max((x for x in scored if x[0] >= top - 0.03), key=lambda x: x[1])
        sf.write(ROOT / f"audio/vo/{lid}.wav", a, 24000)
        man[lid] = {"speed": sp, "utmos": round(s, 3), "dur": round(len(a) / 24000, 3), "text": ln["text"]}
    (ROOT / "audio/vo/vo_manifest.json").write_text(json.dumps(man, indent=1))
    print("total speech", round(sum(v["dur"] for v in man.values()), 2))

if __name__ == "__main__":
    if sys.argv[1] == "gen":
        ids = sys.argv[2:] or list(LINES)
        if len(ids) > 1:
            for i in ids: subprocess.run([sys.executable, __file__, "gen", i], check=False)
        else:
            gen(ids[0])
    else:
        pick()
