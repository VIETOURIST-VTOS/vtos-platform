#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Nạp KHO QUYẾT TOÁN CŨ (tháng 1–6/2026) vào VTOS – chạy trên máy, không chạy trên production.

    python scripts/nap_kho_cu.py du_lieu_nap.json                # xem trước, KHÔNG ghi gì
    python scripts/nap_kho_cu.py du_lieu_nap.json --ghi           # ghi thật
    python scripts/nap_kho_cu.py du_lieu_nap.json --ghi --ke-ca-canh-bao

MẶC ĐỊNH LÀ XEM TRƯỚC, KHÔNG PHẢI GHI

Chạy không cờ thì không một dòng nào vào cơ sở dữ liệu. Phải gõ thêm --ghi mới ghi. Một lệnh nạp
19.000 dòng khách và 13.000 dòng chi mà mặc định là ghi thì chỉ cần một lần gõ nhầm.

NGUỒN RIÊNG, XOÁ-RỒI-GHI

Mọi dòng nạp bằng lệnh này mang source='kho_cu_h1_2026'. Nạp lại thì XOÁ đúng phần mang nguồn ấy
rồi ghi lại – nạp bao nhiêu lần cũng ra một kết quả, và KHÔNG đụng tới dòng do Vietrip hay do người
nhập tay tạo ra.

CHUYẾN ĐÃ CÓ GIÁ VỐN TỪ NGUỒN KHÁC THÌ DỪNG

Cộng thêm một bộ dòng chi vào chuyến đã có dòng chi là nhân đôi giá vốn, và mọi bảng vẫn cân vì tổng
nào cũng cộng từ dòng – không ai nhìn ra. Gặp trường hợp ấy lệnh này BỎ QUA chuyến đó và ghi vào báo
cáo, trừ khi người chạy gõ --ke-ca-canh-bao để tự nhận trách nhiệm.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

NGUON = "kho_cu_h1_2026"


def main() -> int:
    p = argparse.ArgumentParser(description="Nạp kho quyết toán cũ T1–T6/2026 vào VTOS")
    p.add_argument("tep_json", help="du_lieu_nap.json")
    p.add_argument("--ghi", action="store_true", help="ghi thật (mặc định chỉ xem trước)")
    p.add_argument("--ke-ca-canh-bao", action="store_true",
                   help="nạp cả chuyến đã có giá vốn từ nguồn khác – TỰ CHỊU TRÁCH NHIỆM")
    p.add_argument("--bao-cao", default="ket_qua_nap.json")
    a = p.parse_args()

    from sqlalchemy import func, select
    from app.db.session import SessionLocal
    import app.models  # noqa: F401
    from app.models.core import Booking, Tour
    from app.models.lop3_tour import BookingKhach, TourDoanhThuDong, TourHdvChi
    from app.models.vietrip import TourCostLine
    from app.services import chong_trung_quyet_toan as CT

    ds = json.load(open(a.tep_json, encoding="utf-8"))
    db = SessionLocal()
    kq = {"chay_luc": datetime.now().isoformat(timespec="seconds"),
          "che_do": "GHI THẬT" if a.ghi else "xem trước",
          "tong_tep": len(ds), "da_nap": [], "bo_qua": [], "khong_thay_chuyen": []}

    for d in ds:
        ma = (d.get("ma_tour") or "").strip()
        t = db.scalars(select(Tour).where(func.upper(Tour.code) == ma.upper())).first() if ma else None
        if t is None:
            kq["khong_thay_chuyen"].append({"tep": d["ten_tep"], "ma_tour": ma})
            continue

        va = CT.doi_chieu_he_thong(db, d, t.id)
        chan = [x for x in va if x["muc"] == CT.NANG]
        hoi = [x for x in va if x["muc"] == CT.HOI]
        if chan or (hoi and not a.ke_ca_canh_bao):
            kq["bo_qua"].append({"tep": d["ten_tep"], "ma_tour": ma,
                                 "vi_sao": [x["noi"] for x in (chan + hoi)]})
            continue

        if a.ghi:
            # XOÁ ĐÚNG PHẦN CỦA NGUỒN NÀY, không đụng nguồn khác.
            # Mỗi bảng có một cột ghi NGUỒN khác nhau, nên phải khai từng bảng một. Viết một vòng
            # lặp chung rồi đoán tên cột là cách chắc chắn để hoặc nổ, hoặc tệ hơn: xoá nhầm cả dòng
            # của nguồn khác vì điều kiện lọc không áp được.
            db.query(TourCostLine).filter(
                TourCostLine.tour_id == t.id,
                TourCostLine.source == NGUON).delete(synchronize_session=False)
            db.query(BookingKhach).filter(
                BookingKhach.tour_id == t.id,
                BookingKhach.nguoi_sua == NGUON).delete(synchronize_session=False)
            db.query(TourHdvChi).filter(
                TourHdvChi.tour_id == t.id,
                TourHdvChi.nguoi_nhap == NGUON).delete(synchronize_session=False)
            # tour_doanh_thu_dong KHÔNG có cột nào ghi nguồn, nên không xoá có phạm vi được – và
            # lệnh này cũng không ghi vào đó. Doanh thu của kho cũ vào ở mức CHUYẾN (actual_revenue)
            # chứ không tách thành dòng, vì bản đối chiếu H1 chỉ có số tổng theo chuyến.
            db.flush()

            b = db.scalars(select(Booking).where(Booking.tour_id == t.id)
                           .order_by(Booking.id)).first()
            # Không có phiếu đặt thì KHÔNG treo dòng khách vào hư không – booking_khach.booking_id
            # là cột bắt buộc. Nhưng phải NÓI RA: bỏ lặng lẽ thì người chạy thấy "nạp xong" trong
            # khi cả danh sách khách của chuyến ấy không vào đâu cả.
            if b is None and d.get("khach"):
                kq.setdefault("mat_dong_khach_vi_chua_co_phieu_dat", []).append(
                    {"tep": d["ten_tep"], "ma_tour": ma, "so_dong_khach": len(d["khach"])})
            for i, x in enumerate(d.get("khach", []), start=1):
                if b is None:
                    break
                db.add(BookingKhach(tour_id=t.id, booking_id=b.id, stt=i,
                                    ho_ten=(x.get("ho_ten") or "")[:200],
                                    gia_ban=x.get("gia_ban"),
                                    ma_dat_cho=(x.get("ma_dat_cho") or "")[:30] or None,
                                    nguoi_sua=NGUON, sua_luc=datetime.now()))
            for i, x in enumerate(d.get("chi", []), start=1):
                db.add(TourCostLine(tour_id=t.id, line_no=i,
                                    description=(x.get("noi_dung") or "(không ghi)")[:200],
                                    nhom=(x.get("nhom") or "")[:80] or None,
                                    ngay=(x.get("ngay") or "")[:60] or None,
                                    supplier_name=(x.get("doi_tac") or "")[:200],
                                    supplier_tax_code=(x.get("mst") or "")[:20],
                                    unit_price=x.get("don_gia"), qty=x.get("so_luong") or 0,
                                    coef=x.get("he_so") or 1, actual=x.get("thanh_tien"),
                                    hinh_thuc_tt=(x.get("hinh_thuc_tt") or "")[:20] or None,
                                    note=(x.get("ghi_chu") or "")[:200],
                                    source=NGUON, status="hd", updated_by=NGUON))
            cb = d.get("dong_can_bang")
            if cb:
                db.add(TourCostLine(tour_id=t.id, line_no=9000,
                                    description=cb["noi_dung"][:200], actual=cb["so_tien"],
                                    note=cb["vi_sao"][:200], source=NGUON, status="hd",
                                    updated_by=NGUON))
            for x in d.get("hdv", {}).get("dong", []):
                db.add(TourHdvChi(tour_id=t.id, noi_dung=(x.get("noi_dung") or "")[:200] or None,
                                  don_gia=x.get("don_gia"), so_luong=x.get("so_luong"),
                                  thanh_tien=x.get("thanh_tien"),
                                  tien_ung=d["hdv"].get("tien_ung"),
                                  trang_thai_duyet="da_duyet",
                                  nguoi_nhap=NGUON, nhap_luc=datetime.now()))
            # ---- Doanh thu và giá vốn Ở MỨC CHUYẾN, lấy theo BẢN ĐÃ CHỐT ----
            #
            # CHỈ ĐIỀN KHI Ô ĐANG TRỐNG. Đè lên một con số đã có là xoá dữ liệu thật của công ty
            # bằng suy đoán của một lệnh nạp – kể cả khi con số mới có vẻ đúng hơn. Ô đã có số thì
            # ghi vào báo cáo để người đối chiếu, không tự sửa.
            tien = d.get("tien_theo_ban_chot") or {}
            for cot, gia in (("actual_revenue", tien.get("tong_thu")),
                             ("actual_cost", tien.get("tong_chi"))):
                if not isinstance(gia, (int, float)):
                    continue
                cu = getattr(t, cot)
                if cu is None:
                    setattr(t, cot, float(gia))
                elif abs(float(cu) - float(gia)) > 1000:
                    kq.setdefault("khong_de_len", []).append(
                        {"tep": d["ten_tep"], "ma_tour": ma, "cot": cot,
                         "dang_co": float(cu), "ban_chot": float(gia)})

        kq["da_nap"].append({"tep": d["ten_tep"], "ma_tour": ma, "tour_id": t.id,
                             "so_khach": len(d.get("khach", [])),
                             "so_dong_chi": len(d.get("chi", [])),
                             "co_dong_can_bang": "dong_can_bang" in d})

    if a.ghi:
        db.commit()
    else:
        db.rollback()
    db.close()

    json.dump(kq, open(a.bao_cao, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"chế độ      : {kq['che_do']}")
    print(f"tệp đưa vào : {kq['tong_tep']}")
    print(f"nạp được    : {len(kq['da_nap'])}")
    print(f"bỏ qua      : {len(kq['bo_qua'])}  (chuyến đã có dữ liệu từ nguồn khác)")
    print(f"không thấy chuyến trong VTOS: {len(kq['khong_thay_chuyen'])}")
    mat = kq.get("mat_dong_khach_vi_chua_co_phieu_dat") or []
    if mat:
        print(f"CHÚ Ý: {len(mat)} chuyến chưa có phiếu đặt nên "
              f"{sum(x['so_dong_khach'] for x in mat)} dòng khách KHÔNG được ghi")
    de = kq.get("khong_de_len") or []
    if de:
        print(f"CHÚ Ý: {len(de)} chuyến đã có sẵn doanh thu/giá vốn khác số đã chốt – KHÔNG đè, "
              f"xem mục 'khong_de_len' trong báo cáo")
    print(f"báo cáo chi tiết: {a.bao_cao}")
    if not a.ghi:
        print("\nĐÂY LÀ XEM TRƯỚC – chưa ghi gì vào cơ sở dữ liệu. Thêm --ghi để ghi thật.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
