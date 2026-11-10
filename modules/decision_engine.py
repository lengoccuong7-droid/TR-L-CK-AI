import pandas as pd
from modules.technical_analysis import evaluate_technical
from modules.support_resistance import find_support_resistance

def make_trading_decision(df: pd.DataFrame, ai_result: dict) -> dict:
    last = df.iloc[-1]
    last_close = float(last["close"])
    tech = evaluate_technical(df)
    sr = find_support_resistance(df)
    score = tech["score"]
    risk_level = ai_result["risk_level"]
    atr = float(last.get("ATR14", last_close * 0.02))

    if score >= 3 and risk_level != "CAO":
        decision = "MUA"
        reason = "Tín hiệu kỹ thuật ủng hộ mạnh mẽ, dòng tiền tốt và rủi ro ở mức kiểm soát được."
    elif score >= 1:
        decision = "CHỜ MUA"
        reason = "Xu hướng tích cực nhưng cần kiên nhẫn chờ giá điều chỉnh về vùng hỗ trợ đẹp."
    elif score >= -1:
        decision = "GIỮ"
        reason = "Cổ phiếu đang tích lũy đi ngang, chưa xuất hiện tín hiệu vi phạm xấu."
    elif score >= -3:
        decision = "CHỜ BÁN"
        reason = "Động lượng suy yếu, ưu tiên canh các nhịp hồi phục kỹ thuật để hạ tỷ trọng."
    else:
        decision = "BÁN"
        reason = "Tín hiệu kỹ thuật vi phạm ngưỡng an toàn, áp lực bán xả lớn."

    support_price = sr["support"]
    resistance_price = sr["resistance"]

    # --- TỐT ƯU VÙNG MUA CHUẨN (CÓ KHÔNG GIAN THỞ BẰNG 0.5 * ATR) ---
    buy_zone_low = round(max(support_price, last_close - 1.5 * atr), 2)
    
    # Cận trên cộng thêm biên độ ATR ngắn hạn nhưng chặn lại không vượt quá Kháng cự
    buy_zone_high = round(min(resistance_price, last_close + 0.5 * atr), 2)
    
    # Đảm bảo cận dưới không lớn hơn cận trên
    if buy_zone_low > buy_zone_high:
        buy_zone_low = round(buy_zone_high * 0.98, 2)

    buy_zone = f"{buy_zone_low:,.0f} - {buy_zone_high:,.0f}"

    confirm_price = round(last_close * 1.015, 2)
    target_price = round(max(resistance_price, last_close + 2.5 * atr), 2)
    stop_loss = round(min(support_price * 0.97, last_close - 2.0 * atr), 2)

    return {
        "decision": decision,
        "reason": reason,
        "buy_zone": buy_zone,
        "confirm_price": f"{confirm_price:,.0f}",
        "target_price": f"{target_price:,.0f}",
        "stop_loss": f"{stop_loss:,.0f}",
    }
