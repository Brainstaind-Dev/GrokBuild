# Current vs Target Behavior – Sensation Coherence Layer

| Dimension                        | Current Behavior (coherence.py)                          | Target Behavior                                      | Priority |
|----------------------------------|-----------------------------------------------------------|-------------------------------------------------------|----------|
| **Description Generation**       | Mechanical string concatenation (`base + movement + temp`) | Composed from rich structured representation          | High     |
| **Zone Awareness**               | Mostly numeric multiplier via `get_zone_sensitivity()`    | Zone-specific sensory character + intensity scaling   | High     |
| **Arousal Modulation**           | Primarily scales intensity number                         | Increases richness + detail in high-sensitivity zones | High     |
| **Temporal Qualities**           | Almost entirely missing                                   | Explicit `temporal_quality` field + representation    | High     |
| **Multi-Feature Composition**    | Weak / additive                                           | Intelligent blending of simultaneous signals          | Medium   |
| **Texture / Quality**            | Very limited                                              | Structured `texture_qualities` list                   | Medium   |
| **Sensation Category**           | Implicit via source_features                              | Explicit `category` field                             | Medium   |
| **Future Pattern Mapping Readiness** | Low                                                    | High (rich structured fields designed for mapping)    | High     |
| **Natural Language Role**        | Primary construction target                               | Secondary / generated from structured data            | Medium   |

## Summary

The current implementation produces understandable output but lacks the depth, structure, and compositional intelligence required for meaningful embodied experience. The target is a sensation synthesis engine that prioritizes rich structured representation while still producing useful natural language descriptions.