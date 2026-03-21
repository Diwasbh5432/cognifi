# price_fetcher.py
# =============================================================================
# CogniFi — Price Data Layer
# Menggunakan curl_cffi untuk bypass Yahoo Finance IP block.
# curl_cffi impersonate fingerprint browser asli → tidak kena block.
#
# Install: pip install curl_cffi
#
# CARA PAKAI:
#   from price_fetcher import get_price_data, get_current_price, get_ticker_info, get_historical_df
# =============================================================================

import json
import time
import datetime
import pandas as pd

# ── Cache ─────────────────────────────────────────────────────────────────────
_cache: dict  = {}
_CACHE_TTL    = 300  # 5 menit

def _fresh(key: str) -> bool:
    return key in _cache and (time.time() - _cache[key].get("_ts", 0)) < _CACHE_TTL


def _get(url: str) -> dict:
    from curl_cffi import requests as cffi_req
    resp = cffi_req.get(
        url,
        impersonate="chrome120",
        timeout=10,
        headers={"Accept-Language": "en-US,en;q=0.9"},
    )
    resp.raise_for_status()
    return resp.json()


def _fetch_chart(ticker: str, period: str = "3mo") -> dict:
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?interval=1d&range={period}&includePrePost=false"
    )
    return _get(url)


def _parse_chart(data: dict, ticker: str) -> pd.DataFrame:
    result = data["chart"]["result"][0]
    ts     = result["timestamp"]
    ohlcv  = result["indicators"]["quote"][0]
    closes = result["indicators"].get("adjclose", [{}])[0].get("adjclose", ohlcv["close"])
    df = pd.DataFrame({
        "open":   ohlcv["open"],
        "high":   ohlcv["high"],
        "low":    ohlcv["low"],
        "close":  closes,
        "volume": ohlcv["volume"],
    }, index=pd.to_datetime(ts, unit="s").normalize())
    df.index.name = "date"
    return df.dropna(subset=["close"]).sort_index()


def _fetch_quote(ticker: str) -> dict:
    """
    Ambil quote data via v8/finance/chart meta (masih publik).
    Fundamental via quoteSummary dengan modules defaultKeyStatistics + financialData.
    """
    # Harga dari chart meta (sudah terbukti jalan)
    try:
        chart_url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            f"?interval=1d&range=5d&includePrePost=false"
        )
        chart_data = _get(chart_url)
        meta = chart_data["chart"]["result"][0]["meta"]
    except Exception:
        meta = {}

    # Fundamental dari quoteSummary — coba beberapa versi endpoint
    stats, fin, summary = {}, {}, {}
    for base in [
        "https://query1.finance.yahoo.com/v10/finance/quoteSummary",
        "https://query2.finance.yahoo.com/v10/finance/quoteSummary",
    ]:
        try:
            summary_url = (
                f"{base}/{ticker}"
                f"?modules=defaultKeyStatistics%2CfinancialData%2CsummaryDetail"
            )
            summary_data = _get(summary_url)
            qs = summary_data.get("quoteSummary", {}).get("result", [{}])[0]
            if qs:
                stats   = qs.get("defaultKeyStatistics", {})
                fin     = qs.get("financialData", {})
                summary = qs.get("summaryDetail", {})
                break
        except Exception:
            continue

    def raw(d, k):
        v = d.get(k)
        if isinstance(v, dict):
            return v.get("raw")
        return v

    return {
        "regularMarketPrice":           meta.get("regularMarketPrice"),
        "regularMarketChangePercent":   meta.get("regularMarketChangePercent"),
        "fiftyTwoWeekHigh":             raw(summary, "fiftyTwoWeekHigh"),
        "fiftyTwoWeekLow":              raw(summary, "fiftyTwoWeekLow"),
        "trailingPE":                   raw(summary, "trailingPE"),
        "debtToEquity":                 raw(stats, "debtToEquity"),
        "revenueGrowth":                raw(fin, "revenueGrowth"),
        "profitMargins":                raw(fin, "profitMargins"),
    }


def get_price_data(ticker: str, days: int = 60) -> dict:
    key = f"price_{ticker}_{days}"
    if _fresh(key):
        return _cache[key]
    period = "3mo" if days <= 90 else "6mo"
    try:
        raw = _fetch_chart(ticker, period)
        df  = _parse_chart(raw, ticker)
        if len(df) < 10:
            return {"error": "Data tidak cukup"}
        close  = df["close"]
        volume = df["volume"]
        change_5d  = float(close.iloc[-1] / close.iloc[-6]  - 1) if len(close) >= 6  else 0.0
        change_10d = float(close.iloc[-1] / close.iloc[-11] - 1) if len(close) >= 11 else 0.0
        avg_vol    = float(volume.iloc[:-5].mean()) if len(volume) > 5 else float(volume.mean())
        recent_vol = float(volume.iloc[-5:].mean())
        vol_ratio  = recent_vol / avg_vol if avg_vol > 0 else 1.0
        ma20 = float(close.iloc[-20:].mean())
        ma50 = float(close.iloc[-50:].mean()) if len(close) >= 50 else ma20
        result = {
            "change_5d":     change_5d,
            "change_10d":    change_10d,
            "volume_ratio":  vol_ratio,
            "downtrend":     ma20 < ma50,
            "current_price": float(close.iloc[-1]),
            "fomo_signal":   change_5d > 0.10 or vol_ratio > 2.0,
            "loss_signal":   change_5d < -0.08 and ma20 < ma50,
            "_ts":           time.time(),
        }
        _cache[key] = result
        return result
    except ImportError:
        return {"error": "curl_cffi tidak terinstall — jalankan: pip install curl_cffi"}
    except Exception as e:
        return {"error": f"Gagal ambil data harga: {str(e)[:80]}"}


def get_current_price(ticker: str) -> dict:
    key = f"cur_{ticker}"
    if _fresh(key):
        return _cache[key]
    try:
        q = _fetch_quote(ticker)
        result = {
            "current_price": q.get("regularMarketPrice"),
            "change_pct":    q.get("regularMarketChangePercent"),
            "_ts":           time.time(),
        }
        _cache[key] = result
        return result
    except Exception:
        price = get_price_data(ticker, days=10)
        if "error" in price:
            return price
        return {
            "current_price": price.get("current_price"),
            "change_pct":    price.get("change_5d", 0) * 100,
            "_ts":           time.time(),
        }


def get_ticker_info(ticker: str) -> dict:
    key = f"info_{ticker}"
    if _fresh(key):
        return _cache[key]
    def fmt(v, mode=None):
        if v is None: return "N/A"
        if mode == "pct": return f"{v:.1%}"
        if mode == "2f": return f"{v:.2f}"
        return v
    try:
        q = _fetch_quote(ticker)
        result = {
            "P/E Ratio":      fmt(q.get("trailingPE"), "2f"),
            "Debt/Equity":    fmt(q.get("debtToEquity"), "2f"),
            "Revenue Growth": fmt(q.get("revenueGrowth"), "pct"),
            "Profit Margin":  fmt(q.get("profitMargins"), "pct"),
            "52W High":       fmt(q.get("fiftyTwoWeekHigh")),
            "52W Low":        fmt(q.get("fiftyTwoWeekLow")),
            "_ts":            time.time(),
        }
        _cache[key] = result
        return result
    except Exception:
        return {k: "N/A" for k in ["P/E Ratio","Debt/Equity","Revenue Growth","Profit Margin","52W High","52W Low"]}


def get_historical_df(ticker: str, start_year: int = 2015) -> pd.DataFrame:
    key = f"hist_{ticker}_{start_year}"
    if _fresh(key):
        return _cache[key].get("df", pd.DataFrame())
    try:
        raw = _fetch_chart(ticker, period="10y")
        df  = _parse_chart(raw, ticker)
        df  = df[df.index.year >= start_year]
        _cache[key] = {"df": df, "_ts": time.time()}
        return df
    except Exception:
        return pd.DataFrame()