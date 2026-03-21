# llm.py
from google import genai
from config import GEMINI_API_KEY, GEMINI_MODEL
import json
import re
import time
import logging

logger = logging.getLogger(__name__)

client = genai.Client(api_key=GEMINI_API_KEY)

# ── RAG ─────────────────────────────────────────────────────────────────────
try:
    from rag import retrieve_context_formatted
    RAG_ENABLED = True
except ImportError:
    RAG_ENABLED = False
    def retrieve_context_formatted(*args, **kwargs) -> str:
        return ""


# ── Retry with Exponential Backoff ──────────────────────────────────────────
def _call_gemini(prompt: str, max_retries: int = 3) -> str:
    """
    Wrapper Gemini API dengan retry + exponential backoff.
    Menangani 429 (rate limit) dan error sementara lainnya.
    
    Delays: 2s → 4s → 8s (total max ~14s sebelum give up)
    """
    delay = 2
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )
            return response.text.strip()

        except Exception as e:
            last_error = e
            err_str = str(e).lower()

            # 429 = rate limit, 500/503 = server error sementara → retry
            is_retryable = (
                "429" in err_str or
                "quota" in err_str or
                "rate" in err_str or
                "500" in err_str or
                "503" in err_str or
                "unavailable" in err_str or
                "deadline" in err_str
            )

            if not is_retryable or attempt == max_retries:
                logger.warning(f"Gemini call failed (attempt {attempt}/{max_retries}): {e}")
                break

            logger.info(f"Gemini rate limit/error, retry {attempt}/{max_retries} in {delay}s...")
            time.sleep(delay)
            delay *= 2  # exponential: 2 → 4 → 8

    # Semua retry habis — kembalikan string kosong, caller handle fallback
    logger.error(f"Gemini call exhausted retries. Last error: {last_error}")
    return ""


def classify_bias_from_input(user_input: str, ticker: str) -> dict:
    # --- STEP 1: ENHANCED PRE-CLASSIFICATION (Few-Shot) ---
    # Kita beri contoh agar Gemini tahu bedanya tanya data vs bias
    pre_prompt = f"""
    Klasifikasikan input investor ke salah satu: FOMO, LOSS_AVERSION, CONFIRMATION_BIAS, atau NONE.
    
    Contoh:
    "Apa itu PER?" -> NONE
    "Gue nyangkut, gamau jual" -> LOSS_AVERSION
    "Semua orang beli, gue telat ga?" -> FOMO
    "Bener kan saham ini bagus? Semua grup bilang gitu" -> CONFIRMATION_BIAS
    
    Input: "{user_input}"
    Jawab hanya 1 kata kategori.
    """
    
    try:
        text = _call_gemini(pre_prompt)
        predicted_bias = re.sub(r'[^A-Z_]', '', text.upper()) if text else "NONE"
    except:
        predicted_bias = "NONE"

    # --- STEP 2: RAG DENGAN STRICT FILTER ---
    # Hanya panggil RAG jika Step 1 SANGAT yakin ada bias. 
    # Jika NONE, jangan kasih rag_context sama sekali agar tidak "meracuni" logika.
    rag_context = ""
    if predicted_bias in ["FOMO", "LOSS_AVERSION", "CONFIRMATION_BIAS"]:
        rag_context = retrieve_context_formatted(
            query=user_input,
            bias_type=predicted_bias,
            category="deteksi", 
            top_k=2 # Perkecil top_k agar tidak terlalu banyak noise
        )

    rag_block = f"\n[KNOWLEDGE BASE SIGNAL]:\n{rag_context}\n" if rag_context else ""

    # --- STEP 3: FINAL CLASSIFICATION (Logic Gate) ---
    prompt = f"""
Kamu adalah CogniFi AI. Tugasmu membedakan antara pertanyaan INFORMASIONAL (NONE) dan BIAS PSIKOLOGIS.

Input: "{user_input}"
Saham: {ticker}
{rag_block}

ATURAN KETAT:
- Jika input mengandung kata tanya (Apa, Bagaimana, Siapa, Berapa) dan TIDAK menunjukkan emosi/kepemilikan saham -> WAJIB NONE.
- Jika ada kata "Nyangkut", "Sayang kalau jual rugi", "Average down biar balik modal", "Hold sampai balik" -> LOSS_AVERSION.
- Jika ada kata "Ketinggalan", "Semua orang profit", "Ikutan masuk", "Takut telat" -> FOMO.
- Jika user sudah punya posisi dan mencari pembenaran ("Bener kan?", "Grup bilang bagus") -> CONFIRMATION_BIAS.

Jawab dalam JSON:
{{
  "bias": "KATEGORI",
  "confidence": [0.0 - 1.0],
  "alasan": "jelaskan alasan klasifikasi dalam 1 kalimat"
}}
"""

    try:
        text = _call_gemini(prompt)
        if not text:
            return {"bias": "NONE", "confidence": 0.0, "alasan": "API tidak merespons."}
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            result = json.loads(match.group())
            if result.get("confidence", 0) < 0.5 and predicted_bias == "NONE":
                return {"bias": "NONE", "confidence": result.get("confidence", 0), "alasan": "Pertanyaan umum/edukasi."}
            return result
        return {"bias": "NONE", "confidence": 0.0, "alasan": "Parsing error"}
    except Exception as e:
        return {"bias": "NONE", "confidence": 0.0, "alasan": str(e)}

def generate_intervention_text(
    bias_type: str, ticker: str, confidence: float,
    signals: list, evidence: dict, user_input: str,
    fundamental: dict = None, lang: str = "ID"
) -> dict:
    bias_labels = {
        "FOMO": "FOMO (Fear of Missing Out)",
        "LOSS_AVERSION": "Loss Aversion",
        "CONFIRMATION_BIAS": "Confirmation Bias",
    }
    evidence_summary = _format_evidence_for_prompt(bias_type, evidence)
    fund_summary = _format_fundamental_for_prompt(fundamental) if fundamental else "Data fundamental tidak tersedia."

    # RAG: ambil konteks teori + prinsip intervensi dari knowledge base
    rag_theory = retrieve_context_formatted(
        query=f"{bias_type} {user_input}",
        bias_type=bias_type,
        category="teori",
        top_k=2
    )
    rag_prinsip = retrieve_context_formatted(
        query="prinsip intervensi output format tone",
        bias_type="GENERAL",
        category="prinsip",
        top_k=2
    )
    rag_block = ""
    if rag_theory:
        rag_block += f"\nTEORI BEHAVIORAL FINANCE (gunakan sebagai dasar penjelasan):\n{rag_theory}\n"
    if rag_prinsip:
        rag_block += f"\nPRINSIP OUTPUT (ikuti ketat):\n{rag_prinsip}\n"

    if lang == "ID":
        prompt = f"""
Kamu adalah sistem AI berbasis riset behavioral finance (Kahneman 2011, Odean 1998, Thaler 2015).
Tugasmu: menghasilkan analisis yang jelas, berbasis data, membantu investor berpikir lebih rasional.
{rag_block}
KONTEKS:
- Input investor: "{user_input}"
- Saham: {ticker}
- Bias terdeteksi: {bias_labels.get(bias_type, bias_type)}
- Confidence score: {confidence:.0%}
- Sinyal teknikal: {', '.join(signals[:4]) if signals else 'tidak ada'}

DATA HISTORIS:
{evidence_summary}

DATA FUNDAMENTAL:
{fund_summary}

Jawab dalam format PERSIS ini (tidak ada teks lain):

NARASI: [2-3 kalimat kondisi {ticker} berbasis data. Mulai langsung dengan fakta. Tanpa rekomendasi beli/jual.]

PERTANYAAN: [1 pertanyaan reflektif spesifik ke bias {bias_type} dan saham {ticker}. Harus bisa dijawab dengan angka atau fakta konkret.]

KONTRIBUTOR_1: [Kontributor terbesar confidence — label singkat: penjelasan 1 kalimat berbasis penelitian Kahneman/Thaler/Odean tentang mengapa sinyal ini relevan]

KONTRIBUTOR_2: [Kontributor kedua — format sama]

KONTRIBUTOR_3: [Kontributor ketiga — format sama]

ACTION: [AVOID atau REDUCE atau HOLD. AVOID = bias tinggi >70% + fundamental warn; REDUCE = loss aversion + posisi sudah merugi signifikan; HOLD = bias sedang + fundamental ok]

ACTION_ALASAN: [1-2 kalimat alasan action, berbasis data yang tersedia]
"""
    else:
        prompt = f"""
You are an AI system grounded in behavioral finance research (Kahneman 2011, Odean 1998, Thaler 2015).
{rag_block}
CONTEXT:
- Investor input: "{user_input}"
- Stock: {ticker}
- Bias detected: {bias_labels.get(bias_type, bias_type)}
- Confidence: {confidence:.0%}
- Technical signals: {', '.join(signals[:4]) if signals else 'none'}

HISTORICAL DATA: {evidence_summary}
FUNDAMENTAL DATA: {fund_summary}

Respond in EXACTLY this format (no other text):

NARASI: [2-3 sentences on {ticker} condition. Start with facts. No buy/sell recommendation.]

PERTANYAAN: [1 reflective question specific to {bias_type} and {ticker}. Must be answerable with numbers or facts.]

KONTRIBUTOR_1: [Biggest contributor — short label: 1-sentence explanation based on Kahneman/Thaler/Odean research]

KONTRIBUTOR_2: [Second contributor — same format]

KONTRIBUTOR_3: [Third contributor — same format]

ACTION: [AVOID or REDUCE or HOLD. AVOID = high bias >70% + fundamental warn; REDUCE = loss aversion + significant loss; HOLD = moderate bias + ok fundamentals]

ACTION_ALASAN: [1-2 sentence rationale based on available data]
"""

    try:
        text = _call_gemini(prompt)
        if not text:
            return {"status": "error", "narasi": "", "pertanyaan": "", "kontributor": [], "action": "HOLD", "action_alasan": "", "error": "API tidak merespons."}
        result = {"status": "ok", "narasi": "", "pertanyaan": "", "kontributor": [], "action": "HOLD", "action_alasan": ""}
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith("NARASI:"):
                result["narasi"] = line.replace("NARASI:", "").strip()
            elif line.startswith("PERTANYAAN:"):
                result["pertanyaan"] = line.replace("PERTANYAAN:", "").strip()
            elif line.startswith("KONTRIBUTOR_1:"):
                result["kontributor"].append(line.replace("KONTRIBUTOR_1:", "").strip())
            elif line.startswith("KONTRIBUTOR_2:"):
                result["kontributor"].append(line.replace("KONTRIBUTOR_2:", "").strip())
            elif line.startswith("KONTRIBUTOR_3:"):
                result["kontributor"].append(line.replace("KONTRIBUTOR_3:", "").strip())
            elif line.startswith("ACTION:"):
                val = line.replace("ACTION:", "").strip()
                if val in ["AVOID", "REDUCE", "HOLD"]:
                    result["action"] = val
            elif line.startswith("ACTION_ALASAN:"):
                result["action_alasan"] = line.replace("ACTION_ALASAN:", "").strip()
        return result
    except Exception as e:
        return {"status": "error", "narasi": "", "pertanyaan": "", "kontributor": [], "action": "HOLD", "action_alasan": "", "error": str(e)}


def summarize_stock_condition(ticker: str, price_data: dict) -> str:
    if not price_data or "error" in price_data:
        return ""
    change_5d    = price_data.get("change_5d", 0)
    change_10d   = price_data.get("change_10d", 0)
    volume_ratio = price_data.get("volume_ratio", 1)
    current      = price_data.get("current_price", 0)
    downtrend    = price_data.get("downtrend", False)
    prompt = f"""
Tulis ringkasan kondisi teknikal saham dalam 2 kalimat.
Bahasa Indonesia. Natural. Tidak ada rekomendasi beli/jual. Hanya fakta.

Data {ticker}: Harga Rp {current:,.0f}, perubahan 5h: {change_5d:.1%},
perubahan 10h: {change_10d:.1%}, volume: {volume_ratio:.1f}x rata-rata,
tren: {"turun (MA20 < MA50)" if downtrend else "naik atau sideways"}.

Output: hanya 2 kalimat, tidak ada label, tidak ada preamble.
"""
    try:
        text = _call_gemini(prompt)
        return text if text else ""
    except Exception:
        return ""


def analyze_fundamental(ticker: str, fundamental: dict, lang: str = "ID") -> dict:
    """Label metrik fundamental: OK / CAUTION / WARN berbasis riset Graham & Damodaran."""
    if not fundamental:
        return {}

    def label_pe(val):
        # Graham (1949): P/E < 15 = value, > 25 = mahal
        if val == "N/A": return "N/A", "neutral"
        try:
            v = float(val)
            if v < 0:  return val, "warn"
            if v < 15: return val, "ok"
            if v < 25: return val, "caution"
            return val, "warn"
        except: return val, "neutral"

    def label_der(val):
        # Damodaran emerging markets: DER > 2 = berisiko
        if val == "N/A": return "N/A", "neutral"
        try:
            v = float(val)
            if v < 1:  return val, "ok"
            if v < 2:  return val, "caution"
            return val, "warn"
        except: return val, "neutral"

    def label_margin(val):
        if val == "N/A": return "N/A", "neutral"
        try:
            pct = float(val.replace("%","")) if "%" in str(val) else float(val)*100
            if pct > 15: return val, "ok"
            if pct > 5:  return val, "caution"
            return val, "warn"
        except: return val, "neutral"

    def label_growth(val):
        if val == "N/A": return "N/A", "neutral"
        try:
            pct = float(val.replace("%","")) if "%" in str(val) else float(val)*100
            if pct > 10: return val, "ok"
            if pct > 0:  return val, "caution"
            return val, "warn"
        except: return val, "neutral"

    labeled = {}
    for k, v in fundamental.items():
        if "P/E" in k or "PE" in k:
            labeled[k] = label_pe(v)
        elif "Debt" in k or "DER" in k:
            labeled[k] = label_der(v)
        elif "Margin" in k:
            labeled[k] = label_margin(v)
        elif "Growth" in k:
            labeled[k] = label_growth(v)
        else:
            labeled[k] = (v, "neutral")

    warns    = sum(1 for _, (_, s) in labeled.items() if s == "warn")
    cautions = sum(1 for _, (_, s) in labeled.items() if s == "caution")
    overall  = "WARN" if warns >= 2 else ("CAUTION" if warns >= 1 or cautions >= 2 else "OK")

    return {"labeled": labeled, "overall": overall}


def generate_bias_summary(history: list, lang: str = "ID") -> str:
    if len(history) < 2:
        return ""
    history_text = "\n".join([
        f"- [{h['ticker']}] \"{h['input']}\" → {h['bias']} ({h['confidence']:.0%})"
        for h in history
    ])
    if lang == "ID":
        prompt = f"""
Kamu adalah psikolog investasi. Analisis pola perilaku investor ini dalam 2-3 kalimat.
Riwayat: {history_text}
- Identifikasi bias dominan, artinya, dan 1 saran konkret.
- Natural, tidak menghakimi, berbasis fakta.
Output: hanya paragraf, tanpa label.
"""
    else:
        prompt = f"""
You are an investment psychologist. Analyze this investor's behavioral pattern in 2-3 sentences.
History: {history_text}
- Identify dominant bias, its meaning, and 1 concrete suggestion.
- Natural, non-judgmental, facts-based.
Output: only paragraph, no labels.
"""
    try:
        text = _call_gemini(prompt)
        return text if text else ""
    except Exception:
        return ""


def _format_evidence_for_prompt(bias_type: str, evidence: dict) -> str:
    if evidence.get("status") != "ok":
        return "Data historis tidak tersedia."
    if bias_type == "FOMO":
        return (
            f"Episode serupa: {evidence.get('episodes_found',0)} kejadian. "
            f"Koreksi: {evidence.get('corrections_count',0)} kali ({evidence.get('correction_probability',0):.0%}). "
            f"Avg koreksi: {evidence.get('avg_correction',0):.1%}. Best: +{evidence.get('best_outcome',0):.1%}."
        )
    elif bias_type == "LOSS_AVERSION":
        return (
            f"Episode downtrend: {evidence.get('episodes_found',0)}. "
            f"Recovery: {evidence.get('recovered_count',0)}/{evidence.get('sampled',0)} ({evidence.get('recovery_probability',0):.0%}). "
            f"Avg waktu: {evidence.get('avg_recovery_days','N/A')} hari."
        )
    elif bias_type == "CONFIRMATION_BIAS":
        fund = evidence.get("fundamental", {})
        return "Fundamental: " + ", ".join(f"{k}: {v}" for k,v in fund.items() if v != "N/A")
    return "N/A"


def _format_fundamental_for_prompt(fundamental: dict) -> str:
    if not fundamental:
        return "Tidak tersedia."
    return ", ".join(f"{k}: {v}" for k,v in fundamental.items() if v != "N/A") or "Tidak tersedia."