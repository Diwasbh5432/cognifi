import json
import time
import urllib.request
import urllib.error

import os
from config import GEMINI_API_KEY
GEMINI_MODEL = "gemini-3-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

INPUT_FILE = "data/held_out_TEST_ONLY.json"
OUTPUT_FILE = "data/gemini_baseline_results.json"

SYSTEM_PROMPT = """You are an expert in behavioral finance and cognitive bias detection.

Your task is to classify a text written by an Indonesian retail investor into exactly one of four categories:

FOMO - Fear of Missing Out
The speaker is driven by urgency to enter because others are profiting or because a price is rising. Key signals: social proof as trigger ("semua orang beli", "temen gua udah profit"), urgency language ("masih sempet ga", "buruan"), price momentum cited without fundamental basis.

LOSS_AVERSION
The speaker has an unrealized loss and is generating reasons to hold rather than exit. Key signals: breakeven anchoring ("nunggu balik modal"), minimizing loss framing ("cuma koreksi", "sementara"), holding rationalization despite declining price.

CONFIRMATION_BIAS
The speaker is seeking validation for a belief or decision already made, not genuine analysis. Key signals: leading questions ("bagus kan?", "pasti naik kan?"), requests for supporting analysis only ("analisis yang mendukung"), post-decision validation seeking.

NONE
The text does not exhibit the defining patterns of the three biases above. The speaker is genuinely analytical, asks neutral questions open to any answer, or seeks objective information without directional framing.

Rules:
- Respond with ONLY one word: FOMO, LOSS_AVERSION, CONFIRMATION_BIAS, or NONE
- Do not explain your reasoning
- Do not add punctuation or extra text
- The text may be in Indonesian, English, or mixed Indonesian-English"""

def classify(text):
    body = json.dumps({
        "contents": [
            {
                "parts": [
                    {"text": SYSTEM_PROMPT + "\n\nText to classify:\n" + text}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 10
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            raw = result["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
            # Bersihkan output kalau ada punctuation
            raw = raw.replace(".", "").replace(",", "").replace("*", "").strip()
            # Validasi label
            valid = {"FOMO", "LOSS_AVERSION", "CONFIRMATION_BIAS", "NONE"}
            if raw in valid:
                return raw
            # Coba partial match kalau model tetap verbose
            for v in valid:
                if v in raw:
                    return v
            return "UNKNOWN"
    except urllib.error.HTTPError as e:
        return f"ERROR_{e.code}"
    except Exception as e:
        return f"ERROR_{str(e)[:30]}"

def main():
    with open(INPUT_FILE, encoding="utf-8") as f:
        data = json.load(f)

    results = []
    errors = []
    total = len(data)

    print(f"Memulai klasifikasi {total} kasus...\n")

    for i, item in enumerate(data, 1):
        text = item["text"]
        label = classify(text)
        results.append({
            "no": item["no"],
            "original_index": item["original_index"],
            "text": text,
            "gemini_prediction": label
        })

        status = "OK" if label in {"FOMO", "LOSS_AVERSION", "CONFIRMATION_BIAS", "NONE"} else "ERR"
        print(f"[{i:3d}/{total}] {status} | {label:20s} | {text[:60]}")

        if status == "ERR":
            errors.append({"no": i, "text": text, "raw": label})

        # Rate limit: 1 detik per request untuk menghindari quota hit
        time.sleep(1.0)

    # Simpan hasil
    output = {
        "model": GEMINI_MODEL,
        "total": total,
        "errors": len(errors),
        "results": results
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nSelesai. {total - len(errors)}/{total} berhasil diklasifikasi.")
    print(f"Hasil disimpan ke: {OUTPUT_FILE}")

    if errors:
        print(f"\nError pada {len(errors)} kasus:")
        for e in errors:
            print(f"  No {e['no']}: {e['raw']}")

if __name__ == "__main__":
    main()
