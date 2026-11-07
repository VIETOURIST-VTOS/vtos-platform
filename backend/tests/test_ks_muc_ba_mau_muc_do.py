"""KS-MUC (07/11/2026) — ba mức độ phải ba màu, trên mọi màn hình crm.

Đợt KS-NAVY (#704) đổi `--vtos-danger` sang xanh navy sáng: ở nền tối nó TRÙNG ĐÚNG `--vtos-info`
(#6FA8F0), ở nền sáng gần như trùng. Mức Nghiêm trọng, Quá hạn, Từ chối, Lỗ, số âm, báo lỗi… thành
cùng một màu với Theo dõi — Chủ tịch soát màn hình 07/11 và chỉ ra. Cùng lúc tìm ra lỗi cũ từ TQ-1
(23/10): thanh mức «Cảnh báo» trên khối Vận hành lấy `--vtos-info` chứ không phải `--vtos-warning`.

Navy giữ cho thương hiệu (logo, thanh trên, menu, nút); mức độ dùng ba màu riêng.
"""
import os, re
GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _doc(*p):
    return open(os.path.join(GOC, *p), encoding="utf-8").read()


def _khoi(css: str, chon: str) -> str:
    i = css.index(chon)
    return css[i:css.index("}", i)]


def _bien(khoi: str, ten: str) -> str:
    m = re.search(re.escape(ten) + r":\s*(#[0-9A-Fa-f]{6})", khoi)
    assert m, ten
    return m.group(1).upper()


def test_ks_muc_1_nguy_hiem_khac_theo_doi_o_ca_hai_nen():
    css = _doc("web", "app", "tokens.css")
    toi = _khoi(css, ":root")
    assert _bien(toi, "--vtos-danger") == "#FF6B90"
    assert _bien(toi, "--vtos-danger") != _bien(toi, "--vtos-info"), "nền tối: nghiêm trọng trùng màu theo dõi"
    i = css.index("#A8145C")
    assert "--vtos-danger" in css[css.rfind("\n", 0, i):i], "nền sáng: --vtos-danger phải là #A8145C"
    for ten in ("--vtos-danger", "--vtos-warning", "--vtos-info"):
        assert ten in toi


def test_ks_muc_2_thanh_muc_do_ba_mau_va_canh_bao_la_vang():
    css = _doc("web", "components", "KhoiVanHanh.css")
    assert ".c-vang{background:var(--vtos-warning)}" in css, "mức Cảnh báo phải vàng"
    assert ".c-xanh{background:var(--vtos-info)}" in css
    assert ".vh-muc.warn{color:var(--vtos-warning)" in css
    tsx = _doc("web", "components", "KhoiVanHanh.tsx")
    assert 'red: "c-do", warn: "c-vang", info: "c-xanh"' in tsx


def test_ks_muc_3_cau_canh_bao_nao_cung_co_mau():
    """KS-MUC2: lớp «warn» / «red» / «note» gắn mà không có kiểu tô thì câu cảnh báo hiện như chữ
    thường. Trang nào dùng lớp trơn ấy phải tự khai nó trong `<style jsx>` của CHÍNH thành phần đó;
    còn lại dùng bộ dùng chung `cb-do` / `cb-vang` / `so-do` / `so-vang` / `so-xanh-la`."""
    g = _doc("web", "app", "globals.css")
    for lop in (".cb-do{", ".cb-vang{", ".so-do{", ".so-vang{", ".so-xanh-la{"):
        assert lop in g, lop
    xau = []
    for thu_muc in ("app", "components"):
        for goc, _, tep in os.walk(os.path.join(GOC, "web", thu_muc)):
            for t in tep:
                if not t.endswith(".tsx"):
                    continue
                p = os.path.join(goc, t)
                s = open(p, encoding="utf-8").read()
                # chia theo thành phần: mỗi `function X(` là một phạm vi <style jsx> riêng
                phan = re.split(r"\n(?:export )?(?:default )?function ", s)
                for k in phan:
                    dung = set(re.findall(r'className=\{?"(warn|red|note[^"]*)"', k))
                    for m in re.findall(r'className=\{[^}]*?\? "(red|warn)" : "(red|warn)"', k):
                        dung |= set(m)
                    if not dung:
                        continue
                    for lop in dung:
                        ten = lop.split()[0]
                        if not re.search(r"^\s*\." + re.escape(ten) + r"\s*\{", k, re.M):
                            xau.append(f"{os.path.relpath(p, GOC)}: «{lop}»")
    assert not xau, "lớp cảnh báo không có kiểu tô:\n" + "\n".join(sorted(set(xau)))


def test_ks_muc_4_cong_khach_bao_loi_va_cho_mat_tien_khong_navy():
    """KS-MUC3 (08/11/2026): cổng kh/dt/ir đổi «tất cả đỏ sang navy» (#699, #704) nhưng báo lỗi,
    «chỉ còn N phòng», tiền hoàn khi hủy, nút Hủy đơn và dấu ✕ «không bao gồm» là CẢNH BÁO, không
    phải trang trí — Chủ tịch duyệt trả màu cũ. Giá, nút chính, hero vẫn navy."""
    navy = ("#1E63C8", "#14538D", "#E8F0FB")
    vtd = _doc("web", "public", "cong", "vtd.css")
    ks = _doc("web", "components", "cong", "KhachSanVtd.tsx")
    tr = _doc("web", "components", "cong", "ToursAgoda.tsx")
    for nguon, chon in ((vtd, ".v4-error{"), (vtd, ".cong-loi{"), (ks, ".ksv-loi{"), (ks, ".ksv13-it{"),
                        (ks, ".ksv13-do{"), (ks, ".ksv13-huy{"), (tr, ".tra-ko li::before{")):
        k = _khoi(nguon, chon)
        assert not any(m.lower() in k.lower() for m in navy), f"{chon} lại bị tô navy: {k}"
