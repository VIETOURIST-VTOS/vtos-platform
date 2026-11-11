# -*- coding: utf-8 -*-
"""VH-19 · BÁO CÁO XE PHẢI GHI TÀI XẾ (thử bản thật 11/11/2026, phiếu #866 xe 50F-017.83).

Phiếu nhập qua cửa bốn bước mà KHÔNG chọn lệnh điều xe thì trước đây không có chỗ chọn tài xế:
chuyến vào sổ với `tai_xe` rỗng, rơi khỏi xếp hạng tài xế, và tờ quyết toán không biết trả cho ai.
"""
import os

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _doc(p):
    with open(os.path.join(GOC, p), encoding="utf-8") as f:
        return f.read()


def test_cua_bon_buoc_co_o_tai_xe_bat_buoc():
    s = _doc("web/components/doixe/BonBuocBaoCaoXe.tsx")
    assert '"/fleet/tai-xe-chon"' in s, "danh sách tài xế phải đọc cửa trong nhóm fleet"
    assert 'dat("driver_id"' in s, "phải có ô chọn tài xế ở bước 1"
    assert '"Chọn tài xế."' in s, "thiếu tài xế thì chưa gửi được"
    assert 'nhan="Tài xế"' in s, "bước kiểm tra phải hiện tài xế"


def test_bang_sua_phieu_sua_duoc_tai_xe():
    s = _doc("web/app/doi-xe/page.tsx")
    assert "driver_id: Number(form.driver_id)" in s
    assert '"/fleet/tai-xe-chon"' in s


def test_danh_sach_chuyen_tra_driver_id():
    s = _doc("backend/app/api/v1/fleet.py")
    assert '"driver_id": t.driver_id, "tai_xe": emps.get(t.driver_id, "")' in s
