import numpy as np
import pandas as pd

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    
    # 1. CHUẨN HÓA TÊN CỘT: Chuyển toàn bộ tên cột về chữ thường và bỏ khoảng trắng thừa
    out.columns = [str(col).strip().lower() for col in out.columns]
    
    # 2. Ép kiểu an toàn cho toàn bộ các cột số liệu
    for col in ["open", "high", "low", "close", "volume"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
            
    # 3. Kiểm tra xem cột 'close' có thực sự tồn tại sau khi chuẩn hóa không
    if "close" not in out.columns:
        raise ValueError(f"Dữ liệu của bạn không có cột 'close'! Các cột hiện có là: {list(out.columns)}")

    # Xóa các dòng có giá trị close bị trống (None / NaN)
    out = out.dropna(subset=["close"]).reset_index(drop=True)

    # Các phần tính toán chỉ báo giữ nguyên như cũ...
    for window in [10, 20, 50, 100, 200]:
        out[f"MA{window}"] = out["close"].rolling(window, min_periods=1).mean()

    for window in [10, 20, 50]:
        out[f"VOL_MA{window}"] = out["volume"].rolling(window, min_periods=1).mean()

    delta = out["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=1, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out["RSI14"] = 100 - (100 / (1 + rs))

    ema12 = out["close"].ewm(span=12, adjust=False).mean()
    ema26 = out["close"].ewm(span=26, adjust=False).mean()
    out["MACD"] = ema12 - ema26
    out["MACD_SIGNAL"] = out["MACD"].ewm(span=9, adjust=False).mean()
    out["MACD_HIST"] = out["MACD"] - out["MACD_SIGNAL"]

    ma20 = out["MA20"]
    std20 = out["close"].rolling(20, min_periods=1).std()
    out["BB_UPPER"] = ma20 + (std20 * 2)
    out["BB_LOWER"] = ma20 - (std20 * 2)
    out["BB_MIDDLE"] = ma20

    tp = (out["high"] + out["low"] + out["close"]) / 3.0
    rmf = tp * out["volume"]
    pos_flow = pd.Series(np.where(tp > tp.shift(1), rmf, 0.0), index=out.index)
    neg_flow = pd.Series(np.where(tp < tp.shift(1), rmf, 0.0), index=out.index)
    pos_mf14 = pos_flow.rolling(14, min_periods=1).sum()
    neg_mf14 = neg_flow.rolling(14, min_periods=1).sum()
    mfr = pos_mf14 / neg_mf14.replace(0, np.nan)
    out["MFI14"] = 100 - (100 / (1 + mfr))

    high_low = out["high"] - out["low"]
    high_cp = (out["high"] - out["close"].shift(1)).abs()
    low_cp = (out["low"] - out["close"].shift(1)).abs()
    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    out["ATR14"] = tr.rolling(14, min_periods=1).mean()

    return out
