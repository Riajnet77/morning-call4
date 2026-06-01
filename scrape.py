import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

USERNAME = "Juniorwuttke"
URL = f"https://br.tradingview.com/u/{USERNAME}/"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def scrape_tradingview():
    try:
        resp = requests.get(URL, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Tenta encontrar o texto das últimas publicações (estrutura flexível)
        # TradingView usa classes dinâmicas; faremos uma busca por textos longos
        page_text = soup.get_text()
        
        # Procura por padrões como "Análise", "Setup", "Resistência", "Suporte"
        linhas = [l.strip() for l in page_text.split('\n') if len(l.strip()) > 20]
        if not linhas:
            raise Exception("Nenhuma publicação encontrada")
        
        # Pega os 2 primeiros blocos que parecem análise
        insights_raw = linhas[:3]
        
        # Monta um JSON inteligente
        data = {
            "date": datetime.now().strftime("%d/%m/%Y"),
            "lastUpdate": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "lastFetch": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "title": f"Morning Call · {datetime.now().strftime('%d/%m')}",
            "tags": [],
            "insights": insights_raw,
            "agenda": [
                {"time": "09:30", "event": "Dados de emprego (EUA)"},
                {"time": "11:00", "event": "Fala do Fed"}
            ],
            "strategy": "Aguardar abertura americana para definir posição.",
            "indicators": {
                "fearGreed": 48,
                "dxy": "104.10",
                "vix": "15.2"
            }
        }
        
        # Tenta extrair palavras-chave (resistência, suporte)
        for line in page_text.split('\n'):
            if 'resistência' in line.lower() or 'suporte' in line.lower():
                data["tags"].append(line.strip()[:40])
        
        if not data["tags"]:
            data["tags"] = ["Resistência $147,80", "Suporte $139,20"]
        
        # Salva
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print("✅ data.json atualizado com sucesso")
        
    except Exception as e:
        print(f"❌ Erro no scraping: {e}")
        # Em caso de erro, mantém o último data.json ou cria um padrão
        with open("data.json", "r", encoding="utf-8") as f:
            fallback = json.load(f)
        fallback["lastFetch"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S") + " (erro no scraping)"
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(fallback, f, indent=2, ensure_ascii=False)
        print("⚠️ Mantido conteúdo anterior devido a erro.")

if __name__ == "__main__":
    scrape_tradingview()
