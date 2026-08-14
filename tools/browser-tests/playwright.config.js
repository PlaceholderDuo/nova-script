/**
 * playwright.config.js — the browser-test suite configuration.
 *
 * THREE THINGS CONFIGURED HERE:
 *   1. `globalSetup/globalTeardown` — boot the engine + virtualizer backend
 *      once for the whole run, so every test just opens a page.
 *   2. Track `HTML_PATH` as a local file via `page.goto('file://…')`. The
 *      page needs no HTTP server: it talks to the backend over the
 *      WebSocket at ws://localhost:8766 from the same machine.
 *   3. Timeouts tuned for a full-live-chop chain (DOM→WS→MIDI→engine→MIDI→WS→DOM).
 *      Assertions use generous defaults; timing tests pass explicit budgets
 *      only where they need them.
 */

const { defineConfig } = require('@playwright/test');
const { HTML_PATH } = require('./lib/env');

module.exports = defineConfig({
  testDir: './tests',
  // Single worker: the stack is one shared instance + MIDI is serialized.
  workers: 1,
  fullyParallel: false,
  // Fail hard if something crashes; we don't want a green run hiding a red.
  // One retry absorbs the occasional transient MIDI/WS latency blip in this
  // virtualized live chain (a long-press landing marginally short, a dropped
  // LED echo) — a genuine engine bug still fails on both attempts.
  retries: 1,
  // The live chain includes the real engine's beat clock & MIDI polling,
  // so give actions a little room before Playwright nags about timeouts.
  timeout: 30_000,
  expect: { timeout: 8_000 },
  reporter: [
    ['list'],
    ['html', { open: 'never' }],
  ],
  projects: [
    {
      // Hardware-independent browsers (the tool runs headless by default).
      name: 'chromium',
      use: {
        browserName: 'chromium',
        headless: true,
      },
    },
  ],
  // Use named hooks for boot/teardown lifecycle.
  globalSetup: require.resolve('./global-setup.js'),
  globalTeardown: require.resolve('./global-teardown.js'),
});