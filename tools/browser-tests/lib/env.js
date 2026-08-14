/**
 * env.js — central configuration & paths for the browser test suite.
 *
 * WHY THIS FILE EXISTS
 * --------------------
 * Every test needs to know where things live and what the stack's contract is.
 * Keeping all paths/ports/colors here means you rarely edit a test file just
 * because something moved. Change ONE thing here and the whole suite adapts.
 *
 * HOW THE STACK WORKS (so you can reason about the tests):
 *
 *   [Your real controller would sit here]
 *                     │
 *        ┌────────────▼──────────────┐
 *        │  tools/novation-virtualizer│  <-- "virtual MIDI ports" + WS :8766
 *        │  .py (backend process)     │      simulates the physical Launchpad
 *        └────────────┬──────────────┘
 *                     │  rtmidi virtual ports ("Launchpad Mini")
 *        ┌────────────▼──────────────┐
 *        │  nova-script engine        │  <-- the REAL app logic (src/engine.py)
 *        │  (started by this suite)   │      connects to the virtual ports
 *        └────────────┬──────────────┘
 *                     │  WebSocket :8766 (LED state broadcasts)
 *        ┌────────────▼──────────────┐
 *        │  tools/novation-virtualizer│  <-- the SAME page you open in a browser
 *        │  .html (Playwright drives) │      every pad/button/LED is a DOM node
 *        └───────────────────────────┘
 *
 * A Playwright test therefore exercises the ENTIRE live chain:
 *   DOM click → WS action → virtual MIDI → engine logic → LED render → WS → DOM.
 * If a pad doesn't light the way the engine says it should, the test fails —
 * exactly the kind of glitch you'd catch on stage.
 */

const path = require('path');

// ── Project layout ─────────────────────────────────────────────────────────
// env.js lives in  browser-tests/lib/, so the project root is three up:
//   lib/ → browser-tests/ → tools/ → nova-script/
const PROJECT_ROOT = path.resolve(__dirname, '..', '..', '..');
const TOOLS_DIR = path.join(PROJECT_ROOT, 'tools');
const HTML_PATH = path.join(TOOLS_DIR, 'novation-virtualizer.html');
const BACKEND_SCRIPT = path.join(TOOLS_DIR, 'novation-virtualizer.py');
const VENV_PYTHON = path.join(PROJECT_ROOT, '.venv', 'bin', 'python');
// Engine stderr capture (helps diagnose boot/animation flakes).
const ENGINE_LOG = path.join(PROJECT_ROOT, 'tools', 'browser-tests', 'engine.log');
// Backend stderr capture (mirrors every LED write the backend relayed).
const BACKEND_LOG = path.join(PROJECT_ROOT, 'tools', 'browser-tests', 'backend.log');

// ── Network contract (must match the Python backend) ──────────────────────
const WS_URL = 'ws://localhost:8766';        // virtualizer WebSocket
const OSC_PORT = 9001;                       // engine OSC listen (tuner/VU/text)
const OSC_HOST = '127.0.0.1';

// ── Timing budgets (ms) ───────────────────────────────────────────────────
// These are the "how long is acceptable" slop windows for timing tests.
// On a fast Mac these are generous; tighten them to catch real regressions.
const LED_SETTLE_MS = 400;       // time allowed for an LED to reach its target
const MODE_SWITCH_MS = 600;      // time for a mode switch render to land in DOM
const BEAT_MS = 500;             // 120 BPM = 500 ms per beat (engine default)
const BEAT_TOLERANCE_MS = 120;   // how sloppy the beat flash may be before fail

module.exports = {
  PROJECT_ROOT,
  TOOLS_DIR,
  HTML_PATH,
  BACKEND_SCRIPT,
  VENV_PYTHON,
  ENGINE_LOG,
  BACKEND_LOG,
  WS_URL,
  OSC_HOST,
  OSC_PORT,
  LED_SETTLE_MS,
  MODE_SWITCH_MS,
  BEAT_MS,
  BEAT_TOLERANCE_MS,
};
