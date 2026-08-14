/**
 * global-teardown.js — Playwright shutdown hook. Must export ONE function.
 *
 * Called once after the whole run finishes (even if tests failed hard), so
 * we never leave orphan processes holding virtual MIDI ports. This is what
 * makes the suite rerunnable without "address in use" surprises.
 */

const { stopStack } = require('./lib/stack');

async function globalTeardown() {
  console.log('[global-teardown] stopping engine + backend…');
  try {
    await stopStack();
    console.log('[global-teardown] stack stopped cleanly');
  } catch (err) {
    console.error('[global-teardown] had trouble stopping:', err.message);
  }
}

module.exports = globalTeardown;