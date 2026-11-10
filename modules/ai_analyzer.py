
import pandas as pd
import numpy as np

from modules.money_flow import evaluate_money_flow
from modules.technical_analysis import evaluate_technical
from modules.support_resistance import find_support_resistance


def _num(value, default=None):
    try:
        number = float(value)
        return number if np.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def run_ai_analysis(
    df: pd.DataFrame,
    symbol: str,
    ato_data: dict = None,
    financial_metrics: dict = None
) -> dict:
    """
    Phân tích tổng hợp:
    - Xu hướng và động lượng.
    - Dòng tiền có bằng chứng.
    - Hỗ trợ, kháng cự.
    - Rủi ro và các yếu tố phản biện.

    Không tự tạo dữ liệu ATO hoặc chỉ báo còn thiếu.
    """

    if df is None or not isinstance(df, pd.DataFrame) or len(df) < 3:
        return None

    data = df.copy()

    required = ["close", "high", "low"]
    if any(col not in data.columns for col in required):
        return None

    for col in required:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna(subset=required)

    if len(data) < 3:
        return None

    last = data.iloc[-1]
    prev = data.iloc[-2]

    close = _num(last.get("close"))
    previous_close = _num(prev.get("close"))

    if close is None or close <= 0:
        return None

    # Phân tích các module thành phần.
    tech = evaluate_technical(data)
    flow = evaluate_money_flow(data)
    sr = find_support_resistance(data)

    score = _num(tech.get("score"), 0)

    rsi = _num(last.get("RSI14"))
    ma20 = _num(last.get("MA20"))
    ma50 = _num(last.get("MA50"))
    ma200 = _num(last.get("MA200"))

    # 1. Xác định xu hướng, không tự kết luận khi thiếu MA.
    if ma20 is not None and ma50 is not None:
        if close > ma20 > ma50:
            trend = "TĂNG"
        elif close < ma20 < ma50:
            trend = "GIẢM"
        else:
            trend = "TÍCH LŨY / CHƯA ĐỒNG THUẬN"
    elif ma20 is not None:
        trend = (
            "TĂNG NGẮN HẠN"
            if close > ma20
            else "YẾU HƠN MA20"
        )
    else:
        trend = "CHƯA ĐỦ DỮ LIỆU XÁC ĐỊNH XU HƯỚNG"

    if ma200 is not None:
        long_trend = (
            "Giá trên MA200"
            if close > ma200
            else "Giá dưới MA200"
        )
    else:
        long_trend = "Chưa đủ dữ liệu MA200"

    # 2. Đánh giá động lượng.
    if rsi is None:
        momentum = "CHƯA ĐỦ DỮ LIỆU RSI"
    elif rsi >= 70:
        momentum = "MẠNH NHƯNG QUÁ MUA"
    elif rsi >= 55:
        momentum = "TÍCH CỰC"
    elif rsi >= 45:
        momentum = "TRUNG TÍNH"
    elif rsi >= 30:
        momentum = "SUY YẾU"
    else:
        momentum = "QUÁ BÁN"

    # 3. Dòng tiền: dùng đúng kết quả và bằng chứng của module 3.
    flow_status = flow.get(
        "flow_status",
        "TRUNG TÍNH / CHƯA ĐỦ BẰNG CHỨNG"
    )

    flow_notes = flow.get("notes", [])
    flow_evidence = flow.get("evidence", [])

    if not isinstance(flow_notes, list):
        flow_notes = [str(flow_notes)]

    if not isinstance(flow_evidence, list):
        flow_evidence = [str(flow_evidence)]

    # 4. Hỗ trợ và kháng cự.
    support = _num(sr.get("support"))
    resistance = _num(sr.get("resistance"))

    dist_support = _num(sr.get("dist_to_support_pct"))
    dist_resistance = _num(sr.get("dist_to_resistance_pct"))

    counter_arguments = []

    if previous_close is not None and close > previous_close:
        vol_ratio = _num(flow.get("vol_ratio_20"))

        if vol_ratio is not None and vol_ratio < 0.8:
            counter_arguments.append(
                "Giá tăng nhưng khối lượng thấp hơn đáng kể "
                "mức trung bình 20 phiên: đà tăng chưa được "
                "thanh khoản xác nhận."
            )

    if rsi is not None and rsi >= 70:
        counter_arguments.append(
            "RSI từ 70 trở lên: cổ phiếu đang ở vùng quá mua, "
            "có thể xuất hiện rung lắc hoặc chốt lời."
        )

    if (
        dist_resistance is not None
        and 0 <= dist_resistance <= 2
    ):
        counter_arguments.append(
            f"Giá đang sát kháng cự khoảng {dist_resistance:.2f}%. "
            "Dư địa tăng ngắn hạn bị hạn chế; không nên mua đuổi."
        )

    if (
        dist_support is not None
        and dist_support <= 1.5
    ):
        counter_arguments.append(
            "Giá đang gần vùng hỗ trợ. Cần quan sát phản ứng "
            "giá để xác nhận hỗ trợ còn hiệu lực."
        )

    if "PHÂN PHỐI" in str(flow_status).upper():
        counter_arguments.append(
            "Dòng tiền có dấu hiệu phân phối. Cần thận trọng "
            "với rủi ro áp lực bán."
        )

    if "MÂU THUẪN" in str(flow_status).upper():
        counter_arguments.append(
            "Các chỉ báo dòng tiền chưa đồng thuận; "
            "chưa đủ cơ sở kết luận bên mua hay bên bán chiếm ưu thế."
        )

    if not counter_arguments:
        counter_arguments.append(
            "Chưa phát hiện yếu tố phản biện nổi bật "
            "trong các dữ liệu hiện có."
        )

    # 5. Xử lý ATO: chỉ sử dụng dữ liệu thực tế được truyền vào.
    ato_summary = "Không có dữ liệu ATO thực tế."

    if isinstance(ato_data, dict):
        ato_open = _num(ato_data.get("open"))
        ato_volume = _num(ato_data.get("volume"))

        if ato_open is not None and ato_volume is not None:
            gap_pct = (ato_open - close) / close * 100

            ato_summary = (
                f"Giá ATO: {ato_open:,.2f}; "
                f"chênh lệch so với giá đóng cửa trước: "
                f"{gap_pct:+.2f}%; "
                f"khối lượng ATO: {ato_volume:,.0f}."
            )

            if gap_pct >= 1.5:
                counter_arguments.append(
                    "ATO mở cửa tăng mạnh. Cần theo dõi khả năng "
                    "duy trì giá sau khi vào phiên liên tục."
                )
            elif gap_pct <= -1.5:
                counter_arguments.append(
                    "ATO mở cửa giảm mạnh. Cần theo dõi áp lực bán "
                    "và phản ứng của vùng hỗ trợ."
                )

    # 6. Đánh giá rủi ro tổng hợp.
    high_risk_conditions = 0

    if score <= -3:
        high_risk_conditions += 1

    if rsi is not None and rsi < 30:
        high_risk_conditions += 1

    if "PHÂN PHỐI" in str(flow_status).upper():
        high_risk_conditions += 1

    if (
        dist_support is not None
        and dist_support < 0
    ):
        high_risk_conditions += 1

    if high_risk_conditions >= 2:
        risk_level = "CAO"
    elif score >= 2 and rsi is not None and 45 <= rsi < 70:
        risk_level = "THẤP"
    else:
        risk_level = "TRUNG BÌNH"

    # 7. Tổng hợp nhận định có căn cứ.
    summary_parts = [
        f"Mã {symbol}: giá đóng cửa {close:,.2f}.",
        f"Xu hướng: {trend}.",
        f"Động lượng: {momentum}.",
        f"Vị trí dài hạn: {long_trend}.",
        f"Dòng tiền: {flow_status}.",
    ]

    if rsi is not None:
        summary_parts.append(f"RSI14: {rsi:.2f}.")

    if ma20 is not None:
        summary_parts.append(f"MA20: {ma20:,.2f}.")

    if ma50 is not None:
        summary_parts.append(f"MA50: {ma50:,.2f}.")

    if support is not None:
        summary_parts.append(f"Hỗ trợ tham chiếu: {support:,.2f}.")

    if resistance is not None:
        summary_parts.append(f"Kháng cự tham chiếu: {resistance:,.2f}.")

    if dist_resistance is not None and dist_resistance >= 0:
        summary_parts.append(
            f"Cách kháng cự: {dist_resistance:.2f}%."
        )

    if flow_evidence:
        summary_parts.append(
            "Bằng chứng dòng tiền: " + "; ".join(
                str(x) for x in flow_evidence[:4]
            ) + "."
        )

    summary_parts.append(f"Rủi ro tổng quan: {risk_level}.")

    summary_text = " ".join(summary_parts)

    # 8. Thông tin tài chính cơ bản.
    fin_summary = "Chưa có dữ liệu tài chính chi tiết."

    if isinstance(financial_metrics, dict) and financial_metrics:
        fin_summary = ", ".join(
            f"{key}: {value}"
            for key, value in financial_metrics.items()
            if value is not None
        )

    return {
        # Giữ nguyên các khóa cũ để tương thích giao diện.
        "trend": trend,
        "momentum": momentum,
        "flow_summary": flow_status,
        "ato_summary": ato_summary,
        "counter_arguments": counter_arguments,
        "risk_level": risk_level,
        "summary": summary_text,
        "fin_summary": fin_summary,

        # Dữ liệu bổ sung cho các module tiếp theo.
        "technical_score": score,
        "rsi14": rsi,
        "support": support,
        "resistance": resistance,
        "dist_to_support_pct": dist_support,
        "dist_to_resistance_pct": dist_resistance,
        "flow_notes": flow_notes,
        "flow_evidence": flow_evidence,
        "technical_warnings": tech.get("warnings", []),
    }
