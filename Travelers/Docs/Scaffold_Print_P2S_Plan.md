# Embodi Scaffold Shell — Blender + P2S Staged Prints

**Status**: Active plan (Phase 0)  
**Date**: 2026-08-03  
**BOM source**: `I:\GrokBuild\Parts.md`  
**Printer**: Bambu Lab **P2S** — build volume **256 × 256 × 256 mm**  
**Software**: Embodi unchanged (Pi = host; shell is mechanical only)

---

## 1. Purpose

Create a **3D-printable, biomimetic body shell/scaffold** that houses collected Embodi components, printable in **stages** on a P2S, authored in **Blender** (with **Blender MCP** once connected).

| In scope | Out of scope (v1) |
|----------|-------------------|
| Head + torso shells, bays, lids, mounts | Full limbs / life-size human scale |
| Dry-fit of Pi, ESP32, dual ear mics, batteries | Live wiring firmware |
| Stage exports for Bambu Studio | UE avatar client |
| Docs + measurement tables | Replacing ReflexKernel |

---

## 2. Locked layout decisions

- **Biomimicry**: sensors where biology puts them when practical.  
- **Mics (MAX9814 × 2)**: left/right **ear** positions.  
- **Raspberry Pi 5**: **torso** bay (not in head).  
- **ESP32s**: head node for dual mic (+ spare body node).  
- **Battery**: rechargeable pack(s) + charge access for power-loss resilience.  
- **Print strategy**: split parts so each stage ≤ **~250 mm** (margin inside 256 mm cube).

```text
  [L ear mic]     [R ear mic]
         \         /
      HEAD (ESP32, optional IMU/speaker)
               |
            neck trunk
               |
   TORSO FRONT          TORSO BACK
    speakers/FSR         Pi 5 + airflow
    haptics              battery + charge
    service access       ambient DHT port
```

---

## 3. BOM → scaffold role (from Parts.md)

### Compute
| Part | Role |
|------|------|
| CanaKit Pi 5 PRO 8GB / 128GB | Torso host — service ports, cooling |
| Breadboards + jumpers | Dev only — external tray, not final shell |

### Edge / RF
| Part | Role |
|------|------|
| ESP32-WROOM-32 × 3 | Head mic node + spare + experiment |

### Audio
| Part | Role |
|------|------|
| MAX9814 × 2 | Ear mics |
| Speakers 3 W 8 Ω × 4 | Chest/head grills (start 1–2) |
| MAX98357A I2S amp × 2 | Near speakers / torso amp bay |

### Motion / haptics
| Part | Role |
|------|------|
| SG90 × 3 | Optional neck/lid |
| Vibration motors | Sparse haptic cups |

### Sensors
| Part | Role |
|------|------|
| MPU-6050 × (1–2 used) | Head/torso IMU pocket |
| FSR402 × 5 | Surface patches |
| DS3231 RTC | Torso stack |
| DHT22/DHT11 | Ambient port (vented) |
| Grove GSR / MAX30102 | External interface, not fully buried |

### Power
| Part | Role |
|------|------|
| LiPo 3.7 V 2000 mAh × 2 | Battery tray (no crush) |
| TP4056 Type-C × 3 | Charge panel access |
| Larger UPS (if separate) | Optional bay TBD |

**Measurements:** see `Models/BOM_MEASUREMENTS.md` (fill with calipers before freezing geometry).

---

## 4. P2S print stages

| Stage | Content | Notes |
|------:|---------|--------|
| 1 | Head outer (or L/R halves) | Split if needed for bed; latch interfaces on seams |
| 2 | Head internals / mic cradles / ESP32 cradle | Flat on bed |
| 3 | Torso front | Hollow, speakers/FSR; latch catches for back |
| 4 | Torso back | Pi bay, battery, vents; matching latches |
| 5 | Lids, **latched** service doors, battery tray | Tool-free or single-tool open |
| 6 | **Featured ear shells (pinnae)**, grills, mounts | Batch plate — acoustic form, not flush holes |
| 7 | Optional base / limb stubs | Later |

Exports: `Models/print/` as STL/3MF per stage.

### Latch strategy

Major body parts should **latch together** (not glue-primary):

| Joint | Mechanism (v1 target) |
|-------|------------------------|
| Torso front ↔ back | 2–4 cantilever clips or draw latches along seam |
| Head halves / faceplate | Snap clips + optional security screw |
| Service door (Pi / charge) | Living hinge or captive latch |
| Neck ring ↔ head/torso | Bayonet or clip ring (head removable for wiring) |
| Battery tray | Latch or slide lock so packs cannot free-fall |

Print latch flex arms in the orientation that maximizes layer strength (usually arm flat on bed). Screws/heat-set inserts are fine as secondary retention on high-load bays (Pi, neck).

### Ear / mic features (directionality)

Do **not** use flush holes alone for the ear mics. Outer-ear geometry improves L/R and front/rear cues for the dual MAX9814 pair:

| Feature | Why |
|---------|-----|
| Forward cup / pinna ridge | Shadows rear sound → better spatial contrast |
| Outward flare | Incidence like a human ear |
| Mic board behind aperture | Short path to ESP32; acoustic opening clear |
| Optional TPU pad later | Isolation from shell vibration |

Body form may be **feature-rich** (stylized biomimetic detail is encouraged when it serves sensing, service, or assembly).

---

## 5. Existing geometry

Reuse as reference (ghost) in master blend:

- `Models/Head_Main*.stl`, `HeadMod.stl`, `HeadMinus.blend`
- `Models/Torso_Front*.stl`, `Torso_Back*.stl`, `TFrontMod.*`, `TBackMod.stl`

Master file (target): `Models/embodi_scaffold_v1.blend`

---

## 6. Blender MCP (Phase 0)

Not yet in project MCP config. Before agent-driven modeling:

1. Install Blender 4.x LTS.  
2. Install Blender MCP bridge/addon.  
3. Register server in Grok config; restart session.  
4. Document exact commands in `Models/BLENDER_MCP_SETUP.md`.

Until MCP is live: measure + docs + manual Blender; same stage list.

---

## 7. Printability rules (summary)

- Walls ≥ 1.6–2.0 mm structural.  
- Split for overhangs / bed size (≤ ~250 mm per stage).  
- **Latches/clips first** for major joins; M3 inserts where load needs it; no glue-only critical joints.  
- **Featured ears** (not blank flush ports).  
- Pi airflow; mic/DHT ports open.  
- Neck trunk ≥ 12–15 mm for cables.  
- Battery tray: no sharp crush ribs; charge accessible.  
- Filament default: **PETG** structural, **PLA** OK for fit checks.

---

## 8. Phases checklist

- [ ] **0** Blender MCP setup + caliper measurements  
- [ ] **1** Master scene + bay blocks (mm)  
- [ ] **2** Head shell + **featured ear cups (directionality)** + ESP32 + latch points  
- [ ] **3** Torso front/back + Pi + battery + **seam latches**  
- [ ] **4** Lids, grills, neck ring, service-door latch  
- [ ] **5** P2S print + dry-fit + iterate  
- [ ] **6** Zone name map to Embodi (later)

---

## 9. Success criteria

1. Each stage slices within P2S 256³.  
2. Pi dry-fits torso with airflow + cable exit.  
3. Dual MAX9814 dry-fit ears with **non-flush ear geometry** (cups/ridges present).  
4. ≥1 ESP32 dry-fits head.  
5. Battery + charge accessible.  
6. Service access for Pi SD/USB via **latched** door (no glue-only major joints).  
7. Torso and head major splits **latch closed** and open without destruction.  
8. Docs live in Git for desktop/Pi alignment.

---

## 10. Related docs

| Doc | Path |
|-----|------|
| Parts list | `Parts.md` |
| Measurements | `Models/BOM_MEASUREMENTS.md` |
| Blender MCP setup | `Models/BLENDER_MCP_SETUP.md` |
| UE avatar (software viz) | `Travelers/Docs/UE_Virtual_Avatar_Environment_Plan.md` |
| Pi standup | `scripts/pi/README.md` |

---

*Shell is mechanical biomimicry. Embodi software remains source of truth for sensing and HI.*
