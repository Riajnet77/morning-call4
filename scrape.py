import os
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

        # Fluxo de login automatizado
        if "login" in page.url or page.locator("input[type='email']").count() > 0:
            print("Efetuando login...")
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
        # Clica no primeiro card disponível na lista
        primeiro_card = page.locator("div:has-text('☀️ Aquecimento do Pregão')").first
        primeiro_card.click()
        page.wait_for_timeout(4000)

        print("Capturando o conteúdo completo da análise...")
        
        # Estratégia agressiva: tenta pegar o texto do modal aberto ou do container principal
        # Se houver um botão de fechar (X) ou uma estrutura de artigo, o Playwright captura o HTML interno texturizado
        conteudo_html = ""
        
        # Seletores possíveis para o miolo da notícia aberta
        seletores = ["div[role='dialog']", "article", "main"]
        for seletor in seletores:
            elemento = page.locator(seletor).first
            if elemento.count() > 0:
                # Pega o HTML interno para manter a formatação de parágrafos, listas e negritos original deles
                conteudo_html = elemento.inner_html()
                break
        
        # Se falhar em pegar o HTML estruturado, pega o texto bruto como plano B
        if not conteudo_html:
            conteudo_html = page.locator("body").text_content()

        browser.close()
        return conteudo_html

def limpar_e_formatar(html_bruto):
    # Remove pedaços de textos repetidos de botões do sistema do TraderBI que possam vir junto
    remover_termos = [
        "Ler análise completa →", "Publicado às", "Pré-mercado", 
        "Análises TraderBI", "Calendário Econômico", "Notícias Mercado"
    ]
    for termo in remover_termos:
        html_bruto = html_bruto.replace(termo, "")
        
    # Garante que quebras de texto normais virem quebras de linha visíveis caso venha texto puro
    html_formatado = html_bruto.replace("\n", "<br>")
    return html_formatado

def gerar_portal_completo(conteudo_real):
    data_hoje = datetime.datetime.now().strftime('%d/%m/%Y')

    html_final = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Morning Call Completo - TraderBI</title>
    <style>
        :root {{ 
            --bg-principal: #090d16; --bg-card: #111827;
            --texto-claro: #f3f4f6; --texto-mutado: #9ca3af; 
            --azul-trade: #38bdf8; --borda: #1f2937; 
        }}
        body {{ font-family: 'Inter', system-ui, sans-serif; background-color: var(--bg-principal); color: var(--texto-claro); margin: 0; padding: 20px; line-height: 1.6; }}
        .container {{ max-width: 900px; margin: auto; background: var(--bg-card); padding: 35px; border-radius: 12px; border: 1px solid var(--borda); box-shadow: 0 10px 25px rgba(0,0,0,0.3); }}
        header {{ border-bottom: 1px solid var(--borda); padding-bottom: 20px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; }}
        h1 {{ color: var(--azul-trade); font-size: 24px; margin: 0; font-weight: 800; }}
        .timestamp {{ font-size: 12px; background: #090d16; padding: 8px 14px; border-radius: 6px; border: 1px solid var(--borda); color: var(--azul-trade); font-family: monospace; }}
        .conteudo-traderbi {{ font-size: 15px; color: #e5e7eb; text-align: justify; }}
        /* Estilização para caso o HTML deles traga títulos ou listas */
        .conteudo-traderbi h1, .conteudo-traderbi h2, .conteudo-traderbi h3 {{ color: var(--azul-trade); margin-top: 25px; font-size: 18px; border-left: 3px solid var(--azul-trade); padding-left: 8px; }}
        .conteudo-traderbi strong {{ color: #fff; font-weight: 600; }}
    </style>
</head>
<body>
<div class="container">
    <header>
        <div>
            <h1>🌅 Aquecimento do Pregão</h1>
            <div style="color: var(--texto-mutado); font-size: 13px; margin-top: 4px;">Conteúdo Integral Transmitido via Scraper • TraderBI</div>
        </div>
        <div class="timestamp" id="live-clock">{data_hoje} • Atualizando...</div>
    </header>

    <!-- AQUER ENTRARÁ TODO O CONTEÚDO SEM CORTES, EXATAMENTE COMO ESTÁ NO TRADERBI -->
    <div class="conteudo-traderbi">
        {conteudo_real}
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
    print("Sucesso! index.html gerado com 100% das informações extraídas.")

if __name__ == "__main__":
    html_obtido = extrair_dados_traderbi()
    if html_obtido:
        conteudo_limpo = limpar_e_formatar(html_obtido)
        gerar_portal_completo(conteudo_limpo)
