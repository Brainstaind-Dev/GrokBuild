# GrokBuild Context Vaults

**Why this exists:** Long Embodi sessions hit compaction (~80% context). Chat history is ephemeral; **these files are durable, git-friendly, and load-on-demand.**

## How agents should use this

1. **Start of session / after compaction** — read `Context/NOW.md` (hot status) + `Context/INDEX.md` (map).
2. **Before deep work in a domain** — open only that vault under `Context/vaults/` (do not load every vault).
3. **After material progress** — update `NOW.md` and the relevant vault (facts, not transcripts).
4. **Optional Grok memory** — `/flush` still writes to `~/.grok/memory/`; vaults are the **repo source of truth**. When both disagree, trust vaults + code.

## What belongs here

| Put in vaults | Do **not** put here |
|---------------|---------------------|
| Locked decisions & rationale | Full chat transcripts |
| Current phase / open fuses | Huge logs / binary dumps |
| Paths, ports, pin versions | Secrets / API keys |
| “What works” smoke recipes | Duplicate full design docs (link instead) |
| Gotchas that burned context | Speculative TODO essays |

Keep each vault **under ~150 lines** when possible. Prefer bullets and tables.

## Layout

```
Context/
  README.md          ← this file
  INDEX.md           ← topic → vault map
  NOW.md             ← single hot status card (always short)
  vaults/
    architecture.md
    scaffold.md
    blender-mcp.md
    pi-hardware.md
    software-stack.md
    decisions.md
    ops.md
```

## Human tips

- Edit vaults anytime in your editor; agents re-read them.
- After a big day: skim `NOW.md` and fix anything stale (one minute).
- `/flush` in Grok TUI still helps the **searchable** memory index; vaults help **structured** recovery.
- For multi-domain days (Pi + Blender + Cortex), open one vault at a time to save tokens.

## Disk policy (agent)

User allocated **`I:\`** for agent continuity (ample free space; prefer here over C: dumps).

| Prefer on `I:\` | Avoid |
|-----------------|--------|
| `Context/` vaults & `NOW.md` updates | Duplicating entire chat transcripts |
| Scaffold blends, print STLs, previews under `Models/` | Secrets / API keys |
| Optional working notes under `Context/scratch/` (gitignore if noisy) | Filling the prompt with every vault every turn |
| Large eval/session artefacts already under `data/` | Unbounded log mirrors of `~/.grok/` |

**Token ≠ disk:** keep *prompt* loads lean (NOW + one vault); keep *disk* rich if it helps recovery.
