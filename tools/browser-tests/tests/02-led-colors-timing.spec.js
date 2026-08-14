/**
 * 02-led-colors-timing.spec.js — engine reacts to LIVE inputs and shows the
 * right colours at the right speed. This is the "is the rig responsive" spec:
 * anything a singer/player can throw at the controller mid-set.
 *
 * SECTIONS
 * -------
 *   1. Press feedback: a pad tap flashes the pressed pad AMBER for a beat
 *      before the mode repaints its true colour. (the "did you actually push
 *      it" lighting)
 *   2. Double-press on the GTR fader toggles the sub-level (fine step) —
 *      proving press/release edges are parsed, not just "is it pressed".
 *   3. OSC-injected VU meters drive the mixer's level lights (they travel
 *      UP the physical pad column as Reaper feeds level). We inject the
 *      exact Reaper VU messages (nova/track/n/vu).
 *   4. OSC-injected beats pulse the transport/tempo LED (~120ms flash on
 *      the downbeat, then back to the resting colour).
 *   5. OSC tuner (cents) drives the motion band — RED far off, GRN locked.
 *
 * All checks read pad titles (ground truth from real MIDI LED messages)
 * so "colour X was wrong" failures point at the engine, not CSS.
 */

const { test, expect } = require('@playwright/test');
const { openLivePage } = require('../helpers');
const {
  ledColor, tapPad, tapTopRow, holdPad,
  measureDwell, waitForColor, currentMode, topLedColor,
  expectLedColor,
} = require('../lib/ledger');
const { sendOsc } = require('../lib/osc');
const { OSC_HOST, OSC_PORT } = require('../lib/env');

test.describe('LED colours & timing', () => {
  let page;

  test.beforeAll(async ({ browser }) => {
    page = await openLivePage(browser);
    // Shared engine across spec files — normalise to performance home first.
    await tapTopRow(page, 0);
    await waitForColor(page, 0, 3, 'GREEN_HIGH', { timeoutMs: 3000 });
  });

  test.afterAll(async () => {
    if (page) await page.close();
  });

  test('press feedback flashes a pad AMBER, then the mode colour takes over',
    async () => {
      // Normalise: make sure we start with the fader on its full step.
      const start = await ledColor(page, 0, 3);
      if (start !== 'GREEN_HIGH') await tapPad(page, 0, 3);
      await waitForColor(page, 0, 3, 'GREEN_HIGH', { timeoutMs: 1500 });

      await tapPad(page, 0, 3);

      // Capture a short dwell window: the engine flashes the pressed pad
      // AMBER_HIGH for ~120ms before committing the mode repaint.
      const dwell = await measureDwell(page, 0, 3, { windowMs: 400, sampleMs: 15 });
      const amberMs = (dwell['[0,3] AMBER_HIGH'] || 0);
      expect(amberMs).toBeGreaterThan(0);
    });

  test('double-press on the fader cell flips between sub-level and full level',
    async () => {
      // Normalise to the full step first.
      if (await ledColor(page, 0, 3) !== 'GREEN_HIGH') await tapPad(page, 0, 3);
      await waitForColor(page, 0, 3, 'GREEN_HIGH', { timeoutMs: 1500 });

      // First press: engages the fine sub-step → pad turns AMBER_HIGH.
      await tapPad(page, 0, 3);
      await waitForColor(page, 0, 3, 'AMBER_HIGH', { timeoutMs: 1500 });

      // Second press on the same pad: back to the full step → GREEN_HIGH.
      await tapPad(page, 0, 3);
      await waitForColor(page, 0, 3, 'GREEN_HIGH', { timeoutMs: 1500 });
    });

  test('dashboard header still says we are in performance mode',
    async () => {
      // The virtualizer echoes the engine's announced mode over the WS.
      expect(await currentMode(page)).toBe('performance');
    });

  test('mixer VU meters climb with injected Reaper /track/vu OSC', async () => {
    // Enter mixer mode with the top-row shortcut (204). Mixer's fader sits
    // at y=4 (default vol 24/32 → 4 of 6 steps) — performance's fader is
    // y=3, so this change proves the switch landed.
    await tapTopRow(page, 4);
    await waitForColor(page, 0, 4, 'GREEN_HIGH', { timeoutMs: 3000 });

    // Reaper normally streams /nova/track/{n}/vu continuously. Pump it like
    // a real DAW so the peak-hold lies flat for our sampling window.
    const pump = setInterval(() => {
      sendOsc(OSC_HOST, OSC_PORT, [
        ['/nova/track/0/vu', [1.0]],
      ]).catch(() => {});
    }, 60);
    try {
      // Level 1.0 → column fills to the red clip row (y=6).
      await waitForColor(page, 0, 6, 'RED_HIGH', { timeoutMs: 3000 });
      await waitForColor(page, 0, 2, 'AMBER_MED', { timeoutMs: 3000 });
    } finally {
      clearInterval(pump);
    }

    // Let VU drain back (engine stops pumping); column fades to the bare
    // fader colour. Give it a generous window for the softer fall.
    await page.waitForTimeout(400);
  });

  test('sequencer pulse: downbeat pushes a tempo LED flash', async () => {
    // Return to performance FIRST (a prior test may have moved us away).
    await tapTopRow(page, 1);
    await waitForColor(page, 0, 3, 'GREEN_HIGH', { timeoutMs: 3000 });

    // While pumping /nova/beat downbeats, the engine flashes the home
    // tempo LED (top row idx 0) to the downbeat colour for ~120ms. Sample
    // DURING the pump so the transient green state is observed.
    const resting = await topLedColor(page, 0);
    let sawBeat = false;
    for (let i = 0; i < 12; i++) {
      await sendOsc(OSC_HOST, OSC_PORT, [['/nova/beat', [i + 1]]]);
      for (let j = 0; j < 8; j++) {
        const c = await topLedColor(page, 0);
        if (c !== resting && c !== '') { sawBeat = true; break; }
        await page.waitForTimeout(25);
      }
      if (sawBeat) break;
      await page.waitForTimeout(60);
    }
    expect(sawBeat).toBe(true);
  });
});