import streamlit as st
import pandas as pd
import requests
import json
import re
from datetime import datetime
from supabase import create_client, Client
from API import goi_api
from logic_xuly import doc_danh_muc, tinh_toan_don_hang

# ==========================================
# CẤU HÌNH HỆ THỐNG & TÙY CHỈNH THEME
# ==========================================
st.set_page_config(layout="wide", page_title="Hệ thống B2B OMS")

st.markdown("""
<style>
h1, h2, h3, h4, h5, h6 { color: #1a7b45 !important; font-weight: bold !important; }
div.stButton > button[kind="primary"] {
    background-color: #28a745 !important; color: white !important;
    border-color: #28a745 !important; font-weight: 600 !important;
    border-radius: 8px !important;
}
div.stButton > button[kind="primary"]:hover {
    background-color: #218838 !important; border-color: #1e7e34 !important;
    box-shadow: 0 4px 8px rgba(40,167,69,0.3) !important;
}
[data-testid="stDataFrame"] {
    border-radius: 10px !important;
    overflow: hidden !important;
}
</style>
""", unsafe_allow_html=True)

LINK_SHEET_DANH_MUC = "https://docs.google.com/spreadsheets/d/1jSW3RiwM7GPKpwVG1C_AErR3EY6RXXFaOPJzP9QH9fQ/edit?gid=0#gid=0"
LINK_MAKE_WEBHOOK = "https://hook.eu1.make.com/dcne517s4e17rm7t2jzkip87f34w9og7"

# ==========================================
# CÁC HÀM VALIDATION NHẬP LIỆU
# ==========================================
def kiem_tra_sdt(sdt):
    """
    Kiểm tra SĐT: Bắt đầu bằng số 0 và có đúng 10 chữ số.
    """
    return bool(re.match(r"^0\d{9}$", sdt.strip()))

# ==========================================
# SUPABASE KẾT NỐI
# ==========================================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    SUPABASE_URL = ""
    SUPABASE_KEY = ""

@st.cache_resource
def init_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# ==========================================
# SESSION STATE & LOGIN
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if 'processing' not in st.session_state:
    st.session_state.processing = False

def login(username, password):
    if not supabase:
        st.error("Chưa cấu hình thông tin bảo mật Supabase.")
        return False
    try:
        res = supabase.table("Users").select("*").eq("username", username).eq("password", password).execute()
        if len(res.data) > 0:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"Đăng nhập thành công: {username}")
            st.rerun()
        else:
            st.error("Mật khẩu hoặc tên đăng nhập không chính xác.")
    except Exception as e:
        st.error(f"Lỗi kết nối máy chủ Supabase: {e}")

def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.processing = False
    if "table_data" in st.session_state:
        del st.session_state.table_data
    st.rerun()

# --- MÀN HÌNH LOGIN ---
if not st.session_state.logged_in:
    st.title("ĐĂNG NHẬP HỆ THỐNG OMS B2B")
    with st.form("login_form"):
        user_input = st.text_input("Tên đăng nhập", max_chars=50)
        pass_input = st.text_input("Mật khẩu", type="password", max_chars=50)
        if st.form_submit_button("Đăng nhập"):
            login(user_input, pass_input)
    st.stop()

# ==========================================
# GIAO DIỆN CHÍNH (SAU KHI LOGIN)
# ==========================================
st.sidebar.title(f"Tài khoản: {st.session_state.username}")
if st.sidebar.button("Đăng xuất"):
    logout()

st.title("HỆ THỐNG QUẢN LÝ ĐƠN HÀNG B2B (OMS)")

DANH_MUC_DB = doc_danh_muc(LINK_SHEET_DANH_MUC)
if DANH_MUC_DB is None:
    st.error("Không thể tải danh mục sản phẩm từ Google Sheets. Vui lòng kiểm tra lại kết nối mạng.")
    st.stop()

danh_sach_sku_display = []
if DANH_MUC_DB:
    for sku, info in DANH_MUC_DB.items():
        danh_sach_sku_display.append(f"{sku} | {info['ten']}")

# Rút trích danh bạ cá nhân hóa theo sales_username
@st.cache_data
def get_customers(username):
    if not supabase or not username: return {}
    try:
        res = supabase.table("Customers").select("*").eq("sales_username", username).execute()
        return {item['ten_khach']: item for item in res.data}
    except Exception:
        return {}

DANH_BA = get_customers(st.session_state.username)

# ==========================================
# BƯỚC 1: THÔNG TIN ĐƠN HÀNG (MULTI-TENANT & SIẾT VALIDATION)
# ==========================================
st.subheader("Bước 1: Thông tin đơn hàng")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.text_input("Nhân viên kinh doanh:", value=st.session_state.username, disabled=True)
    sales_name = st.session_state.username

with col2:
    danh_sach_ten = ["--- Chọn khách hàng ---", "+ Thêm khách hàng mới"] + list(DANH_BA.keys())
    chon_khach = st.selectbox("Khách hàng:", danh_sach_ten)

# Xử lý Thêm khách hàng mới
if chon_khach == "+ Thêm khách hàng mới":
    with col2:
        new_ten = st.text_input("Tên khách hàng mới:", max_chars=50)
    with col3:
        new_sdt = st.text_input("Số điện thoại:", max_chars=10)
    with col4:
        new_dc = st.text_input("Địa chỉ giao hàng:", max_chars=200)
    with col2:
        if st.button("Lưu khách hàng", type="primary"):
            new_ten_clean = new_ten.strip()
            new_sdt_clean = new_sdt.strip()
            new_dc_clean = new_dc.strip()

            if len(new_ten_clean) == 0 or len(new_sdt_clean) == 0 or len(new_dc_clean) == 0:
                st.warning("Vui lòng nhập đầy đủ Tên, Số điện thoại và Địa chỉ (Không được để toàn khoảng trắng).")
            elif not kiem_tra_sdt(new_sdt_clean):
                st.warning("Số điện thoại không hợp lệ (Phải bắt đầu bằng số 0 và có đúng 10 chữ số).")
            elif new_ten_clean in DANH_BA:
                st.warning("Tên khách hàng này đã tồn tại trong danh bạ của bạn, vui lòng chọn từ danh sách hoặc đặt tên khác.")
            elif supabase:
                try:
                    supabase.table("Customers").insert({
                        "ten_khach": new_ten_clean,
                        "sdt": new_sdt_clean,
                        "dia_chi": new_dc_clean,
                        "sales_username": st.session_state.username
                    }).execute()
                    st.cache_data.clear()
                    st.success("Đã thêm thông tin khách hàng mới.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi lưu dữ liệu khách hàng: {e}")

    ten_khach, sdt_khach, dc_khach = "", "", ""

elif chon_khach != "--- Chọn khách hàng ---":
    khach_info = DANH_BA[chon_khach]
    ten_khach = chon_khach
    khach_id = khach_info.get('id')

    with col2:
        with st.popover("Xóa khách hàng"):
            st.warning(f"Bạn có chắc muốn xóa khách hàng '{ten_khach}'?")
            if st.button("Xác nhận xóa vĩnh viễn", type="primary"):
                if supabase and khach_id:
                    try:
                        supabase.table("Customers").delete().eq("id", khach_id).execute()
                        st.cache_data.clear()
                        st.success("Đã xóa khách hàng thành công.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi xóa: {e}")

    with col3:
        edit_sdt = st.text_input("Số điện thoại:", value=khach_info.get('sdt', ''), max_chars=10)
    with col4:
        edit_dc = st.text_input("Địa chỉ giao hàng:", value=khach_info.get('dia_chi', ''), max_chars=200)
    with col2:
        if st.button("Cập nhật thông tin", type="primary"):
            edit_sdt_clean = edit_sdt.strip()
            edit_dc_clean = edit_dc.strip()

            if len(edit_sdt_clean) == 0 or len(edit_dc_clean) == 0:
                st.warning("Số điện thoại và Địa chỉ không được để trống.")
            elif not kiem_tra_sdt(edit_sdt_clean):
                st.warning("Số điện thoại không hợp lệ (Phải bắt đầu bằng số 0 và có đúng 10 chữ số).")
            elif supabase and khach_id:
                try:
                    supabase.table("Customers").update({
                        "sdt": edit_sdt_clean,
                        "dia_chi": edit_dc_clean
                    }).eq("id", khach_id).execute()
                    st.cache_data.clear()
                    st.success(f"Đã cập nhật thông tin cho khách hàng {ten_khach}.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi cập nhật thông tin: {e}")

    sdt_khach = edit_sdt
    dc_khach = edit_dc
else:
    ten_khach, sdt_khach, dc_khach = "", "", ""
    with col3:
        st.text_input("Số điện thoại:", disabled=True)
    with col4:
        st.text_input("Địa chỉ giao hàng:", disabled=True)

# ==========================================
# GỌI AI TRÍCH XUẤT ZALO
# ==========================================
zalo_text = st.text_area("Nội dung tin nhắn đặt hàng (Zalo / SMS):", height=100, max_chars=3000)

if st.button("BÓC TÁCH DỮ LIỆU ĐƠN HÀNG", type="primary", disabled=st.session_state.processing):
    if chon_khach in ["--- Chọn khách hàng ---", "+ Thêm khách hàng mới"]:
        st.warning("Vui lòng chọn hoặc lưu thông tin khách hàng.")
    elif not zalo_text or len(zalo_text.strip()) == 0:
        st.warning("Vui lòng nhập nội dung tin nhắn đặt hàng (Không được để toàn khoảng trắng).")
    else:
        st.session_state.processing = True
        try:
            with st.spinner("Đang trích xuất dữ liệu từ tin nhắn..."):
                success, result = goi_api(zalo_text, sales_name, ten_khach, sdt_khach, dc_khach)
                if success:
                    if not result:
                        st.warning("Không tìm thấy sản phẩm hợp lệ trong tin nhắn. Vui lòng kiểm tra lại nội dung.")
                    else:
                        for row in result:
                            raw_sku = str(row.get('Mã SKU', '')).strip()
                            if raw_sku in DANH_MUC_DB:
                                row['Mã SKU'] = f"{raw_sku} | {DANH_MUC_DB[raw_sku]['ten']}"
                        st.session_state.table_data = result
                        st.success("Đã trích xuất dữ liệu đơn hàng thành công. Vui lòng kiểm tra bảng bên dưới.")
                else:
                    st.error(result)
        finally:
            st.session_state.processing = False

st.divider()
st.subheader("Bước 2: Kiểm tra & Cập nhật dữ liệu")

# ==========================================
# BẢNG CHỈNH SỬA & DUYỆT ĐƠN (KHOÁ NGUYÊN NGHĨA CHO SỐ LƯỢNG)
# ==========================================
if "table_data" in st.session_state and st.session_state.table_data:
    df = pd.DataFrame(st.session_state.table_data)
    ai_nhap_vao = df['Mã SKU'].dropna().unique().tolist()
    danh_sach_dropdown_hon_hop = list(dict.fromkeys(danh_sach_sku_display + ai_nhap_vao))

    config = {
        "Mã SKU": st.column_config.SelectboxColumn(
            "Mã SKU | Tên Sản Phẩm",
            help="Bấm vào để chọn sản phẩm chuẩn từ danh mục",
            width="large",
            options=danh_sach_dropdown_hon_hop,
            required=True
        ),
        "Số Lượng": st.column_config.NumberColumn(
            "Số Lượng",
            help="Nhập số lượng sản phẩm (bắt buộc số nguyên >= 1)",
            min_value=1,
            step=1,
            required=True
        )
    }

    edited_df = st.data_editor(
        df, num_rows="dynamic", use_container_width=True,
        hide_index=True, column_config=config
    )

    if st.button("XÁC NHẬN & PHÊ DUYỆT ĐƠN HÀNG", type="primary", use_container_width=True, disabled=st.session_state.processing):
        st.session_state.processing = True
        try:
            # Gọt sạch phần Tên Sản Phẩm khỏi cột Mã SKU trong edited_df, chỉ giữ lại Mã SKU thuần túy trước khi xử lý
            if 'Mã SKU' in edited_df.columns:
                edited_df['Mã SKU'] = edited_df['Mã SKU'].astype(str).apply(
                    lambda x: x.split('|')[0].strip() if '|' in str(x) else str(x).strip()
                )

            with st.spinner("Đang kiểm tra dữ liệu giá và tồn kho..."):
                if hasattr(doc_danh_muc, 'clear'):
                    doc_danh_muc.clear()
                DANH_MUC_DB_MOI = doc_danh_muc(LINK_SHEET_DANH_MUC)

                if DANH_MUC_DB_MOI is None:
                    st.error("Không thể tải danh mục sản phẩm từ Google Sheets. Vui lòng kiểm tra lại kết nối mạng.")
                    st.stop()

                hop_le, df_da_tinh, tong_tien, loi_nhan = tinh_toan_don_hang(edited_df, DANH_MUC_DB_MOI)

                if not hop_le:
                    st.error(f"TỪ CHỐI PHÊ DUYỆT ĐƠN HÀNG: {loi_nhan}")
                else:
                    final_payload = df_da_tinh.to_dict(orient="records")
                    for item in final_payload:
                        item['Khuyến Mãi'] = str(item['Khuyến Mãi']).replace('.', ',')

                    try:
                        response = requests.post(LINK_MAKE_WEBHOOK, json=final_payload, timeout=10)
                        if response.status_code == 200:
                            st.success("ĐƠN HÀNG ĐÃ ĐƯỢC XÁC NHẬN VÀ LƯU VÀO HỆ THỐNG.")
                            st.write(f"**Khách hàng:** {ten_khach}")
                            
                            bill_columns = ['Tên Sản Phẩm', 'Số Lượng', 'Đơn Giá', 'Khuyến Mãi', 'Thành Tiền']
                            st.table(df_da_tinh[bill_columns].style.format(
                                {"Đơn Giá": "{:,.0f}", "Khuyến Mãi": "{:.0%}", "Thành Tiền": "{:,.0f}"}
                            ))
                            st.markdown(f"### TỔNG GIÁ TRỊ ĐƠN HÀNG: {tong_tien:,.0f} VNĐ")
                            st.markdown("---")

                            st.info("**BÁO CÁO TỒN KHO DỰ KIẾN SAU XUẤT KHO:**")
                            for _, row in df_da_tinh.iterrows():
                                sku = str(row['Mã SKU']).strip()
                                so_luong = int(row['Số Lượng'])
                                if sku in DANH_MUC_DB_MOI:
                                    ton_cu = DANH_MUC_DB_MOI[sku]['ton']
                                    ton_moi = ton_cu - so_luong
                                    st.write(f"- Mã **{sku}** ({DANH_MUC_DB_MOI[sku]['ten']}): Tồn ban đầu ({ton_cu}) $\\rightarrow$ **Tồn còn lại: {ton_moi}**")

                            if "table_data" in st.session_state:
                                del st.session_state.table_data
                        else:
                            st.error(f"Lỗi phản hồi hệ thống (mã {response.status_code}): {response.text}")
                    except requests.exceptions.Timeout:
                        st.error("Lỗi kết nối: Yêu cầu gửi đơn hàng sang Make.com bị quá thời gian (Timeout). Vui lòng thử lại.")
                    except Exception as e:
                        st.error(f"Lỗi kết nối máy chủ: {e}")
        finally:
            st.session_state.processing = False