# evaluate_final.py
# ─────────────────────────────────────────────────────────────────────────────
# Evaluasi FINAL model CogniFi di held-out test set (150 kasus)
# Jalankan HANYA SEKALI setelah semua sprint fix selesai.
#
# Cara pakai:
#   python evaluate_final.py
#
# Output: laporan akurasi held-out + perbandingan vs training accuracy
# ─────────────────────────────────────────────────────────────────────────────

import json
from collections import defaultdict
from bias_detector import detect_bias

# ── Load held-out ─────────────────────────────────────────────────
with open('data/held_out_ANSWER_KEY.json', 'r', encoding='utf-8') as f:
    held_out = json.load(f)

print(f"\n{'='*65}")
print(f"CogniFi — EVALUASI FINAL (Held-Out Test Set)")
print(f"Total held-out kasus: {len(held_out)}")
print(f"{'='*65}\n")
print("⚠️  File ini dijalankan HANYA SEKALI untuk laporan final.\n")

TICKER_DEFAULT = "BBCA.JK"

results = defaultdict(lambda: {"TP": 0, "FP": 0, "FN": 0})
correct = 0
wrong = []

for item in held_out:
    text     = item['text']
    expected = item['expected']
    ticker   = item.get('ticker', TICKER_DEFAULT)

    result    = detect_bias(text, ticker)
    predicted = result.get("bias_detected") or "NONE"
    confidence = result.get("confidence", 0.0)

    is_correct = (predicted == expected)
    if is_correct:
        correct += 1
    else:
        wrong.append((item.get('no', '?'), text[:60], expected, predicted, confidence))

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

total = len(held_out)
acc   = correct / total * 100

# ── Laporan ───────────────────────────────────────────────────────
print(f"{'='*65}")
print(f"HASIL EVALUASI FINAL — HELD-OUT TEST SET")
print(f"{'='*65}")
print(f"Overall accuracy : {correct}/{total} = {acc:.1f}%")
print()

labels = ["FOMO", "LOSS_AVERSION", "CONFIRMATION_BIAS", "NONE"]
print(f"{'Bias':<22} {'Precision':>10} {'Recall':>10} {'F1':>10} {'TP':>5} {'FP':>5} {'FN':>5}")
print("-" * 65)

for label in labels:
    r  = results[label]
    tp, fp, fn = r["TP"], r["FP"], r["FN"]
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    bar = ("█" * round(f1 * 10)) + ("░" * (10 - round(f1 * 10)))
    print(f"{label:<22} {precision:>9.1%} {recall:>10.1%} {f1:>9.1%}  {tp:>4}  {fp:>4}  {fn:>4}  {bar}")

if wrong:
    print(f"\n{'─'*65}")
    print(f"SALAH ({len(wrong)} kasus):")
    print(f"{'─'*65}")
    for no, text, exp, pred, conf in wrong:
        print(f"  [{no}] \"{text}...\"")
        print(f"        Expected: {exp:<22} | Got: {pred} (conf={conf:.2f})")

# ── Simpan hasil ──────────────────────────────────────────────────
output = {
    "held_out_accuracy": round(acc, 2),
    "correct": correct,
    "total": total,
    "wrong_count": len(wrong),
    "per_label": {}
}
for label in labels:
    r  = results[label]
    tp, fp, fn = r["TP"], r["FP"], r["FN"]
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    output["per_label"][label] = {
        "precision": round(precision, 4),
        "recall":    round(recall, 4),
        "f1":        round(f1, 4),
        "TP": tp, "FP": fp, "FN": fn
    }

with open('data/held_out_evaluation_result.json', 'w') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n{'='*65}")
print(f"Hasil disimpan ke: data/held_out_evaluation_result.json")
print(f"Angka ini yang dipakai di paper sebagai 'test accuracy'.")
print(f"{'='*65}\n")