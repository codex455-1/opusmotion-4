/* ---------- shared atmosphere ---------- */
function bg(ctx, a, b, glow, gx = .5, gy = .45, ga = .5) {
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, a); g.addColorStop(1, b);
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  if (glow) {
    const r = ctx.createRadialGradient(W * gx, H * gy, 0, W * gx, H * gy, W * 1.15);
    r.addColorStop(0, rgba(glow, ga)); r.addColorStop(.55, rgba(glow, ga * .18)); r.addColorStop(1, rgba(glow, 0));
    ctx.fillStyle = r; ctx.fillRect(0, 0, W, H);
  }
  const v = ctx.createRadialGradient(W / 2, H * .48, W * .25, W / 2, H * .48, W * .95);
  v.addColorStop(0, "rgba(0,0,0,0)"); v.addColorStop(1, "rgba(0,0,0,.55)");
  ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);
}
function stars(ctx, img, t, alpha = .7, drift = 6) {
  if (!img) return;
  ctx.save(); ctx.globalAlpha *= alpha;
  ctx.drawImage(img, -drift + Math.sin(t * .02) * 4, -drift * .5, W + drift * 2, H + drift);
  ctx.restore();
}
function grainImage(ctx, img, x, y, w, h, alpha, filter = "none") {
  ctx.save(); ctx.globalAlpha *= alpha; ctx.globalCompositeOperation = "soft-light";
  imageCover(ctx, img, x, y, w, h, 1, filter); ctx.restore();
}
function ruled(ctx, x, y, w, color, alpha = .3, lw = 1) {
  ctx.save(); ctx.strokeStyle = color; ctx.globalAlpha *= alpha; ctx.lineWidth = lw;
  ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + w, y); ctx.stroke(); ctx.restore();
}
function metaTop(ctx, left, right, alpha = 1) {
  ctx.save(); ctx.globalAlpha *= alpha;
  text(ctx, left, 62, 72, { family: F.mono, size: 18, tracking: 2.6, color: C.boneDim });
  text(ctx, right, W - 62, 72, { family: F.mono, size: 18, tracking: 2.6, color: C.boneDim, align: "right" });
  ruled(ctx, 62, 92, W - 124, C.bone, .18);
  ctx.restore();
}
function metaBottom(ctx, left, right, alpha = 1) {
  ctx.save(); ctx.globalAlpha *= alpha;
  ruled(ctx, 62, H - 92, W - 124, C.bone, .16);
  text(ctx, left, 62, H - 62, { family: F.mono, size: 15, tracking: 2.2, color: C.boneDim });
  text(ctx, right, W - 62, H - 62, { family: F.mono, size: 15, tracking: 2.2, color: C.boneDim, align: "right" });
  ctx.restore();
}
function labelLine(ctx, txt, x, y, tx, ty, color = C.boneDim, alpha = .8) {
  ctx.save(); ctx.globalAlpha *= alpha; ctx.strokeStyle = color; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(tx, ty); ctx.stroke();
  ctx.beginPath(); ctx.arc(x, y, 2.2, 0, Math.PI * 2); ctx.fillStyle = color; ctx.fill();
  ctx.restore();
  text(ctx, txt, tx, ty - 10, { family: F.mono, size: 14, tracking: 1.6, color, alpha });
}

/* ---------- aircraft ---------- */
function u2TopPath(ctx) {
  ctx.beginPath();
  ctx.moveTo(-520, 0);
  ctx.bezierCurveTo(-500, -7, -440, -14, -360, -17);
  ctx.lineTo(-120, -19);
  ctx.bezierCurveTo(-92, -19, -74, -15, -56, -12);
  ctx.lineTo(330, -12);
  ctx.bezierCurveTo(400, -12, 460, -7, 515, 0);
  ctx.bezierCurveTo(460, 7, 400, 12, 330, 12);
  ctx.lineTo(-56, 12);
  ctx.bezierCurveTo(-74, 15, -92, 19, -120, 19);
  ctx.lineTo(-360, 17);
  ctx.bezierCurveTo(-440, 14, -500, 7, -520, 0);
  ctx.closePath();
  // wings
  ctx.moveTo(-70, -16);
  ctx.lineTo(-180, -760);
  ctx.lineTo(-120, -775);
  ctx.lineTo(40, -20);
  ctx.lineTo(40, 20);
  ctx.lineTo(-120, 775);
  ctx.lineTo(-180, 760);
  ctx.lineTo(-70, 16);
  // tailplane
  ctx.moveTo(380, -9);
  ctx.lineTo(475, -185);
  ctx.lineTo(505, -182);
  ctx.lineTo(520, -6);
  ctx.lineTo(520, 6);
  ctx.lineTo(505, 182);
  ctx.lineTo(475, 185);
  ctx.lineTo(380, 9);
}
function drawU2Top(ctx, x, y, s, color, fill, lw = 2, alpha = 1) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.globalAlpha *= alpha;
  u2TopPath(ctx);
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  ctx.strokeStyle = color; ctx.lineWidth = lw / s; ctx.lineJoin = "round"; ctx.stroke();
  // panel / spine
  ctx.beginPath(); ctx.moveTo(-500, 0); ctx.lineTo(500, 0); ctx.strokeStyle = rgba(color, .22); ctx.stroke();
  ctx.restore();
}
function u2SidePath(ctx) {
  ctx.beginPath();
  ctx.moveTo(-520, 8);
  ctx.bezierCurveTo(-470, -2, -380, -8, -300, -12);
  ctx.bezierCurveTo(-270, -30, -235, -30, -205, -14);
  ctx.bezierCurveTo(-120, -20, 120, -22, 300, -16);
  ctx.bezierCurveTo(390, -14, 465, -10, 510, 0);
  ctx.lineTo(505, 18);
  ctx.bezierCurveTo(390, 24, 240, 26, 80, 26);
  ctx.bezierCurveTo(-160, 26, -390, 34, -500, 40);
  ctx.closePath();
  // wing
  ctx.moveTo(-40, 10);
  ctx.lineTo(130, 54);
  ctx.lineTo(105, 62);
  ctx.lineTo(-95, 22);
  // tail fin
  ctx.moveTo(370, -10);
  ctx.lineTo(440, -210);
  ctx.lineTo(495, -210);
  ctx.lineTo(505, -8);
  // ventral fin
  ctx.moveTo(380, 22);
  ctx.lineTo(430, 90);
  ctx.lineTo(465, 90);
  ctx.lineTo(465, 18);
}
function drawU2Side(ctx, x, y, s, color, lw = 2, alpha = 1) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.globalAlpha *= alpha;
  u2SidePath(ctx); ctx.strokeStyle = color; ctx.lineWidth = lw / s; ctx.lineJoin = "round"; ctx.stroke();
  ctx.beginPath(); ctx.arc(-250, -12, 8, Math.PI, 0); ctx.strokeStyle = rgba(color, .7); ctx.stroke();
  ctx.restore();
}
function h6SidePath(ctx) {
  ctx.beginPath();
  ctx.moveTo(-300, 10);
  ctx.bezierCurveTo(-280, -8, -240, -20, -190, -24);
  ctx.lineTo(120, -26);
  ctx.lineTo(210, -60);
  ctx.lineTo(295, -62);
  ctx.lineTo(330, -20);
  ctx.lineTo(420, -18);
  ctx.lineTo(470, -110);
  ctx.lineTo(505, -108);
  ctx.lineTo(500, -8);
  ctx.lineTo(470, 18);
  ctx.lineTo(210, 24);
  ctx.lineTo(110, 40);
  ctx.lineTo(-190, 38);
  ctx.bezierCurveTo(-245, 34, -285, 24, -300, 10);
  ctx.closePath();
  // wing
  ctx.moveTo(-30, 16);
  ctx.lineTo(150, 86);
  ctx.lineTo(120, 96);
  ctx.lineTo(-80, 30);
}

/* ---------- objects ---------- */
function canister(ctx, x, y, s, color, p = 1, alpha = 1) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.globalAlpha *= alpha;
  const w = 54, h = 260;
  ctx.strokeStyle = color; ctx.lineWidth = 2 / s;
  ctx.fillStyle = "rgba(8,12,12,.55)";
  ctx.beginPath(); ctx.roundRect(-w / 2, -h / 2, w, h, 24); ctx.fill(); ctx.stroke();
  for (let i = -2; i <= 2; i++) {
    ctx.beginPath(); ctx.moveTo(-w / 2 + 4, i * 34); ctx.lineTo(w / 2 - 4, i * 34);
    ctx.strokeStyle = rgba(color, .35); ctx.stroke();
  }
  ctx.beginPath(); ctx.moveTo(0, -h / 2); ctx.lineTo(0, -h / 2 - 46 * clamp(p * 2));
  ctx.moveTo(0, h / 2); ctx.lineTo(0, h / 2 + 30 * clamp(p * 2 - .4)); ctx.strokeStyle = color; ctx.stroke();
  ctx.beginPath(); ctx.arc(0, -h / 2 - 48 * clamp(p * 2), 3.5, 0, Math.PI * 2); ctx.fillStyle = color; ctx.fill();
  ctx.restore();
}
function parachute(ctx, x, y, s, color, p = 1, alpha = 1) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.globalAlpha *= alpha;
  const r = 110 * easeOut(clamp(p)), h = 120 * easeOut(clamp(p));
  ctx.strokeStyle = color; ctx.lineWidth = 1.5 / s;
  ctx.beginPath(); ctx.arc(0, 0, r, Math.PI, 0); ctx.stroke();
  for (let i = 0; i <= 6; i++) {
    const a = Math.PI + i / 6 * Math.PI;
    ctx.beginPath(); ctx.moveTo(Math.cos(a) * r, Math.sin(a) * r); ctx.lineTo(0, h); ctx.strokeStyle = rgba(color, .5); ctx.stroke();
  }
  ctx.beginPath(); ctx.moveTo(-6, h); ctx.lineTo(6, h); ctx.strokeStyle = color; ctx.stroke();
  ctx.restore();
}
function seismo(ctx, x, y, w, h, p, color, alpha = 1, seed = 1) {
  ctx.save(); ctx.globalAlpha *= alpha; ctx.strokeStyle = color; ctx.lineWidth = 1.6;
  ctx.beginPath();
  const n = 420, tt = p * 1.7;
  for (let i = 0; i <= n; i++) {
    const u = i / n;
    const env = Math.exp(-Math.pow((u - .42) * 7, 2)) + .12 * Math.exp(-Math.pow((u - .7) * 10, 2));
    const v = (Math.sin(u * 90 + seed) * .55 + Math.sin(u * 210 + seed * 3) * .3 + Math.sin(u * 31 + seed * 5) * .2) * env;
    const px = x + u * w, py = y + v * h * .45 + (hash(i + seed) - .5) * .8;
    i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
  }
  ctx.stroke();
  ctx.globalAlpha *= .35; ctx.strokeStyle = rgba(color, .5); ctx.lineWidth = .8;
  ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + w, y); ctx.stroke();
  ctx.restore();
}
function tapeReel(ctx, x, y, r, angle, color, alpha = 1) {
  ctx.save(); ctx.translate(x, y); ctx.rotate(angle); ctx.globalAlpha *= alpha;
  ctx.strokeStyle = color; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.arc(0, 0, r, 0, Math.PI * 2); ctx.stroke();
  ctx.beginPath(); ctx.arc(0, 0, r * .35, 0, Math.PI * 2); ctx.stroke();
  for (let i = 0; i < 6; i++) {
    const a = i / 6 * Math.PI * 2;
    ctx.beginPath(); ctx.moveTo(Math.cos(a) * r * .35, Math.sin(a) * r * .35);
    ctx.lineTo(Math.cos(a) * r * .92, Math.sin(a) * r * .92); ctx.strokeStyle = rgba(color, .45); ctx.stroke();
  }
  ctx.restore();
}
function docSheet(ctx, img, x, y, w, h, rot, alpha = 1, redactions = 0, stampText = "TOP SECRET") {
  ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.globalAlpha *= alpha;
  ctx.shadowColor = "rgba(0,0,0,.7)"; ctx.shadowBlur = 40;
  ctx.fillStyle = "#d9cdb2"; ctx.fillRect(-w / 2, -h / 2, w, h);
  ctx.shadowBlur = 0;
  if (img) imageCover(ctx, img, -w / 2, -h / 2, w, h, .55, "none");
  ctx.strokeStyle = "rgba(40,35,25,.35)"; ctx.lineWidth = 1;
  for (let i = 0; i < 18; i++) {
    const yy = -h / 2 + 90 + i * 26;
    ctx.beginPath(); ctx.moveTo(-w / 2 + 46, yy); ctx.lineTo(w / 2 - 46 - hash(i) * 80, yy); ctx.stroke();
  }
  for (let i = 0; i < redactions; i++) {
    const ry = -h / 2 + 70 + i * 23;
    ctx.fillStyle = "#0b0d0d"; ctx.fillRect(-w / 2 + 60, ry, w * (.3 + hash(i + 3) * .5), 12);
  }
  ctx.save(); ctx.rotate(-.06); ctx.globalAlpha *= .8;
  ctx.strokeStyle = "#8f2f26"; ctx.lineWidth = 4;
  ctx.strokeRect(-w * .32, -h * .3, w * .64, 74);
  text(ctx, stampText, 0, -h * .3 + 48, { family: F.mono, size: 28, weight: 500, tracking: 4, color: "#8f2f26", align: "center" });
  ctx.restore();
  ctx.restore();
}

/* ---------- scene 1 : open ---------- */
function sceneOpen(ctx, t) {
  const titleIn = easeOut4(inv(9.25, 10.6, t));
  const fade = t < .35 ? t / .35 : t > 12.7 ? (13.1 - t) / .4 : 1;
  bg(ctx, "#040606", "#080b0b", "#8a5a2a", .5, .78, .16 * fade);
  stars(ctx, window.ASSETS.stars, t, .18 + .12 * titleIn);
  // horizon and runway
  const hy = 1470;
  const g = ctx.createLinearGradient(0, hy - 260, 0, hy + 20);
  g.addColorStop(0, "rgba(224,168,60,0)"); g.addColorStop(1, "rgba(224,168,60,.10)");
  ctx.fillStyle = g; ctx.fillRect(0, hy - 260, W, 280);
  ctx.strokeStyle = "rgba(233,223,200,.20)"; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(0, hy); ctx.lineTo(W, hy); ctx.stroke();
  const vx = 540, vy = 1330;
  ctx.save(); ctx.globalAlpha *= .55;
  for (let i = -7; i <= 7; i++) {
    ctx.beginPath(); ctx.moveTo(vx + i * 9, vy);
    ctx.lineTo(vx + i * 175, H + 40); ctx.strokeStyle = "rgba(233,223,200,.10)"; ctx.stroke();
  }
  for (let i = 1; i < 16; i++) {
    const p = i / 16, yy = lerp(vy, H, p * p), xx = lerp(vx, vx + 560, p * p);
    for (const s of [-1, 1]) {
      const lx = vx + s * (xx - vx), a = .10 + .5 * p;
      glowDot(ctx, lx, yy, 5 + 16 * p, C.amber, a * .55);
    }
  }
  ctx.restore();
  // climbing aircraft
  if (t > 1.9) {
    const p = easeInOut(inv(2.0, 7.8, t));
  const ax = lerp(430, 760, p), ay = lerp(1570, 800, p * .82 + p * p * .18);
    drawU2Top(ctx, ax, ay, .20 + .05 * p, rgba(C.bone, .62 + .25 * p), "rgba(5,7,7,.9)", 1.4, .9);
    const ex = ax - 26, ey = ay + 4;
    glowDot(ctx, ex, ey, 26, C.amber, .25 + .15 * Math.sin(t * 11));
    ctx.save(); ctx.globalAlpha *= .35;
    for (let i = 0; i < 4; i++) {
      const q = i / 4, tx = lerp(ax, 360, q * .35 + .1), ty = lerp(ay, 1650, q);
      ctx.fillStyle = rgba(C.bone, .08 * (1 - q)); ctx.beginPath(); ctx.arc(tx, ty, 1.5, 0, 7); ctx.fill();
    }
    ctx.restore();
  }
  // metadata
  metaTop(ctx, "CASE FILE  /  35-07", "EYES ONLY", .7 * fade);
  const typedP = inv(0.6, 2.1, t);
  if (t > .5) {
    typed(ctx, "MAY 1967", 62, 190, typedP, { family: F.mono, size: 20, tracking: 5, color: C.amber, cursorColor: C.amber });
    if (t > 2.2) {
      text(ctx, "TAKHLI  ·  THAILAND", 62, 226, { family: F.mono, size: 15, tracking: 3.4, color: C.boneDim, alpha: inv(2.3, 3.1, t) });
      text(ctx, "15.27° N   100.05° E", 62, 250, { family: F.mono, size: 15, tracking: 2.8, color: C.boneDim, alpha: inv(2.5, 3.3, t) });
    }
  }
  // title
  if (t > 9.2) {
    const cx = W / 2;
    ctx.save(); ctx.globalAlpha *= fade;
    const rule = easeOut(inv(9.9, 11.2, t));
    const rw = 360 * rule;
    ruled(ctx, cx - rw / 2, 772, rw, C.bone, .35, 1);
    text(ctx, "TABASCO", cx, 960, { family: F.display, size: 174, weight: 500, tracking: 4 + 16 * (1 - titleIn), color: C.bone, align: "center", alpha: titleIn });
    text(ctx, "THE MISSION THAT LISTENED TO A BOMB", cx, 1020, { family: F.mono, size: 20, tracking: 4.2, color: C.boneDim, align: "center", alpha: easeOut(inv(10.0, 11.0, t)) });
    text(ctx, "黑猫", cx + 500, 855, { family: F.cn, size: 44, weight: 500, tracking: 4, color: rgba(C.rust, .9), align: "center", alpha: easeOut(inv(10.4, 11.4, t)) });
    ctx.restore();
  }
  if (fade < 1) { ctx.fillStyle = `rgba(0,0,0,${1 - fade})`; ctx.fillRect(0, 0, W, H); }
}

/* ---------- scene 2 : cats ---------- */
function sceneCats(ctx, t) {
  const lt = t - 13.10;
  const fade = lt < .35 ? lt / .35 : lt > 11.6 ? (11.95 - lt) / .35 : 1;
  bg(ctx, "#0a0e0e", "#090b0b", "#2f5a4c", .72, .28, .20);
  ctx.save(); ctx.globalAlpha *= .12;
  imageCover(ctx, window.ASSETS.paper, 0, 0, W, H, 1, "none");
  ctx.restore();
  metaTop(ctx, "35TH SQUADRON  /  ROCAF", "PROJECT RAZOR", .8 * fade);
  // dossier block
  const stampIn = easeOut4(inv(.1, .9, lt));
  ctx.save(); ctx.globalAlpha *= fade;
  text(ctx, "PILOT", 62, 360, { family: F.mono, size: 18, tracking: 4, color: C.amber, alpha: inv(.5, 1.2, lt) });
  text(ctx, "CHUANG", 58, 470, { family: F.display, size: 112, weight: 500, tracking: 1, color: C.bone, alpha: inv(.7, 1.6, lt) });
  text(ctx, "JEN-LIANG", 62, 570, { family: F.display, size: 86, weight: 400, tracking: 2, color: C.bone, alpha: inv(1.1, 2.0, lt) });
  text(ctx, "莊人亮", 66, 632, { family: F.cn, size: 30, weight: 400, tracking: 6, color: C.boneDim, alpha: inv(1.4, 2.2, lt) });
  ctx.restore();
  // black cat stamp
  if (lt > .15) {
    ctx.save(); ctx.globalAlpha *= fade; ctx.translate(780, 340); ctx.rotate(-.16);
    ctx.strokeStyle = rgba(C.rust, .8 * stampIn); ctx.lineWidth = 3;
    ctx.beginPath(); ctx.arc(0, 0, 126, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.arc(0, 0, 108, 0, Math.PI * 2); ctx.strokeStyle = rgba(C.rust, .4); ctx.lineWidth = 1; ctx.stroke();
    // cat mark : ears + eyes, abstract
    ctx.fillStyle = rgba(C.rust, .85 * stampIn);
    ctx.beginPath(); ctx.moveTo(-44, -30); ctx.lineTo(-30, -76); ctx.lineTo(-6, -46); ctx.closePath(); ctx.fill();
    ctx.beginPath(); ctx.moveTo(44, -30); ctx.lineTo(30, -76); ctx.lineTo(6, -46); ctx.closePath(); ctx.fill();
    ctx.beginPath(); ctx.ellipse(0, 2, 54, 44, 0, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = C.ink;
    ctx.beginPath(); ctx.ellipse(-20, -6, 9, 13, .2, 0, 7); ctx.fill();
    ctx.beginPath(); ctx.ellipse(20, -6, 9, 13, -.2, 0, 7); ctx.fill();
    text(ctx, "BLACK CATS", 0, 180, { family: F.mono, size: 20, weight: 500, tracking: 3, color: rgba(C.rust, .9 * stampIn), align: "center" });
    ctx.restore();
  }
  // redacted memo
  if (lt > 2.0) {
    const p = easeOut(inv(2.0, 3.2, lt));
    ctx.save(); ctx.globalAlpha *= fade;
    ctx.fillStyle = "rgba(9,13,13,.55)"; ctx.fillRect(62, 720, 500, 245);
    ctx.strokeStyle = rgba(C.bone, .16); ctx.lineWidth = 1; ctx.strokeRect(62, 720, 500, 245);
    for (let i = 0; i < 7; i++) {
      const w = 120 + hash(i + 8) * 300;
      ctx.fillStyle = rgba(C.bone, .12); ctx.fillRect(88, 752 + i * 26, w, 7);
    }
    for (let i = 0; i < 3; i++) redact(ctx, 88, 752 + (i * 2 + 1) * 26, 200 + hash(i) * 150, 9, p);
    text(ctx, "PERSONNEL FILE  /  REDACTED", 88, 942, { family: F.mono, size: 16, tracking: 2.2, color: C.rust, alpha: p });
    ctx.restore();
  }
  // blueprint U-2
  if (lt > 3.4) {
    const p = easeOut(inv(3.4, 5.8, lt));
    const bx = 80, by = 1120, bw = 920, bh = 380;
    ctx.save(); ctx.globalAlpha *= fade;
    ctx.strokeStyle = rgba(C.jade, .20); ctx.lineWidth = 1;
    for (let x = 0; x <= 8; x++) { ctx.beginPath(); ctx.moveTo(bx + x * bw / 8, by); ctx.lineTo(bx + x * bw / 8, by + bh); ctx.stroke(); }
    for (let y = 0; y <= 4; y++) { ctx.beginPath(); ctx.moveTo(bx, by + y * bh / 4); ctx.lineTo(bx + bw, by + y * bh / 4); ctx.stroke(); }
    corner(ctx, bx, by, bw, bh, 26, C.jade, 1.4, .8);
    // reveal clip
    ctx.beginPath(); ctx.rect(bx, by, bw * p, bh); ctx.clip();
    drawU2Side(ctx, 540, 1300, .78, C.jade, 1.8, .9);
    ctx.restore();
    text(ctx, "LOCKHEED U-2  /  DRAGON LADY", 80, 1180, { family: F.mono, size: 15, tracking: 2.6, color: C.jade, alpha: p * fade });
    text(ctx, "31.4 M", 80, 1545, { family: F.mono, size: 13, tracking: 2, color: C.boneDim, alpha: p * fade });
    labelLine(ctx, "WINGSPAN", 80, 1545, 300, 1545, C.boneDim, p * .9 * fade);
    labelLine(ctx, "OPTICAL BAY", 600, 1320, 820, 1250, C.boneDim, p * .9 * fade);
  }
  // altitude ladder
  if (lt > 8.2) {
    const p = easeOut(inv(8.2, 9.6, lt));
    ctx.save(); ctx.globalAlpha *= fade;
    const lx = 930, y0 = 760, y1 = 1650;
    ctx.strokeStyle = rgba(C.bone, .25); ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(lx, y0); ctx.lineTo(lx, y1); ctx.stroke();
    for (let i = 0; i <= 7; i++) {
      const yy = lerp(y1, y0, i / 7);
      ctx.beginPath(); ctx.moveTo(lx - 7, yy); ctx.lineTo(lx + 7, yy); ctx.stroke();
      text(ctx, `${i * 10}k`, lx + 16, yy + 4, { family: F.mono, size: 11, color: C.boneDim, alpha: .8 });
    }
    const mark = lerp(y1, y0, easeInOut(inv(9.0, 10.6, lt)) * .7);
    ctx.fillStyle = C.rust; ctx.beginPath(); ctx.arc(lx, mark, 6, 0, 7); ctx.fill();
    glowDot(ctx, lx, mark, 40, C.rust, .3);
    text(ctx, "70,000 FT", 760, 700, { family: F.display, size: 56, weight: 500, color: C.bone, alpha: p });
    text(ctx, "21,336 M", 762, 736, { family: F.mono, size: 16, tracking: 3, color: C.amber, alpha: p });
    ctx.restore();
  }
  if (fade < 1) { ctx.fillStyle = `rgba(0,0,0,${1 - fade})`; ctx.fillRect(0, 0, W, H); }
}

/* ---------- map ---------- */
function drawAsia(ctx, box, alpha = 1, lights = .7, chinaOnly = false) {
  const P = projectFactory(box);
  ctx.save(); ctx.globalAlpha *= alpha;
  // graticule
  ctx.strokeStyle = "rgba(233,223,200,.055)"; ctx.lineWidth = 1;
  for (let lon = 80; lon <= 130; lon += 10) {
    const a = P(lon, 15), b = P(lon, 55);
    ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
  }
  for (let lat = 20; lat <= 50; lat += 10) {
    const a = P(70, lat), b = P(140, lat);
    ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
  }
  const china = window.ASIA.filter(p => p.n === "China");
  // neighbours
  if (!chinaOnly) {
    for (const poly of window.ASIA) {
      if (poly.n === "China") continue;
      const pts = poly.p.map(([lon, lat]) => { const q = P(lon, lat); return [q.x, q.y]; });
      polygon(ctx, pts);
      ctx.fillStyle = "rgba(10,15,15,.42)"; ctx.fill();
      ctx.strokeStyle = "rgba(111,143,125,.26)"; ctx.lineWidth = .9; ctx.stroke();
    }
  }
  // china fill
  ctx.save();
  ctx.beginPath();
  for (const poly of china) {
    const pts = poly.p.map(([lon, lat]) => { const q = P(lon, lat); return [q.x, q.y]; });
    pts.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]));
    ctx.closePath();
  }
  ctx.fillStyle = "rgba(13,20,19,.74)"; ctx.fill("evenodd");
  ctx.restore();
  // lights, clipped to china
  if (window.ASSETS.lights && lights > 0) {
    ctx.save(); ctx.beginPath();
    for (const poly of china) {
      const pts = poly.p.map(([lon, lat]) => { const q = P(lon, lat); return [q.x, q.y]; });
      pts.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]));
      ctx.closePath();
    }
    ctx.clip("evenodd");
    ctx.globalCompositeOperation = "screen"; ctx.globalAlpha *= lights;
    ctx.drawImage(window.ASSETS.lights, box.x, box.y, box.w, box.h); ctx.restore();
  }
  // china outline
  ctx.beginPath();
  for (const poly of china) {
    const pts = poly.p.map(([lon, lat]) => { const q = P(lon, lat); return [q.x, q.y]; });
    pts.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]));
    ctx.closePath();
  }
  ctx.strokeStyle = "rgba(233,223,200,.62)"; ctx.lineWidth = 1.5; ctx.stroke();
  ctx.restore();
}
function mapPin(ctx, P, lon, lat, label, sub, color = C.amber, alpha = 1, align = "left") {
  const p = P(lon, lat);
  ctx.save(); ctx.globalAlpha *= alpha;
  glowDot(ctx, p.x, p.y, 22, color, .22);
  ctx.strokeStyle = color; ctx.lineWidth = 1.2;
  ctx.beginPath(); ctx.arc(p.x, p.y, 5, 0, 7); ctx.stroke();
  ctx.beginPath(); ctx.arc(p.x, p.y, 2, 0, 7); ctx.fillStyle = color; ctx.fill();
  const tx = align === "right" ? p.x - 14 : p.x + 14;
  text(ctx, label, tx, p.y - 4, { family: F.mono, size: 14, tracking: 2.2, color, align: align === "right" ? "right" : "left" });
  if (sub) text(ctx, sub, tx, p.y + 16, { family: F.mono, size: 11, tracking: 1.8, color: C.boneDim, align: align === "right" ? "right" : "left" });
  ctx.restore();
}

/* ---------- scene 3 : problem ---------- */
function sceneProblem(ctx, t) {
  const lt = t - 25.05;
  const fade = lt < .4 ? lt / .4 : lt > 7.0 ? (7.45 - lt) / .45 : 1;
  bg(ctx, "#080b0b", "#050707", "#3d4a35", .3, .35, .16);
  metaTop(ctx, "NATIONAL INTELLIGENCE ESTIMATE", "25.05.1967", .75 * fade);
  const box = { x: 70, y: 470, w: 940, h: 648 };
  const P = projectFactory(box);
  const zoom = 1 + .012 * easeOut(inv(0, 7.4, lt));
  ctx.save(); ctx.globalAlpha *= fade;
  ctx.translate(W / 2, box.y + box.h / 2); ctx.scale(zoom, zoom); ctx.translate(-W / 2, -(box.y + box.h / 2));
  if (window.CACHE && window.CACHE.main) ctx.drawImage(window.CACHE.main, 0, 0);
  else drawAsia(ctx, box, 1, .8);
  // silk road / infrastructure traces
  ctx.save(); ctx.strokeStyle = "rgba(224,168,60,.12)"; ctx.lineWidth = 1; ctx.setLineDash([2, 6]);
  for (let i = 0; i < 9; i++) {
    const y = box.y + 120 + i * 54;
    ctx.beginPath(); ctx.moveTo(box.x + 90, y); ctx.bezierCurveTo(box.x + 360, y - 30, box.x + 620, y + 40, box.x + 880, y - 8); ctx.stroke();
  }
  ctx.restore();
  // pins
  mapPin(ctx, P, 89.79, 40.81, "LOP NUR", "TEST SITE", C.rust, easeOut(inv(.8, 1.6, lt)), "left");
  mapPin(ctx, P, 116.40, 39.90, "BEIJING", "", C.boneDim, .55, "left");
  mapPin(ctx, P, 121.56, 25.03, "TAIPEI", "", C.jade, .55, "right");
  // orbit
  const orb = easeOut(inv(2.6, 4.4, lt));
  if (orb > 0) {
    ctx.save(); ctx.globalAlpha *= orb;
    for (let i = 0; i < 3; i++) {
      ctx.beginPath();
      ctx.ellipse(W / 2, 830 + i * 16, 520 - i * 60, 180 - i * 18, -.12 + i * .05, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(111,143,125,${.18 - i * .04})`; ctx.lineWidth = 1; ctx.stroke();
    }
    const sx = lerp(80, 1000, (lt - 2.6) / 4.4), sy = 750 + Math.sin((lt - 2.6) * 1.4) * 30;
    ctx.strokeStyle = rgba(C.jade, .7); ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(sx - 12, sy); ctx.lineTo(sx + 12, sy); ctx.moveTo(sx, sy - 12); ctx.lineTo(sx, sy + 12); ctx.stroke();
    ctx.beginPath(); ctx.arc(sx, sy, 3, 0, 7); ctx.fillStyle = C.jade; ctx.fill();
    text(ctx, "KH-7  /  OPTICAL", sx + 22, sy + 4, { family: F.mono, size: 14, tracking: 1.8, color: C.jade });
    ctx.restore();
  }
  ctx.restore();
  // title
  text(ctx, "THE DESERT", 62, 360, { family: F.display, size: 80, weight: 400, tracking: 3, color: C.bone, alpha: easeOut(inv(.2, 1.2, lt)) * fade });
  text(ctx, "IS BLIND", 62, 432, { family: F.display, size: 80, weight: 500, tracking: 6, color: rgba(C.bone, .5), alpha: easeOut(inv(.5, 1.5, lt)) * fade });
  // tags
  const tag = easeOut(inv(2.0, 2.8, lt));
  ctx.save(); ctx.globalAlpha *= tag * fade;
  ctx.strokeStyle = rgba(C.rust, .8); ctx.lineWidth = 1; ctx.strokeRect(62, 1370, 440, 74);
  text(ctx, "16 OCT 1964", 82, 1400, { family: F.mono, size: 14, tracking: 2.6, color: C.rust });
  text(ctx, "FIRST ATOMIC TEST", 82, 1426, { family: F.mono, size: 13, tracking: 2.2, color: C.boneDim });
  text(ctx, "NEXT  /  THERMONUCLEAR", 548, 1400, { family: F.mono, size: 14, tracking: 2.4, color: C.amber, alpha: tag });
  text(ctx, "THE CAMERA SEES.  THE EARTH HEARS.", 548, 1426, { family: F.mono, size: 12, tracking: 1.8, color: C.boneDim, alpha: tag });
  ctx.restore();
  // flatline panel
  if (lt > 3.4) {
    const p = easeOut(inv(3.4, 4.4, lt));
    ctx.save(); ctx.globalAlpha *= p * fade;
    ctx.fillStyle = "rgba(5,8,8,.7)"; ctx.fillRect(62, 1500, 956, 190);
    ctx.strokeStyle = "rgba(233,223,200,.14)"; ctx.strokeRect(62, 1500, 956, 190);
    text(ctx, "SEISMIC  /  NO SIGNAL", 84, 1534, { family: F.mono, size: 13, tracking: 2.2, color: C.rust });
    ctx.strokeStyle = rgba(C.ink, 1); ctx.lineWidth = 1;
    ctx.save(); ctx.beginPath(); ctx.rect(84, 1552, 912, 110); ctx.clip();
    ctx.strokeStyle = rgba(C.bone, .3); ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.moveTo(84, 1610); ctx.lineTo(996, 1610); ctx.stroke();
    for (let i = 0; i < 6; i++) {
      const x = 120 + i * 160;
      text(ctx, "·", x, 1614, { family: F.mono, size: 20, color: C.rust, alpha: .5 });
    }
    ctx.restore();
    text(ctx, "A PHOTOGRAPH CANNOT FEEL A SHOCKWAVE.", 84, 1676, { family: F.mono, size: 16, tracking: 1.6, color: C.boneDim });
    ctx.restore();
  }
  if (fade < 1) { ctx.fillStyle = `rgba(0,0,0,${1 - fade})`; ctx.fillRect(0, 0, W, H); }
}

/* ---------- scene 4 : plan ---------- */
function scenePlan(ctx, t) {
  const lt = t - 32.50;
  const fade = lt < .35 ? lt / .35 : lt > 14.3 ? (14.7 - lt) / .4 : 1;
  bg(ctx, "#070a0a", "#040606", "#4d3b23", .3, .55, .14);
  metaTop(ctx, "OPERATION TABASCO  /  MISSION PROFILE", "07 MAY 1967", .8 * fade);
  const routeP = easeInOut(inv(.1, 6.0, lt));
  const bayP = inv(5.9, 7.2, lt);
  const waitP = inv(10.6, 12.2, lt);
  // profile
  ctx.save(); ctx.globalAlpha *= fade * (1 - .45 * bayP);
  const x0 = 150, x1 = 940, y0 = 1620, y1 = 420;
  // altitude grid
  ctx.strokeStyle = "rgba(233,223,200,.08)"; ctx.lineWidth = 1;
  for (let i = 0; i <= 5; i++) {
    const y = lerp(y0, y1, i / 5);
    ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke();
    text(ctx, `${i * 5}k`, 66, y + 4, { family: F.mono, size: 11, color: C.boneDim, alpha: .7 });
  }
  // terrain silhouette
  ctx.beginPath(); ctx.moveTo(x0, y0);
  const terr = [];
  for (let i = 0; i <= 80; i++) {
    const u = i / 80, x = lerp(x0, x1, u);
    const him = Math.exp(-Math.pow((u - .52) * 2.6, 2));
    const h = 40 + him * 220 * (.65 + .35 * Math.sin(u * 28) ** 2) + Math.sin(u * 11) * 25 + hash(i) * 8;
    terr.push([x, y0 - h]); ctx.lineTo(x, y0 - h);
  }
  ctx.lineTo(x1, y0); ctx.closePath();
  const tg = ctx.createLinearGradient(0, y0 - 300, 0, y0); tg.addColorStop(0, "rgba(22,32,29,.9)"); tg.addColorStop(1, "rgba(5,8,8,1)");
  ctx.fillStyle = tg; ctx.fill();
  ctx.strokeStyle = "rgba(111,143,125,.35)"; ctx.lineWidth = 1; ctx.beginPath();
  terr.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])); ctx.stroke();
  // route
  const ry = lerp(y0 - 130, y1 + 40, routeP);
  const grad = ctx.createLinearGradient(0, y0, 0, y1);
  grad.addColorStop(0, C.amber); grad.addColorStop(1, "rgba(224,168,60,.25)");
  ctx.strokeStyle = grad; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(x0 + 240, y0 - 130); ctx.lineTo(x0 + 240, ry); ctx.stroke();
  // waypoint marks
  const way = [["TAKHLI", "0 KM", 0], ["MYANMAR", "700 KM", .24], ["INDIA", "1,300 KM", .45], ["TIBET", "2,100 KM", .72], ["LOP NUR", "3,000 KM", 1]];
  way.forEach(([n, d, u], i) => {
    const y = lerp(y0 - 130, y1 + 40, u);
    const on = routeP >= u - .01;
    ctx.strokeStyle = on ? rgba(C.bone, .7) : rgba(C.bone, .15); ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(x0 + 228, y); ctx.lineTo(x0 + 252, y); ctx.stroke();
    text(ctx, n, x0 + 270, y + 4, { family: F.mono, size: 17, tracking: 2.2, color: on ? C.bone : rgba(C.bone, .3) });
    text(ctx, d, x0 + 270, y + 26, { family: F.mono, size: 15, tracking: 1.6, color: on ? C.boneDim : rgba(C.bone, .18) });
  });
  // aircraft at tip
  if (routeP > 0 && routeP < 1) {
    drawU2Top(ctx, x0 + 240, ry - 22, .075, C.amber, "rgba(5,7,7,.9)", 1.2, 1);
    glowDot(ctx, x0 + 240, ry - 22, 34, C.amber, .22);
  }
  // bamboo curtain
  ctx.save(); ctx.translate(1000, 1000); ctx.rotate(-Math.PI / 2);
  text(ctx, "BAMBOO CURTAIN", 0, 0, { family: F.mono, size: 12, tracking: 4, color: rgba(C.boneDim, .65), align: "center" });
  ctx.restore();
  text(ctx, "3,000", 62, 1240, { family: F.display, size: 88, weight: 500, color: C.bone, alpha: easeOut(inv(2.0, 3.2, lt)) * (1 - bayP) });
  text(ctx, "KILOMETERS", 64, 1276, { family: F.mono, size: 14, tracking: 4, color: C.amber, alpha: easeOut(inv(2.2, 3.4, lt)) * (1 - bayP) });
  text(ctx, "21,000 M", 64, 1350, { family: F.mono, size: 14, tracking: 3, color: C.boneDim, alpha: easeOut(inv(3.4, 4.4, lt)) * (1 - bayP) });
  text(ctx, "ONE PASS.  TWO LISTENERS.", 64, 1390, { family: F.mono, size: 12, tracking: 2.2, color: C.boneDim, alpha: easeOut(inv(4.4, 5.4, lt)) * (1 - bayP) });
  ctx.restore();
  // bay / drop
  const bayA = smooth(bayP) * (1 - smooth(waitP));
  if (bayA > .001) {
    ctx.save(); ctx.globalAlpha *= bayA * fade;
    // desert below
    ctx.save(); ctx.beginPath(); ctx.rect(0, 1130, W, 790); ctx.clip();
    imageCover(ctx, window.ASSETS.desert, 0, 1130, W, 790, .55, "none");
    ctx.fillStyle = "rgba(5,8,8,.45)"; ctx.fillRect(0, 1130, W, 790);
    ctx.restore();
    // bay ceiling
    const yb = 1130;
    const bg2 = ctx.createLinearGradient(0, 140, 0, yb);
    bg2.addColorStop(0, "rgba(12,16,16,1)"); bg2.addColorStop(.7, "rgba(23,26,24,1)"); bg2.addColorStop(1, "rgba(6,8,8,1)");
    ctx.fillStyle = bg2; ctx.fillRect(0, 120, W, yb - 120);
    ctx.strokeStyle = "rgba(233,223,200,.18)"; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(0, yb); ctx.lineTo(W, yb); ctx.stroke();
    // ribs
    for (let i = 0; i < 5; i++) {
      const rx = 110 + i * 215;
      ctx.strokeStyle = `rgba(233,223,200,${.08 + i * .01})`; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.ellipse(rx, 560, 180, 420, 0, Math.PI * .15, Math.PI * .85); ctx.stroke();
    }
    // hatch doors
    const open = smooth(inv(.2, 1.4, lt));
    ctx.fillStyle = "rgba(10,13,13,.95)"; ctx.strokeStyle = "rgba(233,223,200,.3)";
    ctx.fillRect(120 - open * 170, 940, 410, 170); ctx.strokeRect(120 - open * 170, 940, 410, 170);
    ctx.fillRect(550 + open * 170, 940, 410, 170); ctx.strokeRect(550 + open * 170, 940, 410, 170);
    for (let i = 0; i < 4; i++) {
      ctx.strokeStyle = "rgba(180,71,47,.32)"; ctx.lineWidth = 10;
      ctx.beginPath(); ctx.moveTo(140 + i * 100 - open * 170, 955); ctx.lineTo(180 + i * 100 - open * 170, 1095); ctx.stroke();
    }
    // canisters
    const fall = easeIn(inv(1.8, 3.4, lt));
    const cy = lerp(990, 1530, fall);
    canister(ctx, 400, cy, .95, C.bone, 1, 1);
    canister(ctx, 680, cy + 20, .95, C.bone, 1, 1);
    if (fall > .12) {
      parachute(ctx, 400, cy - 300, .85, rgba(C.bone, .8), inv(.2, .7, fall), .8);
      parachute(ctx, 680, cy - 280, .85, rgba(C.bone, .8), inv(.3, .8, fall), .8);
    }
    // labels
    text(ctx, "OPTICAL BAY  /  MODIFIED", 62, 180, { family: F.mono, size: 13, tracking: 2.4, color: C.boneDim });
    labelLine(ctx, "UNIT 01  /  2.0 M", 400, cy, 540, cy - 40, C.amber, .9);
    labelLine(ctx, "UNIT 02  /  2.0 M", 680, cy + 20, 780, cy + 80, C.amber, .9);
    text(ctx, "RELEASE", 540, 900, { family: F.mono, size: 12, tracking: 4, color: C.rust, align: "center", alpha: inv(1.2, 1.6, lt) });
    ctx.restore();
  }
  // waiting
  const waitA = smooth(waitP) * (1 - smooth(inv(13.8, 14.5, lt)));
  if (waitA > .001) {
    ctx.save(); ctx.globalAlpha *= waitA * fade;
    imageCover(ctx, window.ASSETS.desert, 0, 0, W, H, .62, "none");
    ctx.fillStyle = "rgba(4,7,7,.55)"; ctx.fillRect(0, 0, W, H);
    // dunes
    const dg = ctx.createLinearGradient(0, 1100, 0, H); dg.addColorStop(0, "rgba(10,14,13,.2)"); dg.addColorStop(1, "rgba(4,6,6,.95)");
    ctx.fillStyle = dg; ctx.fillRect(0, 1050, W, 870);
    canister(ctx, 380, 1400, 1.15, C.bone, 1, 1);
    canister(ctx, 720, 1450, 1.0, C.bone, 1, 1);
    const blink = .45 + .55 * Math.abs(Math.sin(lt * 3.2));
    glowDot(ctx, 380, 1818, 30 + 8 * blink, C.rust, .5 * blink);
    glowDot(ctx, 720, 1860, 26 + 7 * blink, C.rust, .4 * blink);
    // seismic rings
    for (let i = 0; i < 3; i++) {
      const p = ((lt * .55 + i / 3) % 1);
      ctx.beginPath(); ctx.ellipse(540, 1650, 350 * p, 90 * p, 0, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(224,168,60,${.18 * (1 - p)})`; ctx.lineWidth = 1; ctx.stroke();
    }
    text(ctx, "THE DESERT IS LISTENING", 62, 380, { family: F.display, size: 62, weight: 400, tracking: 2, color: C.bone });
    text(ctx, "UNIT 01  /  UNIT 02", 62, 430, { family: F.mono, size: 13, tracking: 3, color: C.amber });
    text(ctx, "WAITING", 62, 1820, { family: F.mono, size: 15, tracking: 3, color: C.boneDim });
    ctx.restore();
  }
  if (fade < 1) { ctx.fillStyle = `rgba(0,0,0,${1 - fade})`; ctx.fillRect(0, 0, W, H); }
}

/* ---------- scene 5 : test ---------- */
function sceneTest(ctx, t) {
  const lt = t - 47.20;
  const fade = lt < .3 ? lt / .3 : lt > 7.95 ? (8.4 - lt) / .45 : 1;
  bg(ctx, "#080b0a", "#050707", "#6b4a24", .5, .52, .12);
  // desert plate
  const zoom = 1.03 + .05 * easeOut(inv(0, 7.9, lt));
  ctx.save(); ctx.globalAlpha *= fade;
  ctx.translate(W / 2, 960); ctx.scale(zoom, zoom); ctx.translate(-W / 2, -960);
  imageCover(ctx, window.ASSETS.desert, -40, 120, W + 80, 1680, .78, "none");
  ctx.restore();
  ctx.save(); ctx.globalAlpha *= fade * .35;
  imageCover(ctx, window.ASSETS.contours, 0, 300, W, 1300, .26, "none");
  ctx.restore();
  // dark framing
  const dg = ctx.createLinearGradient(0, 0, 0, H);
  dg.addColorStop(0, "rgba(4,6,6,.92)"); dg.addColorStop(.35, "rgba(4,6,6,.25)");
  dg.addColorStop(.72, "rgba(4,6,6,.3)"); dg.addColorStop(1, "rgba(3,5,5,.95)");
  ctx.fillStyle = dg; ctx.fillRect(0, 0, W, H);
  metaTop(ctx, "TEST 596  /  LOP NUR", "17 JUN 1967", .9 * fade);
  // targeting HUD
  const hudA = fade * (1 - .6 * inv(5.3, 6.4, lt));
  ctx.save(); ctx.globalAlpha *= hudA;
  corner(ctx, 70, 470, W - 140, 900, 34, C.bone, 1.2, .45);
  crosshair(ctx, 540, 1000, 54, rgba(C.bone, .55), .8, 1);
  text(ctx, "TARGET  /  AREA D", 90, 520, { family: F.mono, size: 12, tracking: 2.6, color: C.boneDim });
  text(ctx, "40.812° N   89.790° E", 90, 544, { family: F.mono, size: 12, tracking: 2.2, color: C.boneDim });
  text(ctx, "08:20  LOCAL", W - 90, 520, { family: F.mono, size: 12, tracking: 2.6, color: C.amber, align: "right" });
  text(ctx, "H-6  /  ALT 10,000 M", W - 90, 544, { family: F.mono, size: 12, tracking: 2.2, color: C.boneDim, align: "right" });
  ctx.restore();
  // title
  text(ctx, "17 JUNE 1967", 62, 380, { family: F.display, size: 76, weight: 400, tracking: 4, color: C.bone, alpha: easeOut(inv(.1, 1.0, lt)) * fade });
  // bomber
  if (lt > 1.1) {
    const bp = easeOut(inv(1.1, 2.6, lt));
    const bx = lerp(-160, 420, bp), by = 730;
    ctx.save(); ctx.globalAlpha *= fade;
    ctx.translate(bx, by); ctx.scale(.86, .86);
    h6SidePath(ctx); ctx.fillStyle = "rgba(6,9,9,.92)"; ctx.fill();
    ctx.strokeStyle = rgba(C.bone, .65); ctx.lineWidth = 1.6; ctx.stroke();
    // engines
    for (const ex of [-10, 90]) {
      ctx.beginPath(); ctx.ellipse(ex, 30, 20, 8, .1, 0, 7); ctx.fillStyle = "rgba(224,168,60,.5)"; ctx.fill();
    }
    ctx.restore();
    text(ctx, "H-6  /  BOMBER", 500, 690, { family: F.mono, size: 12, tracking: 2.2, color: C.boneDim, alpha: bp * fade });
  }
  // bomb fall
  if (lt > 3.1 && lt < 6.6) {
    const bp = easeIn(inv(3.1, 6.52, lt));
    const bx = 540, by = lerp(790, 1150, bp);
    const sc = lerp(.9, .45, bp);
    ctx.save(); ctx.translate(bx, by); ctx.rotate(-.08); ctx.scale(sc, sc); ctx.globalAlpha *= fade;
    ctx.fillStyle = "rgba(8,11,11,.95)"; ctx.strokeStyle = rgba(C.bone, .7); ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.ellipse(0, 0, 16, 66, 0, 0, 7); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(-14, 50); ctx.lineTo(-34, 78); ctx.lineTo(-16, 70); ctx.lineTo(0, 84);
    ctx.lineTo(16, 70); ctx.lineTo(34, 78); ctx.lineTo(14, 50); ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.restore();
    text(ctx, "639", 610, by, { family: F.mono, size: 12, tracking: 2, color: C.amber, alpha: fade });
    const alt = Math.round(lerp(9000, 3000, bp) / 100) * 100;
    text(ctx, `${alt.toLocaleString()} M`, 90, 1480, { family: F.mono, size: 18, tracking: 2, color: C.bone, alpha: fade });
    text(ctx, "RELEASE", 90, 1506, { family: F.mono, size: 11, tracking: 2.4, color: C.rust, alpha: fade });
  }
  // flash
  const flash = inv(6.52, 6.64, lt) * (1 - inv(6.72, 7.05, lt));
  if (flash > 0) {
    ctx.save(); ctx.globalAlpha *= fade;
    const fg = ctx.createRadialGradient(540, 1150, 0, 540, 1150, 900);
    fg.addColorStop(0, `rgba(255,250,238,${flash})`); fg.addColorStop(.4, `rgba(255,226,180,${flash * .9})`);
    fg.addColorStop(1, `rgba(224,168,60,0)`);
    ctx.fillStyle = fg; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = `rgba(255,248,232,${flash * .55})`; ctx.fillRect(0, 0, W, H);
    ctx.restore();
  }
  // shockwave
  if (lt > 6.52) {
    const sp = inv(6.52, 8.3, lt);
    ctx.save(); ctx.globalAlpha *= fade;
    for (let i = 0; i < 4; i++) {
      const p = clamp(sp - i * .08);
      if (p <= 0) continue;
      const r = 90 + p * 620;
      ctx.beginPath(); ctx.ellipse(540, 1150, r, r * .28, 0, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(233,223,200,${.35 * (1 - p)})`; ctx.lineWidth = 2.5 * (1 - p) + .4; ctx.stroke();
    }
    // dust
    for (let i = 0; i < 60; i++) {
      const a = hash(i) * Math.PI * 2, r = 40 + sp * (90 + hash(i + 4) * 420);
      const x = 540 + Math.cos(a) * r, y = 1150 + Math.sin(a) * r * .26 - sp * hash(i + 9) * 140;
      const al = (1 - sp) * .35 * hash(i + 2);
      ctx.fillStyle = `rgba(224,196,150,${al})`;
      ctx.beginPath(); ctx.arc(x, y, 1 + hash(i + 6) * 6 * (1 - sp), 0, 7); ctx.fill();
    }
    ctx.restore();
  }
  // yield
  if (lt > 6.7) {
    const p = easeOut4(inv(6.7, 7.4, lt));
    ctx.save(); ctx.globalAlpha *= fade;
    ctx.fillStyle = `rgba(4,6,6,${.84 * p})`; ctx.fillRect(64, 652, 700, 86);
    text(ctx, "THE SKY TURNS WHITE.", 88, 710, { family: F.mono, size: 27, weight: 500, tracking: 3.0, color: C.bone, alpha: p });
    text(ctx, "3.3", 62, 1650, { family: F.display, size: 190, weight: 500, tracking: 0, color: C.bone, alpha: p });
    text(ctx, "MEGATONS", 70, 1700, { family: F.mono, size: 16, tracking: 4, color: C.amber, alpha: p });
    text(ctx, "TEST 639  /  THERMONUCLEAR", 70, 1740, { family: F.mono, size: 12, tracking: 2.2, color: C.boneDim, alpha: p });
    // seismo
    seismo(ctx, 540, 1580, 450, 120, inv(6.8, 8.25, lt), rgba(C.amber, .8), p, 3);
    text(ctx, "SEISMIC  /  EVENT", 540, 1700, { family: F.mono, size: 11, tracking: 2.2, color: C.boneDim, alpha: p });
    ctx.restore();
  }
  if (fade < 1) { ctx.fillStyle = `rgba(0,0,0,${1 - fade})`; ctx.fillRect(0, 0, W, H); }
}

/* ---------- scene 6 : signal ---------- */
function sceneSignal(ctx, t) {
  const lt = t - 55.60;
  const fade = lt < .35 ? lt / .35 : lt > 5.95 ? (6.4 - lt) / .45 : 1;
  bg(ctx, "#070909", "#040606", "#254b3f", .68, .4, .16);
  metaTop(ctx, "SIGNAL INTELLIGENCE  /  TAIPEI", "JUL 1967", .8 * fade);
  // tape reels
  const rot = lt * 1.7;
  tapeReel(ctx, 170, 320, 82, rot, rgba(C.bone, .35), fade);
  tapeReel(ctx, 360, 320, 62, rot * 1.25, rgba(C.bone, .25), fade);
  ctx.save(); ctx.globalAlpha *= fade;
  text(ctx, "SIX WEEKS LATER", 62, 470, { family: F.display, size: 82, weight: 400, tracking: 2, color: C.bone, alpha: easeOut(inv(.2, 1.2, lt)) });
  text(ctx, "THE SENSORS ANSWER", 64, 514, { family: F.mono, size: 14, tracking: 3.4, color: C.amber, alpha: easeOut(inv(.5, 1.3, lt)) });
  ctx.restore();
  // waveform panel
  const wp = easeOut(inv(.6, 2.4, lt));
  ctx.save(); ctx.globalAlpha *= fade;
  ctx.fillStyle = "rgba(4,7,7,.72)"; ctx.fillRect(62, 570, 956, 260);
  ctx.strokeStyle = "rgba(233,223,200,.14)"; ctx.strokeRect(62, 570, 956, 260);
  text(ctx, "RECEIVER  02  /  FILTERED", 84, 604, { family: F.mono, size: 11, tracking: 2.2, color: C.boneDim });
  text(ctx, "CHANNEL 7  /  0.4–8 HZ", W - 84, 604, { family: F.mono, size: 11, tracking: 2.2, color: C.boneDim, align: "right" });
  seismo(ctx, 92, 710, 896, 88, wp, rgba(C.jade, .85), wp, 7);
  text(ctx, "T+ 41 DAYS", 84, 790, { family: F.mono, size: 11, tracking: 2.2, color: C.amber, alpha: wp });
  ctx.restore();
  // map signal path
  const mp = easeOut(inv(1.4, 3.0, lt));
  if (mp > 0) {
    const box = { x: 120, y: 900, w: 840, h: 580 };
    const P = projectFactory(box);
    ctx.save(); ctx.globalAlpha *= fade * mp;
    if (window.CACHE && window.CACHE.signal) ctx.drawImage(window.CACHE.signal, 0, 0);
    else drawAsia(ctx, box, .85, .38, true);
    const a = P(89.79, 40.81), b = P(121.56, 25.03);
    const arc = [];
    for (let i = 0; i <= 60; i++) {
      const u = i / 60;
      arc.push([lerp(a.x, b.x, u), lerp(a.y, b.y, u) - Math.sin(u * Math.PI) * 120]);
    }
    ctx.strokeStyle = rgba(C.amber, .65); ctx.lineWidth = 1.5; ctx.setLineDash([4, 7]);
    polygon(ctx, arc, false); ctx.stroke(); ctx.setLineDash([]);
    const pulse = (lt * .55) % 1;
    const pp = pointAlong(arc, pulse);
    glowDot(ctx, pp[0], pp[1], 28, C.amber, .4);
    ctx.fillStyle = C.amber; ctx.beginPath(); ctx.arc(pp[0], pp[1], 3.2, 0, 7); ctx.fill();
    mapPin(ctx, P, 89.79, 40.81, "LOP NUR", "SENSOR", C.rust, 1, "left");
    mapPin(ctx, P, 121.56, 25.03, "TAIPEI", "RECEIVER", C.jade, 1, "right");
    text(ctx, "SIGNAL PATH  /  3,400 KM", 140, 1470, { family: F.mono, size: 11, tracking: 2.2, color: C.boneDim });
    ctx.restore();
  }
  // confirmation
  const cp = easeOut4(inv(3.1, 3.8, lt));
  if (cp > 0) {
    ctx.save(); ctx.globalAlpha *= fade;
    ctx.translate(730, 1100); ctx.rotate(-.08);
    ctx.strokeStyle = rgba(C.rust, .9 * cp); ctx.lineWidth = 3;
    ctx.strokeRect(-170, -42, 340, 84);
    text(ctx, "CONFIRMED", 0, 14, { family: F.mono, size: 34, weight: 500, tracking: 5, color: rgba(C.rust, .95 * cp), align: "center" });
    ctx.restore();
  }
  // bottom data
  const dp = easeOut(inv(3.3, 4.4, lt));
  if (dp > 0) {
    ctx.save(); ctx.globalAlpha *= fade * dp;
    ctx.fillStyle = "rgba(5,8,8,.72)"; ctx.fillRect(62, 1530, 956, 260);
    ctx.strokeStyle = "rgba(233,223,200,.14)"; ctx.strokeRect(62, 1530, 956, 260);
    text(ctx, "EVENT", 86, 1570, { family: F.mono, size: 11, tracking: 2.4, color: C.boneDim });
    text(ctx, "THERMONUCLEAR", 86, 1604, { family: F.mono, size: 22, tracking: 2.2, color: C.bone });
    text(ctx, "YIELD", 600, 1570, { family: F.mono, size: 11, tracking: 2.4, color: C.boneDim });
    text(ctx, "3.3 MT", 600, 1604, { family: F.mono, size: 22, tracking: 2.2, color: C.amber });
    text(ctx, "THE SIGNAL IS SMALL.", 86, 1710, { family: F.display, size: 48, weight: 400, tracking: 1, color: C.bone });
    text(ctx, "THE MEANING IS NOT.", 86, 1756, { family: F.display, size: 48, weight: 500, tracking: 1, color: C.bone });
    ctx.restore();
  }
  if (fade < 1) { ctx.fillStyle = `rgba(0,0,0,${1 - fade})`; ctx.fillRect(0, 0, W, H); }
}

/* ---------- scene 7 : coda ---------- */
function sceneCoda(ctx, t) {
  const lt = t - 62.00;
  const fade = lt < .4 ? lt / .4 : lt > 6.2 ? (6.6 - lt) / .4 : 1;
  bg(ctx, "#040606", "#020303", "#2f3f35", .5, .6, .10);
  stars(ctx, window.ASSETS.stars, t, .75);
  metaTop(ctx, "EPILOGUE  /  1974", "PROJECT RAZOR", .6 * fade);
  const docP = inv(1.7, 2.6, lt);
  const desertP = inv(3.6, 4.6, lt);
  const endP = inv(5.1, 5.9, lt);
  // departing aircraft
  const p1 = easeInOut(inv(0, 3.4, lt));
  ctx.save(); ctx.globalAlpha *= fade * (1 - .7 * docP);
  drawU2Top(ctx, lerp(200, 780, p1), lerp(1520, 640, p1), .10, rgba(C.bone, .65), "rgba(4,6,6,.9)", 1.3, 1);
  glowDot(ctx, lerp(200, 780, p1) - 18, lerp(1520, 640, p1), 32, C.amber, .18);
  text(ctx, "1974", 62, 380, { family: F.display, size: 130, weight: 500, tracking: 2, color: C.bone, alpha: easeOut(inv(.2, 1.2, lt)) });
  text(ctx, "THE FLIGHTS END", 66, 426, { family: F.mono, size: 13, tracking: 3.2, color: C.boneDim, alpha: easeOut(inv(.4, 1.2, lt)) });
  ctx.restore();
  // document
  if (docP > 0) {
    ctx.save(); ctx.globalAlpha *= fade * easeOut(docP) * (1 - .92 * easeOut(desertP));
    docSheet(ctx, window.ASSETS.paper, 540, 1050, 760, 980, -.035, 1, 5, "CLOSED");
    text(ctx, "PROJECT RAZOR  /  TERMINATED", 170, 1560, { family: F.mono, size: 12, tracking: 2.2, color: C.rust, alpha: docP });
    text(ctx, "THE PLANES GO HOME.", 170, 1610, { family: F.display, size: 52, weight: 400, tracking: 1, color: "#241f17", alpha: docP });
    ctx.restore();
  }
  // desert coda
  if (desertP > 0) {
    ctx.save(); ctx.globalAlpha *= fade * easeOut(desertP) * (1 - endP * .65);
    imageCover(ctx, window.ASSETS.desert, 0, 0, W, H, .55, "none");
    ctx.fillStyle = "rgba(3,5,5,.6)"; ctx.fillRect(0, 0, W, H);
    for (let i = 0; i < 2; i++) {
      const x = i ? 670 : 410, y = i ? 1480 : 1430;
      canister(ctx, x, y, 1.0, rgba(C.bone, .8), 1, .9);
      const blink = .3 + .7 * Math.abs(Math.sin(lt * 2.2 + i * 1.7));
      glowDot(ctx, x, y + 132, 22 + 6 * blink, C.rust, .45 * blink);
    }
    text(ctx, "THE DESERT", 62, 390, { family: F.display, size: 76, weight: 400, tracking: 2, color: C.bone, alpha: easeOut(desertP) });
    text(ctx, "KEEPS THE REST.", 62, 466, { family: F.display, size: 76, weight: 500, tracking: 2, color: C.bone, alpha: easeOut(inv(3.9, 4.6, lt)) });
    ctx.restore();
  }
  // end card
  if (endP > 0) {
    ctx.save(); ctx.globalAlpha *= fade;
    ctx.fillStyle = `rgba(3,5,5,${.94 * easeOut(endP)})`; ctx.fillRect(0, 0, W, H);
    const cx = W / 2;
    text(ctx, "TABASCO", cx, 880, { family: F.display, size: 150, weight: 500, tracking: 8, color: C.bone, align: "center", alpha: easeOut(inv(5.2, 6.0, lt)) });
    ruled(ctx, cx - 230, 930, 460, C.bone, .3, 1);
    text(ctx, "LOP NUR  /  XINJIANG  /  1967", cx, 976, { family: F.mono, size: 15, tracking: 4, color: C.boneDim, align: "center", alpha: easeOut(inv(5.4, 6.1, lt)) });
    text(ctx, "A RECONSTRUCTION FROM DECLASSIFIED RECORDS", cx, 1040, { family: F.mono, size: 11, tracking: 2.4, color: rgba(C.boneDim, .8), align: "center", alpha: easeOut(inv(5.6, 6.2, lt)) });
    text(ctx, "CIA U-2 / OXCART HISTORY  ·  ROCAF 35TH SQUADRON  ·  TAIPEI TIMES  ·  NATIONAL SECURITY ARCHIVE", cx, 1780, { family: F.mono, size: 9, tracking: 1.2, color: rgba(C.boneDim, .55), align: "center", alpha: easeOut(inv(5.8, 6.3, lt)) });
    ctx.restore();
  }
  if (fade < 1) { ctx.fillStyle = `rgba(0,0,0,${1 - fade})`; ctx.fillRect(0, 0, W, H); }
}

window.SCENES = {
  open: sceneOpen, cats: sceneCats, problem: sceneProblem, plan: scenePlan,
  test: sceneTest, signal: sceneSignal, coda: sceneCoda
};
