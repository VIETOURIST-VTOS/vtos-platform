"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import { GROUPS } from "@/components/Shell";

/** QL-1 · Ô CẤP NGOẠI LỆ QUYỀN CÓ THỜI HẠN (Chủ tịch duyệt bản xem thử 17/10/2026).
 *
 *  Cửa máy chủ `POST /access/grants` có từ lâu, nhưng màn hình chỉ LIỆT KÊ và THU HỒI — không có
 *  chỗ nào để cấp. Ngày 17/10, cấp quyền duyệt công bố nhận xét cho anh Thắng phải chạy lệnh tay
 *  trong trình duyệt. Một cửa máy chủ không có ô nhập trên màn hình là một việc còn thiếu.
 *
 *  Ba điều Chủ tịch chốt: (1) mở được từ đầu khối «Ngoại lệ» VÀ từ từng dòng tài khoản (điền sẵn
 *  người nhận); (2) cấp được cả NĂNG LỰC (bấm được) lẫn MÀN HÌNH (vào được); (3) hạn mặc định +90
 *  ngày, đúng mức tối đa của máy chủ. KHÔNG có ô «không thời hạn»: quyền không hạn không tự thu về.
 *
 *  Màn hình KHÔNG gõ lại luật nào: danh sách năng lực, danh sách màn hình và số ngày tối đa đều lấy
 *  từ `GET /access/grants`. Máy chủ vẫn là người kiểm cuối — bước «Soát» ở đây chỉ để người bấm
 *  nhìn tận mắt mình sắp cấp gì cho ai, đến ngày nào, trước khi bấm. */

const homNay = () => new Date().toISOString().slice(0, 10);
const cong = (iso: string, n: number) => { const d = new Date(iso); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };
const vn = (s: string) => (s ? s.split("-").reverse().join("/") : "");
const soNgay = (a: string, b: string) => Math.round((new Date(b).getTime() - new Date(a).getTime()) / 864e5);

/** Tên màn hình theo đúng chữ trên thanh dọc — không có thì in đường dẫn, vẫn đúng. */
function tenManHinh(): Record<string, string> {
  const m: Record<string, string> = {};
  for (const g of GROUPS as any[]) for (const b of g.blocks || []) {
    if (Array.isArray(b)) m[String(b[1]).split("?")[0]] = b[0];
    else for (const [l, h] of b.items || []) m[String(h).split("?")[0]] = l;
  }
  return m;
}

export default function CapNgoaiLe({ uidDau, dsNguoi, meta, onClose, onDone }: {
  uidDau: number | null;               // mở từ một dòng tài khoản thì điền sẵn người ấy
  dsNguoi: any[];                       // acc.rows
  meta: any;                            // payload của GET /access/grants
  onClose: () => void;
  onDone: (msg: string) => void;
}) {
  const boc = useRef<HTMLDivElement>(null);
  const toiDa: number = meta?.max_days || 90;
  const [uid, setUid] = useState<string>(uidDau ? String(uidDau) : "");
  const [kind, setKind] = useState<string>("capability");
  const [value, setValue] = useState("");
  const [tu, setTu] = useState(homNay());
  const [den, setDen] = useState(cong(homNay(), toiDa));
  const [ly, setLy] = useState("");
  const [soat, setSoat] = useState<{ ok: boolean; noi: string[] } | null>(null);
  const [dang, setDang] = useState(false);
  const ten = useMemo(tenManHinh, []);

  // Mở từ dòng thứ 100 của bảng thì mẫu phải hiện trước mắt — bài học HS-8: một ô mở ra ngoài tầm
  // nhìn thì về mặt người dùng là không mở.
  useEffect(() => { boc.current?.scrollIntoView({ block: "start", behavior: "smooth" }); }, [uidDau]);
  useEffect(() => { setUid(uidDau ? String(uidDau) : ""); setSoat(null); }, [uidDau]);

  const nguoi = dsNguoi.find((r: any) => String(r.id) === uid);
  const chon: [string, string][] = kind === "capability"
    ? Object.entries(meta?.capabilities || {}) as [string, string][]
    : (meta?.man_hinh || []).map((p: string) => [p, ten[p] ? `${ten[p]} (${p})` : p] as [string, string]);
  const tenQuyen = chon.find(([k]) => k === value)?.[1] || value;
  const doi = (f: () => void) => { f(); setSoat(null); };

  const kiem = () => {
    const loi: string[] = [];
    if (!nguoi) loi.push("Chọn người nhận.");
    if (!value) loi.push(kind === "capability" ? "Chọn năng lực cấp." : "Chọn màn hình cấp.");
    if (!den) loi.push("Ghi ngày hết hạn.");
    else if (den < tu) loi.push("Ngày hết hạn phải sau ngày bắt đầu.");
    else if (soNgay(tu, den) > toiDa) loi.push(`Tối đa ${toiDa} ngày — cần lâu hơn thì đổi vai trò, hoặc sửa ma trận quyền.`);
    if (!ly.trim()) loi.push("Phải ghi lý do cấp quyền.");
    if (nguoi && value && (meta?.rows || []).some((g: any) =>
      g.user_id === nguoi.id && g.kind === kind && g.value === value && g.hieu_luc))
      loi.push(`${nguoi.full_name} đang có quyền này còn hiệu lực — thu hồi dòng cũ trước nếu muốn đổi hạn.`);
    if (loi.length) { setSoat({ ok: false, noi: loi }); return false; }
    setSoat({ ok: true, noi: [
      `Sẽ cấp cho ${nguoi.full_name} (${nguoi.username}, ${nguoi.role_name || nguoi.role}): ${tenQuyen}.`,
      `Từ ${vn(tu)} đến ${vn(den)} — ${soNgay(tu, den)} ngày. Người duyệt ghi là tài khoản đang đăng nhập.`,
    ] });
    return true;
  };

  const cap = async () => {
    if (!kiem()) return;
    setDang(true);
    try {
      const r: any = await api("/access/grants", { method: "POST", json: {
        user_id: nguoi.id, kind, value, from_date: tu, to_date: den, reason: ly.trim() } });
      onDone(r.message || "Đã cấp");
    } catch (e) { setSoat({ ok: false, noi: [errMsg(e)] }); } finally { setDang(false); }
  };

  return (<div ref={boc} className="panel" style={{ borderStyle: "dashed" }}>
    <h3 style={{ marginTop: 0 }}>Cấp ngoại lệ quyền có thời hạn</h3>
    <p className="muted">Quyền cấp cho MỘT người, tự hết hiệu lực đúng ngày. Tối đa {toiDa} ngày; cần lâu hơn thì đổi vai trò hoặc sửa ma trận quyền.</p>
    <div className="grid2">
      <label>Người nhận
        <select value={uid} onChange={(e) => doi(() => setUid(e.target.value))}>
          <option value="">– chọn tài khoản –</option>
          {dsNguoi.filter((r: any) => r.active).map((r: any) => <option key={r.id} value={r.id}>
            {r.full_name} · {r.username}</option>)}
        </select>
        {nguoi && <span className="muted">Vai hiện tại: {nguoi.role_name || nguoi.role}</span>}
      </label>
      <label>Loại
        <select value={kind} onChange={(e) => doi(() => { setKind(e.target.value); setValue(""); })}>
          {Object.entries(meta?.kinds || { capability: "Năng lực", menu: "Màn hình" }).map(([k, l]) =>
            <option key={k} value={k}>{String(l)}{k === "capability" ? " — bấm được" : " — vào được"}</option>)}
        </select>
      </label>
      <label style={{ gridColumn: "1 / -1" }}>{kind === "capability" ? "Năng lực" : "Màn hình"}
        <select value={value} onChange={(e) => doi(() => setValue(e.target.value))}>
          <option value="">– chọn –</option>
          {chon.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
      </label>
      <label>Từ ngày<input type="date" value={tu} onChange={(e) => doi(() => setTu(e.target.value))} /></label>
      <label>Đến ngày<input type="date" value={den} onChange={(e) => doi(() => setDen(e.target.value))} /></label>
      <label style={{ gridColumn: "1 / -1" }}>Lý do <span className="muted">(bắt buộc — tháng sau còn trả lời được vì sao người này có quyền ấy)</span>
        <textarea rows={2} value={ly} onChange={(e) => doi(() => setLy(e.target.value))}
          placeholder="Ví dụ: người thứ ba duyệt đăng nhận xét, theo Đợt HD-DG3" /></label>
    </div>
    {soat && <div className={"gate " + (soat.ok ? "pass" : "fail")} style={{ marginTop: 10 }}>
      {soat.noi.map((x, i) => <div key={i}>{x}</div>)}</div>}
    <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
      <button className="act grey" style={{ margin: 0 }} disabled={dang} onClick={kiem}>Soát trước khi cấp</button>
      <button className="act teal" style={{ margin: 0 }} disabled={dang || !soat?.ok} onClick={cap}>
        {dang ? "Đang cấp…" : "Xác nhận cấp"}</button>
      <button className="act grey" style={{ margin: 0 }} onClick={onClose}>Thôi</button>
      {soat?.ok && <Tag cls="ok">đã soát</Tag>}
    </div>
  </div>);
}
