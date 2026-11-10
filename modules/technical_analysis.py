import pandas as pd

def evaluate_technical(df: pd.DataFrame) -> dict:
    last = df.iloc[-1]
    prev = df.iloc[-2]
    score = 0
    signals = []

    if pd.notna(last.get("MA20")):
        if last["close"] > last["MA20"]:
            score += 1
            signals.append("Giá đang nằm trên đường trung bình MA20.")
        else:
            score -= 1
            signals.append("Giá đã cắt xuống dưới đường MA20.")

    if pd.notna(last.get("MA50")):
        if last["close"] > last["MA50"]:
            score += 1
            signals.append("Giá nằm trên MA50 (xu hướng trung hạn tích cực).")
        else:
            score -= 1
            signals.append("Giá nằm dưới MA50 (trung hạn suy yếu).")

    if pd.notna(last.get("MA200")):
        if last["close"] > last["MA200"]:
            score += 1
            signals.append("Nằm trên MA200 - Xu hướng dài hạn tăng.")
        else:
            score -= 1
            signals.append("Nằm dưới MA200 - Xu hướng dài hạn giảm.")

    if pd.notna(last.get("MACD")) and pd.notna(last.get("MACD_SIGNAL")):
        if prev["MACD"] <= prev["MACD_SIGNAL"] and last["MACD"] > last["MACD_SIGNAL"]:
            score += 2
            signals.append("MACD vừa cắt LÊN đường tín hiệu (Tín hiệu Mua).")
        elif prev["MACD"] >= prev["MACD_SIGNAL"] and last["MACD"] < last["MACD_SIGNAL"]:
            score -= 2
            signals.append("MACD vừa cắt XUỐNG đường tín hiệu (Tín hiệu Bán).")

    rsi = last.get("RSI14")
    if pd.notna(rsi):
        rsi = float(rsi)
        if rsi > 70:
            score -= 1
            signals.append(f"RSI14 = {rsi:.1f} (Cảnh báo quá mua).")
        elif rsi < 30:
            score += 1
            signals.append(f"RSI14 = {rsi:.1f} (Vùng quá bán - cơ hội phục hồi).")
        elif 50 <= rsi <= 65:
            score += 1
            signals.append(f"RSI14 = {rsi:.1f} (Động lượng tăng duy trì ổn định).")

    return {"score": score, "signals": signals}
