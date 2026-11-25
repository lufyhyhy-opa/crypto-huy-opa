"""Historical OHLCV and perpetual funding rate downloader with Parquet caching."""
from __future__ import annotations

import logging
import time
from pathlib import Path

import ccxt
import pandas as pd

from core.config import PROJECT_ROOT, TF_SECONDS

log = logging.getLogger(__name__)


def _symbol_slug(symbol: str) -> str:
    return symbol.replace("/", "_").replace(":", "_")


def create_exchange(
    exchange_id: str = "bybit",
    default_type: str = "swap",
    testnet: bool = False,
    api_key: str | None = None,
    secret: str | None = None,
    password: str | None = None,
) -> ccxt.Exchange:
    """Instantiate a ccxt exchange configured for perpetual futures."""
    params: dict = {
        "enableRateLimit": True,
        "options": {"defaultType": default_type},
    }
    if api_key:
        params["apiKey"] = api_key
    if secret:
        params["secret"] = secret
    if password:
        params["password"] = password
    ex = getattr(ccxt, exchange_id)(params)
    if testnet:
        ex.set_sandbox_mode(True)
    return ex


def fetch_ohlcv_history(
    symbol: str,
    timeframe: str = "1d",
    days: int = 1825,
    exchange_id: str = "bybit",
    data_dir: str | Path | None = None,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """Download or load cached OHLCV history (UTC index, unfinished candle dropped)."""
    cache_dir = Path(data_dir) if data_dir else (PROJECT_ROOT / "data")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{exchange_id}_{_symbol_slug(symbol)}_{timeframe}.parquet"

    if cache_path.exists() and not force_refresh:
        df = pd.read_parquet(cache_path)
        if not df.empty:
            return df

    ex = create_exchange(exchange_id=exchange_id)
    tf_ms = TF_SECONDS[timeframe] * 1000
    now_ms = int(pd.Timestamp.now(tz="UTC").timestamp() * 1000)
    since_ms = now_ms - days * 86400 * 1000

    all_rows: list[list] = []
    cursor = since_ms
    limit = 1000

    log.info("Fetching %s %s from %s (%d days)...", symbol, timeframe, exchange_id, days)
    while cursor < now_ms - tf_ms:
        batch = ex.fetch_ohlcv(symbol, timeframe=timeframe, since=cursor, limit=limit)
        if not batch:
            break
        all_rows.extend(batch)
        last_ts = batch[-1][0]
        if last_ts <= cursor:
            break
        cursor = last_ts + tf_ms
        if len(batch) < limit and last_ts >= now_ms - 2 * tf_ms:
            break
        time.sleep(max(ex.rateLimit / 1000.0, 0.05))

    if not all_rows:
        raise RuntimeError(f"No OHLCV data returned for {symbol} ({timeframe}) on {exchange_id}")

    df = pd.DataFrame(all_rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.drop_duplicates(subset=["ts"]).sort_values("ts").set_index("ts")

    # Drop unfinished candle (its close time is still in the future)
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(seconds=TF_SECONDS[timeframe])
    df = df[df.index <= cutoff]

    df.to_parquet(cache_path)
    log.info("Saved %d candles to %s", len(df), cache_path.name)
    return df


def fetch_funding_history(
    symbol: str,
    days: int = 1095,
    exchange_id: str = "bybit",
    data_dir: str | Path | None = None,
    force_refresh: bool = False,
) -> pd.Series:
    """Download or load cached perpetual funding rate history (UTC index)."""
    cache_dir = Path(data_dir) if data_dir else (PROJECT_ROOT / "data")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{exchange_id}_{_symbol_slug(symbol)}_funding.parquet"

    if cache_path.exists() and not force_refresh:
        df = pd.read_parquet(cache_path)
        if not df.empty:
            return df["fundingRate"]

    ex = create_exchange(exchange_id=exchange_id)
    if not ex.has.get("fetchFundingRateHistory"):
        log.warning("%s does not support fetchFundingRateHistory", exchange_id)
        return pd.Series(dtype=float, name="fundingRate")

    now_ms = int(pd.Timestamp.now(tz="UTC").timestamp() * 1000)
    since_ms = now_ms - days * 86400 * 1000
    rows: list[dict] = []
    cursor = since_ms

    log.info("Fetching funding history for %s on %s...", symbol, exchange_id)
    # Bybit returns newest-first when endTime is used, or oldest-first with since; paginate defensively
    seen_ts: set[int] = set()
    for _ in range(100):
        try:
            batch = ex.fetch_funding_rate_history(symbol, since=cursor, limit=200)
        except Exception as exc:
            log.warning("Funding fetch stopped for %s: %s", symbol, exc)
            break
        if not batch:
            break
        new_items = [b for b in batch if b.get("timestamp") and b["timestamp"] not in seen_ts]
        if not new_items:
            break
        for item in new_items:
            seen_ts.add(item["timestamp"])
            rows.append({"ts": item["timestamp"], "fundingRate": float(item["fundingRate"])})
        max_ts = max(b["timestamp"] for b in new_items)
        if max_ts >= now_ms - 8 * 3600 * 1000:
            break
        cursor = max_ts + 1
        time.sleep(max(ex.rateLimit / 1000.0, 0.05))

    if not rows:
        return pd.Series(dtype=float, name="fundingRate")

    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.drop_duplicates(subset=["ts"]).sort_values("ts").set_index("ts")
    df.to_parquet(cache_path)
    return df["fundingRate"]


def load_basket(
    symbols: list[str],
    timeframe: str = "1d",
    days: int = 1825,
    exchange_id: str = "bybit",
    data_dir: str | Path | None = None,
    force_refresh: bool = False,
) -> dict[str, pd.DataFrame]:
    """Load OHLCV DataFrames for multiple symbols."""
    return {
        sym: fetch_ohlcv_history(
            sym,
            timeframe=timeframe,
            days=days,
            exchange_id=exchange_id,
            data_dir=data_dir,
            force_refresh=force_refresh,
        )
        for sym in symbols
    }
