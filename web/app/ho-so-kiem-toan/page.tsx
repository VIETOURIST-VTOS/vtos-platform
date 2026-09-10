"use client";
/** Hồ sơ kiểm toán – V7 Đợt 3 (10/9/2026).
 *
 *  ĐỪNG NHẦM VỚI /audit. Màn hình Nhật ký nghiệp vụ (/audit) là sổ thao tác bất biến do máy tự ghi, và
 *  nó CHỈ XEM. Màn hình này là hồ sơ ta giao cho kiểm toán viên: kỳ nào, đơn vị nào, họ hỏi những tài
 *  liệu gì, ai bên mình phụ trách từng mục, đã gửi chưa, và cuối cùng ý kiến kiểm toán là gì.
 *
 *  Bảng bút toán điều chỉnh KHÔNG có ô số tiền. Điều chỉnh sau soát xét là bút toán thật ở sổ; ở đây
 *  chỉ giữ số hiệu bút toán đã ghi. Có ô số tiền tại đây thì sổ và bản giải trình cho kiểm toán sẽ có
 *  ngày nói hai con số khác nhau. */
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import DinhKem from "@/components/DinhKem";

const RONG = { ky: "", loai: "soat_xet", company_id: "", don_vi_kiem_toan: "", so_hop_dong: "",
               nguoi_dau_moi: "", ngay_bat_dau: "", han_hoan_thanh: "", ghi_chu: "", dung_mau: true };
const MAU: Record<string, string> = { chuan_bi: "grey", dang_cung_cap: "warn", dang_soat_xet: "warn",
                                      co_y_kien: "warn", da_phat_hanh: "ok", dong: "ok" };
const MAU_MUC: Record<string, string> = { chua_gui: "red", da_gui: "warn", hoi_them: "red",
                                          chap_nhan: "ok", khong_can: "grey" };

function HoSoKiemToan() {
  const { toast } = useShell();
  const [meta, setMeta] = useState<any>({ loai: {}, trang_thai: {}, y_kien: {}, muc_trang_thai: {},
                                          dc_trang_thai: {}, nhom_ho_so: {} });
  const [ds, setDs] = useState<any[]>([]);
  const [ct, setCt] = useState<any>(null);
  const [cty, setCty] = useState<any[]>([]);
  const [f, setF] = useState<any>({ ...RONG });
  const [hien, setHien] = useState(false);
  const [mucMoi, setMucMoi] = useState<any>({ ten: "", nhom_ho_so: "08_Kiem_toan", phong_ban: "ketoan", nguoi_phu_trach: "", han_nop: "" });
  const [dcMoi, setDcMoi] = useState("");
  const [ph, setPh] = useState<any>({ loai_y_kien: "chap_nhan_toan_phan", so_bao_cao: "", ngay_bao_cao: "", van_de_nhan_manh: "" });

  const load = useCallback(() => {
    api("/kiem-toan").then(setDs).catch((e) => toast(errMsg(e), true));
  }, []); // eslint-disable-line
  useEffect(() => {
    api("/kiem-toan/meta").then(setMeta).catch(() => {});
    api("/companies").then((r) => setCty(Array.isArray(r) ? r : r.rows || [])).catch(() => {});
  }, []);
  useEffect(load, [load]);

  const moHoSo = (id: number) => {
    if (ct?.id === id) { setCt(null); return; }
    api(`/kiem-toan/${id}`).then(setCt).catch((e) => toast(errMsg(e), true));
  };
  const lamMoi = () => { load(); if (ct) api(`/kiem-toan/${ct.id}`).then(setCt).catch(() => {}); };

  const post = async (p: string, json?: any, method = "POST") => {
    try { const r = await api(p, { method, json }); toast(r.message || "Xong"); lamMoi(); return r; }
    catch (x) { toast(errMsg(x), true); }
  };

  const lap = () => post("/kiem-toan", {
    ...f, company_id: f.company_id ? Number(f.company_id) : null,
    ngay_bat_dau: f.ngay_bat_dau || null, han_hoan_thanh: f.han_hoan_thanh || null,
  }).then((r) => { if (r) { setF({ ...RONG }); setHien(false); moHoSo(r.id); } });

  return (<>
    <h1>Hồ sơ kiểm toán</h1>
    <p className="muted">Hồ sơ ta <b>giao cho kiểm toán viên</b>: kỳ nào, đơn vị nào, họ yêu cầu tài liệu gì, ai phụ trách
      từng mục, đã gửi chưa. Khác với <b>Nhật ký nghiệp vụ</b> (mục “Kiểm soát &amp; Chính sách”) — đó là sổ thao tác bất
      biến do máy tự ghi. Bảng điều chỉnh dưới đây <b>không có ô số tiền</b>: bút toán điều chỉnh nằm ở sổ, ở đây chỉ
      giữ số hiệu.</p>

    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "10px 0" }}>
      <button className="act" onClick={() => setHien(!hien)}>{hien ? "Đóng biểu mẫu" : "+ Lập hồ sơ kiểm toán"}</button>
    </div>

    {hien && <div className="panel"><h2>Hồ sơ kiểm toán mới</h2>
      <div className="grid">
        <label>Kỳ *<input value={f.ky} onChange={(e) => setF({ ...f, ky: e.target.value })} placeholder="2026H1 · 2026 · 2026Q3" /></label>
        <label>Loại *<select value={f.loai} onChange={(e) => setF({ ...f, loai: e.target.value })}>
          {Object.entries(meta.loai).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Pháp nhân được kiểm toán<select value={f.company_id} onChange={(e) => setF({ ...f, company_id: e.target.value })}>
          <option value="">— chưa xác định —</option>
          {cty.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
        <label>Đơn vị kiểm toán *<input value={f.don_vi_kiem_toan} onChange={(e) => setF({ ...f, don_vi_kiem_toan: e.target.value })} placeholder="Baker Tilly A&C" /></label>
        <label>Số hợp đồng kiểm toán<input value={f.so_hop_dong} onChange={(e) => setF({ ...f, so_hop_dong: e.target.value })} /></label>
        <label>Người đầu mối bên mình<input value={f.nguoi_dau_moi} onChange={(e) => setF({ ...f, nguoi_dau_moi: e.target.value })} /></label>
        <label>Ngày bắt đầu<input type="date" value={f.ngay_bat_dau} onChange={(e) => setF({ ...f, ngay_bat_dau: e.target.value })} /></label>
        <label>Hạn hoàn thành<input type="date" value={f.han_hoan_thanh} onChange={(e) => setF({ ...f, han_hoan_thanh: e.target.value })} /></label>
      </div>
      <label>Ghi chú<textarea rows={2} style={{ width: "100%" }} value={f.ghi_chu} onChange={(e) => setF({ ...f, ghi_chu: e.target.value })} /></label>
      <label><input type="checkbox" checked={f.dung_mau} onChange={(e) => setF({ ...f, dung_mau: e.target.checked })} /> Nạp sẵn danh mục tài liệu mẫu ({meta.mau_danh_muc?.length || 0} mục) — vẫn thêm, sửa, bỏ được sau</label>
      <button className="act" disabled={!f.ky || !f.don_vi_kiem_toan} onClick={lap}>Lập hồ sơ</button>
    </div>}

    <div className="panel wrap"><table><thead><tr>
      <th>Mã</th><th>Kỳ</th><th>Loại</th><th>Pháp nhân</th><th>Đơn vị kiểm toán</th><th>Tiến độ</th><th>Trạng thái</th><th></th>
    </tr></thead><tbody>
      {ds.map((h) => <tr key={h.id}>
        <td><b>{h.code}</b></td>
        <td>{h.ky}</td>
        <td>{h.loai_ten}</td>
        <td>{h.company_name || <i className="muted">chưa xác định</i>}</td>
        <td>{h.don_vi_kiem_toan}<div className="muted">{h.so_hop_dong}</div></td>
        <td>{h.tong_muc - h.con_thieu}/{h.tong_muc} mục{h.tre_han > 0 && <Tag cls="red">{h.tre_han} trễ hạn</Tag>}</td>
        <td><Tag cls={MAU[h.trang_thai] || "grey"}>{h.trang_thai_ten}</Tag>
          {h.loai_y_kien_ten && <div className="muted">{h.loai_y_kien_ten}</div>}</td>
        <td><button className="act grey" style={{ margin: 0, fontSize: 12 }} onClick={() => moHoSo(h.id)}>{ct?.id === h.id ? "Ẩn" : "Mở"}</button></td>
      </tr>)}
    </tbody></table>
    {ds.length === 0 && <p className="muted">Chưa có hồ sơ kiểm toán nào.</p>}
    </div>

    {ct && <div className="panel">
      <h2>{ct.code} · {ct.loai_ten} kỳ {ct.ky}</h2>
      <p className="muted">Đơn vị kiểm toán <b>{ct.don_vi_kiem_toan}</b>
        {ct.nguoi_dau_moi && <> · đầu mối bên mình <b>{ct.nguoi_dau_moi}</b></>}
        {ct.han_hoan_thanh && <> · hạn hoàn thành {fmtD(ct.han_hoan_thanh)}</>}</p>
      {ct.so_bao_cao && <p><b>Báo cáo:</b> {ct.so_bao_cao} ngày {fmtD(ct.ngay_bao_cao)} — <b>{ct.loai_y_kien_ten}</b></p>}
      {ct.van_de_nhan_manh && <p><b>Cơ sở của ý kiến / vấn đề nhấn mạnh:</b> {ct.van_de_nhan_manh}</p>}

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "8px 0" }}>
        {ct.chuyen_duoc?.filter((t: string) => t !== "da_phat_hanh").map((t: string) =>
          <button key={t} className="act grey" onClick={() => post(`/kiem-toan/${ct.id}/chuyen`, { trang_thai: t })}>→ {meta.trang_thai[t]}</button>)}
        <button className="act grey" onClick={() => post(`/kiem-toan/${ct.id}/danh-muc-mau`)}>Bổ sung danh mục mẫu</button>
      </div>

      {ct.chuyen_duoc?.includes("da_phat_hanh") && <div className="panel" style={{ background: "var(--bg2)" }}>
        <h3>Phát hành báo cáo kiểm toán</h3>
        <p className="muted">Chỉ phát hành được khi mọi mục đã gửi xong hoặc đã đánh dấu không áp dụng kèm lý do.
          Hiện còn <b>{ct.con_thieu}</b> mục chưa xong.</p>
        <div className="grid">
          <label>Loại ý kiến *<select value={ph.loai_y_kien} onChange={(e) => setPh({ ...ph, loai_y_kien: e.target.value })}>
            {Object.entries(meta.y_kien).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
          <label>Số báo cáo *<input value={ph.so_bao_cao} onChange={(e) => setPh({ ...ph, so_bao_cao: e.target.value })} placeholder="4.0299/26/TC-AC" /></label>
          <label>Ngày báo cáo<input type="date" value={ph.ngay_bao_cao} onChange={(e) => setPh({ ...ph, ngay_bao_cao: e.target.value })} /></label>
        </div>
        <label>Cơ sở của ý kiến / vấn đề nhấn mạnh {ph.loai_y_kien !== "chap_nhan_toan_phan" && <b style={{ color: "var(--red)" }}>*</b>}
          <i className="muted"> (nguyên văn của kiểm toán)</i>
          <textarea rows={3} style={{ width: "100%" }} value={ph.van_de_nhan_manh} onChange={(e) => setPh({ ...ph, van_de_nhan_manh: e.target.value })} /></label>
        <button className="act" onClick={() => post(`/kiem-toan/${ct.id}/chuyen`, { trang_thai: "da_phat_hanh", ...ph, ngay_bao_cao: ph.ngay_bao_cao || null })}>Phát hành</button>
      </div>}

      <h3>Danh mục tài liệu ({ct.tong_muc} mục · còn thiếu {ct.con_thieu})</h3>
      <div className="wrap"><table><thead><tr>
        <th>#</th><th>Tài liệu</th><th>Nhóm hồ sơ</th><th>Phụ trách</th><th>Hạn</th><th>Tệp</th><th>Trạng thái</th>
      </tr></thead><tbody>
        {(ct.muc || []).map((m: any) => [
          <tr key={m.id}>
            <td>{m.stt}</td>
            <td>{m.ten}{m.cau_hoi && <div className="muted"><b>Kiểm toán hỏi:</b> {m.cau_hoi}</div>}
              {m.tra_loi && <div className="muted"><b>Ta trả lời:</b> {m.tra_loi}</div>}</td>
            <td className="muted">{m.nhom_ho_so_ten}</td>
            <td>{m.phong_ban}<div className="muted">{m.nguoi_phu_trach}</div></td>
            <td>{fmtD(m.han_nop)}{m.tre_han && <Tag cls="red">trễ</Tag>}</td>
            <td>{m.so_tep}</td>
            <td><select value={m.trang_thai} onChange={(e) => post(`/kiem-toan/muc/${m.id}`, { trang_thai: e.target.value }, "PATCH")}>
              {Object.entries(meta.muc_trang_thai).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select>
              <div><Tag cls={MAU_MUC[m.trang_thai] || "grey"}>{m.trang_thai_ten}</Tag></div></td>
          </tr>,
          <tr key={m.id + "t"}><td colSpan={7} style={{ background: "var(--bg2)" }}>
            <div className="grid">
              <label>Người phụ trách<input defaultValue={m.nguoi_phu_trach} onBlur={(e) => e.target.value !== m.nguoi_phu_trach && post(`/kiem-toan/muc/${m.id}`, { nguoi_phu_trach: e.target.value }, "PATCH")} /></label>
              <label>Hạn nộp<input type="date" defaultValue={m.han_nop || ""} onBlur={(e) => post(`/kiem-toan/muc/${m.id}`, { han_nop: e.target.value || null }, "PATCH")} /></label>
              <label>Kiểm toán hỏi thêm<input defaultValue={m.cau_hoi} onBlur={(e) => e.target.value !== m.cau_hoi && post(`/kiem-toan/muc/${m.id}`, { cau_hoi: e.target.value }, "PATCH")} /></label>
              <label>Ta trả lời<input defaultValue={m.tra_loi} onBlur={(e) => e.target.value !== m.tra_loi && post(`/kiem-toan/muc/${m.id}`, { tra_loi: e.target.value }, "PATCH")} /></label>
              <label>Ghi chú / lý do không áp dụng<input defaultValue={m.ghi_chu} onBlur={(e) => e.target.value !== m.ghi_chu && post(`/kiem-toan/muc/${m.id}`, { ghi_chu: e.target.value }, "PATCH")} /></label>
            </div>
            <DinhKem doiTuong="ho_so_kiem_toan_muc" doiTuongId={m.id} loai="chung_tu"
                     tieuDe={`Tài liệu gửi kiểm toán – mục #${m.stt}`} />
          </td></tr>,
        ])}
      </tbody></table></div>

      <div className="panel" style={{ background: "var(--bg2)" }}>
        <h3>Thêm mục ngoài danh mục mẫu</h3>
        <div className="grid">
          <label>Tên tài liệu *<input value={mucMoi.ten} onChange={(e) => setMucMoi({ ...mucMoi, ten: e.target.value })} /></label>
          <label>Nhóm hồ sơ<select value={mucMoi.nhom_ho_so} onChange={(e) => setMucMoi({ ...mucMoi, nhom_ho_so: e.target.value })}>
            {Object.entries(meta.nhom_ho_so).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
          <label>Phòng phụ trách<input value={mucMoi.phong_ban} onChange={(e) => setMucMoi({ ...mucMoi, phong_ban: e.target.value })} /></label>
          <label>Người phụ trách<input value={mucMoi.nguoi_phu_trach} onChange={(e) => setMucMoi({ ...mucMoi, nguoi_phu_trach: e.target.value })} /></label>
          <label>Hạn nộp<input type="date" value={mucMoi.han_nop} onChange={(e) => setMucMoi({ ...mucMoi, han_nop: e.target.value })} /></label>
        </div>
        <button className="act" disabled={!mucMoi.ten.trim()} onClick={() => post(`/kiem-toan/${ct.id}/muc`, { ...mucMoi, han_nop: mucMoi.han_nop || null }).then((r) => { if (r) setMucMoi({ ...mucMoi, ten: "", nguoi_phu_trach: "" }); })}>Thêm mục</button>
      </div>

      <h3>Bút toán điều chỉnh kiểm toán đề nghị</h3>
      <p className="muted">Không có ô số tiền ở đây. Điều chỉnh là bút toán thật ở sổ — đánh dấu “đã ghi sổ” thì phải kèm
        số hiệu bút toán; không đồng ý thì phải nêu lý do, vì kiểm toán sẽ hỏi lại bằng văn bản.</p>
      <div className="wrap"><table><thead><tr>
        <th>Nội dung</th><th>Bút toán</th><th>Trạng thái</th><th>Người quyết</th><th></th>
      </tr></thead><tbody>
        {(ct.dieu_chinh || []).map((d: any) => <tr key={d.id}>
          <td>{d.noi_dung}{d.ly_do && <div className="muted"><b>Lý do:</b> {d.ly_do}</div>}</td>
          <td className="mono">{d.journal_entry_id ? `#${d.journal_entry_id}` : "—"}<div className="muted">{d.journal_entry_ref}</div></td>
          <td><Tag cls={d.trang_thai === "da_ghi_so" ? "ok" : d.trang_thai === "khong_dong_y" ? "red" : "warn"}>{d.trang_thai_ten}</Tag></td>
          <td className="muted">{d.nguoi_quyet || "—"}</td>
          <td>{d.trang_thai === "de_xuat" && <QuyetDieuChinh id={d.id} onXong={(json: any) => post(`/kiem-toan/dieu-chinh/${d.id}/quyet`, json)} />}</td>
        </tr>)}
      </tbody></table></div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <input style={{ flex: "1 1 340px" }} value={dcMoi} onChange={(e) => setDcMoi(e.target.value)} placeholder="Kiểm toán đề nghị điều chỉnh nội dung gì" />
        <button className="act" disabled={!dcMoi.trim()} onClick={() => post(`/kiem-toan/${ct.id}/dieu-chinh`, { noi_dung: dcMoi }).then((r) => { if (r) setDcMoi(""); })}>Ghi nhận điều chỉnh</button>
      </div>
    </div>}
  </>);
}

function QuyetDieuChinh({ id, onXong }: { id: number; onXong: (json: any) => void }) {
  const [mo, setMo] = useState(false);
  const [tt, setTt] = useState("da_ghi_so");
  const [je, setJe] = useState("");
  const [ly, setLy] = useState("");
  if (!mo) return <button className="act grey" style={{ margin: 0, fontSize: 12 }} onClick={() => setMo(true)}>Quyết</button>;
  return (<div>
    <select value={tt} onChange={(e) => setTt(e.target.value)}>
      <option value="da_ghi_so">Đã ghi sổ</option>
      <option value="khong_dong_y">Công ty không đồng ý</option>
    </select>
    {tt === "da_ghi_so"
      ? <input type="number" value={je} onChange={(e) => setJe(e.target.value)} placeholder="Số hiệu bút toán" />
      : <input value={ly} onChange={(e) => setLy(e.target.value)} placeholder="Lý do (≥ 20 ký tự)" />}
    <button className="act" style={{ margin: 0, fontSize: 12 }}
            onClick={() => { onXong({ trang_thai: tt, journal_entry_id: je ? Number(je) : null, ly_do: ly }); setMo(false); }}>Lưu</button>
  </div>);
}

export default function Page() { return <Shell><HoSoKiemToan /></Shell>; }
