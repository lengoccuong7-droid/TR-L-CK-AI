# modules/support_resistance.py

class SupportResistanceAnalyzer:
    def __init__(self, df):
        self.df = df

    def calculate_levels(self):
        """
        Xác định vùng hỗ trợ, kháng cự và kiểm tra biên độ an toàn cho trader.
        """
        if self.df is None or self.df.empty:
            return None

        current_price = float(self.df['close'].iloc[-1])
        
        # Giả lập logic tìm hỗ trợ/kháng cự từ dữ liệu giá (hoặc thuật toán sẵn có của bạn)
        # Đảm bảo các mốc này được tính toán thực tế từ đáy/đỉnh gần nhất hoặc Bollinger/MA
        support = float(self.df['low'].rolling(window=20).min().iloc[-1])
        resistance = float(self.df['high'].rolling(window=20).max().iloc[-1])
        
        # Đảm bảo vùng mua (entry) nằm gần hỗ trợ
        entry_zone_min = support
        entry_zone_max = support * 1.025 # Biên độ chênh lệch 2.5% từ hỗ trợ
        
        # Kiểm tra khoảng cách an toàn đến kháng cự (Margin of Safety)
        distance_to_resistance_pct = (resistance - current_price) / current_price * 100
        
        # Nếu khoảng cách đến kháng cự quá hẹp (< 3%), cảnh báo không đủ biên lợi nhuận
        is_safe_distance = distance_to_resistance_pct >= 3.0

        return {
            "current_price": current_price,
            "support": support,
            "resistance": resistance,
            "entry_zone": (round(entry_zone_min, 2), round(entry_zone_max, 2)),
            "distance_to_resistance_pct": round(distance_to_resistance_pct, 2),
            "is_safe_distance": is_safe_distance
        }
