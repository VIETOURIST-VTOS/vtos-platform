"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import { useHoi } from "@/components/HopHoi";

/** Danh mục pháp nhân và đối chiếu công ty chủ quản của hồ sơ (Ý kiến thẩm định 06/9/2026 – Đợt 2 mục 2).
 *  Màn hình này cố ý KHÔNG có nút "gán tất cả về công ty mẹ": rỗng nghĩa là chưa xác định, và gán sai
 *  pháp nhân làm sai cả báo cáo từng đơn vị lẫn phần loại trừ giao dịch nội bộ khi hợp nhất. */
const KINDS: [string, string][] = [["tour", "Chuyến tour"], ["booking", "Booking"], ["receipt", "Phiếu thu"], ["chi", "Đề nghị chi"], ["chung_tu", "Chứng từ ghi sổ"]];

function Companies() {
  const { xacNhan, nhap, hop } = useHoi();
  const { user, toast } = useShell();
  const role = user?.role || "";
  const canWrite = ["cntt", "ketoan", "tgd", "chutich", "tp_dh", "ptgd_doan"].includes(role);
  const [cos, setCos] = useState<any[]>([]);
  const [cov, setCov] = useState<any>(null);
  const [hr, setHr] = useState<any>(null);
  const [kind, setKind] = useState("tour");
  const [pend, setPend] = useState<any>(null);
  const [sel, setSel] = useState<number[]>([]);
  const [co, setCo] = useState("");
  const [lo, setLo] = useState<any>({ company_id: "", nguon: "vietrip", tu_ngay: "", den_ngay: "", loai: "", chi_chua_gan: true });
  const [grp, setGrp] = useState<any>(null);
  const [lo2, setLo2] = useState<any>({ company_id: "", tu_ky: "", den_ky: "", nguon: "", nhom: "", khong_co_tour: true, chi_chua_gan: true });
  const [lh, setLh] = useState<any>({ id: "", address: "", phone: "" });   // KS-20e: địa chỉ + hotline in trên phiếu
  const chonLh = (id: string) => { const c = cos.find((x) => String(x.id) === id); setLh({ id, address: c?.address || "", phone: c?.phone || "" }); };
  useEffect(() => { if (!lh.id && cos.length) { const me = cos.find((c) => c.kind === "me") || cos[0]; setLh({ id: String(me.id), address: me.address || "", phone: me.phone || "" }); } }, [cos]);  // eslint-disable-line react-hooks/exhaustive-deps

  const load = useCallback(() => {
    api("/companies").then(setCos).catch(() => {});
    api("/companies/scope/coverage").then(setCov).catch(() => {});
    api("/companies/coverage").then(setHr).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);
  const loadPend = useCallback(() => {
    setSel([]); setGrp(null);
    api(`/companies/scope/${kind}/pending?limit=200`).then(setPend).catch(() => {});
    if (kind === "chung_tu" || kind === "chi") api(`/companies/scope/${kind}/groups`).then(setGrp).catch(() => {});
  }, [kind]);
  useEffect(() => { loadPend(); }, [loadPend]);

  const post = async (path: string, json?: any) => {
    try { const r = await api(path, { method: "POST", json }); toast(r.message || `Đã xử lý ${r.tong ?? r.da_gan ?? ""}`); load(); loadPend(); return r; }
    catch (x) { toast(errMsg(x), true); }
  };
  const gan = () => { if (!co) return toast("Chọn pháp nhân trước", true); post(`/companies/scope/${kind}/assign`, { ids: sel, company_id: Number(co) }); };
  const toggle = (id: number) => setSel((s) => s.includes(id) ? s.filter((x) => x !== id) : [...s, id]);

  return (<>{hop}
    <h1>Pháp nhân &amp; công ty chủ quản của hồ sơ</h1>
    <p className="muted">Ô trống nghĩa là <b>chưa xác định</b>, không phải công ty mẹ. Hồ sơ chưa xác định nằm ở danh sách đối chiếu bên dưới cho tới khi người có thẩm quyền chỉ định – mọi lần gán đều vào nhật ký nghiệp vụ.</p>

    <div className="panel wrap"><h2>Danh mục pháp nhân</h2>
      <table><thead><tr><th>Mã</th><th>Tên</th><th>Mã số thuế</th><th>Quan hệ</th><th className="num">Tỷ lệ sở hữu</th><th>Hiệu lực từ</th><th>Phạm vi</th><th>Trạng thái</th></tr></thead>
        <tbody>{cos.map((c) => <tr key={c.id} style={{ opacity: c.active ? 1 : 0.55 }}><td className="mono"><b>{c.code}</b></td><td>{c.name}</td>
          <td className="mono">{c.tax_code || <Tag cls="warn">thiếu MST</Tag>}</td><td>{c.kind_label}</td><td className="num">{c.ownership_pct ? c.ownership_pct + "%" : "–"}</td><td>{fmtD(c.effective_from)}</td>
          <td>{c.in_group ? <Tag cls="navy">trong hợp nhất</Tag> : <Tag cls="warn">bên liên quan</Tag>}</td>
          <td>{c.active ? <Tag cls="ok">Đang hoạt động</Tag> : <Tag cls="red">Tạm ngưng</Tag>}</td></tr>)}</tbody></table>
      {canWrite && <div style={{ marginTop: 12 }}><h3>Địa chỉ &amp; hotline in trên phiếu</h3>
        <p className="muted">In trên phiếu xác nhận, hóa đơn đặt phòng VTD và chân email gửi khách (KS-20e). Ô trống thì giấy tờ ghi «chưa khai».</p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
          <label>Pháp nhân<select value={lh.id} onChange={(e) => chonLh(e.target.value)}>{cos.map((c) => <option key={c.id} value={c.id}>{c.code} · {c.name}</option>)}</select></label>
          <label style={{ flex: "1 1 260px" }}>Địa chỉ<input value={lh.address} maxLength={300} onChange={(e) => setLh({ ...lh, address: e.target.value })} /></label>
          <label>Hotline<input value={lh.phone} maxLength={40} onChange={(e) => setLh({ ...lh, phone: e.target.value })} /></label>
          <button className="act" disabled={!lh.id} onClick={() => post(`/companies/${lh.id}/lien-he`, { address: lh.address, phone: lh.phone })}>Lưu</button></div></div>}
      <p className="muted">Trong phạm vi hợp nhất: công ty mẹ, công ty con, chi nhánh – giao dịch giữa các đơn vị này là giao dịch nội bộ, phải loại trừ khi hợp nhất. Công ty liên kết hạch toán theo phương pháp vốn chủ sở hữu; công ty độc lập chỉ thuyết minh bên liên quan.</p></div>

    <div className="panel wrap"><h2>Mức độ đã xác định pháp nhân</h2>
      <table><thead><tr><th>Loại hồ sơ</th><th className="num">Tổng</th><th className="num">Đã xác định</th><th className="num">Còn phải đối chiếu</th><th className="num">Tỷ lệ</th><th>Cách xác định</th></tr></thead>
        <tbody>
          {(cov?.rows || []).map((r: any) => <tr key={r.kind}><td><b>{r.label}</b></td><td className="num">{r.tong}</td><td className="num">{r.da_gan}</td>
            <td className="num">{r.chua_gan ? <Tag cls="warn">{r.chua_gan}</Tag> : <Tag cls="ok">0</Tag>}</td><td className="num">{r.ty_le}%</td>
            <td className="muted">{r.suy_duoc_tu ? "suy được từ hồ sơ cha" : "phải do người chỉ định"}</td></tr>)}
          {hr && <><tr><td><b>Xe</b></td><td className="num">{hr.xe.tong}</td><td className="num">{hr.xe.da_gan}</td><td className="num">{hr.xe.chua_gan ? <Tag cls="warn">{hr.xe.chua_gan}</Tag> : <Tag cls="ok">0</Tag>}</td><td className="num">–</td><td className="muted">theo giấy đăng ký xe</td></tr>
            <tr><td><b>Hướng dẫn viên</b></td><td className="num">{hr.hdv.tong}</td><td className="num">{hr.hdv.da_gan}</td><td className="num">{hr.hdv.chua_gan ? <Tag cls="warn">{hr.hdv.chua_gan}</Tag> : <Tag cls="ok">0</Tag>}</td><td className="num">–</td><td className="muted">theo công ty ký hợp đồng</td></tr></>}
        </tbody></table>
      {canWrite && <button className="act orange" onClick={() => post("/companies/scope/derive")}>Suy pháp nhân từ hồ sơ cha</button>}
      <p className="muted">Suy từ hồ sơ cha: booking lấy theo chuyến tour, phiếu thu lấy theo booking, đề nghị chi và chứng từ ghi sổ lấy theo tour. Không đụng tới hồ sơ đã gán tay và không suy được cho tour – tour phải do Điều hành hoặc Kế toán chỉ định.</p></div>

    {canWrite && <div className="panel"><h2>Gán pháp nhân cho một lô tour theo tiêu chí</h2>
      <div className="grid">
        <label>Pháp nhân<select value={lo.company_id} onChange={(e) => setLo({ ...lo, company_id: e.target.value })}><option value="">– chọn –</option>{cos.filter((c) => c.active).map((c) => <option key={c.id} value={c.id}>{c.code} · {c.name}</option>)}</select></label>
        <label>Nguồn dữ liệu<select value={lo.nguon} onChange={(e) => setLo({ ...lo, nguon: e.target.value })}><option value="">Tất cả</option><option value="vietrip">Nhập từ Vietrip</option><option value="vtos">Tạo trên VTOS</option></select></label>
        <label>Khởi hành từ<input type="date" value={lo.tu_ngay} onChange={(e) => setLo({ ...lo, tu_ngay: e.target.value })} /></label>
        <label>Khởi hành đến<input type="date" value={lo.den_ngay} onChange={(e) => setLo({ ...lo, den_ngay: e.target.value })} /></label>
        <label><input type="checkbox" checked={lo.chi_chua_gan} onChange={(e) => setLo({ ...lo, chi_chua_gan: e.target.checked })} /> Chỉ tour chưa xác định</label>
      </div>
      <button className="act orange" disabled={!lo.company_id} onClick={async () => {
        const c = cos.find((x) => x.id === Number(lo.company_id));
        if (await xacNhan(`Gán ${c?.name} cho toàn bộ tour thỏa tiêu chí đang chọn? Tiêu chí và số hồ sơ sẽ được ghi vào nhật ký.`))
          post("/companies/scope/tour/assign-filter", { ...lo, company_id: Number(lo.company_id), tu_ngay: lo.tu_ngay || null, den_ngay: lo.den_ngay || null });
      }}>Gán theo tiêu chí</button>
      <p className="muted">Dùng khi phải xử lý hàng nghìn tour cũ. Tiêu chí đã nêu được lưu vào nhật ký để sau này truy lại được căn cứ vì sao một tour thuộc pháp nhân này chứ không phải pháp nhân kia.</p></div>}

    <div className="panel wrap"><h2>Danh sách đối chiếu – hồ sơ chưa xác định pháp nhân</h2>
      <div className="tabs">{KINDS.map(([k, l]) => <button key={k} type="button" className={k === kind ? "on" : ""} onClick={() => setKind(k)}>{l}{cov ? ` (${(cov.rows.find((r: any) => r.kind === k) || {}).chua_gan ?? 0})` : ""}</button>)}</div>
      {canWrite && <div className="grid" style={{ marginTop: 8 }}>
        <label>Gán {sel.length} hồ sơ đang chọn cho<select value={co} onChange={(e) => setCo(e.target.value)}><option value="">– chọn pháp nhân –</option>{cos.filter((c) => c.active).map((c) => <option key={c.id} value={c.id}>{c.code} · {c.name}</option>)}</select></label>
        <div><button className="act" disabled={!sel.length || !co} onClick={gan}>Gán cho hồ sơ đã chọn</button></div>
      </div>}
      {grp && grp.rows.length > 0 && <div style={{ margin: "8px 0" }}>
        <table><thead><tr><th>{grp.theo}</th><th className="num">Số hồ sơ chưa xác định</th></tr></thead>
          <tbody>{grp.rows.map((r: any, i: number) => <tr key={i}><td>{kind === "chung_tu" ? `${r.nguon} · kỳ ${r.ky}` : r.nhom}</td><td className="num">{r.so_luong}</td></tr>)}</tbody></table>
        <p className="muted">Nhóm theo tiêu chí để thấy cần bao nhiêu lần gán, chứ không phải bao nhiêu nghìn dòng phải bấm.</p>
      </div>}
      {canWrite && (kind === "chung_tu" || kind === "chi") && <div className="panel" style={{ marginBottom: 8 }}>
        <h3>Gán theo lô cho hồ sơ không gắn tour</h3>
        <div className="grid">
          <label>Pháp nhân<select value={lo2.company_id} onChange={(e) => setLo2({ ...lo2, company_id: e.target.value })}><option value="">– chọn –</option>{cos.filter((c) => c.active).map((c) => <option key={c.id} value={c.id}>{c.code} · {c.name}</option>)}</select></label>
          {kind === "chung_tu" && <><label>Kỳ từ<input placeholder="2026-01" value={lo2.tu_ky} onChange={(e) => setLo2({ ...lo2, tu_ky: e.target.value })} /></label>
            <label>Kỳ đến<input placeholder="2026-08" value={lo2.den_ky} onChange={(e) => setLo2({ ...lo2, den_ky: e.target.value })} /></label>
            <label>Nguồn chứng từ<input placeholder="misa, thu_tien…" value={lo2.nguon} onChange={(e) => setLo2({ ...lo2, nguon: e.target.value })} /></label></>}
          {kind === "chi" && <label>Nhóm chi<input placeholder="hanh_chinh, marketing…" value={lo2.nhom} onChange={(e) => setLo2({ ...lo2, nhom: e.target.value })} /></label>}
          <label><input type="checkbox" checked={lo2.khong_co_tour} onChange={(e) => setLo2({ ...lo2, khong_co_tour: e.target.checked })} /> Chỉ hồ sơ không gắn tour</label>
        </div>
        <button className="act orange" disabled={!lo2.company_id} onClick={async () => {
          const c = cos.find((x) => x.id === Number(lo2.company_id));
          if (await xacNhan(`Gán ${c?.name} cho toàn bộ hồ sơ thỏa tiêu chí đang chọn? Tiêu chí và số hồ sơ sẽ được ghi vào nhật ký.`))
            post(`/companies/scope/${kind}/assign-batch`, { ...lo2, company_id: Number(lo2.company_id) });
        }}>Gán theo lô</button>
        <p className="muted">Hồ sơ gắn tour đã đi theo tour ở bước &quot;suy từ hồ sơ cha&quot;. Phần còn lại là chi hành chính, chi marketing và chứng từ nạp từ MISA – Kế toán nhìn kỳ và nguồn chứng từ là biết thuộc sổ của pháp nhân nào.</p>
      </div>}
      <table><thead><tr>{canWrite && <th><input type="checkbox" checked={!!pend?.rows?.length && sel.length === pend.rows.length} onChange={(e) => setSel(e.target.checked ? (pend?.rows || []).map((r: any) => r.id) : [])} /></th>}<th>Mã</th><th>Nội dung</th></tr></thead>
        <tbody>{(pend?.rows || []).map((r: any) => <tr key={r.id}>{canWrite && <td><input type="checkbox" checked={sel.includes(r.id)} onChange={() => toggle(r.id)} /></td>}<td className="mono">{r.code}</td><td>{r.mo_ta}</td></tr>)}</tbody></table>
      {pend && <p className="muted">Còn <b>{pend.tong}</b> {pend.label.toLowerCase()} chưa xác định pháp nhân{pend.tong > (pend.rows || []).length ? ` – đang hiển thị ${pend.rows.length} bản ghi mới nhất` : ""}.</p>}
    </div>
  </>);
}

export default function Page() { return <Shell><Companies /></Shell>; }
