"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import DinhKem from "@/components/DinhKem";
import { api, vnd, fmtD, soTien } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Hợp đồng lao động — V5 của lệnh giao việc 08/9/2026.
 *
 *  Backend đã viết xong từ trước (18 endpoint, có cảnh báo hết hạn) nhưng chưa ai dùng được vì không có
 *  màn hình: 0 hợp đồng trên hệ thống thật trong khi công ty có hơn 100 người.
 *
 *  Chỉ đạo 08/9 của Chủ tịch quyết cách làm: BẢN SCAN LÀ CHÍNH, HCNS tải lên khi có thay đổi. Nên màn
 *  hình này không bắt gõ lại toàn bộ nội dung hợp đồng — chỉ những trường máy phải biết để cảnh báo hết
 *  hạn và để tính lương, phần còn lại nằm trong tệp đính kèm.
 *
 *  Hợp đồng lao động thuộc nhóm hồ sơ 06_Nhan_su: dữ liệu cá nhân, phân quyền riêng theo Nghị định
 *  13/2023 — chỉ HCNS, Ban TGĐ, Chủ tịch và Ban Kiểm soát đọc được tệp. */
function HopDong() {
  const { user, toast } = useShell();
  const [meta, setMeta] = useState<any>(null);
  const [ds, setDs] = useState<any[]>([]);
  const [emps, setEmps] = useState<any[]>([]);
  const [canh, setCanh] = useState<any[]>([]);
  const [f, setF] = useState<any>(null);
  const [tep, setTep] = useState<any>(null);
  const [luu, setLuu] = useState(false);
  const canGhi = ["hcns", "cntt"].includes(user?.role || "");

  /** NS-3 · 08/10/2026 — HAI CỬA CÒN THIẾU CỦA PHÂN HỆ NHÂN SỰ, dựng ở đây chứ không ở màn hình mới.
   *
   *  `GET/PUT /employees/{id}/profile`, `/hrm/profile-gaps`, `/dependents` và `/pit-deduction` nằm trên
   *  máy chủ từ lâu mà ra cả thư mục `web/` thì KHÔNG MỘT TỆP NÀO gọi tới. Hậu quả đo được: `pit_deduction()`
   *  chỉ được gọi từ đúng cửa API của chính nó — người phụ thuộc không có cửa khai, nên giảm trừ gia cảnh
   *  là một phép tính chạy không tải suốt từ ngày viết.
   *
   *  VÌ SAO ĐẶT Ở MÀN HÌNH HỢP ĐỒNG, KHÔNG DỰNG TRANG MỚI: `MAN_HINH_API` của /hop-dong-lao-dong đã khai
   *  sẵn `/api/v1/hrm`, `/api/v1/dependents` và `/api/v1/employees` từ trước, và màn hình này đã là màn
   *  hình hồ sơ-của-một-người (BASE_VIEW + hcns + cntt). Dựng trang mới là phải khai thêm một dòng trong
   *  ma trận quyền cho đúng những cửa đã khai ở đây — thêm một chỗ để hai bản khai lệch nhau, không thêm
   *  một quyền nào. Phạm vi vai trò sau vòng này KHÔNG đổi một đơn vị.
   */
  const [thieuHoSo, setThieuHoSo] = useState<any>(null);
  const [chon, setChon] = useState<number>(0);          // nhân viên đang mở hồ sơ
  const [hs, setHs] = useState<any>(null);              // /employees/{id}/profile
  const [fHs, setFHs] = useState<any>({});              // ô đang sửa
  const [npt, setNpt] = useState<any[]>([]);
  const [fNpt, setFNpt] = useState<any>(null);
  const [gt, setGt] = useState<any>(null);              // /pit-deduction
  const ky = new Date().toISOString().slice(0, 7);

  const load = useCallback(async () => {
    try {
      setDs(await api("/labor-contracts"));
      setCanh(await api("/labor-contracts/alerts?within_days=45"));
    } catch (e) { toast(errMsg(e), true); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    api("/hrm/meta").then(setMeta).catch(() => {});
    api("/employees").then((r: any) => setEmps(r.rows || r)).catch(() => {});
    api("/hrm/profile-gaps").then(setThieuHoSo).catch(() => setThieuHoSo(null));
  }, []);

  /** Mở hồ sơ một người: ba lời gọi, và KHÔNG lời gọi nào tính lại cái máy chủ đã tính. Mức giảm trừ
   *  gia cảnh lấy nguyên từ `/pit-deduction` — tính ở màn hình là tính lần thứ hai, và lần thứ hai bao
   *  giờ cũng là lần lệch khi Nhà nước nâng mức. */
  const moHoSo = useCallback((eid: number) => {
    setChon(eid); setHs(null); setFHs({}); setNpt([]); setGt(null); setFNpt(null);
    if (!eid) return;
    api(`/employees/${eid}/profile`).then((r: any) => { setHs(r); setFHs(r.profile || {}); })
      .catch((e) => toast(errMsg(e), true));
    api<any[]>(`/dependents?employee_id=${eid}`).then(setNpt).catch(() => setNpt([]));
    api(`/employees/${eid}/pit-deduction?period=${ky}`).then(setGt).catch(() => setGt(null));
  }, [toast, ky]);

  const luuHoSo = async () => {
    try {
      await api(`/employees/${chon}/profile`, { method: "PUT", json: fHs });
      toast("Đã lưu hồ sơ");
      api("/hrm/profile-gaps").then(setThieuHoSo).catch(() => {});
      moHoSo(chon);
    } catch (e) { toast(errMsg(e), true); }
  };

  const themNpt = async () => {
    if (!String(fNpt?.full_name || "").trim()) { toast("Thiếu họ tên người phụ thuộc", true); return; }
    try {
      await api("/dependents", { method: "POST", json: { ...fNpt, employee_id: chon } });
      toast("Đã thêm người phụ thuộc"); setFNpt(null); moHoSo(chon);
    } catch (e) { toast(errMsg(e), true); }
  };

  /** NGỪNG, không phải XOÁ. Máy chủ đặt `active = false` và giữ lại dòng: một người phụ thuộc đã từng
   *  được giảm trừ là căn cứ quyết toán thuế của những kỳ trước, xoá đi là xoá mất căn cứ ấy. */
  const ngungNpt = async (d: any) => {
    if (!window.confirm(`Ngừng giảm trừ cho ${d.full_name}? Dòng cũ vẫn giữ để tra lại.`)) return;
    try { await api(`/dependents/${d.id}`, { method: "DELETE" }); toast("Đã ngừng"); moHoSo(chon); }
    catch (e) { toast(errMsg(e), true); }
  };

  const luuHd = async () => {
    setLuu(true);
    try {
      await api("/labor-contracts", { method: "POST", json: {
        employee_id: Number(f.employee_id), code: f.code, kind: f.kind,
        signed_on: f.signed_on || null, effective_from: f.effective_from,
        effective_to: f.effective_to || null, salary: soTien(f.salary),
        si_salary: soTien(f.si_salary), allowance: soTien(f.allowance),
        annual_leave_days: Number(f.annual_leave_days) || 12,
        note: f.note || "" } });
      toast("Đã lưu hợp đồng. Nhớ đính kèm bản scan ở dòng của người này.");
      setF(null); await load();
    } catch (e) { toast(errMsg(e), true); } finally { setLuu(false); }
  };

  const chamDut = async (c: any) => {
    const on = window.prompt(`Chấm dứt hợp đồng ${c.code}. Ngày chấm dứt (YYYY-MM-DD):`,
                             new Date().toISOString().slice(0, 10));
    if (!on) return;
    const reason = window.prompt("Lý do chấm dứt (ghi lại để sau này đối chiếu hồ sơ BHXH):") || "";
    try { await api(`/labor-contracts/${c.id}/terminate`, { method: "POST", json: { on, reason } });
          toast("Đã ghi chấm dứt."); await load(); }
    catch (e) { toast(errMsg(e), true); }
  };

  const coHd = new Set(ds.filter((c) => c.status !== "cham_dut").map((c) => c.employee_id));
  const thieu = emps.filter((e: any) => e.active && e.contract_type === "hdld" && !coHd.has(e.id));

  return (<>
    <h1>Hợp đồng lao động</h1>
    <p className="muted">Bản scan là chính — HCNS tải lên mỗi khi có hợp đồng mới hoặc phụ lục. Màn hình
      chỉ giữ những trường hệ thống phải biết để <b>cảnh báo hết hạn</b> và để tính lương; phần còn lại
      nằm trong tệp. Tệp thuộc nhóm hồ sơ 06_Nhan_su — dữ liệu cá nhân, phân quyền riêng theo Nghị định
      13/2023.</p>

    {canh.length > 0 && <div className="panel">
      <h2>Sắp hết hạn trong 45 ngày</h2>
      <div className="wrap"><table>
        <thead><tr><th>Nhân viên</th><th>Số HĐ</th><th>Loại</th><th>Hết hiệu lực</th><th>Còn</th></tr></thead>
        <tbody>{canh.map((c: any) => <tr key={c.id || c.code}>
          <td>{c.employee_name || c.full_name}</td><td className="mono">{c.code}</td>
          <td className="muted">{c.kind_name || c.kind}</td><td>{fmtD(c.effective_to)}</td>
          <td>{(c.days_left ?? c.con_lai) <= 15 ? <Tag cls="red">{c.days_left ?? c.con_lai} ngày</Tag>
            : <Tag cls="warn">{c.days_left ?? c.con_lai} ngày</Tag>}</td>
        </tr>)}</tbody></table></div>
      <p className="muted">Hết hạn mà không ký tiếp thì quan hệ lao động vẫn tiếp diễn trên thực tế —
        đó là chỗ tranh chấp lao động bắt đầu, và cũng là chỗ thanh tra hỏi trước tiên.</p>
    </div>}

    {thieu.length > 0 && <div className="panel">
      <h2><Tag cls="red">{thieu.length}</Tag> người ký HĐLĐ nhưng chưa có hợp đồng trên hệ thống</h2>
      <p className="muted">{thieu.slice(0, 40).map((e: any) => `${e.code} ${e.full_name}`).join(" · ")}
        {thieu.length > 40 ? ` … và ${thieu.length - 40} người nữa` : ""}</p>
    </div>}

    {canGhi && <div className="panel">
      <h2>Ghi một hợp đồng</h2>
      {!f && <button className="act" onClick={() => setF({ employee_id: "", code: "", kind: "xac_dinh",
        signed_on: "", effective_from: "", effective_to: "", salary: "", si_salary: "", allowance: "",
        annual_leave_days: 12, note: "" })}>+ Thêm hợp đồng</button>}
      {f && <>
        <div className="grid2">
          <label>Nhân viên
            <select value={f.employee_id} onChange={(e) => setF({ ...f, employee_id: e.target.value })}>
              <option value="">— chọn người —</option>
              {emps.filter((e: any) => e.active).map((e: any) =>
                <option key={e.id} value={e.id}>{e.code} · {e.full_name}</option>)}
            </select></label>
          <label>Số hợp đồng
            <input value={f.code} onChange={(e) => setF({ ...f, code: e.target.value })} /></label>
          <label>Loại hợp đồng
            <select value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}>
              {Object.entries(meta?.contract_kinds || {}).map(([k, v]: any) =>
                <option key={k} value={k}>{typeof v === "string" ? v : v?.ten || k}</option>)}
            </select></label>
          <label>Ngày ký
            <input type="date" value={f.signed_on}
                   onChange={(e) => setF({ ...f, signed_on: e.target.value })} /></label>
          <label>Có hiệu lực từ
            <input type="date" value={f.effective_from}
                   onChange={(e) => setF({ ...f, effective_from: e.target.value })} /></label>
          <label>Hết hiệu lực <span className="muted">(để trống nếu không xác định thời hạn)</span>
            <input type="date" value={f.effective_to}
                   onChange={(e) => setF({ ...f, effective_to: e.target.value })} /></label>
          <label>Lương hợp đồng
            <input type="number" step={100000} value={f.salary}
                   onChange={(e) => setF({ ...f, salary: e.target.value })} /></label>
          <label>Mức đóng BHXH
            <input type="number" step={100000} value={f.si_salary}
                   onChange={(e) => setF({ ...f, si_salary: e.target.value })} /></label>
          {/* HS-9 · 17/10/2026 — HAI Ô LÂU NAY GỬI LÊN MÀ KHÔNG AI NHẬP ĐƯỢC.
              `allowance` nằm trong gói gửi đi từ đầu nhưng chưa bao giờ có ô, nên mọi hợp đồng
              đã ghi đều có phụ cấp rỗng. `annual_leave_days` thì cửa máy chủ mặc định 12 — một
              con số mặc định mà người ký không đổi được không phải là một thoả thuận, nó là một
              giả định nằm im trong mã. */}
          <label>Phụ cấp (đ)
            <input type="number" step={100000} value={f.allowance}
                   onChange={(e) => setF({ ...f, allowance: e.target.value })} /></label>
          <label>Số ngày phép năm
            <input type="number" step={0.5} value={f.annual_leave_days}
                   onChange={(e) => setF({ ...f, annual_leave_days: e.target.value })} /></label>
          <label>Ghi chú
            <input value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} /></label>
        </div>
        <p className="muted">Mức đóng BHXH khác lương hợp đồng — ghi đúng mức đang đóng, đừng chép lại
          lương, vì bảng lương và hồ sơ bảo hiểm đối chiếu bằng chính ô này.</p>
        <button className="act teal" disabled={luu || !f.employee_id || !f.code || !f.effective_from}
                onClick={luuHd}>{luu ? "Đang lưu…" : "Lưu hợp đồng"}</button>{" "}
        <button className="act grey" onClick={() => setF(null)}>Đóng</button>
      </>}
    </div>}

    <div className="panel wrap">
      <h2>Danh sách hợp đồng</h2>
      <table><thead><tr><th>Nhân viên</th><th>Số HĐ</th><th>Loại</th><th>Hiệu lực</th>
        <th className="num">Lương HĐ</th><th className="num">Mức đóng BHXH</th><th>Trạng thái</th>
        <th></th></tr></thead>
        <tbody>{ds.length ? ds.map((c: any) => <tr key={c.id}>
          <td><b>{c.employee_name}</b><div className="muted">{c.employee_code}</div></td>
          <td className="mono">{c.code}</td><td className="muted">{c.kind_name || c.kind}</td>
          <td>{fmtD(c.effective_from)} → {c.effective_to ? fmtD(c.effective_to)
            : <span className="muted">không xác định</span>}</td>
          <td className="num">{vnd(c.salary)}</td>
          <td className="num muted">{c.si_salary ? vnd(c.si_salary) : <Tag cls="warn">chưa ghi</Tag>}</td>
          <td>{c.status === "cham_dut" ? <Tag>đã chấm dứt</Tag>
            : c.status === "het_han" ? <Tag cls="red">hết hạn</Tag> : <Tag cls="ok">đang hiệu lực</Tag>}</td>
          <td style={{ whiteSpace: "nowrap" }}>
            <button className="act grey" style={{ margin: 0 }}
                    onClick={() => setTep({ ma: c.employee_code, ten: c.employee_name })}>Bản scan</button>
            {canGhi && c.status !== "cham_dut" && <> <button className="act grey" style={{ margin: 0 }}
              onClick={() => chamDut(c)}>Chấm dứt</button></>}</td>
        </tr>) : <tr><td colSpan={8} className="muted">Chưa có hợp đồng nào trên hệ thống.</td></tr>}</tbody></table>
    </div>

    {/* NS-4 · 08/10/2026 — mặt sau của lần siết tuyến ký đơn. Mỗi phòng nay đúng MỘT vai ký, nên một
        vai không tài khoản nào giữ thì đơn của cả phòng ấy nằm im trong hàng đợi và KHÔNG dòng nào
        báo. Màn hình in ra để HCNS đi cấp tài khoản, chứ không để phần mềm tự nới lại danh sách —
        nới lại là xoá đúng quyết định vừa ký. */}
    {(meta?.phong_thieu_nguoi_giu_vai?.length || meta?.phong_chua_chot_nguoi_ky?.length) ? <div className="panel">
      <h2>Tuyến ký đơn nghỉ còn chỗ hở</h2>
      {meta.phong_thieu_nguoi_giu_vai?.length > 0 && <p>
        <Tag cls="red">{meta.phong_thieu_nguoi_giu_vai.length} phòng</Tag> đã chỉ định người ký nhưng
        <b> chưa tài khoản nào giữ vai ấy</b> — đơn của họ sẽ nằm im trong hàng đợi:{" "}
        {meta.phong_thieu_nguoi_giu_vai.map((x: any) => `${x.phong_ten} (cần vai ${x.vai_ky.join(", ")})`).join(" · ")}.
        {" "}HCNS cấp tài khoản cho đúng vai là xong.</p>}
      {meta.phong_chua_chot_nguoi_ky?.length > 0 && <p>
        <Tag cls="warn">{meta.phong_chua_chot_nguoi_ky.length} phòng</Tag> chưa ai quyết người ký, đang
        chạy bằng danh sách dự phòng: {meta.phong_chua_chot_nguoi_ky.join(" · ")}.</p>}
    </div> : null}

    <div className="panel">
      <h2>Hồ sơ định danh &amp; người phụ thuộc</h2>
      <p className="muted">Hai cửa này nằm trên máy chủ từ lâu mà chưa màn hình nào gọi tới, nên
        <b> giảm trừ gia cảnh là một phép tính chạy không tải</b>: không ai khai được người phụ thuộc thì
        mức giảm trừ của mọi người đều bằng mức bản thân. Số liệu do Nhân sự nhập — dữ liệu cá nhân,
        phân quyền riêng theo Nghị định 13/2023.</p>
      {thieuHoSo && thieuHoSo.count > 0 && <p>
        <Tag cls="warn">{thieuHoSo.count}</Tag> người còn thiếu thông tin hồ sơ bắt buộc
        <span className="muted"> ({(thieuHoSo.required_fields || []).join(" · ")})</span></p>}

      <div className="wrap">
        <label>Chọn người<br />
          <select value={chon || ""} onChange={(e) => moHoSo(Number(e.target.value))}>
            <option value="">— chọn nhân viên —</option>
            {emps.map((e: any) => <option key={e.id} value={e.id}>{e.code} · {e.full_name}</option>)}
          </select></label>
        {hs && <p className="muted" style={{ alignSelf: "end", margin: 0 }}>
          Hồ sơ đầy đủ <b>{hs.completeness?.percent}%</b>
          {hs.completeness?.missing?.length ? <> · còn thiếu: {hs.completeness.missing.join(", ")}</> : null}</p>}
      </div>

      {chon > 0 && hs && <>
        <div className="wrap" style={{ marginTop: 8 }}>
          {/* HS-9 · 17/10/2026 — ĐỦ 17 TRƯỜNG, không phải 8.
              Cửa `PUT /employees/{id}/profile` nhận 17 trường; biểu này dựng 8. Chín trường còn
              lại — trong đó có NGÀY CẤP và NƠI CẤP căn cước, hai thứ hợp đồng lao động và hồ sơ
              BHXH đều cần — không màn hình nào nhập được.
              Nặng hơn: màn «Hồ sơ nhân viên» HIỆN RA đúng những trường ấy, nên chúng trống vĩnh
              viễn và trông y hệt «người này chưa khai». Một ô dữ liệu bày ra mà không có cửa nhập
              thì không phải thiếu dữ liệu, là thiếu phần mềm. `test_hs9_1` canh đúng chỗ này:
              thêm một trường vào `ProfileIn` mà quên dựng ô là đỏ. */}
          {([["id_number", "Số CCCD"], ["id_issued_on", "Ngày cấp"], ["id_issued_by", "Nơi cấp"],  
             ["dob", "Ngày sinh"], ["gender", "Giới tính"],
             ["permanent_address", "Địa chỉ thường trú"], ["current_address", "Chỗ ở hiện tại"],
             ["phone", "Điện thoại"], ["email", "Email"],
             ["tax_code", "Mã số thuế"], ["social_insurance_no", "Số sổ BHXH"],
             ["bank_account", "Số tài khoản"], ["bank_name", "Ngân hàng"],
             ["marital_status", "Tình trạng hôn nhân"], ["education", "Học vấn"],
             ["emergency_contact", "Liên hệ khẩn cấp"], ["note", "Ghi chú"]] as [string, string][])
            .map(([k, l]) => <label key={k}>{l}
              {(hs.completeness?.missing || []).includes(k) && <Tag cls="warn">thiếu</Tag>}<br />
              {k === "gender"
                ? <select value={(fHs as any)[k] || ""} disabled={!canGhi}
                          onChange={(e) => setFHs({ ...fHs, [k]: e.target.value })}>
                    <option value="">— chưa khai —</option>
                    <option value="nam">Nam</option><option value="nu">Nữ</option>
                    <option value="khac">Khác</option></select>
                : <input type={(k === "dob" || k === "id_issued_on") ? "date" : "text"}
                         value={(fHs as any)[k] || ""} disabled={!canGhi}
                         onChange={(e) => setFHs({ ...fHs, [k]: e.target.value })} />}</label>)}
          {canGhi && <div style={{ alignSelf: "end" }}><button className="act teal" onClick={luuHoSo}>Lưu hồ sơ</button></div>}
        </div>

        <h3 style={{ marginTop: 16 }}>Người phụ thuộc · giảm trừ gia cảnh</h3>
        {gt && <p className="muted">Kỳ {gt.period}: bản thân <b>{vnd(gt.self)}</b>
          {" "}+ {gt.dependents} người phụ thuộc × {vnd(gt.dependent_rate)}
          {" "}= <b>{vnd(gt.total)}</b> mỗi tháng.
          {" "}<span className="muted">Mức do Kế toán chỉnh trong Chính sách &amp; quy trình khi Nhà nước nâng.</span></p>}
        <table><thead><tr><th>Họ tên</th><th>Quan hệ</th><th>Ngày sinh</th><th>MST</th><th>Từ kỳ</th><th>Đến kỳ</th><th></th></tr></thead>
          <tbody>{npt.length ? npt.map((d: any) => <tr key={d.id}>
            <td><b>{d.full_name}</b></td><td>{d.relation_name}</td><td>{d.dob ? fmtD(d.dob) : ""}</td>
            <td className="mono">{d.tax_code}</td><td>{d.from_period}</td><td>{d.to_period}</td>
            <td>{canGhi && <button className="act grey" style={{ margin: 0 }} onClick={() => ngungNpt(d)}>Ngừng</button>}</td>
          </tr>) : <tr><td colSpan={7} className="muted">Chưa khai người phụ thuộc nào.</td></tr>}</tbody></table>

        {canGhi && (!fNpt
          ? <button className="act teal" style={{ marginTop: 8 }}
                    onClick={() => setFNpt({ full_name: "", relation: "con", dob: "", tax_code: "", from_period: ky, to_period: "" })}>Thêm người phụ thuộc</button>
          : <div className="wrap" style={{ marginTop: 8 }}>
              <label>Họ tên<br /><input value={fNpt.full_name}
                onChange={(e) => setFNpt({ ...fNpt, full_name: e.target.value })} /></label>
              <label>Quan hệ<br /><select value={fNpt.relation}
                onChange={(e) => setFNpt({ ...fNpt, relation: e.target.value })}>
                {Object.entries(meta?.relations || { con: "Con" }).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}
              </select></label>
              <label>Ngày sinh<br /><input type="date" value={fNpt.dob}
                onChange={(e) => setFNpt({ ...fNpt, dob: e.target.value })} /></label>
              <label>Mã số thuế<br /><input value={fNpt.tax_code}
                onChange={(e) => setFNpt({ ...fNpt, tax_code: e.target.value })} /></label>
              <label>Từ kỳ <span className="muted">(YYYY-MM)</span><br /><input value={fNpt.from_period} style={{ width: 110 }}
                onChange={(e) => setFNpt({ ...fNpt, from_period: e.target.value })} /></label>
              <label>Đến kỳ <span className="muted">(để trống = còn hiệu lực)</span><br /><input value={fNpt.to_period} style={{ width: 110 }}
                onChange={(e) => setFNpt({ ...fNpt, to_period: e.target.value })} /></label>
              <div><button className="act teal" onClick={themNpt}>Lưu</button>{" "}
                <button className="act grey" onClick={() => setFNpt(null)}>Thôi</button></div>
            </div>)}
      </>}
    </div>

    {tep && <DinhKem doiTuong="nhan_su" doiTuongId={tep.ma} loai="hop_dong"
      tieuDe={`Hợp đồng và phụ lục – ${tep.ten} (${tep.ma})`}
      goi={"Bản scan hợp đồng, phụ lục điều chỉnh lương, quyết định bổ nhiệm, thỏa thuận chấm dứt. " +
           "Giữ trong thời gian làm việc + 5 năm theo quy ước lưu trữ."} />}
  </>);
}

export default function Page() { return <Shell><HopDong /></Shell>; }
