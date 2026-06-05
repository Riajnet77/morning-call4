import os
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

BRT = ZoneInfo("America/Sao_Paulo")

def log(msg):
    print(f"[{datetime.now(BRT).strftime('%H:%M:%S')}] {msg}", flush=True)

# ── 1. FEAR & GREED ───────────────────────────────────────────────────────────
def buscar_fear_greed():
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        data = r.json()
        valor = round(data["fear_and_greed"]["score"])
        rating = data["fear_and_greed"]["rating"]
        log(f"Fear & Greed: {valor} ({rating})")
        return {"value": valor, "label": rating}
    except Exception as e:
        log(f"AVISO Fear&Greed: {e}")
        return {"value": None, "label": "N/A"}

# ── 2. YAHOO FINANCE ──────────────────────────────────────────────────────────
def buscar_yahoo(symbol, nome):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        data = r.json()
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        preco = round(closes[-1], 2)
        variacao = round(((closes[-1] / closes[-2]) - 1) * 100, 2) if len(closes) >= 2 else 0
        log(f"{nome}: {preco} ({variacao:+.2f}%)")
        return {"price": preco, "change_pct": variacao}
    except Exception as e:
        log(f"AVISO {nome}: {e}")
        return {"price": None, "change_pct": None}

# ── 3. AGENDA FOREXFACTORY ────────────────────────────────────────────────────
def buscar_agenda():
    try:
        from bs4 import BeautifulSoup
        hoje = datetime.now(BRT)
        data_str = hoje.strftime("%b%d.%Y").lower()
        url = f"https://www.forexfactory.com/calendar?day={data_str}"
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        eventos = []
        hora_atual = ""
        for row in soup.select("tr.calendar__row"):
            hora_el = row.select_one(".calendar__time")
            if hora_el and hora_el.text.strip():
                hora_atual = hora_el.text.strip()
            impact_el = row.select_one(".calendar__impact span")
            impacto = ""
            if impact_el:
                cls = " ".join(impact_el.get("class", []))
                if "high" in cls: impacto = "alto"
                elif "medium" in cls: impacto = "medio"
            moeda_el = row.select_one(".calendar__currency")
            moeda = moeda_el.text.strip() if moeda_el else ""
            evento_el = row.select_one(".calendar__event-title")
            evento = evento_el.text.strip() if evento_el else ""
            if evento and moeda in ["USD", "BRL", "EUR"] and impacto in ["alto", "medio"]:
                eventos.append({"time": hora_atual, "currency": moeda, "event": evento, "impact": impacto})
        log(f"Agenda: {len(eventos)} eventos")
        return eventos[:12]
    except Exception as e:
        log(f"AVISO Agenda: {e}")
        return []

# ── 4. NOTÍCIAS RSS ───────────────────────────────────────────────────────────
def buscar_noticias():
    try:
        import feedparser
        noticias = []
        feeds = [
            "https://br.investing.com/rss/news_25.rss",
            "https://br.investing.com/rss/news_14.rss",
        ]
        for url in feeds:
            feed = feedparser.parse(url)
            for entry in feed.entries[:4]:
                noticias.append(entry.get("title", ""))
        log(f"Noticias: {len(noticias)} itens")
        return noticias[:8]
    except Exception as e:
        log(f"AVISO Noticias: {e}")
        return []

# ── 5. GEMINI ─────────────────────────────────────────────────────────────────
def gerar_com_gemini(dados):
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            log("ERRO: GEMINI_API_KEY nao encontrada nos Secrets.")
            return None

        hoje_str = datetime.now(BRT).strftime("%d/%m/%Y")
        fg = dados["fear_greed"]
        dxy = dados["dxy"]
        vix = dados["vix"]
        ibov = dados["ibov"]
        usd = dados["usdbrl"]
        sp = dados["sp500"]
        nq = dados["nasdaq"]
        agenda = dados["agenda"]
        noticias = dados["noticias"]

        def fmt(d, decimais=2):
            if d.get("price") is None: return "N/A"
            sinal = "+" if d["change_pct"] >= 0 else ""
            return f"{d['price']} ({sinal}{d['change_pct']:.2f}%)"

        agenda_txt = "\n".join([f"  {e['time']} [{e['currency']}] {e['event']} (impacto: {e['impact']})" for e in agenda]) or "  Sem eventos relevantes."
        noticias_txt = "\n".join([f"  - {n}" for n in noticias]) or "  Sem notícias."

        prompt = f"""Você é um analista de mercado brasileiro experiente. Com base nos dados abaixo, escreva um morning call profissional e objetivo para o dia {hoje_str}.

INDICADORES:
- IBOV: {fmt(ibov)}
- USD/BRL: {fmt(usd)}
- S&P 500: {fmt(sp)}
- Nasdaq: {fmt(nq)}
- DXY: {fmt(dxy)}
- VIX: {fmt(vix)}
- Fear & Greed: {fg.get('value', 'N/A')} ({fg.get('label', 'N/A')})

AGENDA ECONÔMICA HOJE:
{agenda_txt}

PRINCIPAIS NOTÍCIAS:
{noticias_txt}

Escreva o morning call com EXATAMENTE esta estrutura:

[CONTEXTO GLOBAL]
Analise o cenário externo e as correlações entre DXY, VIX, S&P e impacto no Brasil.

[IBOVESPA]
Analise o índice, nível atual, suportes e resistências relevantes.

[DÓLAR]
Analise USD/BRL, contexto do DXY e perspectiva para o real.

[AGENDA DO DIA]
Destaque os eventos mais relevantes e o que esperar.

[VIÉS DO DIA]
Conclua com o viés direcional: ALTISTA, BAIXISTA ou NEUTRO — com justificativa clara e objetiva baseada nos drivers acima."""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1500}
        }
        r = requests.post(url, json=payload, timeout=30)
        result = r.json()

        if "candidates" not in result:
            log(f"ERRO Gemini: {result}")
            return None

        texto = result["candidates"][0]["content"]["parts"][0]["text"]
        log(f"Morning call gerado: {len(texto)} chars")
        return texto

    except Exception as e:
        log(f"ERRO Gemini: {e}")
        return None

# ── 6. PARSEAR TEXTO DA IA ────────────────────────────────────────────────────
def parsear(texto):
    if not texto:
        return [], "Neutro", ""

    secoes = {"CONTEXTO GLOBAL": "", "IBOVESPA": "", "DÓLAR": "", "AGENDA DO DIA": "", "VIÉS DO DIA": ""}
    atual = None
    for linha in texto.split("\n"):
        linha_up = linha.strip().upper()
        encontrou = False
        for sec in secoes:
            if sec in linha_up:
                atual = sec
                encontrou = True
                break
        if not encontrou and atual:
            secoes[atual] += linha + "\n"

    paragrafos = []
    for sec in ["CONTEXTO GLOBAL", "IBOVESPA", "DÓLAR", "AGENDA DO DIA"]:
        txt = secoes[sec].strip()
        if txt:
            paragrafos.append(f"**{sec}**\n{txt}")

    vies_txt = secoes["VIÉS DO DIA"].strip()
    vies = "Neutro"
    for palavra in ["ALTISTA", "BAIXISTA", "NEUTRO"]:
        if palavra in vies_txt.upper():
            vies = palavra.capitalize()
            break

    return paragrafos, vies, vies_txt

# ── 7. MAIN ───────────────────────────────────────────────────────────────────
def salvar_dados():
    log("=" * 50)
    log("Morning Call — Gemini + Fontes públicas")
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
    agenda   = buscar_agenda()
    noticias = buscar_noticias()

    dados = {
        "fear_greed": fg, "dxy": dxy, "vix": vix,
        "ibov": ibov, "usdbrl": usd, "sp500": sp, "nasdaq": nq,
        "agenda": agenda, "noticias": noticias,
    }

    texto = gerar_com_gemini(dados)
    paragrafos, vies, vies_txt = parsear(texto)

    if not paragrafos:
        paragrafos = ["⚠️ Não foi possível gerar a análise hoje. Verifique os logs."]

    agenda_fmt = [{"time": e["time"], "event": f"[{e['currency']}] {e['event']}"} for e in agenda]
    if not agenda_fmt:
        agenda_fmt = [{"time": "—", "event": "Sem eventos de alto impacto hoje"}]

    tags = [f"Viés {vies}"]
    if ibov.get("change_pct") is not None:
        d = "▲" if ibov["change_pct"] >= 0 else "▼"
        tags.append(f"IBOV {d} {ibov['change_pct']:+.2f}%")
    if usd.get("price") is not None:
        tags.append(f"USD/BRL R$ {usd['price']:.2f}")

    json_final = {
        "date": agora.strftime("%d/%m/%Y"),
        "lastUpdate": agora_str,
        "lastFetch": agora_str,
        "title": f"Morning Call · {agora.strftime('%d/%m')}",
        "vies": vies,
        "vies_txt": vies_txt,
        "tags": tags,
        "tags_tipados": [{"tipo": vies.lower(), "label": tags[0]}],
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
        },
        "scrape_ok": bool(texto),
        "feriado_aviso": None,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(json_final, f, ensure_ascii=False, indent=2)

    log(f"data.json salvo! Viés: {vies} | Parágrafos: {len(paragrafos)} | Agenda: {len(agenda_fmt)}")
    log("=" * 50)

if __name__ == "__main__":
    salvar_dados()
