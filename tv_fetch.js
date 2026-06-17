const TradingView = require('@mathieuc/tradingview');

async function fetchIndicators(ticker, exchange, timeframe) {
    return new Promise((resolve, reject) => {
        const client = new TradingView.Client();
        const chart = new client.Session.Chart();

        let resultado = {
            ticker: ticker,
            exchange: exchange,
            timeframe: timeframe,
            preco: null,
            variacao: null,
            volume: null,
            volumeMedio: null,
            rsi: null,
            stochK: null,
            stochD: null,
            macd: null,
            macdSignal: null,
            macdHistogram: null,
            erro: null
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

        chart.setMarket(exchange + ':' + ticker, {
            timeframe: timeframe,
            range: 100
        });

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
