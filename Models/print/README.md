# Embodi scaffold — P2S print stages (v2)

**Source blend:** `Models/embodi_scaffold_v2.blend`  
**Units:** mm · **Wall:** ~2 mm · **Printer:** Bambu P2S 256³ (design max ~250)

## Use these STLs in Bambu Studio (print pose already applied)

Import **`print_bed_*.stl`** — each sits on **Z = 0** with **open cavity facing up**.  
You should **not** need to rotate in Bambu (supports may still be suggested).

| File | Role | Size on bed (mm, X×Y×Z height) |
|------|------|--------------------------------|
| `print_bed_torso_back.stl` | Torso back (Pi pocket + charge) | ~154 × 185 × 62 |
| `print_bed_torso_front.stl` | Torso front | ~154 × 182 × 48 |
| `print_bed_head_back.stl` | Head back | ~103 × 91 × 48 |
| `print_bed_head_front.stl` | Head front | ~103 × 91 × 48 |
| `print_bed_ear_L.stl` / `_R.stl` | Ears | ~25 × 32 × 50 |
| `print_hw_boss_m3_01..06.stl` | Separate M3 bosses (beside body) | Ø10 × 6 |
| `print_hw_latch_tab_01..04.stl` | Separate latch tabs (beside body) | ~14 × 7 × 9 |

**Hardware is not floating on the shell** — bosses/tabs are **separate parts** printed to the side, then bonded/screwed later (stronger prints, fewer fragile points).

### Legacy names (assembly orientation — avoid in Bambu)

`stage1_*`, `stage3_*`, `stage4_*`, `stage6_*` were export-before-bed-layout. Prefer `print_bed_*` for slicing.

## Blender collections

| Collection | Purpose |
|------------|---------|
| `PRINT_BED` | Parts in **print position** (use for export / visual plate) |
| `PRINT_HARDWARE` | Bosses + latch tabs to the side of the body |
| `ASSEMBLY` | Design pose (how it closes) — offset +X so it doesn’t overlap the bed |
| `print_bed_plane_250` | Wire 250 mm footprint guide |

## How it opens (component access)

```
        head front  ⟷  head back     ← ESP32, IMU, mic wiring
              │ neck interface
        torso front ⟷  torso back    ← Pi (back), battery (back), charge
```

1. Print front and back for the section you need.  
2. Place boards into the **open cavity** on the mating face (Y-split).  
3. Close clamshell; latch bosses are on the **back** halves (first-pass tabs — refine after dry-fit).  
4. Ears print separate; attach after head is stable.  
5. Neck: head sits on torso top; cable trunk through neck opening.

## Design rule (user)

**Fewer fragile points → better prints.** Prefer continuous shell, filleted junctions, chunky features. Avoid skinny cantilevers, lace grills, isolated micro-bosses, and sharp thin rims around large cutouts until a dry-fit proves they’re needed.

## Suggested print settings (start)

| Setting | Value |
|---------|--------|
| Filament | PETG structural (PLA OK for fit checks) |
| Layer | 0.2 mm |
| Walls | ≥ 3 |
| Infill | 15–25% gyroid |
| Orientation | Mating face on bed **or** on its side if supports cleaner — dry-fit both |
| Supports | As needed on latch bosses / ear cup |

## Assembly dry-fit order

1. Torso back alone → drop Pi + battery trays (use bay guides in Blender for positions)  
2. Torso front on → check latch catch  
3. Head back → ESP32  
4. Head front on  
5. Ears L/R  
6. Iterate clearances with calipers → update `BOM_MEASUREMENTS.md`

## Pi kit freeze (2026-08-11)

| | mm |
|--|-----|
| CanaKit L × W × H | **93.77 × 63.02 × 30.45** (fan included in H) |
| Bay envelope (w/ clearance) | ~100.8 × 45.5 × 70 (rounded pocket) |
| Charge / power exit | **Right base** — clean oval (~14 × 11 mm) |
| Alignment | 4× Ø6 mm dowel holes on torso F/B; separate `print_hw_dowel_*.stl` |
| Photo | `Models/PIinBod1.jpeg` |

### Cleanup pass (pre-print, 2026-08-11)

- Rebuilt torso back from clean base  
- **Rounded** Pi pocket (no sharp box corners)  
- **Oval** charge port (not a long tunnel)  
- Mesh repair: doubles / degenerate faces removed (**0 zero-area faces**)  
- Open cavity preserved; bed STLs re-exported (manual binary STL for reliability)  

### Floater strip (2026-08-11)

Old latch/boss cubes had been **joined into** the shell mesh (10 islands on torso back, 5 on head back).  
Those are **deleted** — each `print_bed_*.stl` shell is now **one connected body only**.  
Hardware lives only in separate files: `print_hw_boss_*.stl`, `print_hw_latch_*.stl`, `print_hw_dowel_*.stl` (do **not** merge those into the body STL for slicing unless you place them intentionally).

**Slice these:** `print_bed_torso_back.stl` first for Pi dry-fit.

## Not yet (next iterations)

- True cantilever clip geometry (current latches = boss placeholders)  
- Mating lip / alignment pins  
- Dedicated Pi fan grill (vent pattern over kit fan)  
- Limb roots (arms/waist/legs later)  
- Other board cradles to calipers  


## Previews

- Closed form: `_scaffold_v2_preview.png`  
- Access concept: `_scaffold_v2_exploded.png` (render; blend stays closed pose)
