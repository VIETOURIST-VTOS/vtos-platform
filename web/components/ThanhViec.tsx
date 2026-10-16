"use client";
import { useCallback, useEffect, useState } from "react";

/** THANH VIỆC — hàng ngang đầu màn hình (Chủ tịch duyệt bản xem thử 16/10/2026, bản 5).
 *
 *  Năm luật Chủ tịch chốt, ghi lại ở đây vì đã ba lần đoán sai:
 *    1. Đây KHÔNG phải menu điều hướng. Nó là thanh thao tác CỦA MÀN ĐANG MỞ — không lặp lại thanh
 *       dọc hay menu đã có.
 *    2. Màn hình việc nhảy ra là TOÀN MÀN: không còn thanh dọc bên trái. Thay vào đó là một dòng
 *       vụn đường «VTOS · Đội xe», vì bỏ thanh dọc là bỏ luôn chỗ báo «anh đang ở đâu».
 *    3. Mỗi nút mở MỘT TAB MỚI của trình duyệt — không phải cửa sổ nổi.
 *    4. Hệ quả bắt buộc của (3): trạng thái màn hình phải nằm TRÊN ĐƯỜNG DẪN. Không dựng lại được
 *       từ đường dẫn thì tab mới mở ra trống.
 *    5. Tab cũ không biết tab mới vừa làm gì — nên tab danh sách có dải băng hổ phách
 *       «Đã có thay đổi — bấm để nạp lại» (xem `useDaDoi`).
 *
 *  Không sửa Shell.tsx để giấu thanh dọc: chế độ toàn màn tự gắn một luật CSS khi màn việc còn mở,
 *  và luật ấy tự mất khi người dùng rời màn — Next gỡ thẻ <style> cùng với thành phần. */

export type Viec = {
  nhan: string;
  href: string;
  chinh?: boolean;            // nút chính: tô đậm, đứng đầu
  so?: number | null;         // con số đếm đi kèm (đứng NGAY trên thanh việc, không thành khối riêng)
  len?: boolean;              // «‹ Lên một cấp» — đi trong CÙNG tab, không mở tab mới
  tat?: string;               // có chữ thì nút mờ đi và chữ ấy nói vì sao
};

/* ── TRẠNG THÁI TRÊN ĐƯỜNG DẪN ────────────────────────────────────────────────────────────────
   Đọc từ window chứ không dùng useSearchParams — cùng lẽ với /doi-xe: hook ấy đòi bọc Suspense,
   và một trang hỏng khi dựng vì thiếu bọc là cái giá quá đắt cho việc đọc vài chữ trên địa chỉ. */
export function docUrl(): URLSearchParams {
  try { return new URLSearchParams(window.location.search); } catch { return new URLSearchParams(); }
}

/** Ghi đè vài tham số lên địa chỉ đang mở, KHÔNG thêm một bước vào lịch sử trình duyệt: gõ một ô
 *  ngày mà mỗi chữ thành một lần «Quay lại» là bắt người dùng bấm Quay lại hai mươi lần. Giá trị
 *  rỗng thì gỡ hẳn tham số, để đường dẫn chép đi gửi người khác vẫn ngắn và đọc được. */
export function ghiUrl(p: Record<string, string | number | null | undefined>) {
  try {
    const q = new URLSearchParams(window.location.search);
    for (const [k, v] of Object.entries(p)) {
      if (v === null || v === undefined || v === "") q.delete(k); else q.set(k, String(v));
    }
    const s = q.toString();
    window.history.replaceState(window.history.state, "", window.location.pathname + (s ? "?" + s : ""));
  } catch { /* không ghi được địa chỉ thì màn hình vẫn chạy, chỉ là tab mới không dựng lại được */ }
}

/* ── DẢI BĂNG «ĐÃ CÓ THAY ĐỔI» ────────────────────────────────────────────────────────────────
   Một tab vừa ghi gì (lập lệnh, đổi xe, đóng lệnh…) thì báo sang mọi tab khác của cùng người dùng.
   Hai đường, vì mỗi đường có chỗ không tới: BroadcastChannel không có trên vài trình duyệt cũ, còn
   sự kiện `storage` không có khi localStorage bị chặn. Tab tự báo thì không tự nhận — mã tab ở dưới
   lọc chuyện ấy, vì BroadcastChannel giao cả cho kênh khác mở trong CÙNG tab. */
const KENH = "vtos_lenh_dieu_xe_doi";
const TAB = Math.random().toString(36).slice(2);

export function baoDaDoi(viec: string) {
  const goi = { viec, tab: TAB, luc: Date.now() };
  try { const c = new BroadcastChannel(KENH); c.postMessage(goi); c.close(); } catch { /* trình duyệt cũ */ }
  try { localStorage.setItem(KENH, JSON.stringify(goi)); } catch { /* máy chặn localStorage */ }
}

const gioPhut = (d: Date) => String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");

/** Trả về: việc vừa xảy ra ở tab khác (null nếu chưa có), giờ màn này nạp số lần cuối, và hàm xoá
 *  dải băng — gọi nó ngay sau khi nạp lại xong. */
export function useDaDoi(): { doi: string | null; luc: string; xong: () => void } {
  const [doi, setDoi] = useState<string | null>(null);
  const [luc, setLuc] = useState(() => gioPhut(new Date()));
  useEffect(() => {
    const nghe = (g: any) => { if (g && g.tab !== TAB) setDoi(g.viec || "một tab khác vừa ghi"); };
    let c: BroadcastChannel | null = null;
    try { c = new BroadcastChannel(KENH); c.onmessage = (e) => nghe(e.data); } catch { /* trình duyệt cũ */ }
    const onSt = (e: StorageEvent) => {
      if (e.key !== KENH || !e.newValue) return;
      try { nghe(JSON.parse(e.newValue)); } catch { /* không đọc được thì thôi */ }
    };
    window.addEventListener("storage", onSt);
    return () => { try { c?.close(); } catch { /* đã đóng */ } window.removeEventListener("storage", onSt); };
  }, []);
  const xong = useCallback(() => { setDoi(null); setLuc(gioPhut(new Date())); }, []);
  return { doi, luc, xong };
}

/* `a.act`: globals.css chỉ tô `button.act`. Nút nào phải mở TAB MỚI thì buộc là thẻ <a> (một
   <button> không mở tab mới được bằng chuột giữa hay Ctrl+bấm), nên nó cần cùng hình dáng ấy. */
const CSS = `
.thanh-viec{display:flex;gap:6px;align-items:center;flex-wrap:wrap;padding:8px 10px;margin:0 0 12px;
  background:var(--panel2);border:1px solid var(--line);border-radius:8px}
.thanh-viec .tv-nhan{font-size:calc(11/14*1rem);font-weight:700;letter-spacing:.06em;text-transform:uppercase;
  color:var(--ink2);padding-right:8px;margin-right:2px;border-right:1px solid var(--line)}
.thanh-viec .tv-duong{font-weight:600;color:var(--ink2);padding-right:10px;margin-right:4px;border-right:1px solid var(--line)}
.thanh-viec .tv-duong a{color:inherit}
.thanh-viec a.tv{display:inline-flex;gap:6px;align-items:center;padding:6px 11px;border-radius:7px;
  border:1px solid var(--line);background:var(--panel);color:inherit;text-decoration:none;font-weight:600;white-space:nowrap}
.thanh-viec a.tv:hover{border-color:var(--orange);color:var(--orange)}
.thanh-viec a.tv.chinh{background:var(--vtos-navy);border-color:var(--vtos-navy);color:var(--vtos-text-on-navy,#fff)}
.thanh-viec a.tv.chinh:hover{opacity:.9;color:var(--vtos-text-on-navy,#fff)}
.thanh-viec a.tv.tat{opacity:.5;pointer-events:none}
.thanh-viec .tv-so{font-size:calc(11/14*1rem);padding:1px 7px;border-radius:10px;background:var(--warnbg);color:var(--orange)}
.thanh-viec .tv-mui{font-size:9px;opacity:.6}
a.act{display:inline-block;background:var(--navy2);color:#fff;border:1px solid var(--vtos-navy);border-radius:6px;
  padding:7px 13px;font-size:calc(13/14*1rem);text-decoration:none;white-space:nowrap}
a.act.teal{background:var(--teal);color:var(--vtos-surface);border-color:var(--teal)}
a.act.grey{background:var(--vtos-info-bg);color:var(--vtos-text);border-color:var(--line)}
.tv-bang{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:8px 12px;margin:0 0 12px;border-radius:8px;
  background:var(--warnbg);border:1px solid var(--orange)}
.tv-bang b{color:var(--orange)}
.tv-bang button{margin-left:auto;border:1px solid var(--orange);background:transparent;color:var(--orange);
  font-weight:600;padding:5px 10px;border-radius:6px;cursor:pointer}
`;
/* Toàn màn: giấu thanh dọc và nút ☰ mở nó, và cho vùng nội dung dùng hết bề ngang. */
const CSS_TOAN_MAN = `aside.side{display:none!important}.top .burger{display:none!important}main{max-width:none!important}`;

export default function ThanhViec({ viec, duong, toanMan, daDoi }: {
  viec: Viec[];
  duong: React.ReactNode;           // vụn đường, ví dụ «VTOS · Đội xe · Lệnh điều xe»
  toanMan?: boolean;
  daDoi?: { doi: string | null; luc: string; napLai: () => void };
}) {
  return (<>
    <style>{CSS + (toanMan ? CSS_TOAN_MAN : "")}</style>
    <nav className="thanh-viec" aria-label="Việc làm được ở màn hình này">
      {toanMan ? <span className="tv-duong">{duong}</span> : <span className="tv-nhan">Việc</span>}
      {viec.map((v) => (
        <a key={v.nhan + v.href} href={v.href}
          className={"tv" + (v.chinh ? " chinh" : "") + (v.tat ? " tat" : "")}
          title={v.tat || (v.len ? "" : "Mở trong tab mới")}
          aria-disabled={v.tat ? true : undefined}
          {...(v.len ? {} : { target: "_blank", rel: "noopener" })}>
          {v.nhan}
          {v.so != null && v.so > 0 && <span className="tv-so">{v.so}</span>}
          {!v.len && <span className="tv-mui" aria-hidden="true">↗</span>}
        </a>
      ))}
    </nav>
    {daDoi?.doi && <div className="tv-bang" role="status">
      <span><b>Đã có thay đổi</b> — {daDoi.doi}. Số trên màn này là số lúc {daDoi.luc}.</span>
      <button type="button" onClick={daDoi.napLai}>Bấm để nạp lại</button>
    </div>}
  </>);
}
