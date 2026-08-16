# Blender MCP setup (Embodi scaffold)

**Goal:** Let Grok Build drive Blender for scaffold modeling and STL/3MF export.

**Status:** Blender Lab MCP installed at `I:\Tools\blender_mcp` (2026-08).  
**Config:** Project `.grok/config.toml` → `[mcp_servers.blender]`

---

## 1. What is installed

| Piece | Location |
|-------|----------|
| Lab source tree | `I:\Tools\blender_mcp\` |
| Add-on | Installed in Blender (MCP extension; needs **Blender 5.1+**) |
| MCP package | `I:\Tools\blender_mcp\mcp\` (`blmcp`, entry `blender-mcp`) |
| uv | `C:\Users\Agentdud\.local\bin\uv.exe` |

**Data flow:**

```text
Grok Build  ⇐ stdio MCP ⇒  uv run blender-mcp  ⇐ TCP 127.0.0.1:9876 ⇒  Blender add-on
```

---

## 2. Grok Build config (project)

In `I:\GrokBuild\.grok\config.toml`:

```toml
[mcp_servers.blender]
command = "I:\\Tools\\blender_mcp\\mcp\\.venv\\Scripts\\python.exe"
args = ["-m", "blmcp"]
enabled = true
startup_timeout_sec = 120
env = { BLENDER_MCP_HOST = "127.0.0.1", BLENDER_MCP_PORT = "9876" }
```

**Important:** Lab’s `blmcp` needs **`mcp.server.fastmcp` (MCP SDK 1.x)**.  
`mcp` 2.0 removed FastMCP; if `uv` resolves to 2.0, the server crashes on handshake.

Pin in `I:\Tools\blender_mcp\mcp\pyproject.toml`:

```toml
"mcp[cli]>=1.9.0,<2.0",
```

Then:

```powershell
cd I:\Tools\blender_mcp\mcp
uv lock
uv sync
python -c "from mcp.server.fastmcp import FastMCP; print('OK')"
python -m blmcp --help
```

---

## 3. Every session checklist

1. Start **Blender 5.1+** with your scaffold file (or empty scene).  
2. Ensure **MCP add-on** is enabled and its **bridge server is running** (preferences → start if not auto-start).  
3. Confirm TCP listen (PowerShell):  
   `Get-NetTCPConnection -LocalPort 9876 -State Listen`  
4. Start **Grok Build** in `I:\GrokBuild` (or restart after config changes).  
5. Confirm blender tools appear (not “timed out”).

---

## 4. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `blender` MCP **timed out after 60s** | `uv` not on Grok PATH | Full path to `uv.exe` (above) |
| Tools fail / cannot connect to Blender | Add-on not listening | Start MCP server in Blender prefs; check port 9876 |
| Wrong Blender version | Need 5.1+ for Lab add-on | Upgrade Blender |
| Slow first start | `uv run` resolving env | Run once: `cd I:\Tools\blender_mcp\mcp; uv run blender-mcp` then Ctrl+C |
| Port mismatch | Add-on not on 9876 | Align prefs with `BLENDER_MCP_PORT` |

---

## 5. Project conventions (once connected)

| Convention | Value |
|------------|--------|
| Scene unit | Millimeters |
| Master file | `Models/embodi_scaffold_v1.blend` |
| Collections | `REF_legacy`, `BAYS`, `SHELL_HEAD`, `SHELL_TORSO`, `HARDWARE_PROXY`, `PRINT_STAGES` |
| Export dir | `Models/print/` |
| Naming | `bay_pi5`, `bay_esp32_head`, `bay_mic_l`, `bay_mic_r`, `bay_battery`, … |

---

## 6. Smoke test

1. Blender open + port 9876 listening.  
2. Grok session with blender MCP connected.  
3. Agent: create a 20×20×20 mm cube named `mcp_smoke`.  
4. Export `Models/print/_smoke_cube.stl`.  
5. Open in Bambu Studio — confirm **20 mm** scale.

---

## 7. Security

Lab warning: MCP can run LLM-generated Python **inside Blender**. Use non-sensitive project files only.

---

## 8. Related

- Scaffold plan: `Travelers/Docs/Scaffold_Print_P2S_Plan.md`  
- Parts list: `Parts.md`  
- Measurements: `Models/BOM_MEASUREMENTS.md`  
- Lab tree: `I:\Tools\blender_mcp\`
