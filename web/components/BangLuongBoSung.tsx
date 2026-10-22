"use client";
import { useCallback, useEffect, useState } from "react";
import { useShell } from "@/components/Shell";
import { api, vnd, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** CN-2 · Giữ lương và bảng lương bổ sung — Chủ tịch chốt 21/10/2026.
 *
 *  Phòng chưa được duyệt công lúc ký bảng chính thì lương phòng ấy bị GIỮ. Công duyệt rồi, HCNS lập
 *  bảng bổ sung; bảng ấy đi cùng chuỗi: máy kiểm cơ sở → HCNS kiểm → Chủ tịch/TGĐ ký → chi riêng.
 *  Ẩn nút ở đây KHÔNG phải hàng rào — hàng rào ở máy chủ (services/giu_luong.py).
 */
const MAU: Record<string, string> = { nhap: "warn", da_kiem_co_so: "navy", hcns_kiem: "warn", da_ky: "ok" };

export default function BangLuongBoSung({ period, onChi }: { period: string; onChi?: () => void }) {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const [d, setD] = useState<any>(null);
  const tai = useCallback(() => {
    api(`/payroll-runs/${period}/bo-sung`).then(setD).catch(() => setD(null));
  }, [period]);
  useEffect(() => { tai(); }, [tai]);
  const bam = async (path: string, ok?: () => void) => {
    try { const r = await api<any>(path, { method: "POST" }); toast(r.message || "Xong"); tai(); ok?.(); }
    catch (e) { toast(errMsg(e), true); tai(); }
  };

  if (!d) return null;
  const giu = Object.entries(d.giu_lai || {});
  if (!giu.length && !d.bang.length) return null;
  return <div className="panel wrap">
    <h2>Giữ lương & bảng bổ sung · kỳ {period}</h2>
    <p className="muted">Phòng chưa được TGĐ duyệt công lúc ký bảng chính thì lương phòng ấy được giữ lại — không vào
      bản khoá, bút toán hay lệnh chi của bảng chính. Người bị giữ nhận chuông và tin Zalo; phiếu lương chỉ ghi «đang giữ».</p>
    {giu.length > 0 && <table><thead><tr><th>Phòng bị giữ</th><th className="num">Số người</th><th>Lý do lúc ký</th><th>Bảng bổ sung</th></tr></thead>
      <tbody>{giu.map(([p, g]: any) => <tr key={p}>
        <td>{p}</td><td className="num">{g.ma.length}</td><td className="muted">{g.ly_do} · {fmtDT(g.luc)}</td>
        <td>{g.bo_sung_so ? <Tag cls="ok">số {g.bo_sung_so}</Tag>
          : d.phong_lap_duoc.includes(p) ? <Tag cls="navy">công đã duyệt – lập được</Tag> : <Tag cls="red">chờ duyệt công</Tag>}</td>
      </tr>)}</tbody></table>}
    {role === "hcns" && d.phong_lap_duoc.length > 0 &&
      <button className="act teal" onClick={() => bam(`/payroll-runs/${period}/bo-sung`)}>
        Lập bảng bổ sung ({d.phong_lap_duoc.join(", ")})</button>}
    {d.bang.map((b: any) => <div key={b.so} style={{ marginTop: 10 }}>
      <p><b>Bảng bổ sung số {b.so}</b> · {b.phong.join(", ")} · {b.totals.so_nguoi} người · thực nhận {vnd(b.totals.thuc_nhan)}{" "}
        <Tag cls={MAU[b.status] || "warn"}>{b.status_ten}</Tag>
        {b.hcns_by && <span className="muted"> · HCNS {b.hcns_by} {fmtDT(b.hcns_at)}</span>}
        {b.ky_boi && <span className="muted"> · ký {b.ky_boi} {fmtDT(b.ky_luc)}</span>}</p>
      <div className="row" style={{ gap: 6, flexWrap: "wrap" }}>
        {["hcns", "cntt"].includes(role) && b.status === "nhap" &&
          <button className="act" onClick={() => bam(`/payroll-runs/${period}/bo-sung/${b.so}/kiem-co-so`)}>Chạy kiểm cơ sở</button>}
        {role === "hcns" && b.status === "da_kiem_co_so" &&
          <button className="act" onClick={() => bam(`/payroll-runs/${period}/bo-sung/${b.so}/advance`)}>HCNS kiểm xong – trình ký</button>}
        {["chutich", "tgd"].includes(role) && b.status === "hcns_kiem" &&
          <button className="act teal" onClick={() => bam(`/payroll-runs/${period}/bo-sung/${b.so}/advance`)}>Ký & khoá bảng bổ sung</button>}
        {["ketoan", "cntt"].includes(role) && b.status === "da_ky" &&
          <button className="act grey" onClick={() => bam(`/payroll-runs/${period}/chi?bo_sung=${b.so}`, onChi)}>Mở lần chi cho bảng bổ sung</button>}
      </div>
      <table><thead><tr><th>Mã</th><th>Họ tên</th><th className="num">Thực nhận</th></tr></thead>
        <tbody>{b.rows.map((r: any) => <tr key={r.ma}><td className="mono">{r.ma}</td><td>{r.ten}</td><td className="num">{vnd(r.thuc_nhan)}</td></tr>)}</tbody></table>
    </div>)}
  </div>;
}
