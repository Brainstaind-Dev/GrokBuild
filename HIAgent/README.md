# HIAgent — Higher Intelligence on the Saddle

Grok (via **xAI API**) as mind, **Sensory Cortex** as felt sense, **ReflexKernel** as body.

```
You / pulse loop
    → HIAgent (tools)
        → xAI API (Grok)
        → Body backend: embedded RK+Cortex  OR  remote Saddle HTTP
```

## Prerequisites

1. ReflexKernel venv with deps + `xai-sdk`:
   ```powershell
   cd I:\GrokBuild\EmbodI\ReflexKernel
   .\.venv\Scripts\activate
   pip install -e ".[server,dev]"
   pip install xai-sdk
   ```
2. **`XAI_API_KEY`** = API **secret** (`xai-…`), not the key ID. Supported sources (does not override a key already in the process env):
   - **Pi / Linux:** `~/.config/embodi/env` with `export XAI_API_KEY=xai-...` (`chmod 600`); optional `source` from `~/.bashrc`
   - **Windows:** User env var *or* `%USERPROFILE%\.config\embodi\env`
   - Optional gitignored project `.env`
   - Loaded automatically by HIAgent (`env_bootstrap`); Pi `scripts/pi/env.pi.sh` also sources `~/.config/embodi/env`
3. Repo paths on `PYTHONPATH` when running manually (stand-up script sets this).

## Quick start (recommended)

### A) Simplest — embedded body (one process)

```powershell
cd I:\GrokBuild
.\HIAgent\scripts\standup.ps1 -Mode EmbeddedAgent -StartAgent interactive
```

Or:

```powershell
$env:PYTHONPATH = "I:\GrokBuild;I:\GrokBuild\EmbodI\ReflexKernel\src"
cd I:\GrokBuild
& EmbodI\ReflexKernel\.venv\Scripts\python.exe -m HIAgent interactive --backend embedded
```

### B) Remote Saddle + agent

```powershell
.\HIAgent\scripts\standup.ps1 -Mode FullRemote -StartAgent interactive
```

Order of stand-up:

1. Check Python venv + `XAI_API_KEY`
2. Start ReflexKernel Saddle (`scripts.server`)
3. Start conversation bridge (Grok Web path; optional failure is non-fatal if missing)
4. Start HIAgent (foreground)

### C) Saddle only

```powershell
.\HIAgent\scripts\standup.ps1 -Mode SaddleOnly -StartAgent none
```

## CLI

```text
python -m HIAgent interactive [--backend embedded|saddle] [--model …] [--viz]
python -m HIAgent pulse [--interval 3] [--max-cycles 10]
python -m HIAgent once "Feel your body and describe it."
```

## Tools available to Grok

| Tool | Role |
|------|------|
| `feel` | Sensory Cortex experience package |
| `body_snapshot` | Broader kernel state |
| `recall` | High-arousal memory |
| `inject_thought` | Affective seed into body |
| `send_reward` | Teaching signal |
| `inject_stimulus` / `step` | Sim stimulus + ticks |
| `begin_demo` / `end_demo` | Learner demos |
| `get_status` | Backend + feed status |
| **`pause_feed`** | Pause automatic BODY UPDATEs / pulse feel injection |
| **`resume_feed`** | Resume after pause |

### Pause / resume (HI-controlled quiet time)

1. Grok calls **`pause_feed`** (optional reason).  
2. Interactive auto-feel and autonomous pulse **stop pushing** new experiences (voluntary `feel force=true` still works).  
3. After **`pause_poll_sec`** (default **30**), the agent injects a system check: *ready to resume?*  
4. Grok should call **`resume_feed`** or pause again.

```powershell
python -m HIAgent interactive --pause-poll 30
```

## Session logs

JSONL under `data/hi_sessions/` (gitignored). Each session records feels, tool calls, and assistant text.

## Tests

```powershell
cd I:\GrokBuild
$env:PYTHONPATH = "I:\GrokBuild;I:\GrokBuild\EmbodI\ReflexKernel\src"
& EmbodI\ReflexKernel\.venv\Scripts\python.exe -m pytest HIAgent/tests/ SensoryCortex/tests/ -q
```

Live xAI is **not** required for unit tests. For a live one-shot:

```powershell
& …\python.exe -m HIAgent once "Call feel, then say one sentence about what you sense."
```

## Config / env

| Variable | Purpose |
|----------|---------|
| `XAI_API_KEY` | xAI secret (required for LLM) |
| `REFLEXKERNEL_API_KEY` | Saddle API key (remote) |
| `HI_AGENT_MODEL` | Override model |
| `HI_AGENT_BACKEND` | `embedded` / `saddle` |

See `HIAgent/config.py` for full options.
