#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Classifica os anuncios crus da Biblioteca do Meta.

  extrai.py coleta.json anuncios.json --nicho odonto [--ref 2026-08-19]

Sai um JSON com: page, ad_id, tema, formato, destino, inicio, dias, variacoes,
preco, copy, thumb, video, link. Nichos: ver referencia/taxonomias.md
"""
import argparse, ast, collections, datetime, json, re

NICHOS = {
 "dermato": [
   ("Botox / toxina",        r"botox|toxina botul|botul[ií]nica|rugas? de express|linhas de express|p[ée] de galinha"),
   ("Preenchimento",         r"preenchimento|[áa]cido hialur|skin ?booster|labial|olheira"),
   ("Flacidez / lifting",    r"flacidez|bioestimul|lifting|ultraformer|fios? de sustenta|fio de pdo|col[áa]geno|papada|sculptra|ellanse|firmeza"),
   ("Pele / manchas / acne", r"melasma|mancha|acne|espinha|peeling|poro|skincare|vi[çc]o|textura da pele|cravos|oleosidade|clareamento"),
   ("Laser / tecnologias",   r"laser|co2|fotona|lavieen|luz pulsada|criofrequ|radiofrequ|microagulhamento|ultrassom dermatol|coolsculpt|criolip"),
   ("Capilar / tricologia",  r"cabelo|capilar|calv[íi]cie|queda de fio|alopec|transplante capilar|tricolog"),
   ("Blefaroplastia",        r"blefaroplastia|p[áa]lpebra"),
   ("Corporal / emagrec.",   r"emagrec|gordura localizada|lipedema|celulite|corporal|abd[ôo]men"),
   ("Dermatologia clínica",  r"c[âa]ncer de pele|dermatoscop|verruga|micose|psor[íi]ase|dermatite|melanoma|pinta"),
 ],
 "odonto": [
   ("Implante",              r"implante"),
   ("Protocolo / carga imediata", r"protocolo|carga imediata|dentes fixos"),
   ("Prótese / dentadura",   r"pr[óo]tese|dentadura|flex[íi]vel"),
   ("Estética / lentes",     r"lente|faceta|resina|clareamento|harmoniza"),
   ("Ortodontia / aparelho", r"aparelho|ortodont|alinhador|invisalign"),
   ("Clínico geral",         r"limpeza|canal|extra[çc][ãa]o|c[áa]rie"),
 ],
 "vascular": [
   ("Varizes / escleroterapia", r"varizes?|vasinho|escleroterapia|espuma"),
   ("Laser vascular",        r"laser"),
   ("Trombose / circulação", r"trombose|circula[çc][ãa]o|incha[çc]o|perna pesada"),
   ("Check-up vascular",     r"doppler|ultrassom|check[- ]?up"),
 ],
 "plastica": [
   ("Mamoplastia",           r"mama|mamopl|pr[óo]tese de silicone|silicone"),
   ("Abdominoplastia",       r"abdominopl|abd[ôo]men"),
   ("Lipoaspiração",         r"lipo|lipoaspira"),
   ("Rinoplastia",           r"rinoplastia|nariz"),
   ("Facial / lifting",      r"lifting|deep plane|blefaro|face"),
 ],
}
INSTITUCIONAL = (r"seja bem[- ]vind|siga (meu|o) perfil|conhe[çc]a meu trabalho|sobre mim|"
                 r"minha hist[óo]ria|agende sua consulta|marque sua avalia")

PEGADAS = [
 ("Depoimento de paciente",     r'^\s*[“"«]|”\s*@|"\s*@|\bfa[çc]o com (a|o) dr|n[ãa]o troco a|minha fada madrinha|'
                                r'me sinto outra|acompanhei a trajet[óo]ria|realmente eu rejuvenesci|depoimento'),
 ("Caso real / antes e depois", r"\besse (paciente|caso)\b|atendi (uma|um)|minha paciente|essa paciente|"
                                r"acompanhe esse caso|foram implantad|antes e depois|evolu[çc][ãa]o do tratamento|"
                                r"uma paciente (me disse|convive|com hist)|ela olhou no espelho"),
 ("Oferta / promoção / pacote", r"neste m[êe]s de|no m[êe]s d|campanha .* do m[êe]s|voc[êe] ganha|ganha \w+ ?booster|"
                                r"pacote|clube do|vagas (s[ãa]o )?limitadas|valores especiais|beauty day|"
                                r"cart[ãa]o presente|men[u] de sess|condi[çc][õo]es especiais|promo[çc]"),
 ("Quebra de objeção / mito",   r"\bmito|verdade\b|n[ãa]o é (culpa|drama|frescura|s[óo])|o problema n[ãa]o é|"
                                r"n[ãa]o existe (milagre|f[óo]rmula m[áa]gica)|ser[áa] que|desvendando|"
                                r"realmente funciona|n[ãa]o deve ser ignorad|n[ãa]o deve ser normalizada|"
                                r"ainda gera muitas d[úu]vidas|n[ãa]o é “?s[óo] uma fase|n[ãa]o é apenas"),
 ("Emocional / storytelling",   r"\bhist[óo]ria\b|da s[ée]rie|bodas de ouro|meus pais|minha m[ãa]e|meu pai|"
                                r"autoestima|nasceu de algo|por tr[áa]s de cada|ess[êe]ncia|jornada|se redescobre"),
 ("Tecnologia / equipamento",   r"ultraformer|linear z|oligio|oligo x|visalift|fotona|laser de co2|hifu|"
                                r"ultrassom microfocado|radiofrequ|lavieen|coopeel|luz intensa pulsada|"
                                r"depila[çc][ãa]o a laser|ultrassom dermatol|fios? (de )?(pdo|aptos)|"
                                r"tecnologia coreana|nova tecnologia|equipamento|aparelho"),
 ("Didático / explicativo",     r"nesse v[íi]deo|neste v[íi]deo|no v[íi]deo|te explico|vamos falar sobre|voc[êe] sabe|"
                                r"qual a diferen[çc]a|qual [ée] o (melhor|seu)|entenda|explico|passo a passo|"
                                r"checklist|dicas|guia|arraste|carrossel|o que (é|faz)|por que|anota"),
 ("Institucional / convite",    r"agende|marque|siga (meu|o) perfil|clique no link|link na bio|"
                                r"toque em saiba mais|conhe[çc]a|link da bio"),
]


def snap(a):
    s = a.get("snapshot")
    if isinstance(s, str):
        try: return ast.literal_eval(s)
        except Exception: return {}
    return s or {}


def texto(s):
    partes = []
    b = s.get("body")
    partes.append(b.get("text") or "" if isinstance(b, dict) else (b or ""))
    for k in ("title", "caption", "linkDescription"):
        if isinstance(s.get(k), str): partes.append(s[k])
    for c in (s.get("cards") or []):
        for k in ("body", "title", "caption", "linkDescription"):
            if isinstance(c.get(k), str): partes.append(c[k])
    return " \n ".join(p for p in partes if p)


def tema(t, regras):
    tl = (t or "").lower()
    for nome, rx in regras:
        if re.search(rx, tl, re.I): return nome
    if re.search(INSTITUCIONAL, tl, re.I): return "Institucional / marca"
    return "Não identificado"


def formato(s):
    df = (s.get("displayFormat") or "").upper()
    cards = s.get("cards") or []
    tem_video = bool(s.get("videos")) or any(c.get("videoHdUrl") or c.get("videoSdUrl") for c in cards)
    if df == "DCO": return "DCO"
    if df in ("CAROUSEL", "MULTI_IMAGES", "DPA") or len(cards) > 1: return "CARROSSEL"
    if tem_video: return "VIDEO"
    if s.get("images") or cards: return "IMAGE"
    return df or "-"


def destino(s):
    u = (s.get("linkUrl") or "")
    for c in (s.get("cards") or []): u = u or (c.get("linkUrl") or "")
    u, cta = u.lower(), (s.get("ctaType") or "").upper()
    if "whatsapp" in u or "wa.me" in u or "WHATSAPP" in cta: return "WhatsApp"
    if "instagram.com" in u: return "Instagram"
    if "m.me" in u or "messenger" in u: return "Messenger"
    return "Site/LP" if u.startswith("http") else "-"


def pegada(copy, fmt):
    t = (copy or "").strip()
    if fmt != "VIDEO": return "-"
    if len(t) < 15: return "Sem copy (só a peça)"
    for nome, rx in PEGADAS:
        if re.search(rx, t, re.I): return nome
    return "Didático / explicativo" if len(t) > 180 else "Institucional / convite"


def midia(s):
    for v in (s.get("videos") or []):
        if v.get("videoHdUrl") or v.get("videoSdUrl"):
            return v.get("videoHdUrl") or v.get("videoSdUrl"), v.get("videoPreviewImageUrl")
    for c in (s.get("cards") or []):
        if c.get("videoHdUrl") or c.get("videoSdUrl"):
            return c.get("videoHdUrl") or c.get("videoSdUrl"), c.get("videoPreviewImageUrl") or c.get("resizedImageUrl")
    imgs = s.get("images") or []
    if imgs: return "", imgs[0].get("resizedImageUrl")
    cards = s.get("cards") or []
    if cards: return "", cards[0].get("resizedImageUrl")
    return "", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada"); ap.add_argument("saida")
    ap.add_argument("--nicho", default="odonto")
    ap.add_argument("--ref", default=str(datetime.date.today()))
    args = ap.parse_args()
    regras = NICHOS[args.nicho]
    ref = datetime.date.fromisoformat(args.ref)

    itens = json.load(open(args.entrada))
    if isinstance(itens, dict): itens = [itens]
    out, vistos = [], set()
    for a in itens:
        aid = a.get("adArchiveID") or a.get("adArchiveId")
        if not aid or aid in vistos: continue
        vistos.add(aid)
        s = snap(a); t = texto(s); fmt = formato(s)
        try:
            d0 = datetime.date.fromisoformat((a.get("startDateFormatted") or "")[:10]); dias = (ref - d0).days
        except Exception:
            d0, dias = None, None
        video, thumb = midia(s)
        out.append(dict(
            page=s.get("pageName") or a.get("pageName"), page_id=a.get("pageId"), ad_id=aid,
            tema=tema(t, regras), formato=fmt, destino=destino(s),
            inicio=str(d0) if d0 else "", dias=dias, variacoes=a.get("collationCount") or 1,
            preco=" / ".join(dict.fromkeys(re.findall(r"R\$\s?\d[\d\.\,]*", t)))[:60],
            copy=re.sub(r"\s+", " ", t).strip(), pegada=pegada(t, fmt),
            video=video or "", thumb=thumb or "",
            link=f"https://www.facebook.com/ads/library/?id={aid}"))
    json.dump(out, open(args.saida, "w"), ensure_ascii=False, indent=1)
    for p, n in collections.Counter(x["page"] for x in out).most_common():
        print(f"{n:4}  {p}")
    print("TOTAL", len(out))


if __name__ == "__main__":
    main()
