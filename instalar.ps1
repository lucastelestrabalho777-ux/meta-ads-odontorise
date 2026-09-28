# Instalador do pacote de skills da OdontoRise (Windows). No PowerShell, depois de clonar o repositório:
#   powershell -ExecutionPolicy Bypass -File "$HOME\.claude\skills\meta-ads-odontorise\instalar.ps1"
# Cria %USERPROFILE%\OdontoRise (CLAUDE.md, credentials, meta-ads), liga cada skill do pacote em
# %USERPROFILE%\.claude\skills e confere Python e a biblioteca da Meta. Não mexe em credenciais nem em contas.
$ErrorActionPreference = "Stop"
$Aqui = Split-Path -Parent $MyInvocation.MyCommand.Path
$Cfg = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $HOME ".claude" }
$Skills = Join-Path $Cfg "skills"
$Ws = Join-Path $HOME "OdontoRise"
Write-Host "Pacote: $Aqui"
New-Item -ItemType Directory -Force -Path (Join-Path $Ws "credentials"), (Join-Path $Ws "meta-ads"), $Skills | Out-Null
if (-not (Test-Path (Join-Path $Ws "CLAUDE.md"))) { Copy-Item (Join-Path $Aqui "workspace\CLAUDE.md") (Join-Path $Ws "CLAUDE.md"); Write-Host "criado: $Ws\CLAUDE.md" }
function Ligar($alvo, $nome) {
  $dest = Join-Path $Skills $nome
  if (Test-Path $dest) { Remove-Item $dest -Force -Recurse }
  New-Item -ItemType Junction -Path $dest -Target $alvo | Out-Null
  Write-Host "ligada: $dest"
}
if ($Aqui -ne (Join-Path $Skills "meta-ads-odontorise")) { Ligar $Aqui "meta-ads-odontorise" }
Get-ChildItem (Join-Path $Aqui "skills") -Directory | ForEach-Object { Ligar $_.FullName $_.Name }
try { python -c "import facebook_business" 2>$null } catch { }
if ($LASTEXITCODE -ne 0) { Write-Host "instalando a biblioteca da Meta..."; python -m pip install --user -q -r (Join-Path $Aqui "requirements.txt") }
python -c "import facebook_business; print('biblioteca da Meta ok', facebook_business.__version__)"
Write-Host ""
Write-Host "Pronto. Próximos passos: credenciais (passos 6 e 8 do guia) e depois, no Claude: 'rode o setup da skill Meta'."
