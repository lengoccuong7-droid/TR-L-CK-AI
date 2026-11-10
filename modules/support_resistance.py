
import numpy as np
import pandas as pd


def _valid_number(value):
    try:
        number = float(value)
        return number if np.isfinite(number) and number > 0 else None
    except (TypeError, ValueError):
        return None


def _cluster_levels(levels, tolerance):
    """Gộp các mức giá nằm gần nhau thành một vùng."""
    if not levels:
        return []

    levels = sorted(levels, key=lambda item: item["price"])
    clusters = [[levels[0]]]

    for item in levels[1:]:
        current_center = np.mean(
            [x["price"] for x in clusters[-1]]
        )
        if abs(item["price"] - current_center) <= tolerance:
            clusters[-1].append(item)
        else:
            clusters.append([item])

    results = []
    for group in clusters:
        weights = [max(x["weight"], 1) for x in group]
        prices = [x["price"] for x in group]

        center = np.average(prices, weights=weights)

        results.append({
            "price": float(center),
            "touches": len(group),
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
    Xác định hỗ trợ/kháng cự dựa trên:
    - Đỉnh và đáy đảo chiều cục bộ.
    - Các vùng giá được kiểm tra nhiều lần.
    - MA20 và MA50 khi có đủ dữ liệu.
    - ATR để xác định khoảng cách và độ rộng vùng.

    Không khẳng định một mức giá là hỗ trợ/kháng cự mạnh
    chỉ vì đó là giá cao nhất hoặc thấp nhất trong dữ liệu.
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

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return empty_result

    required = ["high", "low", "close"]
    if any(col not in df.columns for col in required):
        return empty_result

    data = df.copy()
    for col in required:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna(subset=required)
    data = data[
        (data["high"] > 0) &
        (data["low"] > 0) &
        (data["close"] > 0) &
        (data["high"] >= data["low"])
    ]

    if data.empty:
        return empty_result

    recent = data.tail(max(int(window), 20)).reset_index(drop=True)
    last_close = _valid_number(recent["close"].iloc[-1])

    if last_close is None:
        return empty_result

    notes = []

    # ATR chỉ sử dụng khi có dữ liệu thực tế.
    atr = None
    if "ATR14" in recent.columns:
        atr = _valid_number(recent["ATR14"].iloc[-1])

    if atr is None and len(recent) >= 15:
        previous_close = recent["close"].shift(1)
        true_range = pd.concat(
            [
                recent["high"] - recent["low"],
                (recent["high"] - previous_close).abs(),
                (recent["low"] - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        atr_value = true_range.tail(14).mean()
        atr = _valid_number(atr_value)

    if atr is None:
        atr = last_close * 0.02
        notes.append("ATR chưa đủ dữ liệu; dùng biên độ dự phòng 2% để phân vùng.")

    tolerance = max(atr * 0.45, last_close * 0.004)

    support_candidates = []
    resistance_candidates = []

    # 1. Tìm các đáy và đỉnh đảo chiều cục bộ.
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
                })

            if high_value == nearby_highs.max():
                resistance_candidates.append({
                    "price": high_value,
                    "weight": 2,
                })

    # 2. Bổ sung các đường MA có dữ liệu hợp lệ.
    for ma_name in ("MA20", "MA50"):
        if ma_name in recent.columns:
            ma_value = _valid_number(recent[ma_name].iloc[-1])

            if ma_value is not None:
                item = {"price": ma_value, "weight": 1}

                if ma_value <= last_close:
                    support_candidates.append(item.copy())

                if ma_value >= last_close:
                    resistance_candidates.append(item.copy())

    # 3. Gộp các mức giá gần nhau thành vùng.
    support_clusters = _cluster_levels(
        support_candidates, tolerance
    )
    resistance_clusters = _cluster_levels(
        resistance_candidates, tolerance
    )

    supports_below = [
        x for x in support_clusters
        if x["price"] <= last_close
    ]
    resistances_above = [
        x for x in resistance_clusters
        if x["price"] >= last_close
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

    # 5. Nếu không tìm được vùng phù hợp, dùng cực trị lịch sử
    # nhưng ghi rõ đây là mức tham chiếu, không phải vùng mạnh.
    if support_info is None:
        support_price = float(recent["low"].min())
        support_info = {
            "price": support_price,
            "touches": 1,
            "strength": 1,
            "low": support_price,
            "high": support_price,
        }
        notes.append("Hỗ trợ dùng đáy thấp nhất trong dữ liệu làm mức tham chiếu.")

    if resistance_info is None:
        resistance_price = float(recent["high"].max())
        resistance_info = {
            "price": resistance_price,
            "touches": 1,
            "strength": 1,
            "low": resistance_price,
            "high": resistance_price,
        }

        if resistance_price < last_close:
            notes.append("Giá đang cao hơn các đỉnh tham chiếu trong dữ liệu.")
        else:
            notes.append("Kháng cự dùng đỉnh cao nhất trong dữ liệu làm mức tham chiếu.")

    support = float(support_info["price"])
    resistance = float(resistance_info["price"])

    dist_support = (
        (last_close - support) / support * 100
        if support > 0 else None
    )

    dist_resistance = (
        (resistance - last_close) / last_close * 100
        if last_close > 0 else None
    )

    # 6. Đánh giá độ tin cậy theo số lần kiểm tra vùng.
    def strength_label(info):
        touches = info["touches"]

        if touches >= 4:
            return "MẠNH"
        if touches >= 2:
            return "TRUNG BÌNH"
        return "YẾU / CHƯA ĐỦ XÁC NHẬN"

    if resistance < last_close:
        resistance_position = "GIÁ ĐÃ VƯỢT MỨC KHÁNG CỰ THAM CHIẾU"
    elif dist_resistance is not None and dist_resistance <= 2:
        resistance_position = "SÁT KHÁNG CỰ"
    else:
        resistance_position = "CÒN KHOẢNG CÁCH ĐẾN KHÁNG CỰ"

    if len(data) < 20:
        notes.append("Dữ liệu dưới 20 phiên; các vùng giá có độ tin cậy hạn chế.")

    return {
        # Giữ nguyên 4 khóa cũ để tương thích module khác.
        "support": round(support, 2),
        "resistance": round(resistance, 2),
        "dist_to_support_pct": (
            round(dist_support, 2)
            if dist_support is not None else None
        ),
        "dist_to_resistance_pct": (
            round(dist_resistance, 2)
            if dist_resistance is not None else None
        ),

        # Thông tin vùng giá chi tiết.
        "support_zone_low": round(support_info["low"], 2),
        "support_zone_high": round(support_info["high"], 2),
        "resistance_zone_low": round(resistance_info["low"], 2),
        "resistance_zone_high": round(resistance_info["high"], 2),

        # Độ tin cậy.
        "support_touches": support_info["touches"],
        "resistance_touches": resistance_info["touches"],
        "support_strength": strength_label(support_info),
        "resistance_strength": strength_label(resistance_info),

        "resistance_position": resistance_position,
        "atr14": round(atr, 2),
        "notes": notes,
    }
