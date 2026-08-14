# Reaper OSC Setup — The Easy Way

**nova-script sends OSC → ReaLearn listens → Done.**  Everything runs on the same MacBook, so `127.0.0.1` (localhost) works forever — wifi changes don't matter.

## 3 Steps

### 1. Install ReaLearn
ReaPack → search "ReaLearn" → install.

### 2. Configure ReaLearn OSC
ReaLearn window → Settings (gear icon) → scroll to OSC:

| Field | Value | Why |
|---|---|---|
| **Local listen port** | `8000` | Where ReaLearn hears nova-script |
| **Device IP** | `127.0.0.1` | Localhost, never changes |
| **Device port** | `9001` | nova-script's listen port (optional, for feedback) |

Leave everything else default. Close settings.

> ⚠ **Device IP** is `127.0.0.1` — the same machine. It does NOT change when you change wifi networks.

### 3. Press buttons → Learn → Map
Press any pad on the Launchpad. In ReaLearn, click **"Learn source"** (or right-click → Learn) to capture the message. Then map it to whatever you want in Reaper — volume, FX parameter, action, anything. Repeat for each control you want to map.

## What nova-script Sends

| Launchpad Button | OSC Address | Value |
|---|---|---|
| GTR Volume (col 0 pads 0-7) | `/track/2/volume` | 0.0–1.0 |
| VOX Volume (col 4 pads 0-7) | `/track/1/volume` | 0.0–1.0 |
| GTR Delay presets (col 1-3, row 7-6) | `/track/2/fx/1/preset` | 1–6 |
| GTR Harmony presets (col 1-3, row 5-4) | `/track/2/fx/2/preset` | 1–6 |
| GTR Amp&Drv presets (col 1-3, row 3-2) | `/track/2/fx/3/preset` | 1–6 |
| GTR Tremolo presets (col 1-3, row 1-0) | `/track/2/fx/4/preset` | 1–6 |
| VOX Delay presets (col 5-7) | `/track/1/fx/1/preset` | 1–6 |
| VOX Harmony presets (col 5-7) | `/track/1/fx/2/preset` | 1–6 |
| VOX Drv&Flt presets (col 5-7) | `/track/1/fx/3/preset` | 1–6 |
| VOX Misc SFX presets (col 5-7) | `/track/1/fx/4/preset` | 1–6 |
| FX disable (red bar below FX) | `/track/{n}/fx/{k}/bypass` | 0=on, 1=off |
| Clip launch (Clip mode) | `/nova/clip/{track}/{scene}` | 0 or 1 |
| Mixer faders | `/track/{n}/volume` | 0.0–1.0 |
| Mixer mute | `/track/{n}/mute` | 0 or 1 |

## Switching Ports

If 8000 is taken by another app, edit `config/profiles/live-show.yaml`:
```yaml
osc:
  reaper_port: 8001
```
Then set ReaLearn's **local listen port** to `8001`.  Done.
