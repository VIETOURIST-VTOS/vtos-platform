"use client";
/** SÁU KHỐI CÒN LẠI CỦA BẢN VẼ V1.4 – màn hình 01 (13/9/2026).
 *
 *  Bản vẽ xếp tám khối; VTOS đã có 01 phạm vi/kỳ, 02 cần quyết định, 03 tám thẻ, và 06 dòng tiền
 *  (dựng theo hình khác, xem ghi chú cuối tệp). Tệp này dựng phần còn lại:
 *
 *  TC-40 (15/9/2026) — BA TRONG SÁU KHỐI NÀY ĐÃ GỠ KHỎI MÀN HÌNH 01.
 *  Anh Tuấn soát từng khối trên bản chạy thật và chốt danh sách GIỮ: 04b Hiệu quả đội xe, 05a
 *  Phải thu, 05b Phải trả. Ba khối bị gỡ: 04c Tồn đọng theo bộ phận, 07 Rủi ro trọng yếu, 08
 *  Tiến độ báo cáo.
 *
 *  Lý do gỡ không phải "làm thiếu" mà là TRÙNG hoặc RỖNG-KHÔNG-AI-DÙNG: 04c nói đúng con số mà
 *  thẻ "Tồn đọng cần xử lý" đã nói; 07 và 08 là hai bảng chưa có sổ nào phía sau, mỗi bảng chiếm
 *  gần một màn hình để ghi "Chưa kết nối".
 *
 *  Mã của chúng GIỮ NGUYÊN ở đây, không xoá, vì hai lẽ: các `type` bên dưới là HỢP ĐỒNG với máy
 *  chủ — bản mô tả những trường máy chủ còn nợ, xoá đi là mất bản mô tả; và khi nào có màn hình
 *  riêng cho từng phòng thì ba khối ấy lắp vào đó là dùng được ngay.
 *
 *    04b  Hiệu quả đội xe trong kỳ
 *    04c  Tồn đọng theo bộ phận
 *    05a  Phải thu theo hạn thanh toán   – 5 nhóm KHÔNG trùng nhau
 *    05b  Phải trả theo hạn thanh toán   – 5 nhóm + quá hạn theo dõi riêng
 *    07   Rủi ro trọng yếu
 *    08   Tiến độ báo cáo & kết luận chỉ đạo
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  RANH GIỚI 09/9 – ĐỌC TRƯỚC KHI SỬA TỆP NÀY
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Sáu khối này HÔM NAY CHƯA CÓ MỘT CON SỐ NÀO. Máy chủ chưa có bảng cho chúng. Đó là lý do mỗi ô
 *  đều ghi "Chưa kết nối" kèm BỘ PHẬN phải nhập và CỬA NHẬP để đi tới.
 *
 *  Bản vẽ chỉ ghi "Chưa kết nối". VTOS ghi thêm bộ phận và cửa nhập, vì một ô trống không nói ai
 *  chịu trách nhiệm thì nó nằm đó mãi: ai đọc cũng nghĩ người khác lo. Đây là chỗ VTOS làm HƠN bản
 *  vẽ, có chủ đích.
 *
 *  TUYỆT ĐỐI KHÔNG điền số mẫu, số ước lượng, hay số suy ra từ khối khác để "cho đỡ trống". Một con
 *  số trên bảng điều hành Chủ tịch là một con số ông ấy sẽ dùng để quyết.
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *
 *  HỢP ĐỒNG VỚI MÁY CHỦ nằm ngay dưới, ở các `type`. Làn viết máy chủ chỉ cần trả đúng những trường
 *  ấy trong /api/v1/dashboard; khối nào chưa có thì để thiếu, màn hình tự hiện "Chưa kết nối" chứ
 *  không vỡ.
 */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Tag } from "@/components/ui";
import { gonSo } from "@/components/BieuDo";
import { api } from "@/lib/api";

/* ─────────────────────────────── HỢP ĐỒNG DỮ LIỆU ─────────────────────────────── */

/** 04b · Hiệu quả đội xe trong kỳ. Bốn chỉ số + một trạng thái chốt sổ.
 *  CẢNH BÁO NGHIỆP VỤ ghi trong bản vẽ, giữ nguyên: xe không có lệnh CHƯA CHẮC sẵn sàng, và công
 *  suất tính trên thời gian xe CÓ THỂ khai thác chứ không phải trên số ngày trong kỳ. */
export type HieuQuaXe = {
  ngay_xe_hoat_dong?: number | null;
  cong_suat_khai_thac?: number | null;   // phần trăm, 0–100
  km_chay_rong?: number | null;
  chi_phi_moi_km?: number | null;        // đồng
  /** HQ-1b (13/10/2026) — VÌ SAO công suất trống, và AI phải làm gì.
   *
   *  Công suất là ô duy nhất trong bốn ô có thể trống trong khi ba ô kia có số: nó cần MẪU SỐ
   *  (đội hình xe tại kỳ), mà mẫu số ấy do người khai chứ không suy ra được. Một ô gạch ngang
   *  nằm giữa ba ô có số đọc ra như ô hỏng, chứ không đọc ra là "đang chờ ai đó nhập".
   *
   *  Máy chủ đã tính sẵn ô này từ vòng HQ-1; chỗ này chỉ in ra. Rỗng nghĩa là KHÔNG thiếu gì. */
  cong_suat_thieu?: {
    bo_phan: string;                     // bộ phận phải khai
    cua_nhap: string;                    // đường tới cửa nhập
    thieu: { xe: string; thieu: string }[];
  } | null;
  /** HQ-1c (13/10/2026) — nhãn kỳ ("Tháng 10/2026", "Năm 2026 (T01–T10)") và VÌ SAO kỳ ấy trống.
   *  "Năm" mà thật ra mới tới tháng 10 là chỗ rất dễ đọc nhầm, nên nhãn nói thẳng khoảng. */
  nhan?: string;
  trong_vi_sao?: string | null;
  da_chot?: boolean;                      // kỳ đã khoá sổ hay chưa
  /** HQ-2 (13/10/2026) — ba chỉ số Chủ tịch chọn thêm.
   *
   *  `doanh_thu` cộng thẳng từ dòng chuyến: Chủ tịch quyết 13/10/2026 rằng con số trên mỗi dòng là
   *  giá của MỖI XE, nên một đoàn ba xe cộng cả ba là đúng. Đo trước khi hỏi: 59 đoàn dùng nhiều
   *  hơn một xe, 40 đoàn trong đó ghi số tiền giống hệt nhau — 573.460.000 đ treo trên đúng câu
   *  hỏi ấy.
   *
   *  `tieu_hao_l100` chia cho KM CHUYẾN, không cộng km rỗng. `tieu_hao_nguong_thieu` rỗng nghĩa là
   *  Đội xe đã khai ngưỡng; có giá trị nghĩa là con số vẫn in ra nhưng chưa ai bật được cảnh báo. */
  doanh_thu?: number | null;
  loi_nhuan?: number | null;
  ty_le_loi_nhuan?: number | null;        // phân số, 0–1
  tieu_hao_l100?: number | null;
  tieu_hao_nguong_thieu?: { bo_phan: string; cua_nhap: string } | null;
  tieu_hao_vuot?: { xe: string; so_cho: number; tieu_hao: number; nguong: number }[] | null;
  /** So với kỳ liền trước, CÙNG SỐ THÁNG. Rỗng khi kỳ chưa hết — lúc ấy `chua_so_sanh_vi` nói vì
   *  sao: 13 ngày đầu tháng 10 so với trọn tháng 9 là so lệch, và mũi tên đỏ ấy nói về tờ lịch
   *  chứ không nói về đội xe. */
  so_sanh?: {
    nhan: string;
    lech: Record<string, number | null>;
    truoc: Record<string, number | null>;
  } | null;
  chua_so_sanh_vi?: string | null;
};

/** 04c · Tồn đọng theo bộ phận. MỖI HỒ SƠ CHỈ TÍNH MỘT LẦN (bản vẽ nhấn mạnh): một hồ sơ phát ba
 *  cảnh báo vẫn là một hồ sơ, cộng cả ba là thổi phồng con số. Việc chống trùng làm Ở MÁY CHỦ. */
export type DongTonDong = {
  bo_phan: string;
  ma_bo_phan?: string;
  ho_so_qua_han?: number | null;
  ho_so_lau_nhat?: string | null;        // ví dụ "42 ngày · TOUR-A"
  nguoi_chiu_trach_nhiem?: string | null;
  han_khac_phuc?: string | null;
};

/** TC-32 · Hai thứ đi KÈM bảng 04c, và không cái nào là trang trí.
 *
 *  `chua_ro_bo_phan` – hồ sơ chưa suy ra được bộ phận vì cảnh báo chưa giao cho ai. Đây là một
 *  DÒNG ĐƯỢC ĐẾM, không phải một ô trống bị bỏ qua: nhét nó vào một phòng là đổ việc cho người
 *  không gây ra nó; giấu nó đi là làm tổng bảng nhỏ hơn sự thật mà không ai thấy.
 *
 *  `da_loai` – những loại cảnh báo CỐ Ý không tính là hồ sơ quá hạn, kèm lý do. Phải hiện ra: khối
 *  "Tồn đọng cần xử lý" ngay trên trang ghi 1.476, khối này ghi vài chục. Hai con số lệch nhau mà
 *  không giải thích thì người đọc kết luận một trong hai cái sai — và họ có lý.
 */
export type ChuaRoBoPhan = { so: number; vi_sao: string };
export type LoaiDaLoai = { loai: string; so_ho_so: number; ly_do: string };

/** 05 · Một nhóm hạn thanh toán. `nhan` là tên nhóm, `mo_ta` là định nghĩa khoảng – in ra màn hình
 *  để không ai phải đoán "2 tuần" tính từ đâu.
 *
 *  `do` = nhóm này là một TRẠNG THÁI, không phải một quãng hạn còn lại. "Quá hạn" của Phải thu là
 *  tiền ĐÃ trễ; bốn nhóm kia là tiền chưa đến hạn. Nên nó mang màu cảnh báo, còn bốn nhóm kia mang
 *  một dải xanh nhạt dần theo hạn xa dần. Tô cả năm cùng một dải là để nhóm đã trễ trông như đầu
 *  một hàng đợi bình thường. */
export type NhomHan = { nhan: string; mo_ta: string; so?: number | null; do?: boolean };

/** 07 · Rủi ro trọng yếu. Hai mức: cần quyết định (thuộc thẩm quyền Chủ tịch) và cần theo dõi.
 *  Nghiệp vụ thường ngày KHÔNG lên đây – bản vẽ ghi rõ, và đó cũng là lý do khối này khác khối
 *  "Tồn đọng cần xử lý" ở trên. */
export type RuiRo = {
  noi_dung: string;
  muc?: "quyet_dinh" | "theo_doi";
  muc_anh_huong?: string | null;
  don_vi?: string | null;
  nguoi_xu_ly?: string | null;
  han_khac_phuc?: string | null;
  tien_do?: string | null;
};

/** 08 · Tiến độ báo cáo & kết luận chỉ đạo. Theo dõi hồ sơ chưa chốt và việc làm theo chỉ đạo. */
export type DongTienDo = {
  ho_so: string;
  ma_pham_vi?: string;
  don_vi?: string | null;
  han?: string | null;
  tien_do?: string | null;
  da_nop?: boolean;
  buoc_tiep?: string | null;
  cua?: string | null;              // cửa đi tới, để "bước tiếp theo" bấm được chứ không chỉ để đọc
  so_viec_do?: number | null;       // rỗng = chưa nộp nên chưa đếm được, KHÁC 0 = nộp rồi và sạch
};

/* ────────────────────────── MẢNH DÙNG CHUNG ────────────────────────── */

/** Ô rỗng chuẩn của màn hình này: nói CHƯA CÓ GÌ, AI phải nhập, và ĐI ĐÂU để nhập.
 *  Ba thứ ấy đi liền nhau; thiếu một cái là ô trống trở thành việc không ai nhận. */
function ChuaNoi({ ai, cua, cua_ten }: { ai: string; cua?: string; cua_ten?: string }) {
  return (
    <span className="v14-chua">
      <span className="tag">Chưa kết nối</span>
      <span className="muted"> · {ai} nhập</span>
      {cua && <Link className="the-cua" href={cua}>{cua_ten || "Cửa nhập"} →</Link>}
    </span>
  );
}

function DauKhoi({ ten, phu, id }: { ten: string; phu?: string; id?: string }) {
  return (
    <div className="mh01-dau" id={id}>
      <h2>{ten}</h2>
      {phu && <span className="tag">{phu}</span>}
    </div>
  );
}

/** Bảng chưa có dòng nào: vẫn VẼ ĐỦ ĐẦU CỘT rồi mới nói chưa kết nối.
 *  Vì sao không giấu bảng đi: đầu cột chính là bản mô tả việc còn nợ – nhìn vào là biết máy chủ
 *  phải trả những trường gì. Giấu đi thì đến lúc dựng lại phải đi tìm bản vẽ. */
function BangRong({ cot, ghi_chu, ai, cua, cua_ten }:
  { cot: string[]; ghi_chu: string; ai: string; cua?: string; cua_ten?: string }) {
  return (
    <>
      <div className="wrap">
        <table className="v14-bang">
          <thead><tr>{cot.map((c) => <th key={c}>{c}</th>)}</tr></thead>
          <tbody>
            <tr><td colSpan={cot.length} className="v14-trong">
              <ChuaNoi ai={ai} cua={cua} cua_ten={cua_ten} />
            </td></tr>
          </tbody>
        </table>
      </div>
      <p className="muted v14-ghi">{ghi_chu}</p>
    </>
  );
}

/* ───────────────────────── 04b · HIỆU QUẢ ĐỘI XE ───────────────────────── */

/** TC-40 · BA KỲ XEM: THÁNG · QUÝ · NĂM (anh Tuấn chốt 15/9/2026 — "kết quả đội xe sẽ update
 *  hàng ngày theo tháng, quý, năm").
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  NÚT CÓ, SỐ CHƯA CÓ — VÀ MÀN HÌNH PHẢI NÓI RA ĐIỀU ĐÓ
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Máy chủ hôm nay trả đúng MỘT bộ bốn chỉ số, không phân theo kỳ: `/dashboard` chưa nhận tham số
 *  kỳ cho khối đội xe, và sổ đội xe cũng chưa có (cả bốn ô đang "Chưa kết nối").
 *
 *  Nên nút chọn kỳ ở đây là CẤU TRÚC dựng sẵn, chưa phải một nút chạy được. Và đây là chỗ rất dễ
 *  làm sai: dựng ba nút rồi để cả ba hiện CÙNG một bộ số là nói dối bằng giao diện — người đọc bấm
 *  "Quý" thấy số không đổi sẽ kết luận quý bằng tháng, chứ không kết luận là chưa có số.
 *
 *  Nên: bấm sang kỳ nào chưa có nguồn thì ô số nói thẳng kỳ ấy chưa có, kèm bộ phận và cửa nhập.
 *  Khi máy chủ trả `hieu_qua_xe_theo_ky`, chỗ này chỉ việc đọc đúng khoá kỳ — không phải dựng lại.
 */
const KY_XE: { ma: "thang" | "quy" | "nam"; ten: string }[] = [
  { ma: "thang", ten: "Tháng" }, { ma: "quy", ten: "Quý" }, { ma: "nam", ten: "Năm" },
];

type BoKy = Partial<Record<"thang" | "quy" | "nam", HieuQuaXe>> & {
  mac_dinh?: "thang" | "quy" | "nam";
  ky_co_chuyen?: string[];
  moc?: string;
};

export function KhoiHieuQuaXe({ d, theo_ky }: {
  d?: HieuQuaXe | null;
  /** Khi máy chủ trả số theo từng kỳ thì truyền vào đây: { thang: {...}, quy: {...}, nam: {...} },
   *  kèm `mac_dinh` — kỳ HẸP NHẤT còn có số. */
  theo_ky?: BoKy | null;
}) {
  /* HQ-1c — MỞ SẴN Ở KỲ CÒN CÓ SỐ, không cứng ở "thang".
     Sổ quyết toán xe chỉ chốt sau khi hết tháng, nên tháng đang chạy trống gần như suốt. Đo trên
     hệ thật 13/10/2026: máy chủ có số ở kỳ năm nhưng khối mở ở kỳ tháng và in bốn dấu gạch — Chủ
     tịch kết luận "đội xe chưa lên màn hình". Con số có thật mà vẫn bằng không có.
     Máy chủ chọn kỳ mở sẵn (`mac_dinh`) vì chỉ nó biết kỳ nào còn chuyến; chỗ này chỉ nghe theo,
     và người đọc vẫn bấm sang kỳ khác được bất cứ lúc nào. */
  const [ky, setKy] = useState<"thang" | "quy" | "nam">(theo_ky?.mac_dinh || "thang");

  /* HQ-2 (13/10/2026) — Ô CHỌN KỲ, và vì sao nó KHÔNG phải ô "Thời điểm" của màn hình Điều hành xe.
     Ô bên ấy mở BẢN CHỤP, vì những con số ấy đếm hàng đợi TẠI MỘT THỜI ĐIỂM — qua rồi thì không
     tính lại được. Bốn chỉ số đội xe thì ngược lại: mỗi chuyến thuộc về một kỳ theo NGÀY ĐI của
     nó, nên tháng 9 lúc nào cũng tính lại được từ sổ sách hiện có. Chỗ này TÍNH LẠI, không đọc
     bản chụp — và hệ quả phải nói ra ngay dưới ô chọn, không giấu trong mã.

     Vì sao cần: trước vòng này khối chỉ tính được tháng này / quý này / năm nay theo HÔM NAY. Đo
     13/10/2026: tháng 10 chưa nạp chuyến nào nên kỳ Tháng rỗng, quý 4 chỉ có tháng 10 nên Quý
     cũng rỗng — chín tháng số liệu nằm sẵn mà không có đường nào mở ra. */
  const [moc, setMoc] = useState<string>("");
  const [napLai, setNapLai] = useState<BoKy | null>(null);
  const [dangNap, setDangNap] = useState(false);
  const tai = useCallback(async () => {
    if (!moc) { setNapLai(null); return; }
    setDangNap(true);
    try { setNapLai(await api(`/fleet/hieu-qua-doi-xe?moc=${moc}`)); }
    catch { setNapLai(null); }
    finally { setDangNap(false); }
  }, [moc]);
  useEffect(() => { tai(); }, [tai]);
  const bo: BoKy | null | undefined = napLai || theo_ky;
  /* Ô chọn chỉ liệt kê kỳ THẬT SỰ có chuyến — máy chủ trả danh sách ấy. Liệt kê đủ 12 tháng cho
     đẹp thì người đọc bấm vào một tháng rỗng, thấy bốn dấu gạch, rồi lại kết luận màn hình hỏng. */
  const dsKy = theo_ky?.ky_co_chuyen || napLai?.ky_co_chuyen || [];
  /* Kỳ THÁNG lấy `d` làm lối lui, vì đó là bộ số máy chủ đang trả hôm nay. Quý và năm KHÔNG lấy
     lối lui ấy — lấy là bày số tháng dưới nhãn quý. */
  const o: HieuQuaXe = (bo?.[ky]) || (ky === "thang" && !moc ? (d || {}) : {});
  const coNguonKy = !!bo?.[ky] || (ky === "thang" && !moc && !!d);

  const so = (x: any, duoi = "") =>
    x === null || x === undefined || x === "" ? null : `${x}${duoi}`;
  const tien = (x: any) => (x === null || x === undefined ? null : gonSo(Number(x)));
  const cot: [string, string | null, string][] = [
    ["Ngày xe hoạt động", so(o.ngay_xe_hoat_dong), "ngay_xe_hoat_dong"],
    ["Công suất khai thác", so(o.cong_suat_khai_thac, "%"), "cong_suat_khai_thac"],
    ["Km chạy rỗng", so(o.km_chay_rong), "km_chay_rong"],
    ["Chi phí / km", so(o.chi_phi_moi_km, " đ"), "chi_phi_moi_km"],
    ["Doanh thu", tien(o.doanh_thu), "doanh_thu"],
    ["Lợi nhuận", tien(o.loi_nhuan), "loi_nhuan"],
    ["Tiêu hao", so(o.tieu_hao_l100, " L/100km"), "tieu_hao_l100"],
  ];
  /* Mũi tên so với kỳ trước. CHIỀU TỐT của mỗi chỉ số khác nhau: km chạy rỗng tăng là XẤU, doanh
     thu tăng là TỐT, chi phí mỗi km tăng là XẤU. Tô một màu cho mọi mũi tên tăng là dạy người đọc
     rằng tăng luôn tốt — và họ sẽ đọc "km rỗng tăng 412" thành một tin vui. */
  const TANG_LA_TOT: Record<string, boolean> = {
    ngay_xe_hoat_dong: true, cong_suat_khai_thac: true, km_chay_rong: false,
    chi_phi_moi_km: false, doanh_thu: true, loi_nhuan: true, tieu_hao_l100: false,
  };
  const muiTen = (khoa: string) => {
    const v = o.so_sanh?.lech?.[khoa];
    if (v === null || v === undefined || v === 0) return null;
    const tot = (v > 0) === TANG_LA_TOT[khoa];
    const con = khoa === "doanh_thu" || khoa === "loi_nhuan"
      ? gonSo(Math.abs(v)) : Math.abs(v).toLocaleString("vi-VN");
    // Kiểu đặt thẳng tại chỗ, KHÔNG thêm lớp vào globals.css: tệp ấy bốn làn cùng sửa, và cửa đẩy
    // thay nguyên tệp — thêm một dòng vào đó là đổi lấy nguy cơ xoá mất dòng của làn khác.
    return <span style={{ display: "block", marginTop: 2, fontWeight: 600,
                          fontSize: "calc(11.5/14*1rem)", color: tot ? "var(--teal)" : "var(--red)" }}>
      {v > 0 ? "▲" : "▼"} {con}</span>;
  };
  /* Chỉ thay dấu gạch của ô CÔNG SUẤT, và chỉ khi máy chủ nói được vì sao. Ba ô kia trống vì kỳ
     chưa có chuyến nào — đó là chuyện khác, và câu trả lời của nó nằm ở dòng "Chưa có số cho kỳ…"
     bên dưới. Trộn hai lý do vào một chỗ thì cả hai cùng mất nghĩa. */
  const thieuCS = o.cong_suat_khai_thac == null ? o.cong_suat_thieu : null;
  return (
    <section className="panel" id="hieu-qua-doi-xe">
      <div className="mh01-dau">
        <h2>Hiệu quả đội xe</h2>
        {/* Nút chọn kỳ nằm ngay đầu khối, cạnh tên — không giấu dưới đáy: nó đổi ý nghĩa của MỌI
            con số trong khối, nên người đọc phải thấy mình đang xem kỳ nào trước khi đọc số. */}
        {o.nhan && <span className="muted" style={{ fontSize: ".85em", marginRight: 8 }}>{o.nhan}</span>}
        <div className="v14-ky" role="group" aria-label="Kỳ xem của khối đội xe">
          {KY_XE.map((k) => (
            <button key={k.ma} type="button"
              className={"v14-ky-nut" + (ky === k.ma ? " chon" : "")}
              aria-pressed={ky === k.ma} onClick={() => setKy(k.ma)}>{k.ten}</button>
          ))}
        </div>
        {dsKy.length > 0 && (
          <select aria-label="Thời điểm" value={moc} disabled={dangNap}
            style={{ width: "auto", marginLeft: 8, maxWidth: 230 }}
            onChange={(e) => setMoc(e.target.value)}>
            <option value="">Kỳ gần nhất còn có số</option>
            {dsKy.map((k) => {
              const [y, m] = k.split("-");
              return <option key={k} value={`${k}-01`}>Tính đến tháng {m}/{y}</option>;
            })}
          </select>
        )}
      </div>
      <div className="v14-o-ds">
        {cot.map(([nhan, gt, khoa]) => (
          <div key={nhan} className={"v14-o" + (gt === null ? " rong" : "")}>
            <div className="v14-o-nhan">{nhan}</div>
            {gt === null && nhan === "Công suất khai thác" && thieuCS ? (
              <Link className="v14-o-so v14-o-chu" href={thieuCS.cua_nhap}
                title={thieuCS.thieu.slice(0, 8).map((x) => `${x.xe}: thiếu ${x.thieu}`).join("\n")}>
                chờ {thieuCS.bo_phan}
                <span className="muted"> · {thieuCS.thieu.length} xe chưa khai ngày vào đội</span>
              </Link>
            ) : (
              <>
                <div className="v14-o-so">{gt ?? "—"}</div>
                {gt !== null && muiTen(khoa)}
              </>
            )}
          </div>
        ))}
        {/* Ô này là TRẠNG THÁI, không phải con số – nên không dùng phông chữ số. Phông số sinh ra
            để cột số dóng thẳng hàng; đặt một chữ tiếng Việt vào đó thì chữ giãn ra trông như lỗi. */}
        <div className="v14-o rong">
          <div className="v14-o-nhan">Kết quả đã chốt</div>
          <div className="v14-o-so v14-o-chu">{o.da_chot ? "Đã chốt" : "Chưa chốt"}</div>
        </div>
      </div>
      {!coNguonKy && (
        <p className="v14-ghi">
          <span className="tag">Chưa có số cho kỳ {KY_XE.find((k) => k.ma === ky)!.ten.toLowerCase()}</span>{" "}
          <span className="muted">· Đội xe nhập</span>
          <Link className="the-cua" href="/doi-xe">Cửa nhập đội xe →</Link>
        </p>
      )}
      {/* Kỳ trống thì nói VÌ SAO trống và chỉ sang kỳ còn số — "Chưa có số" một mình đọc ra như
          màn hình hỏng. Nút nhảy đưa thẳng sang kỳ máy chủ bảo là còn số. */}
      {coNguonKy && o.trong_vi_sao && (
        <p className="v14-ghi">
          <span className="tag">{o.trong_vi_sao}</span>
          {theo_ky?.mac_dinh && theo_ky.mac_dinh !== ky && (
            <button type="button" className="v14-ky-nut" style={{ marginLeft: 8 }}
              onClick={() => setKy(theo_ky.mac_dinh!)}>
              Xem {KY_XE.find((k) => k.ma === theo_ky.mac_dinh)!.ten.toLowerCase()} →
            </button>
          )}
        </p>
      )}
      {/* Hai câu phải nằm TRÊN màn hình, không nằm trong mã: người đọc so con số này với màn hình
          Điều hành xe và cần biết hai ô «thời điểm» ấy làm hai việc khác nhau. */}
      {moc && <p className="v14-ghi muted">
        Số của kỳ đã chọn được <b>tính lại</b> từ sổ sách hiện có, không phải bản chụp. Đội xe nạp
        bù chuyến của kỳ ấy thì con số ở đây <b>sẽ đổi</b> — đó là đúng.
      </p>}
      {o.so_sanh && <p className="v14-ghi muted">Mũi tên {o.so_sanh.nhan}.</p>}
      {coNguonKy && !o.so_sanh && o.chua_so_sanh_vi && !o.trong_vi_sao &&
        <p className="v14-ghi"><span className="tag">{o.chua_so_sanh_vi}</span></p>}
      {/* Tiêu hao: con số LUÔN in ra, ngưỡng thì chờ người khai. Giấu con số đi vì chưa có ngưỡng
          là lặp lại đúng lỗi vòng HQ-1 đã sửa — tính sẵn một câu trả lời rồi không in nó ra. */}
      {o.tieu_hao_l100 != null && o.tieu_hao_nguong_thieu && (
        <p className="v14-ghi">
          <span className="tag warn">chưa có định mức dầu</span>{" "}
          <span className="muted">Chưa biết {o.tieu_hao_l100} L/100km là cao hay thấp ·{" "}
          {o.tieu_hao_nguong_thieu.bo_phan} khai theo số chỗ</span>{" "}
          <Link className="the-cua" href={o.tieu_hao_nguong_thieu.cua_nhap}>Cửa nhập định mức →</Link>
        </p>
      )}
      {o.tieu_hao_vuot && o.tieu_hao_vuot.length > 0 && (
        <p className="v14-ghi">
          <span className="tag red">{o.tieu_hao_vuot.length} xe vượt định mức dầu</span>{" "}
          <span className="muted">{o.tieu_hao_vuot.slice(0, 4).map(
            (x) => `${x.xe} ${x.tieu_hao}/${x.nguong}`).join(" · ")}</span>
        </p>
      )}
      {coNguonKy && !o.trong_vi_sao && cot.every(([, g]) => g === null) &&
        <p className="v14-ghi"><ChuaNoi ai="Đội xe" cua="/doi-xe" cua_ten="Cửa nhập đội xe" /></p>}
      {/* Hai câu cảnh báo nghiệp vụ của bản vẽ. Giữ nguyên vì cả hai đều là chỗ dễ đọc sai con số. */}
      <p className="muted v14-ghi">
        Cập nhật hằng ngày. Xe không có lệnh <b>chưa chắc</b> sẵn sàng; công suất tính trên thời
        gian xe <b>có thể</b> khai thác, không phải trên số ngày trong kỳ. Hướng dẫn viên vẫn được
        quản lý riêng.
      </p>
    </section>
  );
}

/* ───────────────────────── 04c · TỒN ĐỌNG THEO BỘ PHẬN ───────────────────────── */

export function KhoiTonDongBoPhan({ ds, chua_ro, da_loai, vi_sao }: {
  ds?: DongTonDong[] | null;
  chua_ro?: ChuaRoBoPhan | null;
  da_loai?: LoaiDaLoai[] | null;
  vi_sao?: string | null;
}) {
  const co = ds || [];
  const loai = da_loai || [];
  const cot = ["Bộ phận", "Hồ sơ quá hạn", "Hồ sơ lâu nhất", "Người chịu trách nhiệm", "Hạn khắc phục"];
  const ghi = "Mỗi hồ sơ chỉ tính MỘT lần: một hồ sơ phát ba cảnh báo vẫn là một hồ sơ. Việc chống cộng trùng làm ở máy chủ, không làm ở màn hình.";
  /* Tổng bảng gồm CẢ dòng chưa rõ bộ phận. Ghi tổng mà bỏ dòng ấy ra là ghi một con số nhỏ hơn
     sự thật – đúng kiểu sai mà không ai kiểm được, vì con số vẫn cộng khớp với các dòng hiện ra.

     RỖNG KHÁC KHÔNG, và luật ấy áp cả cho DÒNG TỔNG. Một dòng chưa có số thì tổng KHÔNG BIẾT
     ĐƯỢC – coi nó là 0 rồi cộng tiếp ra một con số nhỏ hơn sự thật mà vẫn khớp với các dòng hiện
     ra, nên không ai kiểm được. Thiếu một dòng thì không ghi tổng, chứ không ghi tổng thiếu. */
  const thieu_so = co.some((r) => typeof r.ho_so_qua_han !== "number");
  const tong = thieu_so
    ? null
    : co.reduce((s, r) => s + (r.ho_so_qua_han as number), 0) + (chua_ro ? chua_ro.so : 0);
  return (
    <section className="panel" id="ton-dong-bo-phan">
      <DauKhoi ten="Tồn đọng theo bộ phận" phu={typeof tong === "number" && tong > 0 ? `${tong} hồ sơ` : "Mỗi hồ sơ chỉ tính một lần"} />
      {co.length === 0 && !chua_ro
        ? (vi_sao
            /* Sổ có thật mà rỗng KHÁC sổ chưa nối. Cái đầu là tin tốt và phải nói rõ là tin tốt;
               cái sau là việc còn nợ. Dùng chung một ô "Chưa kết nối" thì trộn mất hai thứ. */
            ? <>
                <div className="wrap">
                  <table className="v14-bang">
                    <thead><tr>{cot.map((c) => <th key={c}>{c}</th>)}</tr></thead>
                    <tbody><tr><td colSpan={cot.length} className="v14-trong">
                      <Tag>Không có hồ sơ quá hạn</Tag> <span className="muted">{vi_sao}</span>
                    </td></tr></tbody>
                  </table>
                </div>
                <p className="muted v14-ghi">{ghi}</p>
              </>
            : <BangRong cot={cot} ghi_chu={ghi} ai="Công nghệ thông tin" cua="/alerts" cua_ten="Trang cảnh báo" />)
        : <>
            {/* TC-38 · Thanh ngang đã chuyển sang khu Biểu đồ 3, cùng lý do với thanh cơ cấu ở
                khối 05: một trang không vẽ cùng một biểu đồ hai lần. */}
            <p className="muted v14-ghi">
              <a className="the-cua" href="#khu-bieu-do">Xem biểu đồ theo bộ phận →</a>
            </p>
            <div className="wrap">
              <table className="v14-bang">
                <thead><tr>{cot.map((c) => <th key={c}>{c}</th>)}</tr></thead>
                <tbody>
                  {co.map((r) => (
                    <tr key={r.ma_bo_phan || r.bo_phan}>
                      <td><b>{r.bo_phan}</b></td>
                      <td className="num">{r.ho_so_qua_han ?? "—"}</td>
                      <td>{r.ho_so_lau_nhat || <span className="muted">—</span>}</td>
                      <td>{r.nguoi_chiu_trach_nhiem || <span className="muted">chưa gán</span>}</td>
                      <td>{r.han_khac_phuc || <span className="muted">chưa đặt</span>}</td>
                    </tr>
                  ))}
                  {chua_ro && (
                    <tr className="v14-chua-ro">
                      <td><b>Chưa rõ bộ phận</b></td>
                      <td className="num">{chua_ro.so}</td>
                      <td colSpan={3}><span className="muted">{chua_ro.vi_sao}</span></td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <p className="muted v14-ghi">{ghi}</p>
          </>}
      {loai.length > 0 && (
        <p className="muted v14-ghi">
          {"Không tính vào bảng này: "}
          {loai.map((l, i) => (
            <span key={l.loai}>
              {i > 0 && " · "}<b>{l.so_ho_so}</b>{" hồ sơ loại "}<code>{l.loai}</code>{" — "}{l.ly_do}
            </span>
          ))}
        </p>
      )}
    </section>
  );
}

/* ───────────────────────── 05 · PHẢI THU & PHẢI TRẢ THEO HẠN ───────────────────────── */

/** BẢY NHÓM KHÔNG TRÙNG NHAU, và đó là điểm khác hẳn bảng dòng tiền bốn mốc LŨY KẾ ở khối 06.
 *  Ở đây một đợt thanh toán rơi vào ĐÚNG MỘT nhóm, nên cộng bảy nhóm lại ra tổng công nợ; ở bảng
 *  dòng tiền thì cột 14 ngày đã chứa trọn cột 7 ngày, cộng vào là sai.
 *
 *  ═════════════════════════════════════════════════════════════════════════════════════════════
 *  TC-45 · MỘT BỘ MỐC CHO CẢ HAI PHÍA — anh Tuấn chốt 16/9/2026
 *  ═════════════════════════════════════════════════════════════════════════════════════════════
 *  Bản cũ để Phải thu và Phải trả dùng hai bộ mốc khác nhau (thu: quá hạn·2 tuần·4 tuần·2 tháng·
 *  dài hạn — trả: 1 tuần·2 tuần·4 tuần·3 tháng·dài hạn, quá hạn theo dõi riêng). Hai khối ấy nằm
 *  cạnh nhau, nên mắt dóng "4 tuần" bên này với "4 tuần" bên kia — mà mép sau của chúng khác nhau,
 *  và nhóm cuối bên này là 2 tháng còn bên kia là 3 tháng. Không con số nào sai; cái sai là phép
 *  so mà người đọc tự làm.
 *
 *  Nay MỘT khung bảy nhóm, khai ở `MOC` (backend/app/services/han_cong_no.py) và chép đúng chữ ở
 *  đây. Quá hạn nằm TRONG bảy nhóm ở cả hai phía — trước đây phía chi để riêng, nghĩa là tổng phải
 *  trả trên màn hình không gồm khoản đã trễ.
 *
 *  Hai tháng và ba tháng tính theo THÁNG LỊCH từ ngày báo cáo, không mặc định 60/90 ngày (bản vẽ
 *  ghi rõ). Hạn rơi ĐÚNG ngày báo cáo thuộc nhóm sắp đến hạn đầu tiên, không thuộc nhóm quá hạn. */
const BAY_NHOM: NhomHan[] = [
  { nhan: "Quá hạn", mo_ta: "Hạn thanh toán trước ngày báo cáo", do: true },
  { nhan: "1 tuần", mo_ta: "Từ ngày báo cáo đến hết ngày +7" },
  { nhan: "2 tuần", mo_ta: "Sau 1 tuần đến hết ngày +14" },
  { nhan: "4 tuần", mo_ta: "Sau 2 tuần đến hết ngày +28" },
  { nhan: "2 tháng", mo_ta: "Sau 4 tuần đến hết mốc +2 tháng lịch" },
  { nhan: "3 tháng", mo_ta: "Sau mốc 2 tháng đến hết mốc +3 tháng lịch" },
  { nhan: "Dài hạn", mo_ta: "Sau mốc 3 tháng" },
];

/* ═══════════════════════════════════════════════════════════════════════════════════════════════
   BẢY Ô SỐ VUÔNG VÀ THANH CƠ CẤU MỘT VẠCH ĐỀU ĐÃ ĐI — THAY BẰNG BẢY THANH NGANG
   ═══════════════════════════════════════════════════════════════════════════════════════════════
   Bản cũ bày CẢ HAI: năm ô số vuông, rồi một thanh chia khúc ngay dưới. Hai bức tranh của cùng một
   hàng số, cách nhau bốn chục pixel — đúng thứ luật "MỘT CON SỐ · MỘT CHỖ · MỘT HÌNH" (TC-40) sinh
   ra để chặn, và với bảy nhóm thì bảy ô vuông còn chiếm gần trọn chiều cao khối.

   Bảy thanh ngang (dựng ở `bieuDoCua`, components/BaKhuBieuDo.tsx) trả lời cả hai câu trong một
   hình: con số nằm cuối mỗi thanh, bề dài so với nhau cho ngay tỉ lệ. Hàm `coCau` đi cùng bảy ô
   vuông — điều kiện vẽ nay hỏi qua `duVeThanh` của bộ biểu đồ dùng chung, không viết lại tại chỗ.

   MỐC TÍNH TỪ ĐÂU thì không mất: `BAY_NHOM` vẫn giữ `mo_ta` của từng nhóm, và chúng in thành MỘT
   dòng ở chân khối. Bỏ hẳn mấy câu ấy là để người mới đọc tự đoán "4 tuần" đếm từ ngày nào.
   ═══════════════════════════════════════════════════════════════════════════════════════════════ */

/* 29/9/2026 · anh Tuấn: "trong phần phải thu phải trả em xoá hết ghi chú cho anh, chỉ để lại biểu
   đồ và con số, link vào xem chi tiết". Khối chỉ còn: tên · bảy thanh ngang có số · khoản chưa có
   hạn (nếu có) · một lối "Xem chi tiết →". Mọi lời giải thích (mốc tính, nguồn số, cửa nhập) bỏ khỏi
   màn hình; luật chia nhóm vẫn nằm ở backend/app/services/han_cong_no.py. */
function KhoiHan({ ten, id, chua_co_han, bieu_do, chi_tiet }: {
  ten: string; khung?: NhomHan[]; ds?: Record<string, number | null> | null;
  id: string; chua_co_han?: number | null; vi_sao?: string | null; bieu_do?: React.ReactNode;
  chi_tiet: string;
}) {
  return (
    <section className="panel" id={id}>
      <DauKhoi ten={ten} />
      {bieu_do}
      {chua_co_han !== null && chua_co_han !== undefined && chua_co_han > 0 && (
        <div className="v14-quahan">
          <b>Chưa có hạn:</b>{" "}
          <span className="the-so v14-qh-so">{gonSo(chua_co_han, "tien")}</span>
        </div>)}
      <p className="v14-ghi"><Link className="the-cua" href={chi_tiet}>Xem chi tiết →</Link></p>
    </section>
  );
}

export function KhoiPhaiThu({ ds, chua_co_han, vi_sao, bieu_do }: {
  ds?: Record<string, number | null> | null; chua_co_han?: number | null; vi_sao?: string | null;
  bieu_do?: React.ReactNode;
}) {
  return <KhoiHan id="phai-thu" ten="Phải thu theo hạn thanh toán" khung={BAY_NHOM} ds={ds}
    chua_co_han={chua_co_han} vi_sao={vi_sao} bieu_do={bieu_do} chi_tiet="/cong-no" />;
}

export function KhoiPhaiTra({ ds, chua_co_han, vi_sao, bieu_do }: {
  ds?: Record<string, number | null> | null;
  chua_co_han?: number | null; vi_sao?: string | null; bieu_do?: React.ReactNode;
}) {
  return <KhoiHan id="phai-tra" ten="Phải trả theo hạn thanh toán" khung={BAY_NHOM} ds={ds}
    chua_co_han={chua_co_han} vi_sao={vi_sao} bieu_do={bieu_do} chi_tiet="/cong-no?tab=tra" />;
}

/* ───────────────────────── 07 · RỦI RO TRỌNG YẾU ───────────────────────── */

export function KhoiRuiRo({ ds }: { ds?: RuiRo[] | null }) {
  const co = ds || [];
  const cot = ["Nội dung", "Mức ảnh hưởng", "Đơn vị", "Người xử lý", "Hạn khắc phục", "Tiến độ"];
  const ghi = "Chỉ trình việc cần quyết định hoặc cần theo dõi ở cấp lãnh đạo; cảnh báo thường ngày nằm lại ở phòng ban. Lỗi gom theo VẤN ĐỀ và ĐƠN VỊ, không trình hàng trăm dòng cùng loại.";
  return (
    <section className="panel" id="rui-ro">
      <DauKhoi ten="Rủi ro trọng yếu" phu="Đã gom nhóm" />
      <div className="v14-muc-ds">
        <span className="tag red">Cần quyết định</span>
        <span className="muted">hồ sơ thuộc thẩm quyền Chủ tịch</span>
        <span className="tag warn">Cần theo dõi</span>
        <span className="muted">rủi ro lớn, đã có người xử lý và hạn</span>
      </div>
      {co.length === 0
        ? <BangRong cot={cot} ghi_chu={ghi} ai="Các phòng ban" cua="/ngoai-le" cua_ten="Cửa nhập ngoại lệ" />
        : <>
            <div className="wrap">
              <table className="v14-bang">
                <thead><tr>{cot.map((c) => <th key={c}>{c}</th>)}</tr></thead>
                <tbody>
                  {co.map((r, i) => (
                    <tr key={i}>
                      <td>
                        <b>{r.noi_dung}</b>{" "}
                        {r.muc === "quyet_dinh"
                          ? <Tag cls="red">Cần quyết định</Tag>
                          : <Tag cls="warn">Cần theo dõi</Tag>}
                      </td>
                      <td>{r.muc_anh_huong || <span className="muted">—</span>}</td>
                      <td>{r.don_vi || <span className="muted">—</span>}</td>
                      <td>{r.nguoi_xu_ly || <span className="muted">chưa gán</span>}</td>
                      <td>{r.han_khac_phuc || <span className="muted">chưa đặt</span>}</td>
                      <td>{r.tien_do || <span className="muted">—</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="muted v14-ghi">{ghi}</p>
          </>}
    </section>
  );
}

/* ───────────────────────── 08 · TIẾN ĐỘ BÁO CÁO & KẾT LUẬN CHỈ ĐẠO ───────────────────────── */

/** TC-33 · Bản vẽ đặt MỘT khối nhưng hỏi HAI câu khác hẳn nhau, nên màn hình dựng thành hai phần:
 *
 *    (A) TIẾN ĐỘ BÁO CÁO   – phòng nào đã nộp bản của kỳ vừa đóng. Trả lời được ngay hôm nay.
 *    (B) KẾT LUẬN CHỈ ĐẠO  – chưa có bảng nào giữ. Nằm im ở "chưa kết nối", và NÓI RA là chưa có.
 *
 *  Gộp hai phần vào một bảng thì khối trông như đã xong trong khi một nửa còn chưa bắt đầu. */
export function KhoiTienDoBaoCao({ ds, ten_ky, so_da_nop, so_thieu, vi_sao, chi_dao_vi_sao }: {
  ds?: DongTienDo[] | null;
  ten_ky?: string | null;
  so_da_nop?: number | null;
  so_thieu?: number | null;
  vi_sao?: string | null;
  chi_dao_vi_sao?: string | null;
}) {
  const co = ds || [];
  const cot = ["Hồ sơ / kết luận", "Đơn vị phụ trách", "Hạn", "Tiến độ", "Bước tiếp theo"];
  const ghi = "Theo dõi hồ sơ chưa chốt và công việc thực hiện theo chỉ đạo. Một dòng ở đây là một việc có người chịu và có hạn — không phải một ghi chú.";
  /* Nhãn đầu khối nói KỲ NÀO đang được đo. Một bảng tiến độ không nói nó đo kỳ nào là một bảng
     không kiểm được: người đọc không biết "chưa nộp" nghĩa là chưa nộp của tháng nào. */
  const phu = ten_ky
    ? (typeof so_thieu === "number" ? `${ten_ky} · còn thiếu ${so_thieu}/${co.length}` : ten_ky)
    : "Theo trách nhiệm";
  return (
    <section className="panel" id="tien-do-bao-cao">
      <DauKhoi ten="Tiến độ báo cáo &amp; kết luận chỉ đạo" phu={phu} />
      {co.length === 0
        ? (vi_sao
            ? <div className="wrap">
                <table className="v14-bang">
                  <thead><tr>{cot.map((c) => <th key={c}>{c}</th>)}</tr></thead>
                  <tbody><tr><td colSpan={cot.length} className="v14-trong">
                    <span className="muted">{vi_sao}</span>
                  </td></tr></tbody>
                </table>
              </div>
            : <BangRong cot={cot} ghi_chu={ghi} ai="Văn phòng Hội đồng quản trị" cua="/reports" cua_ten="Trang báo cáo" />)
        : <>
            <div className="wrap">
              <table className="v14-bang">
                <thead><tr>{cot.map((c) => <th key={c}>{c}</th>)}</tr></thead>
                <tbody>
                  {co.map((r, i) => (
                    <tr key={i}>
                      <td><b>{r.ho_so}</b></td>
                      <td>{r.don_vi || <span className="muted">—</span>}</td>
                      <td>{r.han || <span className="muted">chưa đặt</span>}</td>
                      {/* "Chưa nộp" là việc còn nợ, nên nó phải đọc ra được là việc còn nợ — không
                          nằm chung một màu với dòng đã xong. */}
                      <td>{r.tien_do
                        ? (r.da_nop ? r.tien_do : <Tag>{r.tien_do}</Tag>)
                        : <span className="muted">—</span>}</td>
                      <td>{r.cua
                        ? <Link className="the-cua" href={r.cua}>{r.buoc_tiep} →</Link>
                        : (r.buoc_tiep || <span className="muted">—</span>)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="muted v14-ghi">{ghi}</p>
          </>}
      {/* (B) — phần CHƯA BẮT ĐẦU, tách hẳn khỏi bảng trên. Không mượn số của phần (A) lấp vào. */}
      {chi_dao_vi_sao && (
        <div className="v14-chi-dao">
          <span className="tag">Kết luận chỉ đạo · chưa kết nối</span>
          <span className="muted"> {chi_dao_vi_sao}</span>
        </div>
      )}
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════════════════
 * KHỐI 06 – DÒNG TIỀN: KHÔNG DỰNG Ở ĐÂY, CÓ LÝ DO
 *
 * VTOS đã có components/KhoiDongTien.tsx, lấy số từ làn Dòng tiền. Bản vẽ V1.4 muốn một hình khác:
 * bốn mốc 7/14/30/60 KHÔNG lũy kế, bảng chi tiết chuyển sang trang riêng, và thay cột "Cửa nhập –
 * bộ phận" bằng ba trạng thái Đầy đủ / Còn thiếu / Chưa đối soát.
 *
 * Anh Tuấn đã chốt phương án dung hoà cho khối ấy ngày 13/9. Nhưng nó đụng SỐ của làn khác, không
 * phải việc của lớp giao diện — dựng một khối thứ hai ở đây là có hai chỗ cùng nói về dòng tiền mà
 * không chỗ nào là chỗ thật. Để nguyên khối cũ, và đổi nó trong một vòng riêng cùng làn Dòng tiền.
 * ═══════════════════════════════════════════════════════════════════════════════════════════ */
