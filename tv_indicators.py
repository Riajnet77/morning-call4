"""
TradingView Indicators Module - Integracao com morning-call4
Coleta RSI, Stochastic, MACD e Volume de ativos via TradingView WebSocket API
Mercados: B3, EUA, Cripto
"""

import subprocess
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

BRT = ZoneInfo("America/Sao_Paulo")

ATIVOS = {
    "b3": {
        "nome": "B3 - Brasil",
        "exchange": "BMFBOVESPA",
        "ativos": ["PETR4", "VALE3", "ITUB4", "BBDC4", "ABEV3", "WEGE3", "RENT3", "BBAS3"],
        "top_count": 5
    },
    "eua": {
        "nome": "NYSE/NASDAQ - EUA",
        "exchange": "NASDAQ",
        "ativos": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "AMD"],
        "top_count": 5
    },
    "crypto": {
        "nome": "Criptomoedas",
        "exchange": "BINANCE",
        "ativos": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT"],
        "top_count": 5
    }
}

TIMEFRAME = "1D"
TIMEOUT = 35


def interpretar_rsi(rsi):
    if rsi is None:
        return {"sinal": "NEUTRO", "emoji": "-", "classe": "neutro"}
    if rsi > 70:
        return {"sinal": "SOBRECOMPRA", "emoji": "SC", "classe": "baixista"}
    if rsi < 30:
        return {"sinal": "SOBREVENDA", "emoji": "SV", "classe": "altista"}
    return {"sinal": "NEUTRO", "emoji": "-", "classe": "neutro"}


def interpretar_stoch(k, d):
    if k is None or d is None:
        return {"sinal": "NEUTRO", "emoji": "-", "classe": "neutro"}
    if k > 80 and d > 80:
        return {"sinal": "SOBRECOMPRA", "emoji": "SC", "classe": "baixista"}
    if k < 20 and d < 20:
        return {"sinal": "SOBREVENDA", "emoji": "SV", "classe": "altista"}
    if k > d:
        return {"sinal": "TENDENCIA ALTA", "emoji": "TA", "classe": "altista"}
    if k < d:
        return {"sinal": "TENDENCIA BAIXA", "emoji": "TB", "classe": "baixista"}
    return {"sinal": "NEUTRO", "emoji": "-", "classe": "neutro"}


def interpretar_macd(macd, signal, histogram):
    if macd is None or signal is None:
        return {"sinal": "NEUTRO", "emoji": "-", "classe": "neutro"}
    if macd > signal and histogram > 0:
        return {"sinal": "COMPRA", "emoji": "C", "classe": "altista"}
    if macd < signal and histogram < 0:
        return {"sinal": "VENDA", "emoji": "V", "classe": "baixista"}
    if macd > signal:
        return {"sinal": "COMPRA FRACA", "emoji": "CF", "classe": "altista"}
    if macd < signal:
        return {"sinal": "VENDA FRACA", "emoji": "VF", "classe": "baixista"}
    return {"sinal": "NEUTRO", "emoji": "-", "classe": "neutro"}


def interpretar_volume(volume, volume_medio):
    if not volume or not volume_medio:
        return {"sinal": "NEUTRO", "emoji": "-", "classe": "neutro"}
    ratio = volume / volume_medio
    if ratio > 2.0:
        return {"sinal": "MUITO ACIMA DA MEDIA", "emoji": "MA", "classe": "alta_atencao"}
    if ratio > 1.5:
        return {"sinal": "ACIMA DA MEDIA", "emoji": "AM", "classe": "neutro"}
    if ratio < 0.5:
        return {"sinal": "ABAIXO DA MEDIA", "emoji": "BM", "classe": "neutro"}
    return {"sinal": "MEDIO", "emoji": "M", "classe": "neutro"}


def calcular_score_tecnico(interpretacoes):
    score = 0
    pesos = {"rsi": 25, "stoch": 25, "macd": 30, "volume": 20}

    rsi_sinal = interpretacoes["rsi"]["sinal"]
    if rsi_sinal == "SOBREVENDA":
        score += pesos["rsi"]
    elif rsi_sinal == "SOBRECOMPRA":
        score -= pesos["rsi"]

    stoch_sinal = interpretacoes["stoch"]["sinal"]
    if stoch_sinal == "SOBREVENDA":
        score += pesos["stoch"]
    elif stoch_sinal == "SOBRECOMPRA":
        score -= pesos["stoch"]
    elif stoch_sinal == "TENDENCIA ALTA":
        score += pesos["stoch"] * 0.5
    elif stoch_sinal == "TENDENCIA BAIXA":
        score -= pesos["stoch"] * 0.5

    macd_sinal = interpretacoes["macd"]["sinal"]
    if macd_sinal == "COMPRA":
        score += pesos["macd"]
    elif macd_sinal == "VENDA":
        score -= pesos["macd"]
    elif macd_sinal == "COMPRA FRACA":
        score += pesos["macd"] * 0.5
    elif macd_sinal == "VENDA FRACA":
        score -= pesos["macd"] * 0.5

    vol_sinal = interpretacoes["volume"]["sinal"]
    if vol_sinal in ["MUITO ACIMA DA MEDIA", "ACIMA DA MEDIA"]:
        score = score * 1.2
    elif vol_sinal == "ABAIXO DA MEDIA":
        score = score * 0.7

    return max(-100, min(100, round(score)))


def classificar_score(score):
    if score >= 60:
        return "FORTE COMPRA", "altista"
    if score >= 30:
        return "COMPRA", "altista"
    if score >= 10:
        return "COMPRA FRACA", "altista"
    if score > -10:
        return "NEUTRO", "neutro"
    if score > -30:
        return "VENDA FRACA", "baixista"
    if score > -60:
        return "VENDA", "baixista"
    return "FORTE VENDA", "baixista"


def escrever_script_node():
    script_path = os.path.join(os.path.dirname(__file__), "tv_fetch.js")
    if os.path.exists(script_path):
        return script_path
    tv_fetch = r"""const TradingView = require('@mathieuc/tradingview');

async function fetchIndicators(ticker, exchange, timeframe) {
    return new Promise((resolve, reject) => {
        const client = new TradingView.Client();
        const chart = new client.Session.Chart();
        let resultado = {
            ticker: ticker, exchange: exchange, timeframe: timeframe,
            preco: null, variacao: null, volume: null, volumeMedio: null,
            rsi: null, stochK: null, stochD: null,
            macd: null, macdSignal: null, macdHistogram: null, erro: null
        };
        let studiesCompleted = 0;
        const totalStudies = 3;
        let timeoutId;
        function checkDone() {
            studiesCompleted++;
            if (studiesCompleted >= totalStudies) {
                clearTimeout(timeoutId);
                client.end();
                resolve(resultado);
            }
        }
        chart.setMarket(exchange + ':' + ticker, { timeframe: timeframe, range: 100 });
        const rsiStudy = new chart.Study({ name: 'RSI', length: 14 });
        rsiStudy.onUpdate(() => {
            const periods = rsiStudy.periods;
            if (periods && periods.length > 0) {
                const last = periods[periods.length - 1];
                resultado.rsi = last['RSI'] ? parseFloat(last['RSI'].toFixed(2)) : null;
            }
            checkDone();
        });
        const stochStudy = new chart.Study({
            name: 'Stochastic',
            inputs: { length: 14, smoothK: 3, smoothD: 3 }
        });
        stochStudy.onUpdate(() => {
            const periods = stochStudy.periods;
            if (periods && periods.length > 0) {
                const last = periods[periods.length - 1];
                resultado.stochK = last['%K'] ? parseFloat(last['%K'].toFixed(2)) : null;
                resultado.stochD = last['%D'] ? parseFloat(last['%D'].toFixed(2)) : null;
            }
            checkDone();
        });
        const macdStudy = new chart.Study({
            name: 'MACD',
            inputs: { fastLength: 12, slowLength: 26, signalLength: 9 }
        });
        macdStudy.onUpdate(() => {
            const periods = macdStudy.periods;
            if (periods && periods.length > 0) {
                const last = periods[periods.length - 1];
                resultado.macd = last['MACD'] ? parseFloat(last['MACD'].toFixed(4)) : null;
                resultado.macdSignal = last['Signal'] ? parseFloat(last['Signal'].toFixed(4)) : null;
                resultado.macdHistogram = last['Histogram'] ? parseFloat(last['Histogram'].toFixed(4)) : null;
            }
            checkDone();
        });
        chart.onUpdate(() => {
            const periods = chart.periods;
            if (periods && periods.length > 0) {
                const last = periods[periods.length - 1];
                resultado.preco = last.close ? parseFloat(last.close.toFixed(2)) : null;
                resultado.volume = last.volume || null;
                const volumes = periods.slice(-20).map(p => p.volume).filter(v => v);
                resultado.volumeMedio = volumes.length > 0
                    ? Math.round(volumes.reduce((a, b) => a + b, 0) / volumes.length)
                    : null;
                if (periods.length > 1) {
                    const prev = periods[periods.length - 2];
                    resultado.variacao = prev.close
                        ? parseFloat((((last.close - prev.close) / prev.close) * 100).toFixed(2))
                        : null;
                }
            }
        });
        chart.onError((err) => {
            resultado.erro = err.message || 'Erro no chart';
            clearTimeout(timeoutId);
            client.end();
            resolve(resultado);
        });
        timeoutId = setTimeout(() => {
            client.end();
            resolve(resultado);
        }, 30000);
    });
}

const [ticker, exchange, timeframe] = process.argv.slice(2);
fetchIndicators(ticker, exchange, timeframe)
    .then(r => console.log(JSON.stringify(r)))
    .catch(e => console.log(JSON.stringify({erro: e.message})));
"""
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(tv_fetch)
    return script_path


def buscar_indicadores_tv(ticker, exchange, timeframe=TIMEFRAME, script_path=None):
    if script_path is None:
        script_path = escrever_script_node()
    try:
        result = subprocess.run(
            ["node", script_path, ticker, exchange, timeframe],
            capture_output=True, text=True, timeout=TIMEOUT
        )
        if result.returncode != 0 and not result.stdout:
            return {"ticker": ticker, "erro": f"Node error: {result.stderr}"}
        lines = result.stdout.strip().split("\n")
        for line in reversed(lines):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    return json.loads(line)
                except:
                    continue
        return {"ticker": ticker, "erro": "Nenhum JSON valido encontrado na saida"}
    except subprocess.TimeoutExpired:
        return {"ticker": ticker, "erro": f"Timeout apos {TIMEOUT}s"}
    except FileNotFoundError:
        return {"ticker": ticker, "erro": "Node.js nao encontrado. Instale: npm install @mathieuc/tradingview"}
    except Exception as e:
        return {"ticker": ticker, "erro": str(e)}


def processar_ativo(dados_raw):
    if dados_raw.get("erro"):
        return {
            "ticker": dados_raw.get("ticker"),
            "erro": dados_raw["erro"],
            "status": "erro"
        }

    rsi = dados_raw.get("rsi")
    stoch_k = dados_raw.get("stochK")
    stoch_d = dados_raw.get("stochD")
    macd = dados_raw.get("macd")
    macd_signal = dados_raw.get("macdSignal")
    macd_hist = dados_raw.get("macdHistogram")
    volume = dados_raw.get("volume")
    volume_medio = dados_raw.get("volumeMedio")

    interpretacoes = {
        "rsi": interpretar_rsi(rsi),
        "stoch": interpretar_stoch(stoch_k, stoch_d),
        "macd": interpretar_macd(macd, macd_signal, macd_hist),
        "volume": interpretar_volume(volume, volume_medio)
    }

    score = calcular_score_tecnico(interpretacoes)
    recomendacao, classe = classificar_score(score)

    return {
        "ticker": dados_raw["ticker"],
        "exchange": dados_raw["exchange"],
        "timeframe": dados_raw["timeframe"],
        "preco": dados_raw.get("preco"),
        "variacao_pct": dados_raw.get("variacao"),
        "volume": volume,
        "volume_medio": volume_medio,
        "indicadores": {
            "rsi": {"valor": rsi, "periodos": 14},
            "stochastic": {
                "k": stoch_k, "d": stoch_d,
                "periodos": 14, "smooth_k": 3, "smooth_d": 3
            },
            "macd": {
                "macd": macd, "signal": macd_signal, "histogram": macd_hist,
                "fast": 12, "slow": 26, "signal_length": 9
            }
        },
        "interpretacoes": interpretacoes,
        "score_tecnico": score,
        "recomendacao": recomendacao,
        "classe": classe,
        "status": "ok"
    }


def coletar_indicadores_tv():
    print(f"[{datetime.now(BRT).strftime('%H:%M:%S')}] Iniciando coleta TradingView...")
    script_path = escrever_script_node()
    resultado = {
        "gerado_em": datetime.now(BRT).isoformat(),
        "fonte": "TradingView API (@mathieuc/tradingview)",
        "mercados": {}
    }

    for mercado_key, mercado_cfg in ATIVOS.items():
        print(f"\n[{mercado_key.upper()}] {mercado_cfg['nome']}")
        mercado_data = {
            "nome": mercado_cfg["nome"],
            "exchange": mercado_cfg["exchange"],
            "ativos": [],
            "resumo": {
                "compra": 0, "venda": 0, "neutro": 0,
                "erros": 0, "sentimento_geral": "NEUTRO"
            }
        }

        for ticker in mercado_cfg["ativos"]:
            print(f"  -> {ticker}...", end=" ", flush=True)
            raw = buscar_indicadores_tv(ticker, mercado_cfg["exchange"], TIMEFRAME, script_path)
            processado = processar_ativo(raw)
            mercado_data["ativos"].append(processado)

            if processado.get("status") == "erro":
                print(f"X {processado.get('erro', 'erro')}")
                mercado_data["resumo"]["erros"] += 1
            else:
                cls = processado.get("classe", "neutro")
                if cls == "altista":
                    mercado_data["resumo"]["compra"] += 1
                elif cls == "baixista":
                    mercado_data["resumo"]["venda"] += 1
                else:
                    mercado_data["resumo"]["neutro"] += 1
                print(f"OK Score:{processado['score_tecnico']} ({processado['recomendacao']})")

        total_ok = mercado_data["resumo"]["compra"] + mercado_data["resumo"]["venda"] + mercado_data["resumo"]["neutro"]
        if total_ok > 0:
            pct_compra = mercado_data["resumo"]["compra"] / total_ok
            pct_venda = mercado_data["resumo"]["venda"] / total_ok
            if pct_compra > 0.55:
                mercado_data["resumo"]["sentimento_geral"] = "ALTA"
            elif pct_venda > 0.55:
                mercado_data["resumo"]["sentimento_geral"] = "BAIXA"
            elif pct_compra > pct_venda:
                mercado_data["resumo"]["sentimento_geral"] = "LEVE ALTA"
            elif pct_venda > pct_compra:
                mercado_data["resumo"]["sentimento_geral"] = "LEVE BAIXA"
            else:
                mercado_data["resumo"]["sentimento_geral"] = "NEUTRO"

        resultado["mercados"][mercado_key] = mercado_data

    try:
        os.remove(script_path)
    except:
        pass

    print(f"\n[{datetime.now(BRT).strftime('%H:%M:%S')}] Coleta finalizada!")
    return resultado


def gerar_narrativa_tecnica(tv_data):
    linhas = ["**ANALISE TECNICA - INDICADORES**"]
    emoji_map = {
        "ALTA": "+", "LEVE ALTA": "~+", "NEUTRO": "=",
        "LEVE BAIXA": "~-", "BAIXA": "-"
    }

    for mercado_key, mercado in tv_data["mercados"].items():
        nome = mercado["nome"]
        sentimento = mercado["resumo"]["sentimento_geral"]
        emoji_sent = emoji_map.get(sentimento, "=")
        linhas.append(f"\n**{nome}** {emoji_sent} *Sentimento: {sentimento}*")

        ativos_ok = [a for a in mercado["ativos"] if a.get("status") == "ok"]
        ativos_ok.sort(key=lambda x: abs(x.get("score_tecnico", 0)), reverse=True)

        for ativo in ativos_ok[:4]:
            ticker = ativo["ticker"]
            score = ativo["score_tecnico"]
            rec = ativo["recomendacao"]
            preco = ativo.get("preco")
            var = ativo.get("variacao_pct")

            parts = []
            rsi = ativo["indicadores"]["rsi"]["valor"]
            if rsi:
                parts.append(f"RSI {rsi}")
            stoch = ativo["indicadores"]["stochastic"]
            if stoch["k"] is not None:
                parts.append(f"Stoch K={stoch['k']}")
            macd = ativo["indicadores"]["macd"]
            if macd["macd"] is not None:
                parts.append(f"MACD {macd['macd']:.3f}")

            preco_txt = f"R$ {preco:.2f}" if preco else "N/A"
            var_txt = f"({var:+.2f}%)" if var is not None else ""
            ind_txt = " | ".join(parts) if parts else "dados indisponiveis"
            linhas.append(f"- **{ticker}** {preco_txt} {var_txt} -- {rec} (Score:{score}) [{ind_txt}]")

        erros = [a["ticker"] for a in mercado["ativos"] if a.get("status") == "erro"]
        if erros:
            linhas.append(f"! Sem dados: {', '.join(erros)}")

    return "\n".join(linhas)


def integrar_no_morning_call(data_json_path="data.json"):
    tv_data = coletar_indicadores_tv()
    narrativa = gerar_narrativa_tecnica(tv_data)
    emoji_map = {
        "ALTA": "+", "LEVE ALTA": "~+", "NEUTRO": "=",
        "LEVE BAIXA": "~-", "BAIXA": "-"
    }

    try:
        with open(data_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        data = {}

    data["tradingview_indicators"] = tv_data
    data["technical_analysis_text"] = narrativa

    if "insights" not in data:
        data["insights"] = []
    if len(data["insights"]) >= 1:
        data["insights"].insert(1, narrativa)
    else:
        data["insights"].append(narrativa)

    if "tags" not in data:
        data["tags"] = []

    for mk, mv in tv_data["mercados"].items():
        sent = mv["resumo"]["sentimento_geral"]
        emoji = emoji_map.get(sent, "=")
        data["tags"].append(f"TV {mk.upper()} {emoji} {sent}")

    with open(data_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[{datetime.now(BRT).strftime('%H:%M:%S')}] data.json atualizado com indicadores TradingView!")
    return data


if __name__ == "__main__":
    resultado = coletar_indicadores_tv()
    with open("tv_indicators.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    print("\n" + "=" * 50)
    print(gerar_narrativa_tecnica(resultado))
    print("=" * 50)
    print("\nArquivo salvo: tv_indicators.json")
