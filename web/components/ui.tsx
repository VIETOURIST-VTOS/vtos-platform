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
