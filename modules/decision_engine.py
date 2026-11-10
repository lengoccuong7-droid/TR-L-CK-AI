
import pandas as pd
import numpy as np

from modules.technical_analysis import evaluate_technical
from modules.support_resistance import find_support_resistance
import modules.money_flow as money_flow_module


def _number(value, default=None):
    try:
        x = float(value)
        return x if np.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def _price(value):
    value = _number(value)
    if value is None or value <= 0:
        return "CHƯA XÁC ĐỊNH"
    return f"{value:,.0f}"


def _text(value):
    return str(value or "").strip().upper()


def _get_money_flow(data):
    """Tìm hàm phân tích dòng tiền trong money_flow.py."""
    function_names = (
        "evaluate_money_flow",
        "analyze_money_flow",
        "analyze_flow",
        "get_money_flow",
    )

    for name in function_names:
        function = getattr(money_flow_module, name, None)
        if callable(function):
            try:
                result = function(data)
                if isinstance(result, dict):
                    return result
            except Exception:
                pass

    return {}


def make_trading_decision(df: pd.DataFrame, ai_result: dict) -> dict:
    result = {
        "decision": "CHỜ MUA",
        "reason": "Chưa đủ dữ liệu xác nhận điểm mua an toàn.",
        "buy_zone": "CHƯA XÁC ĐỊNH",
        "confirm_price": "CHƯA XÁC ĐỊNH",
        "target_price": "CHƯA XÁC ĐỊNH",
        "stop_loss": "CHƯA XÁC ĐỊNH",
        "support": None,
        "resistance": None,
        "distance_to_support_pct": None,
        "distance_to_resistance_pct": None,
        "risk_reward_ratio": None,
        "volume_confirmed": False,
        "breakout_confirmed": False,
        "flow_status": "CHƯA ĐỦ DỮ LIỆU",
        "decision_evidence": [],
        "buy_confirmation_conditions": [],
        "invalidation_conditions": [],
        "why_not_buying": [],
    }

    if not isinstance(df, pd.DataFrame) or len(df) < 3:
        return result

    required = ["close", "high", "low"]
    if any(col not in df.columns for col in required):
        return result

    data = df.copy()

    for col in ["close", "high", "low", "volume", "ATR14"]:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna(subset=required).sort_index()

    if len(data) < 3:
        return result

    last = data.iloc[-1]
    previous = data.iloc[-2]

    close = _number(last["close"])
    previous_close = _number(previous["close"])
    atr = _number(last.get("ATR14"))

    if close is None or close <= 0:
        return result

    # Không tự tạo ATR khi dữ liệu không có.
    atr_valid = atr is not None and atr > 0

    try:
        tech = evaluate_technical(data) or {}
    except Exception:
        tech = {}

    try:
        sr = find_support_resistance(data) or {}
    except Exception:
        sr = {}

    flow = _get_money_flow(data)

    score = _number(tech.get("score"), 0)
    trend = _text(tech.get("trend"))
    momentum = _text(tech.get("momentum"))
    flow_status = _text(flow.get("flow_status", "CHƯA ĐỦ DỮ LIỆU"))

    risk_level = _text((ai_result or {}).get("risk_level", "TRUNG BÌNH"))

    support = _number(sr.get("support"))
    resistance = _number(sr.get("resistance"))

    # Không chấp nhận kháng cự nằm dưới giá hiện tại.
    if resistance is not None and resistance <= close:
        resistance = None

    dist_support = (
        (close - support) / close * 100
        if support is not None and support > 0 else None
    )

    dist_resistance = (
        (resistance - close) / close * 100
        if resistance is not None else None
    )

    evidence = []
    reasons_not_buying = []
    confirmation_conditions = []
    invalidation_conditions = []

    # 1. Đánh giá xu hướng độc lập.
    trend_bad = any(word in trend for word in (
        "GIẢM", "YẾU", "SUY YẾU", "DOWN", "WEAKEN",
        "BEAR", "NEGATIVE"
    ))

    trend_good = any(word in trend for word in (
        "TĂNG", "UPTREND", "BULL", "TÍCH CỰC",
        "PHỤC HỒI", "ĐẢO CHIỀU TĂNG"
    ))

    if trend_bad:
        evidence.append(f"Xu hướng chưa thuận lợi: {trend}.")
        reasons_not_buying.append("Xu hướng đang yếu hoặc suy giảm.")
    elif trend_good:
        evidence.append(f"Xu hướng có tín hiệu tích cực: {trend}.")
    else:
        evidence.append(f"Xu hướng chưa xác nhận rõ: {trend or 'không xác định'}.")

    # 2. Đánh giá động lượng độc lập.
    momentum_bad = any(word in momentum for word in (
        "YẾU", "SUY YẾU", "GIẢM", "WEAK",
        "NEGATIVE", "BEARISH"
    ))

    momentum_good = any(word in momentum for word in (
        "MẠNH", "TĂNG", "TÍCH CỰC",
        "BULLISH", "POSITIVE"
    ))

    if momentum_bad:
        evidence.append(f"Động lượng yếu: {momentum}.")
        reasons_not_buying.append("Động lượng chưa ủng hộ giao dịch mua.")
    elif momentum_good:
        evidence.append(f"Động lượng tích cực: {momentum}.")
    else:
        evidence.append("Động lượng chưa có xác nhận rõ ràng.")

    # 3. Đánh giá dòng tiền độc lập.
    flow_distribution = any(word in flow_status for word in (
        "PHÂN PHỐI", "TIÊU CỰC", "NEGATIVE",
        "DISTRIBUTION", "OUTFLOW", "SELLING"
    ))

    flow_positive = any(word in flow_status for word in (
        "TÍCH CỰC", "THU HÚT", "TÍCH LŨY",
        "POSITIVE", "ACCUMULATION", "INFLOW"
    ))

    if flow_distribution:
        evidence.append(f"Dòng tiền có dấu hiệu phân phối: {flow_status}.")
        reasons_not_buying.append("Dòng tiền phân phối hoặc tiêu cực.")
    elif flow_positive:
        evidence.append(f"Dòng tiền tích cực: {flow_status}.")
    else:
        evidence.append(f"Dòng tiền chưa xác nhận: {flow_status}.")

    # 4. Kiểm tra khối lượng.
    volume_confirmed = False
    volume_ratio = None

    if "volume" in data.columns and "VOL_MA20" in data.columns:
        volume = _number(last.get("volume"))
        vol_ma20 = _number(last.get("VOL_MA20"))

        if volume is not None and vol_ma20 is not None and vol_ma20 > 0:
            volume_ratio = volume / vol_ma20
            volume_confirmed = volume_ratio >= 1.2

    if volume_ratio is not None:
        evidence.append(
            f"Khối lượng bằng {volume_ratio:.2f} lần trung bình 20 phiên."
        )
    else:
        evidence.append("Chưa đủ dữ liệu để xác nhận khối lượng.")

    # 5. Xác nhận hành động giá.
    candle_range = _number(last["high"] - last["low"])
    close_position = None

    if candle_range is not None and candle_range > 0:
        close_position = (close - float(last["low"])) / candle_range

    price_action_confirmed = (
        previous_close is not None
        and close > previous_close
        and close_position is not None
        and close_position >= 0.65
    )

    # Đảo chiều cần đồng thời có giá, khối lượng và chỉ báo xác nhận.
    indicator_confirmation = momentum_good or flow_positive

    reversal_confirmed = (
        price_action_confirmed
        and volume_confirmed
        and indicator_confirmation
    )

    breakout_confirmed = (
        resistance is not None
        and previous_close is not None
        and previous_close <= resistance
        and close > resistance
        and volume_confirmed
    )

    if price_action_confirmed:
        evidence.append("Hành động giá có dấu hiệu hồi phục.")
    else:
        evidence.append("Chưa có xác nhận hành động giá hồi phục.")

    if reversal_confirmed:
        evidence.append(
            "Đảo chiều được xác nhận bởi giá, khối lượng "
            "và chỉ báo động lượng hoặc dòng tiền."
        )

    if breakout_confirmed:
        evidence.append("Giá vượt kháng cự kèm khối lượng xác nhận.")

    # 6. Tính vùng mua, cắt lỗ, mục tiêu chỉ khi có ATR thật.
    zone_low = None
    zone_high = None
    stop_loss = None
    target_price = None
    confirm_price = None
    rr_ratio = None

    if atr_valid and support is not None and support < close:
        zone_low = max(support, close - 0.8 * atr)
        zone_high = min(support + 0.3 * atr, close)

        # Cắt lỗ dưới hỗ trợ với khoảng đệm ATR vừa phải.
        stop_loss = support - 0.3 * atr

        if stop_loss <= 0 or stop_loss >= zone_low:
            stop_loss = None

        # Chỉ lấy kháng cự thực tế phía trên làm mục tiêu.
        if resistance is not None and resistance > zone_high:
            target_price = resistance

        if zone_low is not None and zone_high is not None:
            risk = zone_high - stop_loss if stop_loss is not None else None
            reward = target_price - zone_high if target_price is not None else None

            if risk is not None and reward is not None and risk > 0 and reward > 0:
                rr_ratio = reward / risk

    if atr_valid and resistance is not None:
        confirm_price = resistance + 0.2 * atr

    # 7. Các điều kiện an toàn bắt buộc.
    data_ready = (
        atr_valid
        and support is not None
        and target_price is not None
        and stop_loss is not None
        and rr_ratio is not None
    )

    near_support = (
        dist_support is not None
        and 0 <= dist_support <= 2.5
    )

    near_resistance = (
        dist_resistance is not None
        and 0 <= dist_resistance <= 2.0
    )

    rr_acceptable = rr_ratio is not None and rr_ratio >= 1.5

    trend_gate = trend_good or (reversal_confirmed and not trend_bad)
    momentum_gate = momentum_good or reversal_confirmed
    flow_gate = not flow_distribution and (flow_positive or reversal_confirmed)

    # Không để điểm tổng hợp bù cho điều kiện an toàn bắt buộc.
    buy_conditions_met = (
        data_ready
        and trend_gate
        and momentum_gate
        and flow_gate
        and volume_confirmed
        and (reversal_confirmed or breakout_confirmed)
        and rr_acceptable
        and not near_resistance
        and risk_level not in ("CAO", "HIGH", "RẤT CAO", "VERY HIGH")
    )

    if not atr_valid:
        reasons_not_buying.append("Thiếu ATR14 hợp lệ; không thể tính vùng mua và quản trị rủi ro.")
    if support is None:
        reasons_not_buying.append("Chưa xác định được vùng hỗ trợ.")
    if target_price is None:
        reasons_not_buying.append("Chưa xác định được kháng cự mục tiêu phía trên.")
    if rr_ratio is None:
        reasons_not_buying.append("Chưa tính được tỷ lệ lợi nhuận/rủi ro.")
    elif not rr_acceptable:
        reasons_not_buying.append(f"Tỷ lệ lợi nhuận/rủi ro chỉ đạt {rr_ratio:.2f}, thấp hơn 1.5.")
    if not volume_confirmed:
        reasons_not_buying.append("Khối lượng chưa xác nhận.")
    if flow_distribution:
        reasons_not_buying.append("Không mua khi dòng tiền đang phân phối.")
    if near_resistance:
        reasons_not_buying.append("Giá đang sát kháng cự, dư địa tăng hạn chế.")
    if risk_level in ("CAO", "HIGH", "RẤT CAO", "VERY HIGH"):
        reasons_not_buying.append("Mức rủi ro tổng thể cao.")

    # 8. Điều kiện xác nhận và vô hiệu hóa cho người theo dõi.
    confirmation_conditions = [
        "Giá duy trì trên vùng hỗ trợ đã xác định.",
        "Khối lượng tăng so với trung bình 20 phiên.",
        "Động lượng hoặc dòng tiền chuyển sang tích cực.",
        "Tỷ lệ lợi nhuận/rủi ro đạt tối thiểu 1.5."
    ]

    invalidation_conditions = [
        "Giá đóng cửa thủng vùng hỗ trợ.",
        "Dòng tiền chuyển sang trạng thái phân phối.",
        "Động lượng tiếp tục suy yếu.",
        "Khối lượng tăng mạnh nhưng giá giảm."
    ]

    # 9. Ra quyết định.
    if risk_level in ("CAO", "HIGH", "RẤT CAO", "VERY HIGH"):
        decision = "TRÁNH MUA"
        reason = "Rủi ro tổng thể cao. Ưu tiên bảo toàn vốn."

    elif flow_distribution and trend_bad and momentum_bad:
        decision = "TRÁNH MUA"
        reason = "Xu hướng, động lượng và dòng tiền cùng bất lợi."

    elif buy_conditions_met:
        decision = "MUA"
        reason = (
            "Các điều kiện an toàn đã được xác nhận độc lập: "
            "xu hướng, động lượng, dòng tiền, giá, khối lượng "
            "và tỷ lệ lợi nhuận/rủi ro."
        )

    elif trend_bad or momentum_bad or flow_distribution:
        decision = "CHỜ MUA"
        reason = "Có điều kiện kỹ thuật chưa đạt. Chưa mở vị thế mua mới."

    else:
        decision = "CHỜ MUA"
        reason = "Chưa có đủ xác nhận đồng thời để kích hoạt điểm mua."

    # CHỜ MUA là theo dõi, không phải khuyến nghị đặt lệnh.
    if decision != "MUA":
        buy_zone = "CHƯA CÓ ĐIỂM MUA ĐƯỢC XÁC NHẬN"
    elif zone_low is not None and zone_high is not None:
        buy_zone = f"{zone_low:,.0f} - {zone_high:,.0f}"
    else:
        buy_zone = "CHƯA XÁC ĐỊNH"

    if not atr_valid:
        confirm_price = None
        target_price = None
        stop_loss = None
        rr_ratio = None
        buy_zone = "CHƯA XÁC ĐỊNH"

    return {
        # Giữ các khóa cũ để tương thích app.py.
        "decision": decision,
        "reason": reason,
        "buy_zone": buy_zone,
        "confirm_price": _price(confirm_price),
        "target_price": _price(target_price),
        "stop_loss": _price(stop_loss),
        "support": support,
        "resistance": resistance,
        "distance_to_support_pct": (
            round(dist_support, 2) if dist_support is not None else None
        ),
        "distance_to_resistance_pct": (
            round(dist_resistance, 2) if dist_resistance is not None else None
        ),
        "risk_reward_ratio": (
            round(rr_ratio, 2) if rr_ratio is not None else None
        ),
        "volume_confirmed": volume_confirmed,
        "breakout_confirmed": breakout_confirmed,

        # Dữ liệu phân tích bổ sung.
        "flow_status": flow_status,
        "decision_evidence": evidence,
        "buy_confirmation_conditions": confirmation_conditions,
        "invalidation_conditions": invalidation_conditions,
        "why_not_buying": reasons_not_buying,
        "reversal_confirmed": reversal_confirmed,
        "price_action_confirmed": price_action_confirmed,
        "trend_gate": trend_gate,
        "momentum_gate": momentum_gate,
        "flow_gate": flow_gate,
        "atr_available": atr_valid,
    }
