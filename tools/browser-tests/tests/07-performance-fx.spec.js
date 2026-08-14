/**
 * 07-performance-fx.spec.js — deep dive on Performance Mode's FX banks and
 * volume mute, complementing the colour/timing checks in 02.
 *
 * Layout (2 channels, vertical split):
 *   GTR → cols 0-3, VOX → cols 4-7. Each channel has a volume column
 *   (0 / 4) and 4 FX columns. FX blocks are laid out top-to-bottom:
 *
 *     y=7,6 → FX1 Delay     (preset row / disable row)
 *     y=5,4 → FX2 Harmony
 *     y=3,2 → FX3 Amp&Drv
 *     y=1,0 → FX4 Tremolo
 *
 *   disable row (bottom of each block): tap = on/off bypass.
 *     OFF state: disable row RED_MED, preset row dark.
 *     ON state:  disable row RED_HIGH; current preset AMBER_HIGH (bank 1)
 *                or RED_HIGH (bank 2), other presets GREEN_HIGH.
 *   preset row: tap a preset = select it; tap the same pad again flips the
 *     bank (preset numbers 1-3 ↔ 4-6).
 *
 *   Volume column: bottom pad twice = MUTE (whole column RED_HIGH); any
 *   fader tap unmutes.
 *
 * The engine is shared across tests, so FX on/off/preset/bank state PERSISTS
 * between tests. Every test starts from resetPerformanceFx() — a known
 * "everything bypassed" state — to stay independent and rerunnable.
 */

const { test, expect } = require('@playwright/test');
const { openLivePage } = require('../helpers');
const {
  ledColor, tapPad, tapTopRow,
  waitForColor, waitForMode, normalizeHome,
} = require('../lib/ledger');

// Per-channel FX rows, top FX first: Delay, Harmony, Amp&Drv, Tremolo.
// Rows = (FX_COUNT-1-fx_idx)*ROWS_PER_FX + sub_row, sub_row 1=preset 0=disable.
const FX_PRESET_ROWS = [7, 5, 3, 1];
const FX_DISABLE_ROWS = [6, 4, 2, 0];

/**
 * Wait for an FX disable-row pad to settle to a REAL state. Tapping an FX
 * shows a ~0.3s AMBER_HIGH hint glyph that overlaps the disable row, so a
 * naive colour read can mistake "hint showing" for "not bypassed".
 */
async function waitDisableRowStable(page, x, y, { timeoutMs = 2000 } = {}) {
  const deadline = Date.now() + timeoutMs;
  let c;
  do {
    await page.waitForTimeout(100);
    c = await ledColor(page, x, y);
  } while ((c === 'AMBER_HIGH' || c === 'OFF' || c === '') && Date.now() < deadline);
  return c;
}

/**
 * Force one FX block (cols start..start+2) to a known state: BYPASSED and
 * preset 1. Bypass leaks across tests (engine lives for the whole run), and
 * so does the selected preset — tapping the disable row alone only toggles
 * on/off, it never re-selects preset 1.
 */
async function resetFxBlock(page, start, disableRow, presetRow) {
  // 1) Ensure bypassed (disable row RED_MED).
  for (let tries = 0; tries < 4; tries++) {
    const c = await waitDisableRowStable(page, start, disableRow);
    if (c === 'RED_MED') break;
    await tapPad(page, start, disableRow);
  }
  // 2) Re-select preset 1: while bypassed, tapping preset pad 0 enables the
  //    block at preset 1, bank 1. Confirm via the disable row turning
  //    RED_HIGH — the preset row sits inside the hint-glyph rows (2-6), so
  //    waiting on it can be fooled by the transient letter.
  await tapPad(page, start, presetRow);
  await waitForColor(page, start, disableRow, 'RED_HIGH', { timeoutMs: 3000 });
  // 3) Bypass again, leaving preset = 1.
  for (let tries = 0; tries < 4; tries++) {
    const c = await waitDisableRowStable(page, start, disableRow);
    if (c === 'RED_MED') break;
    await tapPad(page, start, disableRow);
  }
}

/**
 * Force both channels back to "all FX bypassed at preset 1" + fader home.
 */
async function resetPerformanceFx(page) {
  await normalizeHome(page);
  for (const start of [1, 5]) {                  // GTR fx cols, VOX fx cols
    for (let i = 0; i < FX_PRESET_ROWS.length; i++) {
      await resetFxBlock(page, start, FX_DISABLE_ROWS[i], FX_PRESET_ROWS[i]);
    }
  }
}

test.describe('Performance mode: FX banks & mute', () => {
  let page;

  test.beforeAll(async ({ browser }) => {
    page = await openLivePage(browser);
    await resetPerformanceFx(page);
  });

  test.afterAll(async () => {
    if (page) await page.close();
  });

  test('tap on an FX disable row powers the block on', async () => {
    await resetPerformanceFx(page);

    // GTR Delay: disable row y=6, preset row y=7 (cols 1-3).
    await tapPad(page, 1, 6);

    await waitForColor(page, 1, 7, 'AMBER_HIGH', { timeoutMs: 3000 }); // preset 1 active
    await waitForColor(page, 2, 7, 'GREEN_HIGH', { timeoutMs: 3000 }); // preset 2 idle
    await waitForColor(page, 3, 7, 'GREEN_HIGH', { timeoutMs: 3000 }); // preset 3 idle
    await waitForColor(page, 1, 6, 'RED_HIGH', { timeoutMs: 3000 });  // disable row lit
  });

  test('tapping a preset in the block selects it', async () => {
    await resetPerformanceFx(page);
    await tapPad(page, 1, 6);                    // enable Delay
    await waitForColor(page, 1, 7, 'AMBER_HIGH', { timeoutMs: 3000 });

    await tapPad(page, 2, 7);                    // preset 2
    await waitForColor(page, 2, 7, 'AMBER_HIGH', { timeoutMs: 3000 });
    await waitForColor(page, 1, 7, 'GREEN_HIGH', { timeoutMs: 3000 });
    await waitForColor(page, 3, 7, 'GREEN_HIGH', { timeoutMs: 3000 });
  });

  test('re-tapping the active preset flips the bank (presets 4-6)', async () => {
    await resetPerformanceFx(page);
    await tapPad(page, 1, 6);                    // enable Delay
    await waitForColor(page, 1, 7, 'AMBER_HIGH', { timeoutMs: 3000 });
    await tapPad(page, 2, 7);                    // preset 2
    await waitForColor(page, 2, 7, 'AMBER_HIGH', { timeoutMs: 3000 });

    await tapPad(page, 2, 7);                    // same pad → bank 2, preset 5
    await waitForColor(page, 2, 7, 'RED_HIGH', { timeoutMs: 3000 }); // bank colour
    await waitForColor(page, 1, 7, 'GREEN_HIGH', { timeoutMs: 3000 });
    await waitForColor(page, 3, 7, 'GREEN_HIGH', { timeoutMs: 3000 });
  });

  test('tapping the disable row again returns the block to bypass', async () => {
    await resetPerformanceFx(page);
    await tapPad(page, 1, 6);
    await waitForColor(page, 1, 7, 'AMBER_HIGH', { timeoutMs: 3000 });

    await tapPad(page, 1, 6);                    // toggle off
    await waitForColor(page, 1, 6, 'RED_MED', { timeoutMs: 3000 });
    await waitForColor(page, 1, 7, 'OFF', { timeoutMs: 3000 });
    await waitForColor(page, 2, 7, 'OFF', { timeoutMs: 3000 });
    await waitForColor(page, 3, 7, 'OFF', { timeoutMs: 3000 });
  });

  test('VOX channel has its own FX bank, independent of GTR', async () => {
    await resetPerformanceFx(page);

    // VOX Delay lives on cols 5-7 (same rows as GTR Delay).
    await tapPad(page, 5, 6);
    await waitForColor(page, 5, 7, 'AMBER_HIGH', { timeoutMs: 3000 });
    await waitForColor(page, 6, 7, 'GREEN_HIGH', { timeoutMs: 3000 });
    await waitForColor(page, 7, 7, 'GREEN_HIGH', { timeoutMs: 3000 });

    // GTR Delay untouched.
    await waitForColor(page, 1, 7, 'OFF', { timeoutMs: 3000 });
    await waitForColor(page, 1, 6, 'RED_MED', { timeoutMs: 3000 });
  });

  test('volume column: two presses on the bottom pad mute the channel', async () => {
    await normalizeHome(page);                   // fader back at (0,3) GREEN

    // Press 1: bottom pad → coarse step 1 (vol 18) → the pad lights GREEN.
    await tapPad(page, 0, 0);
    await waitForColor(page, 0, 0, 'GREEN_HIGH', { timeoutMs: 3000 });

    // Press 2 on the same pad: sub-level 0 → volume 0 → MUTE.
    await tapPad(page, 0, 0);
    await waitForColor(page, 0, 0, 'RED_HIGH', { timeoutMs: 3000 });
    expect(await ledColor(page, 0, 7)).toBe('RED_HIGH');   // whole column red

    // Any fader tap unmutes.
    await tapPad(page, 0, 3);
    await waitForColor(page, 0, 3, 'GREEN_HIGH', { timeoutMs: 3000 });
    expect(await ledColor(page, 0, 0)).not.toBe('RED_HIGH');
  });
});
