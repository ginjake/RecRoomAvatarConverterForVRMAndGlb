$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$pyInstaller = "python -m PyInstaller"

Write-Host "Building RecRoomVrmConverter.exe..."
Invoke-Expression "$pyInstaller --noconfirm --clean .\RecRoomVrmConverter.spec"

Write-Host ""
Write-Host "Build complete."
Write-Host "Output: $projectRoot\dist\RecRoomVrmConverter\RecRoomVrmConverter.exe"
