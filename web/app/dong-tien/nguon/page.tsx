"use client";
/** NGUỒN SỐ CỦA BẢNG DÒNG TIỀN — trang chi tiết của phương án dung hoà (anh Tuấn chốt 13/9/2026).
 *
 *  Bản vẽ V1.4 đòi BỎ HẲN cột "Cửa nhập · bộ phận" khỏi trang Chủ tịch. Bỏ hẳn thì ngược ranh giới
 *  09/9: mỗi con số phải có một cửa nhập, và cửa nào chưa có phải nhìn thấy được, nếu không nó nằm
 *  đó mãi. Phương án dung hoà: màn hình 01 chỉ còn MỘT nhãn ba mức, còn TRANG NÀY giữ đủ nguyên
 *  nhân · bộ phận chịu · nguồn hiện có · cửa nhập phải dựng.
 *
 *  TRANG NÀY KHÔNG LỌC GÌ (SEC-02). Máy chủ đã cắt tập dòng theo vai ở /dong-tien/khung; ở đây chỉ
 *  vẽ lại đúng những dòng nhận được. Vai nào không được xem khối dòng tiền thì /dong-tien/meta trả
 *  403 và trang nói thẳng là không có quyền, chứ không hiện một bảng rỗng trông như chưa có dữ liệu.
 *
 *  HẠN XỬ LÝ: bản vẽ muốn có cột hạn. Hệ thống hôm nay KHÔNG có chỗ nào ghi hạn khắc phục cho từng
 *  dòng dòng tiền — không có bảng, không có cửa nhập. Nên cột hạn vẫn dựng, và mỗi ô ghi "chưa đặt"
 *  kèm bộ phận. Bịa một hạn ra là hạn ấy trôi qua mà không ai biết mình đã lỡ cái gì.
 */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { errMsg } from "@/components/ui";
import { xepDonVi, type DonViChon } from "@/lib/thu_tu_don_vi";

const NHAN: Record<string, string> = {
  day_du: "Đầy đủ", chua_doi_soat: "Chưa đối soát", con_thieu: "Còn thiếu",
};
const LOP: Record<string, string> = { day_du: "ok", chua_doi_soat: "warn", con_thieu: "red" };

/** Thứ tự trình bày: việc còn thiếu lên trước. Trang này để đi đòi nguồn, không để tra cứu theo
 *  thứ tự bảng — dòng đã đầy đủ đọc sau cùng cũng không sao. */
const NANG: Record<string, number> = { con_thieu: 0, chua_doi_soat: 1, day_du: 2 };

function Trang() {
  const { toast } = useShell();
  const [dsPn, setDsPn] = useState<DonViChon[]>([]);
  const [pn, setPn] = useState<number | null>(null);
  const [k, setK] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const [cam, setCam] = useState(false);

  useEffect(() => {
    api("/dong-tien/meta")
      .then((r: any) => {
        const ds = xepDonVi<DonViChon>(r.phap_nhan || []);
        setDsPn(ds);
        if (ds.length) setPn(ds[0].id); else setCam(true);
      })
      .catch((e: any) => { if (e?.status === 403) setCam(true); else setLoi(errMsg(e)); });
  }, []);

  const tai = useCallback(async () => {
    if (!pn) return;
    setLoi("");
    try { setK(await api(`/dong-tien/khung/${pn}`)); }
    catch (e: any) { if (e?.status === 403) setCam(true); else setLoi(errMsg(e) || "Không tải được"); }
  }, [pn]);
  useEffect(() => { tai(); }, [tai]);

  if (cam) return <div className="panel">
    <h1>Nguồn số của bảng dòng tiền</h1>
    <p className="muted">Tài khoản này không được xem khối dòng tiền. Máy chủ cắt quyền theo vai
      (SEC-02), không phải màn hình ẩn đi.</p>
  </div>;

  if (loi) return <div className="panel" style={{ borderColor: "var(--red)" }}>
    <b style={{ color: "var(--red)" }}>Không tải được nguồn số.</b>
    <div className="muted" style={{ margin: "6px 0" }}>{loi}</div>
    <button className="act" onClick={tai}>Thử lại</button>
  </div>;

  if (!k) return <p className="muted">Đang tải…</p>;

  // Dòng TỰ CỘNG không có cửa nhập nên không nằm trong danh sách đi đòi nguồn — nó thiếu là vì
  // dòng khác thiếu. Vẫn liệt kê ở cuối, ghi rõ nó phụ thuộc dòng nào.
  const co_cua = (k.dong || []).filter((d: any) => !d.tu_tinh)
    .slice().sort((a: any, b: any) => (NANG[a.trang_thai] ?? 9) - (NANG[b.trang_thai] ?? 9));
  const tu_cong = (k.dong || []).filter((d: any) => d.tu_tinh && d.chua_co_nguon);
  const tt = k.tom_tat_trang_thai || {};

  return (<>
    <h1>Nguồn số của bảng dòng tiền</h1>
    <p className="muted">
      <Link href="/">← Bảng điều hành</Link> · Mỗi dòng của bảng dòng tiền phải có một cửa nhập hoặc
      một cửa tải. Trang này nói dòng nào đã có, dòng nào chưa, và ai phải nhập.
    </p>

    <div className="panel">
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        {dsPn.length > 1 && (
          <select value={pn ?? ""} onChange={(e) => setPn(Number(e.target.value))}
            style={{ width: "auto", minWidth: 220 }} aria-label="Pháp nhân đang xem">
            {dsPn.map((c) => <option key={c.id} value={c.id}>{c.code} – {c.name}</option>)}
          </select>)}
        <span className="tag ok">{tt.day_du ?? 0} đầy đủ</span>
        <span className="tag warn">{tt.chua_doi_soat ?? 0} chưa đối soát</span>
        <span className="tag red">{tt.con_thieu ?? 0} còn thiếu</span>
      </div>
      <p className="muted" style={{ marginBottom: 0 }}>{k.cau_pham_vi}</p>
    </div>

    <div className="panel">
      <h2>Từng dòng</h2>
      <div className="wrap">
        <table className="v14-bang">
          <thead><tr>
            <th style={{ minWidth: 180 }}>Dòng tiền</th>
            <th style={{ minWidth: 110 }}>Nguồn số</th>
            <th style={{ minWidth: 200 }}>Nguyên nhân</th>
            <th style={{ minWidth: 130 }}>Bộ phận chịu</th>
            <th style={{ minWidth: 220 }}>Nguồn hiện có</th>
            <th style={{ minWidth: 240 }}>Cửa nhập phải dựng</th>
            <th style={{ minWidth: 90 }}>Hạn xử lý</th>
          </tr></thead>
          <tbody>
            {co_cua.map((d: any) => (
              <tr key={d.ma}>
                <td><b>{d.ten}</b></td>
                <td><span className={"tag " + (LOP[d.trang_thai] || "")}>
                  {NHAN[d.trang_thai] || d.nhan_trang_thai || "—"}</span></td>
                <td>{d.nguyen_nhan || <span className="muted">—</span>}</td>
                <td>{d.bo_phan || <span className="muted">chưa gán</span>}</td>
                <td className={d.da_co_nguon ? "" : "muted"}>
                  {d.nguon || <span className="muted">chưa khai</span>}</td>
                <td>{d.cua || <span className="muted">chưa khai</span>}
                  {d.cua_do_de_xuat && <> <span className="tag warn">cửa do đề xuất, chờ chốt</span></>}</td>
                <td><span className="muted">chưa đặt</span></td>
              </tr>))}
          </tbody>
        </table>
      </div>
      <p className="muted v14-ghi">
        Cột <b>Hạn xử lý</b> chưa có nguồn: hệ thống chưa có bảng nào ghi hạn khắc phục cho từng dòng
        dòng tiền, và cũng chưa có cửa nhập hạn. Đây là việc còn thiếu — không phải ô để trống cho đẹp.
      </p>
    </div>

    {tu_cong.length > 0 && (
      <div className="panel">
        <h2>Dòng tự cộng đang rỗng</h2>
        <p className="muted">Những dòng này không có cửa nhập. Chúng rỗng vì dòng khác rỗng — chữa
          dòng ở bảng trên là chúng tự có số.</p>
        <div className="wrap">
          <table className="v14-bang">
            <thead><tr><th style={{ minWidth: 200 }}>Dòng</th><th>Đang chờ dòng nào</th></tr></thead>
            <tbody>
              {tu_cong.map((d: any) => (
                <tr key={d.ma}>
                  <td><b>{d.ten}</b></td>
                  <td>{d.vi_sao_rong || <span className="muted">—</span>}</td>
                </tr>))}
            </tbody>
          </table>
        </div>
      </div>)}
  </>);
}

export default function Page() {
  return <Shell><Trang /></Shell>;
}
