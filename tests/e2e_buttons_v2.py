#!/usr/bin/env python3
"""E2E v2: virtualizer + engine, stable-state verification of mode switches."""
import asyncio
import json
import subprocess
import sys

import websockets

PROJECT = "/Users/rdfx1/Documents/projects/nova-script"
CH = {"OFF": ".", "RED_LOW": "r", "RED_MED": "R", "RED_HIGH": "#",
      "GREEN_LOW": "g", "GREEN_MED": "G", "GREEN_HIGH": "$",
      "AMBER_LOW": "a", "AMBER_MED": "A", "AMBER_HIGH": "@"}


def gstr(g):
    return "\n".join("".join(CH.get(c, "?") for c in row) for row in reversed(g))


async def read_state(ws):
    """Poll get_state until the device grid is stable (2 consecutive identical)."""
    last = None
    for _ in range(20):
        await ws.send(json.dumps({"action": "get_state"}))
        raw = await asyncio.wait_for(ws.recv(), timeout=5)
        s = json.loads(raw)
        grid = s.get("grid", [])
        if grid == last:
            return s
        last = grid
        await asyncio.sleep(0.25)
    return s


async def main():
    subprocess.run(["pkill", "-f", "novation-virtualizer"], capture_output=True)
    subprocess.run(["pkill", "-f", "src.main"], capture_output=True)
    subprocess.run(["pkill", "-f", "nova-script"], capture_output=True)
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
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=PROJECT)

            async def btn(i):
                await ws.send(json.dumps({"action": "top_down", "index": i}))
                await asyncio.sleep(0.1)
                await ws.send(json.dumps({"action": "top_up", "index": i}))
                await asyncio.sleep(1.0)

            await asyncio.sleep(8)
            s = await read_state(ws)
            lit0 = sum(1 for r in s["grid"] for c in r if c != "OFF")
            print(f"START mode={s.get('mode')!r} lit={lit0}", flush=True)

            seq = [("CLIP", 1), ("SEQ", 2), ("MIX", 3), ("INST", 4), ("MENU", 5)]
            prev_key = tuple(tuple(r) for r in s["grid"])
            results = []
            for label, idx in seq:
                await btn(idx)
                await btn(idx)  # double-tap to handle 2-press overlays
                s = await read_state(ws)
                grid = s["grid"]
                lit = sum(1 for r in grid for c in r if c != "OFF")
                key = tuple(tuple(r) for r in grid)
                changed = key != prev_key
                print(f"{label} mode={s.get('mode')!r} lit={lit} changed={changed}", flush=True)
                results.append(changed)
                prev_key = key

            print(f"\n=== MODE SWITCH DISTINCT: {sum(results)}/5 ===", flush=True)
    except Exception as e:
        print(f"E2E ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        if eng:
            try:
                eng.send_signal(subprocess.signal.SIGINT)
                eng.wait(timeout=5)
            except Exception:
                pass
        virt.send_signal(subprocess.signal.SIGINT)
        try:
            virt.wait(timeout=5)
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())