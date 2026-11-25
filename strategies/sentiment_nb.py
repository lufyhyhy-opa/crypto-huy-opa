"""Strategy 5: X Sentiment Bernoulli Naive Bayes (Section 18.3).

Implements the exact book formula (Eq. 546): multiplies word likelihoods across
ALL tweets in the hour while applying the class prior P(C) only once.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import BernoulliNB

from strategies.base import BaseStrategy

VOCAB = [
    "bullish", "bearish", "pump", "dump", "moon", "crash", "buy", "sell", "long",
    "short", "ath", "dip", "rekt", "hodl", "breakout", "liquidation", "liquidated",
    "fud", "fomo", "rally", "etf", "sec", "whale", "support", "resistance",
    "bottom", "top", "capitulation", "squeeze", "bubble",
]


def default_fetch_tweets(since: pd.Timestamp, until: pd.Timestamp) -> pd.DataFrame:
    """Default placeholder fetcher — inject a real X API / dataset fetcher."""
    raise NotImplementedError(
        "Plug in an X API client or historical tweet dataset via tweet_fetcher=..."
    )


class Strategy(BaseStrategy):
    symbols = ["BTC/USDT:USDT"]
    timeframe = "1h"

    def __init__(
        self,
        vocab: list[str] | None = None,
        horizon_h: int = 1,
        alpha: float = 1.0,
        tweet_fetcher: Callable[[pd.Timestamp, pd.Timestamp], pd.DataFrame] | None = None,
        symbol: str | None = None,
    ):
        if symbol is not None:
            self.symbols = [symbol]
        self.vec = CountVectorizer(vocabulary=vocab or VOCAB, binary=True)
        self.nb = BernoulliNB(alpha=alpha)
        self.horizon = pd.Timedelta(hours=horizon_h)
        self.tweet_fetcher = tweet_fetcher or default_fetch_tweets
        self.history = 24 * 30
        self.pos = 0
        self.is_fitted = False

    def fit(self, tweets: pd.DataFrame, close: pd.Series) -> None:
        """Train BernoulliNB using price return strictly AFTER each tweet's hour."""
        t = pd.to_datetime(tweets["time"], utc=True).dt.floor("h")
        p0 = close.reindex(t).to_numpy(dtype=float)
        p1 = close.reindex(t + self.horizon).to_numpy(dtype=float)
        ok = ~np.isnan(p0) & ~np.isnan(p1)
        if not np.any(ok):
            raise ValueError("No overlapping timestamps between tweets and close prices")
        X = self.vec.transform(tweets["text"].astype(str).str.lower()[ok])
        y = (p1[ok] > p0[ok]).astype(int)
        self.nb.fit(X, y)
        self.is_fitted = True

    def predict(self, texts: pd.Series | list[str]) -> int:
        """Exact Eq. 546 log-likelihood sum over all tweets in the hour, P(C) once."""
        if not self.is_fitted:
            raise RuntimeError("Call strategy.fit(tweets, close) before predicting")
        s = pd.Series(texts, dtype=str).str.lower()
        X = self.vec.transform(s).toarray()
        logp = self.nb.feature_log_prob_
        log1m = np.log1p(-np.exp(logp))
        per_tweet = X @ logp.T + (1.0 - X) @ log1m.T
        score = self.nb.class_log_prior_ + per_tweet.sum(axis=0)
        return int(self.nb.classes_[int(np.argmax(score))])

    def target_weights(self, data: dict[str, pd.DataFrame]) -> dict[str, float]:
        sym = self.symbols[0]
        now = data[sym].index[-1] + pd.Timedelta(hours=1)
        tweets = self.tweet_fetcher(now - pd.Timedelta(hours=1), now)
        if tweets is not None and len(tweets) > 0:
            self.pos = 1 if self.predict(tweets["text"]) == 1 else -1
        return {sym: float(self.pos)}
