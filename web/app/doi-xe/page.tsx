"use client";
import { useEffect, useState, useCallback } from "react";
import DinhKem from "@/components/DinhKem";
import QuyetToanChuyen from "@/components/QuyetToanChuyen";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, fmtDT, soTien } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Hồ sơ đội xe Vietrip – Đợt 1.
 *
 *  Nguyên tắc hiển thị của màn hình này: KHÔNG có màu xanh khi hệ thống chưa kiểm tra được. Một chiếc xe chưa
 *  nhập đăng kiểm phải hiện "Chưa đủ dữ liệu" chứ không phải một dấu tích – nếu không, người điều hành tin
 *  rằng hồ sơ đã được kiểm tra và cho xe xuất bến. */
const MUC_CLS: Record<string, string> = { OK: "ok", UNKNOWN: "warn", REVIEW: "warn", APPROVAL_REQUIRED: "warn", BLOCK: "red" };
const MUC_TEN: Record<string, string> = { OK: "Đạt", UNKNOWN: "Chưa đủ dữ liệu", REVIEW: "Cần xem lại", APPROVAL_REQUIRED: "Cần duyệt ngoại lệ", BLOCK: "Chặn" };

function DoiXe() {
  const { user, toast } = useShell();
  const [tq, setTq] = useState<any>(null);
  const [xe, setXe] = useState<any[]>([]);
  const [chon, setChon] = useState<any>(null);
  const [xm, setXm] = useState<any[]>([]);
  const [tab, setTab] = useState<"xe" | "chuyen" | "giaodich" | "quyettoan" | "congno" | "baoduong" | "baohong">("xe");
  const [bh, setBh] = useState<any>(null);          // sổ báo hư hỏng của cả đội
  const [bd, setBd] = useState<any>(null);          // tình trạng bảo dưỡng của cả đội
  const [bdLs, setBdLs] = useState<any[]>([]);      // lịch sử phiếu bảo dưỡng
  const [formBD, setFormBD] = useState<any>(null);  // form ghi phiếu bảo dưỡng
  const [chuyen, setChuyen] = useState<any[]>([]);
  const [gd, setGd] = useState<any>(null);
  const [chuXe, setChuXe] = useState<any[]>([]);
  const [qt, setQt] = useState<any[]>([]);
  const [dm3, setDm3] = useState<any>(null);
  const [dm2, setDm2] = useState<any>(null);     // danh mục đợt 2: nguồn số km, ví ePass
  const [cn, setCn] = useState<any>(null);
  const [soChuXe, setSoChuXe] = useState<any>(null);
  const canWrite = ["cntt", "hcns", "tp_dh", "nv_dh"].includes(user?.role || "");
  // Người được nhập và sửa số liệu đội xe: điều hành, kế toán, và lãnh đạo.
  // "gd_doi_xe" là chính người sẽ nhập số liệu đội xe hằng ngày – thiếu vai trò này thì nút nhập không hiện
  // ra với đúng người mà form được làm cho, dù máy chủ đã cho phép.
  const canNhap = ["cntt", "hcns", "tp_dh", "nv_dh", "ketoan", "chutich", "tgd", "gd_doi_xe"].includes(user?.role || "");
  const [form, setForm] = useState<any>(null);      // form nhật trình chuyến (thêm / sửa)
  const [formDX, setFormDX] = useState<any>(null);  // form đề xuất chi
  const [formNga, setFormNga] = useState<any>(null); // form định tuyến một giao dịch nguồn ngoài
  const [dangLuu, setDangLuu] = useState(false);

  // Mục 4.9.6 "Bảo dưỡng & sửa chữa" của cây phân hệ trỏ thẳng vào tab này bằng ?tab=bao-duong.
  // Đọc từ window chứ không dùng useSearchParams: hook ấy đòi bọc Suspense, và một trang hỏng khi
  // dựng vì thiếu bọc là cái giá quá đắt cho việc đọc một chữ trên địa chỉ.
  useEffect(() => {
    try {
      const t = new URLSearchParams(window.location.search).get("tab");
      if (t === "bao-duong") setTab("baoduong");
      if (t === "bao-hong") setTab("baohong");
    } catch { /* không có địa chỉ thì giữ tab mặc định */ }
  }, []);

  /** Đội xe tiếp nhận một báo hỏng. KHÔNG đóng — xe vẫn bị chặn nếu mức là phải dừng xe.
   *  Tách hai nút là để trả lời được hai câu khác nhau: đã có ai nhìn chưa, và đã sửa xong chưa. */
  const tiepNhanHong = async (id: number) => {
    try { const r = await api<any>(`/fleet/bao-hong/${id}/tiep-nhan`, { method: "POST" }); toast(r.message); load(); }
    catch (e) { toast(errMsg(e), true); }
  };
  /** Đóng báo hỏng. Máy chủ BẮT BUỘC ghi kết quả, nên màn hình hỏi trước khi gọi. */
  const dongHong = async (id: number) => {
    const v = window.prompt("Đã xử lý thế nào? (bắt buộc)\n\nGhi rõ để lần sau gặp lại hiện tượng này còn tra được.");
    if (v === null) return;
    try { const r = await api<any>(`/fleet/bao-hong/${id}/dong`, { method: "POST", json: { ket_qua: v } }); toast(r.message); load(); }
    catch (e) { toast(errMsg(e), true); }
  };

  const load = useCallback(async () => {
    try {
      setTq(await api("/fleet/tong-quan"));
      setXe(await api("/fleet/xe?kem_kiem_tra=true"));
      setXm(await api("/fleet/xac-minh"));
      setChuyen(await api("/fleet/chuyen"));
      setGd(await api("/fleet/giao-dich"));
      setChuXe(await api("/fleet/chu-xe"));
      setQt(await api("/fleet/quyet-toan"));
      setDm3(await api("/fleet/danh-muc-dot3"));
      setDm2(await api("/fleet/danh-muc-dot2"));
      setCn(await api("/fleet/cong-no"));
      setBd(await api("/fleet/bao-duong/theo-xe"));
      setBdLs(await api("/fleet/bao-duong"));
      setBh(await api("/fleet/bao-hong"));
    } catch (e) { toast(errMsg(e), true); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  /** Ghi một phiếu bảo dưỡng / sửa chữa.
   *
   *  KHÔNG tự điền mốc kỳ tới khi người nhập bỏ trống: máy chủ nói thẳng là chưa tính được, còn
   *  suy ra từ chu kỳ chung là cách chi phí bị ghi sai kỳ mà không ai phát hiện.
   *
   *  Cảnh báo máy chủ trả về (`canh_bao`) phải HIỆN RA, không nuốt: nó bắt đúng lỗi có thật —
   *  mốc km ghi trên phiếu lớn hơn km đồng hồ đã xác nhận, tức là sai ngày hoặc sai kỳ.
   */
  const luuBaoDuong = async () => {
    if (!formBD.vehicle_id) return toast("Chọn xe trước đã", true);
    if (!formBD.ngay) return toast("Nhập ngày thực hiện", true);
    setDangLuu(true);
    try {
      const r = await api<any>("/fleet/bao-duong", { method: "POST", json: {
        vehicle_id: Number(formBD.vehicle_id), ngay: formBD.ngay, kind: formBD.kind || "dinh_ky",
        km_luc_lam: soTien(formBD.km_luc_lam), km_ky_toi: soTien(formBD.km_ky_toi),
        noi_dung: formBD.noi_dung || "", garage: formBD.garage || "",
        so_tien: soTien(formBD.so_tien), chung_tu: formBD.chung_tu || "" } });
      toast(r.message);
      (r.canh_bao || []).forEach((c: string) => toast(c, true));
      setFormBD(null);
      await load();
    } catch (e) { toast(errMsg(e), true); } finally { setDangLuu(false); }
  };

  /** Định tuyến một giao dịch nguồn ngoài. Lý do là BẮT BUỘC ở máy chủ — đây là phán xét của người
   *  đọc chứng từ, không phải phép tính, nên ba tháng sau phải còn căn cứ để trả lời "vì sao". */
  const luuNga = async () => {
    if (!formNga?.nga) return toast("Chọn ngả đã", true);
    if (!formNga?.ly_do?.trim()) return toast("Phải ghi lý do chọn ngả này", true);
    setDangLuu(true);
    try {
      const r = await api<any>("/fleet/giao-dich/dinh-tuyen", { method: "POST", json: {
        ma_gd: [formNga.ma_gd], nga: formNga.nga, ly_do: formNga.ly_do,
        bien_so: formNga.bien_so || "" } });
      toast(`Đã định tuyến ${r.da_dinh_tuyen} khoản về "${r.nga_ten}"`);
      setFormNga(null); await load();
    } catch (e) { toast(errMsg(e), true); } finally { setDangLuu(false); }
  };

  /** Tra lại xe theo biển cho các dòng chưa gắn được xe. Cửa này cần vì `vehicle_id` được tra ĐÚNG
   *  MỘT LẦN lúc nạp: sao kê về trước, hồ sơ xe nhập sau, và sau đó không gì tra lại. */
  const traLaiXe = async () => {
    try {
      const r = await api<any>("/fleet/giao-dich/tra-lai-xe", { method: "POST" });
      toast(`Đã gắn được ${r.da_gan} khoản. Không tra ra xe: ${r.khong_tra_ra_xe}. `
            + `Không có biển số: ${r.khong_co_bien_so} – những dòng này phải định tuyến bằng tay.`);
      await load();
    } catch (e) { toast(errMsg(e), true); }
  };

  /** Tính lại cờ chuyến theo luật kiểm hiện hành. Cờ được tính lúc GHI rồi lưu vào dòng, nên mỗi lần
   *  luật đổi là các dòng cũ mang cờ của luật cũ — và không ai thấy. */
  const tinhLaiCo = async () => {
    try {
      const r = await api<any>("/fleet/chuyen/tinh-lai-co", { method: "POST" });
      toast(r.da_tinh_lai ? `Đã tính lại cờ cho ${r.da_tinh_lai} chuyến`
                          : "Không chuyến nào đổi cờ – cờ đang khớp với luật kiểm hiện hành");
      await load();
    } catch (e) { toast(errMsg(e), true); }
  };

  const mo = async (id: number) => { try { setChon(await api(`/fleet/xe/${id}`)); } catch (e) { toast(errMsg(e), true); } };

  const luuChuyen = async () => {
    if (!form.vehicle_id) return toast("Chọn xe trước đã", true);
    if (!form.ngay_di || !form.ngay_ve) return toast("Nhập ngày đi và ngày về", true);
    setDangLuu(true);
    try {
      if (form.id) {
        await api(`/fleet/chuyen/${form.id}`, { method: "PUT", json: {
          ten_tour: form.ten_tour, ngay_di: form.ngay_di, ngay_ve: form.ngay_ve,
          km_dau: form.km_dau, km_cuoi: form.km_cuoi, km_gps: form.km_gps,
          km_nguon: form.km_nguon || "", doanh_thu: form.doanh_thu, note: form.note } });
        toast("Đã cập nhật phiếu chuyến");
      } else {
        const r = await api<any>("/fleet/chuyen", { method: "POST", json: {
          vehicle_id: form.vehicle_id, ten_tour: form.ten_tour, ngay_di: form.ngay_di, ngay_ve: form.ngay_ve,
          km_dau: form.km_dau, km_cuoi: form.km_cuoi, km_gps: form.km_gps,
          km_nguon: form.km_nguon || "nhap_tay", doanh_thu: form.doanh_thu, note: form.note } });
        // Bốn khoản chi phí ghi thành bốn dòng riêng: mỗi dòng phải trả lời được loại gì, ai chịu, chứng từ đâu.
        for (const k of ["dau", "cau_duong", "cong_tac_phi", "giu_xe"]) {
          const tien = soTien(form[k]);
          if (tien && tien > 0) await api(`/fleet/chuyen/${r.id}/chi-phi`, { method: "POST", json: {
            kind: k, amount: tien, lit: k === "dau" ? soTien(form.lit) : null, chung_tu: form.chung_tu || "" } });
        }
        toast("Đã ghi phiếu chi phí xe");
      }
      setForm(null); load();
    } catch (e) { toast(errMsg(e), true); } finally { setDangLuu(false); }
  };

  const moLai = async (id: number) => {
    const ly = prompt("Lý do mở lại phiếu đã xác nhận (bắt buộc – để sau này còn biết vì sao số đổi):");
    if (!ly) return;
    try { await api(`/fleet/chuyen/${id}/mo-lai`, { method: "POST", json: { ly_do: ly } });
          toast("Đã mở lại – sửa xong nhớ xác nhận lại"); load(); }
    catch (e) { toast(errMsg(e), true); }
  };

  const luuDeXuat = async () => {
    setDangLuu(true);
    try {
      const r = await api<any>("/fleet/de-xuat-chi", { method: "POST", json: formDX });
      toast(r.message); setFormDX(null); load();
    } catch (e) { toast(errMsg(e), true); } finally { setDangLuu(false); }
  };

  const dongViec = async (id: number) => {
    const kl = prompt("Kết luận xác minh (bắt buộc – để lần sau còn biết việc đã xử lý thế nào):");
    if (!kl) return;
    try { await api(`/fleet/xac-minh/${id}/ket-luan`, { method: "POST", json: { status: "xong", resolution: kl } }); toast("Đã đóng việc xác minh"); load(); }
    catch (e) { toast(errMsg(e), true); }
  };

  if (!tq) return <p className="muted">Đang tải…</p>;
  return (<>
    <h1>Đội xe Vietrip – hồ sơ và điều kiện khai thác</h1>
    <p className="muted">Mã xe theo chiếc xe suốt vòng đời, không theo biển số: đổi biển hay chuyển sở hữu đều giữ nguyên lịch sử chuyến và chi phí của chính chiếc xe đó.</p>

    <div className="kpis">
      <div className="kpi"><b>{tq.tong_so_xe}</b><span>xe trong danh mục</span></div>
      <div className="kpi"><b style={{ color: "var(--ok, green)" }}>{tq.san_sang}</b><span>sẵn sàng (đủ hồ sơ, qua kiểm tra)</span></div>
      <div className="kpi"><b style={{ color: "var(--orange)" }}>{tq.chua_du_du_lieu}</b><span>chưa đủ dữ liệu để kết luận</span></div>
      {/* Hai ô dưới đây thêm 07/10/2026. Trước đó dãy ô chỉ in ba trong NĂM mức mà máy chủ trả về,
          nên xe ở mức "cần xem lại" hay "cần duyệt ngoại lệ" biến mất khỏi mọi ô đếm: đo trên hệ
          thật là 16 xe = 0 + 0 + 5, mười một chiếc không ở đâu cả. In điều kiện `> 0` để dãy ô không
          dài ra khi không có xe nào ở mức ấy, nhưng con số thì KHÔNG được phép thiếu. */}
      {tq.can_xem_lai > 0 && <div className="kpi"><b style={{ color: "var(--orange)" }}>{tq.can_xem_lai}</b><span>cần xem lại (có giấy, chưa đối chiếu bản gốc)</span></div>}
      {tq.can_duyet_ngoai_le > 0 && <div className="kpi"><b style={{ color: "var(--orange)" }}>{tq.can_duyet_ngoai_le}</b><span>cần duyệt ngoại lệ</span></div>}
      <div className="kpi"><b style={{ color: tq.bi_chan ? "var(--red)" : undefined }}>{tq.bi_chan}</b><span>đang bị chặn khai thác</span></div>
      <div className="kpi"><b>{tq.viec_xac_minh_dang_mo}</b><span>việc xác minh hồ sơ còn treo</span></div>
    </div>
    {/* Nếu năm mức cộng lại không đủ tổng số xe thì NÓI RA ngay, đừng để người đọc tự trừ. Máy chủ
        tự khai số lệch (`thieu_trong_o_dem`), nên màn hình không phải đoán. */}
    {tq.thieu_trong_o_dem > 0 && <p className="note red">Có <b>{tq.thieu_trong_o_dem}</b> xe không nằm
      trong ô đếm nào ở trên — nghĩa là máy chủ xếp chúng vào một mức mà dãy ô này chưa in. Đừng đọc
      các con số trên như đã đủ; báo CNTT.</p>}
    <p className="muted">{tq.ghi_chu}{tq.chan_khi_thieu_giay ? " Đang BẬT chế độ chặn khi thiếu giấy tờ." : " Chế độ chặn khi thiếu giấy tờ đang TẮT – thiếu hồ sơ chỉ cảnh báo, chưa dừng lệnh điều xe."}</p>

    <div style={{ display: "flex", gap: 8, margin: "10px 0" }}>
      {([["xe", "Hồ sơ xe"], ["chuyen", `Nhật trình chuyến (${chuyen.length})`], ["giaodich", `Đối soát nguồn ngoài (${gd?.rows?.length || 0})`], ["quyettoan", `Chủ xe & quyết toán (${chuXe.length})`], ["congno", "Công nợ đội xe"], ["baoduong", bd ? `Bảo dưỡng (${(bd.theo_muc?.BLOCK || 0) + (bd.theo_muc?.REVIEW || 0)} cần xếp lịch)` : "Bảo dưỡng"], ["baohong", bh ? `Báo hỏng (${bh.dem?.dang_mo || 0} đang mở)` : "Báo hỏng"]] as const)
        .map(([k, ten]) => <button key={k} className={`act ${tab === k ? "teal" : "grey"}`} onClick={() => setTab(k as any)}>{ten}</button>)}
    </div>

    {tab === "chuyen" && <>
      {form?.id && <DinhKem doiTuong="chuyen_xe" doiTuongId={form.id}
        tieuDe={`Chứng từ của phiếu chuyến #${form.id}`}
        goi={"Ảnh hóa đơn dầu, vé cầu đường, phiếu gửi xe, ảnh đồng hồ km. Chứng từ nằm cùng phiếu thì " +
             "đến kỳ quyết toán không phải đi tìm, và người duyệt nhìn thấy đúng thứ họ đang duyệt."} />}
      {/* QT-1 · tờ quyết toán Mẫu 2 đặt NGAY SAU khối đính kèm và NGAY TRÊN biểu phiếu chuyến: người
          nhập cầm tờ giấy trong tay, đính ảnh rồi khai luôn ai trả, không phải đi tìm sang tab khác.
          Chỉ hiện với phiếu ĐÃ CÓ số: chưa lưu phiếu thì chưa có gì để quyết toán. */}
      {form?.id && <QuyetToanChuyen tripId={form.id} toast={toast} />}
      {form && <div className="panel">
        <h2>{form.id ? `Sửa phiếu chuyến #${form.id}` : "Phiếu chi phí xe – nhập mới"}</h2>
        <p className="muted">Đúng bộ trường của phiếu trên Vietrip. Ô để trống nghĩa là <b>chưa có số</b>, không phải bằng 0 –
          hệ thống không tự điền 0 và không tính ra quãng đường âm.</p>
        <div className="grid2">
          <label>Xe
            <select value={form.vehicle_id || ""} onChange={(e) => setForm({ ...form, vehicle_id: Number(e.target.value) })} disabled={!!form.id}>
              <option value="">— chọn xe —</option>
              {xe.map((v: any) => <option key={v.id} value={v.id}>{v.plate}{v.code ? ` · ${v.code}` : ""}</option>)}
            </select></label>
          <label>Tour / khách hàng
            <input value={form.ten_tour || ""} onChange={(e) => setForm({ ...form, ten_tour: e.target.value })} placeholder="Đà Lạt (lẻ)" /></label>
          <label>Ngày đi<input type="date" value={form.ngay_di || ""} onChange={(e) => setForm({ ...form, ngay_di: e.target.value })} /></label>
          <label>Ngày về<input type="date" value={form.ngay_ve || ""} onChange={(e) => setForm({ ...form, ngay_ve: e.target.value })} /></label>
          <label>Km đầu<input type="number" value={form.km_dau ?? ""} onChange={(e) => setForm({ ...form, km_dau: soTien(e.target.value) })} /></label>
          <label>Km cuối<input type="number" value={form.km_cuoi ?? ""} onChange={(e) => setForm({ ...form, km_cuoi: soTien(e.target.value) })} /></label>
          <label>Km theo GPS<input type="number" value={form.km_gps ?? ""} onChange={(e) => setForm({ ...form, km_gps: soTien(e.target.value) })} placeholder="để trống nếu kỳ này chưa lấy số GPS" /></label>
          <label>Nguồn số km
            {/* Ô chọn dựng từ danh mục của máy chủ, KHÔNG gõ lại danh sách ở đây: gõ lại là ngày nào
                đó hai bên lệch nhau mà không ai biết. Nguồn là bắt buộc về nghiệp vụ khi có số GPS —
                lấy GPS so với GPS thì luôn khớp, và cái "luôn khớp" ấy làm người xem tin là đã kiểm. */}
            <select value={form.km_nguon || ""} onChange={(e) => setForm({ ...form, km_nguon: e.target.value })}>
              <option value="">— chọn nguồn —</option>
              {Object.entries(dm2?.km_nguon || {}).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}
            </select></label>
          <label>Doanh thu (đ)<input type="number" value={form.doanh_thu ?? ""} onChange={(e) => setForm({ ...form, doanh_thu: soTien(e.target.value) })} /></label>
          <label>Ghi chú<input value={form.note || ""} onChange={(e) => setForm({ ...form, note: e.target.value })} /></label>
        </div>
        {!form.id && <>
          <h3>Chi phí chuyến</h3>
          <p className="muted">Bốn khoản này Vietourist tạm ứng theo quy tắc chốt 07/9/2026. Để trống khoản nào thì không ghi dòng đó.</p>
          <div className="grid2">
            <label>Tiền dầu (đ)<input type="number" value={form.dau ?? ""} onChange={(e) => setForm({ ...form, dau: soTien(e.target.value) })} /></label>
            <label>Số lít<input type="number" step="0.001" value={form.lit ?? ""} onChange={(e) => setForm({ ...form, lit: soTien(e.target.value) })} /></label>
            <label>Phí cầu đường (đ)<input type="number" value={form.cau_duong ?? ""} onChange={(e) => setForm({ ...form, cau_duong: soTien(e.target.value) })} /></label>
            <label>Công tác phí tài xế (đ)<input type="number" value={form.cong_tac_phi ?? ""} onChange={(e) => setForm({ ...form, cong_tac_phi: soTien(e.target.value) })} /></label>
            <label>Phí gửi xe (đ)<input type="number" value={form.giu_xe ?? ""} onChange={(e) => setForm({ ...form, giu_xe: soTien(e.target.value) })} /></label>
            <label>Số chứng từ<input value={form.chung_tu || ""} onChange={(e) => setForm({ ...form, chung_tu: e.target.value })} /></label>
          </div>
        </>}
        <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
          <button className="act teal" disabled={dangLuu} onClick={luuChuyen}>{dangLuu ? "Đang lưu…" : "Lưu phiếu"}</button>
          <button className="act grey" onClick={() => setForm(null)}>Đóng</button>
        </div>
      </div>}

      {chuyen.some((t: any) => t.nguon === "bao_cao_vietrip") && <div className="panel" style={{ borderColor: "var(--orange)" }}>
        <b>Dữ liệu đối chiếu – CHƯA CHÍNH THỨC.</b>
        <p className="muted">{chuyen.filter((t: any) => t.nguon === "bao_cao_vietrip").length} phiếu trong danh sách dưới
          đây nạp từ báo cáo quyết toán xe của Vietrip để đối chiếu và chạy thử. Số liệu chính thức là phiếu do
          người phụ trách nhập và xác nhận trên VTOS. Đừng lấy các con số này để báo cáo hay quyết toán khi
          chưa được rà lại.</p>
      </div>}
      <div className="panel wrap"><h2>Nhật trình chuyến</h2>
      <p className="muted">Km để trống nghĩa là <b>chưa đo</b>, không phải bằng 0. Cột &quot;Vietourist tạm ứng&quot; và &quot;Chủ xe chịu&quot; tách theo quy tắc chốt 07/9/2026: Vietourist tạm ứng nhiên liệu, cầu đường, công tác phí, bãi xe.</p>
      {canNhap && !form && <div style={{ marginBottom: 10, display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button className="act teal" onClick={() => setForm({ ngay_di: "", ngay_ve: "" })}>+ Nhập phiếu chi phí xe</button>
        {/* Cờ được tính lúc GHI rồi lưu vào dòng. Đo trên hệ thật 07/10/2026: cả 24 chuyến in rõ
            "chưa có số GPS" ở cột km mà cột Cờ vẫn XANH, vì cờ lưu sẵn từ lần nạp trước — màn hình
            và cờ nói hai điều khác nhau về cùng một chuyến. Cửa này chỉ tính lại cờ và lý do cờ:
            không đổi trạng thái, không đổi km, không đổi tiền. */}
        <button className="act grey" onClick={tinhLaiCo}>Tính lại cờ chuyến</button>
      </div>}
      <table><thead><tr><th>Phiếu</th><th>Xe</th><th>Tour</th><th>Đi → về</th><th>Km chạy</th><th>Doanh thu</th><th>VTS tạm ứng</th><th>Chủ xe chịu</th><th>Cờ</th>{canNhap && <th></th>}</tr></thead>
        <tbody>{chuyen.length ? chuyen.map((t) => <tr key={t.id}>
          <td className="muted">{t.ma_phieu || `#${t.id}`}
            {t.nguon === "bao_cao_vietrip" && <div><Tag cls="warn">dữ liệu thử</Tag></div>}</td>
          <td>{t.xe}</td><td>{t.ten_tour || <span className="muted">—</span>}</td>
          <td>{fmtD(t.ngay_di)} → {fmtD(t.ngay_ve)} <span className="muted">({t.so_ngay} ngày)</span></td>
          <td className="num">{t.km_chay === null ? <span className="muted">chưa đo</span> : t.km_chay.toLocaleString("vi-VN")}
            {t.km_nguon_ten && <div className="muted">{t.km_nguon_ten}</div>}
            {t.km_gps ? <div className="muted">GPS {t.km_gps.toLocaleString("vi-VN")}
              {t.km_lech_gps !== null && t.km_lech_gps !== undefined ? ` · lệch ${t.km_lech_gps.toLocaleString("vi-VN")}` : ""}</div>
              : <div className="muted">chưa có số GPS</div>}</td>
          <td className="num">{t.doanh_thu ? t.doanh_thu.toLocaleString("vi-VN") : ""}</td>
          <td className="num">{t.tong_chi_vietourist.toLocaleString("vi-VN")}</td>
          <td className="num">{t.tong_chi_chu_xe.toLocaleString("vi-VN")}</td>
          <td><Tag cls={t.co === "xanh" ? "ok" : t.co === "do" ? "red" : "warn"}>{t.co === "xanh" ? "Xanh" : t.co === "do" ? "Đỏ" : "Vàng"}</Tag>
            {t.co_ly_do && <div className="muted">{t.co_ly_do}</div>}
            {t.note && <div className="muted">{t.note}</div>}</td>
          {canNhap && <td>{t.status === "da_xac_nhan"
            ? <button className="act grey" onClick={() => moLai(t.id)}>Mở lại để sửa</button>
            : <button className="act grey" onClick={() => setForm({
                id: t.id, vehicle_id: t.vehicle_id, ten_tour: t.ten_tour,
                ngay_di: (t.ngay_di || "").slice(0, 10), ngay_ve: (t.ngay_ve || "").slice(0, 10),
                km_dau: t.km_dau, km_cuoi: t.km_cuoi, km_gps: t.km_gps, km_nguon: t.km_nguon,
                doanh_thu: t.doanh_thu, note: t.note })}>Sửa</button>}</td>}
        </tr>) : <tr><td colSpan={canNhap ? 10 : 9} className="muted">Chưa có chuyến nào được ghi nhật trình.</td></tr>}</tbody></table>
      </div>
    </>}

    {tab === "giaodich" && formNga && <div className="panel" style={{ borderColor: "var(--orange)" }}>
      <h2>Định tuyến khoản {formNga.ma_gd}</h2>
      {/* Vì sao hỏi NGẢ chứ không hỏi "của xe nào": phiếu đề xuất chi trên Vietrip gắn vào TOUR và
          không có ô xe (khảo sát 05/9/2026 — bộ trường: tour · NCC · hình thức TT · loại tiền · dòng
          dịch vụ). Hỏi mãi "của xe nào" thì mỗi tháng lại một nắm dòng không ai trả lời được. */}
      <p className="muted">Khoản này chạy về đâu? Chỉ hai ngả <b>của một chiếc xe</b> và <b>của cả đội</b>
        là chi phí đội xe. Ghi ngả KHÔNG tự cộng tiền vào báo cáo — khoản của đội vẫn phải nạp qua cửa
        <b> Chi phí kỳ của đội xe</b>; cộng ở hai đường là tính hai lần đúng một khoản.</p>
      <div className="grid2">
        <label>Ngả
          {/* Danh sách dựng từ máy chủ, không gõ lại ở đây. */}
          <select value={formNga.nga} onChange={(e) => setFormNga({ ...formNga, nga: e.target.value })}>
            <option value="">— chọn ngả —</option>
            {Object.entries(gd?.nga_chi_phi || {}).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}
          </select></label>
        {formNga.nga === "xe" && <label>Biển số xe
          <input value={formNga.bien_so || ""} onChange={(e) => setFormNga({ ...formNga, bien_so: e.target.value })}
            placeholder="50F-034.71" /></label>}
        <label style={{ gridColumn: "1 / -1" }}>Lý do (bắt buộc)
          <input value={formNga.ly_do || ""} onChange={(e) => setFormNga({ ...formNga, ly_do: e.target.value })}
            placeholder="VD: nạp quỹ thẻ dầu của cả đội, không phải chi phí của chiếc nào" /></label>
      </div>
      <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
        <button className="act teal" disabled={dangLuu} onClick={luuNga}>{dangLuu ? "Đang lưu…" : "Lưu ngả"}</button>
        <button className="act grey" onClick={() => setFormNga(null)}>Đóng</button>
      </div>
    </div>}

    {tab === "giaodich" && formDX && <div className="panel">
      <h2>Lập đề xuất chi</h2>
      <p className="muted">Cùng bộ trường với phiếu đề xuất chi trên Vietrip. Bắt buộc chọn <b>nhóm</b>: &quot;nạp thẻ dầu&quot;
        và &quot;sửa xe&quot; nhìn giống nhau lúc lập phiếu, nhưng một cái là nạp quỹ còn một cái là chi phí — không phân loại
        ngay thì cuối tháng phải đọc lại từng phiếu để đoán.</p>
      <div className="grid2">
        <label>Ngày đề xuất<input type="date" value={formDX.ngay || ""} onChange={(e) => setFormDX({ ...formDX, ngay: e.target.value })} /></label>
        <label>Số tiền (đ)<input type="number" value={formDX.so_tien ?? ""} onChange={(e) => setFormDX({ ...formDX, so_tien: soTien(e.target.value) })} /></label>
        <label>Xe (để trống = đề xuất chung)
          <select value={formDX.bien_so || ""} onChange={(e) => setFormDX({ ...formDX, bien_so: e.target.value })}>
            <option value="">— đề xuất chung, không thuộc xe nào —</option>
            {xe.map((v: any) => <option key={v.id} value={v.plate}>{v.plate}</option>)}
          </select></label>
        <label>Nhóm khoản chi
          <select value={formDX.nhom || ""} onChange={(e) => {
            const n = e.target.value;
            setFormDX({ ...formDX, nhom: n, khong_phai_chi_phi: n.startsWith("Nạp quỹ") || n.startsWith("Điều chuyển") });
          }}>
            <option value="">— chọn nhóm —</option>
            <option>Chi phí riêng của xe</option>
            <option>Chi phí chung phân bổ</option>
            <option>Sửa chữa – bảo dưỡng</option>
            <option>Tài xế (công tác phí, lương)</option>
            <option>Quyết toán chủ xe / đối tác</option>
            <option>Nạp quỹ / tạm ứng (không phải chi phí)</option>
            <option>Điều chuyển tiền nội bộ (không phải chi phí)</option>
          </select></label>
        <label>Số chứng từ<input value={formDX.chung_tu || ""} onChange={(e) => setFormDX({ ...formDX, chung_tu: e.target.value })} placeholder="HĐ 0000xxxx" /></label>
        <label>Người / đơn vị thụ hưởng<input value={formDX.nguoi_thu_huong || ""} onChange={(e) => setFormDX({ ...formDX, nguoi_thu_huong: e.target.value })} /></label>
        <label>Số tài khoản<input value={formDX.so_tai_khoan || ""} onChange={(e) => setFormDX({ ...formDX, so_tai_khoan: e.target.value })} /></label>
        <label>Ngân hàng<input value={formDX.ngan_hang || ""} onChange={(e) => setFormDX({ ...formDX, ngan_hang: e.target.value })} /></label>
      </div>
      <label style={{ display: "block", marginTop: 8 }}>Nội dung đề xuất
        <textarea rows={4} value={formDX.noi_dung || ""} onChange={(e) => setFormDX({ ...formDX, noi_dung: e.target.value })} /></label>
      {formDX.khong_phai_chi_phi && <p className="muted">Khoản này được đánh dấu <b>không phải chi phí kỳ này</b> nên
        sẽ không cộng vào tổng chi phí đội xe — tiền dầu thật nằm ở phiếu chi phí của từng chuyến.</p>}
      <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
        <button className="act teal" disabled={dangLuu} onClick={luuDeXuat}>{dangLuu ? "Đang lưu…" : "Lập đề xuất"}</button>
        <button className="act grey" onClick={() => setFormDX(null)}>Đóng</button>
      </div>
    </div>}

    {tab === "giaodich" && gd?.rows?.some((r: any) => r.source === "de_xuat_vietrip") && <div className="panel" style={{ borderColor: "var(--orange)" }}>
      <b>Dữ liệu đối chiếu – CHƯA CHÍNH THỨC.</b>
      <p className="muted">Các dòng nguồn &quot;Đề xuất chi trên phần mềm Vietrip&quot; là bản trích để đối chiếu và
        chạy thử, không phải sổ chi phí đã duyệt của VTOS.</p>
    </div>}

    {tab === "giaodich" && gd && <div className="panel wrap"><h2>Đối soát dữ liệu nguồn ngoài</h2>
      {canNhap && !formDX && <div style={{ marginBottom: 10, display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button className="act teal" onClick={() => setFormDX({ ngay: new Date().toISOString().slice(0, 10) })}>+ Lập đề xuất chi</button>
        <button className="act grey" onClick={traLaiXe}>Tra lại xe theo biển</button>
      </div>}
      <div className="kpis">
        <div className="kpi"><b>{Number(gd.tong_chi_phi || 0).toLocaleString("vi-VN")}</b><span>chi phí (đã loại bản ghi lặp)</span></div>
        <div className="kpi"><b style={{ color: "var(--orange)" }}>{Number(gd.tong_chua_quy_ve_xe || 0).toLocaleString("vi-VN")}</b><span>chưa quy được về xe nào</span></div>
        <div className="kpi"><b className="muted">{Number(gd.tong_dieu_chuyen || 0).toLocaleString("vi-VN")}</b><span>điều chuyển tiền nội bộ – KHÔNG phải chi phí</span></div>
        {gd.tong_chua_dinh_tuyen > 0 && <div className="kpi"><b style={{ color: "var(--orange)" }}>{Number(gd.tong_chua_dinh_tuyen).toLocaleString("vi-VN")}</b><span>chưa định tuyến – chưa biết của xe, của đội hay của tour</span></div>}
        {gd.tong_chua_quy_ve_vi > 0 && <div className="kpi"><b style={{ color: "var(--orange)" }}>{Number(gd.tong_chua_quy_ve_vi).toLocaleString("vi-VN")}</b><span>ePass chưa ghi tài khoản – chưa quy về pháp nhân nào</span></div>}
      </div>
      <p className="muted">{gd.ghi_chu} Biển số được tra về xe theo <b>thời điểm giao dịch</b>, không theo biển hiện tại — xe đổi biển giữa kỳ vẫn gộp đúng về một chiếc.</p>
      {/* Chia theo NGẢ. Trước 07/10/2026 màn hình chỉ có MỘT con số "chưa quy được về xe nào", và
          trên hệ thật nó bằng ĐÚNG tổng chi phí — 1.121.825.494 đ, 100%, cả 36 dòng. Con số ấy đọc
          ra như "chi phí đội xe chưa gắn xe", trong khi phần lớn là khoản của TOUR: phiếu đề xuất
          chi trên Vietrip gắn vào tour và KHÔNG có ô xe (khảo sát 05/9/2026). Gộp hai thứ khác bản
          chất vào một con số thì mỗi tháng báo động một tỷ hai mà không ai làm được gì — rồi quen
          dần và thôi nhìn. */}
      {gd.theo_nga?.length > 0 && <>
        <h3>Chia theo ngả</h3>
        <table><thead><tr><th>Ngả</th><th>Của đội xe?</th><th>Số khoản</th><th>Số tiền</th></tr></thead>
          <tbody>{gd.theo_nga.map((n: any) => <tr key={n.nga || "chua"}>
            <td>{n.nga ? n.ten : <Tag cls="warn">{n.ten}</Tag>}</td>
            <td>{n.nga ? (n.cua_doi_xe ? <b>có</b> : <span className="muted">không</span>) : <span className="muted">—</span>}</td>
            <td>{n.so_khoan}</td>
            <td className="num">{Number(n.so_tien).toLocaleString("vi-VN")}</td>
          </tr>)}</tbody></table>
        <p className="muted">Chỉ hai ngả <b>của một chiếc xe</b> và <b>của cả đội</b> là chi phí đội xe.
          Khoản của <b>tour</b> nằm ở bảng này là đúng chỗ, không thiếu gì cả. Khoản của <b>chủ xe</b>
          đi qua khối quyết toán chủ xe — cộng cả hai nơi là tính hai lần đúng một khoản.</p>
      </>}

      {/* Chia theo VÍ ePass. Đội xe đi đường bằng hai ví của hai pháp nhân khác nhau; cộng chung thì
          tổng vẫn đúng mà phần của từng bên sai — nên không ai nhìn ra. Phần "chưa ghi tài khoản" là
          nợ số liệu của các kỳ cũ: nạp lại tệp có cột tài khoản là hết, KHÔNG chia hộ theo tỷ lệ. */}
      {gd.theo_vi?.length > 0 && <>
        <h3>Phí cầu đường theo ví ePass</h3>
        <table><thead><tr><th>Ví / pháp nhân</th><th>Số tài khoản</th><th>Số khoản</th><th>Số tiền</th></tr></thead>
          <tbody>{gd.theo_vi.map((v: any) => <tr key={v.tai_khoan || "khong"}>
            <td>{v.tai_khoan && gd.vi_epass?.[v.tai_khoan] ? v.ten : <Tag cls="warn">{v.ten}</Tag>}</td>
            <td className="muted">{v.tai_khoan || "—"}</td><td>{v.so_khoan}</td>
            <td className="num">{Number(v.so_tien).toLocaleString("vi-VN")}</td>
          </tr>)}</tbody></table>
        {gd.theo_vi.length === 1 && gd.theo_vi[0].tai_khoan === "" && <p className="muted">Toàn bộ giao dịch
          ePass hiện chưa ghi số tài khoản, nên chưa tách được chi phí cầu đường của hai pháp nhân. Nạp lại
          sao kê theo từng ví (cửa nạp &quot;Phí cầu đường&quot; đã có ô <b>Tài khoản ePass</b>) là tách được.</p>}
      </>}
      {gd.theo_nhom?.length > 1 && <table><thead><tr><th>Nhóm khoản</th><th>Số khoản</th><th>Số tiền</th></tr></thead>
        <tbody>{gd.theo_nhom.map((n: any) => <tr key={n.nhom}>
          <td>{n.nhom}</td><td>{n.so_khoan}</td><td className="num">{Number(n.so_tien).toLocaleString("vi-VN")}</td>
        </tr>)}</tbody></table>}
      <table><thead><tr><th>Nguồn</th><th>Mã giao dịch</th><th>Thời điểm</th><th>Biển / thẻ</th><th>Xe</th><th>Nhóm</th><th>Ngả</th><th>Số tiền</th><th>Trạng thái</th></tr></thead>
        <tbody>{gd.rows.length ? gd.rows.map((r: any) => <tr key={r.id}>
          <td>{r.source_ten || (r.source === "epass" ? "ePass/VETC" : "Thẻ dầu")}</td><td>{r.ma_gd}</td><td>{fmtDT(r.thoi_diem)}</td>
          <td>{r.bien_so || (r.the_4so ? `••••${r.the_4so}` : "")}
            {r.source === "epass" && <div className="muted">{r.vi || (r.tai_khoan ? `ví ${r.tai_khoan} – chưa khai` : "chưa ghi ví")}</div>}</td>
          <td>{r.xe || (r.khong_phai_chi_phi ? <span className="muted">không thuộc xe nào</span> : <Tag cls="red">chưa tra được xe</Tag>)}</td>
          <td className="muted">{r.nhom || ""}</td>
          <td>{r.nga ? <><span>{r.nga_ten}</span>{r.nga_ly_do && <div className="muted">{r.nga_ly_do}</div>}
              {r.nga_boi && <div className="muted">— {r.nga_boi}</div>}</>
            : <Tag cls="warn">chưa định tuyến</Tag>}
            {canNhap && <div><button className="act grey" onClick={() => setFormNga({
              ma_gd: r.ma_gd, nga: r.nga || "", ly_do: "", bien_so: r.bien_so || "" })}>
              {r.nga ? "Đổi ngả" : "Định tuyến"}</button></div>}</td>
          <td className="num">{r.so_tien.toLocaleString("vi-VN")}</td>
          <td><Tag cls={r.co === "do" ? "red" : "warn"}>{r.khop === "da_khop" ? "Đã khớp chuyến" : "Chưa khớp chuyến"}</Tag>
            {r.ghi_chu && <div className="muted">{r.ghi_chu}</div>}</td>
        </tr>) : <tr><td colSpan={9} className="muted">Chưa nhập sao kê thẻ dầu, báo cáo ePass hay đề xuất chi Vietrip nào.</td></tr>}</tbody></table>
    </div>}

    {tab === "quyettoan" && <>
      {dm3 && <div className="panel"><h2>Người được tạo và chốt lệnh điều xe</h2>
        {dm3.nguoi_lap_lenh?.length
          ? <p>{dm3.nguoi_lap_lenh.map((x: any) => <Tag key={x.username} cls="ok">{x.full_name} ({x.username})</Tag>)} <span className="muted">— chỉ đạo 07/9/2026. Thay người phụ trách thì sửa tham số chính sách <code>xe_nguoi_lap_lenh</code>, không phải sửa phần mềm.</span></p>
          : <p><Tag cls="warn">Chưa áp dụng</Tag> <span className="muted">{dm3.nguoi_lap_lenh_ghi_chu}</span></p>}
      </div>}

      <div className="panel wrap"><h2>Chủ xe hợp tác ({chuXe.length})</h2>
        <table><thead><tr><th>Chủ xe</th><th>Pháp nhân đối ứng</th><th>Xe</th><th>Công nợ còn lại</th><th>Định danh</th></tr></thead>
          <tbody>{chuXe.length ? chuXe.map((p) => <tr key={p.id}>
            <td><b>{p.ho_ten}</b>{p.phone && <div className="muted">{p.phone}</div>}</td>
            <td>{p.company || <span className="muted">chưa xác định</span>}</td>
            <td>{p.xe.join(", ") || <span className="muted">chưa gán xe</span>}</td>
            <td className="num">{p.cong_no_con_lai.toLocaleString("vi-VN")}</td>
            <td>{p.xac_minh === "da_xac_minh" ? <Tag cls="ok">đã đối chiếu</Tag> : <Tag cls="warn">theo nguồn</Tag>}</td>
          </tr>) : <tr><td colSpan={5} className="muted">Chưa có chủ xe hợp tác nào trong hệ thống.</td></tr>}</tbody></table>
      </div>

      <div className="panel wrap"><h2>Quyết toán chủ xe theo kỳ ({qt.length})</h2>
        <p className="muted">Kỳ là tháng dương lịch, chuyến gán theo ngày khởi hành. <b>Số âm ghi thành phải thu và chuyển kỳ sau, không tạo phiếu chi âm.</b> Đóng kỳ rồi thì khóa — sửa phải ghi bút toán điều chỉnh ở kỳ sau.</p>
        <table><thead><tr><th>Kỳ</th><th>Chủ xe</th><th>Doanh thu</th><th>Đối tác chịu</th><th>Điều chỉnh</th><th>Trước cấn trừ</th><th>Cấn trừ</th><th>Phải trả</th><th>Chuyển kỳ sau</th><th>Trạng thái</th></tr></thead>
          <tbody>{qt.length ? qt.map((s) => <tr key={s.id}>
            <td>{s.ky}</td><td>{s.chu_xe}</td>
            <td className="num">{s.doanh_thu.toLocaleString("vi-VN")}</td>
            <td className="num">{s.doi_tac_chiu.toLocaleString("vi-VN")}</td>
            <td className="num">{s.dieu_chinh.toLocaleString("vi-VN")}</td>
            <td className="num">{s.truoc_can_tru.toLocaleString("vi-VN")}</td>
            <td className="num">{s.can_tru.toLocaleString("vi-VN")}</td>
            <td className="num"><b>{s.sau_can_tru.toLocaleString("vi-VN")}</b></td>
            <td className="num">{s.chuyen_ky_sau ? <Tag cls="warn">{s.chuyen_ky_sau.toLocaleString("vi-VN")}</Tag> : ""}</td>
            <td>{s.status === "dong_ky" ? <Tag cls="ok">{s.status_ten}</Tag> : <Tag cls="warn">{s.status_ten}</Tag>}</td>
          </tr>) : <tr><td colSpan={10} className="muted">Chưa dựng kỳ quyết toán nào.</td></tr>}</tbody></table>
      </div>
    </>}

    {tab === "congno" && cn && <>
      <div className="panel">
        <h2>Công nợ đội xe</h2>
        <p className="muted">Bốn khoản dưới đây với bốn đối tượng khác nhau nên để riêng, KHÔNG cộng thành một
          con số &quot;công nợ đội xe&quot;. Tính đến {fmtDT(cn.tinh_den)}.</p>
        <div className="kpis">
          <div className="kpi"><b>{Number(cn.voi_chu_xe.cong_ty_phai_tra).toLocaleString("vi-VN")}</b>
            <span>công ty phải trả chủ xe (kỳ đã chốt, đã trừ phần đã chi)</span></div>
          <div className="kpi"><b>{Number(cn.voi_chu_xe.chu_xe_phai_tra_cong_ty).toLocaleString("vi-VN")}</b>
            <span>chủ xe phải trả công ty (chuyển kỳ sau + nợ theo lịch)</span></div>
          <div className="kpi"><b>{Number(cn.ban_xe.con_phai_thu).toLocaleString("vi-VN")}</b>
            <span>còn phải thu của người mua xe</span></div>
          <div className="kpi"><b>{Number(cn.vay_the_chap_xe.du_no_theo_khe_uoc).toLocaleString("vi-VN")}</b>
            <span>dư nợ ngân hàng có thế chấp xe (cộng theo khế ước)</span></div>
        </div>
        <div className="kpis">
          <div className="kpi"><b style={{ color: "var(--orange)" }}>{Number(cn.voi_chu_xe.dang_tinh_chua_chot).toLocaleString("vi-VN")}</b>
            <span>đang tính, chưa chốt với đối tác – chưa phải công nợ</span></div>
          <div className="kpi"><b style={{ color: "var(--orange)" }}>{Number(cn.voi_chu_xe.chi_ho_chua_vao_ky).toLocaleString("vi-VN")}</b>
            <span>công ty đã chi hộ nhưng tháng đó chưa dựng bảng quyết toán</span></div>
          <div className="kpi"><b style={{ color: cn.voi_chu_xe.so_chu_xe_chua_co_bang ? "var(--orange)" : undefined }}>{cn.voi_chu_xe.so_chu_xe_chua_co_bang}</b>
            <span>chủ xe chưa có bảng quyết toán nào (chưa biết, không phải bằng 0)</span></div>
        </div>
        <ul className="muted" style={{ marginTop: 8 }}>{cn.giai_thich.map((g: string, i: number) => <li key={i}>{g}</li>)}</ul>
      </div>

      <div className="panel wrap">
        <h2>Theo chủ xe hợp tác</h2>
        <table><thead><tr><th>Chủ xe</th><th>Xe</th><th>Công ty phải trả</th><th>Đang tính, chưa chốt</th>
          <th>Chủ xe phải trả công ty</th><th>Chi hộ chưa vào kỳ</th><th>Tình trạng</th><th></th></tr></thead>
          <tbody>{cn.voi_chu_xe.chi_tiet.length ? cn.voi_chu_xe.chi_tiet.map((c: any) => <tr key={c.partner_id}>
            <td>{c.ho_ten}</td>
            <td className="muted">{c.xe.map((x: any) => x.plate).join(", ") || "—"}</td>
            <td>{Number(c.cong_ty_phai_tra).toLocaleString("vi-VN")}</td>
            <td className="muted">{Number(c.dang_tinh_chua_chot).toLocaleString("vi-VN")}</td>
            <td>{Number(c.chu_xe_phai_tra_cong_ty).toLocaleString("vi-VN")}</td>
            <td className={c.tong_chi_ho_chua_vao_ky ? "" : "muted"}>{Number(c.tong_chi_ho_chua_vao_ky).toLocaleString("vi-VN")}</td>
            <td>{c.tinh_trang === "chua_co_bang_quyet_toan"
              ? <Tag cls="warn">Chưa có bảng quyết toán</Tag> : <Tag cls="ok">Có dữ liệu</Tag>}</td>
            <td><button className="act grey" onClick={async () => {
              try { setSoChuXe(await api(`/fleet/cong-no/chu-xe/${c.partner_id}`)); } catch (e) { toast(errMsg(e), true); }
            }}>Sổ chi tiết</button></td>
          </tr>) : <tr><td colSpan={8} className="muted">Chưa có chủ xe hợp tác nào.</td></tr>}</tbody></table>
      </div>

      {soChuXe && <div className="panel wrap">
        <h2>Sổ chi tiết – {soChuXe.ho_ten}</h2>
        {soChuXe.ghi_chu && <p className="muted">{soChuXe.ghi_chu}</p>}
        <h3>Từng kỳ quyết toán</h3>
        <table><thead><tr><th>Kỳ</th><th>Trạng thái</th><th>Doanh thu</th><th>Đối tác chịu</th><th>Cấn trừ</th>
          <th>Phải trả theo bảng</th><th>Đã trả</th><th>Còn phải trả</th><th>Chuyển kỳ sau</th></tr></thead>
          <tbody>{soChuXe.cac_ky.length ? soChuXe.cac_ky.map((k: any) => <tr key={k.settlement_id}>
            <td>{k.ky}</td>
            <td>{k.da_chot ? <Tag cls="ok">Đã chốt</Tag> : <Tag cls="warn">Đang tính</Tag>}</td>
            <td>{Number(k.doanh_thu).toLocaleString("vi-VN")}</td>
            <td>{Number(k.doi_tac_chiu).toLocaleString("vi-VN")}</td>
            <td>{Number(k.can_tru).toLocaleString("vi-VN")}</td>
            <td>{Number(k.phai_tra_theo_bang).toLocaleString("vi-VN")}</td>
            <td>{Number(k.da_tra).toLocaleString("vi-VN")}</td>
            <td><b>{k.da_chot ? Number(k.con_phai_tra).toLocaleString("vi-VN") : "—"}</b></td>
            <td className="muted">{Number(k.chuyen_ky_sau).toLocaleString("vi-VN")}</td>
          </tr>) : <tr><td colSpan={9} className="muted">Chưa dựng kỳ nào cho chủ xe này.</td></tr>}</tbody></table>

        {soChuXe.lich_can_tru.length > 0 && <><h3>Lịch cấn trừ (nợ mua xe)</h3>
          <table><thead><tr><th>Lịch</th><th>Trạng thái</th><th>Gốc</th><th>Đã cấn trừ</th><th>Còn lại</th></tr></thead>
            <tbody>{soChuXe.lich_can_tru.map((l: any) => <tr key={l.plan_id}>
              <td>{l.ten}</td><td>{l.status}</td>
              <td>{Number(l.principal).toLocaleString("vi-VN")}</td>
              <td>{Number(l.da_can_tru).toLocaleString("vi-VN")}</td>
              <td><b>{Number(l.con_lai).toLocaleString("vi-VN")}</b></td>
            </tr>)}</tbody></table></>}

        {soChuXe.chi_ho_chua_vao_ky.length > 0 && <><h3>Khoản đã chi hộ chưa vào kỳ quyết toán nào</h3>
          <p className="muted">Tiền công ty đã bỏ ra nhưng tháng đó chưa ai dựng bảng – trên giấy tờ chưa ai nợ khoản này.</p>
          <table><thead><tr><th>Tháng</th><th>Số tiền</th></tr></thead>
            <tbody>{soChuXe.chi_ho_chua_vao_ky.map((x: any) => <tr key={x.ky}>
              <td>{x.ky}</td><td>{Number(x.so_tien).toLocaleString("vi-VN")}</td></tr>)}</tbody></table></>}

        <h3>Đã trả / đã thu</h3>
        <table><thead><tr><th>Ngày</th><th>Hướng</th><th>Số tiền</th><th>Kỳ</th><th>Chứng từ</th><th>Người ghi</th></tr></thead>
          <tbody>{soChuXe.thanh_toan?.length ? soChuXe.thanh_toan.map((t: any) => <tr key={t.id}>
            <td>{fmtD(t.ngay)}</td><td>{t.huong_ten}</td>
            <td>{Number(t.so_tien).toLocaleString("vi-VN")}</td>
            <td className="muted">{t.settlement_id || "—"}</td>
            <td className="muted">{t.chung_tu || "—"}</td><td className="muted">{t.boi}</td>
          </tr>) : <tr><td colSpan={6} className="muted">Chưa ghi nhận lần trả/thu nào. Đóng kỳ KHÔNG có nghĩa là tiền đã đi.</td></tr>}</tbody></table>
      </div>}

      <div className="panel wrap">
        <h2>Còn phải thu của người mua xe</h2>
        <table><thead><tr><th>Xe</th><th>Giá bán</th><th>Đã thu</th><th>Còn phải thu</th><th>Bàn giao</th>
          <th>Giải chấp</th><th>Sang tên</th><th>Cảnh báo</th></tr></thead>
          <tbody>{cn.ban_xe.chi_tiet.length ? cn.ban_xe.chi_tiet.map((b: any) => <tr key={b.sale_case_id}>
            <td>{b.xe}</td>
            <td>{Number(b.gia_ban).toLocaleString("vi-VN")}</td>
            <td>{Number(b.da_thu).toLocaleString("vi-VN")}</td>
            <td><b>{Number(b.con_phai_thu).toLocaleString("vi-VN")}</b></td>
            <td>{b.da_ban_giao ? "Rồi" : "Chưa"}</td>
            <td>{b.da_giai_chap ? "Rồi" : "Chưa"}</td>
            <td>{b.da_sang_ten ? "Rồi" : "Chưa"}</td>
            <td>{b.canh_bao ? <Tag cls="red">{b.canh_bao}</Tag> : ""}</td>
          </tr>) : <tr><td colSpan={8} className="muted">Không có hồ sơ bán xe nào còn phải thu.</td></tr>}</tbody></table>
      </div>

      <div className="panel wrap">
        <h2>Dư nợ ngân hàng có thế chấp xe</h2>
        <p className="muted">Cộng theo KHẾ ƯỚC. Ngân hàng nhận cả gói nhiều xe cho một khoản vay, nên chia dư nợ
          về từng xe rồi cộng lại sẽ ra một con số không có thật.</p>
        <table><thead><tr><th>Khế ước</th><th>Ngân hàng</th><th>Pháp nhân</th><th>Dư nợ</th><th>Lãi suất</th>
          <th>Đáo hạn</th><th>Xe đang thế chấp</th></tr></thead>
          <tbody>{cn.vay_the_chap_xe.chi_tiet.length ? cn.vay_the_chap_xe.chi_tiet.map((k: any) => <tr key={k.contract_id}>
            <td>{k.code}</td><td>{k.ngan_hang}</td><td className="muted">{k.phap_nhan}</td>
            <td><b>{Number(k.du_no).toLocaleString("vi-VN")}</b></td>
            <td className="muted">{k.lai_suat}%</td>
            <td className="muted">{k.dao_han ? fmtD(k.dao_han) : "Hồ sơ không ghi"}</td>
            <td className="muted">{k.xe.map((x: any) => x.plate).join(", ")}</td>
          </tr>) : <tr><td colSpan={7} className="muted">Không có khế ước nào đang thế chấp xe.</td></tr>}</tbody></table>
      </div>
    </>}

    {tab === "xe" && <div className="panel wrap"><h2>Danh sách xe ({xe.length})</h2>
      <table><thead><tr><th>Mã xe</th><th>Biển đang dùng</th><th>Quyền khai thác</th><th>Vòng đời</th><th>Pháp nhân sở hữu</th><th>Đối tác</th><th>Hợp đồng</th><th>Tài xế</th><th>Điều kiện hôm nay</th></tr></thead>
        <tbody>{xe.map((v) => <tr key={v.id} onClick={() => mo(v.id)} style={{ cursor: "pointer" }}>
          <td><b>{v.code || "—"}</b></td><td>{v.plate}</td><td>{v.op_right_ten}</td><td>{v.lifecycle_ten}</td>
          <td>{v.owner_company || <span className="muted">chưa xác định</span>}</td>
          <td>{v.partner_name || ""}</td><td>{v.contract_ref || ""}</td><td>{v.driver || <span className="muted">chưa gán</span>}</td>
          <td><Tag cls={MUC_CLS[v.san_sang?.muc] || ""}>{MUC_TEN[v.san_sang?.muc] || v.san_sang?.muc}</Tag>
            {v.san_sang?.ly_do?.length > 0 && <div className="muted">{v.san_sang.ly_do[0]}</div>}</td>
        </tr>)}</tbody></table>
    </div>}

    {tab === "xe" && chon && <div className="panel"><h2>Hồ sơ xe {chon.code} · {chon.plate}</h2>
      <p className="muted">Số khung {chon.vin || "chưa nhập"} · {chon.seats} chỗ · đồng hồ {chon.odo_km ? `${chon.odo_km.toLocaleString("vi-VN")} km` : "chưa nhập"}{chon.odo_at ? ` (ghi ngày ${fmtD(chon.odo_at)})` : ""}</p>
      <div className="grid">
        <div><h3>Lịch sử biển số</h3>
          <table><tbody>{chon.lich_su_bien.map((p: any, i: number) => <tr key={i}>
            <td>{p.plate} {p.to_date === null && <Tag cls="ok">đang dùng</Tag>}</td>
            <td className="muted">{p.from_date ? fmtD(p.from_date) : "?"} → {p.to_date ? fmtD(p.to_date) : "nay"}</td>
            <td className="muted">{p.source}</td></tr>)}</tbody></table>
        </div>
        <div><h3>Giấy tờ có hạn</h3>
          {chon.giay_to.length ? <table><tbody>{chon.giay_to.map((g: any) => <tr key={g.id}>
            <td>{g.kind_ten} <span className="muted">({g.cho_ai === "xe" ? "của xe" : "của tài xế"})</span></td>
            <td>{g.number || <span className="muted">chưa có số</span>}</td>
            <td>{g.expires_on ? <>hết hạn {fmtD(g.expires_on)}</> : <Tag cls="warn">chưa có ngày hết hạn</Tag>}</td>
            <td>{g.verify === "da_xac_minh" ? <Tag cls="ok">đã đối chiếu gốc</Tag> : <Tag cls="warn">theo nguồn</Tag>}</td>
          </tr>)}</tbody></table> : <p className="muted">Chưa có giấy tờ nào trong hồ sơ – hệ thống KHÔNG kết luận xe còn hạn.</p>}
        </div>
      </div>
      {chon.san_sang?.ly_do?.length > 0 && <p><Tag cls={MUC_CLS[chon.san_sang.muc]}>{MUC_TEN[chon.san_sang.muc]}</Tag> {chon.san_sang.ly_do.join(" · ")}</p>}
      <button className="act grey" onClick={() => setChon(null)}>Đóng</button>
    </div>}

    {/* Ô đính kèm cho HỒ SƠ XE. Máy chủ khai "xe" là đối tượng gắn được tệp từ đầu, nhóm hồ sơ 01_Pháp lý,
        nhưng đến 09/9/2026 không màn hình nào dựng ô ấy – nên bản chụp đăng kiểm, bảo hiểm, phù hiệu không
        có chỗ nào để nằm. Điều đó không chỉ bất tiện: tham số xe_chan_khi_thieu_giay chặn phát lệnh khi xe
        thiếu giấy, mà giấy thì chỉ có dòng khai hạn chứ không có bản chụp – bật cổng ấy lên thành ra tin
        vào một ô ngày do người gõ, không có gì đối chiếu.

        doiTuongId dùng MÃ XE, không dùng biển số. Biển đổi thì hồ sơ vẫn phải nằm cùng một chỗ – đó đúng
        là lý do hệ thống có cột mã xe cố định bên cạnh lịch sử biển. */}
    {tab === "xe" && chon && (chon.code
      ? <DinhKem doiTuong="xe" doiTuongId={chon.code} loai="hop_dong"
                 tieuDe={`Giấy tờ xe ${chon.code} · ${chon.plate}`} />
      : <div className="panel"><h2>Giấy tờ xe</h2>
          <p className="muted">Xe này <b>chưa có mã xe cố định</b> nên chưa gắn tệp được. Tệp gắn theo mã chứ
          không theo biển – biển đổi mà hồ sơ đi theo biển thì giấy tờ của một chiếc xe nằm rải ở hai chỗ.
          Đặt mã cho xe ở bảng trên rồi quay lại.</p></div>)}

    {/* ── 4.9.6 · BẢO DƯỠNG & SỬA CHỮA ────────────────────────────────────────────────────────
        Bảng `fleet_maintenance`, hai cửa API và thuật toán `moc_bao_duong()` có từ Đợt 1; tới
        29/9/2026 KHÔNG màn hình nào gọi tới, nên mục 4.9.6 của cây phân hệ vẫn trống và đội xe
        không có chỗ nhập lịch bảo dưỡng. Đây là chỗ đó.

        Màn hình KHÔNG tự tính mốc hay ngưỡng: cả cột "còn bao nhiêu km" lẫn mức Chặn/Cần xem lại
        đều do `/fleet/bao-duong/theo-xe` trả về, và cửa ấy gọi đúng hàm mà bộ điều kiện phát lệnh
        điều xe đang dùng. Chép ngưỡng sang đây là dựng công thức thứ hai cho cùng một luật. */}
    {tab === "baoduong" && <>
      {bd && <div className="kpis">
        <div className="kpi"><b style={{ color: bd.theo_muc?.BLOCK ? "var(--red)" : undefined }}>{bd.theo_muc?.BLOCK || 0}</b><span>đã vượt mốc – chặn phát lệnh</span></div>
        <div className="kpi"><b style={{ color: bd.theo_muc?.REVIEW ? "var(--orange)" : undefined }}>{bd.theo_muc?.REVIEW || 0}</b><span>sắp tới mốc – cần xếp lịch garage</span></div>
        <div className="kpi"><b style={{ color: bd.theo_muc?.UNKNOWN ? "var(--orange)" : undefined }}>{bd.theo_muc?.UNKNOWN || 0}</b><span>chưa đủ dữ liệu để kết luận</span></div>
        <div className="kpi"><b>{bd.theo_muc?.OK || 0}</b><span>còn trong hạn</span></div>
      </div>}
      {bd?.ghi_chu && <p className="muted">{bd.ghi_chu}</p>}

      <div className="panel wrap">
        <h2>Từng xe đứng đâu so với mốc</h2>
        <table><thead><tr>
          <th>Xe</th><th className="num">Đồng hồ</th><th className="num">Mốc kỳ tới</th>
          <th className="num">Còn</th><th>Nguồn mốc</th><th>Tình trạng</th>{canNhap && <th></th>}
        </tr></thead><tbody>
          {(bd?.xe || []).map((x: any) => <tr key={x.vehicle_id}>
            <td><b>{x.code || x.plate}</b>{x.code && <div className="muted">{x.plate}</div>}</td>
            <td className="num">{x.odo_km ? `${x.odo_km.toLocaleString("vi-VN")} km` : <span className="muted" title="Chưa có số – khác với bằng 0">—</span>}
              {x.odo_at && <div className="muted">{fmtD(x.odo_at)}</div>}</td>
            <td className="num">{x.km_ky_toi ? `${x.km_ky_toi.toLocaleString("vi-VN")} km` : <span className="muted">—</span>}</td>
            <td className="num">{x.con_km === null || x.con_km === undefined
              ? <span className="muted">—</span>
              : <b className={x.con_km < 0 ? "red" : ""}>{x.con_km.toLocaleString("vi-VN")} km</b>}</td>
            <td className="muted">{x.nguon === "ghi_tren_phieu" ? "Ghi trên phiếu lần trước"
              : x.nguon === "chu_ky_chung" ? "Chu kỳ chung (phiếu trước không ghi mốc)"
              : x.nguon === "chua_co_lich_su" ? "Chưa có lịch sử"
              : x.nguon === "phieu_thieu_km" ? "Phiếu trước thiếu số km" : x.nguon}</td>
            <td><Tag cls={MUC_CLS[x.muc]}>{MUC_TEN[x.muc]}</Tag>
              {x.loi && <div className="muted">{x.loi}</div>}
              {x.viec && <div className="muted"><b>Việc cần làm:</b> {x.viec}</div>}</td>
            {canNhap && <td><button className="act teal" onClick={() => setFormBD({
              vehicle_id: x.vehicle_id, ngay: new Date().toISOString().slice(0, 10), kind: "dinh_ky",
              km_luc_lam: x.odo_km || "", km_ky_toi: "", noi_dung: "", garage: "", so_tien: "", chung_tu: "",
            })}>Ghi phiếu</button></td>}
          </tr>)}
          {!bd?.xe?.length && <tr><td colSpan={canNhap ? 7 : 6} className="muted">Chưa có xe nào đang khai thác.</td></tr>}
        </tbody></table>
      </div>

      {formBD && <div className="panel">
        <h2>Ghi phiếu bảo dưỡng / sửa chữa</h2>
        <p className="muted">
          Bỏ trống <b>mốc kỳ tới</b> thì hệ thống nói thẳng là chưa tính được, <b>không</b> suy ra từ
          chu kỳ chung — suy ra là cách chi phí bị ghi sai kỳ mà không ai phát hiện.
        </p>
        <div className="grid">
          <div><label>Xe</label>
            <select value={formBD.vehicle_id} onChange={(e) => setFormBD({ ...formBD, vehicle_id: e.target.value })}>
              {xe.map((v: any) => <option key={v.id} value={v.id}>{v.code || v.plate} · {v.plate}</option>)}
            </select></div>
          <div><label>Ngày thực hiện</label>
            <input type="date" value={formBD.ngay} onChange={(e) => setFormBD({ ...formBD, ngay: e.target.value })} /></div>
          <div><label>Loại</label>
            <select value={formBD.kind} onChange={(e) => setFormBD({ ...formBD, kind: e.target.value })}>
              <option value="dinh_ky">Bảo dưỡng định kỳ</option>
              <option value="sua_chua">Sửa chữa</option>
              <option value="vo_xe">Vỏ xe</option>
              <option value="khac">Khác</option>
            </select></div>
          <div><label>Km lúc làm</label>
            <input value={formBD.km_luc_lam} onChange={(e) => setFormBD({ ...formBD, km_luc_lam: e.target.value })} /></div>
          <div><label>Mốc km kỳ tới (ghi trên phiếu)</label>
            <input value={formBD.km_ky_toi} onChange={(e) => setFormBD({ ...formBD, km_ky_toi: e.target.value })} /></div>
          <div><label>Garage</label>
            <input value={formBD.garage} onChange={(e) => setFormBD({ ...formBD, garage: e.target.value })} /></div>
          <div><label>Số tiền</label>
            <input value={formBD.so_tien} onChange={(e) => setFormBD({ ...formBD, so_tien: e.target.value })} /></div>
          <div><label>Chứng từ</label>
            <input value={formBD.chung_tu} onChange={(e) => setFormBD({ ...formBD, chung_tu: e.target.value })} /></div>
        </div>
        <label>Nội dung</label>
        <input value={formBD.noi_dung} onChange={(e) => setFormBD({ ...formBD, noi_dung: e.target.value })} />
        <p>
          <button className="act teal" disabled={dangLuu} onClick={() => luuBaoDuong()}>{dangLuu ? "Đang lưu…" : "Ghi phiếu"}</button>{" "}
          <button className="act grey" onClick={() => setFormBD(null)}>Thôi</button>
        </p>
      </div>}

      <div className="panel wrap">
        <h2>Lịch sử phiếu ({bdLs.length})</h2>
        <table><thead><tr>
          <th>Ngày</th><th>Xe</th><th>Loại</th><th className="num">Km lúc làm</th>
          <th className="num">Mốc kỳ tới</th><th>Nội dung</th><th>Garage</th>
          <th className="num">Số tiền</th><th>Bên chịu</th><th>Chứng từ</th>
        </tr></thead><tbody>
          {bdLs.map((m: any) => <tr key={m.id}>
            <td>{fmtD(m.ngay)}</td><td>{m.xe}</td><td>{m.kind_ten}</td>
            <td className="num">{m.km_luc_lam ? m.km_luc_lam.toLocaleString("vi-VN") : <span className="muted">—</span>}</td>
            <td className="num">{m.km_ky_toi ? m.km_ky_toi.toLocaleString("vi-VN") : <span className="muted">—</span>}</td>
            <td>{m.noi_dung}</td><td>{m.garage}</td>
            <td className="num">{m.so_tien === null || m.so_tien === undefined ? <span className="muted" title="Chưa có số – khác với bằng 0">—</span> : m.so_tien.toLocaleString("vi-VN")}</td>
            <td>{m.ben_chiu_ten}</td>
            <td>{m.chung_tu || <Tag cls="warn">chưa có</Tag>}</td>
          </tr>)}
          {!bdLs.length && <tr><td colSpan={10} className="muted">Chưa có phiếu bảo dưỡng nào được ghi.</td></tr>}
        </tbody></table>
      </div>
    </>}

    {tab === "xe" && <div className="panel wrap"><h2>Hàng đợi xác minh hồ sơ ({xm.filter((x) => x.status !== "xong" && x.status !== "khong_ap_dung").length} còn treo)</h2>
      <p className="muted">Những việc hệ thống không tự quyết được và cần người trả lời. Hệ thống nói ra chỗ nó không chắc, thay vì tự điền cho đủ form.</p>
      <table><thead><tr><th>Đối tượng</th><th>Việc cần xác minh</th><th>Nguồn</th><th>Trạng thái</th><th>Kết luận</th>{canWrite && <th></th>}</tr></thead>
        <tbody>{xm.map((x) => <tr key={x.id} style={{ opacity: x.status === "xong" ? 0.55 : 1 }}>
          <td>{x.ref}</td><td>{x.issue}</td><td className="muted">{x.source}</td>
          <td>{x.status === "xong" ? <Tag cls="ok">{x.status_ten}</Tag> : <Tag cls="warn">{x.status_ten}</Tag>}</td>
          <td className="muted">{x.resolution}{x.resolved_by ? ` — ${x.resolved_by}, ${fmtDT(x.resolved_at)}` : ""}</td>
          {canWrite && <td>{x.status !== "xong" && x.status !== "khong_ap_dung" && <button className="act teal" onClick={() => dongViec(x.id)}>Kết luận</button>}</td>}
        </tr>)}</tbody></table>
    </div>}

    {/* BÁO HƯ HỎNG — hàng đợi của đội xe. Sổ này KHÔNG có cột tiền, và đó là chủ ý: tiền xuất hiện
        ở bước sau, bằng một đề nghị chi loại `sua_chua_xe` do chính đội xe lập khi có báo giá. */}
    {tab === "baohong" && <>
      <div className="panel"><h2>Báo hư hỏng</h2>
        <p className="muted">Tài xế báo xe nào hỏng gì, <b>không kèm tiền</b>. Xe có báo hỏng mức
          <b> Phải dừng xe</b> chưa đóng thì <b>bị chặn</b> khi lập lệnh điều xe; mức
          <b> Còn chạy được</b> chỉ hiện cảnh báo cho người phát lệnh nhìn thấy trước khi ký.</p>
        <div className="kpis">
          <div className="kpi"><div className="k">Đang mở</div><div className="v">{bh?.dem?.dang_mo ?? "—"}</div></div>
          <div className="kpi"><div className="k">Phải dừng xe</div><div className="v">{bh?.dem?.phai_dung_xe ?? "—"}</div></div>
        </div>
        {bh?.ghi_chu && <p className="muted">{bh.ghi_chu}</p>}
      </div>

      <div className="panel wrap"><h2>Sổ báo hỏng</h2>
        <table><thead><tr><th>Xe</th><th>Báo lúc</th><th>Người báo</th><th>Hiện tượng</th><th>Mức độ</th>
          <th className="num">Km</th><th>Trạng thái</th><th>Kết quả</th>{canNhap && <th></th>}</tr></thead>
          <tbody>{(bh?.rows || []).map((x: any) => <tr key={x.id} style={{ opacity: x.trang_thai === "da_dong" ? 0.55 : 1 }}>
            <td className="mono"><b>{x.plate}</b></td><td>{fmtDT(x.bao_luc)}</td><td>{x.nguoi_bao}</td>
            <td>{x.hien_tuong}{x.noi_xay_ra ? <div className="muted">{x.noi_xay_ra}</div> : null}</td>
            <td>{x.muc_do === "phai_dung_xe" ? <Tag cls="red">Phải dừng xe</Tag> : <Tag cls="warn">Còn chạy được</Tag>}</td>
            <td className="num">{x.odo_km ? x.odo_km.toLocaleString("vi-VN") : "—"}</td>
            <td>{x.trang_thai === "da_dong" ? <Tag cls="ok">Đã xử lý xong</Tag>
              : x.trang_thai === "da_tiep_nhan" ? <Tag cls="navy">Đã tiếp nhận</Tag>
              : <Tag cls="warn">Mới báo</Tag>}</td>
            <td className="muted">{x.ket_qua}{x.maintenance_id ? <div className="muted">phiếu sửa chữa #{x.maintenance_id}</div> : null}</td>
            {canNhap && <td style={{ whiteSpace: "nowrap" }}>
              {x.trang_thai === "moi" && <><button className="act grey" style={{ margin: 0 }} onClick={() => tiepNhanHong(x.id)}>Tiếp nhận</button>{" "}</>}
              {x.trang_thai !== "da_dong" && <button className="act teal" style={{ margin: 0 }} onClick={() => dongHong(x.id)}>Đóng</button>}
            </td>}
          </tr>)}</tbody></table>
        {!(bh?.rows || []).length && <p className="muted">Chưa có báo hỏng nào.</p>}
      </div>
    </>}
  </>);
}

export default function Page() { return <Shell><DoiXe /></Shell>; }
