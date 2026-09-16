"use client";
/** SÁU Ô LỚN của màn hình Chủ tịch — anh Tuấn chốt 16/9/2026.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  TÁM THẺ NHỎ → SÁU Ô LỚN + MỘT HÀNG THẺ NHỎ
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Anh Tuấn mở bản chạy thật rồi chốt: *"8 ô này anh muốn thay đổi vị trí — doanh thu, lợi nhuận
 *  trước thuế, dòng tiền, phải thu, phải trả, tồn đọng cần xử lý: 6 ô này làm biểu đồ lớn lên,
 *  chia ra các chart khác nhau theo cấu trúc; phần doanh thu và lợi nhuận phân ra theo tháng, quý,
 *  năm. Giảm từ 8 ô xuống còn 6 ô. Các phần tour đang bán, tour chờ quyết toán, tour sắp khởi
 *  hành, đội xe hôm nay, marketing đưa xuống vị trí dưới."*
 *
 *  Điều đáng ghi lại là VÌ SAO sáu ô ấy khác năm ô kia, chứ không phải chúng to hơn:
 *
 *    · SÁU Ô LỚN là những con số phải NGHĨ mới hiểu — chúng chỉ có nghĩa khi đặt cạnh kỳ trước,
 *      cạnh kế hoạch, hoặc chia theo cơ cấu. Một mình chúng không nói gì: "doanh thu 4,3 tỷ" là
 *      tốt hay xấu thì không ai trả lời được nếu không biết kế hoạch và tháng trước.
 *    · NĂM THẺ NHỎ là những con số chỉ để LIẾC — 349 tour đang bán, 93 tour sắp khởi hành. Đọc
 *      xong là xong, không cần so với gì cả. Thêm biểu đồ vào chúng là kéo mắt khỏi sáu ô trên.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  BA KHỐI CHUYỂN HẲN LÊN, KHÔNG ĐỂ LẠI BẢN SAO
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Dòng tiền · Phải thu · Phải trả trước vòng này là ba khối riêng nằm phía dưới. Anh Tuấn chọn
 *  "thay luôn — gộp lên trên". Nếu giữ cả hai thì mỗi con số nằm hai chỗ, đúng cái ông bảo bỏ ở
 *  vòng TC-40 ("các mục lặp lại thì bỏ hết"). Nên ba khối ấy KHÔNG có bản mới ở tệp này — chúng
 *  đổi CHỖ, không đổi mã. Tệp này chỉ dựng ba khối còn thiếu: Doanh thu, Lợi nhuận, Tồn đọng.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  TỆP NÀY KHÔNG TÍNH GÌ CẢ
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Ranh giới 09/9 giữ nguyên. Ba chuỗi tháng/quý/năm do `services/xu_huong.bo_ba_ky` dựng; tỉ lệ
 *  đạt kế hoạch do `services/ke_hoach.ty_le_dat` tính; ba mức tồn đọng do `services/canh_bao_muc`
 *  gom. Ở đây chỉ chọn trường nào vào hình nào, và diễn đạt lại thành câu.
 */
import { useState } from "react";
import Link from "next/link";
import {
  BieuDoCot, BieuDoCoCau, duVeCot, duVeCoCau, gonSo,
  type Diem, type Phan, type DinhDang,
} from "@/components/BieuDo";

type Ky = "thang" | "quy" | "nam";
const BA_KY: { ma: Ky; ten: string }[] = [
  { ma: "thang", ten: "Tháng" }, { ma: "quy", ten: "Quý" }, { ma: "nam", ten: "Năm" },
];

/** "2026-08" → "08/2026" · "2026-Q3" → "Q3/2026" · "2026" → "2026". */
export function tenKy(ky: string): string {
  const s = String(ky);
  if (s.includes("-Q")) { const [y, q] = s.split("-Q"); return `Q${q}/${y}`; }
  if (s.includes("-")) { const [y, m] = s.split("-"); return `${m}/${y}`; }
  return s;
}

const namCua = (ky: string) => String(ky).slice(0, 4);

/** Nhãn ngắn cho trục ngang: "T8" · "Q3" · "2026", và KÈM NĂM khi chuỗi vắt qua hai năm.
 *
 *  Trục có tới sáu cột nên nhãn dài là nhãn chồng lên nhau — đó là lý do mặc định cắt ngắn. Nhưng
 *  bốn quý gần nhất thường là "Q3 Q4 Q1 Q2", và đọc dãy ấy thì không ai biết Q3 thuộc năm nào;
 *  tệ hơn, cùng màn hình còn có quý đang chạy cũng tên Q3. Tìm ra bằng cách dựng ảnh ở TC-42.
 *
 *  Nên: chuỗi nằm gọn trong một năm thì nhãn ngắn; vắt qua năm thì thêm hai chữ số năm. Thêm năm
 *  cho MỌI nhãn chứ không riêng cái đầu năm mới — chỉ một nhãn mang năm thì nó đọc ra như một chú
 *  thích riêng của cột ấy, không đọc ra là mốc đổi năm.
 */
function nhanTruc(ky: string, kem_nam: boolean): string {
  const s = String(ky);
  const yy = s.slice(2, 4);
  if (s.includes("-Q")) return "Q" + s.split("-Q")[1] + (kem_nam ? "/" + yy : "");
  if (s.includes("-")) return "T" + Number(s.split("-")[1]) + (kem_nam ? "/" + yy : "");
  return s;      // năm thì bản thân nhãn đã là năm
}

function diemTu(c: any): Diem[] {
  const ds = c?.diem || [];
  const kem_nam = new Set(ds.map((d: any) => namCua(d.ky))).size > 1;
  return ds.map((d: any) => ({
    nhan: nhanTruc(d.ky, kem_nam),
    // `gia_tri === null` giữ nguyên là null: kỳ ấy CHƯA CÓ SỐ, và bộ biểu đồ vẽ nó thành ô trống
    // đúng vị trí. Quy về 0 ở đây là phá luật ngay tại cửa vào.
    gt: d.gia_tri === null || d.gia_tri === undefined ? null : Number(d.gia_tri),
    ghi: tenKy(d.ky),
  }));
}

function Dau({ ten, phu, ky, doiKy, nhan_nhom }: {
  ten: string; phu?: string; ky: Ky; doiKy: (k: Ky) => void; nhan_nhom: string;
}) {
  return (
    <div className="mh01-dau">
      <h2>{ten}</h2>
      {phu && <span className="tag">{phu}</span>}
      {/* Nút chọn kỳ nằm NGAY ĐẦU KHỐI, cạnh tên. Nó đổi ý nghĩa của mọi con số bên dưới, nên
          người đọc phải thấy mình đang xem kỳ nào TRƯỚC khi đọc số. */}
      <div className="v14-ky" role="group" aria-label={nhan_nhom}>
        {BA_KY.map((k) => (
          <button key={k.ma} type="button"
            className={"v14-ky-nut" + (ky === k.ma ? " chon" : "")}
            aria-pressed={ky === k.ma} onClick={() => doiKy(k.ma)}>{k.ten}</button>
        ))}
      </div>
    </div>
  );
}

/** MỘT Ô LỚN CÓ BA BỀ RỘNG KỲ. Dùng cho Doanh thu và Lợi nhuận trước thuế.
 *
 *  CON SỐ LỚN LÀ KỲ ĐANG CHẠY, BIỂU ĐỒ LÀ CÁC KỲ ĐÃ ĐÓNG — và hai điều ấy phải nói ra, không để
 *  người đọc tự đoán. Kỳ đang chạy mới đi được nửa đường; đặt nó vào biểu đồ cạnh các kỳ đủ ngày
 *  thì cột cuối luôn thấp và đường xu hướng luôn trông như đang lao dốc (luật 1 của xu_huong.py).
 *  Nhưng chính con số ấy, đặt riêng ra kèm chữ "đến hôm nay", lại là thứ Chủ tịch cần nhất.
 */
export function KhoiBaKy({ id, ten, phu, ba_ky, dinh_dang = "tien", moc, duoi, chan, ai, cua }: {
  id: string; ten: string; phu?: string; ba_ky?: any; dinh_dang?: DinhDang;
  moc?: (k: Ky) => { gt: number; nhan: string } | null;
  duoi?: (k: Ky) => string;
  chan?: string; ai?: string; cua?: string;
}) {
  const [ky, setKy] = useState<Ky>("thang");
  const c = ba_ky?.[ky];
  const diem = diemTu(c);
  const dc = c?.dang_chay;
  const m = moc ? moc(ky) : null;

  return (
    <section className="panel" id={id}>
      <Dau ten={ten} phu={phu} ky={ky} doiKy={setKy} nhan_nhom={`Kỳ xem của khối ${ten}`} />

      {!c
        ? <p className="muted">
            <span className="tag">Chưa kết nối</span> Máy chủ chưa trả chuỗi kỳ cho khối này.
            {ai && <> {ai} nhập.</>}{" "}
            {cua && <Link className="the-cua" href={cua}>Cửa nhập →</Link>}
          </p>
        : <>
            <div className="o6-so">
              <b className={"o6-lon" + (dc?.gia_tri === null || dc?.gia_tri === undefined ? " rong" : "")}>
                {dc?.gia_tri === null || dc?.gia_tri === undefined
                  ? "—" : gonSo(Number(dc.gia_tri), dinh_dang)}
              </b>
              <span className="muted o6-nhan">
                {dc ? <>{tenKy(dc.ky)} · đến hôm nay</> : "kỳ đang chạy"}
                {dc && dc.gia_tri === null && <> · chưa đủ số của {dc.so_thang_da_troi} tháng đã trôi</>}
              </span>
            </div>

            {duVeCot(diem)
              ? <BieuDoCot ten={`Các ${BA_KY.find((x) => x.ma === ky)!.ten.toLowerCase()} đã đóng`}
                  phu={`${diem.length} kỳ gần nhất`} diem={diem} dinh_dang={dinh_dang}
                  moc={m} chan={chan} />
              : <p className="muted v14-ghi">{c.vi_sao || "Chưa đủ hai kỳ có số để vẽ."}</p>}

            {duoi && duoi(ky) && <p className="muted v14-ghi">{duoi(ky)}</p>}
          </>}
    </section>
  );
}

/** Câu đọc hộ phần kế hoạch, dùng chung cho Doanh thu và Lợi nhuận.
 *
 *  Kế hoạch tháng là con số Kế toán nhập ở /ke-hoach-thang (TC-41). Nó chỉ có cho KỲ THÁNG: chỉ
 *  tiêu quý và năm là quyết định riêng của Hội đồng quản trị, không phải tổng ba tháng — nên bấm
 *  sang Quý mà thấy một vạch mốc dựng từ kế hoạch tháng là bịa ra một chỉ tiêu chưa ai duyệt.
 */
export function docHoKeHoachKy(ky: Ky, kh: any, don_vi: "doanh_thu" | "loi_nhuan_truoc_thue",
                               ty_le: number | null | undefined): string {
  if (ky !== "thang") {
    return "Kế hoạch mới có cho kỳ tháng — chỉ tiêu quý và năm do Hội đồng quản trị duyệt riêng, "
      + "hệ thống không suy ra từ kế hoạch tháng.";
  }
  const o = kh?.[don_vi];
  if (!o) return "Chưa có kế hoạch tháng để so sánh (Kế toán nhập ở Kế hoạch tháng).";
  if (!o.du) {
    const thieu: string[] = o.thieu || [];
    if (thieu.length === 0) return "Chưa có kế hoạch tháng để so sánh (Kế toán nhập ở Kế hoạch tháng).";
    const ten = thieu.slice(0, 2).join(", ")
      + (thieu.length > 2 ? ` và ${thieu.length - 2} pháp nhân nữa` : "");
    return `Kế hoạch tháng chưa đủ — còn thiếu ${ten} (Kế toán nhập ở Kế hoạch tháng).`;
  }
  const dau = `Kế hoạch tháng ${gonSo(Number(o.gia_tri), "tien")}`;
  if (ty_le === null || ty_le === undefined) return `${dau} · chưa tính được tỉ lệ đạt.`;
  return `${dau} · đạt ${Math.round(ty_le * 100)}%.`;
}

/** Vạch mốc kế hoạch trên biểu đồ — CHỈ ở kỳ tháng, và chỉ khi kế hoạch đã đủ mọi pháp nhân. */
function mocKeHoach(kh: any, don_vi: "doanh_thu" | "loi_nhuan_truoc_thue") {
  return (ky: Ky) => {
    if (ky !== "thang") return null;
    const o = kh?.[don_vi];
    if (!o || !o.du || o.gia_tri === null || o.gia_tri === undefined) return null;
    return { gt: Number(o.gia_tri), nhan: "Kế hoạch tháng" };
  };
}

export function KhoiDoanhThu({ ba_ky, ke_hoach, so_chuyen }: {
  ba_ky?: any; ke_hoach?: any; so_chuyen?: number | null;
}) {
  return (
    <KhoiBaKy id="doanh-thu" ten="Doanh thu" phu="chuyến đã quyết toán" ba_ky={ba_ky?.doanh_thu_thang}
      moc={mocKeHoach(ke_hoach, "doanh_thu")}
      duoi={(ky) => (ky === "thang" && typeof so_chuyen === "number"
        ? `${so_chuyen} chuyến đã quyết toán trong tháng. ` : "")
        + docHoKeHoachKy(ky, ke_hoach, "doanh_thu", ke_hoach?.ty_le_dat_doanh_thu)}
      chan="Kỳ đang chạy KHÔNG nằm trong biểu đồ: đặt một kỳ mới đi nửa đường cạnh các kỳ đủ ngày thì cột cuối luôn thấp và đường xu hướng luôn trông như đang lao dốc."
      ai="Kế toán" cua="/ke-hoach-thang" />
  );
}

export function KhoiLoiNhuan({ ba_ky, ke_hoach }: { ba_ky?: any; ke_hoach?: any }) {
  return (
    <KhoiBaKy id="loi-nhuan" ten="Lợi nhuận trước thuế" phu="sổ kế toán"
      ba_ky={ba_ky?.ln_ke_toan_thang}
      moc={mocKeHoach(ke_hoach, "loi_nhuan_truoc_thue")}
      duoi={(ky) => docHoKeHoachKy(ky, ke_hoach, "loi_nhuan_truoc_thue",
                                   ke_hoach?.ty_le_dat_loi_nhuan)}
      chan="Cột dưới vạch 0 là kỳ lỗ. Lỗ ít đi so với kỳ trước vẫn tính là TĂNG — so sánh chia cho trị tuyệt đối."
      ai="Kế toán" cua="/ke-hoach-thang" />
  );
}

/** TỒN ĐỌNG CẦN XỬ LÝ, tách theo ba mức độ.
 *
 *  Trước vòng này khối này là một con số duy nhất (1483 cảnh báo đỏ). Một con số nằm một mình thì
 *  không nói được điều gì để hành động — không biết bao nhiêu phần trong đó là việc phải làm ngay.
 *
 *  Nhóm "Chưa phân loại" hiện RA chứ không bị gộp lặng lẽ: `Alert.level` là cột chuỗi, nên một
 *  robot viết sai chính tả mức là sinh ra một mức thứ tư. Gộp nó vào đâu đó thì tổng trên màn hình
 *  nhỏ hơn số việc thật; hiện nó ra thì trong tuần sẽ có người đi sửa.
 */
export function KhoiTonDongMuc({ d }: { d?: any | null }) {
  if (!d) {
    return (
      <section className="panel" id="ton-dong">
        <div className="mh01-dau"><h2>Tồn đọng cần xử lý</h2></div>
        <p className="muted">
          <span className="tag">Chưa kết nối</span> Máy chủ chưa trả bảng tồn đọng theo mức độ.{" "}
          <Link className="the-cua" href="/alerts">Trang cảnh báo →</Link>
        </p>
      </section>
    );
  }
  const phan: Phan[] = (d.phan || []).map((p: any) => ({
    ten: p.ten, gt: p.so === null || p.so === undefined ? null : Number(p.so),
    trang_thai: !!p.trang_thai,
  }));
  const do_ = (d.phan || []).find((p: any) => p.ma === "red")?.so ?? 0;
  return (
    <section className="panel" id="ton-dong">
      <div className="mh01-dau">
        <h2>Tồn đọng cần xử lý</h2>
        <span className="tag">chưa xử lý</span>
      </div>
      <div className="o6-so">
        <b className={"o6-lon" + (do_ > 0 ? " do" : "")}>{gonSo(Number(d.tong || 0), "dem")}</b>
        <span className="muted o6-nhan">việc đang mở · {gonSo(Number(do_), "dem")} mức nghiêm trọng</span>
      </div>
      {duVeCoCau(phan)
        ? <BieuDoCoCau ten="Cơ cấu theo mức độ" ds={phan} dinh_dang="dem"
            chan="Mức Nghiêm trọng mang màu cảnh báo vì nó là TRẠNG THÁI — việc đã thành vấn đề, không phải nấc nặng nhất của một thang." />
        : <p className="muted v14-ghi">Chưa có việc nào đang mở, nên chưa có cơ cấu để vẽ.</p>}
      <p className="muted v14-ghi">
        {d.co_muc_la
          ? <>Có việc mang mức KHÔNG nằm trong ba mức đã khai — hiện ở nhóm “Chưa phân loại”. Gộp
              lặng lẽ vào một mức khác là làm tổng trên màn hình nhỏ hơn số việc thật. (CNTT) </>
          : <>Chưa tách được hồ sơ quá hạn và hồ sơ chưa có người nhận — hai chỉ tiêu ấy máy chủ
              chưa đếm. (CNTT) </>}
        <Link className="the-cua" href="/alerts">Xem danh sách →</Link>
      </p>
    </section>
  );
}
