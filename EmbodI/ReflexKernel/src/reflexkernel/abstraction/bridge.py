"""
Data bridge between the Feature Extraction / Abstraction Layer and ReflexKernel.

Responsibilities:
- Convert `AbstractionOutput` (events + features + state summary) into
  structures that ReflexKernel already understands (`Stimulus`, or direct
  injection points).
- Keep the bridge thin and explicit so it is easy to evolve or replace.

This allows the new abstraction layer to be dropped in without breaking
the existing Reflex Core, Learner, or remote Saddle.
"""

from __future__ import annotations

from typing import List

from ..types import Stimulus
from .schema import AbstractionOutput, BodyStateSummary, Sensation


def abstraction_to_stimuli(output: AbstractionOutput) -> List[Stimulus]:
    """
    Convert the full output of the abstraction layer into ReflexKernel Stimulus objects.

    This path is for ReflexKernel compatibility (events + features).
    The higher intelligence / Saddle should prefer the sensations path.
    """
    stimuli: List[Stimulus] = []

    for item in output.events + output.features:
        stim_dict = item.to_stimulus_dict()
        stimuli.append(Stimulus.from_dict(stim_dict))

    # Inject enhanced state summary (now can come from coherent sensations)
    if output.state_summary:
        summary = output.state_summary
        stimuli.append(
            Stimulus(
                modality="proprio",
                data={
                    "type": "body_state_summary",
                    "arousal_estimate": summary.arousal_estimate,
                    "valence_estimate": summary.valence_estimate,
                    "contact_state": summary.contact_state,
                    "posture_stability": summary.posture_stability,
                    "dominant_sensation": getattr(summary, "dominant_sensation", summary.dominant_event),
                    "dominant_zone": getattr(summary, "dominant_zone", None),
                    "active_sensations": getattr(summary, "active_sensations", []),
                },
                ts=output.ts,
                confidence=summary.confidence,
                source="abstraction",
            )
        )

    return stimuli


def get_coherent_sensations(output: AbstractionOutput) -> List[Sensation]:
    """
    Primary output path for the Saddle / higher intelligence.
    Returns coherent, natural sensations (after coherence + sensitivity + arousal modulation).
    """
    return output.sensations or []


def get_state_summary(output: AbstractionOutput) -> BodyStateSummary | None:
    """Convenience accessor for the highest-level signal the Saddle should see."""
    return output.state_summary
