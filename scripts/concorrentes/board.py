#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera o documento HTML da pesquisa de concorrentes.

  board.py config.json anuncios.json            # gera o HTML
  board.py config.json anuncios.json --folha    # folha de contato das capas (leitura visual)

O config.json carrega o julgamento (achados, analise final, perfis). Modelo em
referencia/config-modelo.json. Texto do documento segue referencia/tom-cliente.md.
"""
import base64, collections, html, json, os, statistics, sys

E = html.escape
CAP_GALERIA = 24  # anúncios por clínica na galeria; o resto fica no link da Biblioteca


def carrega(cfg_path, ads_path):
    cfg = json.load(open(cfg_path))
    ads = json.load(open(ads_path))
    perfis = cfg["perfis"]
    ads = [a for a in ads if a["page"] in perfis]
    for a in ads:
        a.update(perfis[a["page"]])
    return cfg, ads


def resumir(ads, cliente_page, perfis):
    por = collections.defaultdict(list)
    for a in ads: por[a["nome"]].append(a)
    out = []
    for nome, rows in por.items():
        dias = [r["dias"] for r in rows if r["dias"] is not None]
        vids = [r for r in rows if r["formato"] == "VIDEO"]
        out.append(dict(
            nome=nome, cliente=(rows[0]["page"] == cliente_page), n=len(rows),
            reg=rows[0]["reg"], end=rows[0]["end"], dist=rows[0]["dist"],
            pctvid=round(100 * len(vids) / len(rows)),
            peg=collections.Counter(r["pegada"] for r in vids).most_common(2),
            maxd=max(dias) if dias else 0,
            med=int(statistics.median(dias)) if dias else 0,
            rows=sorted(rows, key=lambda x: -(x["dias"] or 0))))
    out.sort(key=lambda x: -x["n"])
    return out


def img64(thumbs_dir, ad_id):
    p = f"{thumbs_dir}/{ad_id}.jpg"
    if not os.path.exists(p): return None
    return "data:image/jpeg;base64," + base64.b64encode(open(p, "rb").read()).decode()


def barras(itens, total, cls=""):
    return "".join(
        f'<div class="bar-row"><span class="bar-lab">{E(k)}</span>'
        f'<span class="bar-track"><span class="bar-fill {cls}" style="width:{round(100*v/total)}%"></span></span>'
        f'<span class="bar-num">{v}</span></div>' for k, v in itens)


def folha_contato(cfg, ads):
    """Uma capa por anunciante (o video mais antigo) num mosaico, para leitura visual."""
    from PIL import Image, ImageDraw
    td = cfg["thumbs_dir"]
    vids = [a for a in ads if a["formato"] == "VIDEO" and os.path.exists(f"{td}/{a['ad_id']}.jpg")]
    melhor = {}
    for a in sorted(vids, key=lambda x: -(x["dias"] or 0)):
        melhor.setdefault(a["nome"], a)
    sel = list(melhor.values())[:16]
    C = R = 4; W = H = 300
    sheet = Image.new("RGB", (C * W, R * H), "white"); dr = ImageDraw.Draw(sheet)
    for i, a in enumerate(sel):
        im = Image.open(f"{td}/{a['ad_id']}.jpg").convert("RGB"); im.thumbnail((W, H))
        x, y = (i % C) * W, (i // C) * H
        sheet.paste(im, (x + (W - im.width) // 2, y + (H - im.height) // 2))
        dr.rectangle([x, y, x + W - 1, y + H - 1], outline="black")
        dr.text((x + 6, y + 6), str(i + 1), fill="red")
    saida = os.path.join(os.path.dirname(cfg["saida"]) or ".", "folha_contato.jpg")
    sheet.save(saida, quality=70)
    for i, a in enumerate(sel):
        print(i + 1, a["nome"][:40], "|", a["dias"], "d |", a["tema"])
    print("\nfolha:", saida, ": abrir e ler antes de fechar a pegada dos videos")


CSS = """
:root{
  --bg:#F5F6F8; --panel:#FFFFFF; --ink:#141922; --ink-2:#4B5563; --ink-3:#8A93A0;
  --line:#DFE3E9; --line-2:#EDF0F4;
  --client:#7A0C39; --client-soft:#F6E9EF;
  --data:#15616D; --data-soft:#E4EFF1;
  --flag:#9A4A12; --flag-soft:#F7EBE1;
  --shadow:0 1px 2px rgba(20,25,34,.05);
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#11141A; --panel:#171B23; --ink:#E8EBF0; --ink-2:#A8B1BE; --ink-3:#6F7A88;
  --line:#262C36; --line-2:#1F242D; --client:#E2769F; --client-soft:#2A1520;
  --data:#63C2CE; --data-soft:#122228; --flag:#E0965C; --flag-soft:#241A11; --shadow:none;}}
:root[data-theme="dark"]{
  --bg:#11141A; --panel:#171B23; --ink:#E8EBF0; --ink-2:#A8B1BE; --ink-3:#6F7A88;
  --line:#262C36; --line-2:#1F242D; --client:#E2769F; --client-soft:#2A1520;
  --data:#63C2CE; --data-soft:#122228; --flag:#E0965C; --flag-soft:#241A11; --shadow:none;}
*{box-sizing:border-box}
body{margin:0; background:var(--bg); color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; font-size:15px; line-height:1.55;
  -webkit-font-smoothing:antialiased}
.wrap{max-width:1120px; margin:0 auto; padding:40px 24px 80px; display:flex; flex-direction:column; gap:52px}
h1,h2,h3{font-family:"Helvetica Neue",Helvetica,Arial,sans-serif; text-wrap:balance; margin:0}
h1{font-size:clamp(30px,4.4vw,46px); font-weight:700; letter-spacing:-.03em; line-height:1.04}
h2{font-size:20px; font-weight:700; letter-spacing:-.015em}
h3{font-size:15px; font-weight:700; letter-spacing:-.01em}
p{margin:0; max-width:66ch}
a{color:inherit}
.eyebrow{font-size:11px; font-weight:700; letter-spacing:.13em; text-transform:uppercase; color:var(--ink-3)}
.lede{color:var(--ink-2); font-size:16.5px}
.sec{display:flex; flex-direction:column; gap:18px}
.sec-head{display:flex; flex-direction:column; gap:6px; border-top:1px solid var(--line); padding-top:14px}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-variant-numeric:tabular-nums}
.kpis{display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:1px;
  background:var(--line); border:1px solid var(--line); border-radius:3px; overflow:hidden}
.kpi{background:var(--panel); padding:16px 18px; display:flex; flex-direction:column; gap:3px}
.kpi b{font-family:"Helvetica Neue",Helvetica,Arial,sans-serif; font-size:29px; font-weight:700;
  letter-spacing:-.03em; line-height:1; font-variant-numeric:tabular-nums}
.kpi span{font-size:12.5px; color:var(--ink-2); line-height:1.35}
.rank{display:flex; flex-direction:column; border:1px solid var(--line); border-radius:3px;
  overflow:hidden; background:var(--panel)}
.rk{display:grid; grid-template-columns:minmax(210px,2.1fr) 116px 96px 1fr 64px; gap:14px;
  align-items:center; padding:11px 16px; border-top:1px solid var(--line-2); font-size:13.5px}
.rk:first-child{border-top:none}
.rk.head{background:var(--bg); font-size:11px; font-weight:700; letter-spacing:.09em;
  text-transform:uppercase; color:var(--ink-3)}
.rk.is-client{background:var(--client-soft)}
.rk-name{display:flex; flex-direction:column; gap:1px; min-width:0}
.rk-name b{font-weight:650}
.rk-name small{color:var(--ink-3); font-size:11.5px}
.rk.is-client .rk-name b{color:var(--client)}
.vol{display:flex; align-items:center; gap:8px}
.vol-track{flex:1; height:7px; background:var(--line-2); border-radius:2px; overflow:hidden}
.vol-fill{display:block; height:100%; background:var(--data)}
.is-client .vol-fill{background:var(--client)}
.vol-n{width:26px; text-align:right; font-size:12.5px; color:var(--ink-2)}
.tag{display:inline-block; padding:2px 7px; border-radius:2px; font-size:11px; font-weight:650;
  background:var(--data-soft); color:var(--data); white-space:nowrap}
.tag.perto{background:var(--client-soft); color:var(--client)}
.pctv{font-size:12.5px; color:var(--ink-2)}
.two{display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:28px}
.panel{background:var(--panel); border:1px solid var(--line); border-radius:3px; padding:18px 20px;
  display:flex; flex-direction:column; gap:12px; box-shadow:var(--shadow)}
.bar-row{display:grid; grid-template-columns:minmax(120px,1.1fr) 2fr 30px; gap:10px;
  align-items:center; font-size:13px}
.bar-lab{color:var(--ink-2)}
.bar-track{height:9px; background:var(--line-2); border-radius:2px; overflow:hidden}
.bar-fill{display:block; height:100%; background:var(--data)}
.bar-fill.warm{background:var(--flag)}
.bar-num{text-align:right; font-size:12.5px; color:var(--ink-3); font-variant-numeric:tabular-nums}
.finds{display:flex; flex-direction:column; border:1px solid var(--line); border-radius:3px;
  background:var(--panel); overflow:hidden}
.find{display:grid; grid-template-columns:74px 1fr; gap:18px; padding:16px 18px; border-top:1px solid var(--line-2)}
.find:first-child{border-top:none}
.find-n{font-family:"Helvetica Neue",Helvetica,Arial,sans-serif; font-size:26px; font-weight:700;
  letter-spacing:-.03em; color:var(--data); font-variant-numeric:tabular-nums; line-height:1.1}
.find-n small{display:block; font-size:10.5px; font-weight:700; letter-spacing:.08em;
  text-transform:uppercase; color:var(--ink-3)}
.find.warm .find-n{color:var(--flag)}
.find-b{display:flex; flex-direction:column; gap:4px}
.find-b p{color:var(--ink-2); font-size:13.5px}
.comp{display:flex; flex-direction:column; gap:12px; padding-top:18px; border-top:1px solid var(--line)}
.comp-head{display:flex; flex-wrap:wrap; align-items:baseline; gap:10px}
.comp-head h3{font-size:16px}
.comp-head .meta{font-size:12.5px; color:var(--ink-3)}
.comp.is-client h3{color:var(--client)}
.grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(122px,1fr)); gap:10px}
.card{display:block; text-decoration:none; border:1px solid var(--line); border-radius:3px;
  overflow:hidden; background:var(--panel); transition:border-color .15s, transform .15s}
.card:hover,.card:focus-visible{border-color:var(--data); transform:translateY(-2px)}
.card:focus-visible{outline:2px solid var(--data); outline-offset:2px}
.card img{display:block; width:100%; aspect-ratio:9/16; object-fit:cover; background:var(--line-2)}
.card .cap{padding:6px 7px 7px; display:flex; flex-direction:column; gap:2px}
.card .cap b{font-size:10.5px; font-weight:650; line-height:1.25; color:var(--ink)}
.card .cap span{font-size:10px; color:var(--ink-3); font-variant-numeric:tabular-nums}
.noimg{aspect-ratio:9/16; display:flex; align-items:center; justify-content:center;
  background:var(--line-2); color:var(--ink-3); font-size:10.5px; padding:8px; text-align:center}
.blocos{display:flex; flex-direction:column; gap:20px}
.bloco{background:var(--panel); border:1px solid var(--line); border-radius:3px; overflow:hidden}
.bloco-head{padding:15px 20px; border-bottom:1px solid var(--line-2); display:flex;
  flex-direction:column; gap:4px}
.bloco-head h3{font-size:16.5px}
.bloco-head p{font-size:13.5px; color:var(--ink-2)}
.bloco.livre .bloco-head h3{color:var(--data)}
.bloco.falta .bloco-head h3{color:var(--flag)}
.item{display:grid; grid-template-columns:26px 1fr; gap:14px; padding:14px 20px;
  border-top:1px solid var(--line-2)}
.item:first-of-type{border-top:none}
.item-n{font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; color:var(--ink-3);
  padding-top:2px}
.item-b{display:flex; flex-direction:column; gap:4px}
.item-b b{font-size:14px; font-weight:650}
.item-b p{font-size:13.5px; color:var(--ink-2)}
.fonte{font-size:12px; color:var(--data); text-decoration:none; border-bottom:1px solid transparent;
  width:fit-content}
.fonte:hover,.fonte:focus-visible{border-bottom-color:var(--data)}
table{width:100%; border-collapse:collapse; font-size:13px}
.tblwrap{overflow-x:auto; border:1px solid var(--line); border-radius:3px; background:var(--panel)}
th,td{text-align:left; padding:9px 14px; border-top:1px solid var(--line-2); vertical-align:top}
th{background:var(--bg); font-size:11px; letter-spacing:.08em; text-transform:uppercase;
  color:var(--ink-3); border-top:none}
td.no{color:var(--ink-3)}
.foot{color:var(--ink-3); font-size:12.5px; border-top:1px solid var(--line); padding-top:16px;
  display:flex; flex-direction:column; gap:6px}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
@media (max-width:760px){
  .rk{grid-template-columns:1fr 78px; gap:8px; row-gap:6px}
  .rk .vol,.rk .pctv{grid-column:1/-1}
  .rk.head{display:none}}
"""


def gera(cfg, ads):
    cliente_page = cfg["pagina_cliente"]
    resumo = resumir(ads, cliente_page, cfg["perfis"])
    conc = [a for a in ads if a["page"] != cliente_page]
    if cliente_page in cfg["perfis"] and not any(r["cliente"] for r in resumo):
        pc = cfg["perfis"][cliente_page]
        resumo.append(dict(nome=pc["nome"], cliente=True, n=0, reg=pc["reg"], end=pc["end"], dist=pc["dist"], pctvid=0, peg=[], maxd=0, med=0, rows=[]))
    maxn = max(r["n"] for r in resumo)
    td = f"{cfg['thumbs_dir']}/mini" if os.path.isdir(f"{cfg['thumbs_dir']}/mini") else cfg["thumbs_dir"]
    tema = collections.Counter(a["tema"] for a in conc)
    pegv = collections.Counter(a["pegada"] for a in conc if a["formato"] == "VIDEO")
    nvid = sum(1 for a in conc if a["formato"] == "VIDEO")

    P = [f'<title>{E(cfg["titulo_aba"])}</title>', f"<style>{CSS}</style>", '<div class="wrap">']

    # capa
    P.append(f'<header class="sec"><span class="eyebrow">{E(cfg["eyebrow"])}</span>'
             f'<h1>{cfg["h1"]}</h1><p class="lede">{cfg["lede"]}</p><div class="kpis">')
    for k in cfg["kpis"]:
        P.append(f'<div class="kpi"><b>{E(str(k["valor"]))}</b><span>{k["texto"]}</span></div>')
    P.append("</div></header>")

    # ranking
    P.append('<section class="sec"><div class="sec-head"><span class="eyebrow">O campo</span>'
             f'<h2>{E(cfg["titulos"]["ranking"])}</h2></div><div class="rank">'
             '<div class="rk head"><span>Quem anuncia</span><span>Região</span><span>Distância</span>'
             '<span>Anúncios ativos</span><span>Vídeo</span></div>')
    for r in resumo:
        cls = " is-client" if r["cliente"] else ""
        tag = "tag perto" if r["reg"] in cfg.get("regioes_proximas", []) else "tag"
        P.append(f'<div class="rk{cls}"><span class="rk-name"><b>{E(r["nome"])}</b>'
                 f'<small>{E(r["end"])}</small></span><span><span class="{tag}">{E(r["reg"])}</span></span>'
                 f'<span class="mono" style="font-size:12.5px;color:var(--ink-2)">{E(r["dist"])}</span>'
                 f'<span class="vol"><span class="vol-track"><span class="vol-fill" '
                 f'style="width:{round(100*r["n"]/maxn)}%"></span></span>'
                 f'<span class="vol-n mono">{r["n"]}</span></span>'
                 f'<span class="pctv mono">{r["pctvid"]}%</span></div>')
    P.append("</div></section>")

    # temas e pegada
    temas_vis = [(k, v) for k, v in tema.most_common() if k != "Não identificado"]
    P.append(f'<section class="sec"><div class="sec-head"><span class="eyebrow">O que e como</span>'
             f'<h2>{E(cfg["titulos"]["temas"])}</h2></div><div class="two">'
             f'<div class="panel"><h3>Assunto do anúncio <span style="font-weight:400;color:var(--ink-3);'
             f'font-size:12.5px">· {len(conc)} anúncios</span></h3>{barras(temas_vis, len(conc))}'
             f'<p style="font-size:12px;color:var(--ink-3)">{cfg["notas"]["temas"]}</p></div>'
             f'<div class="panel"><h3>Estilo dos vídeos <span style="font-weight:400;color:var(--ink-3);'
             f'font-size:12.5px">· {nvid} vídeos</span></h3>{barras(pegv.most_common(), nvid, "warm")}'
             f'<p style="font-size:12px;color:var(--ink-3)">{cfg["notas"]["pegada"]}</p></div></div></section>')

    # achados
    P.append('<section class="sec"><div class="sec-head"><span class="eyebrow">Leituras</span>'
             f'<h2>{E(cfg["titulos"]["achados"])}</h2></div><div class="finds">')
    for a in cfg["achados"]:
        P.append(f'<div class="find{" warm" if a.get("destaque") else ""}">'
                 f'<div class="find-n">{E(str(a["numero"]))}<small>{E(a["unidade"])}</small></div>'
                 f'<div class="find-b"><h3>{E(a["titulo"])}</h3><p>{a["texto"]}</p></div></div>')
    P.append("</div></section>")

    # perfis indicados
    if cfg.get("indicados"):
        P.append('<section class="sec"><div class="sec-head">'
                 '<span class="eyebrow">Os perfis apontados pela clínica</span>'
                 f'<h2>{E(cfg["titulos"]["indicados"])}</h2></div><div class="tblwrap"><table>'
                 "<tr><th>Perfil</th><th>Quem é</th><th>Onde atende</th><th>Anuncia hoje</th></tr>")
        for i in cfg["indicados"]:
            cls = "" if i["anuncia"] else ' class="no"'
            P.append(f'<tr><td>{E(i["perfil"])}</td><td>{E(i["quem"])}</td><td>{E(i["onde"])}</td>'
                     f'<td{cls}>{E(i["status"])}</td></tr>')
        P.append(f'</table></div><p style="font-size:13px;color:var(--ink-2)">{cfg["notas"]["indicados"]}</p></section>')

    # galeria
    P.append('<section class="sec"><div class="sec-head"><span class="eyebrow">Os anúncios</span>'
             f'<h2>{E(cfg["titulos"]["galeria"])}</h2>'
             f'<p style="font-size:13.5px;color:var(--ink-2)">{cfg["notas"]["galeria"]}</p></div>')
    for r in resumo:
        if not r["rows"]: continue
        cls = " is-client" if r["cliente"] else ""
        peg = " · ".join(f"{k} ({v})" for k, v in r["peg"]) or "sem vídeo"
        P.append(f'<div class="comp{cls}"><div class="comp-head"><h3>{E(r["nome"])}</h3>'
                 f'<span class="meta">{E(r["reg"])} · {r["n"]} anúncios · {r["pctvid"]}% vídeo · '
                 f'mediana {r["med"]} dias no ar · mais antigo {r["maxd"]} dias</span></div>'
                 f'<div class="comp-head"><span class="meta">Estilo: {E(peg)}{(" · Mostrando os " + str(CAP_GALERIA) + " anúncios há mais tempo no ar, de " + str(r["n"]) + " ativos") if r["n"] > CAP_GALERIA else ""}</span></div><div class="grid">')
        for a in r["rows"][:CAP_GALERIA]:
            b64 = img64(td, a["ad_id"])
            vis = (f'<img src="{b64}" alt="Anúncio de {E(r["nome"])}: {E(a["tema"])}" loading="lazy">'
                   if b64 else '<div class="noimg">sem capa</div>')
            lab = a["pegada"] if a["formato"] == "VIDEO" else a["formato"].title()
            P.append(f'<a class="card" href="{a["link"]}" target="_blank" rel="noopener">{vis}'
                     f'<span class="cap"><b>{E(a["tema"])}</b>'
                     f'<span>{E(lab)} · {a["dias"]}d</span></span></a>')
        P.append("</div></div>")
    P.append("</section>")

    # concorrente de outros servicos (opcional): rede fora do foco com 100+ anuncios no raio (regra de 06/10/2026)
    if cfg.get("outros"):
        o = cfg["outros"]; ads_o = json.load(open(o["arquivo"]))
        rows_o = sorted(ads_o, key=lambda x: -(x["dias"] or 0))
        dias_o = [a["dias"] for a in ads_o if a["dias"] is not None]
        vids_o = [a for a in ads_o if a["formato"] == "VIDEO"]
        peg_o = " · ".join(f"{k} ({v})" for k, v in collections.Counter(a["pegada"] for a in vids_o).most_common(2)) or "sem vídeo"
        P.append(f'<section class="sec"><div class="sec-head"><span class="eyebrow">{E(o["eyebrow"])}</span>'
                 f'<h2>{E(o["titulo"])}</h2><p style="font-size:13.5px;color:var(--ink-2)">{o["intro"]}</p></div>')
        if o.get("kpis"):
            P.append('<div class="kpis">')
            for k in o["kpis"]:
                P.append(f'<div class="kpi"><b>{E(str(k["valor"]))}</b><span>{k["texto"]}</span></div>')
            P.append("</div>")
        if o.get("leitura"):
            P.append(f'<p style="font-size:14.5px;color:var(--ink-2);max-width:72ch;margin:14px 0 6px">{o["leitura"]}</p>')
        nome_o = rows_o[0]["nome"] if rows_o else o["titulo"]
        P.append(f'<div class="comp"><div class="comp-head"><h3>{E(nome_o)}</h3>'
                 f'<span class="meta">{E(rows_o[0].get("reg", "") if rows_o else "")} · {E(rows_o[0].get("dist", "") if rows_o else "")} · {len(ads_o)} anúncios · {round(100*len(vids_o)/max(1,len(ads_o)))}% vídeo · '
                 f'mediana {int(statistics.median(dias_o)) if dias_o else 0} dias no ar · mais antigo {max(dias_o) if dias_o else 0} dias</span></div>'
                 f'<div class="comp-head"><span class="meta">Estilo: {E(peg_o)}</span></div><div class="grid">')
        for a in rows_o[:CAP_GALERIA]:
            b64 = img64(td, a["ad_id"])
            vis = (f'<img src="{b64}" alt="Anúncio da {E(nome_o)}: {E(a["tema"])}" loading="lazy">' if b64 else '<div class="noimg">sem capa</div>')
            lab = a["pegada"] if a["formato"] == "VIDEO" else a["formato"].title()
            P.append(f'<a class="card" href="{a["link"]}" target="_blank" rel="noopener">{vis}'
                     f'<span class="cap"><b>{E(a["tema"])}</b><span>{E(lab)} · {a["dias"]}d</span></span></a>')
        P.append("</div></div>")
        if o.get("nota"):
            P.append(f'<p style="font-size:13px;color:var(--ink-2)">{o["nota"]}</p>')
        P.append("</section>")

    # google meu negocio (opcional)
    if cfg.get("gmn"):
        g = cfg["gmn"]
        P.append('<section class="sec"><div class="sec-head">'
                 '<span class="eyebrow">Google Meu Negócio</span>'
                 f'<h2>{E(g["titulo"])}</h2><p style="font-size:13.5px;color:var(--ink-2)">{g["intro"]}</p></div>')
        if g.get("kpis"):
            P.append('<div class="kpis">')
            for k in g["kpis"]:
                P.append(f'<div class="kpi"><b>{E(str(k["valor"]))}</b><span>{k["texto"]}</span></div>')
            P.append("</div>")
        P.append('<div class="tblwrap"><table><tr><th>Clínica ou profissional</th><th>Região</th>'
                 '<th>Distância</th><th>Google</th><th>Instagram</th><th>Anuncia hoje</th></tr>')
        for l in g["linhas"]:
            cls = ' class="is-client"' if l.get("cliente") else ""
            anun = ("<b>Sim</b>" if l["anuncia"] else '<span style="color:var(--ink-3)">Não</span>')
            ig = (f'<a href="https://instagram.com/{E(l["ig"])}" target="_blank" rel="noopener">@{E(l["ig"])}</a>'
                  f'<br><span style="color:var(--ink-3)">{E(l["seguidores"])}</span>') if l.get("ig") else \
                 '<span style="color:var(--ink-3)">não localizado</span>'
            P.append(f'<tr{cls}><td><b>{E(l["nome"])}</b></td><td>{E(l["reg"])}</td>'
                     f'<td class="mono">{E(l["km"])}</td>'
                     f'<td class="mono">{E(l["google"])}</td><td>{ig}</td><td>{anun}</td></tr>')
        P.append("</table></div>")
        for n in g.get("notas", []):
            P.append(f'<p style="font-size:13px;color:var(--ink-2)">{n}</p>')
        P.append("</section>")

    # analise final
    P.append('<section class="sec"><div class="sec-head"><span class="eyebrow">Análise</span>'
             f'<h2>{E(cfg["titulos"]["analise"])}</h2>'
             f'<p style="font-size:13.5px;color:var(--ink-2)">{cfg["notas"]["analise"]}</p></div>'
             '<div class="blocos">')
    for b in cfg["analise"]:
        P.append(f'<div class="bloco {b.get("estilo","")}"><div class="bloco-head">'
                 f'<h3>{E(b["titulo"])}</h3><p>{b["resumo"]}</p></div>')
        for i, it in enumerate(b["itens"], 1):
            fonte = ""
            if it.get("fonte_url"):
                fonte = (f'<a class="fonte" href="{it["fonte_url"]}" target="_blank" rel="noopener">'
                         f'↗ {E(it["fonte_label"])}</a>')
            P.append(f'<div class="item"><span class="item-n">{i:02d}</span><div class="item-b">'
                     f'<b>{E(it["titulo"])}</b><p>{it["texto"]}</p>{fonte}</div></div>')
        P.append("</div>")
    P.append("</div></section>")

    P.append('<footer class="foot">' + "".join(f"<span>{t}</span>" for t in cfg["rodape"]) + "</footer></div>")

    open(cfg["saida"], "w").write("\n".join(P))
    print("gerado:", cfg["saida"], round(os.path.getsize(cfg["saida"]) / 1e6, 2), "MB")


if __name__ == "__main__":
    cfg, ads = carrega(sys.argv[1], sys.argv[2])
    if "--folha" in sys.argv:
        folha_contato(cfg, ads)
    else:
        gera(cfg, ads)
