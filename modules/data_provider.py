import pandas as pd
import numpy as np

def load_from_file(uploaded_file) -> pd.DataFrame:
    """
    Đọc dữ liệu từ tệp CSV hoặc Excel.
    Trả về None nếu tệp trống hoặc thiếu các cột bắt buộc.
    """
    if uploaded_file is None:
        return None
        
    file_name = getattr(uploaded_file, "name", "").lower()
    try:
        if file_name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif file_name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file)
        else:
            return None

        if df.empty:
            return None

        df.columns = [str(c).strip().lower() for c in df.columns]
        
        rename_dict = {
            "ngày": "date", "thời gian": "date", "ngay": "date", "date": "date",
            "mở": "open", "mo": "open", "giá mở": "open", "open": "open",
            "cao": "high", "giá cao": "high", "high": "high",
            "thấp": "low", "giá thấp": "low", "low": "low",
            "đóng": "close", "dong": "close", "giá đóng": "close", "close": "close",
            "khối lượng": "volume", "khoi luong": "volume", "kl": "volume", "volume": "volume"
        }
        df = df.rename(columns=rename_dict)

        required = ["date", "open", "high", "low", "close", "volume"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            return None

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            
        df = df.dropna(subset=["date", "close"]).sort_values("date").reset_index(drop=True)
        return df if len(df) >= 3 else None

    except Exception:
        return None

def parse_grid_data(df_grid: pd.DataFrame) -> pd.DataFrame:
    """
    Chuẩn hóa dữ liệu dán trực tiếp từ Grid (Excel-like).
    """
    if df_grid is None or df_grid.empty:
        return None
    try:
        df = df_grid.copy()
        df.columns = [str(c).strip().lower() for c in df.columns]
        rename_dict = {
            "ngày": "date", "ngay": "date", "date": "date",
            "mở": "open", "giá mở": "open", "open": "open",
            "cao": "high", "giá cao": "high", "high": "high",
            "thấp": "low", "giá thấp": "low", "low": "low",
            "đóng": "close", "giá đóng": "close", "close": "close",
            "khối lượng": "volume", "kl": "volume", "volume": "volume"
        }
        df = df.rename(columns=rename_dict)
        required = ["date", "open", "high", "low", "close", "volume"]
        for col in required:
            if col not in df.columns:
                return None
        
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["date", "close"]).sort_values("date").reset_index(drop=True)
        return df if len(df) >= 3 else None
    except Exception:
        return None
