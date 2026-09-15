# -*- coding: utf-8 -*-
"""TC-33 · Khối 08 bản vẽ V1.4 — TIẾN ĐỘ BÁO CÁO & KẾT LUẬN CHỈ ĐẠO.

Bản vẽ đặt MỘT khối nhưng hỏi HAI câu khác hẳn nhau, và đây là chỗ phải tách ngay từ đầu:

    (A) TIẾN ĐỘ BÁO CÁO   – phòng nào đã nộp bản cho kỳ vừa đóng, phòng nào chưa.
    (B) KẾT LUẬN CHỈ ĐẠO  – chỉ đạo của Chủ tịch có được làm không, ai làm, hạn nào.

Câu (A) trả lời được NGAY HÔM NAY, không cần bảng mới và không cần ai nhập gì: danh sách phòng
phải nộp đã khai sẵn ở `bao_cao_phong.PHONG`, và bản đã nộp nằm ở bảng `bao_cao_luu`. Đối chiếu hai
cái là ra.

Câu (B) KHÔNG có bảng nào giữ. Nó phải nằm im ở trạng thái "chưa kết nối" cho tới khi có người khai
— và phải nói rõ là chưa có, chứ không mượn số của câu (A) để lấp chỗ trống. Trộn hai câu vào một
bảng thì khối này trông như đã xong trong khi một nửa còn chưa bắt đầu.

════════════════════════════════════════════════════════════════════════════════════════════════
KỲ NÀO ĐƯỢC ĐEM RA ĐO — CHỖ DỄ SAI NHẤT CỦA KHỐI NÀY

Báo cáo tháng 09/2026 KHÔNG thể "trễ" vào ngày 15/09: kỳ chưa đóng thì chưa tới hạn nộp. Lấy kỳ
ĐANG CHẠY ra đo thì mọi phòng đều hiện "chưa nộp", và tám dòng đỏ ấy hoàn toàn vô nghĩa — tệ hơn
là sau vài lần nhìn thấy, người ta thôi tin cả khối.

Nên khối này đo KỲ VỪA ĐÓNG, và ghi rõ đang đo kỳ nào ngay trên màn hình. Một bảng tiến độ không
nói nó đang đo kỳ nào là một bảng không kiểm được.

════════════════════════════════════════════════════════════════════════════════════════════════
KHÔNG KHAI LẠI DANH SÁCH PHÒNG

`bao_cao_phong.PHONG` đã là bản khai chính thức: phòng nào có báo cáo riêng, tên tiếng Việt, và
những vai trò nào được xem. Khai lại ở đây là tạo ra bản thứ hai — và hai bản khai cùng một thứ thì
sớm muộn lệch nhau, lúc lệch thì phòng mới thêm chỉ hiện ở một trong hai chỗ.

Bộ phận TRỰC THUỘC (Visa thuộc Điều hành, Chủ tịch chốt 10/9/2026) không đứng thành dòng riêng ở
cấp khối này — `PHONG_GOC` đã lọc sẵn.

════════════════════════════════════════════════════════════════════════════════════════════════
SEC-02 · AI ĐƯỢC THẤY DÒNG NÀO

Dùng lại đúng bảng khai quyền của `bao_cao_phong`: XEM_TAT_CA thấy hết; vai trò khác chỉ thấy
những phòng mà `PHONG[ma]["xem"]` có tên vai ấy. Không khai quyền riêng cho khối này — nới quyền
mà không ai quyết định là cách quyền rộng ra một cách im lặng.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bao_cao_luu import BaoCaoLuu
from app.services.bao_cao_phong import PHONG, PHONG_GOC, TOAN_CTY, XEM_TAT_CA

# Chưa có bảng nào giữ kết luận chỉ đạo. Nói thẳng ra, kèm ai phải khai — một ô trống không nói ai
# chịu trách nhiệm thì nó nằm đó mãi: ai đọc cũng nghĩ người khác lo.
CHUA_CO_SO_CHI_DAO = (
    "Chưa có sổ kết luận chỉ đạo. Đây là phần CHƯA BẮT ĐẦU, không phải phần đang rỗng: hệ thống "
    "chưa có bảng nào giữ nội dung chỉ đạo, đơn vị phụ trách, hạn và tiến độ. Văn phòng Hội đồng "
    "quản trị khai sổ thì khối này hiện được."
)

TEN_KY_DAI = {"ngay": "ngày", "tuan": "tuần", "thang": "tháng"}


def _ky_vua_dong(kind: str, hom_nay: date) -> tuple[str, date, date]:
    """(mã kỳ, ngày đầu, ngày cuối) của kỳ VỪA ĐÓNG tính đến `hom_nay`.

    Kỳ đang chạy không đem ra đo: chưa đóng thì chưa tới hạn nộp, và mọi phòng sẽ hiện "chưa nộp".
    """
    if kind == "ngay":
        d = hom_nay - timedelta(days=1)
        return d.isoformat(), d, d
    if kind == "tuan":
        # Tuần ISO vừa đóng: lùi về thứ Hai của tuần này rồi lùi thêm một tuần.
        dau_tuan_nay = hom_nay - timedelta(days=hom_nay.weekday())
        dau = dau_tuan_nay - timedelta(days=7)
        cuoi = dau + timedelta(days=6)
        nam, tuan, _ = dau.isocalendar()
        return f"{nam}-W{tuan:02d}", dau, cuoi
    # tháng
    dau_thang_nay = date(hom_nay.year, hom_nay.month, 1)
    cuoi = dau_thang_nay - timedelta(days=1)
    dau = date(cuoi.year, cuoi.month, 1)
    return f"{cuoi.year}-{cuoi.month:02d}", dau, cuoi


def _ten_ky(kind: str, ky: str, dau: date, cuoi: date) -> str:
    if kind == "ngay":
        return f"Báo cáo ngày {dau.strftime('%d/%m/%Y')}"
    if kind == "tuan":
        return f"Báo cáo tuần {ky} ({dau.strftime('%d/%m')}–{cuoi.strftime('%d/%m/%Y')})"
    return f"Báo cáo tháng {cuoi.month:02d}/{cuoi.year}"


def pham_vi_duoc_xem(vai_tro: str | None) -> set[str] | None:
    """None = xem hết. Ngoài ra là tập mã phạm vi mà vai ấy được xem.

    Đọc thẳng bảng khai của `bao_cao_phong`, không khai lại.
    """
    if vai_tro is None or vai_tro in XEM_TAT_CA:
        return None
    duoc = {ma for ma in PHONG_GOC if vai_tro in PHONG[ma].get("xem", ())}
    return duoc


def tien_do(db: Session, *, kind: str = "thang", hom_nay: date | None = None,
            vai_tro: str | None = None) -> dict:
    """Bảng (A) — tiến độ nộp báo cáo của KỲ VỪA ĐÓNG.

    Trả `dong` theo đúng năm cột của bản vẽ, kèm `ky` để màn hình nói rõ đang đo kỳ nào.
    """
    hom_nay = hom_nay or date.today()
    if kind not in TEN_KY_DAI:
        raise ValueError(f"kỳ không hợp lệ: {kind!r}")
    ky, dau, cuoi = _ky_vua_dong(kind, hom_nay)

    duoc_xem = pham_vi_duoc_xem(vai_tro)
    # Toàn công ty đứng đầu bảng, rồi tới từng phòng — đọc từ trên xuống là đi từ tổng tới chi tiết.
    can_nop = [TOAN_CTY] + list(PHONG_GOC)
    if duoc_xem is not None:
        can_nop = [m for m in can_nop if m in duoc_xem]

    if not can_nop:
        return {"ky": ky, "kind": kind, "ten_ky": _ten_ky(kind, ky, dau, cuoi),
                "dong": [], "so_da_nop": 0, "so_thieu": 0,
                "vi_sao": "Vai trò này không phụ trách báo cáo của phạm vi nào.",
                "chi_dao": None, "chi_dao_vi_sao": CHUA_CO_SO_CHI_DAO}

    # MỘT câu truy vấn cho cả bảng, không hỏi từng phòng một: tám phạm vi là tám lượt đi về cơ sở
    # dữ liệu cho một khối chỉ để vẽ tám dòng.
    da_luu = {
        r.pham_vi: r for r in db.execute(
            select(BaoCaoLuu).where(BaoCaoLuu.kind == kind, BaoCaoLuu.ky == ky,
                                    BaoCaoLuu.pham_vi.in_(tuple(can_nop)))).scalars()
    }

    dong = []
    for ma in can_nop:
        ban = da_luu.get(ma)
        ten_pv = "Toàn công ty" if ma == TOAN_CTY else PHONG[ma]["ten"]
        dong.append({
            "ho_so": _ten_ky(kind, ky, dau, cuoi),
            "ma_pham_vi": ma,
            "don_vi": ten_pv,
            # Hạn là NGÀY KỲ ĐÓNG. Không bịa thêm giờ chốt: giờ chốt của báo cáo ngày (20:00) là
            # luật của Điều 12, còn kỳ tuần/tháng chưa ai chốt giờ — bịa ra một mốc là tạo ra một
            # cái hạn mà không ai từng quyết định.
            "han": cuoi.strftime("%d/%m/%Y"),
            "tien_do": ("Đã nộp · lưu lúc " + ban.tao_luc.strftime("%d/%m %H:%M")) if ban
                       else "Chưa có bản lưu",
            "da_nop": ban is not None,
            # Đã nộp thì bước tiếp là ĐỌC; chưa nộp thì bước tiếp là LẬP. Ghi chung một câu cho cả
            # hai thì cột này không nói thêm gì so với cột bên cạnh.
            "buoc_tiep": ("Xem bản lưu" if ban else "Lập và lưu báo cáo kỳ này"),
            "cua": f"/bao-cao?kind={kind}&ky={ky}&pham_vi={ma}",
            # Ba con số đã đếm sẵn trong bản lưu — hiện luôn, vì "đã nộp" mà toàn việc đỏ thì
            # "đã nộp" không phải là tin tốt.
            "so_viec_do": ban.so_viec_do if ban else None,
        })

    so_da = sum(1 for d in dong if d["da_nop"])
    return {
        "ky": ky, "kind": kind, "ten_ky": _ten_ky(kind, ky, dau, cuoi),
        "dong": dong,
        "so_da_nop": so_da,
        "so_thieu": len(dong) - so_da,
        "vi_sao": "",
        # Bảng (B) — CHƯA CÓ SỔ. Trả None kèm lý do, không trả danh sách rỗng: danh sách rỗng đọc
        # là "không có chỉ đạo nào đang theo dõi", khác hẳn "chưa có chỗ nào để theo dõi".
        "chi_dao": None,
        "chi_dao_vi_sao": CHUA_CO_SO_CHI_DAO,
    }
