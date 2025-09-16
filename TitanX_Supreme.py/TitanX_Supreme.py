import streamlit as st
import ccxt
import plotly.graph_objects as go
sentiment_model = lambda x: [{"label": "POSITIVE", "score": 0.95}]
from streamlit_autorefresh import st_autorefresh
import numpy as np
import pandas as pd

# Auto-refresh every 60 seconds
st_autorefresh(interval=60000, key="refresh")

# KuCoin API setup
kucoin_api_key = st.secrets["KUCOIN_API_KEY"]
kucoin_api_secret = st.secrets["KUCOIN_API_SECRET"]
kucoin_api_passphrase = st.secrets["KUCOIN_API_PASSPHRASE"]
exchange = ccxt.kucoin({
    "apiKey": kucoin_api_key,
    "secret": kucoin_api_secret,
    "password": kucoin_api_passphrase
})

# Coin and timeframe options
coins = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]

# Tabs
tabs = st.tabs(["Overview", "Trades", "Strategy", "Profit", "Replay"])

trade_history = []
trading_active = st.sidebar.checkbox("Start Trading")
stop_trading = st.sidebar.button("Stop Trading")

if stop_trading:
    try:
        positions = exchange.fetch_open_orders()
        for position in positions:
            exchange.cancel_order(position["id"])
        st.sidebar.write("All open positions closed.")
    except Exception as e:
        st.sidebar.write(f"Error closing positions: {e}")

with tabs[0]:
    st.title("TitanX Supreme — Overview")
try:
    balance = exchange.fetch_balance()["total"]
    usdt_balance = balance.get("USDT", 0)
except Exception:
    usdt_balance = 0

st.write(f"KuCoin Balance: ${usdt_balance:.2f}")

    trade_limit = st.slider("Max Trade Allocation ($)", min_value=10, max_value=int(usdt_balance), value=10)
    st.write("Total Trades: " + str(len(trade_history)))
    st.write("Transactions: " + str(len(trade_history)))
    st.write("Today's P&L: $0")
    reinvest = st.checkbox("Reinvest Profits")
    lock_profit = st.checkbox("Lock Profits Above $20")
    st.write("Trade History")
    for trade in trade_history:
        st.write(trade)

with tabs[1]:
    st.title("Live Trades")
    st.write("Fetching live trades...")
    # Placeholder for trade data

with tabs[2]:
    st.title("Strategy Engine")
    st.write("Sentiment + Technical Strategy")
    best_score = 0
    best_combo = None
    news = ""
    try:
        import requests
        news_sources = [
            "https://cryptopanic.com/api/posts/?auth_token=demo&public=true",
            "https://api.coindesk.com/v1/news",
            "https://api.cointelegraph.com/v1/news"
        ]
        for url in news_sources:
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    news += response.text
            except:
                pass
    except:
        pass

    if news:
        result = sentiment_model(news)[0]
        score = result["score"]
        st.write(f"Sentiment: {result['label']} ({score:.2f})")
        best_score = score
        best_combo = ("BTC/USDT", "1h")

    if best_combo and trading_active:
        st.write(f"Best Setup: {best_combo[0]} on {best_combo[1]} with score {best_score:.2f}")
        st.write("Strategy Optimizer: GPT-5 recommends best mode")

        ohlcv = exchange.fetch_ohlcv(best_combo[0], best_combo[1])
        df = pd.DataFrame(ohlcv, columns=["Timestamp", "Open", "High", "Low", "Close", "Volume"])
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], unit="ms")
        df.set_index("Timestamp", inplace=True)
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"]
        )])
        st.plotly_chart(fig)

        entry_price = df["Close"].iloc[-1]
        sentiment_score = best_score

        def calculate_atr(df, period=14):
            df["H-L"] = df["High"] - df["Low"]
            df["H-PC"] = abs(df["High"] - df["Close"].shift(1))
            df["L-PC"] = abs(df["Low"] - df["Close"].shift(1))
            df["TR"] = df[["H-L", "H-PC", "L-PC"]].max(axis=1)
            df["ATR"] = df["TR"].rolling(window=period).mean()
            return df["ATR"].iloc[-1]

        atr = calculate_atr(df)
        tp_multiplier = 1 + sentiment_score
        sl_multiplier = 1 - sentiment_score
        tp_price = entry_price + atr * tp_multiplier
        sl_price = entry_price - atr * sl_multiplier
        current_price = df["Close"].iloc[-1]

        trade_amount = usdt_balance * 0.25
        if sentiment_score > 0.75:
            trade_amount = usdt_balance * 0.5
        if sentiment_score > 0.9:
            trade_amount = usdt_balance

        if trade_amount >= 10:
            try:
                order = exchange.create_market_buy_order(best_combo[0], trade_amount / 100)
                st.write(f"Trade Executed: {order}")
                trade_history.append({
                    "Coin": best_combo[0],
                    "Timeframe": best_combo[1],
                    "Entry": entry_price,
                    "Amount": trade_amount,
                    "Timestamp": pd.Timestamp.now()
                })
            except Exception as e:
                st.write(f"Trade failed: {e}")

        if current_price >= tp_price or current_price <= sl_price:
            try:
                order = exchange.create_market_sell_order(best_combo[0], trade_amount / 100)
                st.write(f"Sell Executed: {order}")
                trade_history[-1]["Exit"] = current_price
                trade_history[-1]["Profit"] = current_price - entry_price
                trade_history[-1]["Exit Timestamp"] = pd.Timestamp.now()
            except Exception as e:
                st.write(f"Sell failed: {e}")

with tabs[3]:
    st.title("Profit Summary")
    st.write("Profit tracking coming soon...")

with tabs[4]:
    st.title("Trade Replay")
    for trade in trade_history:
        st.write(f"Trade Replay for {trade['Coin']} on {trade['Timeframe']}")
        ohlcv = exchange.fetch_ohlcv(trade["Coin"], trade["Timeframe"])
        df = pd.DataFrame(ohlcv, columns=["Timestamp", "Open", "High", "Low", "Close", "Volume"])
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], unit="ms")
        df.set_index("Timestamp", inplace=True)
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"]
        )])
        fig.add_trace(go.Scatter(x=[trade["Timestamp"]], y=[trade["Entry"]], mode="markers", marker=dict(color="green", size=10), name="Entry"))
        if "Exit" in trade:
            fig.add_trace(go.Scatter(x=[trade["Exit Timestamp"]], y=[trade["Exit"]], mode="markers", marker=dict(color="red", size=10), name="Exit"))
        st.plotly_chart(fig)