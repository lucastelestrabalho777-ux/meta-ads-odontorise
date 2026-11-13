#!/usr/bin/env python3
"""
meta-ads-odontorise: PDF no padrão visual da OdontoRise (documento de leitura em A4 ou apresentação 16:9).

Uso:
  python3 scripts/pdf.py novo --tipo documento|apresentacao --nome "Ata da reunião Dra. X"
      copia o modelo e o logo para ~/OdontoRise/pdfs/<data>-<nome>/ e diz qual arquivo .html editar
  python3 scripts/pdf.py gerar CAMINHO.html [--saida ARQUIVO.pdf]
      confere o conteúdo (nada passando do rodapé, sem travessão, sem texto do modelo esquecido) e gera o PDF

Não instala nada: usa o Chrome ou o Edge que já está no computador (override: ODR_NAVEGADOR com o caminho do
executável). Só escreve dentro da pasta do próprio documento. Não envia o PDF a ninguém.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from datetime import date

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

AQUI = os.path.dirname(os.path.abspath(__file__))
MODELOS = os.path.join(AQUI, "..", "skills", "pdf-odontorise", "modelos")
PASTA_PDFS = os.path.expanduser(os.environ.get("ODR_PDFS", "~/OdontoRise/pdfs"))
TIPOS = {"documento": "documento.html", "apresentacao": "apresentacao.html"}

# Texto que só existe no modelo: se sobrar no arquivo, o documento não está pronto.
SOBRAS = ("DD · MM · AAAA", "Título do documento", "Título da apresentação", "segunda linha em verde",
          "Nome do indicador", "Título da seção", "Título do slide", "Título do cartão", "Quem assina",
          "Quem apresenta", "Rótulo da seção", "Área ou assunto", "Tipo do material")

# Roda dentro da página: mede, por página ou slide, quanto falta para o conteúdo encostar no rodapé.
JS_CONFERE = """
<script>
window.addEventListener('load', function () {
  var sel = document.querySelector('.slide') ? '.slide' : '.page';
  var out = Array.prototype.map.call(document.querySelectorAll(sel), function (s, i) {
    var r = s.getBoundingClientRect();
    var f = s.querySelector('.pfoot, .footer, .bottom');
    var ftop = f ? f.getBoundingClientRect().top - r.top : r.height;
    var maxb = 0;
    Array.prototype.forEach.call(s.querySelectorAll('*'), function (el) {
      if (el.closest('.pfoot, .footer, .bottom')) return;
      var b = el.getBoundingClientRect().bottom - r.top;
      if (b > maxb) maxb = b;
    });
    return { n: i + 1, sobra: Math.round(ftop - maxb), altura: Math.round(r.height) };
  });
  document.documentElement.setAttribute('data-odr-confere', JSON.stringify(out));
});
</script>
"""


def _sai(obj, codigo=0):
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    sys.exit(codigo)


def _falha(msg, acao=None):
    out = {"ok": False, "erro": msg}
    if acao:
        out["acao"] = acao
    _sai(out, 1)


def slug(texto):
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t[:60].strip("-") or "documento"


def nome_pdf(titulo):
    t = unicodedata.normalize("NFKD", str(titulo or "")).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "_", t).strip("_")
    return (t[:80].strip("_") or "Documento") + "_OdontoRise.pdf"


def navegador():
    """Caminho do Chrome ou do Edge instalado. None se não achar."""
    cand = [os.environ.get("ODR_NAVEGADOR")]
    if sys.platform == "darwin":
        for app, exe in (("Google Chrome", "Google Chrome"), ("Microsoft Edge", "Microsoft Edge"),
                         ("Brave Browser", "Brave Browser"), ("Chromium", "Chromium")):
            for base in ("/Applications", os.path.expanduser("~/Applications")):
                cand.append(f"{base}/{app}.app/Contents/MacOS/{exe}")
    elif os.name == "nt":
        for var in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(var)
            if base:
                cand.append(os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"))
                cand.append(os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"))
    else:
        for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"):
            cand.append(shutil.which(n))
    for c in cand:
        if c and os.path.isfile(c):
            return c
    return None


def _uri(caminho):
    from pathlib import Path
    return Path(caminho).resolve().as_uri()


def _chrome(exe, args, perfil, timeout=120):
    base = [exe, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
            "--disable-extensions", "--hide-scrollbars", f"--user-data-dir={perfil}"]
    return subprocess.run(base + args, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")


def conferir_texto(html):
    """Problemas que dá para ver sem abrir o navegador. Devolve lista de avisos."""
    avisos = []
    corpo = re.sub(r"<style>.*?</style>|<!--.*?-->", "", html, flags=re.S)
    texto = re.sub(r"<[^>]+>", " ", corpo)
    if "\u2014" in texto:
        avisos.append("tem travessão no texto: trocar por vírgula, ponto ou dois-pontos")
    sobras = [s for s in SOBRAS if s in texto]
    if sobras:
        avisos.append("sobrou texto do modelo: " + "; ".join(sobras))
    if re.search(r"(?<![\w.])00(?![\w.])", texto):
        avisos.append("sobrou número 00 do modelo: trocar pelo número real ou apagar o bloco")
    return avisos


def cmd_novo(a):
    origem = os.path.join(MODELOS, TIPOS[a.tipo])
    if not os.path.isfile(origem):
        _falha("modelo não encontrado no pacote", "rodar /atualizar-git-odontorise")
    s = slug(a.nome)
    pasta = os.path.join(PASTA_PDFS, f"{date.today().isoformat()}-{s}")
    destino = os.path.join(pasta, s + ".html")
    if os.path.exists(destino):
        _falha(f"já existe um documento com esse nome hoje: {destino}", "editar esse arquivo ou usar outro --nome")
    os.makedirs(pasta, exist_ok=True)
    shutil.copy(origem, destino)
    shutil.copy(os.path.join(MODELOS, "logo.png"), os.path.join(pasta, "logo.png"))
    _sai({"ok": True, "tipo": a.tipo, "editar": destino, "pasta": pasta,
          "proximo_passo": f"trocar o conteúdo do arquivo e rodar: pdf.py gerar \"{destino}\""})


def cmd_gerar(a):
    html_path = os.path.abspath(os.path.expanduser(a.html))
    if not os.path.isfile(html_path):
        _falha(f"arquivo não encontrado: {html_path}")
    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    apresentacao = 'class="slide' in html
    if not apresentacao and 'class="page' not in html:
        _falha("o arquivo não segue o modelo da OdontoRise (sem .page e sem .slide)",
               "criar o arquivo com: pdf.py novo --tipo documento|apresentacao --nome \"...\"")
    exe = navegador()
    if not exe:
        _falha("não achei o Chrome nem o Edge neste computador",
               "instalar o Google Chrome, ou apontar ODR_NAVEGADOR para o executável do navegador")
    pasta = os.path.dirname(html_path)
    if not os.path.isfile(os.path.join(pasta, "logo.png")) and os.path.isfile(os.path.join(MODELOS, "logo.png")):
        shutil.copy(os.path.join(MODELOS, "logo.png"), os.path.join(pasta, "logo.png"))
    titulo = re.search(r"<title>(.*?)</title>", html, re.S)
    saida = os.path.abspath(os.path.expanduser(a.saida)) if a.saida else os.path.join(
        pasta, nome_pdf(titulo.group(1).strip() if titulo else os.path.basename(html_path)))
    avisos = conferir_texto(html)
    janela = "1920,1080" if apresentacao else "794,1123"

    perfil = tempfile.mkdtemp(prefix="odr-pdf-")
    copia = os.path.join(pasta, ".conferindo-" + os.path.basename(html_path))
    paginas = []
    try:
        # 1) medir a sobra de cada página numa cópia com o script de conferência
        with open(copia, "w", encoding="utf-8") as f:
            f.write(html.replace("</body>", JS_CONFERE + "</body>") if "</body>" in html else html + JS_CONFERE)
        r = _chrome(exe, [f"--window-size={janela}", "--virtual-time-budget=3000", "--dump-dom", _uri(copia)], perfil)
        m = re.search(r'data-odr-confere="([^"]*)"', r.stdout or "")
        if m:
            paginas = json.loads(m.group(1).replace("&quot;", '"'))
        else:
            avisos.append("não consegui medir as páginas: abrir o PDF e conferir se nada passou do rodapé")
        # 2) gerar o PDF do arquivo original
        if os.path.exists(saida):
            os.remove(saida)
        r = _chrome(exe, [f"--window-size={janela}", "--no-pdf-header-footer", "--virtual-time-budget=3000",
                          f"--print-to-pdf={saida}", _uri(html_path)], perfil)
        if not os.path.isfile(saida) or os.path.getsize(saida) < 1000:
            _falha("o navegador não gerou o PDF", (r.stderr or "").strip()[-300:] or "tentar de novo")
    except subprocess.TimeoutExpired:
        _falha("o navegador demorou demais para responder", "fechar o Chrome e tentar de novo")
    finally:
        shutil.rmtree(perfil, ignore_errors=True)
        if os.path.exists(copia):
            os.remove(copia)

    estouro = [p["n"] for p in paginas if p["sobra"] < 0]
    apertado = [p["n"] for p in paginas if 0 <= p["sobra"] < 12]
    nome = "slide" if apresentacao else "página"
    if estouro:
        avisos.append(f"conteúdo passando do rodapé: {nome} " + ", ".join(map(str, estouro))
                      + ". Tirar texto ou dividir em mais um(a) " + nome)
    if apertado:
        avisos.append(f"conteúdo colado no rodapé: {nome} " + ", ".join(map(str, apertado)))
    _sai({"ok": not estouro, "pdf": saida, "tipo": "apresentacao" if apresentacao else "documento",
          "paginas": len(paginas) or None, "sobra_por_pagina": {p["n"]: p["sobra"] for p in paginas},
          "avisos": avisos, "navegador": os.path.basename(exe),
          "lembrete": "abrir o PDF e olhar antes de enviar; o arquivo fica só neste computador"},
         0 if not estouro else 2)


def main():
    p = argparse.ArgumentParser(description="PDF no padrão OdontoRise")
    sub = p.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("novo")
    n.add_argument("--tipo", choices=sorted(TIPOS), default="documento")
    n.add_argument("--nome", required=True)
    n.set_defaults(f=cmd_novo)
    g = sub.add_parser("gerar")
    g.add_argument("html")
    g.add_argument("--saida")
    g.set_defaults(f=cmd_gerar)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
