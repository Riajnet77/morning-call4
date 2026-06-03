import os
import re
import datetime
from playwright.sync_api import sync_playwright

def extrair_dados_traderbi():
    # Puxa credenciais seguras do ambiente (configuradas no GitHub Secrets)
    EMAIL = os.getenv("TRADERBI_EMAIL", "seu_email@exemplo.com")
    PASSWORD = os.getenv("TRADERBI_PASSWORD", "sua_senha_aqui")

    with sync_playwright() as p:
        # Abre o navegador em segundo plano
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Acessando TraderBI...")
        page.goto("https://app.traderbi.com.br/noticias")

        # 1. Realiza o fluxo de Login (se aplicável)
        if "login" in page.url or page.locator("input[type='email']").count() > 0:
            print("Efetuando login automatizado...")
            page.locator("input[type='email']").fill(EMAIL)
            page.locator("input[type='password']").fill(PASSWORD)
            page.locator("button[type='submit']").click()
            page.wait_for_timeout(5000)  # Aguarda 5s para consolidação da sessão

        # Garante que está na página correta após o login
        if page.url != "https://app.traderbi.com.br/noticias":
            page.goto("https://app.traderbi.com.br/noticias")

        print("Navegando até a aba de Análises...")
        # Clica explicitamente no botão correspondente à aba 'Análises TraderBI'
        page.locator("button:has-text('Análises TraderBI')").click()
        page.wait_for_timeout(2000)

        print("Abrindo o briefing mais recente...")
        # Localiza o primeiro card '☀️ Aquecimento do Pregão' dentro da listagem
        primeiro_card = page.locator("div:has-text('☀️ Aquecimento do Pregão')").first
        primeiro_card.click()
        page.wait_for_timeout(3000)

        # Captura o texto completo da análise renderizada na tela modal/página
        # Nota: Ajusta o seletor abaixo caso o texto abra em um container específico
        texto_noticia = page.locator("main").text_content()

        browser.close()
        return texto_noticia

def processar_e_gerar_html(briefing):
    # Dicionário para armazenar os blocos de texto extraídos via Expressões Regulares
    dados = {
        "geopolitico": "Desenvolvimentos de última hora ditam o tom do mercado internacional.",
        "win_detalhes": "Aguardando definição técnica no intraday.",
        "wdo_detalhes": "Curva futura operando sob pressão de fluxo.",
        "win_range": "Mínimas e máximas da última sessão técnica.",
        "wdo_range": "Patamares de troca sob monitoramento."
    }

    # Regex para fatiar inteligentemente o briefing baseado na sua estrutura padrão
    geo_match = re.search(r"Contexto Macro\n(.*?)(?=\n📈|\n💵|\n⚠️)", briefing, re.DOTALL)
    win_match = re.search(r"Ibovespa / WIN\n(.*?)(?=\n💵|\n⚠️|\n🔍)", briefing, re.DOTALL)
    wdo_match = re.search(r"Dólar / WDO\n(.*?)(?=\n⚠️|\n🔍)", briefing, re.DOTALL)

    if geo_match: dados["geopolitico"] = geo_match.group(1).strip()
    if win_match: dados["win_detalhes"] = win_match.group(1).strip()
    if wdo_match: dados["wdo_detalhes"] = wdo_match.group(1).strip()

    # Tenta extrair Ranges Técnicos explícitos baseados em menções numéricas
    range_win = re.search(r"amplitude entre ([\d\.]+) e ([\d\.]+)", briefing)
    if range_win: dados["win_range"] = f"{range_win.group(1)} — {range_win.group(2)} pontos"

    data_hoje = datetime.datetime.now().strftime('%d/%m/%Y')

    # Injeta a extração cirúrgica direto na sua interface limpa e otimizada
    html_final = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Morning Call - Aquecimento do Pregão</title>
    <style>
        :root {{ --bg-principal: #0b0f19; --bg-card: #151c2c; --texto-claro: #f1f5f9; --texto-mutado: #64748b; --azul-trade: #38bdf8; --alta: #22c55e; --baixa: #ef4444; --alerta: #f59e0b; --borda: #1e293b; }}
        body {{ font-family: 'Segoe UI', sans-serif; background-color: var(--bg-principal); color: var(--texto-claro); margin: 0; padding: 15px; line-height: 1.5; }}
        .container {{ max-width: 1200px; margin: auto; background: var(--bg-card); padding: 25px; border-radius: 8px; border: 1px solid var(--borda); }}
        header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--borda); padding-bottom: 15px; margin-bottom: 25px; }}
        h1 {{ color: var(--azul-trade); font-size: 22px; margin: 0; text-transform: uppercase; }}
        .timestamp {{ font-size: 13px; background: #0b0f19; padding: 6px 12px; border-radius: 4px; border: 1px solid var(--borda); font-weight: bold; }}
        h2 {{ font-size: 16px; color: var(--azul-trade); margin-top: 30px; margin-bottom: 15px; text-transform: uppercase; border-left: 4px solid var(--azul-trade); padding-left: 10px; }}
        .callout-urgente {{ background: rgba(239, 68, 68, 0.1); border-left: 4px solid var(--baixa); padding: 15px; border-radius: 4px; margin-bottom: 25px; }}
        .callout-urgente h3 {{ margin: 0 0 5px 0; color: var(--baixa); font-size: 15px; text-transform: uppercase; }}
        .grid-vies {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 25px; }}
        .card-vies {{ background: #0b0f19; border: 1px solid var(--borda); border-radius: 6px; padding: 18px; }}
        .card-header-vies {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--borda); padding-bottom: 10px; margin-bottom: 12px; }}
        .badge-vies {{ padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; text-transform: uppercase; }}
        .badge-vies.venda {{ color: var(--baixa); background: rgba(239, 68, 68, 0.15); }}
        .badge-vies.compra {{ color: var(--alta); background: rgba(34, 197, 94, 0.15); }}
        .grid-atencao {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px; }}
        .card-atencao {{ background: rgba(56, 189, 248, 0.03); border: 1px solid var(--borda); border-radius: 6px; padding: 15px; }}
        .card-atencao h4 {{ margin: 0 0 8px 0; color: var(--azul-trade); font-size: 13px; text-transform: uppercase; }}
        .card-atencao p {{ margin: 0; font-size: 12.5px; color: #94a3b8; text-align: justify; }}
    </style>
</head>
<body>
<div class="container">
    <header>
        <div>
            <h1>🌅 Aquecimento do Pregão</h1>
            <div style="color: var(--texto-mutado); font-size: 12px; margin-top: 2px;">Análise Operacional Automática • TraderBI</div>
        </div>
        <div class="timestamp" id="live-clock">{data_hoje} • Aguardando...</div>
    </header>

    <div class="callout-urgente">
        <h3>🚨 Contexto Macro / Drivers do Dia</h3>
        <p>{dados["geopolitico"]}</p>
    </div>

    <h2>📈 Matriz Técnica e Viés Operacional</h2>
    <div class="grid-vies">
        <div class="card-vies">
            <div class="card-header-vies">
                <span style="font-weight:bold;">Índice Futuro (WIN)</span>
                <span class="badge-vies venda">Dinâmica Intraday</span>
            </div>
            <div style="font-size:13px; color:#94a3b8; margin-bottom:10px;">📌 <strong>Range:</strong> {dados["win_range"]}</div>
            <p style="font-size: 13px; margin: 0; color: #cbd5e1; text-align: justify;">{dados["win_detalhes"]}</p>
        </div>

        <div class="card-vies">
            <div class="card-header-vies">
                <span style="font-weight:bold;">Dólar Futuro (WDO)</span>
                <span class="badge-vies compra">Fluxo Cambial</span>
            </div>
            <div style="font-size:13px; color:#94a3b8; margin-bottom:10px;">📌 <strong>Cotação Base:</strong> Monitoramento Ativo</div>
            <p style="font-size: 13px; margin: 0; color: #cbd5e1; text-align: justify;">{dados["wdo_detalhes"]}</p>
        </div>
    </div>

    <h2>🔍 Monitor de Riscos e Armadilhas Técnicas</h2>
    <div class="grid-atencao">
        <div class="card-atencao">
            <h4>⚠️ Falsos Rompimentos</h4>
            <p>Em janelas de alta volatilidade motivada por notícias externas, os extremos de suportes e resistências operam sob risco de falsos breakouts. Aguarde a validação institucional pelo volume antes de assumir posições contrárias.</p>
        </div>
        <div class="card-atencao">
            <h4>🔄 Correlações Cruzadas</h4>
            <p>Monitore o comportamento casado entre o Petróleo e o índice de força do Dólar global (DXY). Padrões direcionais unidirecionais reduzem as taxas de acerto de operações puramente gráficas.</p>
        </div>
    </div>
</div>

<script>
    function relogioBrasilia() {{
        const agora = new Date();
        const opcoesHora = {{ timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit', second: '2-digit' }};
        const opcoesData = {{ timeZone: 'America/Sao_Paulo', day: '2-digit', month: '2-digit', year: 'numeric' }};
        document.getElementById('live-clock').innerText = agora.toLocaleDateString('pt-BR', opcoesData) + " • " + agora.toLocaleTimeString('pt-BR', opcoesHora) + " (BRT)";
    }}
    setInterval(relogioBrasilia, 1000); relogioBrasilia();
</script>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_final)
    print("index.html atualizado com sucesso!")

if __name__ == "__main__":
    conteudo_bruto = extrair_dados_traderbi()
    if conteudo_bruto:
        processar_e_gerar_html(conteudo_bruto)
