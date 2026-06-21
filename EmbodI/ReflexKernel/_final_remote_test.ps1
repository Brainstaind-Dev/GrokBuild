$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
Write-Host "Using: $py"

& $py -m pip install -e .[server] --quiet --disable-pip-version-check | Out-Null
Write-Host "Server deps ensured."

& $py -c "
import sys
sys.path.insert(0, 'src')
import reflexkernel
print('Package version:', reflexkernel.__version__)
from reflexkernel.interface import create_app, run_server, EventBroadcaster
print('Server symbols: OK')
from reflexkernel.config import load_config
cfg = load_config('configs/sim_only.yaml')
print('Config loaded, server.enabled =', cfg.interface.server.enabled)
print('All imports and basic config: SUCCESS')
" 2>&1
Remove-Item $ps -Force -ErrorAction SilentlyContinue
