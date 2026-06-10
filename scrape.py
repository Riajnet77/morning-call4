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

# Calendário fixo de eventos de alto impacto 2026
CALENDARIO_FIXO = {
    # JUNHO 2026
    "2026-06-09": [
        {"time":"02:00","currency":"EUR","event":"German Industrial Production m/m","impact":"medio"},
        {"time":"02:00","currency":"EUR","event":"German Trade Balance","impact":"medio"},
        {"time":"06:00","currency":"USD","event":"NFIB Small Business Index","impact":"medio"},
        {"time":"08:15","currency":"USD","event":"ADP Weekly Employment Change","impact":"medio"},
        {"time":"08:30","currency":"USD","event":"Trade Balance (EUA)","impact":"medio"},
        {"time":"10:00","currency":"USD","event":"Existing Home Sales","impact":"medio"},
    ],
    "2026-06-10": [
        {"time":"08:30","currency":"USD","event":"CPI — Inflação EUA (Mai)","impact":"alto"},
        {"time":"09:00","currency":"BRL","event":"IPCA (Mai) — Inflação Brasil","impact":"alto"},
    ],
    "2026-06-11": [
        {"time":"08:30","currency":"USD","event":"PPI — Preços ao Produtor (Mai)","impact":"medio"},
        {"time":"10:00","currency":"USD","event":"Michigan Consumer Sentiment","impact":"medio"},
    ],
    "2026-06-12": [
        {"time":"08:30","currency":"USD","event":"Initial Jobless Claims","impact":"medio"},
    ],
    "2026-06-13": [
        {"time":"08:30","currency":"USD","event":"Retail Sales (Mai)","impact":"alto"},
        {"time":"09:15","currency":"USD","event":"Industrial Production (Mai)","impact":"medio"},
    ],
    "2026-06-16": [
        {"time":"08:30","currency":"USD","event":"Empire State Manufacturing","impact":"medio"},
    ],
    "2026-06-17": [
        {"time":"08:30","currency":"USD","event":"Housing Starts & Building Permits","impact":"medio"},
    ],
    "2026-06-18": [
        {"time":"14:00","currency":"USD","event":"Decisão do Fed — FOMC Rate Decision","impact":"alto"},
        {"time":"14:30","currency":"USD","event":"Coletiva Powell — Fed","impact":"alto"},
        {"time":"18:00","currency":"BRL","event":"Decisão COPOM — Taxa Selic","impact":"alto"},
    ],
    "2026-06-19": [
        {"time":"08:30","currency":"USD","event":"Initial Jobless Claims","impact":"medio"},
        {"time":"10:00","currency":"USD","event":"Existing Home Sales","impact":"medio"},
    ],
    "2026-06-23": [
        {"time":"09:45","currency":"USD","event":"PMI Manufatura Flash (Jun)","impact":"medio"},
        {"time":"10:00","currency":"USD","event":"New Home Sales","impact":"medio"},
    ],
    "2026-06-24": [
        {"time":"08:30","currency":"USD","event":"Durable Goods Orders","impact":"medio"},
    ],
    "2026-06-25": [
        {"time":"08:30","currency":"USD","event":"GDP Final Q1 2026","impact":"alto"},
        {"time":"08:30","currency":"USD","event":"Initial Jobless Claims","impact":"medio"},
    ],
    "2026-06-26": [
        {"time":"08:30","currency":"USD","event":"PCE Price Index (Mai)","impact":"alto"},
        {"time":"10:00","currency":"USD","event":"Michigan Consumer Sentiment Final","impact":"medio"},
    ],
    "2026-06-30": [
        {"time":"09:00","currency":"BRL","event":"IGP-M Junho (Inflação BR)","impact":"medio"},
    ],
    # JULHO 2026
    "2026-07-01": [
        {"time":"10:00","currency":"USD","event":"ISM Manufacturing PMI (Jun)","impact":"medio"},
    ],
    "2026-07-02": [
        {"time":"08:30","currency":"USD","event":"Non-Farm Payrolls (Jun)","impact":"alto"},
        {"time":"08:30","currency":"USD","event":"Unemployment Rate (Jun)","impact":"alto"},
        {"time":"08:30","currency":"USD","event":"Average Hourly Earnings","impact":"alto"},
    ],
    "2026-07-07": [
        {"time":"10:00","currency":"USD","event":"ISM Services PMI (Jun)","impact":"medio"},
    ],
    "2026-07-09": [
        {"time":"08:30","currency":"USD","event":"Initial Jobless Claims","impact":"medio"},
        {"time":"09:00","currency":"BRL","event":"IPCA (Jun) — Inflação Brasil","impact":"alto"},
    ],
    "2026-07-10": [
        {"time":"08:30","currency":"USD","event":"CPI — Inflação EUA (Jun)","impact":"alto"},
    ],
    "2026-07-14": [
        {"time":"08:30","currency":"USD","event":"PPI — Preços ao Produtor (Jun)","impact":"medio"},
    ],
    "2026-07-16": [
        {"time":"08:30","currency":"USD","event":"Retail Sales (Jun)","impact":"alto"},
        {"time":"08:30","currency":"USD","event":"Initial Jobless Claims","impact":"medio"},
    ],
    "2026-07-28": [
        {"time":"08:30","currency":"USD","event":"GDP Preliminar Q2 2026","impact":"alto"},
        {"time":"08:30","currency":"USD","event":"Initial Jobless Claims","impact":"medio"},
    ],
    "2026-07-29": [
        {"time":"14:00","currency":"USD","event":"Decisão do Fed — FOMC Rate Decision","impact":"alto"},
        {"time":"18:00","currency":"BRL","event":"Decisão COPOM — Taxa Selic","impact":"alto"},
    ],
    "2026-07-31": [
        {"time":"08:30","currency":"USD","event":"PCE Price Index (Jun)","impact":"alto"},
        {"time":"09:00","currency":"BRL","event":"IGP-M Julho","impact":"medio"},
    ],
}

# Fallback semanal — só usado se não houver no calendário fixo
AGENDA_SEMANAL = {
    3: [{"time":"08:30","currency":"USD","event":"Initial Jobless Claims (semanal)","impact":"medio"}],
}

KEYWORDS_AGENDA = {
    "PAYROLL": ("08:30","USD","Non-Farm Payrolls (NFP)","alto"),
    "NFP":     ("08:30","USD","Non-Farm Payrolls (NFP)","alto"),
    "CPI":     ("08:30","USD","CPI — Inflação EUA","alto"),
    "FOMC":    ("14:00","USD","Decisão FOMC / Fed","alto"),
    "COPOM":   ("18:00","BRL","Decisão COPOM — Selic","alto"),
    "IPCA":    ("09:00","BRL","IPCA — Inflação Brasil","alto"),
    "CAGED":   ("09:00","BRL","CAGED — Empregos Formais","medio"),
    "PIB":     ("09:00","BRL","PIB Brasil","alto"),
    "GDP":     ("08:30","USD","GDP — PIB EUA","alto"),
    "PMI":     ("09:45","USD","PMI Composto","medio"),
    "JOBLESS": ("08:30","USD","Initial Jobless Claims","medio"),
    "JOLTS":   ("10:00","USD","JOLTS — Vagas de Emprego","medio"),
    "ADP":     ("08:15","USD","ADP Payroll Privado","medio"),
    "PPI":     ("08:30","USD","PPI — Preços ao Produtor","medio"),
    "RETAIL":  ("08:30","USD","Retail Sales — Varejo EUA","medio"),
    "PCE":     ("08:30","USD","PCE Price Index","alto"),
    "SELIC":   ("18:00","BRL","Decisão COPOM — Selic","alto"),
}

def buscar_agenda():
    """Calendário econômico: fixo + ForexFactory + fallback notícias."""
    from datetime import date
    hoje = datetime.now(BRT)
    hoje_str = hoje.strftime("%Y-%m-%d")
    dia = hoje.weekday()
    eventos = []
    encontrados = set()

    # 1. Calendário fixo (datas exatas conhecidas)
    for ev in CALENDARIO_FIXO.get(hoje_str, []):
        if ev["event"] not in encontrados:
            encontrados.add(ev["event"])
            eventos.append(ev)
    if eventos:
        log(f"Agenda calendário fixo: {len(eventos)} eventos")

    # 2. Tenta ForexFactory HTML
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
            imp = row.select_one(".calendar__impact span, .impact-icon, [class*='impact']")
            impacto = "medio"  # default medio para não perder eventos
            if imp:
                cls = " ".join(imp.get("class", [])).lower()
                title = (imp.get("title","") or imp.get("data-original-title","")).lower()
                if "high" in cls or "high" in title or "red" in cls: impacto = "alto"
                elif "low" in cls or "low" in title or "gray" in cls or "grey" in cls: impacto = "baixo"
                else: impacto = "medio"
            moeda_el = row.select_one(".calendar__currency")
            moeda = moeda_el.text.strip() if moeda_el else ""
            ev_el = row.select_one(".calendar__event-title")
            evento = ev_el.text.strip() if ev_el else ""
            if evento and moeda in ["USD","BRL","EUR","EUR","JPY","CNY","CAD","GBP"] and impacto in ["alto","medio"] and evento not in encontrados:
                encontrados.add(evento)
                eventos.append({"time": hora_atual, "currency": moeda, "event": evento, "impact": impacto})
        if len(eventos) > len(CALENDARIO_FIXO.get(hoje_str,[])):
            log(f"Agenda FF adicionou eventos: total {len(eventos)}")
    except Exception as e:
        log(f"AVISO FF: {e}")

    # 3. Detecta eventos nas notícias já coletadas (Reuters, Bloomberg, CNBC, etc)
    try:
        import feedparser
        DETECTOR = {
            # Palavra-chave : (horário, moeda, nome completo, impacto)
            "ADP":              ("08:15","USD","ADP Employment Change","medio"),
            "NFIB":             ("06:00","USD","NFIB Small Business Index","medio"),
            "TRADE BALANCE":    ("08:30","USD","Trade Balance (EUA)","medio"),
            "EXISTING HOME":    ("10:00","USD","Existing Home Sales","medio"),
            "NEW HOME":         ("10:00","USD","New Home Sales","medio"),
            "JOBLESS":          ("08:30","USD","Initial Jobless Claims","medio"),
            "CLAIMS":           ("08:30","USD","Initial Jobless Claims","medio"),
            "PAYROLL":          ("08:30","USD","Non-Farm Payrolls","alto"),
            "NFP":              ("08:30","USD","Non-Farm Payrolls","alto"),
            "UNEMPLOYMENT":     ("08:30","USD","Unemployment Rate","alto"),
            "CPI":              ("08:30","USD","CPI — Inflação EUA","alto"),
            "INFLATION":        ("08:30","USD","CPI — Inflação EUA","alto"),
            "PPI":              ("08:30","USD","PPI — Preços ao Produtor","medio"),
            "PCE":              ("08:30","USD","PCE Price Index","alto"),
            "RETAIL SALES":     ("08:30","USD","Retail Sales","alto"),
            "GDP":              ("08:30","USD","GDP — PIB EUA","alto"),
            "FOMC":             ("14:00","USD","Decisão FOMC / Fed","alto"),
            "FED DECISION":     ("14:00","USD","Decisão FOMC / Fed","alto"),
            "RATE DECISION":    ("14:00","USD","Decisão de Juros Fed","alto"),
            "POWELL":           ("14:00","USD","Fala do Powell / Fed","alto"),
            "ISM MANUFACTUR":   ("10:00","USD","ISM Manufacturing PMI","medio"),
            "ISM SERVICES":     ("10:00","USD","ISM Services PMI","medio"),
            "ISM NON-MANUF":    ("10:00","USD","ISM Services PMI","medio"),
            "JOLTS":            ("10:00","USD","JOLTS Job Openings","medio"),
            "DURABLE GOODS":    ("08:30","USD","Durable Goods Orders","medio"),
            "HOUSING STARTS":   ("08:30","USD","Housing Starts","medio"),
            "INDUSTRIAL PROD":  ("09:15","USD","Industrial Production","medio"),
            "CONSUMER CONF":    ("10:00","USD","Consumer Confidence","medio"),
            "MICHIGAN":         ("10:00","USD","UMich Consumer Sentiment","medio"),
            "PMI":              ("09:45","USD","PMI Composto EUA","medio"),
            # Brasil
            "COPOM":            ("18:00","BRL","Decisão COPOM — Selic","alto"),
            "SELIC":            ("18:00","BRL","Decisão COPOM — Selic","alto"),
            "IPCA":             ("09:00","BRL","IPCA — Inflação Brasil","alto"),
            "CAGED":            ("09:00","BRL","CAGED — Empregos Formais","medio"),
            "PIB BRASIL":       ("09:00","BRL","PIB Brasil","alto"),
            "FOCUS":            ("08:30","BRL","Boletim Focus — BCB","medio"),
            # Europa
            "GERMAN":           ("02:00","EUR","Dados Alemanha","medio"),
            "ECB":              ("07:45","EUR","Decisão BCE","alto"),
            "EURO":             ("04:00","EUR","Dados da Zona do Euro","medio"),
        }

        # Coleta títulos das notícias do dia
        todos_titulos = []
        for feed_url in [
            "https://br.investing.com/rss/news_25.rss",
            "https://br.investing.com/rss/news_14.rss",
            "https://feeds.marketwatch.com/marketwatch/topstories/",
            "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
        ]:
            try:
                feed = feedparser.parse(feed_url)
                for e in feed.entries[:8]:
                    todos_titulos.append(e.get("title","").upper())
            except Exception:
                pass

        for titulo in todos_titulos:
            for kw, (hora, moeda, nome, impacto) in DETECTOR.items():
                if kw in titulo and nome not in encontrados:
                    encontrados.add(nome)
                    eventos.append({"time": hora, "currency": moeda, "event": nome, "impact": impacto})
                    log(f"  Evento detectado nas noticias: {nome}")

    except Exception as e:
        log(f"AVISO detector noticias: {e}")

    # 4. Sempre adiciona eventos recorrentes do dia da semana (se não conflitar)
    for ev in AGENDA_SEMANAL.get(dia, []):
        if ev["event"] not in encontrados:
            eventos.append(ev)

    log(f"Agenda final: {len(eventos)} eventos")
    return sorted(eventos, key=lambda x: x.get("time","99:99"))[:12]

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
    """Coleta noticias de Reuters, Bloomberg, FT, MarketWatch via RSS."""
    import feedparser
    FEEDS = [
        # Reuters mercados globais
        ("Reuters",      "https://news.google.com/rss/search?q=site:reuters.com+markets+OR+economy+OR+fed+OR+stocks&hl=en-US&gl=US&ceid=US:en"),
        # Reuters Brasil
        ("Reuters BR",   "https://news.google.com/rss/search?q=site:reuters.com+ibovespa+OR+brazil+OR+petrobras+OR+vale+OR+copom&hl=pt-BR&gl=BR&ceid=BR:pt-419"),
        # Bloomberg mercados
        ("Bloomberg",    "https://news.google.com/rss/search?q=site:bloomberg.com+markets+OR+fed+OR+stocks+OR+economy&hl=en-US&gl=US&ceid=US:en"),
        # Financial Times
        ("FT",           "https://www.ft.com/rss/home/international"),
        # MarketWatch
        ("MarketWatch",  "https://feeds.marketwatch.com/marketwatch/topstories/"),
        # CNBC Markets
        ("CNBC Markets", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839135"),
        # Brasil — InfoMoney
        ("InfoMoney",    "https://www.infomoney.com.br/feed/"),
        # Brasil — Valor Econômico
        ("Valor",        "https://news.google.com/rss/search?q=site:valor.globo.com+ibovespa+OR+bolsa+OR+dolar+OR+juros&hl=pt-BR&gl=BR&ceid=BR:pt-419"),
        # Brasil — Investing.com
        ("Investing BR", "https://br.investing.com/rss/news_25.rss"),
        # Brasil — B3/mercado local
        ("Brasil Mkt",   "https://news.google.com/rss/search?q=ibovespa+OR+petrobras+OR+vale+OR+selic+OR+copom+OR+%22mercado+brasileiro%22&hl=pt-BR&gl=BR&ceid=BR:pt-419"),
    ]

    noticias = []
    vistos = set()
    for nome, url in FEEDS:
        try:
            feed = feedparser.parse(url)
            count = 0
            agora = datetime.now(BRT)
            for e in feed.entries[:10]:
                titulo = e.get("title", "").strip()

                # Filtro de data — ignora noticias com mais de 48h
                import calendar as cal
                pub = e.get("published_parsed") or e.get("updated_parsed")
                if pub:
                    try:
                        pub_dt = datetime.fromtimestamp(cal.timegm(pub), tz=BRT)
                        if (agora - pub_dt).total_seconds() > 48 * 3600:
                            continue
                    except Exception:
                        pass

                # Fonte real
                fonte_real = nome
                if hasattr(e, "source") and hasattr(e.source, "title"):
                    fonte_real = e.source.title

                # Remove prefixo redundante
                for pref in ["Reuters - ", "Bloomberg - ", "Reuters:", "Bloomberg:", "FT - "]:
                    if titulo.startswith(pref):
                        titulo = titulo[len(pref):].strip()

                if titulo and titulo not in vistos:
                    vistos.add(titulo)
                    noticias.append({"title": titulo, "source": fonte_real})
                    count += 1
                    if count >= 4:
                        break
            log(f"Noticias {nome}: {count}")
        except Exception as ex:
            log(f"AVISO {nome}: {ex}")

    log(f"Total noticias: {len(noticias)}")
    return noticias[:16]
    return noticias[:16]

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

def buscar_focus():
    """Busca expectativas do Boletim Focus via SGS do BCB."""
    try:
        resultado = {}
        headers = {"User-Agent": "Mozilla/5.0"}
        # Séries SGS corretas:
        # 13521 = IPCA esperado (% a.a.) — Focus
        # 4390  = PIB esperado (% a.a.) — Focus  
        # 4175  = Selic esperada fim ano — Focus
        series = [
            ("selic_esperada", "4823"),  # Selic esperada Focus — série correta
            ("ipca_esperado",  "13521"),
            ("pib_esperado",   "4390"),
        ]
        for campo, serie in series:
            try:
                url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados/ultimos/1?formato=json"
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 200:
                    d = r.json()
                    if d:
                        val = float(str(d[0]["valor"]).replace(",","."))
                        # Validação básica de sanidade
                        if campo == "selic_esperada" and 5 < val < 25:
                            resultado[campo] = val
                            resultado["selic_data"] = d[0].get("data","")
                        elif campo == "selic_esperada":
                            log(f"Focus Selic serie 4823 valor invalido: {val}")
                        elif campo == "ipca_esperado" and 0 < val < 30:
                            resultado[campo] = val
                        elif campo == "pib_esperado" and -10 < val < 20:
                            resultado[campo] = val
            except Exception:
                pass

        if resultado:
            log(f"Focus: Selic {resultado.get('selic_esperada','?')}% | IPCA {resultado.get('ipca_esperado','?')}% | PIB {resultado.get('pib_esperado','?')}%")
        else:
            log("Focus: API BCB indisponível neste ambiente")
        return resultado
    except Exception as e:
        log(f"AVISO Focus: {e}")
        return {}

def buscar_ptax():
    """Busca PTax oficial do BCB."""
    try:
        from datetime import date, timedelta
        hoje = date.today()
        # Tenta hoje, se não tiver tenta ontem
        for delta in range(5):
            data = hoje - timedelta(days=delta)
            data_str = data.strftime("%m-%d-%Y")
            url = f"https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarDia(dataCotacao=@dataCotacao)?@dataCotacao='{data_str}'&$format=json&$select=cotacaoCompra,cotacaoVenda,dataHoraCotacao"
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                d = r.json()
                if d.get("value"):
                    venda = float(d["value"][-1]["cotacaoVenda"])
                    data_cot = d["value"][-1]["dataHoraCotacao"][:10]
                    log(f"PTax: R$ {venda:.4f} ({data_cot})")
                    return {"venda": venda, "data": data_cot}
        log("PTax: sem dados disponíveis")
        return {}
    except Exception as e:
        log(f"AVISO PTax: {e}")
        return {}

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

def gerar_analise_ibov(ibov, sp, dxy, eww=None, ech=None):
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

    # Peers emergentes
    peers = []
    eww = eww or {}
    ech = ech or {}
    if eww.get("change_pct") is not None:
        peers.append(f"México (EWW) {'+' if eww['change_pct']>=0 else ''}{eww['change_pct']:.2f}%")
    if ech.get("change_pct") is not None:
        peers.append(f"Chile (ECH) {'+' if ech['change_pct']>=0 else ''}{ech['change_pct']:.2f}%")
    if peers:
        niveis_txt += f" Peers emergentes: {', '.join(peers)}."

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

def gerar_vies_texto(vies_label, tipo, fg, dxy, vix, ibov, sp, usd,
                      nq=None, oil=None, brent=None, soja=None,
                      eww=None, ech=None, us10y=None, selic=None, focus=None):
    """Gera texto de direcionamento estratégico dinâmico e específico."""
    hoje = datetime.now(BRT).strftime("%d/%m/%Y")
    linhas = []

    # ── ABERTURA ──────────────────────────────────────────────────────────────
    ibov_pts = f"{int(ibov['price']):,}".replace(",",".") if ibov.get("price") else "N/A"
    ibov_var = f"{ibov['change_pct']:+.2f}%" if ibov.get("change_pct") is not None else ""
    usd_val  = f"R$ {usd['price']:.2f}" if usd.get("price") else "N/A"
    usd_var  = f"{usd['change_pct']:+.2f}%" if usd.get("change_pct") is not None else ""

    if tipo == "baixista":
        abertura = f"O pregão de {hoje} abre com viés **{vies_label}**. IBOV em {ibov_pts} pts ({ibov_var}), dólar em {usd_val} ({usd_var})."
    elif tipo == "altista":
        abertura = f"O pregão de {hoje} abre com viés **{vies_label}**. IBOV em {ibov_pts} pts ({ibov_var}), dólar em {usd_val} ({usd_var})."
    else:
        abertura = f"O pregão de {hoje} abre com viés **{vies_label}**. IBOV em {ibov_pts} pts ({ibov_var}), dólar em {usd_val} ({usd_var})."
    linhas.append(abertura)

    # ── DRIVERS PRINCIPAIS ────────────────────────────────────────────────────
    drivers = []

    # Fear & Greed
    fg_val = fg.get("value") if fg else None
    if fg_val is not None:
        if fg_val <= 15:
            drivers.append(f"Fear & Greed em {fg_val}/100 (Medo Extremo) — mercado em pânico, potencial reversão técnica no radar")
        elif fg_val <= 30:
            drivers.append(f"Fear & Greed em {fg_val}/100 (Medo) — sentimento negativo predomina")
        elif fg_val >= 80:
            drivers.append(f"Fear & Greed em {fg_val}/100 (Ganância Extrema) — mercado sobrecomprado, cautela")
        elif fg_val >= 65:
            drivers.append(f"Fear & Greed em {fg_val}/100 (Ganância) — apetite a risco elevado")

    # VIX
    if vix.get("price") is not None:
        vix_p = vix["price"]
        vix_c = vix.get("change_pct", 0)
        if vix_p > 30:
            drivers.append(f"VIX em {vix_p:.1f} pts (+{vix_c:.1f}%) — pânico no mercado americano, risco elevado")
        elif vix_p > 20:
            drivers.append(f"VIX em {vix_p:.1f} pts — volatilidade elevada, operar com stops apertados")
        elif vix_c > 15:
            drivers.append(f"VIX disparou {vix_c:+.1f}% para {vix_p:.1f} pts — aumento súbito de volatilidade")
        elif vix_c < -10:
            drivers.append(f"VIX recuou {vix_c:.1f}% para {vix_p:.1f} pts — compressão de volatilidade favorece risk-on")

    # DXY
    if dxy.get("change_pct") is not None:
        dxy_c = dxy["change_pct"]
        dxy_p = dxy.get("price", 0)
        if dxy_c > 0.5:
            drivers.append(f"DXY {dxy_c:+.2f}% em {dxy_p:.2f} — dólar forte pressiona emergentes e commodities")
        elif dxy_c < -0.5:
            drivers.append(f"DXY {dxy_c:+.2f}% em {dxy_p:.2f} — dólar fraco favorece IBOV e commodities em BRL")

    # S&P e Nasdaq
    if sp.get("change_pct") is not None:
        sp_c = sp["change_pct"]
        nq_c = (nq or {}).get("change_pct")
        if sp_c < -2:
            drivers.append(f"S&P 500 {sp_c:+.2f}% — derrocada em NY contamina abertura brasileira")
        elif sp_c < -0.8:
            drivers.append(f"S&P 500 {sp_c:+.2f}% — queda moderada em NY, pressão sobre bolsas emergentes")
        elif sp_c > 1.5:
            drivers.append(f"S&P 500 {sp_c:+.2f}% — rali em NY abre espaço para recuperação do IBOV")
        elif sp_c > 0.5:
            drivers.append(f"S&P 500 {sp_c:+.2f}% — leve otimismo externo apoia ativos de risco")

    # Juros EUA
    if us10y and us10y.get("price") is not None:
        u10_p = us10y["price"]
        u10_c = us10y.get("change_pct", 0)
        if u10_c > 0.5:
            drivers.append(f"Treasury 10Y {u10_p:.2f}% ({u10_c:+.2f}%) — juro longo americano subindo pressiona emergentes")
        elif u10_c < -0.5:
            drivers.append(f"Treasury 10Y {u10_p:.2f}% ({u10_c:+.2f}%) — alívio nos juros americanos favorece fluxo para emergentes")

    # Selic e juros BR
    if selic:
        if focus and focus.get("selic_esperada"):
            s_esp = focus["selic_esperada"]
            if s_esp > selic + 1:
                drivers.append(f"Selic em {selic:.1f}% a.a. com mercado projetando {s_esp:.1f}% — expectativa de alta pressionando prêmios de risco")
            elif s_esp < selic - 0.5:
                drivers.append(f"Selic em {selic:.1f}% a.a. com Focus projetando {s_esp:.1f}% — expectativa de corte no horizonte")

    # Petróleo — impacto Petrobras
    oil_data = brent if (brent or {}).get("price") else oil
    if oil_data and oil_data.get("change_pct") is not None:
        oil_c = oil_data["change_pct"]
        oil_p = oil_data.get("price", 0)
        nome_oil = "Brent" if (brent or {}).get("price") else "WTI"
        if oil_c > 2:
            drivers.append(f"Petróleo {nome_oil} {oil_c:+.2f}% para US$ {oil_p:.2f} — alta beneficia Petrobras (PETR3/4) e setor de energia")
        elif oil_c < -2:
            drivers.append(f"Petróleo {nome_oil} {oil_c:+.2f}% para US$ {oil_p:.2f} — queda pressiona Petrobras e reduz inflação de combustíveis")

    # Soja — agronegócio
    if soja and soja.get("change_pct") is not None:
        sj_c = soja["change_pct"]
        if abs(sj_c) > 1:
            dirs = "alta beneficia exportadoras de grãos" if sj_c > 0 else "queda pressiona receitas do agronegócio"
            drivers.append(f"Soja {sj_c:+.2f}% — {dirs}")

    # Peers emergentes
    peers_txt = []
    if eww and eww.get("change_pct") is not None:
        peers_txt.append(f"México (EWW) {eww['change_pct']:+.2f}%")
    if ech and ech.get("change_pct") is not None:
        peers_txt.append(f"Chile (ECH) {ech['change_pct']:+.2f}%")
    if peers_txt:
        divergencia = ""
        ibov_c = ibov.get("change_pct", 0) or 0
        peers_medio = sum([
            (eww or {}).get("change_pct", 0) or 0,
            (ech or {}).get("change_pct", 0) or 0
        ]) / 2
        if ibov_c > peers_medio + 1:
            divergencia = " — Brasil outperformando peers"
        elif ibov_c < peers_medio - 1:
            divergencia = " — Brasil underperformando peers"
        drivers.append(f"Peers emergentes: {', '.join(peers_txt)}{divergencia}")

    if drivers:
        linhas.append("Principais drivers: " + " · ".join(drivers) + ".")

    # ── RECOMENDAÇÃO OPERACIONAL ──────────────────────────────────────────────
    if tipo == "baixista":
        if fg_val and fg_val <= 20 and vix.get("price", 0) > 25:
            recom = "Medo extremo + VIX elevado = zona de reversão potencial. Aguardar confirmação antes de posições vendidas. Stops obrigatórios."
        elif dxy.get("change_pct", 0) > 0.5:
            recom = "Dólar forte + viés baixista: evitar ações com receita em BRL e importadoras. Foco em exportadoras (Vale, Petrobras, agro) como proteção cambial."
        else:
            recom = "Reduzir exposição a risco. Priorizar proteção com hedge cambial ou posições defensivas. Aguardar estabilização antes de novas entradas."
    elif tipo == "altista":
        if sp.get("change_pct", 0) > 1 and dxy.get("change_pct", 0) < 0:
            recom = "Cenário ideal: NY em alta + dólar fraco = fluxo para emergentes. Oportunidade em ações de crescimento e small caps da B3."
        else:
            recom = "Viés construtivo. Posições compradas em ativos de qualidade com stops definidos. Atenção à agenda do dia para ajustes de risco."
    else:
        recom = "Mercado sem direção clara. Seletividade máxima — operar apenas em ativos com catalisador próprio. Evitar alavancagem e aguardar definição de tendência."

    linhas.append(recom)

    return "\n\n".join(linhas)

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
    brent = buscar_yahoo("BZ=F", "Brent")
    soja  = buscar_yahoo("ZS=F", "Soja")
    stoxx = buscar_yahoo("^STOXX50E", "Euro Stoxx 50")
    ewz   = buscar_yahoo("EWZ", "EWZ-BR")
    eww   = buscar_yahoo("EWW", "México ETF")
    ech   = buscar_yahoo("ECH", "Chile ETF")
    selic = buscar_juros_br()
    juros = buscar_di_futuro()
    focus = buscar_focus()
    ptax  = buscar_ptax()
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
    analise_ibov = gerar_analise_ibov(ibov, sp, dxy, eww=eww, ech=ech)
    analise_usd  = gerar_analise_dolar(usd, dxy)
    sec_agenda   = gerar_secao_agenda(agenda)
    vies_label, vies_tipo = calcular_vies(fg, dxy, vix, ibov, sp, usd)
    vies_txt     = gerar_vies_texto(vies_label, vies_tipo, fg, dxy, vix, ibov, sp, usd, nq=nq, oil=oil, brent=brent, soja=soja, eww=eww, ech=ech, us10y=juros.get("us10y",{}), selic=selic, focus=focus)

    # Seção de juros
    selic_txt = ""
    if selic is not None:
        selic_txt = f"A taxa Selic está em {selic:.2f}% a.a."
        # Boletim Focus
        if focus.get("selic_esperada"):
            selic_txt += f" O mercado projeta Selic em {focus['selic_esperada']:.2f}% ao final do ciclo (Boletim Focus)."
        if focus.get("ipca_esperado"):
            selic_txt += f" Expectativa de IPCA para o ano: {focus['ipca_esperado']:.2f}%."
        if focus.get("pib_esperado"):
            selic_txt += f" Projeção de PIB: {focus['pib_esperado']:.2f}%."
        # PTax
        if ptax.get("venda"):
            selic_txt += f" A PTax oficial do BCB fechou em R$ {ptax['venda']:.4f}."
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
        # Formata com fonte: "• Título [Reuters]"
        linhas = []
        for n in noticias:
            if isinstance(n, dict):
                fonte = n.get("source", "")
                titulo = n.get("title", "")
                linhas.append(f"• {titulo} [{fonte}]" if fonte else f"• {titulo}")
            else:
                linhas.append(f"• {n}")
        noticias_txt = "\n".join(linhas)
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
            "selicEsperada": focus.get("selic_esperada"),
            "ipcaEsperado": focus.get("ipca_esperado"),
            "pibEsperado": focus.get("pib_esperado"),
            "ptax": ptax.get("venda"),
            "ptaxData": ptax.get("data"),
            "btc": btc.get("price"),
            "btcChange": btc.get("change_pct"),
            "gold": gold.get("price"),
            "goldChange": gold.get("change_pct"),
            "oil": oil.get("price"),
            "oilChange": oil.get("change_pct"),
            "stoxx": stoxx.get("price"),
            "stoxxChange": stoxx.get("change_pct"),
            "brent": brent.get("price"),
            "brentChange": brent.get("change_pct"),
            "soja": soja.get("price"),
            "sojaChange": soja.get("change_pct"),
            "eww": eww.get("price"),
            "ewwChange": eww.get("change_pct"),
            "ech": ech.get("price"),
            "echChange": ech.get("change_pct"),
        },
        "scrape_ok": True,
        "generated_at": agora_str,
        "feriado_aviso": None,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(json_final, f, ensure_ascii=False, indent=2)

    log(f"data.json salvo! Viés: {vies_label} | Seções: {len(paragrafos)}")
    log("=" * 50)

if __name__ == "__main__":
    salvar_dados()
