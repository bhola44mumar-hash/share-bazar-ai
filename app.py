import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import io
from PIL import Image
from gtts import gTTS
from google import genai

st.set_page_config(page_title="शेयर बाजार मस्तिष्क AI Pro", page_icon="🧠", layout="centered")

st.markdown('<div style="background: linear-gradient(90deg, #1e3d59, #2b5876);padding:14px;border-radius:12px;text-align:center;"><h2 style="color:white;margin:0;">🧠 शेयर बाजार मस्तिष्क AI (Pro)</h2><p style="color:#e0e6ed;margin:4px 0 0 0;font-size:13px;">1000+ ट्रेडर्स ज्ञान • लाइव चार्ट • पेपर ट्रेडिंग • चार्ट स्कैनर • हिंदी आवाज़</p></div>', unsafe_allow_html=True)

saved_key = ""
try:
    saved_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    saved_key = ""

with st.sidebar:
    st.header("🔑 AI सेटिंग्स")
    if saved_key:
        api_key = saved_key
        st.success("✅ API Key स्थायी रूप से सेव है!")
    else:
        api_key = st.text_input("अपनी Gemini API Key डालें:", type="password", placeholder="यहाँ अपनी Key पेस्ट करें...")
    st.divider()
    st.header("🔊 आवाज़ सेटिंग")
    voice_on = st.checkbox("AI के जवाब हिंदी में बोलकर सुनाएं", value=True)
    st.info("यह सुपर-ऐप केवल शेयर बाजार, Intraday और F&O के लिए बना है।")

@st.cache_data(ttl=120)
def get_indices():
    res = {}
    for name, sym in [("Nifty 50", "^NSEI"), ("Bank Nifty", "^NSEBANK"), ("India VIX", "^INDIAVIX")]:
        try:
            d = yf.Ticker(sym).history(period="2d")
            if len(d) >= 2:
                c = round(float(d['Close'].iloc[-1]), 2)
                p = round(float(d['Close'].iloc[-2]), 2)
                res[name] = (c, round(c - p, 2))
            elif len(d) == 1:
                res[name] = (round(float(d['Close'].iloc[-1]), 2), 0.0)
        except Exception:
            pass
    return res

indices = get_indices()
if indices:
    cols = st.columns(len(indices))
    for i, (k, (val, chg)) in enumerate(indices.items()):
        cols[i].metric(k, f"{val}", f"{chg}")

@st.cache_data(ttl=86400)
def load_nifty_500():
    fallback = {
        "SBI (SBIN)": "SBIN.NS", "Reliance (RELIANCE)": "RELIANCE.NS",
        "HDFC Bank (HDFCBANK)": "HDFCBANK.NS", "Infosys (INFY)": "INFY.NS",
        "TCS (TCS)": "TCS.NS", "ITC (ITC)": "ITC.NS",
        "Tata Motors (TATAMOTORS)": "TATAMOTORS.NS", "ICICI Bank (ICICIBANK)": "ICICIBANK.NS",
        "Bharti Airtel (BHARTIARTL)": "BHARTIARTL.NS", "Larsen & Toubro (LT)": "LT.NS"
    }
    try:
        url = "https://nseindia.com"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            df = pd.read_csv(io.StringIO(r.text))
            shares = {f"{str(row['Company Name']).strip()} ({str(row['Symbol']).strip()})": f"{str(row['Symbol']).strip()}.NS" for _, row in df.iterrows()}
            if len(shares) > 50:
                return shares
    except Exception:
        pass
    return fallback

ALL_SHARES = load_nifty_500()

if "wallet" not in st.session_state:
    st.session_state.wallet = 100000.0
if "positions" not in st.session_state:
    st.session_state.positions = {}
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "नमस्ते! मैं आपका **शेयर बाजार मस्तिष्क AI (Pro)** हूँ। आप मुझसे कोई भी सवाल पूछ सकते हैं या ऊपर **चार्ट की फोटो** अपलोड करके उसका विश्लेषण करवा सकते हैं!"}
    ]

tab1, tab2, tab3 = st.tabs(["💬 AI गुरु & चार्ट स्कैनर", "📊 लाइव चार्ट & इंडिकेटर", "💰 पेपर ट्रेडिंग (प्रैक्टिस)"])

selected_share = st.selectbox("🔍 शेयर खोजें या चुनें (Top 500):", sorted(list(ALL_SHARES.keys())))
ticker = ALL_SHARES[selected_share]

curr_price = 0.0
live_context = ""
hist_data = pd.DataFrame()

try:
    hist_data = yf.Ticker(ticker).history(period="5d", interval="15m")
    if not hist_data.empty and len(hist_data) >= 15:
        curr_price = round(float(hist_data['Close'].iloc[-1]), 2)
        prev_close = round(float(hist_data['Close'].iloc[-2]), 2)
        diff = round(curr_price - prev_close, 2)
        delta = hist_data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi_series = 100 - (100 / (1 + rs))
        rsi_val = round(float(rsi_series.iloc[-1]), 1) if not pd.isna(rsi_series.iloc[-1]) else 50.0
        ma_fast = round(float(hist_data['Close'].tail(5).mean()), 2)
        ma_slow = round(float(hist_data['Close'].tail(15).mean()), 2)
        support = round(float(hist_data['Low'].tail(20).min()), 2)
        resistance = round(float(hist_data['High'].tail(20).max()), 2)
        trend = "तेज़ी (Bullish)" if ma_fast > ma_slow else "कमजोरी (Bearish)"
        live_context = f"शेयर: {selected_share} | ताज़ा भाव: ₹{curr_price} | बदलाव: ₹{diff} | ट्रेंड: {trend} | RSI(14): {rsi_val} | Support: ₹{support} | Resistance: ₹{resistance}"
except Exception:
    pass

with tab2:
    if curr_price > 0:
        c1, c2, c3 = st.columns(3)
        c1.metric("ताज़ा भाव", f"₹{curr_price}", f"{diff}")
        c2.metric("AI ट्रेंड", trend)
        c3.metric("RSI (ताकत)", f"{rsi_val}", "Overbought >70 | Oversold <30")
        st.write(f"🛡️ **मजबूत Support (सहारा):** ₹{support} &nbsp;|&nbsp; 🚧 **Resistance (रुकावट):** ₹{resistance}")
        st.line_chart(hist_data['Close'].tail(50))
    else:
        st.warning("डेटा लोड नहीं हो सका, कृपया इंटरनेट जांचें या दूसरा शेयर चुनें।")

    st.divider()
    if st.button("🔎 आज के टॉप 8 शेयरों का तेज़ स्कैन करें"):
        with st.spinner("बाजार स्कैन हो रहा है..."):
            quick_list = ["SBIN.NS", "RELIANCE.NS", "HDFCBANK.NS", "INFY.NS", "TCS.NS", "TATAMOTORS.NS", "ICICIBANK.NS", "ITC.NS"]
            scan_rows = []
            for sym in quick_list:
                try:
                    d = yf.Ticker(sym).history(period="2d", interval="15m")
                    if len(d) >= 15:
                        cp = round(float(d['Close'].iloc[-1]), 2)
                        m5 = d['Close'].tail(5).mean()
                        m15 = d['Close'].tail(15).mean()
                        st_txt = "🟢 तेज़ी (Bullish)" if m5 > m15 else "🔴 कमजोरी (Bearish)"
                        scan_rows.append({"शेयर": sym.replace(".NS", ""), "ताज़ा भाव (₹)": cp, "संकेत": st_txt})
                except Exception:
                    pass
            if scan_rows:
                st.dataframe(pd.DataFrame(scan_rows), use_container_width=True)

with tab3:
    st.subheader("💼 आपका वर्चुअल ट्रेडिंग खाता (बिना असली पैसे के प्रैक्टिस)")
    st.metric("उपलब्ध प्रैक्टिस बैलेंस", f"₹{round(st.session_state.wallet, 2)}")
    if curr_price > 0:
        col_q, col_t, col_s = st.columns(3)
        qty = col_q.number_input("मात्रा (Shares):", min_value=1, max_value=1000, value=10)
        target_pts = col_t.number_input("Target मुनाफा (₹/शेयर):", min_value=1.0, value=5.0)
        sl_pts = col_s.number_input("Stop-Loss नुकसान (₹/शेयर):", min_value=1.0, value=3.0)
        b1, b2 = st.columns(2)
        if b1.button("🟢 खरीदें (Paper Buy)", use_container_width=True):
            cost = curr_price * qty
            if st.session_state.wallet >= cost:
                st.session_state.wallet -= cost
                st.session_state.positions[selected_share] = {
                    "qty": qty, "buy_price": curr_price, "ticker": ticker,
                    "target": curr_price + target_pts, "sl": curr_price - sl_pts
                }
                st.success(f"✅ {selected_share} के {qty} शेयर ₹{curr_price} पर खरीदे गए!")
            else:
                st.error("वर्चुअल बैलेंस कम है!")
        if selected_share in st.session_state.positions:
            pos = st.session_state.positions[selected_share]
            live_pnl = round((curr_price - pos["buy_price"]) * pos["qty"], 2)
            st.info(f"📌 चलता हुआ सौदा: {pos['qty']} शेयर @ ₹{pos['buy_price']} | लाइव मुनाफा/नुकसान: **₹{live_pnl}**")
            if curr_price >= pos["target"]:
                st.session_state.wallet += curr_price * pos["qty"]
                del st.session_state.positions[selected_share]
                st.balloons()
                st.success(f"🎉 Target पूरा! ₹{live_pnl} मुनाफे पर अपने आप बिक गया!")
            elif curr_price <= pos["sl"]:
                st.session_state.wallet += curr_price * pos["qty"]
                del st.session_state.positions[selected_share]
                st.warning(f"🛑 Stop-Loss हिट! ₹{live_pnl} नुकसान पर सौदा अपने आप कट गया।")
            if b2.button("🔴 अभी बेचें (Paper Sell)", use_container_width=True):
                st.session_state.wallet += curr_price * pos["qty"]
                del st.session_state.positions[selected_share]
                st.success(f"सौदा बंद किया गया। कुल मुनाफा/नुकसान: ₹{live_pnl}")

def text_to_speech_hindi(text):
    try:
        clean_txt = text.replace("*", "").replace("#", "").replace("`", "")[:600]
        tts = gTTS(text=clean_txt, lang='hi')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp
    except Exception:
        return None

with tab1:
    if curr_price > 0:
        st.caption(f"📡 लाइव संदर्भ: {live_context}")
    uploaded_chart = st.file_uploader("📸 किसी भी चार्ट का स्क्रीनशॉट अपलोड करें (AI चार्ट पढ़कर बताएगा):", type=["png", "jpg", "jpeg"])
    chart_img = None
    if uploaded_chart:
        chart_img = Image.open(uploaded_chart)
        st.image(chart_img, caption="अपलोड किया गया चार्ट", width=300)

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

