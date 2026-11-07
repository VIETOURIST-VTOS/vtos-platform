"use client";
/* KS-16q · Khung chung của ba trang riêng kh.vietourist.vn/hotel, /restaurant, /tours (Chủ tịch duyệt bản xem thử
   01/11/2026). Không có thanh bên của cổng: đầu trang chỉ có logo (về tab Khám phá), ba mục và tài khoản.
   Khách chưa đăng nhập xem tự do; bấm Đặt / Gửi yêu cầu thì lib/cong báo SU_KIEN_CAN_DANG_NHAP → hiện ô đăng nhập,
   đăng nhập xong quay lại đúng trang (login?ve=…). Đã đăng nhập ở kh. thì sang đây vẫn còn phiên (cùng tên miền). */
import { useEffect, useState } from "react";
import { duongDangNhap, duongRieng, goiCong, phienCong, SU_KIEN_CAN_DANG_NHAP, type TrangRieng } from "@/lib/cong";

const MUC: [TrangRieng, string][] = [["tours", "Tour du lịch"], ["hotel", "Khách sạn"], ["restaurant", "Nhà hàng"]];

export function useToiRieng(): { toi: any; xong: boolean } {
  const [toi, setToi] = useState<any>(null);
  const [xong, setXong] = useState(false);
  useEffect(() => {
    if (!phienCong()) { setXong(true); return; }
    goiCong("/toi").then(setToi).catch(() => setToi(null)).finally(() => setXong(true));
  }, []);
  return { toi, xong };
}

export default function KhungRieng({ dang, toi, xong, children }: { dang: TrangRieng; toi: any; xong: boolean; children: React.ReactNode }) {
  const [goc, setGoc] = useState<Record<TrangRieng, string>>({ hotel: "/kham-pha/hotel", restaurant: "/kham-pha/restaurant", tours: "/kham-pha/tours" });
  const [hoi, setHoi] = useState(false);
  useEffect(() => {
    setGoc({ hotel: duongRieng("hotel"), restaurant: duongRieng("restaurant"), tours: duongRieng("tours") });
    const nghe = (e: Event) => { e.preventDefault(); setHoi(true); };   // KS-19e: báo goiCong là ô đăng nhập đã hiện
    window.addEventListener(SU_KIEN_CAN_DANG_NHAP, nghe);
    return () => window.removeEventListener(SU_KIEN_CAN_DANG_NHAP, nghe);
  }, []);
  const ten = (toi?.ho_ten || "").trim().split(/\s+/).pop() || toi?.dien_thoai || "";
  return <>
    <link rel="stylesheet" href="/cong/vtd.css?v=42" />
    <style dangerouslySetInnerHTML={{ __html: CSS }} />
    <div className="kr">
      <header className="kr-top"><div className="kr-in">
        {/* Logo v2 (anh Tuấn duyệt 07/11/2026): logo Vietourist Holdings bản nền tối trên thanh navy #14538D. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <a className="kr-logo" href="/cong" aria-label="Vietourist Holdings — về trang Khám phá"><img src="/thuong-hieu/v2/khoachu-holdings-nen-trong.svg" alt="" width={1107} height={269} /></a>
        <nav className="kr-nav" aria-label="Dịch vụ">{MUC.map(([k, t]) =>
          <a key={k} href={goc[k]} aria-current={dang === k ? "page" : undefined}>{t}</a>)}</nav>
        {!xong ? <span className="kr-acc kr-ghost">…</span>
          : toi ? <a className="kr-acc" href="/cong?tab=bookings"><b>{ten}</b><span>Đơn của tôi</span></a>
          : <a className="kr-acc" href={duongDangNhap()} onClick={(e) => { e.currentTarget.href = duongDangNhap(); }}><b>Đăng nhập</b></a>}
      </div></header>
      <div id="vtd-access" data-role="khach-hang" className="kr-body"><section className="v3-app kr-app" data-portal="khach-hang"><div className="kr-in">{children}</div></section></div>
      <footer className="kr-foot"><div className="kr-in">Vietourist Holdings · Giá hợp đồng của Vietourist · <a href="/cong">Cổng khách hàng</a></div></footer>
    </div>
    {hoi && <div className="kr-modal" role="dialog" aria-modal="true" aria-labelledby="kr-hoi-t" onClick={(e) => { if (e.target === e.currentTarget) setHoi(false); }}>
      <div className="kr-box"><b id="kr-hoi-t">Đăng nhập để tiếp tục</b>
        <p>Đặt dịch vụ và gửi yêu cầu cần tài khoản Vietourist để giữ đơn, thanh toán và tích điểm. Đăng nhập bằng mã gửi qua Zalo hoặc email, không cần mật khẩu. Xong sẽ quay lại đúng trang này.</p>
        <div className="kr-act"><button type="button" className="kr-btn ghost" onClick={() => setHoi(false)}>Xem tiếp</button>
          <a className="kr-btn" href={duongDangNhap()}>Đăng nhập</a></div></div></div>}
  </>;
}

const CSS = `
.kr{min-height:100vh;display:flex;flex-direction:column;background:#f4f7fa;color:#142a43;font-family:"Be Vietnam Pro","Segoe UI",Arial,sans-serif}
.kr-in{max-width:1440px;margin:0 auto;width:100%;box-sizing:border-box;padding-left:max(24px,env(safe-area-inset-left,0px));padding-right:max(24px,env(safe-area-inset-right,0px))}
.kr-top{background:#14538D;color:#fff;position:sticky;top:0;z-index:40;border-bottom:4px solid #0B2545;box-shadow:0 2px 10px rgba(11,37,69,.22)}
.kr-top .kr-in{display:flex;align-items:center;gap:22px;min-height:64px;flex-wrap:wrap}
.kr-logo{display:block;line-height:0;text-decoration:none}
.kr-logo img{display:block;height:38px;width:auto}
.kr-nav{display:flex;gap:4px;flex-wrap:wrap}
.kr-nav a{color:#E3EEF9;text-decoration:none;padding:8px 12px;border-radius:9px;font-weight:600;font-size:14px}
.kr-nav a:hover{color:#fff;background:rgba(255,255,255,.08)}
.kr-nav a[aria-current=page]{color:#fff;background:rgba(255,255,255,.16)}
.kr-acc{margin-left:auto;display:flex;flex-direction:column;align-items:flex-end;color:#14538D;text-decoration:none;font-size:12px;background:#fff;padding:6px 12px;border-radius:9px;line-height:1.3;font-weight:700}
.kr-acc b{font-size:13.5px}.kr-acc span{color:#14538D}
.kr-acc.kr-ghost{background:rgba(255,255,255,.12);color:#fff}
.kr-ghost{opacity:.5}
#vtd-access.kr-body{flex:1;display:flex;flex-direction:column;background:#f3f6fa;background-image:none;border-radius:0;overflow:visible;padding:0;margin:0;min-height:0}
#vtd-access.kr-body>.kr-app{flex:1;margin:0;padding:0;background:#f3f6fa}
.kr-app>.kr-in{padding-block:18px 32px;display:flex;flex-direction:column;gap:14px;min-width:0}
.kr-foot{background:#0B2545;color:#9fb3d1;font-size:12.5px}
.kr-foot .kr-in{padding-block:16px}.kr-foot a{color:#cfdcff}
.kr-modal{position:fixed;inset:0;z-index:100;background:rgba(8,20,38,.55);display:flex;align-items:center;justify-content:center;padding:16px}
.kr-box{background:#fff;color:#142a43;border-radius:14px;max-width:420px;width:100%;padding:22px;display:flex;flex-direction:column;gap:10px;box-shadow:0 20px 50px rgba(0,0,0,.3)}
.kr-box b{font-size:18px}.kr-box p{margin:0;color:#52677f;line-height:1.55;font-size:14px}
.kr-act{display:flex;gap:10px;justify-content:flex-end;flex-wrap:wrap;margin-top:6px}
.kr-btn{background:#14538D;color:#fff;border:0;border-radius:99px;padding:10px 22px;font:inherit;font-weight:700;text-decoration:none;cursor:pointer}
.kr-btn.ghost{background:transparent;color:#14538D;border:1px solid #14538D}
@media (max-width:640px){.kr-top .kr-in{gap:8px;padding-block:8px}.kr-logo img{height:30px}.kr-nav{order:3;width:100%;overflow-x:auto;flex-wrap:nowrap}.kr-nav a{white-space:nowrap;padding:6px 10px;font-size:13px}}
`;
