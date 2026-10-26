"use client";
import { useCallback, useEffect, useState } from "react";
import { THANH_TREN } from "@/components/cong/manh";
import { goiCong, phienCong, xoaPhienCong } from "@/lib/cong";

/* CG-1 · KHÔNG GIAN SAU ĐĂNG NHẬP của cổng ngoài (khách hàng, đối tác, cổ đông).
   Đợt này làm cổng và tài khoản. Các phân hệ (đặt dịch vụ, đơn, điểm, ưu đãi cổ đông…) là đợt sau —
   hiện «Đang xây dựng», KHÔNG hiện số mẫu như thật. Đối tác / cổ đông chưa duyệt chỉ gửi được hồ sơ. */
const PHAN_HE: Record<string, [string, string, string][]> = {
  khach_hang: [["Đặt dịch vụ", "Tour du lịch · Khách sạn · Nhà hàng & ẩm thực", "xay"], ["Đơn của tôi", "Chỉ đơn đã nối với tài khoản có chứng cứ", "xay"],
    ["Điểm & ưu đãi", "Chờ duyệt chính sách điểm", "cho"], ["Hỗ trợ", "Góp ý, khiếu nại tới Vietourist", "xay"]],
  doi_tac: [["Dịch vụ cung cấp / Báo giá & bán / Khách giới thiệu", "Tour du lịch · Khách sạn · Nhà hàng & ẩm thực", "xay"],
    ["Công nợ & đối soát", "Phải thu – phải trả theo hợp đồng", "xay"], ["Hoa hồng (D06)", "Lũy tiến theo tháng — chờ cấu hình phạm vi", "cho"]],
  co_dong: [["Công bố thông tin & đại hội", "Tài liệu IR công khai", "xay"], ["Ưu đãi cổ đông", "Tour · Khách sạn · Nhà hàng — chờ duyệt chính sách", "cho"],
    ["Quan hệ nhà đầu tư", "Gửi câu hỏi tới IR", "xay"]],
};

export default function Cong() {
  const [toi, setToi] = useState<any>(null);
  const [f, setF] = useState<any>({ ho_ten: "", loai_doi_tac: "", ten_don_vi: "", ma_so_thue: "", giay_to: "", tk_luu_ky: "", ghi_chu: "" });
  const [msg, setMsg] = useState(""); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const tai = useCallback(() => goiCong("/toi").then((t) => {
    setToi(t);
    setF((x: any) => ({ ...x, ho_ten: t.ho_ten || x.ho_ten, loai_doi_tac: t.loai_doi_tac || x.loai_doi_tac, ten_don_vi: t.ten_don_vi || x.ten_don_vi,
      ma_so_thue: t.ma_so_thue || x.ma_so_thue, tk_luu_ky: t.tk_luu_ky || x.tk_luu_ky, ghi_chu: t.ghi_chu_ho_so || x.ghi_chu }));
  }).catch(() => { xoaPhienCong(); location.replace("/login"); }), []);
  useEffect(() => { if (!phienCong()) { location.replace("/login"); return; } tai(); }, [tai]);
  const guiHoSo = async () => {
    setBusy(true); setErr(""); setMsg("");
    try { const r = await goiCong("/ho-so", f); setMsg(r.message); setToi(r.toi); } catch (x: any) { setErr(x.message); } finally { setBusy(false); }
  };
  const luuToi = async (patch: any) => { try { setToi(await goiCong("/toi", patch)); setMsg("Đã lưu"); } catch (x: any) { setErr(x.message); } };
  const thoat = async () => { try { await goiCong("/dang-xuat", {}); } catch { /* phiên đã hết thì thôi */ } xoaPhienCong(); location.replace("/login"); };
  const o = (k: string, nhan: string, ph = "") => <label className="v3-field">{nhan}<input value={f[k]} placeholder={ph} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></label>;
  const role = toi?.loai === "doi_tac" ? "doi-tac" : toi?.loai === "co_dong" ? "co-dong" : "khach-hang";
  const canHoSo = toi && toi.loai !== "khach_hang" && ["ho_so", "bo_sung"].includes(toi.trang_thai);
  return (<>
    <link rel="stylesheet" href="/cong/vtd.css?v=34b" />
    <div style={{ background: "#081826", minHeight: "100vh" }}>
      <div id="vtd-access" data-mode="inline" data-page="login" data-role={role} data-preview="off" data-vtos-screen="off" data-vtos-menu="closed">
        <div id="vtd-screen">
          <div style={{ display: "contents" }} dangerouslySetInnerHTML={{ __html: THANH_TREN }} />
          {!toi ? <p style={{ color: "#a9b9ce", padding: 24 }}>Đang tải…</p> : <div data-role={role}><div className="v4-auth">
            <nav className="vtd-breadcrumb"><span>{toi.loai_ten}</span><span>·</span><span>{toi.dien_thoai || toi.email}</span>
              <button type="button" className="v3-button v3-secondary cursor-interaction" style={{ marginLeft: "auto" }} onClick={thoat}>Đăng xuất</button></nav>
            <main className="vtd-login" style={{ gridTemplateColumns: "1fr" }}>
              <section className="vtd-form">
                <h2>Xin chào{toi.ho_ten ? `, ${toi.ho_ten}` : ""}</h2>
                <p>Trạng thái tài khoản: <b>{toi.trang_thai_ten}</b>{toi.ly_do && <> — {toi.ly_do}</>}</p>
                {msg && <div className="cong-ok">{msg}</div>}{err && <div className="cong-loi">{err}</div>}

                {canHoSo && <>
                  <h3 style={{ margin: "10px 0 4px" }}>{toi.loai === "doi_tac" ? "Hồ sơ đối tác" : "Hồ sơ xác minh cổ đông"}</h3>
                  <p>{toi.loai === "doi_tac" ? "Vietourist đối chiếu thông tin rồi duyệt; được duyệt mới mở không gian đối tác." : "IR – Pháp chế đối chiếu sổ cổ đông rồi xác minh; chưa xác minh thì chưa có ưu đãi, chưa xem hồ sơ sở hữu."}</p>
                  {o("ho_ten", toi.loai === "doi_tac" ? "Họ tên người đại diện" : "Họ tên / tên tổ chức")}
                  {toi.loai === "doi_tac" ? <>
                    <label className="v3-field">Loại đối tác<select value={f.loai_doi_tac} onChange={(e) => setF({ ...f, loai_doi_tac: e.target.value })}>
                      <option value="">— chọn —</option>{Object.entries(toi.loai_doi_tac_chon).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
                    {o("ten_don_vi", "Tên đơn vị")}{o("ma_so_thue", "Mã số thuế")}
                  </> : <>{o("giay_to", "Số CCCD / mã số doanh nghiệp")}{o("tk_luu_ky", "Tài khoản lưu ký (nếu có)")}</>}
                  <label className="v3-field">Ghi chú<textarea rows={3} value={f.ghi_chu} onChange={(e) => setF({ ...f, ghi_chu: e.target.value })} /></label>
                  <div className="v4-actions"><button type="button" className="v3-button v3-primary cursor-interaction" disabled={busy} onClick={guiHoSo}>{busy ? "Đang gửi…" : "Gửi hồ sơ"}</button></div>
                </>}
                {toi.trang_thai === "cho_duyet" && <div className="cong-ok">Hồ sơ đã gửi lúc {String(toi.gui_ho_so_luc || "").slice(0, 16).replace("T", " ")} — đang chờ Vietourist duyệt.</div>}

                {toi.trang_thai === "hoat_dong" && <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 10, margin: "10px 0" }}>
                  {(PHAN_HE[toi.loai] || []).map(([t, m, s]) => <div key={t} style={{ border: "1px solid #dfe6ef", borderRadius: 12, padding: 12, color: "#142a43" }}>
                    <b>{t}</b><div style={{ fontSize: 13, color: "#52677f" }}>{m}</div>
                    <span style={{ fontSize: 12, fontWeight: 700, borderRadius: 6, padding: "2px 8px", background: s === "cho" ? "#fbf1dc" : "#eef3f8", color: s === "cho" ? "#8a5a00" : "#52677f" }}>{s === "cho" ? "Chờ duyệt chính sách" : "Đang xây dựng"}</span></div>)}
                </div>}

                <h3 style={{ margin: "14px 0 4px" }}>Hồ sơ & riêng tư</h3>
                {toi.loai === "khach_hang" && <label className="v3-field">Họ tên<input defaultValue={toi.ho_ten} onBlur={(e) => e.target.value !== toi.ho_ten && luuToi({ ho_ten: e.target.value })} /></label>}
                <label className="cong-dong-y"><input type="checkbox" checked={!!toi.nhan_tin_quang_cao} onChange={(e) => luuToi({ nhan_tin_quang_cao: e.target.checked })} />
                  <span>Nhận tin ưu đãi từ Vietourist (tự nguyện, bỏ chọn bất cứ lúc nào).</span></label>
                <p className="vtd-form-notice">Liên hệ đăng nhập: {toi.dien_thoai || toi.email}. Đổi liên hệ cần xác thực lại — liên hệ Vietourist.</p>
              </section>
            </main></div></div>}
        </div>
      </div>
    </div>
  </>);
}
