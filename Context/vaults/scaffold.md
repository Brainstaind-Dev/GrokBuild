# Vault — Scaffold / print shell

## Goal

Biomimetic printable head+torso scaffold for Embodi hardware on **Bambu P2S** (256³, design max ~250 mm/stage).

## Design language (locked 2026-08-10)

**Clean organic humanoid** — not the old boolean-coordinate block models.

| Generation | File | Notes |
|------------|------|--------|
| **v2 current** | `Models/embodi_scaffold_v2.blend` | Ellipsoid union → voxel remesh → smooth; featured ear cups |
| v1 archive | `Models/embodi_scaffold_v1.blend` | First bay pass on legacy REF boxes |
| Legacy REF STLs | `Models/Head_*`, `Torso_*` | Boolean-era; kept on disk, not form source |

Legacy geometry may live in collection **`ARCHIVE_legacy`** (hidden) inside v2 for comparison only.

## Locked layout (still)

- MAX9814 ×2 → **featured ear** pinnae with forward cup  
- Pi 5 → **torso back** bay + airflow  
- ESP32 → **head** node  
- Battery + charge → lower torso back / panel  
- Joins → **latches first** (not built yet)  

## Phase status

| Phase | Status |
|------:|--------|
| 0 MCP + smoke | Done |
| 1 Master + bays (boxy v1) | Superseded by v2 clean form |
| 1b Clean organic form + soft bays | Done |
| **2–3 Print-ready openable shell** | **Done** 2026-08-10 — hollow ~2 mm, head+torso F/B clamshells, open seams, stage STLs |
| 4 Refine latches, lips, vents, board cradles | Open |
| 5 P2S dry-fit + iterate | Open (STLs ready) |
| Later | Arms, hands, waist, legs, feet |

## Master file (use this)

`Models/embodi_scaffold_v2.blend` — units **mm**

### Collections

| Collection | Contents |
|------------|----------|
| **PRINT_BED** | Shell halves + ears in **print pose** (Z=0, cavity up) — export `print_bed_*.stl` |
| **PRINT_HARDWARE** | Separate bosses/latch tabs **to the side** (not floating on body) |
| **ASSEMBLY** | Design/closed pose for fit check |
| FORM / BAYS / EARS | Design helpers (often hidden when prepping print) |
| ARCHIVE_legacy | Hidden old REF + v1 boxes |
| META | ORIGIN_mm |

### Approx envelope (mm)

- Body ~ **154 × 96 × 272** (W×D×H) — stages required  
- Soft companion/desktop humanoid scale (not adult life-size)  

### Print parts (`Models/print/`)

| STL | Fits 250? | Access |
|-----|-----------|--------|
| stage1_head_front/back | yes | Head opens F/B |
| stage3_torso_front | yes | Torso opens F/B |
| stage4_torso_back | yes | Pi + battery side |
| stage6_ear_L/R | yes | Separate |

Wall ~2 mm; seam faces opened (boundary edges present). Latch bosses on back halves = first pass.  
See `Models/print/README.md`.

### Pi kit (calipers 2026-08-11)

- CanaKit: **93.77 × 63.02 × 30.45** mm (L×W×H, fan in H)  
- **Seat:** Interior L-rails only (do **not** pass through to bed). Snug +0.5 mm  
- **Fan:** 30×30×7.38, wire 63.92 mm — **mounted on body**, Cana lid stays off  
- **Ports (Cana1–9):** USB-C+HDMI long wall → +X charge; GPIO/open toward seam; ETH/USB and SD on shorts  
- Photos: `Cana1`–`Cana9`, `81726Back*.jpeg`
- **Print:** `Models/print/print_bed_*.stl` only  


### Print durability (user 2026-08-11)

**Fewer fragile points → better prints.** Prefer:

- Continuous walls, generous fillets, chunky latch geometry  
- Simple port holes over thin webs / isolated bosses / lace vents  
- Avoid hairline rims around large pockets (reinforce pocket edges)  

Current risks to clean up later: small latch boss tabs, sharp boolean pocket corners, thin charge tunnel edges.


## Docs

- Plan: `Travelers/Docs/Scaffold_Print_P2S_Plan.md`  
- BOM: `Models/BOM_MEASUREMENTS.md`  
- Preview: `Models/print/_scaffold_v2_preview.png`  
- Exploded: `Models/print/_scaffold_v2_exploded.png`  

