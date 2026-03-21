# test_bias_accuracy.py
# ─────────────────────────────────────────────────────────────────────────────
# Test akurasi deteksi bias CogniFi — keyword-based (bias_detector.py)
# Dua layer test:
#   1. UNIT TEST  — test setiap scorer langsung, tanpa API call
#   2. ACCURACY   — jalankan semua test case, hitung precision/recall per bias
#
# Cara pakai:
#   python test_bias_accuracy.py            → full test + laporan akurasi
#   python test_bias_accuracy.py --unit     → unit test saja (cepat)
#   python test_bias_accuracy.py --verbose  → print detail tiap test case
#
# ─────────────────────────────────────────────────────────────────────────────

import sys
import argparse
import json
from collections import defaultdict
from bias_detector import detect_bias, initialize_price_check

# Cek koneksi Yahoo Finance sekali di awal.
# Kalau diblock, tanya user apakah mau lanjut tanpa price data.
initialize_price_check()

# ═════════════════════════════════════════════════════════════════════════════
# TEST DATASET
# 120 kalimat variatif, masing-masing dengan label ground truth.
# Dibagi 4 kategori: FOMO, LOSS_AVERSION, CONFIRMATION_BIAS, NONE
#
# Prinsip variasi:
#   - Bahasa formal ↔ slang ↔ campuran
#   - Langsung ↔ implisit ↔ tersamar
#   - Kalimat pendek ↔ panjang
#   - Ada ticker ↔ tidak ada ticker
#   - Bahasa Indonesia ↔ English ↔ campuran (code-switching)
# ═════════════════════════════════════════════════════════════════════════════

with open('data/training_700.json', 'r', encoding='utf-8') as f:
    raw_cases = json.load(f)

TEST_CASES = [
    (case['text'], case.get('ticker', 'BBCA.JK'), case['expected'])
    for case in raw_cases
]

print(f"Loaded {len(TEST_CASES)} test cases from JSON")


# ═════════════════════════════════════════════════════════════════════════════
# RUNNER
# ═════════════════════════════════════════════════════════════════════════════

TICKER_DEFAULT = ""   # kosong = skip yfinance untuk test tanpa ticker eksplisit


def run_tests(verbose: bool = False) -> dict:
    """
    Jalankan semua test cases, return hasil per bias.
    """

    results = defaultdict(lambda: {"TP": 0, "FP": 0, "FN": 0, "TN": 0, "details": []})

    total     = len(TEST_CASES)
    correct   = 0
    wrong     = []

    print(f"\n{'='*65}")
    print(f"CogniFi Bias Detection Accuracy Test")
    print(f"Total test cases: {total}")
    print(f"{'='*65}\n")

    for i, (query, ticker, expected) in enumerate(TEST_CASES, 1):
        result    = detect_bias(query, ticker or TICKER_DEFAULT)  # pakai ticker kalau ada
        predicted = result.get("bias_detected") or "NONE"
        confidence = result.get("confidence", 0.0)

        is_correct = (predicted == expected)
        if is_correct:
            correct += 1

        # Confusion matrix per bias
        all_labels = {"FOMO", "LOSS_AVERSION", "CONFIRMATION_BIAS", "NONE"}
        for label in all_labels:
            pred_pos = (predicted == label)
            true_pos = (expected  == label)
            if pred_pos and true_pos:
                results[label]["TP"] += 1
            elif pred_pos and not true_pos:
                results[label]["FP"] += 1
            elif not pred_pos and true_pos:
                results[label]["FN"] += 1
            else:
                results[label]["TN"] += 1

        # Record detail
        status = "✅" if is_correct else "❌"
        detail = {
            "query":      query[:60],
            "expected":   expected,
            "predicted":  predicted,
            "confidence": confidence,
            "correct":    is_correct,
        }
        results[expected]["details"].append(detail)

        if verbose or not is_correct:
            print(f"{status} [{i:03d}] {query[:55]}...")
            if not is_correct:
                print(f"       Expected: {expected} | Got: {predicted} (conf={confidence:.2f})")
                wrong.append((i, query, expected, predicted, confidence))
            elif verbose:
                print(f"       Label: {expected} | Conf: {confidence:.2f}")

    return {
        "total":   total,
        "correct": correct,
        "wrong":   wrong,
        "results": dict(results),
    }


def print_report(data: dict) -> None:
    """
    Print laporan akurasi per bias + overall.
    """
    total   = data["total"]
    correct = data["correct"]
    results = data["results"]
    wrong   = data["wrong"]

    overall_acc = correct / total * 100

    print(f"\n{'='*65}")
    print(f"LAPORAN AKURASI")
    print(f"{'='*65}")
    print(f"Overall accuracy : {correct}/{total} = {overall_acc:.1f}%")
    print()

    labels = ["FOMO", "LOSS_AVERSION", "CONFIRMATION_BIAS", "NONE"]
    header = f"{'Bias':<22} {'Precision':>10} {'Recall':>10} {'F1':>10} {'TP':>5} {'FP':>5} {'FN':>5}"
    print(header)
    print("-" * 65)

    for label in labels:
        r  = results.get(label, {})
        tp = r.get("TP", 0)
        fp = r.get("FP", 0)
        fn = r.get("FN", 0)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1        = (2 * precision * recall / (precision + recall)
                     if (precision + recall) > 0 else 0.0)

        bar = _bar(f1)
        print(f"{label:<22} {precision:>9.1%} {recall:>10.1%} {f1:>9.1%}  {tp:>4}  {fp:>4}  {fn:>4}  {bar}")

    if wrong:
        print(f"\n{'─'*65}")
        print(f"SALAH ({len(wrong)} kasus):")
        print(f"{'─'*65}")
        for idx, query, expected, predicted, conf in wrong:
            print(f"  [{idx:03d}] \"{query[:55]}...\"")
            print(f"        Expected: {expected:<22} | Got: {predicted} (conf={conf:.2f})")

    print(f"\n{'='*65}")
    _print_recommendation(overall_acc, results)


def _bar(f1: float, width: int = 10) -> str:
    filled = round(f1 * width)
    return "█" * filled + "░" * (width - filled)


def _print_recommendation(acc: float, results: dict) -> None:
    """
    Rekomendasi perbaikan berdasarkan hasil test.
    """
    print("REKOMENDASI PERBAIKAN:")
    print()

    if acc >= 85:
        print("  ✅ Akurasi keseluruhan sudah baik (>85%)")
    elif acc >= 70:
        print("  ⚠️  Akurasi sedang (70-85%) — ada ruang perbaikan")
    else:
        print("  ❌ Akurasi rendah (<70%) — perlu perbaikan keyword banks")

    labels = ["FOMO", "LOSS_AVERSION", "CONFIRMATION_BIAS", "NONE"]
    for label in labels:
        r  = results.get(label, {})
        tp = r.get("TP", 0)
        fp = r.get("FP", 0)
        fn = r.get("FN", 0)
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0

        if recall < 0.70:
            print(f"  ❌ {label}: Recall rendah ({recall:.0%}) → tambah keyword di bank deteksi")
        if precision < 0.70:
            print(f"  ❌ {label}: Precision rendah ({precision:.0%}) → false positive tinggi, "
                  f"naikkan threshold atau perkecil keyword yang terlalu umum")

    print()


# ═════════════════════════════════════════════════════════════════════════════
# UNIT TESTS — test scorer langsung tanpa price data
# ═════════════════════════════════════════════════════════════════════════════

def run_unit_tests() -> None:
    """
    Test subset kecil dari JSON (yang punya "unit_test": true)
    """
    from bias_detector import (
        score_fomo, score_loss_aversion, score_confirmation_bias,
        analyze_text
    )

    # Load dari JSON yang sama
    with open('data/training_700.json', 'r', encoding='utf-8') as f:
        raw_cases = json.load(f)

    # Filter hanya unit test cases
    UNIT_CASES = [
        (case['text'], case['expected'], case.get('min_score', None))
        for case in raw_cases
        if case.get('unit_test', False)
    ]

    print(f"\n{'='*55}")
    print(f"UNIT TEST — Scorer Langsung ({len(UNIT_CASES)} cases from JSON)")
    print(f"{'='*55}\n")

    pass_count = 0
    for query, expected_bias, min_score in UNIT_CASES:
        signals = analyze_text(query)

        fomo_score  = score_fomo(signals, {"change_5d": 0, "volume_ratio": 1.0, "change_10d": 0}, query.lower())
        la_score    = score_loss_aversion(signals, {"downtrend": False, "change_5d": 0})
        cb_score    = score_confirmation_bias(signals, query)

        scores = {
            "FOMO": fomo_score,
            "LOSS_AVERSION": la_score,
            "CONFIRMATION_BIAS": cb_score,
            "NONE": 0.0
        }
        best = max(scores, key=scores.get)

        # Untuk NONE, expected no score exceeds threshold 0.40
        if expected_bias == "NONE":
            ok = all(s < 0.40 for s in [fomo_score, la_score, cb_score])
        else:
            ok = (best == expected_bias) and (min_score is None or scores[expected_bias] >= min_score)

        status = "✅" if ok else "❌"
        if ok:
            pass_count += 1

        print(f"{status} \"{query[:50]}...\"")
        print(f"   Expected: {expected_bias:<22} | FOMO={fomo_score:.2f} "
              f"LA={la_score:.2f} CB={cb_score:.2f}")
        if not ok:
            print(f"   ⚠️  Best={best} (expected {expected_bias})")
        print()

    print(f"Unit test: {pass_count}/{len(UNIT_CASES)} passed")
    print(f"{'='*55}\n")

# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CogniFi Bias Detection Accuracy Test")
    parser.add_argument("--unit",    action="store_true", help="Jalankan unit test saja")
    parser.add_argument("--verbose", action="store_true", help="Print semua detail, bukan hanya yang salah")
    args = parser.parse_args()

    if args.unit:
        run_unit_tests()
    else:
        if args.verbose:
            print("Mode: verbose — semua test case ditampilkan")
        data = run_tests(verbose=args.verbose)
        print_report(data)