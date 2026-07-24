import ccxt
import pandas as pd
import ta
import streamlit as st
import time

st.set_page_config(page_title="Otomatik Binance Botu", layout="wide")

st.title("⚡ Binance Otomatik Trade Sinyal Paneli")
st.markdown("Bu panel tamamen otomatik çalışır ve her 30 saniyede bir kendini günceller.")

exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'}
})

def get_market_data():
    try:
        markets = exchange.load_markets()
        semboller = [s for s in markets if s.endswith('/USDT')][:20]
        
        rapor = []
        for symbol in semboller:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=50)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                rsi_indicator = ta.momentum.RSIIndicator(close=df['close'], window=14)
                df['RSI'] = rsi_indicator.rsi()
                
                macd = ta.trend.MACD(close=df['close'])
                df['MACD'] = macd.macd()
                df['MACD_Signal'] = macd.macd_signal()
                
                df['EMA_20'] = ta.trend.ema_indicator(close=df['close'], window=20)
                df['EMA_50'] = ta.trend.ema_indicator(close=df['close'], window=50)
                
                son_fiyat = df['close'].iloc[-1]
                son_rsi = df['RSI'].iloc[-1]
                son_macd = df['MACD'].iloc[-1]
                son_macd_signal = df['MACD_Signal'].iloc[-1]
                ema_20 = df['EMA_20'].iloc[-1]
                ema_50 = df['EMA_50'].iloc[-1]
                
                puan = 0
                if son_rsi < 35:
                    puan += 2
                elif son_rsi > 65:
                    puan -= 2
                    
                if son_macd > son_macd_signal:
                    puan += 1
                else:
                    puan -= 1
                    
                if ema_20 > ema_50:
                    puan += 1
                else:
                    puan -= 1
                
                if puan >= 3:
                    sinyal = "🟢 GÜÇLÜ LONG"
                elif puan == 1 or puan == 2:
                    sinyal = "🟢 LONG"
                elif puan <= -3:
                    sinyal = "🔴 GÜÇLÜ SHORT"
                elif puan == -1 or puan == -2:
                    sinyal = "🔴 SHORT"
                else:
                    sinyal = "⚪ NÖTR / BEKLE"
                
                rapor.append({
                    'Coin': symbol,
                    'Fiyat ($)': round(son_fiyat, 4),
                    'RSI': round(son_rsi, 2),
                    'MACD Durumu': "Pozitif" if son_macd > son_macd_signal else "Negatif",
                    'Trend (EMA)': "Yükseliş" if ema_20 > ema_50 else "Düşüş",
                    'Sinyal / Tahmin': sinyal
                })
            except Exception:
                continue
                
        return pd.DataFrame(rapor)
    except Exception as e:
        return pd.DataFrame()

durum_alani = st.empty()
tablo_alani = st.empty()

durum_alani.info("🔄 Binance verileri yükleniyor...")

df_sonuc = get_market_data()

if not df_sonuc.empty:
    tablo_alani.dataframe(df_sonuc, use_container_width=True)
else:
    tablo_alani.warning("⚠️ Veriler alınamadı.")

for kalan_sure in range(30, 0, -1):
    durum_alani.markdown(
    "⏳ **Otomatik yenilenmeye kalan süre:** `{}` saniye".format(kalan_sure)
)
    time.sleep(1)

st.rerun()