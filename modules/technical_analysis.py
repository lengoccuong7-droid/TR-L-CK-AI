
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


def evaluate_technical(df):
    """
    Hàm chính để app.py gọi phân tích kỹ thuật.
    """
    return _evaluate_technical(df)
