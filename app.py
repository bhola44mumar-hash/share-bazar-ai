import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import io
from gtts import gTTS
from google import genai
from google.genai import types

st.set_page_config(page_title="शेयर बाजार मस्तिष्क AI Pro", page_icon="🧠", layout="centered")

st.markdown('<div style="background: linear-gradient(90deg, #1e3d59, #2b5876);padding:10px;border-radius:10px;text-align:center;"><h3 style="color:white;margin:0;">🧠 शेयर बाजार मस्तिष्क AI (Pro)</h3></div>', unsafe_allow_html=True)

saved_key = ""
try:
    k = st.secrets["GEMINI_API_KEY"].strip()
    if k:
        saved_key = k
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
    if st.button("🗑️ पुरानी चैट साफ करें"):
        st.session_state.messages = []
        st.rerun()

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
        {"role": "assistant", "content": "नमस्ते! मैं आपका **शेयर बाजार मस्तिष्क AI (Pro)** हूँ। नीचे दिए गए बॉक्स में सवाल लिखें या **(`+`) आइकन** दबाकर चार्ट की फोटो भेजें!"}
    ]

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

with st.expander("📊 लाइव चार्ट, RSI इंडिकेटर और टॉप शेयर स्कैनर देखें"):
    if curr_price > 0:
        c1, c2, c3 = st.columns(3)
        c1.metric("ताज़ा भाव", f"₹{curr_price}", f"{diff}")
        c2.metric("AI ट्रेंड", trend)
        c3.metric("RSI (ताकत)", f"{rsi_val}", "Overbought >70 | Oversold <30")
        st.write(f"🛡️ **मजबूत Support:** ₹{support} &nbsp;|&nbsp; 🚧 **Resistance:** ₹{resistance}")
        st.line_chart(hist_data['Close'].tail(50))
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

with st.expander("💰 पेपर ट्रेडिंग प्रैक्टिस (₹1,00,000 वर्चुअल बैलेंस)"):
    st.metric("उपलब्ध प्रैक्टिस बैलेंस", f"₹{round(st.session_state.wallet, 2)}")
    if curr_price > 0:
        col_q, col_t, col_s = st.columns(3)
        qty = col_q.number_input("मात्रा:", min_value=1, max_value=1000, value=10)
        target_pts = col_t.number_input("Target (₹/शेयर):", min_value=1.0, value=5.0)
        sl_pts = col_s.number_input("Stop-Loss (₹/शेयर):", min_value=1.0, value=3.0)
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
                st.error("बैलेंस कम है!")
        if selected_share in st.session_state.positions:
            pos = st.session_state.positions[selected_share]
            live_pnl = round((curr_price - pos["buy_price"]) * pos["qty"], 2)
            st.info(f"📌 चलता हुआ सौदा: {pos['qty']} शेयर @ ₹{pos['buy_price']} | मुनाफा/नुकसान: **₹{live_pnl}**")
            if curr_price >= pos["target"]:
                st.session_state.wallet += curr_price * pos["qty"]
                del st.session_state.positions[selected_share]
                st.balloons()
                st.success(f"🎉 Target पूरा! ₹{live_pnl} मुनाफे पर बिक गया!")
            elif curr_price <= pos["sl"]:
                st.session_state.wallet += curr_price * pos["qty"]
                del st.session_state.positions[selected_share]
                st.warning(f"🛑 Stop-Loss हिट! ₹{live_pnl} नुकसान पर कट गया।")
            if b2.button("🔴 अभी बेचें (Paper Sell)", use_container_width=True):
                st.session_state.wallet += curr_price * pos["qty"]
                del st.session_state.positions[selected_share]
                st.success(f"सौदा बंद। कुल मुनाफा/नुकसान: ₹{live_pnl}")

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

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if "image" in msg and msg["image"] is not None:
            st.image(msg["image"], width=280)
        st.markdown(msg["content"])

SYSTEM_PROMPT = "तुम 'शेयर बाजार मस्तिष्क AI (Pro)' हो—भारतीय शेयर बाजार (NSE/BSE), Equity, Intraday और F&O के सर्वोच्च विशेषज्ञ। तुम्हारे अंदर दुनिया के 1000+ प्रोफेशनल ट्रेडर्स का ज्ञान है। नियम: 1. यूज़र की टूटी-फूटी हिंदी, Hinglish या गलत स्पेलिंग को भी पूरी तरह समझो और सरल हिंदी में जवाब दो। 2. यदि चार्ट की फोटो भेजी गई है, तो उसमें दिख रहे ट्रेंड, सपोर्ट, रेजिस्टेंस और पैटर्न को समझाओ। 3. केवल शेयर बाजार और वित्त से जुड़े सवालों का ही जवाब दो। 4. हर सलाह के साथ Stop-Loss और Risk Management का महत्व जरूर समझाओ।"

submission = st.chat_input(
    "यहाँ सवाल लिखें या बाईं तरफ (+) दबाकर चार्ट की फोटो भेजें...",
    accept_file=True,
    file_type=["png", "jpg", "jpeg"]
)

if not submission:
    st.stop()

user_text = submission.text.strip() if submission.text else ""
img_bytes = None
mime_type = "image/png"
for f in (submission.files or []):
    img_bytes = f.getvalue()
    mime_type = f.type or "image/png"
    break

if not user_text and img_bytes:
