import asyncio
import aiohttp
import ccxt.async_support as ccxt_async
import pandas as pd
import streamlit as st
import ta
import time

st.set_page_config(page_title="MEXC Seçmeli Çift Periyotlu Panel", layout="wide")

st.title("⚡ MEXC Akıllı Arama ve Çift Periyotlu Tahmin Paneli")
st.markdown("Arama çubuğuna yazdığınız ifadeye uyan **tüm coin seçenekleri bir listede görünür**, dilediğinizi seçerek çift periyotlu analizini yapabilirsiniz.")

if 'kalan_sure' not in st.session_state:
    st.session_state.kalan_sure = 300

arama_input = st.sidebar.text_input("Aranacak Kelimeyi Yazın (Örn: BTC, ETH, PEPE):", "BTC").upper()

if st.sidebar.button("🔄 Piyasayı Şimdi Tara ve Güncelle"):
    st.session_state.kalan_sure = 300
    st.cache_data.clear()
    st.rerun()

sayac_alani = st.sidebar.empty()

# 1. Aşama: Yazılan kelimeyi içeren TÜM USDT paritelerini liste olarak çeken fonksiyon
async def fetch_matching_markets(symbol_query):
    exchange = ccxt_async.mexc({
        'enableRateLimit': True,
        'timeout': 30000,
        'options': {'defaultType': 'spot'}
    })
    try:
        markets = await exchange.load_markets()
        # Arama terimini içeren ve /USDT ile biten tüm coinleri buluyoruz
        eslesenler = [s for s in markets if symbol_query in s and s.endswith('/USDT') and not any(x in s for x in ['UP/USDT', 'DOWN/USDT', 'BEAR/USDT', 'BULL/USDT'])]
        return sorted(eslesenler)
    except Exception:
        return []
    finally:
        await exchange.close()

# 2. Aşama: Seçilen spesifik coinin 5m ve 15m verilerini çeken fonksiyon
async def fetch_both_timeframes(target_symbol):
    exchange = ccxt_async.mexc({
        'enableRateLimit': True,
        'timeout': 30000,
        'options': {'defaultType': 'spot'}
    })
    sonuclar = {}
    try:
        for tf in ['5m', '15m']:
            try:
                ohlcv = await exchange.fetch_ohlcv(target_symbol, timeframe=tf, limit=40)
                if len(ohlcv) < 25:
                    continue
                
                df_mum = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                son_fiyat = float(df_mum['close'].iloc[-1])
                
                df_mum['ema9'] = ta.trend.ema_indicator(df_mum['close'], window=9)
                df_mum['ema21'] = ta.trend.ema_indicator(df_mum['close'], window=21)
                df_mum['rsi'] = ta.momentum.rsi(df_mum['close'], window=14)
                
                ema9_son = df_mum['ema9'].iloc[-1]
                ema21_son = df_mum['ema21'].iloc[-1]
                rsi_son = df_mum['rsi'].iloc[-1]
                
                if pd.isna(ema9_son) or pd.isna(ema21_son) or pd.isna(rsi_son):
                    continue

                if ema9_son > ema21_son and rsi_son > 47:
                    sinyal = "🟢 LONG"
                elif ema9_son < ema21_son and rsi_son < 53:
                    sinyal = "🔴 SHORT"
                else:
                    if son_fiyat > float(df_mum['close'].iloc[-2]):
                        sinyal = "🟢 LONG"
                    else:
                        sinyal = "🔴 SHORT"

                if tf == '15m':
                    tp_oran = 1.025  
                    stop_oran = 0.985 
                    tahmini_kazanc = "100$ bütçe (5x) ile ~12$ - 15$ kâr (15m Trend)"
                else:
                    tp_oran = 1.012  
                    stop_oran = 0.994 
                    tahmini_kazanc = "100$ bütçe (5x) ile ~6$ - 8$ kâr (5m Scalping)"

                if "LONG" in sinyal:
                    tp_degeri = son_fiyat * tp_oran
                    stop_degeri = son_fiyat * stop_oran
                else:
                    tp_degeri = son_fiyat * (2 - tp_oran)
                    stop_degeri = son_fiyat * (2 - stop_oran) if stop_oran < 1 else son_fiyat * 1.01

                sonuclar[tf] = {
                    'Coin': target_symbol,
                    'Zaman Dilimi': tf.upper(),
                    'Fiyat ($)': round(son_fiyat, 6),
                    'RSI (14)': round(float(rsi_son), 1),
                    'Sinyal / Tahmin': sinyal,
                    'Önerilen İşlem': "LONG (AL)" if "LONG" in sinyal else "SHORT (SAT)",
                    'Giriş Fiyatı ($)': round(son_fiyat, 6),
                    'TP (Hedef) ($)': round(float(tp_degeri), 6),
                    'STOP (Zarar Durdur) ($)': round(float(stop_degeri), 6),
                    'Tahmini Kâr Potansiyeli': tahmini_kazanc
                }
            except Exception:
                continue
        return sonuclar
    except Exception:
        return {}
    finally:
        await exchange.close()

@st.cache_data(ttl=120, show_spinner="Piyasa eşleşmeleri taranıyor...")
def get_market_list_cached(query):
    try:
        return asyncio.run(fetch_matching_markets(query))
    except Exception:
        return []

@st.cache_data(ttl=120, show_spinner="Seçilen coinin mum verileri analiz ediliyor...")
def get_coin_data_cached(symbol):
    try:
        return asyncio.run(fetch_both_timeframes(symbol))
    except Exception:
        return {}

if arama_input:
    bulunan_liste = get_market_list_cached(arama_input)
    
    if bulunan_liste:
        st.sidebar.success(f"🎯 {len(bulunan_liste)} adet eşleşen coin bulundu.")
        # Sol menüde eşleşen tüm alternatiflerin çıkacağı açılır seçim kutusu (selectbox)
        secilen_coin = st.sidebar.selectbox("Listeden İstediğiniz Coini Seçin:", bulunan_liste)
        
        if secilen_coin:
            veri_sozlugu = get_coin_data_cached(secilen_coin)
            
            if veri_sozlugu:
                st.success(f"✅ Seçilen Aktif Coin: **{secilen_coin}** için çift periyotlu analiz aşağıdadır.")
                
                col_5m, col_15m = st.columns(2)
                
                with col_5m:
                    st.markdown("### ⏱️ 5 Dakikalık Periyot (Scalping)")
                    if '5m' in veri_sozlugu:
                        d5 = veri_sozlugu['5m']
                        st.metric("Anlık Fiyat", f"{d5['Fiyat ($)']} $")
                        st.metric("RSI Değeri", d5['RSI (14)'])
                        st.metric("Önerilen İşlem", d5['Önerilen İşlem'])
                        st.metric("Hedef (TP)", f"{d5['TP (Hedef) ($)']} $")
                        st.metric("Stop Loss", f"{d5['STOP (Zarar Durdur) ($)']} $")
                        st.info(f"💡 **Strateji:** {d5['Sinyal / Tahmin']} | {d5['Tahmini Kâr Potansiyeli']}")
                    else:
                        st.warning("5m verisi alınamadı.")
                        
                with col_15m:
                    st.markdown("### ⏱️ 15 Dakikalık Periyot (Trend)")
                    if '15m' in veri_sozlugu:
                        d15 = veri_sozlugu['15m']
                        st.metric("Anlık Fiyat", f"{d15['Fiyat ($)']} $")
                        st.metric("RSI Değeri", d15['RSI (14)'])
                        st.metric("Önerilen İşlem", d15['Önerilen İşlem'])
                        st.metric("Hedef (TP)", f"{d15['TP (Hedef) ($)']} $")
                        st.metric("Stop Loss", f"{d15['STOP (Zarar Durdur) ($)']} $")
                        st.info(f"💡 **Strateji:** {d15['Sinyal / Tahmin']} | {d15['Tahmini Kâr Potansiyeli']}")
                    else:
                        st.warning("15m verisi alınamadı.")
            else:
                st.error("Seçilen coinin mum verileri yüklenirken hata oluştu.")
    else:
        st.warning(f"⚠️ '{arama_input}' ile eşleşen hiçbir USDT paritesi bulunamadı.")
else:
    st.info("👈 Lütfen sol menüdeki arama çubuğuna bir ifade girin.")

while st.session_state.kalan_sure > 0:
    dakika = st.session_state.kalan_sure // 60
    saniye = st.session_state.kalan_sure % 60
    sayac_alani.info(f"⏳ **Otomatik Yenilemeye Kalan Süre:** `{dakika} dk {saniye} sn`")
    time.sleep(1)
    st.session_state.kalan_sure -= 1

st.cache_data.clear()
st.rerun()
