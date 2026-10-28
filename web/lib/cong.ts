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
