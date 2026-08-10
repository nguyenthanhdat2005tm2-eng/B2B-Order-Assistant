import json
import re
import streamlit as st
from datetime import datetime
from google import genai
import time

try:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    MY_API_KEY = ""

def goi_api(tin_nhan_zalo, sales, ten_khach, sdt, dia_chi, max_retries=2):
    """
    Gọi Gemini, có retry và validate dữ liệu JSON đầu ra.
    Trả về (success, data/error_message)
    """
    if not MY_API_KEY:
        return False, "Chưa cấu hình GEMINI_API_KEY trong Secrets!"

    now = datetime.now()
    thoi_gian_chuan = now.strftime("%d/%m/%Y %H:%M")
    ma_don_chuan = f"DH-{now.strftime('%y%m%d-%H%M%S')}"

    prompt = f"""
Bạn là hệ thống xử lý dữ liệu. Hãy đọc tin nhắn Zalo và tách ra danh sách các món hàng.

THÔNG TIN CỐ ĐỊNH (Bắt buộc chép y nguyên vào tất cả các dòng sản phẩm):
- "Mã Đơn": "{ma_don_chuan}"
- "Thời Gian": "{thoi_gian_chuan}"
- "Sales": "{sales}"
- "Tên Khách Hàng": "{ten_khach}"
- "SĐT": "{sdt}"
- "Địa Chỉ": "{dia_chi}"

TIN NHẮN ĐẶT HÀNG:
"{tin_nhan_zalo}"

YÊU CẦU ĐẦU RA BẮT BUỘC:
Trả về MỘT MẢNG JSON DUY NHẤT `[...]`. Mỗi phần tử trong mảng là 1 món hàng.
Phải chứa ĐÚNG 8 trường sau, theo đúng thứ tự:

"Mã Đơn": (lấy từ thông tin cố định)
"Thời Gian": (lấy từ thông tin cố định)
"Sales": (lấy từ thông tin cố định)
"Tên Khách Hàng": (lấy từ thông tin cố định)
"SĐT": (lấy từ thông tin cố định)
"Địa Chỉ": (lấy từ thông tin cố định)
"Mã SKU": (Trích xuất NGUYÊN VĂN từ ngữ chỉ sản phẩm hoặc đặc điểm mà khách gọi. TUYỆT ĐỐI KHÔNG tự ý bịa ra mã chuẩn. Ví dụ: khách ghi "chai hủ đỏ", "kcn vạch xanh" thì trích xuất y hệt như vậy).
"Số Lượng": (Số lượng khách đặt, bắt buộc là dạng số nguyên).

Lưu ý: Chỉ trả về mảng JSON nguyên gốc, không thêm bất kỳ văn bản giải thích nào, không bọc bằng markdown json (```json).
"""

    try:
        client = genai.Client(api_key=MY_API_KEY)
    except Exception as e:
        return False, f"Không thể kết nối đến Gemini API Client: {str(e)}"

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            raw_text = response.text.strip()

            # Thử parse trực tiếp
            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError:
                # Nếu lỗi, dùng regex bắt mảng JSON
                json_match = re.search(r'(\[.*\])', raw_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    data = json.loads(json_str)
                else:
                    return False, "Không tìm thấy mảng JSON hợp lệ trong phản hồi từ AI."

            # Kiểm tra data là list
            if not isinstance(data, list):
                return False, "Dữ liệu AI trả về không phải mảng sản phẩm."

            # Validate từng item có đủ trường cần thiết và không bị NULL / rỗng
            required_fields = ["Mã SKU", "Số Lượng"]
            for idx, item in enumerate(data):
                for field in required_fields:
                    val = item.get(field)
                    if field not in item or val is None or str(val).strip() == "" or str(val).strip().lower() in ["null", "none"]:
                        return False, f"Dòng {idx+1} thiếu hoặc rỗng trường '{field}'."
                # Đảm bảo số lượng là int
                try:
                    item["Số Lượng"] = int(float(item["Số Lượng"]))
                except (ValueError, TypeError):
                    return False, f"Dòng {idx+1} có số lượng không hợp lệ: {item.get('Số Lượng', '')}"

            return True, data

        except Exception as e:
            if attempt == max_retries - 1:
                return False, f"Lỗi kết nối dịch vụ AI sau {max_retries} lần thử: {str(e)}"
            time.sleep(1.5 ** attempt)
            continue
            
    return False, "Không thể xử lý yêu cầu qua API Gemini."