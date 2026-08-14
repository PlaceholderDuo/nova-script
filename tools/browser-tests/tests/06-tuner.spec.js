/**
 * 06-tuner.spec.js — the guitar tuner (Performance Mode, right-column H).
 *
 * The tuner is a full little state machine that lives INSIDE performance
 * mode (no mode switch — `state.mode` stays "performance" the whole time):
 *
 *   off ─(H)→ intro ─(1.2s)→ active ─(H or grid press)→ exit ─(0.3s)→ off
 *
 *   • intro:  the letters T·N·R flash one at a time (~0.3s each, AMBER_HIGH),
 *             then a ~0.3s ripple transition rolls into the live band.
 *   • active: a vertical "needle" band of ~1.5 columns sweeps the grid. Its
 *             colour tracks the incoming cents:
 *               < 3 cents  → GREEN_HIGH (locked)
 *               < 20 cents → AMBER_HIGH (close)
 *               else       → RED_HIGH   (far)
 *             The needle's drift speed scales with |cents|, so a flat note
 *             parks dead-centre (GREEN), a sharp/flat note hunts left-right.
 *   • right-column G while active switches the tuning target GTR↔VOX and
 *     re-centres the needle (cents reset to 0 → locked GREEN).
 *   • any grid pad press while active bails out to the performance screen.
 *
 * Reaper feeds the tuner live via OSC `/nova/tuner` (cents, channel) — we
 * inject the same datagrams the DAW would send, so these tests prove the
 * whole chain: OSC → engine → LED render → virtual MIDI → DOM.
 */

const { test, expect } = require('@playwright/test');
const { openLivePage } = require('../helpers');
const {
  ledColor, tapPad, tapTopRow, tapRightCol,
  waitForColor, waitForMode, normalizeHome,
} = require('../lib/ledger');
const { osc } = require('../lib/osc');
const { OSC_HOST, OSC_PORT } = require('../lib/env');

// Centre pad (4,4) is inside the 5×5 glyphs for T, N and R, so it's lit
// AMBER_HIGH throughout the letter intro.
const LETTER_PAD = { x: 4, y: 4 };

/** Enter the tuner from a clean performance screen and wait for a letter. */
async function enterTuner(page) {
  await normalizeHome(page);
  await tapRightCol(page, 7);
  await waitForColor(page, LETTER_PAD.x, LETTER_PAD.y, 'AMBER_HIGH', { timeoutMs: 1500 });
}

/** Leave the tuner (H toggles it off) and return to the performance screen. */
async function leaveTuner(page) {
  // H only stops the tuner once it's in the ACTIVE state — during the intro
  // (letters) start/stop are guarded, so wait for the live band first.
  await waitForColor(page, 4, 4, 'GREEN_HIGH', { timeoutMs: 4000 });
  await tapRightCol(page, 7);
  await waitForColor(page, 0, 3, 'GREEN_HIGH', { timeoutMs: 3000 });
}

test.describe('Guitar tuner', () => {
  let page;

  test.beforeAll(async ({ browser }) => {
    page = await openLivePage(browser);
    await normalizeHome(page);
  });

  test.afterAll(async () => {
    if (page) await page.close();
  });

  test('H starts the tuner: T·N·R letter intro on the grid', async () => {
    await enterTuner(page);

    // The intro wipes the performance screen — the GTR fader disappears.
    const fader = await ledColor(page, 0, 3);
    expect(fader).not.toBe('GREEN_HIGH');

    // Still inside performance mode (tuner is a sub-state, not a mode).
    expect(await waitForMode(page, 'performance', { timeoutMs: 1500 })).toBe(true);

    await leaveTuner(page);
  });

  test('intro rolls into the active band, locked GREEN at zero cents', async () => {
    await enterTuner(page);

    // ~1.2s after entry the band renders; at cents=0 the needle parks dead
    // centre (cols 2..5) and reads GREEN_HIGH = "in tune".
    await waitForColor(page, 4, 4, 'GREEN_HIGH', { timeoutMs: 3500 });

    // Band spans columns 2..5 across the full column height…
    expect(await ledColor(page, 2, 7)).toBe('GREEN_HIGH');
    expect(await ledColor(page, 5, 0)).toBe('GREEN_HIGH');
    // …and stops before the grid edges (col 1 is outside the needle).
    expect(await ledColor(page, 1, 7)).not.toBe('GREEN_HIGH');

    await leaveTuner(page);
  });

  test('incoming cents drive the needle: far note → RED, flat note → GREEN', async () => {
    await enterTuner(page);
    await waitForColor(page, 4, 4, 'GREEN_HIGH', { timeoutMs: 3500 });

    // A +45-cent note: way past the near threshold → RED band that hunts
    // left-right across the grid. Pump like a live tuner.
    const pump = setInterval(() => {
      osc(OSC_HOST, OSC_PORT, '/nova/tuner', [45.0, 'GTR']).catch(() => {});
    }, 40);
    try {
      // The moving needle sweeps col 4 many times per second; any hit proves
      // the engine turned the cents into a RED band.
      await waitForColor(page, 4, 4, 'RED_HIGH', { timeoutMs: 4000 });
    } finally {
      clearInterval(pump);
    }

    // Back to zero cents → the needle recentres and locks GREEN again
    // (speed eases back over ~1s, so give it room).
    await osc(OSC_HOST, OSC_PORT, '/nova/tuner', [0.0, 'GTR']);
    await waitForColor(page, 4, 4, 'GREEN_HIGH', { timeoutMs: 4000 });

    await leaveTuner(page);
  });

  test('G switches tuning target and re-centres the needle', async () => {
    await enterTuner(page);
    await waitForColor(page, 4, 4, 'GREEN_HIGH', { timeoutMs: 3500 });

    const pump = setInterval(() => {
      osc(OSC_HOST, OSC_PORT, '/nova/tuner', [45.0, 'GTR']).catch(() => {});
    }, 40);
    try {
      await waitForColor(page, 4, 4, 'RED_HIGH', { timeoutMs: 4000 });
    } finally {
      clearInterval(pump);
    }

    // G (right-col idx 6) flips GTR→VOX: cents reset to 0, needle recentred.
    await tapRightCol(page, 6);
    await waitForColor(page, 4, 4, 'GREEN_HIGH', { timeoutMs: 4000 });

    await leaveTuner(page);
  });

  test('a grid pad press while tuning bails out to the performance screen', async () => {
    await enterTuner(page);
    await waitForColor(page, 4, 4, 'GREEN_HIGH', { timeoutMs: 3500 });

    // Grid press while tuner is active exits it (the press is swallowed, so
    // the fader is untouched — it comes back exactly where it was).
    await tapPad(page, 0, 0);
    await waitForColor(page, 0, 3, 'GREEN_HIGH', { timeoutMs: 3000 });

    // Tuner needle is gone.
    expect(await ledColor(page, 4, 4)).not.toBe('GREEN_HIGH');
  });

  test('H toggles the tuner off with the exit fade', async () => {
    await enterTuner(page);
    await waitForColor(page, 4, 4, 'GREEN_HIGH', { timeoutMs: 3500 });

    await leaveTuner(page);
  });
});
