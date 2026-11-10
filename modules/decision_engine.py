# modules/decision_engine.py

class DecisionEngine:
    def __init__(self, market_data, technical_indicators, sr_levels):
        self.market_data = market_data
        self.indicators = technical_indicators
        self.sr = sr_levels

    def generate_strategy(self):
        """
        Phân rã thành 2 lối chơi độc lập, loại bỏ xung đột logic.
        """
        trend = self.indicators.get("trend", "Giảm / Tích lũy")
        risk = self.indicators.get("risk", "CAO")
        current_price = self.sr.get("current_price", 0)
        support = self.sr.get("support", 0)
        resistance = self.sr.get("resistance", 0)
        is_safe_distance = self.sr.get("is_safe_distance", True)

        # Khung kết quả trả về cấu trúc 2 lối chơi
        strategy_result = {
            "overall_status": {
                "trend": trend,
                "risk_level": risk,
                "action_signal": "ĐỨNG NGOÀI / CHỜ BÁN" if risk == "CAO" else "QUAN SÁT"
            },
            "t_plus_strategy": None,
            "holding_strategy": None
        }

        # --- NHÁNH 1: LỐI CHƠI T+ (Lướt sóng ngắn hạn) ---
        # Quy tắc: Nếu rủi ro CAO hoặc khoảng cách đến kháng cự quá hẹp -> KHÔNG PHÁT TÍN HIỆU MUA T+
        if risk == "CAO" or not is_safe_distance:
            strategy_result["t_plus_strategy"] = {
                "status": "KHÔNG KHUYẾN NGHỊ MUA",
                "reason": "Rủi ro thị trường cao hoặc biên độ đến kháng cự quá hẹp, không đạt tỷ lệ R:R an toàn."
            }
        else:
            # Tính toán các mốc T+ chuẩn thực chiến
            entry_min, entry_max = self.sr.get("entry_zone", (support, support * 1.02))
            stop_loss = round(support * 0.97, 2) # Cắt lỗ dưới hỗ trợ 3%
            take_profit = round(resistance * 0.98, 2) # Chốt lời sát kháng cự
            
            # Tính tỷ lệ Rủi ro / Lợi nhuận (R:R)
            risk_amount = current_price - stop_loss
            reward_amount = take_profit - current_price
            rr_ratio = round(reward_amount / risk_amount, 2) if risk_amount > 0 else 0

            strategy_result["t_plus_strategy"] = {
                "status": "CÓ THỂ CÂN NHẮC THĂM DÒ",
                "entry_zone": f"{entry_min:,.0f} - {entry_max:,.0f}",
                "take_profit": f"{take_profit:,.0f}",
                "stop_loss": f"{stop_loss:,.0f} (Thủng hỗ trợ cứng)",
                "risk_reward_ratio": f"1:{rr_ratio}",
                "max_holding_days": "3 - 7 phiên (T+3 đến T+7)",
                "note": "Tuân thủ tuyệt đối cắt lỗ, không gồng lỗ ngắn hạn."
            }

        # --- NHÁNH 2: LỐI CHƠI NẮM GIỮ (Trung / Dài hạn) ---
        if "Giảm" in trend or risk == "CAO":
            strategy_result["holding_strategy"] = {
                "status": "CHƯA PHÙ HỢP TÍCH SẢN",
                "action": "Tiếp tục đứng ngoài quan sát xu hướng lớn. Chưa vội gom hàng khi dòng tiền trung tính/yếu."
            }
        else:
            strategy_result["holding_strategy"] = {
                "status": "NẮM GIỮ / GỒNG LÃI",
                "action": "Tiếp tục nắm giữ theo xu hướng lớn. Chỉ chốt lời từng phần khi gãy đường xu hướng (MA50/MA200)."
            }

        return strategy_result
