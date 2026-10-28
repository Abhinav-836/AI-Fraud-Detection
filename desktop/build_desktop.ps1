# Builds the Windows desktop app and installer.
#
#   powershell -ExecutionPolicy Bypass -File desktop\build_desktop.ps1
#
# Needs: Python 3.10-3.12 (64-bit) and Node.js 20+ on PATH.
# Optional: Inno Setup 6 (for the setup .exe; without it you still get the
#           portable folder dist\AIFraudDetection\).
#
# Output:
#   dist\AIFraudDetection\AIFraudDetection.exe        portable app folder
#   dist\AIFraudDetection-Setup-2.0.0.exe              installer (if Inno Setup is installed)
#   dist\AIFraudDetection-portable.zip                 zipped portable folder

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Run($exe, [string[]]$argv) {
    & $exe @argv
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $exe $($argv -join ' ')" }
}

Step "Python build environment (.venv-desktop)"
if (-not (Test-Path ".venv-desktop\Scripts\python.exe")) {
    Run "python" @("-m", "venv", ".venv-desktop")
}
$Py = Join-Path $Root ".venv-desktop\Scripts\python.exe"
Run $Py @("-m", "pip", "install", "--upgrade", "pip")
Run $Py @("-m", "pip", "install", "-r", "requirements.txt", "-r", "desktop\requirements-desktop.txt")

Step "Dashboard (React -> frontend\dist)"
Push-Location frontend
Run "npm" @("ci", "--no-audit", "--no-fund")
Run "npm" @("run", "build")
Pop-Location

Step "Model (bundled default; skipped if models\model.pkl already exists)"
if (-not (Test-Path "models\model.pkl")) {
    Run $Py @("-m", "src.pipelines.training_pipeline", "--no-feedback")
}

Step "Icon"
Run $Py @("desktop\make_icon.py")

Step "PyInstaller (dist\AIFraudDetection)"
Run $Py @("-m", "PyInstaller", "desktop\fraud_detection.spec", "--noconfirm", "--clean")

Step "Portable zip"
$Zip = "dist\AIFraudDetection-portable.zip"
if (Test-Path $Zip) { Remove-Item $Zip }
Compress-Archive -Path "dist\AIFraudDetection" -DestinationPath $Zip

Step "Installer (Inno Setup)"
$Iscc = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($Iscc) {
    Run $Iscc @("desktop\installer.iss")
    Write-Host "`nInstaller: dist\AIFraudDetection-Setup-2.0.0.exe" -ForegroundColor Green
} else {
    Write-Host "Inno Setup 6 not found - skipped the installer. Install it from https://jrsoftware.org/isdl.php and re-run." -ForegroundColor Yellow
}

Write-Host "`nPortable app: dist\AIFraudDetection\AIFraudDetection.exe" -ForegroundColor Green
Write-Host "Portable zip: $Zip" -ForegroundColor Green
