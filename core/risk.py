"""Hard-coded risk controls: staleness check, daily loss circuit breaker, leverage cap."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from core.config import TF_SECONDS


@dataclass
class RiskConfig:
    max_gross_leverage: float = 1.0
    max_daily_loss: float = 0.03
    min_order_usd: float = 10.0
    max_stale_candles: int = 3


class RiskManager:
    """Enforces hard risk limits before any strategy signal is executed."""

    def __init__(self, cfg: RiskConfig | None = None):
        self.cfg = cfg or RiskConfig()
        self.day: date | None = None
        self.day_start_eq: float | None = None

    def check_data_freshness(
        self,
        df: pd.DataFrame,
        timeframe: str,
        symbol: str,
        now_utc: pd.Timestamp | None = None,
    ) -> None:
        """Raise RuntimeError if the latest closed candle is too old."""
        if df.empty:
            raise RuntimeError(f"{symbol}: empty OHLCV dataframe")
        now = now_utc or pd.Timestamp.now(tz="UTC")
        last_ts = df.index[-1]
        if last_ts.tzinfo is None:
            last_ts = last_ts.tz_localize("UTC")
        age_sec = (now - last_ts).total_seconds()
        max_age = self.cfg.max_stale_candles * TF_SECONDS[timeframe]
        if age_sec > max_age:
            raise RuntimeError(
                f"{symbol}: data is {age_sec:.0f}s stale (limit={max_age}s)"
            )

    def check_daily_loss(
        self, equity: float, now_utc: pd.Timestamp | None = None
    ) -> bool:
        """Return False if intraday drawdown breaches max_daily_loss."""
        now = now_utc or pd.Timestamp.now(tz="UTC")
        today = now.date()
        if self.day != today or self.day_start_eq is None:
            self.day = today
            self.day_start_eq = float(equity)
        floor_eq = self.day_start_eq * (1.0 - self.cfg.max_daily_loss)
        return float(equity) >= floor_eq

    def cap_leverage(self, weights: dict[str, float]) -> dict[str, float]:
        """Scale weights down proportionally if gross leverage exceeds max_gross_leverage."""
        gross = sum(abs(float(w)) for w in weights.values())
        cap = self.cfg.max_gross_leverage
        if gross <= cap or gross == 0.0:
            return {k: float(v) for k, v in weights.items()}
        scale = cap / gross
        return {k: float(v) * scale for k, v in weights.items()}

    def should_trade(self, delta_qty: float, price: float) -> bool:
        """Skip tiny orders below min_order_usd to prevent fee churn."""
        return abs(delta_qty * price) >= self.cfg.min_order_usd

    def to_state(self) -> dict:
        return {
            "day": self.day.isoformat() if self.day else None,
            "day_start_eq": self.day_start_eq,
        }

    def load_state(self, state: dict) -> None:
        if state.get("day"):
            self.day = date.fromisoformat(state["day"])
        if state.get("day_start_eq") is not None:
            self.day_start_eq = float(state["day_start_eq"])
