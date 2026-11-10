
import pandas as pd
import numpy as np

from modules.technical_analysis import evaluate_technical
from modules.support_resistance import find_support_resistance


def _number(value, default=None):
    try:
        x = float(value)
        return x if np.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def _price(value):
    if value is None or not np.isfinite(value) or value <= 0:
        return "CHƯA XÁC ĐỊNH"
    return f"{value:,.0f}"


def make_trading_decision(df: pd.DataFrame, ai_result: dict) -> dict:
    """
    Bộ máy quyết định giao dịch:
    - Không khuyến nghị mua sát kháng cự.
    - Không mua chỉ dựa vào điểm kỹ thuật.
    - Ưu tiên mua gần hỗ trợ khi có tỷ lệ lợi nhuận/rủi ro phù hợp.
    - Chỉ xác nhận mua khi có điều kiện xác nhận rõ ràng.
    - Không tự tạo dữ liệu chỉ báo còn thiếu.
    """

    result = {
        "decision": "CHƯA ĐỦ DỮ LIỆU",
        "reason": "Dữ liệu chưa đủ để đưa ra quyết định giao dịch đáng tin cậy.",
        "buy_zone": "CHƯA XÁC ĐỊNH",
        "confirm_price": "CHƯA XÁC ĐỊNH",
        "target_price": "CHƯA XÁC ĐỊNH",
        "stop_loss": "CHƯA XÁC ĐỊNH",
    }

    if df is None or not isinstance(df, pd.DataFrame) or len(df) < 3:
        return result

    required = ["close", "high", "low"]
    if any(col not in df.columns for col in required):
        return result

    data = df.copy()
    for col in required:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna(subset=required)
    if len(data) < 3:
        return result

    last = data.iloc[-1]
    prev = data.iloc[-2]

    close = _number(last["close"])
    previous_close = _number(prev["close"])

    if close is None or close <= 0:
        return result

    tech = evaluate_technical(data)
    sr = find_support_resistance(data)

    score = _number(tech.get("score"), 0)
    risk_level = (ai_result or {}).get("risk_level", "TRUNG BÌNH")
    risk_level = str(risk_level).upper()

    support = _number(sr.get("support"))
    resistance = _number(sr.get("resistance"))
    atr = _number(last.get("ATR14"))

    if atr is None or atr <= 0:
        atr = close * 0.02

    if support is None or support <= 0:
        return {
            **result,
            "reason": "Chưa xác định được vùng hỗ trợ đáng tin cậy. Không nên tự đặt vùng mua.",
        }

    if resistance is None or resistance <= 0:
        resistance = None

    dist_support = (close - support) / close * 100
    dist_resistance = (
        (resistance - close) / close * 100
        if resistance is not None else None
    )

    # Khoảng cách tối thiểu để tránh mua đuổi sát kháng cự.
    near_resistance = (
        dist_resistance is not None
        and 0 <= dist_resistance <= 2.0
    )

    # Giá xác nhận: vượt kháng cự hoặc vượt đỉnh gần nhất,
    # cộng biên an toàn nhỏ.
    recent_high = _number(data["high"].tail(20).max())
    breakout_reference = resistance

    if breakout_reference is None:
        breakout_reference = recent_high

    confirm_price = (
        max(breakout_reference, close) + 0.2 * atr
        if breakout_reference is not None else close + 0.5 * atr
    )

    # Xác định vùng mua quanh hỗ trợ, không lấy giá hiện tại
    # cộng ATR để tạo vùng mua quá rộng.
    zone_low = max(support, close - 0.8 * atr)
    zone_high = min(support + 0.5 * atr, close)

    if zone_low > zone_high:
        zone_low = None
        zone_high = None

    # Điểm dừng lỗ nằm dưới hỗ trợ và có khoảng đệm ATR.
    stop_loss = min(support - 0.5 * atr, close - 1.5 * atr)

    if stop_loss <= 0:
        stop_loss = None

    # Mục tiêu ưu tiên kháng cự phía trên.
    target_candidates = [close + 2.5 * atr]

    if resistance is not None and resistance > close:
        target_candidates.append(resistance)

    target_price = min(target_candidates)

    # Không cho mục tiêu nằm dưới giá hiện tại.
    if target_price <= close:
        target_price = close + 2.5 * atr

    # Tính tỷ lệ lợi nhuận/rủi ro tại vùng mua.
    rr_ratio = None

    if zone_high is not None and stop_loss is not None:
        risk = zone_high - stop_loss
        reward = target_price - zone_high

        if risk > 0 and reward > 0:
            rr_ratio = reward / risk

    # Kiểm tra khối lượng xác nhận nếu có dữ liệu.
    volume_confirmed = False

    if "volume" in data.columns and "VOL_MA20" in data.columns:
        vol = _number(last.get("volume"))
        vol_ma = _number(last.get("VOL_MA20"))

        if vol is not None and vol_ma is not None and vol_ma > 0:
            volume_confirmed = vol >= vol_ma * 1.2

    # Điều kiện giá đã vượt kháng cự.
    breakout_confirmed = (
        resistance is not None
        and close > resistance
        and previous_close is not None
        and previous_close <= resistance
        and volume_confirmed
    )

    # Quyết định giao dịch.
    if score <= -4 or risk_level == "CAO":
        decision = "TRÁNH MUA"
        reason = (
            "Tín hiệu kỹ thuật hoặc mức rủi ro chưa phù hợp. "
            "Ưu tiên bảo toàn vốn, chưa mở vị thế mua mới."
        )

    elif near_resistance and not breakout_confirmed:
        decision = "CHỜ MUA"
        reason = (
            "Giá đang ở sát vùng kháng cự. Không nên mua đuổi. "
            "Chờ giá điều chỉnh về hỗ trợ hoặc vượt kháng cự "
            "với thanh khoản xác nhận."
        )

    elif (
        breakout_confirmed
        and score >= 2
        and risk_level != "CAO"
    ):
        decision = "MUA"
        reason = (
            "Giá vượt kháng cự tham chiếu, thanh khoản cao hơn "
            "trung bình 20 phiên và điểm kỹ thuật ủng hộ. "
            "Cần tuân thủ mức cắt lỗ."
        )

    elif (
        zone_low is not None
        and zone_high is not None
        and dist_support <= 2.5
        and score >= 1
        and risk_level != "CAO"
        and rr_ratio is not None
        and rr_ratio >= 1.5
    ):
        decision = "CHỜ MUA"
        reason = (
            "Giá đang ở gần vùng hỗ trợ có thể theo dõi. "
            "Chỉ cân nhắc mua khi xuất hiện tín hiệu hồi phục "
            "và tỷ lệ lợi nhuận/rủi ro đạt yêu cầu."
        )

    elif score >= 2:
        decision = "CHỜ MUA"
        reason = (
            "Điểm kỹ thuật tích cực nhưng vị trí giá chưa tạo "
            "được điểm mua có lợi thế. Chờ điều chỉnh hoặc xác nhận "
            "vượt kháng cự, không mua đuổi."
        )

    elif score >= -1:
        decision = "GIỮ"
        reason = (
            "Tín hiệu chưa đủ mạnh để mở vị thế mới. "
            "Nếu đang nắm giữ, tiếp tục theo dõi hỗ trợ và xu hướng."
        )

    elif score >= -3:
        decision = "CHỜ BÁN"
        reason = (
            "Động lượng suy yếu. Hạn chế mua mới và theo dõi "
            "khả năng hồi phục trước khi quyết định giảm tỷ trọng."
        )

    else:
        decision = "TRÁNH MUA"
        reason = (
            "Tín hiệu kỹ thuật tiêu cực. Ưu tiên đứng ngoài "
            "cho đến khi xu hướng được cải thiện."
        )

    # Không đưa vùng mua giả tạo khi chưa xác định được vùng hợp lý.
    if zone_low is None or zone_high is None or zone_low >= zone_high:
        buy_zone = "CHƯA CÓ VÙNG MUA AN TOÀN"
    else:
        buy_zone = f"{zone_low:,.0f} - {zone_high:,.0f}"

    # Nếu sát kháng cự, không hiển thị vùng mua như một khuyến nghị mua ngay.
    if near_resistance and not breakout_confirmed:
        buy_zone = "CHỜ ĐIỀU CHỈNH / XÁC NHẬN VƯỢT KHÁNG CỰ"

    return {
        "decision": decision,
        "reason": reason,
        "buy_zone": buy_zone,
        "confirm_price": _price(confirm_price),
        "target_price": _price(target_price),
        "stop_loss": _price(stop_loss),

        # Thông tin bổ sung để phục vụ nâng cấp phân tích sau này.
        "support": support,
        "resistance": resistance,
        "distance_to_support_pct": round(dist_support, 2),
        "distance_to_resistance_pct": (
            round(dist_resistance, 2)
            if dist_resistance is not None else None
        ),
        "risk_reward_ratio": (
            round(rr_ratio, 2) if rr_ratio is not None else None
        ),
        "volume_confirmed": volume_confirmed,
        "breakout_confirmed": breakout_confirmed,
    }
