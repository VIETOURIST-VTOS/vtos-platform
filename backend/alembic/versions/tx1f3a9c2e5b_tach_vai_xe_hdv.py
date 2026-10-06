# -*- coding: utf-8 -*-
"""Tách vai trò `xe_hdv` thành `tai_xe` và `hdv` — Chủ tịch quyết 05/10/2026.

VÌ SAO: một vai trò mang tên "Tài xế & Hướng dẫn viên" gộp hai nghề vào một. Gộp chạy được tám tuần
vì cả hai chỉ ĐỌC việc của chính mình, và hai người chỉ-đọc thì giống nhau. Hết gộp được khi họ bắt
đầu ĐỀ XUẤT: đơn của tài xế đi về Giám đốc đội xe, đơn của hướng dẫn viên đi về Trưởng phòng Hướng
dẫn. Hai tuyến ký, mà một vai trò thì chỉ chở được một tuyến.

CHIA THEO CÁI GÌ: theo `employees.position`, cột HCNS đã giữ sẵn và đã dùng đúng hai mã `tai_xe` và
`hdv` từ trước. Không đoán theo "người này có xe đứng tên không": một tài xế chưa được giao xe vẫn
là tài xế, và một suy luận như thế sẽ gán sai đúng vào những người mới nhất.

BA BẬC, theo thứ tự chắc chắn giảm dần — bậc sau chỉ chạy khi bậc trước không trả lời được:

  1. `employees.position` = 'tai_xe' hoặc 'hdv'  → lấy thẳng.
  2. không có hồ sơ nhân sự, hoặc chức danh khác (ví dụ 'tp'): lấy theo `employees.department`
     ('doi_xe' → tai_xe, 'huong_dan' → hdv).
  3. còn lại → 'tai_xe'.

BẬC 3 KHÔNG PHẢI LÀ MỘT PHỎNG ĐOÁN VỀ NGHỀ NGHIỆP, mà là chỗ đỗ KHÔNG ĐỔI QUYỀN: hôm nay `xe_hdv`
mở đúng hai màn hình `/xe-hdv` và `/doi-mat-khau`, và cả `tai_xe` lẫn `hdv` cũng mở đúng hai màn hình
ấy — nội dung bên trong `/xe-hdv` đi theo DỮ LIỆU của người đăng nhập chứ không theo vai trò. Nên
người rơi vào bậc 3 thấy đúng những gì họ thấy hôm qua. Cái họ chưa có là TUYẾN KÝ đúng, và tuyến ký
là thứ phải có người quyết — nên việc rà lại bậc 3 là việc của HCNS, không phải của bản ghi này.

KHÔNG NÂNG AI LÊN VAI QUẢN LÝ. Trong danh sách hiện có vài người mang vai hiện trường mà chức danh
là cấp trưởng; bản này giữ nguyên phạm vi của họ và KHÔNG tự nâng thành `gd_doi_xe` hay `tp_hd`.
Nâng quyền cho một tài khoản đang chạy là việc phải có chữ ký, không phải việc một migration tự quyết.

ĐỔI NGƯỢC ĐƯỢC KHÔNG: `downgrade` gộp cả hai vai về lại `xe_hdv`. Gộp lại thì KHÔNG khôi phục được
ai từng là tài xế, ai từng là hướng dẫn viên — thông tin ấy vẫn còn nguyên ở `employees.position`,
nên chạy `upgrade` lần nữa sẽ dựng lại đúng như cũ.

Revision ID: tx1f3a9c2e5b
Revises: pv2d8e1a6c4b
"""
import sqlalchemy as sa
from alembic import op

revision = "tx1f3a9c2e5b"
down_revision = "pv2d8e1a6c4b"
branch_labels = None
depends_on = None

# Viết thành ba câu UPDATE riêng thay vì một câu CASE lồng: mỗi câu là một bậc, đọc là thấy bậc nào
# bắt được ai. Câu sau chỉ còn chạm những dòng câu trước chưa đổi, vì điều kiện luôn là role = 'xe_hdv'.
_BAC_1 = """
UPDATE users SET role = (
    SELECT e.position FROM employees e WHERE e.user_id = users.id AND e.position IN ('tai_xe', 'hdv')
)
WHERE role = 'xe_hdv'
  AND EXISTS (SELECT 1 FROM employees e WHERE e.user_id = users.id AND e.position IN ('tai_xe', 'hdv'))
"""

_BAC_2 = """
UPDATE users SET role = (
    SELECT CASE e.department WHEN 'doi_xe' THEN 'tai_xe' ELSE 'hdv' END
    FROM employees e WHERE e.user_id = users.id AND e.department IN ('doi_xe', 'huong_dan')
)
WHERE role = 'xe_hdv'
  AND EXISTS (SELECT 1 FROM employees e WHERE e.user_id = users.id AND e.department IN ('doi_xe', 'huong_dan'))
"""

_BAC_3 = "UPDATE users SET role = 'tai_xe' WHERE role = 'xe_hdv'"


def upgrade() -> None:
    for cau in (_BAC_1, _BAC_2, _BAC_3):
        op.execute(sa.text(cau))


def downgrade() -> None:
    # Gộp lại thành một tên. Không mất thông tin nghề nghiệp: nó nằm ở employees.position, không nằm
    # ở cột này — nên chạy upgrade lần nữa dựng lại đúng như cũ.
    op.execute(sa.text("UPDATE users SET role = 'xe_hdv' WHERE role IN ('tai_xe', 'hdv')"))
