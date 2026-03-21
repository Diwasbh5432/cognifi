# fundamental_data.py
# =============================================================================
# CogniFi — Data Fundamental IDX Universe (10 ticker)
# =============================================================================
# Sumber: Laporan Keuangan Q3 2025, IDX.co.id
# Update: Maret 2026
# Cara update: Buka idx.co.id → Perusahaan Tercatat → Laporan Keuangan
# =============================================================================

FUNDAMENTAL: dict = {
    "BBCA.JK": {
        "name":           "Bank Central Asia Tbk",
        "sector":         "Keuangan — Perbankan",
        "pe_ratio":       "24.1",
        "pbv":            "5.2",
        "der":            "7.8",        # Debt/Equity (leverage bank = wajar tinggi)
        "roe":            "23.4%",
        "npm":            "42.1%",      # Net Profit Margin
        "revenue_growth": "12.3%",
        "source":         "Laporan Keuangan Q3 2025, IDX.co.id",
    },
    "BBRI.JK": {
        "name":           "Bank Rakyat Indonesia (Persero) Tbk",
        "sector":         "Keuangan — Perbankan",
        "pe_ratio":       "11.2",
        "pbv":            "2.1",
        "der":            "8.4",
        "roe":            "18.7%",
        "npm":            "28.3%",
        "revenue_growth": "8.1%",
        "source":         "Laporan Keuangan Q3 2025, IDX.co.id",
    },
    "TLKM.JK": {
        "name":           "Telkom Indonesia (Persero) Tbk",
        "sector":         "Teknologi — Telekomunikasi",
        "pe_ratio":       "13.8",
        "pbv":            "2.4",
        "der":            "0.9",
        "roe":            "17.2%",
        "npm":            "16.8%",
        "revenue_growth": "3.2%",
        "source":         "Laporan Keuangan Q3 2025, IDX.co.id",
    },
    "ASII.JK": {
        "name":           "Astra International Tbk",
        "sector":         "Industri — Konglomerasi",
        "pe_ratio":       "9.4",
        "pbv":            "1.4",
        "der":            "0.7",
        "roe":            "15.1%",
        "npm":            "7.3%",
        "revenue_growth": "4.8%",
        "source":         "Laporan Keuangan Q3 2025, IDX.co.id",
    },
    "BMRI.JK": {
        "name":           "Bank Mandiri (Persero) Tbk",
        "sector":         "Keuangan — Perbankan",
        "pe_ratio":       "10.8",
        "pbv":            "2.0",
        "der":            "7.2",
        "roe":            "19.3%",
        "npm":            "32.1%",
        "revenue_growth": "9.4%",
        "source":         "Laporan Keuangan Q3 2025, IDX.co.id",
    },
    "UNVR.JK": {
        "name":           "Unilever Indonesia Tbk",
        "sector":         "Consumer Goods — FMCG",
        "pe_ratio":       "18.3",
        "pbv":            "21.4",
        "der":            "2.1",
        "roe":            "117.2%",
        "npm":            "12.4%",
        "revenue_growth": "-3.1%",
        "source":         "Laporan Keuangan Q3 2025, IDX.co.id",
    },
    "GOTO.JK": {
        "name":           "GoTo Gojek Tokopedia Tbk",
        "sector":         "Teknologi — E-Commerce",
        "pe_ratio":       "N/A",        # Masih rugi
        "pbv":            "1.2",
        "der":            "0.4",
        "roe":            "-8.2%",
        "npm":            "-12.3%",
        "revenue_growth": "21.4%",
        "source":         "Laporan Keuangan Q3 2025, IDX.co.id",
    },
    "BREN.JK": {
        "name":           "Barito Renewables Energy Tbk",
        "sector":         "Energi — Energi Terbarukan",
        "pe_ratio":       "42.1",
        "pbv":            "8.3",
        "der":            "1.2",
        "roe":            "19.7%",
        "npm":            "38.2%",
        "revenue_growth": "15.6%",
        "source":         "Laporan Keuangan Q3 2025, IDX.co.id",
    },
    "EMTK.JK": {
        "name":           "Elang Mahkota Teknologi Tbk",
        "sector":         "Teknologi — Media",
        "pe_ratio":       "31.2",
        "pbv":            "2.8",
        "der":            "0.3",
        "roe":            "8.9%",
        "npm":            "22.1%",
        "revenue_growth": "6.3%",
        "source":         "Laporan Keuangan Q3 2025, IDX.co.id",
    },
    "SIDO.JK": {
        "name":           "Industri Jamu dan Farmasi Sido Muncul Tbk",
        "sector":         "Healthcare — Farmasi",
        "pe_ratio":       "16.7",
        "pbv":            "3.1",
        "der":            "0.1",
        "roe":            "18.4%",
        "npm":            "19.8%",
        "revenue_growth": "7.2%",
        "source":         "Laporan Keuangan Q3 2025, IDX.co.id",
    },
}


def get_fundamental(ticker: str) -> dict:
    """
    Ambil data fundamental untuk ticker IDX.
    Return dict dengan P/E, DER, ROE, dll.
    Kalau ticker tidak ada di database, return semua N/A.
    """
    data = FUNDAMENTAL.get(ticker, {})
    if not data:
        return {
            "PE Ratio":       "N/A",
            "PBV":            "N/A",
            "Debt/Equity":    "N/A",
            "ROE":            "N/A",
            "Profit Margin":  "N/A",
            "Revenue Growth": "N/A",
            "Source":         "Tidak ada data untuk ticker ini",
        }
    return {
        "PE Ratio":       data.get("pe_ratio", "N/A"),
        "PBV":            data.get("pbv", "N/A"),
        "Debt/Equity":    data.get("der", "N/A"),
        "ROE":            data.get("roe", "N/A"),
        "Profit Margin":  data.get("npm", "N/A"),
        "Revenue Growth": data.get("revenue_growth", "N/A"),
        "Source":         data.get("source", "N/A"),
    }


if __name__ == "__main__":
    print("=== Fundamental Data IDX Universe ===\n")
    for ticker, data in FUNDAMENTAL.items():
        print(f"{ticker} — {data['name']}")
        print(f"  P/E    : {data['pe_ratio']}")
        print(f"  PBV    : {data['pbv']}")
        print(f"  DER    : {data['der']}")
        print(f"  ROE    : {data['roe']}")
        print(f"  Margin : {data['npm']}")
        print()