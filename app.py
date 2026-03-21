# app.py
import streamlit as st
from bias_detector import detect_bias
from counter_evidence import CounterEvidenceEngine
from intervention import generate_intervention
from ticker_extractor import extract_ticker_and_intent
from datetime import datetime
from llm import (
    generate_intervention_text,
    summarize_stock_condition,
    classify_bias_from_input,
    generate_bias_summary,
    analyze_fundamental,
    _call_gemini,
)
from price_fetcher import get_current_price, get_ticker_info as _pf_get_info
import re
import html
import time

# ── Security Helpers ────────────────────────────────────────────────────────

def sanitize(text: str) -> str:
    """Escape HTML special chars untuk mencegah XSS via unsafe_allow_html."""
    if not isinstance(text, str):
        return ""
    return html.escape(str(text))


def validate_ticker_format(ticker: str) -> bool:
    """Whitelist format ticker IDX: 2-5 huruf kapital, opsional .JK."""
    return bool(re.match(r'^[A-Za-z]{2,5}(\.JK)?$', ticker.strip()))


# ── Caching price data (curl_cffi via price_fetcher) ─────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def _cached_download(ticker: str, period: str = "3mo") -> object:
    """Tidak dipakai langsung — gunakan _cached_fast_info atau _cached_ticker_info."""
    return None


@st.cache_data(ttl=300, show_spinner=False)
def _cached_ticker_info(ticker: str) -> dict:
    """Cache fundamental info 5 menit via price_fetcher (curl_cffi)."""
    return _pf_get_info(ticker)


@st.cache_data(ttl=60, show_spinner=False)
def _cached_fast_info(ticker: str) -> dict:
    """Cache harga terkini 1 menit via price_fetcher (curl_cffi)."""
    result = get_current_price(ticker)
    return {
        "last_price": result.get("current_price"),
        "change_pct": result.get("change_pct"),
    }

st.set_page_config(
    page_title="CogniFi · Behavioral Finance AI",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #09090f; }
[data-testid="stSidebar"] {
    background: #0d0d18 !important;
    border-right: 1px solid #1a1a2e !important;
}
[data-testid="stSidebarNav"] { display: none; }
#MainMenu, footer, header { visibility: hidden; }
h1 { font-size:1.55rem !important; font-weight:600 !important; letter-spacing:-0.02em; color:#ededf5 !important; }
p, li { color:#a0a0c0 !important; }

/* ── Override semua outline pink/merah Streamlit ── */
*, *:focus, *:focus-visible, *:focus-within {
    outline: none !important;
    box-shadow: none !important;
}

.stTextArea textarea {
    background:#111120 !important; border:1px solid #22223a !important;
    border-radius:10px !important; color:#ddddf0 !important; font-size:0.93rem !important; padding:14px !important;
    transition: border-color 0.15s ease !important;
}
.stTextArea textarea:focus {
    border-color:#4f46e5 !important;
    box-shadow:0 0 0 2px rgba(79,70,229,0.15) !important;
    outline: none !important;
}
.stTextArea [data-baseweb="textarea"] {
    border-color:#22223a !important;
    box-shadow: none !important;
}
.stTextArea [data-baseweb="textarea"]:focus-within {
    border-color:#4f46e5 !important;
    box-shadow:0 0 0 2px rgba(79,70,229,0.15) !important;
}
.stTextInput input {
    background:#111120 !important; border:1px solid #22223a !important;
    border-radius:8px !important; color:#ddddf0 !important;
}
.stTextInput input:focus {
    border-color:#4f46e5 !important;
    box-shadow:0 0 0 2px rgba(79,70,229,0.15) !important;
    outline: none !important;
}
.stTextInput [data-baseweb="input"] {
    border-color:#22223a !important;
    box-shadow: none !important;
}
.stTextInput [data-baseweb="input"]:focus-within {
    border-color:#4f46e5 !important;
    box-shadow:0 0 0 2px rgba(79,70,229,0.15) !important;
}

/* Baseweb global override — ini yang generate pink */
[data-baseweb] { outline: none !important; }
[data-baseweb]:focus { outline: none !important; box-shadow: none !important; }
[data-baseweb="base-input"] { box-shadow: none !important; }
[data-baseweb="base-input"]:focus-within {
    border-color: #4f46e5 !important;
    box-shadow: 0 0 0 2px rgba(79,70,229,0.15) !important;
}

.stButton > button[kind="primary"] {
    background:#4f46e5 !important; border:none !important; border-radius:8px !important;
    color:white !important; font-weight:500 !important; font-size:0.9rem !important; padding:0.6rem 1.2rem !important;
}
.stButton > button[kind="primary"]:hover { background:#4338ca !important; }
.stButton > button[kind="primary"]:disabled { background:#1e1e38 !important; color:#6060a0 !important; }
.stButton > button[kind="secondary"] { background:transparent !important; border:1px solid #22223a !important; border-radius:8px !important; color:#9090b8 !important; font-size:0.82rem !important; }
[data-testid="stMetric"] { background:#111120; border:1px solid #1a1a2e; border-radius:10px; padding:14px 18px; }
[data-testid="stMetricValue"] { color:#ddddf0 !important; font-size:1.35rem !important; }
[data-testid="stMetricLabel"] { color:#505070 !important; font-size:0.72rem !important; }
.stExpander { border:1px solid #1a1a2e !important; border-radius:10px !important; background:#111120 !important; }
hr { border-color:#1a1a2e !important; }
.stProgress > div > div { background:#4f46e5 !important; border-radius:3px !important; }
.stProgress { background:#1a1a2e !important; border-radius:3px !important; }
.stCheckbox label { color:#a0a0c0 !important; font-size:0.86rem !important; }
.stCaption { color:#6060a0 !important; }
.stAlert { border-radius:10px !important; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ─────────────────────────────────────────────

def render_action_badge(action: str, alasan: str, lang: str):
    cfg = {
        "AVOID":  {"bg":"#140808","border":"#6b1a1a","tc":"#fca5a5","bb":"#6b1a1a","bt":"#fef2f2","lid":"AVOID — Hindari Eksekusi","len":"AVOID — Do Not Execute"},
        "REDUCE": {"bg":"#140e04","border":"#6b4a08","tc":"#fcd34d","bb":"#6b4a08","bt":"#fffbeb","lid":"REDUCE — Pertimbangkan Ulang","len":"REDUCE — Reconsider"},
        "HOLD":   {"bg":"#04080f","border":"#0f2a4a","tc":"#93c5fd","bb":"#0f2a4a","bt":"#eff6ff","lid":"HOLD — Tunggu Konfirmasi","len":"HOLD — Wait for Confirmation"},
    }
    c = cfg.get(action, cfg["HOLD"])
    label = c["lid"] if lang == "ID" else c["len"]
    st.markdown(f"""
<div style="background:{c['bg']};border:1px solid {c['border']};border-radius:12px;padding:18px 22px;margin:16px 0 8px;">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
    <span style="background:{c['bb']};color:{c['bt']};font-size:0.72rem;font-weight:700;letter-spacing:0.1em;padding:3px 10px;border-radius:20px;">{action}</span>
    <span style="color:{c['tc']};font-weight:500;font-size:0.92rem;">{label}</span>
  </div>
  <p style="color:{c['tc']};opacity:0.75;font-size:0.82rem;margin:0;line-height:1.55;">{alasan}</p>
</div>""", unsafe_allow_html=True)


def render_confidence_breakdown(kontributor: list, confidence: float, lang: str):
    title = f"Mengapa confidence <strong style='color:#a0a0c8;'>{confidence:.0%}</strong>?" if lang == "ID" else f"Why confidence <strong style='color:#a0a0c8;'>{confidence:.0%}</strong>?"
    html = f"""
<div style="background:#0d0d18;border:1px solid #1a1a2e;border-radius:12px;padding:18px 22px;margin:8px 0;">
  <div style="color:#8080a8;font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:14px;">{title}</div>"""
    icons = ["01.","02.","03."]
    for i, k in enumerate(kontributor[:3]):
        html += f'<div style="display:flex;gap:12px;margin-bottom:9px;align-items:flex-start;"><span style="color:#4f46e5;font-size:0.88rem;min-width:18px;">{icons[i]}</span><span style="color:#a0a0c8;font-size:0.83rem;line-height:1.55;">{k}</span></div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_fundamental_panel(labeled: dict, overall: str, lang: str):
    oc = {"OK":("#4ade80","#031a0a","#0d4a1e"),"CAUTION":("#fbbf24","#140e02","#4a3008"),"WARN":("#f87171","#140404","#4a1010")}.get(overall,("#6060a0","#0d0d18","#1a1a2e"))
    ol = {"OK":"Fundamental OK","CAUTION":"Perhatikan Fundamental" if lang=="ID" else "Monitor Fundamentals","WARN":"Fundamental Bermasalah" if lang=="ID" else "Fundamental Issues"}.get(overall,"")
    lmap = {"ok":("OK","#4ade80","#031a0a"),"caution":("CAUTION","#fbbf24","#140e02"),"warn":("WARN","#f87171","#140404"),"neutral":("—","#50507080","#0d0d18")}
    rows = ""
    for metric,(val,status) in labeled.items():
        lbl,lc,lb = lmap.get(status,lmap["neutral"])
        rows += f'<div style="background:#0d0d18;border:1px solid #1a1a2e;border-radius:8px;padding:9px 13px;display:flex;justify-content:space-between;align-items:center;"><span style="color:#8080a8;font-size:0.78rem;">{metric}</span><div style="display:flex;align-items:center;gap:8px;"><span style="color:#c0c0d8;font-size:0.83rem;font-weight:500;">{val}</span><span style="background:{lb};color:{lc};font-size:0.62rem;font-weight:700;padding:2px 6px;border-radius:4px;">{lbl}</span></div></div>'
    st.markdown(f"""
<div style="background:{oc[1]};border:1px solid {oc[2]};border-radius:12px;padding:16px 20px;margin:8px 0;">
  <div style="color:{oc[0]};font-size:0.72rem;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:12px;">◈ {ol}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">{rows}</div>
</div>""", unsafe_allow_html=True)


def label_section(text: str):
    st.markdown(f"<div style='color:#7070a0;font-size:0.72rem;letter-spacing:0.07em;text-transform:uppercase;margin:20px 0 6px;'>{text}</div>", unsafe_allow_html=True)


# ── Language Pack ──────────────────────────────────────
TEXT = {
    "ID": {
        "subtitle":    "Deteksi bias kognitif sebelum keputusan investasi.",
        "input_label": "Apa yang sedang kamu pertimbangkan?",
        "btn_analyze": "Analisis",
        "btn_broker":  "Lanjutkan ke broker →",
        "checkbox":    "Saya telah membaca analisis di atas dan memahami risikonya.",
        "confirmed":   "Keputusan ada di tanganmu.",
        "no_bias":     "Tidak ada pola bias signifikan yang terdeteksi.",
        "signals":     "Sinyal Terdeteksi",
        "history":     "Riwayat Sesi",
        "before_exec": "Sebelum Eksekusi",
        "data_hist":   "Data Historis",
        "fundamental": "Analisis Fundamental",
        "confidence_breakdown": "Bedah Confidence Score",
        "viz_episode": "Visualisasi Episode FOMO",
        "viz_trend":   "Tren & Moving Average",
        "footer":      "CogniFi · Behavioral Finance AI · v1.1 · Bukan rekomendasi investasi · Data pasar: Yahoo Finance · Riset: Kahneman (2011), Odean (1998), Thaler (2015)",
    },
    "EN": {
        "subtitle":    "Detect cognitive bias before your investment decision.",
        "input_label": "What are you considering?",
        "btn_analyze": "Analyze",
        "btn_broker":  "Continue to broker →",
        "checkbox":    "I have read the analysis above and understand the risks.",
        "confirmed":   "The decision is yours.",
        "no_bias":     "No significant bias pattern detected.",
        "signals":     "Detected Signals",
        "history":     "Session History",
        "before_exec": "Before Execution",
        "data_hist":   "Historical Data",
        "fundamental": "Fundamental Analysis",
        "confidence_breakdown": "Confidence Score Breakdown",
        "viz_episode": "FOMO Episode Visualization",
        "viz_trend":   "Trend & Moving Average",
        "footer":      "CogniFi · Behavioral Finance AI · v1.1 · Not investment advice · Market data: Yahoo Finance · Research: Kahneman (2011), Odean (1998), Thaler (2015)",
    }
}

# ── Session State ──────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "sidebar_state" not in st.session_state:
    st.session_state.sidebar_state = "expanded"
if "last_analysis_time" not in st.session_state:
    st.session_state.last_analysis_time = 0.0  # S-03: rate limiting timestamp

# ── Utils ──────────────────────────────────────────────

def validate_ticker(t: str) -> tuple[str, bool]:
    t = t.strip().upper()
    if not t.endswith(".JK"):
        t += ".JK"
    # S-04: Validasi format ticker sebelum network call
    base = t.replace(".JK", "")
    if not re.match(r'^[A-Z]{2,5}$', base):
        return t, False
    try:
        d = _cached_download(t, period="5d")  # P-01: pakai cache
        return t, len(d) > 0
    except Exception:
        return t, False

def get_fundamental(ticker: str) -> dict:
    try:
        info = _cached_ticker_info(ticker)
        def safe(k, fmt=None):
            v = info.get(k)
            if v is None: return "N/A"
            if fmt == "pct": return f"{v:.1%}"
            if fmt == "2f":  return f"{v:.2f}"
            return v
        # yahooquery key mapping (berbeda dari yfinance)
        return {
            "P/E Ratio":      safe("trailingPE", "2f"),
            "Debt/Equity":    safe("debtToEquity", "2f"),
            "Revenue Growth": safe("revenueGrowth", "pct"),
            "Profit Margin":  safe("profitMargins", "pct"),
            "52W High":       safe("fiftyTwoWeekHigh"),
            "52W Low":        safe("fiftyTwoWeekLow"),
        }
    except Exception:
        return {}

# ── Analysis Parameters (hardcoded smart defaults) ──────
# Tidak ada slider — parameter ini sudah dioptimalkan
# berdasarkan observasi data IDX (verify_data.py):
#   threshold  : 20% — sweet spot antara terlalu sensitif dan terlalu ketat
#   window     : 5 hari — cukup untuk deteksi momentum jangka pendek
#   forward_days: 30 hari — horizon yang relevan untuk retail investor
threshold    = 0.20
window       = 5
forward_days = 30

# ── Sidebar ────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div style='color:#4f46e5;font-size:1.05rem;font-weight:600;letter-spacing:-0.01em;padding:10px 0 2px;'>◈ CogniFi</div>"
        "<div style='color:#7070a0;font-size:0.72rem;margin-bottom:18px;'>Behavioral Finance AI</div>",
        unsafe_allow_html=True
    )
    lang = st.radio("Language", options=["ID","EN"], horizontal=True, label_visibility="collapsed")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    ticker_input = st.text_input(
        "Override Saham" if lang=="ID" else "Override Stock",
        placeholder="GOTO, BBRI, BUMI...",
        help="Opsional — isi jika saham tidak terdeteksi otomatis dari teks kamu." if lang=="ID" else "Optional — fill only if stock not auto-detected from your input."
    )
    st.markdown(
        "<div style='color:#6060a0;font-size:0.7rem;line-height:1.7;margin-top:20px;'>"
        "Anthropic Economic Index (2026)<br>"
        "Financial analysts: 57.2% AI exposure<br>"
        "Behavioral layer: 0% coverage"
        "</div>", unsafe_allow_html=True
    )


# ── Header ─────────────────────────────────────────────
st.markdown(
    "<div style='padding:28px 0 4px;'>"
    "<div style='color:#4f46e5;font-size:0.7rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:10px;'>◈ COGNI FI</div>"
    "<h1 style='margin:0 0 6px;'>Behavioral Finance AI</h1>"
    "</div>", unsafe_allow_html=True
)
st.markdown(f"<p style='color:#7070a0;font-size:0.88rem;margin-bottom:22px;'>{TEXT[lang]['subtitle']}</p>", unsafe_allow_html=True)

# ── Input ──────────────────────────────────────────────
st.markdown(f"<div style='color:#FFFFFF;font-size:0.8rem;margin-bottom:6px;'>{TEXT[lang]['input_label']}</div>", unsafe_allow_html=True)

placeholder_id = "Mau beli GOTO, kayaknya mau naik nih, semua orang pada masuk...\nUNVR nyangkut, nunggu balik modal dulu...\nBBRI bagus kan? prospek bagus banget..."
placeholder_en = "Thinking of buying GOTO, looks like it's about to pump...\nUNVR is stuck, waiting to break even...\nBBRI looks solid right? great prospects..."

user_input = st.text_area(
    label="input", height=108, label_visibility="collapsed",
    placeholder=placeholder_id if lang=="ID" else placeholder_en
)

analyze = st.button(TEXT[lang]["btn_analyze"], type="primary", width='stretch', disabled=not user_input.strip())

# ── Processing ─────────────────────────────────────────
if analyze and user_input.strip():

    # S-03: Rate limiting — min 5 detik antar analisis
    _now = time.time()
    _elapsed = _now - st.session_state.last_analysis_time
    _COOLDOWN = 5.0
    if _elapsed < _COOLDOWN:
        _wait = int(_COOLDOWN - _elapsed) + 1
        st.warning(
            f"Tunggu {_wait} detik sebelum analisis berikutnya." if lang == "ID"
            else f"Please wait {_wait} seconds before the next analysis."
        )
        st.stop()
    st.session_state.last_analysis_time = _now

    st.session_state.last_result = None
    ticker, ticker_valid = None, False
    intent = "INTERVENTION"

    # ── STEP 1: Auto Ticker Extraction + Intent ────────────
    # Sidebar override → selalu intervention mode
    # Auto NER → Layer 1 alias dict, Layer 2 Gemini fallback
    if ticker_input.strip():
        with st.spinner("Validating..." if lang=="EN" else "Memvalidasi..."):
            ticker, ticker_valid = validate_ticker(ticker_input)
        if not ticker_valid:
            st.error(f"Ticker **{sanitize(ticker)}** tidak ditemukan.")
            st.stop()
        intent = "INTERVENTION"
    else:
        with st.spinner("Mendeteksi saham..." if lang=="ID" else "Detecting stock..."):
            ner_result = extract_ticker_and_intent(user_input)
            ticker     = ner_result["ticker"]
            intent     = ner_result["intent"]
            ner_source = ner_result["source"]

        if ticker:
            ticker_valid = True
            if ner_source == "layer2":
                st.caption(
                    f"↳ Terdeteksi otomatis: **{ticker}**" if lang=="ID"
                    else f"↳ Auto-detected: **{ticker}**"
                )
        elif intent != "EDUCATIONAL":
            st.warning(
                "Kode saham tidak terdeteksi. Masukkan di sidebar." if lang=="ID"
                else "Stock code not detected. Enter it in the sidebar."
            )
            st.stop()

    # ── STEP 2: Intent Router ──────────────────────────────
    # Jalur C — Educational: pertanyaan konsep tanpa ticker
    if intent == "EDUCATIONAL":
        with st.spinner("Menyiapkan jawaban..." if lang=="ID" else "Preparing answer..."):
            try:
                edu_prompt = f"""
Kamu adalah CogniFi, asisten behavioral finance untuk investor retail Indonesia.
User bertanya hal edukatif atau konseptual. Jawab dengan:
- Bahasa yang natural, tidak kaku
- 2-3 paragraf padat, tanpa bullet berlebihan
- Gunakan contoh konteks Indonesia jika relevan
- Akhiri dengan 1 insight dari Kahneman atau Thaler yang relevan
- Jangan rekomendasikan beli/jual saham spesifik

Bahasa output: {"Indonesia" if lang == "ID" else "English"}
Pertanyaan: "{user_input}"
"""
                edu_answer = _call_gemini(edu_prompt) or "Maaf, tidak dapat memproses pertanyaan saat ini."
            except Exception as e:
                edu_answer = f"Maaf, tidak dapat memproses pertanyaan saat ini. ({e})"

        st.session_state.history.append({
            "ticker": ticker or "—", "input": user_input,
            "bias": "NONE", "confidence": 0,
            "narasi": "", "intent": "EDUCATIONAL",
        })
        st.session_state.last_result = {
            "intent": "EDUCATIONAL",
            "ticker": ticker, "user_input": user_input,
            "edu_answer": edu_answer,
            "bias": None,
            "bias_result": {"bias_detected": None, "confidence": 0, "signals": []},
            "evidence": {}, "intervention": {"bias_detected": None, "pre_mortem": None},
            "llm_result": {}, "stock_summary": "",
            "fundamental_raw": {}, "fundamental_analysis": {},
        }

    # Jalur B — Data Query: pertanyaan data dengan ticker, tanpa emosi
    elif intent == "DATA_QUERY" and ticker:
        with st.spinner("Mengambil data..." if lang=="ID" else "Fetching data..."):
            fundamental_raw      = get_fundamental(ticker)
            fundamental_analysis = analyze_fundamental(ticker, fundamental_raw, lang)
            try:
                _fi = _cached_fast_info(ticker)
                current_price = _fi.get("last_price")
                change_pct    = _fi.get("change_pct")
            except Exception:
                current_price, change_pct = None, None

        st.session_state.history.append({
            "ticker": ticker, "input": user_input,
            "bias": "NONE", "confidence": 0,
            "narasi": "", "intent": "DATA_QUERY",
        })
        st.session_state.last_result = {
            "intent": "DATA_QUERY",
            "ticker": ticker, "user_input": user_input,
            "current_price": current_price, "change_pct": change_pct,
            "bias": None,
            "bias_result": {"bias_detected": None, "confidence": 0, "signals": []},
            "evidence": {}, "intervention": {"bias_detected": None, "pre_mortem": None},
            "llm_result": {}, "stock_summary": "",
            "fundamental_raw": fundamental_raw,
            "fundamental_analysis": fundamental_analysis,
        }

    # Jalur A — Full Intervention Pipeline
    else:
        with st.spinner("Analyzing bias..." if lang=="EN" else "Menganalisis bias..."):
            llm_classify   = classify_bias_from_input(user_input, ticker)
            bias_result_kw = detect_bias(user_input, ticker)

            if llm_classify.get("bias") and llm_classify["bias"] not in ("NONE", None):
                bias_result = {
                    "bias_detected": llm_classify["bias"],
                    "confidence":    max(llm_classify["confidence"], bias_result_kw.get("confidence", 0)),
                    "signals":       bias_result_kw.get("signals", []),
                    "price_data":    bias_result_kw.get("price_data", {}),
                }
            elif bias_result_kw.get("bias_detected"):
                bias_result = bias_result_kw
            else:
                bias_result = bias_result_kw

        with st.spinner("Historical data..." if lang=="EN" else "Data historis..."):
            engine   = CounterEvidenceEngine(ticker)
            evidence = engine.get_counter_evidence(
                bias_result.get("bias_detected") or "FOMO",
                threshold=threshold, window=window, forward_days=forward_days
            )

        with st.spinner("Fundamental data..."):
            fundamental_raw      = get_fundamental(ticker)
            fundamental_analysis = analyze_fundamental(ticker, fundamental_raw, lang)

        stock_summary = ""
        price_data    = bias_result.get("price_data", {})
        if price_data and "error" not in price_data:
            with st.spinner("Stock summary..."):
                stock_summary = summarize_stock_condition(ticker, price_data)

        llm_result = {}
        bias       = bias_result.get("bias_detected")
        if bias:
            with st.spinner("AI analysis..."):
                llm_result = generate_intervention_text(
                    bias_type=bias, ticker=ticker,
                    confidence=bias_result["confidence"],
                    signals=bias_result.get("signals", []),
                    evidence=evidence, user_input=user_input,
                    fundamental=fundamental_raw, lang=lang,
                )

        intervention = generate_intervention(bias_result, evidence)

        st.session_state.history.append({
            "ticker": ticker, "input": user_input,
            "bias":       bias_result.get("bias_detected") or "NONE",
            "confidence": bias_result.get("confidence", 0),
            "narasi":     llm_result.get("narasi", "") if llm_result else "",
        })

        st.session_state.last_result = {
            "intent": "INTERVENTION",
            "ticker": ticker, "user_input": user_input, "bias": bias,
            "bias_result": bias_result, "evidence": evidence,
            "intervention": intervention, "llm_result": llm_result,
            "stock_summary": stock_summary,
            "fundamental_raw": fundamental_raw,
            "fundamental_analysis": fundamental_analysis,
            "secondary_bias": bias_result.get("secondary_bias"),
            "secondary_conf": bias_result.get("secondary_conf", 0.0),
            "news_context":   bias_result.get("news_context", {}),
        }


# ── Display ─────────────────────────────────────────────
if st.session_state.last_result:
    r      = st.session_state.last_result
    intent = r.get("intent", "INTERVENTION")

    # ── JALUR C: Educational Display ──────────────────────
    if intent == "EDUCATIONAL":
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        st.markdown(
            "<div style='color:#7070a0;font-size:0.72rem;letter-spacing:0.07em;"
            "text-transform:uppercase;margin-bottom:8px;'>◈ JAWABAN</div>",
            unsafe_allow_html=True
        )
        st.markdown(f"""
<div style="background:#0d0d18;border:1px solid #1a1a2e;border-radius:12px;
padding:20px 24px;margin:4px 0 16px;">
  <p style="color:#c0c0d8;font-size:0.88rem;line-height:1.75;margin:0;">
    {sanitize(r['edu_answer']).replace(chr(10), '<br>')}
  </p>
</div>""", unsafe_allow_html=True)

    # ── JALUR B: Data Query Display ────────────────────────
    elif intent == "DATA_QUERY":
        ticker               = r["ticker"]
        fundamental_raw      = r["fundamental_raw"]
        fundamental_analysis = r["fundamental_analysis"]

        st.markdown(f"<div style='color:#6060a0;font-size:0.72rem;margin-top:24px;'>↳ {sanitize(ticker)} · {datetime.now().strftime('%d %b %Y, %H:%M')}</div>", unsafe_allow_html=True)

        # Price card
        cp  = r.get("current_price")
        chg = r.get("change_pct")
        if cp:
            chg_color = "#4ade80" if (chg or 0) >= 0 else "#f87171"
            chg_str   = f"{chg:+.2f}%" if chg is not None else ""
            st.markdown(f"""
<div style="background:#0d0d18;border:1px solid #1a1a2e;border-radius:10px;
padding:16px 20px;margin:8px 0;">
  <div style="color:#8080a8;font-size:0.72rem;letter-spacing:0.06em;
  text-transform:uppercase;margin-bottom:6px;">Harga Saat Ini</div>
  <div style="display:flex;align-items:baseline;gap:12px;">
    <span style="color:#ddddf0;font-size:1.5rem;font-weight:600;">
      Rp {cp:,.0f}
    </span>
    <span style="color:{chg_color};font-size:0.88rem;">{chg_str}</span>
  </div>
</div>""", unsafe_allow_html=True)

        if fundamental_analysis.get("labeled"):
            label_section(TEXT[lang]["fundamental"])
            render_fundamental_panel(
                fundamental_analysis["labeled"],
                fundamental_analysis["overall"], lang
            )

    # ── JALUR A: Full Intervention Display ────────────────
    else:
        ticker               = r["ticker"]
        user_input           = r["user_input"]
        bias                 = r["bias"]
        bias_result          = r["bias_result"]
        evidence             = r["evidence"]
        intervention         = r["intervention"]
        llm_result           = r["llm_result"]
        stock_summary        = r["stock_summary"]
        fundamental_raw      = r["fundamental_raw"]
        fundamental_analysis = r["fundamental_analysis"]
        secondary_bias       = r.get("secondary_bias")
        secondary_conf       = r.get("secondary_conf", 0.0)
        news_context         = r.get("news_context", {})

        st.markdown(f"<div style='color:#6060a0;font-size:0.72rem;margin-top:24px;'>↳ {sanitize(ticker)} · {datetime.now().strftime('%d %b %Y, %H:%M')}</div>", unsafe_allow_html=True)

        # Action badge
        action        = llm_result.get("action", "HOLD") if llm_result else "HOLD"
        action_alasan = llm_result.get("action_alasan", "") if llm_result else ""
        if bias:
            render_action_badge(action, sanitize(action_alasan), lang)

        # Bias card
        if bias:
            bstyle = {
                "FOMO":              ("#6b1a1a","#fca5a5","FOMO"),
                "LOSS_AVERSION":     ("#6b4a08","#fcd34d","LOSS"),
                "CONFIRMATION_BIAS": ("#0f2a4a","#93c5fd","BIAS"),
            }
            bc, tc, icon = bstyle.get(bias, ("#1a1a2e","#8080a0","—"))
            pct = int(bias_result['confidence']*100)
            _stock_summary_safe = sanitize(stock_summary) if stock_summary else ""
            st.markdown(f"""
<div style="background:#0d0d18;border:1px solid {bc};border-radius:10px;padding:16px 20px;margin:8px 0 4px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
    <span style="color:{tc};font-weight:600;font-size:0.88rem;">{icon} {sanitize(intervention['label'])}</span>
    <span style="color:{tc};font-size:0.82rem;opacity:0.8;">Confidence {bias_result['confidence']:.0%}</span>
  </div>
  <div style="background:#0a0a14;border-radius:4px;height:3px;margin-bottom:12px;">
    <div style="background:{tc};height:3px;border-radius:4px;width:{pct}%;opacity:0.65;"></div>
  </div>
  {"<p style='color:#9090b8;font-size:0.82rem;margin:0;line-height:1.6;'>" + _stock_summary_safe + "</p>" if _stock_summary_safe else ""}
</div>""", unsafe_allow_html=True)

            signals = bias_result.get("signals", [])
            if signals:
                label_section(TEXT[lang]["signals"])
                for s in signals:
                    st.markdown(f"<div style='color:#9090b8;font-size:0.82rem;padding:3px 0;'>· {s}</div>", unsafe_allow_html=True)

            # ── Secondary bias badge ──────────────────────────────
            if secondary_bias and secondary_bias != "NONE":
                sec_labels = {
                    "FOMO":              "FOMO",
                    "LOSS_AVERSION":     "Loss Aversion",
                    "CONFIRMATION_BIAS": "Confirmation Bias",
                }
                sec_label = sec_labels.get(secondary_bias, secondary_bias)
                sec_note = (
                    f"Juga terdeteksi pola <strong>{sec_label}</strong> "
                    f"(conf {secondary_conf:.0%}) — bias sekunder, bukan dominan."
                    if lang == "ID" else
                    f"Secondary pattern detected: <strong>{sec_label}</strong> "
                    f"(conf {secondary_conf:.0%}) — not dominant."
                )
                st.markdown(f"""
<div style="background:#0a0a14;border:1px solid #22223a;border-radius:8px;
padding:10px 16px;margin:6px 0 2px;display:flex;align-items:center;gap:10px;">
  <span style="color:#6060a0;font-size:0.68rem;font-weight:700;
  letter-spacing:0.08em;text-transform:uppercase;min-width:60px;">
  {'Sekunder' if lang=='ID' else 'Secondary'}</span>
  <span style="color:#8080b0;font-size:0.80rem;line-height:1.5;">{sec_note}</span>
</div>""", unsafe_allow_html=True)

            # ── News context headline ─────────────────────────────
            news_status  = news_context.get("status")
            news_summary = news_context.get("summary", "")
            news_articles = news_context.get("articles", [])
            if news_status == "ok" and news_articles:
                news_sentiment = news_context.get("sentiment", "neutral")
                sent_color = {
                    "positive": "#4ade80", "negative": "#f87171",
                    "mixed":    "#fbbf24", "neutral":  "#6060a0",
                }.get(news_sentiment, "#6060a0")
                sent_icon = {
                    "positive": "↑", "negative": "↓", "mixed": "↕", "neutral": "—",
                }.get(news_sentiment, "—")
                news_label = "Berita Terbaru" if lang == "ID" else "Latest News"
                label_section(news_label)
                st.markdown(f"""
<div style="background:#0d0d18;border:1px solid #1a1a2e;border-radius:10px;
padding:14px 18px;margin:4px 0;">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
    <span style="color:{sent_color};font-size:0.75rem;font-weight:700;">{sent_icon} {sanitize(news_sentiment.upper())}</span>
    <span style="color:#505070;font-size:0.70rem;">{len(news_articles)} artikel · {sanitize(ticker)}</span>
  </div>""", unsafe_allow_html=True)
                for art in news_articles[:3]:
                    art_color = {
                        "positive": "#4ade80", "negative": "#f87171", "neutral": "#606080",
                    }.get(art.get("sentiment", "neutral"), "#606080")
                    st.markdown(f"""
  <div style="display:flex;gap:10px;align-items:flex-start;margin-bottom:7px;">
    <span style="color:{art_color};font-size:0.68rem;min-width:14px;margin-top:2px;">●</span>
    <span style="color:#9090b8;font-size:0.79rem;line-height:1.5;">{sanitize(art['title'][:80])}</span>
  </div>""", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.success(TEXT[lang]["no_bias"])

        # Confidence breakdown
        kontributor = llm_result.get("kontributor", []) if llm_result else []
        if kontributor and bias:
            label_section(TEXT[lang]["confidence_breakdown"])
            render_confidence_breakdown(kontributor, bias_result["confidence"], lang)

        # Fundamental
        if fundamental_analysis.get("labeled"):
            label_section(TEXT[lang]["fundamental"])
            render_fundamental_panel(fundamental_analysis["labeled"], fundamental_analysis["overall"], lang)

        # Counter evidence
        if bias and evidence.get("status") == "ok":
            label_section(TEXT[lang]["data_hist"])
            if bias == "FOMO":
                c1,c2,c3 = st.columns(3)
                c1.metric("Episode Serupa" if lang=="ID" else "Similar Episodes", evidence['episodes_found'])
                c2.metric("Prob. Koreksi" if lang=="ID" else "Correction Prob.", f"{evidence['correction_probability']:.0%}")
                c3.metric("Avg Koreksi" if lang=="ID" else "Avg Correction", f"{evidence['avg_correction']:.1%}")
                narasi = llm_result.get("narasi") or intervention["evidence_text"]
                if narasi:
                    st.markdown(f"<p style='color:#9090b8;font-size:0.83rem;margin:10px 0 4px;'>{sanitize(narasi)}</p>", unsafe_allow_html=True)
                label_section(TEXT[lang]["viz_episode"])
                CounterEvidenceEngine(ticker).plot_episodes(evidence)

            elif bias == "LOSS_AVERSION":
                c1,c2,c3 = st.columns(3)
                c1.metric("Episode Downtrend", evidence['episodes_found'])
                c2.metric("Prob. Recovery", f"{evidence['recovery_probability']:.0%}")
                c3.metric("Avg Recovery", f"{evidence.get('avg_recovery_days','N/A')} {'hari' if lang=='ID' else 'days'}")
                narasi = llm_result.get("narasi") or intervention["evidence_text"]
                if narasi:
                    st.markdown(f"<p style='color:#9090b8;font-size:0.83rem;margin:10px 0 4px;'>{sanitize(narasi)}</p>", unsafe_allow_html=True)
                label_section(TEXT[lang]["viz_trend"])
                CounterEvidenceEngine(ticker).plot_ma_chart()

            elif bias == "CONFIRMATION_BIAS":
                narasi = llm_result.get("narasi") or intervention["evidence_text"]
                if narasi:
                    narasi_clean = re.sub(r'\*\*(.+?)\*\*', r'\1', narasi)
                    st.markdown(f"<p style='color:#9090b8;font-size:0.83rem;margin:10px 0;'>{sanitize(narasi_clean)}</p>", unsafe_allow_html=True)

        elif bias and evidence.get("status") == "insufficient_data":
            st.caption(evidence.get("message","Data tidak cukup."))

        # Pre-execution friction
        if bias:
            label_section(TEXT[lang]["before_exec"])
            pertanyaan = llm_result.get("pertanyaan") or intervention.get("reflective_question","")
            if pertanyaan:
                st.markdown(f"""
<div style="background:#0a0a14;border:1px solid #1a1a2e;border-left:3px solid #4f46e5;border-radius:0 8px 8px 0;padding:14px 18px;margin-bottom:14px;">
  <p style="color:#a0a0c8;font-size:0.86rem;margin:0;line-height:1.6;font-style:italic;">"{sanitize(pertanyaan)}"</p>
</div>""", unsafe_allow_html=True)

            # Pre-mortem: muncul jika confidence >= 0.70
            pre_mortem = intervention.get("pre_mortem")
            if pre_mortem:
                st.markdown(f"""
<div style="background:#0d0a04;border:1px solid #3a2a06;border-left:3px solid #d97706;border-radius:0 8px 8px 0;padding:14px 18px;margin-bottom:14px;">
  <div style="color:#d97706;font-size:0.68rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;">
    ◈ Pre-Mortem · Sovereign Checkpoint
  </div>
  <p style="color:#c0a060;font-size:0.84rem;margin:0;line-height:1.65;">{sanitize(pre_mortem)}</p>
</div>""", unsafe_allow_html=True)

            confirmed = st.checkbox(TEXT[lang]["checkbox"])

            broker_clicked = st.button(
                TEXT[lang]["btn_broker"], type="primary",
                width='stretch', disabled=not confirmed
            )

            if broker_clicked:
                st.markdown(f"""
<div style="background:#040f04;border:1px solid #0d3a0d;border-radius:10px;padding:16px 20px;margin-top:12px;">
  <div style="color:#4ade80;font-size:0.85rem;font-weight:500;margin-bottom:6px;">OK — {TEXT[lang]['confirmed']}</div>
  <div style="color:#5a8a5a;font-size:0.78rem;">{"Pastikan stop-loss dan target profit sudah ditetapkan." if lang=='ID' else "Ensure stop-loss and profit target are set before entering."}</div>
</div>""", unsafe_allow_html=True)


# ── Session History ─────────────────────────────────────
if st.session_state.history:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    label_section(TEXT[lang]["history"])

    # Hitung bias hanya dari sesi INTERVENTION yang benar-benar terdeteksi bias
    bias_counts = {}
    intervention_entries = [
        h for h in st.session_state.history
        if h.get("intent", "INTERVENTION") == "INTERVENTION"
        and h.get("bias") not in (None, "NONE")
    ]
    for h in intervention_entries:
        b = h["bias"]
        bias_counts[b] = bias_counts.get(b, 0) + 1

    total    = len(st.session_state.history)
    dominant = max(bias_counts, key=bias_counts.get) if bias_counts else None

    if total >= 2:
        col1, col2 = st.columns([1,2])
        with col1:
            if dominant:
                bias_total = len(intervention_entries)
                st.metric(
                    "Bias Dominan" if lang=="ID" else "Dominant Bias",
                    dominant.replace("_"," ").title(),
                    f"{bias_counts[dominant]}/{bias_total}"
                )
                st.progress(bias_counts[dominant] / bias_total)
            else:
                st.metric(
                    "Bias Dominan" if lang=="ID" else "Dominant Bias",
                    "—", "Belum terdeteksi" if lang=="ID" else "None detected"
                )
        with col2:
            if intervention_entries:
                with st.spinner("Analyzing..." if lang=="EN" else "Menganalisis..."):
                    summary = generate_bias_summary(st.session_state.history, lang)
                if summary:
                    st.markdown(f"<div style='background:#0d0d18;border:1px solid #1a1a2e;border-radius:10px;padding:14px 18px;'><p style='color:#a0a0b8;font-size:0.82rem;margin:0;line-height:1.6;'>{summary}</p></div>", unsafe_allow_html=True)

    bicon = {"FOMO":"[F]","LOSS_AVERSION":"[L]","CONFIRMATION_BIAS":"[B]","NONE":"[-]"}
    for h in reversed(st.session_state.history):
        bias_val   = h.get("bias", "NONE") or "NONE"
        intent_val = h.get("intent", "INTERVENTION")
        ticker_val = h.get("ticker") or "—"
        icon       = bicon.get(bias_val, "[-]")
        # Label berbeda per intent
        if intent_val == "EDUCATIONAL":
            prefix = "[EDU]"
        elif intent_val == "DATA_QUERY":
            prefix = f"[DATA] [{ticker_val}]"
        else:
            prefix = f"{icon} [{ticker_val}]"
        inp   = h.get("input", "")
        label = f"{prefix} {inp[:55]}..." if len(inp) > 55 else f"{prefix} {inp}"
        with st.expander(label):
            if intent_val == "EDUCATIONAL":
                st.caption("Pertanyaan edukasi")
            elif intent_val == "DATA_QUERY":
                st.caption(f"Data query · {ticker_val}")
            else:
                conf = h.get("confidence", 0)
                st.caption(f"Bias: {bias_val.replace('_',' ').title()} · Confidence: {conf:.0%}")
            narasi = h.get("narasi", "")
            if narasi:
                st.markdown(f"<p style='color:#9090b8;font-size:0.82rem;'>{narasi}</p>", unsafe_allow_html=True)

    if st.button("Hapus riwayat" if lang=="ID" else "Clear history", type="secondary"):
        st.session_state.history = []
        st.session_state.last_result = None
        st.rerun()

# ── Footer ──────────────────────────────────────────────
st.markdown("<div style='height:48px'></div>", unsafe_allow_html=True)
footer_line1 = "CogniFi · Behavioral Finance AI · v1.1" 
footer_line2_id = "Bukan rekomendasi investasi · Data pasar: Yahoo Finance · Riset: Kahneman (2011), Odean (1998), Thaler (2015)"
footer_line2_en = "Not investment advice · Market data: Yahoo Finance · Research: Kahneman (2011), Odean (1998), Thaler (2015)"
footer_line2 = footer_line2_id if lang == "ID" else footer_line2_en
st.markdown(f"""
<div style='border-top:1px solid #141428;padding:18px 0 8px;text-align:center;'>
  <div style='color:#4040a0;font-size:0.75rem;font-weight:600;letter-spacing:0.04em;margin-bottom:4px;'>{footer_line1}</div>
  <div style='color:#383870;font-size:0.68rem;letter-spacing:0.01em;'>{footer_line2}</div>
</div>""", unsafe_allow_html=True)