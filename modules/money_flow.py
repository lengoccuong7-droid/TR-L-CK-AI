
import pandas as pd
import numpy as np


def _num(value):
    try:
        value = float(value)
        return value if np.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def evaluate_money_flow(df: pd.DataFrame) -> dict:
    """
    Phân tích dòng tiền dựa trên giá, khối lượng,
    MFI, CMF và OBV.

    Giữ các khóa cũ để tương thích với ai_analyzer.py:
        vol_ratio_20
        mfi14
        flow_status
        notes

    Bổ sung:
        vol_ratio_5
        cmf20
        obv_trend
        price_change_pct
        price_change_5d_pct
        flow_strength
        accumulation_signal
        distribution_signal
        evidence
    """

    if df is None or not isinstance(df, pd.DataFrame):
        raise ValueError("Dữ liệu dòng tiền không hợp lệ.")

    if len(df) < 2:
        raise ValueError("Cần tối thiểu 2 phiên để phân tích dòng tiền.")

    required = ["close", "volume", "high", "low"]
    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(
            "Thiếu dữ liệu: " + ", ".join(missing)
        )

    data = df.copy()

    for col in required:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna(subset=required)

    if len(data) < 2:
        raise ValueError("Không đủ dữ liệu hợp lệ.")

    last = data.iloc[-1]
    prev = data.iloc[-2]

    close = _num(last["close"])
    prev_close = _num(prev["close"])
    volume = _num(last["volume"])

    if not close or not prev_close or volume is None:
        raise ValueError("Giá hoặc khối lượng không hợp lệ.")

    notes = []
    evidence = []

    # ==========================================
    # 1. KHỐI LƯỢNG SO VỚI TRUNG BÌNH
    # ==========================================

    vol_ma20 = _num(last.get("VOL_MA20"))
    vol_ma5 = _num(last.get("VOL_MA10"))

    # Nếu có dữ liệu VOL_MA5 riêng thì ưu tiên.
    if "VOL_MA5" in data.columns:
        vol_ma5 = _num(last.get("VOL_MA5"))

    if vol_ma5 is None:
        vol_ma5 = _num(
            data["volume"].tail(5).mean()
        ) if len(data) >= 5 else None

    if vol_ma20 is None:
        vol_ma20 = _num(
            data["volume"].tail(20).mean()
        ) if len(data) >= 20 else None

    vol_ratio_20 = (
        volume / vol_ma20
        if vol_ma20 is not None and vol_ma20 > 0
        else None
    )

    vol_ratio_5 = (
        volume / vol_ma5
        if vol_ma5 is not None and vol_ma5 > 0
        else None
    )

    if vol_ratio_20 is None:
        notes.append(
            "Chưa đủ dữ liệu để so sánh khối lượng với MA20."
        )
    elif vol_ratio_20 >= 1.5:
        notes.append(
            f"Khối lượng tăng mạnh: {vol_ratio_20:.2f} lần "
            "trung bình 20 phiên."
        )
        evidence.append("Thanh khoản tăng mạnh.")
    elif vol_ratio_20 >= 1.2:
        notes.append(
            f"Khối lượng cao hơn trung bình 20 phiên "
            f"({vol_ratio_20:.2f} lần)."
        )
    elif vol_ratio_20 < 0.7:
        notes.append(
            f"Khối lượng thấp, chỉ bằng {vol_ratio_20:.2f} "
            "lần trung bình 20 phiên."
        )

    # ==========================================
    # 2. BIẾN ĐỘNG GIÁ
    # ==========================================

    price_change_pct = (
        (close - prev_close) / prev_close * 100
    )

    price_change_5d_pct = None

    if len(data) >= 6:
        close_5d = _num(data.iloc[-6]["close"])

        if close_5d and close_5d > 0:
            price_change_5d_pct = (
                (close - close_5d) / close_5d * 100
            )

    # ==========================================
    # 3. MFI14
    # ==========================================

    mfi = _num(last.get("MFI14"))

    if mfi is None:
        notes.append("Chưa đủ dữ liệu MFI14.")
    elif mfi >= 80:
        notes.append(
            f"MFI14 = {mfi:.2f}: dòng tiền vào mạnh "
            "nhưng có thể đang ở vùng quá mua."
        )
    elif mfi <= 20:
        notes.append(
            f"MFI14 = {mfi:.2f}: dòng tiền yếu, "
            "có thể xuất hiện trạng thái quá bán."
        )
    elif mfi > 50:
        notes.append(
            f"MFI14 = {mfi:.2f}: dòng tiền theo MFI "
            "đang nghiêng về phía tích cực."
        )
    else:
        notes.append(
            f"MFI14 = {mfi:.2f}: dòng tiền theo MFI "
            "đang nghiêng về phía tiêu cực."
        )

    # ==========================================
    # 4. CMF20
    # ==========================================

    cmf = _num(last.get("CMF20"))

    if cmf is None:
        notes.append("Chưa đủ dữ liệu CMF20.")
    elif cmf > 0.05:
        notes.append(
            f"CMF20 = {cmf:.3f}: áp lực dòng tiền "
            "đang nghiêng về phía mua."
        )
        evidence.append("CMF dương.")
    elif cmf < -0.05:
        notes.append(
            f"CMF20 = {cmf:.3f}: áp lực dòng tiền "
            "đang nghiêng về phía bán."
        )
        evidence.append("CMF âm.")
    else:
        notes.append(
            f"CMF20 = {cmf:.3f}: dòng tiền tương đối trung tính."
        )

    # ==========================================
    # 5. OBV
    # ==========================================

    obv = _num(last.get("OBV"))
    obv_trend = "CHƯA ĐỦ DỮ LIỆU"

    if obv is not None and len(data) >= 6:
        old_obv = _num(data.iloc[-6].get("OBV"))

        if old_obv is not None:
            if obv > old_obv:
                obv_trend = "TĂNG"
                evidence.append("OBV tăng trong 5 phiên.")
            elif obv < old_obv:
                obv_trend = "GIẢM"
                evidence.append("OBV giảm trong 5 phiên.")
            else:
                obv_trend = "ĐI NGANG"

    # ==========================================
    # 6. PHÂN TÍCH GIÁ VÀ KHỐI LƯỢNG
    # ==========================================

    volume_strong = (
        vol_ratio_20 is not None
        and vol_ratio_20 >= 1.3
    )

    volume_weak = (
        vol_ratio_20 is not None
        and vol_ratio_20 < 0.8
    )

    price_up = price_change_pct > 1.0
    price_down = price_change_pct < -1.0
    price_sideways = abs(price_change_pct) <= 1.0

    price_volume_status = "CHƯA RÕ"

    if price_up and volume_strong:
        price_volume_status = "GIÁ TĂNG - KHỐI LƯỢNG TĂNG"
        notes.append(
            "Giá tăng cùng khối lượng lớn: có cầu mua xác nhận, "
            "cần kiểm tra thêm CMF và OBV."
        )

    elif price_up and volume_weak:
        price_volume_status = "GIÁ TĂNG - KHỐI LƯỢNG YẾU"
        notes.append(
            "Giá tăng nhưng khối lượng thấp: đà tăng "
            "chưa được thanh khoản xác nhận."
        )

    elif price_down and volume_strong:
        price_volume_status = "GIÁ GIẢM - KHỐI LƯỢNG TĂNG"
        notes.append(
            "Giá giảm với khối lượng lớn: áp lực bán đáng chú ý."
        )

    elif price_down and volume_weak:
        price_volume_status = "GIÁ GIẢM - KHỐI LƯỢNG YẾU"
        notes.append(
            "Giá giảm nhưng thanh khoản thấp: áp lực bán "
            "có thể suy yếu, chưa xác nhận đảo chiều."
        )

    elif price_sideways and volume_weak:
        price_volume_status = "ĐI NGANG - THANH KHOẢN THẤP"
        notes.append(
            "Giá đi ngang với thanh khoản thấp: có thể "
            "là giai đoạn tích lũy, cần chờ xác nhận."
        )

    elif price_sideways and volume_strong:
        price_volume_status = "ĐI NGANG - THANH KHOẢN CAO"
        notes.append(
            "Giá đi ngang nhưng thanh khoản cao: cần phân tích "
            "CMF, OBV và vị trí đóng cửa để phân biệt hấp thụ "
            "với phân phối."
        )

    # ==========================================
    # 7. VỊ TRÍ ĐÓNG CỬA TRONG BIÊN ĐỘ GIÁ
    # ==========================================

    high = _num(last["high"])
    low = _num(last["low"])

    close_position = None

    if high is not None and low is not None and high > low:
        close_position = (close - low) / (high - low)

    if close_position is not None:
        if close_position >= 0.7:
            notes.append(
                "Giá đóng cửa gần vùng cao nhất phiên."
            )
        elif close_position <= 0.3:
            notes.append(
                "Giá đóng cửa gần vùng thấp nhất phiên."
            )

    # ==========================================
    # 8. ĐÁNH GIÁ TÍCH LŨY VÀ PHÂN PHỐI
    # ==========================================

    positive_votes = 0
    negative_votes = 0

    if cmf is not None:
        if cmf > 0.05:
            positive_votes += 1
        elif cmf < -0.05:
            negative_votes += 1

    if mfi is not None:
        if mfi > 55:
            positive_votes += 1
        elif mfi < 45:
            negative_votes += 1

    if obv_trend == "TĂNG":
        positive_votes += 1
    elif obv_trend == "GIẢM":
        negative_votes += 1

    if close_position is not None:
        if close_position >= 0.7:
            positive_votes += 1
        elif close_position <= 0.3:
            negative_votes += 1

    accumulation_signal = (
        price_sideways
        and positive_votes >= 2
        and not (negative_votes >= 2)
    )

    distribution_signal = (
        price_sideways
        and negative_votes >= 2
        and not (positive_votes >= 2)
    )

    if accumulation_signal:
        flow_status = "CÓ DẤU HIỆU TÍCH LŨY"
        notes.append(
            "Một số chỉ báo dòng tiền ủng hộ khả năng tích lũy; "
            "chưa đủ căn cứ khẳng định tổ chức đang gom hàng."
        )

    elif distribution_signal:
        flow_status = "CÓ DẤU HIỆU PHÂN PHỐI"
        notes.append(
            "Một số chỉ báo dòng tiền ủng hộ khả năng phân phối; "
            "cần theo dõi thêm các phiên xác nhận."
        )

    elif positive_votes >= 2 and negative_votes == 0:
        flow_status = "NGHIÊNG TÍCH CỰC"

    elif negative_votes >= 2 and positive_votes == 0:
        flow_status = "NGHIÊNG TIÊU CỰC"

    elif positive_votes > 0 and negative_votes > 0:
        flow_status = "DÒNG TIỀN MÂU THUẪN"

    else:
        flow_status = "TRUNG TÍNH / CHƯA ĐỦ BẰNG CHỨNG"

    # ==========================================
    # 9. ĐỘ MẠNH DÒNG TIỀN
    # ==========================================

    if positive_votes >= 3 and negative_votes == 0:
        flow_strength = "MẠNH"
    elif positive_votes >= 2:
        flow_strength = "KHÁ"
    elif negative_votes >= 3 and positive_votes == 0:
        flow_strength = "RẤT YẾU"
    elif negative_votes >= 2:
        flow_strength = "YẾU"
    else:
        flow_strength = "TRUNG TÍNH"

    return {
        # Khóa cũ: giữ tương thích
        "vol_ratio_20": (
            round(vol_ratio_20, 2)
            if vol_ratio_20 is not None else None
        ),
        "mfi14": (
            round(mfi, 2) if mfi is not None else None
        ),
        "flow_status": flow_status,
        "notes": notes,

        # Khóa mới
        "vol_ratio_5": (
            round(vol_ratio_5, 2)
            if vol_ratio_5 is not None else None
        ),
        "cmf20": (
            round(cmf, 3) if cmf is not None else None
        ),
        "obv_trend": obv_trend,
        "price_change_pct": round(price_change_pct, 2),
        "price_change_5d_pct": (
            round(price_change_5d_pct, 2)
            if price_change_5d_pct is not None else None
        ),
        "price_volume_status": price_volume_status,
        "close_position": (
            round(close_position, 2)
            if close_position is not None else None
        ),
        "flow_strength": flow_strength,
        "accumulation_signal": accumulation_signal,
        "distribution_signal": distribution_signal,
        "positive_votes": positive_votes,
        "negative_votes": negative_votes,
        "evidence": evidence,
    }
