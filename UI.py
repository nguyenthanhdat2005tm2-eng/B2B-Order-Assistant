import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
from supabase import create_client, Client
from API import goi_api
from logic_xuly import doc_danh_muc, tinh_toan_don_hang

# ==========================================
# CẤU HÌNH HỆ THỐNG & GIAO DIỆN XANH LÁ
# ==========================================
st.set_page_config(layout="wide", page_title="OMS B2B - Picare")

st.markdown("""
    <style>
    h1, h2, h3, h4, h5, h6 {
        color: #1a7b45 !important;
        font-weight: bold !important;
    }
    div.stButton > button[kind="primary"] {
        background-color: #28a745 !important;
        color: white !important;
        border-color: #28a745 !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        transition: all 0.3s ease;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #218838 !important;
        border-color: #1e7e34 !important;
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

# KẾT NỐI SUPABASE TỪ ST.SECRETS
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
# Tự động duy trì phiên đăng nhập khi F5 / Reload trang bằng Query Params
if "user" in st.query_params and not st.session_state.get("logged_in"):
    saved_user = st.query_params["user"]
    if saved_user:
        st.session_state.logged_in = True
        st.session_state.username = saved_user

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

def login(username, password):
    if not supabase:
        st.error("Chưa cấu hình Supabase URL/Key trong hệ thống!")
        return False
        
    response = supabase.table("Users").select("*").eq("username", username).eq("password", password).execute()
    if len(response.data) > 0:
        st.session_state.logged_in = True
        st.session_state.username = username
        st.query_params["user"] = username # Lưu phiên làm việc vào URL
        st.success(f"Đăng nhập thành công: {username}")
        st.rerun()
    else:
        st.error("Tên đăng nhập hoặc mật khẩu không chính xác.")

def logout():
    st.query_params.clear() # Xóa phiên làm việc trên URL
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()

# --- MÀN HÌNH LOGIN ---
if not st.session_state.logged_in:
    st.title("ĐĂNG NHẬP HỆ THỐNG OMS B2B")
    with st.form("login_form"):
        user_input = st.text_input("Tên đăng nhập")
        pass_input = st.text_input("Mật khẩu", type="password")
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
danh_sach_sku_chuan = list(DANH_MUC_DB.keys()) if DANH_MUC_DB else []

@st.cache_data(ttl=30)
def get_customers():
    if not supabase: return {}
    res = supabase.table("Customers").select("*").execute()
    return {item['ten_khach']: item for item in res.data}

DANH_BA = get_customers()

st.subheader("Bước 1: Thông tin đơn hàng")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.text_input("Nhân viên kinh doanh:", value=st.session_state.username, disabled=True)
    sales_name = st.session_state.username

with col2:
    danh_sach_ten = ["--- Chọn khách hàng ---", "+ Thêm khách hàng mới"] + list(DANH_BA.keys())
    chon_khach = st.selectbox("Khách hàng:", danh_sach_ten)

if chon_khach == "+ Thêm khách hàng mới":
    with col2:
        new_ten = st.text_input("Tên khách hàng mới:")
    with col3:
        new_sdt = st.text_input("Số điện thoại:")
    with col4:
        new_dc = st.text_input("Địa chỉ giao hàng:")
    with col2:
        if st.button("Lưu khách hàng", type="primary"):
            if new_ten and supabase:
                supabase.table("Customers").insert({
                    "ten_khach": new_ten,
                    "sdt": new_sdt,
                    "dia_chi": new_dc
                }).execute()
                st.cache_data.clear()
                st.success("Đã lưu thông tin khách hàng mới.")
                st.rerun()
            else:
                st.warning("Vui lòng nhập tên khách hàng.")
    ten_khach, sdt_khach, dc_khach = "", "", ""

elif chon_khach != "--- Chọn khách hàng ---":
    khach_info = DANH_BA[chon_khach]
    ten_khach = chon_khach
    khach_id = khach_info.get('id')
    
    with col2:
        if st.button("Xóa khách hàng") and supabase and khach_id:
            supabase.table("Customers").delete().eq("id", khach_id).execute()
            st.cache_data.clear()
            st.rerun()
            
    with col3:
        edit_sdt = st.text_input("Số điện thoại:", value=khach_info.get('sdt', ''))
    with col4:
        edit_dc = st.text_input("Địa chỉ giao hàng:", value=khach_info.get('dia_chi', ''))
        
    sdt_khach = edit_sdt
    dc_khach = edit_dc
    
    if (edit_sdt != khach_info.get('sdt', '') or edit_dc != khach_info.get('dia_chi', '')) and supabase and khach_id:
        supabase.table("Customers").update({
            "sdt": edit_sdt,
            "dia_chi": edit_dc
        }).eq("id", khach_id).execute()
        st.cache_data.clear()
        st.toast(f"Đã cập nhật thông tin cho khách hàng {ten_khach}.")
else:
    ten_khach, sdt_khach, dc_khach = "", "", ""
    with col3:
        st.text_input("Số điện thoại:", disabled=True)
    with col4:
        st.text_input("Địa chỉ giao hàng:", disabled=True)


# ==========================================
# GỌI AI TRÍCH XUẤT ZALO
# ==========================================
zalo_text = st.text_area("Nội dung tin nhắn đặt hàng (Zalo / SMS):", height=100)

if st.button("BÓC TÁCH DỮ LIỆU ĐƠN HÀNG", type="primary"):
    if chon_khach == "--- Chọn khách hàng ---" or chon_khach == "+ Thêm khách hàng mới":
        st.warning("Vui lòng chọn hoặc lưu thông tin khách hàng.")
    elif not zalo_text:
        st.warning("Vui lòng nhập nội dung tin nhắn đặt hàng.")
    else:
        with st.spinner("Đang trích xuất dữ liệu từ tin nhắn..."):
            success, result = goi_api(zalo_text, sales_name, ten_khach, sdt_khach, dc_khach)
            if success:
                st.session_state.table_data = result
                st.success("Đã trích xuất dữ liệu đơn hàng thành công. Vui lòng kiểm tra bảng bên dưới.")
            else:
                st.error(result)

st.divider()
st.subheader("Bước 2: Kiểm tra & Cập nhật dữ liệu")

if "table_data" in st.session_state and st.session_state.table_data:
    df = pd.DataFrame(st.session_state.table_data)
    
    ai_nhap_vao = df['Mã SKU'].dropna().unique().tolist()
    danh_sach_dropdown_hon_hop = list(set(danh_sach_sku_chuan + ai_nhap_vao))

    config = {
        "Mã SKU": st.column_config.SelectboxColumn(
            "Mã SKU",
            help="Bấm vào để chọn mã sản phẩm chuẩn",
            width="medium",
            options=danh_sach_dropdown_hon_hop, 
            required=True
        )
    }
    
    edited_df = st.data_editor(
        df, num_rows="dynamic", use_container_width=True, hide_index=True, column_config=config 
    )
    
    if st.button("XÁC NHẬN & PHÊ DUYỆT ĐƠN HÀNG", type="primary", use_container_width=True):
        with st.spinner("Đang kiểm tra dữ liệu giá và tồn kho..."):
            if hasattr(doc_danh_muc, 'clear'):
                doc_danh_muc.clear()
            DANH_MUC_DB_MOI = doc_danh_muc(LINK_SHEET_DANH_MUC)
            
            hop_le, df_da_tinh, tong_tien, loi_nhan = tinh_toan_don_hang(edited_df, DANH_MUC_DB_MOI)
            
            if not hop_le:
                st.error(f"TỪ CHỐI PHÊ DUYỆT ĐƠN HÀNG: {loi_nhan}")
            else:
                final_payload = df_da_tinh.to_dict(orient="records")
                for item in final_payload:
                    item['Khuyến Mãi'] = str(item['Khuyến Mãi']).replace('.', ',')
                
                try:
                    response = requests.post(LINK_MAKE_WEBHOOK, json=final_payload)
                    if response.status_code == 200:
                        st.success("ĐƠN HÀNG ĐÃ ĐƯỢC XÁC NHẬN VÀ LƯU VÀO HỆ THỐNG.")
                        st.write(f"**Khách hàng:** {ten_khach}")
                        
                        bill_columns = ['Tên Sản Phẩm', 'Số Lượng', 'Đơn Giá', 'Khuyến Mãi', 'Thành Tiền']
                        st.table(df_da_tinh[bill_columns].style.format({"Đơn Giá": "{:,.0f}", "Khuyến Mãi": "{:.0%}", "Thành Tiền": "{:,.0f}"}))
                        st.markdown(f"### TỔNG GIÁ TRỊ ĐƠN HÀNG: {tong_tien:,.0f} VNĐ")
                        st.markdown("---")

                        st.info("**BÁO CÁO TỒN KHO DỰ KIẾN SAU XUẤT KHO:**")
                        for index, row in df_da_tinh.iterrows():
                            sku = str(row['Mã SKU']).strip()
                            so_luong = int(row['Số Lượng'])
                            if sku in DANH_MUC_DB_MOI:
                                ton_cu = DANH_MUC_DB_MOI[sku]['ton']
                                ton_moi = ton_cu - so_luong
                                st.write(f"- Mã **{sku}**: Tồn ban đầu ({ton_cu}) $\\rightarrow$ **Tồn còn lại: {ton_moi}**")
                    else:
                        st.error(f"Lỗi phản hồi hệ thống: {response.text}")
                except Exception as e:
                    st.error(f"Lỗi kết nối máy chủ: {e}")