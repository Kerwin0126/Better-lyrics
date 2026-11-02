# Author: Kerwin
param([switch]$SkipDesktopShortcut)
$ErrorActionPreference = 'Stop'
$project = $PSScriptRoot
$python = Join-Path $project '.venv\Scripts\python.exe'
$packageRoot = Join-Path $project '.packaging'
$targetExe = Join-Path $project '浮词.exe'
if (Get-Process -Name '浮词' -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $targetExe }) {
    throw '请先从托盘退出浮词，再更新 EXE。'
}
Push-Location -LiteralPath $project
try {
    & $python tools\write_version.py
    if ($LASTEXITCODE -ne 0) { throw '版本资源生成失败' }
    & $python tools\prepare_licenses.py
    if ($LASTEXITCODE -ne 0) { throw '第三方许可和对应源码准备失败' }
    & (Join-Path $project 'build_reader.ps1')
    if ($LASTEXITCODE -ne 0) { throw '播放读取器编译失败' }
    & (Join-Path $project 'build_backdrop.ps1')
    if ($LASTEXITCODE -ne 0) { throw '磨砂组件编译失败' }
    & $python make_icon.py
    if ($LASTEXITCODE -ne 0) { throw '图标生成失败' }
    & $python -m PyInstaller --noconfirm --clean `
        --distpath (Join-Path $packageRoot 'dist') `
        --workpath (Join-Path $packageRoot 'build') floating_lyrics.spec
    if ($LASTEXITCODE -ne 0) { throw 'EXE 打包失败' }
    $payload = Join-Path $packageRoot 'dist\浮词'
    # App-local Microsoft redistributable DLLs keep a clean PC independent of
    # globally installed VC++ runtimes. Use only the compiler's REDIST directory.
    $vswhere='C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe'
    $visualStudio=& $vswhere -latest -products '*' -property installationPath
    $crt=Get-ChildItem -Path (Join-Path $visualStudio 'VC\Redist\MSVC\*\x64\Microsoft.VC*.CRT') -Directory |
        Sort-Object FullName -Descending | Select-Object -First 1
    if (-not $crt) { throw '缺少可再发行的 x64 MSVC 运行库，无法保证独立安装' }
    Get-ChildItem -LiteralPath $crt.FullName -Filter '*.dll' | Copy-Item -Destination (Join-Path $payload '_internal') -Force
    Get-ChildItem -LiteralPath $crt.FullName -Filter '*.dll' | ForEach-Object {
        [PSCustomObject]@{Name=$_.Name;Version=$_.VersionInfo.FileVersion}
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $payload '_internal\third_party\licenses\msvc-runtime-manifest.json') -Encoding utf8
    # Replace the complete runtime so removed dependencies cannot shadow OS DLLs.
    $runtime = [IO.Path]::GetFullPath((Join-Path $project '_internal'))
    $backup = [IO.Path]::GetFullPath((Join-Path $packageRoot ('previous-runtime-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))))
    $projectPrefix = [IO.Path]::GetFullPath($project).TrimEnd('\') + '\'
    if (-not $runtime.StartsWith($projectPrefix, [StringComparison]::OrdinalIgnoreCase) -or
        -not $backup.StartsWith($projectPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw '运行库路径超出项目目录'
    }
    if (Test-Path -LiteralPath $runtime) {
        Move-Item -LiteralPath $runtime -Destination $backup
    }
    Copy-Item -LiteralPath (Join-Path $payload '浮词.exe') -Destination $project -Force
    Copy-Item -LiteralPath (Join-Path $payload '_internal') -Destination $project -Recurse -Force
    $exe = Join-Path $project '浮词.exe'
    if (-not $SkipDesktopShortcut) {
        $desktop = [Environment]::GetFolderPath('Desktop')
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut((Join-Path $desktop '浮词.lnk'))
        $shortcut.TargetPath = $exe
        $shortcut.WorkingDirectory = $project
        $shortcut.IconLocation = $exe + ',0'
        $shortcut.Description = '浮词 · 透明桌面歌词，支持酷狗、汽水、QQ音乐和网易云音乐'
        $shortcut.Save()
    }
    Write-Output ('已生成：' + $exe)
} finally {
    Pop-Location
}
