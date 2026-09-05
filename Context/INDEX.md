# Context INDEX — load map

Read **`NOW.md`** first. Then open **only** the vault(s) for the active task.

| When working on… | Open vault | Primary deep docs |
|------------------|------------|-------------------|
| Session recovery / “where are we?” | `NOW.md` | — |
| ReflexKernel layers, Cortex ownership | `vaults/architecture.md` | `EmbodI/`, `SensoryCortex/Docs/` |
| HIAgent, Saddle, xAI API, eval | `vaults/software-stack.md` | `HIAgent/README.md`, `Travelers/Docs/*Eval*` |
| Pi host, git-only deploy, env keys | `vaults/pi-hardware.md` | `scripts/pi/README.md` |
| Scaffold shell, P2S stages, bays | `vaults/scaffold.md` | `Travelers/Docs/Scaffold_Print_P2S_Plan.md`, `Models/` |
| Blender Lab MCP, smoke, pins | `vaults/blender-mcp.md` | `Models/BLENDER_MCP_SETUP.md` |
| Locked product/process decisions | `vaults/decisions.md` | — |
| Commands, paths, smoke rituals | `vaults/ops.md` | `AGENTS.md` |
| Activation patterns (HI feel channel) | `NOW.md` + plan | `Travelers/Docs/Activation_Pattern_Contract_v0_Plan.md` |
| Minds meet (architecture papers) | Crosstalk | https://github.com/Brainstaind-Dev/Crosstalk — start at `INDEX.md` |

## Load budget (token hygiene)

| Situation | Max extra files |
|-----------|-----------------|
| After compaction | `NOW.md` + `INDEX.md` only |
| Domain task | + 1 vault |
| Cross-cutting (e.g. Pi + HIAgent) | + 2 vaults max |
| Design/spec work | vault pointer → open real design doc |

Do **not** bulk-load entire `Travelers/`, `logs/`, or session compaction dumps into the prompt.
