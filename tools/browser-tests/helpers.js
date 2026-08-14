/**
 * helpers.js — the shared "open a fresh browser page against the live
 * virtualizer" fixture used by every spec.
 *
 * WHY A SEPARATE FILE:
 * Every test needs the same page prologue: open the HTML from disk, wait for
 * the WebSocket to connect, wait out the ~6-second startup wave, and confirm
 * the engine is actually driving LEDs. That prologue is ~10 lines of subtle
 * async waiting — keeping it in one place means tests stay readable and the
 * prologue only needs fixing once.
 *
 * Liftoff contract (in order):
 *   1. page.goto(file:// path to novation-virtualizer.html)
 *   2. WS connects  →  #ws-dot turns dot-green
 *   3. 64 .pad nodes render
 *   4. startup wave runs ~6.5s, then the default mode paints its screen
 *   5. grid is STABLE (two consecutive dumps — 500ms apart — match), which
 *      proves the engine finished animating and settled on its mode screen
 */
const { pathToFileURL } = require('url');
const { expect } = require('@playwright/test');
const { HTML_PATH } = require('./lib/env');

/** Snapshot grid colours (y 0..7 rows × x 0..7 cols) into a comparable key. */
async function gridKey(page) {
  const titles = await page.locator('.pad').evaluateAll(els =>
    els.map(el => el.title)
  );
  return titles.join('|');
}

async function openLivePage(browser) {
  const page = await browser.newPage();

  // 1) Navigate to the virtualizer page. It's a static file that talks WS.
  await page.goto(pathToFileURL(HTML_PATH).href);
  await page.waitForTimeout(300);

  // 2) Backend must be attached.
  await page.waitForFunction(() => {
    const el = document.getElementById('ws-dot');
    return el && el.classList.contains('dot-green');
  }, { timeout: 15000 });

  // 3) Full Launchpad grid rendered.
  await expect(page.locator('.pad')).toHaveCount(64);

  // 4) Startup wave (≈6.5s) must finish BEFORE we snapshot LEDs — otherwise
  //    tests read transient wave colors. Wait for TWO stability signals:
  //      (a) some pad is lit (wave has begun),
  //      (b) the grid goes STABLE = 3 consecutive identical samples taken
  //          500ms apart. 3 samples is ~1s of unchanged screen, which clears
  //          the boot wave's continuous flicker and lands on the static mode
  //          screen even across engine/tick jitter.
  await page.waitForFunction(() => {
    const pads = document.querySelectorAll('.pad');
    return Array.from(pads).some(p => p.title && !/OFF$/.test(p.title));
  }, { timeout: 30000 });

  const stableFor = async (tries) => {
    let last = null;
    let runs = 0;
    for (let i = 0; i < tries; i++) {
      const cur = await gridKey(page);
      if (cur === last) {
        runs += 1;
        if (runs >= 3) return true;
      } else {
        runs = 1;
      }
      last = cur;
      await page.waitForTimeout(300);
    }
    return false;
  };

  const deadline = Date.now() + 20000;
  let ok = false;
  while (Date.now() < deadline) {
    ok = await stableFor(4);       // sample 4×, exit if 3 identical in a row
    if (ok) break;
    await page.waitForTimeout(500);
  }
  if (!ok) {
    throw new Error('grid never reached a stable state in 20s');
  }

  return page;
}

module.exports = { openLivePage };