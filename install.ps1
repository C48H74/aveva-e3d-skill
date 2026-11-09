# Instala o E3D Live MCP no Windows (executar UMA vez, com o E3D fechado).
#   powershell -ExecutionPolicy Bypass -File install.ps1 [-AvevaDesignExe "<pasta do E3D>"] [-Target "C:\AVEVA\Custom\E3DLive"]
param([string]$AvevaDesignExe = $env:AVEVA_DESIGN_EXE, [string]$Target = 'C:\AVEVA\Custom\E3DLive')
$ErrorActionPreference = 'Stop'
$src = $PSScriptRoot

# 1) compilar o add-in
& (Join-Path $src 'bridge\build.ps1') -AvevaDesignExe $AvevaDesignExe
$AvevaDesignExe = (Get-Content (Join-Path $src 'bridge\bin\aveva_path.txt')).Trim()

# 2) copiar arquivos
New-Item -ItemType Directory -Force -Path "$Target\addin","$Target\config","$Target\server" | Out-Null
Copy-Item "$src\bridge\bin\E3DLiveBridge.dll" "$Target\addin\" -Force
Copy-Item "$src\server\*.py" "$Target\server\" -Force

# 3) registrar o add-in numa CÓPIA do DesignAddins.xml (nunca editar o arquivo da AVEVA)
$orig = Join-Path $AvevaDesignExe 'DesignAddins.xml'
if (-not (Test-Path $orig)) { throw "DesignAddins.xml não encontrado em $AvevaDesignExe" }
$existing = [Environment]::GetEnvironmentVariable('CAF_ADDINS_PATH','User')
if ($existing -and (Test-Path (Join-Path $existing 'DesignAddins.xml'))) {
    Write-Warning "CAF_ADDINS_PATH já aponta para $existing (customização existente). Vou acrescentar a entrada lá."
    $cfgDir = $existing
} else { $cfgDir = "$Target\config"; Copy-Item $orig $cfgDir -Force }
$xmlPath = Join-Path $cfgDir 'DesignAddins.xml'
[xml]$x = Get-Content $xmlPath
$entry = "$Target\addin\E3DLiveBridge"
if (-not ($x.ArrayOfString.string -contains $entry)) {
    $n = $x.CreateElement('string', $x.DocumentElement.NamespaceURI); $n.InnerText = $entry
    $x.DocumentElement.AppendChild($n) | Out-Null; $x.Save($xmlPath)
}
[Environment]::SetEnvironmentVariable('CAF_ADDINS_PATH', $cfgDir, 'User')
Write-Host "Add-in registrado em $xmlPath (CAF_ADDINS_PATH=$cfgDir)"

# 4) ambiente Python do servidor MCP
if (Get-Command py -ErrorAction SilentlyContinue) { $py = 'py' } else { $py = 'python' }
& $py -m venv "$Target\.venv"
& "$Target\.venv\Scripts\python.exe" -m pip install --quiet "mcp>=1.12,<2"
$cmd = "$Target\.venv\Scripts\python.exe"
Write-Host ''
Write-Host 'Pronto. Para ligar ao Claude Code:'
Write-Host "  claude mcp add e3d-live -- `"$cmd`" `"$Target\server\e3d_mcp.py`""
Write-Host 'Ou no Claude Desktop (claude_desktop_config.json):'
Write-Host ('  "e3d-live": {"command": "' + $cmd.Replace('\','\\') + '", "args": ["' + "$Target\server\e3d_mcp.py".Replace('\','\\') + '"]}')
Write-Host 'Abra o E3D Design; o console deve mostrar: [E3DLiveBridge] ouvindo em http://localhost:8765/'
