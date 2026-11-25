"""Phase 2 & Phase 4 Research Runner: Data Download, 6-Gates Grid Search & Alpha Combo.

Usage:
    .venv/bin/python research/run_research.py
    .venv/bin/python research/run_research.py --exchange binance
"""
from __future__ import annotations

import argparse
import itertools
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from core.backtester import BacktestConfig, run_backtest
from core.config import PROJECT_ROOT, load_config
from core.data_loader import fetch_funding_history, fetch_ohlcv_history
from core.metrics import compute_metrics
from strategies.alpha_combo import AlphaComboStrategy
from strategies.hp_filter import Strategy as HPFilterStrategy
from strategies.knn import Strategy as KNNStrategy
from strategies.statarb import DEFAULT_BASKET, Strategy as StatArbStrategy

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("research")


def download_all_data(exchange_id: str, days_btc: int = 1825, days_basket: int = 1200):
    """Download 1d OHLCV and funding rates for BTC and the 10-coin basket."""
    btc_sym = "BTC/USDT:USDT"
    data: dict[str, pd.DataFrame] = {}
    funding: dict[str, pd.Series] = {}

    data[btc_sym] = fetch_ohlcv_history(btc_sym, timeframe="1d", days=days_btc, exchange_id=exchange_id)
    funding[btc_sym] = fetch_funding_history(btc_sym, days=days_btc, exchange_id=exchange_id)

    for sym in DEFAULT_BASKET:
        if sym == btc_sym:
            continue
        try:
            data[sym] = fetch_ohlcv_history(sym, timeframe="1d", days=days_basket, exchange_id=exchange_id)
            funding[sym] = fetch_funding_history(sym, days=days_basket, exchange_id=exchange_id)
        except Exception as exc:
            log.warning("Skipping %s due to fetch error: %s", sym, exc)

    return data, funding


def eval_grid(
    name: str,
    configs: list[dict[str, Any]],
    builder,
    data: dict[str, pd.DataFrame],
    funding: dict[str, pd.Series],
    bt_cfg: BacktestConfig,
):
    """Evaluate a parameter grid, selecting best by IS Sharpe and reporting OOS & plateau."""
    rows = []
    alpha_returns: dict[str, pd.Series] = {}
    alpha_weights: dict[str, pd.DataFrame] = {}

    for idx, params in enumerate(configs):
        strat = builder(**params)
        res = run_backtest(strat, data, cfg=bt_cfg, funding=funding)
        alpha_id = f"{name}_{idx}"
        alpha_returns[alpha_id] = res.net_returns
        alpha_weights[alpha_id] = res.weights
        rows.append(
            {
                "alpha_id": alpha_id,
                "params": params,
                "is": res.metrics_is,
                "oos": res.metrics_oos,
                "full": res.metrics_full,
                "bench_oos": res.benchmark_oos,
                "split_ts": str(res.split_timestamp),
            }
        )

    rows_sorted = sorted(rows, key=lambda r: r["is"]["sharpe"], reverse=True)
    best = rows_sorted[0]
    oos_sharpes = [r["oos"]["sharpe"] for r in rows]
    is_sharpes = [r["is"]["sharpe"] for r in rows]
    plateau_pos_oos = float(np.mean([s > 0.0 for s in oos_sharpes]))
    plateau_pos_is = float(np.mean([s > 0.0 for s in is_sharpes]))

    summary = {
        "strategy": name,
        "grid_size": len(rows),
        "plateau_pct_is_positive": round(plateau_pos_is * 100, 1),
        "plateau_pct_oos_positive": round(plateau_pos_oos * 100, 1),
        "median_oos_sharpe": round(float(np.median(oos_sharpes)), 3),
        "best_by_is": best,
    }
    return summary, alpha_returns, alpha_weights


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 2 & Phase 4 research backtests")
    parser.add_argument("--exchange", default=None, help="Override exchange id (bybit/binance/okx)")
    args = parser.parse_args()

    cfg = load_config()
    exchange_id = args.exchange or cfg.get("exchange", "bybit")
    bt_section = cfg.get("backtest", {})
    bt_cfg = BacktestConfig(
        fee_rate=float(bt_section.get("fee_rate", 0.0006)),
        slippage_rate=float(bt_section.get("slippage_rate", 0.0002)),
        max_gross_leverage=float(cfg.get("risk", {}).get("max_gross_leverage", 1.0)),
        train_ratio=float(bt_section.get("train_ratio", 0.60)),
        use_funding=bool(bt_section.get("use_funding", True)),
    )

    # Try primary exchange, fallback to binance / okx if unreachable
    data, funding = None, None
    for ex_try in [exchange_id, "binance", "okx"]:
        try:
            data, funding = download_all_data(ex_try)
            exchange_id = ex_try
            break
        except Exception as exc:
            log.warning("Exchange %s failed (%s), trying fallback...", ex_try, exc)
    if data is None:
        raise RuntimeError("Could not download market data from any exchange")

    available_basket = [s for s in DEFAULT_BASKET if s in data]
    log.info("Loaded %d symbols from %s (BTC bars=%d)", len(available_basket), exchange_id, len(data["BTC/USDT:USDT"]))

    all_alpha_rets: dict[str, pd.Series] = {}
    all_alpha_weights: dict[str, pd.DataFrame] = {}
    summaries: list[dict[str, Any]] = []

    # 1. HP Filter grid (12 configs)
    hp_grid = [
        {"window": w, "t1": t1, "t2": t2, "lam": lam}
        for w, (t1, t2), lam in itertools.product(
            [180, 365],
            [(5, 20), (10, 30), (20, 60)],
            [14400.0, float(100 * 365 ** 2)],
        )
    ]
    log.info("Running HP Filter grid (%d configs)...", len(hp_grid))
    hp_sum, hp_r, hp_w = eval_grid("hp_filter", hp_grid, HPFilterStrategy, data, funding, bt_cfg)
    summaries.append(hp_sum)
    all_alpha_rets.update(hp_r)
    all_alpha_weights.update(hp_w)

    # 2. Stat Arb grid (24 configs)
    sa_grid = [
        {
            "symbols": available_basket,
            "signal_mode": mode,
            "d": d,
            "cov_window": cw,
            "ridge": ridge,
        }
        for mode, d, cw, ridge in itertools.product(
            ["mean_reversion", "momentum"],
            [1, 3, 7],
            [60, 120],
            [1e-4, 1e-3],
        )
    ]
    log.info("Running Stat Arb grid (%d configs)...", len(sa_grid))
    sa_sum, sa_r, sa_w = eval_grid("statarb", sa_grid, StatArbStrategy, data, funding, bt_cfg)
    summaries.append(sa_sum)
    all_alpha_rets.update(sa_r)
    all_alpha_weights.update(sa_w)

    # 3. kNN grid (12 configs)
    knn_grid = [
        {"T": T, "z1": z1, "train": tr, "weights": wt}
        for T, z1, tr, wt in itertools.product(
            [3, 5, 10],
            [0.005, 0.01],
            [365],
            ["uniform", "distance"],
        )
    ]
    log.info("Running kNN grid (%d configs)...", len(knn_grid))
    knn_sum, knn_r, knn_w = eval_grid("knn", knn_grid, KNNStrategy, data, funding, bt_cfg)
    summaries.append(knn_sum)
    all_alpha_rets.update(knn_r)
    all_alpha_weights.update(knn_w)

    # 4. Alpha Combo (Kakushadze-Yu) across all 48 generated alphas (N=48 > M=20)
    alpha_rets_df = pd.DataFrame(all_alpha_rets).dropna()
    log.info("Running Alpha Combo across N=%d alphas over %d common days...", alpha_rets_df.shape[1], len(alpha_rets_df))
    combo_strat = AlphaComboStrategy(
        alpha_returns_df=alpha_rets_df,
        alpha_weights_map=all_alpha_weights,
        symbols=available_basket,
        timeframe="1d",
        M=20,
        d=5,
    )
    combo_res = run_backtest(combo_strat, data, cfg=bt_cfg, funding=funding)

    # Compare against Equal-Weight blend on the exact same OOS window
    oos_idx = combo_res.net_returns.iloc[int(len(combo_res.net_returns) * bt_cfg.train_ratio) :].index
    eq_w_oos_rets = alpha_rets_df.reindex(oos_idx).mean(axis=1)
    btc_oos_rets = data["BTC/USDT:USDT"]["close"].pct_change().reindex(oos_idx).fillna(0.0)

    combo_summary = {
        "strategy": "alpha_combo",
        "n_alphas": int(alpha_rets_df.shape[1]),
        "is": combo_res.metrics_is,
        "oos": combo_res.metrics_oos,
        "equal_weight_oos": compute_metrics(eq_w_oos_rets, None, btc_oos_rets, "1d"),
        "btc_buy_hold_oos": compute_metrics(btc_oos_rets, None, btc_oos_rets, "1d"),
        "split_ts": str(combo_res.split_timestamp),
    }

    report = {
        "exchange": exchange_id,
        "symbols": available_basket,
        "backtest_config": bt_cfg.__dict__,
        "strategies": summaries,
        "alpha_combo": combo_summary,
    }

    out_dir = PROJECT_ROOT / "research" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "phase2_4_summary.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log.info("Saved full report to %s", out_path)

    # Print concise table
    print("\n=== PHASE 2 & 4 OUT-OF-SAMPLE SUMMARY (40% Holdout, Fees+Slippage+Funding) ===")
    for s in summaries:
        b = s["best_by_is"]
        print(
            f"{s['strategy']:12s} | Grid={s['grid_size']:2d} | Plateau OOS+={s['plateau_pct_oos_positive']:5.1f}% "
            f"| IS Sharpe={b['is']['sharpe']:6.3f} | OOS Sharpe={b['oos']['sharpe']:6.3f} "
            f"| OOS Ret={b['oos']['total_return']*100:6.1f}% | OOS MaxDD={b['oos']['max_drawdown']*100:6.1f}% "
            f"| Beta={b['oos']['btc_beta']}"
        )
    c = combo_summary
    print(
        f"{'alpha_combo':12s} | N={c['n_alphas']:2d}    | IS Sharpe={c['is']['sharpe']:6.3f} "
        f"| OOS Sharpe={c['oos']['sharpe']:6.3f} | OOS Ret={c['oos']['total_return']*100:6.1f}% "
        f"| OOS MaxDD={c['oos']['max_drawdown']*100:6.1f}% | Beta={c['oos']['btc_beta']}"
    )
    print(
        f"{'equal_weight':12s} | N={c['n_alphas']:2d}    | OOS Sharpe={c['equal_weight_oos']['sharpe']:6.3f} "
        f"| OOS Ret={c['equal_weight_oos']['total_return']*100:6.1f}% | OOS MaxDD={c['equal_weight_oos']['max_drawdown']*100:6.1f}%"
    )
    print(
        f"{'BTC_B&H':12s} | bench   | OOS Sharpe={c['btc_buy_hold_oos']['sharpe']:6.3f} "
        f"| OOS Ret={c['btc_buy_hold_oos']['total_return']*100:6.1f}% | OOS MaxDD={c['btc_buy_hold_oos']['max_drawdown']*100:6.1f}%"
    )


if __name__ == "__main__":
    main()
