$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot\..
if (-not (Test-Path .env)) {
    $taskPassword = [Convert]::ToHexString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(24))
    @("ADMIN_USERNAME=admin", "ADMIN_PASSWORD=$taskPassword", "CORS_ORIGINS=http://localhost:5173", "COOKIE_SECURE=false") | Set-Content -Path .env
    Write-Host 'Created an initial local administrator password in .env. Keep this file private.'
}
$taskPython = '.\.venv\Scripts\python.exe'
if (-not (Test-Path $taskPython)) { python -m venv .venv }
& $taskPython -m pip install -r backend/requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
& $taskPython scripts/manage.py migrate
& $taskPython scripts/manage.py bootstrap
& $taskPython scripts/generate_synthetic_data.py
& $taskPython scripts/ingest_data.py
if ($LASTEXITCODE -ne 0) { Write-Host 'Ingestion skipped or rejected; existing transaction IDs are preserved.' }
& $taskPython scripts/preprocess_data.py
& $taskPython scripts/train_models.py
& $taskPython scripts/build_graph.py
& $taskPython scripts/manage.py demo
Write-Host 'Setup finished. Start backend: .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload'
Write-Host 'Start frontend in a second terminal: cd frontend; npm install; npm run dev'
