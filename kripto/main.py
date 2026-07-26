import ccxt
import pandas as pd
import streamlit as st
import time

st.set_page_config(page_title="MEXC Sınırsız Piyasa Tarayıcısı", layout="wide")

st.title("⚡ MEXC İşlem Asistanı")
st.markdown("Bu panel **MEXC borsasındaki tüm USDT coinlerini** anında tarar ve her **5 dakikada bir** güncellenir.")

@st.cache_data(ttl=280)
def get_market_data():
    try:
        # MEXC borsasına bağlanıyoruz
        exchange = ccxt.mexc({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        
        markets = exchange.load_markets()
        semboller = [s for s in markets if s.endswith('/USDT')]
        
        # Takılmayı önlemek için toplu veri çekme fonksiyonu kullanıyoruz
        tickers = exchange.fetch_tickers(semboller)
        
        rapor = []
        for symbol in semboller:
            try:
                if symbol in tickers:
                    ticker = tickers[symbol]
                    son_fiyat = ticker.get('last')
                    if not son_fiyat:
                        continue
                    
                    degisim = ticker.get('percentage', 0)
                    if degisim is None:
                        degisim = 0
                        
                    sinyal = "🟢 LONG" if degisim >= 0 else "🔴 SHORT"
                    
                    if "LONG" in sinyal:
                        tp_degeri = son_fiyat * 1.025
                        stop_degeri = son_fiyat * 0.985
                        tahmini_kazanc = "100$ bütçe (5x) ile ~12.5$ kâr"
                    else:
                        tp_degeri = son_fiyat * 0.975
                        stop_degeri = son_fiyat * 1.015
                        tahmini_kazanc = "100$ bütçe (5x) ile ~12.5$ kâr"

                    rapor.append({
                        'Coin': symbol,
                        'Fiyat ($)': round(float(son_fiyat), 6),
                        '24s Değişim (%)': round(float(degisim), 2),
                        'Sinyal / Tahmin': sinyal,
                        'Önerilen İşlem': "LONG (AL)" if "LONG" in sinyal else "SHORT (SAT)",
                        'Giriş Fiyatı ($)': round(float(son_fiyat), 6),
                        'TP (Hedef) ($)': round(tp_degeri, 6),
                        'STOP (Zarar Durdur) ($)': round(stop_degeri, 6),
                        'Tahmini Kâr Potansiyeli': tahmini_kazanc
                    })
            except Exception:
                continue
                
        return pd.DataFrame(rapor)
    except Exception as e:
        return pd.DataFrame()

st.sidebar.header("🔍 MEXC Coin Arama Paneli")
arama_input = st.sidebar.text_input("Dilediğiniz Coini Yazın (Örn: BTC, MEME, cüzdan coinleri):", "").upper()

durum_alani = st.empty()
tablo_alani = st.empty()

durum_alani.info("🔄 MEXC borsasındaki tüm coinler anında taranıyor, lütfen bekleyin...")

df_sonuc = get_market_data()

if not df_sonuc.empty:
    durum_alani.empty()
    if arama_input:
        filtrelenmis_df = df_sonuc[df_sonuc['Coin'].str.contains(arama_input)]
        if not filtrelenmis_df.empty:
            st.success("🎯 '{}' MEXC'de bulundu! İşlem stratejisi:".format(arama_input))
            st.dataframe(filtrelenmis_df, use_container_width=True)
            
            for index, row in filtrelenmis_df.iterrows():
                st.markdown("### 📊 **{} Detaylı Strateji Paneli**".format(row['Coin']))
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Anlık Fiyat", "{} $".format(row['Fiyat ($)']))
                col2.metric("Önerilen İşlem", row['Önerilen İşlem'])
                col3.metric("Hedef (TP)", "{} $".format(row['TP (Hedef) ($)']))
                col4.metric("Stop Loss", "{} $".format(row['STOP (Zarar Durdur) ($)']))
                st.info("💡 **Grafik Notu:** Potansiyel kazanç durumu: **{}**".format(row['Tahmini Kâr Potansiyeli']))
        else:
            st.warning("⚠️ Aradığınız coin MEXC listesinde bulunamadı. Tüm MEXC listesi aşağıdadır:")
            st.dataframe(df_sonuc, use_container_width=True)
    else:
        st.markdown("### 📋 MEXC Tüm Coinler Listesi (Toplam: {} Coin)".format(len(df_sonuc)))
        st.dataframe(df_sonuc, use_container_width=True)
else:
    durum_alani.warning("⚠️ Veriler alınamadı. Ağ bağlantınızı kontrol edin.")

for kalan_sure in range(300, 0, -1):
    dakika = kalan_sure // 60
    saniye = kalan_sure % 60
    durum_alani.markdown(
        "⏳ **Otomatik yenilenmeye kalan süre:** `{} dakika {} saniye`".format(dakika, saniye)
    )
    time.sleep(1)

st.rerun()
