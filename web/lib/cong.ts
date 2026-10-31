/* CG-1 · phiên CỔNG NGOÀI (khách hàng, đối tác, cổ đông). Khoá lưu RIÊNG, không bao giờ là `vtos_token`:
   lib/api.ts không gửi phiên này lên cửa nội bộ nào, và máy chủ cũng không nhận nó ở đó (ký khoá khác). */
export const KHOA_PHIEN_CONG = "vtd_cong_phien";

/* CG-3 (Chủ tịch chốt 28/10/2026): ba tên miền cổng ngoài KHÓA CỨNG — không bao giờ mở VTOS ở đó. Phiên VTOS
   lỡ lưu trên kh./dt./ir. (vd từng đăng nhập nội bộ ở tên miền ấy) bị bỏ qua và xóa; VTOS chỉ mở ở crm. */
export const TEN_MIEN_CONG = ["kh.vietourist.vn", "dt.vietourist.vn", "ir.vietourist.vn"];
export const VTOS_GOC = "https://crm.vietourist.vn";
export function laTenMienCong(): boolean {
  try { return TEN_MIEN_CONG.includes(location.hostname.toLowerCase()); } catch { return false; }
}

export function phienCong(): string { try { return localStorage.getItem(KHOA_PHIEN_CONG) || ""; } catch { return ""; } }
export function luuPhienCong(p: string) { try { localStorage.setItem(KHOA_PHIEN_CONG, p); } catch { /* trình duyệt chặn lưu */ } }
export function xoaPhienCong() { try { localStorage.removeItem(KHOA_PHIEN_CONG); } catch { /* bỏ qua */ } }

export async function goiCong(path: string, json?: any): Promise<any> {
  const headers: Record<string, string> = {};
  const p = phienCong();
  if (p) headers["Authorization"] = `Bearer ${p}`;
  if (json !== undefined) headers["Content-Type"] = "application/json";
  const r = await fetch(`/api/v1/cong${path}`, json === undefined ? { headers } : { method: "POST", headers, body: JSON.stringify(json) });
  const t = await r.text(); let d: any = null; try { d = t ? JSON.parse(t) : null; } catch { d = t; }
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


/** KS-16l/16m (Chủ tịch 01/11/2026): dịch vụ chưa mở đặt trực tuyến trên cổng thì bấm vào mở trang ngoài ở tab mới.
 *  Gọi ĐỒNG BỘ ngay trong sự kiện bấm (không sau await) để trình duyệt không chặn cửa sổ mới. */
export const LINK_NGOAI = { hotel: "https://www.vietourist.vn/hotel", restaurant: "https://www.vietourist.vn/restaurant", tours: "https://www.vietourist.vn/tours" } as const;
export function moNgoai(url: string): void { window.open(url, "_blank", "noopener,noreferrer"); }
