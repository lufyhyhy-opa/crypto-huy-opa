"""Finale: Alpha Combo — Kakushadze-Yu 11-Step Procedure (Section 3.20).

Combines N alpha return streams over M+1 historical periods (with N > M - 1)
by cross-sectionally regressing volatility-normalized expected alpha returns
onto demeaned historical factor loadings without intercept.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import BaseStrategy


def alpha_combo_weights(R: np.ndarray, d: int = 5) -> np.ndarray:
    """
    Compute Kakushadze-Yu alpha combination weights.

    Parameters
    ----------
    R : np.ndarray of shape (N, M + 1)
        Historical returns of N alphas across M + 1 periods.
        Column 0 MUST be the most recent period (book convention).
    d : int
        Lookback window for expected alpha return E_i = mean(R[i, :d]).

    Returns
    -------
    np.ndarray of shape (N,)
        Normalized alpha weights with sum(|w|) == 1.
    """
    R = np.asarray(R, dtype=float)
    if R.ndim != 2:
        raise ValueError("R must be a 2D array of shape (N_alphas, M + 1)")
    N, M1 = R.shape
    M = M1 - 1
    if M < 2:
        raise ValueError("Need at least 3 periods (M >= 2)")
    if N <= M - 1:
        raise ValueError(f"Need more alphas than M-1 periods (got N={N}, M-1={M-1})")

    # Steps 1-2: serial demeaning
    X = R - R.mean(axis=1, keepdims=True)
    # Step 3: sample standard deviation
    sigma = np.sqrt((X ** 2).sum(axis=1) / M)
    sigma = np.where(sigma < 1e-12, 1e-12, sigma)
    # Steps 4-5: normalize and keep first M columns
    Y = (X / sigma[:, None])[:, :M]
    # Steps 6-7: cross-sectional demeaning and keep first M-1 columns
    Lam = (Y - Y.mean(axis=0, keepdims=True))[:, : M - 1]
    # Step 8: expected alpha return normalized by sigma
    d_eff = min(max(int(d), 1), M1)
    E_tilde = R[:, :d_eff].mean(axis=1) / sigma
    # Step 9: OLS regression of E_tilde on Lam without intercept -> residuals
    beta, *_ = np.linalg.lstsq(Lam, E_tilde, rcond=None)
    eps = E_tilde - Lam @ beta
    # Steps 10-11: rescale by 1/sigma and normalize sum(|w|) = 1
    w = eps / sigma
    gross = float(np.abs(w).sum())
    if gross < 1e-15:
        return np.zeros(N, dtype=float)
    return w / gross


def combine_positions(
    alpha_positions: list[dict[str, float]], weights: np.ndarray
) -> dict[str, float]:
    """Blend each alpha's position dict {symbol: weight} using alpha_combo weights."""
    total: dict[str, float] = {}
    for wi, pos in zip(weights, alpha_positions):
        w_val = float(wi)
        for sym, x in pos.items():
            total[sym] = total.get(sym, 0.0) + w_val * float(x)
    return total


class AlphaComboStrategy(BaseStrategy):
    """Wraps a bank of precomputed alpha return & position streams into a Strategy."""

    def __init__(
        self,
        alpha_returns_df: pd.DataFrame,
        alpha_weights_map: dict[str, pd.DataFrame],
        symbols: list[str],
        timeframe: str = "1d",
        M: int = 20,
        d: int = 5,
    ):
        self.alpha_returns_df = alpha_returns_df  # index=ts, columns=alpha_names
        self.alpha_weights_map = alpha_weights_map  # alpha_name -> DataFrame(index=ts, cols=symbols)
        self.symbols = list(symbols)
        self.timeframe = timeframe
        self.M = int(M)
        self.d = int(d)
        self.history = self.M + 2

    def target_weights(self, data: dict[str, pd.DataFrame]) -> dict[str, float]:
        sym0 = self.symbols[0]
        as_of = data[sym0].index[-1]
        past_rets = self.alpha_returns_df.loc[:as_of].iloc[-(self.M + 1) :]
        if len(past_rets) < self.M + 1:
            return {s: 0.0 for s in self.symbols}

        # Reverse time so column 0 is the most recent period
        R = past_rets.to_numpy(dtype=float).T[:, ::-1]
        w_alpha = alpha_combo_weights(R, d=self.d)

        pos_list: list[dict[str, float]] = []
        for col in past_rets.columns:
            w_df = self.alpha_weights_map[col]
            if as_of in w_df.index:
                row = w_df.loc[as_of]
                pos_list.append({s: float(row.get(s, 0.0)) for s in self.symbols})
            else:
                pos_list.append({s: 0.0 for s in self.symbols})

        blended = combine_positions(pos_list, w_alpha)
        gross = sum(abs(v) for v in blended.values())
        if gross > 1.0:
            blended = {k: v / gross for k, v in blended.items()}
        return blended
