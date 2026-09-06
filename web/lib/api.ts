"use client";
/** Gọi API VTOS – token lưu localStorage, lỗi cổng chặn (422) trả về {gate, message}. */
export type ApiError = { status: number; gate?: string; message: string };

const TOKEN_KEY = "vtos_token";
const USER_KEY = "vtos_user";

export type User = { id: number; username: string; full_name: string; role: string; role_name: string; department: string; hidden_menus?: string[]; can_see_cost?: boolean; read_only?: boolean };

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
