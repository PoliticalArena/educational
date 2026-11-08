#!/usr/bin/env node
// Render an HTML composition (exposing window.render(t)) to a silent MP4, frame by frame.
// Set HIDE_CAPTIONS=1 to render without burned-in captions.
// Usage: node tools/render_reel.js <composition.html> <out.mp4> [seconds=32] [fps=30]
//        node tools/render_reel.js <composition.html> --stills <dir> 1.5 6 15 ...
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

(async () => {
  const [html, out, ...rest] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto("file://" + path.resolve(html));
  await page.evaluate(() => document.fonts.ready);
  if (process.env.HIDE_CAPTIONS === "1") await page.addStyleTag({ content: "#cap{display:none!important}" });

  if (out === "--stills") {
    const [dir, ...times] = rest;
    fs.mkdirSync(dir, { recursive: true });
    for (const t of times.map(Number)) {
      await page.evaluate((x) => window.render(x), t);
      await page.screenshot({ path: path.join(dir, `t${String(t).padStart(5, "0")}.png`) });
    }
    await browser.close();
    return;
  }

  const seconds = Number(rest[0] || 32), fps = Number(rest[1] || 30), frames = Math.round(seconds * fps);
  const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps), "-c:v", "mjpeg", "-i", "-",
    "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", String(fps), out], { stdio: ["pipe", "inherit", "inherit"] });
  const t0 = Date.now();
  for (let f = 0; f < frames; f++) {
    await page.evaluate((x) => window.render(x), f / fps);
    const buf = await page.screenshot({ type: "jpeg", quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
    if (f % 90 === 0) process.stdout.write(`frame ${f}/${frames} (${((Date.now() - t0) / 1000).toFixed(0)}s)\n`);
  }
  ff.stdin.end();
  await new Promise((r) => ff.on("close", r));
  await browser.close();
  console.log(`wrote ${out}`);
})();
