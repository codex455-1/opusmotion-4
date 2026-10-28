"""Render driver.

  python render.py still <t> [out.png]        single frame (for review)
  python render.py sheet <t0> <t1> <n> out    contact sheet of n frames
  python render.py range <f0> <f1> <out.mp4>  frame range -> video segment
  python render.py all [workers]              full film -> build/video.mp4 (no audio)
"""
import os
import sys
import subprocess
import time
import numpy as np
import skia

from engine.core import W, H, FPS
from engine.gfx import surface, snapshot_f32
from engine.gl import Post

_POST = None


def post():
    global _POST
    if _POST is None:
        _POST = Post()
    return _POST


def active(t):
    from scenes import SCENES
    return [s for s in SCENES if s.start - 1e-6 <= t < s.end]


def compose(t):
    from scenes import captions
    surf = surface()
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 1))
    for s in active(t):
        c.save()
        s.draw(c, t)
        c.restore()
    captions.draw_captions(c, t)
    return snapshot_f32(surf)


def post_params(t):
    p = {}
    for s in active(t):
        p.update(s.post(t))
    return p


def frame(t):
    act = active(t)
    n = max([s.mb(t) for s in act] + [1])
    if n <= 1:
        img = compose(t)
    else:
        shutter = 0.5 / FPS  # 180-degree shutter
        acc = None
        for k in range(n):
            tt = t + (k / (n - 1) - 0.5) * shutter
            im = compose(tt)
            acc = im if acc is None else acc + im
        img = acc / n
    return post().run(img, post_params(t), t)


def ffmpeg_writer(out, crf=12):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-tune", "grain", "-crf", str(crf),
           "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", out]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def render_range(f0, f1, out):
    p = ffmpeg_writer(out)
    t_start = time.time()
    for f in range(f0, f1):
        img = frame(f / FPS)
        p.stdin.write(img.tobytes())
        if (f - f0) % 15 == 0:
            el = time.time() - t_start
            done = f - f0 + 1
            print(f"[{out}] frame {f} ({done}/{f1 - f0}) {el / done:.2f}s/f eta {(f1 - f - 1) * el / done / 60:.1f}m",
                  flush=True)
    p.stdin.close()
    p.wait()


def main():
    mode = sys.argv[1]
    if mode == "still":
        from PIL import Image
        t = float(sys.argv[2])
        out = sys.argv[3] if len(sys.argv) > 3 else f"/tmp/verify/still_{t:06.2f}.png"
        t0 = time.time()
        img = frame(t)
        Image.fromarray(img).save(out)
        print(out, f"{time.time() - t0:.2f}s")
    elif mode == "sheet":
        from PIL import Image
        t0, t1, n, out = float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
        cols = min(n, 6)
        rows = (n + cols - 1) // cols
        tw, th = W // 4, H // 4
        sheet = Image.new("RGB", (cols * tw, rows * th))
        for i in range(n):
            t = t0 + (t1 - t0) * i / max(n - 1, 1)
            im = Image.fromarray(frame(t)).resize((tw, th), Image.LANCZOS)
            sheet.paste(im, ((i % cols) * tw, (i // cols) * th))
        sheet.save(out)
        print(out)
    elif mode == "range":
        render_range(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    elif mode == "all":
        from scenes import timeline as TL
        workers = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        n = TL.NFRAMES
        os.makedirs("build/seg", exist_ok=True)
        bounds = [round(n * k / workers) for k in range(workers + 1)]
        procs = []
        for k in range(workers):
            seg = f"build/seg/seg{k}.mp4"
            procs.append(subprocess.Popen([sys.executable, __file__, "range", str(bounds[k]), str(bounds[k + 1]), seg]))
        for p in procs:
            p.wait()
        with open("build/seg/list.txt", "w") as f:
            for k in range(workers):
                f.write(f"file 'seg{k}.mp4'\n")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "build/seg/list.txt",
                        "-c", "copy", "build/video.mp4"], check=True)
        print("build/video.mp4", n, "frames")


if __name__ == "__main__":
    main()
