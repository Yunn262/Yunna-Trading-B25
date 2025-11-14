# app.py
import os
import time
import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BINANCE_KEY = os.getenv("BINANCE_KEY")
BINANCE_SECRET = os.getenv("BINANCE_SECRET")

ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")  # para Forex

st.set_page_config(layout="wide", page_title="Radar Pro – Cripto & Forex")

def fetch_binance_ohlcv(symbol, timeframe='5m', limit=200):
    exchange = ccxt.binance({
        'apiKey': BINANCE_KEY,
        'secret': BINANCE_SECRET,
        'enableRateLimit': True,
    })
    bars = exchange.fetch_ohlcv(symbol.replace("/", ""), timeframe=timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
    df.set_index("ts", inplace=True)
    return df

def fetch_forex(symbol="EURUSD", interval="5min"):
    url = (
        f"https://www.alphavantage.co/query?"
        f"function=FX_INTRADAY&from_symbol={symbol[:3]}&to_symbol={symbol[3:]}&interval={interval}"
        f"&apikey={ALPHA_VANTAGE_KEY}&outputsize=compact"
    )
    r = requests.get(url).json()
    try:
        key = list(r.keys())[1]
        data = r[key]
        df = pd.DataFrame(data).T
        df = df.rename(columns={
            "1. open": "open",
            "2. high": "high",
            "3. low": "low",
            "4. close": "close"
        })
        df = df.astype(float)
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df["volume"] = np.random.randint(1000, 2000, size=len(df))
        return df
    except:
        return None

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.rolling(period).mean()
    ma_down = down.rolling(period).mean()
    rs = ma_up / (ma_down + 1e-9)
    return 100 - (100 / (1 + rs))

def score_signal(df):
    latest = df.iloc[-1]
    score = 0
    details = []
    if latest["ema9"] > latest["ema21"]:
        score += 50
        details.append("EMA9>EMA21")
    else:
        details.append("EMA9<EMA21")
    if 30 < latest["rsi"] < 65:
        score += 30
        details.append(f"RSI_ok:{latest['rsi']:.1f}")
    else:
        details.append(f"RSI_out:{latest['rsi']:.1f}")
    vol_mean = df["volume"].rolling(20).mean().iloc[-1]
    if latest["volume"] > vol_mean * 1.2:
        score += 20
        details.append("Volume_up")
    else:
        details.append("Vol_normal")
    if score >= 75:
        label = "SUBIR" if latest["ema9"] > latest["ema21"] else "DESCER"
    elif score >= 45:
        label = "POTENCIAL"
    else:
        label = "ESPERE"
    return label, score, details

st.sidebar.title("📊 Radar PRO")
menu = st.sidebar.radio(
    "Escolha uma opção:",
    ["Dashboard", "Criptomoedas", "Forex"]
)

if menu == "Dashboard":
    st.title("📌 Painel Geral")
    st.write("Selecione Cripto ou Forex ao lado.")

if menu == "Criptomoedas":
    st.title("🚀 Radar de Criptomoedas")
    col1, col2 = st.columns([1,2])
    with col1:
        asset = st.selectbox("Ativo", [
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "XRP/USDT",
            "SOL/USDT", "ADA/USDT"
        ])
        timeframe = st.selectbox("Timeframe", ["1m", "3m", "5m", "15m"], index=2)
        conf_min = st.slider("Confiança mínima (%)", 50, 100, 75)
        auto = st.checkbox("Atualizar automaticamente", value=True)
        delay = st.number_input("Intervalo (s)", 10, 600, 60)
    with col2:
        placeholder = st.empty()

    def run_crypto():
        df = fetch_binance_ohlcv(asset, timeframe, 200)
        df["ema9"] = ema(df["close"], 9)
        df["ema21"] = ema(df["close"], 21)
        df["rsi"] = rsi(df["close"])
        label, conf, details = score_signal(df)
        with placeholder.container():
            st.subheader(f"Sinal: {label} — Confiança {conf}%")
            st.write(", ".join(details))
            st.line_chart(df[["close", "ema9", "ema21"]])
        if conf >= conf_min:
            st.success(f"ALERTA: {label} ({conf}%)")

    if auto:
        while True:
            run_crypto()
            time.sleep(delay)
    else:
        run_crypto()

if menu == "Forex":
    st.title("💱 Radar Forex")
    col1, col2 = st.columns([1,2])
    with col1:
        fx = st.selectbox("Par Forex", [
            "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"
        ])
        conf_min = st.slider("Confiança mínima (%)", 50, 100, 70)
        auto = st.checkbox("Auto-refresh", value=True)
        delay = st.number_input("Intervalo (s)", 10, 600, 60)
    with col2:
        placeholder_fx = st.empty()

    def run_fx():
        df = fetch_forex(fx)
        if df is None:
            st.error("Erro ao buscar dados Forex")
            return
        df["ema9"] = ema(df["close"], 9)
        df["ema21"] = ema(df["close"], 21)
        df["rsi"] = rsi(df["close"])
        label, conf, details = score_signal(df)
        with placeholder_fx.container():
            st.subheader(f"{fx}: {label} — {conf}%")
            st.write(", ".join(details))
            st.line_chart(df[["close", "ema9", "ema21"]])
        if conf >= conf_min:
            st.success(f"ALERTA FOREX: {label} — {conf}%")

    if auto:
        while True:
            run_fx()
            time.sleep(delay)
    else:
        run_fx()
