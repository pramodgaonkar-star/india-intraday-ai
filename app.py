import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

st.set_page_config(page_title="India Intraday AI Scanner", page_icon="📈", layout="wide")

NIFTY50 = {
    "RELIANCE.NS":"Reliance Industries","HDFCBANK.NS":"HDFC Bank","ICICIBANK.NS":"ICICI Bank",
    "SBIN.NS":"State Bank of India","INFY.NS":"Infosys","TCS.NS":"TCS","BHARTIARTL.NS":"Bharti Airtel",
    "ITC.NS":"ITC","LT.NS":"Larsen & Toubro","AXISBANK.NS":"Axis Bank","KOTAKBANK.NS":"Kotak Mahindra Bank",
    "M&M.NS":"Mahindra & Mahindra","HINDUNILVR.NS":"Hindustan Unilever","SUNPHARMA.NS":"Sun Pharma",
    "MARUTI.NS":"Maruti Suzuki","TITAN.NS":"Titan Company","ADANIENT.NS":"Adani Enterprises",
    "ADANIPORTS.NS":"Adani Ports","BAJFINANCE.NS":"Bajaj Finance","BAJAJFINSV.NS":"Bajaj Finserv",
    "HCLTECH.NS":"HCL Technologies","WIPRO.NS":"Wipro","TECHM.NS":"Tech Mahindra",
    "TATASTEEL.NS":"Tata Steel","JSWSTEEL.NS":"JSW Steel","NTPC.NS":"NTPC","POWERGRID.NS":"Power Grid",
    "ONGC.NS":"ONGC","COALINDIA.NS":"Coal India","TATAMOTORS.NS":"Tata Motors",
    "ULTRACEMCO.NS":"UltraTech Cement","ASIANPAINT.NS":"Asian Paints","NESTLEIND.NS":"Nestle India",
    "CIPLA.NS":"Cipla","DRREDDY.NS":"Dr Reddy's","EICHERMOT.NS":"Eicher Motors",
    "GRASIM.NS":"Grasim Industries","HEROMOTOCO.NS":"Hero MotoCorp","HINDALCO.NS":"Hindalco",
    "INDUSINDBK.NS":"IndusInd Bank","APOLLOHOSP.NS":"Apollo Hospitals","BEL.NS":"Bharat Electronics",
    "TRENT.NS":"Trent","SHRIRAMFIN.NS":"Shriram Finance","JIOFIN.NS":"Jio Financial",
    "TATACONSUM.NS":"Tata Consumer","BPCL.NS":"BPCL","ETERNAL.NS":"Eternal"
}

@st.cache_data(ttl=60)
def get_data(ticker, period="5d", interval="5m"):
    return yf.download(ticker, period=period, interval=interval, auto_adjust=False, progress=False)

def flat(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def indicators(df):
    df = flat(df).copy()
    if df.empty: return df
    for c in ["Open","High","Low","Close","Volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["EMA9"] = df.Close.ewm(span=9, adjust=False).mean()
    df["EMA20"] = df.Close.ewm(span=20, adjust=False).mean()
    df["EMA50"] = df.Close.ewm(span=50, adjust=False).mean()
    delta = df.Close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = 100 - (100/(1+rs))
    tr = pd.concat([
        df.High-df.Low, (df.High-df.Close.shift()).abs(), (df.Low-df.Close.shift()).abs()
    ], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()
    typical = (df.High + df.Low + df.Close)/3
    # Session VWAP; reset at each date
    df["PV"] = typical * df.Volume
    df["CumPV"] = df.groupby(df.index.date)["PV"].cumsum()
    df["CumVol"] = df.groupby(df.index.date)["Volume"].cumsum()
    df["VWAP"] = df.CumPV / df.CumVol.replace(0, np.nan)
    df["VolAvg20"] = df.Volume.rolling(20).mean()
    df["VolRatio"] = df.Volume / df.VolAvg20
    df["High20"] = df.High.rolling(20).max().shift(1)
    df["Low20"] = df.Low.rolling(20).min().shift(1)
    return df.dropna(subset=["EMA20","RSI","ATR","VWAP"])

def score_row(df):
    if len(df) < 30: return None
    x = df.iloc[-1]
    score = 0
    reasons = []
    bullish = 0
    if x.Close > x.VWAP: score += 15; bullish += 1; reasons.append("Above VWAP")
    if x.EMA9 > x.EMA20: score += 15; bullish += 1; reasons.append("EMA9>EMA20")
    if x.EMA20 > x.EMA50: score += 10; bullish += 1; reasons.append("EMA20>EMA50")
    if 52 <= x.RSI <= 70: score += 10; reasons.append("Healthy RSI")
    elif x.RSI > 70: score -= 5
    if x.VolRatio >= 1.5: score += 15; reasons.append("High volume")
    elif x.VolRatio >= 1.1: score += 7
    if x.Close > x.High20: score += 20; reasons.append("20-bar breakout")
    if x.Close < x.Low20: score -= 20
    if x.Close > x.Open: score += 5
    # ATR sanity: avoid extremely quiet names
    if x.ATR / x.Close >= 0.004: score += 5; reasons.append("Tradable volatility")
    score = int(max(0, min(100, score)))
    signal = "BUY" if score >= 65 and bullish >= 3 else ("WATCH" if score >= 50 else "AVOID")
    entry = float(x.Close)
    atr = float(x.ATR)
    if signal == "BUY":
        sl = entry - 1.2*atr
        t1 = entry + 1.8*atr
        t2 = entry + 2.5*atr
    else:
        sl = entry - 1.2*atr
        t1 = entry + 1.8*atr
        t2 = entry + 2.5*atr
    return dict(Score=score, Signal=signal, Entry=entry, StopLoss=sl, Target1=t1, Target2=t2,
                RSI=float(x.RSI), VWAP=float(x.VWAP), VolRatio=float(x.VolRatio), Reasons=", ".join(reasons))

@st.cache_data(ttl=60)
def scan(tickers):
    rows=[]
    for t in tickers:
        try:
            d=indicators(get_data(t))
            r=score_row(d)
            if r:
                r["Ticker"]=t
                r["Company"]=NIFTY50.get(t,t)
                rows.append(r)
        except Exception:
            pass
    if not rows: return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["Score","VolRatio"], ascending=False)

st.title("🇮🇳 India Intraday AI Scanner")
st.caption("Free/paper-trading prototype • NSE candidates • 5-minute technical scanner")

with st.sidebar:
    st.header("Scanner")
    universe = st.multiselect("Stocks", list(NIFTY50.keys()), default=list(NIFTY50.keys())[:15],
                             format_func=lambda x: NIFTY50[x])
    if st.button("🔄 Scan now", type="primary"):
        st.cache_data.clear()
    min_score = st.slider("Minimum score", 40, 90, 60)
    risk_pct = st.slider("Risk per trade (%)", 0.25, 2.0, 1.0, 0.25)
    capital = st.number_input("Paper capital (₹)", 10000, 10000000, 100000, 10000)

st.info("⚠️ Signals are educational/paper-trading signals, not guaranteed returns or investment advice. Verify live NSE prices before trading.")

if not universe:
    st.warning("Select at least one stock.")
    st.stop()

with st.spinner("Scanning..."):
    result = scan(tuple(universe))

if result.empty:
    st.error("No data returned. Yahoo Finance may be temporarily unavailable. Try again in a minute.")
    st.stop()

view = result[result.Score >= min_score].copy()
cols = ["Company","Signal","Score","Entry","StopLoss","Target1","Target2","RSI","VolRatio"]
st.subheader("Top setups")
st.dataframe(view[cols].style.format({
    "Entry":"₹{:.2f}","StopLoss":"₹{:.2f}","Target1":"₹{:.2f}","Target2":"₹{:.2f}",
    "Score":"{:.0f}","RSI":"{:.1f}","VolRatio":"{:.2f}x"
}), use_container_width=True, hide_index=True)

if not view.empty:
    best = view.iloc[0]
    st.subheader(f"🎯 Best current setup: {best.Company}")
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Signal", best.Signal)
    c2.metric("Score", f"{best.Score}/100")
    c3.metric("Entry", f"₹{best.Entry:.2f}")
    c4.metric("Stop", f"₹{best.StopLoss:.2f}")
    c5.metric("Target 1", f"₹{best.Target1:.2f}")
    st.write("**Why:**", best.Reasons)
    risk_rupees = capital * risk_pct / 100
    per_share = max(best.Entry - best.StopLoss, 0.01)
    qty = int(risk_rupees / per_share)
    st.write(f"**Paper position size:** {qty} shares for approximately ₹{risk_rupees:,.0f} maximum planned risk.")

ticker = st.selectbox("Chart / inspect stock", universe, format_func=lambda x: NIFTY50[x])
chart_df = indicators(get_data(ticker, period="5d", interval="5m"))
if not chart_df.empty:
    st.line_chart(chart_df[["Close","VWAP","EMA9","EMA20","EMA50"]], height=420)

st.caption(f"Last app refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (app/server time)")
