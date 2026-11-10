
import numpy as np
import pandas as pd


REQUIRED_COLUMNS = ["open", "high", "low", "close", "volume"]


def _safe_divide(numerator, denominator):
    """Chia an toàn, mẫu số bằng 0 trả về NaN."""
    denominator = denominator.replace(0, np.nan)
    return numerator / denominator


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Chuẩn hóa OHLCV và tính các chỉ báo kỹ thuật.

    - MA chỉ có giá trị khi đủ số phiên.
    - Không giả lập MA50, MA100, MA200.
    - Dữ liệu thiếu trả về NaN, không tự điền 0.
    """

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("Dữ liệu đầu vào trống hoặc không hợp lệ.")

    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in out.columns]
    if missing:
        raise ValueError(
            "Thiếu cột OHLCV bắt buộc: " + ", ".join(missing)
        )

    if "date" in out.columns:
        out["date"] = pd.to_datetime(
            out["date"], errors="coerce"
        )

    for col in REQUIRED_COLUMNS:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out = out.dropna(subset=REQUIRED_COLUMNS)

    out = out[
        (out["close"] > 0)
        & (out["open"] > 0)
        & (out["high"] > 0)
        & (out["low"] > 0)
        & (out["volume"] >= 0)
    ]

    out = out[out["high"] >= out["low"]]

    if "date" in out.columns:
        out = out.dropna(subset=["date"])
        out = (
            out.sort_values("date")
            .drop_duplicates("date", keep="last")
        )

    out = out.reset_index(drop=True)

    if out.empty:
        raise ValueError("Không còn dòng OHLCV hợp lệ.")

    close = out["close"]
    volume = out["volume"]

    # 1. MA10, MA20, MA50, MA100, MA200
    for window in (10, 20, 50, 100, 200):
        out[f"MA{window}"] = close.rolling(
            window=window,
            min_periods=window
        ).mean()

    # 2. Trung bình khối lượng
    for window in (10, 20, 50):
        out[f"VOL_MA{window}"] = volume.rolling(
            window=window,
            min_periods=window
        ).mean()

    # 3. RSI14 - phương pháp Wilder
    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / 14,
        min_periods=14,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / 14,
        min_periods=14,
        adjust=False
    ).mean()

    rs = _safe_divide(avg_gain, avg_loss)

    rsi = 100 - (100 / (1 + rs))

    rsi = rsi.mask(
        (avg_loss == 0) & (avg_gain > 0), 100
    )

    rsi = rsi.mask(
        (avg_loss == 0) & (avg_gain == 0), 50
    )

    out["RSI14"] = rsi

    # 4. MACD (12, 26, 9)
    ema12 = close.ewm(
        span=12,
        adjust=False,
        min_periods=12
    ).mean()

    ema26 = close.ewm(
        span=26,
        adjust=False,
        min_periods=26
    ).mean()

    out["MACD"] = ema12 - ema26

    out["MACD_SIGNAL"] = out["MACD"].ewm(
        span=9,
        adjust=False,
        min_periods=9
    ).mean()

    out["MACD_HIST"] = (
        out["MACD"] - out["MACD_SIGNAL"]
    )

    # 5. Bollinger Bands (20, 2)
    bb_middle = close.rolling(
        window=20,
        min_periods=20
    ).mean()

    bb_std = close.rolling(
        window=20,
        min_periods=20
    ).std(ddof=0)

    out["BB_MIDDLE"] = bb_middle
    out["BB_UPPER"] = bb_middle + (2 * bb_std)
    out["BB_LOWER"] = bb_middle - (2 * bb_std)

    # 6. MFI14
    typical_price = (
        out["high"] + out["low"] + close
    ) / 3.0

    raw_money_flow = typical_price * volume

    direction = typical_price.diff()

    positive_flow = raw_money_flow.where(
        direction > 0, 0.0
    )

    negative_flow = raw_money_flow.where(
        direction < 0, 0.0
    )

    positive_sum = positive_flow.rolling(
        14, min_periods=14
    ).sum()

    negative_sum = negative_flow.rolling(
        14, min_periods=14
    ).sum()

    money_ratio = _safe_divide(
        positive_sum, negative_sum
    )

    mfi = 100 - (100 / (1 + money_ratio))

    mfi = mfi.mask(
        (negative_sum == 0) & (positive_sum > 0), 100
    )

    mfi = mfi.mask(
        (negative_sum == 0) & (positive_sum == 0), 50
    )

    out["MFI14"] = mfi

    # 7. ATR14
    previous_close = close.shift(1)

    true_range = pd.concat(
        [
            out["high"] - out["low"],
            (out["high"] - previous_close).abs(),
            (out["low"] - previous_close).abs(),
        ],
        axis=1
    ).max(axis=1)

    out["ATR14"] = true_range.rolling(
        14, min_periods=14
    ).mean()

    # 8. OBV
    price_direction = np.sign(
        close.diff()
    ).fillna(0)

    out["OBV"] = (
        price_direction * volume
    ).cumsum()

    # 9. CMF20
    price_range = (
        out["high"] - out["low"]
    ).replace(0, np.nan)

    money_flow_multiplier = (
        (
            (close - out["low"])
            - (out["high"] - close)
        ) / price_range
    ).replace([np.inf, -np.inf], np.nan)

    money_flow_multiplier = (
        money_flow_multiplier.fillna(0)
    )

    money_flow_volume = (
        money_flow_multiplier * volume
    )

    cmf_numerator = money_flow_volume.rolling(
        20, min_periods=20
    ).sum()

    cmf_denominator = volume.rolling(
        20, min_periods=20
    ).sum()

    out["CMF20"] = _safe_divide(
        cmf_numerator, cmf_denominator
    )

    return out
