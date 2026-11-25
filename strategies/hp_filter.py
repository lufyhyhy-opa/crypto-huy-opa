"""Strategy 1: Hodrick-Prescott Filter Moving Averages (Section 8.1).

Strictly causal: runs the two-sided HP filter ONLY on the trailing past window
for each point and keeps only the final endpoint to eliminate look-ahead bias.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.filters.hp_filter import hpfilter

from strategies.base import BaseStrategy


class Strategy(BaseStrategy):
    symbols = ["BTC/USDT:USDT"]
    timeframe = "1d"

    def __init__(
        self,
        window: int = 365,
        t1: int = 10,
        t2: int = 30,
        n_per_year: int = 365,
        lam: float | None = None,
        symbol: str | None = None,
    ):
        if symbol is not None:
            self.symbols = [symbol]
        self.window = int(window)
        self.t1 = int(t1)
        self.t2 = int(t2)
        # Book heuristic (Sec. 8.1): lambda = 100 * n^2
        self.lam = float(lam) if lam is not None else float(100 * (n_per_year ** 2))
        self.history = self.window + self.t2 + 5

    def causal_trend(self, close: pd.Series) -> pd.Series:
        """Compute causal HP trend S*(t) using only past bars [t-window : t]."""
        s = close.to_numpy(dtype=float)
        out = np.full(len(s), np.nan)
        for t in range(self.window, len(s) + 1):
            _, tr = hpfilter(s[t - self.window : t], lamb=self.lam)
            out[t - 1] = tr[-1]
        return pd.Series(out, index=close.index)

    def target_weights(self, data: dict[str, pd.DataFrame]) -> dict[str, float]:
        sym = self.symbols[0]
        close = data[sym]["close"].iloc[-(self.window + self.t2) :]
        s_star = self.causal_trend(close).dropna()
        if len(s_star) < self.t2:
            return {sym: 0.0}
        ma1 = float(s_star.iloc[-self.t1 :].mean())
        ma2 = float(s_star.iloc[-self.t2 :].mean())
        return {sym: 1.0 if ma1 > ma2 else -1.0}
