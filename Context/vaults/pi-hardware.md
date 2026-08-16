# Vault — Pi + hardware path

## Deploy policy (locked)

**Git only** on the Pi — no custom sync tool. Desktop is source; Pi `git pull`.

## Scripts

`scripts/pi/` — `01_verify_host.sh`, `02_standup_embodi.sh`, `common.sh`, README

## Env / keys

- xAI: `~/.config/embodi/env` (via `HIAgent/env_bootstrap.py` pattern)  
- Never commit API keys  

## Verified once (prior sessions)

- Kernel smoke on Pi  
- HIAgent short run on Pi  

## Hardware direction (mechanical)

| Item | Placement intent |
|------|------------------|
| Pi 5 (CanaKit) | Torso bay |
| MAX9814 ×2 | Ear cups (featured) |
| ESP32 ×1+ | Head mic node |
| Battery + TP4056 | Torso tray + charge access |
| Ear mics wiring | ESP32 head path (firmware later) |

## Out of scope for shell v1

Live wiring firmware, full limbs, UE avatar (separate app plan).
