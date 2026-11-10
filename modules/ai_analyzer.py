# modules/ai_analyzer.py

class AIAnalyzer:
    def __init__(self, api_client=None):
        self.api_client = api_client

    def build_prompt_with_validation(self, strategy_data):
        """
        Tạo system prompt nghiêm ngặt, ép AI không được mâu thuẫn logic
        giữa trạng thái rủi ro và hành động mua.
        """
        system_prompt = """
        Bạn là một Chuyên gia Quản trị Rủi ro và Trader chứng khoán kỳ cựu. 
        NHIỆM VỤ: Dựa trên dữ liệu cấu trúc chiến lược 2 lối chơi được cung cấp, hãy viết bản nhận định sắc sảo, mạch lạc.
        
        NGUYÊN TẮC BẮT BUỘC:
        1. Tuyệt đối KHÔNG mâu thuẫn logic: Nếu rủi ro cao hoặc hệ thống báo không khuyến nghị mua T+, cấm tuyệt đối việc hô hào bắt đáy.
        2. Phải phân định rõ ràng 2 phần: Dành cho Trader T+ (lướt sóng ngắn hạn) và Dành cho Nhà đầu tư Nắm giữ (trung dài hạn).
        3. Văn phong: Khách quan, sắc sảo, đề cao kỷ luật và quản trị vốn, không hô hào cảm tính theo kiểu "Thầy - Trò" mù quáng.
        """
        
        user_content = f"Dữ liệu chiến lược hệ thống phân tích:\n{strategy_data}"
        
        return system_prompt, user_content
