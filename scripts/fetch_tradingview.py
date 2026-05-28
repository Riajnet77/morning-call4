#!/usr/bin/env python3
"""Script para extrair Morning Call do TradingView (Juniorwuttke)"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timezone, timedelta
import os
import sys

TV_USER = "Juniorwuttke"
TV_URL = "https://br.tradingview.com/u/" + TV_USER + "/#published-charts"
REPO_PATH = os.environ.get("GITHUB_WORKSPACE", ".")
LAST_POST_FILE = os.path.join(REPO_PATH, ".last_post_id")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Referer": "https://br.tradingview.com/"
}

def get_latest_idea():
    try:
        response = requests.get(TV_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Tenta extrair de JSON embeddado
        scripts = soup.find_all("script", type="application/json")
        for script in scripts:
            try:
                data = json.loads(script.string)
                if "props" in data and "pageProps" in data.get("props", {}):
                    ideas = data["props"]["pageProps"].get("ideas", [])
                    if ideas:
                        return ideas[0]
            except:
                continue

        # Fallback: meta description
        meta = soup.find("meta", {"name": "description"})
        if meta:
            return {
                "id": "fallback_" + datetime.now().strftime("%Y%m%d"),
                "title": meta.get("content", "Morning Call")[:100],
                "description": meta.get("content", ""),
                "published": datetime.now().isoformat()
            }
        return None
    except Exception as e:
        print("Erro: " + str(e), file=sys.stderr)
        return None

def has_new_post(idea):
    if not idea:
        return False
    post_id = idea.get("id", "")
    try:
        with open(LAST_POST_FILE, "r") as f:
            last_id = f.read().strip()
    except FileNotFoundError:
        last_id = ""

    now = datetime.now(timezone(timedelta(hours=-3)))
    pub_date = idea.get("published", "")
    if pub_date:
        try:
            pub_dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
            pub_dt = pub_dt.astimezone(timezone(timedelta(hours=-3)))
            if pub_dt.date() == now.date() and pub_dt.hour >= 7:
                return post_id != last_id
        except:
            pass
    return post_id != last_id and post_id != ""

def generate_html(idea):
    title = idea.get("title", "Morning Call")
    description = idea.get("description", "")
    published = idea.get("published", datetime.now().isoformat())

    try:
        dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        dt = dt.astimezone(timezone(timedelta(hours=-3)))
        date_str = dt.strftime("%d/%m/%Y - %H:%M BRT")
    except:
        date_str = datetime.now().strftime("%d/%m/%Y - %H:%M BRT")

    lines = description.split("\n") if description else []
    breaking, high, medium, low = [], [], [], []

    for line in lines[:50]:
        line = line.strip()
        if not line:
            continue
        text_lower = line.lower()
        if any(w in text_lower for w in ["breaking", "urgente", "ataque", "guerra", "crise"]):
            breaking.append(line)
        elif any(w in text_lower for w in ["alto", "importante", "fed", "bce", "pce", "ipca"]):
            high.append(line)
        elif any(w in text_lower for w in ["medio", "relevante", "dados", "indicador"]):
            medium.append(line)
        else:
            low.append(line)

    # Gera HTML
    html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Morning Call - """ + date_str.split(" - ")[0] + """</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0d0d0d;--card:#141414;--text:#fff;--text2:#a0a0a0;--muted:#666;--green:#00e676;--red:#ff1744;--yellow:#ffc400;--blue:#2979ff;--orange:#ff6d00;--border:#222}
body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;line-height:1.6;max-width:420px;margin:0 auto;padding:12px}
.header{background:linear-gradient(135deg,#1a1a2e,#16213e);border-radius:16px;padding:16px;margin-bottom:12px;text-align:center}
.logo{font-family:monospace;font-size:18px;font-weight:800;letter-spacing:3px}
.logo span{color:var(--green)}
.date{font-family:monospace;font-size:12px;color:var(--text2)}
.section{margin-bottom:12px}
.title{display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:12px;margin-bottom:8px;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:1px}
.breaking{background:rgba(255,23,68,.12);color:var(--red);border:1px solid rgba(255,23,68,.2)}
.high{background:rgba(255,109,0,.12);color:var(--orange);border:1px solid rgba(255,109,0,.2)}
.medium{background:rgba(255,196,0,.12);color:var(--yellow);border:1px solid rgba(255,196,0,.2)}
.low{background:rgba(0,230,118,.12);color:var(--green);border:1px solid rgba(0,230,118,.2)}
.card{background:var(--card);border-radius:14px;padding:14px;margin-bottom:8px;border:1px solid var(--border);position:relative;overflow:hidden}
.card::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;border-radius:14px 0 0 14px}
.card.breaking::before{background:var(--red)}
.card.high::before{background:var(--orange)}
.card.medium::before{background:var(--yellow)}
.card.low::before{background:var(--green)}
.news-title{font-size:15px;font-weight:700;line-height:1.4;margin-bottom:6px}
.news-summary{font-size:13px;color:var(--text2);line-height:1.5;margin-bottom:8px}
.tags{display:flex;flex-wrap:wrap;gap:4px}
.tag{font-size:10px;font-weight:600;padding:3px 10px;border-radius:20px;background:rgba(255,255,255,.06);color:var(--muted)}
.tag-win{background:rgba(0,230,118,.15);color:var(--green)}
.tag-wdo{background:rgba(41,121,255,.15);color:var(--blue)}
.tag-brent{background:rgba(255,109,0,.15);color:var(--orange)}
.footer{text-align:center;padding:16px;font-size:10px;color:var(--muted);background:var(--card);border-radius:12px;border:1px solid var(--border)}
</style>
</head>
<body>
<div class="header">
<div class="logo">MORNING<span>CALL</span></div>
<div class="date">""" + date_str + """</div>
</div>
"""

    if breaking:
        html += "<div class="section"><div class="title breaking">🔴 Breaking News</div>"
        for item in breaking[:3]:
            html += "<div class="card breaking"><div class="news-title">" + item[:100] + "</div>"
            html += "<div class="tags"><span class="tag tag-brent">Brent</span><span class="tag tag-wdo">WDO</span></div></div>"
        html += "</div>"

    if high:
        html += "<div class="section"><div class="title high">🟠 Alto Impacto</div>"
        for item in high[:5]:
            html += "<div class="card high"><div class="news-title">" + item[:100] + "</div>"
            html += "<div class="tags"><span class="tag tag-win">WIN</span><span class="tag tag-wdo">WDO</span></div></div>"
        html += "</div>"

    if medium:
        html += "<div class="section"><div class="title medium">🟡 Médio Impacto</div>"
        for item in medium[:5]:
            html += "<div class="card medium"><div class="news-title">" + item[:100] + "</div></div>"
        html += "</div>"

    remaining = low[:10]
    if remaining:
        html += "<div class="section"><div class="title low">🟢 Contexto</div>"
        for item in remaining:
            html += "<div class="card low"><div class="news-summary">" + item[:120] + "</div></div>"
        html += "</div>"

    html += """<div class="footer">
<div style="font-weight:700;color:var(--text2);margin-bottom:4px">Fonte</div>
<div>TradingView - Juniorwuttke/ActivTrades</div>
<div style="margin-top:8px;font-size:9px;color:var(--muted)">morningcall.github.io - """ + date_str.split(" - ")[0] + """</div>
</div>
</body>
</html>"""

    return html

def save_last_post(idea):
    post_id = idea.get("id", datetime.now().strftime("%Y%m%d_%H%M%S"))
    with open(LAST_POST_FILE, "w") as f:
        f.write(post_id)

def main():
    print("🔍 Buscando ultima ideia do Juniorwuttke...")

    idea = get_latest_idea()

    if not idea:
        print("❌ Nao foi possivel extrair conteudo")
        idea = {
            "id": "fallback_" + datetime.now().strftime("%Y%m%d"),
            "title": "Morning Call - " + datetime.now().strftime("%d/%m/%Y"),
            "description": "Conteudo nao disponivel",
            "published": datetime.now().isoformat()
        }

    print("📄 Post: " + idea.get("title", "Sem titulo")[:60])

    if not has_new_post(idea):
        print("⏭️ Post ja processado. Nenhuma acao.")
        return False

    print("🆕 Novo post! Gerando HTML...")

    html_content = generate_html(idea)

    index_path = os.path.join(REPO_PATH, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print("💾 HTML salvo: " + index_path)

    save_last_post(idea)

    return True

if __name__ == "__main__":
    updated = main()
    sys.exit(0)
