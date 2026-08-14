#!/usr/bin/env python3
"""E2E: virtualizer + engine, verify button presses switch modes."""
import asyncio
import json
import signal
import subprocess
import sys
import time

import websockets

PROJECT = "/Users/rdfx1/Documents/projects/nova-script"
CH = {"OFF": ".", "RED_LOW": "r", "RED_MED": "R", "RED_HIGH": "#",
      "GREEN_LOW": "g", "GREEN_MED": "G", "GREEN_HIGH": "$",
      "AMBER_LOW": "a", "AMBER_MED": "A", "AMBER_HIGH": "@"}


def gstr(g):
    return "\n".join("".join(CH.get(c, "?") for c in row) for row in reversed(g))


async def main():
    subprocess.run(["pkill", "-f", "novation-virtualizer"], capture_output=True)
    subprocess.run(["pkill", "-f", "src.main"], capture_output=True)
    await asyncio.sleep(1)

    virt = subprocess.Popen(
        [f"{PROJECT}/.venv/bin/python3", f"{PROJECT}/tools/novation-virtualizer.py"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=PROJECT)
    await asyncio.sleep(2)

    eng = None
    try:
        async with websockets.connect("ws://localhost:8766") as ws:
            eng = subprocess.Popen(
                [f"{PROJECT}/.venv/bin/python3", "-m", "src.main", "live-show"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=PROJECT)

            async def g():
                # Drain stale broadcasts queued before our get_state response.
                for _ in range(6):
                    await ws.send(json.dumps({"action": "get_state"}))
                    raw = await asyncio.wait_for(ws.recv(), timeout=5)
                return json.loads(raw)

            async def btn(i):
                await ws.send(json.dumps({"action": "top_down", "index": i}))
                await asyncio.sleep(0.08)
                await ws.send(json.dumps({"action": "top_up", "index": i}))
                await asyncio.sleep(2.0)

            print("Waiting 15s for startup...", flush=True)
            await asyncio.sleep(15)

            s = await g()
            grid0 = s["grid"]
            lit0 = sum(1 for r in grid0 for c in r if c != "OFF")
            print(f"START mode={s.get('mode')!r} lit={lit0}\n{gstr(grid0)}", flush=True)

            results = []
            expected = [("CLIP", 1), ("SEQ", 2), ("MIX", 3), ("INST", 4), ("MENU", 5)]
            prev_grid = grid0
            prev_label = "START"
            for label, idx in expected:
                await btn(idx)
                s = await g()
                grid = s["grid"]
                lit = sum(1 for r in grid for c in r if c != "OFF")
                changed = grid != prev_grid
                print(f"{label} mode={s.get('mode')!r} lit={lit} changed={changed}\n{gstr(grid)}", flush=True)
                results.append((label, changed, lit))
                prev_grid = grid
                prev_label = label

            ok = sum(1 for _, c, _ in results if c)
            print(f"\n=== MODE SWITCH: {ok}/5 distinct ===", flush=True)

            eng.send_signal(signal.SIGINT)
            out, err = eng.communicate(timeout=5)
            print("--- engine stderr ---", flush=True)
            for line in err.decode().split("\n"):
                if any(k in line for k in ("Switched", "Overlay", "EVENT", "Connected Launchpad")):
                    print(line, flush=True)
    except Exception as e:
        print(f"E2E ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        if eng:
            try:
                eng.send_signal(signal.SIGINT)
                eng.wait(timeout=5)
            except Exception:
                pass
        virt.send_signal(signal.SIGINT)
        try:
            virt.wait(timeout=5)
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())