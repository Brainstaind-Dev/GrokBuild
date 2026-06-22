# GrokBuild — Manual Setup Checklist

Items the agent could not complete automatically. Work through these in order.

---

## 1. Prerequisites (install if missing)

> **Git is not installed on this machine** — `git init` could not run. Install Git first (step 1a), then run step 1b.

### 1a. Install Git (required)

| Tool | Why | How to check | Install |
|------|-----|--------------|---------|
| **Git** | Version control, `/execute-plan`, `/review` | `git --version` | [https://git-scm.com/download/win](https://git-scm.com/download/win) |

After installing, **restart your terminal** so `git` is on PATH.

### 1b. Initialize the repo (run after Git is installed)

```powershell
cd I:\grokbuild
git init
git add .
git commit -m "Initial commit: ReflexKernel + Grok project config"
```

### 1c. Other prerequisites

> **Node.js is not installed on this machine** — MCP servers will not start until Node is installed.

| Tool | Why | How to check | Install | Status |
|------|-----|--------------|---------|--------|
| **Node.js + npm** | MCP servers (Puppeteer, GitHub, Git) run via `npx` | `node --version` | [https://nodejs.org/](https://nodejs.org/) (LTS) | **Not installed** |
| **Python 3.9+** | ReflexKernel runtime | `python --version` | — | OK (`.venv` exists) |

---

## 2. Trust project hooks (required for auto-pytest)

### Why this step exists

Your auto-pytest hook lives **inside the project** at:

```
I:\grokbuild\.grok\hooks\reflexkernel-pytest.json
I:\grokbuild\.grok\hooks\scripts\reflexkernel-pytest.ps1
```

That hook runs a PowerShell script on your machine whenever Grok edits a ReflexKernel `.py` file. Because a malicious repo could ship hooks that run arbitrary code, Grok **silently skips all project-scoped hooks** until you explicitly trust the workspace.

| Hook location | Trust required? |
|---------------|-----------------|
| `C:\Users\Agentdud\.grok\hooks\` (global) | No — always runs |
| `I:\grokbuild\.grok\hooks\` (project) | **Yes** — skipped until trusted |

**Until trusted, nothing breaks — but the hook also does nothing.** You will not get auto-pytest after edits.

### What the hook does (once trusted)

On every successful `search_replace` or `write` to a file under `\ReflexKernel\` ending in `.py`:

1. Grok fires a `PostToolUse` event
2. `reflexkernel-pytest.ps1` runs (up to 120s timeout)
3. The script runs `pytest tests/ -x -q` in `EmbodI\ReflexKernel`
4. Last ~10 lines of output appear in Grok scrollback as a hook annotation

It is **informational only** — a failing test does not block the edit.

### How to trust the project

**Method A — Edit the trust file (recommended in TUI)**

1. Open (or create): `C:\Users\Agentdud\.grok\trusted-hook-projects`
2. Add **one path per line** — the workspace root, not the `.grok\hooks` subfolder:

   ```
   I:\grokbuild
   ```

   If that alone does not work, also add the forward-slash variants Grok may canonicalize to:

   ```
   I:/grokbuild
   I:/grokbuild/
   ```

3. Save the file
4. **Start a new Grok session** in `I:\grokbuild` (trust is read at session start)

**Method B — Shell slash command (if using non-TUI agent mode)**

```
/hooks-trust
```

This writes the current workspace to `trusted-hook-projects` automatically. Note: in the TUI pager, `/hooks-trust` may not appear in the slash menu — use Method A instead.

**Method C — Move hook to global scope (bypasses trust, less portable)**

Copy the hook files to `C:\Users\Agentdud\.grok\hooks\`. Global hooks always run but won't travel with the repo if you clone elsewhere.

### How to verify it worked

**Quick check (run in terminal):**

```powershell
cd I:\grokbuild
grok inspect
```

Look for these two lines:

```
Project trusted: yes        ← must say yes, not no
Hooks (1)                   ← should list reflexkernel-pytest under Project
```

If you still see `Project trusted: no` and `Hooks (0)`, the path in `trusted-hook-projects` does not match what Grok expects — try the forward-slash variants above and restart.

**In the Grok TUI:**

1. Run `/hooks` (or `Ctrl+L` → Hooks tab)
2. Press `r` to reload hooks from disk
3. Under the **Project** group, you should see `reflexkernel-pytest.json`
4. Confirm it shows **enabled** (not `[disabled]` — press `Space` to toggle if needed)

**Live test:**

1. Ask Grok to make a trivial edit to any file under `EmbodI\ReflexKernel\src\` (e.g. add a blank line)
2. Watch scrollback for `[reflexkernel-pytest] running pytest after edit: ...`
3. Pytest output lines should appear shortly after the edit

### Common problems

| Symptom | Cause | Fix |
|---------|-------|-----|
| `grok inspect` → `Project trusted: no` | Path mismatch or session not restarted | Add `I:/grokbuild/` to trust file; restart Grok |
| `Hooks (0)` in inspect | Project untrusted (hooks discovered but not loaded) | Same as above |
| Hook listed but never fires | Matcher only triggers on `search_replace`/`write`, not `read_file` | Edit a `.py` file, not just read one |
| `[reflexkernel-pytest] skipped: .venv not found` | Virtualenv missing | Complete step 7 (venv setup) |
| Hook fires on wrong files | Only `*\ReflexKernel\*.py` paths match | Expected behavior — other files are ignored |
| Want to revoke trust later | — | Remove the path from `trusted-hook-projects`, or run `/hooks-untrust` in shell mode |

### Security note

Only trust projects you wrote or fully reviewed. The hook script is plain text at `.grok\hooks\scripts\reflexkernel-pytest.ps1` — read it before trusting if the repo came from an external source.

---

## 3. MCP servers — verify and enable

**Config at:** `I:\grokbuild\.grok\config.toml`

| Server | Status | Action needed |
|--------|--------|---------------|
| `puppeteer` | Enabled | Run `grok mcp doctor puppeteer` — first run downloads Chromium via npx |
| `git` | **Fixed** — uses Python, not npm | See [Git MCP fix](#git-mcp-handshake-fix) below |
| `filesystem` | Enabled | Scoped to `EmbodI\ReflexKernel\data` — run `grok mcp doctor filesystem` |
| `github` | **Disabled** | Enable after setting token (step 4) |

### Git MCP handshake fix

**Symptom:** `grok mcp doctor git` reports `handshake failed (connection closed: initialize response)`.

**Root cause:** Grok's docs list `@modelcontextprotocol/server-git` as an npm package, but **that package does not exist**. The official Git MCP server is **Python-based** (`mcp-server-git` on PyPI). The stderr log showed:

```
npm error 404 Not Found - GET ... @modelcontextprotocol/server-git
```

**Fix applied in** `I:\grokbuild\.grok\config.toml`:

```toml
# WRONG (npm package doesn't exist):
# command = "npx"
# args = ["-y", "@modelcontextprotocol/server-git", "I:\\grokbuild"]

# CORRECT (Python):
[mcp_servers.git]
command = "python"
args = ["-m", "mcp_server_git", "--repository", "I:\\grokbuild"]
enabled = true
```

**Prerequisite** (installed globally via pip):

```powershell
pip install mcp-server-git
```

**Verify:**

```powershell
grok mcp doctor git
# Expected: handshake OK, 12 tools discovered
```

Restart Grok session and press `r` in `/mcps` to reload.

**Commands:**

```powershell
grok mcp doctor
grok mcp doctor puppeteer
```

In the Grok TUI: `/mcps` → press `r` to refresh after config changes.

If a server fails, check stderr log:

```
C:\Users\Agentdud\.grok\logs\mcp\<server-name>.stderr.log
```

---

## 4. GitHub MCP (when you have a remote repo)

**Config:** `I:\grokbuild\.grok\config.toml` → `[mcp_servers.github]`

1. Create a GitHub Personal Access Token with `repo` scope:
   [https://github.com/settings/tokens](https://github.com/settings/tokens)

2. Set a **user-level** environment variable (do not commit the token):

   ```powershell
   [System.Environment]::SetEnvironmentVariable('GITHUB_TOKEN', 'ghp_...', 'User')
   ```

3. Enable the server in `I:\grokbuild\.grok\config.toml`:

   ```toml
   [mcp_servers.github]
   enabled = true
   ```

4. Restart Grok and run `grok mcp doctor github`.

---

## 5. Git remote (optional but unlocks full workflow)

Git was initialized locally. To use `/pr-babysit` and GitHub MCP fully:

```powershell
cd I:\grokbuild
git remote add origin https://github.com/<your-org>/<your-repo>.git
git push -u origin main
```

---

## 6. Grok user config — partially applied

The agent updated `C:\Users\Agentdud\.grok\config.toml`:

- `[memory] enabled = true` — cross-session recall (added)

**Already set on your machine** (left unchanged):

- `permission_mode = "always-approve"` — auto-approves routine dev commands (equivalent goal to `yolo`)

**Optional** — if you want full yolo mode instead:

```toml
[ui]
yolo = true
permission_mode = "yolo"
```

**To revert memory** (if undesired):

```toml
[memory]
enabled = false
```

Or toggle memory mid-session: `/memory off`

---

## 7. ReflexKernel venv (if pytest hook skips)

The pytest hook expects:

```
I:\grokbuild\EmbodI\ReflexKernel\.venv\Scripts\python.exe
```

If missing:

```powershell
cd I:\grokbuild\EmbodI\ReflexKernel
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"
python -m pytest tests/ -v
```

---

## 8. Optional — custom ReflexKernel MCP (not built yet)

A domain-specific MCP would expose tools like `inject_stimulus`, `read_affective_state`, `run_demo_episode`, `query_logs` so the agent can drive the embodied system programmatically instead of parsing JSONL logs.

**Effort:** ~half day. **Prerequisite:** ReflexKernel Python API stable.

If you want this built, ask: *"Build the ReflexKernel stdio MCP from the plan."*

---

## 9. Optional — hosted issue trackers

Add to `I:\grokbuild\.grok\config.toml` if you use these services:

```toml
[mcp_servers.linear]
url = "https://mcp.linear.app/mcp"
enabled = true

[mcp_servers.sentry]
url = "https://mcp.sentry.dev/mcp"
enabled = true
```

Both require OAuth — authenticate via `/mcps` → select server → press `i`.

---

## 10. Quick verification after setup

```powershell
# Git
cd I:\grokbuild
git status

# ReflexKernel tests
cd EmbodI\ReflexKernel
.\.venv\Scripts\python.exe -m pytest tests/ -v

# MCP health
grok mcp doctor

# Skills visible
grok inspect
```

In Grok, try:

- `/reflexkernel-dev` — should load the project skill
- `/mcps` — puppeteer, git, filesystem should show tools
- Edit a `.py` file in ReflexKernel — pytest hook should run (after step 2)

---

## Files created by the agent

| File | Purpose |
|------|---------|
| `I:\grokbuild\.gitignore` | Root ignore rules |
| `I:\grokbuild\AGENTS.md` | Repo-wide project rules |
| `I:\grokbuild\EmbodI\ReflexKernel\AGENTS.md` | Module-level rules |
| `I:\grokbuild\.grok\config.toml` | Project MCP servers |
| `I:\grokbuild\.grok\hooks\reflexkernel-pytest.json` | Auto-pytest on Python edits |
| `I:\grokbuild\.grok\hooks\scripts\reflexkernel-pytest.ps1` | Hook script |
| `I:\grokbuild\.grok\skills\reflexkernel-dev\SKILL.md` | Domain workflow skill |
| `C:\Users\Agentdud\.grok\config.toml` | Memory + yolo mode (user config) |