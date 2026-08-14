/**
 * global-setup.js — Playwright boot hook. Must export ONE function.
 *
 * Playwright calls this once, before any test, when launching `npm test`.
 * It brings the whole stack (virtualizer backend + real engine) up once so
 * every test in the run shares a live rig. Pair with global-teardown.js.
 */

const { startStack } = require('./lib/stack');

async function globalSetup() {
  console.log('[global-setup] starting virtualizer backend + nova-script engine…');
  try {
    await startStack();
  } catch (err) {
    console.error('[global-setup] FAILED to boot the stack:', err.message);
    throw err;
  }
  console.log('[global-setup] stack is live — browser tests will run now');
}

module.exports = globalSetup;