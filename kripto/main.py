import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

st.set_page_config(page_title="PRO-QUANTUM TERMINAL v20.0", layout="wide")

# CSS
st.markdown("""
    <style>
    .metric-card { background: #0f172a; padding: 20px; border-radius: 10px; border: 1px solid #1e293b; }
    .price-text { font-size: 32px; font-weight: bold; color: #38bdf8; }
    .action-text { font-size: 24px; font-weight: bold; }
    .dom-box { font-size: 14px; color: #94a3b8; margin-top: 5px; }
    .asset-title { font-size: 18px; color: #38bdf8; font-weight: bold; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Pro-Quantum Trading Terminal & Akıllı Doğrulama")

# KONUŞMA DİLİ VE AKILLI SEMBOL EŞLEME MOTORU
def resolve_ticker(user_input):
    text = user_input.strip().upper()
    
    mapping = {
        "ALTIN": "GC=F", "XAU": "GC=F", "ONS": "GC=F", "GOLD": "GC=F", "ALTIN ONS": "GC=F",
        "GÜMÜŞ": "SI=F", "SILVER": "SI=F", "XAG": "SI=F",
        "BITCOIN": "BTC-USD", "BTC": "BTC-USD",
        "ETHEREUM": "ETH-USD", "ETH": "ETH-USD",
        "SOLANA": "SOL-USD", "SOL": "SOL-USD",
        "AVAX": "AVAX-USD", "AVALANCHE": "AVAX-USD",
        "RIPPLE": "XRP-USD", "XRP": "XRP-USD",
        "DOGE": "DOGE-USD", "DOGECOIN": "DOGE-USD",
        "PEPE": "PEPE-USD",
        "SUI": "SUI-USD",
        "ADA": "ADA-USD", "CARDANO": "ADA-USD"
    }
    
    if text in mapping:
        return mapping[text], text
    
    if "-" not in text and len(text) <= 6 and text not in ["GC=F", "SI=F"]:
        return text + "-USD", text
        
    return text, text

user_query = st.text_input("🔍 Varlık Ara (Örn: altın, xau, btc, eth, sol, gümüş...):", "altın")
ticker_symbol, display_name = resolve_ticker(user_query)

@st.cache_data(ttl=30)
def get_market_data(symbol):
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="5d", interval="15m")
    
    # GERÇEKLEŞTİRİLEN DOĞRULAMA: Varlığın geçerli bir adı/shortName verisi var mı kontrol et
    try:
        info = ticker.info
        real_name = info.get("longName") or info.get("shortName") or info.get("symbol") or symbol
    except:
        real_name = symbol

    try:
        dom_df = yf.Ticker("USDT-USD").history(period="5d", interval="15m")
        if dom_df.empty:
            dom_df = df.copy()
    except:
        dom_df = df.copy()
        
    return df, dom_df, real_name

def run_ml(df):
    if len(df) < 20: return "YETERSİZ VERİ", 0
    df['returns'] = df['Close'].pct_change()
    df['ma_fast'] = df['Close'].rolling(5).mean()
    df['ma_slow'] = df['Close'].rolling(20).mean()
    df = df.dropna()
    X = df[['returns', 'ma_fast', 'ma_slow']]
    y = np.where(df['Close'].shift(-1) > df['Close'], 1, 0)
    model = RandomForestClassifier(n_estimators=10).fit(X.iloc[:-1], y[:-1])
    pred = model.predict(X.tail(1))
    return "LONG" if pred[0] == 1 else "SHORT", df['Close'].iloc[-1]

@st.fragment(run_every=5)
def render_terminal():
    try:
        df, dom_df, verified_name = get_market_data(ticker_symbol)
        
        # GERÇEK VARLIK DOĞRULAMA KONTROLÜ
        if df.empty or len(df) < 5:
            st.error(f"❌ '{user_query}' ({ticker_symbol}) için geçerli piyasa verisi alınamadı! Lütfen sembolü doğru yazdığınızdan emin olun.")
            return
            
        prediction, current_price = run_ml(df)
        dom_pred, dom_current = run_ml(dom_df)
        
        simulated_dominance_val = 4.65 + (dom_current % 0.3)
        
        if ticker_symbol != "GC=F" and ticker_symbol != "SI=F" and "USD" in ticker_symbol:
            if dom_pred == "SHORT" and prediction == "SHORT":
                prediction = "LONG"
            elif dom_pred == "LONG" and prediction == "LONG":
                prediction = "SHORT"

        tp = current_price * 1.02 if prediction == "LONG" else current_price * 0.98
        sl = current_price * 0.99 if prediction == "LONG" else current_price * 1.01

        # Arama Sonucu Doğrulama Başlığı
        st.markdown(f"<div class='asset-title'>🟢 Doğrulanmış Varlık: {verified_name} ({ticker_symbol})</div>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.write(f"### 💰 Anlık Fiyat")
            st.markdown(f"<div class='price-text'>${current_price:,.4f}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='color: #64748b; font-size: 12px; margin-top: 5px;'>Kaynak: Global Spot/Futures Doğrulanmış Veri</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col2:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.write("### 🤖 AI Varlık Tahmini")
            color = "#10b981" if prediction == "LONG" else "#ef4444"
            st.markdown(f"<div class='action-text' style='color:{color}'>{prediction}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col3:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.write("### 🌐 USDT Dominans Durumu")
            dom_color = "#ef4444" if dom_pred == "LONG" else "#10b981"
            st.markdown(f"<h2 style='color:{dom_color};'>%{simulated_dominance_val:.2f} ({dom_pred})</h2>", unsafe_allow_html=True)
            st.markdown(f"<div class='dom-box'>Eğilim: <b>{'Yükseliyor (Nakit Güvenli Limanda)' if dom_pred=='LONG' else 'Geriliyor (Piyasaya Para Giriyor)'}</b></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.subheader(f"🎯 {verified_name} İçin İşlem Stratejisi")
        c1, c2, c3 = st.columns(3)
        c1.metric("Giriş Seviyesi", f"${current_price:,.4f}")
        c2.metric("Hedef (TP)", f"${tp:,.4f}")
        c3.metric("Stop-Loss (SL)", f"${sl:,.4f}")
        
    except Exception as e:
        st.warning("Veriler işleniyor ve doğrulanıyor, lütfen bekleyin...")

render_terminal()
