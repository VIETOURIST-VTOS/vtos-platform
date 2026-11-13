"use client";
import { useEffect, useState } from "react";
import { api, getUser } from "@/lib/api";
import { useHoi } from "@/components/HopHoi";

/** 5.9.2 Đề nghị mua và 5.9.3 Cấp phát tài sản (Chủ tịch chốt 08/10/2026).
 *
 *  HAI CHỮ KÝ HIỆN RA LÀ HAI CỘT, KHÔNG PHẢI MỘT CỘT TRẠNG THÁI. Người duyệt nói ĐƯỢC MUA; Kế toán
 *  nói ĐÃ CHI. Gộp lại thì ngày Kế toán chưa chi được vì thiếu tiền, đề nghị vẫn hiện "xong" và
 *  người đề nghị ngồi đợi một món hàng không ai mua.
 *
 *  Chênh giữa SỐ ƯỚC TÍNH và SỐ ĐÃ CHI in sẵn thành một cột. Bắt người đọc tự trừ thì chỗ lệch nằm
 *  trong đầu họ, và không ai nhìn thấy nó hai lần liên tiếp.
 */

const tien = (n: number | null | undefined) =>
  n === null || n === undefined ? "—" : n.toLocaleString("vi-VN");

export function DeNghiMua() {
  const { xacNhan, nhap, hop } = useHoi();   // TR-10: hỏi lại trên trang, không dùng hộp thoại trình duyệt
  const u = getUser();
  const [rows, setRows] = useState<any[]>([]);
  const [meta, setMeta] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const [moi, setMoi] = useState<any>({ noi_dung: "", so_luong: 1, don_vi: "cái", uoc_tinh: "",
                                        ly_do: "", muc_do: "thuong", can_truoc_ngay: "" });

  async function nap() {
    setLoi("");
    try {
      setRows((await api<{ rows: any[] }>("/de-nghi-mua")).rows || []);
      setMeta(await api("/de-nghi-mua/meta"));
    } catch (e: any) { setLoi(String(e?.message || e)); }
  }
  useEffect(() => { nap(); }, []);

  const laDuyet = meta?.vai_duyet_mua?.includes(u?.role);
  const laChi = meta?.vai_chi?.includes(u?.role);

  async function gui() {
    try {
      await api("/de-nghi-mua", { method: "POST", json: {
        ...moi,
        so_luong: Number(moi.so_luong || 1),
        uoc_tinh: moi.uoc_tinh === "" ? null : Number(moi.uoc_tinh),
        can_truoc_ngay: moi.can_truoc_ngay || null } });
      setMoi({ noi_dung: "", so_luong: 1, don_vi: "cái", uoc_tinh: "", ly_do: "",
               muc_do: "thuong", can_truoc_ngay: "" });
      nap();
    } catch (e: any) { setLoi(String(e?.message || e)); }
  }

  async function duyet(r: any, dong_y: boolean) {
    const ghi_chu = dong_y ? "" : (await nhap("Không duyệt vì sao? (bắt buộc)") || "");
    if (!dong_y && !ghi_chu.trim()) { setLoi("Không duyệt thì phải ghi lý do."); return; }
    try { await api(`/de-nghi-mua/${r.id}/duyet`, { method: "POST", json: { dong_y, ghi_chu } }); nap(); }
    catch (e: any) { setLoi(String(e?.message || e)); }
  }

  async function ghiChi(r: any) {
    const s = await nhap(`Số tiền đã chi cho ${r.ma}?`, String(r.uoc_tinh ?? ""));
    if (!s) return;
    const ct = await nhap("Số chứng từ (để trống cũng được):") || "";
    try { await api(`/de-nghi-mua/${r.id}/da-chi`, { method: "POST", json: { so_tien: Number(s), chung_tu_ref: ct } }); nap(); }
    catch (e: any) { setLoi(String(e?.message || e)); }
  }

  return (
    <section>
      {hop}
      <h1>Đề nghị mua</h1>
      <p className="muted">
        Mọi phòng gửi được ở đây. Đề nghị đi <b>TGĐ / Chủ tịch duyệt</b> rồi <b>Kế toán ghi đã chi</b> —
        hai chữ ký của hai người, không gộp. <b>Giá ước tính để trống được</b>: chưa hỏi giá thì cứ gửi,
        đừng điền một con số đoán rồi con số ấy đi thẳng vào bảng chi phí dự kiến.
      </p>
      {loi && <p className="loi">{loi}</p>}

      <div className="the">
        <h3>Gửi một đề nghị</h3>
        <div className="hang">
          <input placeholder="Mua cái gì" value={moi.noi_dung} style={{ minWidth: 260 }}
                 onChange={(e) => setMoi({ ...moi, noi_dung: e.target.value })} />
          <input type="number" placeholder="SL" value={moi.so_luong} style={{ width: 70 }}
                 onChange={(e) => setMoi({ ...moi, so_luong: e.target.value })} />
          <input placeholder="Đơn vị" value={moi.don_vi} style={{ width: 80 }}
                 onChange={(e) => setMoi({ ...moi, don_vi: e.target.value })} />
          <input type="number" placeholder="Ước tính (để trống được)" value={moi.uoc_tinh}
                 onChange={(e) => setMoi({ ...moi, uoc_tinh: e.target.value })} />
          <select value={moi.muc_do} onChange={(e) => setMoi({ ...moi, muc_do: e.target.value })}>
            {Object.entries(meta?.dnm_muc_do || { thuong: "Bình thường" }).map(([k, v]: any) =>
              <option key={k} value={k}>{v}</option>)}
          </select>
          <input type="date" value={moi.can_truoc_ngay}
                 onChange={(e) => setMoi({ ...moi, can_truoc_ngay: e.target.value })} />
        </div>
        <textarea placeholder="Vì sao cần" value={moi.ly_do} rows={2}
                  onChange={(e) => setMoi({ ...moi, ly_do: e.target.value })} />
        <button onClick={gui} disabled={!moi.noi_dung.trim()}>Gửi</button>
      </div>

      <table className="bang">
        <thead>
          <tr><th>Mã</th><th>Nội dung</th><th>Phòng</th><th>Ước tính</th><th>Đã chi</th>
              <th>Chênh</th><th>Trạng thái</th><th></th></tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>{r.ma}</td>
              <td>{r.noi_dung} <span className="muted">{r.so_luong} {r.don_vi}</span></td>
              <td>{r.department}</td>
              <td>{tien(r.uoc_tinh)}</td>
              <td>{tien(r.so_tien_chi)}</td>
              <td>{r.lech_chi_so_voi_uoc === null ? "—"
                   : (r.lech_chi_so_voi_uoc > 0 ? "+" : "") + tien(r.lech_chi_so_voi_uoc)}</td>
              <td>{r.trang_thai_ten}{r.duyet_ghi_chu && <div className="muted">{r.duyet_ghi_chu}</div>}</td>
              <td>
                {laDuyet && r.trang_thai === "cho_duyet" && (<>
                  <button onClick={() => duyet(r, true)}>Duyệt</button>{" "}
                  <button onClick={() => duyet(r, false)}>Không duyệt</button>
                </>)}
                {laChi && r.trang_thai === "da_duyet" && (
                  <button onClick={() => ghiChi(r)}>Ghi đã chi</button>)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && <p className="muted">Chưa có đề nghị nào.</p>}
    </section>
  );
}

export function CapPhatTaiSan() {
  const { xacNhan, nhap, hop } = useHoi();   // TR-10: hỏi lại trên trang, không dùng hộp thoại trình duyệt
  const u = getUser();
  const [rows, setRows] = useState<any[]>([]);
  const [meta, setMeta] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const [moi, setMoi] = useState<any>({ employee_id: "", ten_tai_san: "", so_luong: 1,
                                        don_vi: "cái", cap_ngay: "", muc_dich: "",
                                        tinh_trang_khi_cap: "" });

  async function nap() {
    setLoi("");
    try {
      setRows((await api<{ rows: any[] }>("/cap-phat")).rows || []);
      setMeta(await api("/de-nghi-mua/meta"));
    } catch (e: any) { setLoi(String(e?.message || e)); }
  }
  useEffect(() => { nap(); }, []);

  const laHcns = meta?.vai_cap_phat?.includes(u?.role);

  async function cap() {
    try {
      await api("/cap-phat", { method: "POST", json: {
        ...moi, employee_id: Number(moi.employee_id), so_luong: Number(moi.so_luong || 1),
        asset_id: null } });
      setMoi({ employee_id: "", ten_tai_san: "", so_luong: 1, don_vi: "cái", cap_ngay: "",
               muc_dich: "", tinh_trang_khi_cap: "" });
      nap();
    } catch (e: any) { setLoi(String(e?.message || e)); }
  }

  async function tra(r: any) {
    const tt = await nhap(`Trả "${r.ten_tai_san}" trong tình trạng nào? (bắt buộc)`) || "";
    if (!tt.trim()) { setLoi("Phải ghi tình trạng món đồ khi trả."); return; }
    const hong = await xacNhan("Món này MẤT hoặc HỎNG? (Hủy = trả bình thường)");
    const ngay = new Date().toISOString().slice(0, 10);
    try { await api(`/cap-phat/${r.id}/tra`, { method: "POST", json: { tra_ngay: ngay, tinh_trang: tt, mat_hong: hong } }); nap(); }
    catch (e: any) { setLoi(String(e?.message || e)); }
  }

  return (
    <section>
      {hop}
      <h2>Cấp phát tài sản</h2>
      <p className="muted">
        Sổ này trả lời đúng <b>một câu</b>: món nào đang ở tay ai — câu HCNS phải hỏi mỗi lần có người
        nghỉ việc. Nó <b>không phải sổ tài sản thứ hai</b>: nguyên giá và khấu hao vẫn ở thẻ TSCĐ.
        Món không đủ nguyên giá để thành thẻ TSCĐ — SIM, chìa khóa, đồng phục — vẫn ghi được ở đây.
      </p>
      {loi && <p className="loi">{loi}</p>}
      {laHcns && (
        <div className="the">
          <h3>Cấp một món</h3>
          <div className="hang">
            <input placeholder="Mã hồ sơ nhân sự (id)" value={moi.employee_id} style={{ width: 160 }}
                   onChange={(e) => setMoi({ ...moi, employee_id: e.target.value })} />
            <input placeholder="Tên món" value={moi.ten_tai_san} style={{ minWidth: 200 }}
                   onChange={(e) => setMoi({ ...moi, ten_tai_san: e.target.value })} />
            <input type="number" value={moi.so_luong} style={{ width: 70 }}
                   onChange={(e) => setMoi({ ...moi, so_luong: e.target.value })} />
            <input placeholder="Đơn vị" value={moi.don_vi} style={{ width: 80 }}
                   onChange={(e) => setMoi({ ...moi, don_vi: e.target.value })} />
            <input type="date" value={moi.cap_ngay}
                   onChange={(e) => setMoi({ ...moi, cap_ngay: e.target.value })} />
            <input placeholder="Tình trạng khi cấp" value={moi.tinh_trang_khi_cap}
                   onChange={(e) => setMoi({ ...moi, tinh_trang_khi_cap: e.target.value })} />
          </div>
          <button onClick={cap} disabled={!moi.employee_id || !moi.cap_ngay || !moi.ten_tai_san.trim()}>
            Lập biên bản cấp phát
          </button>
        </div>
      )}
      <table className="bang">
        <thead>
          <tr><th>Mã</th><th>Món</th><th>Người giữ</th><th>Phòng</th><th>Cấp ngày</th>
              <th>Trạng thái</th><th></th></tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>{r.ma}</td>
              <td>{r.ten_tai_san} <span className="muted">{r.so_luong} {r.don_vi}</span></td>
              <td>{r.ho_ten} <span className="muted">{r.ma_nv}</span></td>
              <td>{r.department}</td>
              <td>{r.cap_ngay}</td>
              <td>{r.trang_thai_ten}
                {r.tinh_trang_khi_tra && <div className="muted">{r.tinh_trang_khi_tra}</div>}</td>
              <td>{laHcns && r.trang_thai === "dang_giu" && (
                <button onClick={() => tra(r)}>Ghi trả</button>)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && <p className="muted">Chưa có biên bản cấp phát nào.</p>}
    </section>
  );
}
