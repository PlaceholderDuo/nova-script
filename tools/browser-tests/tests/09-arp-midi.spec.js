/**
 * 09-arp-midi.spec.js — the ARP's ACTUAL MIDI output, not just its LEDs.
 *
 * The ARP (Instrument Mode) sends notes OUT to the Akai Force via
 * `midi_manager.send_force()`. The virtualizer now exposes a virtual "Akai
 * Force" port and captures every note-on/note-off with a monotonic timestamp
 * into `state.midi_log`, so these tests verify the real note stream: pitches,
 * ordering, note-off discipline and step timing.
 *
 * Setup: Instrument Mode (top-row 5). The "normal" ARP pattern is scale
 * degrees [0,1,2,3,4,5,6,7]; with a pad held it cycles the ascending scale
 * from that pad's note. Notes are computed from the MEASURED root (pad (0,0))
 * so the tests don't depend on the key left by earlier files.
 *   Step interval at 120 BPM = 60/120/4 = 125ms per 1/8 step. The engine's
 *   tick loop quantises that to ~0.1-0.2s real time, so timing asserts allow
 *   a generous band while still proving the stream is stepping musically.
 */

const { test, expect } = require('@playwright/test');
const { openLivePage } = require('../helpers');
const {
  tapTopRow, tapRightCol, padDown, padUp,
  waitForColor, midiLog, clearMidi, waitForMidi,
} = require('../lib/ledger');

// note_on events only, in arrival order.
function noteOns(log) {
  return log.filter(e => e.type === 'note_on').map(e => e.note);
}

/** Press the root pad and read its actual note from the MIDI stream. */
async function measureRoot(page) {
  await clearMidi(page);
  await padDown(page, 0, 0);
  let root = null;
  try {
    const log = await waitForMidi(page, 1, { timeoutMs: 1500 });
    root = noteOns(log)[0];
  } catch { /* no capture */ }
  await padUp(page, 0, 0);
  if (root === null || root === undefined) throw new Error('measureRoot: no MIDI note captured');
  return root;
}

/**
 * Major-scale ascending interval pattern for the "normal" arp: the second
 * arp note onward (first arp note == the held pad, dedup'd) walks the scale
 * degrees, differences [2,1,2,2,2,1,2].
 */
const NORMAL_DIFFS = [2, 1, 2, 2, 2, 1, 2];

/**
 * Get the instrument to "arp on + major scale + normal pattern" by probing
 * the ACTUAL MIDI stream (the ground truth) and cycling D (mode), B (scale)
 * and E (pattern) until a held pad arps the ascending major scale. Robust to
 * whatever state earlier files left behind — unlike the page's LED echo.
 */
async function setArpPlayingNormal(page) {
  for (let i = 0; i < 14; i++) {
    await clearMidi(page);
    await padDown(page, 1, 0);
    let ons = [];
    try {
      // Wait until a full cycle's worth of notes actually arrived (the step
      // rate is tick-quantised, so a fixed sleep can cut the cycle short).
      const log = await waitForMidi(page, 18, { timeoutMs: 4000 });
      ons = noteOns(log);
    } catch { /* arp off / slow — fall through to a correction tap */ }
    await padUp(page, 1, 0);

    const dedup = ons.filter((n, k) => n !== ons[k - 1]);
    if (dedup.length >= 8) {
      const diffs = [];
      for (let k = 1; k < 8; k++) diffs.push(dedup[k] - dedup[k - 1]);
      if (JSON.stringify(diffs) === JSON.stringify(NORMAL_DIFFS)) return;
    }
    // Not the ascending major arp — step one control closer: D=arp mode,
    // B=scale, E=pattern.
    await tapRightCol(page, [3, 1, 4][i % 3]);
    await page.waitForTimeout(300);
  }
  throw new Error('setArpPlayingNormal: could not reach ascending major arp');
}

/**
 * Flip the arp to DOWN. UP and DOWN are indistinguishable with one gate, so
 * probe with TWO gates: in DOWN the HIGH gate leads the arp (so `high`
 * appears many times); in UP `high` appears only as the press. Tap D until
 * the high gate is leading.
 */
async function ensureArpDown(page, root) {
  const high = root + 7;
  for (let i = 0; i < 6; i++) {
    await clearMidi(page);
    await padDown(page, 1, 0);
    await padDown(page, 4, 0);
    await page.waitForTimeout(900);
    await padUp(page, 4, 0);
    await padUp(page, 1, 0);
    const ons = noteOns(await midiLog(page));
    // Presses sound low then high; the first arp note re-plays the HIGH gate
    // in DOWN (indices 1 and 2 are both `high`). In UP it re-plays low.
    if (ons.length >= 3 && ons[1] === high && ons[2] === high) return;
    await tapRightCol(page, 3);                      // flip up<->down
    await page.waitForTimeout(300);
  }
  throw new Error('ensureArpDown: could not reach arp DOWN');
}

test.describe('ARP MIDI output', () => {
  let page;

  test.beforeAll(async ({ browser }) => {
    page = await openLivePage(browser);
    await tapTopRow(page, 5);                       // 205 → instrument
    await waitForColor(page, 0, 0, 'RED_HIGH', { timeoutMs: 6000 });
  });

  test.afterAll(async () => {
    if (page) await page.close();
  });

  test('ARP UP plays the pressed note then ascends the scale in order', async () => {
    await setArpPlayingNormal(page);
    const root = await measureRoot(page);        // note of pad (0,0)
    await clearMidi(page);

    await padDown(page, 1, 0);                   // hold the 2nd-scale-degree pad
    const log = await waitForMidi(page, 20, { timeoutMs: 5000 });
    await padUp(page, 1, 0);

    const ons = noteOns(log);
    expect(ons.length).toBeGreaterThanOrEqual(10);

    // The "normal" pattern from scale degree 1 ascends the major scale:
    // root+2, +4, +5, +7, +9, +11, +12, +14. It repeats, so a full 8-step
    // window appears somewhere even if a leading event is lost to latency.
    const CYCLE = [root + 2, root + 4, root + 5, root + 7, root + 9, root + 11, root + 12, root + 14];
    let found = false;
    for (let i = 0; i + 8 <= ons.length; i++) {
      if (JSON.stringify(ons.slice(i, i + 8)) === JSON.stringify(CYCLE)) {
        found = true;
        break;
      }
    }
    expect(found, `expected the ascending cycle ${CYCLE} in ${ons}`).toBe(true);
  });

  test('ARP steps arrive at a musical rate (~125ms each, tick-quantised)', async () => {
    await setArpPlayingNormal(page);
    await clearMidi(page);

    await padDown(page, 1, 0);
    const log = await waitForMidi(page, 14, { timeoutMs: 4000 });
    await padUp(page, 1, 0);

    const ons = log.filter(e => e.type === 'note_on');   // events, keep timestamps
    expect(ons.length).toBeGreaterThanOrEqual(6);
    const gaps = [];
    for (let i = 1; i < Math.min(ons.length, 10); i++) {
      gaps.push(ons[i].t - ons[i - 1].t);
    }
    for (const g of gaps) {
      expect(g).toBeGreaterThanOrEqual(0.05);
      expect(g).toBeLessThanOrEqual(0.35);
    }
    // 10 steps ≈ 1.25s at 125ms/step — the stream must be moving (the
    // engine's 10Hz tick quantises steps, so don't demand the full 1.25s).
    const span = gaps.reduce((a, b) => a + b, 0);
    expect(span).toBeGreaterThanOrEqual(0.6);
  });

  test('every arp step is a clean note_off then note_on pair', async () => {
    await setArpPlayingNormal(page);
    await clearMidi(page);

    await padDown(page, 1, 0);
    const log = await waitForMidi(page, 20, { timeoutMs: 5000 });
    await padUp(page, 1, 0);

    // The stream strictly alternates note_on / note_off / note_on … — the
    // arp retriggers by turning the previous note off before the next on.
    expect(log.length).toBeGreaterThanOrEqual(4);
    for (let i = 1; i < log.length; i++) {
      expect(log[i].type, `event ${i} should alternate`).not.toBe(log[i - 1].type);
    }
  });

  test('ARP DOWN leads with the highest held note', async () => {
    await setArpPlayingNormal(page);
    const root = await measureRoot(page);
    await ensureArpDown(page, root);                 // down order confirmed via MIDI
    await clearMidi(page);

    const low = root + 2;                        // pad (1,0)
    const high = root + 7;                       // pad (4,0)
    await padDown(page, 1, 0);
    await padDown(page, 4, 0);
    // 30 events ≈ 15 note_ons: enough to span a full 8-step high-note cycle
    // AND the flip back down to the low base.
    const log = await waitForMidi(page, 30, { timeoutMs: 6000 });
    await padUp(page, 4, 0);
    await padUp(page, 1, 0);

    const ons = noteOns(log);
    expect(ons).toContain(low);
    expect(ons).toContain(high);
    // The high gate's 2nd scale step (high+2) comes before the low gate's
    // 2nd step (low+2) — the arp runs the high note's cycle first.
    expect(ons.indexOf(high + 2)).toBeLessThan(ons.indexOf(low + 2));
  });

  test('releasing the pad stops the arp (final note_off, no more notes)', async () => {
    await setArpPlayingNormal(page);
    await clearMidi(page);

    await padDown(page, 1, 0);
    await waitForMidi(page, 12, { timeoutMs: 4000 });
    await padUp(page, 1, 0);                        // gate release

    // Let any in-flight step settle, then confirm the stream went silent.
    await page.waitForTimeout(500);
    const log = await midiLog(page);
    const last = log[log.length - 1];
    expect(last.type).toBe('note_off');

    // Nothing after the final note_off — the arp is truly stopped.
    const lastOff = log.findLastIndex(e => e.type === 'note_off');
    expect(log.length - 1 - lastOff).toBe(0);
  });
});
