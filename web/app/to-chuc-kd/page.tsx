"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Cơ cấu tổ chức khối Kinh doanh – chi nhánh, phòng, team, và ai thuộc đơn vị nào TỪ NGÀY NÀO.
 *
 *  Màn hình này cố ý KHÔNG có nút "suy đơn vị từ sales_group". Ba chuỗi chữ tự do cũ
 *  (department / sales_group / office) là thứ bảng này sinh ra để thay, và suy tự động từ chúng là
 *  chép nguyên lỗi gõ sai của bốn năm qua vào một bảng mới rồi tin nó. Người chưa có đơn vị nằm ở
 *  danh sách đối chiếu cuối trang cho tới khi HC-NS chỉ định – cùng nếp với màn hình Pháp nhân.
 *
 *  NGÀY XEM đổi được, và đó là điểm chính của cả vòng: gõ một ngày trong quá khứ thì cây và danh
 *  sách người hiện ra ĐÚNG như hôm ấy. Không có nó thì báo cáo kỳ cũ in lại ra số khác.
 */
const CAP: [string, string][] = [["chi_nhanh", "Chi nhánh"], ["phong", "Phòng"], ["team", "Team"]];
const VAI: [string, string][] = [["nhan_vien", "Nhân viên"], ["leader", "Team Leader"],
                                 ["truong_phong", "Trưởng phòng"], ["giam_doc", "Giám đốc"]];
const nhanCap = (c: string) => CAP.find((x) => x[0] === c)?.[1] || c;
const nhanVai = (v: string) => VAI.find((x) => x[0] === v)?.[1] || v;

function ToChucKD() {
  const { user, toast } = useShell();
  const canWrite = ["chutich", "tgd", "hcns", "cntt"].includes(user?.role || "");

  const [mang, setMang] = useState("le");
  const [ngay, setNgay] = useState("");
  const [cay, setCay] = useState<any>(null);
  const [chon, setChon] = useState<number | null>(null);
  const [nguoi, setNguoi] = useState<any>(null);
  const [thieu, setThieu] = useState<any>(null);
  const [cos, setCos] = useState<any[]>([]);
  const [ds, setDs] = useState<any[]>([]);

  const [dv, setDv] = useState<any>({ ma: "", ten: "", cap: "chi_nhanh", cha_id: "", company_id: "", hieu_luc_tu: "", ghi_chu: "" });
  const [pc, setPc] = useState<any>({ user_id: "", don_vi_id: "", vai: "nhan_vien", tu_ngay: "", den_ngay: "", ly_do: "" });

  const q = `mang=${mang}${ngay ? `&ngay=${ngay}` : ""}`;
  const load = useCallback(() => {
    api(`/to-chuc-kd/cay?${q}`).then(setCay).catch(() => {});
    api(`/to-chuc-kd/chua-phan-cong?${q}`).then(setThieu).catch(() => {});
  }, [q]);
  useEffect(() => { load(); }, [load]);
  // Hai danh sách để khai (pháp nhân, tài khoản) lấy từ CHÍNH cửa của màn hình này, không gọi sang
  // /companies hay /access. Gọi sang là phải khai hai tiền tố ấy vào MAN_HINH_API, và khai xong thì
  // mọi vai mở được màn hình – kể cả nv_kd – được thêm trọn hai nhóm quyền. Chỉ vai GHI mới cần
  // hai danh sách này, nên chỉ vai GHI mới gọi.
  useEffect(() => {
    if (!canWrite) return;
    api("/to-chuc-kd/danh-muc").then((r: any) => { setCos(r?.cong_ty || []); setDs(r?.tai_khoan || []); })
      .catch(() => {});
  }, [canWrite]);
  useEffect(() => {
    if (chon == null) { setNguoi(null); return; }
    api(`/to-chuc-kd/nguoi?don_vi_id=${chon}&${q}`).then(setNguoi).catch((x) => { setNguoi(null); toast(errMsg(x), true); });
  }, [chon, q, toast]);

  const post = async (path: string, json?: any) => {
    try { const r = await api(path, { method: "POST", json }); toast(r.message || "Đã ghi"); load(); if (chon != null) setChon(chon); return r; }
    catch (x) { toast(errMsg(x), true); }
  };

  /** Cây dẹt thành danh sách phẳng để vẽ bảng thụt đầu dòng – giữ nguyên thứ tự cha trước con. */
  const dep = (nut: any[], sau = 0): any[] => nut.flatMap((n) => [{ ...n, sau }, ...dep(n.con || [], sau + 1)]);
  const phang = dep(cay?.cay || []);
  const trongPhamVi = (id: number) => cay?.xem_toan_cay || (cay?.pham_vi || []).includes(id);

  return (<>
    <h1>Cơ cấu tổ chức khối Kinh doanh</h1>
    <p className="muted">Chi nhánh → phòng → team → người, mỗi phân công có <b>ngày hiệu lực</b>. Đổi ngày xem ở ô bên dưới
      là cây hiện ra đúng như ngày ấy – nhờ vậy nhân viên chuyển team không làm đổi số của kỳ đã chốt.</p>

    <div className="panel">
      <div className="grid">
        <label>Mảng<select value={mang} onChange={(e) => { setMang(e.target.value); setChon(null); }}>
          <option value="le">Kinh doanh Lẻ</option><option value="doan">Kinh doanh Đoàn</option></select></label>
        <label>Ngày xem<input type="date" value={ngay} onChange={(e) => setNgay(e.target.value)} /></label>
        <span className="muted">Bỏ trống = hôm nay.{cay && !cay.xem_toan_cay && " Phần in đậm là phạm vi của bạn."}</span>
      </div>
    </div>

    <div className="panel wrap"><h2>Cây đơn vị</h2>
      <table><thead><tr><th>Đơn vị</th><th>Cấp</th><th className="num">Người</th><th>Hiệu lực</th><th>Trạng thái</th><th></th></tr></thead>
        <tbody>{phang.map((n: any) => <tr key={n.id} style={{ opacity: n.con_hieu_luc ? 1 : 0.55 }}>
          <td style={{ paddingLeft: 8 + n.sau * 22 }}>
            <span className="mono">{n.ma}</span> <b style={{ fontWeight: trongPhamVi(n.id) ? 600 : 400 }}>{n.ten}</b>
          </td>
          <td>{nhanCap(n.cap)}</td>
          <td className="num">{n.so_nguoi || <span className="muted">0</span>}</td>
          <td className="mono">{n.hieu_luc_tu}{n.hieu_luc_den ? ` → ${n.hieu_luc_den}` : ""}</td>
          <td>{n.con_hieu_luc ? <Tag cls="ok">Đang mở</Tag> : <Tag cls="red">Đã đóng</Tag>}</td>
          <td><button className="act" onClick={() => setChon(n.id)}>Xem người</button></td>
        </tr>)}
        {!phang.length && <tr><td colSpan={6} className="muted">Chưa có đơn vị nào cho mảng này. {canWrite ? "Tạo đơn vị đầu tiên ở khung bên dưới." : "Nhờ Hành chính – Nhân sự khai danh mục."}</td></tr>}
        </tbody></table>
      <p className="muted">Team phải nằm dưới phòng, phòng dưới chi nhánh – máy chủ chặn, không phải giao diện nhắc.
        Đơn vị không bị xoá bao giờ, chỉ <b>đóng</b> lại, để mọi dòng doanh thu từng gắn vào nó vẫn còn nghĩa.</p></div>

    {nguoi && <div className="panel wrap"><h2>Người trong đơn vị</h2>
      <table><thead><tr><th>Họ tên</th><th>Tài khoản</th><th>Đơn vị</th><th>Vai trong đơn vị</th><th>Hiệu lực</th>{canWrite && <th></th>}</tr></thead>
        <tbody>{(nguoi.rows || []).map((r: any) => <tr key={r.phan_cong_id}>
          <td><b>{r.ho_ten}</b></td><td className="mono">{r.tai_khoan}</td>
          <td><span className="mono">{r.don_vi_ma}</span> {r.don_vi}</td>
          <td>{r.vai === "nhan_vien" ? nhanVai(r.vai) : <Tag cls="navy">{nhanVai(r.vai)}</Tag>}</td>
          <td className="mono">{r.tu_ngay}{r.den_ngay ? ` → ${r.den_ngay}` : ""}</td>
          {canWrite && <td>{!r.den_ngay && <button className="act" onClick={() => {
            const d = prompt("Kết thúc phân công từ ngày nào? (2026-09-30)"); if (!d) return;
            const ly = prompt("Lý do kết thúc:"); if (!ly) return;
            post(`/to-chuc-kd/phan-cong/${r.phan_cong_id}/ket-thuc`, { den_ngay: d, ly_do: ly });
          }}>Kết thúc</button>}</td>}
        </tr>)}
        {!(nguoi.rows || []).length && <tr><td colSpan={canWrite ? 6 : 5} className="muted">Chưa ai được phân công vào đơn vị này.</td></tr>}
        </tbody></table></div>}

    <div className="panel wrap"><h2>Chưa có đơn vị</h2>
      <table><thead><tr><th>Họ tên</th><th>Tài khoản</th><th>Vai đăng nhập</th><th>Nhóm cũ (sales_group)</th></tr></thead>
        <tbody>{(thieu?.rows || []).map((r: any) => <tr key={r.user_id}>
          <td><b>{r.ho_ten}</b></td><td className="mono">{r.tai_khoan}</td><td>{r.vai_dang_nhap}</td>
          <td className="mono">{r.sales_group || <span className="muted">–</span>}</td></tr>)}
        {!(thieu?.rows || []).length && <tr><td colSpan={4}><Tag cls="ok">Không còn ai</Tag></td></tr>}
        </tbody></table>
      <p className="muted">Còn <b>{thieu?.tong ?? 0}</b> tài khoản kinh doanh chưa có đơn vị vào ngày đang xem.
        Cột <b>Nhóm cũ</b> chỉ để tra cứu khi khai – hệ thống <b>không</b> tự suy đơn vị từ nó, vì chuỗi ấy gõ tay nên sai lúc nào không biết.</p></div>

    {canWrite && <div className="panel"><h2>Khai đơn vị mới</h2>
      <div className="grid">
        <label>Mã<input value={dv.ma} placeholder="CT-T1" onChange={(e) => setDv({ ...dv, ma: e.target.value })} /></label>
        <label>Tên<input value={dv.ten} placeholder="Team 1 · KDL Cần Thơ" onChange={(e) => setDv({ ...dv, ten: e.target.value })} /></label>
        <label>Cấp<select value={dv.cap} onChange={(e) => setDv({ ...dv, cap: e.target.value })}>
          {CAP.map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Nằm dưới<select value={dv.cha_id} onChange={(e) => setDv({ ...dv, cha_id: e.target.value })}>
          <option value="">– không, đây là chi nhánh –</option>
          {phang.filter((n: any) => n.cap !== "team").map((n: any) => <option key={n.id} value={n.id}>{n.ma} · {n.ten}</option>)}</select></label>
        <label>Pháp nhân<select value={dv.company_id} onChange={(e) => setDv({ ...dv, company_id: e.target.value })}>
          <option value="">– chưa xác định –</option>
          {cos.map((c: any) => <option key={c.id} value={c.id}>{c.code} · {c.name}</option>)}</select></label>
        <label>Hiệu lực từ<input type="date" value={dv.hieu_luc_tu} onChange={(e) => setDv({ ...dv, hieu_luc_tu: e.target.value })} /></label>
      </div>
      <button className="act orange" onClick={() => post("/to-chuc-kd/don-vi", {
        ...dv, mang, cha_id: dv.cha_id ? Number(dv.cha_id) : null,
        company_id: dv.company_id ? Number(dv.company_id) : null, hieu_luc_tu: dv.hieu_luc_tu || null,
      })}>Tạo đơn vị</button>
    </div>}

    {canWrite && <div className="panel"><h2>Phân công người vào đơn vị</h2>
      <div className="grid">
        <label>Người<select value={pc.user_id} onChange={(e) => setPc({ ...pc, user_id: e.target.value })}>
          <option value="">– chọn tài khoản –</option>
          {ds.map((x: any) => <option key={x.id} value={x.id}>{x.full_name} · {x.username} · {x.role}</option>)}</select></label>
        <label>Đơn vị<select value={pc.don_vi_id} onChange={(e) => setPc({ ...pc, don_vi_id: e.target.value })}>
          <option value="">– chọn đơn vị –</option>
          {phang.filter((n: any) => n.con_hieu_luc).map((n: any) => <option key={n.id} value={n.id}>{n.ma} · {n.ten}</option>)}</select></label>
        <label>Vai trong đơn vị<select value={pc.vai} onChange={(e) => setPc({ ...pc, vai: e.target.value })}>
          {VAI.map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Từ ngày<input type="date" value={pc.tu_ngay} onChange={(e) => setPc({ ...pc, tu_ngay: e.target.value })} /></label>
        <label>Đến ngày<input type="date" value={pc.den_ngay} onChange={(e) => setPc({ ...pc, den_ngay: e.target.value })} /></label>
        <label>Lý do<input value={pc.ly_do} placeholder="Tuyển mới / chuyển team / kiêm nhiệm" onChange={(e) => setPc({ ...pc, ly_do: e.target.value })} /></label>
      </div>
      <button className="act orange" onClick={() => post("/to-chuc-kd/phan-cong", {
        user_id: Number(pc.user_id), don_vi_id: Number(pc.don_vi_id), vai: pc.vai,
        tu_ngay: pc.tu_ngay, den_ngay: pc.den_ngay || null, ly_do: pc.ly_do,
      })}>Ghi phân công</button>
      <p className="muted">Để trống <b>Đến ngày</b> nghĩa là chưa kết thúc – khác hẳn với một ngày xa tít trong tương lai.
        Chuyển team thì <b>kết thúc dòng cũ</b> rồi ghi dòng mới; máy chủ từ chối hai dòng cùng vai phủ cùng một ngày,
        vì chồng lấn là cách một người bị đếm ở hai team.</p>
    </div>}
  </>);
}

export default function Page() { return <Shell><ToChucKD /></Shell>; }
