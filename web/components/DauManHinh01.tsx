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
};

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
    <div className="mh01-trang">
      <div>
        <h1>{ten}</h1>
        <p className="mh01-phu">{PHU_TRANG}</p>
      </div>
      <button type="button" className="act grey mh01-in" onClick={() => window.print()}>
        In / Lưu PDF
      </button>
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
