# Vault — Blender Lab MCP

## Stack

| Piece | Detail |
|-------|--------|
| Install tree | `I:\Tools\blender_mcp` |
| MCP server | `mcp\.venv\Scripts\python.exe -m blmcp` |
| Bridge | Blender add-on TCP **127.0.0.1:9876** |
| Blender | **5.2** (user machine) |
| Grok config | `.grok/config.toml` → `[mcp_servers.blender]` |

## Critical pin

```
mcp[cli] >= 1.9.0, < 2.0
```

**Why:** `mcp==2.0` removed `mcp.server.fastmcp.FastMCP` → Lab `blmcp` import crash → Grok handshake “connection closed”.

## Do / don’t

- **Do** use venv Python `-m blmcp`  
- **Don’t** use bare `uv` on PATH (Grok often lacks `~/.local/bin`)  
- Prefer dedicated blender tools; `execute_blender_code` last resort  
- Inspect scene before destructive edits  

## Smoke (done)

- Object `mcp_smoke` 20×20×20 mm  
- STL `Models/print/_smoke_cube.stl`  
- Units metric mm  

## Setup doc

`Models/BLENDER_MCP_SETUP.md`
