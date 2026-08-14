/**
 * ledger.js — DOM-level helpers to read/click the virtualizer page and assert
 * what the LEDs SHOULD be showing.
 *
 * The virtualizer renders the Launchpad as an 8×8 grid of `.pad` DOM nodes.
 * The Python backend writes each pad's `title` attribute every time a real
 * MIDI LED message arrives: title = "[<x>,<y>] <COLOR>". That title IS the
 * ground truth — it only gets updated when the engine actually sent an LED
 * update. Reading titles beats parsing CSS, and lets timing tests measure
 * colour dwell without pixel-diff fragility.
 *
 * COORDINATE CONVENTION
 * ---------------------
 * All helpers take APP coordinates (x, y) where (0,0) is BOTTOM-LEFT, exactly
 * like the physical Launchpad and everything in nova-script. The virtualizer
 * DOM draws rows with y increasing UP the page, so our padIndex() flips:
 *     dom_row = 7 - y
 * This keeps test code reading like you're pressing the real hardware.
 */

const { expect } = require('@playwright/test');

const TITLE_RE = /^\[(\d+),(\d+)\]\s?(.*)/;

/** App (x,y) → DOM pad index (DOM rows run top-to-bottom). */
function padIndex(x, y) {
  return (7 - y) * 8 + x;
}

async function padTitle(page, x, y) {
  const t = await page.locator('.pad').nth(padIndex(x, y)).getAttribute('title');
  return t || '';
}

/** Colour NAME (e.g. "GREEN_HIGH") currently on app pad (x,y). */
async function ledColor(page, x, y) {
  const m = (await padTitle(page, x, y)).match(TITLE_RE);
  return m ? m[3].trim() : null;
}

/** Live CSS background string actually painted on the pad. */
async function ledRgb(page, x, y) {
  const idx = padIndex(x, y);
  return page.locator('.pad').nth(idx)
    .evaluate(el => getComputedStyle(el).backgroundColor);
}

/** Click a grid pad → engine sees a pad press/release. */
async function tapPad(page, x, y) {
  await page.locator('.pad').nth(padIndex(x, y)).click();
}

/** Click a top-row function button, 0-indexed (0 = leftmost). */
async function tapTopRow(page, idx) {
  await page.locator('.top-btn').nth(idx).click();
}

/** Click a right-column function button, 0-indexed (0 = top). */
async function tapRightCol(page, idx) {
  await page.locator('.col-right .col-btn').nth(idx).click();
}

/**
 * Send a raw action over the page WebSocket. This is how tests get full
 * control over press/release timing that a DOM `.click()` can't express
 * (holds, double-taps, overlapping combos). The virtualizer exposes a global
 * `send()` on the page that forwards any action to the Python backend.
 */
async function wsAction(page, action) {
  await page.evaluate((a) => window.send(a), action);
}

/** Press a grid pad DOWN only (must pair with padUp later). */
async function padDown(page, x, y) {
  await wsAction(page, { action: 'pad_down', x, y });
}

/** Release a held grid pad. */
async function padUp(page, x, y) {
  await wsAction(page, { action: 'pad_up', x, y });
}

/** Hold a pad down for holdMs, then release — mimics a long press. */
async function holdPad(page, x, y, holdMs) {
  await padDown(page, x, y);
  await page.waitForTimeout(holdMs);
  await padUp(page, x, y);
}

/** Press a top-row button DOWN only (pair with topRowUp later). */
async function topRowDown(page, idx) {
  await wsAction(page, { action: 'top_down', index: idx });
}

/** Release a held top-row button. */
async function topRowUp(page, idx) {
  await wsAction(page, { action: 'top_up', index: idx });
}

/** Hold a top-row button down for holdMs, then release. */
async function holdTopRow(page, idx, holdMs) {
  await topRowDown(page, idx);
  await page.waitForTimeout(holdMs);
  await topRowUp(page, idx);
}

/** Press a right-column button DOWN only (pair with rightColUp later). */
async function rightColDown(page, idx) {
  await wsAction(page, { action: 'right_down', index: idx });
}

/** Release a held right-column button. */
async function rightColUp(page, idx) {
  await wsAction(page, { action: 'right_up', index: idx });
}

/**
 * Hold a right-column button down for holdMs, then release. Long-presses
 * trigger things like ARP-edit entry (E) and slot saves in arp_edit, which a
 * plain `.click()` release can't express.
 */
async function holdRightCol(page, idx, holdMs) {
  await rightColDown(page, idx);
  await page.waitForTimeout(holdMs);
  await rightColUp(page, idx);
}

/** Assert the pad's logical colour equals the expected LogicalColor name. */
async function expectLedColor(page, x, y, colorName, label = '') {
  const actual = await ledColor(page, x, y);
  expect(actual, `${label} pad(${x},${y}) should be ${colorName}, saw ${actual}`)
    .toBe(colorName);
}

/**
 * Poll until a pad reaches a target colour (sampling the live DOM).
 * Essential for tblinking/animating glyphs: beat flash, screensaver, tuner.
 */
async function waitForColor(page, x, y, colorName, { timeoutMs = 2000 } = {}) {
  const deadline = Date.now() + timeoutMs;
  let last = null;
  while (Date.now() < deadline) {
    last = await ledColor(page, x, y);
    if (last === colorName) return true;
    await page.waitForTimeout(25);
  }
  throw new Error(`pad (${x},${y}) never became ${colorName} in ${timeoutMs}ms (last: ${last})`);
}

/**
 * Sample a pad's colour for a window and return dwell times per colour:
 *   { "<COLOR>": ms, "<COLOR>": ms }
 * Ideal for timing checks (beat LED period, tuner strobe speed, text scroll).
 */
async function measureDwell(page, x, y, { windowMs = 2000, sampleMs = 20 } = {}) {
  const dwell = {};
  const start = Date.now();
  let last = await padTitle(page, x, y);
  let lastAt = start;

  const sample = async () => {
    const now = Date.now();
    const cur = await padTitle(page, x, y);
    if (cur !== last) {
      dwell[last] = (dwell[last] || 0) + (now - lastAt);
      last = cur;
      lastAt = now;
    }
  };

  while (Date.now() - start < windowMs) {
    await sample();
    await page.waitForTimeout(sampleMs);
  }
  await sample();
  dwell[last] = (dwell[last] || 0) + (Date.now() - lastAt);
  return dwell;
}

/** Number of distinct colour transitions on a pad within a window. */
async function blinkCount(page, x, y, { windowMs = 1000 } = {}) {
  const dwell = await measureDwell(page, x, y, { windowMs });
  const named = Object.entries(dwell).filter(([c]) => c && c !== '[?,?]');
  return Math.max(0, named.length - 1);
}

/**
 * Read the LIVE state snapshot the backend broadcasts (the page's `state`
 * variable). The engine's "mode" name is sent back by the virtualizer when
 * the engine announces it, so this is the ground-truth "which screen am I
 * on" answer — better than inferring from pad colours alone.
 */
async function currentMode(page) {
  return page.evaluate(() => (typeof state !== 'undefined' && state && state.mode) || '');
}

/**
 * Snapshot of the Akai Force MIDI capture (the note stream the engine sends
 * out). The virtualizer exposes a virtual "Akai Force" port and records every
 * note-on/note-off with a monotonic timestamp since the last clear:
 *   [{ type: "note_on"|"note_off", note: 60, vel: 100, t: 0.125 }, ...]
 */
async function midiLog(page) {
  return page.evaluate(() => (typeof state !== 'undefined' && state && state.midi_log) || []);
}

/**
 * Reset the Force MIDI capture log (and its timestamp base) so tests can
 * assert on a clean note stream. Waits until the PAGE's copy of the log is
 * cleared AND stays quiet for a moment — re-clearing if anything (e.g. a
 * slow-arriving note-off from a previous test) shows up in the window.
 */
async function clearMidi(page, { timeoutMs = 4000 } = {}) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const log = await midiLog(page);
    if (Array.isArray(log) && log.length === 0) {
      await page.waitForTimeout(250);             // let in-flight events land
      const again = await midiLog(page);
      if (Array.isArray(again) && again.length === 0) return;
    }
    await wsAction(page, { action: 'clear_midi' });  // drop any stragglers
    await page.waitForTimeout(20);
  }
  const stuck = await midiLog(page);
  throw new Error(`MIDI log never settled clear (events at timeout: ${stuck.length}: ${JSON.stringify(stuck.slice(-3))})`);
}

/**
 * Poll until the Force MIDI capture contains at least `count` note events.
 */
async function waitForMidi(page, count, { timeoutMs = 3000 } = {}) {
  const deadline = Date.now() + timeoutMs;
  let last = 0;
  while (Date.now() < deadline) {
    const log = await midiLog(page);
    if (log.length >= count) return log;
    last = log.length;
    await page.waitForTimeout(50);
  }
  throw new Error(`MIDI capture never reached ${count} events in ${timeoutMs}ms (last: ${last})`);
}

/**
 * Poll for a given mode name. The engine announces its mode to the
 * virtualizer via the virt-sync loop, which only runs once per second, so the
 * backend's `set_info` broadcast can trail an instant LED re-render by up to
 * ~1s.
 */
async function waitForMode(page, mode, { timeoutMs = 3000 } = {}) {
  const deadline = Date.now() + timeoutMs;
  let last = '';
  while (Date.now() < deadline) {
    last = await currentMode(page);
    if (last === mode) return true;
    await page.waitForTimeout(100);
  }
  throw new Error(`mode never became ${mode} in ${timeoutMs}ms (last: ${last || 'none'})`);
}

/**
 * Top-row LED colour (0-indexed, 0 = leftmost). Uses backend truth `state`.
 * `state` is a module-scoped `let` on the page (not on `window`), so we guard
 * with `typeof state !== 'undefined'` — referencing it via `window.state`
 * throws and returns ''.
 */
async function topLedColor(page, idx) {
  return page.evaluate((i) => {
    const s = (typeof state !== 'undefined') ? state : null;
    return (s && s.top_row && s.top_row[i]) || '';
  }, idx);
}

/** Right-column LED colour (0-indexed, 0 = top). Uses backend truth `state`. */
async function rightLedColor(page, idx) {
  return page.evaluate((i) => {
    const s = (typeof state !== 'undefined') ? state : null;
    return (s && s.right_col && s.right_col[i]) || '';
  }, idx);
}

/**
 * Poll until a right-column LED reaches a target colour (sampling the live
 * DOM). Right-column LEDs are driven by mode renders (e.g. ARP on/off, scale
 * name, hold state), so this waits for the backend broadcast to catch up.
 */
async function waitForRightLed(page, idx, colorName, { timeoutMs = 2000 } = {}) {
  const deadline = Date.now() + timeoutMs;
  let last = null;
  while (Date.now() < deadline) {
    last = await rightLedColor(page, idx);
    if (last === colorName) return true;
    await page.waitForTimeout(25);
  }
  throw new Error(`right col ${idx} never became ${colorName} in ${timeoutMs}ms (last: ${last})`);
}

/**
 * Poll until a top-row LED reaches a target colour (sampling the live DOM).
 */
async function waitForTopLed(page, idx, colorName, { timeoutMs = 2000 } = {}) {
  const deadline = Date.now() + timeoutMs;
  let last = null;
  while (Date.now() < deadline) {
    last = await topLedColor(page, idx);
    if (last === colorName) return true;
    await page.waitForTimeout(25);
  }
  throw new Error(`top row ${idx} never became ${colorName} in ${timeoutMs}ms (last: ${last})`);
}

/**
 * Force the rig back to a fresh, known performance screen: HOME (200), then
 * reset the GTR fader to its default full step (pad (0,3) GREEN_HIGH).
 *
 * Must be IDEMPOTENT: earlier stress tests move the fader, but if it is
 * ALREADY sitting on the default full step, a single tap on (0,3) flips it
 * to the fine sub-step (AMBER_HIGH) instead of confirming GREEN. So if a tap
 * lands on AMBER we tap once more to come back to the full step.
 */
async function normalizeHome(page, { timeoutMs = 4000 } = {}) {
  await tapTopRow(page, 0);
  await waitForMode(page, 'performance', { timeoutMs });
  for (let i = 0; i < 6; i++) {
    await tapPad(page, 0, 3);
    await page.waitForTimeout(300);   // let press feedback + render land
    const c = await ledColor(page, 0, 3);
    if (c === 'GREEN_HIGH') return true;
    // AMBER = it was already on the full step and we flipped to the fine
    // sub-step; anything else = not at step 3. Keep tapping until GREEN.
  }
  throw new Error(`normalizeHome: GTR fader never settled GREEN at (0,3) (last: ${await ledColor(page, 0, 3)})`);
}

module.exports = {
  readPad: padTitle,
  ledColor, ledRgb, expectLedColor, waitForColor,
  holdPad, padDown, padUp, topRowDown, topRowUp, holdTopRow, wsAction,
  rightColDown, rightColUp, holdRightCol,
  tapPad, tapTopRow, tapRightCol, padIndex,
  currentMode, waitForMode,
  measureDwell, blinkCount,
  topLedColor, rightLedColor, waitForRightLed, waitForTopLed,
  midiLog, clearMidi, waitForMidi,
  normalizeHome,
};