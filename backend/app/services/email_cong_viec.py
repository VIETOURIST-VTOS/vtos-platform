# -*- coding: utf-8 -*-
"""EM-1 · Email công việc của tài khoản (Chủ tịch duyệt bản xem thử 18/10/2026).

HAI EMAIL, HAI NGHĨA. `employee_profiles.email` là email CÁ NHÂN, HCNS nhập trong hồ sơ nhân sự.
`users.email_cong_viec` là hộp thư CÔNG VIỆC, CNTT nhập ở /access, và là địa chỉ các thông báo
của hệ thống (báo động khủng hoảng trước tiên) gửi tới. Gộp một ô thì có ngày cảnh báo nội bộ
rơi vào hộp thư riêng của một người đã nghỉ việc.

BA LUẬT, Chủ tịch chốt:
  1. Đuôi BẮT BUỘC là @vietourist.com.vn. Gõ đuôi khác là lỗi 422, không phải lời nhắc.
  2. Hai tài khoản đang hoạt động không dùng chung một địa chỉ.
  3. Để trống được: chưa có hộp thư công việc thì «chưa có», không chặn việc gì khác.
"""
import re

DUOI = "@vietourist.com.vn"
_DANG = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9.-]+$")


class EmailSai(ValueError):
    pass


def chuan(s: str | None) -> str:
    """Trả địa chỉ đã chuẩn (bỏ khoảng trắng, chữ thường), chuỗi rỗng nếu để trống; ném EmailSai."""
    v = (s or "").strip().lower()
    if not v:
        return ""
    if not _DANG.match(v):
        raise EmailSai(f"«{v}» không phải một địa chỉ email")
    if not v.endswith(DUOI) or len(v) == len(DUOI):
        raise EmailSai(f"Email công việc phải có đuôi {DUOI}")
    return v
