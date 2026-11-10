import pandas as pd

def evaluate_money_flow(df: pd.DataFrame) -> dict:
    last = df.iloc[-1]
    notes = []

    vol_ratio = None
    if pd.notna(last.get("VOL_MA20")) and last["VOL_MA20"] > 0:
        vol_ratio = float(last["volume"] / last["VOL_MA20"])

    mfi = last.get("MFI14")
    if pd.notna(mfi):
        mfi = float(mfi)
        if mfi > 80:
            notes.append("MFI ở vùng quá mua (dòng tiền nóng có thể hạ nhiệt).")
        elif mfi < 20:
            notes.append("MFI ở vùng quá bán (có thể xuất hiện dòng tiền bắt đáy).")

    if vol_ratio is not None:
        if vol_ratio >= 1.5:
            notes.append(f"Thanh khoản bùng nổ (đạt {vol_ratio:.2f}x so với trung bình 20 phiên).")
        elif vol_ratio < 0.7:
            notes.append(f"Thanh khoản sụt giảm (chỉ bằng {vol_ratio:.2f}x trung bình 20 phiên).")

    price_change_pct = float((last["close"] - df.iloc[-2]["close"]) / df.iloc[-2]["close"] * 100)
    if vol_ratio and vol_ratio >= 1.3 and price_change_pct > 1.5:
        flow_status = "Tích cực (Dòng tiền mua chủ động hấp thụ)"
    elif vol_ratio and vol_ratio >= 1.3 and price_change_pct < -1.5:
        flow_status = "Tiêu cực (Áp lực bán xả hàng khối lượng lớn)"
    elif vol_ratio and vol_ratio < 0.8 and abs(price_change_pct) < 1.0:
        flow_status = "Cạn cung / Tích lũy thanh khoản thấp"
    else:
        flow_status = "Trung tính"

    return {
        "vol_ratio_20": round(vol_ratio, 2) if vol_ratio else None,
        "mfi14": round(mfi, 2) if mfi else None,
        "flow_status": flow_status,
        "notes": notes,
    }
