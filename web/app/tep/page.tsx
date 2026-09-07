"use client";
import { useEffect, useState, useCallback } from "react";
import Shell from "@/components/Shell";
import DinhKem from "@/components/DinhKem";
import { api, fmtDT, getToken } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Tệp & hình ảnh toàn hệ thống: tra theo phòng ban, theo loại hồ sơ, hoặc mở đúng một hồ sơ để đính kèm.
 *
 *  Màn hình này tồn tại vì một lý do rất cụ thể: đến lúc cần chứng minh một khoản chi, người ta phải tìm
 *  được tấm ảnh chứng từ trong vài giây — chứ không phải lục Zalo của người đã nghỉ việc. */
const PHONG: Record<string, string> = { dieu_hanh: "Điều hành", doi_xe: "Đội xe", hcns: "Hành chính & Nhân sự",
  kd_le: "Kinh doanh", ketoan: "Kế toán", visa: "Ban Visa", ban_tgd: "Ban TGĐ" };

function TepPage() {
  const [cf, setCf] = useState<any>(null);
  const [phong, setPhong] = useState("");
  const [doiTuong, setDoiTuong] = useState("");
  const [nhom, setNhom] = useState("");
  const [maHoSo, setMaHoSo] = useState("");
  const [ds, setDs] = useState<any[]>([]);
  const [loi, setLoi] = useState("");

  useEffect(() => { api("/tep/cau-hinh").then(setCf).catch((e) => setLoi(errMsg(e))); }, []);

  const load = useCallback(async () => {
    try {
      const q = new URLSearchParams();
      if (phong) q.set("phong_ban", phong);
      if (doiTuong) q.set("doi_tuong", doiTuong);
      if (nhom) q.set("nhom_ho_so", nhom);
      setDs(await api(`/tep?${q.toString()}`));
    } catch (e) { setLoi(errMsg(e)); }
  }, [phong, doiTuong, nhom]);
  useEffect(() => { load(); }, [load]);

  const xem = (a: any) => {
    fetch(`/api/v1/tep/${a.id}/tai`, { headers: { Authorization: `Bearer ${getToken() || ""}` } })
      .then(async (r) => { if (!r.ok) throw new Error((await r.json())?.detail || "Không đọc được tệp");
                           return r.blob(); })
      .then((b) => window.open(URL.createObjectURL(b), "_blank"))
      .catch((e) => setLoi(String(e.message || e)));
  };

  const dt = cf?.doi_tuong?.filter((x: any) => !phong || x.phong_ban === phong) || [];

  return (<>
    <h1>Tệp &amp; hình ảnh</h1>
    <p className="muted">Một kho chung cho chứng từ ảnh của mọi phòng ban. Tên tệp gốc chỉ để hiển thị; chỗ
      lưu do hệ thống sinh từ mã băm nội dung, và mỗi lần đọc ra đều đối chiếu lại mã băm — tệp lệch thì
      báo lỗi chứ không trả về nội dung &quot;gần đúng&quot;. Gỡ tệp là <b>thu hồi có ghi lý do</b>, không xóa cứng.</p>
    {cf?.cau_truc_kho && <p className="muted">Cấu trúc kho: <b>{cf.cau_truc_kho}</b>. Chín nhóm hồ sơ giống
      nhau ở mọi pháp nhân — nhờ vậy kiểm toán mở kho của một pháp nhân chưa từng làm việc cùng vẫn tìm
      được hồ sơ mà không phải hỏi ai.</p>}
    {loi && <p className="muted"><Tag cls="red">{loi}</Tag></p>}

    <div className="panel">
      <h2>Tra cứu</h2>
      <div className="grid2">
        <label>Nhóm hồ sơ
          <select value={nhom} onChange={(e) => setNhom(e.target.value)}>
            <option value="">Tất cả 9 nhóm</option>
            {(cf?.nhom_ho_so || []).map((n: any) =>
              <option key={n.ma} value={n.ma}>{n.ma} · {n.ten} — giữ {n.thoi_han_luu}</option>)}
          </select></label>
        <label>Phòng ban
          <select value={phong} onChange={(e) => { setPhong(e.target.value); setDoiTuong(""); }}>
            <option value="">Tất cả</option>
            {Object.entries(PHONG).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select></label>
        <label>Loại hồ sơ
          <select value={doiTuong} onChange={(e) => setDoiTuong(e.target.value)}>
            <option value="">Tất cả</option>
            {dt.map((x: any) => <option key={x.ma} value={x.ma}>{x.ten}</option>)}
          </select></label>
      </div>
      <div className="wrap"><table>
        <thead><tr><th>Tệp</th><th>Gắn vào</th><th>Nhóm hồ sơ</th><th>Phòng</th><th>Loại</th>
          <th>Dung lượng</th><th>Người tải</th><th>Lúc</th></tr></thead>
        <tbody>{ds.length ? ds.map((a) => <tr key={a.id}>
          <td><a href="#" onClick={(e) => { e.preventDefault(); xem(a); }}>{a.ten_tep}</a>
            {a.la_anh && <> <Tag cls="ok">ảnh</Tag></>}
            {a.nguon === "ai" && <> <Tag cls="warn">AI: {a.tac_nhan}</Tag></>}</td>
          <td>{a.doi_tuong_ten} <span className="muted">#{a.doi_tuong_id}</span></td>
          <td className="muted">{a.nhom_ho_so}{a.nhay_cam && <> <Tag cls="warn">cá nhân</Tag></>}
            <div className="muted">giữ {a.thoi_han_luu}</div></td>
          <td className="muted">{PHONG[a.phong_ban] || a.phong_ban}</td>
          <td className="muted">{a.loai_ten}</td>
          <td className="num muted">{(a.kich_thuoc / 1024).toFixed(0)} KB</td>
          <td className="muted">{a.boi}</td><td className="muted">{fmtDT(a.luc)}</td>
        </tr>) : <tr><td colSpan={8} className="muted">Chưa có tệp nào khớp bộ lọc.</td></tr>}</tbody></table></div>
    </div>

    <div className="panel">
      <h2>Đính kèm vào một hồ sơ</h2>
      <p className="muted">Chọn loại hồ sơ rồi nhập mã (mã chuyến, mã booking, mã nhân viên…) để xem và gắn
        tệp cho đúng hồ sơ đó.</p>
      <div className="grid2">
        <label>Loại hồ sơ
          <select value={doiTuong} onChange={(e) => setDoiTuong(e.target.value)}>
            <option value="">— chọn —</option>
            {(cf?.doi_tuong || []).map((x: any) => <option key={x.ma} value={x.ma}>{x.ten}</option>)}
          </select></label>
        <label>Mã hồ sơ
          <input value={maHoSo} onChange={(e) => setMaHoSo(e.target.value)} placeholder="VD: BK26080012" /></label>
      </div>
    </div>
    {doiTuong && maHoSo.trim() &&
      <DinhKem doiTuong={doiTuong} doiTuongId={maHoSo.trim()}
               tieuDe={`Tệp của hồ sơ ${maHoSo.trim()}`} />}
  </>);
}

export default function Page() { return <Shell><TepPage /></Shell>; }
