"use client";
import { useCallback, useEffect, useState } from "react";
import { api, fmtD, vnd } from "@/lib/api";
import { useShell } from "@/components/Shell";
import { xepDonVi } from "@/lib/thu_tu_don_vi";

/** Màn hình 01 · Tổng quan điều hành — khối dòng tiền bốn mốc và bốn ô cảnh báo.
 *
 *  MỘT ĐIỀU QUAN TRỌNG HƠN CẢ BỐ CỤC: khối này KHÔNG lọc gì hết.
 *
 *  Máy chủ trả về đúng tập dòng của vai đang đăng nhập (/dong-tien/khung), kể cả tên dòng đáy.
 *  Trình duyệt vẽ ra đúng những gì nhận được. Nếu một ngày nào đó ở đây xuất hiện một câu kiểu
 *  `if (vai === "tgd") ẩn dòng vay` thì SEC-02 đã hỏng: dòng bị ẩn vẫn ĐÃ rời khỏi máy chủ, và ai
 *  mở công cụ nhà phát triển cũng đọc được. Phép thử test_tc8 canh đúng chuyện đó.
 *
 *  HAI ĐIỀU KHÔNG LÀM
 *  1. Không hiện "0 đ" thay cho "chưa có số". Ô rỗng ghi "Chưa có nguồn" kèm tên bộ phận phải
 *     nhập — người đọc biết đi hỏi ai, thay vì tin một con số không có thật.
 *  2. Không cộng bốn cột. Bốn cột lũy kế từ cùng một ngày nên chồng lên nhau; cộng lại ra một con
 *     số lớn gấp mấy lần thực tế. Câu nhắc nằm ngay dưới bảng.
 */

const RONG = (vi_sao?: string) => (
  <span className="muted" title={vi_sao || "Chưa có số — khác hẳn với bằng 0"}>Chưa có nguồn</span>
);

function O({ o }: { o: any }) {
  const co = o.gia_tri !== null && o.gia_tri !== undefined && o.gia_tri !== "";
  const hien = !co ? null : o.kieu === "ngay" ? fmtD(String(o.gia_tri)) : vnd(o.gia_tri);
  return (
    <div className={"o-cb" + (co ? " red" : "")}>
      <b>{co ? hien : <span className="muted" style={{ fontSize: 15 }}>Chưa có nguồn</span>}</b>
      <span>{o.nhan}</span>
      {o.vi_sao && <span className="muted" style={{ fontSize: 11 }}>{o.vi_sao}</span>}
      {o.bo_phan && <span className="muted" style={{ fontSize: 11 }}>Bộ phận nối nguồn: {o.bo_phan}</span>}
    </div>
  );
}

export default function KhoiDongTien() {
  const { toast } = useShell();
  const [dsPn, setDsPn] = useState<any[]>([]);
  const [pn, setPn] = useState<number | null>(null);
  const [k, setK] = useState<any>(null);
  const [an, setAn] = useState(false);   // vai này không mở khối dòng tiền → không vẽ gì

  useEffect(() => {
    api("/dong-tien/meta")
      .then((r: any) => {
        // Xếp theo thứ tự đã chốt (VTD trước) chứ không theo bảng chữ cái của máy chủ: mở màn hình
        // ra mà con số đầu tiên đập vào mắt là của một pháp nhân nhỏ thì đó là con số ít cần nhất.
        const ds = xepDonVi(r.phap_nhan || []);
        setDsPn(ds);
        if (ds.length) setPn(ds[0].id);
        else setAn(true);
      })
      .catch(() => setAn(true));   // 403: vai này không xem khối dòng tiền – im lặng, không báo lỗi
  }, []);

  const tai = useCallback(async () => {
    if (!pn) return;
    try { setK(await api(`/dong-tien/khung/${pn}`)); }
    catch (e: any) { if (e?.status === 403) setAn(true); else toast(e?.message || "Không tải được khối dòng tiền", true); }
  }, [pn, toast]);
  useEffect(() => { tai(); }, [tai]);

  if (an || !k) return null;
  if (!k.xem_duoc) return null;

  const cot = k.cot || [];
  const nCot = cot.length;

  return (
    <section style={{ marginBottom: 14 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: 8 }}>
        <h2 style={{ margin: 0 }}>Dòng tiền — bốn mốc lũy kế</h2>
        {dsPn.length > 1 && (
          <select value={pn ?? ""} onChange={(e) => setPn(Number(e.target.value))}
            style={{ width: "auto", minWidth: 220 }} aria-label="Pháp nhân đang xem">
            {dsPn.map((c) => <option key={c.id} value={c.id}>{c.code} – {c.name}</option>)}
          </select>)}
        <span style={{ flex: 1 }} />
        <button type="button" className="act grey"
          onClick={() => toast("Xuất Excel khối dòng tiền: đang xây dựng")}>Xuất Excel</button>
      </div>

      <p className="muted" style={{ marginTop: 0 }}>{k.cau_pham_vi}</p>

      <div className="bon-o">{(k.canh_bao || []).map((o: any) => <O key={o.ma} o={o} />)}</div>

      <div className="panel wrap">
        <table>
          <thead><tr>
            <th style={{ minWidth: 240 }}>Dòng tiền</th>
            {cot.map((c: any) => <th key={c.ma} className="num">{c.ten}
              <div className="muted" style={{ fontWeight: 400, fontSize: 11 }}>
                {c.tu_hien || fmtD(c.tu_ngay)} – {c.den_hien || fmtD(c.den_ngay)}</div></th>)}
            <th style={{ minWidth: 200 }}>Cửa nhập · bộ phận</th>
          </tr></thead>
          <tbody>
            {(k.dong || []).map((d: any) => (
              <tr key={d.ma}>
                <td>{d.ten}</td>
                {d.mot_moc
                  ? <td className="num" colSpan={nCot} style={{ textAlign: "right" }}>
                      {d.so_mot_moc === null || d.so_mot_moc === undefined
                        ? RONG(d.vi_sao_rong)
                        : <>{vnd(d.so_mot_moc)} <span className="muted" style={{ fontSize: 11 }}>
                            (một mốc, không theo khoảng)</span></>}
                    </td>
                  : cot.map((c: any) => <td key={c.ma} className="num">
                      {(d.so || {})[c.ma] === null || (d.so || {})[c.ma] === undefined
                        ? RONG(d.vi_sao_rong || d.bo_phan_chiu_trach_nhiem)
                        : vnd((d.so || {})[c.ma])}
                    </td>)}
                <td style={{ fontSize: 11.5 }}>
                  {d.tu_tinh
                    ? <span className="muted">Tự cộng — không có cửa nhập</span>
                    : <>
                        <div className={d.da_co_nguon ? "" : "muted"}>{d.nguon}</div>
                        <div className="muted">{d.bo_phan}{d.cua_do_de_xuat ? " · cửa do đề xuất, chờ chốt" : ""}</div>
                      </>}
                </td>
              </tr>))}
            <tr>
              <td><b>{k.ten_dong_thuan}</b></td>
              {cot.map((c: any) => <td key={c.ma} className="num"><b>
                {(k.dong_tien_thuan || {})[c.ma] === null || (k.dong_tien_thuan || {})[c.ma] === undefined
                  ? RONG(k.vi_sao_khong_co_so_cuoi)
                  : vnd((k.dong_tien_thuan || {})[c.ma])}
              </b></td>)}
              <td />
            </tr>
          </tbody>
        </table>

        <p className="muted" style={{ fontSize: 12, marginBottom: 0 }}>{k.cong_bon_cot_la_sai}</p>
        {k.vi_sao_khong_co_so_cuoi && <p className="muted" style={{ fontSize: 12, marginBottom: 0 }}>
          {k.vi_sao_khong_co_so_cuoi}</p>}
        <p className="muted" style={{ fontSize: 12, marginBottom: 0 }}>
          Tập dòng và tên dòng đáy do MÁY CHỦ cắt theo vai đang đăng nhập (SEC-02); màn hình không
          lọc gì thêm. Số làm tròn đến đồng, dòng tổng cộng từ các dòng đã làm tròn.
          {k.doi_soat_den_ngay ? ` Đối soát đến ${fmtD(String(k.doi_soat_den_ngay))}.` : ""}
        </p>
      </div>
    </section>
  );
}
