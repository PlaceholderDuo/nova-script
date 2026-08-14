/**
 * 04-error-shorts.spec.js — the "did you hit the panic button wrong" spec.
 * A gig is full of near-misses: spurious taps, double-taps, held pads,
 * weird quick combos, presses that land on "nothing". The controller must
 * absorb them without locking up, flashing garbage, or leaving the screen
 * stuck in a partial catalog. Each test ends asserting the engine is still
 * alive and the screen is coherent again.
 */

const { test, expect } = require('@playwright/test');
const { openLivePage } = require('../helpers');
const {
  ledColor, tapPad, tapTopRow, holdPad, padDown, padUp, wsAction,
  waitForColor, waitForMode, normalizeHome,
} = require('../lib/ledger');

test.describe('Error shorts & edge handling', () => {
  let page;

  test.beforeAll(async ({ browser }) => {
    page = await openLivePage(browser);
    // The engine is shared across spec files (one stack per run), so we can't
    // assume anything about its screen. Press HOME (200) and reset the GTR
    // fader to its default step before the whole describe runs.
    await normalizeHome(page);
  });

  test.afterAll(async () => {
    if (page) await page.close();
  });

  test('a double-tap on a volume pad is stable (no double-fire)', async () => {
    // Double-tap the GTR fader (2x press_release). The pad should settle on
    // its toggle state, not skip two levels or flicker.
    await tapPad(page, 0, 3);
    await page.waitForTimeout(80);
    await tapPad(page, 0, 3);
    await waitForColor(page, 0, 3, 'GREEN_HIGH', { timeoutMs: 1500 });
    // Still alive and on performance.
    await waitForMode(page, 'performance');
  });

  test('a held pad then release is treated as a single press', async () => {
    // Hold a VOX fader pad for 450ms (well past the 120ms press flash, under
    // the 500ms long-press threshold) then release. It must apply ONCE and
    // settle to the expected colour for that press.
    await padDown(page, 4, 3);
    await page.waitForTimeout(300);
    await wsAction(page, { action: 'pad_up', x: 4, y: 3 });
    // After a hold on the fader pad, the pad reads AMBER (sub-step ON).
    await waitForColor(page, 4, 3, 'AMBER_HIGH', { timeoutMs: 1500 });
    await waitForMode(page, 'performance');
  });

  test('rapid repeated taps do not wedge the engine', async () => {
    // Mash a bunch of pads quickly — the classic "stage doesn't respond,
    // so play smashes the grid" scenario.
    const coords = [[1, 3], [2, 2], [5, 4], [6, 1], [7, 6], [3, 5], [0, 1]];
    for (const [x, y] of coords) await tapPad(page, x, y);
    await page.waitForTimeout(400);

    // Engine must still answer and accept new input.
    await tapPad(page, 0, 7);
    await page.waitForTimeout(150);
    const c = await ledColor(page, 0, 7);
    expect(c).not.toBeNull();
    await waitForMode(page, 'performance');
  });

  test('unknown WS action is ignored without killing the page WS', async () => {
    // Test 3 (rapid taps) left the GTR fader wherever the taps put it —
    // reset to a known home before asserting fixed pad colours.
    await normalizeHome(page);
    await wsAction(page, { action: 'does_not_exist', x: 1, y: 1 });
    await page.waitForTimeout(200);
    // The backend still serves state and the engine still answers presses:
    // a known action (switch to mixer, then home) round-trips fully.
    await tapTopRow(page, 4);                       // 204 → mixer
    await waitForColor(page, 0, 4, 'GREEN_HIGH', { timeoutMs: 3000 });
    await tapTopRow(page, 0);                       // home
    await waitForColor(page, 0, 3, 'GREEN_HIGH', { timeoutMs: 3000 });
    await waitForMode(page, 'performance');
  });

  test('sequencer survives garbage taps and returns home', async () => {
    await normalizeHome(page);
    await tapTopRow(page, 3);                       // → sequencer
    await waitForColor(page, 0, 7, 'GREEN_HIGH', { timeoutMs: 3000 });

    // Random taps all over the 8×8 (including edges).
    for (let x = 0; x < 8; x += 3) {
      for (let y = 0; y < 8; y += 2) await tapPad(page, x, y);
    }
    // Home should bring us back intact.
    await normalizeHome(page);
    await waitForMode(page, 'performance');
  });
});