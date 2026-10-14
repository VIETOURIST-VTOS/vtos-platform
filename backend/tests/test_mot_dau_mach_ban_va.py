# -*- coding: utf-8 -*-
"""MỘT ĐẦU MẠCH — hàng rào sinh ra sau ba lần gãy trong CÙNG MỘT NGÀY (13/10/2026).

VÌ SAO CÓ TỆP NÀY

Container khởi động chạy `alembic upgrade head`. Có hơn một head thì lệnh ấy KHÔNG chọn đại một
cái — nó báo lỗi và dừng:

    CommandError: The script directory has multiple heads (due to branching).

Nghĩa là bản dựng không lên được, và hệ thật đứng ở bản vá cũ cho tới khi có người nối lại mạch.

ĐO ĐƯỢC NGÀY 13/10/2026, BA LẦN:

  1. QT-1 (làn Phân quyền) và E5 (làn khác) cùng móc vào `e4a1b2c3d4e5`, cả hai merge → hai head.
  2. Vòng HQ-2 vá bằng một bản gộp mạch; trong lúc chờ merge, một làn nữa thêm bản vá sau đó →
     bản gộp thành một nhánh rẽ giữa chừng, merge vào là hai head trở lại.
  3. Vòng DL-2 suýt lặp lại y hệt.

VÌ SAO KHÔNG LÀN NÀO TỰ THẤY

Trên cây riêng của mỗi làn CHỈ CÓ MỘT HEAD. Cái gãy chỉ hiện ra sau khi gộp hai nhánh — tức là
đúng lúc không ai còn nhìn nữa. Đó là lý do phép thử này đứng ở đây chứ không nằm trong quy trình
của từng làn: `pull_request` dựng CI trên KẾT QUẢ GỘP, nên nó đỏ TRƯỚC khi merge chứ không phải
sau.

Phép thử này hỏi chính alembic, không tự đọc tệp bằng biểu thức chính quy: một bản vá khai
`down_revision` là một bộ nhiều phần tử (bản gộp mạch) thì cách đọc bằng tay sẽ hiểu sai, và hàng
rào sẽ xanh đúng lúc nó cần đỏ.
"""
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]


def _chuoi():
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    return ScriptDirectory.from_config(Config(str(GOC / "alembic.ini")))


def test_chi_duoc_co_MOT_dau_mach():
    sc = _chuoi()
    try:
        heads = sc.get_heads()
    except Exception as ex:
        # Chuỗi hỏng tới mức alembic không dựng nổi — thường là một `down_revision` gõ nhầm. Phép
        # thử bên dưới gọi đúng tên chỗ hỏng; ở đây chỉ nói ra chứ không ném một KeyError trần.
        raise AssertionError(
            f"Không dựng được chuỗi bản vá: {type(ex).__name__}: {str(ex)[:200]}. "
            f"Xem test_khong_ban_va_nao_moc_vao_mot_so_hieu_khong_ton_tai — nó gọi tên bản hỏng."
        ) from None
    assert len(heads) == 1, (
        f"Chuỗi bản vá có {len(heads)} đầu mạch: {heads}. Container khởi động chạy "
        f"`alembic upgrade head`, và lệnh ấy BÁO LỖI chứ không chọn đại một cái — bản dựng sẽ "
        f"không lên được.\n\n"
        f"Thường là hai làn cùng móc bản vá của mình vào một bản cha. Chữa bằng MỘT trong hai:\n"
        f"  · trỏ lại `down_revision` của bản CHƯA TỪNG CHẠY trên hệ thật xuống dưới bản kia; hoặc\n"
        f"  · thêm một bản GỘP MẠCH có `down_revision` là một bộ chứa tất cả các đầu.\n\n"
        f"KHÔNG đổi `down_revision` của một bản ĐÃ CHẠY trên hệ thật: bảng `alembic_version` đang "
        f"giữ số hiệu ấy, và đổi chuỗi dưới chân nó là làm alembic mất đường đi từ đúng chỗ nó "
        f"đang đứng.")


def test_khong_ban_va_nao_moc_vao_mot_so_hieu_khong_ton_tai():
    """Gõ nhầm một ký tự trong `down_revision` thì alembic báo lỗi lúc KHỞI ĐỘNG, không phải lúc đẩy."""
    sc = _chuoi()
    co = {r.revision for r in sc.walk_revisions()}
    hong = []
    for r in sc.walk_revisions():
        dv = r.down_revision
        cha = () if dv is None else ((dv,) if isinstance(dv, str) else tuple(dv))
        for c in cha:
            if c not in co:
                hong.append(f"{r.revision} móc vào '{c}' — không có bản vá nào mang số hiệu ấy")
    assert not hong, hong
