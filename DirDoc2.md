
---

### Document 2: Sensation Synthesis Qualities Specification

```markdown
# Sensation Synthesis Qualities Specification

**Purpose**: Define the qualities the Sensation Coherence Layer must be capable of expressing. This serves as the target specification for redesigning `combine_into_sensations()`.

## Core Qualities

### 1. Multi-Dimensional Composition
The layer must intelligently blend multiple simultaneous signals (pressure, movement, temperature, texture, context) into one unified sensation rather than producing separate fragments.

### 2. Zone-Specific Character
Different body zones must produce sensations with distinct sensory character:
- High-sensitivity/erogenous zones should feel meaningfully different (not just stronger).
- Special handling required for: nipples/areola, clitoris/vulva, inner thighs, neck/throat, anus (strongly arousal-dependent), lower back/base of spine, lips.
- Low-sensitivity zones (especially feet) should remain intentionally dulled.

### 3. Arousal-Modulated Richness
Arousal should act as a dynamic modulator of *richness*, not just intensity:
- Low arousal → simpler, more contained sensations.
- High arousal (especially in erogenous zones) → increased texture, detail, aliveness, and sensory vividness in the structured representation.

### 4. Temporal Awareness
The layer must distinguish and represent:
- Sudden / impact
- Sustained / steady
- Building / accumulating
- Fading / after-sensation
- Rhythmic or pulsing
- Lingering

### 5. Texture and Quality
Support descriptors such as: warm, cool, smooth, firm, silky, sharp, soft, rough, pressing, stroking, etc.

### 6. Structured + Human-Readable Output
Produce rich structured data (`Sensation` object) as the primary output. Natural language description should be generated from the structured representation, not constructed through string concatenation.

## Success Criteria (for Phase 1)

When given realistic Tier 1 signals, the coherence layer should be able to produce sensations that clearly differentiate:
- A sudden impact on the shoulder vs. sustained firm pressure on the upper inner thigh
- Light stroking on the neck at low arousal vs. the same stroking at high arousal
- Contact on the feet vs. contact on the nipples/areola

The structured fields should reflect these differences meaningfully.