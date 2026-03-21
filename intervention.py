# intervention.py

# ── Reflective Questions ───────────────────────────────

QUESTIONS = {
    "FOMO": (
        "Apakah ada perubahan fundamental yang mendukung "
        "kenaikan ini — atau kamu bereaksi terhadap "
        "pergerakan harga?"
    ),
    "LOSS_AVERSION": (
        "Apakah thesis investasi awalmu masih valid — "
        "atau kamu menahan posisi karena tidak mau "
        "mengakui kerugian yang sudah terjadi?"
    ),
    "CONFIRMATION_BIAS": (
        "Apa yang bisa membuktikan bahwa keputusan ini "
        "salah — dan sudah kamu cari belum?"
    ),
}

BIAS_LABELS = {
    "FOMO":              "FOMO — Fear of Missing Out",
    "LOSS_AVERSION":     "Loss Aversion",
    "CONFIRMATION_BIAS": "Confirmation Bias",
}

BIAS_ICONS = {
    "FOMO":              "[ FOMO ]",
    "LOSS_AVERSION":     "[ LOSS ]",
    "CONFIRMATION_BIAS": "[ BIAS ]",
}

# ── Pre-Mortem Templates ───────────────────────────────
# Data-driven, bukan generic.
# Angka dari counter_evidence engine, real-time.

PRE_MORTEM_TEMPLATES = {
    "FOMO": (
        "Data historis menunjukkan koreksi rata-rata {avg_correction:.0%} "
        "dalam {forward_days} hari setelah kondisi serupa. "
        "Jika skenario itu terjadi — "
        "apakah kamu punya rencana exit, atau kamu akan hold sambil berharap?"
    ),
    "FOMO_NO_DATA": (
        "Sebelum eksekusi — bayangkan harga turun 15% besok. "
        "Apakah kamu akan cut loss, average down, atau hold? "
        "Pastikan jawabannya sudah ada sebelum kamu klik beli."
    ),
    "LOSS_AVERSION": (
        "Dari {episodes_found} episode downtrend serupa pada {ticker}, "
        "{not_recovered_count} tidak recovery dalam {window} hari. "
        "Jika ini salah satunya — berapa kerugian maksimal yang masih bisa kamu terima "
        "sebelum kamu wajib cut loss?"
    ),
    "LOSS_AVERSION_NO_DATA": (
        "Sebelum averaging down — tentukan dulu batas maksimal kerugian "
        "yang bisa kamu terima. Tanpa angka itu, "
        "averaging down bisa berubah menjadi menambah exposure ke aset "
        "yang sedang downtrend."
    ),
    "CONFIRMATION_BIAS": (
        "Kamu sudah hampir memutuskan. "
        "Coba cari satu argumen terkuat yang menentang keputusan ini. "
        "Jika tidak bisa menemukannya — itu bukan karena keputusannya sempurna, "
        "tapi karena kamu belum cukup mencari."
    ),
}


# ── Generator ──────────────────────────────────────────

def generate_intervention(bias_result: dict,
                           evidence: dict) -> dict:

    bias = bias_result.get("bias_detected")

    if not bias or bias == "NONE" or bias not in BIAS_ICONS:
        return {
            "bias_detected": None,
            "header": "Tidak ada pola bias signifikan",
            "summary": (
                "Input kamu tidak menunjukkan pola bias "
                "yang kuat. Tetap lakukan riset fundamental "
                "sebelum eksekusi."
            ),
            "reflective_question": None,
            "evidence_text": None,
            "pre_mortem": None,
        }

    header = (
        f"{BIAS_ICONS[bias]} "
        f"{BIAS_LABELS[bias]} Terdeteksi  \n"
        f"Confidence: {bias_result['confidence']:.0%}"
    )

    evidence_text = _format_evidence(bias, evidence)
    question      = QUESTIONS.get(bias, "")

    # Pre-mortem aktif hanya jika confidence >= 0.70
    # Prinsip Sovereign Node: high conviction bias
    # wajib diperlambat lebih dalam
    pre_mortem = None
    if bias_result.get("confidence", 0) >= 0.70:
        pre_mortem = append_pre_mortem(bias, evidence)

    return {
        "bias_detected":       bias,
        "header":              header,
        "confidence":          bias_result['confidence'],
        "signals":             bias_result.get('signals', []),
        "evidence_text":       evidence_text,
        "reflective_question": question,
        "icon":                BIAS_ICONS[bias],
        "label":               BIAS_LABELS[bias],
        "pre_mortem":          pre_mortem,
    }


def append_pre_mortem(bias: str, evidence: dict) -> str:
    """
    Generate pertanyaan Pre-Mortem yang data-driven.

    Prinsip:
    - Angka nyata dari counter-evidence engine
    - Memaksa user membuat trading plan sebelum eksekusi
    - Tidak menghakimi — hanya mempertanyakan skenario terburuk
    - Posisi tepat di atas Friction Checkbox (lihat app.py)
    """
    status = evidence.get("status")

    if bias == "FOMO":
        if status == "ok":
            avg_corr = abs(evidence.get("avg_correction", 0.15))
            fwd_days = evidence.get("forward_days", 30)
            return PRE_MORTEM_TEMPLATES["FOMO"].format(
                avg_correction=avg_corr,
                forward_days=fwd_days,
            )
        return PRE_MORTEM_TEMPLATES["FOMO_NO_DATA"]

    elif bias == "LOSS_AVERSION":
        if status == "ok":
            episodes = evidence.get("episodes_found", 0)
            not_rec  = evidence.get("not_recovered_count", 0)
            ticker   = evidence.get("ticker", "saham ini")
            avg_days = evidence.get("avg_recovery_days") or 60
            return PRE_MORTEM_TEMPLATES["LOSS_AVERSION"].format(
                episodes_found=episodes,
                not_recovered_count=not_rec,
                ticker=ticker,
                window=avg_days,
            )
        return PRE_MORTEM_TEMPLATES["LOSS_AVERSION_NO_DATA"]

    elif bias == "CONFIRMATION_BIAS":
        return PRE_MORTEM_TEMPLATES["CONFIRMATION_BIAS"]

    return ""


# ── Evidence Formatter ─────────────────────────────────

def _format_evidence(bias: str, evidence: dict) -> str:

    if evidence.get("status") == "insufficient_data":
        ep = evidence.get("episodes_found", 0)
        return (
            f"Data historis tidak cukup untuk "
            f"kalkulasi reliable.\n"
            f"Episode ditemukan: {ep} (minimum: 3)\n\n"
            f"Lakukan riset fundamental secara manual "
            f"sebelum eksekusi."
        )

    if evidence.get("status") == "error":
        return (
            "Tidak dapat mengambil data historis. "
            "Pastikan koneksi internet aktif."
        )

    if bias == "FOMO":
        prob      = evidence.get('correction_probability', 0)
        avg       = evidence.get('avg_correction', 0)
        worst     = evidence.get('worst_correction', 0)
        best      = evidence.get('best_outcome', 0)
        ep        = evidence.get('episodes_found', 0)
        corr      = evidence.get('corrections_count', 0)
        start     = evidence.get('data_start', '')
        end       = evidence.get('data_end', '')
        ticker    = evidence.get('ticker', '')
        threshold = evidence.get('threshold', 0.20)
        window    = evidence.get('window_days', 5)
        fwd       = evidence.get('forward_days', 30)

        return (
            f"**Data historis {ticker}**  \n"
            f"Periode: {start} → {end}\n\n"
            f"Episode serupa "
            f"(naik >{threshold:.0%} dalam {window} hari):\n"
            f"→ Ditemukan        : **{ep} kejadian**\n"
            f"→ Diikuti koreksi  : **{corr} dari {ep}**\n"
            f"→ Probabilitas     : **{prob:.0%}**\n"
            f"→ Rata-rata koreksi: **{avg:.1%}**\n"
            f"→ Koreksi terburuk : **{worst:.1%}**\n"
            f"→ Outcome terbaik  : **+{best:.1%}**\n\n"
            f"*Analisis {fwd} hari setelah episode*"
        )

    elif bias == "LOSS_AVERSION":
        rec_prob = evidence.get('recovery_probability', 0)
        avg_days = evidence.get('avg_recovery_days', 'N/A')
        ep       = evidence.get('episodes_found', 0)
        rec      = evidence.get('recovered_count', 0)
        no_rec   = evidence.get('not_recovered_count', 0)
        ticker   = evidence.get('ticker', '')
        start    = evidence.get('data_start', '')
        end      = evidence.get('data_end', '')

        return (
            f"**Data historis {ticker}**  \n"
            f"Periode: {start} → {end}\n\n"
            f"Episode downtrend serupa:\n"
            f"→ Ditemukan         : **{ep} episode**\n"
            f"→ Akhirnya recovery : **{rec} episode**\n"
            f"→ Tidak recovery    : **{no_rec} episode**\n"
            f"→ Prob. recovery    : **{rec_prob:.0%}**\n"
            f"→ Rata-rata waktu   : **{avg_days} hari**\n\n"
            f"*Recovery = harga kembali ke titik entry*"
        )

    elif bias == "CONFIRMATION_BIAS":
        fundamental = evidence.get('fundamental', {})
        questions   = evidence.get('questions', [])
        ticker      = evidence.get('ticker', '')

        fund_text = "\n".join([
            f"→ {k:20}: **{v}**"
            for k, v in fundamental.items()
            if v != 'N/A'
        ])

        q_text = "\n".join([
            f"• {q}" for q in questions
        ])

        return (
            f"**Data fundamental {ticker}** "
            f"yang perlu dicek:\n\n"
            f"{fund_text}\n\n"
            f"**Pertanyaan yang belum kamu cari:**\n"
            f"{q_text}"
        )

    return "Data tidak tersedia."


# ── Quick Test ─────────────────────────────────────────

if __name__ == "__main__":

    print("Testing intervention.py (incl. pre-mortem)...")
    print("=" * 55)

    test_cases = [
        {
            "label": "FOMO high confidence + data ok → pre-mortem muncul",
            "bias_result": {"bias_detected": "FOMO", "confidence": 0.82, "signals": []},
            "evidence": {
                "status": "ok", "ticker": "GOTO.JK",
                "threshold": 0.20, "window_days": 5, "forward_days": 30,
                "episodes_found": 10, "corrections_count": 8,
                "correction_probability": 0.80, "avg_correction": -0.31,
                "worst_correction": -0.52, "best_outcome": 0.38,
                "data_start": "2022-04-11", "data_end": "2026-03-09",
            }
        },
        {
            "label": "FOMO low confidence → no pre-mortem",
            "bias_result": {"bias_detected": "FOMO", "confidence": 0.55, "signals": []},
            "evidence": {"status": "insufficient_data", "episodes_found": 1}
        },
        {
            "label": "LOSS_AVERSION high confidence + data ok → pre-mortem muncul",
            "bias_result": {"bias_detected": "LOSS_AVERSION", "confidence": 0.75, "signals": []},
            "evidence": {
                "status": "ok", "ticker": "UNVR.JK",
                "episodes_found": 12, "recovered_count": 8,
                "not_recovered_count": 4, "recovery_probability": 0.67,
                "avg_recovery_days": 45,
                "data_start": "2015-01-01", "data_end": "2026-03-09",
            }
        },
        {
            "label": "NONE — no bias",
            "bias_result": {"bias_detected": None, "confidence": 0.0, "signals": []},
            "evidence": {}
        },
    ]

    for tc in test_cases:
        print(f"\n── {tc['label']} ──")
        result = generate_intervention(tc["bias_result"], tc["evidence"])
        print(f"  Header     : {result['header']}")
        print(f"  Question   : {result['reflective_question']}")
        pm = result.get("pre_mortem")
        print(f"  Pre-Mortem : {pm if pm else '(tidak muncul)'}")

    print("\n" + "=" * 55)
    print("Test selesai.")