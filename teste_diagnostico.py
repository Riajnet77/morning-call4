import os
from playwright.sync_api import sync_playwright

def testar_fluxo():
    EMAIL = os.getenv("TRADERBI_EMAIL")
    PASSWORD = os.getenv("TRADERBI_PASSWORD")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("--- PASSO 1: Acessando a página ---")
        page.goto("https://app.traderbi.com.br/noticias", wait_until="networkidle")

        if "login" in page.url or page.locator("input[type='email']").count() > 0:
            print("--- PASSO 2: Fazendo Login ---")
            page.locator("input[type='email']").fill(EMAIL)
            page.locator("input[type='password']").fill(PASSWORD)
            page.locator("button[type='submit']").click()
            page.wait_for_url("**/noticias", timeout=15000)
            print("Login confirmado!")

        print("--- PASSO 3: Clicando na Aba de Análises ---")
        aba = page.locator("button:has-text('Análises TraderBI')")
        aba.wait_for(state="visible", timeout=10000)
        aba.click()
        page.wait_for_timeout(2000)

        print("--- PASSO 4: Clicando no Primeiro Card ---")
        card = page.locator("div:has-text('☀️ Aquecimento do Pregão')").first
        card.wait_for(state="visible", timeout=10000)
        card.click()
        
        # Espera crucial para o Next.js injetar os dados na tela
        page.wait_for_timeout(4000)

        print("--- PASSO 5: DIAGNÓSTICO DO HTML CAPTURADO ---")
        # Vamos capturar o texto bruto da tag BODY inteira para ver o que existe de fato ali dentro
        texto_corpo = page.locator("body").text_content()
        
        print(f"Tamanho do texto capturado: {len(texto_corpo)} caracteres.")
        print("\n--- COMEÇO DO TEXTO DETECTADO NA TELA ---")
        print(texto_corpo[:2000]) # Printa os primeiros 2000 caracteres no terminal do GitHub
        print("--- FIM DO TEXTO DETECTADO ---")

        browser.close()

if __name__ == "__main__":
    testar_fluxo()
