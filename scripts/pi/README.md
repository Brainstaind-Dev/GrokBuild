# Raspberry Pi scripts (Embodi)

Git is the **only** update system. After `git pull` on the Pi, use these scripts to verify the host and stand up Embodi.

```text
Desktop:  commit → push
Pi:       git pull --ff-only → scripts/pi/…
```

## Scripts

| Order | Script | Purpose |
|------:|--------|---------|
| 1 | `01_verify_host.sh` | Check OS packages, arch, I2C/GPIO, git clone layout |
| 2 | `02_standup_embodi.sh` | venv, `pip install -e`, PYTHONPATH, tests, kernel smoke |

Shared helpers: `common.sh`  
Generated after standup: `env.pi.sh` (source in new shells)

## First-time on the Pi

```bash
# After cloning GrokBuild and installing apt packages (see 01 output if anything is missing):
cd ~/GrokBuild   # or your clone path

chmod +x scripts/pi/*.sh

# Step 1 — host tools
./scripts/pi/01_verify_host.sh

# Step 2 — Embodi project
./scripts/pi/02_standup_embodi.sh
```

### Optional flags (`02_standup_embodi.sh`)

| Flag | Meaning |
|------|---------|
| `--with-mcp` | Also install MCP extra |
| `--with-xai` | `pip install xai-sdk` for HIAgent |
| `--start-saddle` | After setup, run Saddle in foreground |
| `--host 0.0.0.0` | Bind address when starting Saddle |
| `--port 8000` | Port when starting Saddle |
| `--skip-tests` | Skip pytest |
| `--skip-verify` | Skip re-running `01_verify_host.sh` |

Examples:

```bash
# Full install + LAN Saddle
./scripts/pi/02_standup_embodi.sh --start-saddle --host 0.0.0.0 --port 8000

# With HI agent deps
./scripts/pi/02_standup_embodi.sh --with-xai
export XAI_API_KEY=xai-…   # secret, not key ID
source scripts/pi/env.pi.sh
python -m HIAgent interactive --backend embedded
```

## After every `git pull`

```bash
cd ~/GrokBuild
git pull --ff-only
./scripts/pi/02_standup_embodi.sh --skip-verify   # or full run
# or only if deps changed:
source scripts/pi/env.pi.sh
cd EmbodI/ReflexKernel && pip install -e ".[dev,server]"
```

## Apt packages (expected baseline)

```bash
sudo apt update
sudo apt install -y git python3-pip python3-venv python3-dev \
  build-essential libopenblas-dev \
  i2c-tools python3-smbus \
  libportaudio2 portaudio19-dev \
  python3-lgpio python3-gpiozero
sudo usermod -aG i2c,gpio "$USER"
# log out/in; enable I2C via raspi-config if needed
```

## Notes

- Default config for smoke/Saddle: `EmbodI/ReflexKernel/configs/mcp_headless.yaml` (no pygame).
- Hardware drivers remain stubs; I2C/GPIO checks prepare for later sensor work.
- Do not commit Pi `.venv/` or local `logs/` / `data/` (gitignored).
- Windows desktop stand-up remains `HIAgent/scripts/standup.ps1` — separate from these Pi scripts.
