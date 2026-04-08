"""
============================================================
  Real-Time Stock Analytics Dashboard
  Stack  : Python · Streamlit · Plotly · yfinance
  Stocks : AAPL · MSFT · GOOGL · AMZN · TSLA · NVDA
  No API key required — yfinance is completely free
============================================================
"""

import yfinance as yf
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# ── Classic font & color theme ─────────────────────────────
CLASSIC_FONT = "Playfair Display, Georgia, 'Times New Roman', serif"
BG_COLOR     = "#0e1117"
CARD_BG      = "#1a1d2e"
ACCENT       = "#c9a84c"
GRID_COLOR   = "#2a2d3e"
TEXT_COLOR   = "#e8e0d0"

STOCK_COLORS = {
    "AAPL" : "#4f8ef7",
    "MSFT" : "#50C878",
    "GOOGL": "#FF6B6B",
    "AMZN" : "#FFD700",
    "TSLA" : "#FF4500",
    "NVDA" : "#9B59B6",
}

DEFAULT_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"]

# ── Page config ────────────────────────────────────────────
st.set_page_config(
    page_title="📈 Stock Analytics Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ─────────────────────────────────────────────
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=EB+Garamond:wght@400;600&display=swap');

  html, body, [class*="css"] {{
      font-family: 'EB Garamond', Georgia, serif !important;
      background-color: {BG_COLOR};
      color: {TEXT_COLOR};
  }}
  h1, h2, h3 {{
      font-family: 'Playfair Display', Georgia, serif !important;
      color: {ACCENT} !important;
  }}
  .metric-card {{
      background: {CARD_BG};
      border-radius: 10px;
      padding: 16px 20px;
      border-left: 4px solid {ACCENT};
      margin-bottom: 10px;
  }}
  .stSelectbox label, .stMultiSelect label {{
      font-family: 'EB Garamond', Georgia, serif !important;
      color: {ACCENT} !important;
      font-size: 15px;
  }}
  section[data-testid="stSidebar"] {{
      background: #12151f;
  }}
  .block-container {{ padding-top: 1.5rem; }}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  DATA LAYER
# ══════════════════════════════════════════════════════════

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_data(ticker: str, period: str = "6mo") -> pd.DataFrame:
    try:
        df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        if df.empty:
            return pd.DataFrame()
        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        df.index   = pd.to_datetime(df.index)
        return df.sort_index()
    except Exception as e:
        st.warning(f"Error fetching {ticker}: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def fetch_quote(ticker: str) -> dict:
    try:
        t  = yf.Ticker(ticker)
        fi = t.fast_info
        prev = getattr(fi, "previous_close", 0) or 0
        curr = getattr(fi, "last_price",      0) or 0
        chg  = curr - prev
        pct  = (chg / prev * 100) if prev else 0
        return {
            "price"  : round(curr, 2),
            "change" : round(chg,  2),
            "pct"    : round(pct,  2),
            "high"   : round(getattr(fi, "day_high",    0) or 0, 2),
            "low"    : round(getattr(fi, "day_low",     0) or 0, 2),
            "volume" : int(getattr(fi,   "last_volume", 0) or 0),
            "mktcap" : getattr(fi, "market_cap", 0) or 0,
        }
    except Exception:
        return {"price": 0, "change": 0, "pct": 0,
                "high": 0, "low": 0, "volume": 0, "mktcap": 0}


def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["return"]     = df["close"].pct_change()
    df["ma7"]        = df["close"].rolling(7).mean()
    df["ma21"]       = df["close"].rolling(21).mean()
    df["volatility"] = df["return"].rolling(7).std() * (252 ** 0.5) * 100
    delta            = df["close"].diff()
    gain             = delta.clip(lower=0).rolling(14).mean()
    loss             = (-delta.clip(upper=0)).rolling(14).mean()
    rs               = gain / loss.replace(0, 1e-9)
    df["rsi"]        = 100 - (100 / (1 + rs))
    std              = df["return"].std()
    df["z_score"]    = (df["return"] - df["return"].mean()) / (std if std else 1e-9)
    df["anomaly"]    = df["z_score"].abs() > 2
    return df


# ══════════════════════════════════════════════════════════
#  CHART HELPERS
# ══════════════════════════════════════════════════════════

LAYOUT_BASE = dict(
    font          = dict(family=CLASSIC_FONT, color=TEXT_COLOR, size=13),
    paper_bgcolor = BG_COLOR,
    plot_bgcolor  = BG_COLOR,
    xaxis         = dict(gridcolor=GRID_COLOR, zeroline=False, showline=False),
    yaxis         = dict(gridcolor=GRID_COLOR, zeroline=False, showline=False),
    margin        = dict(l=50, r=20, t=55, b=40),
    legend        = dict(font=dict(family=CLASSIC_FONT, size=12), bgcolor="rgba(0,0,0,0)"),
    hovermode     = "x unified",
)

def _title(text):
    return dict(text=text, font=dict(family=CLASSIC_FONT, size=17, color=ACCENT))

def hex_to_rgba(hex_color, alpha=0.15):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return f"rgba({r},{g},{b},{alpha})"


def chart_candlestick(df, ticker):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name=ticker,
        increasing_line_color="#50C878", decreasing_line_color="#FF6B6B",
    ))
    fig.add_trace(go.Scatter(x=df.index, y=df["ma7"],  mode="lines",
                             name="MA 7",  line=dict(color=ACCENT,    width=1.5, dash="dot")))
    fig.add_trace(go.Scatter(x=df.index, y=df["ma21"], mode="lines",
                             name="MA 21", line=dict(color="#4f8ef7", width=1.5, dash="dash")))
    fig.update_layout(**{**LAYOUT_BASE,
                         "title": _title(f"{ticker} — Candlestick + Moving Averages"),
                         "xaxis_rangeslider_visible": False})
    return fig


def chart_line(df, ticker, color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["close"], mode="lines",
                             name="Close", line=dict(color=color, width=2.5)))
    fig.add_trace(go.Scatter(x=df.index, y=df["ma7"],  mode="lines",
                             name="MA 7",  line=dict(color=ACCENT,    width=1.5, dash="dot")))
    fig.add_trace(go.Scatter(x=df.index, y=df["ma21"], mode="lines",
                             name="MA 21", line=dict(color="#4f8ef7", width=1.5, dash="dash")))
    fig.update_layout(**{**LAYOUT_BASE,
                         "title": _title(f"{ticker} — Close Price + Moving Averages")})
    return fig


def chart_rsi(df, ticker, color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["rsi"], mode="lines",
                             name="RSI(14)", line=dict(color=color, width=2)))
    fig.add_hrect(y0=70, y1=100, fillcolor="#FF6B6B", opacity=0.07, line_width=0)
    fig.add_hrect(y0=0,  y1=30,  fillcolor="#50C878", opacity=0.07, line_width=0)
    fig.add_hline(y=70, line_dash="dash", line_color="#FF6B6B",
                  annotation_text="Overbought 70",
                  annotation_font=dict(family=CLASSIC_FONT, color="#FF6B6B", size=11))
    fig.add_hline(y=30, line_dash="dash", line_color="#50C878",
                  annotation_text="Oversold 30",
                  annotation_font=dict(family=CLASSIC_FONT, color="#50C878", size=11))
    yax = {**LAYOUT_BASE["yaxis"], "range": [0, 100]}
    fig.update_layout(**{**LAYOUT_BASE, "title": _title(f"{ticker} — RSI (14-day)"),
                         "yaxis": yax})
    return fig


def chart_volatility(df, ticker, color):
    fig = go.Figure(go.Scatter(
        x=df.index, y=df["volatility"],
        fill="tozeroy", mode="lines",
        line=dict(color=color, width=2),
        fillcolor=hex_to_rgba(color, 0.15),
        name="Volatility %",
    ))
    fig.update_layout(**{**LAYOUT_BASE,
                         "title": _title(f"{ticker} — Annualised Volatility (%)")})
    return fig


def chart_volume(df, ticker, color):
    bar_colors = ["#50C878" if r >= 0 else "#FF6B6B"
                  for r in df["close"].pct_change().fillna(0)]
    fig = go.Figure(go.Bar(
        x=df.index, y=df["volume"],
        marker_color=bar_colors, opacity=0.8, name="Volume",
    ))
    fig.update_layout(**{**LAYOUT_BASE,
                         "title": _title(f"{ticker} — Daily Volume")})
    return fig


def chart_trend_comparison(frames, days=90):
    fig = go.Figure()
    for ticker, df in frames.items():
        if df.empty or "close" not in df.columns:
            continue
        s = df["close"].iloc[-days:]
        if s.empty or s.iloc[0] == 0:
            continue
        indexed = (s / s.iloc[0]) * 100
        fig.add_trace(go.Scatter(
            x=indexed.index, y=indexed, mode="lines", name=ticker,
            line=dict(color=STOCK_COLORS.get(ticker, "#fff"), width=2.5),
        ))
    fig.add_hline(y=100, line_dash="dot", line_color=GRID_COLOR)
    fig.update_layout(**{**LAYOUT_BASE,
                         "title": _title("90-Day Indexed Price Trend (Base = 100)")})
    return fig


def chart_correlation(frames):
    returns = {}
    for ticker, df in frames.items():
        if not df.empty and "close" in df.columns:
            returns[ticker] = df["close"].pct_change().dropna()
    if len(returns) < 2:
        return go.Figure()
    corr = pd.DataFrame(returns).corr()
    fig  = go.Figure(go.Heatmap(
        z=corr.values, x=corr.columns.tolist(), y=corr.index.tolist(),
        colorscale="RdYlGn", zmin=-1, zmax=1,
        text=corr.round(2).astype(str).values,
        texttemplate="%{text}",
        textfont=dict(family=CLASSIC_FONT, size=14),
    ))
    fig.update_layout(**{**LAYOUT_BASE, "title": _title("Return Correlation Matrix")})
    return fig


def chart_volatility_compare(frames):
    labels, values, colors = [], [], []
    for ticker, df in frames.items():
        if not df.empty and "volatility" in df.columns:
            v = df["volatility"].dropna()
            if not v.empty:
                labels.append(ticker)
                values.append(round(v.iloc[-1], 2))
                colors.append(STOCK_COLORS.get(ticker, "#fff"))
    fig = go.Figure(go.Bar(
        x=labels, y=values, marker_color=colors,
        text=[f"{v}%" for v in values],
        textposition="outside",
        textfont=dict(family=CLASSIC_FONT, size=13, color=TEXT_COLOR),
    ))
    fig.update_layout(**{**LAYOUT_BASE,
                         "title": _title("Current Annualised Volatility Comparison")})
    return fig


def chart_market_cap(quotes):
    labels = [t for t, q in quotes.items() if q["mktcap"] > 0]
    values = [quotes[t]["mktcap"] / 1e9 for t in labels]
    colors = [STOCK_COLORS.get(t, "#fff") for t in labels]
    fig = go.Figure(go.Bar(
        x=labels, y=values, marker_color=colors,
        text=[f"${v:,.0f}B" for v in values],
        textposition="outside",
        textfont=dict(family=CLASSIC_FONT, size=12, color=TEXT_COLOR),
    ))
    fig.update_layout(**{**LAYOUT_BASE,
                         "title": _title("Market Capitalisation (USD Billion)")})
    return fig


# ══════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════

st.sidebar.markdown(
    f"<h2 style='font-family:{CLASSIC_FONT};color:{ACCENT};'>⚙ Controls</h2>",
    unsafe_allow_html=True,
)

selected = st.sidebar.multiselect(
    "Select Stocks (2–6)",
    options=DEFAULT_TICKERS,
    default=DEFAULT_TICKERS,
)

period_map   = {"1 Month": "1mo", "3 Months": "3mo", "6 Months": "6mo", "1 Year": "1y"}
period_label = st.sidebar.selectbox("History Period", list(period_map.keys()), index=2)
period       = period_map[period_label]

chart_type = st.sidebar.selectbox("Primary Chart", ["Candlestick", "Line"])

st.sidebar.divider()
show_rsi  = st.sidebar.toggle("RSI Chart",           value=True)
show_vol  = st.sidebar.toggle("Volatility Chart",    value=True)
show_volm = st.sidebar.toggle("Volume Chart",        value=True)
show_corr = st.sidebar.toggle("Correlation Heatmap", value=True)
show_mcap = st.sidebar.toggle("Market Cap Chart",    value=True)

st.sidebar.divider()
if st.sidebar.button("🔄 Force Refresh"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown(
    f"<small style='color:#666;font-family:{CLASSIC_FONT};'>"
    "Powered by yfinance · No API key needed</small>",
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════
#  HEADER
# ══════════════════════════════════════════════════════════

st.markdown(
    f"<h1 style='text-align:center;font-family:{CLASSIC_FONT};"
    f"color:{ACCENT};letter-spacing:2px;'>"
    "📈 Real-Time Stock Analytics Dashboard</h1>"
    f"<p style='text-align:center;font-family:{CLASSIC_FONT};"
    "color:#aaa;font-size:15px;'>"
    "Live Quotes · Trends · RSI · Volatility · Correlation · Market Cap</p><hr>",
    unsafe_allow_html=True,
)

if not selected:
    st.warning("Please select at least one stock from the sidebar.")
    st.stop()


# ══════════════════════════════════════════════════════════
#  LOAD DATA
# ══════════════════════════════════════════════════════════

all_frames: dict[str, pd.DataFrame] = {}
all_quotes: dict[str, dict]         = {}

with st.spinner("📡 Fetching data from Yahoo Finance…"):
    for ticker in selected:
        df = fetch_data(ticker, period)
        q  = fetch_quote(ticker)
        if not df.empty:
            df = compute_metrics(df)
        all_frames[ticker] = df
        all_quotes[ticker] = q

failed       = [t for t, df in all_frames.items() if df.empty]
good_tickers = [t for t in selected if not all_frames[t].empty]

if failed:
    st.warning(f"Skipped (no data): {', '.join(failed)}")
if not good_tickers:
    st.error("No data loaded. Check your internet connection and try again.")
    st.stop()

good_frames = {t: all_frames[t] for t in good_tickers}


# ══════════════════════════════════════════════════════════
#  KPI CARDS
# ══════════════════════════════════════════════════════════

st.markdown(
    f"<h3 style='font-family:{CLASSIC_FONT};color:{ACCENT};'>📌 Live Quotes</h3>",
    unsafe_allow_html=True,
)

cols = st.columns(len(good_tickers))
for col, ticker in zip(cols, good_tickers):
    q     = all_quotes[ticker]
    arrow = "▲" if q["pct"] >= 0 else "▼"
    clr   = "#50C878" if q["pct"] >= 0 else "#FF6B6B"
    mc    = q["mktcap"]
    mcap  = f"${mc/1e12:.2f}T" if mc >= 1e12 else (f"${mc/1e9:.0f}B" if mc > 0 else "N/A")
    col.markdown(
        f"""<div class='metric-card'>
          <div style='font-family:{CLASSIC_FONT};font-size:19px;font-weight:700;color:{ACCENT};'>{ticker}</div>
          <div style='font-size:28px;font-weight:bold;color:{TEXT_COLOR};'>${q['price']:,.2f}</div>
          <div style='font-size:15px;color:{clr};'>{arrow} {q['pct']:+.2f}% &nbsp;({q['change']:+.2f})</div>
          <div style='font-size:12px;color:#888;margin-top:6px;'>
            H: ${q['high']:.2f} &nbsp;·&nbsp; L: ${q['low']:.2f}<br>
            Vol: {q['volume']:,} &nbsp;·&nbsp; MCap: {mcap}
          </div>
        </div>""",
        unsafe_allow_html=True,
    )

st.divider()


# ══════════════════════════════════════════════════════════
#  COMPARISON CHARTS
# ══════════════════════════════════════════════════════════

st.markdown(
    f"<h3 style='font-family:{CLASSIC_FONT};color:{ACCENT};'>📊 Multi-Stock Comparison</h3>",
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(chart_trend_comparison(good_frames), use_container_width=True)
with col2:
    st.plotly_chart(chart_volatility_compare(good_frames), use_container_width=True)

col3, col4 = st.columns(2)
with col3:
    if show_corr:
        st.plotly_chart(chart_correlation(good_frames), use_container_width=True)
with col4:
    if show_mcap:
        st.plotly_chart(chart_market_cap(all_quotes), use_container_width=True)

st.divider()


# ══════════════════════════════════════════════════════════
#  INDIVIDUAL DEEP-DIVE
# ══════════════════════════════════════════════════════════

st.markdown(
    f"<h3 style='font-family:{CLASSIC_FONT};color:{ACCENT};'>🔍 Individual Stock Deep-Dive</h3>",
    unsafe_allow_html=True,
)

active  = st.selectbox("Select stock for detailed analysis:", good_tickers)
df_a    = all_frames[active]
color_a = STOCK_COLORS.get(active, "#4f8ef7")

if chart_type == "Candlestick":
    st.plotly_chart(chart_candlestick(df_a, active), use_container_width=True)
else:
    st.plotly_chart(chart_line(df_a, active, color_a), use_container_width=True)

if "anomaly" in df_a.columns:
    anom = df_a[df_a["anomaly"]]
    if not anom.empty:
        st.warning(f"⚠️ {len(anom)} anomalous trading day(s) detected for {active} (|z-score| > 2).")

if show_rsi:
    st.plotly_chart(chart_rsi(df_a, active, color_a), use_container_width=True)

c1, c2 = st.columns(2)
if show_vol:
    with c1:
        st.plotly_chart(chart_volatility(df_a, active, color_a), use_container_width=True)
if show_volm:
    with c2:
        st.plotly_chart(chart_volume(df_a, active, color_a), use_container_width=True)

with st.expander("📋 Raw OHLCV Data (last 30 days)"):
    show_cols = [c for c in ["open","high","low","close","volume","ma7","ma21","rsi","volatility"]
                 if c in df_a.columns]
    st.dataframe(
        df_a[show_cols].tail(30).sort_index(ascending=False),
        use_container_width=True,
    )

st.divider()
st.markdown(
    f"<p style='text-align:center;font-family:{CLASSIC_FONT};color:#555;font-size:13px;'>"
    "Data via Yahoo Finance (yfinance) · No API key required · "
    "Built with Streamlit & Plotly</p>",
    unsafe_allow_html=True,
)