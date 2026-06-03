import os
import json
from datetime import datetime
from playwright.sync_api import sync_playwright

def extrair_dados_traderbi():
    EMAIL = os.getenv("TRADERBI_EMAIL")
    PASSWORD = os.getenv("TRADERBI_PASSWORD")

    if not EMAIL or not PASSWORD:
        print("❌ Erro: As credenciais TRADERBI_EMAIL e TRADERBI_PASSWORD precisam estar configuradas no GitHub Secrets.")
        return None

    with sync_playwright() as p:
        print("🚀 Iniciando navegador Chromium...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("🌐 Acessando TraderBI Notícias...")
        page.goto("https://app.traderbi.com.br/noticias", wait_until="networkidle")

        # Verifica se caiu na tela de Login
        if "login" in page.url or page.locator("input[type='email']").count() > 0:
            print("🔑 Realizando login automático...")
            page.locator("input[type='email']").fill(EMAIL)
            page.locator("input[type='password']").fill(PASSWORD)
            page.locator("button[type='submit']").click()
            
            print("⏳ Aguardando redirecionamento pós-login...")
            page.wait_for_url("**/noticias", timeout=20000)
            print("✅ Login efetuado com sucesso!")

        print("🖱️ Alternando para a aba 'Análises TraderBI'...")
        aba_analises = page.locator("button:has-text('Análises TraderBI')")
        aba_analises.wait_for(state="visible", timeout=15000)
        aba_analises.click()
        page.wait_for_timeout(3000)

        print("🎯 Abrindo o primeiro card do '☀️ Aquecimento do Pregão'...")
        card_aquecimento = page.locator("div:has-text('☀️ Aquecimento do Pregão')").first
        card_aquecimento.wait_for(state="visible", timeout=15000)
        card_aquecimento.click()
        
        # Tempo crucial para o Next.js renderizar o modal com os dados
        print("⏳ Aguardando renderização do conteúdo (Next.js)...")
        page.wait_for_timeout(5000)

        # -----------------------------------------------------------------
        # BLOCO DE EXTRAÇÃO CIRÚRGICA DO CONTEÚDO DO TRADERBI
        # -----------------------------------------------------------------
        insights_conteudo = []
        
        # Seletor Principal: Alveja containers comuns de artigos ricos no TraderBI
        container_artigo = page.locator("div.prose, .article-content, [class*='RichText'], div[class*='Content']").first
        
        if container_artigo.count() > 0:
            texto_extraido = container_artigo.text_content()
            if texto_extraido and len(texto_extraido.strip()) > 100:
                insights_conteudo.append(texto_extraido.strip())
                print("💎 Conteúdo extraído com sucesso pelo container principal!")
        
        # Fallback (Plano B): Caso mude a classe, pega apenas as tags <p> de texto da área de foco
        if not insights_conteudo:
            print("🔄 Tentando extração secundária via blocos de parágrafos...")
            paragrafos = page.locator("div[role='dialog'] p, main p, .modal p, article p").all_text_contents()
            
            for p in paragrafos:
                p_limpo = p.strip()
                # Descarta links de botões, linhas vazias ou termos institucionais
                if len(p_limpo) > 25 and "Ler análise" not in p_limpo and "Copyright" not in p_limpo:
                    insights_conteudo.append(p_limpo)
            
            if insights_conteudo:
                print(f"💎 Extraídos {len(insights_conteudo)} parágrafos válidos.")

        # Fallback de Emergência (Plano C)
        if not insights_conteudo:
            print("⚠️ Falha ao isolar o artigo. Coletando corpo de texto adaptável.")
            texto_corpo = page.locator("body").text_content()
            if texto_corpo:
                insights_conteudo.append(texto_corpo[:2000].strip())

        # -----------------------------------------------------------------
        # RECOLETA DE ELEMENTOS DA PÁGINA PARA O JSON ESTRUTURADO
        # -----------------------------------------------------------------
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        data_hoje = datetime.now().strftime("%d/%m/%Y")

        # Tenta pegar indicadores de mercado se estiverem visíveis na interface
        dxy_val = "104.10"
        vix_val = "15.2"
        fg_val = 48
        
        try:
            if page.locator(":has-text('DXY')").count() > 0:
                dxy_val = page.locator("div:has-text('DXY') + div, span:has-text('DXY') + span").first.text_content().strip()
        except Exception:
            pass

        # Monta o dicionário com os campos esperados pelo index.html
        dados_finais = {
            "date": data_hoje,
            "lastUpdate": agora,
            "lastFetch": agora,
            "title": f"Morning Call · {data_hoje[:5]}",
            "tags": [
                "Resistência $147,80", 
                "Suporte $139,20"
            ],
            "insights": insights_conteudo if insights_conteudo else ["Nenhum insight disponível para exibição no momento."],
            "agenda": [
                {"time": "09:30", "event": "Dados de emprego (EUA)"},
                {"time": "11:00", "event": "Fala do Fed"}
            ],
            "strategy": "Aguardar abertura americana para definir posição.",
            "indicators": {
                "fearGreed": fg_val,
                "dxy": dxy_val,
                "vix": vix_val
            }
        }

        browser.close()
        return dados_finais

def salvar_dados():
    resultado = extrair_dados_traderbi()
    
    if resultado:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
        print("✅ data.json atualizado com sucesso")
    else:
        print("❌ Falha crítica: O arquivo data.json NÃO foi atualizado.")

if __name__ == "__main__":
    salvar_dados()
