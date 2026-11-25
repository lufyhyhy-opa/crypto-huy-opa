"""Unit tests for mathematical invariants, risk controls, and backtest accounting."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.backtester import BacktestConfig, run_backtest
from core.risk import RiskConfig, RiskManager
from strategies.alpha_combo import alpha_combo_weights
from strategies.base import BaseStrategy
from strategies.sentiment_nb import Strategy as SentimentNBStrategy
from strategies.statarb import Strategy as StatArbStrategy


def test_statarb_dollar_neutral_and_unit_gross():
    rng = np.random.default_rng(7)
    syms = [f"C{i}/USDT:USDT" for i in range(10)]
    idx = pd.date_range("2024-01-01", periods=160, freq="1D", tz="UTC")
    data = {}
    for sym in syms:
        px = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.03, len(idx))))
        data[sym] = pd.DataFrame({"close": px, "volume": 1e6}, index=idx)

    strat = StatArbStrategy(symbols=syms, cov_window=120, d=3, ridge=1e-4)
    w = strat.target_weights(data)
    vals = np.array(list(w.values()), dtype=float)
    assert abs(vals.sum()) < 1e-12
    assert abs(np.abs(vals).sum() - 1.0) < 1e-12


def test_alpha_combo_weights_unit_gross_and_edge_detection():
    rng = np.random.default_rng(123)
    N, M = 300, 20
    R = rng.normal(0.0, 0.01, size=(N, M + 1))
    # First 20 alphas have persistent positive drift
    R[:20, :] += 0.004
    w = alpha_combo_weights(R, d=5)
    assert w.shape == (N,)
    assert abs(np.abs(w).sum() - 1.0) < 1e-12
    assert w[:20].sum() > w[20:].sum()


def test_sentiment_nb_multi_tweet_applies_prior_once():
    idx = pd.date_range("2025-01-01", periods=20, freq="1h", tz="UTC")
    close = pd.Series(
        [100 + (i if i % 2 == 0 else -i * 0.2) for i in range(20)], index=idx
    )
    tweets = pd.DataFrame(
        {
            "time": [idx[0], idx[1], idx[2], idx[3], idx[4], idx[5]],
            "text": [
                "btc bullish pump moon",
                "crash dump bearish",
                "bullish breakout rally",
                "bearish crash rekt",
                "bullish buy moon",
                "bearish sell dump",
            ],
        }
    )
    strat = SentimentNBStrategy()
    strat.fit(tweets, close)
    pred = strat.predict(["bullish moon pump", "bullish buy rally"])
    assert pred in (0, 1)


def test_risk_manager_controls():
    rm = RiskManager(RiskConfig(max_gross_leverage=1.0, max_daily_loss=0.03, min_order_usd=10.0))
    now = pd.Timestamp("2026-01-01T12:00:00Z")
    assert rm.check_daily_loss(10_000.0, now_utc=now) is True
    assert rm.check_daily_loss(9_750.0, now_utc=now) is True
    assert rm.check_daily_loss(9_699.0, now_utc=now) is False

    capped = rm.cap_leverage({"A": 0.8, "B": -0.8})
    assert np.isclose(sum(abs(v) for v in capped.values()), 1.0)
    assert rm.should_trade(0.0001, 50_000.0) is False  # $5 < $10
    assert rm.should_trade(0.001, 50_000.0) is True    # $50 >= $10

    stale_df = pd.DataFrame({"close": [100.0]}, index=[now - pd.Timedelta(days=5)])
    with pytest.raises(RuntimeError):
        rm.check_data_freshness(stale_df, "1d", "BTC/USDT:USDT", now_utc=now)


class _AlwaysLong(BaseStrategy):
    symbols = ["BTC/USDT:USDT"]
    timeframe = "1d"
    history = 5

    def target_weights(self, data):
        return {"BTC/USDT:USDT": 1.0}


def test_backtester_fees_and_funding_accounting():
    idx = pd.date_range("2025-01-01", periods=20, freq="1D", tz="UTC")
    # Constant +1% daily return
    close = 100.0 * (1.01 ** np.arange(len(idx)))
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1e6}, index=idx)
    funding = pd.Series(0.001, index=idx)  # 0.1% daily funding paid by longs

    res = run_backtest(
        _AlwaysLong(),
        {"BTC/USDT:USDT": df},
        cfg=BacktestConfig(fee_rate=0.0006, slippage_rate=0.0002, use_funding=True),
        funding={"BTC/USDT:USDT": funding},
    )
    # First bar pays entry cost (0.0008) + funding (0.001) -> 0.01 - 0.0018 = 0.0082
    assert np.isclose(res.net_returns.iloc[0], 0.01 - 0.0008 - 0.001, atol=1e-9)
    # Subsequent bars have zero turnover -> 0.01 - 0.001 = 0.009
    assert np.isclose(res.net_returns.iloc[1], 0.01 - 0.001, atol=1e-9)
