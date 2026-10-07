#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Coleta na Biblioteca de Anúncios do Meta pelo navegador: Chromium headless, sem Apify, sem login.

Rota sem Apify da skill /raio-x-concorrentes. A Biblioteca é pública, então qualquer gestor consegue rodar.
Sai no MESMO formato do coleta.py (itens como o robô facebook-ads-scraper devolve): extrai.py, thumbs.py
e board.py funcionam sem mudar nada.

  navegador.py checar                                     # Playwright e Chromium prontos?
  navegador.py busca   termos.json   30  descoberta.json  # quem anuncia para cada termo (página, id, quantos anúncios)
  navegador.py paginas paginas.json 150  coleta.json      # todos os anúncios ativos de cada página

termos.json  = ["lentes de contato dental guarulhos", "facetas guarulhos"]
paginas.json = ["1232412156613352", "https://www.facebook.com/handle/", {"nome": "Clínica X", "pid": "123"}]
               A Biblioteca abre a página pelo id numérico. Handle ou nome é resolvido pela busca de páginas
               da própria Biblioteca; quando não resolve, o script diz qual falta (o gestor copia o
               view_all_page_id da URL ao abrir a página na Biblioteca).

Instalar, uma vez (o instalador do pacote já faz):
  python3 -m pip install --user playwright     (se reclamar de externally-managed, acrescente --break-system-packages)
  python3 -m playwright install chromium

Mensagens para pessoas vão no stderr; o stdout é só JSON.
"""
import argparse, json, os, re, sys, time, unicodedata, urllib.parse

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE = "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=BR&media_type=all"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/129.0.0.0 Safari/537.36")
MES = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6, "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}
RX_ID = re.compile(r"Identifica[çc][ãa]o da biblioteca:\s*(\d+)")
PY = os.path.basename(sys.executable) or "python3"
COMO_INSTALAR = (f"no terminal: {PY} -m pip install --user playwright (se aparecer externally-managed-environment, "
                 f"acrescente --break-system-packages) e depois {PY} -m playwright install chromium")

# Acha cada cartão de anúncio pela etiqueta "Identificação da biblioteca" e sobe até o bloco do anúncio.
JS = r"""
() => {
  const out = [];
  const labels = Array.from(document.querySelectorAll('div,span')).filter(e => e.children.length === 0 && /^Identifica[çc][ãa]o da biblioteca:\s*\d+/.test(e.textContent.trim()));
  const seen = new Set();
  for (const lab of labels) {
    const id = lab.textContent.match(/(\d+)/)[1];
    if (seen.has(id)) continue; seen.add(id);
    let card = lab;
    for (let i = 0; i < 14 && card.parentElement; i++) {
      card = card.parentElement;
      const t = card.innerText || '';
      const n = (t.match(/Identifica[çc][ãa]o da biblioteca:/g) || []).length;
      if (n > 1) break;
      if (/Patrocinado/.test(t) && (card.querySelector('img') || card.querySelector('video'))) break;
    }
    let txt = card.innerText || '';
    if ((txt.match(/Identifica[çc][ãa]o da biblioteca:/g) || []).length > 1) {
      const idx = txt.indexOf(id);
      const next = txt.indexOf('Identificação da biblioteca:', idx + 10);
      txt = txt.slice(Math.max(0, txt.lastIndexOf('Ativo', idx)), next > 0 ? next : undefined);
    }
    const imgs = Array.from(card.querySelectorAll('img')).map(e => e.currentSrc || e.src).filter(s => s && (s.includes('fbcdn') || s.includes('scontent')) && !s.includes('rsrc.php'));
    const vids = Array.from(card.querySelectorAll('video')).map(e => ({poster: e.poster || null, src: e.currentSrc || e.src || null}));
    const hrefs = Array.from(card.querySelectorAll('a[href]')).map(a => a.href);
    const links = hrefs.filter(h => h.includes('l.facebook.com/l.php') || (!h.includes('facebook.com') && !h.includes('instagram.com/ads')));
    const pageLinks = hrefs.filter(h => /^https?:\/\/(www\.)?facebook\.com\/[^\/?#]+\/?(\?|$)/.test(h) && !h.includes('/ads/library'));
    out.push({id, txt, imgs: imgs.slice(0, 6), vids: vids.slice(0, 3), links: links.slice(0, 6), pageLinks: pageLinks.slice(0, 4)});
  }
  return out;
}
"""
JS_PAGINAS = r"""
() => Array.from(document.querySelectorAll('a[href*="view_all_page_id="]')).map(a => ({href: a.href, texto: (a.innerText || '').trim()}))
"""


def falha(msg, acao=None):
    print(json.dumps({"ok": False, "erro": msg, "acao": acao}, ensure_ascii=False))
    sys.exit(1)


def aviso(msg):
    print(msg, file=sys.stderr, flush=True)


def playwright_ou_falha():
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return sync_playwright
    except ImportError:
        falha("Playwright não instalado (é o navegador do raio-x sem Apify)", COMO_INSTALAR)


def cmd_checar(_args):
    sync_playwright = playwright_ou_falha()
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            versao = b.version
            b.close()
    except Exception as e:  # Chromium ausente ou quebrado
        msg = str(e)
        if "Executable doesn't exist" in msg or "playwright install" in msg:
            falha("Playwright instalado, mas o Chromium não", f"no terminal: {PY} -m playwright install chromium")
        falha(f"não consegui abrir o Chromium ({type(e).__name__})", f"rodar de novo: {PY} -m playwright install chromium")
    print(json.dumps({"ok": True, "chromium": versao, "fonte": "Biblioteca de Anúncios do Meta (pública, sem login)"}, ensure_ascii=False))


# ---------------------------------------------------------------------------
# navegador
# ---------------------------------------------------------------------------

def abre_contexto(p):
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(locale="pt-BR", viewport={"width": 1280, "height": 2400}, user_agent=UA)
    return b, ctx


def fecha_dialogos(pg):
    for nome in ("Permitir todos os cookies", "Allow all cookies", "Aceitar todos", "Fechar", "Agora não"):
        try:
            pg.get_by_role("button", name=re.compile(nome, re.I)).first.click(timeout=1500)
            time.sleep(0.8)
        except Exception:
            pass


def rola_e_coleta(pg, url, limite, max_rolagens):
    """Abre a URL, rola até estabilizar (ou até o limite de anúncios) e devolve (declarado, cartões)."""
    pg.goto(url, wait_until="domcontentloaded", timeout=90000)
    time.sleep(5)
    fecha_dialogos(pg)
    corpo = pg.inner_text("body")
    m = re.search(r"~?\s*([\d\.]+)\s+resultados?", corpo)
    declarado = int(m.group(1).replace(".", "")) if m else 0
    if re.search(r"Nenhum anúncio corresponde|No ads match|Não encontramos anúncios", corpo):
        return declarado, []
    ultimo, iguais = -1, 0
    for _ in range(max_rolagens):
        pg.mouse.wheel(0, 5000)
        time.sleep(1.6)
        n = len(set(RX_ID.findall(pg.inner_text("body"))))
        iguais = iguais + 1 if n == ultimo else 0
        ultimo = n
        if iguais >= 4 or (limite and n >= limite):
            break
    return declarado, pg.evaluate(JS)


def nome_da_pagina(txt):
    linhas = [l.strip() for l in txt.split("\n") if l.strip()]
    for i, l in enumerate(linhas):
        if l == "Patrocinado" and i > 0:
            return linhas[i - 1]
    return None


def cta_tipo(cta):
    if not cta:
        return ""
    if "whatsapp" in cta.lower():
        return "WHATSAPP_MESSAGE"
    s = unicodedata.normalize("NFKD", cta).encode("ascii", "ignore").decode()
    return re.sub(r"\W+", "_", s).strip("_").upper()


def monta_item(c, pid, nome_pagina):
    """Converte um cartão lido na tela para o formato do robô facebook-ads-scraper (o que extrai.py lê)."""
    t = c["txt"]
    m = re.search(r"Veicula[çc][ãa]o iniciada em (\d{1,2}) de (\w+)\.? de (\d{4})", t)
    inicio = f"{m.group(3)}-{MES.get(m.group(2)[:3].lower(), 0):02d}-{int(m.group(1)):02d}" if m else ""
    col = re.search(r"(\d+) anúncios usam esse criativo", t)
    variacoes = int(col.group(1)) if col else 1
    video = bool(re.search(r"\b\d:\d\d\s*/\s*\d:\d\d\b", t)) or bool(c["vids"])
    corpo = ""
    mb = re.search(r"Patrocinado\n(.*?)(?:\n\d:\d\d\s*/\s*\d:\d\d|\n[A-Z0-9.-]+\.[A-Z]{2,}(?:\.[A-Z]{2})?\n|\Z)", t, re.S)
    if mb:
        corpo = mb.group(1).strip()
    cta = None
    mc = re.search(r"\n(Enviar mensagem pelo WhatsApp|Saiba mais|Enviar mensagem|Fale conosco|Agendar|Reservar|Cadastre-se|"
                   r"Ligar agora|Comprar agora|Ver mais|Entre em contato|Baixar|Inscreva-se)\s*$", t.strip())
    if mc:
        cta = mc.group(1)
    dest = None
    for l in c["links"]:
        if "l.facebook.com/l.php" in l:
            q = urllib.parse.parse_qs(urllib.parse.urlparse(l).query).get("u", [None])[0]
            if q:
                dest = q
                break
    if not dest and c["links"]:
        dest = c["links"][0]
    dom = re.search(r"\n([A-Z0-9.-]+\.[A-Z]{2,}(?:\.[A-Z]{2})?)\n", t)
    if not dest and dom:
        dest = "https://" + dom.group(1).lower()
    poster = c["vids"][0]["poster"] if c["vids"] and c["vids"][0].get("poster") else None
    imagem = c["imgs"][0] if c["imgs"] else None
    nome = nome_da_pagina(t) or nome_pagina or ""
    snapshot = {
        "pageName": nome, "body": {"text": corpo}, "displayFormat": "VIDEO" if video else "IMAGE",
        "videos": [{"videoHdUrl": c["vids"][0]["src"] if c["vids"] else "", "videoPreviewImageUrl": poster or imagem or ""}] if video else [],
        "images": [] if video else ([{"resizedImageUrl": imagem}] if imagem else []),
        "cards": [], "linkUrl": dest or "", "ctaType": cta_tipo(cta), "ctaText": cta or "", "fonte": "navegador",
    }
    return {"adArchiveID": c["id"], "pageId": pid or "", "pageName": nome, "startDateFormatted": inicio,
            "collationCount": variacoes, "snapshot": snapshot,
            "pageLinks": c.get("pageLinks") or []}


def pid_de_link(h):
    m = re.match(r"^https?://(?:www\.)?facebook\.com/([^/?#]+)/?", h or "")
    if not m:
        return None, None
    alvo = m.group(1)
    return (alvo, None) if alvo.isdigit() else (None, alvo)


def resolve_pagina(ctx, consulta):
    """Busca de páginas da própria Biblioteca: devolve [(id, nome)] para o handle ou nome dado."""
    pg = ctx.new_page()
    achados = []
    try:
        pg.goto(f"{BASE}&q={urllib.parse.quote(consulta)}&search_type=page", wait_until="domcontentloaded", timeout=90000)
        time.sleep(4)
        fecha_dialogos(pg)
        for a in pg.evaluate(JS_PAGINAS):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(a["href"]).query).get("view_all_page_id", [None])[0]
            if q and (q, a["texto"]) not in achados:
                achados.append((q, a["texto"]))
    except Exception as e:
        aviso(f"  busca de página '{consulta}': {type(e).__name__}")
    finally:
        pg.close()
    return achados


def normaliza_paginas(lista):
    out = []
    for e in lista:
        if isinstance(e, dict):
            pid = str(e.get("pid") or e.get("id") or e.get("page_id") or "").strip() or None
            out.append({"nome": e.get("nome") or e.get("page") or e.get("handle") or pid, "pid": pid if (pid and pid.isdigit()) else None,
                        "handle": e.get("handle") or (None if (pid and pid.isdigit()) else pid)})
        else:
            s = str(e).strip()
            if s.isdigit():
                out.append({"nome": s, "pid": s, "handle": None})
            elif s.startswith("http"):
                pid, handle = pid_de_link(s)
                out.append({"nome": handle or pid, "pid": pid, "handle": handle})
            else:
                out.append({"nome": s, "pid": None, "handle": s})
    return out


def cmd_paginas(args):
    sync_playwright = playwright_ou_falha()
    alvo = normaliza_paginas(json.load(open(args.entrada, encoding="utf-8-sig")))
    itens, resumo, sem_id = [], [], []
    with sync_playwright() as p:
        b, ctx = abre_contexto(p)
        for i, pagina in enumerate(alvo, 1):
            if not pagina["pid"]:
                cand = resolve_pagina(ctx, pagina["handle"] or pagina["nome"])
                if len(cand) == 1 or (cand and pagina["handle"] and cand[0][1].lower().replace(" ", "") == pagina["handle"].lower()):
                    pagina["pid"], pagina["nome"] = cand[0][0], cand[0][1] or pagina["nome"]
                elif cand:
                    sem_id.append({"pagina": pagina["nome"], "candidatos": [{"pid": c[0], "nome": c[1]} for c in cand[:5]]})
                    aviso(f"[{i}/{len(alvo)}] {pagina['nome']}: várias páginas com esse nome, escolha o id e repita")
                    continue
                else:
                    sem_id.append({"pagina": pagina["nome"], "candidatos": []})
                    aviso(f"[{i}/{len(alvo)}] {pagina['nome']}: não achei o id; abra a página na Biblioteca e copie o view_all_page_id da URL")
                    continue
            pg = ctx.new_page()
            url = f"{BASE}&view_all_page_id={pagina['pid']}&search_type=page"
            try:
                declarado, cards = rola_e_coleta(pg, url, args.limite, args.rolagens)
                ads = [monta_item(c, pagina["pid"], pagina["nome"]) for c in cards]
                vids = sum(1 for a in ads if a["snapshot"]["displayFormat"] == "VIDEO")
                wa = sum(1 for a in ads if a["snapshot"]["ctaType"] == "WHATSAPP_MESSAGE" or "whatsapp" in (a["snapshot"]["linkUrl"] or "").lower())
                itens.extend(ads)
                resumo.append({"pagina": pagina["nome"], "pid": pagina["pid"], "declarado": declarado, "coletados": len(ads), "video": vids, "whatsapp": wa})
                aviso(f"[{i}/{len(alvo)}] {str(pagina['nome'])[:38]:38} | declarado={declarado:>4} | coletados={len(ads):>3} | vídeo={vids:>3} | WhatsApp={wa:>3}")
            except Exception as e:
                resumo.append({"pagina": pagina["nome"], "pid": pagina["pid"], "erro": type(e).__name__})
                aviso(f"[{i}/{len(alvo)}] {pagina['nome']}: ERRO {type(e).__name__}: {str(e)[:120]}")
            finally:
                pg.close()
        b.close()
    json.dump(itens, open(args.saida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"ok": True, "arquivo": args.saida, "paginas": len(resumo), "anuncios": len(itens),
                      "resumo": resumo, "sem_id": sem_id, "fonte": "navegador",
                      "proximo": "extrai.py <coleta.json> anuncios.json --nicho odonto, depois thumbs.py na mesma sessão"}, ensure_ascii=False))


def cmd_busca(args):
    sync_playwright = playwright_ou_falha()
    termos = json.load(open(args.entrada, encoding="utf-8-sig"))
    por_pagina = {}
    with sync_playwright() as p:
        b, ctx = abre_contexto(p)
        for i, termo in enumerate(termos, 1):
            pg = ctx.new_page()
            try:
                url = f"{BASE}&q={urllib.parse.quote(termo)}&search_type=keyword_unordered"
                declarado, cards = rola_e_coleta(pg, url, args.limite, args.rolagens)
                for c in cards:
                    nome = nome_da_pagina(c["txt"]) or "?"
                    pid, handle = None, None
                    for h in c.get("pageLinks") or []:
                        pid, handle = pid_de_link(h)
                        if pid or handle:
                            break
                    chave = pid or handle or nome
                    reg = por_pagina.setdefault(chave, {"pageName": nome, "pid": pid, "handle": handle, "anuncios_vistos": 0, "termos": []})
                    reg["anuncios_vistos"] += 1
                    if termo not in reg["termos"]:
                        reg["termos"].append(termo)
                aviso(f"[{i}/{len(termos)}] {termo[:40]:40} | declarado={declarado:>4} | cartões={len(cards):>3}")
            except Exception as e:
                aviso(f"[{i}/{len(termos)}] {termo}: ERRO {type(e).__name__}: {str(e)[:120]}")
            finally:
                pg.close()
        b.close()
    saida = sorted(por_pagina.values(), key=lambda r: -r["anuncios_vistos"])
    json.dump(saida, open(args.saida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"ok": True, "arquivo": args.saida, "paginas": len(saida), "fonte": "navegador",
                      "nota": "volume de descoberta é amostra: o número real de anúncios só sai na coleta por página (subcomando paginas)"},
                     ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("checar")
    for nome in ("busca", "paginas"):
        s = sub.add_parser(nome)
        s.add_argument("entrada")
        s.add_argument("limite", type=int, nargs="?", default=150, help="máximo de anúncios por página ou termo (0 = sem limite)")
        s.add_argument("saida")
        s.add_argument("--rolagens", type=int, default=60, help="máximo de rolagens por página")
    args = ap.parse_args()
    if args.cmd == "checar":
        cmd_checar(args)
    elif args.cmd == "busca":
        cmd_busca(args)
    elif args.cmd == "paginas":
        cmd_paginas(args)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
