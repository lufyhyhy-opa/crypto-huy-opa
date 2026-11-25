"""
24/7 Crypto Bot Skeleton — plugs into any Strategy in strategies/.

Defaults to PAPER=True and TESTNET=True for safety.
Usage:
    python -m core.bot hp_filter
    python -m core.bot statarb --once
"""
from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import PROJECT_ROOT, TF_SECONDS, load_config
from core.data_loader import create_exchange
from core.risk import RiskConfig, RiskManager

log = logging.getLogger("bot")


class Bot:
    """Exchange-agnostic execution skeleton with hard risk limits & state persistence."""

    def __init__(self, strategy: Any, cfg: dict[str, Any]):
        self.strategy = strategy
        self.cfg = cfg
        self.paper = bool(cfg.get("paper", True))
        self.testnet = bool(cfg.get("testnet", True))

        risk_cfg = cfg.get("risk", {})
        self.risk = RiskManager(
            RiskConfig(
                max_gross_leverage=float(risk_cfg.get("max_gross_leverage", 1.0)),
                max_daily_loss=float(risk_cfg.get("max_daily_loss", 0.03)),
                min_order_usd=float(risk_cfg.get("min_order_usd", 10.0)),
                max_stale_candles=int(risk_cfg.get("max_stale_candles", 3)),
            )
        )

        # In paper mode, read real mainnet public candles (no orders are ever sent).
        # Only switch ccxt to exchange sandbox when placing real testnet orders.
        use_sandbox = (not self.paper) and self.testnet
        self.ex = create_exchange(
            exchange_id=cfg.get("exchange", "bybit"),
            default_type=cfg.get("default_type", "swap"),
            testnet=use_sandbox,
            api_key=os.getenv("EXCHANGE_KEY") if not self.paper else None,
            secret=os.getenv("EXCHANGE_SECRET") if not self.paper else None,
            password=os.getenv("EXCHANGE_PASSWORD") if not self.paper else None,
        )

        self.paper_pos: dict[str, float] = {}
        self.paper_eq: float = float(cfg.get("paper_equity", 10_000.0))
        self.last_px: dict[str, float] = {}

        state_dir = PROJECT_ROOT / cfg.get("paths", {}).get("state_dir", "state")
        state_dir.mkdir(parents=True, exist_ok=True)
        strat_name = type(strategy).__module__.split(".")[-1]
        self.state_path = state_dir / f"{strat_name}_state.json"
        self._load_state()

    def _load_state(self) -> None:
        if not self.state_path.exists():
            return
        try:
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
            self.paper_pos = {k: float(v) for k, v in state.get("paper_pos", {}).items()}
            if "paper_eq" in state:
                self.paper_eq = float(state["paper_eq"])
            self.last_px = {k: float(v) for k, v in state.get("last_px", {}).items()}
            self.risk.load_state(state.get("risk", {}))
            log.info("Loaded persisted bot state from %s", self.state_path)
        except Exception as exc:
            log.warning("Could not load state (%s); starting fresh", exc)

    def _save_state(self) -> None:
        payload = {
            "paper_pos": self.paper_pos,
            "paper_eq": self.paper_eq,
            "last_px": self.last_px,
            "risk": self.risk.to_state(),
        }
        self.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def candles(self, symbol: str, limit: int) -> pd.DataFrame:
        raw = self.ex.fetch_ohlcv(symbol, self.strategy.timeframe, limit=limit + 1)
        df = pd.DataFrame(raw, columns=["ts", "open", "high", "low", "close", "volume"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
        df = df.set_index("ts").iloc[:-1]  # drop unfinished candle
        self.risk.check_data_freshness(df, self.strategy.timeframe, symbol)
        return df

    def equity(self) -> float:
        if self.paper:
            return self.paper_eq
        bal = self.ex.fetch_balance()
        return float(bal["USDT"]["total"])

    def positions(self) -> dict[str, float]:
        if self.paper:
            return dict(self.paper_pos)
        pos: dict[str, float] = {}
        for p in self.ex.fetch_positions(self.strategy.symbols):
            qty = float(p.get("contracts") or 0.0) * float(p.get("contractSize") or 1.0)
            if qty > 0:
                pos[p["symbol"]] = qty if p.get("side") == "long" else -qty
        return pos

    def mark_paper(self, prices: dict[str, float]) -> None:
        for sym, qty in self.paper_pos.items():
            if sym in self.last_px and sym in prices:
                self.paper_eq += qty * (prices[sym] - self.last_px[sym])
        self.last_px = dict(prices)

    def trade(self, symbol: str, qty: float) -> None:
        side = "buy" if qty > 0 else "sell"
        if self.paper:
            self.paper_pos[symbol] = self.paper_pos.get(symbol, 0.0) + qty
            log.info("[PAPER] %s %.6f %s", side, abs(qty), symbol)
            return
        amount = float(self.ex.amount_to_precision(symbol, abs(qty)))
        if amount > 0:
            self.ex.create_order(symbol, "market", side, amount)
            log.info("[LIVE] %s %s %s", side, amount, symbol)

    def rebalance(
        self, weights: dict[str, float], prices: dict[str, float], eq: float
    ) -> None:
        capped = self.risk.cap_leverage(weights)
        cur = self.positions()
        for sym in set(capped) | set(cur):
            px = prices[sym]
            target_qty = capped.get(sym, 0.0) * eq / px
            delta = target_qty - cur.get(sym, 0.0)
            if self.risk.should_trade(delta, px):
                self.trade(sym, delta)

    def flatten(self) -> None:
        for sym, qty in self.positions().items():
            if abs(qty) > 0:
                self.trade(sym, -qty)

    def step(self) -> bool:
        """Execute one loop iteration. Returns False if daily loss halt triggered."""
        data = {s: self.candles(s, self.strategy.history) for s in self.strategy.symbols}
        prices = {s: float(df["close"].iloc[-1]) for s, df in data.items()}
        if self.paper:
            self.mark_paper(prices)
        eq = self.equity()
        if not self.risk.check_daily_loss(eq):
            log.error("Daily loss limit breached (equity=%.2f) -> flattening & halting", eq)
            self.flatten()
            self._save_state()
            return False
        weights = self.strategy.target_weights(data)
        log.info("equity=%.2f weights=%s", eq, {k: round(v, 4) for k, v in weights.items()})
        self.rebalance(weights, prices, eq)
        self._save_state()
        return True

    def run(self, once: bool = False) -> None:
        mode = "PAPER" if self.paper else ("TESTNET" if self.testnet else "LIVE")
        log.info(
            "Starting Bot [%s] exchange=%s strategy=%s tf=%s",
            mode,
            self.cfg.get("exchange"),
            type(self.strategy).__module__,
            self.strategy.timeframe,
        )
        while True:
            try:
                ok = self.step()
                if not ok or once:
                    break
            except Exception as exc:
                log.exception("Loop error (changing nothing): %s", exc)
                if once:
                    raise
            time.sleep(TF_SECONDS[self.strategy.timeframe])


def main() -> None:
    parser = argparse.ArgumentParser(description="Run 151-Strategies Crypto Bot Skeleton")
    parser.add_argument("strategy", nargs="?", default="hp_filter", help="Module name in strategies/")
    parser.add_argument("--config", default=None, help="Path to YAML config file")
    parser.add_argument("--once", action="store_true", help="Run a single iteration and exit")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    cfg = load_config(args.config)
    mod = importlib.import_module(f"strategies.{args.strategy}")
    bot = Bot(mod.Strategy(), cfg)
    bot.run(once=args.once)


if __name__ == "__main__":
    main()
