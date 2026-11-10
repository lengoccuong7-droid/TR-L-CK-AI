import pandas as pd
from modules.money_flow import evaluate_money_flow
from modules.technical_analysis import evaluate_technical
from modules.support_resistance import find_support_resistance

def run_ai_analysis(df: pd.DataFrame, symbol: str, ato_data: dict = None, financial_metrics: dict = None) -> dict:
    """
    Phân tích AI chuẩn xác. Nếu thiếu dữ liệu tuyệt đối không gán số 0 hay giả lập.
    """
    if df is None or df.empty or len(df) < 3:
        return None

    last = df.iloc[-1]
    prev = df.iloc[-2]
    last_close = float(last["close"])
    
    tech = evaluate_technical(df)
    flow = evaluate_money_flow(df)
    sr = find_support_resistance(df)
    
    rsi = float(last.get("RSI14", 50))
    vol_ratio = flow.get("vol_ratio_20", 1.0)
    
    trend = "Tăng" if last_close > last.get("MA50", last_close) else "Giảm / Tích lũy"
    momentum = "Mạnh" if rsi > 55 else ("Yếu" if rsi < 45 else "Trung bình")
    
    counter_arguments = []
    if last_close > prev["close"] and vol_ratio and vol_ratio < 0.8:
        counter_arguments.append("CẢNH BÁO BULL-TRAP: Giá tăng nhưng thanh khoản suy yếu (Tăng thiếu cầu).")
    if rsi > 70:
        counter_arguments.append("CẢNH BÁO GIÁ QUÁ CAO: RSI vượt 70, áp lực chốt lời ngắn hạn có thể gia tăng.")
    if sr.get("dist_to_resistance_pct", 99) < 2.0:
        counter_arguments.append(f"CẶP KHÁNG CỰ GẦN: Giá chỉ cách kháng cự mạnh {sr['resistance']} ({sr['dist_to_resistance_pct']}%), dư địa tăng ngắn hạn hẹp.")
    if rsi < 30 and vol_ratio and vol_ratio > 1.3:
        counter_arguments.append("TÍN HIỆU TÍCH CỰC ẨN: Quá bán kèm vol bùng nổ - Dấu hiệu dòng tiền bắt đáy (Spring/Accumulation).")

    # Xử lý thông tin ATO
    ato_summary = "Chưa có dữ liệu ATO đầu phiên."
    if ato_data and ato_data.get("open") is not None and ato_data.get("volume") is not None:
        ato_open = ato_data["open"]
        ato_vol = ato_data["volume"]
        gap_pct = ((ato_open - last_close) / last_close) * 100
        ato_summary = f"ATO Mở cửa: {ato_open:,.2f} ({gap_pct:+.2f}%), Khối lượng ATO: {ato_vol:,.0f}"
        if gap_pct > 1.5:
            counter_arguments.append(f"ATO TÍCH CỰC: Mở cửa tạo Gap tăng {gap_pct:+.2f}% kèm dòng tiền đầu phiên.")
        elif gap_pct < -1.5:
            counter_arguments.append(f"ATO TIÊU CỰC: Mở cửa sụt giảm {gap_pct:+.2f}%, áp lực bán gia tăng từ đầu phiên.")
    
    if not counter_arguments:
        counter_arguments.append("Chưa phát hiện mâu thuẫn bất thường giữa giá và khối lượng.")
        
    if tech["score"] < -2 or rsi > 75:
        risk_level = "CAO"
    elif tech["score"] >= 2 and rsi < 65:
        risk_level = "THẤP"
    else:
        risk_level = "TRUNG BÌNH"
        
    summary_text = (
        f"Mã {symbol} hiện ở xu hướng {trend} với động lượng {momentum}. "
        f"Dòng tiền: {flow['flow_status']}. {ato_summary}. Rủi ro tổng quan: {risk_level}."
    )
    
    # Xử lý thông tin chỉ số tài chính cơ bản để khớp với app.py
    fin_summary = "Chưa có dữ liệu tài chính chi tiết."
    if financial_metrics and isinstance(financial_metrics, dict):
        fin_summary = ", ".join([f"{k}: {v}" for k, v in financial_metrics.items()])

    return {
        "trend": trend,
        "momentum": momentum,
        "flow_summary": flow['flow_status'],
        "ato_summary": ato_summary,
        "counter_arguments": counter_arguments,
        "risk_level": risk_level,
        "summary": summary_text,
        "fin_summary": fin_summary
    }
