"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, fmtD, taiTep, vnd } from "@/lib/api";
import { useShell } from "@/components/Shell";
import { xepDonVi, type DonViChon } from "@/lib/thu_tu_don_vi";

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
 *  2. Không cộng bốn cột Ở KIỂU LUỸ KẾ. Bốn cột lũy kế từ cùng một ngày nên chồng lên nhau; cộng
 *     lại ra một con số lớn gấp mấy lần thực tế. Câu nhắc nằm ngay dưới bảng, và nó ĐỔI theo kiểu
 *     xem đang chọn — ở kiểu "trong từng khoảng" thì bốn cột rời nhau nên cộng lại LẠI ĐÚNG.
 *
 *  HAI THỨ THÊM NGÀY 14/9/2026 (phương án dung hoà anh Tuấn chốt 13/9)
 *
 *  · CỘT TRẠNG THÁI BA MỨC thay cho cột "Cửa nhập · bộ phận". Bản vẽ V1.4 đòi bỏ hẳn cột cửa nhập
 *    khỏi trang Chủ tịch; bỏ hẳn thì ngược ranh giới 09/9. Nên trang này chỉ còn MỘT nhãn ba mức,
 *    còn nguyên nhân · bộ phận · cửa nhập chuyển sang trang /dong-tien/nguon.
 *
 *  · NÚT ĐỔI KIỂU XEM luỹ kế ↔ trong từng khoảng. Bản vẽ muốn bốn mốc không luỹ kế. Số trong từng
 *    khoảng là HIỆU của hai cột luỹ kế liền nhau — máy chủ tính, không tính ở trình duyệt. Ba dòng
 *    MỨC (tiền đầu kỳ · số dư cuối khoảng · thiếu so với dự phòng) giữ nguyên số ở cả hai kiểu và
 *    mang cờ la_dong_chay=false, vì chúng là mức tại mốc chứ không phải lượng tiền chảy qua.
 */

/** Nhãn ba mức. Màu lấy từ bộ nhận diện: xanh lá đủ · vàng cần chú ý · đỏ còn thiếu. */
function ChipTrangThai({ ma, nhan }: { ma?: string; nhan?: string }) {
  if (!ma || !nhan) return null;
  const cls = ma === "day_du" ? "ok" : ma === "chua_doi_soat" ? "warn" : "red";
  return <span className={"tag " + cls}>{nhan}</span>;
}

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
  // Mặc định LUỸ KẾ, không phải kiểu mới. Kiểu luỹ kế là kiểu đã in ra trong tài liệu v1.1 và là
  // kiểu người đọc đang quen; đổi mặc định là hôm sau có người đọc bảng mới bằng thói quen cũ.
  const [khoang, setKhoang] = useState(false);
  const [dangXuat, setDangXuat] = useState(false);

  useEffect(() => {
    api("/dong-tien/meta")
      .then((r: any) => {
        // Xếp theo thứ tự đã chốt (VTD trước) chứ không theo bảng chữ cái của máy chủ: mở màn hình
        // ra mà con số đầu tiên đập vào mắt là của một pháp nhân nhỏ thì đó là con số ít cần nhất.
        // Ghi rõ kiểu phần tử: `r` là any nên nếu để suy diễn, T rơi về đúng ràng buộc {code} và
        // `ds[0].id` không còn tồn tại dưới mắt trình biên dịch (CI/web bắt đỏ lần đầu).
        const ds = xepDonVi<DonViChon>(r.phap_nhan || []);
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
  const tt = k.tom_tat_trang_thai || {};

  /** Số của một dòng ở kiểu xem đang chọn. Dòng MỨC không có số theo khoảng nên luôn lấy `so`. */
  const soCua = (d: any) => (khoang && d.la_dong_chay ? d.so_khoang : d.so) || {};

  return (
    <section style={{ marginBottom: 14 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: 8 }}>
        <h2 style={{ margin: 0 }}>Dòng tiền — bốn mốc {khoang ? "trong từng khoảng" : "lũy kế"}</h2>
        <div className="dt-kieu" role="group" aria-label="Kiểu xem bốn mốc">
          <button type="button" className={"act" + (khoang ? " grey" : "")}
            aria-pressed={!khoang} onClick={() => setKhoang(false)}>Lũy kế</button>
          <button type="button" className={"act" + (khoang ? "" : " grey")}
            aria-pressed={khoang} onClick={() => setKhoang(true)}>Trong từng khoảng</button>
        </div>
        {dsPn.length > 1 && (
          <select value={pn ?? ""} onChange={(e) => setPn(Number(e.target.value))}
            style={{ width: "auto", minWidth: 220 }} aria-label="Pháp nhân đang xem">
            {dsPn.map((c) => <option key={c.id} value={c.id}>{c.code} – {c.name}</option>)}
          </select>)}
        <span style={{ flex: 1 }} />
        {/* NÚT XUẤT EXCEL THẬT (14/9/2026). Trước đây nó chỉ hiện câu "đang xây dựng" — một nút
            hứa rồi không làm còn tệ hơn không có nút, vì lần sau người dùng không tin nút nào nữa.
            Tệp do MÁY CHỦ dựng từ đúng gói mà màn hình này đang đọc, nên Excel không thể nói khác
            màn hình; và máy chủ ghi một dòng nhật ký cho mỗi lần xuất. */}
        <button type="button" className="act grey" disabled={dangXuat || !pn}
          onClick={async () => {
            if (!pn) return;
            setDangXuat(true);
            try { toast("Đã tải " + await taiTep(`/dong-tien/khung/${pn}/excel`)); }
            catch (e: any) { toast(e?.message || "Không xuất được Excel", true); }
            finally { setDangXuat(false); }
          }}>{dangXuat ? "Đang dựng tệp…" : "Xuất Excel"}</button>
      </div>

      <p className="muted" style={{ marginTop: 0 }}>{k.cau_pham_vi}</p>

      {/* DÒNG TÓM TẮT NGUỒN SỐ — phần "một nhãn thay cho cột cửa nhập" của phương án dung hoà.
          Đếm theo DÒNG CÓ CỬA (bỏ dòng tự cộng), vì dòng tự cộng không ai nhập được. */}
      <p className="dt-tomtat">
        <b>Nguồn số:</b>{" "}
        <span className="tag ok">{tt.day_du ?? 0} đầy đủ</span>{" "}
        <span className="tag warn">{tt.chua_doi_soat ?? 0} chưa đối soát</span>{" "}
        <span className="tag red">{tt.con_thieu ?? 0} còn thiếu</span>{" "}
        <Link className="the-cua" href="/dong-tien/nguon">Nguyên nhân · bộ phận · cửa nhập →</Link>
      </p>

      <div className="bon-o">{(k.canh_bao || []).map((o: any) => <O key={o.ma} o={o} />)}</div>

      <div className="panel wrap">
        <table>
          <thead><tr>
            <th style={{ minWidth: 240 }}>Dòng tiền</th>
            {cot.map((c: any) => <th key={c.ma} className="num">{c.ten}
              <div className="muted" style={{ fontWeight: 400, fontSize: 11 }}>
                {/* Ngày đầu ĐỔI theo kiểu xem: luỹ kế thì mọi cột cùng bắt đầu từ ngày báo cáo,
                    theo khoảng thì cột sau bắt đầu ngay sau ngày kết thúc của cột trước. In sai
                    ngày ở đây là người đọc cộng nhầm hai khoảng chồng nhau.

                    CẢ HAI ĐẦU LẤY CHUỖI ĐÃ ĐỊNH DẠNG SẴN CỦA MÁY CHỦ (tu_hien · den_hien ·
                    tu_hien_khoang). fmtD chỉ là lối lui khi máy chủ chưa gửi chuỗi ấy. Trộn hai
                    nơi định dạng thì ra đúng cái ô đã gặp: "14/09/2026 – 20-09-2026". */}
                {khoang
                  ? (c.tu_hien_khoang || fmtD(c.tu_ngay_khoang || c.tu_ngay))
                  : (c.tu_hien || fmtD(c.tu_ngay))}
                {" – "}{c.den_hien || fmtD(c.den_ngay)}</div></th>)}
            <th style={{ minWidth: 130 }}>Nguồn số</th>
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
                      {soCua(d)[c.ma] === null || soCua(d)[c.ma] === undefined
                        ? RONG(d.vi_sao_rong || d.bo_phan_chiu_trach_nhiem)
                        : vnd(soCua(d)[c.ma])}
                    </td>)}
                <td style={{ fontSize: 11.5 }}>
                  {d.tu_tinh
                    ? <span className="muted">Tự cộng</span>
                    : <ChipTrangThai ma={d.trang_thai} nhan={d.nhan_trang_thai} />}
                  {khoang && d.la_dong_chay === false && !d.mot_moc &&
                    <div className="muted" style={{ marginTop: 3 }}>mức tại mốc</div>}
                </td>
              </tr>))}
            <tr>
              <td><b>{k.ten_dong_thuan}</b></td>
              {cot.map((c: any) => {
                const t = ((khoang ? k.dong_tien_thuan_khoang : k.dong_tien_thuan) || {})[c.ma];
                return <td key={c.ma} className="num"><b>
                  {t === null || t === undefined ? RONG(k.vi_sao_khong_co_so_cuoi) : vnd(t)}
                </b></td>;
              })}
              <td />
            </tr>
          </tbody>
        </table>

        {/* CÂU NHẮC ĐỔI THEO KIỂU XEM. Giữ nguyên một câu cho cả hai kiểu là chắc chắn sai một
            nửa số lần: luỹ kế thì cộng bốn cột là sai, theo khoảng thì cộng bốn cột lại đúng. */}
        <p className="muted" style={{ fontSize: 12, marginBottom: 0 }}>
          {khoang ? k.cong_bon_cot_khi_xem_khoang : k.cong_bon_cot_la_sai}</p>
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
