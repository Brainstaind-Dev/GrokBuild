"""
Pattern detectors for the Thought/Emotion Bridge.

Responsibilities:
- Structured JSON seed parsing (fast, preferred path from higher minds)
- Lightweight keyword / rule-based detection (always available)
- Optional heavy ML: sentence-transformers embeddings + similarity
- Optional sentiment analysis (transformers or very light fallback)

All detectors return a list of pattern names (strings) + a suggested delta to affective state.
The fusion engine in thought_bridge.py combines everything.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..types import Stimulus


@dataclass
class PatternMatch:
    name: str
    confidence: float
    valence_delta: float = 0.0
    arousal_delta: float = 0.0
    dominance_delta: float = 0.0
    urgency: float = 0.0


# ----------------------------------------------------------------------
# Structured seed handling (the contract higher intelligence should prefer)
# ----------------------------------------------------------------------

STRUCTURED_KEYS = {
    "emotion", "intensity", "valence", "arousal", "dominance",
    "patterns", "text", "urgency", "trigger"
}


def parse_structured_seed(seed: Dict[str, Any]) -> List[PatternMatch]:
    """
    Turn a clean JSON thought seed into PatternMatch objects.

    Example seeds (any of these keys are accepted):
        {"emotion": "fear", "intensity": 0.9, "valence": -0.8, "arousal": 0.95}
        {"patterns": ["sudden_loud", "social_greeting"], "arousal": 0.4}
        {"text": "I feel a sudden threat approaching", "intensity": 0.75}
    """
    matches: List[PatternMatch] = []
    intensity = float(seed.get("intensity", seed.get("strength", 0.6)))

    # Direct emotion / pattern names
    if "emotion" in seed:
        emo = str(seed["emotion"]).lower()
        matches.append(
            PatternMatch(
                name=f"seed_{emo}",
                confidence=min(0.98, 0.7 + intensity * 0.25),
                valence_delta=float(seed.get("valence", -0.4 if "fear" in emo or "anger" in emo else 0.1)),
                arousal_delta=float(seed.get("arousal", 0.5 + intensity * 0.4)),
                urgency=float(seed.get("urgency", intensity * 0.8)),
            )
        )

    if "patterns" in seed and isinstance(seed["patterns"], (list, tuple)):
        for p in seed["patterns"]:
            matches.append(
                PatternMatch(
                    name=str(p),
                    confidence=0.85,
                    arousal_delta=0.15 * intensity,
                    urgency=0.1 * intensity,
                )
            )

    # Free text in the seed still gets light keyword treatment
    if "text" in seed:
        text_matches = _keyword_detector(str(seed["text"]))
        for m in text_matches:
            m.confidence = min(m.confidence, 0.75)  # lower than explicit structured
            matches.append(m)

    return matches


# ----------------------------------------------------------------------
# Lightweight always-on detectors
# ----------------------------------------------------------------------

_KEYWORD_RULES: List[Tuple[re.Pattern[str], PatternMatch]] = [
    (re.compile(r"\b(sudden|sharp|loud|bang|crash|startl)\b", re.I),
     PatternMatch("sudden_loud", 0.78, valence_delta=-0.25, arousal_delta=0.65, urgency=0.6)),
    (re.compile(r"\b(threat|danger|afraid|fear|scared|panic)\b", re.I),
     PatternMatch("threat", 0.82, valence_delta=-0.55, arousal_delta=0.55, urgency=0.5)),
    (re.compile(r"\b(friendly|wave|hello|hi|greet|smile)\b", re.I),
     PatternMatch("social_greeting", 0.7, valence_delta=0.35, arousal_delta=0.2)),
    (re.compile(r"\b(close|approach|near|coming at)\b", re.I),
     PatternMatch("close_approach", 0.65, valence_delta=-0.15, arousal_delta=0.4, urgency=0.35)),
    (re.compile(r"\b(relax|calm|safe|peace|gentle)\b", re.I),
     PatternMatch("calm", 0.6, valence_delta=0.4, arousal_delta=-0.35)),
]


def _keyword_detector(text: str) -> List[PatternMatch]:
    out: List[PatternMatch] = []
    for pattern, base_match in _KEYWORD_RULES:
        if pattern.search(text):
            out.append(base_match)
    return out


def detect_from_stimuli(stimuli: List[Stimulus]) -> List[PatternMatch]:
    """Turn raw stimulus data into pattern hints (fast path, no ML)."""
    matches: List[PatternMatch] = []
    for s in stimuli:
        data = s.data or {}
        kind = str(data.get("kind", "")).lower()

        if "sudden" in kind or "loud" in kind or "bang" in kind:
            matches.append(PatternMatch("sudden_loud", 0.88, valence_delta=-0.2, arousal_delta=0.7, urgency=0.55))
        if "threat" in kind or "face" in kind and "present" not in kind:
            matches.append(PatternMatch("threat_face", 0.75, valence_delta=-0.45, arousal_delta=0.5))
        if "motion" in kind or "periphery" in kind:
            matches.append(PatternMatch("peripheral_motion", 0.65, arousal_delta=0.35, urgency=0.25))
        if "friendly" in kind or "wave" in kind:
            matches.append(PatternMatch("social_greeting", 0.7, valence_delta=0.3, arousal_delta=0.15))
        if "calm" in kind or "relax" in kind:
            matches.append(PatternMatch("calm", 0.6, valence_delta=0.25, arousal_delta=-0.3))
        if "close" in kind or "approach" in kind:
            matches.append(PatternMatch("close_approach", 0.68, valence_delta=-0.1, arousal_delta=0.35))
    return matches


# ----------------------------------------------------------------------
# Optional heavy ML path (graceful)
# ----------------------------------------------------------------------

_EMBEDDING_MODEL: Optional[object] = None
_SENTIMENT_PIPE: Optional[object] = None


def _get_embedding_model(model_name: str):
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is not None:
        return _EMBEDDING_MODEL
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        _EMBEDDING_MODEL = SentenceTransformer(model_name)
        return _EMBEDDING_MODEL
    except Exception as e:
        print(f"[bridge] sentence-transformers unavailable ({e}). Embedding similarity disabled.")
        return None


def detect_with_embeddings(text: str, model_name: str = "all-MiniLM-L6-v2", threshold: float = 0.55) -> List[PatternMatch]:
    """
    Very lightweight semantic similarity against a tiny hand-curated set of prototypes.
    Only runs when use_sentence_transformers=True and the package is installed.
    """
    model = _get_embedding_model(model_name)
    if model is None:
        return []

    prototypes = {
        "sudden_threat": "a sudden loud noise or dangerous movement right next to me",
        "social_approach": "a friendly person waving or saying hello and approaching",
        "aversive_stimulus": "something unpleasant, harsh, or painful is happening",
        "calming_presence": "everything feels safe, gentle and relaxing right now",
    }

    try:
        emb_text = model.encode([text], normalize_embeddings=True)
        emb_protos = model.encode(list(prototypes.values()), normalize_embeddings=True)
        import numpy as np  # type: ignore

        sims = np.dot(emb_protos, emb_text.T).flatten()
        out: List[PatternMatch] = []
        for (name, _), sim in zip(prototypes.items(), sims):
            if sim >= threshold:
                out.append(
                    PatternMatch(
                        name=f"embed_{name}",
                        confidence=float(min(0.92, sim)),
                        arousal_delta=0.25 if "threat" in name or "aversive" in name else -0.1,
                        valence_delta=-0.35 if "threat" in name or "aversive" in name else 0.25,
                    )
                )
        return out
    except Exception as e:
        print(f"[bridge] embedding detection failed: {e}")
        return []


def detect_sentiment(text: str, model_name: Optional[str] = None) -> List[PatternMatch]:
    """
    Optional sentiment. Falls back to a tiny keyword heuristic if transformers not present.
    """
    global _SENTIMENT_PIPE
    if model_name is None:
        model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"

    # Try real pipeline once
    if _SENTIMENT_PIPE is None:
        try:
            from transformers import pipeline  # type: ignore

            _SENTIMENT_PIPE = pipeline("sentiment-analysis", model=model_name, top_k=None)
        except Exception:
            _SENTIMENT_PIPE = "unavailable"

    if _SENTIMENT_PIPE == "unavailable":
        # Tiny fallback
        neg = len(re.findall(r"\b(bad|awful|scary|angry|hate|threat|pain)\b", text, re.I))
        pos = len(re.findall(r"\b(good|nice|calm|happy|safe|friend|gentle)\b", text, re.I))
        score = (pos - neg) / max(1, pos + neg + 1)
        return [
            PatternMatch(
                name="sentiment_fallback",
                confidence=0.55,
                valence_delta=score * 0.6,
                arousal_delta=0.1 if abs(score) < 0.2 else 0.0,
            )
        ]

    try:
        res = _SENTIMENT_PIPE(text[:256])[0]  # type: ignore
        # res is list of dicts or single dict depending on top_k
        label = res[0]["label"].lower() if isinstance(res, list) else res.get("label", "").lower()
        score = float(res[0]["score"] if isinstance(res, list) else res.get("score", 0.5))
        v = 0.4 if "positive" in label else (-0.45 if "negative" in label else 0.0)
        return [PatternMatch(name=f"sentiment_{label}", confidence=score, valence_delta=v)]
    except Exception:
        return []
