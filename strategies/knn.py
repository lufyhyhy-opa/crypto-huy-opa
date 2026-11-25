"""Strategy 2: k-Nearest Neighbors Pattern Matching (Section 3.17).

Normalizes relative price MAs and relative volume MAs to [0, 1] using ONLY the
training window min/max, then forecasts T-bar forward return via Euclidean kNN.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from sklearn.neighbors import KNeighborsRegressor

from strategies.base import BaseStrategy


class Strategy(BaseStrategy):
    symbols = ["BTC/USDT:USDT"]
    timeframe = "1d"

    def __init__(
        self,
        T: int = 5,
        price_w: tuple[int, ...] = (5, 20, 60),
        vol_w: tuple[int, ...] = (5, 20),
        train: int = 730,
        z1: float = 0.01,
        z2: float = 0.0,
        k: int | None = None,
        weights: str = "uniform",
        symbol: str | None = None,
    ):
        if symbol is not None:
            self.symbols = [symbol]
        self.T = int(T)
        self.price_w = tuple(price_w)
        self.vol_w = tuple(vol_w)
        self.train = int(train)
        self.z1 = float(z1)
        self.z2 = float(z2)
        self.k_override = k
        self.weights = weights  # "uniform" or "distance"
        self.history = self.train + max(self.price_w + self.vol_w + (60,)) + self.T + 5
        self.pos = 0

    def features(self, df: pd.DataFrame) -> pd.DataFrame:
        p, v = df["close"], df["volume"]
        X = pd.DataFrame(index=df.index)
        for w in self.price_w:
            X[f"p{w}"] = p.rolling(w).mean() / p - 1.0
        vol_base = v.rolling(60).mean().replace(0.0, np.nan)
        for w in self.vol_w:
            X[f"v{w}"] = v.rolling(w).mean() / vol_base
        return X

    def predict(self, df: pd.DataFrame) -> float:
        X = self.features(df)
        Y = df["close"].shift(-self.T) / df["close"] - 1.0
        # dropna() removes the last T rows whose future target Y is unknown -> zero leakage
        hist = pd.concat([X, Y.rename("Y")], axis=1).dropna().iloc[-self.train :]
        if len(hist) < 10:
            return 0.0
        cols = list(X.columns)
        lo = hist[cols].min()
        hi = hist[cols].max()
        span = (hi - lo).replace(0.0, 1.0)

        def norm(Z: pd.DataFrame) -> np.ndarray:
            return ((Z - lo) / span).to_numpy(dtype=float)

        k = (
            int(self.k_override)
            if self.k_override is not None
            else max(1, int(math.floor(math.sqrt(len(hist)))))
        )
        k = min(k, len(hist))
        model = KNeighborsRegressor(n_neighbors=k, weights=self.weights, metric="euclidean")
        model.fit(norm(hist[cols]), hist["Y"].to_numpy(dtype=float))
        x_now = X.iloc[[-1]]
        if x_now.isna().any().any():
            return 0.0
        return float(model.predict(norm(x_now))[0])

    def target_weights(self, data: dict[str, pd.DataFrame]) -> dict[str, float]:
        sym = self.symbols[0]
        y_hat = self.predict(data[sym])
        if self.pos == 1 and y_hat <= self.z2:
            self.pos = 0
        if self.pos == -1 and y_hat >= -self.z2:
            self.pos = 0
        if self.pos == 0:
            if y_hat > self.z1:
                self.pos = 1
            elif y_hat < -self.z1:
                self.pos = -1
        return {sym: float(self.pos)}
