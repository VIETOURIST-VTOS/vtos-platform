"""Bóc dấu nguồn quảng cáo ra khỏi webhook Meta và webhook Zalo OA.

VÌ SAO LÀ MỘT TỆP RIÊNG, KHÔNG NHÉT VÀO `services/inbox.py` HAY `services/zalo.py`. Hai tệp ấy lo
hộp thư và lo tài khoản OA; đây là việc khác hẳn — ghi lại BẰNG CHỨNG khách đến từ mẫu quảng cáo
nào. Trộn vào thì mỗi lần sửa luật hộp thư lại phải đọc cả phần quảng cáo, và ngược lại.

KHÔNG DỰNG CỬA WEBHOOK MỚI. Cả hai cửa đã chạy sẵn và đã có xác thực: `/api/v1/facebook/webhook`
kiểm `X-Hub-Signature-256`, `/api/v1/zalo/webhook` kiểm `X-ZEvent-Signature`. Mở cửa thứ ba cho
cùng một nguồn là thêm một chỗ phải canh mà không mua thêm gì.

HAI CHỖ MANG MÃ QUẢNG CÁO MÀ WEBHOOK HIỆN TẠI BỎ QUA — đo trên mã nguồn ngày 07/10/2026:
`services/inbox.fb_webhook` đọc `entry[].messaging[]` và `entry[].changes[]` của bình luận, nhưng
KHÔNG đọc `referral` (khách bấm quảng cáo click-to-Messenger) và KHÔNG đọc `changes[]` field
`leadgen` (khách điền biểu mẫu). Đó đúng là hai chỗ Meta đặt `ad_id` và `leadgen_id` vào.
"""
from datetime import datetime
from sqlalchemy.orm import Session

from app.services import dau_quang_cao as DQ


def _gio(giay) -> str:
    """Meta gửi thời điểm bằng giây Unix. Trả chuỗi cho DQ.ghi tự đọc; hỏng thì trả rỗng.

    Rỗng là CHƯA BIẾT và DQ.ghi chấp nhận – thà mất cái giờ còn hơn mất cả cái dấu.
    """
    try:
        n = int(giay)
    except (TypeError, ValueError):
        return ""
    if n > 1e11:          # vài trường gửi mili giây
        n //= 1000
    try:
        return f"{datetime.fromtimestamp(n):%Y-%m-%d %H:%M:%S}"
    except (OverflowError, OSError, ValueError):
        return ""


def tu_meta(db: Session, payload: dict) -> dict:
    """Bóc dấu từ một gói webhook Meta đã QUA xác thực chữ ký ở cửa.

    Hàm này KHÔNG tự kiểm chữ ký: cửa đã kiểm, và kiểm hai lần ở hai chỗ nghĩa là sẽ có ngày hai
    chỗ dùng hai bí mật khác nhau. Gọi hàm này từ nơi khác mà bỏ qua cửa là tự bơm dấu giả.
    """
    moi = da_co = 0
    loi: list[str] = []

    def ghi(d: dict):
        nonlocal moi, da_co
        try:
            _, la_moi = DQ.ghi(db, d, boi="webhook_fb")
            moi += la_moi
            da_co += (not la_moi)
        except Exception as ex:                      # noqa: BLE001
            # Một dấu hỏng không được làm hỏng cả webhook: Meta TẮT webhook sau vài lần nhận mã
            # lỗi, và mất webhook là mất luôn mọi dấu về sau, không chỉ cái dấu này.
            loi.append(f"{type(ex).__name__}: {str(ex)[:120]}")

    for entry in payload.get("entry") or []:
        page_id = str(entry.get("id") or "")

        # ── 1. Khách bấm quảng cáo rồi NHẮN TIN (click-to-Messenger / click-to-IG-DM) ─────────
        # `referral` tới khi khách đã từng nhắn; lần đầu tiên nó nằm trong `postback.referral`
        # kèm nút Bắt đầu. Đọc cả hai, vì chỉ đọc một thì mất đúng nhóm khách MỚI – nhóm mà
        # quảng cáo vừa mua về.
        for ev in (entry.get("messaging") or []) + (entry.get("standby") or []):
            r = ev.get("referral") or (ev.get("postback") or {}).get("referral") or {}
            if not r:
                continue
            psid = str((ev.get("sender") or {}).get("id") or "")
            ad_id = str(r.get("ad_id") or "")
            # Không có ad_id thì đây là khách tới từ liên kết m.me hay mã QR, không phải quảng
            # cáo trả tiền. Vẫn ghi, vì nó là một nguồn thật – chỉ khác loại mã.
            ghi({"nen_tang": "facebook",
                 "loai_ma": "ad_referral" if ad_id else "khac",
                 "ma": ad_id or str(r.get("ref") or "")[:200],
                 "ma_mau_qc": ad_id or None,
                 "ten_chien_dich": str(r.get("ads_context_data", {}).get("ad_title") or "")[:200]
                                   if isinstance(r.get("ads_context_data"), dict) else "",
                 "zalo_uid": "", "sdt": "",
                 "utm": {"ref": r.get("ref"), "source": r.get("source"), "type": r.get("type"),
                         "psid": psid, "page_id": page_id},
                 "cham_luc": _gio(ev.get("timestamp")),
                 "nguon_ghi": "webhook_fb",
                 "than_nguyen_van": str(ev)[:8000],
                 "ghi_chu": f"PSID {psid}"})

        # ── 2. Khách điền BIỂU MẪU quảng cáo (Lead Ads) ──────────────────────────────────────
        # Đây là dấu CHÍNH XÁC NHẤT trong cả bốn kênh: Meta trả thẳng `leadgen_id`, `ad_id`,
        # `adgroup_id`, `form_id` – biết đúng mẫu quảng cáo nào ra khách, không phải suy đoán.
        #
        # VTOS chỉ GHI LẠI mã, KHÔNG tự đi lấy nội dung biểu mẫu: lấy nội dung cần token trang
        # cùng quyền `leads_retrieval`, mà hai thứ ấy hôm nay chưa có. Ghi mã trước là đúng thứ
        # tự: mã mất thì không lấy lại được, nội dung thì Meta còn giữ.
        for ch in entry.get("changes") or []:
            if (ch.get("field") or "") != "leadgen":
                continue
            v = ch.get("value") or {}
            lid = str(v.get("leadgen_id") or "")
            if not lid:
                continue
            ghi({"nen_tang": "facebook", "loai_ma": "leadgen_id", "ma": lid,
                 "ma_mau_qc": str(v.get("ad_id") or "") or None,
                 "ma_nhom_qc": str(v.get("adgroup_id") or "") or None,
                 "utm": {"form_id": v.get("form_id"), "page_id": v.get("page_id") or page_id},
                 "cham_luc": _gio(v.get("created_time")),
                 "nguon_ghi": "webhook_fb",
                 "than_nguyen_van": str(ch)[:8000],
                 "ghi_chu": "Lead Ads – chua lay noi dung, can quyen leads_retrieval"})

    return {"moi": moi, "da_co": da_co, "loi": loi}


# Sự kiện Zalo đáng ghi một dấu. KHÔNG ghi cho mọi tin nhắn: khoá chống trùng theo uid nên tin
# thứ hai không sinh dòng mới, nhưng gọi DQ.ghi cho từng tin là tra cơ sở dữ liệu không công.
# `follow` là lúc khách ĐẾN; `user_submit_info` là lúc khách cho số – hai mốc đáng ghi.
ZALO_SU_KIEN = ("follow", "user_submit_info")


def tu_zalo(db: Session, ev: dict, ket_qua: dict) -> dict:
    """Ghi dấu cho một sự kiện Zalo OA đã qua `services/zalo.on_webhook`.

    Nhận `ket_qua` của hàm ấy chứ không tự suy lại: nó đã quyết định uid này là KHÁCH hay NHÂN
    VIÊN, và quyết định ấy có luật riêng (zalo_nguoi_dung). Suy lại ở đây là dựng chỗ thứ hai trả
    lời cùng câu hỏi, rồi ngày hai chỗ lệch nhau thì Chủ tịch bấm "Quan tâm" OA sẽ thành một dấu
    quảng cáo trong báo cáo hiệu quả kênh.
    """
    if ket_qua.get("la_nhan_vien"):
        return {"bo_qua": "nhan_vien"}
    ten = str(ev.get("event_name") or "")
    if ten not in ZALO_SU_KIEN:
        return {"bo_qua": ten or "khong_ro"}
    uid = str(ket_qua.get("uid") or "")
    if not uid:
        return {"bo_qua": "khong_co_uid"}
    sdt = str(((ev.get("info") or {}).get("phone")) or "")
    try:
        _, la_moi = DQ.ghi(db, {
            "nen_tang": "zalo", "loai_ma": "zalo_uid", "ma": uid, "zalo_uid": uid, "sdt": sdt,
            "cham_luc": _gio(ev.get("timestamp")), "nguon_ghi": "webhook_zalo",
            "than_nguyen_van": str(ev)[:8000], "ghi_chu": f"su kien {ten}"}, boi="webhook_zalo")
        return {"moi": int(la_moi), "da_co": int(not la_moi)}
    except Exception as ex:                          # noqa: BLE001
        return {"loi": f"{type(ex).__name__}: {str(ex)[:120]}"}
