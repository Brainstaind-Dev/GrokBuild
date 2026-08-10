# Blender MCP setup (Embodi scaffold)

**Goal:** Let Grok Build drive Blender for scaffold modeling and STL/3MF export.

**Status:** Not connected in project `.grok/config.toml` yet.

---

## 1. Install Blender

- Install **Blender 4.x LTS** (or current stable) on the Windows desktop.  
- Confirm it launches: `blender --version` if on PATH, or note full path e.g.  
  `C:\Program Files\Blender Foundation\Blender 4.x\blender.exe`

---

## 2. Install a Blender MCP bridge

Pick one maintained **Blender MCP** integration (addon + MCP server) that exposes tools such as:

- create/list/delete objects  
- set transforms / dimensions  
- import/export STL or OBJ  
- optionally execute Python in Blender  

Record here after install:

| Field | Value |
|-------|--------|
| Package / repo | |
| Version | |
| Addon enabled | yes / no |
| Server start command | |
| Port / transport | |

---

## 3. Register with Grok Build

Add to **user** or **project** MCP config (example shape only — match your package):

```toml
[mcp_servers.blender]
command = "uvx"   # or npx / python path from package docs
args = ["blender-mcp"]
enabled = true
startup_timeout_sec = 60
```

Or if the server is “connect to running Blender addon”:

1. Start Blender.  
2. Enable MCP addon / start server from Blender UI.  
3. Point Grok MCP client at that endpoint per addon docs.

Restart Grok session and confirm **blender** tools appear.

---

## 4. Project conventions (once connected)

| Convention | Value |
|------------|--------|
| Scene unit | Millimeters |
| Master file | `Models/embodi_scaffold_v1.blend` |
| Collections | `REF_legacy`, `BAYS`, `SHELL_HEAD`, `SHELL_TORSO`, `HARDWARE_PROXY`, `PRINT_STAGES` |
| Export dir | `Models/print/` |
| Naming | `bay_pi5`, `bay_esp32_head`, `bay_mic_l`, `bay_mic_r`, `bay_battery`, … |

---

## 5. Smoke test

1. Create a 20×20×20 mm cube named `mcp_smoke`.  
2. Export `Models/print/_smoke_cube.stl`.  
3. Open in Bambu Studio — confirm scale is mm (20 mm cube).  

---

## 6. Fallback (no MCP)

Use manual Blender with the same collections and `BOM_MEASUREMENTS.md`.  
Agent still provides dimensions, stage list, and review against P2S limits.

---

## 7. Related

- Scaffold plan: `Travelers/Docs/Scaffold_Print_P2S_Plan.md`  
- Parts list: `Parts.md`  
- Legacy meshes: `Models/*.stl`, `Models/*.blend`
