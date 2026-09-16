"use client";
/** MÀN HÌNH 01 – phần đầu theo bản vẽ "Bảng điều hành Chủ tịch" V1.2 (12/9/2026).
 *
 *  Ba khối, đúng thứ tự bản vẽ:
 *    01  Phạm vi · kỳ báo cáo · thời điểm cập nhật
 *    02  Cần quyết định – tối đa 5 hồ sơ
 *    03  Tám thẻ chỉ tiêu kinh doanh & vận hành
 *
 *  BẢN TGĐ (SEC-02) KHÔNG PHẢI MỘT MÀN HÌNH KHÁC. Cùng một trang, đổi ba thứ: tên trang theo vai,
 *  nhãn phạm vi, và tập dòng do MÁY CHỦ cắt. Ở đây tuyệt đối không có câu nào kiểu
 *  `if (vai === "tgd") ẩn ...`: dòng bị ẩn ở trình duyệt thì vẫn đã rời khỏi máy chủ, ai mở công cụ
 *  nhà phát triển cũng đọc được – SEC-02 gọi đó là lỗi đỏ, và test_tc8 canh đúng chỗ ấy.
 *
 *  RANH GIỚI 09/9 GIỮ NGUYÊN: thẻ nào máy chủ chưa có nguồn thì ghi "Chưa có nguồn" kèm CỬA NHẬP –
 *  đường dẫn tới màn hình mà bộ phận phụ trách gõ số vào. Không lấy 0 thay cho "chưa ai nhập".
 */
import Link from "next/link";
import { useEffect, useState } from "react";
import { vnd } from "@/lib/api";

/** Tên trang theo vai. Bản vẽ V1.2 vẽ cho Chủ tịch; anh Tuấn chốt 12/9 làm luôn bản TGĐ. */
const TEN_TRANG: Record<string, string> = {
  chutich: "Bảng điều hành Chủ tịch",
  tgd: "Bảng điều hành Tổng giám đốc",
};

/** Màn hình 01 CHỈ hiển thị theo THÁNG (anh Tuấn chốt 13/9/2026). Quý và năm xem ở báo cáo chi
 *  tiết, không nhét vào đây.
 *
 *  Vì sao không để một ô chọn có sẵn ba mức: /dashboard mới tính theo tháng. Một ô chọn có "Quý"
 *  và "Năm" mà bấm vào chỉ ra "chưa có nguồn" là một lời hứa suông ngay trên màn hình đầu tiên –
 *  thà nói thẳng chỗ xem quý và năm nằm ở đâu. */

/** Một thẻ chỉ tiêu.
 *  `so` là null nghĩa là CHƯA CÓ NGUỒN – khác hẳn 0. Khi ấy thẻ đòi `cua` (đường dẫn cửa nhập) và
 *  `ai` (bộ phận phải nhập), để người đọc biết đi hỏi ai chứ không chỉ thấy một ô trống. */
export type The = {
  nhan: string; phu?: string; so: string | null; duoi?: string;
  cua?: string; ai?: string; do?: boolean;
  xu_huong?: XuHuong | null;
};

/** TC-36 · Chuỗi xu hướng của một thẻ. Máy chủ (`services/xu_huong.py`) đã quyết xong ba việc khó
 *  — lấy kỳ nào, kỳ nào rỗng, có đủ điểm để vẽ không — nên màn hình chỉ vẽ, không tự xét. */
export type XuHuong = {
  ten?: string; dinh_dang?: string;
  diem: { ky: string; gia_tri: number | null }[];
  du_ve: boolean; so_ky_co_so?: number; vi_sao?: string;
  so_sanh?: { ky: string; ky_truoc: string; chenh: number;
              phan_tram: number | null; tang: boolean; giam: boolean } | null;
};

/** Tên kỳ "2026-08" → "08/2026". Đọc "2026-08" trên nhãn cột thì phải dịch trong đầu mỗi lần. */
const tenKy = (ky: string) => { const [y, m] = ky.split("-"); return `${m}/${y}`; };

/** TC-41 · DÒNG PHỤ "SO VỚI KẾ HOẠCH" của thẻ Doanh thu và thẻ Lợi nhuận trước thuế.
 *
 *  Bản vẽ V1.4 chốt dòng phụ ấy từ lâu, nhưng suốt bốn vòng thẻ chỉ in được một câu thú nhận vì
 *  chưa có bảng kế hoạch. Cửa nhập /ke-hoach-thang mở ngày 16/9/2026, nên câu ấy nay viết được.
 *
 *  HÀM NÀY KHÔNG TÍNH GÌ. Tỉ lệ đạt do máy chủ tính (services/ke_hoach.ty_le_dat) và gửi xuống ở
 *  `ty_le`; ở đây chỉ nhân 100 để đổi sang phần trăm khi in — đúng như mọi chỗ khác trên màn hình.
 *
 *  BA TRẠNG THÁI, BA CÂU KHÁC HẲN NHAU, và nhập nhằng giữa chúng là chỗ hỏng:
 *    · chưa nhập gì cả        → nói chưa có, và nói ai nhập ở đâu
 *    · nhập thiếu pháp nhân   → nói THIẾU AI, vì phần đã nhập KHÔNG phải kế hoạch nhỏ hơn
 *    · đủ                     → in chỉ tiêu và tỉ lệ đạt
 */
export function docHoKeHoach(kh: any, don_vi: "doanh_thu" | "loi_nhuan_truoc_thue",
                             ty_le: number | null | undefined): string {
  const o = kh?.[don_vi];
  if (!o) return "chưa có kế hoạch tháng để so sánh (Kế toán nhập ở Kế hoạch tháng)";
  if (!o.du) {
    const thieu: string[] = o.thieu || [];
    if (thieu.length === 0) {
      return "chưa có kế hoạch tháng để so sánh (Kế toán nhập ở Kế hoạch tháng)";
    }
    // Kê đích danh, tối đa hai tên rồi mới đếm phần còn lại: "thiếu 4 pháp nhân" không giúp ai đi
    // đòi, còn một danh sách bảy tên thì không đọc hết trên một dòng phụ.
    const ten = thieu.slice(0, 2).join(", ")
      + (thieu.length > 2 ? ` và ${thieu.length - 2} pháp nhân nữa` : "");
    return `kế hoạch tháng chưa đủ — còn thiếu ${ten} (Kế toán nhập ở Kế hoạch tháng)`;
  }
  const chi_tieu = `kế hoạch ${vnd(o.gia_tri)}`;
  if (ty_le === null || ty_le === undefined) return `${chi_tieu} · chưa tính được tỉ lệ đạt`;
  return `${chi_tieu} · đạt ${Math.round(ty_le * 100)}%`;
}

/** BIỂU ĐỒ NHỎ TRÊN THẺ — cột, không phải đường.
 *
 *  Vì sao CỘT: chuỗi này có ô trống thật (kỳ chưa ai lưu báo cáo), và ô trống là chuyện bình
 *  thường chứ không phải ngoại lệ. Đường gấp khúc phải hoặc nối liền qua chỗ trống — tức bịa ra
 *  một đoạn dữ liệu — hoặc đứt quãng trông như lỗi vẽ. Cột thì kỳ nào không có số là chỗ ấy trống,
 *  đọc ra ngay và không gây hiểu nhầm.
 *
 *  MỘT DÃY, KHÔNG CHÚ GIẢI: cả biểu đồ chỉ có một chỉ tiêu, và tên nó là tên thẻ ngay phía trên.
 *  Thêm một hộp chú giải ghi lại đúng cái tên ấy là thêm chữ mà không thêm tin.
 *
 *  KHÔNG GHI SỐ TRÊN TỪNG CỘT: sáu con số nhỏ chen nhau thì không đọc được cái nào. Con số lớn của
 *  kỳ đang chạy đã nằm ngay trên; từng kỳ xem bằng cách rê chuột.
 */
function BieuDoNho({ xh }: { xh: XuHuong }) {
  const diem = xh.diem || [];
  if (!xh.du_ve) {
    return <div className="the-xh-rong muted">{xh.vi_sao || "Chưa đủ dữ liệu để vẽ xu hướng."}</div>;
  }
  const v = diem.map((d) => d.gia_tri).filter((x): x is number => x !== null);
  const max = Math.max(...v, 0), min = Math.min(...v, 0);
  const bien = max - min || 1;
  const H = 30;
  // Mốc 0 nằm đúng chỗ của nó. Vẽ mọi cột từ đáy khung thì một kỳ LỖ trông như một kỳ lãi ít.
  const y0 = Math.round(H * (max / bien));
  const ss = xh.so_sanh;
  return (
    <div className="the-xh">
      <div className="the-xh-cot" style={{ height: H }}>
        {/* MỖI KỲ MỘT Ô RIÊNG, và thanh định vị TRONG ô ấy. Bản đầu đặt thanh định vị tuyệt đối
            thẳng trong lưới: thanh bị nhấc khỏi dòng lưới nên cả sáu thanh trải hết bề ngang và
            chồng lên nhau thành MỘT vệt dài. Dựng ra ảnh mới thấy — đọc mã thì trông vẫn đúng. */}
        {diem.map((d) => {
          // Ô TRỐNG THẬT vẫn chừa đúng chỗ của nó. Bỏ ô đi thì sáu kỳ trông như bốn kỳ liền nhau
          // và khoảng cách thời gian bị bóp méo.
          if (d.gia_tri === null) {
            return <span key={d.ky} className="the-xh-o" title={`${tenKy(d.ky)}: chưa có số`} />;
          }
          const cao = Math.max(2, Math.round((Math.abs(d.gia_tri) / bien) * H));
          const am = d.gia_tri < 0;
          return (
            <span key={d.ky} className="the-xh-o"
              title={`${tenKy(d.ky)}: ${d.gia_tri.toLocaleString("vi-VN")}`}>
              <span className={"the-xh-thanh" + (am ? " am" : "")}
                style={{ height: cao, top: am ? y0 : y0 - cao }} />
            </span>
          );
        })}
        <span className="the-xh-truc0" style={{ top: y0 }} />
      </div>
      {/* TC-40 · ĐỌC HỘ THÀNH CÂU, không chỉ một mũi tên và một tỉ lệ.
          Anh Tuấn chốt 15/9/2026: tám thẻ phải có "biểu đồ và số + phân tích". Bản cũ in
          "▲ 25.0% 08/2026 so với 07/2026" — đúng nhưng phải tự dịch trong đầu, và khi phần trăm
          không tính được (kỳ trước bằng 0) thì nó ra "= —", đọc như một lỗi hiển thị.

          Câu ở đây chỉ DIỄN ĐẠT LẠI con số máy chủ đã tính (`so_sanh`), không tính thêm gì —
          ranh giới 09/9 giữ nguyên. Chênh lệch TUYỆT ĐỐI luôn nói được, kể cả khi phần trăm
          không tồn tại; nên nó đứng trước, và phần trăm chỉ là phần trong ngoặc.

          MŨI TÊN ĐI KÈM CHỮ, không chỉ có màu: người không phân biệt được đỏ–xanh vẫn phải đọc
          được chiều. Và ghi rõ so với KỲ NÀO — "so với kỳ trước" mà không nói kỳ nào là một câu
          không kiểm được. */}
      {ss && <div className="the-xh-ss">
        <span className={"the-xh-mui" + (ss.tang ? " tang" : ss.giam ? " giam" : "")}>
          {ss.tang ? "▲ tăng" : ss.giam ? "▼ giảm" : "= không đổi"}
        </span>
        {typeof ss.chenh === "number" && ss.chenh !== 0 && (
          <span className="the-xh-chenh"> {Math.abs(ss.chenh).toLocaleString("vi-VN")}</span>
        )}
        {ss.phan_tram !== null && ss.phan_tram !== undefined && (
          <span className="muted"> ({Math.abs(ss.phan_tram * 100).toFixed(1)}%)</span>
        )}
        <span className="muted"> so với {tenKy(ss.ky_truoc)}</span>
      </div>}
    </div>
  );
}

export function TheChiTieu({ t }: { t: The }) {
  const rong = t.so === null;
  return (
    <div className={"the-ct" + (rong ? " rong" : "")}>
      <div className="the-nhan">{t.nhan}</div>
      {t.phu && <div className="the-phu">{t.phu}</div>}
      <div className={"the-so" + (t.do ? " do" : "")}>{rong ? "—" : t.so}</div>
      {rong
        ? <div className="the-thieu">
            <span className="tag">Chưa có nguồn</span>
            {t.ai && <span className="muted"> · {t.ai} nhập</span>}
            {t.cua && <Link className="the-cua" href={t.cua}>Cửa nhập →</Link>}
          </div>
        : t.duoi && <div className="the-duoi">{t.duoi}</div>}
      {/* Biểu đồ đặt DƯỚI dòng mô tả: con số lớn vẫn là thứ đọc trước, xu hướng là thứ đọc sau.
          Thẻ chưa có số thì cũng chưa có xu hướng — không vẽ một dãy cột rỗng dưới một ô trống. */}
      {!rong && t.xu_huong && <BieuDoNho xh={t.xu_huong} />}
    </div>
  );
}

/** Ngày báo cáo = NGÀY HÔM NAY THEO LỊCH MÁY (anh Tuấn chốt 12/9), lấy trong useEffect chứ không
 *  tính lúc dựng: tính lúc dựng thì bản vẽ ở máy chủ và bản vẽ ở trình duyệt lệch nhau một nhịp và
 *  React kêu hydration mismatch – lỗi chỉ hiện trong console, không ai thấy. */
export function useHomNay(): string {
  const [s, setS] = useState("");
  useEffect(() => {
    const d = new Date();
    setS(d.toLocaleDateString("vi-VN", { weekday: "long", day: "2-digit", month: "2-digit", year: "numeric" }));
  }, []);
  return s;
}

/** Nhãn tháng báo cáo, lấy từ lịch máy. */
export function tenThang(): string {
  const d = new Date();
  return `Tháng ${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
}

/** KHÔNG in nhãn phạm vi ở đây. Phạm vi đang xem do ô đơn vị TRÊN THANH NGANG giữ, và người dùng
 *  đổi được bất cứ lúc nào; in thêm một nhãn thứ hai ở đây là hai chỗ nói về cùng một thứ, mà chỗ
 *  này thì không biết chỗ kia vừa đổi. Một dòng nhắc là đủ. */
export function DongLoc() {
  const homNay = useHomNay();
  const [thang, setThang] = useState("");
  useEffect(() => setThang(tenThang()), []);
  return (
    <div className="mh01-loc">
      <span className="mh01-ky"><span>Kỳ báo cáo</span><b>{thang || "…"}</b></span>
      {/* Quý và năm KHÔNG nằm trên màn hình này. Dẫn thẳng sang chỗ xem được, chứ không để một ô
          chọn bấm vào lại báo "chưa có nguồn". */}
      <Link className="the-cua" href="/phan-he/baocao">Xem theo quý và năm →</Link>
      <span className="tag">Đơn vị tiền: đồng</span>
      {/* SỬA 13/9/2026. Câu cũ ghi "chọn ở ô đơn vị trên thanh ngang" – chỉ vào một ô KHÔNG CÓ:
          components/ChonDonVi.tsx trả về null khi máy chủ chưa mở GET /pham-vi/don-vi, mà hôm nay
          thì chưa. Bảo người ta bấm vào chỗ trống là kiểu sai khó chịu nhất, vì họ sẽ đi tìm và cho
          rằng mình không thấy. Nói thẳng: chưa đổi được đơn vị, và vì sao. */}
      <span className="muted">Phạm vi do máy chủ áp theo tài khoản · chưa đổi được đơn vị</span>
      {/* Ngày báo cáo là mốc phân nhóm của mọi bảng theo hạn ở dưới – ghi ra để không ai phải đoán. */}
      <span className="muted mh01-ngay">Ngày báo cáo: {homNay || "…"}</span>
      {/* TC-35 · Nút In về ĐÚNG CHỖ bản vẽ đặt: cuối hàng lọc, mép phải. Nó là một THAO TÁC TRÊN
          KỲ ĐANG CHỌN — in đúng cái kỳ ghi ngay bên trái — nên đứng cùng hàng với kỳ thì đọc ra
          quan hệ ấy; đứng cạnh tiêu đề thì nó chỉ là một nút trôi nổi. */}
      <button type="button" className="act grey mh01-in" onClick={() => window.print()}>
        In / Lưu PDF
      </button>
    </div>
  );
}

/** ĐẦU TRANG THEO BẢN VẼ V1.4 — ba thứ bản vẽ mở đầu mà VTOS còn thiếu.
 *
 *  1. ĐƯỜNG DẪN. Bản vẽ ghi "VTOS / Không gian lãnh đạo / Thiết kế đề xuất". Chặng cuối của bản
 *     vẽ là tên CỦA BẢN VẼ, không phải của trang thật — trang thật mang tên trang thật.
 *
 *  2. DÒNG PHỤ nói trang này trả lời những câu hỏi nào. Bản vẽ đặt nó ngay dưới tiêu đề, và nó
 *     làm một việc thật: người mở lần đầu biết cuộn xuống sẽ gặp gì.
 *
 *  3. NÚT IN / LƯU PDF. Đây là việc thật, không phải trang trí: Chủ tịch mang bảng này vào phòng
 *     họp. Kiểu in nằm ở globals.css — giấy là môi trường khác, không phải màn hình thu nhỏ.
 *
 *  KHÔNG lấy huy hiệu "Giao diện xanh navy" ở góc phải bản vẽ: đó là nhãn của TÀI LIỆU THIẾT KẾ
 *  tự mô tả mình, dán lên trang thật thì thành một ô chữ không ai bấm được và không nói gì thêm.
 */
const PHU_TRANG = "Kết quả · Phải thu · Phải trả · Dòng tiền · Quyết định";

export function TieuDe({ vai, ten_vai }: { vai?: string; ten_vai?: string }) {
  const ten = TEN_TRANG[vai || ""] || `Bảng điều hành · ${ten_vai || ""}`;
  return (<>
    <div className="mh01-duong">
      <span>VTOS</span><span>/</span><span>Không gian lãnh đạo</span><span>/</span><span>{ten}</span>
    </div>
    {/* TC-35 · Nút In / Lưu PDF KHÔNG nằm ở đây. Bản vẽ đặt nó trong HÀNG LỌC, mép phải, ngang
        với "Kỳ báo cáo" — xem `DongLoc`. Vòng TC-31 đặt nhầm lên cạnh tiêu đề: đúng nút, sai chỗ.
        Đo trên bản vẽ: nút nằm trong `.filters`, trang thật để ở đầu trang cao hơn 87px. */}
    <div className="mh01-trang">
      <div>
        <h1>{ten}</h1>
        <p className="mh01-phu">{PHU_TRANG}</p>
      </div>
    </div>
  </>);
}

/** Khối 02 – "Cần quyết định". Bản vẽ đặt nó NGAY TRÊN các chỉ tiêu: mở màn hình ra là thấy việc
 *  chờ mình, rồi mới tới số.
 *
 *  KHÔNG GIỚI HẠN SỐ HỒ SƠ (anh Tuấn chốt 13/9/2026). Bản vẽ V1.2 ghi "tối đa 5 hồ sơ ưu tiên",
 *  nhưng cắt ở năm nghĩa là hồ sơ thứ sáu nằm ngoài tầm mắt người duy nhất được quyết nó – mà thứ
 *  tự ưu tiên thì máy chủ chưa xếp, nên "năm cái đầu" chỉ là năm cái ngẫu nhiên. Hiện đủ, và
 *  đếm ra số. */
export function KhoiQuyetDinh({ ds, vai }: { ds: any[]; vai?: string }) {
  const co = ds || [];
  const ten = vai === "tgd" ? "Cần Tổng giám đốc quyết định" : "Cần Chủ tịch quyết định";
  return (
    <section className="panel mh01-qd" id="cho-toi-duyet">
      <div className="mh01-dau">
        <h2>{ten}</h2>
        <span className="tag">{co.length} hồ sơ đang chờ</span>
      </div>
      {co.length === 0
        ? <p className="muted">Không có hồ sơ nào đang chờ ở vai trò này.</p>
        : <div className="mh01-qd-ds">
            {co.map((a: any, i: number) => (
              <Link key={i} href={a.href} className="mh01-qd-nut">{a.label}</Link>
            ))}
          </div>}
    </section>
  );
}

/** Khối 03 – tám thẻ. Bản vẽ xếp hai hàng bốn thẻ trên màn rộng; ở đây để lưới tự xuống dòng theo
 *  bề rộng thật, vì khoá cứng bốn cột thì trên màn 1280px chữ bị cắt. */
export function TamThe({ ds }: { ds: The[] }) {
  return <div className="mh01-the">{ds.map((t) => <TheChiTieu key={t.nhan + (t.phu || "")} t={t} />)}</div>;
}

/** Số tiền cho thẻ: rỗng thì trả null để thẻ tự ghi "Chưa có nguồn", không in "0 đ". */
export function tien(x: any): string | null {
  return x === null || x === undefined || x === "" ? null : vnd(x);
}

/** Số đếm cho thẻ. Cùng quy ước: undefined là chưa có nguồn, 0 là đã đếm và bằng không. */
export function dem(x: any): string | null {
  return x === null || x === undefined || x === "" ? null : String(x);
}
