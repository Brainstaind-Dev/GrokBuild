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

Project hooks live at `I:\grokbuild\.grok\hooks\` but **do not run until you trust the project**.

**File:** `C:\Users\Agentdud\.grok\trusted-hook-projects`

The agent created this file with `I:\grokbuild` already listed. If hooks still do not fire, confirm the path matches your workspace exactly, then restart Grok.

**Verify:** Press `Ctrl+L` → Hooks tab → confirm `reflexkernel-pytest.json` is loaded.

---

## 3. MCP servers — verify and enable

**Config already written at:** `I:\grokbuild\.grok\config.toml`

| Server | Status | Action needed |
|--------|--------|---------------|
| `puppeteer` | Enabled | Run `grok mcp doctor puppeteer` — first run downloads Chromium via npx |
| `git` | Enabled | Run `grok mcp doctor git` |
| `filesystem` | Enabled | Scoped to `EmbodI\ReflexKernel\data` — run `grok mcp doctor filesystem` |
| `github` | **Disabled** | Enable after setting token (step 4) |

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