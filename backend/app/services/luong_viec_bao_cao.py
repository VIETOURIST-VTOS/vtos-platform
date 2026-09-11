# -*- coding: utf-8 -*-
"""PQ-2 · Trình bày bảng LUỒNG CÔNG VIỆC ra màn hình và ra tệp để ký.

Tách khỏi luong_viec.py theo đúng ranh giới đã có giữa access.py và access_admin.py: tệp kia là
NGUỒN LUẬT, tệp này chỉ đọc và trình bày lại. Nguồn luật không được biết gì về màn hình, nếu không
thì sớm muộn có người sửa luật để cho bảng hiển thị đẹp hơn.

Câu mà trang này phải trả lời được, và hiện chưa trang nào trong VTOS trả lời được:

    Chuyến này ai trình, ai xác nhận, ai duyệt, ai đóng sổ,
    và vì sao người khác không làm thay được?

Với công ty đại chúng, đó là câu kiểm toán hỏi đầu tiên. Bảng phân quyền đang có trả lời được câu
"ai được NHÌN màn hình nào" – một câu khác hẳn.
"""
from __future__ import annotations

import io
from datetime import datetime

from app.models.core import ROLES
from app.services import luong_viec as LV


def _ten_vai_tro(ma: str) -> str:
    return ROLES.get(ma, ma)


def _ai_duoc_bang_tieng_viet(b: LV.Buoc) -> str:
    """Câu mô tả bằng TÊN VAI TRÒ tiếng Việt, không phải mã máy.

    Người đọc trang này là Chủ tịch và kiểm toán viên, không phải người viết mã. Một ô ghi
    "chutich, tgd" thì họ vẫn đoán ra; một ô ghi "ptgd_doan" thì không.
    """
    if b.vai_tro_dong:
        return {"rules.approver_role":
                "Tổng giám đốc (tour lẻ) hoặc Phó TGĐ tour đoàn (tour đoàn) – tính theo loại tour"
                }.get(b.vai_tro_dong, f"tính lúc chạy theo {b.vai_tro_dong}")
    ten = ", ".join(_ten_vai_tro(v) for v in b.vai_tro)
    if b.cach_canh == LV.CHI_CHU_SO_HUU:
        return f"CHỈ {LV._TEN_CHU[b.chu_so_huu]} – không ai làm thay được"
    if b.cach_canh == LV.HOAC:
        return f"{ten}, hoặc chính {LV._TEN_CHU[b.chu_so_huu]}"
    if b.cach_canh == LV.VA:
        return f"{ten}, và đồng thời phải là {LV._TEN_CHU[b.chu_so_huu]}"
    return ten


def bao_cao(db=None) -> dict:
    """Payload cho màn hình. Nhóm theo nghiệp vụ, giữ nguyên thứ tự bước trong bảng.

    `db` chưa dùng tới – bảng luồng việc là KHAI BÁO, không phải dữ liệu. Giữ tham số để lời gọi
    không phải đổi khi sau này có phần đọc từ cơ sở dữ liệu (ví dụ ai đang giữ vai trò nào).
    """
    nhom: list[dict] = []
    for ma_nv, ten_nv in LV.NGHIEP_VU.items():
        buoc = []
        for b in LV.theo_nghiep_vu(ma_nv):
            buoc.append({
                "ma": b.ma, "ten": b.ten,
                "ai_duoc": _ai_duoc_bang_tieng_viet(b),
                "vai_tro": [{"ma": v, "ten": _ten_vai_tro(v)} for v in b.vai_tro],
                "mot_cua": b.cach_canh == LV.CHI_CHU_SO_HUU,
                "chu_so_huu": LV._TEN_CHU.get(b.chu_so_huu, ""),
                "chu_ky": b.chu_ky,
                "tu_trang_thai": b.tu_trang_thai, "den_trang_thai": b.den_trang_thai,
                "nguon": b.nguon, "vi_sao": b.vi_sao,
            })
        nhom.append({"ma": ma_nv, "ten": ten_nv, "so_buoc": len(buoc), "buoc": buoc})

    return {
        "nhom": nhom,
        "so_buoc": len(LV.LUONG_VIEC),
        "so_buoc_mot_cua": sum(1 for b in LV.LUONG_VIEC if b.cach_canh == LV.CHI_CHU_SO_HUU),
        "so_buoc_hai_chu_ky": sum(1 for b in LV.LUONG_VIEC if b.chu_ky == 2),
        "nguoi_xac_nhan_de_nghi_chi": {
            loai: [{"ma": v, "ten": _ten_vai_tro(v)} for v in vs]
            for loai, vs in LV.NGUOI_XAC_NHAN_THEO_LOAI.items()
        },
        "ghi_chu": ("Bảng này CHÉP LẠI luật đang chạy trong mã, không phải một bản khai riêng. "
                    "Có phép thử đối chiếu bảng với mã ở mỗi lần chạy: bảng lệch khỏi mã thì phép "
                    "thử đỏ, và quy ước là MÃ ĐÚNG, BẢNG SAI."),
    }


def tra_cuu_vai_tro(vai_tro: str) -> dict:
    """Người giữ vai trò này đẩy được những bước nào – dùng cho tra cứu ngược trên màn hình."""
    ds = LV.buoc_cua_vai_tro(vai_tro)
    return {
        "vai_tro": vai_tro, "ten": _ten_vai_tro(vai_tro), "so_buoc": len(ds),
        "buoc": [{"nghiep_vu": LV.NGHIEP_VU.get(b.nghiep_vu, b.nghiep_vu), "ten": b.ten,
                  "ai_duoc": _ai_duoc_bang_tieng_viet(b), "vi_sao": b.vi_sao} for b in ds],
        "khong_co_buoc_nao": len(ds) == 0,
    }


# ---------------------------------------------------------------------------------------------
# Bản Excel để ký
# ---------------------------------------------------------------------------------------------
COT = (("Nghiệp vụ", 26), ("Bước", 30), ("Ai được đẩy việc", 46), ("Một cửa", 10),
       ("Chữ ký", 8), ("Từ trạng thái", 18), ("Sang trạng thái", 18),
       ("Luật nằm ở đâu", 34), ("Vì sao chặn như vậy", 62))


def xlsx(db=None) -> bytes:
    """Bản Excel cho Chủ tịch rà và ký. Hai ô ký ở cuối, giống bản ma trận quyền đã có."""
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Luồng công việc"

    dam = Font(bold=True)
    nen = PatternFill("solid", fgColor="E2EFED")
    vien = Border(bottom=Side(style="thin", color="C9CDCB"))
    tren = Alignment(vertical="top", wrap_text=True)

    ws.cell(1, 1, "VTOS – LUỒNG CÔNG VIỆC GIỮA CÁC PHÒNG BAN").font = Font(bold=True, size=14)
    ws.cell(2, 1, "Ai được đẩy việc sang bước sau. Khác với bảng phân quyền màn hình, vốn chỉ nói "
                  "ai được NHÌN.")
    ws.cell(3, 1, f"Xuất lúc {datetime.now():%d/%m/%Y %H:%M}. Bảng chép lại luật đang chạy trong "
                  "mã; có phép thử đối chiếu ở mỗi lần chạy.")

    h = 5
    for i, (ten, rong) in enumerate(COT, start=1):
        o = ws.cell(h, i, ten)
        o.font, o.fill, o.border, o.alignment = dam, nen, vien, tren
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = rong

    r = h + 1
    for nv in bao_cao(db)["nhom"]:
        for b in nv["buoc"]:
            gia_tri = (nv["ten"], b["ten"], b["ai_duoc"], "CÓ" if b["mot_cua"] else "",
                       b["chu_ky"], b["tu_trang_thai"], b["den_trang_thai"], b["nguon"], b["vi_sao"])
            for i, v in enumerate(gia_tri, start=1):
                o = ws.cell(r, i, v)
                o.alignment = tren
                o.border = vien
            r += 1

    r += 2
    ws.cell(r, 1, "Người rà soát").font = dam
    ws.cell(r, 4, "Tổng giám đốc xác nhận").font = dam
    ws.cell(r + 1, 1, "Ngày:                        Ký:")
    ws.cell(r + 1, 4, "Ngày:                        Ký:")

    ws.freeze_panes = ws.cell(h + 1, 1)
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()
