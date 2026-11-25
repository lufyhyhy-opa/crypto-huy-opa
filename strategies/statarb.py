"""Strategy 4: Dollar-Neutral Statistical Arbitrage (Section 3.18).

Maximizes expected Sharpe ratio across a crypto basket subject to:
    sum(w_i) = 0   (dollar neutrality)
    sum(|w_i|) = 1 (unit gross exposure)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import BaseStrategy

DEFAULT_BASKET = [
    f"{c}/USDT:USDT"
    for c in ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "LINK", "DOT"]
]


class Strategy(BaseStrategy):
    symbols = list(DEFAULT_BASKET)
    timeframe = "1d"

    def __init__(
        self,
        symbols: list[str] | None = None,
        cov_window: int = 120,
        d: int = 3,
        ridge: float = 1e-4,
        signal_mode: str = "mean_reversion",
    ):
        if symbols is not None:
            self.symbols = list(symbols)
        self.cov_window = int(cov_window)
        self.d = int(d)
        self.ridge = float(ridge)
        self.signal_mode = signal_mode  # "mean_reversion", "momentum", or "zero"
        self.history = self.cov_window + self.d + 5

    def expected_returns(self, rets: pd.DataFrame) -> pd.Series:
        r = rets.iloc[-self.d :].sum()
        if self.signal_mode == "mean_reversion":
            return -(r - r.mean())
        if self.signal_mode == "momentum":
            return r - r.mean()
        if self.signal_mode == "zero":
            return pd.Series(0.0, index=rets.columns)
        raise ValueError(f"Unknown signal_mode: {self.signal_mode}")

    def target_weights(self, data: dict[str, pd.DataFrame]) -> dict[str, float]:
        closes = {s: data[s]["close"] for s in self.symbols if s in data}
        rets = pd.DataFrame(closes).pct_change().dropna().iloc[-self.cov_window :]
        if len(rets) < max(self.d + 2, 10):
            return {s: 0.0 for s in self.symbols}

        C = rets.cov().to_numpy(dtype=float).copy()
        C += self.ridge * np.eye(len(C))
        Cinv = np.linalg.pinv(C)

        E = self.expected_returns(rets).to_numpy(dtype=float)
        if np.allclose(E, 0.0):
            return {s: 0.0 for s in rets.columns}

        a = Cinv @ E                          # sum_j C^-1_ij E_j
        b = Cinv @ np.ones(len(E))            # sum_j C^-1_ij
        b_sum = float(b.sum())
        if abs(b_sum) < 1e-15:
            return {s: 0.0 for s in rets.columns}

        w = a - b * (float(a.sum()) / b_sum)  # exact dollar neutrality: sum(w) == 0
        gross = float(np.abs(w).sum())
        if gross < 1e-15:
            return {s: 0.0 for s in rets.columns}
        w = w / gross                         # unit gross exposure: sum(|w|) == 1
        return dict(zip(rets.columns, w.tolist()))
