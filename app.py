import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import io
from gtts import gTTS
from google import genai
from google.genai import types

st.set_page_config(page_title="शेयर बाजार मस्तिष्क AI Pro", page_icon="🧠", layout="centered")
st.markdown('<div style="background:#1e3d59;padding:12px;border-radius:10px;text-align:center;"><h3 style="color:white;margin:0;">🧠 शेयर बाजार मस्तिष्क AI (Pro)</h3></div>', unsafe_allow_html=True)

saved_key = ""
try:
    saved_key = str(st.secrets["GEMINI_API_KEY"]).strip()
except Exception:
    saved_key = ""

with st.sidebar:
    st.header("🔑 AI सेटिंग्स")
    if saved_key:
        api_key = saved_key
        st.success("✅ API Key सेव है!")
    else:
        api_key = st.text_input("अपनी Gemini API Key डालें:", type="password")
    voice_on = st.checkbox("🔊 जवाब हिंदी में बोलकर सुनाएं", value=True)
    if st.button("🗑️ चैट साफ करें"):
        st.session_state.messages = []
        st.rerun()

@st.cache_data(ttl=120)
def get_indices():
    res = {}
    for name, sym in [("Nifty 50", "^NSEI"), ("Bank Nifty", "^NSEBANK"), ("India VIX", "^INDIAVIX")]:
        try:
            d = yf.Ticker(sym).history(period="2d")
            if len(d) >= 2:
                c, p = round(float(d['Close'].iloc[-1]), 2), round(float(d['Close'].iloc[-2]), 2)
                res[name] = (c, round(c - p, 2))
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
        "Tata Motors (TATAMOTORS)": "TATAMOTORS.NS", "Bharti Airtel (BHARTIARTL)": "BHARTIARTL.NS"
    }
    try:
        r = requests.get("https://nseindia.com", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            df = pd.read_csv(io.StringIO(r.text))
            shares = {f"{str(row['Company Name']).strip()} ({str(row['Symbol']).strip()})": f"{str(row['Symbol']).strip()}.NS" for _, row in df.iterrows()}
            if len(shares) > 50:
                return shares
    except Exception:
        pass
    return fallback

ALL_SHARES = load_nifty_500()
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "नमस्ते! मैं आपका **शेयर बाजार मस्तिष्क AI** हूँ। नीचे सवाल लिखें और **Enter** दबाएं!"}]

selected_share = st.selectbox("🔍 शेयर चुनें (Top 500):", sorted(list(ALL_SHARES.keys())))
ticker = ALL_SHARES[selected_share]

curr_price = 0.0
live_context = ""
try:
    hist = yf.Ticker(ticker).history(period="5d", interval="15m")
    if not hist.empty and len(hist) >= 15:
        curr_price = round(float(hist['Close'].iloc[-1]), 2)
        m5 = round(float(hist['Close'].tail(5).mean()), 2)
        m15 = round(float(hist['Close'].tail(15).mean()), 2)
        trend = "तेज़ी (Bullish)" if m5 > m15 else "कमजोरी (Bearish)"
        live_context = f"शेयर: {selected_share} | ताज़ा भाव: ₹{curr_price} | ट्रेंड: {trend}"
        st.caption(f"📊 {live_context}")
except Exception:
    pass

uploaded_chart = st.file_uploader("📸 चार्ट की फोटो अपलोड करें (वैकल्पिक):", type=["png", "jpg", "jpeg"])

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

def speak_hindi(text):
    try:
        clean = text.replace("*", "").replace("#", "")[:500]
        tts = gTTS(text=clean, lang='hi')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp
    except Exception:
        return None

SYSTEM_PROMPT = "तुम 'शेयर बाजार मस्तिष्क AI' हो—भारतीय शेयर बाजार, Intraday और F&O के विशेषज्ञ। यूज़र की टूटी-फूटी हिंदी या Hinglish को समझकर सरल हिंदी में जवाब दो और Stop-Loss का महत्व जरूर बताओ।"

if prompt := st.chat_input("यहाँ अपना सवाल लिखें और Enter दबाएं..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not api_key:
            reply = "⚠️ कृपया पहले बाईं तरफ अपनी **Gemini API Key** डालें!"
        else:
            with st.spinner("1000+ ट्रेडर्स के ज्ञान से सोच रहा हूँ..."):
                client = genai.Client(api_key=api_key)
                full_q = f"{SYSTEM_PROMPT}\n\nसंदर्भ: {live_context}\n\nसवाल: {prompt}"
                contents = [full_q]
                if uploaded_chart is not None:
                    contents.append(types.Part.from_bytes(data=uploaded_chart.getvalue(), mime_type=uploaded_chart.type or "image/png"))
                
                reply = None
                err_msg = ""
                for m in ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-3.5-flash-lite"]:
                    try:
                        res = client.models.generate_content(model=m, contents=contents)
                        reply = res.text
                        break
                    except Exception as e:
                        err_msg = str(e)
                if not reply:
                    reply = f"❌ त्रुटि: {err_msg}"
        
        st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        if voice_on and not reply.startswith("❌"):
            audio = speak_hindi(reply)
            if audio:
                st.audio(audio, format="audio/mp3")
