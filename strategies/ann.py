"""Strategy 3: Artificial Neural Network Quantile Classifier (Section 18.2).

Written specifically for 15-minute Bitcoin candles in '151 Trading Strategies'
(based on Nakano, Takahashi & Takahashi, 2018).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.neural_network import MLPClassifier

from strategies.base import BaseStrategy

BARS_PER_DAY = 96  # 15m candles per day


def ema(x: pd.Series, lam: float, tau: int) -> pd.Series:
    w = (lam ** np.arange(tau)) * (1.0 - lam) / (1.0 - lam ** tau)
    return x.rolling(tau).apply(lambda a: float(np.dot(w, a[::-1])), raw=True)


def emsd(x: pd.Series, lam: float, tau: int) -> pd.Series:
    w = lam ** np.arange(tau)
    m_norm = (1.0 - lam) / (1.0 - lam ** tau)
    v_norm = (1.0 - lam) / (lam - lam ** tau)

    def _f(a: np.ndarray) -> float:
        a = a[::-1]
        m = float(np.dot(w, a)) * m_norm
        var = max(0.0, float(v_norm * np.dot(w, (a - m) ** 2)))
        return float(np.sqrt(var))

    return x.rolling(tau).apply(_f, raw=True)


def rsi(x: pd.Series, tau: int) -> pd.Series:
    up = x.clip(lower=0.0).rolling(tau).sum()
    dn = (-x).clip(lower=0.0).rolling(tau).sum()
    denom = (up + dn).replace(0.0, np.nan)
    return (up / denom).fillna(0.5)


class Strategy(BaseStrategy):
    symbols = ["BTC/USDT:USDT"]
    timeframe = "15m"

    def __init__(
        self,
        T1: int = BARS_PER_DAY,
        taus: tuple[int, ...] = (2, 4, 12, 24),
        rsi_taus: tuple[int, ...] = (12, 24, 48),
        K: int = 3,
        train_days: int = 60,
        retrain_every: int = BARS_PER_DAY,
        min_prob: float = 0.0,
        symbol: str | None = None,
    ):
        if symbol is not None:
            self.symbols = [symbol]
        self.T1 = int(T1)
        self.taus = tuple(taus)
        self.rsi_taus = tuple(rsi_taus)
        self.K = int(K)
        self.train = int(train_days * BARS_PER_DAY)
        self.retrain_every = int(retrain_every)
        self.min_prob = float(min_prob)
        self.history = self.train + self.T1 + max(self.taus + self.rsi_taus) + 10
        self.model: MLPClassifier | None = None
        self.q: np.ndarray | None = None
        self.bars_since_fit = 0
        self.pos = 0

    def rhat(self, close: pd.Series) -> pd.Series:
        R = close.pct_change()
        past = R.shift(1).rolling(self.T1)  # strictly past candles only
        std = past.std().replace(0.0, np.nan)
        return (R - past.mean()) / std

    def features(self, rh: pd.Series) -> pd.DataFrame:
        X = pd.DataFrame({"rhat": rh})
        for tau in self.taus:
            lam = 1.0 - 1.0 / tau
            X[f"ema{tau}"] = ema(rh, lam, tau)
            X[f"emsd{tau}"] = emsd(rh, lam, tau)
        for tau in self.rsi_taus:
            X[f"rsi{tau}"] = rsi(rh, tau)
        return X

    def fit(self, X: pd.DataFrame, rh: pd.Series) -> None:
        nxt = rh.shift(-1)  # target: quantile of the NEXT candle
        d = pd.concat([X, nxt.rename("y")], axis=1).dropna().iloc[-self.train :]
        if len(d) < 50:
            return
        self.q = np.quantile(d["y"], np.linspace(0.0, 1.0, self.K + 1)[1:-1])
        labels = np.searchsorted(self.q, d["y"].to_numpy(dtype=float), side="right")
        if len(np.unique(labels)) < 2:
            return
        self.model = MLPClassifier(
            hidden_layer_sizes=(32, 16),
            activation="relu",
            solver="sgd",
            learning_rate_init=0.01,
            momentum=0.9,
            max_iter=300,
            early_stopping=True,
            random_state=0,
        )
        self.model.fit(d[X.columns].to_numpy(dtype=float), labels)
        self.bars_since_fit = 0

    def target_weights(self, data: dict[str, pd.DataFrame]) -> dict[str, float]:
        sym = self.symbols[0]
        rh = self.rhat(data[sym]["close"])
        X = self.features(rh)
        if self.model is None or self.bars_since_fit >= self.retrain_every:
            self.fit(X, rh)
        self.bars_since_fit += 1

        if self.model is None or X.iloc[[-1]].isna().any().any():
            return {sym: float(self.pos)}

        probs = self.model.predict_proba(X.iloc[[-1]].to_numpy(dtype=float))[0]
        best_idx = int(np.argmax(probs))
        best_prob = float(probs[best_idx])
        top_class = int(self.model.classes_[best_idx])

        if best_prob >= self.min_prob:
            if top_class == self.K - 1:
                self.pos = 1
            elif top_class == 0:
                self.pos = -1
        return {sym: float(self.pos)}
