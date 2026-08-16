# Vault — Ops (commands & paths)

## Desktop ReflexKernel

```powershell
cd I:\grokbuild\EmbodI\ReflexKernel
.\.venv\Scripts\activate
pip install -e ".[dev]"
python -m pytest tests/ -v
python -m scripts.demo
```

Config: `configs/sim_only.yaml` (hardware-free)

## HIAgent (conceptual)

```powershell
# With XAI key in ~/.config/embodi/env
python -m HIAgent ...
```

See `HIAgent/README.md` and `scripts/standup.*`.

## Pi

```bash
# on Pi after git pull
./scripts/pi/01_verify_host.sh
./scripts/pi/02_standup_embodi.sh
```

## Blender MCP

1. Blender open, MCP add-on connected (9876)  
2. Grok `[mcp_servers.blender]` → `I:\Tools\blender_mcp\mcp\.venv\Scripts\python.exe -m blmcp`  
3. Smoke: create 20 mm cube / export STL under `Models/print/`  

## Scaffold master

```
Models/embodi_scaffold_v1.blend
```

## Grok memory (optional, parallel)

| Location | Role |
|----------|------|
| `~/.grok/memory/MEMORY.md` | Global prefs |
| `~/.grok/memory/grokbuild-*/MEMORY.md` | Workspace memory (search index) |
| `~/.grok/memory/grokbuild-*/sessions/` | Flushed session notes |

Repo vaults (`Context/`) are **not** auto-indexed by Grok memory — agents **read files** explicitly. After big sessions: `/flush` + update `Context/NOW.md`.
