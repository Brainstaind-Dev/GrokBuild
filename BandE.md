# Before & After Examples – Sensation Coherence Layer

**Purpose**: Provide concrete examples of current vs. target output quality. This gives Grok Build a clear qualitative target for both structured data and natural language descriptions.

---

## Example 1: Sustained Gentle Contact on Upper Inner Thigh (Moderate Arousal)

### Current Typical Output (existing coherence.py)
**Description**:  
"Firm, deep pressure with gentle, slow movement warm"

**Structured fields**:  
- `intensity`: ~0.85  
- `zone`: "upper_inner_thigh"  
- `arousal_contribution`: 0.6  
- Little to no temporal or texture differentiation.

### Target Output (desired)

**Structured `Sensation` fields**:
- `category`: `COMBINED_TOUCH`
- `temporal_quality`: `SUSTAINED`
- `texture_qualities`: ["warm", "smooth", "firm"]
- `movement_quality`: "gentle stroking with slight upward drift"
- `arousal_modulated_richness`: 0.65 (elevated due to zone + arousal)
- `zone_character`: "high-sensitivity erogenous zone"
- `intensity`: 0.92
- `valence`: 0.45
- `arousal_contribution`: 0.78

**Generated Description**:
"Slow, warm, firm pressure spreading gently across my upper inner thigh, with a smooth stroking quality that feels increasingly sensitive and alive as arousal builds."

---

## Example 2: Light Breeze + Temperature Gradient (Sitting Near Water, Low Arousal)

### Current Typical Output
The current layer has almost no handling for non-contact environmental sensations. It would likely produce either nothing or a very generic temperature string with no compositional intelligence.

### Target Output (desired)

**Structured `Sensation` fields**:
- `category`: `AMBIENT`
- `temporal_quality`: `SUSTAINED` + subtle `INTERMITTENT` (light gusts)
- `texture_qualities`: ["cool", "light", "flowing"]
- `movement_quality`: "gentle, shifting air movement across skin"
- `arousal_modulated_richness`: 0.15 (low, as expected for ambient sensation)
- `zone_character`: "broad skin surface awareness"
- `intensity`: 0.35
- `valence`: 0.6 (pleasant)
- `arousal_contribution`: 0.12

**Generated Description**:
"A cool, light breeze moving gently across my skin, carrying the subtle temperature contrast of nearby water. The sensation feels soft and refreshing, with small shifting patterns as the air moves."

---

## Example 3: Sudden Impact vs. Sustained Pressure (Comparison)

This example is useful to show that the layer should clearly differentiate temporal character even when intensity is similar.

**Target behavior**:
- A sudden impact on the shoulder should register as `temporal_quality: SUDDEN`, high initial intensity that decays quickly, and possibly negative or neutral valence.
- Sustained firm pressure on the same area should register as `temporal_quality: SUSTAINED`, more stable intensity, and different valence depending on context.

The structured fields should make this distinction obvious without relying solely on the natural language description.

---

**Note to Grok Build**:  
These examples are qualitative targets. The exact wording of descriptions can vary, but the *structured richness* and clear differentiation between scenarios is what matters most for both current usability and future pattern-level mapping.