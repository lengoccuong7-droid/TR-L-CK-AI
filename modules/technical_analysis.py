
import pandas as pd
import numpy as np


def _number(value):
    """Chuyển dữ liệu sang số; dữ liệu thiếu giữ nguyên là None."""
    try:
        value = float(value)
        return value if np.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _valid(value):
    return value is not None and np.isfinite(value)


def _confirmed_pivots(series, left=3, right=3, max_bars=80):
    """
    Tìm điểm xoay chiều đã được xác nhận.
    Một pivot chỉ được xác nhận khi đã có đủ số phiên bên phải.
    """
    values = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
    start = max(0, len(values) - max_bars)

    highs = []
    lows = []

    for i in range(start + left, len(values) - right):
        window = values[i-left:i+right+1]
        current = values[i]

        if not np.isfinite(current) or not np.isfinite(window).all():
            continue

        if current == np.max(window) and np.sum(window == current) == 1:
            highs.append((i, float(current)))

        if current == np.min(window) and np.sum(window == current) == 1:
            lows.append((i, float(current)))

    return highs, lows


def _evaluate_structure(df):
    """Đánh giá cấu trúc bằng hai đỉnh và hai đáy đã xác nhận."""
    result = {
        "structure": "CHƯA ĐỦ DỮ LIỆU",
        "pivot_highs": [],
        "pivot_lows": [],
        "structure_detail": "Chưa có đủ điểm xoay chiều đã xác nhận."
    }

    if not {"high", "low"}.issubset(df.columns):
        return result

   highs, _ = _confirmed_pivots(df["high"])
_, lows = _confirmed_pivots(df["low"])

    result["pivot_highs"] = [round(x[1], 4) for x in highs[-2:]]
    result["pivot_lows"] = [round(x[1], 4) for x in lows[-2:]]

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
        detail = "Đỉnh cao hơn nhưng đáy thấp hơn, xu hướng chưa đồng thuận."
    elif lower_high and higher_low:
        structure = "BIẾN ĐỘNG THU HẸP"
        detail = "Đỉnh thấp hơn nhưng đáy cao hơn, giá đang thu hẹp biên độ."
    else:
        structure = "CẤU TRÚC CHƯA ĐỒNG THUẬN"
        detail = "Cấu trúc đỉnh đáy chưa xác nhận hướng rõ ràng."

    result.update({
        "structure": structure,
        "structure_detail": detail
    })
    return result


def evaluate_technical(df: pd.DataFrame) -> dict:
    """
    Phân tích kỹ thuật:
    - Không đếm trùng tín hiệu MA.
    - Kết hợp xu hướng, cấu trúc, RSI và MACD.
    - Không tự tạo dữ liệu thiếu.
    - Giữ các khóa kết quả tương thích với app.py.
    """

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("Dữ liệu phân tích không hợp lệ.")

    if "close" not in df.columns or len(df) < 2:
        raise ValueError("Cần tối thiểu 2 phiên và có cột close.")

    df = df.copy()

    for col in ["close", "high", "low", "volume",
                "MA20", "MA50", "MA100", "MA200",
                "RSI14", "MACD", "MACD_SIGNAL"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    last = df.iloc[-1]
    prev = df.iloc[-2]

    close = _number(last.get("close"))
    prev_close = _number(prev.get("close"))

    if not _valid(close) or close <= 0:
        raise ValueError("Giá đóng cửa không hợp lệ.")

    signals = []
    warnings = []
    positive_signals = []
    negative_signals = []

    # ==================================================
    # 1. VỊ TRÍ GIÁ SO VỚI MA
    # ==================================================

    ma_status = {}
    available_ma = []

    for period in (20, 50, 100, 200):
        col = f"MA{period}"
        ma = _number(last.get(col))

        if not _valid(ma):
            ma_status[col] = "CHƯA ĐỦ DỮ LIỆU"
            continue

        available_ma.append(period)

        if close > ma:
            ma_status[col] = "TRÊN MA"
        elif close < ma:
            ma_status[col] = "DƯỚI MA"
        else:
            ma_status[col] = "BẰNG MA"

    # Điểm vị trí MA chỉ được tính một lần.
    position_votes = [
        1 if close > _number(last.get(f"MA{p}"))
        else -1 if close < _number(last.get(f"MA{p}"))
        else 0
        for p in available_ma
    ]

    position_score = 0
    if position_votes:
        avg_position = sum(position_votes) / len(position_votes)
        if avg_position >= 0.5:
            position_score = 1
            positive_signals.append("Giá nằm trên phần lớn các đường MA có dữ liệu.")
        elif avg_position <= -0.5:
            position_score = -1
            negative_signals.append("Giá nằm dưới phần lớn các đường MA có dữ liệu.")

    # ==================================================
    # 2. ĐỘ DỐC MA
    # ==================================================

    ma_slopes = {}
    slope_votes = []

    for period in (20, 50, 100, 200):
        col = f"MA{period}"

        if col not in df.columns or len(df) < 6:
            ma_slopes[col] = "CHƯA ĐỦ DỮ LIỆU"
            continue

        current = _number(last.get(col))
        old = _number(df.iloc[-6].get(col))

        if not _valid(current) or not _valid(old):
            ma_slopes[col] = "CHƯA ĐỦ DỮ LIỆU"
            continue

        if current > old:
            ma_slopes[col] = "DỐC LÊN"
            slope_votes.append(1)
        elif current < old:
            ma_slopes[col] = "DỐC XUỐNG"
            slope_votes.append(-1)
        else:
            ma_slopes[col] = "ĐI NGANG"
            slope_votes.append(0)

    slope_score = 0
    if slope_votes:
        avg_slope = sum(slope_votes) / len(slope_votes)
        if avg_slope >= 0.5:
            slope_score = 1
            positive_signals.append("Độ dốc các MA đang nghiêng về hướng tăng.")
        elif avg_slope <= -0.5:
            slope_score = -1
            negative_signals.append("Độ dốc các MA đang nghiêng về hướng giảm.")

    # ==================================================
    # 3. CẤU TRÚC ĐỈNH ĐÁY
    # ==================================================

    structure_data = _evaluate_structure(df)
    structure = structure_data["structure"]

    structure_score = 0

    if structure == "ĐỈNH SAU CAO HƠN, ĐÁY SAU CAO HƠN":
        structure_score = 1
        positive_signals.append(structure_data["structure_detail"])

    elif structure == "ĐỈNH SAU THẤP HƠN, ĐÁY SAU THẤP HƠN":
        structure_score = -1
        negative_signals.append(structure_data["structure_detail"])

    elif structure not in ("CHƯA ĐỦ DỮ LIỆU",):
        warnings.append(structure_data["structure_detail"])

    # ==================================================
    # 4. MACD
    # ==================================================

    macd = _number(last.get("MACD"))
    macd_signal = _number(last.get("MACD_SIGNAL"))
    prev_macd = _number(prev.get("MACD"))
    prev_signal = _number(prev.get("MACD_SIGNAL"))

    macd_status = "CHƯA ĐỦ DỮ LIỆU"
    macd_direction = None
    macd_score = 0

    if _valid(macd) and _valid(macd_signal):
        if _valid(prev_macd) and _valid(prev_signal):
            if prev_macd <= prev_signal and macd > macd_signal:
                macd_status = "CẮT LÊN"
                macd_direction = 1
                macd_score = 1
                positive_signals.append("MACD vừa cắt lên đường tín hiệu.")

            elif prev_macd >= prev_signal and macd < macd_signal:
                macd_status = "CẮT XUỐNG"
                macd_direction = -1
                macd_score = -1
                negative_signals.append("MACD vừa cắt xuống đường tín hiệu.")

            elif macd > macd_signal:
                macd_status = "TÍCH CỰC"
                macd_direction = 1
                macd_score = 1
                positive_signals.append("MACD nằm trên đường tín hiệu.")

            else:
                macd_status = "TIÊU CỰC"
                macd_direction = -1
                macd_score = -1
                negative_signals.append("MACD nằm dưới đường tín hiệu.")

    # ==================================================
    # 5. RSI14
    # ==================================================

    rsi = _number(last.get("RSI14"))
    momentum = "CHƯA ĐỦ DỮ LIỆU"
    rsi_direction = None
    rsi_score = 0

    if _valid(rsi):
        if not 0 <= rsi <= 100:
            rsi = None
        elif rsi >= 70:
            momentum = "MẠNH NHƯNG QUÁ MUA"
            rsi_direction = 1
            rsi_score = 0
            warnings.append("RSI ở vùng quá mua, cần cảnh giác áp lực chốt lời.")
        elif rsi >= 55:
            momentum = "TĂNG"
            rsi_direction = 1
            rsi_score = 1
            positive_signals.append(f"RSI14 = {rsi:.2f}, động lượng nghiêng về tăng.")
        elif rsi >= 45:
            momentum = "TRUNG TÍNH"
            rsi_direction = 0
        elif rsi >= 30:
            momentum = "YẾU"
            rsi_direction = -1
            rsi_score = -1
            negative_signals.append(f"RSI14 = {rsi:.2f}, động lượng đang yếu.")
        else:
            momentum = "RẤT YẾU / QUÁ BÁN"
            rsi_direction = -1
            rsi_score = -1
            negative_signals.append(
                f"RSI14 = {rsi:.2f}, đang quá bán nhưng chưa xác nhận đảo chiều."
            )

    # ==================================================
    # 6. ĐÁNH GIÁ SỰ ĐỒNG THUẬN RSI VÀ MACD
    # ==================================================

    if rsi_direction is None or macd_direction is None:
        momentum_alignment = "CHƯA ĐỦ DỮ LIỆU"
    elif rsi_direction == macd_direction == 1:
        momentum_alignment = "RSI VÀ MACD ĐỒNG THUẬN TÍCH CỰC"
    elif rsi_direction == macd_direction == -1:
        momentum_alignment = "RSI VÀ MACD ĐỒNG THUẬN TIÊU CỰC"
    elif rsi_direction == 0 or macd_direction == 0:
        momentum_alignment = "ĐỘNG LƯỢNG CHƯA ĐỒNG THUẬN RÕ"
    else:
        momentum_alignment = "RSI VÀ MACD MÂU THUẪN"

    if momentum_alignment == "RSI VÀ MACD MÂU THUẪN":
        warnings.append(
            "RSI và MACD phát tín hiệu trái chiều; chưa nên kết luận động lượng."
        )

    # ==================================================
    # 7. PHÂN LOẠI XU HƯỚNG
    # ==================================================

    ma20 = _number(last.get("MA20"))
    ma50 = _number(last.get("MA50"))

    slope20 = ma_slopes.get("MA20")
    slope50 = ma_slopes.get("MA50")

    structure_up = structure == "ĐỈNH SAU CAO HƠN, ĐÁY SAU CAO HƠN"
    structure_down = structure == "ĐỈNH SAU THẤP HƠN, ĐÁY SAU THẤP HƠN"

    if (
        _valid(ma20) and _valid(ma50)
        and close > ma20 > ma50
        and slope20 == "DỐC LÊN"
        and slope50 == "DỐC LÊN"
        and not structure_down
    ):
        trend = "TĂNG"

    elif (
        _valid(ma20) and _valid(ma50)
        and close < ma20 < ma50
        and slope20 == "DỐC XUỐNG"
        and slope50 == "DỐC XUỐNG"
        and not structure_up
    ):
        trend = "GIẢM"

    elif (
        _valid(ma20) and close < ma20
        and slope20 == "DỐC XUỐNG"
    ):
        trend = "GIẢM / SUY YẾU"

    elif (
        _valid(ma20) and close > ma20
        and slope20 == "DỐC LÊN"
        and macd_status == "CẮT LÊN"
        and momentum_alignment == "RSI VÀ MACD ĐỒNG THUẬN TÍCH CỰC"
        and not structure_down
    ):
        trend = "PHỤC HỒI KỸ THUẬT"

    elif structure_up and _valid(ma20) and close > ma20:
        trend = "ĐẢO CHIỀU TĂNG TIỀM NĂNG"

    elif structure_down:
        trend = "GIẢM"

    else:
        trend = "TÍCH LŨY / CHƯA RÕ XU HƯỚNG"

    # ==================================================
    # 8. PHÁT HIỆN MÂU THUẪN XU HƯỚNG
    # ==================================================

    if _valid(ma20) and close > ma20 and momentum in (
        "YẾU", "RẤT YẾU / QUÁ BÁN"
    ):
        warnings.append("Giá trên MA20 nhưng RSI cho thấy động lượng yếu.")

    if _valid(ma20) and close < ma20 and momentum == "TĂNG":
        warnings.append("RSI tích cực nhưng giá vẫn nằm dưới MA20.")

    if macd_status == "CẮT LÊN" and trend in (
        "GIẢM", "GIẢM / SUY YẾU"
    ):
        warnings.append("MACD cắt lên nhưng xu hướng chính vẫn đang yếu.")

    if macd_status == "CẮT XUỐNG" and trend == "TĂNG":
        warnings.append("MACD cắt xuống trong khi xu hướng chính vẫn tăng.")

    if structure_up and trend in ("GIẢM", "GIẢM / SUY YẾU"):
        warnings.append("Cấu trúc đỉnh đáy cải thiện nhưng xu hướng MA vẫn yếu.")

    if structure_down and trend == "TĂNG":
        warnings.append("Cấu trúc đỉnh đáy xấu đi dù các MA vẫn cho xu hướng tăng.")

    # ==================================================
    # 9. ĐIỂM TỔNG HỢP KHÔNG ĐẾM TRÙNG MA
    # ==================================================

    score = (
        position_score
        + slope_score
        + structure_score
        + macd_score
        + rsi_score
    )
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

    if not positive_signals:
        positive_signals.append("Chưa có tín hiệu tích cực đủ rõ.")

    if not negative_signals:
        negative_signals.append("Chưa ghi nhận tín hiệu tiêu cực đủ rõ.")

    if not warnings:
        warnings.append("Chưa phát hiện mâu thuẫn kỹ thuật nổi bật.")

    signals.extend(positive_signals)
    signals.extend(negative_signals)

    # ==================================================
    # 10. CHẤT LƯỢNG DỮ LIỆU VÀ KẾT QUẢ
    # ==================================================

    data_quality = {
        "total_sessions": len(df),
        "ma20_available": _valid(ma20),
        "ma50_available": _valid(ma50),
        "ma100_available": _valid(_number(last.get("MA100"))),
        "ma200_available": _valid(_number(last.get("MA200"))),
        "rsi14_available": _valid(rsi),
        "macd_available": _valid(macd),
        "macd_signal_available": _valid(macd_signal),
        "structure_available": structure != "CHƯA ĐỦ DỮ LIỆU",
    }

    return {
        # Các khóa cũ: giữ nguyên tên
        "score": int(score),
        "signals": signals,
        "trend": trend,
        "momentum": momentum,
        "structure": structure,
        "trend_strength": trend_strength,
        "ma_status": ma_status,
        "ma_slopes": ma_slopes,
        "macd_status": macd_status,
        "warnings": warnings,
        "data_quality": data_quality,

        # Thông tin bổ sung, không bắt buộc app.py phải sử dụng
        "positive_signals": positive_signals,
        "negative_signals": negative_signals,
        "momentum_alignment": momentum_alignment,
        "structure_detail": structure_data["structure_detail"],
        "pivot_highs": structure_data["pivot_highs"],
        "pivot_lows": structure_data["pivot_lows"],
        "rsi14": rsi,
        "macd": macd,
        "macd_signal": macd_signal,
        "position_score": position_score,
        "slope_score": slope_score,
        "structure_score": structure_score,
    }
