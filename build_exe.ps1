$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

Write-Host "Building RecRoomVrmConverter.exe..."
python -m PyInstaller --noconfirm --clean .\RecRoomVrmConverter.spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

$distRoot = Join-Path $projectRoot "dist\RecRoomVrmConverter"
Copy-Item -LiteralPath (Join-Path $projectRoot "README_DIST.txt") -Destination (Join-Path $distRoot "README.txt") -Force

Write-Host ""
Write-Host "Build complete."
Write-Host "Output: $projectRoot\dist\RecRoomVrmConverter\RecRoomVrmConverter.exe"
