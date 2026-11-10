import pandas as pd

def find_support_resistance(df: pd.DataFrame, window: int = 60) -> dict:
    recent = df.tail(window)
    support = float(recent["low"].min())
    resistance = float(recent["high"].max())
    last_close = float(df["close"].iloc[-1])

    dist_to_support_pct = round(((last_close - support) / support) * 100, 2)
    dist_to_resistance_pct = round(((resistance - last_close) / last_close) * 100, 2)

    return {
        "support": support,
        "resistance": resistance,
        "dist_to_support_pct": dist_to_support_pct,
        "dist_to_resistance_pct": dist_to_resistance_pct
    }
