"use client";
import React, { useEffect, useState, useCallback } from "react";
import DinhKem from "@/components/DinhKem";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

// Đội xe thêm 05/10/2026 (Chủ tịch quyết). Hai loại này do Giám đốc đội xe XÁC NHẬN; cửa duyệt vẫn
// là TGĐ / Chủ tịch như mọi loại khác. Bảng này phải khớp CATEGORY_CONFIRMER ở máy chủ – có hàng rào
// canh (test_tx2), vì hai bảng khai tay thì sớm muộn cũng lệch và lúc lệch thì màn hình nói sai
// tên người phụ trách.
const CAT: Record<string, string> = { chi_tour: "Chi phí tour", marketing: "Marketing", hanh_chinh: "Hành chính", hoan_tien: "Hoàn tiền khách", tam_ung: "Tạm ứng HDV/NCC trước tour", sua_chua_xe: "Sửa chữa xe", tam_ung_tai_xe: "Tạm ứng tài xế", chi_doi_xe: "Chi đội xe (GĐ đội xe lập)", hoa_hong: "Hoa hồng đối tác (D06)" , tra_ncc_thu_ho: "Trả NCC tiền thu hộ (khách sạn / nhà hàng)" };
const ST: Record<string, [string, string]> = { cho_tp: ["Chờ bộ phận", "warn"], cho_kt: ["Chờ Kế toán", "warn"], cho_duyet: ["Chờ duyệt", "warn"], cho_chi: ["Lệnh chi chờ", "navy"], da_chi: ["Đã chi", "ok"], tu_choi: ["Từ chối", "red"], tra_bo_sung: ["Trả bổ sung", "red"] };
const CONFIRMER: Record<string, string[]> = { chi_tour: ["tp_dh", "tgd"], marketing: ["ptgd_mkt", "tgd"], hanh_chinh: ["hcns", "tgd"], hoan_tien: ["gd_kd", "tp_dh", "tgd"], tam_ung: ["tp_dh", "tgd"], sua_chua_xe: ["gd_doi_xe", "tgd"], tam_ung_tai_xe: ["gd_doi_xe", "tgd"], chi_doi_xe: ["gd_doi_xe", "tgd"], hoa_hong: ["gd_kd", "tgd"] , tra_ncc_thu_ho: [] };

function Expenses() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const [tab, setTab] = useState("requests");
  const [tepDN, setTepDN] = useState("");   // mã đề nghị chi đang mở chứng từ
  // VH-22 (Chủ tịch duyệt bản xem trước 11/11/2026 23:27): «Xem chi tiết» mở NGAY DƯỚI dòng — đủ nội dung,
  // tuyến ký và chứng từ đính kèm. Thay nút «Chứng từ» cũ (mở khối tệp tận cuối trang, người duyệt không thấy).
  const [moCT, setMoCT] = useState<number | null>(null);
  const [tepUnc, setTepUnc] = useState(false);   // KS-16d: ô đang mở là ô tải UNC (Kế toán, lệnh chi chờ)
  const [filter, setFilter] = useState("cho_tp,cho_kt,cho_duyet,cho_chi,tra_bo_sung");
  const [rows, setRows] = useState<any[]>([]);
  const [cf, setCf] = useState<any[]>([]);
  const [tours, setTours] = useState<any[]>([]);
  const [f, setF] = useState<any>({ category: "chi_tour", tour_id: "", supplier_name: "", supplier_tax_code: "", supplier_bank: "", amount: "", description: "", has_document: false, document_ref: "", has_invoice: false, ngay_den_han: "", marketing_muc: "", campaign_id: "", tien_te: "", so_tien_ngoai_te: "", ty_gia: "", ngay_ty_gia: "" });
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
  const step = (r: any, action: string, reason = "", hinh_thuc_tt = "", so_tien: number | null = null) =>
    post(`/payment-requests/${r.id}/step`, { action, reason, hinh_thuc_tt, so_tien });
  // TRẢ BỔ SUNG (Chủ tịch duyệt 10/11/2026, mọi đề nghị chi): người lập sửa ngay trên hồ sơ cũ rồi gửi lại.
  const [sua, setSua] = useState<any>(null);
  const guiLai = async () => {
    if (!sua) return;
    const { r, ...o } = sua;
    const json: any = {};
    for (const k of ["supplier_name", "supplier_tax_code", "supplier_bank", "description", "document_ref"]) json[k] = o[k];
    if (!r.tien_te) json.amount = Number(o.amount);
    json.has_document = !!o.has_document; json.has_invoice = !!o.has_invoice;
    const kq = await post(`/payment-requests/${r.id}/gui-lai`, json);
    if (kq) setSua(null);
  };
  // DOT R4c-3 02/11/2026 — HAI O ROI NHAU THAY MOT HOP `prompt()`.
  //
  // Hop cu hoi "Ma giao dich ngan hang (hoac 'TM' neu tien mat)" — tuc chinh loi trong hop
  // DAY nguoi dung phep doan hai chu cai cua may chu. Hai thu khac nhau thi hai o: hinh thuc
  // thanh toan quyet VE TIEN cua but toan, ma giao dich chi la so chung tu.
  //
  // Danh sach doc tu `httt` cua may chu (`/hach-toan/bang`), KHONG go lai bay nhan o day.
  const [chi, setChi] = useState<any>(null);   // ho so dang bam da chi
  const [httt, setHttt] = useState<Record<string, string>>({});
  useEffect(() => {
    if (chi && !Object.keys(httt).length)
      api<any>("/hach-toan/bang").then((d) => setHttt(d?.hinh_thuc_tt || {})).catch(() => {});
  }, [chi, httt]);
  const ghiDaChi = async () => {
    if (!chi?.hinh_thuc_tt) { toast("Chọn hình thức thanh toán", true); return; }
    const tien = chi.so_tien === "" ? null : Number(chi.so_tien);
    if (tien !== null && !(tien > 0)) { toast("Số tiền chi lần này phải lớn hơn 0", true); return; }
    await step(chi.r, "pay", chi.ma || "", chi.hinh_thuc_tt, tien);
    setChi(null);
  };
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
    // Bước MỘT của Marketing là chữ ký NỘI DUNG của P.TGĐ Marketing, nên nút phải nói thế —
    // "Xác nhận" chung chung làm người bấm tưởng mình chỉ đang xác nhận giấy tờ (Đợt F1b).
    if (r.status === "cho_tp" && CONFIRMER[r.category]?.includes(role))
      out.push([r.category === "marketing" ? "Duyệt nội dung" : "Xác nhận", "confirm", "teal"]);
    // KS-16d (Chủ tịch 31/10/2026): loại máy tự lập — robot kế toán làm bước xác nhận + kiểm; người chỉ bấm chạy lại robot.
    if (r.may_lap && ["cho_tp", "cho_kt"].includes(r.status) && ["ketoan", "tp_dh", "nv_dh", "tgd", "chutich"].includes(role))
      out.push(["Robot kiểm lại", "robot", "teal"]);
    if (r.status === "cho_kt" && role === "ketoan" && !r.may_lap) out.push(["Kế toán kiểm tra", "check", "teal"]);
    // ĐỢT F1 — màn hình ĐỌC cấp duyệt từ máy chủ (`vai_ky_duoc`), KHÔNG tự suy.
    // Dòng cũ ở đây viết `role === "tgd" || (role === "chutich" && r.two_signatures)` — đúng cái
    // cờ sai mà F1 sửa ở máy chủ, nên để nguyên là màn hình sai cả hai đầu: TGĐ thấy nút trên
    // khoản từ mốc trở lên rồi bấm vào nhận 422, Chủ tịch không có nút trên khoản ông phải ký.
    // Máy chủ vẫn là chỗ chặn thật (`services/ops.py::step`); dòng này chỉ để không vẽ ra một
    // cái nút bấm vào là báo lỗi, và không giấu đi một cái nút đáng lẽ phải có.
    //
    // DANH SÁCH RỖNG nghĩa là KHÔNG AI bấm được lúc này — chưa chốt ngưỡng, hoặc chưa ai giữ vai
    // P.TGĐ Marketing. Hồ sơ vẫn hiện trong danh sách cho cả TGĐ và Chủ tịch XEM, chỉ không có
    // nút: đúng điều Chủ tịch chốt 10/10/2026 — dưới mốc TGĐ duyệt nhưng Chủ tịch vẫn phải thấy,
    // trên mốc TGĐ cũng vẫn thấy nhưng không bấm duyệt.
    // Đợt F1b: Marketing thôi có nhãn riêng ở bước này — bước này nay là LỆNH CHI cho mọi loại
    // chi, do TGĐ hoặc Chủ tịch ký theo mốc. Phép loại người lập cũng thôi gắn riêng Marketing:
    // máy chủ chặn người lập tự ký ở đúng chỗ của nó.
    if (r.status === "cho_duyet" && (r.vai_ky_duoc || []).includes(role))
      out.push([role === "tgd" ? "TGĐ ký lệnh chi" : "Chủ tịch ký lệnh chi", "approve", ""]);
    // KS-16d: CK xong → Kế toán tải UNC → mới bấm «Đã chi» (máy chủ chặn nếu chưa có UNC, mọi loại chi).
    if (r.status === "cho_chi" && role === "ketoan") { out.push(["Tải UNC", "unc", "grey"]); out.push(["Đã chi (nhập mã GD)", "pay", "orange"]); }
    // Trả bổ sung: người giữ bước hiện tại trả về người lập (máy chủ kiểm đúng người, `ops._ai_tra_duoc`).
    if (["cho_tp", "cho_kt", "cho_duyet", "cho_chi"].includes(r.status) && !r.may_lap && !(r.da_chi_tien > 0)
        && ["tgd", "chutich", "ketoan", "ketoan_tt", "ketoan_truong", "thu_quy", ...(CONFIRMER[r.category] || [])].includes(role))
      out.push(["Trả bổ sung", "tra_bo_sung", "grey"]);
    if (r.status === "tra_bo_sung" && r.created_by === user?.username) out.push(["Bổ sung & gửi lại", "gui_lai", "teal"]);
    if (!["da_chi", "tu_choi"].includes(r.status) && !(r.da_chi_tien > 0) && ["tgd", "chutich", "ketoan", "tp_dh", "ptgd_mkt"].includes(role)) out.push(["Từ chối", "reject", "grey"]);
    return out;
  };

  return (<>
    <h1>Đề nghị chi – Lệnh chi (robot R3) &amp; dòng tiền tour</h1>
    <p className="muted">Đề nghị chi bắt buộc mã tour (chi phí tour), NCC có MST, chứng từ đính kèm. Robot xếp cấp duyệt: chi ngoài dự toán tour hoặc Marketing ≥ hạn mức → <b>Chủ tịch + TGĐ</b> (cổng 15). Luồng: bộ phận xác nhận → Kế toán kiểm tra → TGĐ duyệt → lệnh chi chờ → Kế toán chi trên ngân hàng (SePay tiền ra có mã DC… tự khớp). Duyệt → Nợ 154/641/642 – Có 331; chi → Nợ 331 – Có 1121 (tiền mặt: 1111).</p>
    {chi && (<div style={{ border: "1px solid #0f6f5c", borderRadius: 8, padding: 14, margin: "12px 0", maxWidth: 420 }}>
      <b>Ghi nhận đã chi – {chi.r.code}</b>
      <label style={{ display: "block", marginTop: 10 }}>Hình thức thanh toán
        <select value={chi.hinh_thuc_tt} onChange={(e) => setChi({ ...chi, hinh_thuc_tt: e.target.value })}>
          <option value="">— chọn —</option>
          {Object.entries(httt).filter(([k]) => k && k !== "chua_tt")
            .map(([k, t]: any) => <option key={k} value={k}>{t}</option>)}
        </select></label>
      <label style={{ display: "block", marginTop: 8 }}>Số tiền chi lần này (đ)
        <input type="number" value={chi.so_tien} onChange={(e) => setChi({ ...chi, so_tien: e.target.value })} /></label>
      <p className="muted" style={{ margin: "4px 0 0" }}>Được duyệt {vnd(chi.r.amount)} · đã chi {vnd(chi.r.da_chi_tien || 0)} · còn {vnd(chi.r.con_phai_chi ?? chi.r.amount)}.
        Chi ít hơn phần còn lại thì hồ sơ ở «Đã chi một phần»; mỗi lần chi cần một UNC riêng.</p>
      <label style={{ display: "block", marginTop: 8 }}>Mã giao dịch / số chứng từ
        <input value={chi.ma} placeholder="để trống nếu không có"
               onChange={(e) => setChi({ ...chi, ma: e.target.value })} /></label>
      <div style={{ marginTop: 10 }}>
        <button className="act" onClick={ghiDaChi}>Ghi nhận đã chi</button>
        <button className="act grey" style={{ marginLeft: 8 }} onClick={() => setChi(null)}>Thôi</button>
      </div>
    </div>)}
    {sua && (<div style={{ border: "1px solid #b42318", borderRadius: 8, padding: 14, margin: "12px 0", maxWidth: 560 }}>
      <b>Bổ sung & gửi lại – {sua.r.code}</b>
      <p className="muted" style={{ margin: "4px 0 8px" }}>Lý do trả: {sua.r.reject_reason || "—"}. Gửi lại thì đi lại tuyến duyệt từ đầu; chữ ký cũ không còn, bản trước vẫn lưu trong lịch sử hồ sơ.</p>
      {[["supplier_name", "Người nhận / NCC"], ["supplier_tax_code", "Mã số thuế"], ["supplier_bank", "Số TK – ngân hàng"], ["description", "Nội dung"], ["document_ref", "Số chứng từ"]].map(([k, l]) =>
        <label key={k} style={{ display: "block", marginTop: 6 }}>{l}<input value={sua[k] ?? ""} onChange={(e) => setSua({ ...sua, [k]: e.target.value })} /></label>)}
      {!sua.r.tien_te && <label style={{ display: "block", marginTop: 6 }}>Số tiền (đ)<input type="number" value={sua.amount} onChange={(e) => setSua({ ...sua, amount: e.target.value })} /></label>}
      <label style={{ display: "block", marginTop: 6 }}><input type="checkbox" checked={!!sua.has_document} onChange={(e) => setSua({ ...sua, has_document: e.target.checked })} /> Có chứng từ</label>
      <label style={{ display: "block" }}><input type="checkbox" checked={!!sua.has_invoice} onChange={(e) => setSua({ ...sua, has_invoice: e.target.checked })} /> Có hóa đơn GTGT</label>
      <div style={{ marginTop: 10 }}>
        <button className="act teal" onClick={guiLai}>Gửi lại</button>
        <button className="act grey" style={{ marginLeft: 8 }} onClick={() => setSua(null)}>Thôi</button>
      </div>
    </div>)}
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>{[["requests", "Đề nghị chi"], ["thieu_ngay", "Chưa có ngày phải trả"], ["cashflow", "Dòng tiền tour"]].map(([k, l]) => <button key={k} className={"act " + (tab === k ? "" : "grey")} style={{ margin: 0 }} onClick={() => setTab(k)}>{l}</button>)}</div>

    {tab === "requests" && <>
      {canCreate && <div className="panel"><h2>Lập đề nghị chi (mẫu 05-TT)</h2><div className="grid">
        {/* P.TGĐ Marketing KHÔNG lập hồ sơ chi Marketing, chỉ duyệt (Chủ tịch chốt 23/9/2026): mọi
            hồ sơ Marketing dừng ở một chữ ký của ông ấy, nên hồ sơ do chính ông ấy lập thì không
            còn ai ký được ngoài chính mình. Bỏ hẳn lựa chọn khỏi ô chọn loại thay vì để người ta
            điền xong cả biểu mẫu rồi mới bị máy chủ từ chối. */}
        <label>Loại<select value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}>{Object.entries(CAT).filter(([k]) => k !== "tra_ncc_thu_ho" && k !== "chi_doi_xe" && !(k === "marketing" && role === "ptgd_mkt")).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Tour (bắt buộc với chi tour/hoàn tiền)<select value={f.tour_id} onChange={(e) => setF({ ...f, tour_id: e.target.value })}><option value="">–</option>{tours.map((t) => <option key={t.id} value={t.id}>{t.code} · {t.name}</option>)}</select></label>
        <label>NCC / người thụ hưởng<input value={f.supplier_name} onChange={(e) => setF({ ...f, supplier_name: e.target.value })} /></label>
        <label>MST NCC<input value={f.supplier_tax_code} onChange={(e) => setF({ ...f, supplier_tax_code: e.target.value })} /></label>
        <label>Tài khoản thụ hưởng<input value={f.supplier_bank} onChange={(e) => setF({ ...f, supplier_bank: e.target.value })} placeholder="số TK – ngân hàng" /></label>
        {/* BỐN Ô NGOẠI TỆ – Chủ tịch chốt 27/9/2026. Để trống đồng tiền = khoản đồng Việt Nam (đại
            đa số), ô VND gõ như cũ. Khai đồng tiền thì MÁY NHÂN và ô VND thành chỉ-đọc: gõ tay cả ba
            con số là mở đường cho ba con số không khớp nhau – cùng lý do đã ghi ở models/ty_gia.py. */}
        <label>Đồng tiền<select value={f.tien_te} onChange={(e) => setF({ ...f, tien_te: e.target.value, amount: "" })}>
          <option value="">VND – đồng Việt Nam</option>
          {["USD", "EUR", "AUD", "CAD", "GBP", "JPY", "KRW", "CNY", "SGD", "THB", "TWD", "HKD"].map((m) => <option key={m} value={m}>{m}</option>)}</select></label>
        {f.tien_te ? <>
          <label>Số tiền ({f.tien_te})<input type="number" step="0.01" value={f.so_tien_ngoai_te} onChange={(e) => setF({ ...f, so_tien_ngoai_te: e.target.value })} />
            <span className="muted">TỔNG số ngoại tệ phải chuyển, không phải đơn giá – đề nghị chi không có số lượng.</span></label>
          <label>Tỷ giá (1 {f.tien_te} = ? đ)<input type="number" step="0.000001" value={f.ty_gia} onChange={(e) => setF({ ...f, ty_gia: e.target.value })} /></label>
          <label>Ngày tỷ giá<input type="date" value={f.ngay_ty_gia} onChange={(e) => setF({ ...f, ngay_ty_gia: e.target.value })} />
            <span className="muted">Ngày CHUYỂN TIỀN thật, không phải ngày lập phiếu. Nên có dòng tương ứng trong Sổ tỷ giá kèm chứng từ.</span></label>
          <label>Số tiền quy đổi (đ) – máy nhân<input readOnly value={f.so_tien_ngoai_te && f.ty_gia ? Math.round(Number(f.so_tien_ngoai_te) * Number(f.ty_gia)).toLocaleString("vi-VN") : "–"} />
            <span className="muted">Máy nhân, người không gõ. Chênh lệch tỷ giá so với tỷ giá quyết toán được đo riêng, không lẫn vào “còn phải trả NCC”.</span></label>
        </> : <label>Số tiền (đ)<input type="number" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} /></label>}
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
      </div><button className="act" disabled={!f.supplier_name || !f.description || (f.tien_te ? !(f.so_tien_ngoai_te && f.ty_gia && f.ngay_ty_gia) : !f.amount)} onClick={() => post("/payment-requests", { ...f, tour_id: f.tour_id ? Number(f.tour_id) : null, amount: f.tien_te ? 0 : Number(f.amount), tien_te: f.tien_te, so_tien_ngoai_te: f.tien_te && f.so_tien_ngoai_te ? Number(f.so_tien_ngoai_te) : null, ty_gia: f.tien_te && f.ty_gia ? Number(f.ty_gia) : null, ngay_ty_gia: f.tien_te && f.ngay_ty_gia ? f.ngay_ty_gia : null, ngay_den_han: f.ngay_den_han || null, marketing_muc: f.category === "marketing" ? f.marketing_muc : "", campaign_id: f.category === "marketing" && f.campaign_id ? Number(f.campaign_id) : null }).then((r) => r && setF({ ...f, supplier_name: "", amount: "", description: "", document_ref: "", has_document: false, ngay_den_han: "", marketing_muc: "", campaign_id: "", so_tien_ngoai_te: "", ty_gia: "", ngay_ty_gia: "" }))}>Lập đề nghị</button></div>}
      <div>{[["cho_tp,cho_kt,cho_duyet,cho_chi,tra_bo_sung", "Đang xử lý"], ["cho_chi", "Lệnh chi chờ"], ["tra_bo_sung", "Trả bổ sung"], ["da_chi", "Đã chi"], ["tu_choi", "Từ chối"], ["", "Tất cả"]].map(([v, l]) => <button key={v} className={"act " + (filter === v ? "" : "grey")} onClick={() => setFilter(v)}>{l}</button>)}</div>
      <div className="panel wrap"><table><thead><tr><th>Số ĐN</th><th>Loại / Tour</th><th>NCC</th><th style={{ textAlign: "right" }}>Số tiền</th><th>Nội dung</th><th>Hạn trả</th><th>Cờ R3</th><th>Trạng thái → bước tiếp</th><th>Người</th><th style={{ position: "sticky", right: 0, background: "var(--panel)", zIndex: 1 }}>Việc của anh</th></tr></thead>
        <tbody>{rows.length ? rows.map((r) => <React.Fragment key={r.id}><tr><td><b>{r.code}</b><div className="muted">{fmtDT(r.created_at)}</div></td><td>{CAT[r.category]}<div className="muted">{r.tour_code}</div></td><td>{r.supplier_name}<div className="muted">{r.supplier_tax_code || <Tag cls="warn">chưa MST</Tag>}</div></td><td style={{ textAlign: "right" }}><b>{vnd(r.amount)}</b>{r.ngoai_te_loi_nhan && <div className="muted">{r.ngoai_te_loi_nhan}</div>}</td><td><div className="dn-nd" title={r.description}>{r.description}</div><div className="muted">{r.document_ref || <Tag cls="warn">thiếu chứng từ</Tag>}{!r.has_invoice && !["hoan_tien", "tam_ung", "tam_ung_tai_xe"].includes(r.category) && <Tag cls="warn">không HĐ</Tag>}</div></td>
          <td>{r.ngay_den_han ? <b>{String(r.ngay_den_han).slice(0, 10).split("-").reverse().join("/")}</b> : <Tag cls="warn">Chưa có hạn</Tag>}
            <div className="muted">{r.ngay_den_han_boi ? `${r.ngay_den_han_boi} gõ` : ""}{!["da_chi", "tu_choi"].includes(r.status) && <> <button className="act grey" style={{ margin: 0, padding: "1px 6px", fontSize: 11 }} onClick={() => datNgay(r)}>{r.ngay_den_han ? "Sửa" : "Gõ hạn"}</button></>}</div></td>
          <td>{r.over_budget && <Tag cls="red">Ngoài dự toán</Tag>}{r.two_signatures && <Tag cls="navy">2 chữ ký</Tag>}</td><td><Tag cls={r.chi_mot_phan ? "warn" : ST[r.status]?.[1]}>{r.chi_mot_phan ? "Đã chi một phần" : ST[r.status]?.[0]}</Tag><div className="muted">{r.next}{r.two_signatures && r.status === "cho_duyet" && ` (CT ${r.signed_chutich ? "✔" : "…"} · TGĐ ${r.signed_tgd ? "✔" : "…"})`}{r.reject_reason && ` – ${r.reject_reason}`}{r.paid_ref && ` – ${r.paid_ref}`}</div>
            {r.robot_ghi_chu && <div style={{ fontSize: 12, color: "#9a5b00" }}>{r.robot_ghi_chu}</div>}
            {r.status === "cho_chi" && !r.co_unc && <div style={{ fontSize: 12 }}><Tag cls="warn">Chưa có UNC</Tag> CK xong tải UNC rồi bấm «Đã chi»</div>}</td>
          <td className="muted">{r.created_by}{r.tp_by && ` → ${r.tp_by}`}{r.kt_by && ` → ${r.kt_by}`}{r.approved_by && ` → ${r.approved_by}`}</td>
          <td className="dn-nut">{actions(r).map(([l, a, c]) => <button key={a} className={"act " + c} style={{ margin: "0 4px 4px 0" }} disabled={a === "pay" && (r.so_unc ?? (r.co_unc ? 1 : 0)) <= (r.lan_chi || []).length} title={a === "pay" && (r.so_unc ?? 0) <= (r.lan_chi || []).length ? "Tải UNC cho lần chi này trước" : ""} onClick={() => { if (a === "unc") { setTepUnc(true); setTepDN(r.code); return; } if (a === "robot") { post(`/payment-requests/${r.id}/robot-kiem`); return; } if (a === "gui_lai") { setSua({ r, supplier_name: r.supplier_name, supplier_tax_code: r.supplier_tax_code, supplier_bank: r.supplier_bank, description: r.description, document_ref: r.document_ref, amount: r.amount, has_document: r.has_document, has_invoice: r.has_invoice }); return; } let reason = ""; if (a === "reject" || a === "tra_bo_sung") { reason = prompt(a === "reject" ? "Lý do từ chối (bắt buộc):" : "Trả bổ sung — người lập cần bổ sung gì? (bắt buộc)") || ""; if (!reason) return; } if (a === "pay") { setChi({ r, hinh_thuc_tt: "", ma: "", so_tien: String(r.con_phai_chi ?? r.amount) }); return; } step(r, a, reason); }}>{l}</button>)}
            {" "}<button className="act grey dn-xem" style={{ margin: "0 4px 4px 0" }} aria-expanded={moCT === r.id}
              onClick={() => setMoCT(moCT === r.id ? null : r.id)}>{moCT === r.id ? "Ẩn chi tiết" : "Xem chi tiết"}</button></td></tr>
          {moCT === r.id && <tr className="dn-ct"><td colSpan={10}>
            <dl className="dn-luoi">
              <div className="dai"><dt>Nội dung đầy đủ</dt><dd>{r.description}</dd></div>
              <div><dt>Loại</dt><dd>{CAT[r.category] || r.category}{r.tour_code ? ` · ${r.tour_code}` : ""}</dd></div>
              <div><dt>Bên nhận</dt><dd>{r.supplier_name}{r.supplier_tax_code ? ` · MST ${r.supplier_tax_code}` : ""}</dd></div>
              <div><dt>Số tiền</dt><dd><b>{vnd(r.amount)}</b>{r.da_chi_tien > 0 ? ` · đã chi ${vnd(r.da_chi_tien)}` : ""}</dd></div>
              <div><dt>Số chứng từ</dt><dd>{r.document_ref || "—"}</dd></div>
              <div><dt>Lập lúc</dt><dd>{fmtDT(r.created_at)} · {r.created_by}</dd></div>
              <div><dt>Bước tiếp</dt><dd>{r.next || ST[r.status]?.[0]}</dd></div>
              <div className="dai"><dt>Tuyến ký</dt><dd>{[r.created_by && `Lập: ${r.created_by}`, r.tp_by && `Xác nhận: ${r.tp_by}`,
                r.kt_by && `Kế toán: ${r.kt_by}`, r.approved_by && `Ký lệnh chi: ${r.approved_by}`].filter(Boolean).join(" → ")}</dd></div>
              {r.robot_ghi_chu && <div className="dai"><dt>Robot ghi chú</dt><dd>{r.robot_ghi_chu}</dd></div>}
              {r.reject_reason && <div className="dai"><dt>Lý do trả / từ chối</dt><dd>{r.reject_reason}</dd></div>}
            </dl>
            <DinhKem key={`ct-${r.code}`} doiTuong="de_nghi_chi" doiTuongId={r.code} tieuDe={`Chứng từ của ${r.code}`}
              goi="Hóa đơn, hợp đồng, báo giá, ủy nhiệm chi — người duyệt nhìn đúng chứng từ mình đang duyệt." />
          </td></tr>}</React.Fragment>) : <tr><td colSpan={10} className="muted">Không có đề nghị chi.</td></tr>}</tbody></table></div>
      <style>{DN_CSS}</style>
      {tepDN && tepUnc && <DinhKem key={`unc-${tepDN}`} doiTuong="de_nghi_chi" doiTuongId={tepDN} loai="unc" tieuDe={`Tải UNC / phiếu chi của ${tepDN}`}
        goi="Chuyển khoản xong trên ngân hàng → tải ủy nhiệm chi (UNC) hoặc phiếu chi tiền mặt lên đây → nút «Đã chi» mở." onDoi={load} />}
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

/* VH-22 · nội dung hai dòng, cột nút DÍNH bên phải (luôn thấy dù bảng rộng), ngăn chi tiết dưới dòng. */
const DN_CSS = `
.dn-nd{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;max-width:46ch}
td.dn-nut{position:sticky;right:0;background:var(--panel);box-shadow:-8px 0 10px -8px rgba(18,48,84,.25);min-width:170px;z-index:1}
tr.dn-ct td{background:var(--panel2);padding:14px 16px}
.dn-luoi{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px 24px;margin:0 0 10px}
.dn-luoi>div{min-width:0}.dn-luoi .dai{grid-column:1/-1}
.dn-luoi dt{font-size:calc(11/14*1rem);font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--ink2)}
.dn-luoi dd{margin:2px 0 0;white-space:pre-wrap}
`;
