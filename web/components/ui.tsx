export const Tag = ({ cls = "", children }: { cls?: string; children: React.ReactNode }) => <span className={"tag " + cls}>{children}</span>;
export const Gate = ({ ok, children }: { ok: boolean | null; children: React.ReactNode }) => <div className={"gate " + (ok === null ? "" : ok ? "pass" : "fail")}>{children}</div>;
export function errMsg(e: any): string { return e?.gate ? `CỔNG ${e.gate.replace("CONG_", "").replace(/_/g, "+")} – ${e.message}` : e?.message || "Có lỗi xảy ra"; }

/** Nhãn cho biết màn hình đang lọc theo mảng kinh doanh nào.
 *
 *  Có nhãn này vì hai phòng dùng CHUNG một màn hình, chỉ khác bộ lọc. Không nói ra thì người dùng không phân
 *  biệt được "phòng tôi chỉ có ngần này" với "hệ thống lọc mất dữ liệu của tôi" – và họ sẽ đi hỏi vòng quanh
 *  thay vì tin con số. */
export const MangTag = ({ mang }: { mang: string }) => {
  if (!mang) return null;
  const ten = mang === "doan" ? "Kinh doanh Đoàn (MICE)" : mang === "le" ? "Kinh doanh Lẻ" : mang;
  return <p className="muted">Đang lọc theo mảng <b>{ten}</b>. Tour đoàn nhận theo loại chuyến hoặc mã bắt đầu
    bằng MICE; bỏ tham số <code>mang</code> trên đường dẫn để xem tất cả.</p>;
};

/** CỘT CHỮ KÝ — Đợt VA-WEB4, 12/10/2026. MỘT thành phần cho cả bốn màn hình chính sách.
 *
 *  Nó KHÔNG nhận tên vai từ nơi gọi, và đó là cả nội dung của đợt này. Trước hôm nay bốn màn
 *  hình gõ tay `"CT … · TGĐ …"`; Đợt LG2 (11/10/2026) đổi ba cửa sang một chữ ký Chủ tịch và
 *  đổi `VAI_KY_CAN` theo, nhưng bốn chỗ gõ tay ấy không ai đổi. Hậu quả đo được trên
 *  production ngày 12/10: một dòng tham số đã đủ ký, đang có hiệu lực, hiện ra là "TGĐ …".
 *
 *  Danh sách truyền vào do `chu_ky.chu_ky_de_hien` dựng từ bảng luật. Thêm hay bớt người ký
 *  thì sửa đúng một chỗ trong mã nghiệp vụ, bốn màn hình tự đúng theo.
 *
 *  RỖNG KHÔNG PHẢI "KHÔNG CẦN KÝ" (luật K2): danh sách rỗng là MÁY CHỦ CHƯA GỬI — bản web mới
 *  gặp bản máy chủ cũ. Hiện "—" chứ không hiện "đủ ký", vì nói "đủ ký" lúc không biết gì là
 *  đúng loại lỗi mà đợt này đi sửa.
 */
export type ChuKyMot = { vai: string; ten: string; da_ky: boolean };
export const KyO = ({ ky }: { ky?: ChuKyMot[] | null }) => {
  if (!ky || !ky.length) return <span className="muted">—</span>;
  const thieu = ky.filter((k) => !k.da_ky).length;
  return <>{ky.map((k, i) => <span key={k.vai}>{i ? " · " : ""}{k.ten} {k.da_ky ? "✔" : "…"}</span>)}
    {thieu > 0 && <> <Tag cls="warn">chờ {thieu} chữ ký</Tag></>}</>;
};

/** Tên người ký cho tiêu đề và nút Trình. Rỗng trả về chuỗi rỗng để nơi gọi tự chọn câu thay. */
export const tenKy = (ky?: string[] | null) => (ky && ky.length ? ky.join(" + ") : "");
