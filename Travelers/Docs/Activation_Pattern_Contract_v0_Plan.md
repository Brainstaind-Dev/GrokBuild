# Activation Pattern Contract — Plan (v0)

**Status:** Approved (2026-08-15) — implement AP-1 + AP-2 + AP-4  
**Tweak:** During implementation, use existing HI stack (HIAgent / Saddle / experience) for **HI feedback** on sample patterns when useful — not only unit tests.  
**Date:** 2026-08-15  
**Owner layer:** Sensory Cortex (package) + RK AffectiveContext / reflexes (sources)  
**Consumers:** HIAgent, Saddle `/api/v1/experience`, optional UE viz later  

---

## 1. Intent

Embodi’s north star is a **path of enrichment** that grounds an ethereal HI in reality (physical + virtual).

Today the HI mostly receives **language-shaped packages** (sensations, mood text, deltas).  
The long arc is for Embodi to address the HI through **activation patterns** — body-native, structured signals that are the closest analogue to **feelings** (simulated or physical).

**v0 goal of this plan:** define a **small, stable, JSON-serializable contract** we can:

1. Emit from sim (no new hardware required)  
2. Attach alongside existing experience (not replace it yet)  
3. Log and inspect so we learn “what patterns look like”  
4. Feed HIAgent later as a first-class field  

**Out of scope for v0:** reading LLM hidden activations via xAI API; replacing NL sensations; UE binding; full dense tensors.

---

## 2. Design principles

| # | Principle | Implication |
|---|-----------|-------------|
| 1 | **Body-owned, not model-owned** | Patterns are produced by Embodi from RK/Cortex state — not queried from Grok weights |
| 2 | **Same shape, any source** | `source_path`: `physical` \| `virtual` \| `sim` — dual stimulus world, one pattern schema |
| 3 | **Dual channel** | v0 = patterns **+** existing experience; HI may use either; patterns do not delete NL |
| 4 | **Fixed vocabulary** | Zone and reflex keys are enums/constants; unknown zones go to `other` or sparse map only if listed |
| 5 | **Bounded & rate-friendly** | Small payload; suitable for 5–20 Hz polling or event push; no multi-MB tensors |
| 6 | **Cortex does not re-fuse** | Pattern assembly uses already-fused affect, sensations, reflex traces — no second sensor fusion |
| 7 | **Versioned** | `schema_version: "activation_pattern_v0"` for forward evolution |

---

## 3. What an activation pattern *is* (v0)

A **snapshot** of the body’s current activation field for the HI:

- **Global affect** (how “charged / good-bad / pressed” the whole system is)  
- **Spatial field** (where on the body intensity lives)  
- **Motor/reflex field** (what defensive/orienting systems just did or are primed to do)  
- **Provenance** (when, which path, which tick)  

It is **not**: a paragraph, a tool list, or an LLM attention map.

---

## 4. Contract schema (v0)

### 4.1 Top-level object

```json
{
  "schema_version": "activation_pattern_v0",
  "ts": 1712345678.901,
  "tick": 42,
  "source_path": "sim",
  "global": {
    "arousal": 0.62,
    "valence": 0.15,
    "dominance": 0.45,
    "urgency": 0.20
  },
  "zones": {
    "chest": 0.12,
    "ear_L": 0.0,
    "ear_R": 0.0,
    "neck_throat": 0.05,
    "whole_body": 0.18
  },
  "reflexes": {
    "flinch": 0.0,
    "orient": 0.35,
    "freeze": 0.0,
    "tension": 0.22,
    "blink": 0.0,
    "autonomic": 0.40
  },
  "salience": {
    "dominant_zone": "chest",
    "dominant_reflex": "autonomic",
    "active_pattern_ids": ["gentle_contact"]
  },
  "meta": {
    "detail_level": "normal",
    "producer": "sensory_cortex"
  }
}
```

### 4.2 Field rules

| Field | Type | Range / notes |
|-------|------|----------------|
| `schema_version` | string | Always `activation_pattern_v0` for this rev |
| `ts` | float | Wall or perf time; document which in producer (prefer shared clock with experience) |
| `tick` | int \| null | Kernel tick if available |
| `source_path` | enum | `physical` \| `virtual` \| `sim` \| `mixed` |
| `global.*` | float | Prefer **[0, 1]** for arousal/urgency; valence/dominance **[-1, 1]** (match AffectiveContext). Clamp on emit |
| `zones` | map string→float | Values **[0, 1]** intensity. **Sparse OK** — omit zeros or include full core set (see §5). Recommend **core set always present** for HI stability |
| `reflexes` | map string→float | Values **[0, 1]** recent activity / residual (decay window TBD, default last 0.5–1.0 s or last N traces) |
| `salience` | object | Hints for HI attention; derived, not re-fused |
| `meta` | object | Non-semantic ops fields; free to grow without breaking consumers |

### 4.3 Example: “loud left + mild startle” (illustrative)

```json
{
  "schema_version": "activation_pattern_v0",
  "ts": 1712345690.1,
  "tick": 108,
  "source_path": "sim",
  "global": {
    "arousal": 0.78,
    "valence": -0.25,
    "dominance": 0.30,
    "urgency": 0.55
  },
  "zones": {
    "ear_L": 0.85,
    "ear_R": 0.25,
    "neck_throat": 0.40,
    "chest": 0.35,
    "shoulders": 0.30,
    "whole_body": 0.45
  },
  "reflexes": {
    "flinch": 0.55,
    "orient": 0.70,
    "freeze": 0.15,
    "tension": 0.50,
    "blink": 0.20,
    "autonomic": 0.65
  },
  "salience": {
    "dominant_zone": "ear_L",
    "dominant_reflex": "orient",
    "active_pattern_ids": ["sudden_loud"]
  },
  "meta": {
    "detail_level": "normal",
    "producer": "sensory_cortex",
    "note": "illustrative — not live capture"
  }
}
```

---

## 5. Zone vocabulary (v0 core + extension)

### 5.1 Core set (always emit for scaffold / companion body)

Aligned with **current print scaffold + head/torso** (expand later for limbs):

| Zone id | Meaning |
|---------|---------|
| `head` | Cranial mass / general head |
| `ear_L` | Left featured ear / mic |
| `ear_R` | Right featured ear / mic |
| `face` | Face / front head (optional intensity rollup) |
| `neck_throat` | Neck / cable trunk region |
| `chest` | Upper torso front |
| `solar_plexus` | Mid-torso / under sternum (HI feedback) |
| `torso_back` | Upper/mid torso back (Pi bay region) |
| `torso_front` | Mid/lower front torso |
| `shoulders` | Shoulder mass |
| `whole_body` | Non-localized / global body tone |

### 5.2 Extended set (emit when present; map from existing RK zones)

Reuse names already in `FEMALE_SENSITIVITY_MAP` / sensations where possible, e.g.:

`nipples_areola`, `breasts_general`, `inner_thighs`, `outer_thighs`, `hips`, `lower_back_base_spine`, `upper_back`, `lips`, `scalp_hair`, …

**Rule:** if a sensation cites a zone not in core, include it in `zones` sparsely **or** fold into nearest core zone via a published map (v0.1). v0 producer may:

- Prefer **dominant_zone** boost on core + sparse extended keys from active sensations  

### 5.3 Mapping from current sensations (producer algorithm sketch)

```
zones[z] = 0 for z in CORE
for each salient sensation:
  z = sensation.zone or "whole_body"
  z_core = MAP_TO_CORE.get(z, z)  # identity if already core
  intensity = clamp(sensation.intensity or arousal_modulated_richness or 0.3, 0, 1)
  zones[z_core] = max(zones[z_core], intensity)
  if z not in CORE: zones[z] = max(zones.get(z, 0), intensity)  # sparse extended
if dominant_zone: zones[dominant] = max(zones[dominant], global.arousal * 0.5)
```

Exact MAP_TO_CORE table: implementation PR; plan locks the **principle**.

---

## 6. Reflex vocabulary (v0)

Keys match `ReflexKind` (lowercase):

`flinch`, `orient`, `freeze`, `tension`, `blink`, `relax`, `micro_expression`, `autonomic`,  
`jaw_clench`, `shoulder_elevation`, `breath_depth` (HI v0.1), `custom`

**Value meaning (v0):** residual activation in **[0, 1]** from recent traces and/or derived residuals (see `_derive_hi_reflex_residuals`). If no signal, `0`.

---

## 7. Where it lives in the stack

```
Physical sensors ─┐
Virtual / UE ─────┼─► RK (fusion, reflexes) ─► coherent data
Sim virtual ──────┘              │
                                 ▼
                    Sensory Cortex packaging
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
            experience (NL+mood)     activation_pattern_v0
                    │                         │
                    └────────────┬────────────┘
                                 ▼
              Saddle GET /api/v1/experience  (+ optional dedicated GET later)
                                 ▼
                         HIAgent / tools / logs
```

| Layer | Role for patterns |
|-------|-------------------|
| **RK** | Source of affect, reflexes, tick, last sensations |
| **Sensory Cortex** | **Assemble** pattern object (primary producer for HI) |
| **Saddle** | Transport; embed under experience or sibling field |
| **HIAgent** | Consume / log / optional prompt injection of compact pattern summary |
| **UE** | Later: drive viz **from** pattern; later still: emit virtual stimuli **in** |

### 7.1 Experience attachment (v0 transport)

**Preferred:** add field on experience dict:

```json
{
  "...existing experience fields...",
  "activation_pattern": { "...activation_pattern_v0..." }
}
```

**Alternative (v0.1):** `GET /api/v1/activation_pattern` for high-rate poll without full NL package.

v0 implements **attachment on experience** only (minimal surface).

---

## 8. Producer rules (Cortex)

1. Build pattern **after** normal experience packaging for the same tick/update.  
2. Do **not** re-read raw sensors.  
3. Fill `global` from affective core / body_state estimates already in coherent input.  
4. Fill `zones` from sensations + dominant_zone (§5.3).  
5. Fill `reflexes` from `reflex_activity` / last actions already available to adapter.  
6. Set `source_path` from config or payload tag (`sim` default for VirtualSensorSimulator path; `physical` when hardware adapter marks it; `virtual` when inject marked from UE).  
7. Clamp all intensities; never NaN.  

---

## 9. Consumer rules (HIAgent v0)

| Mode | Behavior |
|------|----------|
| **Log** | Write pattern JSON to eval/session log each experience |
| **Prompt (optional)** | Compact line: `feel: arousal=0.62 ear_L=0.85 orient=0.7` — not full dump every turn unless debug |
| **Tools** | Optional `get_activation_pattern` returning last pattern |
| **Non-goal** | HI must not invent body state; only Embodi emits patterns |

---

## 10. Observability — “what do patterns look like?”

Before trusting HI consumption:

1. **Unit tests** with fixed coherent fixtures → golden pattern JSON  
2. **Sim script** run 10–30 s virtual scenarios → dump `data/activation_pattern_samples/*.json`  
3. Optional **CSV/plot** of `global.arousal` and top zones over time  
4. Side-by-side with NL `sensations[].description` to validate mapping  

This answers the research question without LLM activation APIs.

---

## 11. Non-goals (v0)

- LLM hidden-state / full activation tensor access via xAI  
- Replacing sensation NL text  
- Dense per-vertex mesh fields  
- Binary protobuf (JSON first)  
- UE zone bind maps (planned later; same zone ids)  
- Learning a new encoder network  
- Sexual/erogenous content policy changes (extended zones may exist in maps; core scaffold set is companion head/torso first)

---

## 12. Alternatives considered

| Alternative | Why not for v0 |
|-------------|----------------|
| **Only NL sensations** | Already have it; does not give body-native feel channel |
| **Raw stimulus dump to HI** | Overload; bypasses fusion; fights Cortex role |
| **Query Grok logprobs as “feel”** | Token confidence ≠ embodiment; fragile across models |
| **Full zone map every tick as long vector only** | Harder to debug; maps with names are HI-friendlier first |
| **Separate binary UDP bus** | Premature; Saddle JSON is enough |

---

## 13. Open questions (for user before / during goal)

1. **Core zones:** Approve scaffold core list (§5.1) as v0 mandatory keys?  
2. **Valence range:** Keep **[-1, 1]** for valence/dominance vs force all [0,1]? (Plan recommends match AffectiveContext.)  
3. **HIAgent v0:** Log-only first, or also compact prompt injection?  
4. **Rate:** Pattern only when experience emits, or also every kernel tick when gated? (Plan: **same cadence as experience emit**.)  
5. **Naming:** `activation_pattern` vs `body_activation` vs `feel_field`? (Plan default: `activation_pattern`.)

---

## 14. Key decisions (proposed)

| Decision | Rationale |
|----------|-----------|
| Patterns are Embodi-produced body fields | Aligns with north star; independent of LLM internals |
| Dual channel with experience | Safe migration; debuggable |
| Cortex assembles; RK sources | No re-fusion; clear ownership |
| JSON map zones + reflex residuals | Human/HI readable; UE-bindable ids later |
| `source_path` on every pattern | Dual real/virtual theater transparency |
| v0 = experience attachment | Minimal API churn |

---

## 15. PR plan (after goal lock)

| PR | Title | Scope | Depends |
|----|-------|--------|---------|
| **AP-1** | Schema + types for `activation_pattern_v0` | Pydantic/dataclass in SensoryCortex (or shared types); validators/clamps; unit tests on fixtures | — |
| **AP-2** | Producer: build pattern from coherent input | Cortex/adapter function; attach to experience dict; sim path only | AP-1 |
| **AP-3** | Saddle surface | Ensure `/api/v1/experience` includes `activation_pattern` when Cortex embedded | AP-2 |
| **AP-4** | Sample dump + docs | Script → `data/activation_pattern_samples/`; update vaults | AP-2 |
| **AP-5** | HIAgent log (+ optional compact feel line) | Endurance/eval log field; flag for prompt inject | AP-3 |

Suggested first **implementation goal** after plan approval:

> **AP-1 + AP-2 + AP-4:** define schema, produce patterns on sim experience path, dump sample JSON.  
> **HI feedback (approved tweak):** when sample patterns exist, optionally run a short HIAgent/Saddle path so the HI can react to the pattern (log or compact feel line) — use built stack; skip if offline/no key.

---

## 16. Success criteria (v0)

- [x] Schema documented and versioned  
- [x] Sim run produces non-trivial zone/reflex variation under scripted scenarios  
- [x] Experience payload includes `activation_pattern` with valid clamps  
- [x] Tests cover producer + Cortex attach  
- [x] Samples under `data/activation_pattern_samples/`  
- [x] HI feedback pass (xAI) on samples → `hi_feedback.md`  
- [x] No RK re-architecture; no UE requirement  

### HI feedback notes (2026-08-15)

- `feel_line` judged usable; now stored at `activation_pattern.meta.feel_line`  
- Keep `shoulders` in core (already present)  

### Pattern rev 0.1 (folded HI wishlist — same night)

| Addition | How |
|----------|-----|
| `solar_plexus` | Core zone (always in map) |
| `jaw_clench` | Reflex residual; derived from neck/freeze/tension |
| `shoulder_elevation` | Reflex residual; derived from tension/shoulders/neck |
| `breath_depth` | Reflex residual; calmer autonomic → deeper; threat → shallower |
| `meta.pattern_rev` | `"0.1"` |

Wire `schema_version` remains `activation_pattern_v0` (additive, non-breaking).

---

## 17. References

- North star: `Context/vaults/architecture.md`  
- Dual stimuli: `Travelers/Docs/UE_Virtual_Avatar_Environment_Plan.md`  
- Experience packaging: `SensoryCortex/`  
- AffectiveContext / ReflexKind: `EmbodI/ReflexKernel/src/reflexkernel/types.py`  
- Zone sensitivity map: `EmbodI/ReflexKernel/src/reflexkernel/abstraction/schema.py`  
