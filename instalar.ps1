# Instalador do pacote de skills da OdontoRise (Windows). Um comando no PowerShell, sem conta no GitHub:
#   irm https://raw.githubusercontent.com/lucastelestrabalho777-ux/meta-ads-odontorise/main/instalar.ps1 | iex
# Rodar de novo atualiza o pacote.
# Cria %USERPROFILE%\OdontoRise (CLAUDE.md, credentials, meta-ads), liga cada skill do pacote em
# %USERPROFILE%\.claude\skills e confere Python, a biblioteca da Meta e o navegador do raio-x (Playwright + Chromium). Não mexe em credenciais nem em contas.
$ErrorActionPreference = "Stop"
$RepoUrl = "https://github.com/lucastelestrabalho777-ux/meta-ads-odontorise.git"
$Cfg = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $HOME ".claude" }
$Skills = Join-Path $Cfg "skills"
$Ws = Join-Path $HOME "OdontoRise"
$Destino = Join-Path $Skills "meta-ads-odontorise"
$Aqui = if ($MyInvocation.MyCommand.Path) { Split-Path -Parent $MyInvocation.MyCommand.Path } else { $Destino }
New-Item -ItemType Directory -Force -Path $Skills | Out-Null
if (-not (Test-Path (Join-Path $Aqui "SKILL.md"))) { Write-Host "baixando o pacote em $Destino ..."; git clone -q $RepoUrl $Destino; $Aqui = $Destino }
elseif (Test-Path (Join-Path $Aqui ".git")) { Write-Host "atualizando o pacote ..."; git -C $Aqui pull -q --ff-only }
Write-Host "Pacote: $Aqui"
New-Item -ItemType Directory -Force -Path (Join-Path $Ws "credentials"), (Join-Path $Ws "meta-ads"), $Skills | Out-Null
if (-not (Test-Path (Join-Path $Ws "CLAUDE.md"))) { Copy-Item (Join-Path $Aqui "workspace\CLAUDE.md") (Join-Path $Ws "CLAUDE.md"); Write-Host "criado: $Ws\CLAUDE.md" }
# Regra 4 mudou em 01/10/2026: troca só a linha antiga exata; o resto do CLAUDE.md da pessoa fica como está.
# O acento vai por [char] para não depender da codificação com que o PowerShell lê este arquivo.
$ClaudeMd = Join-Path $Ws "CLAUDE.md"
$Regra4Antiga = "4. Nunca sugerir Facebook como posicionamento nem ampliar raio."
$Regra4Nova = "4. Nunca ampliar raio. Posicionamento segue o que a conta j$([char]0x00E1) usa (Instagram, Facebook)."
$Linhas = @(Get-Content -LiteralPath $ClaudeMd -Encoding UTF8)
if ($Linhas -ccontains $Regra4Antiga) {
  $Linhas = $Linhas | ForEach-Object { if ($_ -ceq $Regra4Antiga) { $Regra4Nova } else { $_ } }
  [System.IO.File]::WriteAllLines($ClaudeMd, [string[]]$Linhas, (New-Object System.Text.UTF8Encoding $false))
  Write-Host "atualizado: regra 4 do $ClaudeMd"
}
function Ligar($alvo, $nome) {
  $dest = Join-Path $Skills $nome
  if (Test-Path $dest) { Remove-Item $dest -Force -Recurse }
  New-Item -ItemType Junction -Path $dest -Target $alvo | Out-Null
  Write-Host "ligada: $dest"
}
if ($Aqui -ne (Join-Path $Skills "meta-ads-odontorise")) { Ligar $Aqui "meta-ads-odontorise" }
Get-ChildItem (Join-Path $Aqui "skills") -Directory | ForEach-Object { Ligar $_.FullName $_.Name }
try { python -c "import facebook_business, playwright" 2>$null } catch { }
if ($LASTEXITCODE -ne 0) { Write-Host "instalando a biblioteca da Meta e o Playwright (navegador do raio-x de concorrentes)..."; python -m pip install --user -q -r (Join-Path $Aqui "requirements.txt") }
python -c "import facebook_business; print('biblioteca da Meta ok', facebook_business.__version__)"
try { python -c "import playwright" 2>$null } catch { }
if ($LASTEXITCODE -eq 0) {
  Write-Host "conferindo o Chromium do Playwright (na primeira vez baixa uns 150 MB)..."
  python -m playwright install chromium
  python -c "from importlib.metadata import version; print('navegador do raio-x ok (playwright ' + version('playwright') + ')')"
} else { Write-Host "AVISO: o Playwright nao instalou; so o raio-x de concorrentes sem Apify precisa dele. No Claude, 'rode o setup da skill Meta' mostra o comando." }
Write-Host ""
Write-Host "Pronto. Próximos passos: credenciais (passos 6 e 8 do guia) e depois, no Claude: 'rode o setup da skill Meta'."
