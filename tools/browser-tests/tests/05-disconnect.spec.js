/**
 * 05-disconnect.spec.js — what happens when the rig loses MIDI mid-set.
 *
 * On a real gig the cable doesn't announce itself; the Launchpad just
 * vanishes. The engine's MidiManager polls port availability and should:
 *   1. notice the device disappeared,
 *   2. keep the app alive (no crash, input still routable),
 *   3. auto-reconnect as soon as the port is back and repaint the screen.
 *
 * We simulate the disappearance using the virtualizer's OWN hooks — the same
 * `disconnect`/`connect` MIDI actions the HTML toolbar exposes — so we can
 * safely yank the virtual cable from inside the browser test, then feed it
 * back in and watch the engine recover.
 */

const { test, expect } = require('@playwright/test');
const { openLivePage } = require('../helpers');
const {
  ledColor, tapPad, tapTopRow, wsAction, waitForColor, waitForMode,
  normalizeHome,
} = require('../lib/ledger');

test.describe('Disconnect & reconnect', () => {
  let page;

  test.beforeAll(async ({ browser }) => {
    page = await openLivePage(browser);
    // Shared engine across spec files → force back to performance first.
    await normalizeHome(page);
  });

  test.afterAll(async () => {
    if (page) await page.close();
  });

  test('dropping the MIDI device does not crash or hang the page', async () => {
    await wsAction(page, { action: 'disconnect' });   // yank the virtual cable

    // Backend still answers and the page still paints last-known state.
    await page.waitForTimeout(1500);
    const c = await ledColor(page, 0, 3);             // stale colour remains
    expect(c).not.toBeNull();

    // Feed the cable back: engine should reconnect within its poll window.
    await wsAction(page, { action: 'connect' });
    // The fader may sit wherever the fight left it — reset to a known home.
    await normalizeHome(page, { timeoutMs: 5000 });

    // And a fresh press still drives the UI.
    await tapPad(page, 0, 3);
    await page.waitForTimeout(200);
    await waitForMode(page, 'performance');
  });
});