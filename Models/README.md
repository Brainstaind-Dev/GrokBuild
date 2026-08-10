# Models — Embodi scaffold & print assets

Physical **shell/scaffold** geometry for Embodi hardware (biomimetic layout).  
Software stack stays in `EmbodI/`, `SensoryCortex/`, `HIAgent/`.

## Key docs

| Doc | Purpose |
|-----|---------|
| [../Travelers/Docs/Scaffold_Print_P2S_Plan.md](../Travelers/Docs/Scaffold_Print_P2S_Plan.md) | Full staged-print plan (P2S 256³) |
| [BOM_MEASUREMENTS.md](BOM_MEASUREMENTS.md) | Caliper table for bays |
| [BLENDER_MCP_SETUP.md](BLENDER_MCP_SETUP.md) | Connect Blender MCP to Grok Build |
| [../Parts.md](../Parts.md) | Component inventory |

## Layout targets

- **Head:** dual MAX9814 at **featured ear positions** (pinna-like cups/ridges for directionality), ESP32, optional IMU  
- **Torso:** Raspberry Pi 5, battery + charge, speakers/amps, **latched** service access  
- **Assembly:** latch/clip-first joining of major shells (plus screws where needed)  
- **Printer:** Bambu Lab P2S — print in stages ≤ ~250 mm  
- **Form:** feature-rich biomimetic shell encouraged — not a blank smooth capsule

## Legacy files (reference)

Head/torso STL and blend iterations from earlier Grok Web scaffold work (`Head_*`, `Torso_*`, `*Minus.blend`, etc.).

## Target master file

`embodi_scaffold_v1.blend` — create after measurements + Blender MCP (or manual Blender).

## Print exports

`print/` — staged STL/3MF for Bambu Studio (create when exporting).

## Git note

Large binaries may need Git LFS later. Prefer committing stage STLs when stable; keep WIP blends local if huge.
