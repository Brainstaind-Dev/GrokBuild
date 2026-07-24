# Saddle/MCP Richer Output Exposure — Plan (Source of Truth)

**Goal**: Expose the richer output (coherent `Sensation` objects with structured fields + natural NL descriptions, `BodyStateSummary`, arousal_modulated_richness, zone_character, etc.) more prominently in the Saddle (FastAPI remote interface) and MCP (stdio tools) while verifying that the information will not overload the higher intelligence (HI).

**Date**: 2026-06-23  
**Location**: Embodi/ReflexKernel (saddle = interface/server.py + models; MCP = mcp_server.py; supporting = python_api.py, abstraction/*)  
**Status**: In progress (plan read/created first; todos seeded before code changes)

This plan is the authoritative document. Work checklist strictly in order. Flip checkboxes here (via edits) upon completion of each item. Use todo_write for live tracking. Update documentation after substantive changes. All changes must preserve dual-path (RK gets events/features; HI/Saddle gets sensations) and simulation-first.

## Acceptance Criteria (for "done")
- Richer sensations are returned **by default** (NORMAL detail) in primary Saddle endpoints: GET /api/v1/state (sensations + state_summary fields prominent) and GET /api/v1/sensations.
- MCP tools surface richer output prominently: kernel_status and read_affective_state include concise sensations + summary (at normal); get_coherent_sensations / get_body_state are robust, first-class, and documented for HI use.
- No overload for HI verified: 
  - Default detail="normal" (concise NL-focused descriptions, key fields only).
  - Sensations hard-capped (e.g. max 3-5 dominant/active sensations).
  - state_summary is always the lightweight primary view; full list optional/escalated.
  - Detail escalation (enhanced/diagnostic) only on explicit request.
  - Response payloads stay reasonable (sensations list bounded, no raw dumps by default).
- Virtual abstraction path supports detail_level (richer descs when requested).
- All filters, caps, and detail handling work correctly (no more broken post-filters).
- Existing MCP/saddle tests pass + new/updated verification for rich exposure + overload controls.
- Dual paths untouched: RK path (abstraction_to_stimuli) continues unchanged.
- Backward compatible (optional params default safe).
- Documentation updated (docstrings, Technical Overview.md status + sections, relevant guides) after changes.

## Task Checklist (execute strictly top-to-bottom; mark [x] when fully done)
- [x] 1. Create/read this plan.md as source of truth; seed todo_write from acceptance criteria + checklist items before any code edits.
- [x] 2. Audit current saddle (server.py, models.py) and MCP (mcp_server.py, python_api.py) exposure of richer sensations / summary. Identify gaps for prominence + overload risks. Read coherence/virtual for detail handling.
- [x] 3. Extend VirtualSensorSimulator.process to accept optional detail_level=DetailLevel.NORMAL and forward it to combine_into_sensations (enables richer output on request).
- [x] 4. Fix and enhance Saddle:
  - Make /api/v1/state and /api/v1/sensations always populate rich sensations + summary prominently (default normal).
  - Use detail_level properly (pass to sim).
  - Add caps: limit sensations to top 3 (or active_sensations driven), keep state_summary light.
  - Improve StateResponse / SensationsResponse to emphasize richer path.
  - Fix fragile "if 'out' in locals" and post-filter logic.
- [x] 5. Fix and enhance MCP + PythonAPI:
  - Update get_coherent_sensations and get_body_state to pass detail_level correctly into sim + return full rich dicts (capped).
  - Enrich kernel_status() and read_affective_state() to include "sensations" (normal, capped) and "state_summary" for prominent richer output.
  - Fix scoping bugs, make robust.
- [x] 6. Implement overload safeguards globally (shared helper if useful): hard max_sensations=3 default, truncate long descs only at normal? (prefer natural short at source), document "NORMAL recommended for HI to avoid overload".
- [x] 7. Update/add verification tests (in test_mcp_server.py and/or integration via python -c or demo) that:
  - Default calls return <=3 sensations with NORMAL detail and key richer fields present.
  - Enhanced returns more detail when requested.
  - State/summary responses stay bounded; no overload path.
- [x] 8. Run full verification per "Verification Plan" section (pytest, targeted runs capturing rich output + sizes, dual-path check). Save proof artifacts to private scratch if needed.
- [x] 9. Update documentation: docstrings in server/mcp/python_api, Embodied_Autonomic_System_Technical_Overview.md (status + how HI consumes), any inline examples. (Skip status report per rules.)
- [x] 10. Mark all checklist items done in this plan.md + final todo_write. Confirm acceptance criteria. Run one last clean verification.

## Deviations (record any)
- (none yet)

## Verification Plan (must re-run before claiming complete)
1. cd to Embodi/ReflexKernel; ensure venv or use python -m; `python -m pytest tests/test_mcp_server.py -q --tb=line`
2. Run full `python -m pytest tests/ -q` (15+ should pass, no breakage to existing).
3. Manual richer exposure checks (python -c or scripts/demo integration):
   - Call get /state (default) → assert sensations present (<=3), state_summary present, detail=normal, richer fields (arousal_modulated_richness, temporal_quality etc) in dicts, descriptions natural/short.
   - /api/v1/sensations?detail_level=enhanced → richer/more verbose.
   - MCP equiv via direct import or simulated: kernel_status / read_affective_state contain sensations.
   - get_coherent_sensations(detail_level="normal") vs "enhanced".
4. Overload verification: inspect payload len(json) < threshold for default (e.g. sensations descriptions concise); confirm caps enforced; enhanced only on request.
5. Dual path: confirm abstraction_to_stimuli still produces stimuli (no sensations forced into RK path).
6. Re-run demo.py or targeted sim to ensure live sensations print rich fields.
7. If any failure, fix then re-verify before next checklist item or done.

All verification output must show richer output visible at default while remaining HI-friendly (concise, summarized, capped).

*End of plan. This is single source of truth for completion.*
