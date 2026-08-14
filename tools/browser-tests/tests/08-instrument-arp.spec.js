/**
 * 08-instrument-arp.spec.js — Instrument Mode (the scale-mapped 8×8 "Push"
 * grid) and its ARP pattern editor (long-press E → arp_edit).
 *
 * INSTRUMENT MODE (top-row shortcut 205)
 * -------------------------------------
 * Grid: every pad is a scale-mapped note. Root notes (note % 12 == key root)
 * render RED_HIGH, other scale pads AMBER_LOW, a held pad GREEN_HIGH.
 * Right column controls:
 *   A idx0 Notes/Chords (GREEN = notes mode) · B idx1 Scale · C idx2 Hold
 *   D idx3 ARP mode (off=RED / up=GREEN / down=AMBER)
 *   E idx4 ARP pattern (normal=GREEN / chordal=AMBER / octaves=RED)
 *   F idx5 Key (AMBER) · G,H off
 *
 * ARP EDIT MODE
 * -------------
 * Enter by LONG-pressing right-col E (≥500ms) in instrument mode. The grid
 * becomes a step editor: row 0 = beat chase, rows 1-7 = scale degrees
 * (interval k lights pad (step, k+1) AMBER_HIGH). Right column:
 *   A-D,F  pattern slots (selected=factory RED_HIGH / user AMBER_HIGH,
 *          existing=factory RED_LOW / user AMBER_LOW, empty=OFF)
 *   E      note-length view toggle · G previous page · H next page
 *   Top-1 (HOME) exits back to instrument.
 *
 * These tests read the live LED truth (pad titles + state.right_col), so a
 * failed assertion points at the engine, not the DOM.
 */

const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');
const { openLivePage } = require('../helpers');
const {
  ledColor, tapPad, tapTopRow, tapRightCol, padDown, padUp, holdRightCol,
  waitForColor, rightLedColor, waitForRightLed,
} = require('../lib/ledger');

// User slot the save test writes (page 2 → slot 9). Cleaned up each run so
// the suite stays reproducible.
const USER_SLOT_FILE = path.resolve(
  __dirname, '..', '..', '..', 'config', 'arp_patterns', 'user_09.json',
);

async function enterInstrument(page) {
  await tapTopRow(page, 5);                       // 205 → instrument
  await waitForColor(page, 0, 0, 'RED_HIGH', { timeoutMs: 6000 }); // root pad
  // A-tap resyncs the right column (release re-renders the control LEDs).
  await tapRightCol(page, 0);
  await page.waitForTimeout(250);
}

async function enterArpEdit(page) {
  await enterInstrument(page);
  // Long-press E ≥500ms to open the editor. Give it generous margin: under
  // load the release can otherwise land <500ms after the engine sees the
  // press, which short-presses E (cycles the pattern) instead.
  await holdRightCol(page, 4, 900);
  // Interval 0 lives at (0,1) in the default pattern — the editor is up.
  // (Confirm via the grid, not the page's slow state.mode echo.)
  await waitForColor(page, 0, 1, 'AMBER_HIGH', { timeoutMs: 6000 });
}

async function exitArpEdit(page) {
  await tapTopRow(page, 0);                       // 200 → exits arp_edit
  // Confirm via the GRID (immediate MIDI-LED path), not the slower page
  // mode echo: (0,1) is the instrument root column (RED) vs the editor's
  // interval-0 marker (AMBER).
  await waitForColor(page, 0, 1, 'RED_HIGH', { timeoutMs: 8000 });
  await waitForColor(page, 0, 0, 'RED_HIGH', { timeoutMs: 8000 });
  // A-tap resyncs the right column (release re-renders the control LEDs).
  await tapRightCol(page, 0);
  await page.waitForTimeout(250);
}

test.describe('Instrument mode', () => {
  let page;

  test.beforeAll(async ({ browser }) => {
    page = await openLivePage(browser);
    if (fs.existsSync(USER_SLOT_FILE)) fs.unlinkSync(USER_SLOT_FILE);
    await enterInstrument(page);
  });

  test.afterAll(async () => {
    if (page) await page.close();
  });

  test('instrument renders the scale grid and right-column control LEDs', async () => {
    // Root pad (0,0) is RED_HIGH; the neighbouring scale pad is AMBER_LOW.
    expect(await ledColor(page, 0, 0)).toBe('RED_HIGH');
    expect(await ledColor(page, 1, 0)).toBe('AMBER_LOW');

    // Control LEDs from a fresh entry.
    await waitForRightLed(page, 0, 'GREEN_HIGH');  // notes mode
    await waitForRightLed(page, 1, 'GREEN_HIGH');  // major scale
    await waitForRightLed(page, 2, 'RED_HIGH');    // hold off
    await waitForRightLed(page, 3, 'RED_HIGH');    // arp off
    await waitForRightLed(page, 4, 'GREEN_HIGH');  // pattern normal
    await waitForRightLed(page, 5, 'AMBER_HIGH');  // key
    expect(await rightLedColor(page, 6)).toBe('OFF');
    expect(await rightLedColor(page, 7)).toBe('OFF');
  });

  test('B cycles the scale: major→minor→blues→chromatic→major', async () => {
    await tapRightCol(page, 1);
    await waitForRightLed(page, 1, 'AMBER_HIGH');  // minor
    await tapRightCol(page, 1);
    await waitForRightLed(page, 1, 'RED_HIGH');    // blues
    await tapRightCol(page, 1);
    await waitForRightLed(page, 1, 'RED_HIGH');    // chromatic
    await tapRightCol(page, 1);
    await waitForRightLed(page, 1, 'GREEN_HIGH');  // back to major
  });

  test('D cycles the ARP mode: off→up→down→off', async () => {
    await tapRightCol(page, 3);
    await waitForRightLed(page, 3, 'GREEN_HIGH');  // up
    await tapRightCol(page, 3);
    await waitForRightLed(page, 3, 'AMBER_HIGH');  // down
    await tapRightCol(page, 3);
    await waitForRightLed(page, 3, 'RED_HIGH');    // off
  });

  test('E short-press cycles the ARP pattern: normal→chordal→octaves→normal',
    async () => {
      // Short-press E cycles the pattern; a LONG press opens the editor.
      await tapRightCol(page, 4);
      await waitForRightLed(page, 4, 'AMBER_HIGH');  // chordal
      await tapRightCol(page, 4);
      await waitForRightLed(page, 4, 'RED_HIGH');    // octaves
      await tapRightCol(page, 4);
      await waitForRightLed(page, 4, 'GREEN_HIGH');  // normal
    });

  test('C toggles hold on/off', async () => {
    await tapRightCol(page, 2);
    await waitForRightLed(page, 2, 'GREEN_HIGH');  // hold on
    await tapRightCol(page, 2);
    await waitForRightLed(page, 2, 'RED_HIGH');    // hold off
  });

  test('a held note pad lights GREEN, releases back to the scale colour', async () => {
    await padDown(page, 1, 0);
    await waitForColor(page, 1, 0, 'GREEN_HIGH', { timeoutMs: 2000 });
    await padUp(page, 1, 0);
    await waitForColor(page, 1, 0, 'AMBER_LOW', { timeoutMs: 2000 });
  });

  test('F cycles the key a full octave; the LED stays AMBER throughout', async () => {
    // A full 12-tap loop walks C→C#→…→B→C and lands back on C, leaving the
    // instrument root unchanged for later files (09's MIDI tests need C).
    for (let i = 0; i < 12; i++) {
      await tapRightCol(page, 5);
      await page.waitForTimeout(60);
    }
    await waitForRightLed(page, 5, 'AMBER_HIGH');
  });
});

test.describe('ARP edit mode', () => {
  let page;

  test.beforeAll(async ({ browser }) => {
    page = await openLivePage(browser);
    if (fs.existsSync(USER_SLOT_FILE)) fs.unlinkSync(USER_SLOT_FILE);
  });

  test.afterAll(async () => {
    if (fs.existsSync(USER_SLOT_FILE)) fs.unlinkSync(USER_SLOT_FILE);
    if (page) await page.close();
  });

  test('long-press E opens the pattern editor (diagonal + slot LEDs)', async () => {
    await enterArpEdit(page);

    // Default "normal" intervals [0,1,2,3,4,5,6,7] light a diagonal.
    for (let step = 0; step < 6; step++) {
      expect(await ledColor(page, step, step + 1)).toBe('AMBER_HIGH');
    }

    // Right column: slot 1 selected (RED_HIGH), factory slots RED_LOW,
    // E button RED, page 0 → G AMBER_LOW / H GREEN_HIGH.
    await waitForRightLed(page, 0, 'RED_HIGH');
    await waitForRightLed(page, 1, 'RED_LOW');
    await waitForRightLed(page, 4, 'RED_HIGH');
    expect(await rightLedColor(page, 6)).toBe('AMBER_LOW');
    expect(await rightLedColor(page, 7)).toBe('GREEN_HIGH');

    await exitArpEdit(page);
  });

  test('tapping a step moves its note marker', async () => {
    await enterArpEdit(page);

    // Step 2 is interval 2 (pad (2,3)). Tap row 2 → interval 1 → pad (2,2).
    await tapPad(page, 2, 2);
    await waitForColor(page, 2, 2, 'AMBER_HIGH', { timeoutMs: 2000 });
    await waitForColor(page, 2, 3, 'OFF', { timeoutMs: 2000 });

    await exitArpEdit(page);
  });

  test('E toggles the note-length bar graph and back to the editor', async () => {
    await enterArpEdit(page);

    // Enter note-length mode: "LENGTH" scroll overlay (~1s), then the bar
    // graph. Default lengths are all 5 → rows 0-4 RED, rows 5-7 OFF.
    await tapRightCol(page, 4);
    await page.waitForTimeout(1200);               // let the scroll overlay finish
    await waitForColor(page, 3, 4, 'RED_HIGH', { timeoutMs: 3000 });
    expect(await ledColor(page, 3, 5)).toBe('OFF');
    await waitForRightLed(page, 0, 'RED_HIGH');    // whole right col red

    // E again → back to the step editor.
    await tapRightCol(page, 4);
    await waitForColor(page, 0, 1, 'AMBER_HIGH', { timeoutMs: 3000 });

    await exitArpEdit(page);
  });

  test('H/G page through the three slot banks', async () => {
    await enterArpEdit(page);

    // page0 → page1: G becomes available (GREEN), slot 9 (idx0) is empty.
    await tapRightCol(page, 7);
    await waitForRightLed(page, 6, 'GREEN_HIGH');
    await waitForRightLed(page, 7, 'GREEN_HIGH');
    expect(await rightLedColor(page, 0)).toBe('OFF');

    // page1 → page2: last page → H goes dim.
    await tapRightCol(page, 7);
    await waitForRightLed(page, 7, 'AMBER_LOW');
    expect(await rightLedColor(page, 6)).toBe('GREEN_HIGH');

    // page2 wraps back to page0.
    await tapRightCol(page, 7);
    await waitForRightLed(page, 7, 'GREEN_HIGH');
    await waitForRightLed(page, 6, 'AMBER_LOW');

    // G pages backwards.
    await tapRightCol(page, 6);
    await waitForRightLed(page, 7, 'AMBER_LOW');
    await tapRightCol(page, 6);
    await waitForRightLed(page, 7, 'GREEN_HIGH');
    await tapRightCol(page, 6);
    await waitForRightLed(page, 6, 'AMBER_LOW');

    await exitArpEdit(page);
  });

  test('long-pressing a user slot saves the pattern and flashes it', async () => {
    await enterArpEdit(page);
    await tapRightCol(page, 7);                    // page1 → slots 9-16
    await waitForRightLed(page, 6, 'GREEN_HIGH');

    // Long-press slot 9 (right-col idx 0) → writes user_09.json + green flash.
    // The write happens ~200ms after the release (async processing), so poll.
    await holdRightCol(page, 0, 700);
    const deadline = Date.now() + 3000;
    let saved = false;
    while (Date.now() < deadline) {
      if (fs.existsSync(USER_SLOT_FILE)) { saved = true; break; }
      await page.waitForTimeout(100);
    }
    expect(saved).toBe(true);

    // Save flash: the slot LED blinks GREEN for ~1s.
    await waitForRightLed(page, 0, 'GREEN_HIGH', { timeoutMs: 2000 });

    // After the flash it settles to AMBER_LOW (a user slot that now exists).
    await waitForRightLed(page, 0, 'AMBER_LOW', { timeoutMs: 2500 });

    await exitArpEdit(page);
  });

  test('top-1 (HOME) exits the editor back to instrument', async () => {
    await enterArpEdit(page);
    await exitArpEdit(page);

    // The editor diagonal is gone; instrument root pad colour returns.
    expect(await ledColor(page, 0, 1)).toBe('RED_HIGH');
    await waitForRightLed(page, 4, 'GREEN_HIGH');  // pattern LED back
  });
});
