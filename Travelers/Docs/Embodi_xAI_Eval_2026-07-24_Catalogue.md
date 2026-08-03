# Embodi × xAI API Evaluation Catalogue

**Date**: 2026-07-24  
**Session**: 10-minute endurance eval (`HIAgent/scripts/endurance_eval.py`)  
**Model**: `grok-4-1-fast-non-reasoning`  
**Backend**: embedded (viz off), Sensory Cortex attached  
**Artifacts**:
- Transcript: `data/hi_eval/eval_transcript_20260724T230303Z.md`
- Events: `data/hi_eval/eval_events_20260724T230303Z.jsonl`
- Wall time: **603.2 s** (~10.05 min)  
- Plan steps: **14/14** completed  
- Stimuli injected: **9** (+ **5** virtual scenarios)

This catalogue records **future improvements** distilled from Grok (xAI) feedback and operator observations. Embodi core is not required to change until prioritized work begins.

---

## 1. Session summary (operator)

| Metric | Value |
|--------|--------|
| Duration | 603.2 s |
| LLM turns | 14 (all returned replies) |
| Tool use | `feel` used consistently; `send_reward` on calm recovery; free `inject_thought` exploration |
| Body | Cortex attached; RK reflexes (flinch/blink/autonomic) observed on loud/threat paths |
| Failures | **2 feel failures** when `AffectiveCore.arousal > 1.0` (validation reject) |

### Stimulus timeline

| t (s) | Stimulus | Intensity | Virtual scenario |
|------:|----------|-----------|------------------|
| 15 | baseline feel | — | — |
| 45 | `sudden_sound` | 0.92 | `loud_noise` |
| 90 | `gentle_contact` | 0.55 | `gentle_contact` |
| 130 | idle continuity | — | — |
| 170 | `threat_face` | 0.85 | — |
| 210 | `friendly_wave` | 0.45 | — |
| 250 | `impact` | 0.88 | `impact` |
| 300 | mid reflection | — | — |
| 340 | `relaxing_sound` | 0.35 | — |
| 380 | `calm` | 0.25 | — |
| 420 | `sudden_sound` | 0.70 | `loud_noise` |
| 470 | free thought-seed explore | — | — |
| 520 | `gentle_contact` | 0.75 | `gentle_contact` |
| 560 | final debrief | — | — |

---

## 2. Grok feedback themes (condensed)

### What worked (strengths)

- **Readable ambient package**: cool whole-body breeze + sustained smooth pressure/stroke at baseline.  
- **Startle path works**: loud sound raised arousal (e.g. ~0.49→0.98), added flinch/blink and patterns like `sudden_loud`.  
- **Structured fields useful when present**: `arousal_modulated_richness`, textures, temporal_quality, delta/trend, pattern/reflex lists.  
- **Thought seeds work directionally**: curiosity seed added pattern `seed_curiosity` and modest arousal change.  
- **Reward path usable**: HI chose to reinforce calm recovery.  
- **Cortex gating concept OK**: force vs normal understood as useful.

### What hurt (pain points)

1. **Arousal schema overflow (>1.0)** dropped packages entirely (“body rejecting sensation package”).  
2. **Mostly whole-body ambient**: hard to feel localized contact vs breeze; thigh/zone detail often missing when expected.  
3. **Low richness resolution**: richness often ~0.08–0.29; fine texture discrimination weak.  
4. **Temporal_quality stuck on “sustained”**: few transient/decay/pulse dynamics.  
5. **Threat vs friendly barely differentiated** in affect (valence flat ~0.17; mainly pattern labels change).  
6. **Reflexes feel binary**: same flinch/blink set; little intensity/latency scaling.  
7. **Sensation cardinality**: often only two streams; new contacts overwrite/stack poorly from HI’s view.  
8. **Continuity**: “same two sensations” between events; less event-driven felt change than pattern tags suggest.  
9. **Missing embodiment layers**: proprioception / visceral core called out as absent.  
10. **Intensity scaling coarse**: second startle (0.7) vs first (0.92) only partially separable.

### Grok readiness judgment

> Usable for **10–15 min scripted** interactions today; **open-ended / high-arousal risky** until arousal clamp + richness/temporal fixes. After top fixes, **30–60 min** practical; full-day needs more sensation stack + cross-session memory.

---

## 3. Improvement catalogue (prioritized)

Priority: **P0** = correctness/blockers · **P1** = HI usability · **P2** = richness · **P3** = longer-horizon.

| ID | Priority | Area | Improvement | Source |
|----|----------|------|-------------|--------|
| IMP-01 | **P0** | AffectiveCore / fusion | **Clamp/normalize arousal (and related fields) to schema bounds** on ingest; never drop whole package; emit `warning` / `clamped` flags | Grok (multiple); eval errors at t≈90, 250 |
| IMP-02 | **P0** | Error surfacing | When validation fails, return structured error + last-good experience, not empty rejection only | Grok “rejecting package” |
| IMP-03 | **P1** | Zones | **Increase zone granularity** on virtual contact paths (limb/torso/erogenous maps), not only `whole_body` | Grok mid + final |
| IMP-04 | **P1** | Stimulus→feel | Map social/threat kinds to **distinct valence/dominance/arousal deltas** and optional zone cues, not pattern tags alone | threat vs friendly contrast |
| IMP-05 | **P1** | Sensation stack | Support **N>2 concurrent sensations** with salience ranking (don’t silently overwrite) | Final debrief C4 |
| IMP-06 | **P1** | Temporal | Expand `temporal_quality` usage: transient, decaying, pulsing, onset; optional `duration_ms` | Final debrief B/C2 |
| IMP-07 | **P1** | Reflexes | Expose **per-reflex intensity + optional latency** in HI package (not just presence) | Final C5; startle scaling |
| IMP-08 | **P2** | Richness | Increase usable range of `arousal_modulated_richness` under high arousal; richer texture vocabulary already partially built—ensure it reaches HI package | Final B; baseline “modest richness” |
| IMP-09 | **P2** | Continuity | Micro-history: last 3–5 deltas or short sensation timeline in Cortex package | Mid-session #3 |
| IMP-10 | **P2** | Proprio / visceral | Optional channels for posture/core visceral summary in experience | Baseline “incomplete embodiment” |
| IMP-11 | **P2** | Intensity scaling | Ensure moderate vs strong startle differ in ambient intensity and reflex weights | Second startle critique |
| IMP-12 | **P2** | Scenario coupling | Align `inject_stimulus` kinds with VirtualSensorSimulator scenarios so impact/contact always drive coherence, not only RK sim kinds | Operator: dual-path inject |
| IMP-13 | **P3** | Memory | Cross-session / longer embodied memory for “live in body” day-scale | Final D |
| IMP-14 | **P3** | Eval harness | Keep `endurance_eval.py`; add automated assertion for no arousal>1.0; save improvement extraction | Operator |
| IMP-15 | **P3** | UE avatar stage | Use zone/temporal/richness improvements as drive signals for future UE visualizer (see UE plan) | Architecture alignment |
| IMP-16 | **P1** | Habituation / threat | After startle, threat_face produced little new spike—tune refractory vs re-escalation for threat patterns | Grok threat critique |
| IMP-17 | **P2** | Learner side-effect | Long flinch trains with `mod=['learner']` observed late session—review demo/reward interaction during eval | Operator log observation |

---

## 4. Suggested fix order (when we implement)

1. **IMP-01 + IMP-02** (stop silent package drops)  
2. **IMP-04 + IMP-16** (make threat/friendly/contact *feel* different)  
3. **IMP-03 + IMP-05 + IMP-06** (zones, stack, temporal)  
4. **IMP-07 + IMP-08 + IMP-11** (reflex/intensity/richness fidelity)  
5. **IMP-09 + IMP-10 + IMP-13** (continuity and long tenancy)  
6. **IMP-15** when UE avatar client work starts  

---

## 5. Notable verbatim Grok points (reference)

- Baseline: high clarity ambient; missing proprio/visceral; richness modest.  
- Startle: “successfully elevated arousal and triggered protective reflexes”; wants localized auditory/chest jolt.  
- Contact failure: arousal 1.22 > max 1.0 validation.  
- Threat vs friendly: “valence and social-calm signals are **not readable enough**.”  
- Thought seed: “works as intended” (pattern + modest affective shift).  
- Final readiness: scripted 10–15 min OK; clamp fixes unlock 30–60 min; full-day needs more.

---

## 6. Operator notes

- Eval harness: `HIAgent/scripts/endurance_eval.py` (fixed `log_event` kw conflict mid-debug; full run succeeded).  
- First aborted run (~46s) discarded; analysis based on **20260724T230303Z** only.  
- Do not commit raw session logs with secrets (none expected); transcript/events under `data/hi_eval/` are local artifacts.

---

*Catalogue only — no code changes required by this document alone.*
