import os
import json
import re
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def extrair_dados_traderbi():
    EMAIL = os.getenv("TRADERBI_EMAIL")
    PASSWORD = os.getenv("TRADERBI_PASSWORD")

    if not EMAIL or not PASSWORD:
        log("ERRO: Credenciais TRADERBI_EMAIL e TRADERBI_PASSWORD nao encontradas nos Secrets.")
        return None

    resultado = {
        "date": datetime.now().strftime("%d/%m/%Y"),
        "lastUpdate": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "title": f"Morning Call \u00b7 {datetime.now().strftime('%d/%m')}",
        "insights_raw": "",
        "agenda": [],
        "tags": [],
        "indicators": {"fearGreed": None, "dxy": None, "vix": None},
        "strategy": "",
        "scrape_ok": False,
    }

    with sync_playwright() as p:
        log("Iniciando Chromium headless...")
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        # ── 1. LOGIN ──────────────────────────────────────────────────────────────
        log("Navegando para /noticias ...")
        page.goto("https://app.traderbi.com.br/noticias", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        if "login" in page.url.lower() or page.locator("input[type='email']").count() > 0:
            log("Tela de login detectada - fazendo login...")
            page.locator("input[type='email']").fill(EMAIL)
            page.locator("input[type='password']").fill(PASSWORD)
            page.locator("button[type='submit']").click()

            # Aguarda o formulario sumir (funciona independente da URL de redirect)
            try:
                page.locator("input[type='email']").wait_for(state="hidden", timeout=25000)
                log("Login bem-sucedido (formulario desapareceu)!")
            except PlaywrightTimeout:
                url_atual = page.url.lower()
                if "login" not in url_atual and "signin" not in url_atual:
                    log(f"Login provavelmente ok - URL atual: {page.url}")
                else:
                    log("ERRO: Login falhou - ainda na tela de login apos 25s.")
                    page.screenshot(path="debug_login.png")
                    browser.close()
                    return resultado

            # Aguarda pagina destino carregar
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)

            # Se caiu em outra pagina (ex: /dashboard), navega para /noticias
            if "/noticias" not in page.url:
                log(f"Redirect foi para {page.url} - navegando para /noticias...")
                page.goto("https://app.traderbi.com.br/noticias", wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(2000)

            log(f"URL final pos-login: {page.url}")

        page.wait_for_timeout(3000)

        # ── 2. ABA ANALISES TRADERBI ──────────────────────────────────────────────
        log("Buscando aba 'Analises TraderBI'...")
        try:
            aba = page.locator("button, a, [role='tab']").filter(
                has_text=re.compile(r"An.lises TraderBI", re.IGNORECASE)
            ).first
            aba.wait_for(state="visible", timeout=12000)
            aba.click()
            page.wait_for_timeout(2500)
            log("Aba clicada.")
        except Exception as e:
            log(f"AVISO: Nao encontrou aba 'Analises TraderBI': {e}")

        # ── 3. CARD AQUECIMENTO DO PREGAO ─────────────────────────────────────────
        log("Buscando card 'Aquecimento do Pregao'...")
        card = None
        seletores_card = [
            "text=Aquecimento do Preg\u00e3o",
            "[class*='card']:has-text('Aquecimento')",
            "div:has-text('Aquecimento do Preg\u00e3o')",
            "article:has-text('Aquecimento')",
            ":has-text('Aquecimento')",
        ]
        for sel in seletores_card:
            try:
                c = page.locator(sel).first
                if c.count() > 0:
                    c.wait_for(state="visible", timeout=5000)
                    card = c
                    log(f"Card encontrado com seletor: {sel}")
                    break
            except Exception:
                continue

        if card is None:
            log("ERRO: Card 'Aquecimento do Pregao' nao encontrado. Salvando screenshot...")
            page.screenshot(path="debug_screenshot.png")
            # Salva HTML para diagnostico
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            browser.close()
            return resultado

        card.click()
        log("Card clicado. Aguardando conteudo carregar...")
        page.wait_for_timeout(5000)

        # ── 4. EXTRACAO DO CONTEUDO ───────────────────────────────────────────────
        log("Iniciando extracao de conteudo...")
        conteudo_texto = ""

        seletores_conteudo = [
            "div.prose",
            "[class*='prose']",
            "[class*='article']",
            "[class*='richtext']",
            "[class*='rich-text']",
            "[class*='content']",
            "[class*='body']",
            "[class*='texto']",
            "[class*='conteudo']",
            "[class*='post']",
            "article",
            "[role='article']",
            "[role='dialog'] div",
            "[data-radix-scroll-area-viewport]",
        ]

        for sel in seletores_conteudo:
            try:
                els = page.locator(sel).all()
                for el in els:
                    txt = (el.text_content() or "").strip()
                    if len(txt) > 300:
                        conteudo_texto = txt
                        log(f"Conteudo extraido via '{sel}' ({len(txt)} chars).")
                        break
                if conteudo_texto:
                    break
            except Exception:
                continue

        # Fallback: pega todo o main/body
        if not conteudo_texto:
            log("Fallback: extraindo texto completo da pagina...")
            for sel_area in ["main", "[role='main']", "#__next", "body"]:
                try:
                    area = page.locator(sel_area).first
                    if area.count() > 0:
                        txt = (area.text_content() or "").strip()
                        if len(txt) > 200:
                            conteudo_texto = txt
                            log(f"Fallback usou '{sel_area}' ({len(txt)} chars).")
                            break
                except Exception:
                    continue

        resultado["insights_raw"] = conteudo_texto
        resultado["scrape_ok"] = len(conteudo_texto) > 100

        browser.close()

    log(f"Scrape concluido. Conteudo: {len(resultado['insights_raw'])} chars.")
    return resultado


def limpar_texto(texto):
    if not texto:
        return ""

    padroes_corte = [
        r"Copyright \u00a9",
        r"Todos os direitos reservados",
        r"Pol\u00edtica de Privacidade",
        r"Termos de Uso",
        r"\u00a9 20\d\d",
        r"TradingView",
        r"FactSet",
        r"Dados de mercado selecionados",
        r"Sobre a empresa",
        r"Mais do que um produto",
        r"Ingressou em",
        r"Seguindo\d",
        r"Seguidores\d",
    ]
    for padrao in padroes_corte:
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            texto = texto[:match.start()].strip()

    linhas = texto.split("\n")
    linhas_validas = [l.strip() for l in linhas if len(l.strip()) > 20]
    return "\n\n".join(linhas_validas)


def extrair_suportes_resistencias(texto):
    tags = []
    padroes = [
        (r"resist[e\u00ea]ncia[s]?\s+(?:em|de|no|na|pr[o\u00f3]xim[ao])?\s*(?:\$|R\$)?\s*([\d\.,]+)", "resistencia"),
        (r"suporte[s]?\s+(?:em|de|no|na|pr[o\u00f3]xim[ao])?\s*(?:\$|R\$)?\s*([\d\.,]+)", "suporte"),
        (r"(?:\$|R\$)\s*([\d\.,]+)\s+(?:de\s+)?resist[e\u00ea]ncia", "resistencia"),
        (r"(?:\$|R\$)\s*([\d\.,]+)\s+(?:de\s+)?suporte", "suporte"),
    ]
    vistos = set()
    for padrao, tipo in padroes:
        for match in re.finditer(padrao, texto, re.IGNORECASE):
            valor = match.group(1).strip()
            prefixo = "Resist\u00eancia" if tipo == "resistencia" else "Suporte"
            label = f"{prefixo} {valor}"
            if label not in vistos:
                vistos.add(label)
                tags.append({"tipo": tipo, "label": label})
    return tags[:8]


def extrair_agenda(texto):
    agenda = []
    padroes = [
        r"(\d{1,2}[h:]\d{2})\s*[-\u2013\u2014|]?\s*([A-Z\u00c1\u00c9\u00cd\u00d3\u00da][^\n]{8,80})",
        r"(\d{1,2}h\d{0,2})\s*[-\u2013]?\s*([^\n]{10,80})",
    ]
    vistos = set()
    for padrao in padroes:
        for match in re.finditer(padrao, texto, re.IGNORECASE):
            hora_raw = match.group(1).replace("h", ":").strip()
            if hora_raw.endswith(":"):
                hora_raw += "00"
            evento = match.group(2).strip()
            chave = hora_raw + evento[:20]
            if (len(evento) > 10
                    and chave not in vistos
                    and not any(x in evento.lower() for x in ["clique", "acesse", "login", "sair", "menu"])):
                vistos.add(chave)
                agenda.append({"time": hora_raw, "event": evento[:100]})
    return agenda[:10]


def montar_json_final(dados_brutos):
    texto_limpo = limpar_texto(dados_brutos.get("insights_raw", ""))
    paragrafos = [p.strip() for p in texto_limpo.split("\n\n") if len(p.strip()) > 30]

    strategy = ""
    palavras_estrategia = ["aguardar", "operar", "posi\u00e7\u00e3o", "compra", "venda", "estrat\u00e9gia", "cautela", "vi\u00e9s", "tendencia", "tend\u00eancia"]
    for p in reversed(paragrafos):
        if any(w in p.lower() for w in palavras_estrategia):
            strategy = p
            break
    if not strategy and paragrafos:
        strategy = paragrafos[-1]

    tags = extrair_suportes_resistencias(texto_limpo)
    agenda = extrair_agenda(texto_limpo)

    if not agenda:
        agenda = [
            {"time": "09:30", "event": "Abertura do mercado brasileiro (B3)"},
            {"time": "10:00", "event": "Verificar calendário econômico do dia"},
        ]

    agora = dados_brutos.get("lastUpdate", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    return {
        "date": dados_brutos.get("date", datetime.now().strftime("%d/%m/%Y")),
        "lastUpdate": agora,
        "lastFetch": agora,
        "title": dados_brutos.get("title", f"Morning Call \u00b7 {datetime.now().strftime('%d/%m')}"),
        "tags": [t["label"] for t in tags],
        "tags_tipados": tags,
        "insights": paragrafos if paragrafos else ["Conte\u00fado n\u00e3o dispon\u00edvel para hoje."],
        "agenda": agenda,
        "strategy": strategy or "Acompanhar abertura e aguardar confirma\u00e7\u00e3o de tend\u00eancia.",
        "indicators": dados_brutos.get("indicators", {"fearGreed": None, "dxy": None, "vix": None}),
        "scrape_ok": dados_brutos.get("scrape_ok", False),
    }


MIN_CHARS_CONTEUDO = 200  # abaixo disso considera feriado/sem publicacao


def carregar_json_anterior():
    """Carrega o data.json existente, se houver."""
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            dados = json.load(f)
            log(f"data.json anterior carregado (data: {dados.get('date', '?')}).")
            return dados
    except Exception:
        return None


def salvar_dados():
    log("=" * 50)
    log("Iniciando coleta Morning Call - TraderBI")
    log("=" * 50)

    dados_brutos = extrair_dados_traderbi()
    anterior = carregar_json_anterior()

    # ── FALHA TOTAL (login falhou, navegador nao abriu, etc.) ────────────────
    if not dados_brutos:
        log("FALHA CRITICA: extrair_dados_traderbi retornou None.")
        if anterior:
            log("Mantendo data.json anterior intacto (falha de scrape).")
        else:
            erro_json = {
                "date": datetime.now().strftime("%d/%m/%Y"),
                "lastUpdate": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "lastFetch": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "title": f"Morning Call \u00b7 {datetime.now().strftime('%d/%m')}",
                "tags": [], "tags_tipados": [],
                "insights": ["\u26a0\ufe0f Falha na coleta autom\u00e1tica. Verifique os logs do GitHub Actions."],
                "agenda": [],
                "strategy": "Coleta indispon\u00edvel. Verifique as credenciais e o workflow.",
                "indicators": {"fearGreed": None, "dxy": None, "vix": None},
                "scrape_ok": False,
            }
            with open("data.json", "w", encoding="utf-8") as f:
                json.dump(erro_json, f, ensure_ascii=False, indent=2)
        return

    # ── CONTEUDO MUITO CURTO (feriado, sem publicacao, pagina nao carregou) ──
    chars = len((dados_brutos.get("insights_raw") or "").strip())
    log(f"Conteudo extraido: {chars} chars (minimo: {MIN_CHARS_CONTEUDO}).")

    if chars < MIN_CHARS_CONTEUDO:
        log(f"Conteudo insuficiente — possivel feriado ou ausencia de publicacao.")
        if anterior:
            # Atualiza apenas o lastFetch para registrar que o workflow rodou
            anterior["lastFetch"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            anterior["scrape_ok"] = False
            anterior["feriado_aviso"] = (
                f"Sem nova publicacao em {datetime.now().strftime('%d/%m/%Y')}. "
                "Exibindo conteudo do ultimo dia util."
            )
            with open("data.json", "w", encoding="utf-8") as f:
                json.dump(anterior, f, ensure_ascii=False, indent=2)
            log("data.json anterior preservado com aviso de feriado.")
        else:
            log("Sem data.json anterior — nada a preservar.")
        return

    # ── COLETA NORMAL ─────────────────────────────────────────────────────────
    json_final = montar_json_final(dados_brutos)
    # Remove aviso de feriado se havia
    json_final.pop("feriado_aviso", None)

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(json_final, f, ensure_ascii=False, indent=2)

    log("data.json salvo com sucesso!")
    log(f"  Paragrafos: {len(json_final['insights'])}")
    log(f"  Tags: {len(json_final['tags'])}")
    log(f"  Agenda: {len(json_final['agenda'])}")
    log(f"  Scrape OK: {json_final['scrape_ok']}")
    log("=" * 50)


if __name__ == "__main__":
    salvar_dados()
