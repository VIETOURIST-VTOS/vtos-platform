"use client";
/* KS-16f · video trên cổng khách (kh. / dt. / ir.): bấm mới phát, không tự bật tiếng; xem toàn màn hình trên điện thoại. */
import { useState } from "react";

const giay = (s: number) => (s ? `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}` : "");

export function VideoO({ v, ten, cao, nhan }: { v: any; ten: string; cao?: number | string; nhan?: string }) {
  const [phat, setPhat] = useState(false);
  const st = { width: "100%", height: cao ?? "100%", minHeight: 0, borderRadius: 8, display: "block" } as const;
  if (phat) return <video src={v.xem} poster={v.anh || undefined} controls autoPlay playsInline preload="metadata" style={{ ...st, background: "#000", objectFit: "contain" }}
    aria-label={v.tieu_de || `Video ${ten}`} />;
  return <button type="button" onClick={() => setPhat(true)} aria-label={`Phát video${v.tieu_de ? `: ${v.tieu_de}` : ""}`}
    style={{ ...st, position: "relative", padding: 0, border: 0, cursor: "pointer", background: v.anh ? `#16212c url(${v.anh}) center/cover` : "#16212c" }}>
    <b style={{ position: "absolute", left: "50%", top: "50%", transform: "translate(-50%,-50%)", width: 52, height: 52, borderRadius: "50%", background: "rgba(255,255,255,.9)", color: "#16212c", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>▶</b>
    {(nhan || v.la_gioi_thieu) && <span style={{ position: "absolute", left: 8, top: 8, fontSize: 11, fontWeight: 700, background: "#e0b53a", color: "#16212c", padding: "2px 7px", borderRadius: 4 }}>{nhan || "VIDEO"}</span>}
    {v.thoi_luong > 0 && <em style={{ position: "absolute", right: 8, bottom: 8, fontStyle: "normal", fontSize: 12, color: "#fff", background: "rgba(0,0,0,.6)", padding: "1px 7px", borderRadius: 4 }}>{giay(v.thoi_luong)}</em>}
    {v.tieu_de && <span style={{ position: "absolute", left: 8, bottom: 8, right: 60, background: "transparent", textAlign: "left", fontSize: 13, color: "#fff", textShadow: "0 1px 3px rgba(0,0,0,.7)", fontWeight: 600 }}>{v.tieu_de}</span>}
  </button>;
}

export function DaiVideo({ video, ten, bo = 0 }: { video?: any[]; ten: string; bo?: number }) {
  const ds = (video || []).slice(bo);
  if (!ds.length) return null;
  return <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))", gap: 8 }}>
    {ds.map((v) => <div key={v.id} style={{ aspectRatio: "16 / 9", maxWidth: "100%" }}><VideoO v={v} ten={ten} /></div>)}</div>;
}
