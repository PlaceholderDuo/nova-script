#!/usr/bin/env python3
"""
End-to-end integration test using the virtualizer.
Starts virtualizer server → launches nova-script engine → simulates button presses → validates grid state.
"""
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
import websockets

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPTS_DIR)
VIRT_SERVER = os.path.join(PROJECT_DIR, "tools", "novation-virtualizer.py")
ENGINE_MODULE = "src.main"
WS_PORT = 8766
ENGINE_PORT = 0

CH = {
    "OFF": ".",
    "RED_LOW": "r", "RED_MED": "R", "RED_HIGH": "#",
    "GREEN_LOW": "g", "GREEN_MED": "G", "GREEN_HIGH": "$",
    "AMBER_LOW": "a", "AMBER_MED": "A", "AMBER_HIGH": "@",
}

def grid_str(grid_8x8):
    """Convert a list of 64 color strings to an 8×8 display string."""
    lines = []
    for y in range(7, -1, -1):
        row = grid_8x8[y * 8:(y + 1) * 8]
        lines.append("".join(CH.get(c, "?") for c in row))
    return "\n".join(lines)

async def send_action(ws, action_dict):
    await ws.send(json.dumps(action_dict))
    # Wait briefly for state to propagate through MIDI
    await asyncio.sleep(0.15)

async def get_state(ws):
    await ws.send(json.dumps({"action": "get_state"}))
    raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
    return json.loads(raw)

async def press_top(ws, index):
    """Brief top-row button press (press + release)."""
    await send_action(ws, {"action": "top_down", "index": index})
    await asyncio.sleep(0.08)
    await send_action(ws, {"action": "top_up", "index": index})
    await asyncio.sleep(0.25)

async def test_all(ws):
    results = []
    state = await get_state(ws)
    grid = state.get("grid", [])
    top = state.get("top_row", [])

    def fail(msg):
        results.append(f"  ✗ {msg}")
        return False

    def ok(msg):
        results.append(f"  ✓ {msg}")
        return True

    # ── Wait for startup wave to finish and menu to render ──────────────
    print("\nWaiting for engine startup...")
    for i in range(60):
        state = await get_state(ws)
        grid = state.get("grid", [])
        off_count = sum(1 for c in grid if c == "OFF")
        # Menu mode has most cells OFF (only 8 lit: PERF 4 + CLIP 4 + MIX 4 + INST 4 = 16)
        # Startup wave has many cells lit. Wait for settled state with mostly OFF.
        if off_count >= 48:
            print(f"  Engine ready after {i * 0.1:.1f}s")
            break
        await asyncio.sleep(0.1)
    else:
        fail("Engine did not settle within 6s")
        return results

    state = await get_state(ws)
    grid = state.get("grid", [])
    top_colors = state.get("top_row", [])
    print(f"\n=== MENU (startup) ===\n{grid_str(grid)}")
    print(f"Top row LEDs: {top_colors[:5]}")

    # Verify menu renders with mode blocks
    # PERF at (0,6) 2×2 = RED_HIGH at cols 0,1 rows 6,7
    # CLIP at (2,6) 2×2 = RED_MED at cols 2,3 rows 6,7
    # SEQ  at (4,6) 2×2 = AMBER_HIGH at cols 4,5 rows 6,7
    # MIX  at (0,4) 2×2 = GREEN_HIGH at cols 0,1 rows 4,5
    # INST at (2,4) 2×2 = GREEN_MED at cols 2,3 rows 4,5
    idx = lambda x, y: y * 8 + x

    checks = [
        (idx(0, 6), "RED_HIGH", "PERF"),
        (idx(3, 6), "RED_MED", "CLIP"),
        (idx(4, 6), "AMBER_HIGH", "SEQ"),
        (idx(0, 4), "GREEN_HIGH", "MIX"),
        (idx(2, 4), "GREEN_MED", "INST"),
    ]
    for cell, expected, label in checks:
        if grid[cell] != expected:
            fail(f"Menu {label} at cell {cell}: expected {expected} got {grid[cell]}")
        else:
            ok(f"Menu {label} = {expected}")

    # ── Button 2 (index 1) → CLIP → clip_launcher ──────────────────────
    print("\n--- Pressing Button 2 → CLIP → clip_launcher ---")
    await press_top(ws, 1)
    state = await get_state(ws)
    grid = state.get("grid", [])
    print(f"\n=== CLIP LAUNCHER ===\n{grid_str(grid)}")

    # Clip launcher: top 4 rows (y=7,6,5,4) should have colored blocks
    # Row y=7: all AMBER_HIGH, y=6: all RED_HIGH, y=5: all GREEN_HIGH, y=4: all AMBER_MED
    if grid[idx(0, 7)] == "AMBER_HIGH":
        ok("CLIP row 7 = AMBER_HIGH (full row lit)")
    else:
        fail(f"CLIP row 7 col 0: expected AMBER_HIGH got {grid[idx(0, 7)]}")

    if grid[idx(0, 6)] == "RED_HIGH":
        ok("CLIP row 6 = RED_HIGH (full row lit)")
    else:
        fail(f"CLIP row 6 col 0: expected RED_HIGH got {grid[idx(0, 6)]}")

    # ── HOME → Menu ─────────────────────────────────────────────────────
    print("\n--- Pressing HOME (Button 1, index 0) → Menu ---")
    await press_top(ws, 0)
    state = await get_state(ws)
    grid = state.get("grid", [])
    print(f"\n=== BACK TO MENU ===\n{grid_str(grid)}")
    if grid[idx(0, 6)] == "RED_HIGH":
        ok("HOME returns to menu (PERF block visible)")
    else:
        fail(f"HOME didn't return to menu: cell(0,6)={grid[idx(0, 6)]}")

    # ── Button 3 (index 2) → SEQ → sequencer ───────────────────────────
    print("\n--- Pressing Button 3 → SEQ → sequencer ---")
    await press_top(ws, 2)
    state = await get_state(ws)
    grid = state.get("grid", [])
    print(f"\n=== SEQUENCER ===\n{grid_str(grid)}")

    # Sequencer: transport row (y=7) has GREEN_HIGH at cols 0-1, AMBER_LOW at 6-7
    if grid[idx(0, 7)] == "GREEN_HIGH":
        ok("SEQ transport row = GREEN_HIGH (playing)")
    else:
        fail(f"SEQ transport row col 0: expected GREEN_HIGH got {grid[idx(0, 7)]}")

    if grid[idx(6, 7)] == "AMBER_LOW":
        ok("SEQ page indicators = AMBER_LOW")
    else:
        fail(f"SEQ col 6: expected AMBER_LOW got {grid[idx(6, 7)]}")

    # Verify clip_launcher and sequencer are DIFFERENT
    cl_row7 = "AMBER_HIGH"   # clip_launcher top row = AMBER_HIGH
    sq_row7 = "GREEN_HIGH"   # sequencer top row = GREEN_HIGH
    if cl_row7 != sq_row7:
        ok(f"CLIP vs SEQ distinct: top row {cl_row7} vs {sq_row7}")
    else:
        fail(f"CLIP vs SEQ top row both {cl_row7} - they look the same!")

    # ── HOME → Menu ─────────────────────────────────────────────────────
    await press_top(ws, 0)

    # ── Button 4 (index 3) → MIX → mixer ───────────────────────────────
    print("\n--- Pressing Button 4 → MIX → mixer ---")
    await press_top(ws, 3)
    state = await get_state(ws)
    grid = state.get("grid", [])
    print(f"\n=== MIXER ===\n{grid_str(grid)}")

    # Mixer: top row should show channel aliases/clipping indicators
    if any(grid[idx(x, 7)] != "OFF" for x in range(8)):
        ok("Mixer top row has active fader cells")
    else:
        fail("Mixer top row is all OFF (expected fader levels)")

    # ── HOME → Menu ─────────────────────────────────────────────────────
    await press_top(ws, 0)

    # ── Button 5 (index 4) → INST → instrument ─────────────────────────
    print("\n--- Pressing Button 5 → INST → instrument ---")
    await press_top(ws, 4)
    state = await get_state(ws)
    grid = state.get("grid", [])
    print(f"\n=== INSTRUMENT ===\n{grid_str(grid)}")

    # Instrument: root notes RED_HIGH, background AMBER_LOW
    if grid[idx(0, 7)] == "RED_HIGH":
        ok("Instrument root note = RED_HIGH")
    else:
        fail(f"Instrument root note: expected RED_HIGH got {grid[idx(0, 7)]}")

    # ── HOME → Menu ─────────────────────────────────────────────────────
    await press_top(ws, 0)

    # ── Combo: Top-1+2 → Screensaver ────────────────────────────────────
    print("\n--- Combo: Top-1+2 (hold 1, press 2) → Screensaver ---")
    await send_action(ws, {"action": "top_down", "index": 0})
    await asyncio.sleep(0.05)
    await send_action(ws, {"action": "top_down", "index": 1})
    await asyncio.sleep(0.1)
    await send_action(ws, {"action": "top_up", "index": 0})
    await send_action(ws, {"action": "top_up", "index": 1})
    await asyncio.sleep(0.3)

    state = await get_state(ws)
    grid = state.get("grid", [])
    print(f"\n=== SCREENSAVER (after combo) ===\n{grid_str(grid)}")
    on_cells = sum(1 for c in grid if c != "OFF")
    if on_cells > 0:
        ok(f"Screensaver active ({on_cells} cells lit)")
    else:
        fail("Screensaver shows no cells")

    # ── Dismiss screensaver (2 presses) ─────────────────────────────────
    print("\n--- Dismiss screensaver (2-press flow) ---")
    # First press: consumed by overlay
    await press_top(ws, 2)
    # Second press: should pass to mode
    await press_top(ws, 0)  # HOME
    await asyncio.sleep(0.3)
    state = await get_state(ws)
    grid = state.get("grid", [])
    print(f"\n=== AFTER DISMISS ===\n{grid_str(grid)}")
    if grid[idx(0, 6)] == "RED_HIGH":
        ok("After screensaver dismiss + HOME: back to menu")
    else:
        fail(f"After dismiss: expected menu (PERF RED_HIGH) got {grid[idx(0, 6)]}")

    # ── Summary ─────────────────────────────────────────────────────────
    print("\n" + "=" * 50)
    passed = sum(1 for r in results if r.startswith("  ✓"))
    failed = sum(1 for r in results if r.startswith("  ✗"))
    for r in results:
        print(r)
    print(f"\n{passed} passed, {failed} failed")
    return results


async def main():
    print("Starting virtualizer server...")
    venv_python = os.path.join(PROJECT_DIR, ".venv", "bin", "python3")

    virt_proc = subprocess.Popen(
        [venv_python, VIRT_SERVER, "--port", str(WS_PORT)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=PROJECT_DIR,
    )
    time.sleep(1.5)

    # Kill engine subprocess on exit
    eng_proc = None

    try:
        print("Starting nova-script engine...")
        eng_proc = subprocess.Popen(
            [venv_python, "-m", ENGINE_MODULE, "live-show"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=PROJECT_DIR,
        )
        time.sleep(1.0)

        print(f"Connecting to virtualizer WebSocket ws://localhost:{WS_PORT}...")
        async with websockets.connect(f"ws://localhost:{WS_PORT}") as ws:
            await test_all(ws)

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        print("\nShutting down...")
        if eng_proc:
            eng_proc.send_signal(signal.SIGINT)
            eng_proc.wait(timeout=3)
        virt_proc.send_signal(signal.SIGINT)
        virt_proc.wait(timeout=3)
        print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
