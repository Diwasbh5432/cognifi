# news_context.py
# =============================================================================
# CogniFi — Yahoo Finance News Context Layer
# =============================================================================
#
# Eksperimen: ambil 5 berita terbaru dari Yahoo Finance via yfinance .news,
# ekstrak sentimen kasar, dan pakai sebagai konteks tambahan di Layer 4
# bias_detector.py sebelum scoring final.
#
# POSISI DI PIPELINE:
#   Layer 2 (Price) → Layer 2b (News) ← INI → Layer 3 (Scoring)
#
# PRINSIP DESAIN:
#   - Graceful degradation: kalau gagal, sistem tetap jalan normal
#   - Tidak menggantikan rule-based, hanya memperkuat sinyal lemah
#   - Hanya aktif untuk confidence < 0.60 (zona ambigu)
#   - Cache ringan per sesi untuk hindari API call berulang
#
# SENTIMEN SEDERHANA (no external NLP library):
#   Positif  → cenderung boost FOMO / CB
#   Negatif  → cenderung boost LOSS_AVERSION
#   Mixed    → tidak ada adjustment
#
# HASIL EKSPERIMEN:
#   - yfinance .news tersedia untuk ticker IDX tapi volume berita rendah
#   - Judul berita mayoritas Bahasa Inggris (Yahoo Finance global feed)
#   - False positive risiko cukup tinggi jika langsung di-apply ke skor
#   - KEPUTUSAN: tampilkan sebagai konteks display saja, bukan primary signal
#   - Score adjustment aktif HANYA untuk confidence < 0.60 dan sentimen kuat
#
# =============================================================================

# news_context: curl_cffi via price_fetcher (Yahoo .news tidak dipakai)
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# KEYWORD SENTIMEN SEDERHANA
# Tidak pakai library NLP eksternal — cukup untuk MVP
# ─────────────────────────────────────────────────────────────────────────────

POSITIVE_WORDS = [
    "profit", "growth", "revenue", "record", "beat", "strong", "bullish",
    "upgrade", "buy", "outperform", "dividend", "expansion", "gain",
    "naik", "untung", "laba", "dividen", "positif", "tumbuh", "rekor",
    "meningkat", "bagus", "kuat",
]

NEGATIVE_WORDS = [
    "loss", "decline", "drop", "fall", "cut", "miss", "weak", "bearish",
    "downgrade", "sell", "underperform", "debt", "problem", "risk",
    "turun", "rugi", "merugi", "negatif", "lemah", "anjlok", "jatuh",
    "masalah", "gagal", "hutang", "bangkrut",
]

# Cache sederhana: ticker → (timestamp, result)
_news_cache: dict = {}
CACHE_TTL_SECONDS = 300  # 5 menit


# ─────────────────────────────────────────────────────────────────────────────
# FUNGSI UTAMA
# ─────────────────────────────────────────────────────────────────────────────

def fetch_news_context(ticker: str, max_articles: int = 5) -> dict:
    """
    Ambil berita terbaru untuk ticker dan return sentimen + judul.

    Returns dict:
        status          — "ok" | "empty" | "error"
        ticker          — ticker yang diambil
        articles        — list of {"title": str, "source": str, "sentiment": str}
        sentiment       — "positive" | "negative" | "mixed" | "neutral"
        positive_count  — jumlah judul dengan sentimen positif
        negative_count  — jumlah judul dengan sentimen negatif
        summary         — string ringkasan untuk ditampilkan di UI
    """
    global _news_cache

    # Cek cache
    if ticker in _news_cache:
        ts, cached = _news_cache[ticker]
        if (datetime.now() - ts).total_seconds() < CACHE_TTL_SECONDS:
            return cached

    try:
        raw_news = []  # Yahoo .news endpoint tidak reliable — dinonaktifkan

        if not raw_news:
            result = {
                "status":         "empty",
                "ticker":         ticker,
                "articles":       [],
                "sentiment":      "neutral",
                "positive_count": 0,
                "negative_count": 0,
                "summary":        f"Tidak ada berita terbaru untuk {ticker}.",
            }
            _news_cache[ticker] = (datetime.now(), result)
            return result

        articles  = []
        pos_count = 0
        neg_count = 0

        for item in raw_news[:max_articles]:
            title  = item.get("title", "")
            source = item.get("publisher", item.get("source", "Yahoo Finance"))

            # Sentimen sederhana berbasis keyword
            title_lower = title.lower()
            pos_hits    = sum(1 for w in POSITIVE_WORDS if w in title_lower)
            neg_hits    = sum(1 for w in NEGATIVE_WORDS if w in title_lower)

            if pos_hits > neg_hits:
                sentiment = "positive"
                pos_count += 1
            elif neg_hits > pos_hits:
                sentiment = "negative"
                neg_count += 1
            else:
                sentiment = "neutral"

            articles.append({
                "title":     title,
                "source":    source,
                "sentiment": sentiment,
            })

        # Overall sentiment
        total = len(articles)
        if pos_count > total * 0.6:
            overall = "positive"
        elif neg_count > total * 0.6:
            overall = "negative"
        elif pos_count > 0 and neg_count > 0:
            overall = "mixed"
        else:
            overall = "neutral"

        summary = _build_summary(ticker, articles, overall, pos_count, neg_count)

        result = {
            "status":         "ok",
            "ticker":         ticker,
            "articles":       articles,
            "sentiment":      overall,
            "positive_count": pos_count,
            "negative_count": neg_count,
            "summary":        summary,
        }
        _news_cache[ticker] = (datetime.now(), result)
        return result

    except Exception as e:
        return {
            "status":         "error",
            "ticker":         ticker,
            "articles":       [],
            "sentiment":      "neutral",
            "positive_count": 0,
            "negative_count": 0,
            "summary":        "",
            "error":          str(e),
        }


def _build_summary(ticker: str, articles: list, overall: str,
                   pos: int, neg: int) -> str:
    """Buat ringkasan human-readable dari hasil news scan."""
    total = len(articles)
    if total == 0:
        return ""

    sentiment_label = {
        "positive": "didominasi sentimen positif",
        "negative": "didominasi sentimen negatif",
        "mixed":    "sentimen beragam (positif & negatif)",
        "neutral":  "tidak ada sentimen dominan",
    }.get(overall, "")

    recent_titles = [a["title"][:60] for a in articles[:2]]
    titles_text   = " · ".join(recent_titles)

    return (
        f"{total} berita terbaru {ticker} — {sentiment_label}. "
        f"Headline: {titles_text}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# SCORE ADJUSTMENT HELPER
# Dipakai bias_detector.py di Layer 4 untuk kasus confidence rendah
# ─────────────────────────────────────────────────────────────────────────────

def get_news_score_hint(news_context: dict, current_bias: str) -> dict:
    """
    Return saran penyesuaian skor berdasarkan sentimen berita.

    HANYA aktif jika:
      - status == "ok"
      - sentimen tidak "neutral" atau "mixed"
      - ada minimal 3 artikel

    Returns dict:
        apply       — bool: apakah adjustment layak diterapkan
        boost_bias  — bias yang perlu di-boost (atau None)
        boost_delta — nilai boost (kecil: 0.05–0.10)
        reason      — string alasan untuk logging/debug
    """
    if news_context.get("status") != "ok":
        return {"apply": False, "boost_bias": None, "boost_delta": 0.0, "reason": "no news data"}

    total   = len(news_context.get("articles", []))
    overall = news_context.get("sentiment", "neutral")
    pos     = news_context.get("positive_count", 0)
    neg     = news_context.get("negative_count", 0)

    # Tidak cukup data untuk reliable adjustment
    if total < 3:
        return {"apply": False, "boost_bias": None, "boost_delta": 0.0, "reason": f"only {total} articles"}

    # Berita positif dominan → sedikit boost FOMO / CB (hype cycle lebih mungkin)
    if overall == "positive" and current_bias in ("FOMO", "CONFIRMATION_BIAS"):
        return {
            "apply":       True,
            "boost_bias":  current_bias,
            "boost_delta": 0.07,
            "reason":      f"news positive ({pos}/{total}) supports {current_bias}",
        }

    # Berita negatif dominan → sedikit boost LOSS_AVERSION
    if overall == "negative" and current_bias == "LOSS_AVERSION":
        return {
            "apply":       True,
            "boost_bias":  "LOSS_AVERSION",
            "boost_delta": 0.07,
            "reason":      f"news negative ({neg}/{total}) supports LOSS_AVERSION",
        }

    return {"apply": False, "boost_bias": None, "boost_delta": 0.0, "reason": "sentiment mixed/neutral"}


# ─────────────────────────────────────────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_tickers = ["BBCA.JK", "GOTO.JK", "TLKM.JK"]
    print("Testing news_context.py")
    print("=" * 55)
    for t in test_tickers:
        result = fetch_news_context(t)
        print(f"\n{t}:")
        print(f"  Status   : {result['status']}")
        print(f"  Sentimen : {result['sentiment']}")
        print(f"  Pos/Neg  : {result['positive_count']}/{result['negative_count']}")
        print(f"  Summary  : {result['summary'][:80]}")
        if result.get("articles"):
            for a in result["articles"][:2]:
                print(f"  → [{a['sentiment']:8}] {a['title'][:60]}")
    print("\n" + "=" * 55)