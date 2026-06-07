import os
import json
import random
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

BRT = ZoneInfo("America/Sao_Paulo")

def log(msg):
    print(f"[{datetime.now(BRT).strftime('%H:%M:%S')}] {msg}", flush=True)

# ── COLETA DE DADOS ───────────────────────────────────────────────────────────

def buscar_fear_greed():
    try:
        r = requests.get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
                         timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200 and r.text.strip():
            d = r.json()
            v = round(d["fear_and_greed"]["score"])
            log(f"Fear & Greed (CNN): {v}")
            return {"value": v, "label": d["fear_and_greed"]["rating"]}
    except Exception:
        pass
    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=10,
                         headers={"User-Agent": "Mozilla/5.0"})
        d = r.json()
        v = int(d["data"][0]["value"])
        label = d["data"][0]["value_classification"]
        log(f"Fear & Greed (alt): {v} ({label})")
        return {"value": v, "label": label}
    except Exception as e:
        log(f"AVISO Fear&Greed: {e}")
        return {"value": None, "label": "N/A"}

def buscar_yahoo(symbol, nome):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        d = r.json()
        closes = [c for c in d["chart"]["result"][0]["indicators"]["quote"][0]["close"] if c]
        preco = round(closes[-1], 2)
        var = round(((closes[-1] / closes[-2]) - 1) * 100, 2) if len(closes) >= 2 else 0.0
        log(f"{nome}: {preco} ({var:+.2f}%)")
        return {"price": preco, "change_pct": var}
    except Exception as e:
        log(f"AVISO {nome}: {e}")
        return {"price": None, "change_pct": None}

# Eventos econômicos fixos de alto impacto para identificar no texto de notícias
EVENTOS_CHAVE = [
    "Nonfarm Payroll", "NFP", "Payroll", "CPI", "Core CPI", "PCE", "Core PCE",
    "FOMC", "Fed", "Powell", "GDP", "Retail Sales", "ISM", "PMI", "Jobless Claims",
    "IPCA", "SELIC", "COPOM", "PIB", "IGP", "Focus", "Caged", "Balança Comercial",
    "Taxa de Desemprego", "Confiança", "Ata do", "Decisão de juros",
]

AGENDA_SEMANAL = {
    0: [{"time": "10:00", "currency": "USD", "event": "ISM Manufacturing PMI", "impact": "medio"}],
    1: [{"time": "10:00", "currency": "USD", "event": "JOLTS Job Openings", "impact": "medio"}],
    2: [{"time": "14:00", "currency": "USD", "event": "FOMC Minutes / Beige Book", "impact": "alto"}],
    3: [{"time": "08:30", "currency": "USD", "event": "Initial Jobless Claims", "impact": "medio"}],
    4: [
        {"time": "08:30", "currency": "USD", "event": "Non-Farm Payrolls (NFP)", "impact": "alto"},
        {"time": "08:30", "currency": "USD", "event": "Unemployment Rate", "impact": "alto"},
    ],
}

KEYWORDS_AGENDA = {
    "PAYROLL": ("08:30", "USD", "Non-Farm Payrolls (NFP)", "alto"),
    "NFP": ("08:30", "USD", "Non-Farm Payrolls (NFP)", "alto"),
    "CPI": ("08:30", "USD", "CPI — Inflação EUA", "alto"),
    "FOMC": ("14:00", "USD", "Decisão FOMC / Fed", "alto"),
    "COPOM": ("18:00", "BRL", "Decisão COPOM — Selic", "alto"),
    "IPCA": ("09:00", "BRL", "IPCA — Inflação Brasil", "alto"),
    "CAGED": ("09:00", "BRL", "CAGED — Empregos Formais", "medio"),
    "PIB": ("09:00", "BRL", "PIB Brasil", "alto"),
    "GDP": ("08:30", "USD", "GDP — PIB EUA", "alto"),
    "PMI": ("09:45", "USD", "PMI Composto", "medio"),
    "JOBLESS": ("08:30", "USD", "Initial Jobless Claims", "medio"),
    "JOLTS": ("10:00", "USD", "JOLTS — Vagas de Emprego", "medio"),
    "ADP": ("08:15", "USD", "ADP Payroll Privado", "medio"),
    "PPI": ("08:30", "USD", "PPI — Preços ao Produtor", "medio"),
    "RETAIL": ("08:30", "USD", "Retail Sales — Varejo EUA", "medio"),
}

def buscar_agenda():
    """Tenta ForexFactory, fallback inteligente via notícias + dia da semana."""
    hoje = datetime.now(BRT)
    eventos = []

    # Tenta ForexFactory
    try:
        from bs4 import BeautifulSoup
        url = f"https://www.forexfactory.com/calendar?day={hoje.strftime('%b%d.%Y').lower()}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
        r = requests.get(url, timeout=15, headers=headers)
        soup = BeautifulSoup(r.text, "html.parser")
        hora_atual = ""
        for row in soup.select("tr.calendar__row"):
            h = row.select_one(".calendar__time")
            if h and h.text.strip():
                hora_atual = h.text.strip()
            imp = row.select_one(".calendar__impact span")
            impacto = ""
            if imp:
                cls = " ".join(imp.get("class", []))
                if "high" in cls: impacto = "alto"
                elif "medium" in cls: impacto = "medio"
            moeda_el = row.select_one(".calendar__currency")
            moeda = moeda_el.text.strip() if moeda_el else ""
            ev_el = row.select_one(".calendar__event-title")
            evento = ev_el.text.strip() if ev_el else ""
            if evento and moeda in ["USD", "BRL", "EUR"] and impacto in ["alto", "medio"]:
                eventos.append({"time": hora_atual, "currency": moeda, "event": evento, "impact": impacto})
        if eventos:
            log(f"Agenda FF: {len(eventos)} eventos")
            return eventos[:12]
    except Exception as e:
        log(f"AVISO FF: {e}")

    # Fallback: notícias + dia da semana
    log("FF bloqueado — usando fallback inteligente...")
    import feedparser
    noticias_upper = []
    for feed_url in ["https://br.investing.com/rss/news_25.rss", "https://br.investing.com/rss/news_14.rss",
                     "https://feeds.marketwatch.com/marketwatch/marketpulse/"]:
        try:
            feed = feedparser.parse(feed_url)
            for e in feed.entries[:10]:
                noticias_upper.append(e.get("title", "").upper())
        except Exception:
            pass

    encontrados = set()
    for noticia in noticias_upper:
        for kw, (hora, moeda, nome, impacto) in KEYWORDS_AGENDA.items():
            if kw in noticia and nome not in encontrados:
                encontrados.add(nome)
                eventos.append({"time": hora, "currency": moeda, "event": nome, "impact": impacto})

    # SEMPRE adiciona eventos típicos do dia da semana (seg-sex)
    dia = hoje.weekday()
    for ev in AGENDA_SEMANAL.get(dia, []):
        if ev["event"] not in {e["event"] for e in eventos}:
            eventos.append(ev)

    if not eventos:
        log("Agenda: sem eventos identificados hoje")
    else:
        log(f"Agenda fallback: {len(eventos)} eventos")
    return eventos[:10]

def extrair_eventos_das_noticias(noticias):
    """Identifica eventos econômicos importantes nas manchetes do dia."""
    eventos = []
    for noticia in noticias:
        n_upper = noticia.upper()
        for ev in EVENTOS_CHAVE:
            if ev.upper() in n_upper:
                eventos.append({
                    "time": "Hoje",
                    "currency": "BRL" if any(x in n_upper for x in ["SELIC","COPOM","IPCA","PIB BR","CAGED"]) else "USD",
                    "event": noticia[:80],
                    "impact": "alto"
                })
                break
    return eventos[:6]

def buscar_noticias():
    """Coleta notícias de Reuters, Bloomberg e Investing via RSS/Google News."""
    import feedparser
    FEEDS = [
        # Reuters via Google News (gratuito, tempo real)
        ("Reuters", "https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com/business&hl=pt-BR&gl=BR&ceid=BR:pt-419"),
        ("Reuters Mercados", "https://news.google.com/rss/search?q=when:24h+site:reuters.com+mercado+OR+economia+OR+juros+OR+bolsa&hl=pt-BR&gl=BR&ceid=BR:pt-419"),
        # Bloomberg via Google News
        ("Bloomberg", "https://news.google.com/rss/search?q=when:24h+allinurl:bloomberg.com&hl=pt-BR&gl=BR&ceid=BR:pt-419"),
        # Bloomberg Technology RSS direto
        ("Bloomberg Tech", "https://feeds.bloomberg.com/technology/news.rss"),
        # Investing.com Brasil
        ("Investing BR", "https://br.investing.com/rss/news_25.rss"),
        ("Investing Global", "https://br.investing.com/rss/news_14.rss"),
    ]

    noticias = []
    contagem = {}
    for nome, url in FEEDS:
        try:
            feed = feedparser.parse(url)
            count = 0
            for e in feed.entries[:5]:
                t = e.get("title", "").strip()
                # Remove prefixos de fonte do Google News (ex: "Reuters - ")
                for prefixo in ["Reuters - ", "Bloomberg - ", "Reuters:", "Bloomberg:"]:
                    if t.startswith(prefixo):
                        t = t[len(prefixo):].strip()
                if t and t not in noticias:
                    noticias.append(t)
                    count += 1
            contagem[nome] = count
        except Exception as ex:
            contagem[nome] = f"ERRO: {ex}"
            continue

    log(f"Noticias: {len(noticias)} itens — " + " | ".join(f"{k}:{v}" for k,v in contagem.items()))
    return noticias[:15]

def buscar_juros_br():
    """Busca taxa Selic atual via API do Banco Central do Brasil."""
    try:
        # API pública do BCB — série 432 = Taxa Selic
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
        r = requests.get(url, timeout=10)
        data = r.json()
        selic = float(data[0]["valor"].replace(",", "."))
        log(f"Selic: {selic}% a.a.")
        return selic
    except Exception as e:
        log(f"AVISO Selic: {e}")
        return None

def buscar_di_futuro():
    """DI futuro curto prazo via Yahoo Finance (proxy: juros EUA 10Y para comparação)."""
    try:
        # Treasury 10Y como referência global de juros
        us10y = buscar_yahoo("^TNX", "US10Y")
        br_etf = buscar_yahoo("EWZ", "EWZ-BR")  # ETF Brasil como proxy de risco BR
        return {"us10y": us10y, "ewz": br_etf}
    except Exception as e:
        log(f"AVISO DI/Juros: {e}")
        return {"us10y": {"price": None, "change_pct": None}, "ewz": {"price": None, "change_pct": None}}

# ── ANÁLISE E NARRATIVA ───────────────────────────────────────────────────────

def classificar_fg(v):
    if v is None: return "indefinido", "neutro"
    if v <= 20:  return "Medo Extremo", "baixista"
    if v <= 40:  return "Medo", "levemente baixista"
    if v <= 60:  return "Neutro", "neutro"
    if v <= 80:  return "Ganância", "levemente altista"
    return "Ganância Extrema", "altista"

def classificar_vix(v):
    if v is None: return "indefinido", "neutro"
    if v < 15:  return "baixa", "altista"
    if v < 20:  return "moderada", "neutro"
    if v < 30:  return "elevada", "levemente baixista"
    return "muito alta", "baixista"

def sinal(v):
    if v is None: return "estável"
    return "em alta" if v > 0 else "em queda" if v < 0 else "estável"

def sinal_forte(v, limiar=1.0):
    if v is None: return False
    return abs(v) >= limiar

def calcular_vies(fg, dxy, vix, ibov, sp, usd):
    score = 0
    # Fear & Greed
    if fg.get("value") is not None:
        v = fg["value"]
        if v <= 20: score -= 3
        elif v <= 40: score -= 1
        elif v >= 60: score += 1
        elif v >= 80: score += 3
    # VIX
    if vix.get("change_pct") is not None:
        if vix["change_pct"] > 15: score -= 3
        elif vix["change_pct"] > 5: score -= 1
        elif vix["change_pct"] < -5: score += 1
    # DXY (inverso para emergentes)
    if dxy.get("change_pct") is not None:
        if dxy["change_pct"] > 0.5: score -= 2
        elif dxy["change_pct"] > 0.2: score -= 1
        elif dxy["change_pct"] < -0.5: score += 2
        elif dxy["change_pct"] < -0.2: score += 1
    # S&P500
    if sp.get("change_pct") is not None:
        if sp["change_pct"] < -1.5: score -= 2
        elif sp["change_pct"] < -0.5: score -= 1
        elif sp["change_pct"] > 1.5: score += 2
        elif sp["change_pct"] > 0.5: score += 1
    # IBOV tendência
    if ibov.get("change_pct") is not None:
        if ibov["change_pct"] < -1: score -= 1
        elif ibov["change_pct"] > 1: score += 1

    if score <= -3: return "Baixista", "baixista"
    if score == -2: return "Levemente Baixista", "baixista"
    if score == -1: return "Levemente Baixista", "baixista"
    if score == 0:  return "Neutro", "neutro"
    if score == 1:  return "Levemente Altista", "altista"
    if score == 2:  return "Levemente Altista", "altista"
    return "Altista", "altista"

def gerar_contexto_global(dxy, vix, sp, nq, usd, fg, gold=None, oil=None, btc=None):
    fg_label, _ = classificar_fg(fg.get("value"))
    vix_class, _ = classificar_vix(vix.get("price"))

    # Narrativa DXY
    if dxy.get("change_pct") is not None:
        if dxy["change_pct"] > 0.5:
            dxy_txt = f"O índice do dólar (DXY) avançou {dxy['change_pct']:+.2f}%, sinalizando fortalecimento da moeda americana e aumentando a pressão sobre moedas emergentes, incluindo o real."
        elif dxy["change_pct"] < -0.5:
            dxy_txt = f"O DXY recuou {dxy['change_pct']:+.2f}%, aliviando a pressão sobre emergentes e abrindo espaço para valorização do real e de ativos de risco."
        else:
            dxy_txt = f"O DXY operou relativamente estável ({dxy['change_pct']:+.2f}%), sem grandes desequilíbrios no câmbio global."
    else:
        dxy_txt = "O DXY não apresentou variação significativa."

    # Narrativa S&P/Nasdaq
    if sp.get("change_pct") is not None and nq.get("change_pct") is not None:
        if sp["change_pct"] < -1.5:
            bolsas_txt = (f"As bolsas americanas encerraram em forte queda, com S&P 500 em {sp['change_pct']:+.2f}% "
                         f"e Nasdaq em {nq['change_pct']:+.2f}%. O movimento reflete aversão a risco elevada e tende "
                         f"a contaminar negativamente a abertura brasileira.")
        elif sp["change_pct"] < -0.3:
            bolsas_txt = (f"Wall Street fechou no vermelho — S&P 500 em {sp['change_pct']:+.2f}% e Nasdaq em "
                         f"{nq['change_pct']:+.2f}% —, criando um ambiente de cautela para os mercados emergentes.")
        elif sp["change_pct"] > 1.5:
            bolsas_txt = (f"As bolsas americanas tiveram sessão positiva, com S&P 500 em {sp['change_pct']:+.2f}% "
                         f"e Nasdaq em {nq['change_pct']:+.2f}%, favorecendo o apetite por risco globalmente.")
        elif sp["change_pct"] > 0.3:
            bolsas_txt = (f"Wall Street fechou em alta moderada — S&P 500 em {sp['change_pct']:+.2f}% e Nasdaq em "
                         f"{nq['change_pct']:+.2f}% —, mantendo o ambiente de risk-on.")
        else:
            bolsas_txt = (f"As bolsas americanas tiveram sessão mista ou flat (S&P 500 {sp['change_pct']:+.2f}%, "
                         f"Nasdaq {nq['change_pct']:+.2f}%), sem direcionamento claro para os ativos de risco.")
    else:
        bolsas_txt = "Dados das bolsas americanas indisponíveis no momento."

    # Narrativa VIX + Fear & Greed
    if vix.get("price") is not None:
        if vix["change_pct"] > 15:
            vix_txt = (f"O VIX disparou {vix['change_pct']:+.2f}% para {vix['price']:.1f} pontos, indicando "
                      f"volatilidade {vix_class} — sinal de estresse no mercado que exige cautela nas posições.")
        elif vix["change_pct"] > 5:
            vix_txt = (f"O VIX subiu {vix['change_pct']:+.2f}% para {vix['price']:.1f} pontos, com volatilidade "
                      f"{vix_class}. O mercado demonstra nervosismo crescente.")
        elif vix["change_pct"] < -5:
            vix_txt = (f"O VIX recuou {vix['change_pct']:+.2f}% para {vix['price']:.1f} pontos, com volatilidade "
                      f"{vix_class}. O ambiente está mais favorável ao risco.")
        else:
            vix_txt = f"O VIX permanece em {vix['price']:.1f} pontos, com volatilidade {vix_class}."
    else:
        vix_txt = ""

    fg_val = fg.get("value")
    if fg_val is not None:
        fg_txt = (f"O índice Fear & Greed marca {fg_val} pontos — zona de \"{fg_label}\" — "
                 f"{'sugerindo que o mercado precifica risco excessivo e pode estar próximo de um ponto de reversão técnica.' if fg_val <= 25 else 'refletindo o sentimento atual dos investidores.'}")
    else:
        fg_txt = ""

    # Commodities
    comod_partes = []
    if gold and gold.get("price"):
        direcao = "subiu" if gold["change_pct"] >= 0 else "recuou"
        comod_partes.append(f"Ouro {direcao} {gold['change_pct']:+.2f}% para US$ {gold['price']:,.0f}".replace(",","."))
    if oil and oil.get("price"):
        direcao = "subiu" if oil["change_pct"] >= 0 else "recuou"
        comod_partes.append(f"WTI {direcao} {oil['change_pct']:+.2f}% para US$ {oil['price']:.2f}")
    if btc and btc.get("price"):
        direcao = "subiu" if btc["change_pct"] >= 0 else "recuou"
        comod_partes.append(f"Bitcoin {direcao} {btc['change_pct']:+.2f}% para US$ {btc['price']:,.0f}".replace(",","."))
    comod_txt = "Commodities e cripto: " + " | ".join(comod_partes) + "." if comod_partes else ""

    return "\n\n".join(filter(None, [dxy_txt, bolsas_txt, vix_txt, fg_txt, comod_txt]))

def gerar_analise_ibov(ibov, sp, dxy):
    if ibov.get("price") is None:
        return "Dados do Ibovespa indisponíveis."

    preco = ibov["price"]
    var = ibov["change_pct"]

    # Nível
    if preco > 135000:
        nivel_txt = f"O Ibovespa encerrou a sessão anterior em {int(preco):,} pontos".replace(",", ".")
    else:
        nivel_txt = f"O Ibovespa opera em {int(preco):,} pontos".replace(",", ".")

    # Movimento
    if var < -1.5:
        mov_txt = f", com queda expressiva de {var:.2f}%, evidenciando pressão vendedora relevante."
    elif var < -0.3:
        mov_txt = f", recuando {var:.2f}% na última sessão."
    elif var > 1.5:
        mov_txt = f", com avanço expressivo de {var:+.2f}%, demonstrando força compradora."
    elif var > 0.3:
        mov_txt = f", com leve valorização de {var:+.2f}%."
    else:
        mov_txt = f", praticamente estável ({var:+.2f}%)."

    # Correlação
    if sp.get("change_pct") is not None:
        if sp["change_pct"] < -1 and var < -0.5:
            corr_txt = "O índice segue correlacionado ao movimento negativo de Wall Street, refletindo o ambiente de risk-off global."
        elif sp["change_pct"] > 1 and var > 0.5:
            corr_txt = "O índice acompanhou a melhora externa, beneficiado pelo apetite a risco de Wall Street."
        elif sp["change_pct"] < -1 and var > 0:
            corr_txt = "O índice mostrou resiliência ao ignorar a fraqueza externa, o que pode indicar força técnica local."
        else:
            corr_txt = "A correlação com os mercados externos foi moderada na última sessão."
    else:
        corr_txt = ""

    # Suportes e resistências dinâmicos
    sup1 = int(round(preco * 0.97, -2))
    sup2 = int(round(preco * 0.94, -2))
    res1 = int(round(preco * 1.02, -2))
    res2 = int(round(preco * 1.05, -2))

    niveis_txt = (f"Tecnicamente, monitorar suporte em {sup1:,} e {sup2:,} pontos. "
                 f"Resistências relevantes em {res1:,} e {res2:,} pontos.").replace(",", ".")

    return " ".join(filter(None, [nivel_txt + mov_txt, corr_txt, niveis_txt]))

def gerar_analise_dolar(usd, dxy):
    if usd.get("price") is None:
        return "Dados do câmbio indisponíveis."

    preco = usd["price"]
    var = usd["change_pct"]

    if var > 1.0:
        mov_txt = f"O dólar comercial avançou com força ({var:+.2f}%) para R$ {preco:.2f}, pressionando importadores e acirrando preocupações inflacionárias."
    elif var > 0.3:
        mov_txt = f"O dólar subiu {var:+.2f}% para R$ {preco:.2f}, mantendo pressão sobre o real."
    elif var < -1.0:
        mov_txt = f"O real se valorizou com força, derrubando o dólar {var:.2f}% para R$ {preco:.2f} — movimento positivo para a inflação doméstica."
    elif var < -0.3:
        mov_txt = f"O dólar recuou {var:.2f}% para R$ {preco:.2f}, aliviando a pressão cambial."
    else:
        mov_txt = f"O câmbio operou próximo à estabilidade, com o dólar em R$ {preco:.2f} ({var:+.2f}%)."

    if dxy.get("change_pct") is not None:
        if dxy["change_pct"] > 0.3 and var > 0:
            dxy_txt = f"O movimento é consistente com o fortalecimento global do dólar (DXY +{dxy['change_pct']:.2f}%), reduzindo o componente idiossincrático do real."
        elif dxy["change_pct"] < -0.3 and var > 0.5:
            dxy_txt = f"O movimento do real é mais intenso que o DXY ({dxy['change_pct']:+.2f}%), sugerindo componente local de pressão — atenção ao risco Brasil."
        elif dxy["change_pct"] > 0.3 and var < 0:
            dxy_txt = f"O real resistiu ao fortalecimento do DXY ({dxy['change_pct']:+.2f}%), sinal de força relativa da moeda brasileira."
        else:
            dxy_txt = ""
    else:
        dxy_txt = ""

    return " ".join(filter(None, [mov_txt, dxy_txt]))

def gerar_secao_agenda(agenda):
    if not agenda:
        return (
            "Nenhum evento de alto impacto identificado para hoje via ForexFactory. "
            "Consulte o calendário completo em forexfactory.com. "
            "O fluxo de notícias e movimentos técnicos devem predominar na sessão."
        )

    altos = [e for e in agenda if e["impact"] == "alto"]
    medios = [e for e in agenda if e["impact"] == "medio"]

    linhas = []
    if altos:
        linhas.append("Eventos de ALTO impacto no radar:")
        for e in altos:
            linhas.append(f"• {e['time']} [{e['currency']}] {e['event']}")
    if medios:
        linhas.append("Eventos de impacto MÉDIO:")
        for e in medios[:4]:
            linhas.append(f"• {e['time']} [{e['currency']}] {e['event']}")

    linhas.append("\nOs dados americanos costumam gerar volatilidade relevante no câmbio e, por correlação, no Ibovespa. Monitore os releases e evite exposição excessiva nos momentos de divulgação.")
    return "\n".join(linhas)

def gerar_vies_texto(vies_label, tipo, fg, dxy, vix, ibov, sp, usd):
    drivers = []

    if vix.get("change_pct") is not None and vix["change_pct"] > 10:
        drivers.append(f"VIX em alta acentuada ({vix['change_pct']:+.2f}%) sinalizando estresse")
    if fg.get("value") is not None and fg["value"] <= 25:
        drivers.append(f"Fear & Greed em {fg['value']} (Medo Extremo)")
    if dxy.get("change_pct") is not None and dxy["change_pct"] > 0.4:
        drivers.append(f"DXY em alta ({dxy['change_pct']:+.2f}%) pressionando emergentes")
    if sp.get("change_pct") is not None and sp["change_pct"] < -1:
        drivers.append(f"S&P 500 em queda expressiva ({sp['change_pct']:+.2f}%)")
    if dxy.get("change_pct") is not None and dxy["change_pct"] < -0.4:
        drivers.append(f"DXY em queda ({dxy['change_pct']:+.2f}%) favorecendo emergentes")
    if sp.get("change_pct") is not None and sp["change_pct"] > 1:
        drivers.append(f"S&P 500 em alta ({sp['change_pct']:+.2f}%)")

    if tipo == "baixista":
        intro = random.choice([
            f"O conjunto de fatores aponta para viés {vies_label} no pregão de hoje.",
            f"A leitura dos drivers globais indica abertura com pressão vendedora — viés {vies_label}.",
            f"Diante do cenário externo adverso, o viés para hoje é {vies_label}.",
        ])
        recom = "Gestão de risco é prioridade. Evitar posições compradas sem proteção e aguardar sinais de estabilização antes de ampliar exposição."
    elif tipo == "altista":
        intro = random.choice([
            f"O ambiente externo favorável sustenta viés {vies_label} para o pregão.",
            f"Os drivers globais apontam para uma abertura positiva — viés {vies_label}.",
            f"Com o cenário externo contribuindo, o viés para hoje é {vies_label}.",
        ])
        recom = "Oportunidade para posições compradas em ativos de qualidade, com stops bem definidos."
    else:
        intro = f"Os fatores estão equilibrados, sustentando viés {vies_label} para o pregão de hoje."
        recom = "Seletividade é a palavra-chave. Operar em ativos com catalisadores próprios e aguardar o mercado mostrar direção."

    drivers_txt = ""
    if drivers:
        drivers_txt = "Principais drivers: " + " | ".join(drivers) + "."

    return "\n\n".join(filter(None, [intro, drivers_txt, recom]))

# ── MAIN ──────────────────────────────────────────────────────────────────────

def salvar_dados():
    log("=" * 50)
    log("Morning Call — Análise Programática")
    log("=" * 50)

    agora = datetime.now(BRT)
    agora_str = agora.strftime("%d/%m/%Y %H:%M:%S")

    fg    = buscar_fear_greed()
    dxy   = buscar_yahoo("DX-Y.NYB", "DXY")
    vix   = buscar_yahoo("^VIX", "VIX")
    ibov  = buscar_yahoo("^BVSP", "IBOV")
    usd   = buscar_yahoo("USDBRL=X", "USD/BRL")
    sp    = buscar_yahoo("^GSPC", "S&P500")
    nq    = buscar_yahoo("^IXIC", "Nasdaq")
    btc   = buscar_yahoo("BTC-USD", "Bitcoin")
    gold  = buscar_yahoo("GC=F", "Ouro")
    oil   = buscar_yahoo("CL=F", "Petróleo WTI")
    stoxx = buscar_yahoo("^STOXX50E", "Euro Stoxx 50")
    selic = buscar_juros_br()
    juros = buscar_di_futuro()
    agenda   = buscar_agenda()
    noticias = buscar_noticias()
    # Se agenda vazia, extrai eventos das próprias notícias
    if not agenda and noticias:
        agenda = extrair_eventos_das_noticias(noticias)
        if agenda:
            log(f"Agenda extraída das notícias: {len(agenda)} eventos")

    # Gera as seções
    log("Gerando análise...")
    contexto   = gerar_contexto_global(dxy, vix, sp, nq, usd, fg, gold, oil, btc)
    analise_ibov = gerar_analise_ibov(ibov, sp, dxy)
    analise_usd  = gerar_analise_dolar(usd, dxy)
    sec_agenda   = gerar_secao_agenda(agenda)
    vies_label, vies_tipo = calcular_vies(fg, dxy, vix, ibov, sp, usd)
    vies_txt     = gerar_vies_texto(vies_label, vies_tipo, fg, dxy, vix, ibov, sp, usd)

    # Seção de juros
    selic_txt = ""
    if selic is not None:
        selic_txt = f"A taxa Selic está em {selic:.2f}% a.a."
        us10y = juros.get("us10y", {})
        ewz = juros.get("ewz", {})
        if us10y.get("price") is not None:
            selic_txt += f" Os juros americanos (Treasury 10Y) operam em {us10y['price']:.2f}% ({us10y['change_pct']:+.2f}%)."
            if us10y["change_pct"] > 0.05:
                selic_txt += " A alta dos Treasuries aumenta o custo de capital global e reduz o apelo relativo de emergentes."
            elif us10y["change_pct"] < -0.05:
                selic_txt += " A queda dos Treasuries alivia a pressão sobre emergentes e favorece fluxo para ativos de risco."
        if ewz.get("change_pct") is not None:
            selic_txt += f" O ETF EWZ (proxy do Brasil no exterior) operou {ewz['change_pct']:+.2f}%, sinalizando o apetite do investidor estrangeiro pelo mercado brasileiro."

    paragrafos = [
        f"**CONTEXTO GLOBAL**\n{contexto}",
        f"**IBOVESPA**\n{analise_ibov}",
        f"**DÓLAR / CÂMBIO**\n{analise_usd}",
    ]
    if selic_txt:
        paragrafos.append(f"**JUROS & RENDA FIXA**\n{selic_txt}")
    paragrafos += [
        f"**AGENDA DO DIA**\n{sec_agenda}",
    ]

    if noticias:
        noticias_txt = "\n".join([f"• {n}" for n in noticias])
        paragrafos.append(f"**MANCHETES**\n{noticias_txt}")

    # Agenda formatada
    agenda_fmt = [{"time": e["time"], "event": f"[{e['currency']}] {e['event']}"} for e in agenda]
    if not agenda_fmt:
        agenda_fmt = [{"time": "—", "event": "Sem eventos de alto impacto hoje"}]

    # Tags
    tags = [f"Viés {vies_label}"]
    if ibov.get("change_pct") is not None:
        d = "▲" if ibov["change_pct"] >= 0 else "▼"
        tags.append(f"IBOV {d} {ibov['change_pct']:+.2f}%")
    if usd.get("price") is not None:
        tags.append(f"USD/BRL R$ {usd['price']:.2f}")
    if vix.get("price") is not None:
        tags.append(f"VIX {vix['price']:.1f}")

    json_final = {
        "date": agora.strftime("%d/%m/%Y"),
        "lastUpdate": agora_str,
        "lastFetch": agora_str,
        "title": f"Morning Call · {agora.strftime('%d/%m')}",
        "vies": vies_label,
        "vies_txt": vies_txt,
        "tags": tags,
        "tags_tipados": [{"tipo": vies_tipo, "label": tags[0]}],
        "insights": paragrafos,
        "agenda": agenda_fmt,
        "strategy": vies_txt,
        "indicators": {
            "fearGreed": fg.get("value"),
            "fearGreedLabel": fg.get("label"),
            "dxy": dxy.get("price"),
            "dxyChange": dxy.get("change_pct"),
            "vix": vix.get("price"),
            "vixChange": vix.get("change_pct"),
            "ibov": ibov.get("price"),
            "ibovChange": ibov.get("change_pct"),
            "usdbrl": usd.get("price"),
            "usdbrlChange": usd.get("change_pct"),
            "selic": selic,
            "us10y": juros.get("us10y", {}).get("price"),
            "us10yChange": juros.get("us10y", {}).get("change_pct"),
            "btc": btc.get("price"),
            "btcChange": btc.get("change_pct"),
            "gold": gold.get("price"),
            "goldChange": gold.get("change_pct"),
            "oil": oil.get("price"),
            "oilChange": oil.get("change_pct"),
            "stoxx": stoxx.get("price"),
            "stoxxChange": stoxx.get("change_pct"),
        },
        "scrape_ok": True,
        "feriado_aviso": None,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(json_final, f, ensure_ascii=False, indent=2)

    log(f"data.json salvo! Viés: {vies_label} | Seções: {len(paragrafos)}")
    log("=" * 50)

if __name__ == "__main__":
    salvar_dados()
