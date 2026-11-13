"use client";
import { useCallback, useEffect, useState } from "react";
import { useShell } from "@/components/Shell";
import { api, vnd, soTien } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import { useHoi } from "@/components/HopHoi";

/** Chi phí kỳ đội xe — KHỐI DÙNG CHUNG, không phải mã mới.
 *
 *  Đây ĐÚNG LÀ tab «Chi phí kỳ» của màn Lãi lỗ đội xe (/lai-lo-doi-xe), chuyển nguyên văn ra
 *  thành một mảnh, để màn Bàn làm việc (/xe) gắn lại CHÍNH NÓ chứ không dựng một form thứ hai.
 *
 *  Anh Tuấn chốt 09/11/2026: "không viết mới, chỉ kéo từ trang có sẵn". Lý do không phải đỡ công:
 *  hai form cùng ghi vào POST /fleet/chi-phi-ky là hai chỗ để luật nhập lệch nhau ở lần sửa thứ
 *  nhất — đúng kiểu hỏng mà kho này đã cấm khi cấm chép ma trận quyền ("chép là để hai nơi trôi
 *  khỏi nhau lần nữa"). Một khối, hai màn gắn: sửa luật nhập một chỗ là cả hai màn đổi theo.
 *
 *  Phần JSX bên dưới là bản CHUYỂN NGUYÊN VĂN, cố ý không làm đẹp lại: diff của lần tách phải
 *  đọc ra được là "dời chỗ", không phải "viết lại".
 *
 *  `onDoiSo` để màn đang gắn mảnh tự đọc lại SỐ CỦA NÓ sau khi ghi hoặc gỡ. Bàn làm việc có hàng
 *  đợi và bảng lợi nhuận đọc cùng nguồn với sổ chi phí kỳ; ghi xong mà bàn chưa đổi thì giám đốc
 *  tưởng mình ghi trượt và ghi lần thứ hai. */
export default function ChiPhiKyPanel({ ky, onDoiSo }: { ky: string; onDoiSo?: () => void }) {
  const { xacNhan, nhap, hop } = useHoi();
  const { user, toast } = useShell();
  const [cp, setCp] = useState<any>(null);
  const [xe, setXe] = useState<any[]>([]);
  const [f, setF] = useState<any>(null);
  const [luu, setLuu] = useState(false);
  const canGhi = ["ketoan", "cntt", "gd_doi_xe"].includes(user?.role || "");

  const load = useCallback(async () => {
    try { setCp(await api(`/fleet/chi-phi-ky?ky=${ky}`)); }
    catch (e) { toast(errMsg(e), true); }
  }, [ky, toast]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { api("/fleet/xe").then((r: any) => setXe(r.rows || r)).catch(() => {}); }, []);

  const ghi = async () => {
    setLuu(true);
    try {
      const r = await api<any>("/fleet/chi-phi-ky", { method: "POST", json: {
        ky, nhom: f.nhom, so_tien: soTien(f.so_tien),
        vehicle_id: f.vehicle_id ? Number(f.vehicle_id) : null,
        mo_ta: f.mo_ta || "", chung_tu: f.chung_tu || "" } });
      toast(r.message); setF(null); await load(); onDoiSo?.();
    } catch (e) { toast(errMsg(e), true); } finally { setLuu(false); }
  };

  const go = async (id: number) => {
    const ly_do = await nhap("Gỡ khoản này khỏi kỳ vì lý do gì?\n\n" +
      "Một khoản chi phí biến mất khỏi báo cáo mà không ai biết vì sao là cách nhanh nhất làm cho lãi " +
      "lỗ tháng không đối chiếu được với tháng trước.");
    if (!ly_do || !ly_do.trim()) return;
    try { const r = await api<any>(`/fleet/chi-phi-ky/${id}?ly_do=${encodeURIComponent(ly_do)}`,
                                   { method: "DELETE" });
          toast(r.message); await load(); onDoiSo?.(); }
    catch (e) { toast(errMsg(e), true); }
  };

  const nhomCua = (ma: string) => (cp?.nhom || []).find((n: any) => n.ma === ma);

  return (<>{hop}
    {canGhi && <div className="panel">
      <h2>Ghi chi phí kỳ {ky}</h2>
      <p className="muted">Khoản không gắn vào chuyến nào: bảo hiểm, đăng kiểm, lương tài xế, wifi,
        phân bổ chi phí trả trước, phí bãi, lãi vay, BHXH. Nhóm nào thuộc <b>xe</b> thì bắt buộc chọn
        xe; nhóm nào thuộc <b>đội</b> thì không gắn vào xe nào.</p>
      {!f && <button className="act" onClick={() => setF({ nhom: "", so_tien: "", vehicle_id: "",
                                                           mo_ta: "", chung_tu: "" })}>+ Thêm khoản</button>}
      {f && <>
        <div className="grid2">
          <label>Nhóm chi phí
            <select value={f.nhom} onChange={(e) => setF({ ...f, nhom: e.target.value, vehicle_id: "" })}>
              <option value="">— chọn nhóm —</option>
              {(cp?.nhom || []).map((n: any) =>
                <option key={n.ma} value={n.ma}>{n.ten} ({n.pham_vi === "xe" ? "theo xe" : "cả đội"})</option>)}
            </select></label>
          {nhomCua(f.nhom)?.pham_vi === "xe" && <label>Xe
            <select value={f.vehicle_id} onChange={(e) => setF({ ...f, vehicle_id: e.target.value })}>
              <option value="">— chọn xe —</option>
              {xe.map((v: any) => <option key={v.id} value={v.id}>{v.plate}</option>)}
            </select></label>}
          <label>Số tiền
            <input type="number" step={1000} value={f.so_tien}
                   onChange={(e) => setF({ ...f, so_tien: e.target.value })} /></label>
          <label>Diễn giải
            <input value={f.mo_ta} placeholder="VD: Bảo hiểm TNDS tháng 9"
                   onChange={(e) => setF({ ...f, mo_ta: e.target.value })} /></label>
          <label>Chứng từ
            <input value={f.chung_tu} onChange={(e) => setF({ ...f, chung_tu: e.target.value })} /></label>
        </div>
        <button className="act teal" disabled={luu || !f.nhom || !f.so_tien} onClick={ghi}>
          {luu ? "Đang ghi…" : "Ghi vào kỳ"}</button>{" "}
        <button className="act grey" onClick={() => setF(null)}>Đóng</button>
      </>}
    </div>}
    <div className="panel wrap">
      <h2>Các khoản đã ghi trong kỳ</h2>
      <table><thead><tr><th>Nhóm</th><th>Phạm vi</th><th>Xe</th><th>Diễn giải</th>
        <th className="num">Số tiền</th><th>Người ghi</th>{canGhi && <th></th>}</tr></thead>
        <tbody>{cp?.rows?.length ? cp.rows.map((r: any) => <tr key={r.id}>
          <td>{r.nhom_ten}</td>
          <td>{r.pham_vi === "xe" ? <Tag cls="ok">theo xe</Tag> : <Tag cls="navy">cả đội</Tag>}</td>
          <td className="muted">{r.xe || "—"}</td><td className="muted">{r.mo_ta}</td>
          <td className="num">{vnd(r.so_tien)}</td><td className="muted">{r.boi}</td>
          {canGhi && <td><button className="act grey" style={{ margin: 0 }}
                                 onClick={() => go(r.id)}>Gỡ</button></td>}
        </tr>) : <tr><td colSpan={canGhi ? 7 : 6} className="muted">Kỳ này chưa ghi khoản nào.</td></tr>}</tbody></table>
    </div>
  </>);
}
