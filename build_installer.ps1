# Author: Kerwin
param([string]$CompilerPath)
$ErrorActionPreference='Stop'
$project=$PSScriptRoot
$python=Join-Path $project '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath (Join-Path $project '_internal\PySide6\Qt6Core.dll'))) { throw '请先运行 build_exe.ps1 生成完整应用' }
if (-not $CompilerPath) {
    $candidates=@((Join-Path $project '.build-tools\InnoSetup\ISCC.exe'),
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe","$env:ProgramFiles\Inno Setup 7\ISCC.exe")
    $CompilerPath=$candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $CompilerPath) { throw '未找到 Inno Setup；安装 6.7 或更新版，或用 -CompilerPath 指定 ISCC.exe' }
Push-Location -LiteralPath $project
try {
    $version=& $python -c 'from app_info import VERSION; print(VERSION)'
    & $python tools\make_installer_art.py
    if ($LASTEXITCODE -ne 0) { throw '安装程序图像生成失败' }
    & $CompilerPath ('/DAppVersion='+$version) ('/DProjectRoot='+$project) (Join-Path $project 'installer\BetterLyrics.iss')
    if ($LASTEXITCODE -ne 0) { throw '安装程序编译失败' }
    $installer=Join-Path $project ('.release\BetterLyrics-Setup-'+$version+'-x64.exe')
    Get-FileHash -LiteralPath $installer -Algorithm SHA256 | ForEach-Object {
        ($_.Hash.ToLower()+'  '+[IO.Path]::GetFileName($_.Path)) | Set-Content -LiteralPath (Join-Path $project '.release\SHA256SUMS.txt') -Encoding utf8
    }
    Write-Output ('安装程序：'+$installer)
} finally { Pop-Location }
