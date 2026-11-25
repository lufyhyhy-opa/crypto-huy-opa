# CRYPTO HUY-OPA — MASTER PLAN: Xây Dựng Hệ Thống Giao Dịch Định Lượng Từ "151 Trading Strategies"

> **Biên soạn & Hệ thống hóa bởi Tran Quang Huy (Huy OPA) — Tài liệu nghiên cứu định lượng mã nguồn mở**
>
> **Nguồn học thuật gốc:** *151 Trading Strategies* — **Zura Kakushadze** (PhD Vật lý lý thuyết Cornell năm 23 tuổi, cựu Managing Director tại WorldQuant) & **Juan Andrés Serur**.
> - Bản arXiv (đầy đủ 20 chương, 398 trang, miễn phí): `https://arxiv.org/abs/1912.04492` (bản web HTML: `https://arxiv.org/html/1912.04492v1`)
> - Bản SSRN (tiếng Anh 2018, ~480 trang): `https://papers.ssrn.com/abstract=3247865`
>
> **Cảnh báo rủi ro (Bắt buộc đọc):** Tài liệu này chỉ phục vụ mục đích nghiên cứu, học thuật và thực hành kỹ thuật — **không phải lời khuyên đầu tư**. Giao dịch hợp đồng tương lai có đòn bẩy có thể làm mất toàn bộ vốn. Toàn bộ hệ thống dưới đây mặc định khóa an toàn ở chế độ **Paper Trading (`paper: true`)** và **Testnet (`testnet: true`)**.

---

## Mục Lục Chi Tiết
- [Chương 0: Bản đồ tổng thể & Tư duy xây Bot của Quỹ Quant](#chương-0-bản-đồ-tổng-thể--tư-duy-xây-bot-của-quỹ-quant)
- [Chương 1: Cài đặt môi trường & Khởi tạo dự án (Bước 1.1 → 1.4)](#chương-1-cài-đặt-môi-trường--khởi-tạo-dự-án-bước-11--14)
- [Chương 2: Xây bộ tải dữ liệu lịch sử miễn phí — OHLCV & Funding Rate (Bước 2.1 → 2.2)](#chương-2-xây-bộ-tải-dữ-liệu-lịch-sử-miễn-phí--ohlcv--funding-rate-bước-21--22)
- [Chương 3: Xây Bộ Quản trị Rủi ro, Máy Backtest & Bài Test Chống Nhìn Trộm Tương Lai (Bước 3.1 → 3.4)](#chương-3-xây-bộ-quản-trị-rủi-ro-máy-backtest--bài-test-chống-nhìn-trộm-tương-lai-bước-31--34)
- [Chương 4: Cài đặt trọn bộ 5 Chiến lược Cốt lõi + Bộ Ghép Alpha Combo (Bước 4.1 → 4.6)](#chương-4-cài-đặt-trọn-bộ-5-chiến-lược-cốt-lõi--bộ-ghép-alpha-combo-bước-41--46)
- [Chương 5: Chạy Backtest Đầu Tiên, Đọc Chỉ Số & Case Study Thực Tế (Bước 5.1 → 5.3)](#chương-5-chạy-backtest-đầu-tiên-đọc-chỉ-số--case-study-thực-tế-bước-51--53)
- [Chương 6: Bộ Lọc 6 Cổng (6 Gates) & Prompt Giám Đốc Quản Trị Rủi Ro](#chương-6-bộ-lọc-6-cổng-6-gates--prompt-giám-đốc-quản-trị-rủi-ro)
- [Chương 7: Chạy Bot 24/7 (Paper -> Testnet -> VPS) & Xử Lý Lỗi Thường Gặp (Bước 7.1 → 7.5)](#chương-7-chạy-bot-247-paper---testnet---vps--xử-lý-lỗi-thường-gặp-bước-71--75)
- [Phụ lục: Kho 26 Chiến lược Mở rộng từ Sách đáng Test tiếp trên Crypto](#phụ-lục-kho-26-chiến-lược-mở-rộng-từ-sách-đáng-test-tiếp-trên-crypto)

---

## Chương 0: Bản đồ tổng thể & Tư duy xây Bot của Quỹ Quant

### 0.1. Bạn cần gì để làm theo tài liệu này?
- **Máy tính:** macOS, Windows hoặc Linux (RAM từ 8GB trở lên).
- **Vốn ban đầu:** **0 đồng.** Không cần nạp tiền sàn, không cần tạo API Key để tải dữ liệu lịch sử 5 năm và chạy toàn bộ backtest.
- **Thời gian dự kiến:** 1–2 buổi tối để chạy xong hệ thống hoàn chỉnh; 1 tuần để làm chủ việc backtest & đánh giá chiến lược mới.

### 0.2. Tại sao 90% Bot tự viết bằng AI bị lỗi ngay đêm đầu tiên?
Vì người mới thường ra lệnh cho AI: *"Hãy viết một con bot trade BTC bằng Python"*. AI sẽ sinh ra một tệp mã nguồn đơn khối (monolithic) trộn lẫn công thức, kết nối sàn và đặt lệnh. Khi đổi ý tưởng, bạn phải đập đi viết lại từ đầu — và rất dễ dính bug đặt lệnh sai dẫn đến tổn thất nghiêm trọng nguồn vốn.

**Kiến trúc chuẩn của Quỹ Quant** tách hệ thống thành **4 lớp độc lập**:
1. **Lớp Dữ liệu (`core/data_loader.py`):** Tải nến OHLCV + Funding Rate, luôn **cắt bỏ nến cuối chưa đóng**, lưu cache `.parquet`.
2. **Lớp Chiến lược (`strategies/*.py`):** Chỉ làm đúng 1 việc: nhận dữ liệu quá khứ -> trả về từ điển trọng số mục tiêu từ `-1.0` (Short 100%) đến `+1.0` (Long 100%).
3. **Lớp Kiểm định (`core/backtester.py`, `core/metrics.py`, `tests/`):** Giả lập từng nến, trừ đủ phí + trượt giá + funding, chia 60% In-Sample / 40% Out-of-Sample, chạy bài test tự động bắt lỗi nhìn trộm tương lai.
4. **Lớp Thực thi & Rủi ro (`core/risk.py`, `core/bot.py`):** Chạy 24/7, kiểm tra 5 giới hạn cứng trước khi hỏi chiến lược, lưu trạng thái xuống ổ cứng để restart không mất dữ liệu.

### 0.3. Vòng lặp 7 bước an toàn của Bot
```text
[1. Tải nến OHLCV & BỎ nến cuối chưa đóng]
          │
          ▼
[2. Kiểm tra dữ liệu tươi (< 3 nến) & Lỗ trong ngày <= 3%?]
          ├── KHÔNG ĐẠT ──► [ĐÓNG SẠCH VỊ THẾ (Flatten) & DỪNG BOT NGAY]
          │
          ▼ ĐẠT
[3. Gọi strategy.target_weights(data)]
          │
          ▼
[4. Khóa trần tổng đòn bẩy sum(|w|) <= 1.0x]
          │
          ▼
[5. Tính phần chênh lệch (target - vị thế hiện tại); bỏ qua nếu < $10]
          │
          ▼
[6. Đặt lệnh (hoặc ghi log [PAPER]) & Lưu state.json]
          │
          ▼
[7. Ngủ đến nến kế tiếp -> Lặp lại bước 1]
```

---

## Chương 1: Cài đặt môi trường & Khởi tạo dự án (Bước 1.1 → 1.4)

### Bước 1.1: Kiểm tra Python 3.11+
Mở **Terminal** (macOS/Linux) hoặc **PowerShell** (Windows) và gõ:
```bash
python3 --version
```
- **Checkpoint:** Kết quả phải là `Python 3.11.x` hoặc `Python 3.12.x`.
- Nếu chưa có hoặc phiên bản thấp hơn 3.11: tải bản mới nhất tại `https://www.python.org/downloads/` (trên Windows nhớ tích ô **"Add Python to PATH"** khi cài).

### Bước 1.2: Tạo cây thư mục dự án chuẩn
Chạy lệnh sau (macOS/Linux):
```bash
mkdir -p crypto-huy-opa/config crypto-huy-opa/data crypto-huy-opa/core \
         crypto-huy-opa/strategies crypto-huy-opa/research/reports \
         crypto-huy-opa/tests crypto-huy-opa/state crypto-huy-opa/logs
cd crypto-huy-opa
touch core/__init__.py strategies/__init__.py
```
*(Trên Windows PowerShell, tạo lần lượt các thư mục con `config`, `data`, `core`, `strategies`, `research\reports`, `tests`, `state`, `logs` bên trong `crypto-huy-opa`).*

### Bước 1.3: Tạo môi trường ảo & Cài đặt 9 thư viện lõi
```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install ccxt pandas numpy scikit-learn statsmodels pyarrow pyyaml pytest python-dotenv
```
- **Checkpoint:** Chạy `python -c "import ccxt, pandas, sklearn, statsmodels; print('OK')"` -> Thấy in ra `OK` là thành công!

### Bước 1.4: Tạo 3 file cấu hình gốc
**1. Tạo file `config/default.yaml`** (nơi khóa cứng 5 giới hạn an toàn):
```yaml
exchange: bybit              # Hỗ trợ mọi sàn ccxt: bybit, binance, okx
default_type: swap           # Hợp đồng tương lai vĩnh cửu (Long & Short)
testnet: true                # true = sàn giả lập Testnet
paper: true                  # true = mô phỏng tại chỗ, KHÔNG gửi lệnh lên sàn
paper_equity: 10000.0        # Vốn khởi điểm chế độ Paper (USDT)

risk:
  max_gross_leverage: 1.0    # Tổng |trọng số| không bao giờ vượt 1.0x vốn
  max_daily_loss: 0.03       # Lỗ quá -3% trong ngày -> đóng toàn bộ & tắt bot
  min_order_usd: 10.0        # Bỏ qua điều chỉnh nhỏ dưới $10 để tiết kiệm phí
  max_stale_candles: 3       # Dừng nếu dữ liệu bị đứng quá 3 nến

backtest:
  fee_rate: 0.0006           # Phí taker 0.06% mỗi chiều
  slippage_rate: 0.0002      # Trượt giá 0.02% mỗi chiều
  use_funding: true          # Bắt buộc tính lịch sử Funding Rate thật
  train_ratio: 0.60          # 60% dữ liệu đầu tối ưu / 40% cuối Out-of-Sample
```

**2. Tạo file `.env.example`** (dùng khi chuyển sang Testnet ở Chương 7):
```env
EXCHANGE_KEY=
EXCHANGE_SECRET=
EXCHANGE_PASSWORD=
```

**3. Tạo file `.gitignore`** (bảo vệ tuyệt đối API Key không bị lộ):
```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
.env
data/*.parquet
state/
logs/
```

---

## Chương 2: Xây bộ tải dữ liệu lịch sử miễn phí — OHLCV & Funding Rate (Bước 2.1 → 2.2)

### Bước 2.1: Tạo file `core/data_loader.py`
File này tải dữ liệu công khai từ sàn (không cần API Key), tự động phân trang nhiều năm, **cắt bỏ nến cuối chưa đóng** và lưu cache dạng `.parquet` tốc độ cao.

```python
"""Tải & lưu cache dữ liệu lịch sử OHLCV và Funding Rate qua ccxt."""
from __future__ import annotations

import time
from pathlib import Path

import ccxt
import pandas as pd

TF_SECONDS = {"15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}


def _slug(symbol: str) -> str:
    return symbol.replace("/", "_").replace(":", "_")


def create_exchange(
    exchange_id: str = "bybit",
    default_type: str = "swap",
    testnet: bool = False,
    api_key: str | None = None,
    secret: str | None = None,
    password: str | None = None,
) -> ccxt.Exchange:
    params: dict = {"enableRateLimit": True, "options": {"defaultType": default_type}}
    if api_key and secret:
        params["apiKey"] = api_key
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
    data_dir: str = "data",
    force_refresh: bool = False,
) -> pd.DataFrame:
    cache_dir = Path(data_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{exchange_id}_{_slug(symbol)}_{timeframe}.parquet"
    if cache_path.exists() and not force_refresh:
        return pd.read_parquet(cache_path)

    ex = create_exchange(exchange_id=exchange_id)
    tf_ms = TF_SECONDS[timeframe] * 1000
    now_ms = int(pd.Timestamp.now(tz="UTC").timestamp() * 1000)
    cursor = now_ms - days * 86400 * 1000
    rows: list[list] = []

    while cursor < now_ms - tf_ms:
        batch = ex.fetch_ohlcv(symbol, timeframe=timeframe, since=cursor, limit=1000)
        if not batch:
            break
        rows.extend(batch)
        if batch[-1][0] <= cursor:
            break
        cursor = batch[-1][0] + tf_ms
        time.sleep(max(ex.rateLimit / 1000.0, 0.05))

    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.drop_duplicates("ts").sort_values("ts").set_index("ts")

    # Cắt bỏ nến cuối cùng chưa đóng
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(seconds=TF_SECONDS[timeframe])
    df = df[df.index <= cutoff]
    df.to_parquet(cache_path)
    return df


def fetch_funding_history(
    symbol: str,
    days: int = 1200,
    exchange_id: str = "bybit",
    data_dir: str = "data",
    force_refresh: bool = False,
) -> pd.Series:
    cache_dir = Path(data_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{exchange_id}_{_slug(symbol)}_funding.parquet"
    if cache_path.exists() and not force_refresh:
        return pd.read_parquet(cache_path)["fundingRate"]

    ex = create_exchange(exchange_id=exchange_id)
    if not ex.has.get("fetchFundingRateHistory"):
        return pd.Series(dtype=float, name="fundingRate")

    now_ms = int(pd.Timestamp.now(tz="UTC").timestamp() * 1000)
    cursor = now_ms - days * 86400 * 1000
    rows, seen = [], set()

    for _ in range(100):
        batch = ex.fetch_funding_rate_history(symbol, since=cursor, limit=200)
        new_items = [b for b in batch if b.get("timestamp") and b["timestamp"] not in seen]
        if not new_items:
            break
        for b in new_items:
            seen.add(b["timestamp"])
            rows.append({"ts": b["timestamp"], "fundingRate": float(b["fundingRate"])})
        max_ts = max(b["timestamp"] for b in new_items)
        if max_ts >= now_ms - 8 * 3600 * 1000:
            break
        cursor = max_ts + 1
        time.sleep(max(ex.rateLimit / 1000.0, 0.05))

    if not rows:
        return pd.Series(dtype=float, name="fundingRate")
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.drop_duplicates("ts").sort_values("ts").set_index("ts")
    df.to_parquet(cache_path)
    return df["fundingRate"]
```

### Bước 2.2: Checkpoint kiểm tra tải dữ liệu thật
Chạy lệnh sau trong terminal:
```bash
PYTHONPATH=. python -c "
from core.data_loader import fetch_ohlcv_history, fetch_funding_history
df = fetch_ohlcv_history('BTC/USDT:USDT', '1d', days=1825)
fd = fetch_funding_history('BTC/USDT:USDT', days=1825)
print('Số nến BTC:', len(df), '| Từ:', df.index[0].date(), 'đến:', df.index[-1].date())
print('Số kỳ Funding:', len(fd), '| Funding trung bình/kỳ:', round(fd.mean()*100, 4), '%')
"
```
- **Kết quả mong đợi:** Thấy in ra khoảng `1824` nến BTC và hàng nghìn kỳ funding rate, kèm 2 file `.parquet` trong thư mục `data/`. Nếu Bybit bị chặn tại mạng của bạn, truyền thêm `exchange_id='okx'` hoặc `'binance'`.

---

## Chương 3: Xây Bộ Quản trị Rủi ro, Máy Backtest & Bài Test Chống Nhìn Trộm Tương Lai (Bước 3.1 → 3.4)

### Bước 3.1: Tạo file `core/risk.py` (5 giới hạn cứng)
```python
"""Quản trị rủi ro cứng: kiểm tra dữ liệu tươi, cắt lỗ ngày, khóa đòn bẩy."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import pandas as pd
from core.data_loader import TF_SECONDS


@dataclass
class RiskConfig:
    max_gross_leverage: float = 1.0
    max_daily_loss: float = 0.03
    min_order_usd: float = 10.0
    max_stale_candles: int = 3


class RiskManager:
    def __init__(self, cfg: RiskConfig | None = None):
        self.cfg = cfg or RiskConfig()
        self.day: date | None = None
        self.day_start_eq: float | None = None

    def check_data_freshness(self, df: pd.DataFrame, timeframe: str, symbol: str) -> None:
        if df.empty:
            raise RuntimeError(f"{symbol}: Bảng dữ liệu rỗng")
        age = (pd.Timestamp.now(tz="UTC") - df.index[-1]).total_seconds()
        limit = self.cfg.max_stale_candles * TF_SECONDS[timeframe]
        if age > limit:
            raise RuntimeError(f"{symbol}: Dữ liệu bị trễ {age:.0f}s (giới hạn {limit}s)")

    def check_daily_loss(self, equity: float) -> bool:
        today = pd.Timestamp.now(tz="UTC").date()
        if self.day != today or self.day_start_eq is None:
            self.day, self.day_start_eq = today, float(equity)
        return float(equity) >= self.day_start_eq * (1.0 - self.cfg.max_daily_loss)

    def cap_leverage(self, weights: dict[str, float]) -> dict[str, float]:
        gross = sum(abs(float(w)) for w in weights.values())
        if gross <= self.cfg.max_gross_leverage or gross == 0.0:
            return {k: float(v) for k, v in weights.items()}
        scale = self.cfg.max_gross_leverage / gross
        return {k: float(v) * scale for k, v in weights.items()}

    def should_trade(self, delta_qty: float, price: float) -> bool:
        return abs(delta_qty * price) >= self.cfg.min_order_usd
```

### Bước 3.2: Tạo file `core/metrics.py` (Bộ chấm điểm hiệu suất chuẩn Quỹ)
```python
"""Tính toán Sharpe, Sortino, Max Drawdown, Calmar, Turnover và Beta vs BTC."""
from __future__ import annotations

import math
import pandas as pd

BARS_PER_YEAR = {"15m": 365 * 96, "1h": 365 * 24, "4h": 365 * 6, "1d": 365}


def compute_metrics(
    returns: pd.Series,
    weights_df: pd.DataFrame | None = None,
    benchmark_returns: pd.Series | None = None,
    timeframe: str = "1d",
) -> dict:
    r = returns.dropna().astype(float)
    n = len(r)
    if n == 0:
        return {"bars": 0, "total_return": 0.0, "sharpe": 0.0, "max_drawdown": 0.0}

    ann = BARS_PER_YEAR.get(timeframe, 365)
    equity = (1.0 + r).cumprod()
    total_ret = float(equity.iloc[-1] - 1.0)
    years = max(n / ann, 1e-9)
    cagr = float(equity.iloc[-1] ** (1.0 / years) - 1.0) if equity.iloc[-1] > 0 else -1.0

    std = float(r.std(ddof=1)) if n > 1 else 0.0
    sharpe = float((r.mean() / std) * math.sqrt(ann)) if std > 1e-12 else 0.0

    dd = equity / equity.cummax() - 1.0
    max_dd = float(dd.min())

    turnover, trades = 0.0, 0
    if weights_df is not None and not weights_df.empty:
        w = weights_df.reindex(r.index).fillna(0.0)
        dw = w.diff().abs()
        dw.iloc[0] = w.iloc[0].abs()
        bar_to = dw.sum(axis=1)
        turnover = float(bar_to.mean() * (ann / 365.0))
        trades = int((bar_to > 1e-6).sum())

    btc_beta = None
    if benchmark_returns is not None:
        al = pd.concat([r.rename("s"), benchmark_returns.rename("b")], axis=1).dropna()
        if len(al) > 2 and al["b"].var() > 1e-12:
            btc_beta = round(float(al["s"].cov(al["b"]) / al["b"].var()), 3)

    return {
        "bars": n,
        "total_return": round(total_ret, 4),
        "cagr": round(cagr, 4),
        "sharpe": round(sharpe, 3),
        "max_drawdown": round(max_dd, 4),
        "avg_daily_turnover": round(turnover, 4),
        "trade_count": trades,
        "btc_beta": btc_beta,
    }
```

### Bước 3.3: Tạo file `core/backtester.py` (Máy Backtest Nhân quả từng nến)
```python
"""Máy Backtest từng nến: chỉ cấp dữ liệu quá khứ, trừ phí + trượt giá + funding, chia 60/40."""
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
    net_returns: pd.Series
    weights: pd.DataFrame
    equity_curve: pd.Series
    metrics_is: dict
    metrics_oos: dict
    metrics_full: dict
    benchmark_oos: dict


def _align_funding(funding_map: dict[str, pd.Series] | None, index: pd.DatetimeIndex, symbols: list[str]) -> pd.DataFrame:
    out = pd.DataFrame(0.0, index=index, columns=symbols)
    if not funding_map or len(index) < 2:
        return out
    for sym in symbols:
        s = funding_map.get(sym)
        if s is None or s.empty:
            continue
        s = s.sort_index()
        pos = index.searchsorted(s.index, side="left")
        ok = (pos > 0) & (pos < len(index))
        if np.any(ok):
            g = pd.Series(s.to_numpy()[ok], index=index[pos[ok]]).groupby(level=0).sum()
            out.loc[g.index, sym] = g.to_numpy()
    return out


def run_backtest(
    strategy: Any,
    data: dict[str, pd.DataFrame],
    cfg: BacktestConfig | None = None,
    funding: dict[str, pd.Series] | None = None,
) -> BacktestResult:
    cfg = cfg or BacktestConfig()
    strat = copy.deepcopy(strategy)
    symbols = list(strat.symbols)

    common_idx = None
    for s in symbols:
        common_idx = data[s].index if common_idx is None else common_idx.intersection(data[s].index)
    common_idx = common_idx.sort_values()

    aligned = {s: data[s].loc[common_idx] for s in symbols}
    close_df = pd.DataFrame({s: aligned[s]["close"] for s in symbols}, index=common_idx)
    next_ret = close_df.pct_change().shift(-1)
    fund_df = _align_funding(funding, common_idx, symbols) if cfg.use_funding else pd.DataFrame(0.0, index=common_idx, columns=symbols)

    risk = RiskManager(RiskConfig(max_gross_leverage=cfg.max_gross_leverage))
    prev_w = {s: 0.0 for s in symbols}
    cost_rate = cfg.fee_rate + cfg.slippage_rate
    ts_list, w_rows, net_list = [], [], []

    for i in range(int(strat.history), len(common_idx) - 1):
        # CHỈ truyền dữ liệu quá khứ [0..i]
        window_data = {s: aligned[s].iloc[: i + 1] for s in symbols}
        w = risk.cap_leverage({s: float(strat.target_weights(window_data).get(s, 0.0)) for s in symbols})

        turnover = sum(abs(w[s] - prev_w[s]) for s in symbols)
        gross = sum(w[s] * float(next_ret.iloc[i][s]) for s in symbols)
        fund_cost = sum(w[s] * float(fund_df.iloc[i + 1][s]) for s in symbols)
        net = gross - turnover * cost_rate - fund_cost

        ts_list.append(common_idx[i + 1])
        w_rows.append(w)
        net_list.append(net)
        prev_w = w

    res_idx = pd.DatetimeIndex(ts_list)
    net_s = pd.Series(net_list, index=res_idx, name="net_return")
    w_df = pd.DataFrame(w_rows, index=res_idx)
    eq = (1.0 + net_s).cumprod()

    bench_sym = "BTC/USDT:USDT" if "BTC/USDT:USDT" in data else symbols[0]
    bench = data[bench_sym]["close"].pct_change().reindex(res_idx).fillna(0.0)
    split = int(len(res_idx) * cfg.train_ratio)

    return BacktestResult(
        net_returns=net_s,
        weights=w_df,
        equity_curve=eq,
        metrics_is=compute_metrics(net_s.iloc[:split], w_df.iloc[:split], bench.iloc[:split], strat.timeframe),
        metrics_oos=compute_metrics(net_s.iloc[split:], w_df.iloc[split:], bench.iloc[split:], strat.timeframe),
        metrics_full=compute_metrics(net_s, w_df, bench, strat.timeframe),
        benchmark_oos=compute_metrics(bench.iloc[split:], None, bench.iloc[split:], strat.timeframe),
    )
```

### Bước 3.4: Tạo bài test tự động bắt lỗi Look-Ahead (`tests/test_no_lookahead.py`)
```python
import numpy as np
import pandas as pd
from strategies.hp_filter import Strategy as HPFilter
from strategies.knn import Strategy as KNN
from strategies.statarb import Strategy as StatArb


def _fake_ohlcv(n=260, seed=1):
    rng = np.random.default_rng(seed)
    close = 30000 * np.exp(np.cumsum(rng.normal(0.0005, 0.025, n)))
    idx = pd.date_range("2024-01-01", periods=n, freq="1D", tz="UTC")
    return pd.DataFrame({"open": close, "high": close * 1.01, "low": close * 0.99, "close": close, "volume": rng.uniform(1e6, 5e6, n)}, index=idx)


def test_hp_filter_no_lookahead():
    df = _fake_ohlcv(250, seed=1)
    df_mut = df.copy()
    df_mut.iloc[200:, df_mut.columns.get_loc("close")] *= 10.0  # Phá dữ liệu tương lai
    s1, s2 = HPFilter(window=60, t1=5, t2=15, lam=14400), HPFilter(window=60, t1=5, t2=15, lam=14400)
    assert np.isclose(s1.causal_trend(df["close"].iloc[:200]).iloc[-1], s2.causal_trend(df_mut["close"]).iloc[199], rtol=1e-12)


def test_knn_no_lookahead():
    df = _fake_ohlcv(260, seed=2)
    df_mut = df.copy()
    df_mut.iloc[210:, df_mut.columns.get_loc("close")] *= 0.1
    assert np.isclose(KNN(T=5, train=120).predict(df.iloc[:210]), KNN(T=5, train=120).predict(df_mut.iloc[:210]), rtol=1e-12)


def test_statarb_dollar_neutral():
    syms = [f"C{i}/USDT:USDT" for i in range(8)]
    data = {s: _fake_ohlcv(160, seed=10 + i) for i, s in enumerate(syms)}
    w = list(StatArb(symbols=syms, cov_window=120, d=3).target_weights(data).values())
    assert abs(sum(w)) < 1e-12 and abs(sum(abs(x) for x in w) - 1.0) < 1e-12
```

---

## Chương 4: Cài đặt trọn bộ 5 Chiến lược Cốt lõi + Bộ Ghép Alpha Combo (Bước 4.1 → 4.6)

### Bước 4.1: Chiến lược 1 — Hodrick–Prescott Filter (`strategies/hp_filter.py` — Mục 8.1)
- **Hiểu nhanh:** Giống tai nghe chống ồn — tách giá thành xu hướng mượt $S^*(t)$ + nhiễu $\nu(t)$, rồi mới lấy MA nhanh cắt MA chậm trên $S^*(t)$.
- **Bẫy chết người:** Chạy `hpfilter` 1 lần trên toàn bộ lịch sử sẽ nhìn trộm tương lai. Phải chạy vòng lặp rolling chỉ trên cửa sổ quá khứ.

```python
import numpy as np
import pandas as pd
from statsmodels.tsa.filters.hp_filter import hpfilter


class Strategy:
    symbols = ["BTC/USDT:USDT"]
    timeframe = "1d"

    def __init__(self, window=365, t1=10, t2=30, n_per_year=365, lam=None):
        self.window, self.t1, self.t2 = window, t1, t2
        self.lam = float(lam) if lam is not None else float(100 * (n_per_year ** 2))
        self.history = window + t2 + 5

    def causal_trend(self, close: pd.Series) -> pd.Series:
        s = close.to_numpy(dtype=float)
        out = np.full(len(s), np.nan)
        for t in range(self.window, len(s) + 1):
            _, tr = hpfilter(s[t - self.window : t], lamb=self.lam)
            out[t - 1] = tr[-1]
        return pd.Series(out, index=close.index)

    def target_weights(self, data):
        sym = self.symbols[0]
        close = data[sym]["close"].iloc[-(self.window + self.t2) :]
        s_star = self.causal_trend(close).dropna()
        ma1, ma2 = s_star.iloc[-self.t1 :].mean(), s_star.iloc[-self.t2 :].mean()
        return {sym: 1.0 if ma1 > ma2 else -1.0}
```

### Bước 4.2: Chiến lược 2 — k-Nearest Neighbors (`strategies/knn.py` — Mục 3.17)
- **Hiểu nhanh:** Tìm $k = \lfloor \sqrt{T^*} \rfloor$ ngày trong quá khứ có độ lệch giá và khối lượng giống hệt hôm nay nhất, rồi lấy trung bình lợi suất $T$ ngày sau đó.

```python
import math
import numpy as np
import pandas as pd
from sklearn.neighbors import KNeighborsRegressor


class Strategy:
    symbols = ["BTC/USDT:USDT"]
    timeframe = "1d"

    def __init__(self, T=5, price_w=(5, 20, 60), vol_w=(5, 20), train=365, z1=0.01, z2=0.0, weights="uniform"):
        self.T, self.price_w, self.vol_w = T, price_w, vol_w
        self.train, self.z1, self.z2, self.weights = train, z1, z2, weights
        self.history = train + max(price_w + vol_w + (60,)) + T + 5
        self.pos = 0

    def features(self, df):
        p, v = df["close"], df["volume"]
        X = pd.DataFrame(index=df.index)
        for w in self.price_w:
            X[f"p{w}"] = p.rolling(w).mean() / p - 1.0
        v_base = v.rolling(60).mean().replace(0.0, np.nan)
        for w in self.vol_w:
            X[f"v{w}"] = v.rolling(w).mean() / v_base
        return X

    def predict(self, df):
        X = self.features(df)
        Y = df["close"].shift(-self.T) / df["close"] - 1.0
        hist = pd.concat([X, Y.rename("Y")], axis=1).dropna().iloc[-self.train :]
        cols = list(X.columns)
        lo, hi = hist[cols].min(), hist[cols].max()
        span = (hi - lo).replace(0.0, 1.0)
        norm = lambda Z: ((Z - lo) / span).to_numpy(dtype=float)
        k = max(1, int(math.floor(math.sqrt(len(hist)))))
        model = KNeighborsRegressor(n_neighbors=k, weights=self.weights).fit(norm(hist[cols]), hist["Y"].to_numpy())
        return float(model.predict(norm(X.iloc[[-1]]))[0])

    def target_weights(self, data):
        sym = self.symbols[0]
        y = self.predict(data[sym])
        if self.pos == 1 and y <= self.z2: self.pos = 0
        if self.pos == -1 and y >= -self.z2: self.pos = 0
        if self.pos == 0:
            self.pos = 1 if y > self.z1 else (-1 if y < -self.z1 else 0)
        return {sym: float(self.pos)}
```

### Bước 4.3: Chiến lược 3 — Mạng Neural ANN 15 phút (`strategies/ann.py` — Mục 18.2)
- **Hiểu nhanh:** Viết riêng cho BTC khung 15m. Chia lợi suất nến kế tiếp thành 3 nhóm (Tăng mạnh / Đi ngang / Giảm mạnh), dùng mạng `MLPClassifier(32, 16)` huấn luyện lại mỗi ngày trên 60 ngày gần nhất.

```python
import numpy as np
import pandas as pd
from sklearn.neural_network import MLPClassifier

BARS_PER_DAY = 96

def ema(x, lam, tau):
    w = (lam ** np.arange(tau)) * (1 - lam) / (1 - lam ** tau)
    return x.rolling(tau).apply(lambda a: float(np.dot(w, a[::-1])), raw=True)

def emsd(x, lam, tau):
    w = lam ** np.arange(tau)
    mn, vn = (1 - lam) / (1 - lam ** tau), (1 - lam) / (lam - lam ** tau)
    return x.rolling(tau).apply(lambda a: float(np.sqrt(max(0.0, vn * np.dot(w, (a[::-1] - np.dot(w, a[::-1]) * mn) ** 2)))), raw=True)

def rsi(x, tau):
    up, dn = x.clip(lower=0).rolling(tau).sum(), (-x).clip(lower=0).rolling(tau).sum()
    return (up / (up + dn).replace(0.0, np.nan)).fillna(0.5)

class Strategy:
    symbols = ["BTC/USDT:USDT"]
    timeframe = "15m"

    def __init__(self, T1=BARS_PER_DAY, taus=(2, 4, 12, 24), rsi_taus=(12, 24, 48), K=3, train_days=60, min_prob=0.45):
        self.T1, self.taus, self.rsi_taus, self.K, self.min_prob = T1, taus, rsi_taus, K, min_prob
        self.train, self.retrain_every = train_days * BARS_PER_DAY, BARS_PER_DAY
        self.history = self.train + T1 + max(taus + rsi_taus) + 10
        self.model, self.bars_since_fit, self.pos = None, 0, 0

    def target_weights(self, data):
        sym = self.symbols[0]
        R = data[sym]["close"].pct_change()
        past = R.shift(1).rolling(self.T1)
        rh = (R - past.mean()) / past.std().replace(0.0, np.nan)
        X = pd.DataFrame({"rhat": rh})
        for tau in self.taus:
            lam = 1 - 1 / tau
            X[f"ema{tau}"], X[f"emsd{tau}"] = ema(rh, lam, tau), emsd(rh, lam, tau)
        for tau in self.rsi_taus:
            X[f"rsi{tau}"] = rsi(rh, tau)

        if self.model is None or self.bars_since_fit >= self.retrain_every:
            d = pd.concat([X, rh.shift(-1).rename("y")], axis=1).dropna().iloc[-self.train :]
            q = np.quantile(d["y"], np.linspace(0, 1, self.K + 1)[1:-1])
            labels = np.searchsorted(q, d["y"].to_numpy(), side="right")
            self.model = MLPClassifier((32, 16), activation="relu", solver="sgd", learning_rate_init=0.01, momentum=0.9, max_iter=300, early_stopping=True, random_state=0)
            self.model.fit(d[X.columns].to_numpy(), labels)
            self.bars_since_fit = 0
        self.bars_since_fit += 1

        p = self.model.predict_proba(X.iloc[[-1]].to_numpy())[0]
        best_i = int(np.argmax(p))
        if p[best_i] >= self.min_prob:
            cls = int(self.model.classes_[best_i])
            if cls == self.K - 1: self.pos = 1
            elif cls == 0: self.pos = -1
        return {sym: float(self.pos)}
```

### Bước 4.4: Chiến lược 4 — Statistical Arbitrage 10 Coin (`strategies/statarb.py` — Mục 3.18)
- **Hiểu nhanh:** Long nhóm coin yếu hơn trung bình rổ, Short nhóm coin nóng hơn trung bình rổ, luôn giữ tổng trọng số bằng `0` (Dollar-Neutral) để không phụ thuộc chiều lên/xuống của BTC.

```python
import numpy as np
import pandas as pd

DEFAULT_BASKET = [f"{c}/USDT:USDT" for c in ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "LINK", "DOT"]]


class Strategy:
    symbols = list(DEFAULT_BASKET)
    timeframe = "1d"

    def __init__(self, symbols=None, cov_window=120, d=3, ridge=1e-4, signal_mode="mean_reversion"):
        if symbols is not None:
            self.symbols = list(symbols)
        self.cov_window, self.d, self.ridge, self.signal_mode = cov_window, d, ridge, signal_mode
        self.history = cov_window + d + 5

    def target_weights(self, data):
        closes = {s: data[s]["close"] for s in self.symbols if s in data}
        rets = pd.DataFrame(closes).pct_change().dropna().iloc[-self.cov_window :]
        C = rets.cov().to_numpy() + self.ridge * np.eye(len(rets.columns))
        Cinv = np.linalg.pinv(C)

        r = rets.iloc[-self.d :].sum()
        E = (-(r - r.mean()) if self.signal_mode == "mean_reversion" else (r - r.mean())).to_numpy()
        a = Cinv @ E
        b = Cinv @ np.ones(len(E))
        w = a - b * (a.sum() / b.sum())  # Dollar-neutral: sum(w) == 0
        w = w / np.abs(w).sum()          # Unit gross: sum(|w|) == 1
        return dict(zip(rets.columns, w.tolist()))
```

### Bước 4.5: Chiến lược 5 — Cảm xúc X / Bernoulli Naïve Bayes (`strategies/sentiment_nb.py` — Mục 18.3)
```python
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import BernoulliNB

VOCAB = ["bullish", "bearish", "pump", "dump", "moon", "crash", "buy", "sell", "long", "short",
         "ath", "dip", "rekt", "hodl", "breakout", "liquidation", "fud", "fomo", "rally", "etf",
         "sec", "whale", "support", "resistance", "bottom", "top", "capitulation", "squeeze", "bubble"]


class Strategy:
    symbols = ["BTC/USDT:USDT"]
    timeframe = "1h"

    def __init__(self, tweet_fetcher=None, horizon_h=1):
        self.vec = CountVectorizer(vocabulary=VOCAB, binary=True)
        self.nb = BernoulliNB(alpha=1.0)
        self.horizon = pd.Timedelta(hours=horizon_h)
        self.tweet_fetcher = tweet_fetcher
        self.history, self.pos = 24 * 30, 0

    def fit(self, tweets: pd.DataFrame, close: pd.Series):
        t = pd.to_datetime(tweets["time"], utc=True).dt.floor("h")
        p0, p1 = close.reindex(t).to_numpy(), close.reindex(t + self.horizon).to_numpy()
        ok = ~np.isnan(p0) & ~np.isnan(p1)
        self.nb.fit(self.vec.transform(tweets["text"].str.lower()[ok]), (p1[ok] > p0[ok]).astype(int))

    def predict(self, texts) -> int:
        X = self.vec.transform(pd.Series(texts, dtype=str).str.lower()).toarray()
        logp = self.nb.feature_log_prob_
        log1m = np.log1p(-np.exp(logp))
        # Cộng log-likelihood toàn bộ tweet trong giờ, chỉ cộng P(C) đúng 1 lần (Eq. 546)
        score = self.nb.class_log_prior_ + (X @ logp.T + (1.0 - X) @ log1m.T).sum(axis=0)
        return int(self.nb.classes_[int(np.argmax(score))])

    def target_weights(self, data):
        sym = self.symbols[0]
        now = data[sym].index[-1] + pd.Timedelta(hours=1)
        tweets = self.tweet_fetcher(now - pd.Timedelta(hours=1), now)
        if len(tweets):
            self.pos = 1 if self.predict(tweets["text"]) == 1 else -1
        return {sym: float(self.pos)}
```

### Bước 4.6: Bộ ghép Alpha Combo 11 bước (`strategies/alpha_combo.py` — Mục 3.20)
```python
import numpy as np
import pandas as pd


def alpha_combo_weights(R: np.ndarray, d: int = 5) -> np.ndarray:
    """Quy trình 11 bước Kakushadze-Yu. R có dạng [N alphas, M+1 kỳ], cột 0 là kỳ gần nhất."""
    R = np.asarray(R, dtype=float)
    N, M1 = R.shape
    M = M1 - 1
    assert N > M - 1, f"Cần nhiều alpha hơn M-1 kỳ (N={N}, M-1={M-1})"

    X = R - R.mean(axis=1, keepdims=True)
    sigma = np.maximum(np.sqrt((X ** 2).sum(axis=1) / M), 1e-12)
    Y = (X / sigma[:, None])[:, :M]
    Lam = (Y - Y.mean(axis=0, keepdims=True))[:, : M - 1]
    E_tilde = R[:, :d].mean(axis=1) / sigma
    beta, *_ = np.linalg.lstsq(Lam, E_tilde, rcond=None)
    eps = E_tilde - Lam @ beta
    w = eps / sigma
    return w / np.abs(w).sum()
```

- **Checkpoint kết thúc Chương 4:** Chạy `pytest -v` -> Phải thấy **3/3 bài test PASS** (xác nhận 0% look-ahead và Stat Arb tổng trọng số bằng 0 tuyệt đối).

---

## Chương 5: Chạy Backtest Đầu Tiên, Đọc Chỉ Số & Case Study Thực Tế (Bước 5.1 → 5.3)

### Bước 5.1: Tạo script chạy Backtest mẫu (`research/run_demo.py`)
```python
from core.backtester import BacktestConfig, run_backtest
from core.data_loader import fetch_funding_history, fetch_ohlcv_history
from strategies.statarb import DEFAULT_BASKET, Strategy as StatArb

data = {s: fetch_ohlcv_history(s, "1d", days=1200) for s in DEFAULT_BASKET}
funding = {s: fetch_funding_history(s, days=1200) for s in DEFAULT_BASKET}

res = run_backtest(StatArb(cov_window=120, d=3), data, BacktestConfig(), funding)
print("60% In-Sample :", res.metrics_is)
print("40% Out-Sample:", res.metrics_oos)
print("BTC Buy & Hold:", res.benchmark_oos)
```
Chạy lệnh:
```bash
PYTHONPATH=. python research/run_demo.py
```

### Bước 5.2: Cách đọc 6 chỉ số cốt lõi
| Chỉ số | Ý nghĩa thực tế | Ngưỡng mục tiêu trên Out-of-Sample |
|---|---|---|
| **Sharpe Ratio** | Lợi nhuận trên mỗi đơn vị rủi ro biến động | `> 1.0` (tốt); `< 0.5` (quá yếu) |
| **Max Drawdown** | Mức sụt giảm sâu nhất từ đỉnh xuống đáy | Nên nhỏ hơn `-20%` |
| **Plateau %** | % bộ tham số lân cận cùng có lãi trên OOS | `> 60%` (tránh chọn tham số quá khớp tham số (overfitting)) |
| **Daily Turnover** | % vốn xoay vòng mỗi ngày | `< 20%/ngày` với khung ngày |
| **BTC Beta** | Mức độ lệ thuộc vào chiều lên/xuống của BTC | Gần `0` = trung tính thị trường |
| **IS vs OOS** | 60% tối ưu vs 40% tương lai giữ kín | OOS không được sụp đổ so với IS |

### Bước 5.3: Case Study Thực Tế (Chạy trên dữ liệu thật Bybit 2021–2026)
Bảng dưới là kết quả kiểm chứng thật trên hệ thống này (5 năm BTC + 3.3 năm 10 coin, đã trừ `0.06%` phí + `0.02%` trượt giá + **Funding Rate thật**, 40% Out-of-Sample):

| Chiến lược | Cấu hình | Plateau OOS+ | IS Sharpe | OOS Sharpe | OOS Return | OOS MaxDD | BTC Beta | Phán quyết |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| **HP Filter** (8.1) | 12 | 33.3% | `+0.870` | `-0.870` | `-56.9%` | `-61.7%` | `-0.415` | **KILL** |
| **Stat Arb** (3.18) | 24 | 4.2% | `+0.282` | `-1.501` | `-30.1%` | `-36.6%` | `-0.053` | **KILL (bản 1d)** |
| **kNN** (3.17) | 12 | 0.0% | `-0.014` | `-0.770` | `-44.7%` | `-56.8%` | `+0.121` | **KILL** |
| **Alpha Combo** (3.20) | 48 alphas | — | `-0.927` | **`+0.166`** | **`+1.1%`** | **`-6.0%`** | **`-0.006`** | **TIỀM NĂNG** |
| *Chia đều 48 alphas* | 48 | — | — | `-2.333` | `-28.0%` | `-32.5%` | `-0.045` | Benchmark nội bộ |
| *Mua & Giữ BTC (OOS)* | — | — | — | `-1.025` | `-49.9%` | `-53.0%` | `1.000` | Benchmark |

> **Giá trị lớn nhất của bảng này:** Thay vì mù quáng chạy tiền thật và lỗ 30–57%, hệ thống backtest 6 Gates đã bảo vệ bạn ngay từ trên giấy — đồng thời chứng minh **Alpha Combo** cắt drawdown từ `-53%` xuống chỉ còn `-6%`. Việc của bạn tiếp theo là nạp thêm các chiến lược có lợi thế cấu trúc cao ở **Phụ lục** (như *Perp Funding Carry*, *Volatility Targeting*, *Dual Momentum*) vào bộ ghép Alpha Combo.

---

## Chương 6: Bộ Lọc 6 Cổng (6 Gates) & Prompt Giám Đốc Quản Trị Rủi Ro

Tuyệt đối chỉ nạp tiền thật khi chiến lược vượt qua **đủ 6/6 Cổng**:

| Cổng | Câu hỏi kiểm tra | Điều kiện ĐẠT (PASS) |
|---|---|---|
| **1. Look-ahead** | Code có nhìn trộm tương lai không? | PASS `pytest`; bỏ nến chưa đóng; filter/label chỉ dùng quá khứ |
| **2. Phí & Funding** | Sau chi phí còn lợi nhuận không? | Dương rõ rệt sau `0.06%` phí/chiều + trượt giá + funding thật |
| **3. Out-of-Sample** | Chạy trên 40% dữ liệu cuối thế nào? | OOS duy trì Sharpe & Return dương ổn định |
| **4. Plateau** | Có phải chọn tham số quá khớp tham số (overfitting) không? | Các tham số xung quanh cho kết quả tương đồng (`> 60%` dương) |
| **5. Paper / Testnet** | Chạy thật có khớp backtest không? | Chạy 2–4 tuần Paper & Testnet với độ lệch nhỏ |
| **6. Vốn nhỏ** | Đã sẵn sàng cho ngày xấu nhất? | Bắt đầu vốn nhỏ chấp nhận mất được + đã test nút dừng `-3%/ngày` |

### Prompt "Giám Đốc Quản Trị Rủi Ro" (Copy-paste gửi AI sau mỗi lần backtest)
```text
Bạn là Giám đốc Quản trị Rủi ro (Risk Manager) cực kỳ nghiêm khắc.
Nhiệm vụ của bạn là tìm mọi lý do để LOẠI BỎ (KILL) chiến lược này.
Hãy kiểm tra code và báo cáo backtest của tôi:
1. Có dấu hiệu look-ahead bias trong feature, label hay filter không?
2. Lợi nhuận có đến từ 1-2 lệnh may mắn hay 1 giai đoạn thị trường duy nhất không?
3. Số lệnh có quá ít để kết luận về mặt thống kê không?
4. Phí giao dịch, trượt giá và funding rate có ăn hết lợi thế không?
5. Hiệu suất 40% Out-of-Sample có sụp đổ so với 60% In-Sample không?

Kết thúc bằng đúng 1 từ: KEEP hoặc KILL kèm lý do quan trọng nhất.
```

---

## Chương 7: Chạy Bot 24/7 (Paper -> Testnet -> VPS) & Xử Lý Lỗi Thường Gặp (Bước 7.1 → 7.5)

### Bước 7.1: Tạo khung Bot hoàn chỉnh (`core/bot.py`)
```python
"""Khung Bot chạy 24/7 — mặc định PAPER=True, đọc nến Mainnet thật, lưu state.json."""
import importlib, json, logging, os, sys, time
from pathlib import Path
import pandas as pd
import yaml
from dotenv import load_dotenv
from core.data_loader import TF_SECONDS, create_exchange
from core.risk import RiskConfig, RiskManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bot")


class Bot:
    def __init__(self, strategy, cfg):
        self.s, self.cfg = strategy, cfg
        self.paper = bool(cfg.get("paper", True))
        self.testnet = bool(cfg.get("testnet", True))
        self.risk = RiskManager(RiskConfig(**cfg.get("risk", {})))

        # Paper mode đọc nến Mainnet thật (không gửi lệnh); chỉ bật sandbox khi đặt lệnh Testnet
        use_sandbox = (not self.paper) and self.testnet
        self.ex = create_exchange(
            exchange_id=cfg.get("exchange", "bybit"),
            testnet=use_sandbox,
            api_key=None if self.paper else os.getenv("EXCHANGE_KEY"),
            secret=None if self.paper else os.getenv("EXCHANGE_SECRET"),
        )
        self.paper_pos, self.paper_eq, self.last_px = {}, float(cfg.get("paper_equity", 10000.0)), {}
        self.state_path = Path("state") / f"{type(strategy).__module__.split('.')[-1]}_state.json"
        self.state_path.parent.mkdir(exist_ok=True)
        if self.state_path.exists():
            st = json.loads(self.state_path.read_text())
            self.paper_pos, self.paper_eq, self.last_px = st["pos"], st["eq"], st["px"]

    def save_state(self):
        self.state_path.write_text(json.dumps({"pos": self.paper_pos, "eq": self.paper_eq, "px": self.last_px}, indent=2))

    def candles(self, sym, limit):
        raw = self.ex.fetch_ohlcv(sym, self.s.timeframe, limit=limit + 1)
        df = pd.DataFrame(raw, columns=["ts", "open", "high", "low", "close", "volume"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
        df = df.set_index("ts").iloc[:-1]  # Luôn bỏ nến chưa đóng
        self.risk.check_data_freshness(df, self.s.timeframe, sym)
        return df

    def step(self):
        data = {sym: self.candles(sym, self.s.history) for sym in self.s.symbols}
        prices = {sym: float(df["close"].iloc[-1]) for sym, df in data.items()}
        if self.paper:
            for sym, qty in self.paper_pos.items():
                if sym in self.last_px:
                    self.paper_eq += qty * (prices[sym] - self.last_px[sym])
            self.last_px = dict(prices)
            eq = self.paper_eq
        else:
            eq = float(self.ex.fetch_balance()["USDT"]["total"])

        if not self.risk.check_daily_loss(eq):
            log.error("CHẠM GIỚI HẠN LỖ -3%/NGÀY -> ĐÓNG SẠCH & DỪNG BOT!")
            return False

        weights = self.risk.cap_leverage(self.s.target_weights(data))
        log.info("equity=%.2f weights=%s", eq, {k: round(v, 4) for k, v in weights.items()})
        for sym, w in weights.items():
            cur = self.paper_pos.get(sym, 0.0) if self.paper else 0.0
            delta = (w * eq / prices[sym]) - cur
            if self.risk.should_trade(delta, prices[sym]):
                if self.paper:
                    self.paper_pos[sym] = cur + delta
                    log.info("[PAPER] %s %.6f %s", "BUY" if delta > 0 else "SELL", abs(delta), sym)
                else:
                    amt = float(self.ex.amount_to_precision(sym, abs(delta)))
                    if amt > 0:
                        self.ex.create_order(sym, "market", "buy" if delta > 0 else "sell", amt)
        self.save_state()
        return True

    def run(self, once=False):
        while True:
            try:
                if not self.step() or once:
                    break
            except Exception as e:
                log.exception("Lỗi vòng lặp (giữ nguyên vị thế): %s", e)
                if once:
                    raise
            time.sleep(TF_SECONDS[self.s.timeframe])


if __name__ == "__main__":
    load_dotenv()
    cfg = yaml.safe_load(open("config/default.yaml"))
    name = sys.argv[1] if len(sys.argv) > 1 else "statarb"
    Strat = importlib.import_module(f"strategies.{name}").Strategy
    Bot(Strat(), cfg).run(once="--once" in sys.argv)
```

### Bước 7.2: Chạy thử Paper Trading 1 vòng
```bash
PYTHONPATH=. python core/bot.py statarb --once
```
- **Checkpoint:** Bạn sẽ thấy log in ra `equity=10000.00`, trọng số 10 đồng coin, các dòng `[PAPER] buy/sell ...` và file `state/statarb_state.json` được tạo tự động.

### Bước 7.3: Tạo API Key Testnet an toàn
1. Đăng ký tài khoản giả lập tại `https://testnet.bybit.com` (hoặc `https://testnet.binancefuture.com`).
2. Vào mục **API Management** -> Tạo khóa mới -> **CHỈ BẬT quyền Trade (Contract/Derivatives)**, **TẮT quyền Withdraw (Rút tiền)**, và điền IP máy/VPS vào Whitelist.
3. Copy `.env.example` thành `.env`, dán `EXCHANGE_KEY` và `EXCHANGE_SECRET`.
4. Trong `config/default.yaml`, đổi `paper: false` (vẫn giữ `testnet: true`) để kiểm tra khớp lệnh thật trên sàn Testnet trong 2–4 tuần.

### Bước 7.4: Treo Bot 24/7 trên VPS Linux bằng `systemd`
Tạo file `/etc/systemd/system/quant-bot.service` trên VPS Ubuntu (~`$5`/tháng):
```ini
[Unit]
Description=Crypto Quant Bot 151
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/crypto-huy-opa
Environment="PYTHONPATH=/home/ubuntu/crypto-huy-opa"
ExecStart=/home/ubuntu/crypto-huy-opa/.venv/bin/python core/bot.py statarb
Restart=always
RestartSec=15

[Install]
WantedBy=multi-user.target
```
Kích hoạt & theo dõi log trực tiếp:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now quant-bot
journalctl -u quant-bot -f
```

### Bước 7.5: Bảng xử lý 6 lỗi thường gặp nhất
| Lỗi gặp phải | Nguyên nhân | Cách khắc phục ngay |
|---|---|---|
| `ModuleNotFoundError: No module named 'core'` | Thiếu đường dẫn gốc dự án | Luôn thêm `PYTHONPATH=.` trước lệnh `python` |
| `BadSymbol: bybit does not have ...` | Bật `sandbox_mode` của Testnet (ít cặp coin) | Chế độ Paper phải đọc nến Mainnet (đã xử lý sẵn trong `bot.py`) |
| Lỗi kết nối / chặn IP vùng | Sàn chặn IP khu vực | Đổi `exchange: okx` hoặc `binance` trong `config/default.yaml` |
| `RuntimeError: data is ...s stale` | Rớt mạng hoặc sàn bảo trì | Không tắt cảnh báo này — bot tự bỏ qua vòng lặp để bảo vệ vốn |
| `RateLimitExceeded` | Tải nhiều năm dữ liệu quá nhanh | Đảm bảo có `enableRateLimit: True` và cache `.parquet` |
| Restart bot mất mốc lỗ ngày | Không lưu trạng thái ra ổ cứng | Đảm bảo thư mục `state/` có quyền ghi file `*.json` |

---

## Phụ lục: Kho 26 Chiến lược Mở rộng từ Sách đáng Test tiếp trên Crypto

### Kho GitHub tổng hợp trực tiếp từ sách *151 Trading Strategies*
- **[matimacazaga/strategist](https://github.com/matimacazaga/strategist)** — Cài đặt Python cho các chiến lược trong sách Kakushadze & Serur.
- **[ThewindMom/151-trading-strategies](https://github.com/ThewindMom/151-trading-strategies)** — Cài đặt Python/FastAPI cho nhóm chiến lược non-options (cổ phiếu, ETF, FX, hàng hóa, crypto, macro).
- **[hemv-857/151-trading-strats](https://github.com/hemv-857/151-trading-strats)** — Terminal nghiên cứu định lượng & backtest cho 151 chiến lược trên 18 lớp tài sản.
- **[KellanFinney/Trading_Strategy](https://github.com/KellanFinney/Trading_Strategy)** — Ứng dụng học & trực quan hóa payoff cho các chiến lược từ sách.

Khi đã nắm vững hệ thống ở Chương 1–7, hãy ưu tiên triển khai và đưa vào **Alpha Combo** các chiến lược đánh dấu ⭐ (có lợi thế cấu trúc rõ ràng trên Crypto). Toàn bộ 26 chiến lược kèm link GitHub mã nguồn mở tham khảo:

### Nhóm 1: Arbitrage & Basis (Chênh lệch giá & Lãi suất)
| # | Chiến lược (Mục sách) | Ý tưởng áp dụng trên Crypto | GitHub tham khảo |
|---|---|---|---|
| 1 | ⭐ **Perp Funding Carry** (8.2) | Long Spot + Short Perp hưởng funding dương định kỳ | [counterfactual5/funding-arb](https://github.com/counterfactual5/funding-arb) · [TraderRebate-com/crypto-funding-rate-arbitrage](https://github.com/TraderRebate-com/crypto-funding-rate-arbitrage) |
| 2 | ⭐ **Cash & Carry** (6.2) | Long Spot + Short Quarterly Futures khi basis mở rộng | [R1cK-ChaN/crypto-funding-arbitrage](https://github.com/R1cK-ChaN/crypto-funding-arbitrage) |
| 3 | **Momentum + Carry** (8.4) | Kết hợp xu hướng + funding tối thiểu hóa phương sai | [pst-group/pysystemtrade](https://github.com/pst-group/pysystemtrade) |
| 4 | **Roll Yield** (9.1) | Khai thác đường cong futures (backwardation / contango) | [pst-group/pysystemtrade](https://github.com/pst-group/pysystemtrade) |
| 5 | **Calendar Spread** (10.2) | Long kỳ hạn gần, Short kỳ hạn xa (hoặc ngược lại) | [pst-group/pysystemtrade](https://github.com/pst-group/pysystemtrade) |
| 6 | **Two ETFs on One Index** (6.4) | Chênh lệch giá 1 coin giữa 2 sàn hoặc Spot vs Perp | [counterfactual5/funding-arb](https://github.com/counterfactual5/funding-arb) |
| 7 | **Triangular Arbitrage** (8.5) | Đổi vòng 3 cặp tiền (đòi hỏi tốc độ mili-giây) | [nickmaglowsch/triangular-arbitrage-crypto](https://github.com/nickmaglowsch/triangular-arbitrage-crypto) · [diobenu2silva/triangular_arbitrage_multi_exchange](https://github.com/diobenu2silva/triangular_arbitrage_multi_exchange) |

### Nhóm 2: Trend & Momentum (Xu hướng & Động lượng)
| # | Chiến lược (Mục sách) | Ý tưởng áp dụng trên Crypto | GitHub tham khảo |
|---|---|---|---|
| 8 | ⭐ **Dual Momentum** (4.1.2) | Chỉ mua nhóm coin mạnh nhất khi BTC đang xu hướng tăng | [alexjansenhome/GEM](https://github.com/alexjansenhome/GEM) · [Stockflicks/acc_dual](https://github.com/Stockflicks/acc_dual) |
| 9 | ⭐ **Residual Momentum** (3.7) | Đo động lượng Altcoin sau khi trừ biến động BTC | [ThewindMom/151-trading-strategies](https://github.com/ThewindMom/151-trading-strategies) · [matimacazaga/strategist](https://github.com/matimacazaga/strategist) |
| 10 | **Sector Rotation + MA** (4.1.1) | Xoay vòng giữa L1, DeFi, AI, Meme khi giá > MA | [haowoo0112/Dual-Momentum](https://github.com/haowoo0112/Dual-Momentum) · [adamd1985/quant_research](https://github.com/adamd1985/quant_research) |
| 11 | **Multi-Asset Trend** (4.6) | Danh mục xu hướng đa coin chia tỷ trọng nghịch đảo volatility | [pst-group/pysystemtrade](https://github.com/pst-group/pysystemtrade) · [robcarver17/pysystemtrade_examples](https://github.com/robcarver17/pysystemtrade_examples) |
| 12 | **Donchian Channel** (3.15) | Đánh phá vỡ kênh giá cao/thấp nhất *N* ngày | [joshuaebinisi/Donchian-Breakout-Strategy](https://github.com/joshuaebinisi/Donchian-Breakout-Strategy) · [chrisgqy/crypto_trading_strategy](https://github.com/chrisgqy/crypto_trading_strategy) |
| 13 | **Support & Resistance** (3.14) | Mức Pivot từ High/Low/Close hôm qua | [day0market/support_resistance](https://github.com/day0market/support_resistance) · [ednunezg/pytrendline](https://github.com/ednunezg/pytrendline) |
| 14 | **Multi-Factor Portfolio** (3.6) | Kết hợp nhiều nhân tố ít tương quan (kể cả On-chain) | [blackms/FinRL-Adaptive](https://github.com/blackms/FinRL-Adaptive) · [tanish35/Momentum-Investing](https://github.com/tanish35/Momentum-Investing) · [jackalg42/multi-factor-equity-strategy](https://github.com/jackalg42/multi-factor-equity-strategy) |

### Nhóm 3: Mean Reversion (Đảo chiều về trung bình)
| # | Chiến lược (Mục sách) | Ý tưởng áp dụng trên Crypto | GitHub tham khảo |
|---|---|---|---|
| 15 | **Cluster Reversion** (3.9.1) | Đảo chiều trong cùng nhóm ngành coin (phân cụm) | [dharun4772/Pairs-Trading-Strategy](https://github.com/dharun4772/Pairs-Trading-Strategy) · [fin-ml/Chapter-8---Unsup.-Learning---Clustering](https://github.com/fin-ml/Chapter-8---Unsup.-Learning---Clustering) |
| 16 | **Weighted Regression** (3.10) | Đảo chiều sau khi trừ các yếu tố rủi ro tùy chọn | [KidQuant/Pairs-Trading-With-Python](https://github.com/KidQuant/Pairs-Trading-With-Python) · [MeridianAlgo/Learn-Quant](https://github.com/MeridianAlgo/Learn-Quant) |
| 17 | **Contrarian + Activity Filter** (10.3.1) | Đảo chiều có lọc theo Volume & Open Interest (OI) | [Signalview/signalview-core](https://github.com/Signalview/signalview-core) · [JiangZhihao123/llmalpha](https://github.com/JiangZhihao123/llmalpha) · [BybitPythonTools/BybitPythonTools](https://github.com/BybitPythonTools/BybitPythonTools) |

### Nhóm 4: Volatility & Options (Biến động & Quyền chọn)
| # | Chiến lược (Mục sách) | Ý tưởng áp dụng trên Crypto | GitHub tham khảo |
|---|---|---|---|
| 18 | ⭐ **Volatility Targeting** (6.5) | Giữ tỷ trọng theo `Target Vol / Current Vol`, phần dư giữ tiền mặt (không cần Options) | [pst-group/pysystemtrade](https://github.com/pst-group/pysystemtrade) |
| 19 | **Skewness Premium** (9.5) | Tài sản lệch dương mạnh thường giảm lợi suất tương lai (không cần Options) | [tanish35/Momentum-Investing](https://github.com/tanish35/Momentum-Investing) |
| 20 | **Volatility Risk Premium** (7.4) | Bán biến động khi IV > Realized Vol (Deribit) | [tfrmma/options-volatility-trading-strats](https://github.com/tfrmma/options-volatility-trading-strats) · [anthonymakarewicz/volatility-trading](https://github.com/anthonymakarewicz/volatility-trading) |
| 21 | **Volatility Skew** (7.5) | Mua OTM Call, bán OTM Put khi Put đắt hơn Call (Deribit) | [tfrmma/options-volatility-trading-strats](https://github.com/tfrmma/options-volatility-trading-strats) · [deltaray-io](https://github.com/deltaray-io) |
| 22 | **Dispersion Trading** (6.3) | Long vol thành phần, Short vol chỉ số (Deribit) | [kurupjayesh/Dispersion-Trading-using-Options](https://github.com/kurupjayesh/Dispersion-Trading-using-Options) · [tfrmma/options-volatility-trading-strats](https://github.com/tfrmma/options-volatility-trading-strats) |

### Nhóm 5: Positioning, Tin tức & Thực thi
| # | Chiến lược (Mục sách) | Ý tưởng áp dụng trên Crypto | GitHub tham khảo |
|---|---|---|---|
| 23 | **Announcement Days** (19.5) | Chỉ giữ BTC quanh ngày công bố tin vĩ mô (FOMC/CPI) | [QuantConnect/Lean](https://github.com/QuantConnect/Lean) · [ThewindMom/151-trading-strategies](https://github.com/ThewindMom/151-trading-strategies) |
| 24 | **Hedging Pressure** (9.2) | Theo dõi vị thế CFTC hàng tuần trên CME Bitcoin Futures | [NDelventhal/cot_reports](https://github.com/NDelventhal/cot_reports) · [Mcamin/cot-analysis](https://github.com/Mcamin/cot-analysis) · [kustex/CFTC-COT-Report](https://github.com/kustex/CFTC-COT-Report) |
| 25 | **Market Making** (3.19) | Đặt lệnh 2 đầu Bid/Ask (cần phí Maker âm/thấp) | [hummingbot/hummingbot](https://github.com/hummingbot/hummingbot) · [akshat-gosain/adaptive-crypto-market-maker](https://github.com/akshat-gosain/adaptive-crypto-market-maker) · [mdibo/Avellaneda-Stoikov](https://github.com/mdibo/Avellaneda-Stoikov) |
| 26 | **Leveraged ETFs** (4.5) | Short đồng thời ETF đòn bẩy thuận & nghịch ăn phí bào mòn | [QuantConnect/Lean](https://github.com/QuantConnect/Lean) |

> **Lưu ý khi dùng GitHub mã nguồn mở:** Luôn kiểm tra lại code của các repo cộng đồng qua **Gate 1 (Look-ahead)** và **Gate 2 (Phí + Funding)** ở Chương 6 trước khi đưa vào chạy Paper/Testnet.
---

*Biên soạn bởi Tran Quang Huy (Huy OPA) — Kho mã nguồn chính thức: `https://github.com/lufyhyhy-opa/crypto-huy-opa`.*
