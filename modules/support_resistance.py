
import numpy as np
import pandas as pd


def _valid_number(value):
    try:
        number = float(value)
        return number if np.isfinite(number) and number > 0 else None
    except (TypeError, ValueError):
        return None


def _cluster_levels(levels, tolerance):
    """Gộp các mức giá gần nhau thành vùng hỗ trợ/kháng cự."""
    if not levels:
        return []

    levels = sorted(levels, key=lambda x: x["price"])
    clusters = [[levels[0]]]

    for item in levels[1:]:
        center = np.mean([x["price"] for x in clusters[-1]])

        if abs(item["price"] - center) <= tolerance:
            clusters[-1].append(item)
        else:
            clusters.append([item])

    results = []

    for group in clusters:
        weights = [max(x["weight"], 1) for x in group]
        prices = [x["price"] for x in group]

        results.append({
            "price": float(np.average(prices, weights=weights)),
            "touches": sum(1 for x in group if x["source"] == "PIVOT"),
            "ma_count": sum(1 for x in group if x["source"] == "MA"),
            "strength": float(sum(weights)),
            "low": float(min(prices)),
            "high": float(max(prices)),
        })

    return results


def find_support_resistance(
    df: pd.DataFrame,
    window: int = 60
) -> dict:
    """
    Xác định hỗ trợ và kháng cự từ:
    - Đáy và đỉnh đảo chiều cục bộ.
    - MA20 và MA50 khi có dữ liệu hợp lệ.
    - Các vùng giá gần nhau.

    Không tự tạo ATR.
    Không tự lấy đỉnh/đáy lịch sử làm vùng hỗ trợ/kháng cự
    đã xác nhận nếu không có ứng viên phù hợp.
    """

    empty_result = {
        "support": None,
        "resistance": None,
        "dist_to_support_pct": None,
        "dist_to_resistance_pct": None,
        "support_zone_low": None,
        "support_zone_high": None,
        "resistance_zone_low": None,
        "resistance_zone_high": None,
        "support_touches": 0,
        "resistance_touches": 0,
        "support_strength": "CHƯA ĐỦ DỮ LIỆU",
        "resistance_strength": "CHƯA ĐỦ DỮ LIỆU",
        "resistance_position": "CHƯA XÁC ĐỊNH",
        "atr14": None,
        "notes": [],
    }

    if not isinstance(df, pd.DataFrame) or df.empty:
        return empty_result

    required = ["high", "low", "close"]

    if any(col not in df.columns for col in required):
        return empty_result

    data = df.copy()

    for col in required + ["ATR14", "MA20", "MA50"]:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna(subset=required)

    data = data[
        (data["high"] > 0)
        & (data["low"] > 0)
        & (data["close"] > 0)
        & (data["high"] >= data["low"])
    ]

    if data.empty:
        return empty_result

    try:
        window = max(int(window), 20)
    except (TypeError, ValueError):
        window = 60

    recent = data.tail(window).reset_index(drop=True)
    last_close = _valid_number(recent["close"].iloc[-1])

    if last_close is None:
        return empty_result

    notes = []

    # Chỉ lấy ATR14 thực tế có trong dữ liệu.
    atr = None

    if "ATR14" in recent.columns:
        atr = _valid_number(recent["ATR14"].iloc[-1])

    if atr is None:
        notes.append(
            "Không có ATR14 hợp lệ. Không sử dụng ATR giả "
            "để tính độ rộng vùng giá hoặc quản trị rủi ro."
        )

    # Nếu thiếu ATR, chỉ dùng ngưỡng gom cụm theo giá.
    # Đây không phải giá trị ATR và không dùng để tính cắt lỗ.
    tolerance = (
        max(atr * 0.45, last_close * 0.004)
        if atr is not None
        else last_close * 0.004
    )

    support_candidates = []
    resistance_candidates = []

    # 1. Tìm đáy và đỉnh đảo chiều cục bộ.
    if len(recent) >= 5:
        for i in range(2, len(recent) - 2):
            low_value = float(recent.loc[i, "low"])
            high_value = float(recent.loc[i, "high"])

            nearby_lows = recent.loc[i - 2:i + 2, "low"]
            nearby_highs = recent.loc[i - 2:i + 2, "high"]

            if low_value == nearby_lows.min():
                support_candidates.append({
                    "price": low_value,
                    "weight": 2,
                    "source": "PIVOT",
                })

            if high_value == nearby_highs.max():
                resistance_candidates.append({
                    "price": high_value,
                    "weight": 2,
                    "source": "PIVOT",
                })

    # 2. Bổ sung MA20 và MA50.
    # MA chỉ là mức tham chiếu, không được tính là một lần kiểm tra giá.
    for ma_name in ("MA20", "MA50"):
        if ma_name not in recent.columns:
            continue

        ma_value = _valid_number(recent[ma_name].iloc[-1])

        if ma_value is None:
            continue

        item = {
            "price": ma_value,
            "weight": 1,
            "source": "MA",
        }

        if ma_value < last_close:
            support_candidates.append(item.copy())

        elif ma_value > last_close:
            resistance_candidates.append(item.copy())

    # 3. Gom cụm.
    support_clusters = _cluster_levels(
        support_candidates, tolerance
    )

    resistance_clusters = _cluster_levels(
        resistance_candidates, tolerance
    )

    supports_below = [
        x for x in support_clusters
        if x["price"] < last_close
    ]

    resistances_above = [
        x for x in resistance_clusters
        if x["price"] > last_close
    ]

    # 4. Chọn vùng gần giá hiện tại nhất.
    support_info = (
        max(supports_below, key=lambda x: x["price"])
        if supports_below else None
    )

    resistance_info = (
        min(resistances_above, key=lambda x: x["price"])
        if resistances_above else None
    )

    if support_info is None:
        notes.append(
            "Chưa tìm được vùng hỗ trợ phía dưới giá hiện tại "
            "từ đáy đảo chiều hoặc MA hợp lệ."
        )

    if resistance_info is None:
        notes.append(
            "Chưa tìm được kháng cự phía trên giá hiện tại. "
            "Không lấy đỉnh cũ nằm dưới giá hiện tại làm kháng cự."
        )

    # 5. Khoảng cách và thông tin vùng.
    support = (
        float(support_info["price"])
        if support_info is not None else None
    )

    resistance = (
        float(resistance_info["price"])
        if resistance_info is not None else None
    )

    dist_support = (
        (last_close - support) / last_close * 100
        if support is not None else None
    )

    dist_resistance = (
        (resistance - last_close) / last_close * 100
        if resistance is not None else None
    )

    # 6. Đánh giá độ tin cậy.
    def strength_label(info):
        if info is None:
            return "CHƯA XÁC ĐỊNH"

        touches = info["touches"]

        if touches >= 4:
            return "MẠNH"

        if touches >= 2:
            return "TRUNG BÌNH"

        if touches == 1:
            return "YẾU / CẦN XÁC NHẬN"

        if info["ma_count"] > 0:
            return "MỨC THAM CHIẾU MA"

        return "CHƯA ĐỦ XÁC NHẬN"

    if resistance is None:
        resistance_position = "CHƯA XÁC ĐỊNH KHÁNG CỰ PHÍA TRÊN"

    elif dist_resistance <= 2:
        resistance_position = "SÁT KHÁNG CỰ"

    else:
        resistance_position = "CÒN KHOẢNG CÁCH ĐẾN KHÁNG CỰ"

    if len(data) < 20:
        notes.append(
            "Dữ liệu dưới 20 phiên; độ tin cậy của các vùng giá hạn chế."
        )

    # 7. Kết quả.
    return {
        # Giữ nguyên các khóa cũ.
        "support": round(support, 2) if support is not None else None,
        "resistance": (
            round(resistance, 2)
            if resistance is not None else None
        ),
        "dist_to_support_pct": (
            round(dist_support, 2)
            if dist_support is not None else None
        ),
        "dist_to_resistance_pct": (
            round(dist_resistance, 2)
            if dist_resistance is not None else None
        ),

        # Vùng giá.
        "support_zone_low": (
            round(support_info["low"], 2)
            if support_info is not None else None
        ),
        "support_zone_high": (
            round(support_info["high"], 2)
            if support_info is not None else None
        ),
        "resistance_zone_low": (
            round(resistance_info["low"], 2)
            if resistance_info is not None else None
        ),
        "resistance_zone_high": (
            round(resistance_info["high"], 2)
            if resistance_info is not None else None
        ),

        # Độ tin cậy.
        "support_touches": (
            support_info["touches"] if support_info else 0
        ),
        "resistance_touches": (
            resistance_info["touches"] if resistance_info else 0
        ),
        "support_strength": strength_label(support_info),
        "resistance_strength": strength_label(resistance_info),

        "resistance_position": resistance_position,
        "atr14": round(atr, 2) if atr is not None else None,
        "notes": notes,
    }
