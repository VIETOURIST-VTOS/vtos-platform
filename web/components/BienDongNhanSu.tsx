"use client";
import { useEffect, useState } from "react";
import { api, getUser } from "@/lib/api";

/** 5.8 Báo cáo biến động nhân sự — đứng ở /hr thẻ "Tổng quan HCNS".
 *
 *  MỘT PHÉP TÍNH VÀ NÓ PHẢI CÂN: đầu kỳ + tăng − giảm = cuối kỳ. Cột "Lệch" in ra chính vế thừa
 *  của đẳng thức ấy, và nó phải là 0 ở mọi dòng. In cột lệch thay vì giấu nó đi là có chủ ý: một
 *  bảng tự nhận là cân mà không cho nhìn chỗ cân thì không ai kiểm được nó.
 *
 *  KHỐI "CHƯA BIẾT NGÀY NGHỈ" ĐỨNG NGAY DƯỚI BẢNG, không nằm cuối trang. Đó là nhóm người đã nghỉ
 *  mà chưa ai điền ngày — họ không nằm trong bất kỳ kỳ nào, nên MỌI kỳ đều cân, và cái cân ấy là
 *  cân giả: tổng cuối kỳ thiếu đúng bằng số người ấy.
 */
export default function BienDongNhanSu() {
  const u = getUser();
  const [kyLoai, setKyLoai] = useState("thang");
  const [ky, setKy] = useState(() => new Date().toISOString().slice(0, 7));
  const [bc, setBc] = useState<any>(null);
  const [cc, setCc] = useState<any>(null);
  const [meta, setMeta] = useState<any>(null);
  const [loi, setLoi] = useState("");

  async function nap() {
    setLoi("");
    try {
      setBc(await api(`/bien-dong-ns?ky_loai=${kyLoai}&ky=${encodeURIComponent(ky)}`));
      setCc(await api("/bien-dong-ns/co-cau"));
      setMeta(await api("/bien-dong-ns/meta"));
    } catch (e: any) { setLoi(String(e?.message || e)); }
  }
  useEffect(() => { nap(); /* eslint-disable-next-line */ }, [kyLoai, ky]);

  const laHcns = ["hcns", "cntt", "tgd", "chutich"].includes(u?.role || "");

  async function ghiNghi(employee_id: number) {
    const ngay = window.prompt("Ngày nghỉ (YYYY-MM-DD):") || "";
    if (!ngay) return;
    const loai = window.prompt(
      `Lý do: ${Object.keys(meta?.ly_do_giam || {}).join(" / ")}`, "tu_xin") || "";
    const ghi = window.prompt("Ghi chú (không bắt buộc):") || "";
    try {
      await api("/bien-dong-ns/nghi-viec", { method: "POST",
        json: { employee_id, ngay, ly_do_loai: loai, ly_do: ghi } });
      nap();
    } catch (e: any) { setLoi(String(e?.message || e)); }
  }

  const t = bc?.tong;
  return (
    <section>
      <h2>Biến động nhân sự</h2>
      <p className="muted">
        Một phép tính: <b>đầu kỳ + tăng − giảm = cuối kỳ</b>. Cột <b>Lệch</b> là vế thừa của đẳng thức
        ấy và phải bằng 0 ở mọi dòng — khác 0 nghĩa là có một đường vào hoặc ra mà bộ đếm không thấy.
        Tỷ lệ nghỉ việc tính trên <b>bình quân đầu kỳ và cuối kỳ</b>, không trên đầu kỳ, và{" "}
        <b>không tính người chuyển sang pháp nhân khác trong tập đoàn</b> — họ chưa rời Vietourist.
      </p>
      <div className="hang">
        <label>Loại kỳ{" "}
          <select value={kyLoai} onChange={(e) => setKyLoai(e.target.value)}>
            <option value="thang">Tháng</option><option value="quy">Quý</option>
            <option value="nam">Năm</option>
          </select>
        </label>
        <label>Kỳ{" "}
          <input value={ky} onChange={(e) => setKy(e.target.value)}
                 placeholder={kyLoai === "thang" ? "2026-10" : kyLoai === "quy" ? "2026-Q4" : "2026"} />
        </label>
        <button onClick={nap}>Xem</button>
      </div>
      {loi && <p className="loi">{loi}</p>}

      {bc && (<>
        <table className="bang">
          <thead>
            <tr><th>Phòng</th><th>Đầu kỳ</th><th>Tăng</th><th>Giảm</th><th>Cuối kỳ</th>
                <th>Lệch</th><th>Tỷ lệ nghỉ việc</th></tr>
          </thead>
          <tbody>
            {Object.entries(bc.theo_phong).map(([p, v]: any) => (
              <tr key={p}>
                <td>{p}</td><td>{v.dau_ky}</td><td>{v.tang}</td>
                <td>{v.giam}
                  {v.giam_chuyen_cong_ty > 0 &&
                    <span className="muted"> ({v.giam_chuyen_cong_ty} chuyển pháp nhân)</span>}
                </td>
                <td>{v.cuoi_ky}</td>
                <td className={v.lech !== 0 ? "canh-bao" : ""}>{v.lech}</td>
                <td>{v.ty_le_nghi_viec === null ? "—" : `${v.ty_le_nghi_viec}%`}</td>
              </tr>
            ))}
            {t && (
              <tr><th>Toàn công ty</th><th>{t.dau_ky}</th><th>{t.tang}</th><th>{t.giam}</th>
                  <th>{t.cuoi_ky}</th>
                  <th className={t.lech !== 0 ? "canh-bao" : ""}>{t.lech}</th>
                  <th>{t.ty_le_nghi_viec === null ? "—" : `${t.ty_le_nghi_viec}%`}</th></tr>
            )}
          </tbody>
        </table>

        {bc.chua_biet_ngay_nghi?.so_nguoi > 0 && (
          <div className="the">
            <h3>Đã nghỉ mà chưa có ngày nghỉ — {bc.chua_biet_ngay_nghi.so_nguoi} người</h3>
            <p className="canh-bao">
              Những người này <b>không nằm trong bất kỳ kỳ nào</b>, nên mọi kỳ ở trên đều cân — và cái
              cân ấy là <b>cân giả</b>: tổng cuối kỳ thiếu đúng bằng số người này. Đây là việc HCNS
              điền, không phải con số để báo cáo lên.
            </p>
            <table className="bang">
              <thead><tr><th>Mã</th><th>Họ tên</th><th>Phòng</th><th></th></tr></thead>
              <tbody>
                {bc.chua_biet_ngay_nghi.rows.map((r: any) => (
                  <tr key={r.employee_id}>
                    <td>{r.ma_nv}</td><td>{r.ho_ten}</td><td>{r.department}</td>
                    <td>{laHcns &&
                      <button onClick={() => ghiNghi(r.employee_id)}>Điền ngày nghỉ</button>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {bc.chua_co && (
          <p className="muted">
            <b>Báo cáo này chưa trả lời được:</b>{" "}
            {Object.values(bc.chua_co).join(" · ")}
          </p>
        )}
      </>)}

      {cc && (
        <div className="the">
          <h3>Cơ cấu người đang làm — {cc.so_nguoi} người</h3>
          <div className="hang">
            {[["Theo phòng", cc.theo_phong], ["Theo loại hợp đồng", cc.theo_loai_hop_dong],
              ["Theo văn phòng", cc.theo_van_phong], ["Thâm niên", cc.tham_nien]].map(([ten, m]: any) => (
              <div key={ten}>
                <b>{ten}</b>
                <ul>{Object.entries(m).map(([k, v]: any) => <li key={k}>{k}: {v}</li>)}</ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
