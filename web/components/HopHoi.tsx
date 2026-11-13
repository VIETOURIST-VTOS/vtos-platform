"use client";
/** TR-10 (13/11/2026) · HỎI LẠI NGAY TRÊN TRANG — thay cho `window.confirm` / `window.prompt`.
 *
 *  VÌ SAO CÓ TỆP NÀY, bằng một chuyện có thật. Ngày 13/11/2026, người đi ghép link web cho 22
 *  tour thiếu ảnh KHÔNG ghép được tour nào: nút ấy mở `window.prompt`, và trình duyệt của trợ lý
 *  trả thẳng «prompt() is not supported». Hộp thoại của trình duyệt KHOÁ CẢ TRANG — không bấm
 *  qua được bằng thao tác tự động, và trên điện thoại thì dán một đường dẫn dài vào nổi.
 *  Quét lại cả giao diện: còn 48 lượt `prompt` và 13 lượt `confirm` trên 27 màn khác.
 *
 *  KHÔNG LÀM ĐƯỢC BẰNG MỘT BẢN VÁ CHUNG. `window.prompt` là hàm ĐỒNG BỘ: nó dừng mã lại và trả
 *  về chuỗi. Một khối hỏi vẽ trên trang thì bất đồng bộ. Không có cách nào nhét cái sau vào chữ
 *  ký của cái trước, nên từng chỗ gọi phải đổi — và đó là lý do tệp này cố ý giữ ĐÚNG ngữ nghĩa
 *  của hai hàm cũ, để mỗi chỗ gọi đổi một dòng chứ không phải viết lại:
 *
 *      if (window.confirm(c))              →   if (await xacNhan(c))
 *      const s = window.prompt(c, mac_dinh) →   const s = await nhap(c, mac_dinh)
 *
 *  `nhap` trả `null` khi người dùng bấm Hủy, y như `prompt`. Nên mọi lệnh kiểm `=== null`,
 *  `|| ""` hay `if (!s) return` ở chỗ gọi cũ vẫn đúng nguyên.
 *
 *  KHÔNG DÙNG CONTEXT, KHÔNG SỬA `Shell.tsx`. Màn hình nào cần thì tự gọi `useHoi()` và tự đặt
 *  `{hop}` vào thân trang. Thêm một dòng mỗi màn, đổi lại `Shell.tsx` là tệp làn R2 hay giữ —
 *  một tệp dùng chung mà nhiều làn cùng sửa là chỗ sinh xung đột, không phải chỗ tiết kiệm.
 */
import { useCallback, useRef, useState } from "react";

type Doi = { loi: string; mac_dinh: string | null; nhan_ok: string; nguy: boolean };

export function useHoi() {
  const [d, setD] = useState<Doi | null>(null);
  const [v, setV] = useState("");
  const tra = useRef<((x: any) => void) | null>(null);

  const dong = useCallback((kq: any) => { tra.current?.(kq); tra.current = null; setD(null); setV(""); }, []);

  /** Hỏi có / không. Trả `true` khi người dùng đồng ý. */
  const xacNhan = useCallback((loi: string, nhan_ok = "Đồng ý", nguy = false) =>
    new Promise<boolean>((ok) => { tra.current = ok; setV(""); setD({ loi, mac_dinh: null, nhan_ok, nguy }); }), []);

  /** Hỏi một chuỗi. Trả chuỗi, hoặc `null` khi bấm Hủy — y hệt `window.prompt`. */
  const nhap = useCallback((loi: string, mac_dinh = "", nhan_ok = "Lưu") =>
    new Promise<string | null>((ok) => { tra.current = ok; setV(mac_dinh); setD({ loi, mac_dinh, nhan_ok, nguy: false }); }), []);

  // Nhiều câu hỏi cũ viết nhiều dòng bằng "\n" (prompt hiện được). Giữ nguyên xuống dòng.
  const hop = d ? (
    <div role="dialog" aria-modal="true" aria-label={d.loi.split("\n")[0]}
         style={{ position: "fixed", inset: 0, zIndex: 300, display: "grid", placeItems: "center",
                  background: "rgba(16,22,32,.45)", padding: 16 }}
         onClick={(e) => { if (e.target === e.currentTarget) dong(d.mac_dinh === null ? false : null); }}>
      <div className="panel" style={{ maxWidth: 520, width: "100%", margin: 0, display: "flex",
                                      flexDirection: "column", gap: 12, maxHeight: "86vh", overflow: "auto" }}>
        <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.5 }}>{d.loi}</div>
        {d.mac_dinh !== null && (
          <input autoFocus value={v} onChange={(e) => setV(e.target.value)}
                 onKeyDown={(e) => { if (e.key === "Enter") dong(v); if (e.key === "Escape") dong(null); }} />
        )}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button type="button" className={`act ${d.nguy ? "red" : "teal"}`}
                  autoFocus={d.mac_dinh === null}
                  onClick={() => dong(d.mac_dinh === null ? true : v)}>{d.nhan_ok}</button>
          <button type="button" className="act grey"
                  onClick={() => dong(d.mac_dinh === null ? false : null)}>Hủy</button>
        </div>
      </div>
    </div>
  ) : null;

  return { xacNhan, nhap, hop };
}
