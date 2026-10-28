# Production notes

## 1. What the references do (and where they stop)

| Reference | Visual language | Storytelling | Limits we pushed past |
|---|---|---|---|
| `igexport-DeOyd3hoMTL` (VC money, 68 s, 9:16) | Cream ground, one purple accent, 3D-ish illustrated props (hourglass of coins, pillars), paper grain | A cut every 2–3 s. Word-by-word captions: a small italic lead line over a bold key line; the newest word lands grey and settles dark | Flat lighting, generic props, music-led sound |
| `igexport-DerOn9PoOcl` (Google orbital compute, 66 s, 9:16) | Purple/cream, globe and satellites, server racks, scales, crate-of-rockets metaphors | Same caption grammar; visual metaphors for numbers; slow push-ins | Mostly hard cuts; maps are stylised rather than real |
| `ssstwitter…` (fintech spot, 34 s, 16:9) | Glossy 3D hero objects, light leaks, depth of field, blur-dissolves, glass UI cards | Product beats with fast motion | Product ad, not explanation |

**What we kept:** the two-tier, word-synced captions (proven legible on a phone), and the 2–4 s visual cadence.
**What we changed:**
- Real geography. The Moscow street grid and MKAD, the Europe/Baltic maps, and the London streets and buildings all come from OpenStreetMap and Natural Earth, not illustrations.
- A true 3D night city built from OSM footprints.
- Cinematic light: practical-motivated pools of light, volumetric shafts, halation, grain.
- Technical cutaways as the recurring explanatory device (bag → shoe → dacha floor) to show the *mechanics* of the operation.
- A sound design made only of synthesised, frame-locked effects.

## 2. Story structure (69.9 s)

| t (s) | Beat | Purpose |
|---|---|---|
| 0–11 | The bag: doorway silhouette → smash-zoom → cutaway reveals typed KGB notes under the salami | Hook (an absurd image that turns out to be literally true) |
| 11–15 | The archivist: personnel card typed in, fingerprint inks on | Who |
| 15–23 | Lubyanka → Yasenevo on the real Moscow map, MKAD lights up ("outside Moscow"), packets stream along a 20 km route | Opportunity |
| 23–29 | Files flip, a day counter runs, Cyrillic handwriting writes itself, the note folds into a shoe section | Mechanism 1: copying and smuggling |
| 29–37 | Dacha section: churns rise, lids lift, notes drop; twelve-year time-lapse (seasons, odometer) | Mechanism 2: hiding; then time and suspense |
| 37–43 | The USSR outline glows red and fractures (1991); trail to the US embassies in Riga and Vilnius, both struck through | Turn: rejection |
| 43–46 | A cup of tea | Human warmth; the British say yes |
| 46–51 | Exfiltration route (train, minibus, boat, then London); a trail of paper follows | Operation |
| 51–57 | 3D night London, Century House glows, an index of redacted names; map to Bexleyheath | Payoff setup |
| 57–65 | The suburban house, the dossier (HOLA, unmasked at 87), the Tube Alloys memo, a red thread to Moscow | Twist |
| 65–70 | The FBI's verdict typed out; title; open since 2014 in Cambridge; sources | Resolution and credibility |

## 3. Design system

- Palette: ink #07090D, charcoal #161A21, paper #EAE2D0, cream #F3ECDD, signal red #D23A2E (KGB and danger), lamp amber #E9A64E (evidence and light), Thames teal #6FA3A8 (London). Each scene has its own grade (`post()` per scene).
- Type: Inter for captions and labels, Instrument Serif Italic for emphasis words, Newsreader for big numerals and the title, IBM Plex Mono and PT Mono for typed documents, Bad Script for the Cyrillic handwriting.
- Motion: expo-out arrivals, cubic in-outs on camera moves, back-easing only for markers and pins. Nothing moves linearly except slow drifts. Every shot has a slow push.
- Transitions: smash-zoom with flash (S1); push-through dives (card, Moscow → desk, map → London, pin → house); light-colour washes as warm/cold bridges (map → tea → map).

## 4. Sound

- **Voice:** Kokoro `bf_emma` with British G2P. UTMOS per line is 4.32–4.44 (human studio speech typically scores about 4.0–4.4). Chain: high-pass 70 Hz, low-shelf +1.8 dB at 170 Hz for body, −1.2 dB at 320 Hz, +1.6 dB presence at 3.4 kHz, split-band de-esser, 2.6:1 smooth compressor, 6% small "cabin" room.
- **Keys:** modal "thock" synthesis (body modes at 170–372 Hz, low-passed click, a release stroke 70–110 ms later, desk resonance). Timing is humanised per character with longer gaps after spaces and punctuation, and the same timing drives both the glyph reveal and the sound.
- **Text:** `text_soft` (a velvety puff) on each caption row and `text_pop` (a rounded low pluck) on emphasis words and titles.
- **Mix:** six SFX buses, sidechain-ducked 5.5 dB under the voice (impacts only 2 dB), a 4×-oversampled look-ahead limiter, −14 LUFS integrated with a −1.2 dBTP ceiling.

## 5. Engineering notes and limitations

- **Hardware:** the whole film renders on 2 CPU cores with no GPU. GLSL runs on llvmpipe; a full render takes about 30 minutes with motion-blur subframes.
- **Voice choice:** Chatterbox (the other top open TTS) produced NaN audio and ran at about 35× real time on this CPU, so Kokoro was chosen. Kokoro also emitted occasional NaN takes once other models shared the process, so each line is generated in a fresh process and non-finite takes are rejected.
- **No listening:** I could not listen to the audio in this environment. Quality was controlled objectively instead: UTMOS for the voice; spectrogram checks for HF energy, clicks and loop seams on every SFX; loudness and true-peak measurements; and a Whisper re-transcription of the final mix to confirm the effects do not mask the narration. A human listening pass is still recommended.
- **Reconstructions:** the portrait is anonymous, and documents and handwriting are illustrative. The end card says so.
