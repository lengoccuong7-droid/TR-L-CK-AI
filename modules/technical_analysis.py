
import pandas as pd
import numpy as np


# =========================================================
# 1. CHUẨN HÓA VÀ KIỂM TRA DỮ LIỆU
# =========================================================

def _get_column(df, name):
    """Lấy cột không phân biệt chữ hoa, chữ thường."""
    lookup = {str(col).strip().lower(): col for col in df.columns}
    col = lookup.get(name.lower())

    if col is None:
        return None

    return pd.to_numeric(df[col], errors="coerce")


def _last_value(df, name):
    series = _get_column(df, name)

    if series is None or series.empty:
        return None

    values = series.dropna()

    if values.empty:
        return None

    value = float(values.iloc[-1])

    return value if np.isfinite(value) else None


def _number(value):
    try:
        value = float(value)
        return value if np.isfinite(value) else None
    except (TypeError, ValueError):
        return None


# =========================================================
# 2. XÁC ĐỊNH ĐỈNH VÀ ĐÁY ĐÃ XÁC NHẬN
# =========================================================

def _confirmed_pivots(series, left=3, right=3, max_bars=80):
    """
    Xác định các đỉnh và đáy bằng dữ liệu quá khứ.
    Một điểm chỉ được xác nhận khi đã có đủ nến bên phải.
    """

    values = pd.to_numeric(series, errors="coerce").dropna()

    if len(values) > max_bars:
        values = values.iloc[-max_bars:]

    highs = []
    lows = []

    data = values.to_numpy()

    if len(data) < left + right + 1:
        return highs, lows

    for i in range(left, len(data) - right):
        current = data[i]

        before = data[i - left:i]
        after = data[i + 1:i + right + 1]

        if not np.isfinite(current):
            continue

        if current > max(before) and current > max(after):
            highs.append((i, float(current)))

        if current < min(before) and current < min(after):
            lows.append((i, float(current)))

    return highs, lows


# =========================================================
# 3. ĐÁNH GIÁ CẤU TRÚC ĐỈNH ĐÁY
# =========================================================

def _evaluate_structure(df):

    result = {
        "structure": "CHƯA ĐỦ DỮ LIỆU",
        "pivot_highs": [],
        "pivot_lows": [],
        "structure_detail": "Chưa có đủ điểm xoay chiều đã xác nhận."
    }

    high_series = _get_column(df, "high")
    low_series = _get_column(df, "low")

    if high_series is None or low_series is None:
        return result

    highs, _ = _confirmed_pivots(high_series)
    _, lows = _confirmed_pivots(low_series)

    result["pivot_highs"] = [
        round(float(x[1]), 4) for x in highs[-2:]
    ]

    result["pivot_lows"] = [
        round(float(x[1]), 4) for x in lows[-2:]
    ]

    if len(highs) < 2 or len(lows) < 2:
        return result

    higher_high = highs[-1][1] > highs[-2][1]
    lower_high = highs[-1][1] < highs[-2][1]

    higher_low = lows[-1][1] > lows[-2][1]
    lower_low = lows[-1][1] < lows[-2][1]

    if higher_high and higher_low:
        structure = "ĐỈNH SAU CAO HƠN, ĐÁY SAU CAO HƠN"
        detail = "Hai đỉnh và hai đáy gần nhất cùng nâng cao."

    elif lower_high and lower_low:
        structure = "ĐỈNH SAU THẤP HƠN, ĐÁY SAU THẤP HƠN"
        detail = "Hai đỉnh và hai đáy gần nhất cùng hạ thấp."

    elif higher_high and lower_low:
        structure = "BIẾN ĐỘNG MỞ RỘNG"
        detail = "Đỉnh cao hơn nhưng đáy thấp hơn."

    elif lower_high and higher_low:
        structure = "BIẾN ĐỘNG THU HẸP"
        detail = "Đỉnh thấp hơn nhưng đáy cao hơn."

    else:
        structure = "CẤU TRÚC CHƯA ĐỒNG THUẬN"
        detail = "Cấu trúc đỉnh đáy chưa xác nhận hướng rõ ràng."

    result.update({
        "structure": structure,
        "structure_detail": detail
    })

    return result


# =========================================================
# 4. PHÂN TÍCH XU HƯỚNG
# =========================================================

def _evaluate_trend(df):

    close = _last_value(df, "close")
    ma20 = _last_value(df, "MA20")
    ma50 = _last_value(df, "MA50")

    ma20_series = _get_column(df, "MA20")
    ma50_series = _get_column(df, "MA50")

    ma20_slope = None
    ma50_slope = None

    if ma20_series is not None:
        values = ma20_series.dropna()
        if len(values) >= 6 and values.iloc[-6] != 0:
            ma20_slope = (
                values.iloc[-1] - values.iloc[-6]
            ) / abs(values.iloc[-6]) * 100

    if ma50_series is not None:
        values = ma50_series.dropna()
        if len(values) >= 6 and values.iloc[-6] != 0:
            ma50_slope = (
                values.iloc[-1] - values.iloc[-6]
            ) / abs(values.iloc[-6]) * 100

    structure = _evaluate_structure(df)

    if close is None or ma20 is None:
        trend = "CHƯA ĐỦ DỮ LIỆU"

    elif (
        close > ma20
        and (ma50 is None or ma20 >= ma50)
        and (ma20_slope is None or ma20_slope > 0)
    ):
        trend = "TĂNG"

    elif (
        close < ma20
        and (ma50 is None or ma20 <= ma50)
        and (ma20_slope is None or ma20_slope < 0)
    ):
        trend = "GIẢM"

    elif close > ma20 and ma20_slope is not None and ma20_slope > 0:
        trend = "PHỤC HỒI KỸ THUẬT"

    else:
        trend = "ĐI NGANG / CHƯA RÕ XU HƯỚNG"

    slopes = {
        "MA20": ma20_slope,
        "MA50": ma50_slope
    }

    return trend, slopes, structure


# =========================================================
# 5. PHÂN TÍCH RSI VÀ MACD
# =========================================================

def _evaluate_momentum(df):

    rsi = _last_value(df, "RSI14")
    macd = _last_value(df, "MACD")
    macd_signal = _last_value(df, "MACD_SIGNAL")

    warnings = []

    if rsi is None:
        rsi_status = "CHƯA ĐỦ DỮ LIỆU"
    elif rsi >= 70:
        rsi_status = "QUÁ MUA"
        warnings.append("RSI ở vùng quá mua, cần thận trọng.")
    elif rsi <= 30:
        rsi_status = "QUÁ BÁN"
        warnings.append("RSI ở vùng quá bán, chưa đủ xác nhận đảo chiều.")
    elif rsi > 50:
        rsi_status = "ĐỘNG LƯỢNG TÍCH CỰC"
    else:
        rsi_status = "ĐỘNG LƯỢNG YẾU"

    if macd is None or macd_signal is None:
        macd_status = "CHƯA ĐỦ DỮ LIỆU"
    elif macd > macd_signal:
        macd_status = "MACD TÍCH CỰC"
    elif macd < macd_signal:
        macd_status = "MACD TIÊU CỰC"
    else:
        macd_status = "MACD TRUNG TÍNH"

    rsi_direction = None

    if rsi is not None:
        if 50 < rsi < 70:
            rsi_direction = 1
        elif rsi < 50:
            rsi_direction = -1
        else:
            rsi_direction = 0

    macd_direction = None

    if macd is not None and macd_signal is not None:
        macd_direction = (
            1 if macd > macd_signal
            else -1 if macd < macd_signal
            else 0
        )

    if rsi_direction is None or macd_direction is None:
        alignment = "CHƯA ĐỦ DỮ LIỆU"
    elif rsi_direction == macd_direction and rsi_direction != 0:
        alignment = "ĐỒNG THUẬN TÍCH CỰC" if rsi_direction > 0 else "ĐỒNG THUẬN TIÊU CỰC"
    else:
        alignment = "ĐỘNG LƯỢNG MÂU THUẪN"

    if rsi_status == "QUÁ MUA":
        momentum = "MẠNH NHƯNG CÓ RỦI RO QUÁ MUA"
    elif alignment == "ĐỒNG THUẬN TÍCH CỰC":
        momentum = "TÍCH CỰC"
    elif alignment == "ĐỒNG THUẬN TIÊU CỰC":
        momentum = "TIÊU CỰC"
    else:
        momentum = "CHƯA ĐỒNG THUẬN"

    return {
        "rsi14": rsi,
        "rsi_status": rsi_status,
        "macd": macd,
        "macd_signal": macd_signal,
        "macd_status": macd_status,
        "momentum": momentum,
        "momentum_alignment": alignment,
        "warnings": warnings
    }


# =========================================================
# 6. HÀM PHÂN TÍCH KỸ THUẬT CHÍNH
# =========================================================

def _evaluate_technical(df):

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return {
            "score": 0,
            "signals": [],
            "trend": "CHƯA ĐỦ DỮ LIỆU",
            "momentum": "CHƯA ĐỦ DỮ LIỆU",
            "structure": "CHƯA ĐỦ DỮ LIỆU",
            "trend_strength": "CHƯA ĐỦ DỮ LIỆU",
            "ma_status": "CHƯA ĐỦ DỮ LIỆU",
            "ma_slopes": {},
            "macd_status": "CHƯA ĐỦ DỮ LIỆU",
            "warnings": ["Không có dữ liệu hợp lệ."],
            "data_quality": "THIẾU DỮ LIỆU",
            "positive_signals": [],
            "negative_signals": [],
            "momentum_alignment": "CHƯA ĐỦ DỮ LIỆU",
            "structure_detail": "Chưa có dữ liệu.",
            "pivot_highs": [],
            "pivot_lows": [],
            "rsi14": None,
            "macd": None,
            "macd_signal": None,
            "position_score": 0,
            "slope_score": 0,
            "structure_score": 0
        }

    close = _last_value(df, "close")

    trend, slopes, structure_result = _evaluate_trend(df)
    momentum_result = _evaluate_momentum(df)

    signals = []
    positive = []
    negative = []
    warnings = list(momentum_result["warnings"])

    score = 0
    position_score = 0
    slope_score = 0
    structure_score = 0

    # MA: đánh giá vị trí giá một lần, không cộng trùng từng đường MA.
    ma20 = _last_value(df, "MA20")
    ma50 = _last_value(df, "MA50")

    if close is not None and ma20 is not None:
        if close > ma20:
            position_score += 1
            positive.append("Giá đóng cửa nằm trên MA20.")
        else:
            position_score -= 1
            negative.append("Giá đóng cửa nằm dưới MA20.")

    if close is not None and ma20 is not None and ma50 is not None:
        if close > ma20 > ma50:
            position_score += 1
            positive.append("Giá và MA20 đang nằm trên MA50.")
        elif close < ma20 < ma50:
            position_score -= 1
            negative.append("Giá và MA20 đang nằm dưới MA50.")

    # Độ dốc MA
    ma20_slope = slopes.get("MA20")

    if ma20_slope is not None:
        if ma20_slope > 0:
            slope_score += 1
            positive.append("MA20 đang hướng lên.")
        elif ma20_slope < 0:
            slope_score -= 1
            negative.append("MA20 đang hướng xuống.")

    # Cấu trúc đỉnh đáy
    structure = structure_result["structure"]

    if structure == "ĐỈNH SAU CAO HƠN, ĐÁY SAU CAO HƠN":
        structure_score = 1
        positive.append("Cấu trúc đỉnh đáy cải thiện.")

    elif structure == "ĐỈNH SAU THẤP HƠN, ĐÁY SAU THẤP HƠN":
        structure_score = -1
        negative.append("Cấu trúc đỉnh đáy suy yếu.")

    # RSI và MACD
    rsi = momentum_result["rsi14"]
    macd_status = momentum_result["macd_status"]

    if rsi is not None and 50 < rsi < 70:
        positive.append("RSI xác nhận động lượng tích cực.")
        score += 1
    elif rsi is not None and rsi < 50:
        negative.append("RSI cho thấy động lượng chưa mạnh.")
        score -= 1

    if macd_status == "MACD TÍCH CỰC":
        positive.append("MACD nằm trên đường tín hiệu.")
        score += 1
    elif macd_status == "MACD TIÊU CỰC":
        negative.append("MACD nằm dưới đường tín hiệu.")
        score -= 1

    score += position_score + slope_score + structure_score

    # Giới hạn điểm để tránh một nhóm tín hiệu chi phối toàn bộ.
    score = max(-5, min(5, score))

    if trend == "TĂNG":
        trend_strength = "TĂNG"
    elif trend == "GIẢM":
        trend_strength = "GIẢM"
    elif trend == "CHƯA ĐỦ DỮ LIỆU":
        trend_strength = "CHƯA ĐỦ DỮ LIỆU"
    else:
        trend_strength = "TRUNG TÍNH / CHƯA RÕ"

    if ma20 is None:
        ma_status = "CHƯA ĐỦ DỮ LIỆU"
    elif close is not None and close > ma20:
        ma_status = "GIÁ TRÊN MA20"
    else:
        ma_status = "GIÁ DƯỚI MA20"

    if positive:
        signals.extend(positive)

    if negative:
        signals.extend(negative)

    required = ["close", "high", "low", "volume"]
    missing = [
        col for col in required
        if _get_column(df, col) is None
    ]

    if missing:
        data_quality = "THIẾU: " + ", ".join(missing)
        warnings.append("Dữ liệu thiếu cột: " + ", ".join(missing))
    else:
        data_quality = "ĐÃ KIỂM TRA CÁC CỘT OHLCV"

    return {
        "score": score,
        "signals": signals,
        "trend": trend,
        "momentum": momentum_result["momentum"],
        "structure": structure,
        "trend_strength": trend_strength,
        "ma_status": ma_status,
        "ma_slopes": slopes,
        "macd_status": macd_status,
        "warnings": warnings,
        "data_quality": data_quality,
        "positive_signals": positive,
        "negative_signals": negative,
        "momentum_alignment": momentum_result["momentum_alignment"],
        "structure_detail": structure_result["structure_detail"],
        "pivot_highs": structure_result["pivot_highs"],
        "pivot_lows": structure_result["pivot_lows"],
        "rsi14": momentum_result["rsi14"],
        "macd": momentum_result["macd"],
        "macd_signal": momentum_result["macd_signal"],
        "position_score": position_score,
        "slope_score": slope_score,
        "structure_score": structure_score
    }


# =========================================================
# 7. HÀM ĐƯỢC APP.PY GỌI
# =========================================================

def evaluate_technical(df):
    """Điểm vào chính tương thích với app.py."""
    return _evaluate_technical(df)
