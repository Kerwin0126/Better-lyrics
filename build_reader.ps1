# Author: Kerwin
param([string]$OutputName = 'PlaybackReader.exe')
$ErrorActionPreference = 'Stop'
$framework = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319'
$wpf = Join-Path $framework 'WPF'
& (Join-Path $framework 'csc.exe') /nologo /target:exe /platform:x64 "/out:$PSScriptRoot\$OutputName" /r:Accessibility.dll /r:System.Web.Extensions.dll "$PSScriptRoot\PlaybackReader.cs"
if ($LASTEXITCODE -ne 0) { throw 'PlaybackReader 编译失败' }
