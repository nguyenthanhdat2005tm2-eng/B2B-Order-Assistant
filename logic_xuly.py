import pandas as pd
import re
import streamlit as st

@st.cache_data(ttl=60)
def doc_danh_muc(url_sheet):
    """
    Tải danh mục sản phẩm và bảng giá từ Google Sheets.
    Trả về dict hoặc None nếu lỗi.
    """
    if not url_sheet:
        return None
    try:
        sheet_id = re.search(r'/d/([a-zA-Z0-9-_]+)', url_sheet).group(1)
        gid_match = re.search(r'[?#&]gid=([0-9]+)', url_sheet)
        gid = gid_match.group(1) if gid_match else "0"
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

        try:
            df_dm = pd.read_csv(csv_url, encoding='utf-8')
        except UnicodeDecodeError:
            df_dm = pd.read_csv(csv_url, encoding='latin1')
        except Exception as e:
            st.error(f"Lỗi tải dữ liệu từ Google Sheets: {e}")
            return None

        if df_dm.empty:
            st.error("File Google Sheets trống.")
            return None

        # Xác định cột
        sku_col = next((c for c in df_dm.columns if 'SKU' in str(c).upper()), None)
        ten_col = next((c for c in df_dm.columns if 'TÊN' in str(c).upper() or 'TEN' in str(c).upper()), None)
        gia_col = next((c for c in df_dm.columns if 'GIÁ' in str(c).upper() or 'GIA' in str(c).upper()), None)
        km_col = next((c for c in df_dm.columns if 'KHUYẾN MÃI' in str(c).upper() or 'KM' in str(c).upper()), None)
        ton_cols = [c for c in df_dm.columns if 'TỒN' in str(c).upper() or 'TON' in str(c).upper()]
        ton_col = None
        if ton_cols:
            ton_col = next((c for c in ton_cols if 'HIỆN TẠI' in str(c).upper()), ton_cols[-1])

        if not sku_col:
            st.error("Không tìm thấy cột 'SKU' trong Google Sheets.")
            return None

        db = {}
        for index, row in df_dm.iterrows():
            sku = str(row.get(sku_col, '')).strip()
            if not sku or sku == 'nan':
                continue

            ten_sp = str(row.get(ten_col, '')).strip() if ten_col else sku

            # Xử lý giá: loại bỏ dấu phân cách hàng nghìn, chuyển dấu phẩy thập phân thành dấu chấm
            gia_raw = str(row.get(gia_col, '0')).strip()
            gia_clean = gia_raw.replace('.', '').replace(',', '.')
            gia = int(pd.to_numeric(gia_clean, errors='coerce')) if pd.notnull(gia_clean) else 0

            km_raw = str(row.get(km_col, '0')).replace('%', '').strip() if km_col else '0'
            km_raw = km_raw.replace(',', '.').strip()
            try:
                km = float(km_raw)
            except ValueError:
                km = 0.0

            ton_raw = str(row.get(ton_col, '0')).strip()
            ton_clean = ton_raw.replace(',', '').replace('.', '')
            ton = int(pd.to_numeric(ton_clean, errors='coerce')) if pd.notnull(ton_clean) else 0

            db[sku] = {'ten': ten_sp, 'gia': gia, 'km': km, 'ton': ton}

        return db

    except Exception as e:
        st.error(f"Lỗi xử lý hệ thống danh mục: {e}")
        return None


def tinh_toan_don_hang(df_don_hang, danh_muc_db):
    """
    Tính toán chiết khấu, thành tiền và kiểm tra tồn kho.
    Sử dụng round() trước khi ép sang int để tránh hụt tiền do làm tròn số thập phân float.
    """
    if danh_muc_db is None or not isinstance(danh_muc_db, dict):
        return False, df_don_hang, 0, "Danh mục sản phẩm chưa được tải. Vui lòng thử lại."

    if df_don_hang is None or df_don_hang.empty:
        return False, df_don_hang, 0, "Đơn hàng trống! Vui lòng thêm ít nhất một sản phẩm."

    records = df_don_hang.to_dict('records')
    tong_tien = 0

    for idx, item in enumerate(records):
        sku_raw = str(item.get('Mã SKU', '')).strip()
        if '|' in sku_raw:
            sku_code = sku_raw.split('|')[0].strip()
        else:
            sku_code = sku_raw

        if not sku_code or sku_code.lower() == 'none' or sku_code.lower() == 'null':
            return False, df_don_hang, 0, f"Dòng {idx+1}: Mã SKU không được để trống hoặc rỗng."

        try:
            so_luong_raw = str(item.get('Số Lượng', 0)).replace(',', '.').strip()
            so_luong = int(float(so_luong_raw))
        except (ValueError, TypeError):
            so_luong = 0

        if so_luong <= 0:
            return False, df_don_hang, 0, f"Sản phẩm '{sku_code}' có số lượng không hợp lệ (phải lớn hơn 0)."

        if sku_code not in danh_muc_db:
            return False, df_don_hang, 0, f"Mã SKU '{sku_code}' không tồn tại trong danh mục Google Sheets."

        product = danh_muc_db[sku_code]
        gia = product['gia']
        km = product['km']
        ton_kho = product['ton']
        ten_sp = product['ten']

        if so_luong > ton_kho:
            return False, df_don_hang, 0, f"Mã '{sku_code}' ({ten_sp}) chỉ còn {ton_kho} sản phẩm trong kho. Đặt {so_luong} vượt tồn kho!"

        # Dùng round toán học trước khi ép kiểu int để chống hụt 1 đồng
        thanh_tien = int(round(so_luong * gia * (1 - km / 100)))
        tong_tien += thanh_tien

        # Cập nhật lại các trường
        item['Mã SKU'] = sku_code
        item['Tên Sản Phẩm'] = ten_sp
        item['Đơn Giá'] = gia
        item['Khuyến Mãi'] = km / 100
        item['Thành Tiền'] = thanh_tien

    df_da_tinh = pd.DataFrame(records)
    return True, df_da_tinh, tong_tien, "OK"