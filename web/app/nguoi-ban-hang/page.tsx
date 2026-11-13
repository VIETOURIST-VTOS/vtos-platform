"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import { useHoi } from "@/components/HopHoi";

/** Ai được bán hàng – nhân viên nào, và đối tác nào.
 *
 *  HAI THỨ KHÁC NHAU NẰM CHUNG MỘT MÀN HÌNH, có chủ ý: cả hai đều trả lời đúng một câu – "ai có thể
 *  đứng tên một booking". Tách hai màn hình thì người đi tìm phải đoán xem đối tác nằm ở đâu.
 *
 *  Khối Kinh doanh KHÔNG có ô tick: bán hàng là việc đương nhiên của họ và họ luôn có chỉ tiêu. Ô
 *  tick chỉ dành cho người bộ phận khác, và bật nó không kéo ai vào bảng xếp hạng kinh doanh –
 *  quyền BÁN khác nghĩa vụ ĐẠT CHỈ TIÊU.
 */
const LOAI: [string, string][] = [["ghep_le", "Đối tác ghép lẻ"], ["dai_ly", "Đại lý"],
                                  ["san_ve", "Sàn bán vé"], ["ctv_ban_hang", "CTV bán hàng"], ["khac", "Khác"]];

function NguoiBanHang() {
  const { xacNhan, nhap, hop } = useHoi();
  const { user, toast } = useShell();
  const canWrite = ["chutich", "tgd", "hcns", "cntt"].includes(user?.role || "");
  const [d, setD] = useState<any>(null);
  const [tim, setTim] = useState("");
  const [dt, setDt] = useState<any>({ ma: "", ten: "", loai: "ghep_le", lien_he: "", dien_thoai: "", ma_so_thue: "", hieu_luc_tu: "", ghi_chu: "" });

  const load = useCallback(() => { api("/nguoi-ban-hang").then(setD).catch(() => {}); }, []);
  useEffect(() => { load(); }, [load]);

  const post = async (path: string, json?: any) => {
    try { const r = await api(path, { method: "POST", json }); toast(r.message || "Đã ghi"); load(); }
    catch (x) { toast(errMsg(x), true); }
  };
  const doiQuyen = async (r: any, duoc: boolean) => {
    const ly = await nhap(`${duoc ? "Mở" : "Thu"} quyền bán hàng của ${r.ho_ten}. Lý do:`);
    if (!ly) return;
    post("/nguoi-ban-hang/quyen-ban", { user_id: r.user_id, duoc, ly_do: ly });
  };
  const loc = (ds: any[]) => {
    const q = tim.trim().toLowerCase();
    return !q ? ds : ds.filter((r: any) => (r.ho_ten || "").toLowerCase().includes(q) || (r.tai_khoan || "").toLowerCase().includes(q));
  };

  const khoi = d?.khoi_kinh_doanh || [], bat = d?.ngoai_khoi_duoc_ban || [], tat = d?.ngoai_khoi_chua_bat || [];

  return (<>{hop}
    <h1>Người bán hàng</h1>
    <p className="muted">Ai có thể đứng tên một booking: nhân viên khối Kinh doanh, người bộ phận khác được mở quyền bán,
      và đối tác ngoài công ty. <b>Đối tác không có tài khoản đăng nhập</b> – họ là một danh mục riêng, không phải người dùng hệ thống.</p>

    <div className="panel wrap"><h2>Khối Kinh doanh · {khoi.length} người</h2>
      <p className="muted" style={{ marginTop: -4 }}>Bán hàng là việc đương nhiên, không cần bật gì. Đây là những người <b>có chỉ tiêu</b>.</p>
      <table><thead><tr><th>Họ tên</th><th>Tài khoản</th><th>Vai</th><th>Mã NV</th></tr></thead>
        <tbody>{loc(khoi).map((r: any) => <tr key={r.user_id}>
          <td><b>{r.ho_ten}</b></td><td className="mono">{r.tai_khoan}</td><td>{r.vai}</td>
          <td className="mono">{r.ma_nv || <span className="muted">–</span>}</td></tr>)}</tbody></table></div>

    <div className="panel wrap"><h2>Ngoài khối, đã mở quyền bán · {bat.length} người</h2>
      <p className="muted" style={{ marginTop: -4 }}>Hướng dẫn viên, điều hành, visa… Doanh thu của họ hiện <b>riêng một ngăn</b>,
        không vào chỉ tiêu ai, trừ khi anh giao chỉ tiêu riêng cho họ.</p>
      <table><thead><tr><th>Họ tên</th><th>Tài khoản</th><th>Vai</th>{canWrite && <th></th>}</tr></thead>
        <tbody>{loc(bat).map((r: any) => <tr key={r.user_id}>
          <td><b>{r.ho_ten}</b></td><td className="mono">{r.tai_khoan}</td><td><Tag cls="ok">{r.vai}</Tag></td>
          {canWrite && <td><button className="act" onClick={() => doiQuyen(r, false)}>Thu quyền</button></td>}</tr>)}
        {!bat.length && <tr><td colSpan={canWrite ? 4 : 3} className="muted">Chưa mở cho ai ngoài khối Kinh doanh.</td></tr>}
        </tbody></table></div>

    {canWrite && <div className="panel wrap"><h2>Ngoài khối, chưa mở · {tat.length} người</h2>
      <div className="grid"><label>Tìm tên<input value={tim} placeholder="gõ tên hoặc tài khoản" onChange={(e) => setTim(e.target.value)} /></label></div>
      <table><thead><tr><th>Họ tên</th><th>Tài khoản</th><th>Vai</th><th></th></tr></thead>
        <tbody>{loc(tat).slice(0, 40).map((r: any) => <tr key={r.user_id}>
          <td>{r.ho_ten}</td><td className="mono">{r.tai_khoan}</td><td>{r.vai}</td>
          <td><button className="act" onClick={() => doiQuyen(r, true)}>Mở quyền bán</button></td></tr>)}</tbody></table>
      <p className="muted">Đang hiện tối đa 40 người – gõ tên vào ô tìm để thu hẹp.</p></div>}

    <div className="panel wrap"><h2>Đối tác bán hàng</h2>
      <table><thead><tr><th>Mã</th><th>Tên</th><th>Loại</th><th>Liên hệ</th><th>Hiệu lực</th><th>Trạng thái</th>{canWrite && <th></th>}</tr></thead>
        <tbody>{(d?.doi_tac || []).map((r: any) => <tr key={r.id} style={{ opacity: r.con_hop_tac ? 1 : 0.55 }}>
          <td className="mono"><b>{r.ma}</b></td><td>{r.ten}</td><td>{r.loai_nhan}</td>
          <td>{r.lien_he}{r.dien_thoai ? ` · ${r.dien_thoai}` : ""}</td>
          <td className="mono">{r.hieu_luc_tu}{r.hieu_luc_den ? ` → ${r.hieu_luc_den}` : ""}</td>
          <td>{r.con_hop_tac ? <Tag cls="ok">Đang hợp tác</Tag> : <Tag cls="red">Đã dừng</Tag>}</td>
          {canWrite && <td>{r.con_hop_tac && <button className="act" onClick={async () => {
            const n = await nhap("Dừng hợp tác từ ngày nào? (2026-09-30)"); if (!n) return;
            const ly = await nhap("Lý do dừng:"); if (!ly) return;
            post(`/nguoi-ban-hang/doi-tac/${r.id}/dong`, { den_ngay: n, ly_do: ly });
          }}>Dừng</button>}</td>}
        </tr>)}
        {!(d?.doi_tac || []).length && <tr><td colSpan={canWrite ? 7 : 6} className="muted">Chưa khai đối tác nào.</td></tr>}
        </tbody></table>
      <p className="muted">Doanh thu đối tác <b>vào tổng của công ty</b> và hiện thành một dòng riêng, nhưng <b>không vào chỉ tiêu ai</b>.
        Khác hẳn với “chưa xác định người bán”: một bên là đã biết ai bán, bên kia là chưa biết.</p></div>

    {canWrite && <div className="panel"><h2>Thêm đối tác</h2>
      <div className="grid">
        <label>Mã<input value={dt.ma} placeholder="JTV" onChange={(e) => setDt({ ...dt, ma: e.target.value })} /></label>
        <label>Tên<input value={dt.ten} placeholder="Công ty J Travel" onChange={(e) => setDt({ ...dt, ten: e.target.value })} /></label>
        <label>Loại hợp tác<select value={dt.loai} onChange={(e) => setDt({ ...dt, loai: e.target.value })}>
          {LOAI.map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Người liên hệ<input value={dt.lien_he} onChange={(e) => setDt({ ...dt, lien_he: e.target.value })} /></label>
        <label>Điện thoại<input value={dt.dien_thoai} onChange={(e) => setDt({ ...dt, dien_thoai: e.target.value })} /></label>
        <label>Mã số thuế<input value={dt.ma_so_thue} onChange={(e) => setDt({ ...dt, ma_so_thue: e.target.value })} /></label>
        <label>Hợp tác từ<input type="date" value={dt.hieu_luc_tu} onChange={(e) => setDt({ ...dt, hieu_luc_tu: e.target.value })} /></label>
      </div>
      <button className="act orange" onClick={() => post("/nguoi-ban-hang/doi-tac", { ...dt, hieu_luc_tu: dt.hieu_luc_tu || null })}>Thêm đối tác</button>
      <p className="muted">Đối tác <b>không có mật khẩu và không đăng nhập được</b> – đó là lý do họ nằm ở danh mục riêng
        chứ không phải một tài khoản nhân viên. Dừng hợp tác thì đóng lại, không xoá, để mọi booking cũ còn nghĩa.</p>
    </div>}
  </>);
}

export default function Page() { return <Shell><NguoiBanHang /></Shell>; }
