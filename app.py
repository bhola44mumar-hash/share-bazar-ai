import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import io
import base64
from PIL import Image
from gtts import gTTS
from google import genai

st.set_page_config(page_title="शेयर बाजार मस्तिष्क AI Pro", page_icon="🧠", layout="centered")
st.markdown('<div style="background:#1e3d59;padding:10px;border-radius:10px;text-align:center;"><h3 style="color:white;margin:0;">🧠 शेयर बाजार मस्तिष्क AI (Super-Fast Groq + Gemini)</h3></div>', unsafe_allow_html=True)

groq_key = ""
gemini_key = ""
try:
    groq_key = str(st.secrets.get("GROQ_API_KEY", "")).strip()
    gemini_key = str(st.secrets.get("GEMINI_API_KEY", "")).strip()
except Exception:
    pass

with st.sidebar:
    st.header("⚡ सुपर-फास्ट AI सेटिंग्स")
    if groq_key:
        st.success("✅ Groq इंजन (0.5 सेकंड स्पीड) चालू है!")
    else:
        groq_key = st.text_input("Groq API Key डालें (gsk_...):", type="password")
    if gemini_key:
        st.success("✅ Gemini बैकअप इंजन चालू है!")
    voice_on = st.checkbox("🔊 जवाब हिंदी में बोलकर सुनाएं", value=False)
    if st.button("🗑️ चैट साफ करें"):
        st.session_state.messages = []
        st.rerun()

@st.cache_data(ttl=180)
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
        r = requests.get("https://nseindia.com", headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        if r.status_code == 200:
            df = pd.read_csv(io.StringIO(r.text))
            shares = {f"{str(row['Company Name']).strip()} ({str(row['Symbol']).strip()})": f"{str(row['Symbol']).strip()}.NS" for _, row in df.iterrows()}
            if len(shares) > 50:
                return shares
    except Exception:
        pass
    return fallback

@st.cache_data(ttl=60)
def get_stock_summary(ticker, share_name):
    try:
        hist = yf.Ticker(ticker).history(period="5d", interval="15m")
        if not hist.empty and len(hist) >= 15:
            curr_price = round(float(hist['Close'].iloc[-1]), 2)
            m5 = round(float(hist['Close'].tail(5).mean()), 2)
            m15 = round(float(hist['Close'].tail(15).mean()), 2)
            trend = "तेज़ी (Bullish)" if m5 > m15 else "कमजोरी (Bearish)"
            return f"शेयर: {share_name} | ताज़ा भाव: ₹{curr_price} | ट्रेंड: {trend}"
    except Exception:
        pass
    return ""

ALL_SHARES = load_nifty_500()
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "नमस्ते! मैं आपका **सुपर-फास्ट शेयर बाजार AI** हूँ। अब कोई `503` एरर नहीं आएगा—सवाल लिखें या चार्ट अपलोड करें!"}]

selected_share = st.selectbox("🔍 शेयर चुनें (Top 500):", sorted(list(ALL_SHARES.keys())))
ticker = ALL_SHARES[selected_share]
live_context = get_stock_summary(ticker, selected_share)
if live_context:
    st.caption(f"📊 {live_context}")

uploaded_chart = st.file_uploader("📸 चार्ट की फोटो अपलोड करें (वैकल्पिक):", type=["png", "jpg", "jpeg"])
chart_pil = None
if uploaded_chart is not None:
    chart_pil = Image.open(uploaded_chart).convert("RGB")
    chart_pil.thumbnail((512, 512))
    st.image(chart_pil, caption="✅ चार्ट तैयार है — अब नीचे सवाल लिखें", width=220)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

def speak_hindi(text):
    try:
        clean = text.replace("*", "").replace("#", "")[:450]
        tts = gTTS(text=clean, lang='hi')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp
    except Exception:
        return None

def ask_groq_fast(key, prompt_text, pil_image=None):
    url = "https://groq.com"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if pil_image is not None:
        buf = io.BytesIO()
        pil_image.save(buf, format="JPEG", quality=80)
        b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")
        model = "meta-llama/llama-4-scout-17b-16e-instruct"
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
            ]
        }]
    else:
        model = "llama-3.3-70b-versatile"
        messages = [{"role": "user", "content": prompt_text}]
        
    payload = {"model": model, "messages": messages, "temperature": 0.4, "max_tokens": 1024}
    r = requests.post(url, headers=headers, json=payload, timeout=20)
    if r.status_code == 200:
        return r.json()["choices"]["message"]["content"]
    raise Exception(f"Groq {r.status_code}: {r.text}")

SYSTEM_PROMPT = "तुम 'शेयर बाजार मस्तिष्क AI' हो—भारतीय शेयर बाजार, Intraday और F&O के सर्वोच्च विशेषज्ञ। यदि चार्ट की फोटो भेजी गई है, तो पैटर्न, सपोर्ट, रेजिस्टेंस और ट्रेंड का गहरा विश्लेषण करो। सरल हिंदी में सटीक जवाब दो और Stop-Loss जरूर बताओ।"

if prompt := st.chat_input("यहाँ अपना सवाल लिखें और Enter दबाएं..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not groq_key and not gemini_key:
            reply = "⚠️ कृपया बाईं तरफ अपनी **Groq API Key** डालें!"
        else:
            with st.spinner("0.5 सेकंड में विश्लेषण कर रहा हूँ..."):
                if chart_pil is not None:
                    full_q = f"{SYSTEM_PROMPT}\n\nयूज़र ने चार्ट की फोटो भेजी है और पूछा है: {prompt}\nफोटो देखकर विस्तार से बताएं।"
                else:
                    full_q = f"{SYSTEM_PROMPT}\n\nसंदर्भ: {live_context}\n\nसवाल: {prompt}"
                
                reply = None
                err_log = ""
                
                # नंबर 1: पहले सुपर-फास्ट Groq से तुरंत जवाब लाएं (ताकि कभी 503 न आए)
                if groq_key:
                    try:
                        reply = ask_groq_fast(groq_key, full_q, chart_pil)
                    except Exception as e:
                        err_log += f"Groq: {e} | "
                
                # नंबर 2: बैकअप में Gemini
                if not reply and gemini_key:
                    try:
                        client = genai.Client(api_key=gemini_key)
                        contents = [full_q, chart_pil] if chart_pil is not None else [full_q]
                        res = client.models.generate_content(model="gemini-3.5-flash-lite", contents=contents)
                        reply = res.text
                    except Exception as e:
                        err_log += f"Gemini: {e}"
                        
                if not reply:
                    reply = f"❌ त्रुटि: {err_log}"
        
        st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        if voice_on and not reply.startswith("❌"):
            audio = speak_hindi(reply)
            if audio:
                st.audio(audio, format="audio/mp3")
