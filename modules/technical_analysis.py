
import pandas as pd
import numpy as np


def _number(value):
    """Chuyển dữ liệu sang số, không tự thay dữ liệu thiếu bằng 0."""
    try:
        value = float(value)
        return value if np.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _is_valid(value):
    return value is not None and np.isfinite(value)


def evaluate_technical(df: pd.DataFrame) -> dict:
    """
    Phân tích xu hướng kỹ thuật STOCK AI ANALYST.

    Tương thích với hệ thống cũ:
        {
            "score": int,
            "signals": list
        }

    Bổ sung:
        trend, momentum, structure, ma_status,
        trend_strength, warnings, data_quality.
    """

    if df is None or not isinstance(df, pd.DataFrame):
        raise ValueError("Dữ liệu phân tích không hợp lệ.")

    if df.empty or len(df) < 2:
        raise ValueError("Cần tối thiểu 2 phiên dữ liệu để phân tích.")

    df = df.copy()

    if "close" not in df.columns:
        raise ValueError("Thiếu cột close.")

    close = pd.to_numeric(df["close"], errors="coerce")

    if close.iloc[-1] <= 0 or close.iloc[-2] <= 0:
        raise ValueError("Giá đóng cửa không hợp lệ.")

    last = df.iloc[-1]
    prev = df.iloc[-2]

    signals = []
    warnings = []
    score = 0

    last_close = _number(last.get("close"))
    prev_close = _number(prev.get("close"))

    # ==================================================
    # 1. ĐÁNH GIÁ VỊ TRÍ GIÁ SO VỚI CÁC ĐƯỜNG MA
    # ==================================================

    ma_status = {}

    for period in (20, 50, 100, 200):
        ma_col = f"MA{period}"
        ma_value = _number(last.get(ma_col))

        if not _is_valid(ma_value):
            ma_status[ma_col] = "CHƯA ĐỦ DỮ LIỆU"
            continue

        if last_close > ma_value:
            ma_status[ma_col] = "TRÊN MA"
            score += 1
            signals.append(
                f"Giá {last_close:,.2f} đang nằm trên {ma_col} "
                f"({ma_value:,.2f})."
            )
        elif last_close < ma_value:
            ma_status[ma_col] = "DƯỚI MA"
            score -= 1
            signals.append(
                f"Giá {last_close:,.2f} đang nằm dưới {ma_col} "
                f"({ma_value:,.2f})."
            )
        else:
            ma_status[ma_col] = "BẰNG MA"

    available_ma = [
        period for period in (20, 50, 100, 200)
        if _is_valid(_number(last.get(f"MA{period}")))
    ]

    if not available_ma:
        warnings.append(
            "Chưa có đường MA hợp lệ để đánh giá xu hướng trung và dài hạn."
        )

    # ==================================================
    # 2. ĐÁNH GIÁ ĐỘ DỐC MA
    # ==================================================

    ma_slopes = {}

    for period in (20, 50, 100, 200):
        col = f"MA{period}"

        if col not in df.columns or len(df) <= 5:
            ma_slopes[col] = "CHƯA ĐỦ DỮ LIỆU"
            continue

        current_ma = _number(last.get(col))
        old_ma = _number(df.iloc[-6].get(col))

        if not _is_valid(current_ma) or not _is_valid(old_ma):
            ma_slopes[col] = "CHƯA ĐỦ DỮ LIỆU"
            continue

        if current_ma > old_ma:
            ma_slopes[col] = "DỐC LÊN"
            if period in available_ma:
                score += 1
            signals.append(f"{col} đang có độ dốc đi lên.")
        elif current_ma < old_ma:
            ma_slopes[col] = "DỐC XUỐNG"
            if period in available_ma:
                score -= 1
            signals.append(f"{col} đang có độ dốc đi xuống.")
        else:
            ma_slopes[col] = "ĐI NGANG"

    # ==================================================
    # 3. PHÂN TÍCH CẤU TRÚC ĐỈNH VÀ ĐÁY
    # ==================================================

    structure = "CHƯA ĐỦ DỮ LIỆU"

    if len(df) >= 11 and {"high", "low"}.issubset(df.columns):

        high = pd.to_numeric(df["high"], errors="coerce")
        low = pd.to_numeric(df["low"], errors="coerce")

        recent_high = high.iloc[-5:].max()
        previous_high = high.iloc[-10:-5].max()

        recent_low = low.iloc[-5:].min()
        previous_low = low.iloc[-10:-5].min()

        if all(
            _is_valid(x)
            for x in [
                recent_high,
                previous_high,
                recent_low,
                previous_low
            ]
        ):

            higher_high = recent_high > previous_high
            higher_low = recent_low > previous_low

            lower_high = recent_high < previous_high
            lower_low = recent_low < previous_low

            if higher_high and higher_low:
                structure = "ĐỈNH SAU CAO HƠN, ĐÁY SAU CAO HƠN"
                score += 1
                signals.append(
                    "Cấu trúc giá đang hình thành đỉnh và đáy cao dần."
                )

            elif lower_high and lower_low:
                structure = "ĐỈNH SAU THẤP HƠN, ĐÁY SAU THẤP HƠN"
                score -= 1
                signals.append(
                    "Cấu trúc giá đang hình thành đỉnh và đáy thấp dần."
                )

            else:
                structure = "CẤU TRÚC CHƯA ĐỒNG THUẬN"
                signals.append(
                    "Cấu trúc đỉnh và đáy chưa xác nhận xu hướng rõ ràng."
                )

    # ==================================================
    # 4. MACD
    # ==================================================

    macd = _number(last.get("MACD"))
    macd_signal = _number(last.get("MACD_SIGNAL"))

    prev_macd = _number(prev.get("MACD"))
    prev_signal = _number(prev.get("MACD_SIGNAL"))

    macd_status = "CHƯA ĐỦ DỮ LIỆU"

    if _is_valid(macd) and _is_valid(macd_signal):

        if _is_valid(prev_macd) and _is_valid(prev_signal):

            if prev_macd <= prev_signal and macd > macd_signal:
                macd_status = "CẮT LÊN"
                score += 2
                signals.append(
                    "MACD vừa cắt lên đường tín hiệu, "
                    "động lượng tăng đang cải thiện."
                )

            elif prev_macd >= prev_signal and macd < macd_signal:
                macd_status = "CẮT XUỐNG"
                score -= 2
                signals.append(
                    "MACD vừa cắt xuống đường tín hiệu, "
                    "động lượng giảm đang gia tăng."
                )

            elif macd > macd_signal:
                macd_status = "TÍCH CỰC"
                score += 1
                signals.append(
                    "MACD nằm trên đường tín hiệu."
                )

            else:
                macd_status = "TIÊU CỰC"
                score -= 1
                signals.append(
                    "MACD nằm dưới đường tín hiệu."
                )

    # ==================================================
    # 5. RSI14
    # ==================================================

    rsi = _number(last.get("RSI14"))
    momentum = "CHƯA ĐỦ DỮ LIỆU"

    if _is_valid(rsi):

        if rsi >= 70:
            momentum = "MẠNH NHƯNG QUÁ MUA"
            score -= 1
            signals.append(
                f"RSI14 = {rsi:.2f}: vùng quá mua, "
                "cần cảnh giác áp lực chốt lời."
            )

        elif rsi >= 55:
            momentum = "TĂNG"
            score += 1
            signals.append(
                f"RSI14 = {rsi:.2f}: động lượng tăng tương đối tốt."
            )

        elif rsi >= 45:
            momentum = "TRUNG TÍNH"
            signals.append(
                f"RSI14 = {rsi:.2f}: động lượng chưa rõ ưu thế."
            )

        elif rsi >= 30:
            momentum = "YẾU"
            score -= 1
            signals.append(
                f"RSI14 = {rsi:.2f}: động lượng đang yếu."
            )

        else:
            momentum = "RẤT YẾU / QUÁ BÁN"
            score -= 1
            signals.append(
                f"RSI14 = {rsi:.2f}: vùng quá bán. "
                "Chưa đủ căn cứ xác nhận đảo chiều."
            )

    # ==================================================
    # 6. PHÂN LOẠI XU HƯỚNG
    # ==================================================

    ma20 = _number(last.get("MA20"))
    ma50 = _number(last.get("MA50"))
    ma200 = _number(last.get("MA200"))

    slope20 = ma_slopes.get("MA20")
    slope50 = ma_slopes.get("MA50")
    slope200 = ma_slopes.get("MA200")

    if (
        _is_valid(ma20)
        and _is_valid(ma50)
        and last_close > ma20 > ma50
        and slope20 == "DỐC LÊN"
        and slope50 == "DỐC LÊN"
    ):
        trend = "TĂNG"

    elif (
        _is_valid(ma20)
        and _is_valid(ma50)
        and last_close < ma20 < ma50
        and slope20 == "DỐC XUỐNG"
        and slope50 == "DỐC XUỐNG"
    ):
        trend = "GIẢM"

    elif (
        _is_valid(ma20)
        and last_close > ma20
        and slope20 == "DỐC LÊN"
        and macd_status == "CẮT LÊN"
    ):
        trend = "PHỤC HỒI KỸ THUẬT"

    elif (
        _is_valid(ma20)
        and last_close < ma20
        and slope20 == "DỐC XUỐNG"
    ):
        trend = "GIẢM / SUY YẾU"

    elif (
        structure == "ĐỈNH SAU CAO HƠN, ĐÁY SAU CAO HƠN"
        and _is_valid(ma20)
        and last_close > ma20
    ):
        trend = "ĐẢO CHIỀU TĂNG TIỀM NĂNG"

    elif (
        structure == "ĐỈNH SAU THẤP HƠN, ĐÁY SAU THẤP HƠN"
    ):
        trend = "GIẢM"

    else:
        trend = "TÍCH LŨY / CHƯA RÕ XU HƯỚNG"

    # ==================================================
    # 7. PHÁT HIỆN MÂU THUẪN
    # ==================================================

    if (
        _is_valid(ma20)
        and last_close > ma20
        and momentum in ("YẾU", "RẤT YẾU / QUÁ BÁN")
    ):
        warnings.append(
            "Giá nằm trên MA20 nhưng động lượng RSI còn yếu."
        )

    if (
        _is_valid(ma20)
        and last_close < ma20
        and momentum == "TĂNG"
    ):
        warnings.append(
            "RSI tích cực nhưng giá vẫn nằm dưới MA20."
        )

    if (
        macd_status == "CẮT LÊN"
        and trend in ("GIẢM", "GIẢM / SUY YẾU")
    ):
        warnings.append(
            "MACD có tín hiệu phục hồi nhưng xu hướng chính vẫn yếu."
        )

    if (
        macd_status == "CẮT XUỐNG"
        and trend == "TĂNG"
    ):
        warnings.append(
            "MACD suy yếu trong khi xu hướng chính vẫn đang tăng."
        )

    if not warnings:
        warnings.append(
            "Chưa phát hiện mâu thuẫn kỹ thuật nổi bật."
        )

    # ==================================================
    # 8. CHUẨN HÓA ĐIỂM VÀ KẾT QUẢ
    # ==================================================

    score = max(-5, min(5, score))

    if score >= 4:
        trend_strength = "MẠNH"
    elif score >= 2:
        trend_strength = "KHÁ"
    elif score >= -1:
        trend_strength = "TRUNG BÌNH"
    elif score >= -3:
        trend_strength = "YẾU"
    else:
        trend_strength = "RẤT YẾU"

    if not signals:
        signals.append(
            "Chưa có tín hiệu kỹ thuật đủ điều kiện đánh giá."
        )

    data_quality = {
        "total_sessions": len(df),
        "ma20_available": _is_valid(ma20),
        "ma50_available": _is_valid(ma50),
        "ma100_available": _is_valid(
            _number(last.get("MA100"))
        ),
        "ma200_available": _is_valid(ma200),
    }

    return {
        # Giữ tương thích với code cũ
        "score": int(score),
        "signals": signals,

        # Thông tin phân tích mới
        "trend": trend,
        "momentum": momentum,
        "structure": structure,
        "trend_strength": trend_strength,
        "ma_status": ma_status,
        "ma_slopes": ma_slopes,
        "macd_status": macd_status,
        "warnings": warnings,
        "data_quality": data_quality,
    }
