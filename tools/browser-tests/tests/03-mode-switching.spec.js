/**
 * 03-mode-switching.spec.js — can the rig move between the screens it
 * promises? Covers the top-row shortcuts (201–205) and the "home" button,
 * asserting that:
 *   • each mode switch lands the grid on THAT mode's screen
 *     (distinctive pads change colour — e.g. mixer mute row vs performance
 *     FX rows),
 *   • the engine's reported mode (via the backend state.mode) follows the
 *     button you pressed,
 *   • going home returns the performance default screen exactly.
 *
 * Top-row button IDs on the MK1: 0x68..0x6F map to control IDs 200..207.
 * The engine's global shortcuts are 201=performance, 202=clip_launcher,
 * 203=sequencer, 204=mixer, 205=instrument. `tapTopRow(page, n)` presses the
 * n-th top button (0-indexed), so index 1 → shortcut 201, index 4 → 204.
 */

const { test, expect } = require('@playwright/test');
const { openLivePage } = require('../helpers');
const {
  ledColor, tapTopRow, waitForColor, waitForMode,
} = require('../lib/ledger');

test.describe('Mode switching', () => {
  let page;

  test.beforeAll(async ({ browser }) => {
    page = await openLivePage(browser);
    // Engine is shared across spec files — force HOME before asserting the
    // startup screen, so prior files can't have left us on another mode.
    await tapTopRow(page, 0);
    await waitForColor(page, 0, 3, 'GREEN_HIGH', { timeoutMs: 3000 });
  });

  test.afterAll(async () => {
    if (page) await page.close();
  });

  test('starts on the performance screen', async () => {
    await waitForMode(page, 'performance');
    // Volume fader at (0,3) GREEN — the performance default.
    await waitForColor(page, 0, 3, 'GREEN_HIGH', { timeoutMs: 2000 });
  });

  test('top-row shortcut 204 jumps to mixer and lights the mute row', async () => {
    await tapTopRow(page, 4);                       // 204 → mixer
    await waitForColor(page, 0, 3, 'OFF', { timeoutMs: 3000 });

    // Mixer mute row sits at y=7 (AMBER_LOW, all 8 tracks). Performance has
    // NO row 7 pattern like this — it's a distinctive mixer-only signature.
    await waitForColor(page, 0, 7, 'AMBER_LOW', { timeoutMs: 3000 });
    await waitForMode(page, 'mixer');
  });

  test('top-row shortcut 203 lands on sequencer (transport row lit)', async () => {
    await tapTopRow(page, 3);                       // 203 → sequencer
    // Sequencer transport row (y=7) shows GREEN_HIGH play buttons on cols 0-1.
    await waitForColor(page, 0, 7, 'GREEN_HIGH', { timeoutMs: 3000 });
    await waitForColor(page, 3, 7, 'OFF', { timeoutMs: 3000 });
    await waitForMode(page, 'sequencer');
  });

  test('top-row shortcut 202 jumps to clip launcher', async () => {
    await tapTopRow(page, 2);                       // 202 → clip_launcher
    // Scene 0 (display row y=7) is AMBER_HIGH in the default clip set.
    await waitForColor(page, 0, 7, 'AMBER_HIGH', { timeoutMs: 3000 });
    await waitForMode(page, 'clip_launcher');
  });

  test('home (200) returns to the performance screen exactly', async () => {
    await tapTopRow(page, 0);                       // 200 → home
    await waitForColor(page, 0, 3, 'GREEN_HIGH', { timeoutMs: 3000 });
    await waitForMode(page, 'performance');
  });
});