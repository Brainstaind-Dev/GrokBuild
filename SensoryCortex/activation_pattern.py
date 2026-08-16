"""
Activation pattern v0 — body-native HI feel channel.

Assembled from already-coherent RK/Cortex inputs. Does **not** re-fuse sensors.
See Travelers/Docs/Activation_Pattern_Contract_v0_Plan.md.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Mapping, MutableMapping, Optional

from pydantic import BaseModel, Field

SCHEMA_VERSION = "activation_pattern_v0"
# Additive HI-feedback revision (zones/reflexes); still v0 wire format
PATTERN_REV = "0.1"

# Scaffold / companion core — always present (HI v0.1 added solar_plexus)
CORE_ZONES: tuple[str, ...] = (
    "head",
    "ear_L",
    "ear_R",
    "face",
    "neck_throat",
    "chest",
    "solar_plexus",
    "torso_back",
    "torso_front",
    "shoulders",
    "whole_body",
)

# Map extended / legacy sensation zones → core (identity if already core)
ZONE_TO_CORE: Dict[str, str] = {
    "earlobes": "ear_L",
    "left_ear": "ear_L",
    "right_ear": "ear_R",
    "ear_l": "ear_L",
    "ear_r": "ear_R",
    "scalp_hair": "head",
    "lips": "face",
    "face": "face",
    "head": "head",
    "neck_throat": "neck_throat",
    "neck": "neck_throat",
    "throat": "neck_throat",
    "chest": "chest",
    "breasts_general": "chest",
    "nipples_areola": "chest",
    "solar_plexus": "solar_plexus",
    "solarplexus": "solar_plexus",
    "epigastrium": "solar_plexus",
    "mid_torso": "solar_plexus",
    "upper_back": "torso_back",
    "lower_back_base_spine": "torso_back",
    "torso_back": "torso_back",
    "back": "torso_back",
    "torso_front": "torso_front",
    "lower_stomach": "torso_front",
    "shoulders": "shoulders",
    "upper_arms": "shoulders",
    "whole_body": "whole_body",
    "body": "whole_body",
    # limbs not on scaffold core → whole_body rollup for spatial field
    "inner_thighs": "whole_body",
    "upper_inner_thigh": "whole_body",
    "outer_thighs": "whole_body",
    "hips": "whole_body",
    "calves": "whole_body",
    "feet": "whole_body",
    "outer_arms": "whole_body",
    "inner_wrists": "whole_body",
    "left_forearm": "whole_body",
    "upper_buttocks": "whole_body",
}

REFLEX_KEYS: tuple[str, ...] = (
    "flinch",
    "orient",
    "freeze",
    "tension",
    "blink",
    "relax",
    "micro_expression",
    "autonomic",
    # HI feedback wishlist (2026-08-15) — residuals derived or explicit
    "jaw_clench",
    "shoulder_elevation",
    "breath_depth",
    "custom",
)

SOURCE_PATHS = frozenset({"physical", "virtual", "sim", "mixed"})


def _clamp(x: float, lo: float, hi: float) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return lo
    if v != v:  # NaN
        return lo
    return max(lo, min(hi, v))


def _clamp01(x: float) -> float:
    return _clamp(x, 0.0, 1.0)


def _clamp_valence(x: float) -> float:
    return _clamp(x, -1.0, 1.0)


class PatternSalience(BaseModel):
    dominant_zone: Optional[str] = None
    dominant_reflex: Optional[str] = None
    active_pattern_ids: List[str] = Field(default_factory=list)


class ActivationPatternV0(BaseModel):
    """Body-native activation snapshot for the HI (feel channel v0)."""

    schema_version: str = SCHEMA_VERSION
    ts: float = Field(..., description="Timestamp (perf or wall; producer documents)")
    tick: Optional[int] = None
    source_path: str = Field("sim", description="physical|virtual|sim|mixed")
    global_: Dict[str, float] = Field(
        ...,
        alias="global",
        description="arousal/urgency [0,1]; valence/dominance [-1,1]",
    )
    zones: Dict[str, float] = Field(default_factory=dict)
    reflexes: Dict[str, float] = Field(default_factory=dict)
    salience: PatternSalience = Field(default_factory=PatternSalience)
    meta: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}

    def to_public_dict(self) -> Dict[str, Any]:
        """JSON-friendly dict with key ``global`` (not global_)."""
        return self.model_dump(mode="json", by_alias=True)


def empty_core_zones() -> Dict[str, float]:
    return {z: 0.0 for z in CORE_ZONES}


def empty_reflexes() -> Dict[str, float]:
    return {k: 0.0 for k in REFLEX_KEYS}


def normalize_zone(zone: str) -> tuple[str, Optional[str]]:
    """
    Returns (core_zone, extended_key_or_None).
    Extended key is original if not in core and not fully absorbed.
    """
    z = (zone or "whole_body").strip()
    if not z:
        z = "whole_body"
    key = z.lower().replace(" ", "_")
    # preserve ear_L style
    if z in CORE_ZONES:
        return z, None
    if key in ZONE_TO_CORE:
        core = ZONE_TO_CORE[key]
        ext = None if key in CORE_ZONES or core == key else (z if z not in CORE_ZONES else None)
        # keep original spelling for extended if mapped away from identity
        if key not in {c.lower() for c in CORE_ZONES} and ZONE_TO_CORE[key] != key:
            ext = z if z not in CORE_ZONES else None
        return core, ext if ext and ext not in CORE_ZONES else None
    # unknown → whole_body + sparse original
    if z in CORE_ZONES:
        return z, None
    return "whole_body", z if z != "whole_body" else None


def _sensation_intensity(s: Mapping[str, Any]) -> float:
    for k in ("intensity", "arousal_modulated_richness", "arousal_contribution"):
        if k in s and s[k] is not None:
            return _clamp01(float(s[k]))
    return 0.3


def _reflex_map(reflex_activity: List[Any]) -> Dict[str, float]:
    out = empty_reflexes()
    for r in reflex_activity or []:
        name = str(r).lower().strip()
        # ReflexKind.ORIENT style
        if "." in name:
            name = name.split(".")[-1]
        if name.startswith("reflexkind"):
            name = name.replace("reflexkind", "").strip(".:")
        # aliases from HI / free text
        aliases = {
            "jaw": "jaw_clench",
            "clench": "jaw_clench",
            "shoulder_shrug": "shoulder_elevation",
            "shrug": "shoulder_elevation",
            "breath": "breath_depth",
            "breathing": "breath_depth",
        }
        name = aliases.get(name, name)
        if name in out:
            out[name] = max(out[name], 0.65)
        elif name:
            out["custom"] = max(out["custom"], 0.5)
    return out


def _derive_hi_reflex_residuals(
    reflexes: MutableMapping[str, float],
    zones: Mapping[str, float],
    *,
    arousal: float,
    urgency: float,
) -> None:
    """
    Fill HI wishlist residuals from existing fields (no new sensor fusion).
    - shoulder_elevation from tension / shoulders zone
    - jaw_clench from neck tension / freeze
    - breath_depth: deeper when calm autonomic; shallower under flinch/freeze/urgency
    """
    tension = float(reflexes.get("tension", 0.0))
    freeze = float(reflexes.get("freeze", 0.0))
    flinch = float(reflexes.get("flinch", 0.0))
    autonomic = float(reflexes.get("autonomic", 0.0))
    neck = float(zones.get("neck_throat", 0.0))
    shoulders = float(zones.get("shoulders", 0.0))

    elev = max(tension * 0.75, shoulders * 0.6, neck * 0.35 * (1.0 if tension > 0.2 else 0.5))
    reflexes["shoulder_elevation"] = max(float(reflexes.get("shoulder_elevation", 0.0)), _clamp01(elev))

    jaw = max(freeze * 0.7, neck * 0.55, tension * 0.4)
    reflexes["jaw_clench"] = max(float(reflexes.get("jaw_clench", 0.0)), _clamp01(jaw))

    # calm baseline: autonomic * (1 - threat); threat = max(flinch, freeze, urgency)
    threat = max(flinch, freeze, urgency, max(0.0, arousal - 0.55) * 1.2)
    breath = autonomic * (0.35 + 0.65 * (1.0 - _clamp01(threat)))
    # quiet low-arousal still shows some breath if autonomic present
    if autonomic > 0.2 and arousal < 0.4:
        breath = max(breath, autonomic * 0.55)
    reflexes["breath_depth"] = max(float(reflexes.get("breath_depth", 0.0)), _clamp01(breath))


def build_activation_pattern(
    coherent_input: Mapping[str, Any],
    *,
    affective: Optional[Mapping[str, Any]] = None,
    salient_sensations: Optional[List[Mapping[str, Any]]] = None,
    reflex_activity: Optional[List[Any]] = None,
    active_patterns: Optional[List[str]] = None,
    tick: Optional[int] = None,
    source_path: Optional[str] = None,
    ts: Optional[float] = None,
    detail_level: str = "normal",
    producer: str = "sensory_cortex",
) -> ActivationPatternV0:
    """
    Build activation_pattern_v0 from coherent input and/or already-summarized pieces.
    """
    data = coherent_input or {}
    aff_in = dict(affective or data.get("affective") or {})
    body = dict(data.get("body_state") or {})

    arousal = _clamp01(
        aff_in.get(
            "arousal",
            body.get("arousal_estimate", data.get("arousal", 0.5)),
        )
    )
    valence = _clamp_valence(
        aff_in.get(
            "valence",
            body.get("valence_estimate", data.get("valence", 0.0)),
        )
    )
    dominance = _clamp_valence(aff_in.get("dominance", data.get("dominance", 0.5)))
    urgency = _clamp01(aff_in.get("urgency", data.get("urgency", arousal * 0.5)))

    zones = empty_core_zones()
    sensations: List[Mapping[str, Any]] = []
    if salient_sensations is not None:
        sensations = list(salient_sensations)
    else:
        raw = data.get("sensations") or []
        for s in raw:
            if hasattr(s, "model_dump"):
                sensations.append(s.model_dump())
            elif isinstance(s, Mapping):
                sensations.append(s)

    for s in sensations:
        if not isinstance(s, Mapping):
            continue
        core, ext = normalize_zone(str(s.get("zone") or "whole_body"))
        inten = _sensation_intensity(s)
        zones[core] = max(zones.get(core, 0.0), inten)
        if ext:
            zones[ext] = max(float(zones.get(ext, 0.0)), inten)

    dom_zone = body.get("dominant_zone") or data.get("dominant_zone")
    if not dom_zone and sensations:
        dom_zone = sensations[0].get("zone")
    if dom_zone:
        core, ext = normalize_zone(str(dom_zone))
        zones[core] = max(zones.get(core, 0.0), _clamp01(arousal * 0.5))
        if ext:
            zones[ext] = max(float(zones.get(ext, 0.0)), _clamp01(arousal * 0.45))

    # mild whole_body floor from arousal
    zones["whole_body"] = max(zones["whole_body"], _clamp01(arousal * 0.25))

    refs = list(reflex_activity if reflex_activity is not None else data.get("reflex_activity") or [])
    reflexes = _reflex_map(refs)
    _derive_hi_reflex_residuals(
        reflexes, zones, arousal=arousal, urgency=urgency
    )

    patterns = list(
        active_patterns
        if active_patterns is not None
        else data.get("active_patterns") or []
    )
    patterns = [str(p) for p in patterns]

    # dominant reflex = max residual
    dom_reflex = None
    if reflexes:
        dom_reflex = max(reflexes.items(), key=lambda kv: kv[1])[0]
        if reflexes[dom_reflex] <= 0:
            dom_reflex = None

    dom_zone_out = None
    if dom_zone:
        dom_zone_out, _ = normalize_zone(str(dom_zone))
    else:
        # max zone excluding whole_body if possible
        ranked = sorted(
            ((z, v) for z, v in zones.items() if z != "whole_body"),
            key=lambda kv: kv[1],
            reverse=True,
        )
        if ranked and ranked[0][1] > 0:
            dom_zone_out = ranked[0][0]
        elif zones.get("whole_body", 0) > 0:
            dom_zone_out = "whole_body"

    sp = (source_path or data.get("source_path") or data.get("source") or "sim")
    sp = str(sp).lower()
    if sp in ("kernel", "sensory_cortex", "abstraction"):
        sp = "sim"
    if sp not in SOURCE_PATHS:
        sp = "sim"

    tick_val = tick if tick is not None else data.get("tick")
    try:
        tick_out = int(tick_val) if tick_val is not None else None
    except (TypeError, ValueError):
        tick_out = None

    ts_out = float(ts if ts is not None else time.time())

    return ActivationPatternV0.model_validate(
        {
            "schema_version": SCHEMA_VERSION,
            "ts": ts_out,
            "tick": tick_out,
            "source_path": sp,
            "global": {
                "arousal": arousal,
                "valence": valence,
                "dominance": dominance,
                "urgency": urgency,
            },
            "zones": {k: _clamp01(v) for k, v in zones.items()},
            "reflexes": {k: _clamp01(v) for k, v in reflexes.items()},
            "salience": {
                "dominant_zone": dom_zone_out,
                "dominant_reflex": dom_reflex,
                "active_pattern_ids": patterns,
            },
            "meta": {
                "detail_level": str(
                    detail_level or data.get("detail_level") or "normal"
                ),
                "producer": producer,
                "pattern_rev": PATTERN_REV,
            },
        }
    )


def pattern_to_compact_feel_line(pattern: ActivationPatternV0 | Mapping[str, Any]) -> str:
    """One-line HI prompt gloss: feel: arousal=… ear_L=… orient=…"""
    if isinstance(pattern, ActivationPatternV0):
        d = pattern.to_public_dict()
    else:
        d = dict(pattern)
    g = d.get("global") or {}
    zones = d.get("zones") or {}
    refs = d.get("reflexes") or {}
    sal = d.get("salience") or {}
    # top 3 zones
    top_z = sorted(
        ((k, float(v)) for k, v in zones.items() if float(v) > 0.05),
        key=lambda kv: kv[1],
        reverse=True,
    )[:3]
    top_r = sorted(
        ((k, float(v)) for k, v in refs.items() if float(v) > 0.05),
        key=lambda kv: kv[1],
        reverse=True,
    )[:2]
    parts = [
        f"arousal={float(g.get('arousal', 0)):.2f}",
        f"valence={float(g.get('valence', 0)):.2f}",
    ]
    parts.extend(f"{k}={v:.2f}" for k, v in top_z)
    parts.extend(f"{k}={v:.2f}" for k, v in top_r)
    if sal.get("dominant_zone"):
        parts.append(f"dom={sal['dominant_zone']}")
    return "feel: " + " ".join(parts)
