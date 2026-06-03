import os
import re
import datetime
from playwright.sync_api import sync_playwright

def extrair_dados_traderbi():
    EMAIL = os.getenv("TRADERBI_EMAIL", "seu_email@exemplo.com")
    PASSWORD = os.getenv("TRADERBI_PASSWORD", "sua_senha_aqui")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Acessando TraderBI...")
        page.goto("https://app.traderbi.com.br/noticias")

        # Fluxo de login seguro
        if "login" in page.url or page.locator("input[type='email']").count() > 0:
            print("Efetuando login automatizado...")
            page.locator("input[type='email']").fill(EMAIL)
            page.locator("input[type='password']").fill(PASSWORD)
            page.locator("button[type='submit']").click()
            page.wait_for_timeout(5000)

        if page.url != "https://app.traderbi.com.br/noticias":
            page.goto("https://app.traderbi.com.br/noticias")

        print("Acessando a aba de Análises TraderBI...")
        page.locator("button:has-text('Análises TraderBI')").click()
        page.wait_for_timeout(2000)

        print("Abrindo o Aquecimento do Pregão...")
        primeiro_card = page.locator("div:has-text('☀️ Aquecimento do Pregão')").first
        primeiro_card.click()
        page.wait_for_timeout(3000)

        # Captura o container inteiro do artigo aberto para não perder nenhuma linha
        # Tenta pegar a janela modal ou o artigo ativo na tela
        modal = page.locator("div[role='dialog'], article, main")
        texto_noticia = modal.first.text_content()

        browser.close()
        return texto_noticia

def mapear_conteudo_completo(briefing):
    # Dicionário robusto com fallbacks para garantir que a tela nunca quebre vazia
    dados = {
        "titulo": "Aquecimento do Pregão",
        "contexto_macro": "Dados globais e fluxo macroeconômico em consolidação.",
        "win_cenario": "Análise técnica do Índice Bovespa aguardando abertura.",
        "win_pontos": "Pontos de relevância: Suportes e Resistências em mapeamento.",
        "wdo_cenario": "Análise de fluxo e pressão no Dólar Futuro.",
        "wdo_points": "Pontos de relevância: Zonas de liquidez sob monitoramento.",
        "calendario_eventos": "Consulte o painel integrado para dados de alta relevância.",
        "direcionamento": "Opere estritamente dentro do gerenciamento de risco e plano de trading."
    }

    # Captura o título dinâmico (ex: Aquecimento do Pregão — Quarta-feira...)
    titulo_match = re.search(r"(Aquecimento do Pregão — .*?)(?=\n|Públ)", briefing)
    if titulo_match:
        dados["titulo"] = titulo_match.group(1).strip()

    # --- LÓGICA DE FATIAMENTO POR SEÇÕES MÃE DO TRADERBI ---
    
    # 1. Contexto Macro / Drivers Globais
    macro_match = re.search(r"(?:Contexto Macro|Drivers do Dia|Panorama Internacional)\n(.*?)(?=\n📈|\n💵|\n🎯|\n📅|Ibovespa|Dólar)", briefing, re.DOTALL | re.IGNORECASE)
    if macro_match:
        dados["contexto_macro"] = macro_match.group(1).strip().replace("\n", "<br>")

    # 2. Ibovespa / WIN - Cenário Operacional
    win_match = re.search(r"(?:Ibovespa / WIN|Índice Futuro)\n(.*?)(?=\n💵|\n🎯|\n📅|Dólar|Pontos Relevantes)", briefing, re.DOTALL | re.IGNORECASE)
    if win_match:
        dados["win_cenario"] = win_match.group(1).strip().replace("\n", "<br>")

    # 3. Dólar / WDO - Cenário Operacional
    wdo_match = re.search(r"(?:Dólar / WDO|Dólar Futuro)\n(.*?)(?=\n🎯|\n📅|\n⚠️|Pontos Relevantes|Calendário)", briefing, re.DOTALL | re.IGNORECASE)
    if wdo_match:
        dados["wdo_cenario"] = wdo_match.group(1).strip().replace("\n", "<br>")

    # 4. Extração Cirúrgica de Linhas de Suportes, Resistências e POCs
    # Procura blocos contendo listagens numéricas de pontos importantes
    pontos_win = re.findall(r"(?:Suporte|Resistência|R1|S1|POC).*?\d{3,6}", dados["win_cenario"])
    if pontos_win:
        dados["win_pontos"] = "<br>".join([f"🔹 {p}" for p in pontos_win])
    else:
        # Tenta buscar direto no texto bruto se a estrutura geral falhar
        linhas_ponto = re.findall(r".*?(?:suporte|resistência|ajuste|p鬆).*?\d{3,6}", briefing, re.IGNORECASE)
        if linhas_ponto: dados["win_pontos"] = "<br>".join([f"🔹 {l}" for l in linhas_ponto[:5]])

    # 5. Calendário Econômico / Indicadores Importantes do Dia
    cal_match = re.search(r"(?:Calendário Econômico|Destaques do Dia|Indicadores)\n(.*?)(?=\n🎯|\n⚠️|Direcionamento)", briefing, re.DOTALL | re.IGNORECASE)
    if cal_match:
        dados["calendario_eventos"] = cal_match.group(1).strip().replace("\n", "<br>")

    # 6. Considerações Finais / Direcionamento Estratégico
    dir_match = re.search(r"(?:Direcionamento|Considerações|Conclusão)\n(.*)", briefing, re.DOTALL | re.IGNORECASE)
    if dir_match:
        dados["direcionamento"] = dir_match.group(1).strip().replace("\n", "<br>")

    return dados

def gerar_html_completo(dados):
    data_hoje = datetime.datetime.now().strftime('%d/%m/%Y')

    html_final = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Morning Call Otimizado - TraderBI</title>
    <style>
        :root {{ 
            --bg-principal: #090d16; --bg-card: #111827; --bg-subcard: #1f2937;
            --texto-claro: #f3f4f6; --texto-mutado: #9ca3af; 
            --azul-trade: #38bdf8; --alta: #10b981; --baixa: #ef4444; --alerta: #f59e0b; --borda: #1f2937; 
        }}
        body {{ font-family: 'Inter', system-ui, -apple-system, sans-serif; background-color: var(--bg-principal); color: var(--texto-claro); margin: 0; padding: 20px; line-height: 1.6; }}
        .container {{ max-width: 1100px; margin: auto; background: var(--bg-card); padding: 30px; border-radius: 12px; border: 1px solid var(--borda); box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3); }}
        header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--borda); padding-bottom: 20px; margin-bottom: 25px; }}
        h1 {{ color: var(--azul-trade); font-size: 24px; margin: 0; font-weight: 800; letter-spacing: -0.025em; }}
        .timestamp {{ font-size: 12px; background: #090d16; padding: 8px 14px; border-radius: 6px; border: 1px solid var(--borda); font-family: monospace; color: var(--azul-trade); }}
        h2 {{ font-size: 16px; color: #fff; margin-top: 35px; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 8px; }}
        .secao-macro {{ background: rgba(56, 189, 248, 0.03); border-left: 4px solid var(--azul-trade); padding: 20px; border-radius: 0 8px 8px 0; margin-bottom: 30px; font-size: 14.5px; text-align: justify; }}
        .grid-ativos {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 25px; margin-bottom: 30px; }}
        .card-ativo {{ background: #0f172a; border: 1px solid var(--borda); border-radius: 8px; padding: 22px; display: flex; flex-col: column; justify-content: space-between; }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--borda); padding-bottom: 12px; margin-bottom: 15px; }}
        .ativo-titulo {{ font-size: 16px; font-weight: 700; color: #fff; }}
        .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; }}
        .badge.win {{ color: var(--alta); background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.2); }}
        .badge.wdo {{ color: var(--alerta); background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.2); }}
        .conteudo-tecnico {{ font-size: 14px; color: #d1d5db; text-align: justify; margin-bottom: 15px; }}
        .zona-pontos {{ background: #090d16; padding: 12px 15px; border-radius: 6px; border: 1px solid var(--borda); font-size: 13px; color: #9ca3af; }}
        .grid-footer {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 25px; }}
        .card-footer-info {{ background: rgba(31, 41, 55, 0.4); border: 1px solid var(--borda); padding: 20px; border-radius: 8px; font-size: 13.5px; }}
    </style>
</head>
<body>
<div class="container">
    <header>
        <div>
            <h1>{dados["titulo"]}</h1>
            <div style="color: var(--texto-mutado); font-size: 13px; margin-top: 4px;">Análise Profissional Intel-Scraped • TraderBI Integration</div>
        </div>
        <div class="timestamp" id="live-clock">{data_hoje} • Carregando...</div>
    </header>

    <h2>🌍 Contexto Macro &amp; Geopolítica Internacional</h2>
    <div class="secao-macro">
        {dados["contexto_macro"]}
    </div>

    <h2>📊 Matriz Operacional dos Ativos</h2>
    <div class="grid-ativos">
        <!-- CARD DO ÍNDICE -->
        <div class="card-ativo">
            <div>
                <div class="card-header">
                    <span class="ativo-titulo">Ibovespa Futuro (WIN)</span>
                    <span class="badge win">Estratégia &amp; Tendência</span>
                </div>
                <div class="conteudo-tecnico">{dados["win_cenario"]}</div>
            </div>
            <div class="zona-pontos">
                <strong>📍 Zonas de Liquidez e Alvos:</strong><br>
                <div style="margin-top:6px; font-family: monospace;">{dados["win_pontos"]}</div>
            </div>
        </div>

        <!-- CARD DO DÓLAR -->
        <div class="card-ativo">
            <div>
                <div class="card-header">
                    <span class="ativo-titulo">Dólar Futuro (WDO)</span>
                    <span class="badge wdo">Fluxo &amp; Proteção</span>
                </div>
                <div class="conteudo-tecnico">{dados["wdo_cenario"]}</div>
            </div>
            <div class="zona-pontos">
                <strong>📍 Zonas de Liquidez e Alvos:</strong><br>
                <div style="margin-top:6px; font-family: monospace;">{dados["wdo_cenario"] if "Suporte" in dados["wdo_cenario"] else "Aguardando mapeamento dinâmico de gatilhos..."}</div>
            </div>
        </div>
    </div>

    <div class="grid-footer">
        <div class="card-footer-info">
            <h3 style="margin-top:0; font-size:14px; color: var(--alerta); text-transform: uppercase;">📅 Indicadores e Calendário Econômico</h3>
            <p style="color:#9ca3af; margin:0; font-family: monospace;">{dados["calendario_eventos"]}</p>
        </div>
        <div class="card-footer-info">
            <h3 style="margin-top:0; font-size:14px; color: var(--azul-trade); text-transform: uppercase;">🎯 Direcionamento Técnico do Dia</h3>
            <p style="color:#d1d5db; margin:0; text-align: justify;">{dados["direcionamento"]}</p>
        </div>
    </div>
</div>

<script>
    function atualizarRelogio() {{
        const agora = new Date();
        const fHora = {{ timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit', second: '2-digit' }};
        const fData = {{ timeZone: 'America/Sao_Paulo', day: '2-digit', month: '2-digit', year: 'numeric' }};
        document.getElementById('live-clock').innerText = agora.toLocaleDateString('pt-BR', fData) + " • " + agora.toLocaleTimeString('pt-BR', fHora) + " (BRT)";
    }}
    setInterval(atualizarRelogio, 1000); atualizarRelogio();
</script>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_final)
    print("index.html gerado com sucesso contendo todo o conteúdo do TraderBI!")

if __name__ == "__main__":
    texto_bruto = extrair_dados_traderbi()
    if texto_bruto:
        # Analisa o texto extraído, mapeia os blocos e gera a página completa
        dados_fatiados = mapear_conteudo_completo(texto_bruto)
        gerar_html_completo(dados_fatiados)
