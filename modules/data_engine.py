import yfinance as yf
import pandas as pd
import streamlit as st

@st.cache_data(ttl=50)
def carregar_dados(lista_tickers):
    return yf.download(lista_tickers, period="5d", interval="5m", group_by='ticker', progress=False)

def processar_acao(acao, dados_brutos, total_acoes):
    try:
        df = dados_brutos[acao].copy() if total_acoes > 1 else dados_brutos.copy()
        df.dropna(inplace=True)
        if len(df) < 50:
            return None

        preco = df["Close"].iloc[-1]
        p_ant = df["Close"].iloc[-2]
        var = ((preco / p_ant) - 1) * 100

        # MÉDIAS
        df["MA9"] = df["Close"].rolling(9).mean()
        df["MA21"] = df["Close"].rolling(21).mean()

        # VOLUME
        df["VOL_MED"] = df["Volume"].rolling(20).mean()

        # ATR
        df["TR"] = df["High"] - df["Low"]
        df["ATR"] = df["TR"].rolling(14).mean()
        atr = df["ATR"].iloc[-1]

        # VOLATILIDADE %
        df["RANGE_PCT"] = (df["High"] - df["Low"]) / df["Close"]
        vol_rec = df["RANGE_PCT"].rolling(20).mean().iloc[-1]

        m9, m21 = df["MA9"].iloc[-1], df["MA21"].iloc[-1]
        v_at, v_m = df["Volume"].iloc[-1], df["VOL_MED"].iloc[-1]

        topo = df["High"].iloc[-21:-1].max()
        fundo = df["Low"].iloc[-21:-1].min()

        # 🔥 TENDÊNCIA MAIOR (15min)
        df_15 = df.resample("15min").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last"
        }).dropna()

        df_15["MA21"] = df_15["Close"].rolling(21).mean()

        tendencia_alta = df_15["Close"].iloc[-1] > df_15["MA21"].iloc[-1]
        tendencia_baixa = df_15["Close"].iloc[-1] < df_15["MA21"].iloc[-1]

        # 🚫 ROMPIMENTO REAL
        rompimento_alta = preco > topo and p_ant <= topo
        rompimento_baixa = preco < fundo and p_ant >= fundo

        # 🔥 SCORE
        score = 0

        if preco > m9 > m21:
            score += 3
        elif preco < m9 < m21:
            score += 3

        if v_at > v_m:
            score += 2
        if v_at > v_m * 1.5:
            score += 1

        if rompimento_alta or rompimento_baixa:
            score += 2

        corpo = abs(df["Close"].iloc[-1] - df["Open"].iloc[-1])
        range_candle = df["High"].iloc[-1] - df["Low"].iloc[-1]

        if range_candle > 0 and (corpo / range_candle) > 0.6:
            score += 2

        rating = min(score, 10)

        # 🎯 OPERAÇÃO
        tipo = "NEUTRO"
        ent, stp, alv = 0, 0, 0

        if preco > m9 > m21 and rompimento_alta and tendencia_alta:
            tipo = "COMPRA"
            ent = preco
            stp = preco - atr * 1.2
            alv = preco + atr * 1.8

        elif preco < m9 < m21 and rompimento_baixa and tendencia_baixa:
            tipo = "VENDA"
            ent = preco
            stp = preco + atr * 1.2
            alv = preco - atr * 1.8

        return {
            "nome": acao.replace(".SA",""),
            "preco": preco,
            "var": var,
            "df": df.tail(40),
            "tipo": tipo,
            "rating": int(rating),
            "score": int(score),
            "volat": f"{vol_rec:.2%}",
            "ent": ent,
            "stp": stp,
            "alv": alv,
            "vol_m": round(v_at/v_m, 1)
        }

    except:
        return None