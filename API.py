import json
import streamlit as st
from datetime import datetime
from google import genai

try:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    MY_API_KEY = ""

def goi_api(tin_nhan_zalo, sales, ten_khach, sdt, dia_chi):
    try:
        now = datetime.now()
        thoi_gian_chuan = now.strftime("%d/%m/%Y %H:%M") 
        ma_don_chuan = f"DH-{now.strftime('%y%m%d-%H%M%S')}" 
        client = genai.Client(api_key=MY_API_KEY)
        
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
        Phải chứa ĐÚNG các trường sau, theo đúng thứ tự:
        
        "Mã Đơn": (lấy từ thông tin cố định)
        "Thời Gian": (lấy từ thông tin cố định)
        "Sales": (lấy từ thông tin cố định)
        "Tên Khách Hàng": (lấy từ thông tin cố định)
        "SĐT": (lấy từ thông tin cố định)
        "Địa Chỉ": (lấy từ thông tin cố định)
        "Mã SKU": (Chỉ lấy MÃ SẢN PHẨM KHÁCH GỌI, ví dụ EUC-001, LRP-001...)
        "Số Lượng": (Số lượng khách đặt, dạng số nguyên)
        "Đơn Giá": ''
        "Khuyến Mãi": ''
        "Thành Tiền": ''

        Lưu ý: Chỉ trả về mảng JSON, không thêm bất kỳ văn bản giải thích nào.
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        danh_sach_don = json.loads(raw_text.strip())
        
        return True, danh_sach_don
        
    except Exception as e:
        return False, f"Lỗi gọi API: {str(e)}"