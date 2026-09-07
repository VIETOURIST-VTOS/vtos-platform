"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Nhà cung cấp & đặt dịch vụ.
 *
 *  Màn hình này cố ý KHÔNG cho sửa số tài khoản trong form hồ sơ. Đổi tài khoản đi đường riêng, có người
 *  thứ hai xác nhận, vì đổi số tài khoản của một nhà cung cấp có thật rồi để hệ thống tự chuyển tiền vào đó
 *  là cách gian lận thanh toán phổ biến nhất. */
const n = (x: any) => Number(x || 0).toLocaleString("vi-VN");

function NhaCungCap() {
  const { user, toast } = useShell();
  const [ds, setDs] = useState<any[]>([]);
  const [don, setDon] = useState<any>(null);
  const [cho, setCho] = useState<any[]>([]);
  const [dm, setDm] = useState<any>(null);
  const [tours, setTours] = useState<any[]>([]);
  const [tab, setTab] = useState<"ncc" | "don" | "tk">("ncc");
  const [form, setForm] = useState<any>(null);       // form hồ sơ NCC
  const [formTk, setFormTk] = useState<any>(null);   // form đề nghị đổi tài khoản
  const [formDon, setFormDon] = useState<any>(null); // form đặt dịch vụ
  const [luu, setLuu] = useState(false);
  const canWrite = ["tp_dh", "nv_dh", "cntt", "ketoan"].includes(user?.role || "");
  const canDuyet = ["ketoan", "chutich", "tgd"].includes(user?.role || "");

  const load = useCallback(async () => {
    try {
      setDm(await api("/ncc/danh-muc"));
      setDs(await api("/ncc"));
      setDon(await api("/ncc/don"));
      setCho(await api("/ncc/doi-tai-khoan/cho-xac-nhan"));
      try { setTours(await api("/tours")); } catch { setTours([]); }
    } catch (e) { toast(errMsg(e), true); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const luuNcc = async () => {
    setLuu(true);
    try {
      if (form.id) { await api(`/ncc/${form.id}`, { method: "PUT", json: form }); toast("Đã cập nhật hồ sơ"); }
      else { const r = await api<any>("/ncc", { method: "POST", json: form }); toast(r.message); }
      setForm(null); load();
    } catch (e) { toast(errMsg(e), true); } finally { setLuu(false); }
  };

  const guiDoiTk = async () => {
    setLuu(true);
    try { const r = await api<any>(`/ncc/${formTk.id}/doi-tai-khoan`, { method: "POST", json: formTk });
          toast(r.message); setFormTk(null); load(); }
    catch (e) { toast(errMsg(e), true); } finally { setLuu(false); }
  };

  const xacNhanTk = async (cid: number, dong_y: boolean) => {
    const gc = prompt(dong_y ? "Ghi chú xác nhận (đã xác minh với nhà cung cấp bằng cách nào?):"
                             : "Lý do từ chối:");
    if (gc === null) return;
    try { const r = await api<any>(`/ncc/doi-tai-khoan/${cid}/xac-nhan`, { method: "POST", json: { dong_y, ghi_chu: gc } });
          toast(r.message); load(); }
    catch (e) { toast(errMsg(e), true); }
  };

  const luuDon = async () => {
    setLuu(true);
    try { const r = await api<any>("/ncc/don", { method: "POST", json: formDon }); toast(r.message);
          setFormDon(null); load(); }
    catch (e) { toast(errMsg(e), true); } finally { setLuu(false); }
  };

  const trangThai = async (did: number, status: string) => {
    let xn = "";
    if (status === "da_xac_nhan") {
      const v = prompt("Căn cứ nhà cung cấp đã xác nhận (số văn bản, email, tin nhắn):");
      if (!v) return; xn = v;
    }
    try { const r = await api<any>(`/ncc/don/${did}/trang-thai`, { method: "POST", json: { status, xac_nhan_ncc: xn } });
          toast(r.message); load(); }
    catch (e) { toast(errMsg(e), true); }
  };

  if (!dm) return <p className="muted">Đang tải…</p>;
  return (<>
    <h1>Nhà cung cấp & đặt dịch vụ</h1>
    <p className="muted">Số tài khoản nhà cung cấp <b>chỉ đổi được qua đề nghị có người thứ hai xác nhận</b>.
      Form hồ sơ dưới đây không có ô số tài khoản — đó là chủ ý, không phải thiếu sót.</p>

    {cho.length > 0 && <div className="panel" style={{ borderColor: "var(--orange)" }}>
      <b>{cho.length} đề nghị đổi số tài khoản đang chờ người thứ hai xác nhận.</b>
      <p className="muted">Số đang hiệu lực vẫn là số cũ — đừng chuyển tiền theo số mới khi chưa xác nhận.</p>
    </div>}

    <div style={{ display: "flex", gap: 8, margin: "10px 0" }}>
      {([["ncc", `Nhà cung cấp (${ds.length})`], ["don", `Đơn đặt dịch vụ (${don?.rows?.length || 0})`],
         ["tk", `Đổi tài khoản chờ xác nhận (${cho.length})`]] as const)
        .map(([k, ten]) => <button key={k} className={`act ${tab === k ? "teal" : "grey"}`} onClick={() => setTab(k as any)}>{ten}</button>)}
    </div>

    {tab === "ncc" && <>
      {form && <div className="panel">
        <h2>{form.id ? `Sửa hồ sơ ${form.code || ""}` : "Nhà cung cấp mới"}</h2>
        <div className="grid2">
          <label>Tên nhà cung cấp<input value={form.ten || ""} onChange={(e) => setForm({ ...form, ten: e.target.value })} /></label>
          <label>Loại
            <select value={form.loai || "khac"} onChange={(e) => setForm({ ...form, loai: e.target.value })}>
              {Object.entries(dm.loai_ncc).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}
            </select></label>
          <label>Mã số thuế<input value={form.ma_so_thue || ""} onChange={(e) => setForm({ ...form, ma_so_thue: e.target.value })} /></label>
          <label>Người liên hệ<input value={form.nguoi_lien_he || ""} onChange={(e) => setForm({ ...form, nguoi_lien_he: e.target.value })} /></label>
          <label>Điện thoại<input value={form.dien_thoai || ""} onChange={(e) => setForm({ ...form, dien_thoai: e.target.value })} /></label>
          <label>Email<input value={form.email || ""} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
          <label>Địa chỉ<input value={form.dia_chi || ""} onChange={(e) => setForm({ ...form, dia_chi: e.target.value })} /></label>
          <label>Điều khoản thanh toán<input value={form.dieu_khoan_tt || ""} onChange={(e) => setForm({ ...form, dieu_khoan_tt: e.target.value })} placeholder="VD: thanh toán trong 15 ngày sau tour" /></label>
          {!form.id && <>
            <label>Số tài khoản<input value={form.so_tai_khoan || ""} onChange={(e) => setForm({ ...form, so_tai_khoan: e.target.value })} /></label>
            <label>Ngân hàng<input value={form.ngan_hang || ""} onChange={(e) => setForm({ ...form, ngan_hang: e.target.value })} /></label>
            <label>Chủ tài khoản<input value={form.chu_tai_khoan || ""} onChange={(e) => setForm({ ...form, chu_tai_khoan: e.target.value })} /></label>
          </>}
        </div>
        {form.id && <p className="muted">Số tài khoản không sửa ở đây — dùng nút <b>Đổi tài khoản</b> trên dòng
          nhà cung cấp, và cần người thứ hai xác nhận.</p>}
        <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
          <button className="act teal" disabled={luu} onClick={luuNcc}>{luu ? "Đang lưu…" : "Lưu"}</button>
          <button className="act grey" onClick={() => setForm(null)}>Đóng</button>
        </div>
      </div>}

      {formTk && <div className="panel" style={{ borderColor: "var(--orange)" }}>
        <h2>Đề nghị đổi số tài khoản — {formTk.ten}</h2>
        <p className="muted">Đề nghị này <b>chưa có hiệu lực</b>. Số đang dùng để chi vẫn là
          <b> {formTk.so_tai_khoan || "(chưa có)"}</b> cho tới khi người thứ hai xác nhận.</p>
        <div className="grid2">
          <label>Số tài khoản mới<input value={formTk.so_tk_moi || ""} onChange={(e) => setFormTk({ ...formTk, so_tk_moi: e.target.value })} /></label>
          <label>Ngân hàng<input value={formTk.ngan_hang_moi || ""} onChange={(e) => setFormTk({ ...formTk, ngan_hang_moi: e.target.value })} /></label>
          <label>Chủ tài khoản<input value={formTk.chu_tk_moi || ""} onChange={(e) => setFormTk({ ...formTk, chu_tk_moi: e.target.value })} /></label>
          <label>Văn bản của NCC (bắt buộc)<input value={formTk.chung_tu || ""} onChange={(e) => setFormTk({ ...formTk, chung_tu: e.target.value })} placeholder="Số công văn / email thông báo" /></label>
        </div>
        <label>Lý do<input value={formTk.ly_do || ""} onChange={(e) => setFormTk({ ...formTk, ly_do: e.target.value })} /></label>
        <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
          <button className="act teal" disabled={luu} onClick={guiDoiTk}>Gửi đề nghị</button>
          <button className="act grey" onClick={() => setFormTk(null)}>Đóng</button>
        </div>
      </div>}

      <div className="panel wrap"><h2>Danh mục nhà cung cấp</h2>
        {canWrite && !form && <button className="act teal" style={{ marginBottom: 10 }}
          onClick={() => setForm({ loai: "khac" })}>+ Nhà cung cấp mới</button>}
        <table><thead><tr><th>Mã</th><th>Tên</th><th>Loại</th><th>MST</th><th>Liên hệ</th>
          <th>Tài khoản đang hiệu lực</th><th>Cảnh báo</th>{canWrite && <th></th>}</tr></thead>
          <tbody>{ds.length ? ds.map((s) => <tr key={s.id}>
            <td className="muted">{s.code}</td><td>{s.ten}</td><td className="muted">{s.loai_ten}</td>
            <td className="muted">{s.ma_so_thue || "—"}</td>
            <td className="muted">{s.nguoi_lien_he}{s.dien_thoai ? ` · ${s.dien_thoai}` : ""}</td>
            <td>{s.so_tai_khoan ? <>{s.so_tai_khoan}<div className="muted">{s.ngan_hang} · {s.chu_tai_khoan}</div></> : <span className="muted">chưa có</span>}</td>
            <td>{s.canh_bao.map((c: string, i: number) => <div key={i}><Tag cls="warn">{c}</Tag></div>)}</td>
            {canWrite && <td style={{ whiteSpace: "nowrap" }}>
              <button className="act grey" onClick={() => setForm({ ...s })}>Sửa</button>{" "}
              <button className="act grey" onClick={() => setFormTk({ ...s })}>Đổi tài khoản</button>
            </td>}
          </tr>) : <tr><td colSpan={canWrite ? 8 : 7} className="muted">Chưa có nhà cung cấp nào.</td></tr>}</tbody></table>
      </div>
    </>}

    {tab === "don" && <>
      {formDon && <div className="panel">
        <h2>Đặt dịch vụ</h2>
        <p className="muted">Đơn phải gắn <b>tour</b>: chi phí không gắn tour thì không quy được vào giá thành,
          và cuối kỳ nó nằm trong một cục chi phí chung không ai chia lại được.</p>
        <div className="grid2">
          <label>Nhà cung cấp
            <select value={formDon.supplier_id || ""} onChange={(e) => setFormDon({ ...formDon, supplier_id: Number(e.target.value) })}>
              <option value="">— chọn —</option>
              {ds.map((s) => <option key={s.id} value={s.id}>{s.ten}</option>)}
            </select></label>
          <label>Tour
            <select value={formDon.tour_id || ""} onChange={(e) => setFormDon({ ...formDon, tour_id: Number(e.target.value) })}>
              <option value="">— chọn tour —</option>
              {tours.map((t: any) => <option key={t.id} value={t.id}>{t.code} · {t.name}</option>)}
            </select></label>
          <label>Ngày sử dụng<input type="date" value={formDon.ngay_su_dung || ""} onChange={(e) => setFormDon({ ...formDon, ngay_su_dung: e.target.value })} /></label>
          <label>Số lượng<input type="number" value={formDon.so_luong ?? 1} onChange={(e) => setFormDon({ ...formDon, so_luong: Number(e.target.value) })} /></label>
          <label>Đơn vị<input value={formDon.don_vi || ""} onChange={(e) => setFormDon({ ...formDon, don_vi: e.target.value })} placeholder="phòng / suất / vé" /></label>
          <label>Đơn giá (đ)<input type="number" value={formDon.don_gia ?? 0} onChange={(e) => setFormDon({ ...formDon, don_gia: Number(e.target.value) })} /></label>
        </div>
        <label>Nội dung dịch vụ<input value={formDon.noi_dung || ""} onChange={(e) => setFormDon({ ...formDon, noi_dung: e.target.value })} placeholder="20 phòng đôi 2 đêm" /></label>
        <p className="muted">Thành tiền dự tính: <b>{n((formDon.so_luong || 0) * (formDon.don_gia || 0))} đ</b></p>
        <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
          <button className="act teal" disabled={luu} onClick={luuDon}>{luu ? "Đang lưu…" : "Tạo đơn"}</button>
          <button className="act grey" onClick={() => setFormDon(null)}>Đóng</button>
        </div>
      </div>}

      <div className="panel wrap"><h2>Đơn đặt dịch vụ — tổng {n(don?.tong_tien)} đ</h2>
        {canWrite && !formDon && <button className="act teal" style={{ marginBottom: 10 }}
          onClick={() => setFormDon({ so_luong: 1, don_gia: 0 })}>+ Đặt dịch vụ</button>}
        <table><thead><tr><th>Mã</th><th>Nhà cung cấp</th><th>Tour</th><th>Nội dung</th><th>Ngày dùng</th>
          <th>SL</th><th>Đơn giá</th><th>Thành tiền</th><th>Trạng thái</th>{canWrite && <th></th>}</tr></thead>
          <tbody>{don?.rows?.length ? don.rows.map((d: any) => <tr key={d.id}>
            <td className="muted">{d.code}</td><td>{d.ncc}</td><td className="muted">{d.tour}</td>
            <td>{d.noi_dung}</td>
            <td className="muted">{d.ngay_su_dung ? fmtD(d.ngay_su_dung) : "—"}</td>
            <td className="num">{d.so_luong} {d.don_vi}</td>
            <td className="num">{n(d.don_gia)}</td>
            <td className="num"><b>{n(d.thanh_tien)}</b></td>
            <td><Tag cls={d.status === "da_su_dung" ? "ok" : d.status === "huy" ? "red" : "warn"}>{d.status_ten}</Tag>
              {d.xac_nhan_ncc && <div className="muted">{d.xac_nhan_ncc}</div>}</td>
            {canWrite && <td style={{ whiteSpace: "nowrap" }}>
              {d.status === "nhap" && <button className="act grey" onClick={() => trangThai(d.id, "da_gui")}>Đã gửi NCC</button>}
              {d.status === "da_gui" && <button className="act grey" onClick={() => trangThai(d.id, "da_xac_nhan")}>NCC xác nhận</button>}
              {d.status === "da_xac_nhan" && <button className="act grey" onClick={() => trangThai(d.id, "da_su_dung")}>Đã sử dụng</button>}
            </td>}
          </tr>) : <tr><td colSpan={canWrite ? 10 : 9} className="muted">Chưa có đơn đặt dịch vụ nào.</td></tr>}</tbody></table>
      </div>
    </>}

    {tab === "tk" && <div className="panel wrap">
      <h2>Đề nghị đổi số tài khoản chờ xác nhận</h2>
      <p className="muted">Người xác nhận phải là <b>người khác</b> với người đề nghị. Xác minh lại với nhà
        cung cấp bằng số điện thoại đã biết từ trước, đừng gọi theo số ghi trong chính văn bản đề nghị.</p>
      <table><thead><tr><th>Nhà cung cấp</th><th>Số cũ</th><th>Số mới</th><th>Văn bản</th><th>Lý do</th>
        <th>Người đề nghị</th>{canDuyet && <th></th>}</tr></thead>
        <tbody>{cho.length ? cho.map((c) => <tr key={c.id}>
          <td>{c.ncc}</td>
          <td className="muted">{c.so_tk_cu || "—"}<div className="muted">{c.ngan_hang_cu}</div></td>
          <td><b>{c.so_tk_moi}</b><div className="muted">{c.ngan_hang_moi} · {c.chu_tk_moi}</div></td>
          <td className="muted">{c.chung_tu}</td><td className="muted">{c.ly_do}</td>
          <td className="muted">{c.de_nghi_boi}<div className="muted">{fmtDT(c.de_nghi_luc)}</div></td>
          {canDuyet && <td style={{ whiteSpace: "nowrap" }}>
            <button className="act teal" onClick={() => xacNhanTk(c.id, true)}>Xác nhận</button>{" "}
            <button className="act grey" onClick={() => xacNhanTk(c.id, false)}>Từ chối</button>
          </td>}
        </tr>) : <tr><td colSpan={canDuyet ? 7 : 6} className="muted">Không có đề nghị nào đang chờ.</td></tr>}</tbody></table>
    </div>}
  </>);
}

export default function Page() { return <Shell><NhaCungCap /></Shell>; }
