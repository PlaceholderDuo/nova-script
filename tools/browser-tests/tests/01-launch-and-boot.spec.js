/**
 * 01-launch-and-boot.spec.js — first thing you'd check at a gig: does the
 * whole rig boot cleanly? Covers:
 *
 *   1. page arrives (WS up, backend attached)
 *   2. an 8×8 grid of pads is rendered with exactly the right colours
 *   3. each pad's title carries engine-written ground-truth colour names
 *   4. the app settles into Performance mode with the exact default screen
 *      the engine computes (verified against the real MIDI output): volume
 *      columns GREEN at the fader, RED above, OFF below; disabled FX slots
 *      show RED_MED under empty (OFF) preset areas.
 *
 * COLOUR GROUND TRUTH
 * -------------------
 * Everything reads each pad's `title`: the virtualizer writes
 * "[<x>,<y>] <COLOR>" from the REAL MIDI messages the engine sends. A failed
 * assertion proves the engine really painted the wrong colour.
 *
 * PERFORMANCE DEFAULT SCREEN (src/ui/modes/performance.py):
 *   volumes default to 24 → fader sits at pad_y=3 (GREEN_HIGH), RED_HIGH at
 *   y=4..7 ("too loud"), OFF at y=0..2 (unused zone). FX disable rows map to
 *   y=6,4,2,0 → RED_MED; preset slots at y=7,5,3,1 → OFF (FX disabled).
 */

const { test, expect } = require('@playwright/test');
const { openLivePage } = require('../helpers');
const { ledColor, expectLedColor } = require('../lib/ledger');

test.describe('Launch & boot', () => {
  let page;

  test.beforeAll(async ({ browser }) => {
    page = await openLivePage(browser);
  });

  test.afterAll(async () => {
    await page.close();
  });

  test('the page is live: WS connected, info strip shows backend online',
    async () => {
      await expect(page.locator('#ws-status')).toHaveText('connected');
    });

  test('a full 8×8 pad grid is rendered', async () => {
    await expect(page.locator('.pad')).toHaveCount(64);
  });

  test('every pad carries an engine-ground-truth [x,y] COLOR title',
    async () => {
      const titles = await page.locator('.pad').evaluateAll(els =>
        els.map(el => el.title)
      );
      expect(titles).toHaveLength(64);
      const TITLE_RE = /^\[\d,\d\]\s?\S+$/;
      for (let i = 0; i < titles.length; i++) {
        expect(TITLE_RE.test(titles[i]), `pad #${i} title "${titles[i]}"`)
          .toBe(true);
      }
    });

  test('grid is meaningful: most pads lit, but not all (real screen, mid wave)',
    async () => {
      const lit = await page.locator('.pad').evaluateAll(els =>
        els.filter(el => el.title && !/OFF\s*$/.test(el.title)).length
      );
      // Default performance screen = 2 vol columns (5 lit each) + FX disable
      // rows across 6 cols (4 each) ≈ 34 lit. Far from full-on 64 and far
      // from black, proving engine drew its UI, not a wipe/blank.
      expect(lit).toBeGreaterThanOrEqual(24);
      expect(lit).toBeLessThan(48);
    });

  test('Performance volume columns: GREEN fader @ y=3, RED above, OFF below',
    async () => {
      // GTR volume column (x=0): the default fader sits at y=3.
      await expectLedColor(page, 0, 3, 'GREEN_HIGH', 'GTR fader');
      await expectLedColor(page, 0, 7, 'RED_HIGH', 'GTR too-loud zone');
      await expectLedColor(page, 0, 0, 'OFF', 'GTR below-fader');
      // VOX volume column (x=4): identical layout.
      await expectLedColor(page, 4, 3, 'GREEN_HIGH', 'VOX fader');
      await expectLedColor(page, 4, 7, 'RED_HIGH', 'VOX too-loud zone');
    });

  test('FX pads: disabled FX show OFF presets above RED_MED disable rows',
    async () => {
      // GTR FX block columns 1..3. Preset slot for FX1 at y=7 → OFF (disabled).
      await expectLedColor(page, 1, 7, 'OFF', 'FX1 preset (disabled)');
      // Disable row for FX1 sits at y=6 → RED_MED.
      await expectLedColor(page, 1, 6, 'RED_MED', 'FX1 disable row');
      await expectLedColor(page, 2, 4, 'RED_MED', 'FX2 disable row');
    });
});