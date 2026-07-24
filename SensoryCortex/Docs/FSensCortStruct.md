# Sensory Cortex package structure

```
SensoryCortex/
├── __init__.py              # public exports
├── cortex.py                # main facade (embedded + service)
├── summarizer.py            # coherent → SensoryUpdate
├── memory.py                # short/medium temporal memory
├── schemas.py               # AffectiveCore, SalientSensation, SensoryUpdate
├── translator.py            # HI intent → RK commands (+ dispatch)
├── config.py                # nested settings
├── adapters/
│   ├── __init__.py
│   └── reflex_kernel.py     # from_kernel, from_state_payload, drive_shared_sim
├── integration.py           # try_create_cortex, feed_cortex_from_kernel, SaddleEventConsumer
├── runners/
│   ├── embedded_runner.py   # low-latency demo / host helper
│   └── service_runner.py    # FastAPI façade + --mode consumer
├── tests/
│   ├── test_cortex_unit.py
│   └── test_integration_saddle_consumer.py
└── Docs/
    ├── Sensory_Cortex_Agent_Spec.md
    ├── LatencyStrag.md
    ├── FSensCortStruct.md
    └── example_embedded_usage.py
```

## Import

From repo root `I:\GrokBuild`:

```python
import sys
sys.path.insert(0, r"I:\GrokBuild")
from SensoryCortex import SensoryCortex, load_config
from SensoryCortex.adapters import from_kernel, drive_shared_sim
```

## Run unit tests

```powershell
cd I:\GrokBuild
python -m pytest SensoryCortex/tests/ -q
```

## Run synthetic embedded demo

```powershell
cd I:\GrokBuild
python -m SensoryCortex.runners.embedded_runner --demo --duration 10
```

## Run RK-coupled embedded demo (needs ReflexKernel venv + path)

```powershell
cd I:\GrokBuild
$env:PYTHONPATH = "I:\GrokBuild;I:\GrokBuild\EmbodI\ReflexKernel\src"
& I:\GrokBuild\EmbodI\ReflexKernel\.venv\Scripts\python.exe -m SensoryCortex.runners.embedded_runner --rk --duration 10
```
