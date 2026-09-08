"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import DinhKem from "@/components/DinhKem";
import { api, vnd, fmtD } from "@/lib/api";
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
  }, []);

  const luuHd = async () => {
    setLuu(true);
    try {
      await api("/labor-contracts", { method: "POST", json: {
        employee_id: Number(f.employee_id), code: f.code, kind: f.kind,
        signed_on: f.signed_on || null, effective_from: f.effective_from,
        effective_to: f.effective_to || null, salary: Number(f.salary) || 0,
        si_salary: Number(f.si_salary) || 0, allowance: Number(f.allowance) || 0,
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
        note: "" })}>+ Thêm hợp đồng</button>}
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

    {tep && <DinhKem doiTuong="nhan_su" doiTuongId={tep.ma} loai="hop_dong"
      tieuDe={`Hợp đồng và phụ lục – ${tep.ten} (${tep.ma})`}
      goi={"Bản scan hợp đồng, phụ lục điều chỉnh lương, quyết định bổ nhiệm, thỏa thuận chấm dứt. " +
           "Giữ trong thời gian làm việc + 5 năm theo quy ước lưu trữ."} />}
  </>);
}

export default function Page() { return <Shell><HopDong /></Shell>; }
