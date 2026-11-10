def score_description(score: int) -> str:
    if score >= 4:
        return "TÍN HIỆU RẤT MẠNH: Động lượng và xu hướng kỹ thuật đang cực kỳ ủng hộ đà tăng."
    elif score >= 2:
        return "TÍCH CỰC: Các chỉ báo xu hướng khá tốt, phù hợp theo dõi điểm mua."
    elif score >= -1:
        return "TRUNG TÍNH: Thị trường đang tích lũy hoặc thiếu xu hướng rõ ràng."
    elif score >= -3:
        return "TIÊU CỰC: Xu hướng kỹ thuật đang suy yếu, cần thận trọng."
    else:
        return "RẤT TIÊU CỰC: Áp lực bán áp đảo, rủi ro điều chỉnh mạnh."
