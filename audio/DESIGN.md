# Sound design

The film has no music. Every sound is synthesised from first principles in
`audio/design.py` (NumPy/SciPy), timed to the visual beats in
`engine/timeline.js`.

## Palette

- **Keyboard thock:** three layers — a 90–120 Hz pitched sub with a fast pitch
  fall, a 200–330 Hz wooden body, and a 1.4–6.8 kHz transient softened by a
  7.2 kHz low-pass. Randomised velocity and micro-pitch per key; a small room
  send. The result is deep and creamy rather than clicky.
- **Text air:** band-limited noise swelling under a low sine, with a trace of
  3.4–9 kHz shimmer. Used when a title or dossier line appears.
- **Wind / room:** two decorrelated filtered-noise beds with slow LFOs; the
  room is always present, never a music pad.
- **Jet:** 40–1400 Hz noise, a low rumble and a faint turbine whine, with a
  long swell and tail.
- **Hardware:** metal clunks, servo, parachute cloth flutter, canister impact.
- **Signal:** tape hum and flutter, radio static/beeps, 1.2 kHz sonar ping with
  a long reverb.
- **Flash:** reverse air swell, a 36 Hz sub with pitch fall, a short crack, and
  a 28 Hz rumble tail. The narration is deliberately finished before the
  flash so the line is never buried.

## Mix

- Voice: high-pass 78 Hz, −2.2 dB at 190 Hz, +2.4 dB at 3.3 kHz, de-essed,
  2.5:1 compression, gentle saturation, small room.
- Effects are side-chain ducked under the voice; an additional 1.15 s-wide
  protection curve surrounds the detonation.
- Master: 24 Hz high-pass, bus compression, soft limit, two-pass loudnorm to
  −14.0 LUFS integrated and −1.5 dBTP.
