import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

# 🔥 Put your API key here
API_KEY = "53KULJ8DU5X4NZ5V"

REFRESH = 60

st.set_page_config(page_title="Stock Dashboard", layout="wide")

@st.cache_data(ttl=REFRESH*60)
def fetch_stock(symbol):
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={API_KEY}"
    r = requests.get(url).json()

    data = r.get("Time Series (Daily)", {})
    df = pd.DataFrame(data).T

    df = df.rename(columns={
        "1. open":"Open",
        "2. high":"High",
        "3. low":"Low",
        "4. close":"Close",
        "5. volume":"Volume"
    })

    df = df.astype(float)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    return df

st.title("📈 Real-Time Stock Dashboard")

symbol = st.sidebar.text_input("Enter Stock Symbol", "AAPL")

df = fetch_stock(symbol)

if df.empty:
    st.error("No data found (check API key or symbol)")
else:
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    change = latest["Close"] - prev["Close"]
    pct = (change / prev["Close"]) * 100

    col1, col2, col3 = st.columns(3)
    col1.metric("Current Price", f"${latest['Close']:.2f}", f"{pct:.2f}%")
    col2.metric("High", f"${latest['High']:.2f}")
    col3.metric("Low", f"${latest['Low']:.2f}")

    st.subheader("7-Day Trend")
    st.line_chart(df["Close"].tail(7))

    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"]
    )])

    st.plotly_chart(fig)

    df["returns"] = df["Close"].pct_change()
    volatility = df["returns"].rolling(7).std()

    st.subheader("Volatility (7-day)")
    st.line_chart(volatility)

    if st.button("🔄 Force Refresh"):
        st.cache_data.clear()