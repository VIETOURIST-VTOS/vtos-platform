"use client";
import { useEffect, useState, useCallback } from "react";
import { useShell } from "@/components/Shell";
import LuoiChamCong from "@/components/LuoiChamCong";
import XacNhanCong from "@/components/XacNhanCong";
import BangLuongBoSung from "@/components/BangLuongBoSung";
// 5.6 Danh gia nhan su · 09/10/2026. The nay ten la "Danh gia & su vu" ma truoc ban nay chi co SU
// VU — khong ky danh gia, khong tieu chi, khong nguoi cham. Bang cham dung o DAU the, tren so su
// vu, vi danh gia la viec lam moi ky con bien ban su vu la viec chi lam khi co chuyen.
import { BangChamDiem } from "@/components/DanhGiaNhanSu";
// 5.8 Bao cao bien dong nhan su · 09/10/2026. Dat o the "Tong quan HCNS" chu khong dung man hinh
// rieng: cung mot tap nguoi, cung mot nhom nguoi doc. Tach ra hai cho thi nguoi xem phai nho di
// hai noi de tra loi mot cau hoi.
import BienDongNhanSu from "@/components/BienDongNhanSu";
import DinhKem from "@/components/DinhKem";
import { api, vnd, fmtD, fmtDT, getToken } from "@/lib/api";
import { Tag, errMsg, KyO, tenKy } from "@/components/ui";

/** Visa, HDV & phân chuyến, Đội xe là nghiệp vụ của Điều hành (Đề xuất 06/9/2026 mục 2) nên nằm ở trang
 *  /ops với quyền của Điều hành; Nhân sự giữ hồ sơ lao động, lương và sự vụ. Cùng một màn hình, hai lối vào. */
const TABS_HR: [string, string][] = [["tong_quan", "Tổng quan HCNS"], ["payroll", "Bảng lương"],
  ["employees", "Hồ sơ nhân sự"], ["cham_cong", "Chấm công & nghỉ phép"], ["incidents", "Đánh giá & sự vụ"]];
const TABS_OPS: [string, string][] = [["visa", "Hồ sơ visa"], ["guides", "HDV & phân chuyến"], ["fleet", "Đội xe"]];
const CD: Record<string, string> = { cham_cong: "Chấm công ngày", bao_cao_ngay: "Báo cáo ngày", theo_chuyen: "Theo chuyến", luong_cong_tac_phi: "Lương + công tác phí" };
// Tên trạng thái CŨ giữ nguyên trong bảng này: những kỳ đã chạy qua chuỗi cũ vẫn mang tên cũ, và
// màn hình phải đọc được lịch sử chứ không chỉ đọc được hiện tại.
const PST: Record<string, [string, string]> = {
  nhap: ["Robot nháp", "warn"], da_kiem_co_so: ["Đã kiểm cơ sở – chờ HCNS", "navy"],
  hcns_kiem: ["HCNS đã kiểm – chờ Chủ tịch/TGĐ ký", "warn"], da_ky: ["Đã ký & khóa", "ok"],
  kt_xac_nhan: ["Kế toán đã xác nhận cơ sở (chuỗi cũ)", "navy"],
  hcns_lap: ["HCNS đã lập (chuỗi cũ)", "warn"], tgd_ky: ["TGĐ đã ký lô (chuỗi cũ)", "ok"] };
// Bước kế tiếp: [các vai làm được, nhãn nút]. DANH SÁCH vai chứ không phải một vai — chữ ký cuối
// mở cho Chủ tịch HOẶC TGĐ (quyết định 07/10/2026), và một ô chỉ chứa được một vai thì màn hình
// lại giấu nút của Chủ tịch đúng như bảng cũ đã giấu cột của ông.
// Ẩn nút KHÔNG phải hàng rào: hàng rào nằm ở require_roles và ở hàm advance của máy chủ.
const NEXT: Record<string, [string[], string]> = {
  da_kiem_co_so: [["hcns"], "HCNS kiểm xong – trình ký"],
  hcns_kiem: [["chutich", "tgd"], "Ký & khóa kỳ lương"],
  kt_xac_nhan: [["hcns"], "HCNS kiểm xong – trình ký"],
  hcns_lap: [["chutich", "tgd"], "Ký & khóa kỳ lương"] };
// Trạng thái trả tiền của cả kỳ. Cộng từ các lần chi ở máy chủ; màn hình chỉ đặt tên cho nó.
const TRA: Record<string, [string, string]> = {
  "": ["Chưa chi", "warn"], dang_chi: ["Đã chi một phần", "warn"],
  da_tra_du: ["Đã trả đủ", "ok"], loi_chi: ["Có lần chi sai số", "red"] };
const lastMonth = () => { const d = new Date(); d.setDate(1); d.setMonth(d.getMonth() - 1); return d.toISOString().slice(0, 7); };

export default function HrScreens({ scope = "hr" }: { scope?: "hr" | "ops" }) {
  const { user, toast } = useShell();
  const role = user?.role || "";
  // Bảng lương tách khỏi hồ sơ nhân sự (chỉ đạo 07/9/2026): máy chủ nói tab nào người này mở được.
  // Không tự suy từ vai trò ở giao diện – quyền xem bảng lương có thể là ngoại lệ cấp cho riêng một người,
  // và hai nơi cùng suy ra một câu trả lời là hai nơi sẽ lệch nhau.
  const hrTabs = user?.hr_tabs;
  const TABS = scope === "ops" ? TABS_OPS : TABS_HR.filter(([k]) => !hrTabs || hrTabs.includes(k));
  const [cos, setCos] = useState<any[]>([]);
  const [tab, setTab] = useState(scope === "ops" ? "visa" : "payroll");
  // mở đúng tab khi vào từ menu bên trái (?tab=...); tab không có quyền thì rơi về tab đầu tiên mở được,
  // chứ không hiện màn hình trống rồi để người dùng đoán vì sao
  useEffect(() => { const q = new URLSearchParams(window.location.search).get("tab"); if (q) setTab(q); }, []);
  useEffect(() => { if (TABS.length && !TABS.some(([k]) => k === tab)) setTab(TABS[0][0]); }, [TABS, tab]);
  const [period, setPeriod] = useState(lastMonth());
  const [meta, setMeta] = useState<any>({ departments: {}, positions: {}, offices: {} });
  const [run, setRun] = useState<any>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [emps, setEmps] = useState<any[]>([]);
  const [khoa, setKhoa] = useState<any[]>([]);
  const [tepNV, setTepNV] = useState("");   // mã NV đang mở hồ sơ giấy tờ
  const [treo, setTreo] = useState<any>(null);
  const [phieu, setPhieu] = useState<any>(null);
  const [phapNhan, setPhapNhan] = useState<any>(null);
  const [xungDot, setXungDot] = useState<any>(null);
  // Danh sách cờ của lần kiểm cơ sở gần nhất. RỖNG khác CHƯA CHẠY: `null` là chưa bấm kiểm lần nào,
  // còn `[]` là đã kiểm và không còn gì phải xử lý. Gộp hai cái thành một là nói với người dùng
  // rằng bảng sạch trong khi chưa ai kiểm.
  const [co, setCo] = useState<any[] | null>(null);
  // Các lần chi của kỳ. `null` là chưa hỏi máy chủ; `[]` là đã hỏi và kỳ này chưa chi lần nào —
  // hai điều khác nhau, và gộp lại là nói "chưa chi" trong khi chưa ai biết.
  const [chi, setChi] = useState<any | null>(null);
  const [soTN, setSoTN] = useState<any | null>(null);
  const [tongQuan, setTongQuan] = useState<any | null>(null);
  // `cham` đã rời khỏi đây 08/10/2026: lưới chấm công nay là thành phần `LuoiChamCong`, nó tự gọi
  // `/attendance` và tự giữ trạng thái. Để lại một bản sao thứ hai ở đây là hai chỗ đọc cùng một cửa.
  const [donNghi, setDonNghi] = useState<any[]>([]);
  const [hrmMeta, setHrmMeta] = useState<any>({ leave_kinds: {}, leave_status: {} });
  const [lsMa, setLsMa] = useState("");
  const [lsNV, setLsNV] = useState<any | null>(null);
  const [dangTai, setDangTai] = useState("");
  const [cong, setCong] = useState<Record<string, string>>({});
  // Chỗ lệch giữa BẢNG CHẤM CÔNG và số công đã nhập vào bảng lương. `null` là chưa hỏi máy chủ, khác
  // hẳn "đã hỏi và không có chỗ nào lệch" — gộp hai cái là nói bảng sạch trong khi chưa ai soi.
  const [lech, setLech] = useState<any | null>(null);
  // Cột TNCN của bảng lương KHÔNG gồm người hợp đồng lao động — xem `hrm.tncn_chua_tinh()`.
  const [tncn, setTncn] = useState<any | null>(null);
  const [visa, setVisa] = useState<any[]>([]);
  const [asg, setAsg] = useState<any[]>([]);
  const [veh, setVeh] = useState<any[]>([]);
  const [disp, setDisp] = useState<any[]>([]);
  const [fleet, setFleet] = useState<any>(null);
  const [inc, setInc] = useState<any[]>([]);
  const [tours, setTours] = useState<any[]>([]);
  const [fEmp, setFEmp] = useState<any>({ code: "", full_name: "", department: "kd_le", position: "nv", office: "hcm",
    contract_type: "hdld", base_salary: "", start_date: "", title: "", sales_group: "", phone: "", probation: false });
  const [fVisa, setFVisa] = useState<any>({ customer_name: "", market: "", method: "tu_xu_ly", handler_id: "", office: "hcm", alliance: false, revenue: "" });
  const [fAsg, setFAsg] = useState<any>({ tour_id: "", guide_id: "", days: "", rate_per_day: "", rate_id: "", holiday: false });
  const [grates, setGrates] = useState<any[]>([]);
  const [fGrate, setFGrate] = useState<any>({ route: "", days: "", rate_per_day: "", old_rate_per_day: "", effective_from: new Date().toISOString().slice(0, 10) });
  const [incMeta, setIncMeta] = useState<any>(null);
  const [rates, setRates] = useState<any[]>([]);
  const [fRate, setFRate] = useState<any>({ route: "", days: "", internal_price: "", partner_price: "", effective_from: new Date().toISOString().slice(0, 10) });
  const [fInc, setFInc] = useState<any>({ employee_id: "", level: "2", description: "", occurred_on: new Date().toISOString().slice(0, 10) });
  // SỬA HỒ SƠ — 12/10/2026. Cửa `PUT /employees/{id}` đã có đủ từ lâu (nhận mọi trường, kiểm
  // phiên bản, tự ghi lịch sử điều chuyển), nhưng màn hình chỉ gọi nó đúng một kiểu — gửi
  // {họ tên, phòng, active} để bấm Ngưng / Mở lại. Có biểu TẠO, không có biểu SỬA. Hệ quả: một
  // số điện thoại gõ sai hay một chức danh sai thì không màn hình nào chữa được, phải nhờ người
  // gọi thẳng vào máy chủ. Đúng cái ranh giới 09/9 cấm: con số mà người phụ trách không tự nhập
  // được là con số sẽ sai và ở yên đó.
  const [sua, setSua] = useState<any>(null);
  const [dc, setDc] = useState<any>({ tu_ngay: "", ly_do: "" });
  const canHR = ["hcns", "cntt"].includes(role), canDH = ["nv_dh", "tp_dh", "hcns", "cntt"].includes(role);

  const load = useCallback(async () => {
    if (!Object.keys(meta.departments).length) api("/hr/meta").then(setMeta);
    if (!emps.length) api("/employees").then(setEmps).catch(() => {});
    if (!tours.length) api("/tours").then((r) => setTours(r.rows || [])).catch(() => {});
    if (tab === "payroll") api(`/payroll-runs/${period}`).then(setRun).catch((e) => toast(errMsg(e), true));
    if (tab === "payroll") { api("/payroll/khoan-treo").then(setTreo).catch(() => {}); api("/payroll/xung-dot-ho-so").then(setXungDot).catch(() => {}); }
    if (tab === "payroll") api(`/payroll-runs/${period}/lech-cong`).then(setLech).catch(() => setLech(null));
    if (tab === "payroll") api(`/payroll-runs/${period}/tncn-con-thieu`).then(setTncn).catch(() => setTncn(null));
    if (tab === "payroll") api(`/payroll-runs/${period}/chi`).then(setChi).catch(() => setChi(null));
    if (tab === "payroll") api(`/payroll-runs/${period}/so-thu-nhap`).then(setSoTN).catch(() => setSoTN(null));
    if (tab === "payroll") { api(`/payroll-runs/${period}/phieu-luong`).then(setPhieu).catch(() => setPhieu(null)); api(`/payroll-runs/${period}/theo-phap-nhan`).then(setPhapNhan).catch(() => setPhapNhan(null)); }
    if (tab === "tong_quan") api("/hr/tong-quan").then(setTongQuan).catch((e) => toast(errMsg(e), true));
    if (tab === "cham_cong") api("/leaves").then((r: any) => setDonNghi(r?.rows || (Array.isArray(r) ? r : []))).catch(() => setDonNghi([]));
    if (tab === "cham_cong" && !Object.keys(hrmMeta.leave_kinds || {}).length) api("/hrm/meta").then(setHrmMeta).catch(() => {});
    if (tab === "employees") { api("/employees").then(setEmps); api("/companies").then(setCos).catch(() => {}); }
    if (tab === "employees") api("/users/khoa").then(setKhoa).catch(() => {});
    if (tab === "visa") api("/visa").then(setVisa);
    if (tab === "guides") { api("/guide-assignments").then(setAsg); api("/guide-rates").then(setGrates); }
    if (tab === "fleet") { api("/vehicles").then(setVeh); api("/dispatch").then(setDisp); api("/vehicle-rates").then(setRates); api(`/fleet/summary?period=${period}`).then(setFleet); api("/companies").then(setCos).catch(() => {}); }
    if (tab === "guides") api("/companies").then(setCos).catch(() => {});
    if (tab === "incidents") { api("/incidents").then(setInc); api("/incident-levels").then(setIncMeta); }
  }, [tab, period]); // eslint-disable-line
  useEffect(() => { load(); }, [load]);
  const kiemCoSo = async () => {
    try {
      const r = await api<any>(`/payroll-runs/${period}/kiem-co-so`, { method: "POST" });
      setCo(r.co || []);
      toast(r.message);
      load();
    } catch (x) { toast(errMsg(x), true); }
  };

  const moLichSu = async (eid: number) => {
    if (!eid) { setLsNV(null); return; }
    try { setLsNV(await api(`/employees/${eid}/lich-su-to-chuc`)); }
    catch (x) { toast(errMsg(x), true); setLsNV(null); }
  };
  const chiDanhSach = async () => { try { setChi(await api(`/payroll-runs/${period}/chi`)); } catch { setChi(null); } };
  // Tải tệp phải đi bằng fetch chứ không dùng `api`: FormData cần trình duyệt tự đặt ranh giới
  // multipart, mà `api` thì gán sẵn Content-Type cho thân JSON.
  const taiTep = async (lan: number, cua: "unc" | "phu-luc", f: File) => {
    setDangTai(`${lan}:${cua}`);
    try {
      const fd = new FormData(); fd.append("tep", f);
      const r = await fetch(`/api/v1/payroll-runs/${period}/chi/${lan}/${cua}`, {
        method: "POST", body: fd, headers: { Authorization: `Bearer ${getToken() || ""}` } });
      const d = await r.json();
      if (!r.ok) throw { status: r.status, message: d?.detail || "Không tải được tệp" };
      toast(d.message); await chiDanhSach();
    } catch (x) { toast(errMsg(x), true); } finally { setDangTai(""); }
  };

  const post = async (path: string, json?: any, method = "POST") => { try { const r = await api(path, { method, json }); toast(r.message || "Xong"); load(); return r; } catch (x) { toast(errMsg(x), true); } };
  const guides = emps.filter((e) => e.department === "huong_dan");
  const empName = (id: number) => emps.find((e) => e.id === id)?.full_name || id;

  return (<>
    {/* Cùng một thành phần phục vụ hai phân hệ, nên tiêu đề phải theo phân hệ đang vào. Trước
        29/9/2026 nó ghi cứng "Nhân sự – Lương (robot R6)": người Điều hành bấm "Bảng giá vận tải"
        hay "Lịch & bố trí hướng dẫn" mở đúng tab, nhưng đọc tiêu đề lại tưởng mình lạc sang màn
        hình Lương của Nhân sự — và đoạn giải thích ngay dưới cũng nói chuyện bảng lương. */}
    <h1>{scope === "ops" ? "Điều hành – Visa, hướng dẫn viên & đội xe" : "Nhân sự – Lương (robot R6)"}</h1>
    {scope === "ops"
      ? <p className="muted">Ba việc của Điều hành nằm chung một màn hình: <b>hồ sơ visa</b>, <b>hướng dẫn viên và phân chuyến</b>, <b>đội xe</b>. Số liệu thù lao ở đây là phần Điều hành xác nhận; bảng lương và bút toán vẫn do Nhân sự lập ở màn hình riêng.</p>
      : <p className="muted">Thưởng và hoa hồng tính theo <b>tháng quyết toán</b>, căn cứ duy nhất là số liệu Kế toán đã xác nhận; chế tài chỉ chạm thưởng/hoa hồng, không trừ lương cơ bản (Điều 127.2 BLLĐ). Luồng: robot nháp → Kế toán xác nhận cơ sở → HCNS lập → TGĐ ký lô → bút toán 642/334, 632/338, TNCN 10% CTV.</p>}
    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
      {TABS.map(([k, l]) => <button key={k} className={"act " + (tab === k ? "" : "grey")} style={{ margin: 0 }} onClick={() => setTab(k)}>{l}</button>)}
      <label style={{ marginLeft: "auto" }}>Kỳ lương <input type="month" value={period} onChange={(e) => setPeriod(e.target.value)} /></label>
    </div>

    {tab === "tong_quan" && tongQuan && <>
      <div className="panel"><BienDongNhanSu /></div>
      <p className="muted">Màn hình này <b>chỉ đọc</b> và không sinh ra con số nào của riêng nó: mỗi ô là một phép
        đếm trên bảng đã có, chạy bằng đúng hàm mà các màn hình kia đang dùng. Viết lại phép đếm ở đây là tạo ra
        một nguồn thứ hai, và hai nguồn sẽ lệch.</p>
      <div className="kpis">
        <div className="kpi"><b>{tongQuan.nhan_su.tong}</b><span>Đang làm việc · {tongQuan.nhan_su.hdld} HĐLĐ · {tongQuan.nhan_su.ctv} CTV</span></div>
        <div className="kpi"><b>{tongQuan.ho_so_thieu.so_nguoi}</b><span>Hồ sơ còn thiếu thông tin bắt buộc</span></div>
        <div className="kpi"><b>{tongQuan.hop_dong?.het_han?.length ?? 0}</b><span>Hợp đồng đã hết hạn</span></div>
        <div className="kpi"><b>{tongQuan.hop_dong?.sap_het_han?.length ?? 0}</b><span>Hợp đồng sắp đến hạn</span></div>
        <div className="kpi"><b>{tongQuan.nghi_phep_cho_duyet.so_don}</b><span>Đơn nghỉ chờ duyệt</span></div>
        <div className="kpi"><b>{tongQuan.su_vu_trong_thang.so_vu}</b><span>Sự vụ hiệu lực trong tháng</span></div>
      </div>
      {tongQuan.bang_luong && <p><b>Kỳ lương {tongQuan.bang_luong.period}:</b>{" "}
        <Tag cls={PST[tongQuan.bang_luong.trang_thai]?.[1]}>{PST[tongQuan.bang_luong.trang_thai]?.[0] || tongQuan.bang_luong.trang_thai}</Tag>
        {" "}{tongQuan.bang_luong.so_nguoi} người · thực nhận {vnd(tongQuan.bang_luong.thuc_nhan)}
        {tongQuan.bang_luong.tra_trang_thai && <> · <Tag cls={TRA[tongQuan.bang_luong.tra_trang_thai]?.[1]}>{TRA[tongQuan.bang_luong.tra_trang_thai]?.[0]}</Tag></>}</p>}
      {!tongQuan.co_bang_luong && <p className="muted">Khối bảng lương không hiện vì vai trò của bạn không mở được thẻ Bảng lương.
        Thẻ này mở rộng hơn thẻ Bảng lương, nên in thẳng số lương ở đây là mở bảng lương bằng cửa sau.</p>}
      <div className="panel wrap"><h2>Nhân sự theo phòng</h2>
        <table><thead><tr><th>Phòng</th><th className="num">Tổng</th><th className="num">HĐLĐ</th><th className="num">CTV</th></tr></thead>
          <tbody>{tongQuan.nhan_su.theo_phong.map((g: any) => <tr key={g.ma}><td>{g.ten}</td>
            <td className="num"><b>{g.tong}</b></td><td className="num">{g.hdld}</td><td className="num">{g.ctv}</td></tr>)}</tbody></table></div>
      {tongQuan.ho_so_thieu.so_nguoi > 0 && <div className="panel wrap"><h2>Hồ sơ còn thiếu · {tongQuan.ho_so_thieu.so_nguoi} người</h2>
        <table><thead><tr><th>Mã</th><th>Họ tên</th><th>Phòng</th><th className="num">Đủ</th><th>Thiếu</th></tr></thead>
          <tbody>{tongQuan.ho_so_thieu.rows.map((r: any) => <tr key={r.ma}><td className="mono">{r.ma}</td><td>{r.ten}</td>
            <td>{meta.departments[r.phong] || r.phong}</td><td className="num">{r.phan_tram}%</td>
            <td className="muted">{(r.thieu || []).join(", ")}</td></tr>)}</tbody></table></div>}
      <div className="panel wrap"><h2>Lịch sử tổ chức</h2>
        <p className="muted">{tongQuan.lich_su_to_chuc.ghi_chu} Hiện có <b>{tongQuan.lich_su_to_chuc.chua_co_dong_nao}</b> người chưa có chặng nào.</p>
        <label>Xem của&nbsp;
          <select value={lsMa} onChange={(e) => { setLsMa(e.target.value); moLichSu(Number(e.target.value)); }}>
            <option value="">— chọn người —</option>
            {emps.map((e: any) => <option key={e.id} value={e.id}>{e.code} · {e.full_name}</option>)}
          </select></label>
        {lsNV && (!lsNV.chang.length ? <p className="muted">Chưa có chặng nào cho {lsNV.ten}.</p> :
          <table><thead><tr><th>Từ</th><th>Đến</th><th>Phòng</th><th>Chức vụ</th><th>Văn phòng</th><th>Ghi chú</th></tr></thead>
            <tbody>{lsNV.chang.map((c: any) => <tr key={c.id}>
              <td>{fmtD(c.tu_ngay)}</td><td>{c.den_ngay ? fmtD(c.den_ngay) : <Tag cls="ok">đang mở</Tag>}</td>
              <td>{meta.departments[c.phong] || c.phong}</td><td>{meta.positions[c.chuc_vu] || c.chuc_vu}</td>
              <td>{meta.offices?.[c.van_phong] || c.van_phong}</td>
              {/* Chặng DỰNG LẠI không phải bản ghi lập lúc ấy. Để nó nằm cùng hàng với bản ghi thật
                  mà không nói gì là biến một phỏng đoán hợp lý thành chứng cứ. */}
              <td className="muted">{c.suy_ra && <Tag cls="warn">dựng lại</Tag>} {c.ly_do}</td></tr>)}</tbody></table>)}
      </div>
    </>}

    {tab === "cham_cong" && <>
      <p className="muted">Bảng và cửa nhập <b>đã có từ trước</b>; đợt này chỉ dựng màn hình cho HCNS. Chấm công theo ngày
        áp dụng cho Kế toán và Nhân sự Hành chính; năm phòng còn lại lấy căn cứ là báo cáo công việc trước 20 giờ,
        nên không có mẫu số công chuẩn để chấm.</p>
      {/* 08/10/2026 — THAY bảng chỉ-đọc của Đợt C bằng LƯỚI GHI, vì HAI chuyện:
          (a) `attendance_days` có màn hình ĐỌC mà KHÔNG màn hình nào GHI được, nên HCNS xem được bảng
              chấm công chứ không chấm được — cửa `POST /attendance` mở từ 09/9 mà chưa ai với tới.
          (b) Bảng cũ đọc `r.work ?? r.total_work`, mà `hrm.attendance_sheet()` trả về `work_days` —
              nên cột Công in RỖNG cho mọi dòng. Một cột trống trên bảng chấm công đọc ra là "chưa
              chấm ngày nào", không phải "màn hình đọc sai tên trường". */}
      <LuoiChamCong period={period} />
      {/* CN-1 (21/10/2026): HCNS xác nhận → TGĐ duyệt công tháng; chưa duyệt thì bảng lương chặn. */}
      <XacNhanCong period={period} />
      <div className="panel wrap"><h2>Đơn nghỉ · {donNghi.length}</h2>
        {!donNghi.length ? <p className="muted">Không có đơn nào.</p> :
          <table><thead><tr><th>Người</th><th>Loại</th><th>Từ</th><th>Đến</th><th className="num">Số ngày</th><th>Trạng thái</th><th>Lý do</th></tr></thead>
            <tbody>{donNghi.map((r: any) => <tr key={r.id}>
              <td>{r.full_name || empName(r.employee_id)}</td>
              <td>{hrmMeta.leave_kinds?.[r.kind] || r.kind}</td>
              <td>{fmtD(r.date_from)}</td><td>{fmtD(r.date_to)}</td>
              <td className="num">{r.days}</td>
              <td><Tag cls={r.status === "duyet" ? "ok" : r.status === "cho_duyet" ? "warn" : "red"}>{hrmMeta.leave_status?.[r.status] || r.status}</Tag></td>
              <td className="muted">{r.reason}</td></tr>)}</tbody></table>}</div>
    </>}

    {tab === "payroll" && run && <>
      <DinhKem doiTuong="bang_luong" doiTuongId={period} loai="bang_bieu"
        tieuDe={`Chứng từ bảng lương kỳ ${period}`}
        goi={"Bảng chấm công gốc, quyết định thưởng/phạt, bảng lương đã ký, chứng từ nộp BHXH và TNCN. " +
             "Lưu trong nhóm 06_Nhan_su — dữ liệu cá nhân, phân quyền riêng theo Nghị định 13/2023."} />
      <div className="kpis">
        <div className="kpi"><b>{run.totals.so_nguoi}</b><span>Người · {run.totals.so_chuyen} chuyến KT xác nhận</span></div>
        <div className="kpi"><b>{vnd(run.totals.luong_cb)}</b><span>Lương cơ bản (sau thang giảm)</span></div>
        <div className="kpi"><b>{vnd(run.totals.bien_doi)}</b><span>Thu nhập biến đổi</span></div>
        <div className="kpi"><b>{vnd(run.totals.khoan_tru)}</b><span>Khoản trừ (BHXH {vnd(run.totals.bhxh)} · đoàn phí {vnd(run.totals.doan_phi)} · TNCN {vnd(run.totals.tncn)})</span></div>
        <div className="kpi"><b>{vnd(run.totals.thuc_nhan)}</b><span>Thực nhận</span></div>
      </div>
      <p><Tag cls={PST[run.status]?.[1]}>{PST[run.status]?.[0]}</Tag> {run.kt_confirmed_by && <span className="muted"> · KT {run.kt_confirmed_by} {fmtDT(run.kt_confirmed_at)}</span>}{run.hcns_by && <span className="muted"> · HCNS {run.hcns_by} {fmtDT(run.hcns_at)}</span>}{run.tgd_by && <span className="muted"> · TGĐ {run.tgd_by} {fmtDT(run.tgd_at)} · {run.entry_ids?.length} chứng từ</span>}
        {run.status === "nhap" && ["hcns", "ketoan", "cntt"].includes(role) && <button className="act grey" onClick={() => api(`/payroll-runs/${period}?refresh=true`).then(setRun).then(() => toast("Đã tính lại nháp")).catch((e) => toast(errMsg(e), true))}>Tính lại nháp</button>}
        {run.status === "nhap" && ["hcns", "cntt"].includes(role) && <button className="act" onClick={() => kiemCoSo()}>Kiểm cơ sở</button>}
        {NEXT[run.status] && NEXT[run.status][0].includes(role) && <button className="act teal" onClick={() => post(`/payroll-runs/${period}/advance`)}>{NEXT[run.status][1]}</button>}</p>
      {/* Ô "Khoản trừ … TNCN x đ" ở trên nghĩa là gì thì TUỲ CÔNG TẮC, nên khung này đọc `tncn.da_bat`
          của máy chủ chứ không tự đặt lời. Chưa bật: ô ấy là con số của RIÊNG cộng tác viên (10% thù
          lao HDV), người HĐLĐ đi qua với `tncn: 0.0` và số 0 ấy chìm vào tổng. Đã bật: ô ấy gồm cả
          thuế lũy tiến của người HĐLĐ, và chỗ còn hở là hồ sơ chứ không phải phép tính.
          Màn hình KHÔNG có nút bật. Công tắc là tham số `tncn_luy_tien_tu_ky`, hai chữ ký, ở màn hình
          Tham số — một nút "bắt đầu khấu trừ thuế" đặt cạnh bảng lương là thứ bấm nhầm được. */}
      {tncn && (tncn.tham_so_lac_hau || []).length > 0 && <p className="muted">
        {(tncn.tham_so_lac_hau || []).map((t: any) => <span key={t.khoa}>
          <Tag cls="red">Mức giảm trừ cũ</Tag>{" "}<b>{t.ten}</b> đang áp <b>{vnd(t.dang_ap)}</b>,
          theo <b>{t.can_cu}</b> phải là <b>{vnd(t.theo_luat)}</b>. {t.viec_phai_lam}{" "}
        </span>)}</p>}
      {tncn && tncn.da_bat && <p className="muted">
        <Tag cls="ok">Đang khấu trừ lũy tiến từ kỳ {tncn.ky_bat_dau}</Tag>{" "}
        {tncn.ghi_chu} Còn hở: <b>{tncn.chua_co_hop_dong}</b> người chưa có hợp đồng hiệu lực trong kỳ,{" "}
        <b>{tncn.thieu_mst}</b> người chưa có mã số thuế, <b>{tncn.thieu_muc_bhxh}</b> người chưa có mức
        đóng BHXH (chưa trừ bảo hiểm nên thuế tạm tính đang cao hơn số phải nộp).
        Khai hồ sơ và người phụ thuộc ở màn hình <b>Hợp đồng lao động</b>.</p>}
      {tncn && !tncn.da_bat && tncn.so_nguoi_hdld_khong_tncn > 0 && <p className="muted">
        <Tag cls="warn">{tncn.so_nguoi_hdld_khong_tncn} người HĐLĐ chưa có số TNCN</Tag>{" "}
        {tncn.ghi_chu} Nền dữ liệu hiện tại: <b>{tncn.thieu_mst}</b> người chưa có mã số thuế trong hồ
        sơ, <b>{tncn.co_npt}</b> người đã khai người phụ thuộc mà mức giảm trừ chưa đường nào dùng tới.
        Khai hồ sơ và người phụ thuộc ở màn hình <b>Hợp đồng lao động</b>.</p>}

      {/* BẢNG CHẤM CÔNG VÀ BẢNG LƯƠNG LÀ HAI NGUỒN, VÀ CHỈ MỘT NGUỒN TRẢ TIỀN (08/10/2026).
          Đơn nghỉ đã duyệt ghi vào `attendance_days`; bảng lương lấy số công HCNS gõ tay ở bảng
          "Nhập công thực tế" bên dưới. Không một dòng nào trong `services/hr.py` đọc `AttendanceDay` —
          nên trước bản này, duyệt một đơn nghỉ không lương rồi không làm gì nữa thì bảng lương vẫn
          trả đủ công và KHÔNG CÓ DÒNG NÀO BÁO. Khung này không nối hai nguồn lại (bảng nào thắng là
          quyết định của Chủ tịch / Kế toán trưởng, không phải của màn hình); nó làm chỗ lệch ĐẾM ĐƯỢC. */}
      {lech && lech.so_dong > 0 && <div className="panel"><h2>Bảng chấm công chưa khớp bảng lương · {lech.so_dong} người</h2>
        <p className="muted">Bảng lương trả theo số công <b>HCNS nhập ở bảng dưới</b>, không theo bảng
          chấm công. Hai nơi lệch nhau thì bảng lương vẫn chạy — khung này chỉ nói ra, không tự sửa số
          nào. Lưới chấm công ở thẻ <b>Chấm công &amp; nghỉ phép</b>.</p>
        <div className="kpis">{Object.keys(lech.loai).map((k: string) => <div className="kpi" key={k}>
          <b>{lech.dem[k]}</b><span>{lech.loai[k]}</span></div>)}</div>
        <div className="wrap"><table><thead><tr><th>Mã NV</th><th>Họ tên</th><th>Phòng</th>
          <th className="num">Công theo bảng chấm công</th><th className="num">Công đã nhập</th><th>Việc phải làm</th></tr></thead>
          <tbody>{lech.dong.map((x: any) => <tr key={`${x.ma}-${x.loai}`}>
            <td className="mono">{x.ma}</td><td>{x.ho_ten}</td><td>{meta.departments?.[x.phong] || x.phong}</td>
            <td className="num">{x.cong_theo_bang}</td>
            <td className="num">{x.cong_da_nhap === null ? <Tag cls="warn">chưa nhập</Tag> : x.cong_da_nhap}</td>
            <td className="muted">{x.viec}</td></tr>)}</tbody></table></div>
        {!lech.co_bang_luong && <p className="muted">Kỳ này chưa có bảng lương — số công chưa ai nhập là bình thường.</p>}
      </div>}
      {co !== null && <div className="panel"><h2>Kiểm cơ sở · {co.length} điều cần biết</h2>
        <p className="muted">Quy tắc xác định, không phải suy đoán: cùng đầu vào luôn ra cùng danh sách.
          <b> Không có cờ nghĩa là những thứ đã biết cách kiểm đều sạch, không nghĩa là bảng đúng.</b></p>
        {co.length === 0 ? <p className="muted">Không còn điều gì phải xử lý.</p> :
          <table><thead><tr><th>Mức</th><th>Mã</th><th>Nội dung</th></tr></thead><tbody>
            {co.map((c: any, i: number) => <tr key={i}>
              <td><Tag cls={c.muc === "chan" ? "red" : "warn"}>{c.muc === "chan" ? "Chặn" : "Cảnh báo"}</Tag></td>
              <td className="mono">{c.ma}</td><td>{c.thong_diep}</td></tr>)}
          </tbody></table>}</div>}
      {soTN && soTN.dong?.length > 0 && <div className="panel wrap"><h2>Sổ thu nhập đã ký · {soTN.dong.length} khoản</h2>
        <p className="muted">Ghi tại đúng lúc có chữ ký, trong cùng giao dịch với bản khóa. Đây là chỗ trả lời câu
          <b> “khoản này đã trả chưa”</b> — trước đây hệ thống tính lại mọi khoản từ đầu mỗi lần, nên câu ấy không có
          chỗ nào trả lời được. <b>Không có cửa gõ tay vào sổ này</b>, và việc không có cửa là tính chất an toàn:
          sửa được sổ thì xoá được dấu vết một lần đã trả.</p>
        <table><thead><tr><th>Mã NV</th><th>Loại khoản</th><th>Căn cứ</th><th className="num">Số tiền</th><th>Nguồn</th></tr></thead>
          <tbody>{soTN.dong.map((d: any, i: number) => <tr key={i}>
            <td className="mono">{d.ma_nv}</td>
            <td>{d.loai_ten}{soTN.doc_chiem?.includes(d.loai) && <Tag cls="warn">một quỹ</Tag>}</td>
            <td className="mono muted">{d.can_cu}</td>
            <td className="num">{d.so_tien === null || d.so_tien === undefined ? <Tag cls="warn">rỗng</Tag> : vnd(d.so_tien)}</td>
            <td className="muted mono" style={{ maxWidth: 320 }}>{(d.nguon || []).join(", ")}</td></tr>)}
          </tbody></table></div>}
      {/* CN-2 (21/10/2026): phòng bị giữ lương lúc ký và bảng bổ sung của kỳ. */}
      <BangLuongBoSung period={period} onChi={chiDanhSach} />
      {["da_ky", "tgd_ky"].includes(run.status) && chi && <div className="panel wrap">
        <h2>Kế toán chi · {TRA[chi.tra_trang_thai]?.[0] || "Chưa chi"}</h2>
        <p className="muted">Khúc cuối của chuỗi: kế toán chuyển tiền, tải <b>Ủy nhiệm chi</b> lên, máy đọc rồi
          <b> đối chiếu với bản đã ký</b>. Kết luận đủ / một phần / lỗi do quy tắc xác định tính ra —
          <b> không có ô nào cho người gõ “đã trả đủ”</b>, vì một ô như thế biến cả chuỗi này thành một lời khai.
          Phụ lục từng người là tuỳ chọn, nhưng <b>thiếu nó thì chỉ kết luận được ở mức tổng</b>: tổng khớp vẫn
          có thể một người nhận thừa và một người nhận thiếu.</p>
        {["ketoan", "cntt"].includes(role) &&
          <button className="act" onClick={() => post(`/payroll-runs/${period}/chi`).then(chiDanhSach)}>Mở lần chi mới</button>}
        {(chi.lan_chi || []).length === 0 ? <p className="muted">Kỳ này chưa chi lần nào.</p> :
          <table><thead><tr><th>Lần</th><th>Ủy nhiệm chi</th><th className="num">Số tiền</th><th>Phụ lục</th><th>Kết luận</th><th>Việc tiếp</th></tr></thead>
            <tbody>{chi.lan_chi.map((c: any) => <>
              <tr key={c.lan}>
                <td className="mono">{c.lan}</td>
                <td>{c.ngan_hang} {c.ngay_chuyen && fmtD(c.ngay_chuyen)}<div className="muted mono">{c.so_tham_chieu}</div></td>
                {/* RỖNG ≠ 0: máy chưa đọc được thì nói là chưa đọc được, không in “0 đ”. */}
                <td className="num">{c.so_tien_unc === null || c.so_tien_unc === undefined
                  ? <Tag cls="warn">chưa đọc được</Tag> : <b>{vnd(c.so_tien_unc)}</b>}</td>
                <td>{c.co_phu_luc ? `${c.so_dong_phu_luc} dòng` : <span className="muted">chưa có</span>}</td>
                <td>{c.ket_luan
                  ? <Tag cls={c.ket_luan === "du" ? "ok" : c.ket_luan === "mot_phan" ? "warn" : "red"}>{c.ket_luan_ten}</Tag>
                  : <span className="muted">chưa đối chiếu</span>}</td>
                <td>{!c.ket_luan && ["ketoan", "cntt"].includes(role) && <>
                  <label className="act grey" style={{ cursor: "pointer" }}>{dangTai === `${c.lan}:unc` ? "Đang đọc…" : "Tải UNC"}
                    <input type="file" style={{ display: "none" }} accept="image/*,application/pdf"
                      onChange={(e) => { const f = e.target.files?.[0]; if (f) taiTep(c.lan, "unc", f); e.target.value = ""; }} /></label>
                  <label className="act grey" style={{ cursor: "pointer" }}>{dangTai === `${c.lan}:phu-luc` ? "Đang đọc…" : "Tải phụ lục"}
                    <input type="file" style={{ display: "none" }} accept="image/*,application/pdf"
                      onChange={(e) => { const f = e.target.files?.[0]; if (f) taiTep(c.lan, "phu-luc", f); e.target.value = ""; }} /></label>
                  <button className="act teal" onClick={() => post(`/payroll-runs/${period}/chi/${c.lan}/doi-chieu`).then(chiDanhSach)}>Đối chiếu</button>
                </>}</td></tr>
              {c.ket_qua?.ly_do && <tr key={c.lan + "x"}><td colSpan={6} className="muted" style={{ padding: "2px 24px" }}>
                <b>{c.ket_qua.ly_do}</b>
                {c.ket_qua.tong && <> · bản đã ký {vnd(c.ket_qua.tong.ban_khoa)} · chuyển {vnd(c.ket_qua.tong.unc)}
                  {c.ket_qua.tong.sepay ? <> · <Tag cls="ok">SePay xác nhận tiền đã ra</Tag></>
                    : <> · <Tag cls="warn">chưa thấy giao dịch SePay khớp</Tag></>}</>}
              </td></tr>}
              {(c.ket_qua?.tung_nguoi?.thieu?.length > 0 || c.ket_qua?.tung_nguoi?.lech?.length > 0
                || c.ket_qua?.tung_nguoi?.thua?.length > 0 || c.ket_qua?.tung_nguoi?.nhap_nhang?.length > 0) &&
                <tr key={c.lan + "n"}><td colSpan={6}><table style={{ margin: "4px 0 8px 24px", width: "auto" }}>
                  <thead><tr><th>Mã</th><th>Họ tên</th><th className="num">Phải trả</th><th className="num">Đã chuyển</th><th>Vì sao</th></tr></thead>
                  <tbody>{[...(c.ket_qua.tung_nguoi.thieu || []), ...(c.ket_qua.tung_nguoi.lech || []),
                           ...(c.ket_qua.tung_nguoi.thua || []), ...(c.ket_qua.tung_nguoi.nhap_nhang || [])]
                    .map((x: any, i: number) => <tr key={i}>
                      <td className="mono">{x.ma_nv || ""}</td><td>{x.ho_ten}</td>
                      <td className="num">{x.phai_tra === undefined ? "" : vnd(x.phai_tra)}</td>
                      <td className="num">{x.da_chuyen === undefined ? (x.so_tien === undefined ? "" : vnd(x.so_tien)) : vnd(x.da_chuyen)}</td>
                      <td className="muted">{x.ly_do || (x.lech ? `lệch ${vnd(x.lech)}` : "")}</td></tr>)}
                  </tbody></table></td></tr>}
              {c.phu_luc_ghi_chu && <tr key={c.lan + "g"}><td colSpan={6} className="muted" style={{ padding: "2px 24px" }}>Máy ghi chú: {c.phu_luc_ghi_chu}</td></tr>}
            </>)}</tbody></table>}
      </div>}
      <div className="panel wrap"><table><thead><tr><th>Mã</th><th>Họ tên</th><th>Phòng</th><th>HĐ</th><th>Chế độ công</th><th style={{ textAlign: "right" }}>Lương CB</th><th style={{ textAlign: "right" }}>Biến đổi</th><th style={{ textAlign: "right" }}>BHXH</th><th style={{ textAlign: "right" }}>Đoàn phí</th><th style={{ textAlign: "right" }}>TNCN</th><th style={{ textAlign: "right" }}>Thực nhận</th><th>Ghi chú robot</th></tr></thead>
        <tbody>{run.rows.map((r: any) => <>
          <tr key={r.ma} style={{ cursor: "pointer" }} onClick={() => setOpen(open === r.ma ? null : r.ma)}><td className="mono">{r.ma}</td><td><b>{r.ten}</b></td><td>{meta.departments[r.phong] || r.phong}<div className="muted">{meta.positions[r.chuc_vu]}</div></td><td>{r.hop_dong === "hdld" ? "HĐLĐ" : "CTV"}</td><td className="muted">{CD[r.che_do_cong] || ""}</td>
            <td style={{ textAlign: "right" }}>{vnd(r.luong_cb)}{r.xac_dinh_luong && r.xac_dinh_luong.muc_ky !== r.xac_dinh_luong.muc_hop_dong && <div className="muted" style={{ fontSize: 11 }}>HĐ {vnd(r.xac_dinh_luong.muc_hop_dong)}</div>}</td><td style={{ textAlign: "right" }}>{vnd(r.bien_doi)}</td><td style={{ textAlign: "right" }}>{r.bhxh ? <>{vnd(r.bhxh)}<div className="muted" style={{ fontSize: 11 }}>trên {vnd(r.bhxh_base)}</div></> : (r.thieu_muc_bhxh ? <Tag cls="warn">chưa có mức</Tag> : "")}</td><td style={{ textAlign: "right" }}>{r.doan_phi ? vnd(r.doan_phi) : ""}</td><td style={{ textAlign: "right" }}>{r.tncn ? vnd(r.tncn) : ""}</td><td style={{ textAlign: "right" }}><b>{vnd(r.thuc_nhan)}</b></td><td className="muted" style={{ maxWidth: 320 }}>{r.ghi_chu}</td></tr>
          {open === r.ma && <tr key={r.ma + "x"}><td colSpan={12} className="muted" style={{ padding: "2px 24px" }}><b>Xác định mức lương của kỳ:</b> {r.xac_dinh_luong ? r.xac_dinh_luong.giai_thich : "—"}{r.xac_dinh_luong?.lookback_inputs && <> · {r.xac_dinh_luong.lookback_inputs.map((x: any) => `${x.ky}: ${vnd(x.loi_nhuan)}`).join(" · ")}</>}</td></tr>}
          {open === r.ma && r.khoan.length > 0 && <tr key={r.ma + "k"}><td colSpan={12}><table style={{ margin: "4px 0 8px 24px", width: "auto" }}><tbody>{r.khoan.map((k: any, i: number) => <tr key={i}><td>{k.ten}</td><td style={{ textAlign: "right" }}>{vnd(k.tien)}</td><td className="muted">{k.ghi_chu}</td></tr>)}</tbody></table></td></tr>}
        </>)}</tbody></table></div>
      {run.totals?.thieu_muc_bhxh?.length > 0 && <div className="panel"><h2>Chưa có mức đóng BHXH: {run.totals.thieu_muc_bhxh.length} người</h2>
        <p className="muted">Bảo hiểm và đoàn phí tính trên <b>tiền lương làm căn cứ đóng BHXH bắt buộc</b>, không phải lương hợp đồng. Chưa có mức đóng thì hệ thống <b>không trừ</b> và ghi rõ — trừ nhầm là lấy tiền của người lao động. HCNS nạp danh sách đóng BHXH của kỳ trước khi trình ký.</p>
        <p className="mono">{run.totals.thieu_muc_bhxh.join(", ")}</p></div>}
      {run.totals?.chua_du_co_so?.length > 0 && <div className="panel"><h2>Chưa đủ cơ sở tính lương cho {run.totals.chua_du_co_so.length} người</h2>
        <p className="muted">Doanh thu tính chỉ tiêu chỉ đếm chuyến Kế toán <b>đã xác nhận quyết toán</b>. Những người này còn chuyến chưa chốt nên doanh thu của họ chưa xác định được – <b>không được hiểu là bán được 0 đồng</b>. Kế toán phải chốt quyết toán trước khi trình ký kỳ lương này.</p>
        <p className="mono">{run.totals.chua_du_co_so.join(", ")}</p></div>}
      {xungDot?.so_luong > 0 && <div className="panel"><h2>Xung đột hồ sơ chặn chạy kỳ lương ({xungDot.so_luong})</h2>
        <ul>{xungDot.rows.map((x: any, i: number) => <li key={i}>{x.thong_diep}</li>)}</ul>
        <p className="muted">Một mã dùng cho hai người nghĩa là hệ thống không biết trả tiền cho ai. Hệ thống dừng và nói ra, không tự chọn hồ sơ đầu tiên.</p></div>}
      {canHR && run.status === "nhap" && run.rows.some((r: any) => r.che_do_cong === "cham_cong") && <div className="panel wrap"><h2>Nhập công thực tế — Kế toán và Nhân sự Hành chính</h2>
        <p className="muted">Hai bộ phận duy nhất còn chấm công theo ngày từ 01/9/2026. Năm phòng còn lại lấy căn cứ là báo cáo công việc trước 20 giờ (Điều 12) nên không có mẫu số công chuẩn.</p>
        <table><thead><tr><th>Mã</th><th>Họ tên</th><th className="num">Công chuẩn</th><th className="num">Công thực tế</th><th style={{ textAlign: "right" }}>Lương của kỳ</th></tr></thead>
          <tbody>{run.rows.filter((r: any) => r.che_do_cong === "cham_cong").map((r: any) => <tr key={r.ma}><td className="mono">{r.ma}</td><td>{r.ten}</td>
            <td className="num">{run.totals?.cong_chuan || 26}</td>
            <td className="num"><input style={{ width: 70 }} value={cong[r.ma] ?? (r.xac_dinh_luong?.can_cu?.cong_thuc_te ?? "")} onChange={(e) => setCong({ ...cong, [r.ma]: e.target.value })} /></td>
            <td style={{ textAlign: "right" }}>{vnd(r.luong_cb)}{r.xac_dinh_luong?.thieu_du_lieu && <Tag cls="warn">chưa nhập công</Tag>}</td></tr>)}</tbody></table>
        <button className="act orange" onClick={() => {
          const gui: Record<string, number> = {};
          for (const [k, v] of Object.entries(cong)) if (v !== "") gui[k] = Number(v);
          post(`/payroll-runs/${period}/cham-cong`, { cong_thuc_te: gui }, "PUT").then((r) => { if (r?.run) setRun(r.run); setCong({}); });
        }}>Lưu công và tính lại</button></div>}
      {treo && treo.tong_dong > 0 && <div className="panel wrap"><h2>Khoản đang treo — {treo.tong_dong} dòng trên {treo.tong_chuyen} chuyến</h2>
        <p className="muted">{treo.ghi_chu}</p>
        {treo.viec_can_lam && <p><b>Việc cần làm:</b> {treo.viec_can_lam}</p>}
        <table><thead><tr><th>Chuyến</th><th>Kết thúc</th><th>Hạn quyết toán</th><th className="num">Quá hạn</th><th>Người hưởng</th><th>Vai trò</th><th>Bước tiếp theo</th><th>Lý do</th></tr></thead>
          <tbody>{treo.rows.slice(0, 60).map((x: any, i: number) => <tr key={i}><td><b>{x.tour_code}</b><div className="muted">{x.tour_name}</div></td><td>{fmtD(x.ket_thuc)}</td><td>{fmtD(x.han_quyet_toan)}</td>
            <td className="num">{x.qua_han_ngay ? <Tag cls="red">{x.qua_han_ngay} ngày</Tag> : <Tag cls="warn">chưa tới hạn</Tag>}</td>
            <td className="mono">{x.ma}<div className="muted">{x.ten}</div></td><td>{x.vai_tro}</td><td>{x.buoc_tiep_theo ? <Tag cls={x.co_so_quyet_toan ? "warn" : ""}>{x.buoc_tiep_theo}</Tag> : ""}</td><td className="muted">{x.ly_do}</td></tr>)}</tbody></table>
        {treo.rows.length > 60 && <p className="muted">Đang hiển thị 60 dòng đầu trong {treo.rows.length}.</p>}</div>}
      {phieu && <div className="panel"><h2>Phiếu lương của tôi — kỳ {phieu.period}</h2>
        <p className="muted">{phieu.nhan_su.ten} · mã {phieu.nhan_su.ma} · {phieu.nhan_su.phong}{phieu.nhan_su.phap_nhan_tra_luong ? ` · trả lương tại ${phieu.nhan_su.phap_nhan_tra_luong}` : ""} · {phieu.nhan_su.che_do_cong}</p>
        {phieu.xac_dinh_luong && <p><b>Cách xác định mức lương của kỳ:</b> {phieu.xac_dinh_luong.giai_thich}</p>}
        <div className="grid">
          <div><b>Thu nhập</b>
            <table><tbody>
              <tr><td>Lương cơ bản của kỳ</td><td style={{ textAlign: "right" }}>{vnd(phieu.thu_nhap.luong_co_ban_ky)}</td></tr>
              {phieu.thu_nhap.cac_khoan.map((k: any, i: number) => <tr key={i}><td>{k.ten}</td><td style={{ textAlign: "right" }}>{vnd(k.tien)}</td></tr>)}
              <tr><td><b>Tổng thu nhập</b></td><td style={{ textAlign: "right" }}><b>{vnd(phieu.thu_nhap.tong)}</b></td></tr>
            </tbody></table></div>
          <div><b>Khoản trừ</b>
            <table><tbody>
              {phieu.khoan_tru.chi_tiet_che_tai.map((k: any, i: number) => <tr key={i}><td>{k.ten}</td><td style={{ textAlign: "right" }}>{vnd(-k.tien)}</td></tr>)}
              <tr><td>Bảo hiểm xã hội phần người lao động{phieu.muc_dong_bhxh ? <span className="muted"> (trên {vnd(phieu.muc_dong_bhxh)})</span> : ""}</td><td style={{ textAlign: "right" }}>{vnd(phieu.khoan_tru.bhxh_nguoi_lao_dong)}</td></tr>
              <tr><td>Đoàn phí công đoàn</td><td style={{ textAlign: "right" }}>{vnd(phieu.khoan_tru.doan_phi_cong_doan)}</td></tr>
              {phieu.khoan_tru.tncn_khau_tru > 0 && <tr><td>Thuế TNCN khấu trừ 10%</td><td style={{ textAlign: "right" }}>{vnd(phieu.khoan_tru.tncn_khau_tru)}</td></tr>}
              <tr><td><b>Tổng khoản trừ</b></td><td style={{ textAlign: "right" }}><b>{vnd(phieu.khoan_tru.tong)}</b></td></tr>
            </tbody></table></div>
        </div>
        <p style={{ fontSize: 18 }}><b>Phải trả: {vnd(phieu.thuc_nhan)}</b> {phieu.da_ky ? <Tag cls="ok">Đã ký lô</Tag> : <Tag cls="warn">Chưa ký lô</Tag>}</p>
        {phieu.ghi_chu && <p className="muted">{phieu.ghi_chu}</p>}
        {phieu.khoan_dang_treo?.length > 0 && <><p><b>Đang treo {phieu.khoan_dang_treo.length} khoản</b> — {phieu.luu_y}</p>
          <div className="wrap"><table><thead><tr><th>Chuyến</th><th>Kết thúc</th><th>Hạn quyết toán</th><th className="num">Quá hạn</th><th>Bước tiếp theo</th></tr></thead>
            <tbody>{phieu.khoan_dang_treo.slice(0, 20).map((x: any, i: number) => <tr key={i}><td><b>{x.tour_code}</b></td><td>{fmtD(x.ket_thuc)}</td><td>{fmtD(x.han_quyet_toan)}</td>
              <td className="num">{x.qua_han_ngay ? <Tag cls="red">{x.qua_han_ngay} ngày</Tag> : "—"}</td><td className="muted">{x.buoc_tiep_theo || x.ly_do}</td></tr>)}</tbody></table></div></>}
      </div>}
      {phapNhan?.rows?.length > 0 && <div className="panel wrap"><h2>Bảng lương theo pháp nhân trả lương</h2>
        <p className="muted">{phapNhan.ghi_chu}</p>
        <table><thead><tr><th>Pháp nhân</th><th className="num">Người</th><th style={{ textAlign: "right" }}>Thu nhập</th><th style={{ textAlign: "right" }}>Khoản trừ</th><th style={{ textAlign: "right" }}>BHXH</th><th style={{ textAlign: "right" }}>Phải trả</th></tr></thead>
          <tbody>{phapNhan.rows.map((g: any, i: number) => <tr key={i}><td>{g.chua_xac_dinh ? <Tag cls="warn">Chưa xác định pháp nhân</Tag> : <b>{g.code}</b>}<div className="muted">{g.company}</div></td>
            <td className="num">{g.so_nguoi}</td><td style={{ textAlign: "right" }}>{vnd(g.thu_nhap)}</td><td style={{ textAlign: "right" }}>{vnd(g.khoan_tru)}</td>
            <td style={{ textAlign: "right" }}>{vnd(g.bhxh)}</td><td style={{ textAlign: "right" }}><b>{vnd(g.thuc_nhan)}</b></td></tr>)}</tbody></table></div>}
      <p className="muted">Thang f KD Lẻ: f0–f4 = 0%, f5 = 0,5% … f19 = 4,7%, ≥1000% mốc = 5%; ngưỡng bậc tạm theo % mốc – HCNS nạp Bảng B.1 chính thức trước kỳ lương đầu. Thang đoàn f9–f0 theo bình quân LN 3 tháng / 30 triệu.</p>
    </>}

    {tab === "employees" && <>
      {canHR && <div className="panel"><h2>Danh sách nhân viên chính thức (bảng lương HCNS)</h2><p className="muted">Nạp mã NV / phòng / nhóm kinh doanh / chức vụ từ bảng lương HCNS đã đưa vào hệ thống (tháng 9/2026); ghép tài khoản theo họ tên, tạo tài khoản mới cho khối phải báo cáo ngày (mật khẩu ban đầu = mã NV). Nhân sự không còn trên bảng lương → ngưng hoạt động (không xóa).</p>
        <button className="act orange" onClick={() => post("/employees/import-master").then(() => api("/employees").then(setEmps))}>Nạp / cập nhật danh sách nhân viên</button>
        <button className="act red" onClick={() => { if (confirm("Đặt lại mật khẩu = mã NV cho TẤT CẢ tài khoản trong danh sách (trừ Chủ tịch/TGĐ/CNTT)? Dùng khi cấp tài khoản lần đầu.")) post("/employees/import-master?reset_passwords=true").then(() => api("/employees").then(setEmps)); }}>Nạp + đặt lại mật khẩu = mã NV</button></div>}
      {canHR && <div className="panel"><h2>Thêm hồ sơ</h2><div className="grid">
        <label>Họ tên<input value={fEmp.full_name} onChange={(e) => setFEmp({ ...fEmp, full_name: e.target.value })} /></label>
        <label>Phòng<select value={fEmp.department} onChange={(e) => setFEmp({ ...fEmp, department: e.target.value })}>{Object.entries(meta.departments).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Chức danh<select value={fEmp.position} onChange={(e) => setFEmp({ ...fEmp, position: e.target.value })}>{Object.entries(meta.positions).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Văn phòng<select value={fEmp.office} onChange={(e) => setFEmp({ ...fEmp, office: e.target.value })}>{Object.entries(meta.offices).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Hợp đồng<select value={fEmp.contract_type} onChange={(e) => setFEmp({ ...fEmp, contract_type: e.target.value })}><option value="hdld">HĐLĐ</option><option value="ctv">Cộng tác viên</option><option value="doi_tac">Đối tác</option></select></label>
        <label>Lương công việc (đ)<input type="number" value={fEmp.base_salary} onChange={(e) => setFEmp({ ...fEmp, base_salary: e.target.value })} /></label>
        {/* HS-9 · 17/10/2026 — SÁU Ô THÊM VÀO BIỂU TẠO. Trước vòng này biểu tạo có 6 ô còn biểu
            sửa có 14: HCNS tạo xong là phải bấm Sửa ngay để nhập tiếp, và bước thứ hai ấy thì ai
            cũng quên. Hai biểu cho cùng một hồ sơ thì phải hỏi cùng một bộ câu hỏi. */}
        <label>Mã nhân viên<input value={fEmp.code} placeholder="số trên bảng lương HCNS, vd 276"
          onChange={(e) => setFEmp({ ...fEmp, code: e.target.value })} /></label>
        <label>Ngày vào làm<input type="date" value={fEmp.start_date}
          onChange={(e) => setFEmp({ ...fEmp, start_date: e.target.value })} /></label>
        <label>Chức vụ bảng lương<input value={fEmp.title}
          onChange={(e) => setFEmp({ ...fEmp, title: e.target.value })} /></label>
        <label>Nhóm kinh doanh<input value={fEmp.sales_group}
          onChange={(e) => setFEmp({ ...fEmp, sales_group: e.target.value })} /></label>
        <label>Điện thoại<input value={fEmp.phone}
          onChange={(e) => setFEmp({ ...fEmp, phone: e.target.value })} /></label>
        <label>Thử việc<input type="checkbox" checked={!!fEmp.probation}
          onChange={(e) => setFEmp({ ...fEmp, probation: e.target.checked })} /></label>
      </div>
      {/* Mã để trống thì máy tự sinh NS### — nói thẳng ra, vì mã tự sinh KHÔNG khớp bảng lương
          HCNS và người nhập cần biết điều đó trước khi bấm, không phải sau. */}
      <p className="muted" style={{ fontSize: 12 }}>Để trống mã nhân viên thì hệ thống tự sinh mã
        dạng <b>NS001</b> — mã ấy <b>không khớp bảng lương HCNS</b>, nên nếu đã biết số trên bảng
        lương thì nhập vào đây.</p>
      <button className="act" disabled={!fEmp.full_name} onClick={() => post("/employees", { ...fEmp, base_salary: Number(fEmp.base_salary) || 0, start_date: fEmp.start_date || null }).then((r) => r && setFEmp({ ...fEmp, code: "", full_name: "", base_salary: "", start_date: "", title: "", phone: "" }))}>Tạo hồ sơ</button></div>}
      {canHR && khoa.length > 0 && <div className="panel wrap"><h2>Tài khoản đang bị khóa ({khoa.length})</h2>
        <p className="muted">Người không còn trên bảng lương thì không đăng nhập được nữa. Hồ sơ và tài khoản vẫn giữ để nhật ký nghiệp vụ và chứng từ cũ truy ra được người thực hiện. Khóa nhầm thì mở lại ở đây.</p>
        <table><thead><tr><th>Tài khoản</th><th>Họ tên</th><th>Mã NV</th><th>Vai trò</th><th></th></tr></thead>
          <tbody>{khoa.map((k) => <tr key={k.id}><td className="mono">{k.username}</td><td>{k.full_name}</td><td className="mono">{k.staff_code}</td><td>{k.role_name}</td>
            <td><button className="act" style={{ margin: 0 }} onClick={() => post(`/users/${k.id}`, { active: true }, "PUT").then(() => api("/users/khoa").then(setKhoa))}>Mở lại</button></td></tr>)}</tbody></table></div>}
      {sua && <SuaHoSo sua={sua} setSua={setSua} dc={dc} setDc={setDc} meta={meta} post={post} />}
      <div className="panel wrap"><table><thead><tr><th>Mã NV</th><th>Họ tên</th><th>Phòng</th><th>Nhóm</th><th>Chức vụ</th><th>VP</th><th>HĐ</th><th>Pháp nhân</th><th style={{ textAlign: "right" }}>Lương CV</th><th>Công việc chính</th><th>Ngày sinh</th><th>Điện thoại</th><th>Thẻ HDV</th><th>Trạng thái</th>{canHR && <th></th>}</tr></thead>
        <tbody>{emps.map((e) => <tr key={e.id} style={{ opacity: e.active ? 1 : 0.55 }}><td className="mono">{e.code}</td><td><b>{e.full_name}</b></td><td>{e.department_name}</td><td>{e.sales_group}</td><td>{e.title || e.position_name}</td><td>{e.office_name}</td><td>{e.contract_type === "hdld" ? "HĐLĐ" : e.contract_type === "ctv" ? "CTV" : "Đối tác"}</td>
          {/* Pháp nhân chủ quản của TỪNG nhân sự. Trước 09/9/2026 ô này chỉ có ở bảng hướng dẫn viên và
              bảng xe, nên pháp nhân của một tài xế không có cửa nào để HCNS tự sửa – muốn đổi thì phải
              nhờ người gọi thẳng vào máy chủ. Một con số mà người phụ trách không tự nhập được là một
              con số sẽ sai và ở yên đó.
              Pháp nhân này quyết định bút toán lương thuộc công ty nào khi hợp nhất, nên nó phải nằm
              ngay cạnh hồ sơ chứ không nằm ở một màn hình khác. */}
          <td>{canHR
            ? <select value={e.company_id || ""} onChange={(ev) => post(`/employees/${e.id}/company`, { company_id: ev.target.value ? Number(ev.target.value) : null })}>
                <option value="">– chưa gán –</option>
                {cos.filter((c) => c.active || c.id === e.company_id).map((c) => <option key={c.id} value={c.id}>{c.code}</option>)}
              </select>
            : (cos.find((c) => c.id === e.company_id)?.code || <Tag cls="warn">chưa gán</Tag>)}</td>
          <td style={{ textAlign: "right" }}>{e.base_salary ? vnd(e.base_salary) : ""}</td>
          <td className="muted" style={{ maxWidth: 340 }}>{e.duties}</td><td>{fmtD(e.birth_date)}</td><td className="mono">{e.phone}</td>
          <td>{e.department === "huong_dan" && <>{e.card_no} <span className="muted">hạn {fmtD(e.card_expiry)}</span> {e.guide_ok ? <Tag cls="ok">Đủ điều kiện</Tag> : <Tag cls="red">Cổng 13</Tag>}</>}</td><td>{e.probation && <Tag cls="warn">Thử việc 85%</Tag>}{e.active ? "" : <Tag cls="red">Nghỉ</Tag>}</td>
          {canHR && <td>{e.active
            ? <button className="act red" style={{ margin: 0 }} title="Ngưng hồ sơ (không xóa) – dùng khi trùng hồ sơ hoặc nghỉ việc" onClick={() => { if (confirm(`Ngưng hồ sơ ${e.code} – ${e.full_name}? Hồ sơ vẫn được giữ để tra cứu lịch sử.`)) post(`/employees/${e.id}`, { full_name: e.full_name, department: e.department, active: false }, "PUT"); }}>Ngưng</button>
            : <button className="act" style={{ margin: 0 }} onClick={() => post(`/employees/${e.id}`, { full_name: e.full_name, department: e.department, active: true }, "PUT")}>Mở lại</button>}
            {" "}<button className="act grey" style={{ margin: 0 }} title="Hồ sơ giấy tờ của người này" onClick={() => setTepNV(e.code)}>Giấy tờ</button>
            {" "}<button className="act" style={{ margin: 0 }} title="Sửa thông tin hồ sơ"
              onClick={() => { setDc({ tu_ngay: "", ly_do: "" }); setSua({ ...e, _goc: { department: e.department, position: e.position, office: e.office } }); }}>Sửa</button></td>}</tr>)}</tbody></table></div>
      {tepNV && <DinhKem doiTuong="nhan_su" doiTuongId={tepNV} loai="hop_dong"
        tieuDe={`Hồ sơ giấy tờ – ${tepNV}`}
        goi={"Hợp đồng lao động, phụ lục, quyết định bổ nhiệm, bằng cấp, thẻ HDV. Lưu theo mã nhân viên " +
             "trong nhóm 06_Nhan_su, giữ trong thời gian làm việc + 5 năm. Đây là dữ liệu cá nhân theo " +
             "Nghị định 13/2023 – chỉ HCNS, Ban TGĐ, Chủ tịch và Ban Kiểm soát đọc được."} />}
    </>}

    {tab === "visa" && <>
      {canDH && <div className="panel"><h2>Hồ sơ visa mới</h2><div className="grid">
        <label>Khách<input value={fVisa.customer_name} onChange={(e) => setFVisa({ ...fVisa, customer_name: e.target.value })} /></label>
        <label>Thị trường<input value={fVisa.market} onChange={(e) => setFVisa({ ...fVisa, market: e.target.value })} placeholder="Schengen, Anh, Úc…" /></label>
        <label>Cách xử lý<select value={fVisa.method} onChange={(e) => setFVisa({ ...fVisa, method: e.target.value })}><option value="tu_xu_ly">Tự xử lý (200.000)</option><option value="gui_doi_tac">Gửi đối tác (50.000)</option></select></label>
        <label>Người xử lý<select value={fVisa.handler_id} onChange={(e) => setFVisa({ ...fVisa, handler_id: e.target.value })}><option value="">–</option>{emps.filter((e) => e.department === "visa").map((e) => <option key={e.id} value={e.id}>{e.full_name}</option>)}</select></label>
        <label>Địa bàn<select value={fVisa.office} onChange={(e) => setFVisa({ ...fVisa, office: e.target.value })}><option value="hcm">HCM (chia đều)</option><option value="hanoi">Hà Nội (riêng)</option></select></label>
        <label>Doanh thu visa (đ)<input type="number" value={fVisa.revenue} onChange={(e) => setFVisa({ ...fVisa, revenue: e.target.value })} /></label>
        <label><input type="checkbox" checked={fVisa.alliance} onChange={(e) => setFVisa({ ...fVisa, alliance: e.target.checked })} /> Khách liên minh (+300.000)</label>
      </div><button className="act" disabled={!fVisa.customer_name || !fVisa.handler_id} onClick={() => post("/visa", { ...fVisa, handler_id: Number(fVisa.handler_id), revenue: Number(fVisa.revenue) || 0 }).then((r) => r && setFVisa({ ...fVisa, customer_name: "", market: "", revenue: "" }))}>Tạo hồ sơ</button></div>}
      <div className="panel wrap"><table><thead><tr><th>Mã</th><th>Khách</th><th>Thị trường</th><th>Cách</th><th>Người xử lý</th><th>Địa bàn</th><th style={{ textAlign: "right" }}>DT visa</th><th>Trạng thái</th><th>Hoàn thành</th>{canDH && <th></th>}</tr></thead>
        <tbody>{visa.map((f) => <tr key={f.id}><td className="mono">{f.code}</td><td>{f.customer_name}{f.alliance && <Tag cls="navy">liên minh</Tag>}</td><td>{f.market}</td><td>{f.method === "tu_xu_ly" ? "Tự xử lý" : "Gửi đối tác"}</td><td>{f.handler}</td><td>{f.office === "hanoi" ? "Hà Nội" : "HCM"}</td><td style={{ textAlign: "right" }}>{vnd(f.revenue)}</td>
          <td>{f.status === "hoan_thanh" ? <Tag cls="ok">Hoàn thành</Tag> : <Tag cls="warn">Đang làm</Tag>}</td><td>{fmtD(f.completed_at)}</td>{canDH && <td>{f.status !== "hoan_thanh" && <button className="act teal" style={{ margin: 0 }} onClick={() => post(`/visa/${f.id}/complete`)}>Hoàn thành</button>}</td>}</tr>)}</tbody></table></div>
    </>}

    {tab === "guides" && <>
      {canDH && <div className="panel"><h2>Văn bản phân công HDV (cổng 13 – kiểm tra thẻ, hội viên, hợp đồng CTV)</h2><div className="grid">
        <label>Tour<select value={fAsg.tour_id} onChange={(e) => setFAsg({ ...fAsg, tour_id: e.target.value })}><option value="">–</option>{tours.map((t) => <option key={t.id} value={t.id}>{t.code} · {t.name}</option>)}</select></label>
        <label>HDV<select value={fAsg.guide_id} onChange={(e) => setFAsg({ ...fAsg, guide_id: e.target.value })}><option value="">–</option>{guides.map((g) => <option key={g.id} value={g.id}>{g.full_name} {g.guide_ok ? "" : "(không đủ điều kiện)"}</option>)}</select></label>
        <label>Tuyến (bảng giá HDV)<select value={fAsg.rate_id} onChange={(e) => { const r = grates.find((x) => String(x.id) === e.target.value); setFAsg({ ...fAsg, rate_id: e.target.value, rate_per_day: r ? String(r.rate_per_day) : fAsg.rate_per_day, days: r ? String(Math.round(r.days)) : fAsg.days }); }}><option value="">– ngoài bảng giá (nhập tay) –</option>{grates.filter((r) => r.status === "active").map((r) => <option key={r.id} value={r.id}>{r.route} · {vnd(r.rate_per_day)}/ngày · {r.days} ngày</option>)}</select></label>
        <label>Số ngày<input type="number" value={fAsg.days} onChange={(e) => setFAsg({ ...fAsg, days: e.target.value })} /></label>
        <label>Đơn giá/ngày<input type="number" value={fAsg.rate_per_day} disabled={!!fAsg.rate_id} onChange={(e) => setFAsg({ ...fAsg, rate_per_day: e.target.value })} /></label>
        <label><input type="checkbox" checked={fAsg.holiday} onChange={(e) => setFAsg({ ...fAsg, holiday: e.target.checked })} /> Lễ Tết ×2</label>
      </div><button className="act" disabled={!fAsg.tour_id || !fAsg.guide_id || (!fAsg.rate_id && !fAsg.rate_per_day)} onClick={() => post("/guide-assignments", { tour_id: Number(fAsg.tour_id), guide_id: Number(fAsg.guide_id), days: Number(fAsg.days) || 0, rate_per_day: Number(fAsg.rate_per_day) || 0, rate_id: fAsg.rate_id ? Number(fAsg.rate_id) : null, holiday: fAsg.holiday })}>Phân công</button></div>}
      <div className="panel wrap"><h2>Pháp nhân chủ quản của hướng dẫn viên</h2>
        <table><thead><tr><th>HDV</th><th>Loại hợp đồng</th><th>Thẻ</th><th>Pháp nhân chủ quản</th>{["cntt", "ketoan", "tgd", "chutich", "hcns"].includes(role) && <th></th>}</tr></thead>
          <tbody>{guides.length ? guides.map((g) => <tr key={g.id}><td><b>{g.full_name}</b></td><td>{g.contract_type === "ctv" ? "Cộng tác viên" : g.contract_type === "doi_tac" ? "Đối tác" : "Hợp đồng lao động"}</td><td className="muted">{g.card_no || "–"}</td>
            <td>{cos.find((c) => c.id === g.company_id)?.name || <Tag cls="warn">chưa gán</Tag>}</td>
            {["cntt", "ketoan", "tgd", "chutich", "hcns"].includes(role) && <td>
              <select value={g.company_id || ""} onChange={(e) => post(`/employees/${g.id}/company`, { company_id: e.target.value ? Number(e.target.value) : null })}>
                <option value="">– chưa gán –</option>{cos.filter((c) => c.active || c.id === g.company_id).map((c) => <option key={c.id} value={c.id}>{c.code} · {c.name}{c.active ? "" : " (tạm ngưng)"}</option>)}
              </select></td>}</tr>) : <tr><td colSpan={5} className="muted">Chưa có hướng dẫn viên trong hồ sơ nhân sự.</td></tr>}</tbody></table>
        <p className="muted">Hướng dẫn viên mặc định thuộc Công ty Cổ phần Du lịch Vietourist (công ty mẹ), kể cả khi ký cộng tác viên. Đổi được từng người nếu sau này ký qua pháp nhân khác – thù lao do pháp nhân nào chi trả sẽ quyết định bên ghi nhận chi phí khi hợp nhất.</p></div>
      <div className="panel wrap"><table><thead><tr><th>Tour</th><th>HDV</th><th>Ngày × đơn giá</th><th style={{ textAlign: "right" }}>Thù lao</th><th>Trạng thái</th><th>Báo cáo tour</th><th>Hoàn ứng</th><th>Phân công</th>{canDH && <th></th>}</tr></thead>
        <tbody>{asg.map((a) => <tr key={a.id}><td><b>{a.tour_code}</b><div className="muted">{a.tour_name}</div></td><td>{a.guide}</td><td>{a.days} × {vnd(a.rate_per_day)}{a.holiday && " ×2"}</td><td style={{ textAlign: "right" }}>{vnd(a.amount)}</td>
          <td>{a.status === "da_xac_nhan" ? <Tag cls="ok">HDV đã xác nhận</Tag> : a.status === "huy" ? <Tag cls="red">Hủy</Tag> : <Tag cls="warn">Chờ xác nhận 24h</Tag>}</td><td>{a.report_submitted ? "✔" : <Tag cls="warn">thiếu → treo</Tag>}</td><td>{a.advance_settled ? "✔" : <Tag cls="warn">chưa → treo</Tag>}</td><td className="muted">{a.assigned_by} {fmtDT(a.assigned_at)}</td>
          {canDH && <td>{a.status === "cho_xac_nhan" && <button className="act teal" style={{ margin: 0 }} onClick={() => post(`/guide-assignments/${a.id}/update`, { confirm: true })}>HDV xác nhận</button>}{!a.report_submitted && <button className="act grey" style={{ margin: "0 0 0 4px" }} onClick={() => post(`/guide-assignments/${a.id}/update`, { report_submitted: true })}>Đã nộp báo cáo</button>}</td>}</tr>)}</tbody></table></div>
      <h2>Bảng giá thù lao HDV theo tuyến (đồng/ngày, lễ Tết ×2) – {tenKy(grates[0]?.ten_vai_ky) || "người ký theo luật"} ký, hiệu lực theo ngày</h2>
      {["hcns", "cntt", "tp_dh"].includes(role) && <div className="panel"><div className="grid">
        <label>Tuyến<input value={fGrate.route} onChange={(e) => setFGrate({ ...fGrate, route: e.target.value })} /></label>
        <label>Số ngày<input type="number" step="0.5" value={fGrate.days} onChange={(e) => setFGrate({ ...fGrate, days: e.target.value })} /></label>
        <label>Đơn giá mới/ngày<input type="number" value={fGrate.rate_per_day} onChange={(e) => setFGrate({ ...fGrate, rate_per_day: e.target.value })} /></label>
        <label>Đơn giá cũ (đối chiếu)<input type="number" value={fGrate.old_rate_per_day} onChange={(e) => setFGrate({ ...fGrate, old_rate_per_day: e.target.value })} /></label>
        <label>Hiệu lực từ<input type="date" value={fGrate.effective_from} onChange={(e) => setFGrate({ ...fGrate, effective_from: e.target.value })} /></label>
      </div><button className="act orange" disabled={!fGrate.route || !fGrate.rate_per_day} onClick={() => post("/guide-rates", { ...fGrate, days: Number(fGrate.days) || 0, rate_per_day: Number(fGrate.rate_per_day), old_rate_per_day: Number(fGrate.old_rate_per_day) || 0 }).then((r) => r && setFGrate({ ...fGrate, route: "", days: "", rate_per_day: "", old_rate_per_day: "" }))}>Trình {tenKy(grates[0]?.ten_vai_ky) || "người ký theo luật"}</button></div>}
      <div className="panel wrap"><table><thead><tr><th>Tuyến</th><th>Số ngày</th><th style={{ textAlign: "right" }}>Giá cũ</th><th style={{ textAlign: "right" }}>Giá mới/ngày</th><th style={{ textAlign: "right" }}>Chênh lệch</th><th>Hiệu lực</th><th>Trạng thái</th><th>Ghi chú</th>{["chutich", "tgd"].includes(role) && <th></th>}</tr></thead>
        <tbody>{grates.map((r) => <tr key={r.id} style={{ opacity: r.status === "rejected" ? 0.5 : 1 }}><td><b>{r.route}</b></td><td>{r.days}</td><td style={{ textAlign: "right" }}>{vnd(r.old_rate_per_day)}</td><td style={{ textAlign: "right" }}><b>{vnd(r.rate_per_day)}</b></td><td style={{ textAlign: "right" }}>{vnd(r.rate_per_day - r.old_rate_per_day)}</td><td>{fmtD(r.effective_from)}</td>
          <td>{r.status === "active" ? <Tag cls="ok">Hiệu lực</Tag> : r.status === "pending" ? <KyO ky={r.chu_ky} /> : <Tag>Hết hiệu lực</Tag>}</td><td className="muted">{r.note}</td>
          {["chutich", "tgd"].includes(role) && <td>{r.status === "pending" && <button className="act" style={{ margin: 0 }} onClick={() => post(`/guide-rates/${r.id}/sign`)}>Ký</button>}</td>}</tr>)}</tbody></table></div>
    </>}

    {tab === "fleet" && <>
      {fleet && <div className="kpis"><div className="kpi"><b>{vnd(fleet.total_revenue)}</b><span>Doanh thu nội bộ Đội xe {period}</span></div>{fleet.rows.map((r: any) => <div className="kpi" key={r.vehicle}><b>{r.days} ngày</b><span>{r.vehicle} · {r.driver} · {r.trips} chuyến · CTP {vnd(r.driver_allowance)}</span></div>)}</div>}
      {/* Mẫu lập lệnh ĐÃ CHUYỂN sang /lenh-dieu-xe (09/9/2026). Không phải dọn cho gọn – mẫu cũ ở đây
          không dùng được nữa, và nó hỏng theo kiểu im lặng:

            · Tham số xe_nguoi_lap_lenh chỉ định Giám đốc điều hành đội xe là người DUY NHẤT được chốt
              lệnh (chỉ đạo Chủ tịch 07/9/2026), nên POST /dispatch trả 403 cho cả ba vai trò từng thấy
              mẫu này. Một mẫu chỉ để nhận 403 thì tệ hơn là không có mẫu.
            · Mẫu cũ không gửi so_khach và km_du_kien, nên bộ gợi ý chấm điểm cho một chuyến 0 khách 0 km
              rồi lấy kết quả ấy quyết định có bắt giải trình hay không.
            · Mẫu cũ không có ô ly_do_khac_goi_y, nên khi máy chủ trả 422 đòi lý do thì không có chỗ để
              điền – cụt đường thật, không phải bất tiện.

          Ba vai trò cũ (nv_dh, tp_dh, cntt) đều nhìn thấy /lenh-dieu-xe, nên không ai mất đường. */}
      <div className="panel"><h2>Lệnh điều xe</h2>
        <p className="muted">Lập lệnh nay ở màn hình <b>Lệnh điều xe</b> (nhóm Vận tải &amp; Hướng dẫn viên) –
        nơi có sẵn bảng gợi ý xe, ô số khách và km dự kiến, và ô ghi lý do khi chốt khác gợi ý. Bảng dưới
        đây vẫn là nơi xác nhận và đóng lệnh.</p></div>
      <div className="panel wrap"><table><thead><tr><th>Tour</th><th>Xe</th><th>Tài xế</th><th>Tuyến</th><th>Thời gian</th><th style={{ textAlign: "right" }}>Giá nội bộ</th><th>Pháp nhân sở hữu xe</th><th>Trạng thái</th><th>Sự cố</th>{["cntt", "tp_dh", "nv_dh", "hcns"].includes(role) && <th></th>}</tr></thead>
        <tbody>{disp.map((d) => <tr key={d.id}><td><b>{d.tour_code}</b></td><td>{d.vehicle}</td><td>{d.driver}</td><td className="muted">{d.route}</td><td>{fmtD(d.date_from)} → {fmtD(d.date_to)} ({d.days} ngày)</td><td style={{ textAlign: "right" }}>{vnd(d.internal_price)}</td>
          <td>{d.company ? <>{d.company_code} {d.noi_bo && <Tag cls="navy">nội bộ</Tag>}</> : <Tag cls="warn">chưa gán</Tag>}</td>
          <td>{d.status === "hoan_thanh" ? <Tag cls="ok">Hoàn thành</Tag> : d.status === "da_xac_nhan" ? <Tag cls="navy">Đã xác nhận</Tag> : d.status === "huy" ? <Tag cls="red">Hủy</Tag> : <Tag cls="warn">Chờ xác nhận 4h</Tag>}</td><td className="muted">{d.incident_note}</td>
          {["cntt", "tp_dh", "nv_dh", "hcns"].includes(role) && <td>{d.status === "cho_xac_nhan" && <button className="act teal" style={{ margin: 0 }} onClick={() => post(`/dispatch/${d.id}/update`, { status: "da_xac_nhan" })}>Xác nhận</button>}{d.status === "da_xac_nhan" && <button className="act" style={{ margin: 0 }} onClick={() => post(`/dispatch/${d.id}/update`, { status: "hoan_thanh" })}>Hoàn thành</button>}</td>}</tr>)}</tbody></table></div>
      <div className="panel wrap"><h2>Hồ sơ xe & pháp nhân sở hữu</h2>
        <table><thead><tr><th>Biển số</th><th className="num">Chỗ</th><th>Loại</th><th>Tài xế đứng lái</th><th>Pháp nhân sở hữu</th><th>Trạng thái</th>{["cntt", "ketoan", "tgd", "chutich", "hcns", "tp_dh"].includes(role) && <th></th>}</tr></thead>
          <tbody>{veh.map((v) => <tr key={v.id} style={{ opacity: v.active ? 1 : 0.55 }}><td><b>{v.plate}</b></td><td className="num">{v.seats}</td><td>{v.kind === "hop_tac" ? "Xe hợp tác (thuê ngoài)" : "Xe nội bộ"}</td>
            <td>{["cntt", "ketoan", "tgd", "chutich", "hcns", "tp_dh"].includes(role)
              ? <select value={v.driver_id || ""} onChange={(e) => post(`/vehicles/${v.id}`, { driver_id: e.target.value ? Number(e.target.value) : null }, "PUT")}>
                  <option value="">– chưa gán –</option>{emps.filter((x) => x.active && (x.department === "doi_xe" || x.position === "tai_xe" || x.id === v.driver_id)).map((x) => <option key={x.id} value={x.id}>{x.code} · {x.full_name}</option>)}
                </select>
              : (v.driver || <Tag cls="warn">chưa gán</Tag>)}</td>
            <td>{v.company ? v.company : <Tag cls="warn">chưa gán</Tag>}</td>
            <td>{v.active ? <Tag cls="ok">Đang khai thác</Tag> : <Tag cls="red">Ngưng khai thác</Tag>}</td>
            {["cntt", "ketoan", "tgd", "chutich", "hcns", "tp_dh"].includes(role) && <td>
              <select value={v.company_id || ""} onChange={(e) => post(`/vehicles/${v.id}/company`, { company_id: e.target.value ? Number(e.target.value) : null })}>
                <option value="">– chưa gán –</option>{cos.filter((c) => c.active || c.id === v.company_id).map((c) => <option key={c.id} value={c.id}>{c.code} · {c.name}{c.active ? "" : " (tạm ngưng)"}</option>)}
              </select>
              <button className={v.active ? "act red" : "act"} style={{ margin: "0 0 0 6px" }} onClick={() => { if (!v.active || confirm(`Ngưng khai thác xe ${v.plate}? Xe vẫn được giữ để tra cứu lệnh điều xe cũ.`)) post(`/vehicles/${v.id}`, { active: !v.active }, "PUT"); }}>{v.active ? "Ngưng" : "Mở lại"}</button>
            </td>}</tr>)}</tbody></table>
        <p className="muted">Pháp nhân sở hữu lấy theo <b>giấy đăng ký xe</b>, không suy từ việc xe là xe nội bộ hay thuê ngoài: hiện phần lớn đội xe đứng tên Công ty CP Vietourist Holdings, chỉ một xe đứng tên Vận tải Vietrip. <b>Tài xế hưởng lương ở công ty mẹ</b> dù xe đứng tên pháp nhân nào. Xe thuộc pháp nhân trong phạm vi hợp nhất (mẹ, con, chi nhánh) thì lệnh điều xe là <b>giao dịch nội bộ</b> – phải nhận diện để loại trừ khi lập báo cáo hợp nhất. Xe hợp tác là xe thuê ngoài, không gán pháp nhân trong tập đoàn.</p></div>
      <h2>Bảng giá xe nội bộ theo tuyến ({tenKy(rates[0]?.ten_vai_ky) || "người ký theo luật"} duyệt, hiệu lực theo ngày)</h2>
      {["cntt", "hcns", "tp_dh"].includes(role) && <div className="panel"><div className="grid">
        <label>Tuyến<input value={fRate.route} onChange={(e) => setFRate({ ...fRate, route: e.target.value })} /></label>
        <label>Số ngày<input type="number" value={fRate.days} onChange={(e) => setFRate({ ...fRate, days: e.target.value })} /></label>
        <label>Giá xe Vietrip – VTD<input type="number" value={fRate.internal_price} onChange={(e) => setFRate({ ...fRate, internal_price: e.target.value })} /></label>
        <label>Giá xe hợp tác<input type="number" value={fRate.partner_price} onChange={(e) => setFRate({ ...fRate, partner_price: e.target.value })} /></label>
        <label>Hiệu lực từ<input type="date" value={fRate.effective_from} onChange={(e) => setFRate({ ...fRate, effective_from: e.target.value })} /></label>
      </div><button className="act orange" disabled={!fRate.route || !fRate.internal_price} onClick={() => post("/vehicle-rates", { ...fRate, days: Number(fRate.days) || 0, internal_price: Number(fRate.internal_price), partner_price: Number(fRate.partner_price) || 0 }).then((r) => r && setFRate({ ...fRate, route: "", days: "", internal_price: "", partner_price: "" }))}>Trình {tenKy(rates[0]?.ten_vai_ky) || "người ký theo luật"}</button></div>}
      <div className="panel wrap"><table><thead><tr><th>Tuyến</th><th>Ngày</th><th style={{ textAlign: "right" }}>Xe Vietrip – VTD</th><th style={{ textAlign: "right" }}>Xe hợp tác</th><th>Hiệu lực</th><th>Trạng thái</th><th>Chữ ký</th>{["chutich", "tgd"].includes(role) && <th></th>}</tr></thead>
        <tbody>{rates.map((r) => <tr key={r.id} style={{ opacity: r.status === "rejected" ? 0.5 : 1 }}><td><b>{r.route}</b></td><td>{r.days || "–"}</td><td style={{ textAlign: "right" }}>{vnd(r.internal_price)}</td><td style={{ textAlign: "right" }}>{r.partner_price ? vnd(r.partner_price) : "–"}</td><td>{fmtD(r.effective_from)}</td>
          <td><Tag cls={r.status === "active" ? "ok" : r.status === "pending" ? "warn" : ""}>{r.status === "active" ? "Hiệu lực" : r.status === "pending" ? "Chờ ký" : "Hết hiệu lực"}</Tag></td><td><KyO ky={r.chu_ky} /></td>
          {["chutich", "tgd"].includes(role) && <td>{r.status === "pending" && <button className="act" style={{ margin: 0 }} onClick={() => post(`/vehicle-rates/${r.id}/sign`)}>Ký</button>}</td>}</tr>)}</tbody></table></div>
      <p className="muted">Bảng giá 6/5/2026 (anh Tuấn cung cấp 05/9/2026); cột xe hợp tác áp dụng từ 5/8/2026 cho 50E-955.31, 50H-496.23. Đội xe Vietrip hạch toán riêng như trung tâm lợi nhuận; lệnh điều xe lấy giá theo tuyến và loại xe; tuyến không có trong bảng → giá theo ngày ở hồ sơ xe. Quyết toán tháng do CNTT/AI.</p>
    </>}

    {tab === "incidents" && <>
      <div className="panel"><BangChamDiem /></div>
      {incMeta && <div className="panel"><h2>Bảng phân mức sự vụ (áp dụng từ 05/9/2026 – Chủ tịch + TGĐ ban hành)</h2>
        <table><thead><tr><th>Mức</th><th>Hành vi điển hình</th><th>Chế tài</th><th>Thẩm quyền duyệt</th></tr></thead><tbody>
          {Object.entries(incMeta.levels).map(([k, v]: any) => <tr key={k}><td><Tag cls={k === "3" ? "red" : k === "2" ? "warn" : ""}>{v.ten}</Tag></td><td>{v.mo_ta}</td><td>{v.che_tai}</td><td className="muted">{v.duyet.length ? v.duyet.join(", ") : "không cần duyệt"}</td></tr>)}</tbody></table>
        <p className="muted">{incMeta.quy_trinh}. Người bị lập biên bản được ghi ý kiến; khiếu nại trong 3 ngày làm việc → chế tài treo tới khi cấp trên một bậc kết luận.</p></div>}
      {["hcns", "tp_dh", "gd_kd", "ptgd_doan", "tgd", "cntt", "tp"].includes(role) && <div className="panel"><h2>Lập biên bản sự vụ</h2><div className="grid">
        <label>Nhân sự<select value={fInc.employee_id} onChange={(e) => setFInc({ ...fInc, employee_id: e.target.value })}><option value="">–</option>{emps.map((e) => <option key={e.id} value={e.id}>{e.code} · {e.full_name}</option>)}</select></label>
        <label>Mức<select value={fInc.level} onChange={(e) => setFInc({ ...fInc, level: e.target.value })}>{[1, 2, 3].map((l) => <option key={l} value={l}>Mức {l}{l === 2 ? " (−1 triệu hoa hồng)" : l === 3 ? " (mất hoa hồng booking, kỷ luật)" : " (nhắc nhở)"}</option>)}</select></label>
        <label>Tour liên quan<select value={fInc.tour_id || ""} onChange={(e) => setFInc({ ...fInc, tour_id: e.target.value })}><option value="">–</option>{tours.map((t) => <option key={t.id} value={t.id}>{t.code}</option>)}</select></label>
        <label>Ngày<input type="date" value={fInc.occurred_on} onChange={(e) => setFInc({ ...fInc, occurred_on: e.target.value })} /></label>
        <label>Mô tả<input value={fInc.description} onChange={(e) => setFInc({ ...fInc, description: e.target.value })} /></label>
      </div><button className="act orange" disabled={!fInc.employee_id || !fInc.description} onClick={() => post("/incidents", { employee_id: Number(fInc.employee_id), level: Number(fInc.level), description: fInc.description, occurred_on: fInc.occurred_on, tour_id: fInc.tour_id ? Number(fInc.tour_id) : null }).then((r) => r && setFInc({ ...fInc, description: "" }))}>Lập biên bản</button></div>}
      <div className="panel wrap"><table><thead><tr><th>Ngày</th><th>Nhân sự</th><th>Mức</th><th>Mô tả</th><th>Lập / HCNS / duyệt</th><th>Trạng thái</th><th>Ý kiến – khiếu nại</th><th></th></tr></thead>
        <tbody>{inc.length ? inc.map((i) => <tr key={i.id}><td>{fmtD(i.occurred_on)}</td><td>{i.employee}</td><td><Tag cls={i.level >= 3 ? "red" : i.level === 2 ? "warn" : ""}>Mức {i.level}</Tag></td><td>{i.description}</td>
          <td className="muted">{i.created_by}{i.confirmed_by && ` / ${i.confirmed_by}`}{i.approved_by && ` / ${i.approved_by}`}</td>
          <td>{i.status === "hieu_luc" ? <Tag cls="ok">{i.status_name}</Tag> : i.status === "huy" ? <Tag>{i.status_name}</Tag> : i.status === "khieu_nai" ? <Tag cls="red">{i.status_name}</Tag> : <Tag cls="warn">{i.status_name}{i.status === "cho_khieu_nai" && i.appeal_deadline ? ` (đến ${fmtD(i.appeal_deadline)})` : ""}</Tag>}</td>
          <td className="muted">{i.employee_opinion && <div>Ý kiến: {i.employee_opinion}</div>}{i.appeal_note && <div>Khiếu nại: {i.appeal_note}</div>}{i.appeal_result && <div>Kết luận: {i.appeal_result}</div>}</td>
          <td style={{ whiteSpace: "nowrap" }}>
            {role === "hcns" && i.status === "lap" && <button className="act teal" style={{ margin: 0 }} onClick={() => post(`/incidents/${i.id}/confirm`)}>HCNS xác nhận</button>}
            {["gd_kd", "ptgd_doan", "tgd", "chutich"].includes(role) && i.status === "hcns_xac_nhan" && <button className="act" style={{ margin: 0 }} onClick={() => post(`/incidents/${i.id}/approve`)}>Duyệt</button>}
            {["gd_kd", "ptgd_doan", "tgd", "chutich"].includes(role) && ["khieu_nai", "cho_khieu_nai"].includes(i.status) && <><button className="act grey" style={{ margin: "0 4px 0 0" }} onClick={() => { const n = prompt("Kết luận (giữ nguyên chế tài):"); if (n !== null) post(`/incidents/${i.id}/resolve`, { accept: false, result: n }); }}>Giữ nguyên</button>{i.status === "khieu_nai" && <button className="act grey" style={{ margin: 0 }} onClick={() => { const n = prompt("Kết luận (chấp nhận khiếu nại, hủy chế tài):"); if (n !== null) post(`/incidents/${i.id}/resolve`, { accept: true, result: n }); }}>Chấp nhận KN</button>}</>}
            {i.is_mine && ["lap", "hcns_xac_nhan", "cho_khieu_nai"].includes(i.status) && <button className="act orange" style={{ margin: "0 0 0 4px" }} onClick={() => { const o = prompt("Ý kiến của anh/chị về biên bản:") || ""; const a = prompt("Khiếu nại (để trống nếu không):") || ""; if (o || a) post(`/incidents/${i.id}/opinion`, { opinion: o, appeal: a }); }}>Ghi ý kiến / khiếu nại</button>}
          </td></tr>) : <tr><td colSpan={8} className="muted">Chưa có sự vụ.</td></tr>}</tbody></table></div>
      {["hcns", "cntt"].includes(role) && <button className="act grey" onClick={() => post("/incidents/finalize-expired")}>Chốt hiệu lực sự vụ hết hạn khiếu nại</button>}
    </>}
  </>);
}


/** BIỂU SỬA HỒ SƠ NHÂN SỰ — 12/10/2026.
 *
 *  BA ĐIỀU ĐÁNG GHI, vì cả ba đều là chỗ dễ làm sai mà không lộ ra:
 *
 *  (1) GỬI PHIÊN BẢN. `update_employee` gọi `kiem_phien_ban` từ đợt VPM-8, nhưng cửa đọc trước
 *      nay không trả số phiên bản ra, nên không màn hình nào gửi lại được và phép kiểm luôn rơi
 *      vào nhánh "chưa gửi thì cho qua" — hàng rào chống hai người sửa đè nhau có mà chưa chạy
 *      ngày nào. Biểu này gửi, nên hai người HCNS mở cùng một hồ sơ thì người lưu sau bị chặn và
 *      đọc được bản của người kia, thay vì lặng lẽ xoá công của họ.
 *
 *  (2) ĐIỀU CHUYỂN PHẢI CÓ NGÀY VÀ LÝ DO. Máy chủ coi đổi phòng / chức danh / văn phòng là một
 *      lần ĐIỀU CHUYỂN và tự ghi vào lịch sử tổ chức; để trống ngày thì nó lấy HÔM NAY. Một điều
 *      chuyển có hiệu lực lùi mà ghi ngày hôm nay là ghi sai lịch sử, và cái sai ấy không bao giờ
 *      tự lộ. Nên biểu hiện hai ô ấy ra NGAY KHI phát hiện một trong ba trường đổi, và không cho
 *      lưu khi thiếu lý do.
 *
 *  (3) Ô NGÀY RỖNG GỬI LÀ `null`, KHÔNG PHẢI CHUỖI RỖNG — máy chủ nhận `date | None`, chuỗi rỗng
 *      là 422. Và trường nào không gửi thì máy chủ giữ nguyên (`exclude_unset`), nên biểu thiếu
 *      một trường sẽ không xoá mất dữ liệu đã nạp.
 */
function SuaHoSo({ sua, setSua, dc, setDc, meta, post }: any) {
  const d = (k: string, v: any) => setSua({ ...sua, [k]: v });
  const doiToChuc = !!sua._goc && (sua.department !== sua._goc.department
    || sua.position !== sua._goc.position || sua.office !== sua._goc.office);
  const thieuLyDo = doiToChuc && !String(dc.ly_do || "").trim();

  const luu = () => {
    const g: any = {
      phien_ban: sua.phien_ban,
      full_name: sua.full_name, department: sua.department, position: sua.position,
      office: sua.office, contract_type: sua.contract_type,
      title: sua.title || "", duties: sua.duties || "", sales_group: sua.sales_group || "",
      phone: sua.phone || "", probation: !!sua.probation,
      card_no: sua.card_no || "", card_type: sua.card_type || "",
      base_salary: sua.base_salary === "" || sua.base_salary === null || sua.base_salary === undefined
        ? null : Number(sua.base_salary),
    };
    if (sua.birth_date) g.birth_date = sua.birth_date;
    if (sua.card_expiry) g.card_expiry = sua.card_expiry;
    if (doiToChuc) { g.dieu_chuyen_tu_ngay = dc.tu_ngay || null; g.dieu_chuyen_ly_do = dc.ly_do; }
    post(`/employees/${sua.id}`, g, "PUT").then((r: any) => { if (r) setSua(null); });
  };

  return (
    <div className="panel">
      <h2>Sửa hồ sơ {sua.code} – {sua.full_name}</h2>
      <p className="muted">Trường nào để trống thì giữ nguyên giá trị đang có. Mã nhân viên không
        sửa được ở đây: nó là khoá của mọi chứng từ cũ.</p>
      <div className="grid">
        <label>Họ tên<input value={sua.full_name || ""} onChange={(e) => d("full_name", e.target.value)} /></label>
        <label>Phòng<select value={sua.department || ""} onChange={(e) => d("department", e.target.value)}>
          {Object.entries(meta.departments).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Chức danh<select value={sua.position || ""} onChange={(e) => d("position", e.target.value)}>
          {Object.entries(meta.positions).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Văn phòng<select value={sua.office || ""} onChange={(e) => d("office", e.target.value)}>
          {Object.entries(meta.offices).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Hợp đồng<select value={sua.contract_type || "hdld"} onChange={(e) => d("contract_type", e.target.value)}>
          <option value="hdld">HĐLĐ</option><option value="ctv">Cộng tác viên</option><option value="doi_tac">Đối tác</option></select></label>
        <label>Chức vụ hiển thị<input value={sua.title || ""} onChange={(e) => d("title", e.target.value)} /></label>
        <label>Nhóm kinh doanh<input value={sua.sales_group || ""} onChange={(e) => d("sales_group", e.target.value)} /></label>
        <label>Lương công việc (đ)<input type="number" value={sua.base_salary ?? ""} onChange={(e) => d("base_salary", e.target.value)} /></label>
        {/* HS-11 · 17/10/2026 — hai ô này vẫn ở đây, nhưng nay rơi vào HỒ SƠ CÁ NHÂN. Trước đó
            cùng một người có thể mang hai ngày sinh: một ở bảng nhân sự, một ở màn Hợp đồng lao
            động, và không ai thấy vì cả hai ô đều mang nhãn «Ngày sinh». */}
        <label>Ngày sinh<input type="date" value={sua.birth_date || ""} onChange={(e) => d("birth_date", e.target.value)} /></label>
        <label>Điện thoại<input value={sua.phone || ""} onChange={(e) => d("phone", e.target.value)} /></label>
        <p className="muted" style={{ gridColumn: "1 / -1", margin: 0 }}>Ngày sinh và điện thoại
          lưu vào <b>hồ sơ cá nhân</b> (màn Hợp đồng lao động), không lưu riêng ở bảng nhân sự —
          một người chỉ có một ngày sinh.</p>
        {/* HS-9 · 17/10/2026 — NGÀY VÀO LÀM: trường này trước nay KHÔNG CÓ Ô NÀO, cả ở biểu tạo
            lẫn biểu sửa, nên chỉ nạp được qua tệp bảng lương. Mà thâm niên, phép năm, BHXH và
            thuế đều đọc đúng nó. Một người tuyển giữa kỳ thì không ai gõ được ngày vào của họ. */}
        
        <label>Ngày vào làm<input type="date" value={sua.start_date || ""} onChange={(e) => d("start_date", e.target.value)} /></label>
        <label>Hạn mức tạm ứng (đ)<input type="number" value={sua.advance_limit ?? ""} onChange={(e) => d("advance_limit", e.target.value)} /></label>
        <label>Thử việc<input type="checkbox" checked={!!sua.probation} onChange={(e) => d("probation", e.target.checked)} /></label>
        <label>Đoàn viên tổ chức<input type="checkbox" checked={!!sua.member_org} onChange={(e) => d("member_org", e.target.checked)} /></label>
        <label>Có hợp đồng CTV<input type="checkbox" checked={!!sua.ctv_contract} onChange={(e) => d("ctv_contract", e.target.checked)} /></label>
        {sua.department === "huong_dan" && <>
          <label>Số thẻ HDV<input value={sua.card_no || ""} onChange={(e) => d("card_no", e.target.value)} /></label>
          <label>Hạn thẻ<input type="date" value={sua.card_expiry || ""} onChange={(e) => d("card_expiry", e.target.value)} /></label>
        </>}
      </div>
      <label style={{ display: "block", marginTop: 8 }}>Công việc chính
        <textarea rows={2} style={{ width: "100%" }} value={sua.duties || ""} onChange={(e) => d("duties", e.target.value)} /></label>
      <label style={{ display: "block", marginTop: 6 }}>
        <input type="checkbox" checked={!!sua.probation} onChange={(e) => d("probation", e.target.checked)} /> Đang thử việc (85%)
      </label>

      {doiToChuc && <div className="gate" style={{ marginTop: 10 }}>
        <b>Lần sửa này là một ĐIỀU CHUYỂN</b> — phòng, chức danh hoặc văn phòng đã đổi, nên hệ
        thống sẽ ghi một chặng mới vào lịch sử tổ chức của người này.
        <div className="grid" style={{ marginTop: 6 }}>
          <label>Có hiệu lực từ ngày<input type="date" value={dc.tu_ngay}
            onChange={(e) => setDc({ ...dc, tu_ngay: e.target.value })} /></label>
          <label>Lý do điều chuyển<input value={dc.ly_do}
            onChange={(e) => setDc({ ...dc, ly_do: e.target.value })} /></label>
        </div>
        <p className="muted" style={{ marginTop: 4 }}>Để trống ngày thì hệ thống ghi là <b>hôm
          nay</b>. Quyết định có hiệu lực lùi mà ghi hôm nay là ghi sai lịch sử, và cái sai ấy
          không bao giờ tự lộ ra — nên nếu điều chuyển đã có hiệu lực từ trước, nhập đúng ngày.</p>
      </div>}

      <div style={{ marginTop: 10 }}>
        <button className="act" disabled={!sua.full_name || thieuLyDo} onClick={luu}>Lưu hồ sơ</button>
        <button className="act grey" onClick={() => setSua(null)}>Hủy</button>
        {thieuLyDo && <span className="muted" style={{ marginLeft: 8 }}>Điều chuyển phải ghi lý do.</span>}
      </div>
    </div>
  );
}
