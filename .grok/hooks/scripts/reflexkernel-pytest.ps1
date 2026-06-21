# PostToolUse hook: run fast pytest when ReflexKernel Python files are edited.
$raw = [Console]::In.ReadToEnd()
if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }

try {
    $event = $raw | ConvertFrom-Json
} catch {
    exit 0
}

$toolName = $event.toolName
if ($toolName -notin @('search_replace', 'write', 'Edit', 'Write', 'MultiEdit')) {
    exit 0
}

$path = $null
$input = $event.toolInput
if ($null -ne $input) {
    if ($input.PSObject.Properties['path']) { $path = $input.path }
    elseif ($input.PSObject.Properties['file_path']) { $path = $input.file_path }
}

if ([string]::IsNullOrWhiteSpace($path)) { exit 0 }
$normalized = $path -replace '/', '\'
if ($normalized -notmatch '\\ReflexKernel\\.*\.py$') { exit 0 }

$rkRoot = 'I:\grokbuild\EmbodI\ReflexKernel'
$python = Join-Path $rkRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    Write-Host '[reflexkernel-pytest] skipped: .venv not found at' $rkRoot
    exit 0
}

Write-Host '[reflexkernel-pytest] running pytest after edit:' $path
Push-Location $rkRoot
& $python -m pytest tests/ -x -q --tb=line 2>&1 | Select-Object -Last 10
$code = $LASTEXITCODE
Pop-Location
exit 0