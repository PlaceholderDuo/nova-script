/**
 * stack.js — process management for the browser test suite.
 *
 * Starts the REAL nova-script engine against the virtualizer's virtual MIDI
 * ports so browser tests exercise the live app (boot wave, mode switching,
 * LED rendering, OSC input) — not just the static HTML page.
 *
 * Stack layout:
 *   [backend: tools/novation-virtualizer.py]  → creates virtual MIDI ports
 *                                                        + WS :8766
 *   [engine:  src.main live-show]             → connects to virtual ports,
 *                                                        renders LEDs, handles
 *                                                        OSC on :9001
 *   [browser: novation-virtualizer.html]      → Playwright drives DOM, which
 *                                                        is fed by the backend
 *
 * Every test starts in the EngineHarness global fixture, so a whole run
 * boots the stack ONCE (Playwright worker-local). No physical hardware
 * required. Port ownership is protected by `lsof` reaping stale listeners.
 */

const { spawn } = require('child_process');
const net = require('net');
const { setTimeout: sleep } = require('timers/promises');
const fs = require('fs');
const path = require('path');

const {
  VENV_PYTHON, PROJECT_ROOT, BACKEND_SCRIPT, WS_URL, OSC_HOST, OSC_PORT,
  ENGINE_LOG, BACKEND_LOG,
} = require('./env');

// ── small helpers ──────────────────────────────────────────────────────────

async function waitForPort(port, ms = 20000) {
  const deadline = Date.now() + ms;
  while (Date.now() < deadline) {
    const ok = await new Promise((resolve) => {
      const s = net.connect(port, '127.0.0.1');
      s.once('connect', () => { s.destroy(); resolve(true); });
      s.once('error', () => resolve(false));
    });
    if (ok) return true;
    await sleep(250);
  }
  return false;
}

function killPidOnPort(port) {
  const { execSync } = require('child_process');
  try {
    const out = execSync(`lsof -ti:${port}`, { encoding: 'utf8' });
    for (const pid of out.trim().split('\n')) {
      if (pid) { try { process.kill(Number(pid), 'SIGTERM'); } catch {} }
    }
  } catch { /* nothing listening — fine */ }
}

/**
 * Kill ANY stale nova-script engine or virtualizer backend before booting the
 * test stack. Without this, an engine left running from an earlier session
 * (e.g. `nova-script live-show virtualizer` from last week) auto-reconnects
 * to our virtual "Launchpad Mini" port and writes conflicting LED frames,
 * making every color assertion flaky. This suite owns the stack for its run.
 */
function killStaleStackProcesses() {
  const { execSync } = require('child_process');
  for (const pat of ['src.main', 'novation-virtualizer.py', 'nova-script']) {
    try {
      const out = execSync(`pgrep -f '${pat}'`, { encoding: 'utf8' });
      for (const pid of out.trim().split('\n')) {
        if (!pid) continue;
        try { process.kill(Number(pid), 'SIGTERM'); } catch {}
      }
    } catch { /* none running — fine */ }
  }
  // Give them a beat to release virtual MIDI ports before we rebind.
  return new Promise((r) => setTimeout(r, 800));
}

// ── lifecycle ──────────────────────────────────────────────────────────────

let backend = null;
let engine = null;
let stop_requested = false;

/**
 * Bring up backend + engine, wait until both answer.
 * Safe to call repeatedly (idempotent: kills strays first).
 */
async function startStack() {
  // Kill any orphaned listeners + stale engines from previous runs (port 8766
  // backend) so nobody else writes LED frames to our virtual Launchpad.
  await killStaleStackProcesses();
  killPidOnPort(8766);

  // 1) Backend — virtual MIDI + WS server.
  backend = spawn(VENV_PYTHON, [BACKEND_SCRIPT], {
    cwd: PROJECT_ROOT,
    stdio: ['ignore', 'ignore', 'pipe'],
  });
  backend.stderr.on('data', (d) => {
    const line = d.toString();
    try { fs.appendFileSync(BACKEND_LOG, line, 'utf8'); } catch {}
  });

  const wsUp = await waitForPort(8766, 20000);
  if (!wsUp) throw new Error('virtualizer backend did not open :8766');

  // 2) Engine — real nova-script app, connects to virtual Launchpad.
  //    Uses the live-show-test profile: identical to live-show but with a
  //    longer 30s idle timeout so the 8s screensaver can't hijack the screen
  //    mid-test. Flow specs exercise the steady-state mode UI; the screensaver
  //    gets its own dedicated spec that forces it on via the idle combo.
  engine = spawn(VENV_PYTHON, ['-m', 'src.main', 'live-show-test'], {
    cwd: PROJECT_ROOT,
    stdio: ['ignore', 'ignore', 'pipe'],
  });
  engine.stderr.on('data', (d) => {
    const line = d.toString();
    process.stdout.write(`[ENGINE] ${line}`);
    try { fs.appendFileSync(ENGINE_LOG, line, 'utf8'); } catch {}
  });
  engine.on('exit', (code, signal) => {
    if (stop_requested) return;           // we asked for it — not an error
    throw new Error(`engine exited unexpectedly (code=${code} signal=${signal})`);
  });

  // Give the engine time to enumerate the virtual ports + run boot wave.
  await sleep(3000);
}

async function stopStack() {
  stop_requested = true;
  for (const p of [engine, backend]) {
    if (p && p.exitCode === null) {
      p.kill('SIGTERM');
    }
  }
  engine = null;
  backend = null;
  // let sockets close, then reap whatever remains on the virtualizer port.
  await sleep(800);
  killPidOnPort(8766);
}

module.exports = { startStack, stopStack };