const W = 1080, H = 1920;
const C = {
  ink: "#07090a",
  ink2: "#0c1112",
  bone: "#e9dfc8",
  boneDim: "#b9ae97",
  sand: "#c9a86a",
  amber: "#e0a83c",
  rust: "#b4472f",
  jade: "#6f8f7d",
  red: "#8f2f26",
  white: "#f6efe0"
};
const F = {
  display: "Bodoni",
  sans: "Inter",
  mono: "PlexMono",
  cn: "NotoSC"
};
const clamp = (v, a = 0, b = 1) => v < a ? a : v > b ? b : v;
const lerp = (a, b, t) => a + (b - a) * t;
const inv = (a, b, v) => clamp((v - a) / (b - a));
const smooth = t => (t = clamp(t), t * t * (3 - 2 * t));
const easeOut = t => 1 - Math.pow(1 - clamp(t), 3);
const easeOut4 = t => 1 - Math.pow(1 - clamp(t), 4);
const easeIn = t => Math.pow(clamp(t), 3);
const easeInOut = t => (t = clamp(t), t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const easeOutExpo = t => t >= 1 ? 1 : 1 - Math.pow(2, -10 * clamp(t));
const easeOutBack = t => { t = clamp(t); const c = 1.70158; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2); };
const hash = n => { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); };
const noise = x => { const i = Math.floor(x), f = x - i; return lerp(hash(i), hash(i + 1), smooth(f)); };
const rgba = (hex, a) => {
  const h = hex.replace("#", "");
  const n = parseInt(h.length === 3 ? h.split("").map(c => c + c).join("") : h, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
};
const withA = (hex, a) => rgba(hex, a);

function trackedWidth(ctx, str, tracking) {
  let w = 0;
  for (const ch of str) w += ctx.measureText(ch).width + tracking;
  return Math.max(0, w - tracking);
}
function drawTracked(ctx, str, x, y, tracking) {
  let cx = x;
  for (const ch of str) {
    ctx.fillText(ch, cx, y);
    cx += ctx.measureText(ch).width + tracking;
  }
}
function wrapLines(ctx, str, maxW) {
  const words = str.split(" ");
  const lines = [];
  let line = "";
  for (const w of words) {
    const t = line ? line + " " + w : w;
    if (ctx.measureText(t).width > maxW && line) { lines.push(line); line = w; }
    else line = t;
  }
  if (line) lines.push(line);
  return lines;
}
function text(ctx, str, x, y, o = {}) {
  let size = o.size || 32;
  const fam = o.family || F.sans;
  if (fam === F.mono && size < 15) size = 15;
  const weight = o.weight || 400;
  const tracking = o.tracking || 0;
  const lh = o.lineHeight || 1.18;
  const alpha = o.alpha == null ? 1 : o.alpha;
  ctx.save();
  ctx.font = `${weight} ${size}px ${fam}`;
  ctx.fillStyle = o.color || C.bone;
  ctx.textBaseline = o.baseline || "alphabetic";
  ctx.globalAlpha *= alpha;
  if (o.filter) ctx.filter = o.filter;
  if (o.shadow) { ctx.shadowColor = o.shadow; ctx.shadowBlur = o.shadowBlur || 24; }
  const lines = o.maxWidth ? wrapLines(ctx, str, o.maxWidth) : str.split("\n");
  lines.forEach((line, i) => {
    const w = trackedWidth(ctx, line, tracking);
    let sx = x;
    if (o.align === "center") sx = x - w / 2;
    else if (o.align === "right") sx = x - w;
    drawTracked(ctx, line, sx, y + i * size * lh, tracking);
  });
  ctx.restore();
}
function textW(ctx, str, size, family = F.sans, weight = 400, tracking = 0) {
  ctx.save(); ctx.font = `${weight} ${size}px ${family}`;
  const w = trackedWidth(ctx, str, tracking); ctx.restore(); return w;
}
function typed(ctx, str, x, y, p, o = {}) {
  const n = Math.floor(clamp(p) * str.length);
  const s = str.slice(0, n);
  text(ctx, s, x, y, o);
  if (o.cursor !== false && n < str.length && Math.floor(p * 40) % 2 === 0) {
    const size = o.size || 32;
    ctx.save(); ctx.font = `${o.weight || 400} ${size}px ${o.family || F.mono}`;
    const cw = o.tracking ? trackedWidth(ctx, s, o.tracking) : ctx.measureText(s).width;
    ctx.fillStyle = o.cursorColor || o.color || C.bone;
    ctx.globalAlpha *= o.alpha == null ? 1 : o.alpha;
    ctx.fillRect(x + cw + 2, y - size * .78, Math.max(2, size * .07), size * .86);
    ctx.restore();
  }
  return n;
}
function imageCover(ctx, img, x, y, w, h, alpha = 1, filter = "none") {
  if (!img || !img.width) return;
  const s = Math.max(w / img.width, h / img.height);
  const dw = img.width * s, dh = img.height * s;
  ctx.save(); ctx.globalAlpha *= alpha; ctx.filter = filter;
  ctx.drawImage(img, x + (w - dw) / 2, y + (h - dh) / 2, dw, dh);
  ctx.restore();
}
function polygon(ctx, pts, close = true) {
  ctx.beginPath();
  pts.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]));
  if (close) ctx.closePath();
}
function greatCircle(a, b, n = 96) {
  const toRad = Math.PI / 180, toDeg = 180 / Math.PI;
  const lon1 = a[0] * toRad, lat1 = a[1] * toRad, lon2 = b[0] * toRad, lat2 = b[1] * toRad;
  const d = 2 * Math.asin(Math.sqrt(Math.sin((lat2 - lat1) / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin((lon2 - lon1) / 2) ** 2));
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const f = i / n;
    if (d < 1e-6) { pts.push(a); continue; }
    const A = Math.sin((1 - f) * d) / Math.sin(d), B = Math.sin(f * d) / Math.sin(d);
    const x = A * Math.cos(lat1) * Math.cos(lon1) + B * Math.cos(lat2) * Math.cos(lon2);
    const y = A * Math.cos(lat1) * Math.sin(lon1) + B * Math.cos(lat2) * Math.sin(lon2);
    const z = A * Math.sin(lat1) + B * Math.sin(lat2);
    pts.push([Math.atan2(y, x) * toDeg, Math.atan2(z, Math.sqrt(x * x + y * y)) * toDeg]);
  }
  return pts;
}
function polyLength(pts) {
  let L = 0; for (let i = 1; i < pts.length; i++) L += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
  return L;
}
function partialPath(ctx, pts, p) {
  if (!pts.length) return;
  const total = polyLength(pts) * clamp(p);
  ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]);
  let acc = 0;
  for (let i = 1; i < pts.length; i++) {
    const seg = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    if (acc + seg >= total) {
      const f = (total - acc) / seg;
      ctx.lineTo(lerp(pts[i - 1][0], pts[i][0], f), lerp(pts[i - 1][1], pts[i][1], f));
      return;
    }
    ctx.lineTo(pts[i][0], pts[i][1]); acc += seg;
  }
}
function pointAlong(pts, p) {
  const total = polyLength(pts) * clamp(p);
  let acc = 0;
  for (let i = 1; i < pts.length; i++) {
    const seg = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    if (acc + seg >= total) {
      const f = (total - acc) / seg;
      return [lerp(pts[i - 1][0], pts[i][0], f), lerp(pts[i - 1][1], pts[i][1], f)];
    }
    acc += seg;
  }
  return pts[pts.length - 1];
}
function projectFactory(box) {
  const k = Math.cos(35 * Math.PI / 180);
  const lon0 = 70, lon1 = 140, lat0 = 15, lat1 = 55;
  const gw = (lon1 - lon0) * k, gh = lat1 - lat0;
  return (lon, lat) => ({
    x: box.x + ((lon - lon0) * k) / gw * box.w,
    y: box.y + (lat1 - lat) / gh * box.h
  });
}
function line(ctx, pts, color, width = 2, dash = null, alpha = 1) {
  ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = width; ctx.globalAlpha *= alpha;
  if (dash) ctx.setLineDash(dash);
  polygon(ctx, pts, false); ctx.stroke(); ctx.restore();
}
function corner(ctx, x, y, w, h, s = 24, color = C.bone, lw = 1.5, alpha = 1) {
  ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.globalAlpha *= alpha;
  ctx.beginPath();
  ctx.moveTo(x, y + s); ctx.lineTo(x, y); ctx.lineTo(x + s, y);
  ctx.moveTo(x + w - s, y); ctx.lineTo(x + w, y); ctx.lineTo(x + w, y + s);
  ctx.moveTo(x + w, y + h - s); ctx.lineTo(x + w, y + h); ctx.lineTo(x + w - s, y + h);
  ctx.moveTo(x + s, y + h); ctx.lineTo(x, y + h); ctx.lineTo(x, y + h - s);
  ctx.stroke(); ctx.restore();
}
function crosshair(ctx, x, y, r, color, alpha = 1, lw = 1) {
  ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.globalAlpha *= alpha;
  ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(x - r * 1.6, y); ctx.lineTo(x + r * 1.6, y);
  ctx.moveTo(x, y - r * 1.6); ctx.lineTo(x, y + r * 1.6); ctx.stroke(); ctx.restore();
}
function stamp(ctx, label, x, y, angle, color, alpha = 1, size = 26) {
  ctx.save(); ctx.translate(x, y); ctx.rotate(angle);
  ctx.globalAlpha *= alpha; ctx.strokeStyle = color; ctx.fillStyle = color;
  ctx.lineWidth = 2.5; ctx.strokeRect(-textW(ctx, label, size, F.mono, 500, 2) / 2 - 18, -size, textW(ctx, label, size, F.mono, 500, 2) + 36, size * 1.9);
  text(ctx, label, 0, size * .35, { family: F.mono, size, weight: 500, tracking: 2, color, align: "center" });
  ctx.restore();
}
function redact(ctx, x, y, w, h, p = 1, color = C.ink) {
  ctx.save(); ctx.fillStyle = color; ctx.fillRect(x, y, w * clamp(p), h); ctx.restore();
}
function barcode(ctx, x, y, w, h, alpha = .6) {
  ctx.save(); ctx.globalAlpha *= alpha; ctx.fillStyle = C.bone;
  let cx = x, i = 0;
  while (cx < x + w) {
    const bw = 1 + hash(i * 7.1) * 5;
    if (hash(i * 3.7) > .35) ctx.fillRect(cx, y, bw, h);
    cx += bw + 2; i++;
  }
  ctx.restore();
}
function grainTone(ctx, x, y, w, h, alpha = .18) {
  ctx.save(); ctx.globalAlpha *= alpha;
  for (let i = 0; i < 140; i++) {
    const px = x + hash(i * 1.7) * w, py = y + hash(i * 2.3 + 4) * h;
    ctx.fillStyle = hash(i * 4.1) > .5 ? C.bone : C.ink;
    ctx.fillRect(px, py, 1, 1);
  }
  ctx.restore();
}
function glowDot(ctx, x, y, r, color, alpha = 1) {
  const g = ctx.createRadialGradient(x, y, 0, x, y, r);
  g.addColorStop(0, rgba(color, alpha)); g.addColorStop(.25, rgba(color, alpha * .55));
  g.addColorStop(1, rgba(color, 0));
  ctx.save(); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill(); ctx.restore();
}
