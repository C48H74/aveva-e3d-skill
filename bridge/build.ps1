# Compila o add-in E3DLiveBridge (x86, .NET Framework 4) usando o csc.exe do Windows.
# Uso:  powershell -ExecutionPolicy Bypass -File build.ps1 [-AvevaDesignExe "C:\AVEVA\Plant\Everything3D3.1"]
param([string]$AvevaDesignExe = $env:AVEVA_DESIGN_EXE)
$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($AvevaDesignExe)) {
    $cands = @('C:\AVEVA\Plant\Everything3D3.1', 'C:\Program Files (x86)\AVEVA\Everything3D3.1',
               'C:\Program Files (x86)\AVEVA\Everything3D2.10', 'C:\AVEVA\Everything3D2.1')
    $AvevaDesignExe = $cands | Where-Object { Test-Path (Join-Path $_ 'Aveva.Core.Database.dll') } | Select-Object -First 1
}
if (-not $AvevaDesignExe) { throw 'Pasta do E3D não encontrada. Passe -AvevaDesignExe "<pasta com des.exe>".' }
Write-Host "E3D: $AvevaDesignExe"

$fw = 'C:\Windows\Microsoft.NET\Framework\v4.0.30319'
$csc = Join-Path $fw 'csc.exe'
$out = Join-Path $PSScriptRoot 'bin'
New-Item -ItemType Directory -Force -Path $out | Out-Null

$aveva = 'Aveva.ApplicationFramework.dll','Aveva.Core.Database.dll','Aveva.Core.Database.Filters.dll',
         'Aveva.Core.Utilities.dll','Aveva.Core.Geometry.dll','Aveva.Core.Shared.dll'
$refs = @('System.dll','System.Core.dll','System.Drawing.dll','System.Windows.Forms.dll','System.Web.Extensions.dll') |
        ForEach-Object { Join-Path $fw $_ }
foreach ($a in $aveva) {
    $p = Join-Path $AvevaDesignExe $a
    if (Test-Path $p) { $refs += $p } elseif ($a -in 'Aveva.ApplicationFramework.dll','Aveva.Core.Database.dll','Aveva.Core.Utilities.dll') { throw "Faltando: $p" }
}

$cscArgs = @('/nologo','/target:library','/platform:x86','/optimize+',"/out:$(Join-Path $out 'E3DLiveBridge.dll')")
$cscArgs += $refs | ForEach-Object { "/reference:$_" }
$cscArgs += (Join-Path $PSScriptRoot 'E3DLiveBridge.cs')
& $csc @cscArgs
if ($LASTEXITCODE -ne 0) { throw "csc falhou ($LASTEXITCODE)" }
Set-Content -Path (Join-Path $out 'aveva_path.txt') -Value $AvevaDesignExe
Write-Host "OK -> $out\E3DLiveBridge.dll"
