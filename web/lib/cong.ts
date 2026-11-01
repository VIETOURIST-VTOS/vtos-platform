/* CG-1 · phiên CỔNG NGOÀI (khách hàng, đối tác, cổ đông). Khoá lưu RIÊNG, không bao giờ là `vtos_token`:
   lib/api.ts không gửi phiên này lên cửa nội bộ nào, và máy chủ cũng không nhận nó ở đó (ký khoá khác). */
export const KHOA_PHIEN_CONG = "vtd_cong_phien";

/* CG-3 (Chủ tịch chốt 28/10/2026): ba tên miền cổng ngoài KHÓA CỨNG — không bao giờ mở VTOS ở đó. Phiên VTOS
   lỡ lưu trên kh./dt./ir. (vd từng đăng nhập nội bộ ở tên miền ấy) bị bỏ qua và xóa; VTOS chỉ mở ở crm. */
export const TEN_MIEN_CONG = ["kh.vietourist.vn", "dt.vietourist.vn", "ir.vietourist.vn",
  // TM-1 (Chủ tịch 02/11/2026): vietourist.com.vn chạy song song — cùng luật khóa cứng CG-3.
  "kh.vietourist.com.vn", "dt.vietourist.com.vn", "ir.vietourist.com.vn"];
// TM-1: đang ở họ .com.vn thì nội bộ mở crm.vietourist.com.vn, còn lại crm.vietourist.vn (máy chủ không có location → .vn).
export const VTOS_GOC = (() => {
  try { return location.hostname.toLowerCase().endsWith(".vietourist.com.vn") ? "https://crm.vietourist.com.vn" : "https://crm.vietourist.vn"; }
  catch { return "https://crm.vietourist.vn"; }
})();
export function laTenMienCong(): boolean {
  try { return TEN_MIEN_CONG.includes(location.hostname.toLowerCase()); } catch { return false; }
}

export function phienCong(): string { try { return localStorage.getItem(KHOA_PHIEN_CONG) || ""; } catch { return ""; } }
export function luuPhienCong(p: string) { try { localStorage.setItem(KHOA_PHIEN_CONG, p); } catch { /* trình duyệt chặn lưu */ } }
export function xoaPhienCong() { try { localStorage.removeItem(KHOA_PHIEN_CONG); } catch { /* bỏ qua */ } }

/* DK-3 · DẤU NHỚC MÁY — lớp thứ hai giữ cho mật khẩu 5 ký tự đứng được (Chủ tịch chốt 01/11/2026).
   MỖI CỔNG MỘT DẤU RIÊNG: mỗi cổng là một tài khoản riêng, dùng chung một dấu là lấy máy đã quen ở
   cổng khách hàng mở cho cổng cổ đông. Dấu này KHÔNG phải phiên: tự nó không mở được tài khoản nào,
   nó chỉ trả lời đúng một câu — «máy này đã xác minh chưa» — sau khi mật khẩu đã đúng. */
export const KHOA_MAY_CONG = "vtd_cong_may";
export function dauMay(loai: string): string { try { return localStorage.getItem(`${KHOA_MAY_CONG}:${loai}`) || ""; } catch { return ""; } }
export function luuDauMay(loai: string, d: string) { try { if (d) localStorage.setItem(`${KHOA_MAY_CONG}:${loai}`, d); } catch { /* trình duyệt chặn lưu */ } }
export function xoaDauMay(loai: string) { try { localStorage.removeItem(`${KHOA_MAY_CONG}:${loai}`); } catch { /* bỏ qua */ } }

export async function goiCong(path: string, json?: any): Promise<any> {
  const headers: Record<string, string> = {};
  const p = phienCong();
  if (p) headers["Authorization"] = `Bearer ${p}`;
  if (json !== undefined) headers["Content-Type"] = "application/json";
  const r = await fetch(`/api/v1/cong${path}`, json === undefined ? { headers } : { method: "POST", headers, body: JSON.stringify(json) });
  const t = await r.text(); let d: any = null; try { d = t ? JSON.parse(t) : null; } catch { d = t; }
  if (!r.ok && r.status === 401 && json !== undefined && !p) {
    try { window.dispatchEvent(new CustomEvent(SU_KIEN_CAN_DANG_NHAP)); } catch { /* bỏ qua */ }
  }
  if (!r.ok) { const x = d?.detail; throw { status: r.status, message: typeof x === "string" ? x : x?.message || `Lỗi ${r.status}`, ma: x?.ma || "" }; }
  return d;
}

/* SP-1 · sang cổng thẻ. Máy chủ trả {form} (SePay: biểu mẫu POST đã ký, gửi đúng thứ tự trường) hoặc {url} (OnePay). */
export function diCongThe(r: { url?: string; form?: { action: string; fields: [string, string][] } }) {
  if (r.url) { window.location.href = r.url; return; }
  if (!r.form) throw { message: "Cổng thẻ chưa mở — dùng QR chuyển khoản" };
  const f = document.createElement("form");
  f.method = "POST"; f.action = r.form.action; f.style.display = "none";
  for (const [k, v] of r.form.fields) { const i = document.createElement("input"); i.type = "hidden"; i.name = k; i.value = v; f.appendChild(i); }
  document.body.appendChild(f); f.submit();
}


/** KS-16l/16m (Chủ tịch 01/11/2026): dịch vụ chưa mở đặt trực tuyến trên cổng thì bấm vào mở trang riêng ở tab mới.
 *  Gọi ĐỒNG BỘ ngay trong sự kiện bấm (không sau await) để trình duyệt không chặn cửa sổ mới. */
// KS-16q (Chủ tịch duyệt bản xem thử 01/11/2026): ba trang riêng kh.vietourist.vn/hotel, /restaurant, /tours (thay
// cho trang chủ vietourist.com.vn tạm trỏ ở KS-16n). Trên tên miền cổng, next.config viết lại /hotel → /kham-pha/hotel;
// ở tên miền khác (crm., bản thử) /tours là màn VTOS nên đi thẳng /kham-pha/…
export type TrangRieng = "hotel" | "restaurant" | "tours";
export function duongRieng(k: TrangRieng, id?: number | string): string {
  return `${laTenMienCong() ? "" : "/kham-pha"}/${k}${id !== undefined && id !== null && id !== "" ? `/${id}` : ""}`;
}
export const LINK_NGOAI = {
  get hotel() { return duongRieng("hotel"); }, get restaurant() { return duongRieng("restaurant"); }, get tours() { return duongRieng("tours"); },
};
export function moNgoai(url: string): void { window.open(url, "_blank", "noopener"); }

/* KS-16q · khách CHƯA đăng nhập vẫn XEM được ba trang riêng: các lệnh GET xem (khách sạn, tour, nhà hàng) đi cửa
   /cong/mo khi không có phiên. Đặt, gửi yêu cầu, đơn của tôi vẫn đi cửa cũ và đòi đăng nhập. */
const CUA_MO: [RegExp, string][] = [
  [/^\/ks-vtd\/(tim\b|\d+(\?|$)|\d+\/danh-gia\b)/, "/mo/ks-vtd/"],
  [/^\/khach\/tour\b/, "/mo/tour"],
  [/^\/dat-ban\/nha-hang\b/, "/mo/nha-hang"],
];
export async function xemCong(path: string): Promise<any> {
  if (phienCong()) return goiCong(path);
  for (const [re, moi] of CUA_MO) {
    if (re.test(path)) {
      const p = moi === "/mo/ks-vtd/" ? path.replace(/^\/ks-vtd\//, moi) : path.replace(/^\/khach\/tour|^\/dat-ban\/nha-hang/, moi);
      return goiCong(p);
    }
  }
  return goiCong(path);
}

/* Lệnh GHI bị 401 khi chưa có phiên → báo khung trang riêng hiện ô «Đăng nhập để tiếp tục». */
export const SU_KIEN_CAN_DANG_NHAP = "vtd-can-dang-nhap";
export function duongDangNhap(): string {
  try { return `/login?ve=${encodeURIComponent(location.pathname + location.search)}`; } catch { return "/login"; }
}
