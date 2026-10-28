const puppeteer = require("puppeteer-core");
const fs = require("fs");
const path = require("path");
(async () => {
  const total = parseInt(process.argv[2] || "1646", 10);
  const start = parseInt(process.argv[3] || "0", 10);
  const dir = "render/frames";
  fs.mkdirSync(dir, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: "/usr/local/bin/google-chrome", headless: "new",
    args: ["--no-sandbox", "--enable-unsafe-swiftshader", "--use-angle=swiftshader",
      "--disable-gpu-sandbox", "--hide-scrollbars", "--allow-file-access-from-files",
      "--force-device-scale-factor=1", "--disable-dev-shm-usage"]
  });
  const page = await browser.newPage();
  page.on("pageerror", e => console.log("PAGEERROR", e.message));
  page.on("console", m => { if (m.type() === "error" && !m.text().includes("favicon")) console.log("CONSOLE", m.text()); });
  await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });
  await page.goto("http://127.0.0.1:8000/engine/index.html", { waitUntil: "load" });
  await page.waitForFunction("window.READY === true", { timeout: 60000 });
  const t0 = Date.now();
  for (let f = start; f < total; f++) {
    const out = path.join(dir, `f${String(f).padStart(5, "0")}.png`);
    if (fs.existsSync(out) && fs.statSync(out).size > 1000) continue;
    await page.evaluate(t => window.renderAt(t), f / 24);
    await page.screenshot({ path: out, type: "png", optimizeForSpeed: true });
    if (f % 20 === 0) {
      const el = (Date.now() - t0) / 1000;
      const rate = (f - start + 1) / Math.max(el, .01);
      console.log(`frame ${f}/${total}  ${rate.toFixed(2)} fps  eta ${((total - f) / rate / 60).toFixed(1)} min`);
      fs.writeFileSync("render/progress.json", JSON.stringify({ frame: f, total, fps: rate, at: Date.now() }));
    }
  }
  console.log("DONE");
  await browser.close();
})();
