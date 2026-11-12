"use client";
import { Fragment, useEffect, useState, useCallback } from "react";
import DinhKem from "@/components/DinhKem";
import QuyetToanChuyen from "@/components/QuyetToanChuyen";
import BonBuocBaoCaoXe from "@/components/doixe/BonBuocBaoCaoXe";
import BonBuocDeXuatChi from "@/components/doixe/BonBuocDeXuatChi";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, fmtDT, soTien } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import MauDoiXe from "@/components/doixe/MauDoiXe";

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
  /** VH-42: chỉ hiện các tờ quyết toán đang chờ Chủ tịch duyệt, mỗi tờ mở sẵn để duyệt tại chỗ. */
  const [choTgd, setChoTgd] = useState(false);
  const [tab, setTab] = useState<"xe" | "chuyen" | "giaodich" | "quyettoan" | "congno" | "baoduong" | "baohong" | "nhinlai">("xe");
  /* VH-33 (Chủ tịch 12/11/2026): mở trong khung của bàn GĐ đội xe (/xe) thì /xe đã có tiêu đề, ô đếm và thanh
     nghiệp vụ — ở đây giấu phần đầu trang và dãy tab để không lặp nút trên một màn; liên kết sang màn ngoài
     đội xe (tờ quyết toán tour) cũng giấu vì trong khung chúng không mở được. */
  const [nhung, setNhung] = useState(false);
  useEffect(() => { try { setNhung(window.self !== window.top); } catch { setNhung(true); } }, []);
  // DX-2 · 16/10/2026 — báo cáo NHÌN LẠI. Nạp RIÊNG, không nhét vào `load()` chung: nó quét toàn
  // bộ chặng phương tiện và đối chiếu từng ngày với nhật trình xe, nên nặng hơn hẳn các khối kia.
  // Nhét chung thì mở màn hình Hồ sơ xe cũng phải chờ một phép quét không ai hỏi tới.
  const [nl, setNl] = useState<any>(null);
  const [nlKy, setNlKy] = useState("");             // YYYY-MM, rỗng = để máy chủ lấy tháng trước
  const [nlDang, setNlDang] = useState(false);
  const [bh, setBh] = useState<any>(null);          // sổ báo hư hỏng của cả đội
  const [bd, setBd] = useState<any>(null);          // tình trạng bảo dưỡng của cả đội
  const [bdLs, setBdLs] = useState<any[]>([]);      // lịch sử phiếu bảo dưỡng
  const [formBD, setFormBD] = useState<any>(null);  // form ghi phiếu bảo dưỡng
  const [chuyen, setChuyen] = useState<any[]>([]);
  /** VH-37: chuyến đã huỷ không hiện trên nhật trình. */
  const chuyenHien = chuyen.filter((t) => t.status !== "huy");
  /** VH-2: chuyến cần mở sẵn tờ báo cáo (từ `?chuyen=`); mở khi danh sách chuyến đã về. */
  const [moChuyen, setMoChuyen] = useState<number>(0);
  const [moCT, setMoCT] = useState<number>(0);          // VH-31: chuyến đang mở ngăn chi tiết
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
  /** Biểu mẫu cần bật sẵn theo `?mo=` trên địa chỉ. Đọc ở effect đọc địa chỉ, nhưng
   *  CHỈ bật ở effect dưới — lúc ấy mới biết người này có quyền nhập hay không.
   *  Khai TRƯỚC `canNhap` vì effect bật biểu mẫu đứng ngay sau dòng ấy. */
  const [moSan, setMoSan] = useState<"de-xuat-chi" | "phieu-chi-phi" | null>(null);
  const canNhap = ["cntt", "hcns", "tp_dh", "nv_dh", "ketoan", "chutich", "tgd", "gd_doi_xe"].includes(user?.role || "");

  /** Bật biểu mẫu do `?mo=` yêu cầu — một lần, và chỉ khi có quyền nhập. Người không có
   *  quyền vẫn mở được đúng tab để XEM, chỉ không có biểu mẫu; đó là cùng một màn hình họ
   *  vẫn thấy khi tự bấm vào tab, không phải một trang lỗi. */
  useEffect(() => {
    if (!moSan || !canNhap) return;
    if (moSan === "de-xuat-chi") setFormDX({ ngay: new Date().toISOString().slice(0, 10) });
    if (moSan === "phieu-chi-phi") setForm({ ngay_di: "", ngay_ve: "" });
    setMoSan(null);
  }, [moSan, canNhap]);
  const [form, setForm] = useState<any>(null);      // form nhật trình chuyến (thêm / sửa)
  // VH-19 · tài xế để chọn khi sửa phiếu — chỉ nạp khi mở một phiếu, không nạp mỗi lần vào /doi-xe.
  const [taiXe, setTaiXe] = useState<any[]>([]);
  useEffect(() => { if (form?.id && !taiXe.length) api<any>("/fleet/tai-xe-chon").then((r) => setTaiXe(r?.rows || [])).catch(() => {}); }, [form?.id]); // eslint-disable-line react-hooks/exhaustive-deps
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
      // DL-6 · 16/10/2026: ô đếm «chuyến sinh từ lệnh còn thiếu số thật» trên màn hình Lệnh điều
      // xe trỏ sang đây. Không trỏ tới từng chuyến mà tới đúng tab chứa nhật trình: trỏ sâu hơn
      // đòi một mã mở sẵn một dòng, và một đường dẫn hứa nhiều hơn nó làm được thì tệ hơn.
      if (t === "chuyen") setTab("chuyen");
      // VH-42: dòng «tờ quyết toán chuyến xe chờ CHỦ TỊCH duyệt» trên ô Chờ duyệt trỏ `?tab=chuyen&cho=tgd`.
      if (new URLSearchParams(window.location.search).get("cho") === "tgd") setChoTgd(true);
      if (t === "nhin-lai" || t === "nhinlai") setTab("nhinlai");
      // Bốn tab còn lại: trước hôm nay gõ đúng tên tab vẫn rơi về «Hồ sơ xe».
      if (t === "giaodich" || t === "giao-dich") setTab("giaodich");
      if (t === "quyettoan" || t === "quyet-toan") setTab("quyettoan");
      if (t === "congno" || t === "cong-no") setTab("congno");
      if (t === "xe") setTab("xe");
      if (t === "baoduong") setTab("baoduong");
      if (t === "baohong") setTab("baohong");

      // `?mo=` — hai nút nhập chính của màn /xe (v3.3) dẫn sang đây và bật sẵn biểu mẫu.
      // Chỉ bật cho người đã có quyền nhập: địa chỉ không phải một cách xin quyền.
      const mo = new URLSearchParams(window.location.search).get("mo");
      if (mo === "de-xuat-chi") { setTab("giaodich"); setMoSan("de-xuat-chi"); }
      if (mo === "phieu-chi-phi") { setTab("chuyen"); setMoSan("phieu-chi-phi"); }
      // `?chuyen=` — VH-2: mở thẳng tờ báo cáo xe của một chuyến (màn gọn «Báo cáo từng xe», hàng chờ ký).
      const ct = Number(new URLSearchParams(window.location.search).get("chuyen"));
      if (ct > 0) { setTab("chuyen"); setMoChuyen(ct); }
      // `?xe=` — màn gọn «Hồ sơ xe» của /xe (v3.3) mở thẳng hồ sơ một xe.
      const xeId = Number(new URLSearchParams(window.location.search).get("xe"));
      if (xeId > 0) { setTab("xe"); api(`/fleet/xe/${xeId}`).then(setChon).catch(() => {}); }
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
  useEffect(() => {
    if (!moChuyen || !chuyen.length) return;
    const t = chuyen.find((x: any) => x.id === moChuyen);
    if (t) setForm({ id: t.id, vehicle_id: t.vehicle_id, ten_tour: t.ten_tour,
      ngay_di: (t.ngay_di || "").slice(0, 10), ngay_ve: (t.ngay_ve || "").slice(0, 10),
      km_dau: t.km_dau, km_cuoi: t.km_cuoi, km_gps: t.km_gps, km_nguon: t.km_nguon,
      doanh_thu: t.doanh_thu, note: t.note });
    setMoChuyen(0);
  }, [moChuyen, chuyen]);
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

  /** SỬA một phiếu đã có. KS-64 · 09/11/2026 — hàm này KHÔNG còn đường tạo phiếu mới:
   *  nhập mới đi qua cửa bốn bước `BonBuocBaoCaoXe` (bản v3.3). Để lại cả hai đường tạo là để
   *  ngày nào đó một bên thêm ô kiểm tra mà bên kia không, rồi cùng một phiếu lại hợp lệ hay
   *  không tuỳ người nhập bấm vào nút nào. */
  const luuChuyen = async () => {
    if (!form?.id) return;
    if (!form.ngay_di || !form.ngay_ve) return toast("Nhập ngày đi và ngày về", true);
    setDangLuu(true);
    try {
      await api(`/fleet/chuyen/${form.id}`, { method: "PUT", json: {
        ten_tour: form.ten_tour, ngay_di: form.ngay_di, ngay_ve: form.ngay_ve,
        km_dau: form.km_dau, km_cuoi: form.km_cuoi, km_gps: form.km_gps,
        km_nguon: form.km_nguon || "", doanh_thu: form.doanh_thu, note: form.note,
        ...(form.driver_id ? { driver_id: Number(form.driver_id) } : {}) } });
      toast("Đã cập nhật phiếu chuyến");
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
    {!nhung && <>
    <h1>Đội xe Vietrip – hồ sơ và điều kiện khai thác</h1>

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
    {tq.thieu_trong_o_dem > 0 && <p className="cb-do">Có <b>{tq.thieu_trong_o_dem}</b> xe không nằm
      trong ô đếm nào ở trên — nghĩa là máy chủ xếp chúng vào một mức mà dãy ô này chưa in. Đừng đọc
      các con số trên như đã đủ; báo CNTT.</p>}
    {/* VH-31 (Chủ tịch 12/11/2026): bỏ câu chế độ chặn khi TẮT; khi BẬT thì vẫn nói vì nó đổi việc người điều xe được làm. */}
    {tq.chan_khi_thieu_giay && <p className="cb-vang">Đang BẬT chế độ chặn khi thiếu giấy tờ.</p>}

    <div className="dx-tabs">
      {([["xe", "Hồ sơ xe"], ["chuyen", `Nhật trình chuyến (${chuyenHien.length})`], ["giaodich", `Đối soát nguồn ngoài (${gd?.rows?.length || 0})`], ["quyettoan", `Chủ xe & quyết toán (${chuXe.length})`], ["congno", "Công nợ đội xe"], ["baoduong", bd ? `Bảo dưỡng (${(bd.theo_muc?.BLOCK || 0) + (bd.theo_muc?.REVIEW || 0)} cần xếp lịch)` : "Bảo dưỡng"], ["baohong", bh ? `Báo hỏng (${bh.dem?.dang_mo || 0} đang mở)` : "Báo hỏng"],
        ["nhinlai", "Nhìn lại"]] as const)
        .map(([k, ten]) => <button key={k} className={`act ${tab === k ? "teal" : "grey"}`} onClick={() => setTab(k as any)}>{ten}</button>)}
    </div>
    {/* LỐI VÀO HAI SỔ CON (17/10/2026). Hai màn ghi phạt tài xế và giá dầu là TRANG CON của /doi-xe,
        cố ý không có mục menu riêng — nên lối vào DUY NHẤT của chúng là hàng nút này. Vòng DX-5 lên
        hệ thật mà thiếu hàng này: cửa có, màn có, nhưng không ai tới được trừ khi gõ tay địa chỉ.
        Mở tab mới để không mất chỗ đang xem ở màn đội xe. */}
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "0 0 10px" }}>
      <span className="muted" style={{ alignSelf: "center" }}>Sổ con:</span>
      <a className="act grey" style={{ margin: 0 }} href="/doi-xe/phat-tai-xe" target="_blank" rel="noopener">Phạt tài xế ↗</a>
      <a className="act grey" style={{ margin: 0 }} href="/doi-xe/gia-dau" target="_blank" rel="noopener">Giá dầu & định mức ↗</a>
      <a className="act grey" style={{ margin: 0 }} href="/doi-xe/xe-hom-nay" target="_blank" rel="noopener">Xe hôm nay theo sheet ↗</a>
    </div>
    </>}

    {tab === "chuyen" && <>
      {form?.id && <DinhKem doiTuong="chuyen_xe" doiTuongId={form.id}
        tieuDe={`Chứng từ của phiếu chuyến #${form.id}`}
        goi={"Ảnh hóa đơn dầu, vé cầu đường, phiếu gửi xe, ảnh đồng hồ km. Chứng từ nằm cùng phiếu thì " +
             "đến kỳ quyết toán không phải đi tìm, và người duyệt nhìn thấy đúng thứ họ đang duyệt."} />}
      {/* QT-1 · tờ quyết toán Mẫu 2 đặt NGAY SAU khối đính kèm và NGAY TRÊN biểu phiếu chuyến: người
          nhập cầm tờ giấy trong tay, đính ảnh rồi khai luôn ai trả, không phải đi tìm sang tab khác.
          Chỉ hiện với phiếu ĐÃ CÓ số: chưa lưu phiếu thì chưa có gì để quyết toán. */}
      {form?.id && <QuyetToanChuyen tripId={form.id} toast={toast} />}
      {/* KS-64 · NHẬP MỚI đi qua cửa bốn bước của bản v3.3. SỬA một phiếu đã có thì vẫn là
          bảng một trang ngay dưới: sửa là xem lại đúng vài ô, bắt đi lại bốn bước cho một lần
          đổi tên tour là một cách phạt vô cớ. */}
      {form && !form.id && <BonBuocBaoCaoXe xe={xe} kmNguon={(dm2?.km_nguon || {}) as Record<string, string>}
        toast={toast} onXong={load} onDong={() => setForm(null)} />}
      {form?.id && <div className="panel">
        <h2>{`Sửa phiếu chuyến #${form.id}`}</h2>
        <p className="muted">Đúng bộ trường của phiếu trên Vietrip. Ô để trống nghĩa là <b>chưa có số</b>, không phải bằng 0 –
          hệ thống không tự điền 0 và không tính ra quãng đường âm.</p>
        <div className="grid2">
          <label>Xe
            <select value={form.vehicle_id || ""} onChange={(e) => setForm({ ...form, vehicle_id: Number(e.target.value) })} disabled={!!form.id}>
              <option value="">— chọn xe —</option>
              {xe.map((v: any) => <option key={v.id} value={v.id}>{v.plate}{v.code ? ` · ${v.code}` : ""}</option>)}
            </select></label>
          <label>Tài xế
            {/* VH-19: phiếu nhập không qua lệnh trước đây không ghi được tài xế — sửa bổ sung ở đây. */}
            <select value={form.driver_id || ""} onChange={(e) => setForm({ ...form, driver_id: e.target.value })}>
              <option value="">— chưa ghi tài xế —</option>
              {taiXe.map((x: any) => <option key={x.id} value={x.id}>{x.ho_ten}{x.code ? ` · ${x.code}` : ""}</option>)}
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
        {/* KS-64: sáu ô chi phí từng ở đây đã BỎ. Bảng này chỉ còn dùng để SỬA phiếu đã có, và
            sửa chi phí của phiếu đã có KHÔNG đi qua `POST /chuyen/{id}/chi-phi` được — cửa ấy
            THÊM một dòng mới. Đúng hai lỗi nhân đôi chi phí (19/10 thừa 105.984.428 đ; 02/11
            thừa 26 dòng trên 7 chuyến) đều sinh ra từ việc thêm dòng vào phiếu đã có dòng.
            Chi phí của phiếu đã có sửa ở khối quyết toán phía trên. */}
        <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
          <button className="act teal" disabled={dangLuu} onClick={luuChuyen}>{dangLuu ? "Đang lưu…" : "Lưu phiếu"}</button>
          <button className="act grey" onClick={() => setForm(null)}>Đóng</button>
        </div>
      </div>}

      {choTgd && <div className="panel wrap"><h2>Tờ quyết toán chuyến xe chờ Chủ tịch duyệt</h2>
        {chuyen.filter((t) => t.qt_trang_thai === "cho_tgd").length === 0
          ? <p className="muted">Không còn tờ nào chờ duyệt.</p>
          : chuyen.filter((t) => t.qt_trang_thai === "cho_tgd").map((t) => <div key={t.id} style={{ marginBottom: 14 }}>
              <p style={{ margin: "0 0 6px" }}><b>{t.ma_tour || t.ma_phieu || `#${t.id}`}</b> · {t.xe} · {t.ten_tour || "—"} · {String(fmtD(t.ngay_di)).slice(0, 5)} → {String(fmtD(t.ngay_ve)).slice(0, 5)}</p>
              <QuyetToanChuyen tripId={t.id} toast={toast} />
            </div>)}
      </div>}
      {!choTgd && <div className="panel wrap"><h2>Nhật trình chuyến</h2>
      {canNhap && !form && <div style={{ marginBottom: 10, display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button className="act teal" onClick={() => setForm({ ngay_di: "", ngay_ve: "" })}>+ Nhập phiếu chi phí xe</button>
        {/* Cờ được tính lúc GHI rồi lưu vào dòng. Đo trên hệ thật 07/10/2026: cả 24 chuyến in rõ
            "chưa có số GPS" ở cột km mà cột Cờ vẫn XANH, vì cờ lưu sẵn từ lần nạp trước — màn hình
            và cờ nói hai điều khác nhau về cùng một chuyến. Cửa này chỉ tính lại cờ và lý do cờ:
            không đổi trạng thái, không đổi km, không đổi tiền. */}
        <button className="act grey" onClick={tinhLaiCo}>Tính lại cờ chuyến</button>
      </div>}
      {/* VH-38 (Chủ tịch dặn 12/11/2026 08:36): thu hẹp Ghi chú, mở rộng các cột bị chồng / thiếu chữ, bảng vừa khung không kéo ngang.
          VH-37 (Chủ tịch duyệt bản xem trước 12/11/2026 08:06): đầu bảng navy sáng, kẻ ngang dọc; Mã tour (nối từ tour
          Kinh doanh / lệnh Điều hành) thay Phiếu; Chi phí và Lãi cạnh Doanh thu; Cờ → Ghi chú (cột rộng nhất); cột cuối là
          nút trạng thái 4 màu — bấm nút hay dòng đều mở chi tiết, Sửa / Mở lại để sửa nằm TRONG chi tiết (một nút một
          chỗ). Chuyến đã huỷ không hiện. */}
      <div className="nt-bang"><table><colgroup><col style={{ width: 30 }} /><col style={{ width: 92 }} /><col style={{ width: 150 }} />
        <col style={{ width: 88 }} /><col style={{ width: 116 }} /><col style={{ width: 76 }} /><col style={{ width: 96 }} />
        <col style={{ width: 96 }} /><col style={{ width: 96 }} /><col /><col style={{ width: 76 }} /></colgroup>
        <thead><tr><th aria-hidden="true"></th><th>Mã tour</th><th>Tên tour</th><th>Xe</th><th>Đi → về</th>
        <th className="num">Km chạy</th><th className="num">Doanh thu</th><th className="num">Chi phí</th><th className="num">Lãi</th>
        <th>Ghi chú</th><th title="Trạng thái">T.thái</th></tr></thead>
        <tbody>{chuyenHien.length ? chuyenHien.map((t) => {
          const ly = (t.co_ly_do || "").split(" · ").map((x: string) => x.trim()).filter(Boolean);
          const mo = moCT === t.id;
          const bat = () => setMoCT(mo ? 0 : t.id);
          const tt = NT_TT(t);
          const lai = t.doanh_thu ? Number(t.doanh_thu) - Number(t.tong_chi || 0) : null;
          return <Fragment key={t.id}>
          <tr className={"nt-dong" + (mo ? " mo" : "")} tabIndex={0} aria-expanded={mo} onClick={bat}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); bat(); } }}>
          <td><span className="nt-mui" aria-hidden="true">›</span></td>
          <td title={t.ma_tour || "Chuyến chưa nối tour"}>{t.ma_tour ? <b>{t.ma_tour}</b> : <i className="muted">chưa nối</i>}</td>
          <td className="nt-hai" title={t.ten_tour || undefined}>{t.ten_tour ? <span>{t.ten_tour}</span> : <span className="muted">—</span>}</td>
          <td>{t.xe}</td>
          <td title={`${fmtD(t.ngay_di)} → ${fmtD(t.ngay_ve)} · ${t.so_ngay} ngày`}>{String(fmtD(t.ngay_di)).slice(0, 5)} → {String(fmtD(t.ngay_ve)).slice(0, 5)}</td>
          <td className="num">{t.km_chay === null ? <span className="muted">chưa đo</span> : t.km_chay.toLocaleString("vi-VN")}</td>
          <td className="num">{t.doanh_thu ? Number(t.doanh_thu).toLocaleString("vi-VN") : <span className="muted">—</span>}</td>
          <td className="num">{Number(t.tong_chi || 0).toLocaleString("vi-VN")}</td>
          <td className={"num nt-lai" + (lai !== null && lai < 0 ? " lo" : "")}>{lai === null ? <span className="muted">—</span> : lai.toLocaleString("vi-VN")}</td>
          <td className="nt-gc nt-hai" title={t.co_ly_do || undefined}><span>{ly[0] || ""}{ly.length > 1 ? ` · +${ly.length - 1}` : ""}</span></td>
          <td><button type="button" className={"nt-tt " + tt[0]} title={tt[2]}>{tt[1]}</button></td>
          </tr>
          {mo && <tr className="nt-ct"><td colSpan={11}><dl>
            <div className="dai"><dt>Ghi chú</dt><dd>{ly.length ? <ul>{ly.map((x: string, i: number) => <li key={i}>{x}</li>)}</ul> : "—"}</dd></div>
            <div><dt>Phiếu</dt><dd>{t.ma_phieu || `#${t.id}`}</dd></div>
            <div><dt>Thời gian</dt><dd>{fmtD(t.ngay_di)} → {fmtD(t.ngay_ve)} ({t.so_ngay} ngày)</dd></div>
            <div><dt>Tài xế</dt><dd>{t.tai_xe || "—"}</dd></div>
            <div><dt>Chủ xe chịu (trong chi phí)</dt><dd>{t.tong_chi_chu_xe.toLocaleString("vi-VN")} đ</dd></div>
            <div><dt>Km</dt><dd>{t.km_dau ?? "—"} → {t.km_cuoi ?? "—"}{t.km_nguon_ten ? ` · ${t.km_nguon_ten}` : ""}</dd></div>
            <div><dt>GPS</dt><dd>{t.km_gps ? `${t.km_gps.toLocaleString("vi-VN")} km${t.km_lech_gps != null ? ` · lệch ${t.km_lech_gps.toLocaleString("vi-VN")}` : ""}` : "chưa có số GPS"}</dd></div>
            {t.qt_ten_trang_thai && <div><dt>Báo cáo xe</dt><dd>{t.qt_ten_trang_thai}</dd></div>}
            {t.note && <div className="dai"><dt>Ghi chú nhập tay</dt><dd>{t.note}</dd></div>}
          </dl>
          {canNhap && <div className="nt-nut">{t.status === "da_xac_nhan"
            ? <button className="act grey" onClick={() => moLai(t.id)}>Mở lại để sửa</button>
            : <button className="act grey" onClick={() => setForm({
                id: t.id, vehicle_id: t.vehicle_id, ten_tour: t.ten_tour,
                ngay_di: (t.ngay_di || "").slice(0, 10), ngay_ve: (t.ngay_ve || "").slice(0, 10),
                km_dau: t.km_dau, km_cuoi: t.km_cuoi, km_gps: t.km_gps, km_nguon: t.km_nguon,
                doanh_thu: t.doanh_thu, note: t.note })}>Sửa</button>}</div>}
          </td></tr>}
          </Fragment>;
        }) : <tr><td colSpan={11} className="muted">Chưa có chuyến nào được ghi nhật trình.</td></tr>}</tbody></table></div>
      <style>{NT_CSS}</style>
      </div>}
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

    {tab === "giaodich" && formDX && <BonBuocDeXuatChi xe={xe} vai={user?.role || ""}
      nguongChungTu={dm3?.nguong_chung_tu ?? null}
      toast={toast} onXong={load} onDong={() => setFormDX(null)} />}

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
      <DonGiaNgay key={"dg-" + chon.id} xe={chon} ghi={["cntt", "hcns", "tp_dh", "nv_dh", "gd_doi_xe"].includes(user?.role || "")} xong={() => mo(chon.id)} />
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
      {/* XE-1 (14/10/2026) · XOÁ MỘT DÒNG XE TẠO NHẦM.
          Danh mục dựng trên nguyên tắc "mã xe theo chiếc xe suốt vòng đời": xe bán đi thì ghi vòng
          đời và ngày rời đội, KHÔNG xoá. Nguyên tắc ấy đúng, nhưng không phủ một dòng TẠO NHẦM —
          chưa từng là xe thật, nên không bán được, không ngừng khai thác được, và cứ nằm lại trong
          mẫu số của mọi phép tính đội hình.
          Hai bước chứ không một: BẤM SOÁT trước, máy nói chiếc này vướng gì; nút xoá chỉ hiện khi
          máy đã trả lời là xoá được. Không dùng hộp thoại xác nhận của trình duyệt — một hộp thoại
          bấm quen tay thì không còn là một lần cân nhắc. */}
      {/* `key` theo id xe là BẮT BUỘC, không phải cho gọn: đo 14/10/2026 trên bản chạy thật —
          soát xe A rồi bấm sang xe B thì khối vẫn in câu trả lời của xe A, vì React giữ
          nguyên trạng thái khi chỉ đổi prop. Một người đọc nhanh sẽ tin câu của xe A là của
          xe B, và đây là khối quyết định có xoá hẳn một dòng hay không. */}
      <XoaXe key={chon.id} xe={chon} xong={() => { setChon(null); load(); }} />
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

    {/* ── HQ-2c · ĐỊNH MỨC TIÊU HAO DẦU ──────────────────────────────────────────────────────
        Chủ tịch quyết 13/10/2026: ngưỡng do ĐỘI XE khai, không để máy tự đoán. Lý do nằm ngay
        trong phương án bị loại — lấy trung bình 6 tháng của chính chiếc xe làm mốc nghe thì gọn,
        nhưng một chiếc hao nhiều SUỐT sáu tháng thì máy coi đó là bình thường, và chiếc hao nhất
        đội thành chiếc không bao giờ bị cảnh báo.

        Khai theo SỐ CHỖ chứ không theo từng xe: số chỗ là thuộc tính đã có trong danh mục và chính
        nó quyết định mức hao. Khai theo từng xe thì mỗi lần mua xe mới lại thêm một ô trống nữa. */}
    {tab === "xe" && <DinhMucDau />}

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
    {/* ═══════════ DX-2 · NHÌN LẠI: đã trả tiền thuê xe ngoài trong khi xe nhà đậu ═══════════
        Gợi ý điều xe nhìn VỀ TRƯỚC — giúp người sắp lập lệnh chọn xe rảnh. Khối này nhìn LẠI, và
        trả lời câu khác: tháng vừa rồi đã trả bao nhiêu ra ngoài một cách không cần thiết. Đó là
        câu làm người ta đổi cách làm; con số đã bắt được là 51.348.800 đ nhóm A tháng 9/2026.

        BA NHÓM, KHÔNG MỘT CON SỐ — gộp lại thành «đã phí bao nhiêu» là cách chắc chắn để không ai
        tin bảng này sau lần thứ hai. Và KHÔNG có nút «gắn xe vào chặng» ở đây: báo cáo nêu chỗ
        nghi, người có sổ mới biết chặng ấy thật sự chạy bằng xe nào — đúng lẽ Chủ tịch chốt 18/9
        với sổ chuyến còn nợ: danh sách và đường dẫn, không sửa hàng loạt từ màn hình tổng. */}
    {tab === "nhinlai" && <div className="panel wrap"><h2>Nhìn lại — thuê xe ngoài trong khi xe nhà đậu</h2>
      <p className="muted">Khối này đối chiếu từng chặng ô tô thuê ngoài với nhật trình xe nhà cùng
        ngày. Xe nhà «rảnh» đọc <b>nhật trình chuyến</b>, không đọc lệnh điều xe — hệ thống đang có
        rất ít lệnh trong khi nhật trình đầy, nên đếm theo lệnh thì mọi xe trông như rảnh suốt.</p>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", margin: "8px 0" }}>
        <label style={{ margin: 0 }}>Kỳ
          <input type="month" value={nlKy} onChange={(e) => setNlKy(e.target.value)} /></label>
        <button className="act teal" disabled={nlDang} onClick={async () => {
          setNlDang(true);
          try {
            const q = nlKy ? `?nam=${nlKy.slice(0, 4)}&thang=${Number(nlKy.slice(5, 7))}` : "";
            setNl(await api(`/fleet/doi-chieu-xe-ngoai${q}`));
          } catch (e) { toast(errMsg(e), true); } finally { setNlDang(false); }
        }}>Soát lại</button>
        <span className="muted">Để trống thì máy lấy <b>tháng trước</b> — báo cáo nhìn lại mà mặc
          định tháng này thì nửa tháng đầu luôn gần rỗng.</span>
      </div>

      {!nl ? <p className="muted">Bấm <b>Soát lại</b> để chạy đối chiếu.</p> : <>
        <p className="muted">Kỳ {fmtD(nl.tu)} → {fmtD(nl.den)}</p>
        <div className="kpis">
          <div className="kpi"><b>{(nl.a_dang_le_khong_can_thue?.tien || 0).toLocaleString("vi-VN")}</b>
            <span>A · đáng lẽ không cần thuê · {nl.a_dang_le_khong_can_thue?.so_chang || 0} chặng</span></div>
          <div className="kpi"><b>{nl.b_nghi_khai_nham?.so_chang || 0}</b><span>B · nghi khai nhầm là thuê ngoài</span></div>
          <div className="kpi"><b>{nl.c_khong_doi_chieu_duoc?.so_chang || 0}</b><span>C · chặng không có ngày</span></div>
        </div>

        <h3>A · Đáng lẽ không cần thuê</h3>
        <p className="muted">{nl.a_dang_le_khong_can_thue?.ghi_chu}</p>
        {nl.a_dang_le_khong_can_thue?.so_chang_chua_co_tien > 0 && <p className="muted">
          <Tag cls="warn">lưu ý</Tag> {nl.a_dang_le_khong_can_thue.so_chang_chua_co_tien} chặng
          chưa có thành tiền nên không nằm trong con số trên.</p>}
        <table><thead><tr><th>Ngày</th><th>Chuyến · chặng</th><th>Nhà xe</th>
          <th className="num">Tiền</th><th>Xe nhà rảnh hôm ấy</th><th></th></tr></thead>
          <tbody>{(nl.a_dang_le_khong_can_thue?.danh_sach || []).map((c: any) => <tr key={c.chang_id}>
            <td>{fmtD(c.ngay)}</td>
            <td><b>{c.ma_tour}</b><div className="muted">{c.chang} · {c.so_cho_can || "?"} chỗ</div></td>
            <td>{c.nha_cung_cap}</td>
            <td className="num">{c.thanh_tien === null ? <span className="muted">chưa có</span>
              : c.thanh_tien.toLocaleString("vi-VN")}</td>
            <td>{c.xe_nha_ranh.map((v: any) => <Tag key={v.id} cls="ok">{v.ma} · {v.bien} · {v.ghe} chỗ</Tag>)}
              {c.so_xe_ranh > c.xe_nha_ranh.length && <span className="muted"> và {c.so_xe_ranh - c.xe_nha_ranh.length} xe nữa</span>}</td>
            <td>{!nhung && <a className="act grey" style={{ margin: 0 }} href={`/tours/${c.tour_id}`}>Mở tờ quyết toán</a>}</td>
          </tr>)}{!(nl.a_dang_le_khong_can_thue?.danh_sach || []).length
            && <tr><td colSpan={6} className="muted">Kỳ này không có chặng nào đáng lẽ không cần thuê.</td></tr>}</tbody></table>

        <h3>B · Nghi khai nhầm là thuê ngoài</h3>
        <p className="muted">{nl.b_nghi_khai_nham?.ghi_chu}</p>
        <table><thead><tr><th>Chuyến · chặng</th><th>Biển trên chặng</th><th>Trùng xe</th>
          <th className="num">Tiền</th><th></th></tr></thead>
          <tbody>{(nl.b_nghi_khai_nham?.danh_sach || []).map((c: any) => <tr key={c.chang_id}>
            <td><b>{c.ma_tour}</b><div className="muted">{c.chang}</div></td>
            <td>{c.so_hieu}</td>
            <td><Tag cls="warn">{c.ma_xe} · {c.xe_trong_danh_muc}</Tag></td>
            <td className="num">{c.thanh_tien === null ? <span className="muted">chưa có</span>
              : c.thanh_tien.toLocaleString("vi-VN")}</td>
            {/* Cửa sửa nằm trên TỜ QUYẾT TOÁN (mục Phương tiện, nút «Gắn tay»), không ở đây: người
                giữ màn đội xe không có quyền ghi tờ quyết toán. Mở thẳng đúng tab. */}
            <td>{!nhung && <a className="act grey" style={{ margin: 0 }} href={`/tours/${c.tour_id}?tab=lop3`}>Mở tờ quyết toán để gắn ↗</a>}</td>
          </tr>)}{!(nl.b_nghi_khai_nham?.danh_sach || []).length
            && <tr><td colSpan={5} className="muted">Không có chặng nào nghi khai nhầm.</td></tr>}</tbody></table>

        <h3>C · Không đối chiếu được</h3>
        <p className="muted">{nl.c_khong_doi_chieu_duoc?.ghi_chu}</p>
        <table><thead><tr><th>Chuyến · chặng</th><th>Nhà xe</th><th className="num">Tiền</th><th></th></tr></thead>
          <tbody>{(nl.c_khong_doi_chieu_duoc?.danh_sach || []).map((c: any) => <tr key={c.chang_id}>
            <td><b>{c.ma_tour}</b><div className="muted">{c.chang}</div></td>
            <td>{c.nha_cung_cap}</td>
            <td className="num">{c.thanh_tien === null ? <span className="muted">chưa có</span>
              : c.thanh_tien.toLocaleString("vi-VN")}</td>
            <td>{!nhung && <a className="act grey" style={{ margin: 0 }} href={`/tours/${c.tour_id}`}>Mở tờ quyết toán</a>}</td>
          </tr>)}{!(nl.c_khong_doi_chieu_duoc?.danh_sach || []).length
            && <tr><td colSpan={4} className="muted">Mọi chặng thuê ngoài đều đã có ngày.</td></tr>}</tbody></table>
      </>}
    </div>}

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

export default function Page() { return <Shell><MauDoiXe><DoiXe /></MauDoiXe></Shell>; }

/* TK-1d (Chủ tịch 04/11/2026) · ĐƠN GIÁ NGÀY XE NHÀ. Tạm tính tour đoàn khách tự thiết kế lấy giá xe theo tuyến trước;
   hành trình không trùng tuyến nào thì lấy đơn giá ngày của xe nhà nhỏ nhất đủ chỗ × số ngày. Đội xe nhập ở đây. */
function DonGiaNgay({ xe, ghi, xong }: { xe: any; ghi: boolean; xong: () => void }) {
  const { toast } = useShell();
  const [v, setV] = useState<string>(xe.internal_rate_per_day != null ? String(Math.round(xe.internal_rate_per_day)) : "");
  const [dang, setDang] = useState(false);
  const luu = async () => {
    setDang(true);
    try {
      const r: any = await api(`/fleet/xe/${xe.id}`, { method: "PUT", json: { phien_ban: xe.phien_ban, internal_rate_per_day: v === "" ? null : Number(v) } });
      toast(r.message || "Đã lưu"); xong();
    } catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  };
  return <p style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
    <b>Đơn giá ngày (xe nhà):</b>
    {ghi ? <><input inputMode="numeric" style={{ width: 160 }} value={v} placeholder="đ / ngày" onChange={(e) => setV(e.target.value.replace(/\D/g, ""))} />
      <button className="act teal" disabled={dang} onClick={luu}>Lưu</button></>
      : <span>{xe.internal_rate_per_day != null ? `${Math.round(xe.internal_rate_per_day).toLocaleString("vi-VN")} đ/ngày` : "chưa nhập"}</span>}
    <span className="muted" style={{ fontSize: 13 }}>Dùng cho tạm tính tour đoàn khi hành trình không trùng tuyến trong bảng giá xe.</span></p>;
}

/* ════════════════════════════════════════════════════════════════════════════════════════════
   HQ-2c · ĐỊNH MỨC TIÊU HAO DẦU — cửa nhập của Đội xe.

   Khối «Hiệu quả đội xe» trên màn hình Chủ tịch in con số L/100km ngay từ khi có số lít và số km.
   Nhưng một con số trần trụi không nói được điều gì: 18 L/100km là cao hay thấp còn tuỳ xe 45 chỗ
   hay 16 chỗ. Ngưỡng là thứ biến con số thành một lời cảnh báo, và ngưỡng ấy KHÔNG suy ra được từ
   chính số liệu nó canh.

   Ô để trống nghĩa là CHƯA KHAI, không phải bằng 0 — khối Chủ tịch vẫn in con số thật, chỉ không
   bật cảnh báo, và nói rõ đang chờ Đội xe.
   ════════════════════════════════════════════════════════════════════════════════════════════ */
function DinhMucDau() {
  const { user, toast } = useShell();
  const [d, setD] = useState<any>(null);
  const [sua, setSua] = useState<Record<number, string>>({});
  const [dang, setDang] = useState(false);
  const ghi = ["cntt", "gd_doi_xe", "tp_dh"].includes(user?.role || "");

  const tai = useCallback(async () => {
    try { setD(await api("/fleet/dinh-muc-dau")); } catch (e) { toast(errMsg(e), true); }
  }, [toast]);
  useEffect(() => { tai(); }, [tai]);

  const luu = async (seats: number) => {
    setDang(true);
    try {
      const v = soTien(sua[seats]);
      const r: any = await api("/fleet/dinh-muc-dau", { method: "PUT", json: { seats, l_100km: v } });
      toast(r.message); await tai();
      setSua((x) => { const y = { ...x }; delete y[seats]; return y; });
    } catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  };

  if (!d) return null;
  const chua = d.rows.filter((r: any) => r.l_100km == null).length;
  return (
    <div className="panel">
      <h2>Định mức tiêu hao dầu <span className="muted">(L/100km theo số chỗ)</span></h2>
      <p className="muted">Khối <b>Hiệu quả đội xe</b> của Chủ tịch in con số tiêu hao thật ngay từ
        bây giờ, nhưng chưa biết cao hay thấp cho tới khi có định mức ở đây. Ô để trống nghĩa là
        <b> chưa khai</b>, không phải bằng 0 — khai xong thì cảnh báo <b>xe vượt định mức</b> tự bật.</p>
      {chua > 0 && <div className="gate">Còn <b>{chua}</b> loại xe chưa có định mức.</div>}
      <div className="wrap"><table>
        <thead><tr><th>Số chỗ</th><th className="num">Số xe đang có</th>
          <th>Định mức (L/100km)</th><th>Ghi chú</th><th>Ai khai · lúc nào</th><th></th></tr></thead>
        <tbody>{d.rows.map((r: any) => (
          <tr key={r.seats}>
            <td><b>{r.seats} chỗ</b></td>
            <td className="num">{d.so_xe_theo_cho?.[r.seats] ?? 0}</td>
            <td style={{ minWidth: 140 }}>
              {ghi ? <input type="number" step="0.1" disabled={dang}
                placeholder="chưa khai"
                value={sua[r.seats] ?? (r.l_100km ?? "")}
                onChange={(e) => setSua({ ...sua, [r.seats]: e.target.value })} />
                : (r.l_100km ?? <Tag cls="warn">chưa khai</Tag>)}
            </td>
            <td className="muted">{r.ghi_chu}</td>
            <td className="muted">{r.boi ? `${r.boi} · ${fmtDT(r.luc)}` : "—"}</td>
            <td>{ghi && sua[r.seats] !== undefined &&
              <button className="act teal" style={{ margin: 0 }} disabled={dang}
                onClick={() => luu(r.seats)}>Lưu</button>}</td>
          </tr>))}</tbody>
      </table></div>
      {!ghi && <p className="muted">Anh/chị chỉ xem được — {d.bo_phan} khai ô này.</p>}
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════════════════════════════
   XE-1 · XOÁ MỘT DÒNG XE TẠO NHẦM — và chỉ dòng tạo nhầm.

   Chỉ CNTT thấy nút xoá. Không phải vì Đội xe kém tin cậy hơn, mà vì đây là thao tác DUY NHẤT
   trong phân hệ xe làm mất hẳn một dòng — mọi thao tác khác chỉ đổi trạng thái. Để một vai dùng
   hằng ngày giữ nút ấy là sớm muộn có người bấm nhầm thay vì ghi "ngừng khai thác".

   Nhưng cửa SOÁT thì ai đọc được hồ sơ xe cũng gọi được: Đội xe tự thấy chiếc nào xoá được, chiếc
   nào vướng gì, không phải hỏi CNTT rồi ngồi chờ.
   ════════════════════════════════════════════════════════════════════════════════════════════ */
function XoaXe({ xe, xong }: { xe: any; xong: () => void }) {
  const { user, toast } = useShell();
  const [s, setS] = useState<any>(null);
  const [ly, setLy] = useState("");
  const [dang, setDang] = useState(false);
  // PHẢI khớp với XOA_XE trong backend/app/api/v1/fleet.py — lệch nhau thì hoặc nút hiện rồi
  // bấm vào báo 403, hoặc có vai bấm được mà màn hình không cho thấy nút. Có phép thử canh.
  const XOA_XE_VAI = ["cntt", "chutich"];
  const xoaDuocQuyen = XOA_XE_VAI.includes(user?.role || "");

  const soat = async () => {
    setDang(true);
    try { setS(await api(`/fleet/xe/${xe.id}/xoa-duoc`)); }
    catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  };
  const xoa = async () => {
    setDang(true);
    try {
      const r: any = await api(`/fleet/xe/${xe.id}?ly_do=${encodeURIComponent(ly)}`, { method: "DELETE" });
      toast(r.message); xong();
    } catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  };

  return (
    <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--line)" }}>
      {!s
        ? <><button className="act grey" style={{ margin: 0 }} disabled={dang} onClick={soat}>
            Xe này có xoá được không?</button>{" "}
          <span className="muted">Xe đã có lịch sử thì <b>ghi ngừng khai thác</b>, không xoá.</span></>
        : <>
          <div className={"gate " + (s.xoa_duoc ? "pass" : "fail")}>{s.noi}</div>
          {s.vuong?.length > 0 && <table><thead><tr><th>Đang vướng</th><th className="num">Số dòng</th></tr></thead>
            <tbody>{s.vuong.map((x: any) => <tr key={x.bang}>
              <td>{x.ten} <span className="muted">({x.bang})</span></td>
              <td className="num">{x.so_dong}</td></tr>)}</tbody></table>}
          {s.xoa_duoc && s.se_xoa_theo?.length > 0 && <p className="muted">
            Xoá cùng: {s.se_xoa_theo.map((x: any) => `${x.so_dong} ${x.ten}`).join(" · ")}.</p>}
          {s.xoa_duoc && (xoaDuocQuyen
            ? <>
              <label>Lý do xoá <span className="muted">(bắt buộc — tháng sau còn trả lời được
                vì sao dòng này biến mất)</span>
                <input value={ly} onChange={(e) => setLy(e.target.value)}
                  placeholder="ví dụ: dòng dữ liệu mẫu, chưa từng là xe thật" /></label>
              <button className="act orange" style={{ margin: "8px 0 0" }}
                disabled={dang || !ly.trim()} onClick={xoa}>Xoá xe {xe.plate} khỏi danh mục</button>
            </>
            : <p className="muted">Xoá được, nhưng chỉ <b>CNTT</b> hoặc <b>Chủ tịch</b> bấm được nút xoá.</p>)}
          <p><button className="act grey" style={{ margin: "8px 0 0" }}
            onClick={() => { setS(null); setLy(""); }}>Thôi</button></p>
        </>}
    </div>
  );
}

/* VH-31 · nhật trình chuyến: một dòng ngang mỗi chuyến, bấm dòng mở chi tiết. */
/** VH-37: trạng thái nhật trình — Xám: đã xác nhận (khoá); còn lại theo cờ: Đỏ thiếu số bắt buộc, Vàng cần kiểm, Xanh đủ & khớp. */
const NT_TT = (t: any): [string, string, string] => t.status === "da_xac_nhan" ? ["xam", "Xám", "Đã xác nhận — khoá sổ"]
  : t.co === "do" ? ["do", "Đỏ", "Thiếu số liệu bắt buộc"] : t.co === "xanh" ? ["xanh", "Xanh", "Đủ và khớp — chờ xác nhận"]
  : ["vang", "Vàng", "Đủ số nhưng cần kiểm"];

const NT_CSS = `
.nt-bang{overflow-x:auto;border:1px solid var(--nt-ke);border-radius:10px;--nt-ke:#b9c6d8}
[data-theme="dark"] .nt-bang{--nt-ke:#3c5070}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .nt-bang{--nt-ke:#3c5070}}
.nt-bang table{width:100%;min-width:1030px;table-layout:fixed;border-collapse:separate;border-spacing:0;margin:0}
.nt-bang th{background:linear-gradient(120deg,var(--vtos-ban-a,#2a6db5),var(--vtos-ban-b,#1f5fa8));color:#fff;
  font-size:calc(13/14*1rem);font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:11px 8px;
  border-right:1px solid rgba(255,255,255,.28);border-bottom:0;white-space:nowrap}
.nt-bang td{padding:9px 8px;border-bottom:1px solid var(--nt-ke);border-right:1px solid var(--nt-ke);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;vertical-align:middle}
.nt-bang th:last-child,.nt-bang td:last-child{border-right:0}
.nt-bang tbody tr:last-child>td{border-bottom:0}
.nt-bang th.num,.nt-bang td.num{text-align:right;font-family:inherit;font-variant-numeric:tabular-nums}
.nt-bang td.nt-lai{font-weight:700;color:var(--vtos-success,#23804d)}.nt-bang td.nt-lai.lo{color:var(--red,#c4314b)}
.nt-bang td.nt-gc{color:var(--ink2)}
/* VH-38: Tên tour và Ghi chú xuống tối đa 2 dòng thay vì cắt chữ; Ghi chú hẹp lại nhường chỗ cho các cột số. */
.nt-bang td.nt-hai{white-space:normal}
.nt-bang td.nt-hai>span{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;line-height:1.35}
.nt-dong{cursor:pointer}
.nt-dong:hover>td,.nt-dong.mo>td{background:var(--panel2)}
.nt-dong:focus-visible{outline:2px solid var(--orange);outline-offset:-2px}
.nt-mui{display:inline-block;color:var(--ink2);transition:transform .15s}
.nt-dong.mo .nt-mui{transform:rotate(90deg)}
.nt-tt{display:inline-flex;align-items:center;justify-content:center;gap:5px;width:100%;border:0;border-radius:999px;
  padding:5px 6px;font:inherit;font-size:calc(13/14*1rem);font-weight:700;cursor:pointer;margin:0}
.nt-tt::before{content:"";width:8px;height:8px;border-radius:50%;background:currentColor}
.nt-tt.do{background:#fde8ec;color:#b72f45}.nt-tt.vang{background:#fff1d6;color:#9a6400}
.nt-tt.xanh{background:#e2f4e9;color:#23804d}.nt-tt.xam{background:#eceff4;color:#5f6f86}
.nt-ct>td{background:var(--panel2);white-space:normal;padding:12px 16px 16px;overflow:visible}
.nt-ct dl{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px 24px;margin:0}
.nt-ct dl>div{min-width:0}.nt-ct .dai{grid-column:1/-1}
.nt-ct dt{font-size:calc(13/14*1rem);font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--ink2)}
.nt-ct dd{margin:2px 0 0}.nt-ct ul{margin:2px 0 0;padding-left:18px}
.nt-nut{margin-top:12px;display:flex;gap:8px}.nt-nut .act{margin:0}
`;
