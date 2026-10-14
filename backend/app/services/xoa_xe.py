# -*- coding: utf-8 -*-
"""XE-1 — XOÁ MỘT DÒNG XE TẠO NHẦM, và vì sao cửa này mãi tới 14/10/2026 mới có.

Danh mục xe dựng trên một nguyên tắc viết ngay đầu màn hình: *mã xe theo chiếc xe suốt vòng đời,
không theo biển số*. Xe bán đi thì ghi `lifecycle = da_ban` và ngày rời đội — KHÔNG xoá, vì lịch sử
chuyến và chi phí của chiếc ấy phải ở lại. Nên cửa sửa có, cửa đổi biển có, cửa xoá KHÔNG có. Đúng.

Nhưng có một trường hợp nguyên tắc ấy không phủ: **một dòng tạo nhầm, chưa từng là xe thật**. Đo
trên hệ thật 14/10/2026: danh mục có 16 xe, trong đó `51B-123.45` và `51B-678.90` là hai dòng dữ
liệu mẫu. Chúng không bán được (chưa từng mua), không ngừng khai thác được (chưa từng khai thác),
và không có cách nào bỏ đi. Chúng nằm lại trong mẫu số của mọi phép tính đội hình.

Chủ tịch chọn 14/10/2026: viết cửa xoá có hàng rào, thay vì để CNTT xoá thẳng dưới cơ sở dữ liệu
(đi vòng ngoài mọi phép kiểm, không để lại dấu vết ai xoá, lúc nào, vì sao) hoặc khai hai ngày
vào/rời đội KHÔNG CÓ THẬT để hai dòng ấy rớt khỏi mẫu số — tức là ghi một điều sai vào hồ sơ để
lách một cửa còn thiếu.

═══════════════════════════════════════════════════════════════════════════════════════════════
HÀNG RÀO ĐỌC TỪ METADATA, KHÔNG GÕ TAY
═══════════════════════════════════════════════════════════════════════════════════════════════

Đo 14/10/2026: có 14 cột ở 14 bảng khác nhau móc vào `vehicles.id`. Gõ tay 14 cái tên vào đây thì
bảng thứ 15 thêm vào tháng sau LỌT KHỎI phép kiểm — và cửa xoá trở thành cửa tạo dòng mồ côi.

Nên danh sách ấy đọc từ chính `Base.metadata` lúc chạy. Thêm bảng mới có khoá ngoại tới xe là nó
tự được canh, không ai phải nhớ.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.hr import Vehicle

# Bảng ĐI THEO chiếc xe: xoá xe thì xoá cùng, không phải lý do để từ chối.
# Lịch sử biển số là thuộc tính của chính chiếc xe — một chiếc xe chưa từng dùng vẫn có một dòng
# biển đầu tiên, và dòng ấy không phải là "dấu vết hoạt động".
DI_THEO_XE = {"vehicle_plates"}

# Tên dễ đọc cho người, chỉ để in ra. Thiếu tên thì in tên bảng — không chặn.
TEN_BANG = {
    "fleet_trips": "chuyến xe",
    "dispatch_orders": "lệnh điều xe",
    "fleet_maintenance": "phiếu bảo dưỡng",
    "fleet_faults": "báo hỏng",
    "vehicle_documents": "giấy tờ xe",
    "fleet_verifications": "việc xác minh hồ sơ",
    "fleet_period_costs": "chi phí theo kỳ",
    "fleet_external_txns": "giao dịch nguồn ngoài",
    "fleet_settlement_lines": "dòng quyết toán chủ xe",
    "fleet_shared_invoice_lines": "dòng hoá đơn dùng chung",
    "fleet_collaterals": "tài sản thế chấp",
    "fleet_sale_cases": "hồ sơ bán xe",
    "tour_phuong_tien": "phương tiện của tour",
    "vehicle_plates": "lịch sử biển số",
}


def _cot_moc_vao_xe() -> list[tuple]:
    """Mọi (bảng, cột) có khoá ngoại tới `vehicles.id`, đọc từ metadata lúc chạy."""
    ra = []
    for t in Base.metadata.sorted_tables:
        for c in t.columns:
            for fk in c.foreign_keys:
                if fk.column.table.name == "vehicles":
                    ra.append((t, c))
    return ra


def soat(db: Session, v: Vehicle) -> dict:
    """Những gì đang móc vào chiếc xe này. `xoa_duoc` True khi không còn gì ngoài thứ đi theo xe."""
    vuong, theo = [], []
    for t, c in _cot_moc_vao_xe():
        n = db.execute(select(func.count()).select_from(t).where(c == v.id)).scalar() or 0
        if not n:
            continue
        m = {"bang": t.name, "ten": TEN_BANG.get(t.name, t.name), "so_dong": n}
        (theo if t.name in DI_THEO_XE else vuong).append(m)
    vuong.sort(key=lambda x: -x["so_dong"])
    return {
        "xe": v.plate, "ma_xe": v.code, "xoa_duoc": not vuong,
        "vuong": vuong, "se_xoa_theo": theo,
        "noi": ("Chưa từng dùng — xoá được."
                if not vuong else
                "Không xoá được: chiếc này đã có " +
                ", ".join(f"{x['so_dong']} {x['ten']}" for x in vuong) +
                ". Xe đã có lịch sử thì ghi NGỪNG KHAI THÁC kèm ngày rời đội, không xoá — "
                "xoá là mất lịch sử của chính những dòng ấy."),
    }


def xoa(db: Session, v: Vehicle, ly_do: str) -> dict:
    """Xoá một dòng xe chưa từng dùng. Trả về bản ghi ĐÃ XOÁ để nhật ký kiểm toán giữ lại.

    Vì sao bắt buộc lý do: một dòng biến mất khỏi danh mục mà không ai ghi vì sao là một câu hỏi
    không có câu trả lời vào tháng sau. Và vì sao trả về cả nội dung dòng: nhật ký giữ được thì
    xoá nhầm còn dựng lại được bằng tay.
    """
    if not (ly_do or "").strip():
        raise ValueError("Phải ghi lý do xoá.")
    s = soat(db, v)
    if not s["xoa_duoc"]:
        raise ValueError(s["noi"])

    from app.models.fleet import VehiclePlate
    bien = [{"plate": p.plate, "from_date": p.from_date, "to_date": p.to_date, "source": p.source}
            for p in db.execute(select(VehiclePlate).where(VehiclePlate.vehicle_id == v.id)).scalars()]
    truoc = {c.name: getattr(v, c.name) for c in Vehicle.__table__.columns}
    for p in db.execute(select(VehiclePlate).where(VehiclePlate.vehicle_id == v.id)).scalars():
        db.delete(p)
    db.delete(v)
    db.flush()
    return {"da_xoa": truoc, "lich_su_bien": bien, "ly_do": ly_do.strip()[:300]}
