# 🔍 CYB SEARCH - Hệ Thống Tra Cứu Kết Quả HSG Tỉnh Lào Cai

Hệ thống tra cứu, xếp hạng và thống kê kết quả kỳ thi Học sinh giỏi (HSG) cấp tỉnh Lào Cai. Được phát triển để cung cấp trải nghiệm tra cứu nhanh chóng, chính xác và trực quan.

## ✨ Tính năng nổi bật

- **Tra cứu SBD/Họ tên**: Tìm kiếm nhanh chóng kết quả thi của thí sinh.
- **Bảng xếp hạng (Ranking)**: Xếp hạng chi tiết theo từng môn học và trường học.
- **Thống kê dữ liệu**: Tổng quan về số lượng thí sinh, môn thi và phổ điểm.
- **Live Counter**: Theo dõi số lượng người đang truy cập hệ thống theo thời gian thực (WebSockets).
- **Giao diện hiện đại**: Thiết kế Glassmorphism chuyên nghiệp, thân thiện với người dùng.

## 🛠 Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy
- **Database**: SQLite (dữ liệu được import tự động từ CSV)
- **Frontend**: HTML5, Vanilla CSS, Javascript (ES6+)
- **Real-time**: WebSockets (FastAPI)
- **Deployment**: Hỗ trợ chạy local hoặc Vercel

## 🚀 Hướng dấn cài đặt (Local)

### 1. Cài đặt Python
Đảm bảo bạn đã cài đặt Python 3.9+.

### 2. Cài đặt thư viện
Mở terminal tại thư mục dự án và chạy:
```bash
pip install -r requirements.txt
```

### 3. Khởi chạy hệ thống
Chạy lệnh sau để khởi động server:
```bash
python app.py
```
Hệ thống mặc định chạy tại: **http://localhost:3434**

## 📂 Cấu trúc dữ liệu
- Dữ liệu đầu vào: `diemthihsgtinh.csv`
- Database: `hsgtinh.db` (Tự động tạo và import khi khởi chạy lần đầu)

## 👨‍💻 Phát triển bởi
**Hòa Quang Thắng**
- Học sinh trường THPT Chuyên Nguyễn Tất Thành - Lào Cai.
- GitHub: [HoaThang34](https://github.com/HoaThang34)

---
*Dự án được xây dựng với mục đích hỗ trợ cộng đồng học sinh Lào Cai tra cứu kết quả thi tiện lợi hơn.*
