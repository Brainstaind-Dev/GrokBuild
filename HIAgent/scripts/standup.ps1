#requires -Version 5.1
<#
.SYNOPSIS
  Stand up Embodi HI stack services in the correct order.

.DESCRIPTION
  Ordered launch of processes needed for the higher-intelligence loop:
    1) Optional health checks / env validation
    2) ReflexKernel Saddle (remote server) — required for --backend saddle
    3) Optional conversation sensation bridge (Grok Web path)
    4) Optional HI agent interactive or pulse mode

  Embedded HI agent does NOT require the Saddle (body runs in-process).
  Use -Mode EmbeddedAgent for the simplest path (API key + one process).

.EXAMPLE
  # Full remote stack + interactive agent
  .\HIAgent\scripts\standup.ps1 -Mode FullRemote -StartAgent interactive

  # Simplest: embedded body + interactive Grok
  .\HIAgent\scripts\standup.ps1 -Mode EmbeddedAgent

  # Only start Saddle server
  .\HIAgent\scripts\standup.ps1 -Mode SaddleOnly
#>

param(
    [ValidateSet("EmbeddedAgent", "FullRemote", "SaddleOnly", "SaddleAndBridge")]
    [string]$Mode = "EmbeddedAgent",

    [ValidateSet("none", "interactive", "pulse", "once")]
    [string]$StartAgent = "interactive",

    [string]$AgentMessage = "Feel your body and briefly describe what you notice.",

    [string]$RepoRoot = "",

    [string]$SaddleHost = "127.0.0.1",
    [int]$SaddlePort = 8000,
    [string]$SaddleApiKey = "",

    [int]$BridgePort = 9876,

    [string]$Model = "",
    [switch]$Viz,
    [switch]$SkipKeyCheck,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
    if (-not (Test-Path (Join-Path $RepoRoot "HIAgent"))) {
        $RepoRoot = "I:\grokbuild"
    }
}

$RkRoot = Join-Path $RepoRoot "EmbodI\ReflexKernel"
$VenvPython = Join-Path $RkRoot ".venv\Scripts\python.exe"
$SimConfig = Join-Path $RkRoot "configs\sim_only.yaml"

if (-not $SaddleApiKey) {
    if ($env:REFLEXKERNEL_API_KEY) { $SaddleApiKey = $env:REFLEXKERNEL_API_KEY }
    else { $SaddleApiKey = "reflexkernel-dev" }
}

function Write-Step($n, $msg) {
    Write-Host ""
    Write-Host "==> [$n] $msg" -ForegroundColor Cyan
}

function Assert-Python {
    if (-not (Test-Path $VenvPython)) {
        throw "ReflexKernel venv python not found: $VenvPython — create with python -m venv .venv && pip install -e `".[server,dev]`""
    }
}

function Assert-XaiKey {
    if ($SkipKeyCheck) { return }
    if (-not $env:XAI_API_KEY) {
        throw "XAI_API_KEY is not set in this shell. Set user env var and open a NEW terminal."
    }
    if (-not $env:XAI_API_KEY.StartsWith("xai-")) {
        Write-Warning "XAI_API_KEY does not start with 'xai-' — double-check you used the secret key, not the key ID."
    }
    Write-Host "XAI_API_KEY present (len=$($env:XAI_API_KEY.Length))" -ForegroundColor Green
}

function Wait-HttpOk([string]$Url, [int]$TimeoutSec = 45) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) {
                return $true
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    return $false
}

function Start-Saddle {
    Write-Step 2 "Starting ReflexKernel Saddle on ${SaddleHost}:${SaddlePort}"
    $args = @(
        "-m", "scripts.server",
        "--config", $SimConfig,
        "--host", $SaddleHost,
        "--port", "$SaddlePort",
        "--api-key", $SaddleApiKey,
        "--log-level", "warning"
    )
    if ($WhatIf) {
        Write-Host "WhatIf: $VenvPython $($args -join ' ')"
        return $null
    }
    $p = Start-Process -FilePath $VenvPython `
        -ArgumentList $args `
        -WorkingDirectory $RkRoot `
        -PassThru `
        -WindowStyle Minimized
    $health = "http://${SaddleHost}:${SaddlePort}/health"
    if (-not (Wait-HttpOk $health 60)) {
        throw "Saddle did not become healthy at $health"
    }
    Write-Host "Saddle healthy: $health (PID $($p.Id))" -ForegroundColor Green
    return $p
}

function Start-Bridge {
    Write-Step 3 "Starting conversation sensation bridge on port $BridgePort"
    $bridge = Join-Path $RkRoot "scripts\conversation_sensation_bridge.py"
    if (-not (Test-Path $bridge)) {
        Write-Warning "Bridge script not found: $bridge — skipping"
        return $null
    }
    $env:REFLEXKERNEL_URL = "http://${SaddleHost}:${SaddlePort}"
    $env:REFLEXKERNEL_API_KEY = $SaddleApiKey
    if ($WhatIf) {
        Write-Host "WhatIf: bridge $bridge"
        return $null
    }
    $p = Start-Process -FilePath $VenvPython `
        -ArgumentList @($bridge) `
        -WorkingDirectory $RkRoot `
        -PassThru `
        -WindowStyle Minimized
    Write-Host "Bridge started (PID $($p.Id)) — ensure it listens on $BridgePort" -ForegroundColor Green
    return $p
}

function Start-Agent {
    param([string]$AgentMode)
    if ($AgentMode -eq "none") { return }

    Write-Step 4 "Starting HIAgent ($AgentMode)"
    Assert-XaiKey

    $env:PYTHONPATH = "$RepoRoot;$RkRoot\src"
    $agentArgs = @("-m", "HIAgent", "--backend")
    if ($Mode -eq "EmbeddedAgent") {
        $agentArgs += "embedded"
    } else {
        $agentArgs += "saddle"
        $agentArgs += @("--saddle-url", "http://${SaddleHost}:${SaddlePort}")
        $agentArgs += @("--saddle-api-key", $SaddleApiKey)
    }
    if ($Model) { $agentArgs += @("--model", $Model) }
    if ($Viz) { $agentArgs += "--viz" }

    switch ($AgentMode) {
        "interactive" { $agentArgs += "interactive" }
        "pulse" { $agentArgs += @("pulse", "--interval", "3") }
        "once" { $agentArgs += @("once", $AgentMessage) }
    }

    Write-Host "Command: $VenvPython $($agentArgs -join ' ')"
    if ($WhatIf) { return }

    # Agent runs in foreground so you can chat / see output
    Push-Location $RepoRoot
    try {
        & $VenvPython @agentArgs
    } finally {
        Pop-Location
    }
}

# --- main sequence ---
Write-Host "Embodi HI stand-up" -ForegroundColor Yellow
Write-Host "Repo: $RepoRoot"
Write-Host "Mode: $Mode | Agent: $StartAgent"

Write-Step 1 "Prerequisites"
Assert-Python
if ($Mode -eq "EmbeddedAgent" -or $StartAgent -ne "none") {
    Assert-XaiKey
} else {
    Write-Host "Skipping XAI key check (no agent start)" 
}

$procs = @()

try {
    switch ($Mode) {
        "EmbeddedAgent" {
            Write-Host "Embedded mode: no Saddle process required." -ForegroundColor Green
            Start-Agent -AgentMode $StartAgent
        }
        "SaddleOnly" {
            $p = Start-Saddle
            if ($p) { $procs += $p }
            Write-Host "Saddle running. Press Ctrl+C in this window will not stop child; stop PID manually if needed."
            if ($StartAgent -ne "none") { Start-Agent -AgentMode $StartAgent }
            else { Write-Host "Done. Saddle PID: $($procs.Id -join ', ')" }
        }
        "SaddleAndBridge" {
            $p = Start-Saddle
            if ($p) { $procs += $p }
            $b = Start-Bridge
            if ($b) { $procs += $b }
            if ($StartAgent -ne "none") { Start-Agent -AgentMode $StartAgent }
            else { Write-Host "Saddle+Bridge up. PIDs: $($procs.Id -join ', ')" }
        }
        "FullRemote" {
            $p = Start-Saddle
            if ($p) { $procs += $p }
            $b = Start-Bridge
            if ($b) { $procs += $b }
            Start-Agent -AgentMode $StartAgent
        }
    }
} catch {
    Write-Host "Stand-up failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Stand-up sequence finished." -ForegroundColor Green
