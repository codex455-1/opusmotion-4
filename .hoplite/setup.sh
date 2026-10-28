#!/usr/bin/env bash
# Restores the render/audio toolchain after a sandbox reset (idempotent).
set -euo pipefail
cd "$(dirname "$0")/.."
export DEBIAN_FRONTEND=noninteractive
if ! ldconfig -p | grep -q 'libEGL.so.1' || ! command -v espeak-ng >/dev/null; then
  apt-get update -qq && apt-get install -y -qq libegl1 libegl-mesa0 libgles2 libgbm1 espeak-ng ffmpeg
fi
if [ ! -x .venv/bin/python ]; then
  uv venv -q .venv --python 3.12
  uv pip install -q --python .venv/bin/python -r requirements.txt
fi
# Optional narration toolchain (only needed to regenerate the voice-over)
if [ "${WITH_TTS:-0}" = "1" ] && [ ! -x .venv-tts/bin/python ]; then
  uv venv -q .venv-tts --python 3.11
  uv pip install -q --python .venv-tts/bin/python torch torchaudio --index-url https://download.pytorch.org/whl/cpu
  uv pip install -q --python .venv-tts/bin/python -r requirements-tts.txt
fi
