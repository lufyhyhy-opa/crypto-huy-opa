"""Performance and risk metrics for strategy evaluation."""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from core.config import BARS_PER_YEAR


def compute_metrics(
    returns: pd.Series,
    weights_df: pd.DataFrame | None = None,
    benchmark_returns: pd.Series | None = None,
    timeframe: str = "1d",
) -> dict[str, Any]:
    """Compute standard quant metrics from a series of bar-by-bar net returns."""
    r = returns.dropna().astype(float)
    n = len(r)
    if n == 0:
        return {
            "bars": 0,
            "total_return": 0.0,
            "cagr": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown": 0.0,
            "calmar": 0.0,
            "win_rate": 0.0,
            "avg_daily_turnover": 0.0,
            "trade_count": 0,
            "time_in_market": 0.0,
            "btc_beta": float("nan"),
        }

    ann = BARS_PER_YEAR.get(timeframe, 365)
    equity = (1.0 + r).cumprod()
    total_return = float(equity.iloc[-1] - 1.0)
    years = max(n / ann, 1e-9)
    cagr = float(equity.iloc[-1] ** (1.0 / years) - 1.0) if equity.iloc[-1] > 0 else -1.0

    std = float(r.std(ddof=1)) if n > 1 else 0.0
    sharpe = float((r.mean() / std) * math.sqrt(ann)) if std > 1e-12 else 0.0

    downside = r[r < 0.0]
    down_std = float(downside.std(ddof=1)) if len(downside) > 1 else 0.0
    sortino = float((r.mean() / down_std) * math.sqrt(ann)) if down_std > 1e-12 else 0.0

    peak = equity.cummax()
    dd = equity / peak - 1.0
    max_drawdown = float(dd.min())
    calmar = float(cagr / abs(max_drawdown)) if max_drawdown < -1e-12 else 0.0

    active = r[r != 0.0]
    win_rate = float((active > 0.0).mean()) if len(active) > 0 else 0.0

    avg_turnover = 0.0
    trade_count = 0
    time_in_market = 0.0
    if weights_df is not None and not weights_df.empty:
        w = weights_df.reindex(r.index).fillna(0.0)
        dw = w.diff().abs()
        dw.iloc[0] = w.iloc[0].abs()
        bar_turnover = dw.sum(axis=1)
        bars_per_day = ann / 365.0
        avg_turnover = float(bar_turnover.mean() * bars_per_day)
        trade_count = int((bar_turnover > 1e-6).sum())
        time_in_market = float((w.abs().sum(axis=1) > 1e-6).mean())

    btc_beta = float("nan")
    if benchmark_returns is not None:
        aligned = pd.concat([r.rename("s"), benchmark_returns.rename("b")], axis=1).dropna()
        if len(aligned) > 2 and aligned["b"].var() > 1e-12:
            btc_beta = float(aligned["s"].cov(aligned["b"]) / aligned["b"].var())

    return {
        "bars": n,
        "total_return": round(total_return, 4),
        "cagr": round(cagr, 4),
        "sharpe": round(sharpe, 3),
        "sortino": round(sortino, 3),
        "max_drawdown": round(max_drawdown, 4),
        "calmar": round(calmar, 3),
        "win_rate": round(win_rate, 4),
        "avg_daily_turnover": round(avg_turnover, 4),
        "trade_count": trade_count,
        "time_in_market": round(time_in_market, 4),
        "btc_beta": round(btc_beta, 3) if not math.isnan(btc_beta) else None,
    }
