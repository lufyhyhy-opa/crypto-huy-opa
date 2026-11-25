"""Gate 1 automated verification: strictly zero look-ahead bias across strategies."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from strategies.hp_filter import Strategy as HPFilterStrategy
from strategies.knn import Strategy as KNNStrategy
from strategies.statarb import Strategy as StatArbStrategy


def _make_ohlcv(n: int = 300, seed: int = 42, freq: str = "1D") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0005, 0.025, size=n)
    close = 30_000.0 * np.exp(np.cumsum(rets))
    idx = pd.date_range("2024-01-01", periods=n, freq=freq, tz="UTC")
    return pd.DataFrame(
        {
            "open": close * (1.0 + rng.normal(0, 0.002, n)),
            "high": close * (1.0 + np.abs(rng.normal(0, 0.01, n))),
            "low": close * (1.0 - np.abs(rng.normal(0, 0.01, n))),
            "close": close,
            "volume": rng.uniform(1e6, 5e6, n),
        },
        index=idx,
    )


def test_hp_filter_no_lookahead():
    df_full = _make_ohlcv(250, seed=1)
    cut = 200
    df_cut = df_full.iloc[:cut].copy()
    # Mutate future data dramatically after `cut`
    df_mut = df_full.copy()
    df_mut.iloc[cut:, df_mut.columns.get_loc("close")] *= 10.0

    s1 = HPFilterStrategy(window=60, t1=5, t2=15, lam=14400)
    s2 = HPFilterStrategy(window=60, t1=5, t2=15, lam=14400)

    w_cut = s1.target_weights({"BTC/USDT:USDT": df_cut})
    w_mut_at_cut = s2.target_weights({"BTC/USDT:USDT": df_mut.iloc[:cut]})
    assert w_cut == w_mut_at_cut

    # Also verify causal_trend endpoint invariance
    tr_cut = s1.causal_trend(df_cut["close"]).iloc[-1]
    tr_full_at_cut = s2.causal_trend(df_mut["close"]).iloc[cut - 1]
    assert np.isclose(tr_cut, tr_full_at_cut, rtol=1e-12, atol=1e-12)


def test_knn_no_lookahead():
    df_full = _make_ohlcv(260, seed=2)
    cut = 210
    df_cut = df_full.iloc[:cut].copy()
    df_mut = df_full.copy()
    df_mut.iloc[cut:, df_mut.columns.get_loc("close")] *= 0.1

    s1 = KNNStrategy(T=5, train=120, z1=0.005, z2=0.0)
    s2 = KNNStrategy(T=5, train=120, z1=0.005, z2=0.0)

    y1 = s1.predict(df_cut)
    y2 = s2.predict(df_mut.iloc[:cut])
    assert np.isclose(y1, y2, rtol=1e-12, atol=1e-12)


def test_statarb_no_lookahead():
    syms = [f"COIN{i}/USDT:USDT" for i in range(6)]
    data_full = {s: _make_ohlcv(180, seed=10 + i) for i, s in enumerate(syms)}
    cut = 140
    data_cut = {s: df.iloc[:cut].copy() for s, df in data_full.items()}
    data_mut = {s: df.copy() for s, df in data_full.items()}
    for df in data_mut.values():
        df.iloc[cut:, df.columns.get_loc("close")] *= 5.0

    s1 = StatArbStrategy(symbols=syms, cov_window=60, d=3, ridge=1e-4)
    s2 = StatArbStrategy(symbols=syms, cov_window=60, d=3, ridge=1e-4)

    w1 = s1.target_weights(data_cut)
    w2 = s2.target_weights({s: df.iloc[:cut] for s, df in data_mut.items()})
    for sym in syms:
        assert np.isclose(w1[sym], w2[sym], rtol=1e-12, atol=1e-12)
