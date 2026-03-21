from price_fetcher import get_historical_df as _pf_hist, get_current_price as _pf_price
from fundamental_data import get_fundamental as _get_fundamental
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import streamlit as st

class CounterEvidenceEngine:

    def __init__(self, ticker: str):
        self.ticker = ticker
        self.data   = self._load_data()

    def _load_data(self) -> pd.DataFrame:
        return _pf_hist(self.ticker, start_year=2015)

    def get_counter_evidence(self,
                              bias_type: str,
                              threshold: float = 0.20,
                              window: int = 5,
                              forward_days: int = 30) -> dict:
        if bias_type == "FOMO":
            return self._fomo_evidence(threshold, window, forward_days)
        elif bias_type == "LOSS_AVERSION":
            return self._loss_aversion_evidence()
        elif bias_type == "CONFIRMATION_BIAS":
            return self._confirmation_bias_evidence()
        else:
            return {"status": "error", "message": "Bias type tidak dikenali"}

    def _fomo_evidence(self, threshold=0.20, window=5, forward_days=30) -> dict:
        data = self.data.copy()
        if len(data) < 60:
            return {"status": "insufficient_data", "episodes_found": 0, "message": "Data historis terlalu pendek."}

        close = data['close'].squeeze()
        data['return_5d']      = close.pct_change(window)
        data['forward_return'] = close.shift(-forward_days) / close - 1

        episodes = data[data['return_5d'] > threshold].copy()
        episodes = self._filter_consecutive(episodes, min_gap=5)

        if len(episodes) < 3:
            return {
                "status": "insufficient_data",
                "episodes_found": len(episodes),
                "message": f"Hanya {len(episodes)} episode serupa ditemukan. Minimum 3 untuk kalkulasi reliable."
            }

        corrections  = episodes[episodes['forward_return'] < 0]['forward_return']
        all_outcomes = episodes['forward_return'].dropna()

        return {
            "status": "ok",
            "bias_type": "FOMO",
            "ticker": self.ticker,
            "threshold": threshold,
            "window_days": window,
            "forward_days": forward_days,
            "episodes_found": len(episodes),
            "corrections_count": len(corrections),
            "correction_probability": len(corrections) / len(episodes) if len(episodes) > 0 else 0,
            "avg_correction": float(corrections.mean()) if len(corrections) > 0 else 0,
            "worst_correction": float(corrections.min()) if len(corrections) > 0 else 0,
            "best_outcome": float(all_outcomes.max()) if len(all_outcomes) > 0 else 0,
            "episode_dates": episodes.index.tolist(),
            "data_start": str(self.data.index[0].date()),
            "data_end":   str(self.data.index[-1].date()),
        }

    def _loss_aversion_evidence(self) -> dict:
        data = self.data.copy()
        if len(data) < 60:
            return {"status": "insufficient_data", "message": "Data historis terlalu pendek."}

        close = data['close'].squeeze()
        ma20  = close.rolling(20).mean()
        ma50  = close.rolling(50).mean()

        downtrend = data[ma20 < ma50].copy()
        downtrend = self._filter_consecutive(downtrend, min_gap=20)

        if len(downtrend) < 3:
            return {"status": "insufficient_data", "episodes_found": len(downtrend), "message": "Episode downtrend tidak cukup."}

        recovery_days  = []
        continued_down = 0

        for date in downtrend.index[:20]:
            entry_price  = float(close.loc[date])
            future_close = close[close.index > date].head(120)
            recovered    = future_close[future_close >= entry_price]

            if len(recovered) > 0:
                recovery_days.append((recovered.index[0] - date).days)
            else:
                continued_down += 1

        recovered_count = len(recovery_days)
        total_sampled   = recovered_count + continued_down

        return {
            "status": "ok",
            "bias_type": "LOSS_AVERSION",
            "ticker": self.ticker,
            "episodes_found": len(downtrend),
            "sampled": total_sampled,
            "recovered_count": recovered_count,
            "not_recovered_count": continued_down,
            "recovery_probability": recovered_count / total_sampled if total_sampled > 0 else 0,
            "avg_recovery_days": int(sum(recovery_days) / len(recovery_days)) if recovery_days else None,
            "data_start": str(self.data.index[0].date()),
            "data_end":   str(self.data.index[-1].date()),
        }

    def _confirmation_bias_evidence(self) -> dict:
        try:
            # ── 1. Harga terkini via curl_cffi ───────────────────────────
            price_result  = _pf_price(self.ticker)
            current_price = price_result.get("current_price")
            current_price_str = f"{current_price:,.0f}" if current_price else "N/A"

            # ── 2. 52W High/Low dari data historis lokal ──────────────────
            high_52w = low_52w = "N/A"
            if self.data is not None and not self.data.empty and "close" in self.data.columns:
                import datetime as _dt
                cutoff    = self.data.index[-1] - _dt.timedelta(days=365)
                last_year = self.data["close"][self.data.index >= cutoff]
                if not last_year.empty:
                    high_52w = f"{last_year.max():,.0f}"
                    low_52w  = f"{last_year.min():,.0f}"

            # ── 3. Fundamental dari database IDX (Q3 2025) ───────────────
            fund = _get_fundamental(self.ticker)

            return {
                "status": "ok",
                "bias_type": "CONFIRMATION_BIAS",
                "ticker": self.ticker,
                "fundamental": {
                    "Current Price":  current_price_str,
                    "52W High":       high_52w,
                    "52W Low":        low_52w,
                    "PE Ratio":       fund.get("PE Ratio", "N/A"),
                    "PBV":            fund.get("PBV", "N/A"),
                    "Debt/Equity":    fund.get("Debt/Equity", "N/A"),
                    "ROE":            fund.get("ROE", "N/A"),
                    "Revenue Growth": fund.get("Revenue Growth", "N/A"),
                    "Profit Margin":  fund.get("Profit Margin", "N/A"),
                    "Source":         fund.get("Source", "N/A"),
                },
                "questions": [
                    f"Apa risiko terbesar {self.ticker} saat ini?",
                    "Siapa yang sedang menjual dan mengapa?",
                    "Apa yang bisa membuktikan thesis ini salah?",
                    "Bagaimana performa saat IHSG turun 10%?",
                ]
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _filter_consecutive(self, df: pd.DataFrame, min_gap: int = 5) -> pd.DataFrame:
        if len(df) == 0:
            return df
        filtered = [df.index[0]]
        for idx in df.index[1:]:
            if (idx - filtered[-1]).days >= min_gap:
                filtered.append(idx)
        return df.loc[filtered]

    def plot_episodes(self, evidence: dict) -> None:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        if evidence.get("status") != "ok":
            return
        if evidence.get("bias_type") != "FOMO":
            return

        ep_dates = evidence.get("episode_dates", [])

        # Siapkan data OHLCV
        close  = self.data['close'].squeeze()
        open_  = self.data['open'].squeeze()
        high   = self.data['high'].squeeze()
        low    = self.data['low'].squeeze()
        volume = self.data['volume'].squeeze()
        dates  = self.data.index

        # Warna volume bar: hijau kalau naik, merah kalau turun
        colors = [
            '#26a69a' if c >= o else '#ef5350'
            for c, o in zip(close, open_)
        ]

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.75, 0.25]
        )

        # ── Candlestick ──────────────────────────────────────
        fig.add_trace(go.Candlestick(
            x=dates,
            open=open_,
            high=high,
            low=low,
            close=close,
            name='Harga',
            increasing=dict(line=dict(color='#26a69a'), fillcolor='#26a69a'),
            decreasing=dict(line=dict(color='#ef5350'), fillcolor='#ef5350'),
            hovertext=[
                f"O: {o:,.0f} H: {h:,.0f} L: {l:,.0f} C: {c:,.0f}"
                for o, h, l, c in zip(open_, high, low, close)
            ],
        ), row=1, col=1)

        # ── Episode markers ──────────────────────────────────
        for d in ep_dates:
            fig.add_vline(
                x=d,
                line_color='#FF4B4B',
                line_width=1,
                opacity=0.5,
                row=1, col=1
            )

        # ── Volume bars ──────────────────────────────────────
        fig.add_trace(go.Bar(
            x=dates,
            y=volume,
            name='volume',
            marker_color=colors,
            opacity=0.7,
            hovertemplate='%{x|%d %b %Y}<br>Vol: %{y:,.0f}<extra></extra>'
        ), row=2, col=1)

        # ── Default view: last 6 months ──────────────────────
        import pandas as pd
        x_end   = dates[-1]
        x_start = x_end - pd.DateOffset(months=6)

        # Price range for default 6-month window (adaptive, never negative)
        mask       = (dates >= x_start)
        vis_low    = float(low[mask].min())  if mask.any() else float(low.min())
        vis_high   = float(high[mask].max()) if mask.any() else float(high.max())
        pad        = (vis_high - vis_low) * 0.05
        y_lo       = max(0, vis_low  - pad)
        y_hi       = vis_high + pad

        # ── Layout ───────────────────────────────────────────
        fig.update_layout(
            title=dict(
                text=f"Episode Serupa — {self.ticker} "
                    f"({len(ep_dates)} kejadian ditandai merah)",
                font=dict(color='white', size=14)
            ),
            paper_bgcolor='#0E1117',
            plot_bgcolor='#0E1117',
            font=dict(color='white'),
            xaxis=dict(
                showgrid=True,
                gridcolor='#2a2a2a',
                color='white',
                rangeslider=dict(visible=False),
                range=[x_start, x_end],
                rangeselector=dict(
                    buttons=[
                        dict(count=6, label="6B", step="month", stepmode="backward"),
                        dict(count=1, label="1T", step="year",  stepmode="backward"),
                        dict(count=2, label="2T", step="year",  stepmode="backward"),
                        dict(step="all", label="Semua")
                    ],
                    bgcolor='#1E1E1E',
                    activecolor='#4DA8DA',
                    font=dict(color='white')
                )
            ),
            xaxis2=dict(
                showgrid=True,
                gridcolor='#2a2a2a',
                color='white',
                range=[x_start, x_end],
                rangeslider=dict(visible=True)
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='#2a2a2a',
                color='white',
                title='Harga (IDR)',
                tickformat=',.0f',
                range=[y_lo, y_hi],
                rangemode='nonnegative',
                autorange=False,
            ),
            yaxis2=dict(
                showgrid=True,
                gridcolor='#2a2a2a',
                color='white',
                title='volume',
                tickformat='.2s',
                rangemode='nonnegative',
            ),
            hovermode='x unified',
            height=580,
            margin=dict(l=60, r=20, t=60, b=60),
            legend=dict(bgcolor='#1E1E1E', font=dict(color='white')),
            xaxis_rangeslider_visible=False,
        )

        # Keep y-axis adaptive when user zooms/pans via relayout
        fig.update_layout(yaxis_autorange=False)

        st.plotly_chart(fig, width='stretch')

    def plot_ma_chart(self) -> None:
        import plotly.graph_objects as go

        close = self.data['close'].squeeze()
        ma20  = close.rolling(20).mean()
        ma50  = close.rolling(50).mean()
        dates = self.data.index

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=dates,
            y=close,
            mode='lines',
            name='Harga',
            line=dict(color='#4DA8DA', width=1.2),
            hovertemplate='%{x|%d %b %Y}<br>Rp %{y:,.0f}<extra></extra>'
        ))

        fig.add_trace(go.Scatter(
            x=dates,
            y=ma20,
            mode='lines',
            name='MA 20',
            line=dict(color='#FFD166', width=1.5, dash='dash'),
            hovertemplate='MA20: Rp %{y:,.0f}<extra></extra>'
        ))

        fig.add_trace(go.Scatter(
            x=dates,
            y=ma50,
            mode='lines',
            name='MA 50',
            line=dict(color='#FF4B4B', width=1.5, dash='dash'),
            hovertemplate='MA50: Rp %{y:,.0f}<extra></extra>'
        ))

        import pandas as pd
        x_end   = dates[-1]
        x_start = x_end - pd.DateOffset(months=6)

        mask    = (dates >= x_start)
        vis_lo  = float(close[mask].min()) if mask.any() else float(close.min())
        vis_hi  = float(close[mask].max()) if mask.any() else float(close.max())
        pad     = (vis_hi - vis_lo) * 0.08
        y_lo    = max(0, vis_lo - pad)
        y_hi    = vis_hi + pad

        fig.update_layout(
            title=dict(
                text=f"Harga & Moving Average — {self.ticker}",
                font=dict(color='white', size=14)
            ),
            paper_bgcolor='#0E1117',
            plot_bgcolor='#0E1117',
            font=dict(color='white'),
            xaxis=dict(
                showgrid=True,
                gridcolor='#2a2a2a',
                color='white',
                range=[x_start, x_end],
                rangeslider=dict(visible=True),
                rangeselector=dict(
                    buttons=[
                        dict(count=6, label="6B", step="month", stepmode="backward"),
                        dict(count=1, label="1T", step="year",  stepmode="backward"),
                        dict(count=2, label="2T", step="year",  stepmode="backward"),
                        dict(step="all", label="Semua")
                    ],
                    bgcolor='#1E1E1E',
                    activecolor='#4DA8DA',
                    font=dict(color='white')
                )
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='#2a2a2a',
                color='white',
                title='Harga (IDR)',
                tickformat=',.0f',
                range=[y_lo, y_hi],
                rangemode='nonnegative',
                autorange=False,
            ),
            hovermode='x unified',
            height=480,
            margin=dict(l=60, r=20, t=60, b=60),
            legend=dict(bgcolor='#1E1E1E', font=dict(color='white'))
        )

        st.plotly_chart(fig, width='stretch')


if __name__ == "__main__":
    test_cases = [
        ("GOTO.JK", "FOMO"),
        ("UNVR.JK", "LOSS_AVERSION"),
        ("BBRI.JK", "CONFIRMATION_BIAS"),
    ]
    print("Testing counter_evidence.py...")
    print("=" * 45)
    for ticker, bias in test_cases:
        print(f"\n{ticker} — {bias}")
        engine = CounterEvidenceEngine(ticker)
        result = engine.get_counter_evidence(bias)
        if result['status'] == 'ok':
            print(f"  ✅ Status: ok")
            if bias == "FOMO":
                print(f"  Episodes   : {result['episodes_found']}")
                print(f"  Probability: {result['correction_probability']:.0%}")
            elif bias == "LOSS_AVERSION":
                print(f"  Episodes  : {result['episodes_found']}")
                print(f"  Avg days  : {result['avg_recovery_days']}")
            elif bias == "CONFIRMATION_BIAS":
                for k, v in result['fundamental'].items():
                    print(f"    {k:20}: {v}")
        else:
            print(f"  ⚠️  {result.get('message', '')}")
    print("\n" + "=" * 45)
    print("Test selesai.")