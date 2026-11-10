
def score_description(score: int) -> str:
    """
    Giải thích điểm kỹ thuật.
    Giữ nguyên thang điểm và tên hàm để tương thích App.py.
    """

    try:
        score = float(score)
    except (TypeError, ValueError):
        return "CHƯA ĐỦ DỮ LIỆU: Không xác định được điểm kỹ thuật."

    if score >= 5:
        return (
            "RẤT TÍCH CỰC: Nhiều tín hiệu kỹ thuật ủng hộ xu hướng tăng. "
            "Tuy nhiên vẫn phải kiểm tra kháng cự và điểm mua."
        )

    elif score >= 3:
        return (
            "TÍCH CỰC: Xu hướng và động lượng có dấu hiệu thuận lợi. "
            "Chờ điểm mua có tỷ lệ lợi nhuận/rủi ro phù hợp."
        )

    elif score >= 1:
        return (
            "HƠI TÍCH CỰC: Có tín hiệu cải thiện nhưng chưa đủ mạnh "
            "để xác nhận xu hướng tăng bền vững."
        )

    elif score > -1:
        return (
            "TRUNG TÍNH: Các tín hiệu chưa đồng thuận. "
            "Ưu tiên quan sát, chưa vội mở vị thế mới."
        )

    elif score > -3:
        return (
            "SUY YẾU: Động lượng hoặc xu hướng đang kém thuận lợi. "
            "Thận trọng với các điểm mua mới."
        )

    elif score > -5:
        return (
            "TIÊU CỰC: Áp lực kỹ thuật đáng chú ý. "
            "Theo dõi hỗ trợ và kiểm soát tỷ trọng."
        )

    else:
        return (
            "RẤT TIÊU CỰC: Nhiều tín hiệu bất lợi cùng xuất hiện. "
            "Ưu tiên bảo toàn vốn, chưa nên mua mới."
        )
