# NOW — hot status

**Updated:** 2026-08-15  
**Active fuse:** Night stop — pattern **v0.1** (HI wishlist folded); scaffold print ~6h on plate; dry-fit tomorrow.

## Snapshot

| Area | Status | Pointer |
|------|--------|---------|
| ReflexKernel | Tests green (27); bridge + normalize_stimuli | `EmbodI/ReflexKernel/` |
| Sensory Cortex | Aligned dual-path; tests green | `SensoryCortex/` |
| HIAgent | Embedded + Saddle; Pi + desktop smoke OK | `HIAgent/` |
| Pi | Git-only standup; kernel + HIAgent once | `scripts/pi/`, vault `pi-hardware` |
| Blender MCP | Live (Lab MCP, mcp 1.x pin, port 9876) | vault `blender-mcp` |
| Scaffold | Print plate **in progress**; bed STLs single-body | `Models/print/print_bed_*.stl` |
| UE avatar | Dual stimuli locked: real + virtual → RK (Embodi only); UE = theater + viz | vault `architecture` + UE plan |

## Open / next

1. **Tomorrow:** dry-fit `print_bed_torso_back` + CanaKit when plate finishes (~6h)  
2. Optional AP-5: HIAgent always logs `activation_pattern`  
3. Later: UE dual-stimuli, limbs, ESP32/mics  

## Do not re-litigate

- Cortex does **not** re-fuse sensors (Coherence owns fusion)  
- Pi deploy = **git only** (no custom sync tool)  
- Mics at **featured ears**; Pi in **torso**; latches not glue-primary  
- Blender MCP = **Lab MCP** at `I:\Tools\blender_mcp` (not ahujasid)  
- Form language = **organic humanoid v2**, not boolean-coordinate boxes  
- **North star:** ground ethereal HI via enrichment; long-term HI “feel” = **activation patterns** from Embodi (see `vaults/architecture.md`)  

## Compaction recovery line

> Read `Context/NOW.md` + `Context/vaults/scaffold.md`. Master: `Models/embodi_scaffold_v2.blend`. Preview: `Models/print/_scaffold_v2_preview.png`.
