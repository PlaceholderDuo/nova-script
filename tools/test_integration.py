#!/usr/bin/env python3
"""Full integration test: virtualizer + nova-script end-to-end."""
import json, asyncio, subprocess, sys, time, signal, os
import websockets

NOVA_DIR = "/Users/rdfx1/Documents/projects/nova-script"
PYTHON = f"{NOVA_DIR}/.venv/bin/python"

async def main():
    proc_errors = []

    # 1. Start virtualizer
    virt = subprocess.Popen(
        [PYTHON, "tools/novation-virtualizer.py"],
        cwd=NOVA_DIR,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True
    )
    await asyncio.sleep(2)

    try:
        async with websockets.connect('ws://localhost:8766') as ws:
            await ws.recv()  # initial state
            await ws.send(json.dumps({'action': 'connect'}))
            state = json.loads(await ws.recv())
            assert state['connected'], f"MIDI not connected: {state}"
            print("1. Virtual MIDI ports: OK")

            # 2. Start nova-script
            ns = subprocess.Popen(
                [PYTHON, "-m", "src.main", "live-show"],
                cwd=NOVA_DIR,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            await asyncio.sleep(4)

            # Collect any stderr from nova-script
            err_output = ""
            try:
                err_output = ns.stderr.read() or ""
            except Exception:
                os.set_blocking(ns.stderr.fileno(), False)
                err_output = ns.stderr.read() or ""

            if "Connected" in err_output or "Switched to mode" in err_output:
                print("2. Nova-script connected to virtual Launchpad: OK")
            else:
                print(f"2. Nova-script stderr (first 500 chars):")
                for line in err_output[:500].split('\n')[-6:]:
                    print(f"   {line}")

            # 3. Simulate pad press
            await ws.send(json.dumps({'action': 'press_pad', 'x': 3, 'y': 4}))
            await asyncio.sleep(0.3)
            state = json.loads(await ws.recv())

            grid = state.get('grid', [])
            top = state.get('top_row', [])
            right = state.get('right_col', [])
            lit = sum(1 for row in grid for c in row if c != 'OFF')
            top_lit = sum(1 for c in top if c != 'OFF')
            right_lit = sum(1 for c in right if c != 'OFF')
            print(f"3. Grid: {lit}/64 lit, Top: {top_lit}/8, Right: {right_lit}/8")
            print(f"3. Top row: {top}")
            print(f"3. Right col: {right}")

            if lit > 0 or top_lit > 0 or right_lit > 0:
                print("PASS: nova-script → virtualizer LED communication works")
            else:
                print("FAIL: No LED updates from nova-script — checking connection")
                # Check if ports were connected
                import rtmidi
                mi = rtmidi.MidiIn()
                in_ports = mi.get_ports()
                mi.delete()
                print(f"     Current MIDI IN ports: {in_ports}")

            ns.terminate()
            ns.wait(timeout=5)

    finally:
        virt.terminate()
        try:
            virt.wait(timeout=5)
        except subprocess.TimeoutExpired:
            virt.kill()
            virt.wait()

    print("Done.")

asyncio.run(main())
