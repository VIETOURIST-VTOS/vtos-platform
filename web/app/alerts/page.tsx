"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import { ROLES } from "@/lib/meta";

// KS-4 · 11/9/2026. Đo trên hệ thống thật: 1.703 cảnh báo đang mở, 1.310 đỏ. Màn hình cũ đổ cả bảng
// ra một danh sách phẳng và cho mọi người một nút "Đóng" duy nhất, bấm là xong, không hỏi gì.
//
// Một danh sách 1.310 dòng đỏ thì không ai đọc dòng nào, và một nút đóng không hỏi gì là nút GIẤU
// VIỆC chứ không phải nút xử lý việc. Màn hình này đổi ba chỗ:
//   · NHẬN trước, ĐÓNG sau – nhận rồi thì dòng ấy có tên một người, không còn là việc của bốn vai trò
//   · đóng phải ghi BẰNG CHỨNG (≥10 ký tự): số chứng từ, mã bản ghi, hoặc lý do viết ra
//   · BỎ QUA là một nhánh riêng, có tên riêng, dành cho dữ liệu lịch sử – để "đã xử lý" và "không
//     phải việc nữa" không nằm chung một ô
const NHAN: Record<string, string> = {
  moi: "mới", dang_xu_ly: "đang xử lý", da_xu_ly: "đã xử lý", dong: "đã đóng", bo_qua: "bỏ qua",
};
const LOC: [string, string][] = [
  ["", "Tất cả"], ["moi", "Chưa ai nhận"], ["dang_xu_ly", "Đang xử lý"],
  ["moi,dang_xu_ly", "Còn phải làm"], ["dong,bo_qua", "Đã đóng"],
];

function Alerts() {
  const { user, toast } = useShell();
  const [rows, setRows] = useState<any[]>([]);
  const [tong, setTong] = useState(0);
  const [chamTran, setChamTran] = useState(false);
  const [trangThai, setTrangThai] = useState("moi,dang_xu_ly");
  const [cuaToi, setCuaToi] = useState(false);
  const [thang, setThang] = useState<any>(null);

  const load = useCallback(async () => {
    const q = new URLSearchParams();
    if (trangThai) q.set("trang_thai", trangThai);
    if (cuaToi) q.set("cua_toi", "1");
    const r = await api(`/alerts?${q}`);
    setRows(r.rows || []); setTong(r.tong || 0); setChamTran(!!r.cham_tran);
  }, [trangThai, cuaToi]);
  useEffect(() => { load().catch((x) => toast(errMsg(x), true)); }, [load]);
  // Thang bậc đòi nợ — cửa HẸP HƠN màn hình (Kinh doanh + Kế toán + BLĐ). 403 ở đây là câu trả
  // lời đúng, không phải sự cố: không vẽ khối này chứ không kêu lỗi đỏ.
  useEffect(() => { api("/alerts/thang-doi-no").then(setThang).catch(() => setThang(null)); }, []);

  const goi = async (path: string, json?: any) => {
    try { await api(path, { method: "POST", json }); load(); }
    catch (x) { toast(errMsg(x), true); }
  };
  const dong = (a: any, boQua: boolean) => {
    const hoi = boQua
      ? "Bỏ qua vì sao? (dữ liệu lịch sử, chuyến đã huỷ… – ít nhất 10 ký tự)"
      : "Đóng dựa vào đâu? (số chứng từ, mã bản ghi, hoặc lý do – ít nhất 10 ký tự)";
    const bc = (window.prompt(hoi) || "").trim();
    if (!bc) return;
    if (bc.length < 10) { toast("Bằng chứng phải ít nhất 10 ký tự.", true); return; }
    goi(`/alerts/${a.id}/resolve`, { bang_chung: bc, bo_qua: boQua });
  };

  return (<>
    <h1>Cảnh báo nghiệp vụ</h1>
    <p className="muted">
      {tong} cảnh báo{trangThai && ` ở trạng thái đang lọc`}
      {chamTran && ` — đang hiện ${rows.length} dòng đầu, còn nữa. Lọc hẹp lại để thấy phần còn lại.`}
    </p>
    <div className="panel" style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
      <select value={trangThai} onChange={(e) => setTrangThai(e.target.value)}>
        {LOC.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
      </select>
      <label><input type="checkbox" checked={cuaToi} onChange={(e) => setCuaToi(e.target.checked)} /> Chỉ việc tôi đã nhận</label>
      {["cntt", "tgd", "chutich"].includes(user?.role || "") &&
        <button className="act orange" onClick={() => goi("/robots/run")}>Chạy robot ngay</button>}
      {["cntt", "tgd", "chutich", "bks", "ketoan"].includes(user?.role || "") &&
        <button className="act grey" onClick={async () => {
          try { const r = await api("/robot/r9", { method: "POST" }); toast(`R9: phát hiện ${r.found}, cảnh báo mới ${r.new_alerts}`); load(); }
          catch (x) { toast(errMsg(x), true); }
        }}>R9 – quét bất thường</button>}
    </div>
    {/* THANG BẬC ĐÒI NỢ KHÁCH — Chủ tịch quyết 25/9/2026, câu 5. In ra để người nhận một cảnh
        báo bậc 2 hiểu vì sao nó tới tay mình, và để hai con số mốc ngày không nằm im trong cơ sở
        dữ liệu: tham số mà không ai nhìn thấy thì không ai sửa. */}
    {thang && <details className="panel"><summary><b>Thang bậc đòi nợ khách quá hạn</b> — {thang.moc_bac2_ngay} ngày lên cấp trên, {thang.moc_bac3_ngay} ngày lên lãnh đạo khối</summary>
      <table>
        <thead><tr><th>Mảng</th><th>Bậc 1 — ngay</th><th>Bậc 2 — sau {thang.moc_bac2_ngay} ngày</th><th>Bậc 3 — sau {thang.moc_bac3_ngay} ngày</th></tr></thead>
        <tbody>
          <tr><td><b>Kinh doanh Đoàn</b></td>{(thang.thang?.doan || []).map((v: string, i: number) => <td key={i}>{ROLES[v] || v}</td>)}</tr>
          <tr><td><b>Kinh doanh Lẻ</b></td>{(thang.thang?.le || []).map((v: string, i: number) => <td key={i}>{ROLES[v] || v}</td>)}</tr>
        </tbody>
      </table>
      <p className="muted">Một khoản nợ là <b>một dòng cảnh báo</b> — lên bậc là đổi người chịu trên chính dòng ấy,
        không sinh thêm dòng mới. Hai mốc ngày sửa ở màn hình <b>Chính sách</b> (tham số <code>no_khach_bac2_ngay</code>,
        <code> no_khach_bac3_ngay</code>).</p>
      {["gd_kd", "tp_kd", "sales_admin", "ptgd_doan", "ketoan", "cntt", "tgd", "chutich"].includes(user?.role || "") &&
        <button className="act grey" onClick={async () => {
          try {
            const r = await api("/alerts/thang-doi-no/quet", { method: "POST" });
            toast(`Bậc 1: ${r.bac_1} · bậc 2: ${r.bac_2} · bậc 3: ${r.bac_3}` +
                  (r.khong_ro_chu?.length ? ` — ${r.khong_ro_chu.length} khoản CHƯA BIẾT giao cho ai` : ""));
            load();
          } catch (x) { toast(errMsg(x), true); }
        }}>Quét lại thang bậc</button>}
    </details>}
    <div className="panel wrap"><table>
      <thead><tr>
        <th>Mức</th><th>Trạng thái</th><th>Loại</th><th>Tham chiếu</th><th>Nội dung</th>
        <th>Người nhận</th><th>Hạn</th><th>Lúc</th><th></th>
      </tr></thead>
      <tbody>{rows.length ? rows.map((a) => (
        <tr key={a.id} style={{ opacity: ["dong", "bo_qua"].includes(a.trang_thai) ? 0.5 : 1 }}>
          <td><Tag cls={a.level}>{a.level}</Tag></td>
          <td>{a.tre && <Tag cls="do">trễ</Tag>} {NHAN[a.trang_thai] || a.trang_thai}</td>
          {/* Bậc in CẠNH loại, không thay nó: "bậc 3" mà không biết bậc của việc gì thì vô nghĩa. */}
          <td>{a.kind}{a.bac ? <> <Tag cls={a.bac >= 3 ? "red" : "warn"}>bậc {a.bac}</Tag></> : null}</td>
          <td>{a.ref}</td><td style={{ whiteSpace: "pre-wrap" }}>{a.message}</td>
          <td className="muted">{a.nguoi_nhan || a.to_roles}</td>
          <td className="muted">{a.han_xu_ly ? fmtDT(a.han_xu_ly) : "—"}</td>
          <td className="muted">{fmtDT(a.created_at)}</td>
          <td style={{ whiteSpace: "nowrap" }}>
            {a.trang_thai === "moi" &&
              <button className="act" style={{ margin: 0 }} onClick={() => goi(`/alerts/${a.id}/nhan`)}>Nhận</button>}
            {["dang_xu_ly", "da_xu_ly"].includes(a.trang_thai) && <>
              <button className="act" style={{ margin: 0 }} onClick={() => dong(a, false)}>Đóng</button>{" "}
              <button className="act grey" style={{ margin: 0 }} onClick={() => dong(a, true)}>Bỏ qua</button>
            </>}
            {["dong", "bo_qua"].includes(a.trang_thai) &&
              <span className="muted" title={a.bang_chung || ""}>{NHAN[a.trang_thai]}</span>}
          </td>
        </tr>
      )) : <tr><td colSpan={9} className="muted">Không có cảnh báo nào khớp bộ lọc.</td></tr>}</tbody>
    </table></div>
  </>);
}
export default function Page() { return <Shell><Alerts /></Shell>; }
