"""Step-by-step causal backtest engine with fees, slippage, funding, and IS/OOS splits."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from core.metrics import compute_metrics
from core.risk import RiskConfig, RiskManager


@dataclass
class BacktestConfig:
    fee_rate: float = 0.0006
    slippage_rate: float = 0.0002
    max_gross_leverage: float = 1.0
    train_ratio: float = 0.60
    use_funding: bool = True


@dataclass
class BacktestResult:
    strategy_name: str
    timeframe: str
    gross_returns: pd.Series
    net_returns: pd.Series
    weights: pd.DataFrame
    equity_curve: pd.Series
    metrics_full: dict[str, Any]
    metrics_is: dict[str, Any]
    metrics_oos: dict[str, Any]
    benchmark_full: dict[str, Any]
    benchmark_is: dict[str, Any]
    benchmark_oos: dict[str, Any]
    split_timestamp: pd.Timestamp | None


def _align_funding_to_bars(
    funding_map: dict[str, pd.Series] | None,
    index: pd.DatetimeIndex,
    symbols: list[str],
) -> pd.DataFrame:
    """Sum funding rates occurring between bar t and bar t+1 for each symbol."""
    out = pd.DataFrame(0.0, index=index, columns=symbols)
    if not funding_map or len(index) < 2:
        return out
    for sym in symbols:
        s = funding_map.get(sym)
        if s is None or s.empty:
            continue
        s = s.sort_index()
        # Map each funding timestamp to the bar that closes at or after it
        pos = index.searchsorted(s.index, side="left")
        valid = (pos > 0) & (pos < len(index))
        if not np.any(valid):
            continue
        grouped = pd.Series(s.to_numpy()[valid], index=index[pos[valid]]).groupby(level=0).sum()
        out.loc[grouped.index, sym] = grouped.to_numpy()
    return out


def run_backtest(
    strategy: Any,
    data: dict[str, pd.DataFrame],
    cfg: BacktestConfig | None = None,
    funding: dict[str, pd.Series] | None = None,
    benchmark_symbol: str | None = None,
    fresh_copy: bool = True,
) -> BacktestResult:
    """Run a strictly causal bar-by-bar backtest for any Strategy plugin."""
    cfg = cfg or BacktestConfig()
    strat = copy.deepcopy(strategy) if fresh_copy else strategy
    symbols = list(strat.symbols)
    timeframe = strat.timeframe

    # Build common timestamp index across all required symbols
    common_idx: pd.DatetimeIndex | None = None
    for sym in symbols:
        idx = data[sym].index
        common_idx = idx if common_idx is None else common_idx.intersection(idx)
    if common_idx is None or len(common_idx) <= strat.history + 2:
        raise ValueError(
            f"Insufficient aligned bars ({0 if common_idx is None else len(common_idx)}) "
            f"for strategy history={strat.history}"
        )
    common_idx = common_idx.sort_values()

    aligned_data = {sym: data[sym].loc[common_idx] for sym in symbols}
    close_df = pd.DataFrame({sym: aligned_data[sym]["close"] for sym in symbols}, index=common_idx)
    next_ret_df = close_df.pct_change().shift(-1)  # return earned from bar t to bar t+1

    funding_df = (
        _align_funding_to_bars(funding, common_idx, symbols)
        if cfg.use_funding
        else pd.DataFrame(0.0, index=common_idx, columns=symbols)
    )

    risk = RiskManager(RiskConfig(max_gross_leverage=cfg.max_gross_leverage))
    start_i = int(strat.history)
    end_i = len(common_idx) - 1  # last bar has no next-bar return

    weight_rows: list[dict[str, float]] = []
    timestamps: list[pd.Timestamp] = []
    gross_list: list[float] = []
    net_list: list[float] = []
    prev_w = {sym: 0.0 for sym in symbols}
    cost_rate = cfg.fee_rate + cfg.slippage_rate

    for i in range(start_i, end_i):
        # Strictly causal slice: only bars [0..i] are visible
        window_data = {sym: aligned_data[sym].iloc[: i + 1] for sym in symbols}
        raw_w = strat.target_weights(window_data)
        capped_w = risk.cap_leverage({sym: float(raw_w.get(sym, 0.0)) for sym in symbols})

        turnover = sum(abs(capped_w[sym] - prev_w[sym]) for sym in symbols)
        bar_gross = sum(capped_w[sym] * float(next_ret_df.iloc[i][sym]) for sym in symbols)
        # Funding at bar i+1 is paid by longs, received by shorts
        bar_funding = sum(capped_w[sym] * float(funding_df.iloc[i + 1][sym]) for sym in symbols)
        bar_net = bar_gross - turnover * cost_rate - bar_funding

        timestamps.append(common_idx[i + 1])
        weight_rows.append(capped_w)
        gross_list.append(bar_gross)
        net_list.append(bar_net)
        prev_w = capped_w

    res_idx = pd.DatetimeIndex(timestamps)
    weights_df = pd.DataFrame(weight_rows, index=res_idx)
    gross_returns = pd.Series(gross_list, index=res_idx, name="gross_return")
    net_returns = pd.Series(net_list, index=res_idx, name="net_return")
    equity_curve = (1.0 + net_returns).cumprod().rename("equity")

    # Benchmark series (default: BTC/USDT:USDT or first symbol)
    bench_sym = benchmark_symbol or (
        "BTC/USDT:USDT" if "BTC/USDT:USDT" in data else symbols[0]
    )
    bench_ret = data[bench_sym]["close"].pct_change().reindex(res_idx).fillna(0.0)

    # 60 / 40 IS / OOS split
    split_pos = int(len(res_idx) * cfg.train_ratio)
    split_ts = res_idx[split_pos] if 0 < split_pos < len(res_idx) else None

    is_net = net_returns.iloc[:split_pos]
    oos_net = net_returns.iloc[split_pos:]
    is_w = weights_df.iloc[:split_pos]
    oos_w = weights_df.iloc[split_pos:]
    is_bench = bench_ret.iloc[:split_pos]
    oos_bench = bench_ret.iloc[split_pos:]

    return BacktestResult(
        strategy_name=type(strat).__module__.split(".")[-1],
        timeframe=timeframe,
        gross_returns=gross_returns,
        net_returns=net_returns,
        weights=weights_df,
        equity_curve=equity_curve,
        metrics_full=compute_metrics(net_returns, weights_df, bench_ret, timeframe),
        metrics_is=compute_metrics(is_net, is_w, is_bench, timeframe),
        metrics_oos=compute_metrics(oos_net, oos_w, oos_bench, timeframe),
        benchmark_full=compute_metrics(bench_ret, None, bench_ret, timeframe),
        benchmark_is=compute_metrics(is_bench, None, is_bench, timeframe),
        benchmark_oos=compute_metrics(oos_bench, None, oos_bench, timeframe),
        split_timestamp=split_ts,
    )
