#!/usr/bin/env bash
# Final assembly: frame-locked sound mix + mux with the rendered picture -> output/the_mitrokhin_archive.mp4
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
[ -f build/video.mp4 ] || { echo "render first: $PY render.py all 2"; exit 1; }
[ "${SKIP_MIX:-0}" = "1" ] && [ -f audio/mix.wav ] || $PY tools/mix_audio.py
mkdir -p output
# delivery encode: grain-preserving x264, capped bitrate for social platforms
ffmpeg -v error -y -i build/video.mp4 -i audio/mix.wav -map 0:v:0 -map 1:a:0 \
  -c:v libx264 -preset slow -tune grain -crf 18 -maxrate 24M -bufsize 48M -profile:v high -level 4.2 \
  -pix_fmt yuv420p -color_primaries bt709 -color_trc bt709 -colorspace bt709 \
  -c:a aac -b:a 320k -ar 48000 -movflags +faststart -shortest \
  -metadata title="The Mitrokhin Archive" -metadata comment="Illustrative reconstruction. Sources in docs/research.md" \
  output/the_mitrokhin_archive.mp4
ffprobe -v error -show_entries format=duration,bit_rate:stream=codec_name,width,height,r_frame_rate,sample_rate \
  -of compact output/the_mitrokhin_archive.mp4
ffmpeg -v info -i output/the_mitrokhin_archive.mp4 -af loudnorm=print_format=summary -f null - 2>&1 \
  | grep -E "Input Integrated|Input True Peak|Input LRA"
