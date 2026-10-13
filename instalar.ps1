# Instalador do pacote de skills da OdontoRise (Windows). Um comando no PowerShell, sem conta no GitHub:
#   irm https://raw.githubusercontent.com/lucastelestrabalho777-ux/meta-ads-odontorise/main/instalar.ps1 | iex
# CS (Customer Success), só as skills da CS e sem Meta:
#   $env:ODR_PAPEL="cs"; irm https://raw.githubusercontent.com/lucastelestrabalho777-ux/meta-ads-odontorise/main/instalar.ps1 | iex
# Rodar de novo atualiza o pacote.
# Cria %USERPROFILE%\OdontoRise (CLAUDE.md, credentials, meta-ads), liga cada skill do pacote em
# %USERPROFILE%\.claude\skills e confere Python, a biblioteca da Meta e o navegador do raio-x (Playwright + Chromium). Não mexe em credenciais nem em contas.
# Papel: sem ODR_PAPEL, o pacote completo (gestor e head). "cs" liga só as skills de papeis\cs.txt, usa o CLAUDE.md
# da CS e não instala a biblioteca da Meta nem o navegador. O papel fica em %USERPROFILE%\OdontoRise\.papel e vale
# nas atualizações (/atualizar-git-odontorise roda este instalador sem ODR_PAPEL); "completo" volta ao pacote inteiro.
$ErrorActionPreference = "Stop"
$RepoUrl = "https://github.com/lucastelestrabalho777-ux/meta-ads-odontorise.git"
$Cfg = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $HOME ".claude" }
$Skills = Join-Path $Cfg "skills"
$Ws = Join-Path $HOME "OdontoRise"
$Destino = Join-Path $Skills "meta-ads-odontorise"
$ArqPapel = Join-Path $Ws ".papel"
$Papel = if ($env:ODR_PAPEL) { $env:ODR_PAPEL.Trim() } elseif (Test-Path $ArqPapel) { "$(Get-Content -Raw -LiteralPath $ArqPapel)".Trim() } else { "" }
if (@("", "completo", "gestor", "head") -contains $Papel) { $Papel = "completo" }
elseif ($Papel -ne "cs") { throw "papel desconhecido: $Papel (use cs, ou deixe ODR_PAPEL vazio para o pacote completo)" }
$Aqui = if ($MyInvocation.MyCommand.Path) { Split-Path -Parent $MyInvocation.MyCommand.Path } else { $Destino }
New-Item -ItemType Directory -Force -Path $Skills | Out-Null
if (-not (Test-Path (Join-Path $Aqui "SKILL.md"))) { Write-Host "baixando o pacote em $Destino ..."; git clone -q $RepoUrl $Destino; $Aqui = $Destino }
elseif (Test-Path (Join-Path $Aqui ".git")) { Write-Host "atualizando o pacote ..."; git -C $Aqui pull -q --ff-only }
Write-Host "Pacote: $Aqui"
if ($Papel -eq "cs") {
  New-Item -ItemType Directory -Force -Path (Join-Path $Ws "credentials"), $Skills | Out-Null
  [System.IO.File]::WriteAllText($ArqPapel, "cs")
  Write-Host "Papel: CS (so as skills da CS, sem Meta)"
  $Modelo = Join-Path $Aqui "workspace\CLAUDE-cs.md"; $Outro = Join-Path $Aqui "workspace\CLAUDE.md"
} else {
  New-Item -ItemType Directory -Force -Path (Join-Path $Ws "credentials"), (Join-Path $Ws "meta-ads"), $Skills | Out-Null
  if (Test-Path $ArqPapel) { Remove-Item -LiteralPath $ArqPapel -Force; Write-Host "Papel: pacote completo" }
  $Modelo = Join-Path $Aqui "workspace\CLAUDE.md"; $Outro = Join-Path $Aqui "workspace\CLAUDE-cs.md"
}
$ClaudeMd = Join-Path $Ws "CLAUDE.md"
if (-not (Test-Path $ClaudeMd)) { Copy-Item $Modelo $ClaudeMd; Write-Host "criado: $Ws\CLAUDE.md" }
elseif ((Test-Path $Outro) -and ((Get-FileHash -LiteralPath $ClaudeMd).Hash -eq (Get-FileHash -LiteralPath $Outro).Hash)) {
  Copy-Item $Modelo $ClaudeMd -Force; Write-Host "trocado: $ClaudeMd pelo do papel atual (era o do outro papel, sem alteracao)"
}
elseif ($Papel -eq "cs" -and (Get-Content -LiteralPath $ClaudeMd -TotalCount 1 -Encoding UTF8) -ne "# Workspace OdontoRise (CS)") {
  Write-Host "AVISO: $ClaudeMd nao e o da CS (veio de uma instalacao anterior e foi editado). Para trocar: apague o arquivo e rode o instalador de novo."
}
# Regra 4 mudou em 01/10/2026: troca só a linha antiga exata; o resto do CLAUDE.md da pessoa fica como está.
# O acento vai por [char] para não depender da codificação com que o PowerShell lê este arquivo.
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
# Destino do atalho (junction ou link), ou "" se não for atalho.
function AlvoDoAtalho($caminho) {
  $item = Get-Item -LiteralPath $caminho -Force
  if (-not $item.LinkType) { return "" }
  return [string]($item.Target | Select-Object -First 1)
}
if ($Aqui -ne (Join-Path $Skills "meta-ads-odontorise")) { Ligar $Aqui "meta-ads-odontorise" }
if ($Papel -eq "cs") {
  $Lista = @(Get-Content -LiteralPath (Join-Path $Aqui "papeis\cs.txt") -Encoding UTF8 | ForEach-Object { $_.Trim() } | Where-Object { $_ -and -not $_.StartsWith("#") })
  $PastaSkills = (Join-Path $Aqui "skills") + [System.IO.Path]::DirectorySeparatorChar
  $PastaCs = (Join-Path $Aqui "papeis\cs") + [System.IO.Path]::DirectorySeparatorChar
  # Instalação completa anterior: desliga as skills do pacote que não são da CS (só atalhos para dentro do pacote).
  # Directory.Delete sem recursão apaga só o atalho, nunca o conteúdo da skill no pacote.
  foreach ($item in @(Get-ChildItem -LiteralPath $Skills -Force -Directory)) {
    $alvo = AlvoDoAtalho $item.FullName
    $doPacote = $alvo -and ($alvo.StartsWith($PastaSkills, [System.StringComparison]::OrdinalIgnoreCase) -or $alvo.StartsWith($PastaCs, [System.StringComparison]::OrdinalIgnoreCase))
    if ($doPacote -and ($Lista -notcontains $item.Name)) {
      [System.IO.Directory]::Delete($item.FullName)
      Write-Host "desligada: $($item.FullName) (nao e da CS)"
    }
  }
  foreach ($n in $Lista) {
    # versão da CS (papeis\cs\<nome>, sem Meta) quando existe; senão a skill do pacote
    $alvo = if (Test-Path (Join-Path $Aqui "papeis\cs\$n")) { Join-Path $Aqui "papeis\cs\$n" } else { Join-Path $Aqui "skills\$n" }
    if (-not (Test-Path $alvo)) { Write-Host "AVISO: a skill $n da lista da CS nao existe no pacote"; continue }
    $dest = Join-Path $Skills $n
    if ((Test-Path $dest) -and ((AlvoDoAtalho $dest) -ne (Get-Item -LiteralPath $alvo).FullName)) { [System.IO.Directory]::Delete($dest) }
    if (-not (Test-Path $dest)) { New-Item -ItemType Junction -Path $dest -Target $alvo | Out-Null }
    Write-Host "ligada: $dest"
  }
  $Py = $null
  try { $Py = python --version 2>&1 } catch { }
  if ($Py -and $LASTEXITCODE -eq 0) { Write-Host "Python ok ($Py). A CS nao usa a biblioteca da Meta nem o navegador: nada a instalar." }
  else { Write-Host "AVISO: python nao encontrado. Passo 3 do guia." }
  Write-Host ""
  Write-Host "Pronto. Proximos passos: o token do ClickUp (passo 8 do guia) e depois, no Claude: 'minhas tarefas no ClickUp'."
} else {
  # Quem era CS e volta ao pacote completo: apaga só os atalhos das versões da CS (o conteúdo fica no pacote).
  $PastaCs = (Join-Path $Aqui "papeis\cs") + [System.IO.Path]::DirectorySeparatorChar
  foreach ($item in @(Get-ChildItem -LiteralPath $Skills -Force -Directory)) {
    $alvo = AlvoDoAtalho $item.FullName
    if ($alvo -and $alvo.StartsWith($PastaCs, [System.StringComparison]::OrdinalIgnoreCase)) { [System.IO.Directory]::Delete($item.FullName) }
  }
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
}
