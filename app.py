import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import io
from google import genai

st.set_page_config(page_title="शेयर बाजार मस्तिष्क AI", page_icon="📈", layout="centered")

st.markdown("""
<div style="background-color:#1e3d59;padding:12px;border-radius:10px;text-align:center;">
    <h2 style="color:white;margin:0;">🧠 शेयर बाजार मस्तिष्क AI</h2>
    <p style="color:#d9e2ec;margin:4px 0 0 0;font-size:14px;">1000+ प्रोफेशनल ट्रेडर्स जैसा ज्ञान • Intraday & F&O विशेषज्ञ</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("🔑 AI सेटिंग्स")
    api_key = st.text_input("अपनी Gemini API Key डालें:", type="password", placeholder="यहाँ अपनी Key पेस्ट करें...")
    st.info("यह ऐप केवल शेयर बाजार, Intraday और F&O के सवालों का जवाब देता है।")

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
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if res.status_code == 200:
            df = pd.read_csv(io.StringIO(res.text))
            shares = {f"{str(r['Company Name']).strip()} ({str(r['Symbol']).strip()})": f"{str(r['Symbol']).strip()}.NS" for _, r in df.iterrows()}
            if len(shares) > 50:
                return shares
    except Exception:
        pass
    return fallback

ALL_SHARES = load_nifty_500()

st.subheader("📊 लाइव शेयर स्कैनर (Top 500)")
selected_share = st.selectbox("शेयर खोजें या चुनें (नाम टाइप करें):", sorted(list(ALL_SHARES.keys())))

live_context = ""
if selected_share:
    ticker = ALL_SHARES[selected_share]
    try:
        data = yf.Ticker(ticker).history(period="5d", interval="15m")
        if not data.empty and len(data) >= 15:
            curr_price = round(float(data['Close'].iloc[-1]), 2)
            prev_close = round(float(data['Close'].iloc[-2]), 2)
            diff = round(curr_price - prev_close, 2)
            ma_fast = round(float(data['Close'].tail(5).mean()), 2)
            ma_slow = round(float(data['Close'].tail(15).mean()), 2)
            trend = "तेज़ी (Bullish)" if ma_fast > ma_slow else "कमजोरी (Bearish)"
            
            c1, c2 = st.columns(2)
            c1.metric(label="ताज़ा भाव", value=f"₹{curr_price}", delta=f"{diff}")
            c2.metric(label="AI ट्रेंड संकेत", value=trend)
            live_context = f"वर्तमान में यूज़र ने {selected_share} चुना है। इसका ताज़ा भाव ₹{curr_price} है, 5-कैंडल औसत ₹{ma_fast} और 15-कैंडल औसत ₹{ma_slow} है, और ट्रेंड '{trend}' है।"
    except Exception:
        st.warning("ताज़ा डेटा लोड करने में थोड़ा समय लग रहा है।")

st.divider()

st.subheader("💬 AI मार्केट गुरु से पूछें (हिंदी / Hinglish)")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "नमस्ते! मैं आपका **शेयर बाजार मस्तिष्क AI** हूँ। मुझसे Intraday, F&O, चार्ट या किसी भी शेयर के बारे में पूछें—चाहे आपकी स्पेलिंग थोड़ी गलत ही क्यों न हो, मैं समझ जाऊंगा!"}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

SYSTEM_PROMPT = """
तुम 'शेयर बाजार मस्तिष्क AI' हो—भारतीय शेयर बाजार (NSE/BSE), Equity, Intraday और F&O (Futures & Options) के सर्वोच्च विशेषज्ञ।
तुम्हारे अंदर दुनिया के 1000+ प्रोफेशनल ट्रेडर्स का ज्ञान (Price Action, Option Greeks, OI Data, Risk Management, Stop-Loss, Candlestick Patterns, Psychology) समाहित है।
नियम:
1. यूज़र की टूटी-फूटी हिंदी, Hinglish या गलत स्पेलिंग (जैसे 'sbii ka bhaav', 'f&o kya h', 'intraday me loss se kaise bache') को भी पूरी तरह समझो और सरल, स्पष्ट हिंदी में जवाब दो।
2. केवल शेयर बाजार, ट्रेडिंग, निवेश और वित्त से जुड़े सवालों का ही जवाब दो। यदि कोई फिल्म, राजनीति या बाहरी सवाल पूछे, तो विनम्रता से कहो कि तुम केवल शेयर बाजार के विशेषज्ञ हो।
3. हर ट्रेडिंग सलाह के साथ छोटे Stop-Loss और Risk Management का महत्व जरूर समझाओ। कभी भी 100% गारंटीड मुनाफे का झूठा दावा मत करो।
4. जवाब देने से पहले गहराई से सोचो (Think) और पॉइंट्स में आसान उदाहरण देकर समझाओ।
"""

if prompt := st.chat_input("यहाँ अपना सवाल लिखें... (जैसे: आज Intraday में कैसे ट्रेड करें?)"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not api_key:
            reply = "⚠️ कृपया पहले बाईं तरफ (ऊपर `>` तीर दबाकर) अपनी **Gemini API Key** पेस्ट करें, तभी मेरा AI दिमाग काम करेगा!"
            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
        else:
            with st.spinner("1000+ ट्रेडर्स के ज्ञान से सोच रहा हूँ..."):
                try:
                    client = genai.Client(api_key=api_key)
                    full_prompt = f"{SYSTEM_PROMPT}\n\nलाइव मार्केट संदर्भ: {live_context}\n\nयूज़र का सवाल: {prompt}"
                    try:
                        response = client.models.generate_content(
                            model="gemini-3.8-flash",
                            contents=full_prompt,
                        )
                    except Exception:
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=full_prompt,
                        )
                    reply = response.text
                except Exception as e:
                    reply = f"❌ API Key जांचें या थोड़ी देर बाद कोशिश करें। (त्रुटि: {str(e)})"
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
