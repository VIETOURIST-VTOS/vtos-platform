"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD, fmtDT, getToken } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import { useHoi } from "@/components/HopHoi";

const MANAGERS = ["tp_dh", "gd_kd", "tp_kd", "tn_kd", "ptgd_doan", "ptgd_mkt", "tgd", "chutich", "hcns", "cntt", "bks"];
// BC-2: người xem xét của từng phòng trong bảng phòng (TP Hướng dẫn, GĐ đội xe, Kế toán) cũng mở tab
// Tổng hợp. Phạm vi thật do máy chủ cắt; danh sách này chỉ quyết định có hiện nút tab hay không.
const NGUOI_XEM = [...MANAGERS, "tp_hd", "gd_doi_xe", "ketoan", "ketoan_truong", "ketoan_tt"];
const today = () => new Date().toISOString().slice(0, 10);   // chỉ cho ô ngày phân ca trực page
const thisMonth = () => new Date().toISOString().slice(0, 7);

/* BC-1 (Chủ tịch duyệt bản xem thử 26/10/2026) — MÀN NHÂN VIÊN NỘP BÁO CÁO NGÀY.
   Hạn trước 0 giờ ngày kế tiếp theo GIỜ VIỆT NAM do máy chủ trả (`han_luc`, `bay_gio`); đồng hồ máy
   người dùng chỉ để đếm lùi giữa hai lần tải, không quyết định đúng hạn. Năm phần; ô số có nút
   «Không phát sinh» — ô trống là CHƯA NHẬP, không bao giờ thành 0. Một người một báo cáo mỗi ngày,
   mẫu chính + phần việc kiêm nhiệm Chủ tịch giao. Nộp lại thêm phiên bản; đúng hạn theo lần đầu. */
function Countdown({ seconds, han }: { seconds: number; han: string }) {
  const [left, setLeft] = useState(seconds);
  useEffect(() => { setLeft(seconds); const t = setInterval(() => setLeft((x) => Math.max(0, x - 1)), 1000); return () => clearInterval(t); }, [seconds]);
  const h = Math.floor(left / 3600), m = Math.floor((left % 3600) / 60);
  return <div style={{ textAlign: "right" }}><b style={{ fontSize: 22, color: left > 0 ? "var(--orange)" : "var(--red)" }}>{left > 0 ? `${h} giờ ${m} phút` : "Đã quá hạn"}</b><br />
    <span className="muted">{left > 0 ? `còn lại · hạn ${han} · giờ máy chủ` : "nộp lúc này tính là muộn cho ngày này"}</span></div>;
}

const TRANG_TAG: Record<string, string> = { dung_han: "ok", muon: "warn", qua_han: "red", chua_den_han: "warn", khong_nghia_vu: "" };

function DailyForm({ onDone, rows }: { onDone: () => void; rows: any[] }) {
  const { user, toast } = useShell();
  const [form, setForm] = useState<any>(null);
  const [f, setF] = useState<any>({ part1_done: "", part3_issues: "", part4_plan: "", vuong_mac_cho: "", vuong_mac_han: "" });
  const [p2, setP2] = useState<Record<string, string>>({});
  const [pv, setPv] = useState<{ subject: string; body: string; lines: number } | null>(null);
  const [sent, setSent] = useState<any>(null);
  const [teps, setTeps] = useState<any[]>([]);
  const [dangTai, setDangTai] = useState(false);
  const [ngayMo, setNgayMo] = useState("");          // BC-2: mở lại một ngày cũ được trả bổ sung
  const [viecToi, setViecToi] = useState<any[]>([]);
  const KPS = form?.khong_phat_sinh || "Không phát sinh";
  const ngay: string = form?.ngay || "";
  // Nháp chỉ giữ trong trình duyệt của chính người viết — không phải bằng chứng đã nộp.
  const khoaNhap = ngay ? `vtos_bc_nhap_${user?.username}_${ngay}` : "";
  const taiLai = useCallback(() => api(`/daily-reports/form${ngayMo ? `?ngay=${ngayMo}` : ""}`).then((r) => {
    setForm(r); setTeps([]);
    api("/daily-reports/viec").then((v) => setViecToi(v.cua_toi || [])).catch(() => {});
    if (r.today) {
      setF({ part1_done: r.today.part1_done, part3_issues: r.today.part3_issues, part4_plan: r.today.part4_plan,
             vuong_mac_cho: r.today.vuong_mac_cho || "", vuong_mac_han: r.today.vuong_mac_han || "" });
      setP2(r.today.part2 || {});
      api(`/daily-reports/${r.today.id}/tep`).then(setTeps).catch(() => {});
    } else {
      try { const n = JSON.parse(localStorage.getItem(`vtos_bc_nhap_${user?.username}_${r.ngay}`) || "null"); if (n) { setF(n.f); setP2(n.p2 || {}); } } catch { /* trình duyệt chặn lưu */ }
    }
  }).catch((e) => toast(errMsg(e), true)), [toast, user?.username, ngayMo]);
  useEffect(() => { taiLai(); }, [taiLai]);
  const dept = form?.department || "";
  const mau: string[] = form?.mau || [];
  const khoa: Record<string, Record<string, string>> = form?.khoa || {};
  const moiKhoa = mau.flatMap((m) => Object.values(khoa[m] || {}));
  const payload = { report_date: ngay, department: dept, part1_done: f.part1_done, part3_issues: f.part3_issues, part4_plan: f.part4_plan,
    vuong_mac_cho: f.vuong_mac_cho || "", vuong_mac_han: f.vuong_mac_han || null,
    part2_numbers: Object.fromEntries(moiKhoa.map((k) => [k, p2[k] || ""])) };
  useEffect(() => { if (!form) return; const t = setTimeout(() => api("/daily-reports/preview", { method: "POST", json: payload }).then(setPv).catch(() => {}), 400); return () => clearTimeout(t); }, [JSON.stringify(payload), form]);   // eslint-disable-line react-hooks/exhaustive-deps
  const luuNhap = () => { try { localStorage.setItem(khoaNhap, JSON.stringify({ f, p2 })); toast("Đã lưu nháp trên máy này — chưa nộp"); } catch { toast("Trình duyệt không cho lưu nháp", true); } };
  const submit = async () => {
    try {
      const r = await api("/daily-reports", { method: "POST", json: payload });
      toast(r.message); setSent(r); try { localStorage.removeItem(khoaNhap); } catch { /* bỏ qua */ }
      await taiLai(); onDone();
    } catch (e) { toast(errMsg(e), true); }
  };
  const ganTep = async (tep: File) => {
    if (!form?.today?.id) { toast("Nộp báo cáo trước rồi gắn tệp", true); return; }
    if (tep.size > (form.gioi_han_tep_mb || 8) * 1024 * 1024) { toast(`Tệp quá ${form.gioi_han_tep_mb || 8} MB`, true); return; }
    setDangTai(true);
    try {
      const fd = new FormData(); fd.append("tep", tep);
      const r = await fetch(`/api/v1/daily-reports/${form.today.id}/tep`, { method: "POST", body: fd, headers: { Authorization: `Bearer ${getToken() || ""}` } });
      const d = await r.json();
      if (!r.ok) throw { status: r.status, message: d?.detail || "Không gắn được tệp" };
      toast(d.message); setTeps(await api(`/daily-reports/${form.today.id}/tep`));
    } catch (e) { toast(errMsg(e), true); } finally { setDangTai(false); }
  };
  const moTep = (a: any) => fetch(`/api/v1/daily-reports/${form.today.id}/tep/${a.id}`, { headers: { Authorization: `Bearer ${getToken() || ""}` } })
    .then(async (r) => { if (!r.ok) throw new Error((await r.json())?.detail || "Không đọc được tệp"); return r.blob(); })
    .then((b) => window.open(URL.createObjectURL(b), "_blank")).catch((e) => toast(String(e.message || e), true));
  if (!form) return <p className="muted">Đang tải mẫu báo cáo…</p>;
  const ta = (k: string, rows = 4, ph = "", nhan = "") => <textarea aria-label={nhan} rows={rows} value={f[k]} placeholder={ph} onChange={(e) => setF({ ...f, [k]: e.target.value })} style={{ width: "100%" }} />;
  const daDien = moiKhoa.filter((k) => (p2[k] || "").trim()).length;
  const oSo = (k: string, nhan: string) => {
    const kps = p2[k] === KPS;
    return <div key={k} style={{ display: "grid", gap: 4, border: "1px solid var(--line)", borderRadius: 8, padding: "6px 8px", minWidth: 0 }}>
      <span className="muted" style={{ fontSize: 12, fontWeight: 600 }}>{nhan}</span>
      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
        <input aria-label={nhan} style={{ flex: 1, minWidth: 0 }} value={kps ? "" : (p2[k] || "")} disabled={kps} placeholder={kps ? KPS : "chưa nhập"}
          onChange={(e) => setP2({ ...p2, [k]: e.target.value })} />
        <button type="button" className={"act " + (kps ? "teal" : "grey")} style={{ margin: 0, fontSize: 11, padding: "3px 8px", whiteSpace: "nowrap" }}
          onClick={() => setP2({ ...p2, [k]: kps ? "" : KPS })}>{kps ? "✓ " : ""}{KPS}</button>
      </div></div>;
  };
  const r0 = form.today;
  return (<>
    <div className="panel" style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
      <div><h2 style={{ marginBottom: 2 }}>Báo cáo công việc ngày {fmtD(ngay)}</h2>
        <span className="muted">Nộp trước <b>{form.deadline}</b> · {form.deadline.startsWith("0:00") ? `đúng 0:00 tính là muộn cho ngày ${fmtD(ngay)}` : "luật cũ cho ngày trước mốc"}</span></div>
      <Countdown seconds={form.seconds_left} han={form.deadline} />
    </div>
    {!form.phai_nop && <div className="gate">Hồ sơ của anh/chị hiện không thuộc diện phải nộp báo cáo ngày (HDV, tài xế, Ban TGĐ hoặc chưa nối hồ sơ nhân sự). Vẫn nộp được nếu cần.</div>}
    <div className="grid" style={{ gridTemplateColumns: "minmax(0, 1.5fr) minmax(260px, 1fr)" }}>
      <div className="panel">
        <div className="grid" style={{ gridTemplateColumns: "2fr 1fr 1fr" }}>
          <label>Họ và tên<input value={form.full_name} readOnly /></label>
          <label>Mã nhân viên<input value={form.staff_code || ""} readOnly placeholder="chưa có – HCNS cập nhật" /></label>
          <label>Ngày báo cáo<input value={fmtD(ngay)} readOnly /></label>
        </div>
        <p className="muted" style={{ margin: "6px 0" }}>Mẫu của anh/chị: {mau.map((m, i) => <Tag key={m} cls={i ? "navy" : "ok"}>{form.forms[m]?.name}{i ? " (kiêm nhiệm)" : ""}</Tag>)}</p>
        <h3><Tag cls="ok">Phần 1</Tag> Việc đã làm hôm nay</h3>
        <p className="muted" style={{ margin: "0 0 6px" }}>Mỗi việc một dòng. {form.forms[dept]?.hint}</p>
        {ta("part1_done", 5, "Mỗi việc một dòng, kèm mã booking / mã tour / biển số xe nếu có", "Việc đã làm hôm nay")}
        {mau.map((m, i) => <div key={m}>
          <h3><Tag cls={i ? "navy" : "ok"}>Phần 2{i ? String.fromCharCode(97 + i) : ""}</Tag> Số liệu trong ngày · {form.forms[m]?.name}{i ? " (kiêm nhiệm)" : ""}</h3>
          {i > 0 && <p className="muted" style={{ margin: "0 0 6px" }}>{form.forms[m]?.hint}</p>}
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))" }}>
            {Object.entries(khoa[m] || {}).map(([nhan, k]) => oSo(k, nhan))}
          </div>
          {!Object.keys(khoa[m] || {}).length && <p className="muted">Mẫu này chưa có ô số (danh mục trống — Kế toán khai tài khoản ở Danh mục ngân hàng).</p>}
        </div>)}
        <p className="muted" style={{ marginTop: 4 }}>Ô bỏ trống là <b>chưa nhập</b> — khác «{KPS}». Số không bao giờ tự thành 0.</p>
        <h3><Tag cls="ok">Phần 3</Tag> Kế hoạch ngày mai</h3>
        {ta("part4_plan", 3, "Việc dự kiến làm ngày mai, có mốc giờ / khách / mã tour nếu có", "Kế hoạch ngày mai")}
        <h3><Tag cls="ok">Phần 4</Tag> Vướng mắc – cần hỗ trợ</h3>
        {ta("part3_issues", 2, "Không có thì để trống", "Vướng mắc")}
        <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
          <label>Chuyển cho<select value={f.vuong_mac_cho} onChange={(e) => setF({ ...f, vuong_mac_cho: e.target.value })}>
            <option value="">— không chuyển —</option>{Object.entries(form.forms).map(([k, v]: any) => <option key={k} value={k}>{v.name}</option>)}</select></label>
          <label>Cần xong trước<input type="date" value={f.vuong_mac_han || ""} onChange={(e) => setF({ ...f, vuong_mac_han: e.target.value })} /></label>
        </div>
        <h3><Tag cls="ok">Phần 5</Tag> Đính kèm <span className="muted" style={{ fontWeight: 400 }}>(không bắt buộc · tối đa {form.gioi_han_tep_mb} MB/tệp)</span></h3>
        {r0 ? <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          {teps.map((a) => <button key={a.id} type="button" className="act grey" style={{ margin: 0 }} onClick={() => moTep(a)}>📎 {a.ten_tep} · {Math.round(a.kich_thuoc / 1024)} KB</button>)}
          {!r0.reviewed_by && <label className="act grey" style={{ margin: 0, cursor: "pointer" }}>{dangTai ? "Đang tải…" : "＋ Thêm tệp"}
            <input type="file" hidden disabled={dangTai} onChange={(e) => { const t = e.target.files?.[0]; if (t) ganTep(t); e.target.value = ""; }} /></label>}
        </div> : <p className="muted">Nộp báo cáo trước, rồi gắn tệp vào báo cáo đã nộp.</p>}
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginTop: 10, justifyContent: "flex-end" }}>
          <span className="muted" style={{ marginRight: "auto" }}>Robot chấm nháp: Phần 1 (3đ) · Phần 2 đủ ô (3đ) · Kế hoạch (2đ) · đúng hạn (2đ). Trưởng phòng chấm chính thức.</span>
          {!r0 && <button className="act grey" onClick={luuNhap}>Lưu nháp</button>}
          <button className="act teal" disabled={!f.part1_done.trim() || !f.part4_plan.trim() || !!r0?.reviewed_by} onClick={submit}>{r0 ? "Nộp lại" : "Nộp báo cáo"}</button>
        </div>
        {sent && <div className="gate pass" style={{ marginTop: 10 }}>{sent.message}</div>}
      </div>
      <div style={{ display: "grid", gap: 12, alignContent: "start" }}>
        {ngayMo && <div className="gate">Đang mở báo cáo ngày {fmtD(ngayMo)} để bổ sung. <button className="act grey" style={{ margin: 0 }} onClick={() => setNgayMo("")}>Về hôm nay</button></div>}
        {r0?.xem === "can_bo_sung" && <div className="gate"><b>Trưởng phòng yêu cầu bổ sung:</b> {r0.bo_sung_ly_do}. Sửa rồi bấm Nộp lại — giờ nộp lần đầu giữ nguyên.</div>}
        {viecToi.length > 0 && <ViecPanel title="Việc giao cho bạn" ds={viecToi} onDone={taiLai} />}
        <div className="panel"><h3 style={{ marginTop: 0 }}>Trạng thái {ngayMo ? `ngày ${fmtD(ngayMo)}` : "hôm nay"}</h3>
          <table><tbody>
            <tr><td>Tình trạng</td><td>{r0 ? <Tag cls={r0.on_time ? "ok" : "warn"}>{r0.on_time ? "Đã nộp · đúng hạn" : "Đã nộp · muộn"}</Tag> : <Tag cls={form.seconds_left > 0 ? "warn" : "red"}>{form.seconds_left > 0 ? "Chưa nộp · chưa đến hạn" : "Quá hạn chưa nộp"}</Tag>}</td></tr>
            <tr><td>Hạn nộp</td><td className="mono">{fmtDT(form.han_luc)}</td></tr>
            <tr><td>Ô số đã điền</td><td className="mono">{daDien} / {moiKhoa.length}</td></tr>
            {r0 && <tr><td>Điểm nháp robot</td><td>{r0.robot_score}/10 <span className="muted">{r0.robot_note}</span></td></tr>}
          </tbody></table></div>
        {form.lan_nop?.length > 0 && <div className="panel"><h3 style={{ marginTop: 0 }}>Các lần nộp</h3>
          <table><tbody>{form.lan_nop.map((x: any) => <tr key={x.lan}><td>Lần {x.lan}{x.lan === 1 ? " · đầu tiên" : ""}</td><td className="mono">{fmtDT(x.luc)}</td></tr>)}</tbody></table>
          <p className="muted" style={{ margin: "6px 0 0" }}>Đúng hạn hay muộn tính theo <b>lần nộp đầu</b>. Nộp lại chỉ thêm phiên bản.</p></div>}
        <div className="panel"><h3 style={{ marginTop: 0 }}>7 ngày gần nhất</h3>
          <table><tbody>{(form.bay_ngay || []).map((x: any) => <tr key={x.ngay}><td>{fmtD(x.ngay)}</td><td>{TRANG_TAG[x.ma] ? <Tag cls={TRANG_TAG[x.ma]}>{x.ten}</Tag> : <span className="muted">{x.ten}</span>}</td></tr>)}</tbody></table></div>
        <div className="panel" style={{ background: "var(--panel2)" }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}><h3 style={{ margin: 0 }}>Nội dung lưu kèm</h3><span className="muted">{pv?.lines || 0} dòng</span></div>
          <div className="mono" style={{ fontSize: 12.5, marginTop: 6 }}>{pv?.subject}</div>
          <pre className="mono" style={{ whiteSpace: "pre-wrap", fontSize: 12.5, margin: "6px 0 0", maxHeight: 360, overflow: "auto" }}>{pv?.body}</pre>
        </div>
      </div>
    </div>
    <div className="panel wrap"><h2>Báo cáo của tôi trong tháng</h2><table><thead><tr><th>Ngày</th><th>Nộp lần đầu</th><th>Số lần</th><th>Đúng hạn</th><th>Xem xét</th><th>Điểm robot</th><th>Điểm TP</th><th>Nhận xét</th></tr></thead>
      <tbody>{rows.length ? rows.map((r) => <tr key={r.id}><td>{fmtD(r.report_date)}</td><td>{fmtDT(r.first_submitted_at)}</td><td>{r.so_lan_nop}</td><td>{r.on_time ? <Tag cls="ok">✔</Tag> : <Tag cls="warn">muộn</Tag>}</td><td><Tag cls={XEM_TAG[r.xem] || "grey"}>{r.xem_ten}</Tag>{r.xem === "can_bo_sung" && <div style={{ color: "var(--orange)" }}>Cần bổ sung: {r.bo_sung_ly_do} <button className="act grey" style={{ margin: 0 }} onClick={() => { setNgayMo(String(r.report_date).slice(0, 10)); window.scrollTo(0, 0); }}>Mở để bổ sung</button></div>}</td><td>{r.robot_score}/10 <span className="muted">{r.robot_note}</span></td><td>{r.manager_score ?? "–"}</td><td className="muted">{r.manager_note}</td></tr>) : <tr><td colSpan={8} className="muted">Chưa có báo cáo trong tháng.</td></tr>}</tbody></table></div>
  </>);
}

/* BC-1 — Chủ tịch giao phần việc KIÊM NHIỆM (26/10/2026). Một người vẫn một báo cáo mỗi ngày. */
function KiemNhiem() {
  const { toast } = useShell();
  const [d, setD] = useState<any>(null);
  const load = useCallback(() => api("/daily-reports/kiem-nhiem").then(setD).catch((e) => toast(errMsg(e), true)), [toast]);
  useEffect(() => { load(); }, [load]);
  const doi = async (employee_id: number, mau: string, bat: boolean) => {
    try { const r = await api("/daily-reports/kiem-nhiem", { method: "POST", json: { employee_id, mau, bat } }); toast(r.message); load(); }
    catch (e) { toast(errMsg(e), true); }
  };
  if (!d) return <p className="muted">Đang tải…</p>;
  return (<div className="panel wrap"><h2>Giao phần việc kiêm nhiệm</h2>
    <p className="muted">Người được giao thêm phần nào thì báo cáo ngày của họ có thêm ô số của phần ấy. Không tạo báo cáo thứ hai.</p>
    <table><thead><tr><th>Mã</th><th>Họ tên</th><th>Phòng</th>{d.mau.map((m: any) => <th key={m.ma} style={{ fontSize: 11 }}>{m.ten}</th>)}</tr></thead>
      <tbody>{d.rows.map((r: any) => <tr key={r.employee_id}><td className="mono">{r.code}</td><td>{r.name}</td><td>{r.department}</td>
        {d.mau.map((m: any) => <td key={m.ma} style={{ textAlign: "center" }}>{m.ma === r.department ? <span className="muted">chính</span>
          : <input type="checkbox" aria-label={`${r.name} kiêm ${m.ten}`} checked={r.kiem_nhiem.includes(m.ma)} onChange={(e) => doi(r.employee_id, m.ma, e.target.checked)} />}</td>)}</tr>)}</tbody></table></div>);
}

/* BC-2 (Chủ tịch duyệt bản xem thử 26/10/2026) — TỔNG HỢP CHO NGƯỜI XEM XÉT.
   Số cần xử lý trước, bảng sau. Phạm vi do MÁY CHỦ cắt theo bảng phòng (bao_cao_phong.PHONG): HCNS
   nhận trạng thái cả công ty nhưng không nhận nội dung phòng khác — màn hình không giấu gì, vì không
   có gì để giấu. Trả bổ sung bắt buộc lý do; «Đã xem» không chốt công; không tự xem báo cáo mình. */
const HAN_TAG: Record<string, string> = { dung_han: "ok", muon: "warn", chua_den_han: "grey", qua_han: "red", khong_nghia_vu: "grey" };
const XEM_TAG: Record<string, string> = { cho_xem: "grey", can_bo_sung: "warn", da_xem: "ok" };
const homQua = () => { const d = new Date(Date.now() + 7 * 3600e3 - 864e5); if (d.getUTCDay() === 0) d.setUTCDate(d.getUTCDate() - 1); return d.toISOString().slice(0, 10); };

function ViecPanel({ title, ds, onDone, note }: { title: string; ds: any[]; onDone: () => void; note?: string }) {
  const { toast } = useShell();
  const doi = async (v: any, trang_thai: string) => {
    try { const r = await api<any>(`/daily-reports/viec/${v.id}`, { method: "POST", json: { trang_thai } }); toast(r.message); onDone(); }
    catch (x) { toast(errMsg(x), true); }
  };
  return (<div className="panel"><h3 style={{ marginTop: 0 }}>{title}</h3>
    {note && <p className="muted" style={{ marginTop: 0 }}>{note}</p>}
    {ds.length ? ds.map((v) => <div key={v.id} style={{ border: "1px solid var(--line)", borderRadius: 8, padding: "8px 10px", marginBottom: 8, opacity: ["da_xong"].includes(v.trang_thai) ? 0.6 : 1 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
        <b>{v.loai === "ho_tro" ? `Hỗ trợ · giao cho ${v.nguoi_nhan}` : `${v.tu_phong_ten} → ${v.den_phong_ten}`}</b>
        {v.trang_thai === "da_xong" ? <Tag cls="ok">Đã xong</Tag> : v.qua_han ? <Tag cls="red">quá hạn {-v.con_ngay} ngày</Tag>
          : v.con_ngay != null ? <Tag cls="warn">còn {v.con_ngay} ngày</Tag> : <Tag cls="grey">{v.trang_thai_ten}</Tag>}
      </div>
      <div style={{ whiteSpace: "pre-wrap" }}>{v.noi_dung}</div>
      <div className="muted">{v.han ? `Hạn ${fmtD(v.han)} · ` : ""}từ báo cáo {fmtD(v.ngay_bao_cao)} của {v.nguoi_nop} · {v.trang_thai_ten}{v.ghi_chu ? ` · ${v.ghi_chu}` : ""}</div>
      {v.trang_thai !== "da_xong" && <div style={{ display: "flex", gap: 6, marginTop: 4 }}>
        {v.trang_thai === "mo" && <button className="act grey" style={{ margin: 0 }} onClick={() => doi(v, "dang_xu_ly")}>Nhận xử lý</button>}
        <button className="act grey" style={{ margin: 0 }} onClick={() => doi(v, "da_xong")}>Đã xong</button></div>}
    </div>) : <p className="muted">Không có việc nào.</p>}
  </div>);
}

function TongHop() {
  const { toast } = useShell();
  const [ngay, setNgay] = useState(homQua());
  const [phong, setPhong] = useState("");
  const [loc, setLoc] = useState("");
  const [d, setD] = useState<any>(null);
  const [viec, setViec] = useState<any>({ den_phong: [], cua_toi: [] });
  const [mo, setMo] = useState<number | null>(null);
  const [ly, setLy] = useState("");
  const [diem, setDiem] = useState("");
  const [giao, setGiao] = useState({ nguoi: "", noi_dung: "", han: "" });
  const [err, setErr] = useState("");
  const load = useCallback(() => {
    api(`/daily-reports/tong-hop?ngay=${ngay}${phong ? `&phong=${phong}` : ""}`).then((x) => { setD(x); setErr(""); }).catch((x) => setErr(errMsg(x)));
    api("/daily-reports/viec").then(setViec).catch(() => {});
  }, [ngay, phong]);
  useEffect(() => { load(); }, [load]);
  const moDong = (r: any) => { setMo(mo === r.user_id ? null : r.user_id); setLy(""); setDiem(""); setGiao({ nguoi: "", noi_dung: "", han: "" }); };
  const xem = async (r: any, hanh_dong: string) => {
    try {
      const x = await api<any>(`/daily-reports/${r.report_id}/xem`, { method: "POST",
        json: { hanh_dong, ly_do: ly, diem: diem === "" ? null : Number(diem), lan: r.so_lan } });
      toast(x.message); setMo(null); load();
    } catch (x) { toast(errMsg(x), true); load(); }
  };
  const giaoHoTro = async (r: any) => {
    try {
      const x = await api<any>(`/daily-reports/${r.report_id}/giao-ho-tro`, { method: "POST",
        json: { nguoi: Number(giao.nguoi), noi_dung: giao.noi_dung, han: giao.han || null } });
      toast(x.message); setGiao({ nguoi: "", noi_dung: "", han: "" }); load();
    } catch (x) { toast(errMsg(x), true); }
  };
  if (err) return <div className="panel"><p className="muted">{err}</p></div>;
  if (!d) return <div className="panel"><p className="muted">Đang tải…</p></div>;
  const dong = d.dong.filter((r: any) => !loc || (loc === "qua_han" ? r.thoi_han === "qua_han" : r.report_id && r.xem === loc && r.doc_duoc && !r.tu_minh));
  const dem = d.dem, tong = Math.max(d.dong.length - dem.khong_nghia_vu, 1);
  const BA: [string, string, string, string][] = [["cho_xem", "Chờ xem", "đã nộp, chưa ai xem", "var(--navy)"],
    ["can_bo_sung", "Cần bổ sung", "đã trả, chờ nhân viên nộp lại", "var(--orange)"], ["qua_han", "Quá hạn chưa nộp", `đã qua hạn ${d.han}`, "var(--red)"]];
  return (<>
    <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "end" }}>
      <label>Ngày<input type="date" value={ngay} onChange={(e) => setNgay(e.target.value)} /></label>
      <label>Phòng<select value={phong} onChange={(e) => setPhong(e.target.value)}><option value="">Tất cả trong phạm vi</option>
        {d.cac_phong.map((p: any) => <option key={p.ma} value={p.ma}>{p.ten}</option>)}</select></label>
      <label>Trạng thái<select value={loc} onChange={(e) => setLoc(e.target.value)}><option value="">Tất cả</option>
        {BA.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></label>
      <span className="muted" style={{ marginLeft: "auto" }}>Mốc dữ liệu {fmtDT(d.as_of)} (giờ VN){d.chi_trang_thai ? " · bạn xem trạng thái cả công ty, nội dung chỉ phòng mình" : d.pham_vi === "nhom" ? " · báo cáo của người trong nhóm bạn" : ""}</span>
    </div>
    <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))", marginTop: 10 }}>
      {BA.map(([k, l, g, c]) => <button key={k} className="panel" aria-pressed={loc === k} onClick={() => setLoc(loc === k ? "" : k)}
        style={{ textAlign: "left", cursor: "pointer", outline: loc === k ? "2px solid var(--navy)" : undefined }}>
        <div className="mono" style={{ fontSize: 28, fontWeight: 700, color: c }}>{d.xu_ly[k]}</div><b>{l}</b><div className="muted">{g}</div></button>)}
    </div>
    <div className="panel">
      <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
        <b>Ngày {fmtD(d.ngay)}</b><span><b className="mono">{d.da_nop}/{d.phai_nop}</b> <span className="muted">đã nộp{d.ty_le != null ? ` · ${d.ty_le}%` : ""} (người có nghĩa vụ)</span></span></div>
      <div style={{ display: "flex", height: 10, borderRadius: 5, overflow: "hidden", background: "var(--panel2)", marginTop: 6 }}>
        {[["dung_han", "var(--teal)"], ["muon", "var(--orange)"], ["chua_den_han", "var(--line)"], ["qua_han", "var(--red)"]].map(([k, c]) =>
          <i key={k} style={{ width: `${(dem[k] * 100) / tong}%`, background: c }} />)}</div>
      <div className="muted" style={{ marginTop: 4 }}>Đúng hạn {dem.dung_han} · Muộn {dem.muon} · Chưa đến hạn {dem.chua_den_han} · Quá hạn chưa nộp {dem.qua_han} · Không có nghĩa vụ {dem.khong_nghia_vu} (đếm riêng, không vào mẫu số)</div>
    </div>
    <div className="grid" style={{ gridTemplateColumns: "minmax(0,1.7fr) minmax(260px,1fr)", alignItems: "start" }}>
      <div className="panel wrap"><h3 style={{ marginTop: 0 }}>Từng người · bấm một dòng để mở năm phần</h3>
        <table><thead><tr><th>Người</th><th>Phòng</th><th>Nộp lần đầu</th><th>Số lần</th><th>Thời hạn</th><th>Xem xét</th><th>Robot</th><th>TP</th></tr></thead>
          <tbody>{dong.length ? dong.map((r: any) => <>
            <tr key={r.user_id} style={{ cursor: r.doc_duoc && r.report_id ? "pointer" : "default" }} onClick={() => r.doc_duoc && r.report_id && moDong(r)}>
              <td><b>{r.ten}</b> <span className="muted mono">{r.code}</span>{r.tu_minh && <span className="muted"> · bạn</span>}</td><td>{r.phong_ten}</td>
              <td className="mono">{r.lan_dau ? fmtDT(r.lan_dau) : "—"}</td><td className="mono">{r.so_lan || "—"}</td>
              <td><Tag cls={HAN_TAG[r.thoi_han] || "grey"}>{r.thoi_han_ten}</Tag></td>
              <td>{r.report_id ? <Tag cls={XEM_TAG[r.xem] || "grey"}>{r.xem_ten}</Tag> : "—"}</td>
              <td className="mono">{r.diem_robot ?? "—"}</td><td className="mono">{r.diem_tp ?? "—"}</td></tr>
            {mo === r.user_id && r.noi_dung && <tr key={r.user_id + "d"}><td colSpan={8}><div style={{ background: "var(--panel2)", borderRadius: 8, padding: "10px 12px", display: "grid", gap: 6 }}>
              <div><b>1 · Việc đã làm:</b> <span style={{ whiteSpace: "pre-wrap" }}>{r.noi_dung.p1}</span></div>
              <div><b>2 · Số liệu:</b> {Object.entries(r.noi_dung.p2 || {}).map(([k, v]: any) => <span key={k}> · {k}: {v ? <b>{v}</b> : <span style={{ color: "var(--orange)" }}>chưa nhập</span>}</span>)}</div>
              <div><b>3 · Ngày mai:</b> <span style={{ whiteSpace: "pre-wrap" }}>{r.noi_dung.p3}</span></div>
              <div><b>4 · Vướng mắc:</b> {r.noi_dung.p4 || <span className="muted">không có</span>}{r.noi_dung.vuong_mac_cho && <span className="muted"> → {r.noi_dung.vuong_mac_cho_ten}{r.noi_dung.vuong_mac_han && `, trước ${fmtD(r.noi_dung.vuong_mac_han)}`}</span>}</div>
              <div><b>5 · Đính kèm:</b> {r.noi_dung.so_tep ? `${r.noi_dung.so_tep} tệp` : <span className="muted">không có</span>}</div>
              <div className="muted">Robot: {r.ghi_chu_robot}{r.so_lan > 1 ? ` · đã nộp ${r.so_lan} lần, giờ nộp lần đầu giữ nguyên` : ""}
                {r.noi_dung.lich_su_xem.map((h: any, i: number) => <span key={i}> · {h.hanh_dong === "bo_sung" ? `trả bổ sung (lần ${h.lan_nop}): ${h.ly_do}` : `đã xem${h.diem != null ? ` · ${h.diem}đ` : ""}`} — {h.boi}</span>)}</div>
              {r.xem_xet_duoc && <div style={{ borderTop: "1px solid var(--line)", paddingTop: 8, display: "grid", gap: 6 }}>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "end" }}>
                  <label>Điểm (không bắt buộc)<input type="number" min={0} max={10} step={0.5} value={diem} placeholder={String(r.diem_robot ?? "")} onChange={(e) => setDiem(e.target.value)} style={{ width: 90 }} /></label>
                  <label style={{ flex: 1, minWidth: 220 }}>Nhận xét / lý do trả bổ sung<input value={ly} onChange={(e) => setLy(e.target.value)} placeholder="Bắt buộc khi trả bổ sung" /></label></div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                  <button className="act teal" style={{ margin: 0 }} onClick={() => xem(r, "da_xem")}>Đã xem</button>
                  <button className="act orange" style={{ margin: 0 }} disabled={!ly.trim()} onClick={() => xem(r, "bo_sung")}>Yêu cầu bổ sung</button>
                  <span className="muted">Duyệt nội dung không chốt công.</span></div>
                <details><summary className="muted" style={{ cursor: "pointer" }}>Giao hỗ trợ cho một người trong phòng…</summary>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "end", marginTop: 6 }}>
                    <label>Người nhận<select value={giao.nguoi} onChange={(e) => setGiao({ ...giao, nguoi: e.target.value })}><option value="">— chọn —</option>
                      {d.nguoi_giao_duoc.filter((n: any) => n.user_id !== r.user_id).map((n: any) => <option key={n.user_id} value={n.user_id}>{n.ten} · {n.phong_ten}</option>)}</select></label>
                    <label style={{ flex: 1, minWidth: 200 }}>Việc cần hỗ trợ<input value={giao.noi_dung} onChange={(e) => setGiao({ ...giao, noi_dung: e.target.value })} /></label>
                    <label>Hạn<input type="date" value={giao.han} onChange={(e) => setGiao({ ...giao, han: e.target.value })} /></label>
                    <button className="act grey" style={{ margin: 0 }} disabled={!giao.nguoi || !giao.noi_dung.trim()} onClick={() => giaoHoTro(r)}>Giao hỗ trợ</button></div></details>
              </div>}
              {r.tu_minh && <div className="muted">Báo cáo của chính bạn — cấp trên xem xét.</div>}
            </div></td></tr>}
          </>) : <tr><td colSpan={8} className="muted">Không có dòng nào khớp bộ lọc.</td></tr>}</tbody></table></div>
      <div style={{ display: "grid", gap: 12 }}>
        <ViecPanel title="Vướng mắc chuyển đến phòng bạn" ds={viec.den_phong} onDone={load}
          note="Từ Phần 4 báo cáo của phòng khác và việc hỗ trợ đã giao. Có hạn và trạng thái riêng; không tự đóng khi báo cáo được xem." />
        {viec.cua_toi.length > 0 && <ViecPanel title="Việc giao cho bạn" ds={viec.cua_toi} onDone={load} />}
      </div>
    </div>
  </>);
}

function Reports() {
  const { xacNhan, nhap, hop } = useHoi();
  const { user, toast } = useShell();
  const role = user?.role || "";
  const isMgr = MANAGERS.includes(role);
  const xemXet = NGUOI_XEM.includes(role);
  const [tab, setTab] = useState(xemXet ? "all" : "mine");
  const [period, setPeriod] = useState(thisMonth());
  const [rows, setRows] = useState<any[]>([]);
  const [sum, setSum] = useState<any>(null);
  const [shifts, setShifts] = useState<any[]>([]);
  const [emps, setEmps] = useState<any[]>([]);
  const [fs, setFs] = useState({ shift_date: today(), slot: "toi", employee_id: "" });
  const load = useCallback(() => {
    if (tab === "mine") api(`/daily-reports?mine=1&period=${period}`).then(setRows);
    if (tab === "all" && isMgr) api(`/daily-reports/summary?period=${period}`).then(setSum).catch(() => {});
    if (tab === "shifts") { api(`/page-shifts?period=${period}`).then(setShifts); if (isMgr) api("/employees?department=kd_le").then(setEmps).catch(() => {}); }
  }, [tab, period, isMgr]);
  useEffect(() => { load(); }, [load]);
  const post = async (path: string, json?: any) => { try { const r = await api(path, { method: "POST", json }); toast(r.message || "Xong"); load(); return r; } catch (x) { toast(errMsg(x), true); } };

  return (<>{hop}
    <h1>Báo cáo công việc (Điều 12) &amp; ca trực page</h1>
    <p className="muted">Mọi nhân viên văn phòng (trừ HDV, tài xế, Ban TGĐ) nộp báo cáo 5 phần <b>trước 0 giờ ngày kế tiếp</b> mỗi ngày làm việc (Thứ Hai – Thứ Bảy); nghỉ cả ngày đã duyệt thì không phải nộp. Robot chấm điểm nháp, trưởng phòng chấm chính thức; thiếu 1 ngày → nhắc nhở, 2 ngày liên tiếp → chuyển HCNS. Xếp loại tháng A/B/C/D là cảnh báo sớm, căn cứ đánh giá 3 tháng.</p>
    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
      {[["mine", "Báo cáo của tôi"], ...(xemXet ? [["all", role === "tn_kd" ? "Tổng hợp nhóm" : "Tổng hợp phòng"]] : []), ...(role === "chutich" ? [["kiem", "Kiêm nhiệm"]] : []), ["shifts", "Ca trực page"]].map(([k, l]) => <button key={k} className={"act " + (tab === k ? "" : "grey")} style={{ margin: 0 }} onClick={() => setTab(k)}>{l}</button>)}
      <label style={{ marginLeft: "auto" }}>Tháng <input type="month" value={period} onChange={(e) => setPeriod(e.target.value)} /></label>
    </div>

    {tab === "mine" && <DailyForm onDone={load} rows={rows} />}
    {tab === "kiem" && role === "chutich" && <KiemNhiem />}

    {tab === "all" && <>
      <TongHop />
      {sum && <><h2>Xếp loại tháng {period} ({sum.work_days} ngày làm việc tính đến nay)</h2>
        <div className="panel wrap"><table><thead><tr><th>Mã</th><th>Họ tên</th><th>Phòng</th><th>Đã nộp</th><th>Đúng giờ</th><th>TP đã chấm</th><th>Thiếu</th><th>Điểm BQ</th><th>Xếp loại</th></tr></thead>
          <tbody>{sum.rows.map((r: any) => <tr key={r.code}><td className="mono">{r.code}</td><td><b>{r.name}</b></td><td>{r.department}</td><td>{r.submitted}/{r.work_days}</td><td>{r.on_time}</td><td>{r.reviewed}</td><td>{r.missing ? <Tag cls={r.missing >= 2 ? "red" : "warn"}>{r.missing}</Tag> : "0"}</td><td>{r.avg}</td><td><Tag cls={r.grade === "A" ? "ok" : r.grade === "B" ? "navy" : r.grade === "C" ? "warn" : "red"}>{r.grade}</Tag></td></tr>)}</tbody></table></div>
        {["cntt", "hcns", "tgd"].includes(role) && <button className="act orange" onClick={() => post("/daily-reports/check-missing")}>Robot rà thiếu báo cáo</button>}</>}
    </>}

    {tab === "shifts" && <>
      {["gd_kd", "cntt"].includes(role) && <div className="panel"><h2>Phân ca trực page (GĐ KD)</h2><div className="grid">
        <label>Ngày<input type="date" value={fs.shift_date} onChange={(e) => setFs({ ...fs, shift_date: e.target.value })} /></label>
        <label>Ca<select value={fs.slot} onChange={(e) => setFs({ ...fs, slot: e.target.value })}><option value="sang">Sáng</option><option value="chieu">Chiều</option><option value="toi">Tối</option></select></label>
        <label>Nhân viên<select value={fs.employee_id} onChange={(e) => setFs({ ...fs, employee_id: e.target.value })}><option value="">–</option>{emps.map((e) => <option key={e.id} value={e.id}>{e.full_name}</option>)}</select></label>
      </div><button className="act" disabled={!fs.employee_id} onClick={() => post("/page-shifts", { ...fs, employee_id: Number(fs.employee_id) })}>Phân ca</button></div>}
      <div className="panel wrap"><table><thead><tr><th>Ngày</th><th>Ca</th><th>Nhân viên</th><th>Lượt sót &gt;5 phút</th><th>Chế tài</th><th>Ghi chú robot</th><th>NV phản hồi</th><th></th></tr></thead>
        <tbody>{shifts.length ? shifts.map((s) => <tr key={s.id}><td>{fmtD(s.shift_date)}</td><td>{s.slot}</td><td>{s.employee}</td><td>{s.scanned_at ? s.missed : <span className="muted">chưa quét</span>}</td><td>{s.penalty ? <Tag cls="red">−{vnd(s.penalty)}</Tag> : s.scanned_at ? <Tag cls="ok">0</Tag> : ""}{s.kicked && <Tag cls="red">loại ca</Tag>}</td><td className="muted">{s.missed_note}</td><td className="muted">{s.responded}</td>
          <td>{["cntt", "gd_kd"].includes(role) && <button className="act grey" style={{ margin: 0 }} onClick={async () => { const n = await nhap("Số lượt sót > 5 phút:", String(s.missed)); if (n !== null) post(`/page-shifts/${s.id}/scan`, { missed: Number(n), note: await nhap("Ghi chú:") || "" }); }}>Quét</button>}{s.employee_id && <button className="act grey" style={{ margin: "0 0 0 4px" }} onClick={async () => { const t = await nhap("Phản hồi (trong 3 ngày):"); if (t) post(`/page-shifts/${s.id}/respond`, { text: t }); }}>Phản hồi</button>}</td></tr>) : <tr><td colSpan={8} className="muted">Chưa có ca trong tháng.</td></tr>}</tbody></table></div>
      <p className="muted">Cổng 11: 1–3 lượt −100.000/lượt; 4–5 lượt −200.000/lượt; ≥6 lượt loại khỏi ca tháng sau và điều chỉnh chỉ tiêu. Chỉ trừ vào hoa hồng (đã nối vào bảng lương).</p>
    </>}
  </>);
}
export default function Page() { return <Shell><Reports /></Shell>; }
