"""Rà soát cửa nhập 09/9 – chốt chặn cho lỗ hổng đã tìm ra: API có mà màn hình không có.

Bối cảnh: `POST /api/v1/nap-du-lieu/nhap-mot-dong` đã viết từ trước cho cả 27 bộ nạp, nhưng đếm bằng
lệnh trên web/ ra 0 lần gọi – tức là máy làm được mà người dùng không bấm được ở đâu. Trong hơn ba
tuần không ai phát hiện, vì bộ kiểm chỉ hỏi "API chạy không", không hỏi "có ai gọi được nó không".

Bộ kiểm này hỏi câu thứ hai. Nó cố ý đọc THƯ MỤC GIAO DIỆN chứ không đọc bảng khai báo màn hình: bảng
khai báo là bản sao, và một cửa bị bỏ quên thường bị bỏ quên ở cả bản sao lẫn bản gốc.

  C1 có ít nhất một trang giao diện gọi cửa nhập tay một dòng
  C2 trang đó có nút bấm ghi, không phải chỉ nhắc tới đường dẫn trong chú thích
  C3 mọi bộ nạp đều dùng chung cửa này – không bộ nào có đường riêng
  C4 chuỗi bán hàng có cửa SOẠN báo giá, không phải chỉ có cửa xem
"""
import os, sys, pathlib, re

os.environ["DATABASE_URL"] = "sqlite:///./test_cnt.db"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_cnt.db"): os.remove("test_cnt.db")

GOC = pathlib.Path(__file__).resolve().parents[2]
WEB = GOC / "web" / "app"
DUONG_DAN = "nap-du-lieu/nhap-mot-dong"

trang = [p for p in WEB.rglob("page.tsx")]
goi = [p for p in trang if DUONG_DAN in p.read_text(encoding="utf-8")]

# C1
assert goi, ("C1 ĐỎ – không trang nào gọi " + DUONG_DAN + ". Cửa nhập tay của toàn hệ thống đang đóng: "
             "nhân viên chỉ nạp được bằng tệp, sai một dòng phải sửa tệp rồi nạp lại cả lô.")
print(f"C1 XANH – {len(goi)} trang gọi cửa nhập tay: " + ", ".join(str(p.relative_to(WEB)) for p in goi))

# C2 – gọi trong một hàm gửi đi kèm nút bấm, không phải chỉ nằm trong chú thích
co_nut = False
for p in goi:
    s = p.read_text(encoding="utf-8")
    i = s.find(DUONG_DAN)
    quanh = s[max(0, i - 600): i + 600]
    if "method: \"POST\"" in quanh and "<button" in s:
        co_nut = True
assert co_nut, ("C2 ĐỎ – có nhắc tới đường dẫn nhưng không thấy lời gọi POST kèm nút bấm. "
                "Một đường dẫn trong chú thích không phải là một cái cửa.")
print("C2 XANH – có lời gọi POST và có nút bấm trên màn hình")

# C3 – màn hình dựng biểu từ khai báo cột của máy chủ, nên mọi bộ nạp đều đi qua đây
from app.services import intake as IN
assert len(IN.BO_NAP) >= 27, f"C3 ĐỎ – chỉ thấy {len(IN.BO_NAP)} bộ nạp"
thieu_cot = [k for k, v in IN.BO_NAP.items() if not v.get("cot")]
assert not thieu_cot, ("C3 ĐỎ – bộ nạp không khai cột thì màn hình không dựng được biểu nhập tay: "
                       + ", ".join(thieu_cot))
print(f"C3 XANH – {len(IN.BO_NAP)} bộ nạp đều khai đủ cột, dùng chung một biểu")
# C4 – V6 có màn hình xem báo giá từ đầu, nhưng khâu SOẠN thì chưa; chuỗi bán hàng đứt ngay ở khâu
# đầu tiên. Cùng một loại lỗ hổng với C1: đường đi có, cửa vào thì không.
soan = [p for p in trang if 'method: "POST"' in p.read_text(encoding="utf-8")
        and "/ban-hang/bao-gia" in p.read_text(encoding="utf-8")]
assert soan, ("C4 ĐỎ – không màn hình nào gửi POST /ban-hang/bao-gia. Xem được báo giá nhưng không "
              "soạn được báo giá mới thì chuỗi bán hàng đứt ở khâu đầu.")
print("C4 XANH – " + ", ".join(str(p.relative_to(WEB)) for p in soan) + " soạn được báo giá mới")
print("TEST CUA NHAP TAY: XANH")
