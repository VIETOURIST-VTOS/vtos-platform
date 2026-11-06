"use client";
import { useEffect, useState, useCallback } from "react";
import { createPortal } from "react-dom";
import { api, type User } from "@/lib/api";

/** CHỌN GIAO DIỆN — nền và cỡ chữ của riêng từng người. TC-67, anh Tuấn giao 18/9/2026.
 *
 *  Năm mục anh giao, và chỗ nào trong tệp này trả lời mục nào:
 *    1. Nền navy mặc định, chữ trắng ngà, thân bài 16px  → MAC_DINH dưới đây + tokens.css
 *    2. Nút "Giao diện" góc trên phải, ba lựa chọn nền, thanh trượt cỡ chữ, trả về mặc định → cả tệp
 *    3. Nhớ THEO TÀI KHOẢN, giữ khi chuyển trang và đăng nhập lại → `luu()` ghi về máy chủ
 *    4. Áp dụng toàn hệ thống → đặt ở thẻ <html>, nên mọi màn hình ăn theo
 *    5. To chữ thì nở hoặc xuống dòng, không cắt → luật ở globals.css, đo 57 khổ
 *
 *  ══ BA CHỖ CẤT, VÀ VÌ SAO PHẢI CẢ BA ═══════════════════════════════════════════════════════
 *
 *  1. THẺ <html>  — nơi màu và cỡ chữ THẬT SỰ có hiệu lực. `data-nen` và `--vtos-co-chu`.
 *  2. localStorage — BẢN CHÉP, chỉ để vẽ ngay lúc mở trang. Kịch bản trong layout.tsx đọc nó
 *     TRƯỚC khi trang vẽ ra; không có nó thì mỗi lần đổi trang màn hình loé nền mặc định một
 *     nhịp rồi mới nháy sang nền của người dùng. Bản chép này vứt đi lúc nào cũng được.
 *  3. MÁY CHỦ     — bản CẤT. Chữ "đăng nhập lại" trong yêu cầu của anh Tuấn chỉ có một cách làm
 *     đúng: localStorage đi theo MÁY, không theo NGƯỜI.
 *
 *  Thứ tự bắt buộc là 1 → 2 → 3: vẽ trước, ghi sau. Chờ máy chủ trả lời rồi mới đổi màu thì người
 *  dùng bấm xong phải đợi nửa giây mới thấy gì, và tưởng nút hỏng.
 *
 *  ══ MÀN HÌNH ĐỔI MÀU KHÔNG PHẢI BẰNG CHỨNG ĐÃ LƯU ═════════════════════════════════════════
 *  Vì vẽ trước ghi sau, nên nếu cửa ghi hỏng thì người dùng vẫn thấy màn hình đổi và vẫn tưởng
 *  đã lưu — cho tới lần đăng nhập sau. Nên có dòng trạng thái dưới đáy bảng nói thẳng ra. Một
 *  cái nút im lặng khi hỏng thì tệ hơn một cái nút báo hỏng.
 */

const KHOA = "vtos_giao_dien";
/** Lối lui khi máy chủ chưa gửi `giao_dien_mac_dinh` (máy chủ bản cũ). Hai con số này cũng nằm ở
 *  models/core.py; máy chủ mới thì màn hình dùng số của máy chủ, không dùng hai số này. */
const MAC_DINH = { nen: "toi", co_chu: 16, mau_nut: "navy" };
const CO_MIN = 14, CO_MAX = 20;

type Chon = { nen: string | null; co_chu: number | null; mau_nut?: string | null };

/** Nền THẬT SỰ vẽ ra: "may" phải hỏi cài đặt máy, hai cái kia là chính nó. */
function nenThat(nen: string): "toi" | "sang" {
  if (nen !== "may") return nen === "sang" ? "sang" : "toi";
  try { return window.matchMedia("(prefers-color-scheme: light)").matches ? "sang" : "toi"; }
  catch { return "toi"; }
}

/** Đặt vào thẻ <html>. Tách riêng vì kịch bản trong layout.tsx làm đúng việc này, và hai nơi phải
 *  làm giống hệt nhau — lệch một chữ là trang loé màu lúc React tiếp quản. */
export function apDung(nen: string, co: number, mau = "navy") {
  const g = document.documentElement;
  g.setAttribute("data-nen", nenThat(nen));
  g.style.setProperty("--vtos-co-chu", co + "px");
  /* KS-NUT · 07/11/2026: màu nút do người dùng chọn — "navy" (phương án A) hoặc "sang" (B). */
  g.setAttribute("data-mau-nut", mau === "sang" ? "sang" : "navy");
}

export default function ChonGiaoDien({ user }: { user: User | null }) {
  const [mo, setMo] = useState(false);
  const [gan, setGan] = useState(false);          // đã gắn vào trang chưa (createPortal cần document)
  const [nen, setNen] = useState(MAC_DINH.nen);
  const [co, setCo] = useState(MAC_DINH.co_chu);
  const [mau, setMau] = useState(MAC_DINH.mau_nut);
  const [trangThai, setTrangThai] = useState<{ chu: string; loi?: boolean } | null>(null);

  const md = { ...MAC_DINH, ...(user?.giao_dien_mac_dinh || {}) };

  useEffect(() => { setGan(true); }, []);

  /* Lấy lựa chọn từ MÁY CHỦ khi biết được người đăng nhập, và đè lên bản chép trong trình duyệt.
     Máy chủ là bản cất, nên máy chủ thắng — đúng cái làm cho lựa chọn theo được người sang máy
     khác. `null` ở một trường nghĩa là người này chưa chọn trường ấy, nên rơi về mặc định. */
  useEffect(() => {
    const g: Chon | undefined = user?.giao_dien;
    const n = g?.nen ?? md.nen;
    const c = g?.co_chu ?? md.co_chu;
    const m = g?.mau_nut ?? md.mau_nut;
    setNen(n); setCo(c); setMau(m);
    apDung(n, c, m);
    try { localStorage.setItem(KHOA, JSON.stringify({ nen: n, co: c, mau: m })); } catch { /* máy chặn thì thôi */ }
  }, [user?.giao_dien, md.nen, md.co_chu, md.mau_nut]);

  /* Người để "Theo máy" mà đổi cài đặt máy giữa chừng thì trang phải đổi theo ngay, không đợi tải
     lại. Chỉ nghe khi đang ở "may" — hai chế độ kia thì cài đặt máy không liên quan. */
  useEffect(() => {
    if (nen !== "may") return;
    let mq: MediaQueryList;
    try { mq = window.matchMedia("(prefers-color-scheme: light)"); } catch { return; }
    const nghe = () => apDung("may", co, mau);
    mq.addEventListener?.("change", nghe);
    return () => mq.removeEventListener?.("change", nghe);
  }, [nen, co, mau]);

  const luu = useCallback(async (n: string, c: number, m: string) => {
    apDung(n, c, m);                                                  // 1. vẽ ngay
    try { localStorage.setItem(KHOA, JSON.stringify({ nen: n, co: c, mau: m })); } catch { }   // 2. bản chép
    setTrangThai({ chu: "Đang lưu…" });
    try {
      await api("/auth/giao-dien", { method: "PUT", json: { nen: n, co_chu: c, mau_nut: m } });   // 3. bản cất
      setTrangThai({ chu: "Đã lưu vào tài khoản của anh/chị." });
    } catch {
      setTrangThai({ chu: "CHƯA lưu được về máy chủ — màn hình đã đổi nhưng lần đăng nhập sau sẽ trở lại như cũ.", loi: true });
    }
  }, []);

  const doiNen = (n: string) => { setNen(n); luu(n, co, mau); };
  const doiMau = (m: string) => { setMau(m); luu(nen, co, m); };
  const doiCo = (c: number) => {
    const x = Math.max(CO_MIN, Math.min(CO_MAX, c));
    setCo(x); apDung(nen, x, mau);
    try { localStorage.setItem(KHOA, JSON.stringify({ nen, co: x, mau })); } catch { }
  };
  /* Thanh trượt ghi về máy chủ khi NHẢ TAY, không phải mỗi lần nhích một nấc: kéo từ 14 sang 20 là
     sáu nấc, tức sáu lần gọi máy chủ cho một lần đổi ý. Màn hình vẫn đổi theo từng nấc (doiCo ở
     trên), chỉ có cửa ghi là đợi. */
  const nhaTay = () => luu(nen, co, mau);

  const traVe = async () => {
    setNen(md.nen); setCo(md.co_chu); setMau(md.mau_nut); apDung(md.nen, md.co_chu, md.mau_nut);
    try { localStorage.removeItem(KHOA); } catch { }
    setTrangThai({ chu: "Đang lưu…" });
    try {
      /* XOÁ chứ không ghi đè bằng giá trị mặc định — xem lý do ở cửa DELETE trong routes.py:
         xoá rồi thì mai kia hệ thống đổi mặc định là người này đi theo mặc định mới. */
      await api("/auth/giao-dien", { method: "DELETE" });
      setTrangThai({ chu: "Đã trả về mặc định." });
    } catch {
      setTrangThai({ chu: "CHƯA lưu được về máy chủ.", loi: true });
    }
  };

  /* Đóng bảng khi bấm ra ngoài hoặc bấm Esc. Không có Esc thì người dùng bàn phím không có cách
     nào ra khỏi bảng ngoài việc bấm chuột. */
  useEffect(() => {
    if (!mo) return;
    const ngoai = (e: MouseEvent) => {
      const t = e.target as HTMLElement;
      if (!t.closest(".gd-bang") && !t.closest(".gd-nut")) setMo(false);
    };
    const phim = (e: KeyboardEvent) => { if (e.key === "Escape") setMo(false); };
    document.addEventListener("click", ngoai);
    document.addEventListener("keydown", phim);
    return () => { document.removeEventListener("click", ngoai); document.removeEventListener("keydown", phim); };
  }, [mo]);

  const NEN: [string, string][] = [["toi", "Navy tối"], ["sang", "Trắng sáng"], ["may", "Theo máy"]];
  /* KS-NUT · anh Tuấn 07/11/2026: "chọn cả A và B cho người dùng tự bấm". Chỉ có tác dụng ở nền
     tối — bản sáng vốn đã dùng navy #14538D cho nút. */
  const MAU: [string, string][] = [["navy", "Navy đậm"], ["sang", "Xanh sáng"]];

  /* BẢNG GẮN THẲNG VÀO <body>, KHÔNG NẰM TRONG `.top` — và đây là lỗi đã mắc thật một lần khi
     dựng bản xem thử, ghi lại kẻo vòng sau gom nó vào cho "gọn": để bảng bên trong thanh ngang
     thì nó ăn luật `.top .bar a,.top .bar button` (chữ trắng, nền trắng mờ). Trên nền tối không
     ai thấy gì lạ; ở NỀN SÁNG thì thành chữ trắng trên thẻ trắng và hai nút biến mất hẳn. */
  const bang = (
    <div className="gd-bang" role="dialog" aria-label="Chọn giao diện" hidden={!mo}>
      <h3>Giao diện của tôi</h3>

      <div>
        <span className="gd-nhan">Nền</span>
        <div className="gd-nen">
          {NEN.map(([ma, ten]) => (
            <button key={ma} type="button" aria-pressed={nen === ma} onClick={() => doiNen(ma)}>{ten}</button>
          ))}
        </div>
      </div>

      <div>
        <span className="gd-nhan">Màu nút</span>
        <div className="gd-nen gd-mau">
          {MAU.map(([ma, ten]) => (
            <button key={ma} type="button" aria-pressed={mau === ma} onClick={() => doiMau(ma)}>
              <i className={"gd-mau-o gd-mau-" + ma} aria-hidden="true" />{ten}</button>
          ))}
        </div>
        {nenThat(nen) === "sang" && <small className="gd-goi-y">Nền trắng sáng luôn dùng nút navy.</small>}
      </div>

      <div>
        <span className="gd-nhan">Cỡ chữ</span>
        <div className="gd-co">
          <button type="button" aria-label="Giảm cỡ chữ" onClick={() => luu(nen, Math.max(CO_MIN, co - 1), mau)}>A−</button>
          <span className="gd-truot-boc">
            <input type="range" min={CO_MIN} max={CO_MAX} step={1} value={co}
              aria-label="Cỡ chữ thân bài" aria-valuetext={`${co} điểm ảnh`}
              onChange={(e) => doiCo(+e.target.value)}
              onMouseUp={nhaTay} onTouchEnd={nhaTay} onKeyUp={nhaTay} onBlur={nhaTay} />
            <span className="gd-vach"><span>14</span><span>16</span><span>18</span><span>20</span></span>
          </span>
          <button type="button" aria-label="Tăng cỡ chữ" onClick={() => luu(nen, Math.min(CO_MAX, co + 1), mau)}>A+</button>
          <b>{co}&nbsp;px</b>
        </div>
      </div>

      {/* Chữ mẫu: người chọn cỡ chữ cần thấy NGAY cỡ ấy đọc ra sao, chứ không phải đóng bảng rồi
          mới biết. Có cả một dòng chữ phụ, vì chữ phụ mới là chỗ khó đọc. */}
      <p className="gd-ve">Chữ mẫu ở cỡ đang chọn — doanh thu 45,06 tỷ.
        <small>Chữ phụ trông như thế này.</small></p>

      <button type="button" className="gd-tra" onClick={traVe}>
        Trả về mặc định ({md.nen === "sang" ? "Trắng sáng" : md.nen === "may" ? "Theo máy" : "Navy tối"} · {md.co_chu} px · nút {md.mau_nut === "sang" ? "xanh sáng" : "navy"})
      </button>

      {trangThai && (
        <span className={"gd-trangthai" + (trangThai.loi ? " loi" : "")} role="status">{trangThai.chu}</span>
      )}
    </div>
  );

  return (
    <>
      <button type="button" className="gd-nut" aria-haspopup="dialog" aria-expanded={mo}
        title="Đổi nền và cỡ chữ" onClick={() => setMo((m) => !m)}>
        <span aria-hidden="true">◐</span><span>Giao diện</span>
      </button>
      {gan && createPortal(bang, document.body)}
    </>
  );
}
