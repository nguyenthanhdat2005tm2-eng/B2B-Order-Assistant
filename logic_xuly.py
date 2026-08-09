import pandas as pd
import re
import streamlit as st

@st.cache_data(ttl=60)
def doc_danh_muc(url_sheet):
    """
    Hàm lụm giá siêu cấp: Lấy thêm Tên Sản Phẩm để in Hóa Đơn.
    """
    if not url_sheet:
        return None
    try:
        sheet_id = re.search(r'/d/([a-zA-Z0-9-_]+)', url_sheet).group(1)
        gid_match = re.search(r'[?#&]gid=([0-9]+)', url_sheet)
        gid = gid_match.group(1) if gid_match else "0"
        
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        
        try:
            df_dm = pd.read_csv(csv_url)
        except Exception as e:
            st.error(f"❌ Bắt được lỗi Tải File từ Google: {e}")
            return None
            
        db = {}
        
        sku_col = next((c for c in df_dm.columns if 'SKU' in str(c).upper()), None)
        ten_col = next((c for c in df_dm.columns if 'TÊN' in str(c).upper() or 'TEN' in str(c).upper()), None)
        gia_col = next((c for c in df_dm.columns if 'GIÁ' in str(c).upper() or 'GIA' in str(c).upper()), None)
        km_col = next((c for c in df_dm.columns if 'KHUYẾN MÃI' in str(c).upper() or 'KM' in str(c).upper()), None)
        
        ton_cols = [c for c in df_dm.columns if 'TỒN' in str(c).upper() or 'TON' in str(c).upper()]
        ton_col = None
        if ton_cols:
            ton_col = next((c for c in ton_cols if 'HIỆN TẠI' in str(c).upper()), ton_cols[-1])
        
        if not sku_col:
            st.error(f"❌ Bảng của sếp không có cột nào chứa chữ 'SKU'.")
            return None

        for index, row in df_dm.iterrows():
            sku = str(row.get(sku_col, '')).strip()
            if not sku or sku == 'nan': continue
            
            ten_sp = str(row.get(ten_col, '')).strip() if ten_col else sku
            
            gia_raw = str(row.get(gia_col, '0')).replace(',', '').replace('.', '') if gia_col else '0'
            gia = int(pd.to_numeric(gia_raw, errors='coerce')) if pd.notnull(gia_raw) else 0
            
            km_raw = str(row.get(km_col, '0')).replace('%', '').strip() if km_col else '0'
            try: km = float(km_raw)
            except: km = 0
                
            ton_raw = str(row.get(ton_col, '0')).replace(',', '').replace('.', '') if ton_col else '0'
            ton = int(pd.to_numeric(ton_raw, errors='coerce')) if pd.notnull(ton_raw) else 0
            
            db[sku] = {'ten': ten_sp, 'gia': gia, 'km': km, 'ton': ton}
            
        return db
        
    except Exception as e:
        st.error(f"❌ Lỗi xử lý hệ thống: {e}")
        return None


def tinh_toan_don_hang(df_don_hang, danh_muc_db):
    tong_tien = 0
    
    # Tạo sẵn cột Tên Sản Phẩm để lát in Bill
    if 'Tên Sản Phẩm' not in df_don_hang.columns:
        df_don_hang['Tên Sản Phẩm'] = ""
    
    for index, row in df_don_hang.iterrows():
        sku = str(row.get('Mã SKU', '')).strip()
        so_luong = int(row.get('Số Lượng', 0))
        
        if sku in danh_muc_db:
            gia = danh_muc_db[sku]['gia']
            km = danh_muc_db[sku]['km']
            ton_kho_hien_tai = danh_muc_db[sku]['ton']
            ten_sp = danh_muc_db[sku]['ten']
            
            if so_luong > ton_kho_hien_tai:
                loi_nhan = f"Mã sản phẩm '{sku}' trong kho chỉ còn {ton_kho_hien_tai} cái. Khách đặt {so_luong} là không đủ hàng! Vui lòng sửa lại số lượng."
                return False, df_don_hang, 0, loi_nhan
            
            thanh_tien = int(so_luong * gia * (1 - km/100))
            
            df_don_hang.at[index, 'Tên Sản Phẩm'] = ten_sp
            df_don_hang.at[index, 'Đơn Giá'] = gia
            # CHUYỂN THÀNH SỐ THẬP PHÂN ĐỂ SHEET TỰ HIỂU (Ví dụ: 0.15)
            df_don_hang.at[index, 'Khuyến Mãi'] = km / 100 
            df_don_hang.at[index, 'Thành Tiền'] = thanh_tien
            tong_tien += thanh_tien
        else:
            loi_nhan = f"Mã SKU '{sku}' không tồn tại trong danh mục Google Sheets! Vui lòng chọn lại mã SKU chuẩn từ danh sách."
            return False, df_don_hang, 0, loi_nhan
            
    return True, df_don_hang, tong_tien, "OK"