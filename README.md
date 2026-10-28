# TABASCO — 1967

A 68.6-second cinematic reconstruction of **Mission Tabasco**, a little-documented
CIA–Taiwan U-2 operation that placed two seismic sensors in the Lop Nur desert
weeks before China's first full-scale thermonuclear test.

**Deliverable:** `dist/TABASCO_1967.mp4` — 1080 × 1920, 24 fps, H.264, stereo,
−14 LUFS / −1.5 dBTP. No music. Sound design only.

## What is on screen

| Time | Beat |
|---|---|
| 0:00 | Takhli, Thailand, May 1967. A U-2 climbs before dawn. |
| 0:09 | Title. The Black Cats / 35th Squadron. |
| 0:13 | Pilot Chuang Jen-liang, the CIA–Taiwan programme, the U-2. |
| 0:25 | China's coming test; the optical blind spot. |
| 0:32 | The 3,000 km route; two 2 m sensor packages; the drop. |
| 0:41 | The desert waits. |
| 0:47 | 17 June 1967: H-6 release, 3.3 Mt, shockwave. |
| 0:55 | Six weeks later: the signal reaches Taipei. |
| 1:02 | 1974: the programme ends; the desert keeps the rest. |

## Production

- **Picture:** custom deterministic Canvas2D scene engine with a five-pass WebGL2
  film compositor (bloom, halation, chromatic aberration, gate weave, grain,
  vignette, colour grade), rendered frame-by-frame in headless Chrome and encoded
  with FFmpeg. No stock footage, no template, no music.
- **Type:** Bodoni Moda, Inter, IBM Plex Mono, Noto Serif SC (all open fonts).
- **Imagery:** NASA GIBS/Worldview satellite reflectance and night-lights data,
  Natural Earth boundaries, procedurally generated paper, grain, stars and
  contour fields.
- **Voice:** Kokoro-82M neural TTS (af_heart), re-performed through EQ, de-essing,
  compression, saturation and a small room; 16 timed segments.
- **Sound:** procedural synthesis in NumPy/SciPy — layered low-mid keyboard
  thocks, creamy text air, wind, jet pass, parachute cloth, canister impacts,
  seismic pulses, tape transport, radio, and a deep flash/shockwave. All effects
  are original; there is no music cue.

## Rebuild

```bash
python3 -m http.server 8000            # from repo root
node tools/render_all.js 1647          # writes render/frames/f00000.png …
ffmpeg -framerate 24 -start_number 0 -i render/frames/f%05d.png \
  -i audio/out/master.wav -c:v libx264 -preset slow -crf 16 \
  -pix_fmt yuv420p -c:a aac -b:a 320k -shortest dist/TABASCO_1967.mp4
```

The research notes, uncertainty flags and image-generation prompt book are in
`research/`.

## Verification

- 1,647 frames rendered at 1080 × 1920; final encode checked for duration,
  frame count, black-frame intervals and audio sync.
- Final mix transcribed end-to-end with Whisper: all 16 narration beats are
  intelligible over the effects; integrated loudness −14.0 LUFS, true peak
  −1.5 dBTP.
- Facts checked against the sources in `research/SOURCES.md`. Where the public
  record is thin — notably the internal design and transmission chain of the
  two sensors — the film uses restrained visual inference and flags it in the
  notes rather than inventing hardware detail.
