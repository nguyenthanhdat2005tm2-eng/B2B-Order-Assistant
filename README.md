# B2B Order Assistant (Zalo to Google Sheets)
Công cụ nội bộ giúp phòng Sales tối ưu hóa việc nhập liệu thủ công. 
Tự động bóc tách đơn hàng từ tin nhắn Zalo thành bảng dữ liệu chuẩn và lưu vào Google Sheets chỉ trong 3 giây.

## Bài Toán và Giải Pháp
* **Vấn đề:** Bệnh viện, nhà thuốc, Spa đặt đơn hàng qua Zalo rất dài và thường không theo form cố định.
Sales phải gõ lại từng đơn vào Sheets chung. Nếu nhiều đơn và mỗi đơn có nhiều mặt hàng thì:
  * Rất tốn thời gian nhập liệu.
  * Dễ sai sót mã hàng, số lượng.
* **Giải pháp và Quy mô:** Thiết kế tối ưu cho đội ngũ nội bộ từ **10 - 20 nhân viên Sales** hoạt động đồng thời.
  * Chỉ cần Copy tin nhắn đặt đơn từ Zalo dán vào công cụ, AI tự động trích xuất ra dạng bảng để Review và chỉnh sửa nhanh chóng.
  * Bấm "Xác nhận", dữ liệu được tự động ghi thẳng vào Sheets. Đồng thời, hệ thống hiển thị hóa đơn gọn gàng để Sales chụp màn hình gửi chốt đơn với khách ngay lập tức.

## Trải Nghiệm Nhanh
Không cần cài đặt, anh/chị có thể xem ngay kết quả hoặc tự test hệ thống tại đây:
* **Video Demo (2 phút):**  *(<-- Khuyên xem để thấy toàn bộ luồng)*
* **Live Web App:**  | **Tài khoản test:** `admin` - **Pass:** `123`
* **Live Database & Sheet:** [Chèn Link Google Sheets Viewer] *(<-- Test chốt đơn trên Web, dữ liệu sẽ tự động nhảy vào đây)*

## ⚙️ Công Nghệ Sử Dụng (Tech Stack)
* **Frontend:** `Streamlit (Python)` - Xây dựng giao diện nhập liệu nhanh gọn.
* **AI Parser:** `Gemini 2.5 Flash API` - Tối ưu Prompt để chuyển văn bản thô thành dạng bảng.
* **Database:** `Supabase (PostgreSQL)` - Quản lý tài khoản bảo mật và đồng bộ danh bạ khách hàng.
* **Automation:** `Make.com (Webhook)` - Ghi dữ liệu vào `Google Sheets`.
