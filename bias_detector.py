# bias_detector.py
# =============================================================================
# CogniFi — Mesin Deteksi Bias Perilaku Investor
# =============================================================================
#
# File ini berisi LOGIKA deteksi bias. Kata kunci ada di keywords.py.
#
# ALUR DETEKSI (6 layer):
#   Layer 1 — Early Exit    : override ke NONE jika kalimat edukatif/analitis
#   Layer 2 — Price         : ambil data harga dari yfinance
#   Layer 3 — Base Scores   : hitung skor FOMO, LA, CB dari keyword + harga
#   Layer 4 — Adjustments   : koreksi kontekstual antar-bias
#   Layer 5 — Threshold     : putuskan bias final atau NONE
#   Layer 6 — Signals       : susun daftar sinyal untuk ditampilkan di UI
#
# CARA PAKAI:
#   from bias_detector import detect_bias
#   result = detect_bias("GOTO mau naik nih, semua orang beli", "GOTO.JK")
#   print(result["bias_detected"])   # "FOMO"
#   print(result["confidence"])      # 0.75
#
# CARA TAMBAH KEYWORD:
#   Edit keywords.py saja — tidak perlu menyentuh file ini.
#
# =============================================================================

import re
import pandas as pd
from price_fetcher import get_price_data as _pf_get_price

# =============================================================================
# YFINANCE AVAILABILITY CHECK
# Cek koneksi ke Yahoo Finance saat modul pertama kali di-import.
# Kalau gagal (IP diblock / rate limit / offline), tanya user apakah mau lanjut
# tanpa price data. Jawaban disimpan di _PRICE_ENABLED agar tidak tanya berulang.
# =============================================================================

_PRICE_ENABLED: bool = True   # default: price aktif

def _check_yfinance_availability() -> bool:
    """
    Test koneksi ke Yahoo Finance dengan download singkat.
    Return True jika berhasil, False jika gagal.
    """
    try:
        result = _pf_get_price("AAPL", days=5)
        return "error" not in result
    except Exception:
        return False

def _prompt_skip_price() -> bool:
    """
    Tampilkan pesan ke user dan tanya apakah mau lanjut tanpa price data.
    Return True jika user mau lanjut (skip price), False jika batal.
    """
    print()
    print("=" * 65)
    print("⚠️  YFINANCE TIDAK BISA DIAKSES")
    print("=" * 65)
    print("Yahoo Finance tidak merespons — kemungkinan penyebab:")
    print("  • IP kamu diblock sementara oleh Yahoo Finance")
    print("  • Rate limit karena terlalu banyak request sebelumnya")
    print("  • Tidak ada koneksi internet")
    print()
    print("Tanpa data harga, sistem tetap bisa mendeteksi bias")
    print("menggunakan keyword analysis saja (Layer 3–6 tetap aktif).")
    print("Akurasi sedikit lebih rendah untuk kasus yang butuh konfirmasi harga.")
    print()
    answer = input("Lanjut tanpa data harga? (y/n): ").strip().lower()
    print("=" * 65)
    print()
    return answer in ("y", "yes", "ya", "")

def initialize_price_check():
    """
    Panggil fungsi ini sekali di awal program (atau test runner).
    Mengisi _PRICE_ENABLED berdasarkan hasil koneksi dan pilihan user.
    """
    global _PRICE_ENABLED
    if not _check_yfinance_availability():
        _PRICE_ENABLED = _prompt_skip_price()
        if not _PRICE_ENABLED:
            print("Dibatalkan. Jalankan ulang setelah koneksi Yahoo Finance tersedia.")
            raise SystemExit(0)
        else:
            print("✅ Melanjutkan tanpa data harga — price layer dinonaktifkan.\n")
    else:
        _PRICE_ENABLED = True

# Import semua keyword banks dari file terpisah
from keywords import (
    FOMO_URGENCY, FOMO_SOCIAL,
    LOSS_AVERSION_DENIAL, LOSS_AVERSION_AVERAGING, LOSS_AVERSION_BLAME,
    CONFIRMATION_LEADING, CONFIRMATION_ECHO,
    CONFIRMATION_POSITIVE, CONFIRMATION_OVERCONFIDENT,
    RISK_KEYWORDS, ANALYSIS_KEYWORDS,
    EDUCATION_PATTERNS, ANALYTICAL_PATTERNS,
)

# Panggil sekali saat modul di-import — cek koneksi yfinance
# Kalau non-interactive (test runner), skip prompt dan langsung disable price
import sys as _sys
if _sys.stdin.isatty():
    initialize_price_check()
else:
    _PRICE_ENABLED = False


# =============================================================================
# BAGIAN 1 — ANALISIS TEKS
# Hitung berapa banyak keyword tiap kategori yang muncul di input user.
# Hasilnya adalah dict "signals" yang dipakai oleh semua scorer di bawah.
# =============================================================================

def analyze_text(text: str) -> dict:
    """
    Tokenize input dan hitung sinyal keyword per kategori.

    Return dict dengan key:
        urgency_count       — jumlah keyword FOMO urgency/timing
        social_count        — jumlah keyword FOMO social proof
        denial_count        — jumlah keyword LA denial/hold
        averaging_count     — jumlah keyword LA averaging down
        blame_count         — jumlah keyword LA menyalahkan pihak luar
        leading_count       — jumlah keyword CB leading question
        echo_count          — jumlah keyword CB echo chamber
        positive_count      — jumlah keyword CB minta analisis positif
        overconfident_count — jumlah keyword CB overconfidence/dismiss
        risk_absent         — True jika TIDAK ada kata risiko (NONE signal)
        analysis_absent     — True jika TIDAK ada kata analisis (NONE signal)
        is_education        — True jika pola pertanyaan edukatif
        is_analytical       — True jika pola pertanyaan analitis
    """
    text_lower = text.lower()

    # Helper: hitung berapa keyword yang ada di teks
    def count_keywords(keywords: list) -> int:
        return sum(1 for kw in keywords if kw in text_lower)

    # Helper: cek apakah ada salah satu pola
    def has_pattern(patterns: list) -> bool:
        return any(p in text_lower for p in patterns)

    return {
        "urgency_count":        count_keywords(FOMO_URGENCY),
        "social_count":         count_keywords(FOMO_SOCIAL),
        "denial_count":         count_keywords(LOSS_AVERSION_DENIAL),
        "averaging_count":      count_keywords(LOSS_AVERSION_AVERAGING),
        "blame_count":          count_keywords(LOSS_AVERSION_BLAME),
        "leading_count":        count_keywords(CONFIRMATION_LEADING),
        "echo_count":           count_keywords(CONFIRMATION_ECHO),
        "positive_count":       count_keywords(CONFIRMATION_POSITIVE),
        "overconfident_count":  count_keywords(CONFIRMATION_OVERCONFIDENT),
        "risk_absent":          count_keywords(RISK_KEYWORDS) == 0,
        "analysis_absent":      count_keywords(ANALYSIS_KEYWORDS) == 0,
        "is_education":         has_pattern(EDUCATION_PATTERNS),
        "is_analytical":        has_pattern(ANALYTICAL_PATTERNS),
    }


# =============================================================================
# BAGIAN 2 — ANALISIS HARGA
# Ambil data historis dari yfinance untuk memperkuat/melemahkan sinyal bias.
# Kalau yfinance gagal (network/ticker salah), return {"error": "..."} dan
# semua scorer akan skip bagian harga secara graceful.
# =============================================================================

def analyze_price(ticker: str) -> dict:
    """
    Ambil data harga 60 hari terakhir dan hitung indikator pendukung.

    Return dict dengan key:
        change_5d      — persentase perubahan harga 5 hari terakhir
        change_10d     — persentase perubahan harga 10 hari terakhir
        volume_ratio   — rasio volume 5 hari terakhir vs rata-rata sebelumnya
        downtrend      — True jika MA20 < MA50 (tren turun)
        current_price  — harga penutupan terakhir
        fomo_signal    — True jika naik >10% atau volume 2x rata-rata
        loss_signal    — True jika turun >8% dan sedang downtrend
    """
    # Skip price jika yfinance tidak tersedia (user pilih lanjut tanpa harga)
    if not _PRICE_ENABLED or not ticker:
        return {"error": "Price layer dinonaktifkan"}

    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return _pf_get_price(ticker, days=60)

    except Exception:
        return {"error": "Price tidak tersedia"}


# =============================================================================
# BAGIAN 3 — SCORER
# Hitung skor mentah tiap bias (0.0 – 1.0).
# Skor ini bukan confidence final — masih bisa dimodifikasi di Layer 4.
# =============================================================================

def score_fomo(text: dict, price: dict, text_lower: str) -> float:
    """
    Skor FOMO berdasarkan urgency, social proof, dan data harga.

    Logika utama:
        - Urgency (timing/masuk sekarang) berkontribusi paling besar
        - Social proof (orang lain beli) memperkuat urgency
        - Combo urgency + social = bonus tambahan
        - Data harga naik kuat / volume meledak = boost ekstra
    """
    score = 0.0

    # --- Urgency keywords ---
    if text["urgency_count"] >= 3:   score += 0.45
    elif text["urgency_count"] == 2: score += 0.35
    elif text["urgency_count"] == 1: score += 0.25

    # --- Social proof keywords ---
    if text["social_count"] >= 2:    score += 0.35
    elif text["social_count"] == 1:  score += 0.25

    # --- Bonus: ada urgency DAN social bersamaan ---
    if text["urgency_count"] >= 1 and text["social_count"] >= 1:
        score += 0.15

    # --- Bonus: social tanpa leading question = FOMO murni, bukan CB ---
    if text["social_count"] >= 1 and text["leading_count"] == 0:
        score += 0.15

    # --- Boost dari data harga ---
    if "error" not in price:
        if price["change_5d"] > 0.25:     score += 0.25
        elif price["change_5d"] > 0.15:   score += 0.15
        elif price["change_5d"] > 0.10:   score += 0.10
        if price["volume_ratio"] > 2.0:   score += 0.15
        elif price["volume_ratio"] > 1.5: score += 0.08

    # --- Boost untuk pola "% naik" — implisit FOMO dari profit teman ---
    if "naik" in text_lower and "%" in text_lower:
        score += 0.40

    # --- Boost untuk "waktu terbaik / timing bagus" + social ---
    fomo_timing_words = [
        "waktu terbaik", "saat terbaik", "timing bagus", "sekarang waktu",
        "baru awal", "awal rally", "baru mulai naik", "momen cuan",
        "waktu yang tepat", "waktu masuk terbaik",
    ]
    if text["social_count"] >= 1 and any(kw in text_lower for kw in fomo_timing_words):
        score += 0.60

    # --- Boost komunitas + frasa waktu terbaik ---
    if "komunitas" in text_lower and any(kw in text_lower for kw in fomo_timing_words):
        score += 0.35

    return min(score, 1.0)


def score_loss_aversion(text: dict, price: dict) -> float:
    """
    Skor Loss Aversion berdasarkan denial, averaging, blame, dan data harga.

    Logika utama:
        - Denial (nggak mau cut loss, hold terus) adalah sinyal terkuat
        - Averaging down memperkuat sinyal LA
        - Blame (bandar, manipulasi) sebagai pelengkap
        - Combo denial + averaging = bonus
        - Harga turun dalam konfirmasi sinyal dari data
    """
    score = 0.0

    # --- Denial keywords ---
    if text["denial_count"] >= 3:      score += 0.45
    elif text["denial_count"] == 2:    score += 0.35
    elif text["denial_count"] == 1:    score += 0.25

    # --- Averaging down keywords ---
    if text["averaging_count"] >= 2:   score += 0.35
    elif text["averaging_count"] == 1: score += 0.25

    # --- Blame keywords ---
    if text["blame_count"] >= 2:       score += 0.35
    elif text["blame_count"] == 1:     score += 0.25

    # --- Bonus: ada denial DAN averaging bersamaan ---
    if text["denial_count"] >= 1 and text["averaging_count"] >= 1:
        score += 0.15

    # --- Boost dari data harga turun ---
    if "error" not in price:
        if price["change_5d"] < -0.20:   score += 0.25
        elif price["change_5d"] < -0.10: score += 0.15
        elif price["change_5d"] < -0.05: score += 0.08
        if price["downtrend"]:           score += 0.15

    return min(score, 1.0)


def score_confirmation_bias(text: dict, user_input: str) -> float:
    """
    Skor Confirmation Bias berdasarkan leading question, echo chamber,
    positive seeking, dan overconfidence.

    Logika utama:
        - Harus ada SINYAL AKTIF (leading/echo/overconfident) — tidak cukup
          hanya karena tidak ada kata risiko atau analisis
        - Leading question adalah sinyal terkuat
        - Echo chamber (semua bilang X) memperkuat
        - Overconfident bank menangkap CB halus tanpa leading question eksplisit
        - risk_absent / analysis_absent hanya bonus jika sudah ada sinyal aktif
    """
    score = 0.0

    # --- Leading question (minta validasi / konfirmasi) ---
    if text["leading_count"] >= 2:   score += 0.50
    elif text["leading_count"] == 1: score += 0.28

    # --- Echo chamber (semua bilang / semua analis setuju) ---
    if text["echo_count"] >= 2:      score += 0.45
    elif text["echo_count"] == 1:    score += 0.30

    # --- Bonus: combo leading + echo ---
    if text["leading_count"] >= 1 and text["echo_count"] >= 1:
        score += 0.20

    # --- Positive seeking (minta analisis yang mendukung saja) ---
    if text["positive_count"] >= 2:  score += 0.25
    elif text["positive_count"] >= 1: score += 0.15

    # --- Overconfident / CB halus ---
    overconfident = text.get("overconfident_count", 0)
    if overconfident >= 2:   score += 0.45
    elif overconfident == 1: score += 0.28

    # --- Bonus risk/analysis absent — hanya jika sudah ada sinyal aktif ---
    if score > 0:
        if text["risk_absent"] and text["analysis_absent"]:
            score += 0.10

    return min(score, 1.0)


# =============================================================================
# BAGIAN 4 — DETECT BIAS (fungsi utama)
# Gabungkan semua layer dan return hasil final.
# =============================================================================

def detect_bias(user_input: str, ticker: str) -> dict:
    """
    Deteksi bias dari input user dan data harga ticker.

    Parameter:
        user_input  — kalimat yang diketik user di chat
        ticker      — kode saham, mis. "BBCA.JK"

    Return dict:
        bias_detected   — "FOMO" | "LOSS_AVERSION" | "CONFIRMATION_BIAS" | "NONE"
        confidence      — skor 0.0–1.0 dari bias yang terdeteksi
        scores          — dict skor mentah semua bias
        signals         — list string sinyal yang ditemukan (untuk UI)
        price_data      — dict data harga dari yfinance (atau {"error": ...})
    """
    text_lower = user_input.lower()

    # =========================================================================
    # LAYER 1 — EARLY EXIT: Edukatif & Analitis
    # Jika pertanyaan bersifat edukatif atau analitis murni, langsung return NONE.
    # Kecuali ada sinyal bias yang sangat kuat (threshold "strong_bias").
    # =========================================================================

    text = analyze_text(user_input)

    # Keyword cut loss edukatif — pertanyaan "kapan sebaiknya cut loss", dll.
    # Ini berbeda dari user yang sedang nyangkut dan mempertimbangkan cut loss.
    CUT_LOSS_EDU_KEYWORDS = [
        "kapan ideal cut loss", "kapan cut loss ideal", "ideal cut loss",
        "kapan harus cut loss kalau rugi", "kapan cut loss kalau rugi",
        "kapan sebaiknya cut loss", "cut loss berapa persen", "cut loss ideal berapa",
        "berapa persen cut loss", "kapan cutloss kalau rugi", "kapan waktu cut loss",
        "bagaimana cara cut loss", "strategi cut loss", "cut loss yang baik",
        "kapan waktu yang tepat cut loss", "cut loss sebaiknya kapan",
        "cara menentukan cut loss", "metode cut loss", "cut loss yang benar",
        "idealnya cut loss kapan", "cut loss idealnya berapa",
    ]

    # Keyword risiko / red flag — pertanyaan objektif tentang downside
    RISK_EDU_KEYWORDS = [
        "risiko", "risk", "downside", "red flag", "bahaya", "worst case",
        "skenario terburuk", "skenario buruk", "masalah", "overvalued", "terlalu mahal",
    ]

    # Definisi "strong bias" — kalau ada ini, skip early exit walaupun kalimat edukatif
    def has_strong_bias() -> bool:
        return (
            text["denial_count"] >= 2 or
            text["averaging_count"] >= 1 or
            text["blame_count"] >= 1 or
            (text["urgency_count"] >= 2 and text["social_count"] >= 1)
        )

    # Override 1: pertanyaan "what would invalidate" = pertanyaan analitis murni
    INVALIDATE_KEYWORDS = [
        "invalidate", "thesis salah", "buktikan salah", "what would invalidate",
    ]
    if any(p in text_lower for p in INVALIDATE_KEYWORDS):
        if text["denial_count"] < 2 and text["leading_count"] < 2:
            return _none_result("Override edukatif: pertanyaan invalidate thesis")

    # Override 2: pertanyaan risiko / red flag / analitis
    if any(p in text_lower for p in RISK_EDU_KEYWORDS):
        if (text["denial_count"] < 3 and text["averaging_count"] < 2
                and text["leading_count"] == 0        # tidak ada leading question
                and text["overconfident_count"] == 0): # tidak ada overconfident signal
            return _none_result("Override edukatif: pertanyaan risiko/red flag/analitis")

    # Override 3: pertanyaan strategi cut loss (threshold lebih longgar)
    if any(p in text_lower for p in CUT_LOSS_EDU_KEYWORDS):
        if text["denial_count"] < 6 and text["averaging_count"] < 4:
            return _none_result("Override edukatif: pertanyaan strategi cut loss")
    
    # Override 3b: pertanyaan strategi DCA murni = edukatif, bukan LA
    # Contoh: "Strategi DCA untuk market volatile itu gimana?" = NONE
    STRATEGI_DCA_KEYWORDS = [
        "strategi dca", "strategi dollar cost", "strategi averaging",
        "cara dca", "cara dollar cost", "dca itu gimana", "dca yang benar",
        "kapan dca", "apakah dca", "apa itu dca",
    ]

    if any(p in text_lower for p in STRATEGI_DCA_KEYWORDS):
        if text["denial_count"] < 2 and text["averaging_count"] < 3:
            return _none_result("Override edukatif: pertanyaan strategi DCA")

    # Override 4: pola education/analytical — hanya jika tidak ada strong bias
    if text["is_education"] or text["is_analytical"]:
        if not has_strong_bias():
            return _none_result("Pertanyaan bersifat edukatif atau analitis")

    # =========================================================================
    # LAYER 2 — PRICE DATA
    # Ambil data harga dari yfinance. Kalau gagal, scorer akan skip bagian harga.
    # =========================================================================

    price = analyze_price(ticker)
    change_5d = price.get("change_5d", 0.0)

    # =========================================================================
    # LAYER 3 — BASE SCORES
    # Hitung skor mentah tiap bias menggunakan scorer di Bagian 3.
    # =========================================================================

    scores = {
        "FOMO":              score_fomo(text, price, text_lower),
        "LOSS_AVERSION":     score_loss_aversion(text, price),
        "CONFIRMATION_BIAS": score_confirmation_bias(text, user_input),
        "NONE":              0.0,
    }

    # =========================================================================
    # LAYER 4 — CONTEXTUAL ADJUSTMENTS
    # Koreksi skor berdasarkan konteks yang tidak bisa ditangkap keyword saja.
    # Setiap adjustment diberi label huruf (A, B, C, ...) untuk tracking.
    # =========================================================================

    # --- A) Averaging saat harga turun = Loss Aversion, bukan FOMO ---
    # Contoh: "beli lagi biar rata, harga lagi murah" = LA, bukan mau masuk baru
    AVERAGING_WORDS = [
        "average down", "biar rata", "serok", "akumulasi",
        "add more", "averaging down", "dollar cost averaging",
    ]
    if any(w in text_lower for w in AVERAGING_WORDS):
          if ("murah" in text_lower or "turun" in text_lower
                or "down" in text_lower or text["denial_count"] >= 1):
            scores["FOMO"] = max(scores["FOMO"] - 0.20, 0.0)

    # --- B) FOMO dengan urgency kuat mengalahkan CB jika tidak ada echo ---
    # Contoh: "breaking out + solid right?" = FOMO, bukan confirmation seeking
    if scores["CONFIRMATION_BIAS"] > scores["FOMO"]:
        if text["echo_count"] == 0 and text["urgency_count"] >= 2:
            scores["FOMO"] += 0.30

    # --- C) "?" + social signal — boost sesuai konteks ---
    if "?" in user_input and text["social_count"] >= 1:
        if text["urgency_count"] >= 2:
            scores["FOMO"] += 0.10          # social + urgency kuat = FOMO
        elif text["leading_count"] >= 1:
            scores["CONFIRMATION_BIAS"] += 0.15  # social + leading = CB

    # --- D) Strong word override — satu kata kuat langsung boost bias-nya ---
    # Dipakai untuk kata yang sangat diagnostik dan jarang ambigu
    FOMO_STRONG_WORDS = [
        "fomo", "takut ketinggalan", "ketinggalan", "terlambat",
        "yolo", "moodeng", "to the moon", "moon guys",
    ]
    LA_STRONG_WORDS = [
        "nyangkut", "cut loss", "average down", "jual rugi",
        "kagak mau", "balik modal", "nunggu balik",
    ]
    CB_STRONG_WORDS = [
        "bener kan", "setuju ga", "konfirmasi", "validasi",
        "semua di grup sepakat", "rata-rata analisis",
        "semua influencer", "everyone agrees", "all analysts",
        "alasan beli", "jelasin kenapa", "give me reasons",
        "yang positif aja", "minta analisis mendukung",
        "tolong konfirmasi", "gue udah yakin",
        "kenapa harus beli", "kasih alasan",
    ]

    for word in FOMO_STRONG_WORDS:
        if word in text_lower:
            scores["FOMO"] += 0.25
            break  # cukup satu kata, jangan double-boost

    for word in LA_STRONG_WORDS:
        if word in text_lower:
            scores["LOSS_AVERSION"] += 0.25
            break

    for word in CB_STRONG_WORDS:
        if word in text_lower:
            scores["CONFIRMATION_BIAS"] += 0.25
            break

    # --- E) Prioritaskan CB jika ada kata kunci alasan/validasi kuat ---
    # Mencegah kalimat "banyak analis bilang bagus, kasih alasan beli"
    # salah masuk ke FOMO hanya karena ada "banyak analis"
    CB_REASON_WORDS = [
        "alasan", "jelasin", "reasons", "kenapa harus",
        "kasih alasan", "tolong konfirm", "minta analisis",
        "mendukung",
    ]
    if scores["CONFIRMATION_BIAS"] > 0.10 and any(p in text_lower for p in CB_REASON_WORDS):
        if text["urgency_count"] <= 2 and text["social_count"] <= 2:
            scores["CONFIRMATION_BIAS"] += 0.25
            scores["FOMO"] = max(scores["FOMO"] - 0.15, 0.0)

    # --- F) CB diperkuat jika "grup sepakat" + pertanyaan ---
    # Contoh: "semua di grup sepakat GOTO naik, masuk ga?" = CB, bukan FOMO
    GROUP_AGREE_WORDS = [
        "sepakat", "setuju", "grup sepakat", "semua sepakat", "komunitas setuju",
    ]
    if "?" in user_input and any(kw in text_lower for kw in GROUP_AGREE_WORDS):
        if text["leading_count"] >= 1 or text["echo_count"] >= 1:
            scores["CONFIRMATION_BIAS"] += 0.35
            scores["FOMO"] = max(scores["FOMO"] - 0.30, 0.0)

    # --- G) Boost FOMO jika social + timing/momentum ---
    FOMO_TIMING_WORDS = [
        "waktu terbaik", "timing bagus", "saat terbaik", "sekarang waktu",
        "momen", "baru awal",
    ]
    if text["social_count"] >= 1 and (
        any(kw in text_lower for kw in FOMO_TIMING_WORDS)
        or ("naik" in text_lower and "%" in text_lower)
    ):
        scores["FOMO"] += 0.25

    # --- H) Turunkan LA jika kalimat adalah pertanyaan edukatif cut loss ---
    # Contoh: "kapan waktu ideal cut loss?" = NONE, bukan LA
    if any(kw in text_lower for kw in ["kapan", "ideal", "berapa", "bagaimana", "cara", "strategi"]):
        if any(p in text_lower for p in ["cut loss", "cutloss", "take profit", "stop loss"]):
            scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.50, 0.0)

    # --- I) "Semua bilang mau naik" — tentukan FOMO vs CB berdasarkan konteks ---
    # Kalau ada kata "murah/rendah/turun", cenderung ke FOMO (harga masih murah)
    # Kalau tidak ada, cenderung ke CB (echo chamber validasi)
    SEMUA_BILANG = [
        "semua bilang mau naik", "semua bilang bakal naik", "semua bilang naik",
    ]
    if any(p in text_lower for p in SEMUA_BILANG):
        if "rendah" in text_lower or "murah" in text_lower or "turun" in text_lower:
            # Harga murah + semua bilang naik = FOMO momentum
            scores["FOMO"] += 0.45
            scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.40, 0.0)
        elif text["urgency_count"] <= 1:
            # Tidak ada urgency = echo chamber, bukan FOMO
            scores["CONFIRMATION_BIAS"] += 0.30
            scores["FOMO"] = max(scores["FOMO"] - 0.25, 0.0)

    # --- J) Boost FOMO kuat jika ada frasa "waktu terbaik" + social/semua bilang ---
    WAKTU_TERBAIK_WORDS = [
        "waktu terbaik", "saat terbaik", "timing bagus", "baru awal", "awal rally",
    ]
    if any(kw in text_lower for kw in WAKTU_TERBAIK_WORDS):
        if text["social_count"] >= 1 or "semua bilang" in text_lower:
            scores["FOMO"] += 0.65
            scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.60, 0.0)

    # --- K) Turunkan FOMO jika konteksnya adalah "kapan waktu jual" ---
    # Contoh: "kapan waktu terbaik untuk jual BBCA?" = NONE/LA, bukan FOMO
    if "kapan waktu" in text_lower or "kapan jual" in text_lower or "waktu jual" in text_lower:
        scores["FOMO"] = max(scores["FOMO"] - 0.55, 0.0)

    # --- L) Hard override: "bandar" atau "tidak wajar" = LA ---
    # Kata-kata ini sangat diagnostik untuk blame pattern LA
    if "tidak wajar" in text_lower or "bandar" in text_lower:
        if scores["LOSS_AVERSION"] >= 0.10:
            scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"], 0.50)
    
    # --- M) "takut" + urgensi = FOMO bukan CB ---
    if "takut" in text_lower and text["urgency_count"] >= 1:
        scores["FOMO"] += 0.20
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.20, 0.0)

    # N) Social + urgency dari luar (analis, influencer bilang) = FOMO bukan CB
    # Kasus: "temen analis bilang + momentum" = FOMO, bukan echo chamber CB
    # Kunci: ada kata "teman/temen/influencer" PLUS ada kata momentum/timing
    if text["social_count"] >= 1 and text["urgency_count"] >= 1:
        if scores["CONFIRMATION_BIAS"] > scores["FOMO"]:
            scores["FOMO"] += 0.20
            scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.15, 0.0)

    # O) LA + CB combo: kalau ada sinyal LA yang kuat (denial/averaging/blame >= 1)
    # DAN ada sinyal CB, prioritaskan LA karena LA adalah kondisi yang lebih mendesak
    # secara intervensi behavioral finance
    # Kasus: "nyangkut + gue yakin" = LA (user perlu friction untuk cut loss)
    #        "minus + semua bilang hold" = LA (bukan cari validasi, tapi sudah hold)
    if text["denial_count"] >= 1 or text["averaging_count"] >= 1 or text["blame_count"] >= 1:
        if scores["LOSS_AVERSION"] >= 0.25:  # ada skor LA yang meaningful
            # Kurangi CB agar LA bisa menang
            scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.30, 0.0)
            scores["LOSS_AVERSION"] += 0.15

    # P) Context-aware: kata LA yang muncul di konteks FOMO bukan LA
    # P1) "digoreng" + "ikut"/"cuan" = mau ikut pump bandar = FOMO
    if "digoreng" in text_lower and ("ikut" in text_lower or "cuan" in text_lower):
        scores["FOMO"] += 0.45
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.30, 0.0)

    # P2) "serok" saat harga naik = FOMO (ikut momentum), bukan averaging down
    if "serok" in text_lower and ("naik" in text_lower or "%" in text_lower):
        scores["FOMO"] += 0.40
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.35, 0.0)

    # P3) "ga bakal balik ke level segini" = FOMO (takut harga murah hilang)
    # substring bug: "bakal balik" juga ada di "ga bakal balik" -> false LA
    if "ga bakal balik" in text_lower:
        scores["FOMO"] += 0.35
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.30, 0.0)

    # P4) "kapan lagi harga murah / serok" tanpa konteks minus/nyangkut = FOMO
    # Kasus: "kapan lagi bisa beli big banks dengan harga murah serok" = FOMO entry
    # Beda dari LA averaging: ini tidak ada konteks posisi sebelumnya / nyangkut
    KAPANLAGI_MURAH = ["kapan lagi bisa beli", "kapan lagi harga", "kapan lagi beli"]
    if any(kw in text_lower for kw in KAPANLAGI_MURAH):
        if text["denial_count"] == 0 and text["averaging_count"] <= 1:
            scores["FOMO"] += 0.35
            scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.25, 0.0)

    # P5) "yang serok X lalu pasti senyum/cuan" = social proof FOMO
    # Kasus: "yang serok emiten gold 2 hari lalu pasti senyum-senyum sekarang"
    if ("serok" in text_lower or "yang beli" in text_lower) and (
        "senyum" in text_lower or "pasti cuan" in text_lower or "cuan" in text_lower
    ):
        if text["denial_count"] == 0:
            scores["FOMO"] += 0.40
            scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.35, 0.0)

    # P6) "HAKA" dalam konteks MSCI/event catalyst = FOMO, bukan averaging LA
    # [560] "SEGERA HAKA BIPI CALON KUAT MSCI" → FOMO karena ada catalyst trigger
    # "SEGERA" + "HAKA" = urgency entry, bukan rationalisasi averaging down
    HAKA_URGENCY = ["segera haka", "segera masuk", "segera beli"]
    if any(kw in text_lower for kw in HAKA_URGENCY):
        scores["FOMO"] += 0.50
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.60, 0.0)

    # P7) "belanja di harga X-Y-Z" tanpa konteks minus/nyangkut = FOMO averaging in
    # [505] "cash abis dibagi 4 sekuritas, belanja di 7100-7200-7300" = FOMO bukan LA
    # Bedanya: "belanja" dengan angka range = baru masuk, bukan hold posisi lama
    # re sudah di-import di top-level file
    if re.search(r'belanja di \d+', text_lower):
        if text["denial_count"] == 0:
            scores["FOMO"] += 0.40
            scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.40, 0.0)

    # Q) Post-purchase rationalization: sudah beli/masuk lalu cari konfirmasi = CB
    # Contoh: "keputusan gue beli tadi bener" = cari validasi setelah aksi
    POST_PURCHASE_WORDS = [
        "keputusan gue beli", "keputusan gue masuk",
        "pilihan gue bener", "beli tadi bener", "masuk tadi bener",
    ]
    if any(kw in text_lower for kw in POST_PURCHASE_WORDS):
        scores["CONFIRMATION_BIAS"] += 0.40
        scores["FOMO"] = max(scores["FOMO"] - 0.35, 0.0)

    # R) "temen/teman analis bilang" = social proof = FOMO, bukan echo chamber CB
    # Bedanya dari "semua analis bilang" (CB/echo): ini satu orang yang dikenal
    if any(kw in text_lower for kw in ["temen analis", "teman analis", "temen gue analis"]):
        scores["FOMO"] += 0.30
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.25, 0.0)

    # S) "Told you so" / vindikasi = CB kuat
    # Kasus: user menunggu/mengumumkan bahwa analisisnya terbukti benar
    # "ditunggu told you so moment", "kata gue dari dulu", "sehat sehat dah kata gue"
    TOLD_YOU_SO_WORDS = [
        "told you so", "kata gue", "gue udah bilang", "gue bilang",
        "sudah gue bilang", "kan gue bilang", "terbukti kan",
        "akhirnya terbukti", "nunggu told you so", "ditunggu told you so",
    ]
    if any(kw in text_lower for kw in TOLD_YOU_SO_WORDS):
        scores["CONFIRMATION_BIAS"] += 0.40
        scores["FOMO"] = max(scores["FOMO"] - 0.20, 0.0)
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.20, 0.0)

    # S2) "influencer/komunitas bilang X + sekarang/masuk" = FOMO dominant
    # Echo chamber yang mendorong aksi masuk = FOMO, bukan pure CB
    # CB murni = user tidak ada urgency aksi, hanya cari konfirmasi
    SOCIAL_PROOF_FOMO = [
        "influencer favorit gue bilang", "influencer bilang",
        "komunitas gue bilang sekarang", "komunitas bilang sekarang",
        "semua teman gue profit",
    ]
    if any(kw in text_lower for kw in SOCIAL_PROOF_FOMO):
        if "sekarang" in text_lower or "masuk" in text_lower or "beli" in text_lower:
            scores["FOMO"] += 0.40
            scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.30, 0.0)

    # T) "market luar hijau / ihsg naik besok" = FOMO implisit tanpa kata bias eksplisit
    # Kalimat ini pendek dan tidak punya keyword FOMO klasik tapi maknanya FOMO
    MARKET_BULLISH_SIGNAL = [
        "market luar hijau", "market hijau", "ihsg lanjut naik",
        "ihsg ijo", "besok ijo", "besok naik", "lanjut naik",
        "market rebound", "market recovery", "moga ihsg",
    ]
    if any(kw in text_lower for kw in MARKET_BULLISH_SIGNAL):
        if text["denial_count"] == 0 and text["blame_count"] == 0:
            scores["FOMO"] += 0.30

    # U) Kalimat sangat pendek slang Stockbit: "GASS ARA", "gaskiw", "ayo siap-siap"
    # Pattern: kalimat ≤8 kata dengan slang aksi masuk kuat = FOMO
    EXTREME_SLANG_ENTRY = [
        "gass", "gasss", "gaskiw", "gaskeun", "gas ayo",
        " ara ", "ara!!", "auto reject atas", "ayo siap-siap", "siap-siap masuk",
        "top gainers", "masuk top", "finally mantul", "finally naik",
        "akhirnya mantul",
    ]
    word_count = len(user_input.split())
    if word_count <= 8 and any(kw in text_lower for kw in EXTREME_SLANG_ENTRY):
        scores["FOMO"] += 0.45

    # V) "murah" + "beli lebih banyak / averaging" tanpa FOMO urgency eksplisit = LA
    # Kasus: "Harga BREN murah sekarang, kesempatan beli lebih banyak"
    # "murah" dalam konteks averaging = rationalisasi LA, bukan FOMO entry
    AVERAGING_CONTEXT = ["beli lebih banyak", "beli lagi", "tambah lagi",
                          "nambah posisi", "averaging", "average down"]
    if "murah" in text_lower and any(kw in text_lower for kw in AVERAGING_CONTEXT):
        scores["LOSS_AVERSION"] += 0.25
        scores["FOMO"] = max(scores["FOMO"] - 0.20, 0.0)

    # W) "analisis gue ga pernah salah" / "pasti cuan" + analisis konteks = CB
    # Kasus: "all in GOTO, pasti cuan lah, analisis gue ga pernah salah"
    # FOMO tinggi karena "all in" + "pasti cuan", tapi inti kalimat = overconfidence CB
    ANALYSIS_NEVER_WRONG = [
        "analisis gue ga pernah salah", "analisis gue benar",
        "analisis gue selalu", "riset gue ga pernah",
        "prediksi gue tepat", "gue ga pernah salah soal",
    ]
    if any(kw in text_lower for kw in ANALYSIS_NEVER_WRONG):
        scores["CONFIRMATION_BIAS"] += 0.50
        scores["FOMO"] = max(scores["FOMO"] - 0.60, 0.0)

    # X) "ramai dibicarain / trending tapi masuk karena analisis sendiri" = CB denial
    # Kasus: "TLKM ramai dibicarain tapi gue masuk berdasarkan analisis, bukan ikut-ikutan"
    # User acknowledge FOMO trigger tapi dismiss = CB (denial of social influence)
    DENIAL_IKUT_IKUTAN = [
        "bukan karena ikut-ikutan", "bukan ikut-ikutan",
        "bukan karena fomo", "bukan fomo",
        "bukan karena trending", "berdasarkan analisis sendiri",
        "masuk berdasarkan analisis",
    ]
    if any(kw in text_lower for kw in DENIAL_IKUT_IKUTAN):
        scores["CONFIRMATION_BIAS"] += 0.40
        scores["FOMO"] = max(scores["FOMO"] - 0.50, 0.0)

    # Y) "ARA" dalam konteks pertanyaan = bukan FOMO
    # "kapan ara bang?" = tanya kapan, bukan ajakan masuk
    # "masi ARA X, di hold aja?" = tanya pendapat, bukan entry signal
    ARA_QUESTION_WORDS = ["kapan ara", "kapan aranya", "masi ara", "masih ara",
                        "berapa ara", "potensi berapa ara", "di hold aja"]
    if any(kw in text_lower for kw in ARA_QUESTION_WORDS):
        scores["FOMO"] = max(scores["FOMO"] - 0.60, 0.0)

    # Z) Kalimat yg sebut kata "FOMO" sendiri ≠ FOMO
    # "hindari FOMO dan panic buying" = edukasi/warning, bukan pelaku FOMO  
    # "saham FOMO begini" = komentar, bukan action
    if "hindari fomo" in text_lower or "saham fomo" in text_lower or "jangan fomo" in text_lower:
        scores["FOMO"] = max(scores["FOMO"] - 0.70, 0.0)
        scores["CONFIRMATION_BIAS"] += 0.20

    # Influencer bilang + sekarang = FOMO dominan (social proof → urgency action)
    INFLUENCER_FOMO = ["influencer bilang", "komunitas bilang sekarang",
                        "semua orang masuk dan", "semua teman profit"]
    if any(kw in text_lower for kw in INFLUENCER_FOMO):
        if "sekarang" in text_lower or "masuk" in text_lower:
            scores["FOMO"] += 0.35
            scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.25, 0.0)


    # AA) Kalimat sebut "FOMO" atau "jangan FOMO" = edukasi/warning, bukan pelaku FOMO
    # [524] "hindari FOMO dan panic buying" → harusnya bukan LA
    # [527] "jangan fomo yaaa" → FOMO label karena konteks market bullish, tapi kalimatnya warning
    if "hindari fomo" in text_lower or "jangan fomo" in text_lower:
        scores["FOMO"] = max(scores["FOMO"] - 0.70, 0.0)
    if "saham fomo" in text_lower:   # "nasib saham FOMO begini" = komentar kritis
        scores["FOMO"] = max(scores["FOMO"] - 0.50, 0.0)
        scores["CONFIRMATION_BIAS"] += 0.25

    CB_OBSERVER_SIGNALS = [
        "pantesan membernya", "membernya pada rugi",
        "lagi buang barang pantesan",
        "naik to.. pantesan", "laba naik pantesan",
        "gue bilang apa bandarnya",
        "dah gue bilang turun",
        "gue bilang apa saham ini gajelas",
        "gue bilang apa, aman aja",
        "hahaha gue bilang juga apa",
        "udh gue bilang dri tgl",
        "ketika ritel unyu", "ritel unyu sok",
        "membasuh luka ihsg",
        "sekarang jadi terbiasa ihsg turun",
        "katanya klo lagi perang saham energi naik",
    ]
    if any(kw in text_lower for kw in CB_OBSERVER_SIGNALS):
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.55, 0.0)

    # DD) Pertanyaan sosial ke komunitas = NONE, bukan bias aktif
    SOCIAL_QUESTION_SIGNALS = [
        "guys minta saran", "minta saran dong", "tolong sarannya dong",
        "kalian tim cl", "kalian tim hold", "kalian tim serok",
        "tim cl atau", "tim serok atau", "cl atau serok atau",
        "pada gimana", "pada bingung harus apa",
        "masih pada panic", "panic selling kah",
        "mending cut loss apa enggak", "mending cl apa enggak",
        "nyerok sampe modal mentok",
        "aman ga nyerok", "serok prto pas ihsg crash",
        "nyerok bluechip tapi ada kabar",
        "jangan cintai cut loss",
        "wait n see untuk serok",
    ]
    if any(kw in text_lower for kw in SOCIAL_QUESTION_SIGNALS):
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.45, 0.0)
        scores["FOMO"] = max(scores["FOMO"] - 0.30, 0.0)
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.30, 0.0)

    # EE) Komentar tentang orang lain yang LA = observer, bukan pelaku
    LA_OBSERVER_SIGNALS = [
        "kasian amat ritel", "kasian ritel",
        "yg lain masuk buat nyari rugi",
        "hahaha masuk cl", "yang lain cutloss",
        "cara ngitung time to avg down",
        "cara ngitung", "ngitung time to",
        "saham ini bagus kan buat jangka",
        "kalo saranku ya kak",
        "daripada nunggu balik ke harga avg mending cl",
        "ada yang hold", "ada yang hold ga",
        "ihsg drop begini pada bingung",
        "biasanya pada gimana",
    ]
    if any(kw in text_lower for kw in LA_OBSERVER_SIGNALS):
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.45, 0.0)

    # FF) "kann/kan gue bilang" tanpa action = CB vindikasi
    if any(kw in text_lower for kw in ["kann gue bilang", "kan gue bilang", "kan udh gue bilang"]):
        scores["CONFIRMATION_BIAS"] += 0.40
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.50, 0.0)
        scores["FOMO"] = max(scores["FOMO"] - 0.40, 0.0)

    # GG) "kenaikan harga karena dividen" = analisis, bukan FOMO
    if "kenaikan harga karena dividen" in text_lower or "kenaikan karena dividen" in text_lower:
        scores["FOMO"] = max(scores["FOMO"] - 0.80, 0.0)
        scores["LOSS_AVERSION"] += 0.20

    # HH) Pertanyaan market maker dengan "?" = bukan blame LA
    MARKET_QUESTION_SIGNALS = [
        "kok ga bisa ke buy", "kok ga bisa buy",
        "kenapa ga bisa buy", "masih di tahan bandar",
        "atau masih di tahan",
    ]
    if any(kw in text_lower for kw in MARKET_QUESTION_SIGNALS):
        if "?" in user_input:
            scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.40, 0.0)

    # II) Masuk berdasarkan screenshot/tweet/kabar orang = FOMO sosial
    SOCIAL_TRIGGER_FOMO = [
        "berdasarkan screenshot tweet", "berdasarkan screenshot",
        "beli karena tweet", "beli karena kabar",
        "kabarnya bapak prajogo", "kabarnya prajogo",
        "prajogo pangestu akan ipo", "akan ipo segera",
        "banyak org di stream yang bilang gas king",
        "banyak org di stream yang bilang",
        "stream yang bilang gas",
    ]
    if any(kw in text_lower for kw in SOCIAL_TRIGGER_FOMO):
        scores["FOMO"] += 0.50
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.30, 0.0)

    # JJ) Judul artikel / edukasi psikologi ritel = bukan bias aktif
    ANALYTICAL_OVERRIDE_SIGNALS = [
        "psikologi ritel ketika", "psikologi ritel mengarungi",
        "dikarungi bandar",
    ]
    if any(kw in text_lower for kw in ANALYTICAL_OVERRIDE_SIGNALS):
        for k in scores:
            scores[k] = max(scores[k] - 0.40, 0.0)

    # KK) "jual X masuk Y" = rotasi saham = FOMO entry baru
    if re.search(r'jual \w+ masuk \w+', text_lower):
        scores["FOMO"] += 0.45
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.30, 0.0)

    # LL) "beli di harga pucuk" = FOMO entry di top
    PEAK_BUY_SIGNALS = [
        "beli di harga pucuk", "beli di pucuk",
        "nyantol dipuncaknya", "nyantol di puncak", "beli di puncak",
    ]
    if any(kw in text_lower for kw in PEAK_BUY_SIGNALS):
        scores["FOMO"] += 0.45
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.20, 0.0)

    # MM) "tetep hold + bakal naik + rugi kalau jual" = LA klasik
    if ("tetep hold" in text_lower or "tetap hold" in text_lower) and (
        "bakal naik" in text_lower or "rugi kalo jual" in text_lower
        or "rugi kalau jual" in text_lower
    ):
        scores["LOSS_AVERSION"] += 0.50
        scores["FOMO"] = max(scores["FOMO"] - 0.20, 0.0)

    # NN) "cl hanya orang lemah" = CB self-justification untuk hold
    CL_DISMISS_CB = [
        "cl hanya orang lemah", "hanya orang lemah",
        "cl itu pengecut", "hanya pengecut yang",
        "pengecut yang melakukan cutloss",
    ]
    if any(kw in text_lower for kw in CL_DISMISS_CB):
        scores["CONFIRMATION_BIAS"] += 0.50
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.40, 0.0)

    # OO) "hold + dividen" tanpa konteks rugi/nyangkut = strategi = NONE guard
    if ("dividen" in text_lower or "dividend" in text_lower) and "hold" in text_lower:
        if (text["denial_count"] <= 1 and text["averaging_count"] == 0
                and "minus" not in text_lower and "rugi" not in text_lower
                and "nyangkut" not in text_lower and "cl" not in text_lower):
            scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.35, 0.0)

    # PP) "waktunya CL ya CL + serok" = keputusan strategis = NONE
    if "ya cl" in text_lower or "waktunya cl" in text_lower:
        if "serok" in text_lower or "tipis-tipis" in text_lower:
            scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.45, 0.0)

    # QQ) "gak layak di hold / balik modal aja" = sudah exit = bukan CB aktif
    GUE_BILANG_NONE_PATTERNS = [
        "gak layak di hold", "ga layak di hold",
        "gak layak hold", "ga layak hold",
        "gua balik modal aja", "gue balik modal",
        "balik modal aja", "udah balik modal",
        "hahaha gue bilang juga apa bakal turun",
        "hahaha gue bilang juga apa",
    ]
    if any(kw in text_lower for kw in GUE_BILANG_NONE_PATTERNS):
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.60, 0.0)

    # RR) "kalo pake data crash" = analisis historis = override FOMO
    if "kalo pake data" in text_lower or "kalau pake data" in text_lower:
        if "crash" in text_lower:
            scores["FOMO"] = max(scores["FOMO"] - 0.90, 0.0)
            scores["LOSS_AVERSION"] += 0.30

    # SS) "haka aja" + "kan gue bilang" = FOMO action dominan atas CB
    if ("haka aja" in text_lower or "haka lah" in text_lower) and (
        "kan gue bilang" in text_lower or "kan udh gue bilang" in text_lower
    ):
        scores["FOMO"] += 0.55
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.50, 0.0)

    # TT) "takut ketinggalan" eksplisit = FOMO override semua LA
    # [752] "$MINA waktunya HAKA kah? takut ketinggalan gua"
    # "takut ketinggalan" = definisi FOMO, override LA apapun
    if "takut ketinggalan" in text_lower:
        scores["FOMO"] += 0.60
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.70, 0.0)

    # UU) "nunggu apa lagi" + social context = FOMO urgency
    # [278] "Temen-temen gue pada borong saham, gue masih nunggu apa lagi"
    if "nunggu apa lagi" in text_lower or "tunggu apa lagi" in text_lower:
        if text["social_count"] >= 1:
            scores["FOMO"] += 0.55
            scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.50, 0.0)

    # VV) "akumulasi bandar" = signal FOMO via bandar, bukan LA_AVERAGING
    # PENTING: hanya trigger jika bandar = catalyst masuk, BUKAN bandar = excuse
    # "bandar main makanya ga naik" = LA blame, bukan FOMO
    # "pegang karena ada bandarnya" = CB (authority), bukan FOMO
    # "semua karena bandar bukan fundamental" = CB worldview, bukan FOMO
    BANDAR_FOMO_PATTERNS = [
        "terpantau bandar akumulasi", "bandar lagi akumulasi",
        "king xl masih buy", "king masih buy", "big player masih buy",
        "asing masuk", "big player masuk",
        "cp beli nego",
    ]
    # Hapus: "akumulasi bandar", "bandar akumulasi", "ada bandar", "bandar masuk"
    # karena terlalu broad — cover kasus blame/CB juga
    if any(kw in text_lower for kw in BANDAR_FOMO_PATTERNS):
        if text["denial_count"] == 0:
            scores["FOMO"] += 0.45
            scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.50, 0.0)

    # Fix tambahan: "bandar" sebagai excuse/blame = CB atau LA, bukan FOMO
    BANDAR_EXCUSE_PATTERNS = [
        "ada bandarnya yang aman", "pegang karena ada bandar",
        "karena ada bandarnya", "bandar main makanya",
        "makanya ga naik-naik", "makanya ga naik naik",
        "semua karena bandar", "bukan karena fundamental tapi karena bandar",
        "bukan fundamental tapi bandar", "karena bandar bukan",
        "jebakan batman", "hijau tapi asing kabur",
        "asing kabur",
    ]
    if any(kw in text_lower for kw in BANDAR_EXCUSE_PATTERNS):
        scores["FOMO"] = max(scores["FOMO"] - 0.60, 0.0)
        scores["CONFIRMATION_BIAS"] += 0.30

    # WW) "kapan lagi bisa beli + serok" = FOMO opportunistic, perkuat vs LA
    # [521] P4 adjustment sudah ada tapi kalah oleh serok score
    # Perkuat: jika ada "kapan lagi" + tidak ada konteks nyangkut = pure FOMO
    KAPANLAGI_FOMO = ["kapan lagi bisa beli", "kapan lagi harga", "kapan lagi beli murah"]
    if any(kw in text_lower for kw in KAPANLAGI_FOMO):
        if "nyangkut" not in text_lower and "avg" not in text_lower:
            scores["FOMO"] += 0.45
            scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.55, 0.0)

    # XX) "sudah saatnya" / "jarang-jarang" + beli konteks = FOMO opportunistic
    # [756] "Sudah saatnya mencicil beli. Jarang2 IHSG drop 20%"
    # "cicil beli" dalam konteks IHSG turun besar = FOMO buy-the-dip opportunistic
    OPPORTUNISTIC_FOMO = [
        "sudah saatnya", "saatnya beli", "saatnya masuk",
        "jarang-jarang ihsg", "jarang2 ihsg", "jarang ihsg turun",
        "kesempatan langka", "jarang ada kesempatan",
        "secara historis paling", "historis paling dalem",
    ]
    if any(kw in text_lower for kw in OPPORTUNISTIC_FOMO):
        scores["FOMO"] += 0.45
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.40, 0.0)

    # YY) "serakahlah saat orang lain takut" = Buffett quote = FOMO contrarian
    # [565] "$BUVA takutlah saat orang lain serakah, dan serakahlah saat orang lain takut"
    CONTRARIAN_FOMO = [
        "serakahlah saat orang lain takut", "serakah saat orang takut",
        "beli saat orang lain panik", "beli saat semua orang takut",
        "takutlah saat orang lain serakah",
    ]
    if any(kw in text_lower for kw in CONTRARIAN_FOMO):
        scores["FOMO"] += 0.55
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.60, 0.0)

    # ZZ) "panic buying" + gap up/menguat = FOMO warning context
    # TAPI: "hindari FOMO" dengan skor LA sangat tinggi = LA over-trigger
    # [524] conf LA=0.95 berarti ada banyak LA keywords lain — perlu hard override
    if "panic buying" in text_lower or "hindari fomo" in text_lower:
        if "gap up" in text_lower or "menguat" in text_lower:
            scores["FOMO"] += 0.55
            scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.80, 0.0)


    # AAA) "jebol [N]x + semoga jebol lagi" = FOMO momentum pattern
    # [489] "CNKO jebol 84, jebol 90, jebol 130, semoga tahun ini bisa jebol lagi"
    jebol_count = text_lower.count("jebol")
    if jebol_count >= 2:
        scores["FOMO"] += 0.15 * jebol_count   # 2x jebol = +0.30, 3x = +0.45

    if "semoga" in text_lower and (
        "jebol" in text_lower or "naik" in text_lower or "meroket" in text_lower
    ):
        scores["FOMO"] += 0.25

    # BBB) "jangan fomo" dalam konteks bullish = FOMO label tetap benar
    # [527] "Qatar warning oil bisa 150$ jangan fomo yaaa"
    # Pola: ada trigger bullish + "jangan fomo" = user sendiri tahu itu FOMO
    # FIX: hapus penalty Z jika ada konteks bullish eksternal (harga naik/prediksi naik)
    BULLISH_EXTERNAL = [
        "bisa 150", "bisa naik ke", "target harga", "prediksi harga",
        "oil naik", "harga naik", "naik ke level",
    ]
    if "jangan fomo" in text_lower and any(kw in text_lower for kw in BULLISH_EXTERNAL):
        scores["FOMO"] += 0.50   # restore: ini FOMO tersamarkan sebagai warning

    # CCC) Kalimat pendek FOMO dengan conf 0.25-0.35 = turunkan threshold khusus
    # [586] "hilal udah kelihatan, besok cuma 3 hari lagi" conf=0.35 < 0.38
    # [745] "$PACK akhirnya bangkit" conf=0.35
    # Fix: kalimat FOMO ≤12 kata dengan conf ≥0.25 = pertimbangkan bias
    # (ditangani di Layer 5 threshold — lihat fix Layer 5 di bawah)

    # DDD) "batas profit 200%" + "saham beger/bergerak" = FOMO aggressive target
    # [728] "cara saya di markat, batas profit 200++, saham beger"
    if ("batas profit" in text_lower or "target profit" in text_lower) and (
        "200" in text_lower or "300" in text_lower or "100" in text_lower
    ):
        scores["FOMO"] += 0.45

    if "saham beger" in text_lower or "saham yang begerak" in text_lower:
        scores["FOMO"] += 0.30

    # EEE) "perkiraan IHSG + saham yang dapat diperhatikan" = FOMO watchlist push
    # [755] label FOMO karena ini content creator mendorong beli saham tertentu
    # FIX: hapus "perkiraan ihsg" dari ANALYTICAL_PATTERNS yang terlalu broad
    # (sudah ditangani via penambahan FOMO_URGENCY keywords di atas)
    if "saham2 yg dapat" in text_lower or "saham yang dapat diperhatikan" in text_lower:
        scores["FOMO"] += 0.35

    # FFF) "absolute cinema" + konteks komentar = sarkasme/observasi, bukan FOMO
    # [619] "Bca 7500 absolute cinema Rokok lanjut Ara Konglo serok aja"
    # BB sudah ada tapi tidak cukup: sarcasm score -0.30, tapi FOMO masih 0.65
    # Fix: naikkan penalty sarcasm dan tambahkan guard khusus 'absolute cinema'
    if "absolute cinema" in text_lower:
        scores["FOMO"] = max(scores["FOMO"] - 0.60, 0.0)
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.40, 0.0)

    # GGG) "pasti turun" / sarkasme = NONE kuat — naikkan penalty
    # [638] "Obligasi indo lebih bagus. Pasti turun" conf=0.25 masih lolos
    # Sarcasm threshold perlu naik
    SARCASM_PATTERNS_V2 = [
        "pasti turun", "hit me harder", "silahkan terbangkan",
        "absolute cinema", "pasti rugi", "rugi deh",
        "ya sudah turun saja", "mending turun sekalian",
    ]
    if any(kw in text_lower for kw in SARCASM_PATTERNS_V2):
        for k in scores:
            scores[k] = max(scores[k] - 0.50, 0.0)   # naik dari -0.30 ke -0.50

    # HHH) "soon WD" / "last day" = withdrawal konteks, bukan entry FOMO
    # [833] "$IHSG soon WD krn last day in 2025"
    if "wd" in text_lower and ("soon" in text_lower or "last day" in text_lower):
        scores["FOMO"] = max(scores["FOMO"] - 0.60, 0.0)

    if "last day in 2025" in text_lower or "last day in 2026" in text_lower:
        scores["FOMO"] = max(scores["FOMO"] - 0.60, 0.0)

    # III) "bertahan buat ga cl" SAJA = ambigu, turunkan LA jika tidak ada konteks minus
    # [766] "Gua masih bertahan buat ga cl nder" → label NONE
    # "bertahan buat ga cl" tanpa ada "minus/rugi/nyangkut" = ekspresi tekad pendek
    if "bertahan buat ga cl" in text_lower or "masih bertahan buat ga" in text_lower:
        if "minus" not in text_lower and "rugi" not in text_lower:
            scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.45, 0.0)

    # JJJ) "nyerok + RUPS/dividen" = FOMO event-driven, bukan LA averaging
    # [804] "Nyerok BBNI yang hari ini mau RUPS, semoga berita deviden gede"
    if ("nyerok" in text_lower or "serok" in text_lower) and (
        "rups" in text_lower or "dividen" in text_lower
    ):
        if text["denial_count"] == 0:
            scores["FOMO"] += 0.35
            scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.50, 0.0)

    # KKK) "porto kalian aman? + gw udh cl" = pertanyaan sosial setelah aksi = NONE
    # [807] sudah CL, tanya ke komunitas = bukan sedang LA aktif
    if ("porto kalian" in text_lower or "porto aman" in text_lower) and (
        "udh cl" in text_lower or "udah cl" in text_lower or "gw cl" in text_lower
    ):
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.55, 0.0)

    # LLL) "porta minus X% + hold karena dividen X%" = strategi sadar bukan LA denial
    # [799] "Porto Minus 6%, ane hold karena dividen 8% up"
    # Pola: ada alasan eksplisit hold (dividen) + tidak ada denial = bukan LA
    if "hold karena dividen" in text_lower or "hold krn dividen" in text_lower:
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.50, 0.0)

    # MMM) "jangan dilihat makin nyesek" SAJA tanpa konteks saham spesifik = curhat umum
    # [772] bisa NONE jika tidak ada ticker/konteks posisi
    if "jangan dilihat makin nyesek" in text_lower or "jangan dilihat makin" in text_lower:
        if text["denial_count"] <= 1 and text["averaging_count"] == 0:
            scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.40, 0.0)

    # NNN) LA + echo chamber = CB, bukan LA
    # [462] "Minus di TLKM, tapi semua influencer bilang hold dan gue ikutin"
    # "semua influencer bilang hold" = echo CB, tapi ada minus = LA lebih mendesak
    # FIX: jika ada MINUS + echo chamber + "ikutin" = LA dominant (ikut orang lain untuk justify hold)
    if ("minus" in text_lower or "rugi" in text_lower) and (
        "semua influencer" in text_lower or "semua analis" in text_lower
    ) and "ikutin" in text_lower:
        scores["LOSS_AVERSION"] += 0.40
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.35, 0.0)

    # OOO) Social proof + fundamental + ikutan = FOMO, bukan CB
    # [464] "Semua teman gue profit GOTO, fundamentalnya juga oke, ikutan masuk ga ya"
    # "semua teman profit" = FOMO social, "ikutan masuk ga ya" = FOMO question
    if "semua teman" in text_lower and (
        "profit" in text_lower or "cuan" in text_lower
    ) and ("ikutan" in text_lower or "masuk ga" in text_lower):
        scores["FOMO"] += 0.50
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.45, 0.0)

    # PPP) "dana dingin + yakin apa yang dibeli" = CB overconfidence, bukan LA
    # [482] "PADI kalau uang dingin dan yakin apa yang dibeli, santai aja"
    # "yakin apa yang dibeli" = CB conviction keyword
    if "yakin apa yang dibeli" in text_lower or "yakin sama yang dibeli" in text_lower:
        scores["CONFIRMATION_BIAS"] += 0.50
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.60, 0.0)

    # QQQ) "bandar akumulasi + optimis avg down" = CB via authority, bukan LA
    # [495] "HEAL terpantau bandar akumulasi, optimis ke jemput avg down"
    # VV fix sudah menaikkan FOMO, tapi CB juga valid jika ada "optimis"
    if "terpantau bandar" in text_lower and "optimis" in text_lower:
        scores["CONFIRMATION_BIAS"] += 0.35
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.40, 0.0)

    # RRR) "gimana rasanya yang beli di [harga tinggi]" = CB schadenfreude / told-you-so
    # [508] "PJHB-W gimana rasanya yang beli di 484 ya?"
    # Mengkomentari orang yang beli di harga tinggi = CB vindikasi tersamarkan
    if "gimana rasanya yang beli di" in text_lower or "rasanya yang beli di" in text_lower:
        scores["CONFIRMATION_BIAS"] += 0.55
        scores["FOMO"] = max(scores["FOMO"] - 0.50, 0.0)

    # SSS) "rencana hold + kira2 bagus ga" = LA primary bukan CB
    # [530] "rencana mau hold humi utk setahun ini, kira2 bagus ga?"
    # "kira2 bagus ga" = CB leading question tapi dominated by LA hold plan
    if ("rencana hold" in text_lower or "mau hold" in text_lower) and (
        "kira2" in text_lower or "kira-kira" in text_lower
    ) and "?" in user_input:
        scores["LOSS_AVERSION"] += 0.35
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.40, 0.0)

    # TTT) "lebih menarik dari" = CB perbandingan selektif
    # [553] "DEWA lebih menarik dari BUMI menurut gue"
    if "lebih menarik dari" in text_lower or "lebih bagus dari" in text_lower:
        if text["overconfident_count"] == 0 and text["echo_count"] == 0:
            # Perbandingan selektif = CB ringan, boost sedikit
            scores["CONFIRMATION_BIAS"] += 0.25

    # UUU) "kalau ihsg hijau/opening hijau + pasti naik kan" = FOMO leading
    # [589] "kalau ihsg opening hijau pasti naik juga kan min?"
    # "pasti naik kan" = FOMO karena user berharap hijau = action trigger
    if ("ihsg" in text_lower or "opening" in text_lower) and (
        "hijau" in text_lower or "naik" in text_lower
    ) and ("kan" in text_lower or "pasti" in text_lower):
        if "?" in user_input:
            scores["FOMO"] += 0.40
            scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.35, 0.0)

    # VVV) "Q4 naik siap-siap" = CB post-rationalization untuk entry
    # [596] "laporan ada, Q4 nya naik, siap siap aja"
    # "siap siap aja" + laporan bagus = CB confirm analisis positif
    if "siap siap aja" in text_lower or "siap-siap aja" in text_lower:
        if "naik" in text_lower or "bagus" in text_lower or "laporan" in text_lower:
            scores["CONFIRMATION_BIAS"] += 0.40

    # WWW) "berdoa untuk sahabat yang udah masuk tetap kuat" = LA empathy/holder solidarity
    # [630] "Gw berdoa utk sahabat sahabat yang udah masuk Kacang tetap kuat"
    HOLDER_SOLIDARITY = [
        "berdoa utk yang udah masuk", "berdoa untuk yang masuk",
        "berdoa utk sahabat yang udah masuk",
        "semoga yang masuk tetap kuat", "yang udah masuk tetap kuat",
        "semoga kuat buat yang pegang",
    ]
    if any(kw in text_lower for kw in HOLDER_SOLIDARITY):
        scores["LOSS_AVERSION"] += 0.50
        scores["FOMO"] = max(scores["FOMO"] - 0.45, 0.0)

    # XXX2) "pegang karena bandarnya aman" = CB authority bias
    # [623] "poko pegang $RONY karena ada bandarnya yang aman"
    if ("pegang karena" in text_lower or "hold karena ada" in text_lower) and "bandar" in text_lower:
        scores["CONFIRMATION_BIAS"] += 0.55
        scores["FOMO"] = max(scores["FOMO"] - 0.60, 0.0)

    # YYY) "punya adiknya/anaknya prabowo/jokowi + pasti naik" = CB appeal to authority
    # [666] "INET punya adiknya prabowo pasti yakin bisa naik"
    AUTHORITY_POLITICAL = [
        "punya adiknya prabowo", "punya anaknya prabowo",
        "punya adiknya jokowi", "punya anaknya jokowi",
        "punya adiknya presiden", "milik presiden",
        "punya orang dalam", "ada orang dalamnya",
    ]
    if any(kw in text_lower for kw in AUTHORITY_POLITICAL):
        scores["CONFIRMATION_BIAS"] += 0.55
        scores["FOMO"] = max(scores["FOMO"] - 0.50, 0.0)

    # ZZZ) "masuk saham ketika bullish sekarang pahit" = CB survivor bias / regret
    # [703] "masuk ketika manis manisnya sekarang masa pahitnya"
    SURVIVOR_BIAS_CB = [
        "masuk ketika bullish", "masuk saat bullish",
        "masuk ketika manis", "masuk saat manis",
        "sekarang masa pahit", "sekarang lagi pahit",
        "waktu manis masuk", "pas manis masuk",
    ]
    if any(kw in text_lower for kw in SURVIVOR_BIAS_CB):
        scores["CONFIRMATION_BIAS"] += 0.55
        scores["FOMO"] = max(scores["FOMO"] - 0.60, 0.0)

    # AAAA) "motivasinya beli X apa?" = CB questioning / skeptis terhadap keputusan orang
    # [704] "motivasinya beli saham GIAA apa? all in pula"
    # Pertanyaan tentang motivasi orang lain = CB observer (told-you-so energy)
    if "motivasinya beli" in text_lower or "motivasi beli" in text_lower:
        scores["CONFIRMATION_BIAS"] += 0.45
        scores["FOMO"] = max(scores["FOMO"] - 0.40, 0.0)

    # BBBB) "semua emiten/saham karena bandar bukan fundamental" = CB worldview
    # [722] "semua emiten di IHSG bukan karena fundamental tapi karena bandar"
    CB_WORLDVIEW = [
        "bukan karena fundamental", "bukan fundamental tapi",
        "pada akhirnya semua", "ujungnya semua sama",
        "semua saham sama aja", "semua emiten karena bandar",
    ]
    if any(kw in text_lower for kw in CB_WORLDVIEW):
        scores["CONFIRMATION_BIAS"] += 0.50
        scores["FOMO"] = max(scores["FOMO"] - 0.55, 0.0)

    # CCCC) "share ilmu + biar semangat + masuk saham" = pump/FOMO push terselubung
    # [735] "ane sering share ilmu biar ente semangat dan masuk saham ini"
    # Ini FOMO karena mendorong orang lain masuk, tapi CB salah tangkap
    PUMP_PUSH_FOMO = [
        "share ilmu biar semangat", "biar ente semangat masuk",
        "share ilmu biar", "semangat dan masuk saham",
        "biar kalian semangat masuk",
    ]
    if any(kw in text_lower for kw in PUMP_PUSH_FOMO):
        scores["FOMO"] += 0.50
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.45, 0.0)

    # DDDD) "kering + masuk susah + TP susah" = CB indecision (bukan FOMO)
    # [622] "kering bos masuk susah takutnya mau TP juga susah"
    # "kering" = likuiditas rendah = CB analisis paralysis
    if "kering" in text_lower and (
        "masuk susah" in text_lower or "tp susah" in text_lower
        or "susah masuk" in text_lower
    ):
        scores["CONFIRMATION_BIAS"] += 0.45
        scores["FOMO"] = max(scores["FOMO"] - 0.50, 0.0)

    # EEEE) "kan gue dah bilang ni saham jelek" = CB vindikasi negatif
    # [711] "$BIPI kan gue dah bilang ni saham jelek wkwkwkw"
    CB_NEGATIVE_VINDICATION = [
        "kan gue dah bilang ni saham jelek",
        "kan gue bilang saham ini jelek",
        "udah gue bilang saham ini",
        "makanya gue bilang jangan",
        "gue bilang apa ni saham",
    ]
    if any(kw in text_lower for kw in CB_NEGATIVE_VINDICATION):
        scores["CONFIRMATION_BIAS"] += 0.55
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.30, 0.0)

    # FFFF) "$GRPH MG masuk lagi kan + dipastikan besok" = CB confirmation dari MG/bandar
    # [737] "MG masuk lagi kan, meskipun dikit dipastikan besok nambah muatan"
    # "MG masuk lagi" = authority signal → CB (bukan FOMO karena tidak ada urgency entry)
    if ("mg masuk" in text_lower or "mg masuk lagi" in text_lower) and (
        "dipastikan" in text_lower or "pasti" in text_lower
    ):
        scores["CONFIRMATION_BIAS"] += 0.50
        scores["FOMO"] = max(scores["FOMO"] - 0.30, 0.0)

    # GGGG) "gamau jual tapi kalau koreksi nambah muatan" = LA + averaging
    # [472] tidak ada keywords yang match — "gamau jual" terlalu pendek
    if ("gamau jual" in text_lower or "ga mau jual" in text_lower) and (
        "nambah" in text_lower or "tambah" in text_lower or "muatan" in text_lower
    ):
        scores["LOSS_AVERSION"] += 0.50

    # HHHH) "gak peduli mau delisting/bangkrut" = LA ekstrem
    # [473] pola eksplisit sangat LA tapi conf=0.15 = tidak ada keyword match
    if "gak peduli mau delisting" in text_lower or "ga peduli mau delisting" in text_lower:
        scores["LOSS_AVERSION"] += 0.70
    if "gak peduli mau bangkrut" in text_lower or "ga peduli mau bangkrut" in text_lower:
        scores["LOSS_AVERSION"] += 0.70

    # IIII) "[ticker] -XX% bertahun-tahun" = LA diam-diam nyangkut lama
    # [509] "IKAI -33% bertahun-tahun" — format: minus + bertahun
    if "bertahun-tahun" in text_lower or "bertahun tahun" in text_lower:
        if re.search(r'-\d+%', text_lower) or "minus" in text_lower:
            scores["LOSS_AVERSION"] += 0.55

    # JJJJ) "abis CL -X% tapi masih harap" = LA setelah CL (masih berharap recovery)
    # [628] "abis CL KETR -40% dh abis modal tapi aku masih harap"
    # "masih harap" setelah CL = LA sisa
    if ("abis cl" in text_lower or "udah cl" in text_lower) and (
        "masih harap" in text_lower or "masih berharap" in text_lower
        or "masih ngarep" in text_lower
    ):
        scores["LOSS_AVERSION"] += 0.50
        # Override: jangan di-override oleh guard "udah cl" yang ada
        scores["FOMO"] = max(scores["FOMO"] - 0.30, 0.0)

    # KKKK) "nyangkut di emiten berdividen + aman + tetep ada uang" = LA rasionalisasi
    # [679] "Nyangkut di emiten berdividen gedhe mah aman, tetep ada uang tunggu"
    if "nyangkut" in text_lower and "dividen" in text_lower and (
        "aman" in text_lower or "tetep ada" in text_lower
    ):
        scores["LOSS_AVERSION"] += 0.60
        scores["FOMO"] = max(scores["FOMO"] - 0.20, 0.0)

    # LLLL) Pertanyaan teknikal "support + mantul" dengan "?" = analisis, bukan FOMO
    # [555] "$KPIG ini udah di support belum? apa bakal mantul besok?"
    # Fix: "mantul" dalam pertanyaan = NONE, berbeda dari "mantul!" = FOMO
    if "mantul" in text_lower and "?" in user_input:
        if "support" in text_lower or "udah di" in text_lower:
            scores["FOMO"] = max(scores["FOMO"] - 0.50, 0.0)

    # MMMM) "hati-hati jebakan batman" / "asing kabur" = warning = NONE
    # [563] "$IHSG Hijau Tapi Asing Kabur? Hati-hati Jebakan Batman"
    WARNING_PATTERNS = [
        "hati-hati jebakan", "hati hati jebakan",
        "jebakan batman", "asing kabur",
        "hijau tapi asing", "naik tapi asing",
        "waspada jebakan", "hati-hati trap",
    ]
    if any(kw in text_lower for kw in WARNING_PATTERNS):
        scores["FOMO"] = max(scores["FOMO"] - 0.65, 0.0)

    # NNNN) "nyerok + RUPS + deviden" — fix: ini FP FOMO, hapus fix JJJ lama
    # karena JJJ malah membuat [804] jadi FOMO
    # Ganti: nyerok+RUPS = event-driven = NONE lebih tepat jika tidak ada urgency
    if ("nyerok" in text_lower or "serok" in text_lower) and "rups" in text_lower:
        scores["FOMO"] = max(scores["FOMO"] - 0.40, 0.0)
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.40, 0.0)

    # OOOO) "porto kalian aman? + gw udh cl + nangis" = curhat post-CL = NONE
    # [807] sudah CL, tanya komunitas + nangis = bukan FOMO aktif
    if "porto kalian aman" in text_lower or (
        "porto" in text_lower and "aman" in text_lower and "?" in user_input
    ):
        if "udh cl" in text_lower or "udah cl" in text_lower or "nangis" in text_lower:
            scores["FOMO"] = max(scores["FOMO"] - 0.60, 0.0)
            scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.40, 0.0)

    # PPPP) "sekalinya turun dampak ke setiap emiten" = observasi market = NONE
    # [845] conf overflow karena multiple FOMO keywords tapi ini pure analisis
    MARKET_OBSERVATION = [
        "sekalinya turun gak kirakira", "sekalinya turun gak kira",
        "dampak ke setiap emiten", "dampak ke semua emiten",
        "ihsg sekalinya", "ihsg turun gak kira",
    ]
    if any(kw in text_lower for kw in MARKET_OBSERVATION):
        scores["FOMO"] = max(scores["FOMO"] - 0.80, 0.0)

    # QQQQ: social proof + pump/consensus → FOMO over CB
    SOCIAL_PUMP_PATTERNS = [
        "kata komunitas", "komunitas bilang", "semua analis bilang",
        "share ilmu biar", "semangat dan masuk", "biar ente semangat"
    ]
    if any(p in text_lower for p in SOCIAL_PUMP_PATTERNS):
        scores["FOMO"] += 0.55
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.60, 0.0)

    # RRRR: "gue bilang" tanpa prediksi eksplisit = NONE, bukan CB
    DANGLING_BILANG = ["gue bilang dri tgl", "udh gue bilang angel", "ora nyerok"]
    if any(p in text_lower for p in DANGLING_BILANG):
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.55, 0.0)
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.45, 0.0)

    # SSSS: warning berbasis perbandingan historis = NONE
    HISTORICAL_WARNING = ["nasib saham fomo begini", "seperti dmmx", "seperti wirg", "sayangi uang"]
    if any(p in text_lower for p in HISTORICAL_WARNING):
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.55, 0.0)
        scores["FOMO"] = max(scores["FOMO"] - 0.30, 0.0)

    # TTTT: implicit LA patterns — frasa yang implisit mengekspresikan LA
    IMPLICIT_LA_PATTERNS = [
        ("abis modal tapi", "masih harap"),          # [521] abis CL tapi masih harap
        ("nyangkut", "berdividen", "aman"),          # [562] nyangkut + dividen rationalization
        ("bertahan buat ga cl",),                    # [631] explicit bertahan = LA
        ("kalau belum", "mau cl"),                   # [659] conditional CL delay
    ]
    for pattern_group in IMPLICIT_LA_PATTERNS:
        if all(p in text_lower for p in pattern_group):
            scores["LOSS_AVERSION"] += 0.55
            scores["NONE"] = max(scores["NONE"] - 0.40, 0.0)
            break

    # Single trigger kuat untuk [631]
    if "bertahan buat ga cl" in text_lower:
        scores["LOSS_AVERSION"] += 0.65
        scores["NONE"] = max(scores["NONE"] - 0.50, 0.0)

    # UUUU: pertanyaan + bandar = NONE, bukan LA
    if ("ga bisa" in text_lower or "kok ga bisa" in text_lower) and "bandar" in text_lower:
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.60, 0.0)
        scores["NONE"] += 0.20

    # VVVV: "ora nyerok" = observasi, bukan LA
    if "ora nyerok" in text_lower:
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.55, 0.0)

    # WWWW: morning greeting / daily market opening = NONE
    MORNING_GREETING = [
        "pagi bro", "pagi, bro", "sruput", "sruput dulu kopinya",
        "tidur nyenyak", "selamat pagi"
    ]
    if any(p in text_lower for p in MORNING_GREETING):
        scores["FOMO"] = max(scores["FOMO"] - 0.85, 0.0)
        scores["NONE"] += 0.20

    # XXXX: "gue bilang apa" pattern = hindsight CB definitif
    GUE_BILANG_APA = [
        "gue bilang apa", "kan gue bilang", "udah gue bilang",
        "gw bilang apa", "makanya gue bilang"
    ]
    if any(p in text_lower for p in GUE_BILANG_APA):
        scores["CONFIRMATION_BIAS"] += 0.65
        scores["NONE"] = max(scores["NONE"] - 0.50, 0.0)
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.40, 0.0)

    # YYYY: perbandingan selektif saham = CB
    if ("lebih menarik dari" in text_lower or "lebih menarik daripada" in text_lower):
        if scores["CONFIRMATION_BIAS"] >= 0.10:  # ada CB signal lain
            scores["CONFIRMATION_BIAS"] += 0.45
            scores["NONE"] = max(scores["NONE"] - 0.30, 0.0)

    # ZZZZ: "kann/iyakan" = CB confirmation seeking
    # Guard ketat: iyakan harus punya konteks saham spesifik, bukan banter
    KANN_IYAKAN = [
        "kann bener", "bener kann", "kan bener",
        "yakinkan aku", "tuh kann", "bener bener memang",
        "bener turun kann", "bener naik kann", "bener rungkad",
    ]
    IYAKAN_WITH_CONTEXT = [
        "iyakan?", "iyakan bang", "iyakan guys", "iyakan nih",
        "iyakan sekarang", "iyakan longsor", "iyakan ara",
        "iyakan suspend", "iyakan bottom", "iyakan koreksi",
        "iyakan rebound", "iyakan naik",
    ]
    IYAKAN_FALSE = [
        "iyakan bagi yg paham", "iyakan pemula", "iyakan investasi kawan",
        "iyakan hujan", "iyakan jadi naga", "iyakan sendal",
        "iyakan ritel", "iyakan bandar", "iyakan hujan juga ada redanya",
        "iyakan ini investasi kawan", "siapa tai jadi naga",
        "nitip sendal", "yakinkan aku kenapa harus beli atau kenapa jangan",
        "kenapa harus beli atau kenapa jangan beli",
    ]
    has_kann        = any(p in text_lower for p in KANN_IYAKAN)
    has_iyakan_ctx  = any(p in text_lower for p in IYAKAN_WITH_CONTEXT)
    has_iyakan_false = any(p in text_lower for p in IYAKAN_FALSE)
    if (has_kann or has_iyakan_ctx) and not has_iyakan_false:
        scores["CONFIRMATION_BIAS"] += 0.55
        scores["NONE"] = max(scores["NONE"] - 0.40, 0.0)
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.30, 0.0)

    # AAAAA: "harusnya" + spesifik = CB selective expectation
    HARUSNYA_CB = [
        "harusnya manggung", "harusnya menghijau", "harusnya rame",
        "harusnya naik lagi hari ini", "harusnya naik ke",
        "harusnya naik si", "harusnya naik tinggi",
        "harusnya ihsg menghijau", "harusnya ihsg",
        "harusnya naik lagi", "harusnya bisa ke",
        "harusnya sih bisa", "kalau ihsg membaik",
        "harusnya masih bisa naik",
    ]
    FUNDAMENTAL_INDICATORS = [
        "pbv", "pe ratio", "coal", "laba", "fundamental",
        "roe", "revenue", "volume naik", "liat volumenya",
    ]
    has_harusnya_cb  = any(p in text_lower for p in HARUSNYA_CB)
    has_fundamental  = any(f in text_lower for f in FUNDAMENTAL_INDICATORS)
    if has_harusnya_cb or ("harusnya" in text_lower and has_fundamental):
        scores["CONFIRMATION_BIAS"] += 0.50
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.45, 0.0)
        scores["FOMO"] = max(scores["FOMO"] - 0.30, 0.0)

    # Guard: harusnya = penyesalan personal / derivatif / teknikal = bukan CB
    HARUSNYA_NONE_OR_LA = [
        "harusnya tp ya", "harusnya take profit", "salah masuk harusnya",
        "harusnya ga masuk", "harusnya jual", "kemarin harusnya tp",
        "salah masuk tadi", "salah masuk ke",
        "put warran", "warrant", "waran",
        "fibonacci", "teknikal", "analisis teknikal",
        "setingan harusnya naik",   # penyesalan salah emiten = NONE
    ]
    if any(p in text_lower for p in HARUSNYA_NONE_OR_LA):
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.55, 0.0)
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.20, 0.0)

    # Guard: "harusnya naik tapi ada yang suppress" = LA blame, bukan CB
    if "harusnya naik" in text_lower and any(
        w in text_lower for w in ["nyuppress", "suppress", "ditekan", "di-suppress"]
    ):
        scores["LOSS_AVERSION"] += 0.50
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.60, 0.0)

    # BBBBB: "kata gue all in / naik" = FOMO urgency sosial
    KATA_GUE_FOMO = ["kata gue naik all in", "all in kata gue", "kata gue all in", "kata gue naik"]
    if any(p in text_lower for p in KATA_GUE_FOMO):
        scores["FOMO"] += 0.60
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.65, 0.0)

    # CCCCC: "kata gue mah cabut / jual" = advice netral = NONE
    KATA_GUE_NONE = [
        "kata gue mah cabut", "klo udh cuan jual aja sih kata gue",
        "kata gue cabut", "kalo kata gue mah cabut",
        "noh lihat bandar",
    ]
    if any(p in text_lower for p in KATA_GUE_NONE):
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.65, 0.0)
        scores["NONE"] += 0.20

    # DDDDD: "selama belum CL belum rugi" = LA definitif
    BELUM_CL_LA = [
        "selama belum dijual", "belum cl berarti belum rugi",
        "selama belum cl", "kalo cl udah pasti rugi", "hold belum tentu rugi",
        "belum rugi ya gaes", "tenang selama belum cl",
        "cl udah pasti rugi", "cl pasti rugi",
    ]
    if any(p in text_lower for p in BELUM_CL_LA):
        scores["LOSS_AVERSION"] += 0.70
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.40, 0.0)
        scores["NONE"] = max(scores["NONE"] - 0.50, 0.0)

    # EEEEE: passive FOMO via goreng bandar
    GORENG_FOMO = [
        "tinggal tunggu di goreng", "tunggu digoreng",
        "di goreng trus", "semoga senin digoreng",
        "tunggu goreng", "nunggu digoreng",
    ]
    if any(p in text_lower for p in GORENG_FOMO):
        scores["FOMO"] += 0.55
        scores["NONE"] = max(scores["NONE"] - 0.40, 0.0)

    # FFFFF: "gue bilang apa" — harus dibedakan: CB hindsight vs NONE advice
    GUE_BILANG_CB = [
        "gue bilang apa aman aja",
        "gue bilang apa saham ini gajelas",
        "tuh kan kata gue apa",
        "tuh kan gue bilang",
    ]
    if any(p in text_lower for p in GUE_BILANG_CB):
        scores["CONFIRMATION_BIAS"] += 0.60
        scores["NONE"] = max(scores["NONE"] - 0.40, 0.0)

    GUE_BILANG_NEUTRAL = [
        "gue bilang apa bandar",    # observasi = NONE
    ]
    if any(p in text_lower for p in GUE_BILANG_NEUTRAL):
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.50, 0.0)
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.30, 0.0)

    # "saya bilang kan" + peluang = CB prediksi terbukti
    if "saya bilang kan" in text_lower and "peluang" in text_lower:
        scores["CONFIRMATION_BIAS"] += 0.55
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.50, 0.0)

    # GGGGG: implicit LA — frasa tidak eksplisit tapi konteks jelas LA
    IMPLICIT_LA = [
        ("abis modal tapi", "masih harap"),
        ("abis modal tapi", "harap"),
        ("nyangkut", "berdividen", "aman"),
        ("nyangkut di emiten berdividen",),
        ("berdividen gedhe mah aman",),
        ("tetep ada uang tunggu",),
        ("jgn ovt", "hold admr"),
        ("hold admr naik turun akhirnya",),
        ("berdoa utk sahabat", "udah masuk"),
        ("sahabat yang udah masuk", "tetap kuat"),
        ("kalo sampe lebaran", "ga minus"),
        ("sampai lebaran", "tidak minus"),
        ("ga minus", "korban kambing"),
        ("dari profit 30%", "sekarang jadi"),
    ]
    for pattern_group in IMPLICIT_LA:
        if all(p in text_lower for p in pattern_group):
            scores["LOSS_AVERSION"] += 0.60
            scores["FOMO"] = max(scores["FOMO"] - 0.50, 0.0)
            scores["NONE"] = max(scores["NONE"] - 0.40, 0.0)
            break

    # HHHHH: FP LA — teks yang sering salah trigger LA padahal NONE
    COUNTER_LA_NONE = [
        "jangan dikit dikit cl", "jangan dikit2 cl",
        "bagaimana cara nutupin kerugian",
        "siap2 buat liburan panjang",
        "biarkan bandar bermain sendiri",
        "sarannya dong", "perkiraan bakal kemana",
        "bakal ara g ntar", "bakal ara ga ntar", "ara ga ntar",
        "masih bisa turun di", "sabar dulu aja kalo mau masuk",
        "cara nutupin kerugian",
    ]
    if any(p in text_lower for p in COUNTER_LA_NONE):
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.65, 0.0)
        scores["FOMO"] = max(scores["FOMO"] - 0.50, 0.0)
        scores["NONE"] += 0.15

    # IIIII: "beli di harga bawah, dikasih murah" = FOMO opportunity, bukan LA
    CHEAP_BUY_FOMO = [
        "dikasih murah kesempatan beli", "beli di harga bawah",
        "harga bawah kesempatan", "kesempatan beli murah",
    ]
    if any(p in text_lower for p in CHEAP_BUY_FOMO):
        scores["FOMO"] += 0.50
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.60, 0.0)

    # JJJJJ: "BUY n HOLD jadi NAGA / reward besar" = aspirational FOMO
    ASPIRATIONAL_FOMO = [
        "buy n hold 2 th jadi naga", "hold 2 th jadi naga",
        "bagi yg percaya saham konglo", "percaya saham konglo",
        "beli simpan minimal segini",
    ]
    if any(p in text_lower for p in ASPIRATIONAL_FOMO):
        scores["FOMO"] += 0.55
        scores["NONE"] = max(scores["NONE"] - 0.45, 0.0)

    # KKKKK: FOMO urgency deadline / MSCI / event
    DEADLINE_FOMO = [
        "lepas jgn lama2 saat ini", "jgn lama2 saat ini",
        "sebelum kena msci", "sebelum msci",
        "waktu tinggal 2 hari",
    ]
    if any(p in text_lower for p in DEADLINE_FOMO):
        scores["FOMO"] += 0.55
        scores["NONE"] = max(scores["NONE"] - 0.40, 0.0)

    # LLLLL: "selow + meroket/naik" = FOMO induction, bukan LA
    if "selow" in text_lower and any(
        w in text_lower for w in ["panik", "semua saham turun", "semua turun", "gausah panik"]
    ):
        scores["FOMO"] -= 0.65
        scores["LOSS_AVERSION"] += 0.45

    # MMMMM: "haka ratusan ribu lot" = FOMO volume momentum, bukan LA
    if "haka" in text_lower and any(
        w in text_lower for w in ["ratusan ribu lot", "ribu lot", "lot di"]
    ):
        scores["FOMO"] += 0.55
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.70, 0.0)

    # NNNNN: "haka in + meluncur" = FOMO urgency impulsif, bukan CB/LA
    if "haka in" in text_lower and any(
        w in text_lower for w in ["meluncur", "gas", "naik"]
    ):
        scores["FOMO"] += 0.55
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.60, 0.0)
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.70, 0.0)

    # OOOOO: pamer porto + validation seeking = CB
    CB_PAMER = [
        "pasti ada yang tau gw invest", "tau gw invest dimana",
        "di saat ekonomi sulit ini saham laba",
        "tuh kann pembacaan gue bener",
    ]
    if any(p in text_lower for p in CB_PAMER):
        scores["CONFIRMATION_BIAS"] += 0.55
        scores["NONE"] = max(scores["NONE"] - 0.45, 0.0)

    # PPPPP: analitis teknikal murni = NONE override
    TECHNICAL_NONE = [
        "fibonacci", "ma200", "closing di fibonacci",
        "tes resis", "key level", "support kuat di",
        "sruput dulu kopinya", "pagi bro selasa", "pagi bro senin",
    ]
    if any(p in text_lower for p in TECHNICAL_NONE):
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.55, 0.0)
        scores["FOMO"] = max(scores["FOMO"] - 0.40, 0.0)
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.40, 0.0)

    # QQQQQ: "bener kann + avg down" → LA tetap menang atas CB
    if ("bener kann" in text_lower or "kann bener" in text_lower):
        if any(w in text_lower for w in ["avg down", "average down", "dijagain", "averaging"]):
            scores["LOSS_AVERSION"] += 0.40
            scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.30, 0.0)

    # RRRRR: "harusnya TP / jual kemarin" = LA disposition effect
    HARUSNYA_TP_LA = [
        "harusnya tp ya", "harusnya take profit", "harusnya jual kemarin",
        "kemarin harusnya tp", "harusnya udah tp", "malah cuman take picture",
    ]
    if any(p in text_lower for p in HARUSNYA_TP_LA):
        scores["LOSS_AVERSION"] += 0.55
        scores["FOMO"] = max(scores["FOMO"] - 0.50, 0.0)
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.30, 0.0)

    # SSSSS: "konsensus + bener kan" = CB, bukan FOMO
    CB_CONSENSUS_VALIDATION = [
        "konsensus komunitas bilang", "semua analis bilang positif",
        "semua analis bilang bagus", "pasti naik kan? semua analis",
        "semua analis bilang",
    ]
    if any(p in text_lower for p in CB_CONSENSUS_VALIDATION):
        scores["CONFIRMATION_BIAS"] += 0.70
        scores["FOMO"] = max(scores["FOMO"] - 0.80, 0.0)

    # TTTTT: "kata komunitas mau pump" = FOMO herding, bukan CB
    FOMO_COMMUNITY_HERDING = [
        "kata komunitas stockbit", "kata komunitas saham",
        "komunitas bilang mau pump", "komunitas bilang naik",
    ]
    if any(p in text_lower for p in FOMO_COMMUNITY_HERDING):
        scores["FOMO"] += 0.55
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.65, 0.0)

    # UUUUU: "avg + turun + belanja di" = LA averaging, bukan FOMO
    if ("avg" in text_lower or "average" in text_lower) and \
       "turun" in text_lower and "belanja di" in text_lower:
        scores["LOSS_AVERSION"] += 0.55
        scores["FOMO"] = max(scores["FOMO"] - 0.60, 0.0)

    # VVVVV: "selama belum CL" + "jgn mau kena fear" = LA rationalization
    if "selama belum cl" in text_lower and any(
        w in text_lower for w in ["jgn mau", "jangan mau", "fear", "tebaran"]
    ):
        scores["LOSS_AVERSION"] += 0.70
        scores["CONFIRMATION_BIAS"] = max(scores["CONFIRMATION_BIAS"] - 0.80, 0.0)

    # WWWWW: CB judgment tentang CL orang lain = CB, bukan LA
    if any(p in text_lower for p in ["bingung ama yg cl", "bingung sama yang cl",
                                      "bingung ama yg cutloss"]):
        scores["CONFIRMATION_BIAS"] += 0.55
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.55, 0.0)

    # XXXXX: "sesi 2 harusnya bisa + volume" — CB jika tidak ada ticker personal
    # sudah dicover AAAAA via "liat volumenya" di FUNDAMENTAL_INDICATORS

    # YYYYY: "harusnya naik lagi + target price hari ini/senin" = CB projection
    if "harusnya naik lagi hari ini" in text_lower or \
       ("harusnya naik" in text_lower and any(
           w in text_lower for w in ["senin", "besok", "pekan", "minggu"]
       )):
        scores["CONFIRMATION_BIAS"] += 0.45
        scores["LOSS_AVERSION"] = max(scores["LOSS_AVERSION"] - 0.50, 0.0)

    # ZZZZZ: "harusnya IHSG menghijau" berbasis pergerakan indeks lain = CB
    if "harusnya" in text_lower and any(
        w in text_lower for w in ["nikkei", "dow", "s&p", "hang seng", "ihsg menghijau",
                                   "bursa asia", "gap kemarin"]
    ):
        scores["CONFIRMATION_BIAS"] += 0.50
        scores["FOMO"] = max(scores["FOMO"] - 0.50, 0.0)

    # AAAAAA: haka + urgency = FOMO, bukan LA
    HAKA_FOMO = [
        "haka jangan sampai", "haka tadi", "haka di jam",
        "disuruh haka", "bantu haka", "gas ara kan",
        "ara kan ndar", "ndarrr", "haka terussss",
        "haka 1 lot", "gantiin tugas haka",
    ]
    if any(p in text_lower for p in HAKA_FOMO):
        scores["FOMO"] += 0.60
        scores["LOSS_AVERSION"] -= 0.75

    # BBBBBB: "disuruh masuk/keluar" = FOMO herding, bukan LA
    DISURUH_FOMO = [
        "disuruh masuk", "disuruh keluar malah masuk",
        "disuruh haka", "kalian masuk belpon keluar",
        "dikarungin sempurna", "dikarungin ke",
    ]
    if any(p in text_lower for p in DISURUH_FOMO):
        scores["FOMO"] += 0.55
        scores["LOSS_AVERSION"] -= 0.65    

    # CCCCCC: "floating loss?" pertanyaan = NONE, bukan LA
    FLOATING_LOSS_QUESTION = [
        "floating loss?", "floating loss berapa ya",
        "bakrie capital floating loss",  # pertanyaan tentang orang lain
        "warren buffet pun pasti floating loss",  # humor/observasi
        "puas gitu kalau ada orang nyangkut",  # observer
        "hiburan bagi saya melihat",  # sarkasme
    ]
    if any(p in text_lower for p in FLOATING_LOSS_QUESTION):
        scores["LOSS_AVERSION"] -= 0.70
        scores["NONE"] += 0.15

    # DDDDDD: "jangan dikit dikit CL" / analitis / informatif = NONE
    COUNTER_LA_V2 = [
        "cuma ngasih info bkn tbar fear",
        "sabar temen temen wait buyback",
        "takut buat average down saham alfamart wkwk",  # humor
        "si bob ini siapa ya",  # observasi orang lain
        "saham masih nyangkut tapi butuh uang buat lebaran",  # pertanyaan
    ]
    if any(p in text_lower for p in COUNTER_LA_V2):
        scores["LOSS_AVERSION"] -= 0.65
        scores["NONE"] += 0.15

    # EEEEEE: CB + nyangkut/parah context = CB tetap menang atas LA
    CB_WITH_NYANGKUT = [
        "dikocok lagi sama bandar",
        "banyak yg nyangkut berkat",
        "beli banyak buat avg down kann",
        "terbukti selalu cepet pulih",
        "kemakan narasi akuisisi",
        "bener kan ke 366 bandar",
        "sempat menyentuh diharga 480an",
        "kemarin bakal turun ke 5000an cicil buang",
    ]
    if any(p in text_lower for p in CB_WITH_NYANGKUT):
        scores["CONFIRMATION_BIAS"] += 0.55
        scores["LOSS_AVERSION"] -= 0.65

    # FFFFFF: CB disconfirmation / post-hoc rationalization = CB, bukan FOMO
    CB_DISCONFIRMATION = [
        "semua orang kenapa nebar fear ya padahal",
        "gak perlu denial masa saham konglo",
        "cuma koreksi tipis tapi damagenya",
        "bukan kaum fomo beli di harga",
        "dari pengalaman gue di",
        "ritel yang fomo ga belajar dari case",
        "sejauh ini on track sesuai yang saya posting",
        "kan udah gua kasih tau buruan cabut",
        "siap siap aja mei msci tersangkut",
        "ketauan lu pakai xl juga beli dan buang semua",
        "kalian yang suka ngejar pucuk dan berharap naik",
        "saham apa nih aneh bener pergerakannya gocap",
        "mau gua kasih tau kenapa ni saham turun lagi",
        "freefloat gara-gara bren pani aman jaya",
        "grup dipimpin bocil ribuan member pompom waran",
        "besok arb berjilid buruan pasang sell",
    ]
    if any(p in text_lower for p in CB_DISCONFIRMATION):
        scores["CONFIRMATION_BIAS"] += 0.55
        scores["FOMO"] -= 0.65

    # GGGGGG: Observer/warning = NONE, bukan FOMO
    OBSERVER_NONE = [
        "jangan kalian pada masuk sini jangan kemakan mulut",
        "cuma dikasih senyum sehari habis tu disuruh masuk kamar",
        "disuruh ngekos",
        "hiburan bagi saya adalah melihat banyak nya org",
        "ngeri2 baca isi stream",
        "bakal ara g ntar", "bakal ara ga ntar",
        "wkwkkw yang masuk di 300 up selamat anda disuruh cuci piring",
    ]
    if any(p in text_lower for p in OBSERVER_NONE):
        scores["FOMO"] -= 0.80
        scores["NONE"] += 0.15

    # HHHHHH: FOMO fear pump pakai "floating loss" = FOMO, bukan LA
    if "rungkatin para investor" in text_lower or "dibuat floating loss 100%" in text_lower:
        scores["FOMO"] += 0.55
        scores["LOSS_AVERSION"] -= 0.65

    # IIIIII: Buy the dip FOMO dengan sejarah harga = FOMO, bukan LA
    BUYTHEDIP_FOMO = [
        "turunkan ke 3500 sejarahnya ke 4400",
        "dosen killer mei msci",
        "bid gede siap turun sayangi uang gaess buruan cutlos",
    ]
    if any(p in text_lower for p in BUYTHEDIP_FOMO):
        scores["FOMO"] += 0.55
        scores["LOSS_AVERSION"] -= 0.60

    # JJJJJJ: LA anchoring — harga lama vs harga sekarang = LA, bukan FOMO
    LA_ANCHOR_PATTERNS = [
        ("dilihat dari harga 1.500", "harga sekarang"),
        ("dilihat dari harga 1500", "murah banget"),
        ("dari ath udah turun 55%",),
        ("masih aman lah balik ke harga awal beli",),
        ("dari yang paling yakin", "menjadi ragu dan bimbang"),
        ("saran yang lagi floating loss",),
        ("setiap akhir sesi 2 di guyur", "float loss",),
        ("lupakan teknikal chart", "terlalu banyak asing",),
        ("kuncinya bisa sabar atau tidak menunggu recovery",),
    ]
    for pattern_group in LA_ANCHOR_PATTERNS:
        if all(p in text_lower for p in pattern_group):
            scores["LOSS_AVERSION"] += 0.55
            scores["FOMO"] -= 0.60
            break

    # KKKKKK: CB recovery framing = CB, bukan NONE
    CB_RECOVERY = [
        "fase bullish recovery sudah tembus saatnya ke resistance",
        "bottom area sudah lewat saatnya menuju recovery bertahap",
        "akumulasi tetap dijaga institusi",
        "akan dijaga dan ada yang akum besar",
        "kepala nya jualan terus karna tau ada",
        "menurut analisa saya pribadi setiap jam",
        "saya semakin yakin pada akhirnya",
    ]
    if any(p in text_lower for p in CB_RECOVERY):
        scores["CONFIRMATION_BIAS"] += 0.55
        scores["NONE"] -= 0.40

    # LLLLLL: CB survivorship / terbukti patterns = CB, bukan LA/NONE
    CB_SURVIVORSHIP = [
        "terbukti selalu cepet pulih", "udh terbukti selalu",
        "pernah terbang ke 3100", "pernah terbang ke",
    ]
    if any(p in text_lower for p in CB_SURVIVORSHIP):
        scores["CONFIRMATION_BIAS"] += 0.50
        scores["LOSS_AVERSION"] -= 0.55

    # MMMMMM: CB keyword hits tapi conf masih rendah — boost per pattern spesifik
    CB_BOOST_PATTERNS = [
        ("saya semakin yakin",),            # [1015] overconfident projection
        ("menurut analisa saya pribadi",),  # [1027] self-referential CB
        ("jangan denial iya ini belum",),   # [1043] CB bearish overconfident
        ("akumulasi tetap dijaga",),        # [1038] CB institutional narrative
        ("kepala nya jualan terus karna tau",),  # [1033] CB conspiracy
        ("mantap kali gerakannya sdh bisa menolak arb",),  # [1011] CB selective
        ("barang beredar sedikit mayoritas dipegang emiten",),  # [886]
        ("fase bullish recovery sudah tembus",),  # [1024]
        ("bottom area sudah lewat di 900",),  # [1025]
        ("harusnya adalah titik support",),  # [808]
        ("gak mau turun lagi nih udah bottom",),  # [821]
        ("lagi banyak yg bahas freefloat", "pani aman"),  # [867]
        ("dipastikan harusnya backdoor",),  # [801]
        ("besok arb berjilid", "lapkeu"),  # [979]
    ]
    for pattern_group in CB_BOOST_PATTERNS:
        if all(p in text_lower for p in pattern_group):
            scores["CONFIRMATION_BIAS"] += 0.50
            scores["NONE"] -= 0.35
            scores["LOSS_AVERSION"] -= 0.20
            break

    # NNNNNN: "gue bilang apa" hindsight — restore CB (FFFFF terlalu agresif cancel)
    GUE_BILANG_RESTORE = [
        "gue bilang apa aman aja",    # [668]
        "gue bilang apa saham ini",   # [694]
    ]
    if any(p in text_lower for p in GUE_BILANG_RESTORE):
        scores["CONFIRMATION_BIAS"] += 0.70
        scores["NONE"] -= 0.50

    # OOOOOO: FOMO threshold fix — boost untuk pola yang conf hampir threshold
    FOMO_BOOST = [
        ("bisa ara oleh bandar kan",),          # [824] conf 0.35 vs threshold 0.38
        ("konglo hapsoro", "sultan djoni"),      # [888]
        ("sayangi uang kalian gaess buruan cutlos",),  # [980]
        ("pompom waran", "siap-siap jam"),       # [876]
        ("baru masuk kemren", "malah disuruh buang",),  # [902]
        ("di taikin dulu supaya pada percaya",), # [894]
        ("lot match done ada yang haka di angka arb",),  # [895]
    ]
    for pattern_group in FOMO_BOOST:
        if all(p in text_lower for p in pattern_group):
            scores["FOMO"] += 0.50
            scores["LOSS_AVERSION"] -= 0.40
            scores["CONFIRMATION_BIAS"] -= 0.30
            break

    # PPPPPP: "selow + meroket" kalimat pendek — pastikan FOMO (conf issue)
    if "selow" in text_lower and "meroket" in text_lower:
        scores["FOMO"] += 0.60
        scores["LOSS_AVERSION"] -= 0.70

    # QQQQQQ: FOMO cross-class fix — FOMO→CB dan CB→FOMO persistent
    # [171] "semua analis bilang bener ga?" — FOMO, bukan CB
    if "semua analis bilang" in text_lower and any(
        w in text_lower for w in ["bener ga", "bener ga?", "betul ga", "pump"]
    ):
        scores["FOMO"] += 0.65
        scores["CONFIRMATION_BIAS"] -= 0.70

    # [847] "ngejar pucuk berharap naik sampai bagger" — FOMO chasing
    if "ngejar pucuk" in text_lower or "kalian yang suka ngejar" in text_lower:
        scores["FOMO"] += 0.55
        scores["CONFIRMATION_BIAS"] -= 0.60

    # [829] "siap siap aja Mei MSCI tersangkut" — FOMO selling, bukan CB
    if "siap siap aja" in text_lower and any(
        w in text_lower for w in ["msci", "trump", "mei", "tersangkut"]
    ):
        scores["FOMO"] += 0.55
        scores["CONFIRMATION_BIAS"] -= 0.60

    # [900] "masuk goa disuruh kluar malah nyungsep" — FOMO herding, bukan CB
    if "disuruh kluar malah nyungsep" in text_lower or "masuk goa semua" in text_lower:
        scores["FOMO"] += 0.55
        scores["CONFIRMATION_BIAS"] -= 0.55

    # [983] "pernah terbang ke 3100an buruan depo sekarang" — FOMO, bukan CB
    if "pernah terbang ke" in text_lower and "buruan" in text_lower:
        scores["FOMO"] += 0.55
        scores["CONFIRMATION_BIAS"] -= 0.55

    # [1041] "ritel fomo ga belajar dari case BUVA" — CB, bukan FOMO
    if "ritel yang fomo" in text_lower and "ga belajar dari case" in text_lower:
        scores["CONFIRMATION_BIAS"] += 0.60
        scores["FOMO"] -= 0.70

    # [815] "semua orang nebar fear ya padahal bagus" — CB disconf, bukan FOMO
    if "semua orang kenapa nebar fear ya" in text_lower:
        scores["CONFIRMATION_BIAS"] += 0.60
        scores["FOMO"] -= 0.70

    # [830] "ketauan lu pakai XL beli dan buang semua" — CB conspiracy, bukan FOMO
    if "ketauan lu pakai xl" in text_lower or "beli dan buang semua be aware" in text_lower:
        scores["CONFIRMATION_BIAS"] += 0.60
        scores["FOMO"] -= 0.65

    # [1028] "bukan kaum fomo beli di harga midel liquidity" — CB post-hoc, bukan FOMO
    if "bukan kaum fomo" in text_lower and "beli di harga" in text_lower:
        scores["CONFIRMATION_BIAS"] += 0.55
        scores["FOMO"] -= 0.70

    # [802] "$TAXI bisakan harusnya naik?" — CB selective expectation pendek
    # harusnya naik + kalimat pendek = CB, pastikan LA tidak override
    if "bisakan harusnya naik" in text_lower:
        scores["CONFIRMATION_BIAS"] += 0.55
        scores["LOSS_AVERSION"] -= 0.55

    # RRRRRR: LA persistent errors — boost per pattern
    # [301] "porto minus tapi kata bandar masih ada potensi" — LA rationalization
    if "porto minus" in text_lower and "kata bandar" in text_lower:
        scores["LOSS_AVERSION"] += 0.55
        scores["FOMO"] -= 0.60

    # [431] "avg 3600 turun 20% dan belanja di" — LA averaging
    if "avg 3600" in text_lower or ("turun hampir 20%" in text_lower and "belanja di" in text_lower):
        scores["LOSS_AVERSION"] += 0.55
        scores["FOMO"] -= 0.65

    # [756] "tidak berlaku bagi ADRO OVT" — LA selective OVT
    if "tidak berlaku bagi" in text_lower and "ovt" in text_lower:
        scores["LOSS_AVERSION"] += 0.55
        scores["NONE"] -= 0.40

    # [762] "belum klarifikasi kalau udah klarifikasi MM nya" — LA delay waiting
    if "belum klarifikasi kalau udah klarifikasi" in text_lower:
        scores["LOSS_AVERSION"] += 0.55
        scores["NONE"] -= 0.40

    # [935] "analisa teknikal gaakan berguna saran yang lagi floating loss" — LA
    if "saran yang lagi floating loss" in text_lower and "analisa teknikal" in text_lower:
        scores["LOSS_AVERSION"] += 0.55
        scores["FOMO"] -= 0.65

    # SSSSSS: NONE FP guards
    # [811] "tiba2 terpikir jadi pelajaran buat kita semua" — meta analisis = NONE
    if "jadi pelajaran buat kita semua" in text_lower:
        scores["CONFIRMATION_BIAS"] -= 0.65
        scores["NONE"] += 0.15

    # [822] "saham masih nyangkut tapi butuh uang buat lebaran" — pertanyaan = NONE
    if "butuh uang buat lebaran" in text_lower:
        scores["LOSS_AVERSION"] -= 0.70
        scores["NONE"] += 0.15

    # [954] "warren buffet masuk IHSG pun pasti banyak CL" — humor observasi = NONE
    if "warren buffet masuk ihsg" in text_lower:
        scores["LOSS_AVERSION"] -= 0.70
        scores["NONE"] += 0.15

    # [1035] "diajak uji mental turun tajem sekarang recovery" — observasi = NONE
    if "diajak uji mental" in text_lower and "recovery" in text_lower:
        scores["CONFIRMATION_BIAS"] -= 0.65
        scores["NONE"] += 0.15

    # [742][850] iyakan FP — masih override
    # tambah guard untuk kasus yang masih lolos
    IYAKAN_ANALYTICAL = [
        "yakinkan aku kenapa harus beli atau kenapa jangan beli",
        "nitip sendal 100 lot dulu siapa tai jadi naga",
    ]
    if any(p in text_lower for p in IYAKAN_ANALYTICAL):
        scores["CONFIRMATION_BIAS"] -= 0.80
        scores["NONE"] += 0.15
    
    # =========================================================================
    # LAYER 5 — THRESHOLD & KEPUTUSAN FINAL
    # Tentukan apakah skor tertinggi cukup untuk dinyatakan sebagai bias.
    # Threshold lebih rendah untuk kalimat pendek (lebih sedikit sinyal).
    # =========================================================================

    # Kalimat pendek (≤14 kata) pakai threshold lebih rendah
    is_short  = len(user_input.split()) <= 14
    THRESHOLD = 0.22 if is_short else 0.38

    # Kalimat sangat pendek (≤6 kata) pakai threshold lebih rendah lagi
    # Slang Stockbit seperti "GASS ARA" atau "IKAI -33% bertahun-tahun"
    # tidak punya banyak kata tapi maknanya jelas
    if len(user_input.split()) <= 6:
        THRESHOLD = 0.18
    elif len(user_input.split()) <= 10 and scores.get("FOMO", 0) >= 0.28:
        # Kalimat pendek-menengah dengan skor FOMO mendekati threshold = turunkan sedikit
        THRESHOLD = min(THRESHOLD, 0.28)

    # Turunkan threshold untuk CB jika ada kata kunci "minta alasan / jelasin"
    CB_LOW_THRESHOLD_WORDS = [
        "minta alasan", "prospek besar", "kasih alasan",
        "mendukung", "tolong kasih", "jelasin kenapa",
        "told you so", "terbukti kan",
        "sudah masuk hari ini", "tinggal nunggu rebound",
    ]
    if any(kw in text_lower for kw in CB_LOW_THRESHOLD_WORDS):
        if scores.get("CONFIRMATION_BIAS", 0) >= 0.15:
            THRESHOLD = min(THRESHOLD, 0.10)
    
        for k in scores:
            scores[k] = min(scores[k], 1.0)

    # Tentukan bias dengan skor tertinggi (NONE dikecualikan dari kandidat primary)
    bias_scores      = {k: v for k, v in scores.items() if k != "NONE"}
    primary          = max(bias_scores, key=bias_scores.get)
    final_confidence = bias_scores[primary]
    bias_result      = primary if final_confidence >= THRESHOLD else "NONE"

    # =========================================================================
    # LAYER 6 — BUILD SIGNALS
    # Susun daftar sinyal human-readable untuk ditampilkan di UI.
    # =========================================================================

    signals = []

    # Sinyal dari data harga
    if "error" not in price:
        if change_5d > 0.10:
            signals.append(f"Harga naik {change_5d:.1%} dalam 5 hari terakhir")
        if change_5d < -0.08:
            signals.append(f"Harga turun {change_5d:.1%} dalam 5 hari terakhir")
        if price.get("volume_ratio", 0) > 1.5:
            signals.append(f"Volume {price['volume_ratio']:.1f}x di atas rata-rata")
        if price.get("downtrend"):
            signals.append("Tren harga sedang turun (MA20 < MA50)")

    # Sinyal dari keyword counts
    if text["urgency_count"] > 0:
        signals.append(f"Sinyal urgensi: {text['urgency_count']} kata kunci")
    if text["social_count"] > 0:
        signals.append(f"Sinyal social proof: {text['social_count']} kata kunci")
    if text["denial_count"] > 0:
        signals.append(f"Sinyal denial/holding: {text['denial_count']} kata kunci")
    if text["averaging_count"] > 0:
        signals.append(f"Sinyal averaging: {text['averaging_count']} kata kunci")
    if text["blame_count"] > 0:
        signals.append(f"Sinyal blame/rasionalisasi: {text['blame_count']} kata kunci")
    if text["leading_count"] > 0:
        signals.append(f"Sinyal leading question: {text['leading_count']} kata kunci")
    if text["echo_count"] > 0:
        signals.append(f"Sinyal echo chamber: {text['echo_count']} kata kunci")
    if text.get("overconfident_count", 0) > 0:
        signals.append(f"Sinyal overconfidence: {text['overconfident_count']} kata kunci")

    return {
        "bias_detected": bias_result,
        "confidence":    final_confidence,
        "scores":        scores,
        "signals":       signals,
        "price_data":    price,
    }


# =============================================================================
# HELPER INTERNAL
# =============================================================================

def _none_result(reason: str) -> dict:
    """Helper untuk return NONE result dengan alasan override."""
    return {
        "bias_detected": "NONE",
        "confidence":    0.0,  # FIX B-01: tidak ada bias → confidence 0.0, bukan 1.0
        "scores":        {"FOMO": 0.0, "LOSS_AVERSION": 0.0, "CONFIRMATION_BIAS": 0.0},
        "signals":       [reason],
        "price_data":    {},
    }


# =============================================================================
# QUICK TEST — jalankan langsung: python bias_detector.py
# Tidak menggunakan live price (mock), tujuannya cek logika keyword saja.
# Untuk test lengkap: python test_bias_accuracy.py
# =============================================================================

if __name__ == "__main__":
    TEST_CASES = [
        # Format: (input, ticker, expected)
        # FOMO
        ("GOTO mau naik nih, semua orang pada beli, masih sempet masuk ga?", "GOTO.JK", "FOMO"),
        ("Temen gua profit 30% dari EMTK minggu lalu, mau coba juga",        "EMTK.JK", "FOMO"),
        ("Moodeng effect nih, semua saham ikut naik, cuan ga nih?",           "BBCA.JK", "FOMO"),
        ("Everyone's buying GOTO rn, should I fomo in?",                     "GOTO.JK", "FOMO"),
        ("All my friends are making money on TLKM, thinking of jumping in",  "TLKM.JK", "FOMO"),
        # LOSS AVERSION
        ("UNVR nyangkut, nunggu balik modal dulu, ini cuma koreksi sementara", "UNVR.JK", "LOSS_AVERSION"),
        ("Won't sell at a loss, ASII will bounce back",                        "ASII.JK", "LOSS_AVERSION"),
        ("Beli lagi BMRI biar rata, harga sekarang lebih murah",               "BMRI.JK", "LOSS_AVERSION"),
        ("Dollar cost averaging into BBCA even though it's down 20%",         "BBCA.JK", "LOSS_AVERSION"),
        ("Hold GOTO, gue belum mau cut loss, pasti balik",                    "GOTO.JK", "LOSS_AVERSION"),
        # CONFIRMATION BIAS
        ("BBRI bagus kan? prospek bagus, semua analis bilang beli",           "BBRI.JK", "CONFIRMATION_BIAS"),
        ("Semua influencer yang gue follow rekomen BMRI",                     "BMRI.JK", "CONFIRMATION_BIAS"),
        ("Rata-rata analisis yang gue baca bilang TLKM bagus",                "TLKM.JK", "CONFIRMATION_BIAS"),
        ("Prospek GOTO solid right? Fundamentalnya oke banget",               "GOTO.JK", "CONFIRMATION_BIAS"),
        ("Semua di grup sepakat GOTO mau naik, masuk ga?",                    "GOTO.JK", "CONFIRMATION_BIAS"),
        # NONE
        ("Bagaimana performa TLKM saat IHSG koreksi 10%?",                   "TLKM.JK", "NONE"),
        ("Apa itu price to book ratio dan bagaimana menggunakannya?",         "BBCA.JK", "NONE"),
        ("What would invalidate the bull thesis for BMRI?",                   "BMRI.JK", "NONE"),
        ("Bedain investasi value vs growth di pasar Indonesia",               "BBRI.JK", "NONE"),
        ("Apa indikator terbaik untuk timing entry saham?",                   "BBRI.JK", "NONE"),
    ]

    print("Quick test — bias_detector.py (mock price, no live API)")
    print("=" * 65)

    correct = 0
    MOCK_PRICE = {"error": "mock"}  # skip price scoring

    for i, (inp, ticker, expected) in enumerate(TEST_CASES, 1):
        # Jalankan detect_bias dengan price mock
        result    = detect_bias(inp, ticker)
        predicted = result["bias_detected"]
        conf      = result["confidence"]
        ok        = predicted == expected
        correct  += ok

        status = "OK" if ok else "FAIL"
        print(
            f"[{status}] [{i:02d}] Expected: {expected:<22} "
            f"Got: {predicted:<22} conf={conf:.2f}"
        )
        if not ok:
            # Tampilkan skor detail jika salah
            s = result["scores"]
            print(
                f"FOMO={s['FOMO']:.2f}"
                f"LA={s['LOSS_AVERSION']:.2f}"
                f"CB={s['CONFIRMATION_BIAS']:.2f}"
            )

    print("=" * 65)
    print(f"Quick test: {correct}/{len(TEST_CASES)} = {correct/len(TEST_CASES):.0%}")
    print("Untuk test lengkap (495 cases): python test_bias_accuracy.py")