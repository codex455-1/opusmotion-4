const sceneCanvas = document.getElementById("scene");
const outCanvas = document.getElementById("out");
const sctx = sceneCanvas.getContext("2d", { alpha: false });
const post = new Post(outCanvas);
const TL = window.TIMELINE;
let READY = false;

function loadImage(src) {
  return new Promise((res, rej) => {
    const im = new Image();
    im.onload = () => res(im);
    im.onerror = () => rej(new Error("image " + src));
    im.src = src;
  });
}
async function init() {
  await Promise.all([
    document.fonts.load("500 100px Bodoni"),
    document.fonts.load("400 30px Inter"),
    document.fonts.load("500 30px Inter"),
    document.fonts.load("400 20px PlexMono"),
    document.fonts.load("500 20px PlexMono"),
    document.fonts.load("400 30px NotoSC"),
    document.fonts.load("500 30px NotoSC")
  ]);
  await document.fonts.ready;
  const [stars, paper, desert, lights, contours, t0, t1, t2, t3, t4, t5, t6, t7, t8, t9] = await Promise.all([
    loadImage("../assets/tex/stars.jpg"),
    loadImage("../assets/tex/paper_dark.jpg"),
    loadImage("../assets/img/desert.jpg"),
    loadImage("../assets/img/lights.jpg"),
    loadImage("../assets/tex/contours.png"),
    loadImage("../assets/tex/grain_0.png"), loadImage("../assets/tex/grain_1.png"),
    loadImage("../assets/tex/grain_2.png"), loadImage("../assets/tex/grain_3.png"),
    loadImage("../assets/tex/grain_4.png"), loadImage("../assets/tex/grain_5.png"),
    loadImage("../assets/tex/grain_6.png"), loadImage("../assets/tex/grain_7.png"),
    loadImage("../assets/tex/grain_8.png"), loadImage("../assets/tex/grain_9.png")
  ]);
  window.ASSETS = { stars, paper, desert, lights, contours };
  window.ASIA = window.ASIA || [];
  post.setGrain([t0, t1, t2, t3, t4, t5, t6, t7, t8, t9]);
  const mkMap = (box, alpha, lights, chinaOnly) => {
    const c = document.createElement("canvas"); c.width = W; c.height = H;
    const g = c.getContext("2d");
    g.clearRect(0, 0, W, H);
    drawAsia(g, box, alpha, lights, chinaOnly);
    return c;
  };
  window.CACHE = {
    main: mkMap({ x: 70, y: 470, w: 940, h: 648 }, 1, .8, false),
    signal: mkMap({ x: 120, y: 900, w: 840, h: 580 }, .85, .38, true)
  };
  sctx.textRendering = "geometricPrecision";
  READY = true;
  window.READY = true;
  document.title = "READY";
}
function activeScene(t) {
  for (const s of TL.scenes) if (t >= s.start && t < s.end) return s;
  return TL.scenes[TL.scenes.length - 1];
}
function renderAt(t) {
  const s = activeScene(t);
  sctx.setTransform(1, 0, 0, 1, 0, 0);
  sctx.globalAlpha = 1; sctx.globalCompositeOperation = "source-over"; sctx.filter = "none";
  sctx.fillStyle = "#000"; sctx.fillRect(0, 0, W, H);
  const fn = window.SCENES[s.id];
  if (fn) fn(sctx, t);
  const flash = Math.max(0, 1 - Math.abs(t - 53.84) / .13) * .55;
  const fade = Math.min(1, t / .45, (TL.duration - t) / .5);
  const mood = {
    grain: s.id === "test" ? .06 : .052,
    bloom: s.id === "test" ? .52 : s.id === "open" ? .46 : .38,
    warm: s.id === "test" ? .72 : .5,
    sat: s.id === "cats" ? .82 : .9,
    flash,
    fade: clamp(fade)
  };
  post.render(sceneCanvas, t, mood);
  return true;
}
window.renderAt = renderAt;
window.renderFrame = f => renderAt(f / TL.fps);
init().catch(e => { console.error(e); document.title = "ERR " + e.message; });
