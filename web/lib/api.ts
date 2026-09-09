"use client";
/** Gọi API VTOS – token lưu localStorage, lỗi cổng chặn (422) trả về {gate, message}. */
export type ApiError = { status: number; gate?: string; message: string };

const TOKEN_KEY = "vtos_token";
const USER_KEY = "vtos_user";

export type User = { id: number; username: string; full_name: string; role: string; role_name: string; department: string; hidden_menus?: string[]; can_see_cost?: boolean; read_only?: boolean; can_create_request?: boolean; can_create_booking?: boolean; must_change_password?: boolean; hr_tabs?: string[]; company_id?: number | null; ngoai_bien_che?: boolean };

export function getToken() { try { return localStorage.getItem(TOKEN_KEY); } catch { return null; } }
export function getUser(): User | null { try { const s = localStorage.getItem(USER_KEY); return s ? JSON.parse(s) : null; } catch { return null; } }
export function setSession(token: string, user: User) { localStorage.setItem(TOKEN_KEY, token); localStorage.setItem(USER_KEY, JSON.stringify(user)); }
export function clearSession() { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USER_KEY); }

export async function api<T = any>(path: string, init: RequestInit & { json?: any } = {}): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers as any) };
  const tok = getToken();
  if (tok) headers["Authorization"] = `Bearer ${tok}`;
  let body = init.body;
  if (init.json !== undefined) { headers["Content-Type"] = "application/json"; body = JSON.stringify(init.json); }
  const r = await fetch(`/api/v1${path}`, { ...init, headers, body });
  if (r.status === 401) { clearSession(); if (typeof window !== "undefined" && !location.pathname.startsWith("/login")) location.href = "/login"; }
  const text = await r.text();
  let data: any = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!r.ok) {
    const d = data?.detail;
    const err: ApiError = typeof d === "object" && d ? { status: r.status, gate: d.gate, message: d.message } : { status: r.status, message: typeof d === "string" ? d : "Lỗi " + r.status };
    throw err;
  }
  return data as T;
}

export async function login(username: string, password: string) {
  const fd = new URLSearchParams({ username, password });
  const r = await fetch("/api/v1/auth/login", { method: "POST", body: fd, headers: { "Content-Type": "application/x-www-form-urlencoded" } });
  const data = await r.json();
  if (!r.ok) throw { status: r.status, message: data?.detail || "Đăng nhập thất bại" } as ApiError;
  setSession(data.access_token, data.user);
  return data.user as User;
}

export const vnd = (x: number | null | undefined) => Math.round(x || 0).toLocaleString("vi-VN");
export const pct = (x: number | null | undefined) => ((x || 0) * 100).toFixed(1).replace(".", ",") + "%";
export const fmtD = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "");
export const fmtDT = (s?: string | null) => (s ? fmtD(s) + " " + s.slice(11, 16) : "");

/** Đọc một ô nhập TIỀN: ô trống trả về rỗng, KHÔNG trả về 0.
 *
 * `Number("")` bằng 0 chứ không phải NaN – đó là lý do mọi ô tiền để trống trong VTOS xưa nay đều
 * được ghi xuống thành số 0, và vì sao không ai phân biệt được "chưa nhập" với "bằng 0". Đợt K2 đã
 * mở đường ở tầng dưới (91 cột tiền nhận rỗng); hàm này là cánh cửa cuối cùng, chỗ người dùng gõ.
 *
 * Dùng cho TIỀN và các con số người nhập có quyền để trống. KHÔNG dùng cho số bắt buộc phải có
 * (số tiền của một phiếu thu chẳng hạn) – ở đó ô trống là lỗi nhập liệu, phải chặn ngay trên biểu
 * chứ không lặng lẽ hoá rỗng.
 *
 * Số 0 do người gõ vẫn là 0. Phân biệt được hai thứ mới là mục đích, không phải cấm số 0.
 */
export const soTien = (v: unknown): number | null => {
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  if (s === "") return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
};
