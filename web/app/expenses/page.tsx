"use client";
import { useEffect, useState, useCallback } from "react";
import DinhKem from "@/components/DinhKem";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

const CAT: Record<string, string> = { chi_tour: "Chi phí tour", marketing: "Marketing", hanh_chinh: "Hành chính", hoan_tien: "Hoàn tiền khách", tam_ung: "Tạm ứng HDV/NCC trước tour" };
const ST: Record<string, [string, string]> = { cho_tp: ["Chờ bộ phận", "warn"], cho_kt: ["Chờ Kế toán", "warn"], cho_duyet: ["Chờ duyệt", "warn"], cho_chi: ["Lệnh chi chờ", "navy"], da_chi: ["Đã chi", "ok"], tu_choi: ["Từ chối", "red"] };
const CONFIRMER: Record<string, string[]> = { chi_tour: ["tp_dh", "tgd"], marketing: ["ptgd_mkt", "tgd"], hanh_chinh: ["hcns", "tgd"], hoan_tien: ["gd_kd", "tp_dh", "tgd"], tam_ung: ["tp_dh", "tgd"] };

function Expenses() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const [tab, setTab] = useState("requests");
  const [tepDN, setTepDN] = useState("");   // mã đề nghị chi đang mở chứng từ
  const [filter, setFilter] = useState("cho_tp,cho_kt,cho_duyet,cho_chi");
  const [rows, setRows] = useState<any[]>([]);
  const [cf, setCf] = useState<any[]>([]);
  const [tours, setTours] = useState<any[]>([]);
  const [f, setF] = useState<any>({ category: "chi_tour", tour_id: "", supplier_name: "", supplier_tax_code: "", supplier_bank: "", amount: "", description: "", has_document: false, document_ref: "", has_invoice: false, ngay_den_han: "", marketing_muc: "", campaign_id: "" });
  // VPM-17 – danh sách đề nghị chi CHƯA ai gõ ngày phải trả. Mỗi dòng ở đây là một khoản tiền hệ
  // thống biết phải trả nhưng không biết trả NGÀY NÀO, nên không xếp được vào cột nào của bảng dòng tiền.
  const [thieuNgay, setThieuNgay] = useState<any>(null);
  // Hai ô của phiếu chi marketing. Cột `marketing_muc` và `campaign_id` của đề nghị chi có từ lâu
  // và API vẫn nhận, nhưng MÀN HÌNH NÀY CHƯA BAO GIỜ CÓ Ô NÀO — nên tới 24/9/2026 chưa một dòng
  // chi marketing nào được gắn hạng mục hay chiến dịch. Hệ quả: cổng ngân sách không bao giờ đối
  // chiếu được hạn mục nào, và bảng hiệu quả chiến dịch không có chi phí thực tế để chia.
  //
  // Danh mục lấy qua cửa của CHÍNH phân hệ đề nghị chi, không gọi sang /api/v1/marketing – xem
  // ghi chú ở api/v1/ops.py.
  const [dmMkt, setDmMkt] = useState<any>(null);
  const load = useCallback(() => {
    if (!tours.length) api("/tours").then((r) => setTours(r.rows || [])).catch(() => {});
    if (tab === "requests") api(`/payment-requests${filter ? `?status=${filter}` : ""}`).then(setRows);
    if (tab === "cashflow") api("/cashflow").then(setCf).catch((e) => toast(errMsg(e), true));
    if (tab === "thieu_ngay") api("/payment-requests/thieu-ngay-den-han").then(setThieuNgay).catch((e) => toast(errMsg(e), true));
  }, [tab, filter]); // eslint-disable-line
  // Chỉ nạp khi người dùng thật sự chọn Marketing: phần lớn phiếu chi là chi phí tour, không việc
  // gì bắt mọi người tải danh sách chiến dịch.
  useEffect(() => {
    if (f.category === "marketing" && !dmMkt) api("/payment-requests/danh-muc-marketing").then(setDmMkt).catch(() => {});
  }, [f.category, dmMkt]);
  useEffect(() => { load(); }, [load]);
  const post = async (path: string, json?: any) => { try { const r = await api(path, { method: "POST", json }); toast(r.message || "Xong"); load(); return r; } catch (x) { toast(errMsg(x), true); } };
  const step = (r: any, action: string, reason = "") => post(`/payment-requests/${r.id}/step`, { action, reason });
  // Gõ hoặc sửa ngày phải trả. Gửi rỗng = gỡ ngày, khoản ấy quay lại danh sách chưa có hạn — nhập
  // nhầm thì phải sửa lại được về "chưa biết", chứ không kẹt với một ngày sai.
  const datNgay = async (r: any) => {
    const cu = r.ngay_den_han ? String(r.ngay_den_han).slice(0, 10) : "";
    const v = prompt(`Ngày phải trả cho ${r.code} (dd/mm/yyyy hoặc yyyy-mm-dd).\nĐể TRỐNG rồi bấm OK = gỡ ngày, khoản này quay lại danh sách chưa có hạn.`, cu);
    if (v === null) return;
    const t = v.trim();
    let iso: string | null = null;
    if (t) {
      const vn = t.match(/^(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})$/);
      iso = vn ? `${vn[3]}-${vn[2].padStart(2, "0")}-${vn[1].padStart(2, "0")}` : t;
      if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) { toast("Ngày không hợp lệ – gõ dd/mm/yyyy", true); return; }
    }
    try { const kq = await api(`/payment-requests/${r.id}/ngay-den-han`, { method: "PUT", json: { ngay_den_han: iso } }); toast(kq.message || "Xong"); load(); }
    catch (x) { toast(errMsg(x), true); }
  };
  const canCreate = ["nv_dh", "tp_dh", "ptgd_mkt", "hcns", "cntt", "gd_kd", "nv_kd"].includes(role);
  const actions = (r: any) => {
    const out: any[] = [];
    if (r.status === "cho_tp" && CONFIRMER[r.category]?.includes(role)) out.push(["Xác nhận", "confirm", "teal"]);
    if (r.status === "cho_kt" && role === "ketoan") out.push(["Kế toán kiểm tra", "check", "teal"]);
    // Chi MARKETING đi MỘT chữ ký, và là chữ ký của P.TGĐ Marketing (Chủ tịch chốt 23/9/2026).
    // TGĐ và Chủ tịch vẫn THẤY hồ sơ trong danh sách — chỉ không có nút bấm. Đó đúng là điều đã
    // chốt: "dữ liệu vẫn đẩy lên cho TGĐ và CT xem, và không cần duyệt".
    // Máy chủ mới là chỗ chặn thật (services/ops.py::step); dòng này chỉ để không vẽ ra một cái
    // nút bấm vào là báo lỗi.
    if (r.status === "cho_duyet" && r.category === "marketing" && role === "ptgd_mkt" && r.created_by !== user?.username)
      out.push(["P.TGĐ Marketing duyệt", "approve", ""]);
    if (r.status === "cho_duyet" && r.category !== "marketing" && (role === "tgd" || (role === "chutich" && r.two_signatures))) out.push([role === "tgd" ? "TGĐ duyệt" : "Chủ tịch ký", "approve", ""]);
    if (r.status === "cho_chi" && role === "ketoan") out.push(["Đã chi (nhập mã GD)", "pay", "orange"]);
    if (!["da_chi", "tu_choi"].includes(r.status) && ["tgd", "chutich", "ketoan", "tp_dh", "ptgd_mkt"].includes(role)) out.push(["Từ chối", "reject", "grey"]);
    return out;
  };

  return (<>
    <h1>Đề nghị chi – Lệnh chi (robot R3) &amp; dòng tiền tour</h1>
    <p className="muted">Đề nghị chi bắt buộc mã tour (chi phí tour), NCC có MST, chứng từ đính kèm. Robot xếp cấp duyệt: chi ngoài dự toán tour hoặc Marketing ≥ hạn mức → <b>Chủ tịch + TGĐ</b> (cổng 15). Luồng: bộ phận xác nhận → Kế toán kiểm tra → TGĐ duyệt → lệnh chi chờ → Kế toán chi trên ngân hàng (SePay tiền ra có mã DC… tự khớp). Duyệt → Nợ 154/641/642 – Có 331; chi → Nợ 331 – Có 112.</p>
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>{[["requests", "Đề nghị chi"], ["thieu_ngay", "Chưa có ngày phải trả"], ["cashflow", "Dòng tiền tour"]].map(([k, l]) => <button key={k} className={"act " + (tab === k ? "" : "grey")} style={{ margin: 0 }} onClick={() => setTab(k)}>{l}</button>)}</div>

    {tab === "requests" && <>
      {canCreate && <div className="panel"><h2>Lập đề nghị chi (mẫu 05-TT)</h2><div className="grid">
        {/* P.TGĐ Marketing KHÔNG lập hồ sơ chi Marketing, chỉ duyệt (Chủ tịch chốt 23/9/2026): mọi
            hồ sơ Marketing dừng ở một chữ ký của ông ấy, nên hồ sơ do chính ông ấy lập thì không
            còn ai ký được ngoài chính mình. Bỏ hẳn lựa chọn khỏi ô chọn loại thay vì để người ta
            điền xong cả biểu mẫu rồi mới bị máy chủ từ chối. */}
        <label>Loại<select value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}>{Object.entries(CAT).filter(([k]) => !(k === "marketing" && role === "ptgd_mkt")).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Tour (bắt buộc với chi tour/hoàn tiền)<select value={f.tour_id} onChange={(e) => setF({ ...f, tour_id: e.target.value })}><option value="">–</option>{tours.map((t) => <option key={t.id} value={t.id}>{t.code} · {t.name}</option>)}</select></label>
        <label>NCC / người thụ hưởng<input value={f.supplier_name} onChange={(e) => setF({ ...f, supplier_name: e.target.value })} /></label>
        <label>MST NCC<input value={f.supplier_tax_code} onChange={(e) => setF({ ...f, supplier_tax_code: e.target.value })} /></label>
        <label>Tài khoản thụ hưởng<input value={f.supplier_bank} onChange={(e) => setF({ ...f, supplier_bank: e.target.value })} placeholder="số TK – ngân hàng" /></label>
        <label>Số tiền (đ)<input type="number" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} /></label>
        <label>Nội dung<input value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></label>
        <label>Ngày phải trả (đã hẹn với NCC)<input type="date" value={f.ngay_den_han} onChange={(e) => setF({ ...f, ngay_den_han: e.target.value })} />
          <span className="muted">Chưa hẹn được thì để trống – đừng đoán. Khoản để trống sẽ nằm ở tab “Chưa có ngày phải trả” cho tới khi có người gõ.</span></label>
        <label>Chứng từ đính kèm (số HĐ/HĐơn/báo giá)<input value={f.document_ref} onChange={(e) => setF({ ...f, document_ref: e.target.value, has_document: !!e.target.value })} /></label>
        <label><input type="checkbox" checked={f.has_invoice} onChange={(e) => setF({ ...f, has_invoice: e.target.checked })} /> Có hóa đơn GTGT (không có → không được trừ TNDN)</label>
        {f.category === "marketing" && <>
          <label>Hạng mục ngân sách Marketing<select value={f.marketing_muc} onChange={(e) => setF({ ...f, marketing_muc: e.target.value })}>
            <option value="">– chưa gắn –</option>
            {Object.entries(dmMkt?.hang_muc || {}).map(([k, v]) => <option key={k} value={k}>{v as string}</option>)}</select>
            <span className="muted">Chưa gắn hạng mục thì cổng ngân sách coi khoản này là ngoài dự toán và cần hai chữ ký.</span></label>
          <label>Chiến dịch<select value={f.campaign_id} onChange={(e) => setF({ ...f, campaign_id: e.target.value })}>
            <option value="">– chưa gắn –</option>
            {(dmMkt?.chien_dich || []).map((c: any) => <option key={c.id} value={c.id}>{c.ma} · {c.ten}</option>)}</select>
            <span className="muted">Để trống được. Nhưng khoản để trống nằm ở phần “chưa gắn chiến dịch” của bảng Đóng góp doanh thu, và không chiến dịch nào nhận nó.</span></label>
        </>}
      </div><button className="act" disabled={!f.supplier_name || !f.amount || !f.description} onClick={() => post("/payment-requests", { ...f, tour_id: f.tour_id ? Number(f.tour_id) : null, amount: Number(f.amount), ngay_den_han: f.ngay_den_han || null, marketing_muc: f.category === "marketing" ? f.marketing_muc : "", campaign_id: f.category === "marketing" && f.campaign_id ? Number(f.campaign_id) : null }).then((r) => r && setF({ ...f, supplier_name: "", amount: "", description: "", document_ref: "", has_document: false, ngay_den_han: "", marketing_muc: "", campaign_id: "" }))}>Lập đề nghị</button></div>}
      <div>{[["cho_tp,cho_kt,cho_duyet,cho_chi", "Đang xử lý"], ["cho_chi", "Lệnh chi chờ"], ["da_chi", "Đã chi"], ["tu_choi", "Từ chối"], ["", "Tất cả"]].map(([v, l]) => <button key={v} className={"act " + (filter === v ? "" : "grey")} onClick={() => setFilter(v)}>{l}</button>)}</div>
      <div className="panel wrap"><table><thead><tr><th>Số ĐN</th><th>Loại / Tour</th><th>NCC</th><th style={{ textAlign: "right" }}>Số tiền</th><th>Nội dung</th><th>Hạn trả</th><th>Cờ R3</th><th>Trạng thái → bước tiếp</th><th>Người</th><th></th></tr></thead>
        <tbody>{rows.length ? rows.map((r) => <tr key={r.id}><td><b>{r.code}</b><div className="muted">{fmtDT(r.created_at)}</div></td><td>{CAT[r.category]}<div className="muted">{r.tour_code}</div></td><td>{r.supplier_name}<div className="muted">{r.supplier_tax_code || <Tag cls="warn">chưa MST</Tag>}</div></td><td style={{ textAlign: "right" }}><b>{vnd(r.amount)}</b></td><td>{r.description}<div className="muted">{r.document_ref || <Tag cls="warn">thiếu chứng từ</Tag>}{!r.has_invoice && !["hoan_tien", "tam_ung"].includes(r.category) && <Tag cls="warn">không HĐ</Tag>}</div></td>
          <td>{r.ngay_den_han ? <b>{String(r.ngay_den_han).slice(0, 10).split("-").reverse().join("/")}</b> : <Tag cls="warn">Chưa có hạn</Tag>}
            <div className="muted">{r.ngay_den_han_boi ? `${r.ngay_den_han_boi} gõ` : ""}{!["da_chi", "tu_choi"].includes(r.status) && <> <button className="act grey" style={{ margin: 0, padding: "1px 6px", fontSize: 11 }} onClick={() => datNgay(r)}>{r.ngay_den_han ? "Sửa" : "Gõ hạn"}</button></>}</div></td>
          <td>{r.over_budget && <Tag cls="red">Ngoài dự toán</Tag>}{r.two_signatures && <Tag cls="navy">2 chữ ký</Tag>}</td><td><Tag cls={ST[r.status]?.[1]}>{ST[r.status]?.[0]}</Tag><div className="muted">{r.next}{r.two_signatures && r.status === "cho_duyet" && ` (CT ${r.signed_chutich ? "✔" : "…"} · TGĐ ${r.signed_tgd ? "✔" : "…"})`}{r.reject_reason && ` – ${r.reject_reason}`}{r.paid_ref && ` – ${r.paid_ref}`}</div></td>
          <td className="muted">{r.created_by}{r.tp_by && ` → ${r.tp_by}`}{r.kt_by && ` → ${r.kt_by}`}{r.approved_by && ` → ${r.approved_by}`}</td>
          <td>{actions(r).map(([l, a, c]) => <button key={a} className={"act " + c} style={{ margin: "0 4px 4px 0" }} onClick={() => { let reason = ""; if (a === "reject") { reason = prompt("Lý do từ chối (bắt buộc):") || ""; if (!reason) return; } if (a === "pay") { reason = prompt("Mã giao dịch ngân hàng (hoặc 'TM' nếu tiền mặt):") || ""; } step(r, a, reason); }}>{l}</button>)}
            {" "}<button className="act grey" style={{ margin: "0 4px 4px 0" }} title="Chứng từ kèm theo" onClick={() => setTepDN(r.code)}>Chứng từ</button></td></tr>) : <tr><td colSpan={10} className="muted">Không có đề nghị chi.</td></tr>}</tbody></table></div>
      {tepDN && <DinhKem doiTuong="de_nghi_chi" doiTuongId={tepDN} tieuDe={`Chứng từ của đề nghị chi ${tepDN}`}
        goi={"Hóa đơn, hợp đồng, báo giá, ủy nhiệm chi. Người duyệt nhìn thấy đúng chứng từ mình đang " +
             "duyệt thay vì tin vào một dòng mô tả."} />}
    </>}

    {tab === "thieu_ngay" && <div className="panel wrap">
      <h2>Đề nghị chi chưa có ngày phải trả</h2>
      <p className="muted">Mỗi dòng dưới đây là một khoản tiền hệ thống <b>biết là phải trả</b> nhưng <b>không biết trả ngày nào</b>.
        Bảng dòng tiền xếp từng khoản vào một cột theo ngày, nên những khoản này chưa xếp được vào cột nào —
        chúng đang nằm ở rổ “Chưa đủ dữ liệu dự báo”. Hệ thống <b>cố ý không đoán hộ một ngày</b>: ngày bịa ra
        trông y hệt ngày thật trên màn hình lãnh đạo. Người lập đề nghị hoặc Kế toán gõ ngày đã hẹn với nhà cung cấp vào đây.</p>
      {thieuNgay && <p><b>{thieuNgay.so_khoan}</b> khoản · tổng <b>{vnd(thieuNgay.tong_tien)}</b> chưa xếp được vào cột nào</p>}
      <table><thead><tr><th>Số ĐN</th><th>Loại / Tour</th><th>NCC</th><th style={{ textAlign: "right" }}>Số tiền</th><th>Nội dung</th><th>Người lập</th><th></th></tr></thead>
        <tbody>{thieuNgay?.chi_tiet?.length ? thieuNgay.chi_tiet.map((r: any) => <tr key={r.id}>
          <td><b>{r.code}</b><div className="muted">{fmtDT(r.created_at)}</div></td>
          <td>{CAT[r.category]}</td><td>{r.supplier_name}</td>
          <td style={{ textAlign: "right" }}><b>{vnd(r.amount)}</b></td>
          <td>{r.description}</td><td className="muted">{r.created_by}</td>
          <td><button className="act" style={{ margin: 0 }} onClick={() => datNgay(r)}>Gõ hạn trả</button></td></tr>)
          : <tr><td colSpan={7} className="muted">Không còn khoản nào thiếu ngày phải trả.</td></tr>}</tbody></table></div>}

    {tab === "cashflow" && <div className="panel wrap"><table><thead><tr><th>Tour</th><th>Trạng thái</th><th style={{ textAlign: "right" }}>Doanh thu booking</th><th style={{ textAlign: "right" }}>Đã thu</th><th style={{ textAlign: "right" }}>Đã chi</th><th style={{ textAlign: "right" }}>Lệnh chi chờ</th><th style={{ textAlign: "right" }}>Đang trình</th><th style={{ textAlign: "right" }}>Tiền còn lại</th><th style={{ textAlign: "right" }}>Dự toán chi</th><th style={{ textAlign: "right" }}>LN dự kiến</th><th>Cảnh báo</th></tr></thead>
      <tbody>{cf.map((c) => <tr key={c.tour_id}><td><b>{c.code}</b><div className="muted">{c.name}</div></td><td className="muted">{c.status}</td><td style={{ textAlign: "right" }}>{vnd(c.revenue)}</td><td style={{ textAlign: "right" }}>{vnd(c.collected)}</td><td style={{ textAlign: "right" }}>{vnd(c.paid)}</td><td style={{ textAlign: "right" }}>{vnd(c.committed)}</td><td style={{ textAlign: "right" }}>{vnd(c.pending)}</td><td style={{ textAlign: "right" }}><b style={{ color: c.cash_left < 0 ? "var(--red)" : undefined }}>{vnd(c.cash_left)}</b></td><td style={{ textAlign: "right" }}>{vnd(c.budget)}</td><td style={{ textAlign: "right" }}>{vnd(c.expected_profit)}</td>
        <td>{c.red && <Tag cls="red">Chi vượt thu</Tag>}{c.over_budget && <Tag cls="warn">Vượt dự toán</Tag>}</td></tr>)}</tbody></table>
      <p className="muted">Bảng dòng tiền tour tự động (R3): cảnh báo đỏ khi chi + lệnh chi chờ vượt tiền đã thu. Mọi cấp duyệt xem bảng này trước khi duyệt đề nghị chi.</p></div>}
  </>);
}
export default function Page() { return <Shell><Expenses /></Shell>; }
