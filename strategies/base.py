"""Base interface for all Strategy plugins."""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class BaseStrategy(ABC):
    symbols: list[str]
    timeframe: str
    history: int

    @abstractmethod
    def target_weights(self, data: dict[str, pd.DataFrame]) -> dict[str, float]:
        """Given strictly past closed OHLCV candles, return target weights in [-1, 1]."""
        raise NotImplementedError
