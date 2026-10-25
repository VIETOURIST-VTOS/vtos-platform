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
import { gonSo, BieuDoDuong, type Duong } from "@/components/BieuDo";
import { api } from "@/lib/api";

/* ─────────────────────────────── HỢP ĐỒNG DỮ LIỆU ─────────────────────────────── */

/** 04b · Hiệu quả đội xe trong kỳ. Bốn chỉ số + một trạng thái chốt sổ.
 *  CẢNH BÁO NGHIỆP VỤ ghi trong bản vẽ, giữ nguyên: xe không có lệnh CHƯA CHẮC sẵn sàng, và công
 *  suất tính trên thời gian xe CÓ THỂ khai thác chứ không phải trên số ngày trong kỳ. */
export type HieuQuaXe = {
  ngay_xe_hoat_dong?: number | null;
  /** XS-3 — số cho dòng phụ dưới mỗi ô (máy chủ tính, màn hình chỉ ghép chữ). */
  so_xe_chay?: number | null; so_chuyen?: number | null; so_lit?: number | null;
  km_chuyen?: number | null; ngay_xe_mau?: number | null;
  cong_suat_khai_thac?: number | null;   // phần trăm, 0–100
  /** Mục 3 (21/10/2026) — ngày cuối mà MẪU SỐ của công suất đếm tới, dạng YYYY-MM-DD.
   *
   *  Máy chủ chỉ đặt trường này khi kỳ ĐANG CHẠY DỞ: mẫu dừng ở hôm nay chứ không chia cho những
   *  ngày chưa tới. Kỳ đã trọn thì rỗng, và màn hình không in gì thêm.
   *
   *  Vì sao phải in ra: «52,3%» của tháng 10 đọc giữa tháng trông y hệt một con số cả tháng, và
   *  người đọc mang nó đi so với tháng 9 đã trọn. Hai con số ấy không cùng một phép đo. */
  cong_suat_den_ngay?: string | null;
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

/** HQ-3 · một cột của hình diễn biến. `null` = kỳ ấy chưa nạp chuyến nào — KHÁC 0. */
type DiemChuoi = {
  ky: string; nhan: string;
  doanh_thu?: number | null; loi_nhuan?: number | null; cong_suat_khai_thac?: number | null;
};

type BoKy = Partial<Record<"thang" | "quy" | "nam", HieuQuaXe>> & {
  mac_dinh?: "thang" | "quy" | "nam";
  ky_co_chuyen?: string[];
  moc?: string;
  /** 12 kỳ gần nhất tính đến `moc`, cũ → mới. Máy chủ chưa trả thì hình tự hiện khối rỗng. */
  chuoi?: DiemChuoi[] | null;
};

/** TC-72 · «Xe đang đi» chuyển từ hàng tám thẻ xuống khối này (anh Tuấn chốt 20/10/2026).
 *  `co_nguon` phân biệt "hôm nay không điều xe nào" (số THẬT, bằng 0) với "chưa ai nhập bảng xe". */
type XeHomNay = {
  dang_chay?: number | null; o_bai?: number | null; dieu_duoc?: number | null;
  bat_thuong?: number | null; lech?: number | null; co_nguon?: boolean | null;
  /** HQ-5 — bảng LỆNH ĐIỀU XE đã có lấy một dòng chưa. Khác `co_nguon`, vốn soi bảng XE.
   *  Xem `services/xe_hom_nay._co_lenh_bao_gio` để biết vì sao cần hai cờ, không phải một. */
  co_lenh?: boolean | null;
};

/** XS-1 (Chủ tịch duyệt bản xem thử 25/10/2026) — `sections.xe_theo_sheet`: xe đang đi đọc từ sheet
 *  quyết toán của Đội xe. Máy chủ CHỈ gửi khi chưa có lệnh điều xe nào (lệnh VTOS thay sheet), và
 *  `null` khi chưa nối link. Xem `services/xe_theo_sheet.tom_tat`. */
type XeTheoSheet = {
  loi?: string | null; doc_luc?: string | null; ban_cu?: boolean; dieu_duoc?: number;
  dang_di?: number; o_bai?: number; khong_khop?: number; so_can_sua?: number;
};

export function KhoiHieuQuaXe({ d, theo_ky, xe, sheet }: {
  d?: HieuQuaXe | null;
  /** `sections.xe_hom_nay` — xem `XeHomNay`. */
  xe?: XeHomNay | null;
  /** `sections.xe_theo_sheet` — xem `XeTheoSheet`. */
  sheet?: XeTheoSheet | null;
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

  /* QT-3 24/10/2026 — ĐI QUA `toLocaleString("vi-VN")`, ĐỪNG NỐI THẬNG SỐ VÀO CHUỖI.
     Bản cũ viết `${x}${duoi}` nên JS in theo chuẩn Mỹ: màn Chủ tịch hiện `37.3%`, `43.6%`,
     `27.1 L/100km`, `10799 đ` — trong khi 19 chỗ khác của cùng màn dùng chuẩn Việt (`176,3 tỷ`,
     `8.030.563.416`). Hai cách viết số trên một màn tiền là người đọc phải tự đoán dấu nào là gì.
     `10799 đ` là chỗ nặng nhất: thiếu dấu phân nhóm thì đọc lướt dễ thành 107,99.
     `maximumFractionDigits: 1` để phần trăm và tiêu hao giữ đúng một số lẻ như cũ. */
  const so = (x: any, duoi = "") =>
    x === null || x === undefined || x === "" ? null
      : `${typeof x === "number"
            ? x.toLocaleString("vi-VN", { maximumFractionDigits: 1 })
            : x}${duoi}`;
  const tien = (x: any) => (x === null || x === undefined ? null : gonSo(Number(x)));
  /* «2026-10-20» → «20/10». Cắt bằng chuỗi chứ không qua `new Date`: chuỗi ngày trần được trình
     duyệt đọc là UTC rồi in lại theo múi giờ máy, nên ở múi âm nó lùi một ngày — và một con số
     ngày lùi một ngày trên màn hình Chủ tịch là một con số sai, dù chỉ sai một chữ. */
  const ngayNgan = (iso: string) => {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
    return m ? `${m[3]}/${m[2]}` : iso;
  };
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
    ty_le_loi_nhuan: true,
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

  /* ─────────────────────── TC-71 · BẢN VẼ 20/10/2026 (anh Tuấn gửi) ───────────────────────
     Bản vẽ xếp lại khối này thành ba tầng thay vì một dãy bảy ô ngang hàng: TẦNG CHỦ (ba con số
     Chủ tịch đọc trước), TẦNG VẬN HÀNH (bốn chỉ số nghề), rồi CÔNG SUẤT đứng riêng vì nó là ô
     duy nhất còn đang chờ người khai.

     Vì sao xếp lại: bảy ô cùng cỡ chữ, cùng màu, cùng hàng thì không ô nào nổi lên. Chủ tịch mở
     màn hình này để biết "đội xe lãi bao nhiêu", mà con số ấy nằm lẫn giữa "Km chạy rỗng" và
     "Tiêu hao" — hai chỉ số của người điều hành, không phải của người quyết.

     THÊM MỘT Ô, KHÔNG THÊM MỘT SỐ: `ty_le_loi_nhuan` đã nằm trong hợp đồng dữ liệu từ đầu và máy
     chủ đã trả nó (0.3729 ở tháng 10/2026), nhưng khối chưa bao giờ in ra. Biên lợi nhuận là con
     số trả lời "lãi ấy có mỏng hay dày", và nó đọc được mà không cần nhớ doanh thu kỳ trước.

     BA KHỐI CỦA BẢN VẼ KHÔNG DỰNG Ở ĐÂY, và phải nói rõ vì sao:
       · "Diễn biến 30 ngày" — máy chủ chỉ trả MỘT kỳ mỗi lần, chưa có chuỗi theo ngày. Dựng bằng
         `BieuDoDuong` với chuỗi rỗng: nó tự rơi về `BieuDoRong` kèm bộ phận và cửa nhập, đúng
         luật của tệp này. Khi máy chủ trả chuỗi thì chỉ việc đổ số vào `dienBien`.
       · "Doanh thu & lợi nhuận từng xe" — ĐÃ CÓ RỒI, là trang riêng `/lai-lo-doi-xe` dựng trên
         `fleet_lai_lo`. Dựng lại ở đây là hai màn hình cùng một con số, rồi lệch nhau. Nên chỉ
         mở một cửa sang đó.
       · "Xe đang đi hôm nay" — nằm ở `app/page.tsx` (`sec.xe_hom_nay`), không thuộc tệp này. Bản
         vẽ ghép hai khối cạnh nhau là việc xếp TRANG, không phải việc của khối này; gộp vào đây
         là bê một khối của trang khác vào, rồi trang kia in lần nữa.

     Số minh họa trong bản vẽ (sáu "Xe A–F", đường 30 ngày của tháng 9) KHÔNG lấy một con nào —
     xem RANH GIỚI 09/9 ở đầu tệp. */
  const pt = (x: any) =>
    x === null || x === undefined ? null : `${(Number(x) * 100).toFixed(1)}%`;
  /* Ô to: kiểu đặt thẳng tại chỗ, không thêm lớp vào globals.css — bốn làn cùng sửa tệp ấy và cửa
     đẩy thay nguyên tệp, thêm một dòng vào đó là đổi lấy nguy cơ xoá mất dòng của làn khác. */
  const O_CHU: React.CSSProperties = {
    border: "1px solid var(--vien)", borderRadius: 10, padding: "12px 14px",
    background: "var(--nen-2, transparent)",
  };
  const chu: [string, string | null, string][] = [
    ["Doanh thu", tien(o.doanh_thu), "doanh_thu"],
    ["Lợi nhuận", tien(o.loi_nhuan), "loi_nhuan"],
    ["Biên lợi nhuận", pt(o.ty_le_loi_nhuan), "ty_le_loi_nhuan"],
  ];
  /* HQ-4 (23/10/2026) — «Chi phí / km» GỠ KHỎI MÀN HÌNH CHỦ TỊCH, anh Tuấn chốt.
     Lý do xếp chỗ: tầng vận hành đang có SÁU ô (bốn ô của `vanHanh` + Công suất + Xe đang đi) trong một
     lưới `auto-fit minmax(150px)` — trên màn của anh lưới ấy xếp năm ô một hàng, nên ô thứ sáu
     «Xe đang đi» rơi xuống hàng riêng và đứng một mình dưới một hàng trống. Bỏ một ô là cả tầng
     về đúng MỘT hàng năm ô, không cần đụng tới lưới chung.

     Vì sao ô bị bỏ là «Chi phí / km» chứ không phải ô khác: trong sáu ô thì năm ô kia trả lời
     một câu Chủ tịch hỏi hằng ngày (đội xe chạy bao nhiêu ngày · ăn bao nhiêu dầu · chạy rỗng
     bao nhiêu · dùng hết bao nhiêu phần công suất · hôm nay mấy xe đang trên đường), còn
     «chi phí mỗi km» là chỉ số để Đội xe so giữa các xe với nhau — nó chỉ có nghĩa khi đặt cạnh
     chi phí/km của TỪNG xe, và chỗ ấy là trang `/lai-lo-doi-xe`.

     CON SỐ KHÔNG BỊ XOÁ, NÓ CHỈ KHÔNG LÊN MÀN NÀY: `chi_phi_moi_km` giữ nguyên trong hợp đồng dữ
     liệu ở đầu tệp, máy chủ vẫn trả, và nó vẫn nằm trong `cot` bên dưới — mảng ấy là phép đo
     "kỳ này có số hay không", không phải danh sách ô để vẽ. Xoá nó khỏi `cot` là làm khối tưởng
     mình rỗng trong khi máy chủ có số. */
  const vanHanh: [string, string | null, string][] = [
    ["Ngày xe hoạt động", so(o.ngay_xe_hoat_dong), "ngay_xe_hoat_dong"],
    ["Tiêu hao", so(o.tieu_hao_l100, " L/100km"), "tieu_hao_l100"],
    ["Km chạy rỗng", so(o.km_chay_rong), "km_chay_rong"],
  ];
  /* HQ-3 (20/10/2026) — HÌNH DIỄN BIẾN ĐỌC CHUỖI THẬT CỦA MÁY CHỦ.
     Trước vòng này chỗ đây dựng chuỗi RỖNG, nên hình luôn rơi về khối "chờ Đội xe nạp số" — đọc ra
     như Đội xe còn thiếu số, trong khi số của từng tháng vẫn nằm sẵn trong máy và lấy được. Thiếu
     là MỘT ĐOẠN MÃ ĐI LẤY, không phải thiếu dữ liệu; nói sai chỗ thiếu thì người ta đi đòi nhầm chỗ.

     Trục giữ ĐỦ 12 CỘT, kể cả tháng chưa nạp chuyến nào: tháng rỗng mang `null`, và `BieuDoDuong`
     cắt đường tại đó thay vì nối qua. Lọc tháng rỗng ra cho hình "đẹp" là bóp hai tháng cách nhau
     một quãng nghỉ thành hai cột liền nhau. */
  /* Cỡ số của TẦNG VẬN HÀNH nhỏ hơn tầng chủ một bậc, và KHÔNG xuống dòng: «27.1 L/100km» ở cỡ cũ
     vắt thành hai dòng, làm ô ấy cao hơn năm ô bên cạnh và cả hàng gãy. */
  const SO_NHO: React.CSSProperties = { fontSize: "calc(16/14*1rem)", whiteSpace: "nowrap" };
  /* XS-3 — năm ô bằng nhau: cột dọc, cao tối thiểu như nhau, nút «Xem chi tiết» đẩy xuống đáy. */
  const O_VH: React.CSSProperties = { display: "flex", flexDirection: "column", minHeight: 128, minWidth: 0 };
  const PHU: React.CSSProperties = { fontSize: "calc(11.5/14*1rem)", marginTop: 2, whiteSpace: "nowrap",
                                     overflow: "hidden", textOverflow: "ellipsis" };
  const XEM: React.CSSProperties = { marginTop: "auto", paddingTop: 6, fontSize: "calc(12/14*1rem)" };
  const DV: React.CSSProperties = { fontSize: "calc(12/14*1rem)", fontWeight: 600 };
  const vnd = (x?: number | null) => (x == null ? null : Math.round(x).toLocaleString("vi-VN"));
  const PHU_VH: Record<string, string> = {
    ngay_xe_hoat_dong: [o.so_xe_chay && `${o.so_xe_chay} xe`, o.so_chuyen && `${o.so_chuyen} chuyến`]
      .filter(Boolean).join(" · "),
    tieu_hao_l100: [o.so_lit && `${vnd(o.so_lit)} lít`, o.km_chuyen && `${vnd(o.km_chuyen)} km`]
      .filter(Boolean).join(" · "),
    km_chay_rong: o.km_chuyen ? `trên ${vnd(o.km_chuyen)} km chuyến` : "",
  };
  const CHI_TIET_VH: Record<string, string> = {
    ngay_xe_hoat_dong: "/lai-lo-doi-xe", tieu_hao_l100: "/doi-xe/gia-dau", km_chay_rong: "/doi-xe",
  };
  const xeCoNguon = !!xe?.co_nguon;
  /* HQ-5 (23/10/2026) — BẢNG LỆNH TRỐNG THÌ KHÔNG IN SỐ 0.
     Đo trên hệ thật 23/10/2026: `/fleet/lenh-dieu-xe` trả MẢNG RỖNG — chưa ai lập một lệnh điều
     xe nào, bao giờ. Mà `co_nguon` soi bảng XE (11 xe → true), nên ô này in «0» kèm «11 xe nằm
     bãi trên 11 xe điều được»: đọc ra là đã đếm xong và hôm nay đội xe nghỉ.
     Sự thật khác hẳn: cái bảng mà con số này đếm chưa có ai nhập. Và vì nó chưa có ai nhập nên ô
     ấy sẽ in 0 mỗi ngày — một con số không bao giờ sai, không bao giờ đổi, và không bao giờ cho
     ai biết là cửa nhập đang bỏ không.
     `co_lenh === false` mới là «chưa ai lập lệnh». `undefined` thì giữ nguyên lối cũ: máy chủ
     bản trước chưa trả cờ này, và đoán hộ một màn hình Chủ tịch thì thà đừng đoán. */
  const chuaLapLenh = xe?.co_lenh === false;
  const chuoi: DiemChuoi[] = bo?.chuoi || [];
  const nhanKy = chuoi.map((c) => c.nhan);
  const diem = (lay: (c: DiemChuoi) => number | null | undefined) =>
    chuoi.map((c) => ({ nhan: c.nhan, gt: lay(c) ?? null }));
  /* MÀU THEO NGHĨA, không theo thứ tự chuỗi (anh Tuấn chốt 20/10/2026):
       doanh thu — VÀNG (d1) · lợi nhuận — XANH (d4) · lợi nhuận có kỳ ÂM — ĐỎ (d2)
     Đổi màu cả đường khi CÓ MỘT kỳ lỗ, chứ không tô đỏ riêng đoạn ấy: một đường hai màu đọc ra
     như hai chuỗi khác nhau, còn người đọc cần thấy ngay "năm nay có tháng lỗ" rồi mới tìm tháng nào. */
  const coLo = chuoi.some((c) => typeof c.loi_nhuan === "number" && c.loi_nhuan < 0);
  const dienBien: Duong[] = [
    { ten: "Doanh thu", lop: "d1", diem: diem((c) => c.doanh_thu) },
    { ten: coLo ? "Lợi nhuận (có kỳ lỗ)" : "Lợi nhuận", lop: coLo ? "d2" : "d4",
      diem: diem((c) => c.loi_nhuan) },
  ];
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

      {/* ── TẦNG CHỦ ── */}
      <div style={{ display: "grid", gap: 10, marginBottom: 12,
                    gridTemplateColumns: "repeat(auto-fit, minmax(168px, 1fr))" }}>
        {chu.map(([nhan, gt, khoa]) => (
          <div key={nhan} style={O_CHU}>
            <div className="v14-o-nhan">{nhan}</div>
            <div className="v14-o-so" style={{ fontSize: "calc(26/14*1rem)", lineHeight: 1.15 }}>
              {gt ?? "—"}</div>
            {gt !== null && muiTen(khoa)}
          </div>
        ))}
      </div>

      {/* ── TẦNG VẬN HÀNH ── XS-3 (anh Tuấn duyệt bản xem thử 25/10/2026): năm ô BẰNG NHAU — mỗi ô
          tên · con số · MỘT dòng 4–5 chữ kèm số cụ thể · nút «Xem chi tiết» nằm ở đáy, thẳng hàng
          giữa năm ô. Lời giải thích dài chuyển vào màn chi tiết, không nằm trên màn Chủ tịch.
          Kiểu đặt thẳng tại chỗ (O_VH, PHU, XEM) — không thêm lớp vào globals.css (tệp làn khác giữ). */}
      <div className="v14-o-ds" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))" }}>
        {vanHanh.map(([nhan, gt, khoa]) => (
          <div key={nhan} className={"v14-o" + (gt === null ? " rong" : "")} style={O_VH}>
            <div className="v14-o-nhan">{nhan}</div>
            <div className="v14-o-so" style={SO_NHO}>{gt ?? "—"}</div>
            {gt !== null && muiTen(khoa)}
            <div className="muted" style={PHU}>{PHU_VH[khoa] ?? ""}</div>
            <Link className="the-cua" href={CHI_TIET_VH[khoa]} style={XEM}>Xem chi tiết →</Link>
          </div>
        ))}
        {/* Ô CÔNG SUẤT là ô duy nhất có thể đang chờ người khai, nên dấu gạch của nó được thay bằng
            tên bộ phận và lối vào cửa nhập. */}
        <div className={"v14-o" + (o.cong_suat_khai_thac == null ? " rong" : "")} style={O_VH}>
          <div className="v14-o-nhan">Công suất khai thác</div>
          {o.cong_suat_khai_thac == null && thieuCS ? (
            <>
              <div className="v14-o-so v14-o-chu" style={SO_NHO}>chờ {thieuCS.bo_phan}</div>
              <div className="muted" style={PHU}>{thieuCS.thieu.length} xe chưa khai ngày vào đội</div>
              <Link className="the-cua" href={thieuCS.cua_nhap} style={XEM}>Xem chi tiết →</Link>
            </>
          ) : (
            <>
              <div className="v14-o-so" style={SO_NHO}>{so(o.cong_suat_khai_thac, "%") ?? "—"}</div>
              {o.cong_suat_khai_thac != null && muiTen("cong_suat_khai_thac")}
              <div className="muted" style={PHU}>
                {o.ngay_xe_mau ? `${so(o.ngay_xe_hoat_dong) ?? "—"} / ${so(o.ngay_xe_mau)} ngày-xe` : ""}
                {o.cong_suat_den_ngay ? ` · tới ${ngayNgan(o.cong_suat_den_ngay)}` : ""}</div>
              <Link className="the-cua" href="/lai-lo-doi-xe" style={XEM}>Xem chi tiết →</Link>
            </>
          )}
        </div>
        {/* XE ĐANG ĐI — số của HÔM NAY, không theo kỳ đang chọn, nên nhãn nói «hôm nay». */}
        <div className={"v14-o" + (xeCoNguon && (!chuaLapLenh || (!!sheet && !sheet.loi)) ? "" : " rong")}
             style={O_VH}>
          <div className="v14-o-nhan">Xe đang đi · hôm nay</div>
          {xeCoNguon && chuaLapLenh && sheet && !sheet.loi ? (
            /* XS-1 (25/10/2026): chưa có lệnh điều xe thì đếm theo sheet quyết toán của Đội xe. Nguồn
               và giờ đọc nằm ở màn chi tiết; ô chỉ giữ con số và việc cần làm. */
            <>
              <div className="v14-o-so" style={SO_NHO}>{sheet.dang_di ?? "—"}
                <span className="muted" style={DV}> / {sheet.dieu_duoc} xe</span></div>
              <div className="muted" style={PHU}>{sheet.o_bai} nằm bãi
                {!!sheet.so_can_sua && <> · <b style={{ color: "var(--orange)" }}>{sheet.so_can_sua} dòng sửa</b></>}
                {sheet.ban_cu && " · bản cũ"}</div>
              <Link className="the-cua" href="/doi-xe/xe-hom-nay" style={XEM}>Xem chi tiết →</Link>
            </>
          ) : xeCoNguon && chuaLapLenh ? (
            <>
              <div className="v14-o-so v14-o-chu" style={SO_NHO}>chờ Đội xe</div>
              <div className="muted" style={PHU}>chưa lập lệnh · {xe!.dieu_duoc} xe</div>
              <Link className="the-cua" href="/doi-xe" style={XEM}>Xem chi tiết →</Link>
            </>
          ) : xeCoNguon ? (
            <>
              {/* `dang_chay` rỗng là «nguồn có mà số chưa về» — không in 0 (ca đỏ test_tc23). */}
              <div className="v14-o-so" style={SO_NHO}>
                {xe!.dang_chay === null || xe!.dang_chay === undefined
                  ? <span className="muted" style={{ fontSize: "calc(13/14*1rem)" }}>chưa có số</span>
                  : <>{xe!.dang_chay}<span className="muted" style={DV}> / {xe!.dieu_duoc} xe</span></>}
              </div>
              <div className="muted" style={PHU}>{xe!.o_bai} nằm bãi
                {!!xe!.bat_thuong && <> · <b style={{ color: "var(--red)" }}>{xe!.bat_thuong} bất thường</b></>}
                {!!xe!.lech && <> · <b style={{ color: "var(--red)" }}>{xe!.lech} lệnh lệch</b></>}</div>
              <Link className="the-cua" href="/doi-xe" style={XEM}>Xem chi tiết →</Link>
            </>
          ) : (
            <>
              <div className="v14-o-so v14-o-chu" style={SO_NHO}>chờ Đội xe</div>
              <div className="muted" style={PHU}>chưa nhập bảng xe</div>
              <Link className="the-cua" href="/doi-xe" style={XEM}>Xem chi tiết →</Link>
            </>
          )}
        </div>
      </div>

      {/* ── DIỄN BIẾN ── Hình của bản vẽ. Chuỗi còn rỗng nên `BieuDoDuong` tự rơi về khối rỗng
           kèm bộ phận và cửa nhập; không vẽ một đường bịa để lấp chỗ. */}
      {/* Lớp màu `d4` (xanh «tốt») nay nằm trong `globals.css` cạnh d1/d2/d3 — vòng 20/10 phải
          khai tạm bằng một thẻ <style> tại đây vì làn Vòng đang giữ tệp ấy; làn ấy xong rồi nên
          21/10 gộp về chỗ đúng. Khối đo mù màu đi kèm nằm trong globals.css, ngay trên nhóm
          `.bd-net`. Một dòng của nó nói về chính chỗ này, nên chép lại cho khỏi lạc:

            d2 (đỏ) và d4 (xanh) chỉ cách ΔE 3,8 với mắt mù lục — với người ấy, đường lợi nhuận
            lúc lãi và lúc có kỳ lỗ là CÙNG MỘT MÀU. Dấu hiệu thứ hai là CHỮ «(có kỳ lỗ)» thêm
            vào tên chuỗi ngay bên dưới. Gỡ chữ ấy đi là gỡ tín hiệu, không phải gỡ lời giải thích. */}
      <div style={{ marginTop: 14 }}>
        <BieuDoDuong ten="Diễn biến hiệu quả đội xe" phu={o.nhan || undefined}
          ds={dienBien} nhan={nhanKy} dinh_dang="tien"
          ai="Đội xe" cua="/doi-xe" cua_ten="Cửa nhập đội xe"
          chan={<span className="muted">12 tháng của năm. Tháng không có điểm là tháng <b>chưa nạp
            chuyến nào</b> hoặc <b>chưa tới</b> — đường cắt tại đó chứ không nối qua, vì nối là vẽ ra
            một con số không ai nhập.</span>} />
      </div>

      {/* Cửa sang bảng từng xe. Bản vẽ xếp nó thành một khối trong khối này, nhưng bảng ấy đã có
          trang riêng dựng trên `fleet_lai_lo`; in lại ở đây là hai chỗ cùng một con số. */}
      <p className="v14-ghi">
        <span className="muted">Doanh thu, chi phí và lợi nhuận của TỪNG xe ·{" "}</span>
        <Link className="the-cua" href="/lai-lo-doi-xe">Bảng lãi lỗ từng xe →</Link>
      </p>

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
