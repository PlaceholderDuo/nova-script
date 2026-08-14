/**
 * osc.js — tiny OSC client for the test suite.
 *
 * Some modes in nova-script react to LIVE input that never appears on the
 * Launchpad hardware: the tuner listens for note events, the mixer's VU
 * meters react to Reaper fader signals, the sequencer's beat clock comes
 * from Reaper. To exercise those flows in the browser we inject the exact
 * same OSC messages the real DAW would send, straight at the engine's OSC
 * listener (default :9001).
 *
 * The engine talks OSC to the Akai Force (outbound) and to Reaper (inbound).
 * We only need the inbound half: `send_bundle(msg)` wakes the engine's OSC
 * handler, which then computes LED state and pushes it down to the
 * virtualizer over MIDI — the same path real input takes.
 *
 * We use a minimal OSC encoder because the system python-osc library may not
 * be installed in the venv; this file reimplements just enough of the OSC
 * packet framing to build a valid bundle (a few dozen lines, fully tested in
 * this suite). Keeps the harness dependency-free.
 */

const dgram = require('dgram');

function oscString(s) {
  const buf = Buffer.from(s, 'utf8');
  const len = Math.ceil((buf.length + 1) / 4) * 4;
  const out = Buffer.alloc(len);
  out.set(buf);
  return out;
}

function oscInt(n) {
  const b = Buffer.alloc(4);
  b.writeInt32BE(n);
  return b;
}

function oscFloat(f) {
  const b = Buffer.alloc(4);
  b.writeFloatBE(f);
  return b;
}

/** Encode a single OSC message (address + args) as a padded byte buffer. */
function encodeMessage(addr, args) {
  let types = ',';
  const data = [];
  for (const a of args) {
    if (typeof a === 'number' && Number.isInteger(a)) { types += 'i'; data.push(oscInt(a)); }
    else if (typeof a === 'number') { types += 'f'; data.push(oscFloat(a)); }
    else { types += 's'; data.push(oscString(String(a))); }
  }
  return Buffer.concat([oscString(addr), oscString(types), ...data]);
}

/**
 * Encode a set of OSC messages into a single /bundle datagram.
 *
 * Wire format (RFC-like OSC):
 *   "#bundle"  |  int64 timetag (0 = immediately)  |  { int32 size + message }*
 * Each "size" is that message's byte length (already a multiple of 4, since
 * every OSC atom — string, int, float — is individually padded).
 */
function encodeBundle(messages) {
  // OSC spec: bundle = "#bundle\0" (8 bytes, NUL-terminated) + 8-byte
  // timetag. pythonosc requires the exact "#bundle\0" prefix; without the
  // NUL every following field is read one byte early and nothing parses.
  const parts = [Buffer.from('#bundle\0', 'utf8'), Buffer.alloc(8)];
  for (const [addr, args] of messages) {
    const msg = encodeMessage(addr, args);
    parts.push(oscInt(msg.length), msg);
  }
  return Buffer.concat(parts);
}

/**
 * Send a bunch of OSC messages to the engine in one UDP datagram.
 * Returns a Promise that resolves when the datagram is flushed to the socket.
 */
function sendOsc(host, port, messages, timeoutMs = 2000) {
  return new Promise((resolve, reject) => {
    const sock = dgram.createSocket('udp4');
    const payload = encodeBundle(messages);
    const timer = setTimeout(() => {
      sock.close();
      reject(new Error('OSC send timed out (is the engine running?)'));
    }, timeoutMs);

    sock.send(payload, port, host, (err) => {
      clearTimeout(timer);
      sock.close();
      if (err) reject(err);
      else resolve();
    });
  });
}

/**
 * Convenience: send a single OSC message (addr + args) to the engine.
 */
async function osc(host, port, addr, args) {
  return sendOsc(host, port, [[addr, args]]);
}

module.exports = { sendOsc, osc };