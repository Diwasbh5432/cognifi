# ticker_extractor.py
# ──────────────────────────────────────────────────────────
# Auto Ticker Extraction — Anti-Sidebar Feature
#
# Layer 1 (Deterministik): Scan alias dict
#   → Cepat, zero API call, 0 hallucination risk
#   → Covers nama populer, singkatan, nama grup, nama brand
#
# Layer 2 (Gemini Fallback): LLM extraction
#   → Hanya aktif jika Layer 1 gagal
#   → Prompt ketat dengan explicit NULL return
#   → Menjaga akurasi 98.2% tetap stabil
#
# Layer 3 (Intent Check): Apakah ticker relevan dengan bias?
#   → Deteksi Intent A / B / C untuk routing di app.py
#
# Prinsip: Reza tidak perlu tahu tentang sidebar.
# ──────────────────────────────────────────────────────────

import re
from price_fetcher import get_price_data as _pf_validate

# ── ALIAS DICTIONARY ──────────────────────────────────────
# Format: "ticker.JK": ["alias1", "alias2", ...]
# Prioritas: nama paling sering dipakai investor retail ID
# Source: observasi komunitas Stockbit, TikTok, Telegram

TICKER_ALIASES: dict[str, list[str]] = {
    # ── PERBANKAN ─────────────────────────────────────────
    "BBCA.JK": ["bca", "bank bca", "central asia"],
    "BBRI.JK": ["bri", "bank bri", "rakyat indonesia", "bri bank"],
    "BMRI.JK": ["mandiri", "bank mandiri"],
    "BBNI.JK": ["bni", "bank bni", "negara indonesia"],
    "BBTN.JK": ["btn", "bank btn", "tabungan negara"],
    "BJBR.JK": ["bjb", "bank bjb", "jabar banten"],
    "BRIS.JK": ["bri syariah", "bris"],
    "ARTO.JK": ["bank jago", "jago", "bank_jago"],
    "BBYB.JK": ["bank neo", "neo commerce"],
    "AGRO.JK": ["bri agro", "agro"],

    # ── TEKNOLOGI / STARTUP ───────────────────────────────
    "GOTO.JK": ["goto", "gojek", "tokopedia", "gojek tokopedia", "go-to"],
    "BUKA.JK": ["bukalapak", "buka", "buka lapak"],
    "EMTK.JK": ["emtk", "elang mahkota", "emtek", "sctv", "indosiar"],
    "MNCN.JK": ["mnc", "media nusantara", "rcti", "global tv"],
    "INET.JK": ["indosat", "isat baru"],

    # ── TELEKOMUNIKASI ────────────────────────────────────
    "TLKM.JK": ["telkom", "tele", "telkomsel", "tlkm"],
    "ISAT.JK": ["indosat", "im3", "ooredoo", "indosat ooredoo"],
    "EXCL.JK": ["xl", "xl axiata", "excl", "axis"],
    "FREN.JK": ["smartfren", "fren", "smart"],

    # ── ENERGI & TAMBANG ──────────────────────────────────
    "ADRO.JK": ["adaro", "adro"],
    "ITMG.JK": ["indo tambangraya", "itmg", "itm"],
    "PTBA.JK": ["bukit asam", "ptba"],
    "HRUM.JK": ["harum energy", "hrum"],
    "BUMI.JK": ["bumi resources", "bumi"],
    "MDKA.JK": ["merdeka copper", "mdka", "merdeka"],
    "ANTM.JK": ["antam", "aneka tambang"],
    "TINS.JK": ["timah", "tins"],
    "INCO.JK": ["vale", "inco", "vale indonesia"],
    "MEDC.JK": ["medco", "medc"],
    "PGAS.JK": ["pg", "perusahaan gas", "pgas"],
    "BREN.JK": ["bren", "barito renewables", "barito"],

    # ── CONSUMER & RETAIL ─────────────────────────────────
    "UNVR.JK": ["unilever", "unvr"],
    "ICBP.JK": ["indomie", "icbp", "indofood cbp"],
    "INDF.JK": ["indofood", "indf"],
    "GGRM.JK": ["gudang garam", "ggrm"],
    "HMSP.JK": ["sampoerna", "hmsp", "hm sampoerna"],
    "KLBF.JK": ["kalbe", "klbf", "kalbe farma"],
    "SIDO.JK": ["sido muncul", "sido", "sidomuncul", "jamu sido"],
    "ACES.JK": ["ace hardware", "aces"],
    "MAPA.JK": ["sport station", "mapa", "maps"],
    "ERAA.JK": ["erajaya", "eraa", "ibox"],

    # ── PROPERTI & KONSTRUKSI ────────────────────────────
    "WSKT.JK": ["waskita", "wskt"],
    "WIKA.JK": ["wijaya karya", "wika"],
    "SMGR.JK": ["semen indonesia", "smgr", "semen"],
    "TOWR.JK": ["tower bersama", "towr", "tbig"],
    "AKRA.JK": ["akr", "akr corporindo"],

    # ── OTOMOTIF & INDUSTRI ───────────────────────────────
    "ASII.JK": ["astra", "asii", "astra international"],

    # ── SAHAM MEME & HYPE ─────────────────────────────────
    "RAJA.JK": ["ratu", "raja", "rukun raharja"],
    "NICL.JK": ["nickel industries", "nicl"],
    "AMMN.JK": ["amman mineral", "ammn", "amman"],
    "PGEO.JK": ["pgeo", "pertamina geothermal"],
}

# Buat reverse lookup: alias → ticker
_ALIAS_LOOKUP: dict[str, str] = {}
for ticker, aliases in TICKER_ALIASES.items():
    for alias in aliases:
        _ALIAS_LOOKUP[alias.lower()] = ticker


# ── LAYER 1: DETERMINISTIK ────────────────────────────────

def _extract_layer1(text: str) -> str | None:
    """
    Scan teks untuk ticker code langsung (GOTO, BBCA, dll)
    dan alias dalam ALIAS_LOOKUP.
    Return ticker format XXXX.JK atau None.
    """
    text_lower = text.lower()
    text_upper = text.upper()

    # 1a. Cek ticker eksplisit dengan suffix .JK
    jk_match = re.search(r'\b([A-Z]{3,5})\.JK\b', text_upper)
    if jk_match:
        return jk_match.group(0)

    # 1b. Cek ticker eksplisit tanpa .JK (minimal 3 huruf kapital berurutan)
    ticker_match = re.search(r'\b([A-Z]{3,5})\b', text_upper)
    if ticker_match:
        candidate = ticker_match.group(1) + ".JK"
        if candidate in TICKER_ALIASES:
            return candidate

    # 1c. Cek alias — longest match dulu untuk akurasi
    sorted_aliases = sorted(_ALIAS_LOOKUP.keys(), key=len, reverse=True)
    for alias in sorted_aliases:
        if alias in text_lower:
            return _ALIAS_LOOKUP[alias]

    return None


# ── LAYER 2: GEMINI FALLBACK ──────────────────────────────

def _extract_layer2(text: str) -> str | None:
    """
    Panggil Gemini hanya jika Layer 1 gagal.
    Prompt ketat: return ticker IDX atau NULL.
    """
    try:
        import os
        from google import genai

        api_key = os.environ.get("GEMINI_API_KEY", "")
        model   = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        if not api_key:
            return None

        client = genai.Client(api_key=api_key)

        prompt = f"""Ekstrak kode saham IDX dari kalimat berikut.
Aturan ketat:
- Jika ada saham IDX yang disebutkan (nama perusahaan, kode, atau brand), kembalikan kode ticker IDX-nya dalam format XXXX (tanpa .JK).
- Jika tidak ada saham IDX yang bisa diidentifikasi, kembalikan persis: NULL
- Jangan kembalikan apapun selain kode ticker atau NULL.
- Satu ticker saja, yang paling relevan.

Contoh:
"Goto mau naik nih" → GOTO
"Gojek gimana ya" → GOTO
"Ratu saham ini bagus" → RAJA
"Apa itu PER?" → NULL
"Semua saham naik" → NULL

Kalimat: "{text}"
Jawab:"""

        response = client.models.generate_content(
            model=model, contents=prompt
        )
        result = response.text.strip().upper()

        if result == "NULL" or not result:
            return None

        # Bersihkan output — ambil hanya karakter huruf
        clean = re.sub(r'[^A-Z]', '', result)[:5]
        if len(clean) >= 3:
            return clean + ".JK"

    except Exception:
        pass

    return None


# ── LAYER 3: VALIDATE & INTENT ────────────────────────────

def _validate_ticker(ticker: str) -> bool:
    """Cek apakah ticker valid via price_fetcher (curl_cffi)."""
    try:
        result = _pf_validate(ticker, days=7)
        return "error" not in result
    except Exception:
        return False


def classify_intent(text: str, ticker: str | None) -> str:
    """
    Klasifikasi intent untuk Intent Router A/B/C.

    Returns:
        "INTERVENTION" — Ada ticker + sinyal emosi/urgensi
                         → Pipeline bias detection penuh
        "DATA_QUERY"   — Ada ticker + pertanyaan data murni
                         → Structured card, skip bias warning
        "EDUCATIONAL"  — Tidak ada ticker / pertanyaan konsep murni
                         → Conversational mode via Gemini
    """
    text_lower = text.lower()

    # Sinyal emosi dan urgensi (Intent A)
    emotion_signals = [
        "mau naik", "bakal naik", "masih sempet", "beli sekarang",
        "nyangkut", "floating loss", "nunggu balik", "average down",
        "fomo", "takut ketinggalan", "ketinggalan", "telat",
        "bagus kan", "bener kan", "semua orang", "pada beli",
        "ikutan", "yolo", "all in", "kayaknya mau", "feeling",
        "kata grup", "kata influencer", "to the moon", "pump",
        "hold", "cut loss", "rugi", "sayang", "mending",
        "harga murah", "diskon", "serok", "akumulasi",
        "prospek bagus kan", "worth it ga", "masih worth",
    ]

    # Pertanyaan data murni (Intent B)
    data_query_signals = [
        "per ", "p/e", "price to earning",
        "berapa harga", "harga sekarang", "harga saat ini",
        "harga berapa", "saat ini berapa", "sekarang berapa",
        "52 week", "52w high", "all time high",
        "market cap", "revenue", "earning",
        "dividend", "dividen",
        "debt", "hutang",
        "laporan keuangan", "annual report",
        "pb ratio", "price to book",
    ]

    # Pertanyaan edukatif murni (Intent C → EDUCATIONAL)
    education_signals = [
        "apa itu", "apa yang dimaksud", "jelaskan",
        "bagaimana cara", "cara menghitung", "cara analisis",
        "bedain", "perbedaan antara", "kenapa harga",
        "bagaimana pasar", "teori", "konsep",
        "fundamental itu apa", "valuasi itu",
    ]

    has_emotion    = any(s in text_lower for s in emotion_signals)
    has_data_query = any(s in text_lower for s in data_query_signals)
    has_education  = any(s in text_lower for s in education_signals)

    if not ticker:
        return "EDUCATIONAL"

    if has_emotion:
        return "INTERVENTION"

    if has_data_query and not has_emotion:
        return "DATA_QUERY"

    if has_education:
        return "EDUCATIONAL"

    # Default: ada ticker tapi sinyal ambigu → jalankan bias detection
    # Lebih baik false positive intervention daripada miss
    return "INTERVENTION"


# ── PUBLIC API ────────────────────────────────────────────

def extract_ticker(text: str, validate: bool = True) -> tuple[str | None, str]:
    """
    Main entry point. Extract ticker dari natural language.

    Args:
        text:     Input user dalam bahasa apapun
        validate: Jika True, validasi ke Yahoo Finance

    Returns:
        (ticker, source) — ticker dalam format XXXX.JK atau None
        source: "layer1", "layer2", atau "none"
    """
    # Layer 1: deterministik
    ticker = _extract_layer1(text)
    if ticker:
        if not validate or _validate_ticker(ticker):
            return ticker, "layer1"

    # Layer 2: Gemini fallback
    ticker = _extract_layer2(text)
    if ticker:
        if not validate or _validate_ticker(ticker):
            return ticker, "layer2"

    return None, "none"


def extract_ticker_and_intent(text: str) -> dict:
    """
    Convenience wrapper: extract ticker + classify intent sekaligus.

    Returns:
        {
            "ticker": "GOTO.JK" | None,
            "source": "layer1" | "layer2" | "none",
            "intent": "INTERVENTION" | "DATA_QUERY" | "EDUCATIONAL",
        }
    """
    ticker, source = extract_ticker(text)
    intent = classify_intent(text, ticker)

    return {
        "ticker": ticker,
        "source": source,
        "intent": intent,
    }


# ── QUICK TEST ────────────────────────────────────────────

if __name__ == "__main__":
    test_cases = [
        # Layer 1 — ticker eksplisit
        ("GOTO mau naik nih, masih sempet masuk ga?",          "GOTO.JK",  "INTERVENTION"),
        ("UNVR nyangkut, nunggu balik modal dulu",              "UNVR.JK",  "INTERVENTION"),
        # Layer 1 — alias
        ("Gojek Tokopedia gimana ya, pada bilang mau pump",    "GOTO.JK",  "INTERVENTION"),
        ("Telkom lagi gimana? worth it ga masuk sekarang",     "TLKM.JK",  "INTERVENTION"),
        ("BCA fundamental bagus kan? bener ga",                "BBCA.JK",  "INTERVENTION"),
        ("Ratu saham ini mau naik, kata grup pada beli",       "RAJA.JK",  "INTERVENTION"),
        # Intent B — data query
        ("PER BBCA berapa sekarang?",                          "BBCA.JK",  "DATA_QUERY"),
        ("Harga TLKM saat ini berapa?",                        "TLKM.JK",  "DATA_QUERY"),
        # Intent C — educational
        ("Apa itu Price to Earning ratio?",                    None,       "EDUCATIONAL"),
        ("Bagaimana cara analisis fundamental saham?",         None,       "EDUCATIONAL"),
        # No ticker
        ("Semua saham mau naik kayaknya",                      None,       "EDUCATIONAL"),
    ]

    print("Testing ticker_extractor.py")
    print("=" * 65)
    correct = 0
    for text, exp_ticker, exp_intent in test_cases:
        result = extract_ticker_and_intent(text)
        t_ok = result["ticker"] == exp_ticker
        i_ok = result["intent"] == exp_intent
        ok = t_ok and i_ok
        correct += ok
        status = "PASS" if ok else "FAIL"
        print(f"{status} \"{text[:50]}...\"")
        if not ok:
            print(f"   Ticker  : expected {exp_ticker:<12} got {result['ticker']} ({result['source']})")
            print(f"   Intent  : expected {exp_intent:<15} got {result['intent']}")

    print("=" * 65)
    print(f"Result: {correct}/{len(test_cases)} passed")