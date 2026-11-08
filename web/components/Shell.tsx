"use client";
import { useEffect, useState, useRef, createContext, useContext, useCallback, useMemo } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { getUser, clearSession, type User } from "@/lib/api";
import { laTenMienCong, phienCong } from "@/lib/cong";
import ChonDonVi from "@/components/ChonDonVi";
import ChonGiaoDien from "@/components/ChonGiaoDien";
import { duongCuaPhong } from "@/lib/duong_phong";

/** Mục v1.1 §I.2 có tên nhưng CHƯA có trang. TC-2 yêu cầu ẩn chức năng "sắp có", nên chúng không vào
 *  menu – nhưng cũng không bị xoá khỏi mã, vì lộ trình còn nợ phải có chỗ đọc được. Phép thử test_menu
 *  đọc chính danh sách này để canh rằng một mục đã dựng xong thì phải RỜI khỏi đây và có đường dẫn
 *  thật – không được ở cả hai trạng thái cùng lúc.
 *
 *  Đây KHÔNG phải CHUA_CO_TRANG của cổng P11: cổng ấy nói về mục đã KHAI QUYỀN mà chưa có trang, và
 *  đòi ngày dự kiến. Sáu mục dưới đây chưa khai quyền, chưa có trang, nên chúng không thuộc cổng đó. */
export const CHUA_XAY = [
  "Việc của tôi", "Chỉ đạo & giao việc", "Ngân sách", "Phòng ban",
  "Hiệu quả đơn vị", "Hồ sơ pháp lý & thuế", "Văn bản", "Nhật ký kỹ thuật",
];

type Item = [string, string];
type Section = { label: string; items: Item[] };
type Block = Item | Section;
/** `icon` phục vụ trạng thái THU của menu (v1.1 §I.2: rộng 224–240px, thu còn 56–64px). Khi thu thì
 *  chỉ còn biểu tượng, và §I.2 đòi "biểu tượng phải có chú thích" – nhãn nhóm đi vào title và
 *  aria-label chứ không mất. Một hàng biểu tượng không chú thích là một hàng phải đoán. */
/** `href` – nơi thanh phân hệ dẫn tới khi BẤM (anh Tuấn chốt phương án B, 13/9/2026). Bảy nhóm
 *  nghiệp vụ dẫn tới TRANG PHÂN HỆ /phan-he/<khoa>: một trang vẽ đủ cây chức năng theo bản vẽ v1.3,
 *  mục nào đã có trang thì bấm đi được, mục nào còn nợ thì ghi rõ "chưa dựng". Riêng Tổng quan dẫn
 *  thẳng "/" vì bảng điều hành CHÍNH LÀ màn hình của phân hệ ấy – dựng thêm một trang mục lục cho
 *  nó chỉ tổ thêm một cú bấm. */
/** TC-69 · `label_ngan` — CHỮ VẼ RA trên thanh dọc khi nó khác với TÊN THẬT của phân hệ.
 *
 *  Anh Tuấn 18/9/2026: thu hẹp thanh dọc, và đổi nhãn menu "Nhân sự – Hành chính" thành "HC – NS".
 *
 *  Vì sao là một trường RIÊNG chứ không sửa thẳng `label`: `label` là TÊN của phân hệ — nó đi vào
 *  `title`, `aria-label`, và là thứ phép thử canh danh sách tám nhóm đọc. Rút gọn nó là rút gọn
 *  tên phân hệ trong cả hệ thống, trong khi việc anh Tuấn giao chỉ là chữ VẼ RA cho vừa thanh.
 *
 *  Nhờ tách hai trường, câu trả lời không mất: rê chuột lên "HC – NS" vẫn đọc được "Nhân sự –
 *  Hành chính", và máy đọc màn hình vẫn đọc tên đầy đủ. Đúng luật của kho — bớt chữ thì thứ nó nói
 *  phải còn ở đâu đó. */
/** TC-70 · 18/9/2026 — `phans`: nhóm này KHÔNG tự dẫn đi đâu mà xổ ra mấy phân hệ con.
 *
 *  ĐÂY LÀ CHỖ ĐẢO LẠI phương án B anh Tuấn chốt 13/9/2026 ("bấm là đi, không phải bung"). Lý do
 *  ngày 13/9 vẫn đúng và vẫn còn nguyên giá trị: một thanh không thể vừa đi vừa bung, nên PHẢI chọn
 *  một. Với sáu nhóm còn lại, chọn "đi" – giữ nguyên. Với Kinh doanh và Điều hành thì anh Tuấn chốt
 *  ngày 18/9 rằng chúng không còn là MỘT phòng nữa: Kinh doanh là hai phòng (lẻ và đoàn), Điều hành
 *  là ba đơn vị (tour, xe, hướng dẫn viên – xe đã sang pháp nhân Vietrip). Một thanh đại diện cho
 *  nhiều phòng thì "bấm là đi" đi đâu cũng sai một phòng, nên ở hai chỗ ấy chọn "bung".
 *
 *  `href` vì thế thành TUỲ CHỌN. Nhóm có `phans` thì vẽ bằng <button> chứ không phải <Link>: một
 *  thẻ <a> không dẫn đi đâu là nói dối với bàn phím và với trình đọc màn hình, cả hai đều báo cho
 *  người dùng rằng đây là một đường dẫn. */
/** Đích của một phân hệ con KHÔNG khai ở đây mà hỏi `duongCuaPhong` (lib/duong_phong.ts) — một
 *  bảng, một chỗ. KS-54 từng cho `PhanCon` một trường `href` riêng để "Điều hành xe" nhảy ra
 *  /xe trong khi /phan-he/dhxe còn sống; 09/11/2026 anh Tuấn bỏ hẳn trang cũ nên `dhxe` vào
 *  thẳng bảng ấy, và trường riêng đã gỡ. Hai lối tới cùng một đích là hai chỗ để sửa nhầm. */
type PhanCon = { khoa: string; label: string };
type Group = { key: string; label: string; label_ngan?: string; icon: string; blocks: Block[];
               href?: string; phans?: PhanCon[] };

/** Biểu tượng vẽ bằng NÉT (24×24, stroke 1.7, không tô đặc) thay cho emoji. Ba lý do, không phải
 *  chuyện thẩm mỹ: emoji mỗi máy vẽ một kiểu – Windows, máy Mac và điện thoại ra ba hình khác nhau
 *  nên không có một bộ nhận diện chung; emoji không đổi màu theo nền nên trên nền xanh đậm nó vẫn
 *  là mảng màu sặc sỡ; và emoji không co giãn theo cỡ chữ của người dùng. Nét dùng currentColor nên
 *  nhận đúng màu của hàng đang chọn.
 *
 *  `icon` VẪN LÀ MỘT CHUỖI – đây là khoá tra bảng dưới đây, không phải ký tự để in ra. Phép thử
 *  test_menu đọc trường này và đòi TÁM nhóm đều có, nên khoá nào không có hình sẽ rơi về hình
 *  mặc định chứ không để trống một ô. */
const HINH: Record<string, string> = {
  // Tổng quan – bốn ô bảng điều hành
  tongquan: "M4 4h7v7H4zM13 4h7v5h-7zM13 11h7v9h-7zM4 13h7v7H4z",
  // Marketing & PR – loa tay (thêm 12/9/2026 khi menu lên tám nhóm)
  marketing: "M3.5 9.2 16 5v14L3.5 14.8zM6.2 15.6 7.2 20.5h3l-1-4.9M19.5 8.5 21.5 6.5M20 12h2.5",
  // Kinh doanh – hai người
  khachhang: "M9 11a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM2.5 20a6.5 6.5 0 0113 0M17 11.5a3 3 0 100-6M18 20a6 6 0 00-2-4.5",
  // Vận hành – la bàn
  vanhanh: "M12 21a9 9 0 100-18 9 9 0 000 18zM15.5 8.5l-2 5-5 2 2-5 5-2z",
  // Tài chính – két tiền
  taichinh: "M3 7.5A2.5 2.5 0 015.5 5h13A2.5 2.5 0 0121 7.5v9a2.5 2.5 0 01-2.5 2.5h-13A2.5 2.5 0 013 16.5zM16 12h2.5M3 9.5h18",
  // Nhân sự – Hành chính – thẻ nhân viên
  nhansu: "M3 5.5h18v13H3zM9 12a2 2 0 100-4 2 2 0 000 4zM6 16a3.2 3.2 0 016 0M14 10h4M14 13.5h4",
  // Báo cáo – cột biểu đồ
  baocao: "M4 20V4M4 20h16M8 20v-6M12.5 20V9M17 20v-9",
  // Quản trị – bánh răng
  quantri: "M12 15a3 3 0 100-6 3 3 0 000 6zM19.4 14a1.7 1.7 0 00.34 1.87l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.7 1.7 0 00-1.87-.34 1.7 1.7 0 00-1.03 1.56V20a2 2 0 01-4 0v-.1A1.7 1.7 0 009 18.3a1.7 1.7 0 00-1.87.34l-.06.06a2 2 0 11-2.83-2.83l.06-.06A1.7 1.7 0 004.64 14a1.7 1.7 0 00-1.56-1.03H3a2 2 0 010-4h.1A1.7 1.7 0 004.64 8a1.7 1.7 0 00-.34-1.87l-.06-.06a2 2 0 112.83-2.83l.06.06A1.7 1.7 0 009 3.64 1.7 1.7 0 0010.03 2.08V2a2 2 0 014 0v.1A1.7 1.7 0 0015 3.64a1.7 1.7 0 001.87-.34l.06-.06a2 2 0 112.83 2.83l-.06.06A1.7 1.7 0 0019.36 8v.03A1.7 1.7 0 0020.92 9H21a2 2 0 010 4h-.1a1.7 1.7 0 00-1.5 1z",
};
const MAC_DINH = "M5 5h14v14H5z";

/** aria-hidden: nhãn nhóm đã nằm ở title và aria-label của cái nút bọc ngoài. Nếu hình cũng tự xưng
 *  tên thì máy đọc màn hình đọc hai lần một mục. */
function Hinh({ ten }: { ten: string }) {
  return (
    <svg className="bt-hinh" viewBox="0 0 24 24" width={20} height={20} aria-hidden="true"
      fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round">
      <path d={HINH[ten] || MAC_DINH} />
    </svg>
  );
}

/** Biểu tượng của THANH NGANG. Tách khỏi bảng HINH ở trên vì bảng ấy là biểu tượng các NHÓM MENU và
 *  phép thử test_menu đếm số biểu tượng phải khớp số nhóm – trộn hình của thanh ngang vào là làm
 *  hỏng phép đếm. Cùng quy cách nét: 24×24, stroke 1.7, currentColor. */
const HINH_BAR: Record<string, string> = {
  tim: "M11 17.5a6.5 6.5 0 100-13 6.5 6.5 0 000 13zM20 20l-3.6-3.6",
  viec: "M7 4.5h10A1.5 1.5 0 0118.5 6v13A1.5 1.5 0 0117 20.5H7A1.5 1.5 0 015.5 19V6A1.5 1.5 0 017 4.5zM9.5 4.5V3.8a1.3 1.3 0 011.3-1.3h2.4a1.3 1.3 0 011.3 1.3v.7M9 12.5l2 2 4-4",
  duyet: "M12 21a9 9 0 100-18 9 9 0 000 18zM8.5 12.2l2.4 2.4 4.6-4.8",
  chuong: "M18 8.8a6 6 0 10-12 0c0 5.2-2 6.7-2 6.7h16s-2-1.5-2-6.7M13.7 19a2 2 0 01-3.4 0",
  ai: "M12 3l1.7 4.6L18 9.3l-4.3 1.7L12 15.6l-1.7-4.6L6 9.3l4.3-1.7zM18.5 15l.8 2.1 2.2.8-2.2.8-.8 2.1-.8-2.1-2.2-.8 2.2-.8z",
};

function Bt({ d }: { d: string }) {
  return (
    <svg className="bar-hinh" viewBox="0 0 24 24" width={18} height={18} aria-hidden="true"
      fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round">
      <path d={HINH_BAR[d] || MAC_DINH} />
    </svg>
  );
}

/** Chữ đầu cho ô tròn đại diện. Lấy chữ đầu của HAI từ cuối, vì tên người Việt đọc theo tên chứ
 *  không theo họ: "Trần Anh Tuấn" ra "AT" chứ không phải "TA". Không có tên thì trả về rỗng và ô
 *  tròn vẫn giữ chỗ, không nhảy bố cục khi hồ sơ tải xong. */
function chuDau(ten?: string | null): string {
  const tu = (ten || "").trim().split(/\s+/).filter(Boolean);
  if (tu.length === 0) return "";
  return tu.slice(-2).map((t) => t[0]).join("").toUpperCase();
}

/** Ô tài khoản: TÊN rồi CHỨC DANH, và chức danh chỉ in MỘT LẦN (bản vẽ V1.4 nêu đích danh, sửa
 *  13/9/2026).
 *
 *  Bản chạy thật đang hiện "Chủ tịch HĐQT · Chủ tịch HĐQT". Đây KHÔNG phải lỗi vẽ hai lần: tài
 *  khoản ấy chưa được đặt họ tên thật, nên `full_name` đang chính là chức danh, và câu
 *  `{full_name} · {role_name}` in ra hai bản của cùng một chuỗi. Sửa ở máy chủ là đặt tên thật cho
 *  tài khoản; sửa ở đây là không in trùng khi hai trường bằng nhau – cần cả hai, vì tài khoản chưa
 *  có tên thật sẽ còn xuất hiện nữa.
 *
 *  Không tự đặt tên thay người dùng (bản vẽ ghi rõ). Không có tên thì hiện chức danh, thế thôi. */
function tenVaChuc(u?: { full_name?: string | null; role_name?: string | null } | null) {
  const ten = (u?.full_name || "").trim();
  const chuc = (u?.role_name || "").trim();
  if (!ten) return <b>{chuc}</b>;
  if (!chuc || ten.toLowerCase() === chuc.toLowerCase()) return <b>{ten}</b>;
  return <>{ten} · <b>{chuc}</b></>;
}

/** Ngưỡng NGĂN KÉO của thanh dọc – phải TRÙNG `@media (max-width:900px)` trong globals.css, nơi
 *  `aside.side.hide{display:none}` biến thanh dọc thành ngăn kéo mở bằng nút ☰. Dưới ngưỡng ấy bảng
 *  xổ ra KHÔNG được bay sang phải: màn hình rộng 390px mà thanh dọc đã chiếm gần hết, bay sang phải
 *  là bay hẳn ra ngoài màn hình – em đo trong mockup 18/9: bảng nằm ở 388px trên màn 390px. */
const NGUONG_NGAN_KEO = 900;

/** NHÓM XỔ RA – TC-70 · 18/9/2026.
 *
 *  BA CHỖ PHẢI LÀM ĐÚNG, không phải chuyện trang trí:
 *
 *  1. <button> CHỨ KHÔNG PHẢI <a>. Nhóm này không dẫn đi đâu. Một thẻ <a> không có đích là nói dối
 *     với bàn phím (Enter không đi đâu cả) và với trình đọc màn hình (nó xướng "liên kết").
 *     `aria-haspopup` + `aria-expanded` là cách nói thật: đây là nút mở một bảng.
 *
 *  2. BẢNG PHẢI RA NGOÀI THANH DỌC. `aside.side` có `overflow-y:auto`; đặt bảng bên trong nó thì
 *     phần thò ra bị CẮT MẤT, không phải bị che – người dùng không cuộn tới được. Nên bảng đi qua
 *     `createPortal` ra thẳng <body> và định vị `fixed`, đúng cách đã dùng cho bảng Giao diện.
 *     Trên ngăn kéo (≤900px) thì ngược lại: vẽ TẠI CHỖ, không cổng, không fixed.
 *
 *  3. NEO THEO MÉP PHẢI CỦA THANH DỌC, không theo mép nút. Nút thụt vào 8px (margin 0 8px), neo
 *     theo nút thì bảng đè lên viền thanh dọc 3px. Em đo thấy trong mockup rồi mới sửa. */
function NhomXo({ g, thu, dangO, dongThanhDoc }:
                { g: Group; thu: boolean; dangO: boolean; dongThanhDoc: () => void }) {
  const [mo, datMo] = useState(false);
  const [toaDo, datToaDo] = useState<{ left: number; top: number } | null>(null);
  const [taiCho, datTaiCho] = useState(false);   // true = ngăn kéo, vẽ tại chỗ
  const boc = useRef<HTMLDivElement | null>(null);
  const bang = useRef<HTMLDivElement | null>(null);
  const hen = useRef<ReturnType<typeof setTimeout> | null>(null);

  /** Chế độ tại chỗ đọc từ CHÍNH cùng một ngưỡng với CSS. Đọc một lần lúc gắn rồi thôi là sai:
   *  người dùng xoay điện thoại hoặc kéo cửa sổ hẹp lại thì chế độ phải đổi theo. */
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mq = window.matchMedia(`(max-width:${NGUONG_NGAN_KEO}px)`);
    const doi = () => { datTaiCho(mq.matches); datMo(false); };
    doi();
    mq.addEventListener("change", doi);
    return () => mq.removeEventListener("change", doi);
  }, []);

  const dinhVi = useCallback(() => {
    if (taiCho || !boc.current) return;
    const nut = boc.current.getBoundingClientRect();
    const thanh = boc.current.closest("aside.side")?.getBoundingClientRect();
    const cao = bang.current?.offsetHeight ?? 0;
    const left = Math.round((thanh?.right ?? nut.right) + 6);
    // Không để bảng tràn đáy màn hình. Đẩy LÊN chứ không cắt: cắt thì mục cuối biến mất mà không
    // có gì báo, còn đẩy lên thì cả bảng vẫn đọc được.
    const top = cao && nut.top + cao > window.innerHeight - 12
      ? Math.max(8, window.innerHeight - 12 - cao)
      : Math.round(nut.top);
    datToaDo({ left, top });
  }, [taiCho]);

  useEffect(() => {
    if (!mo || taiCho) return;
    dinhVi();
    const lai = () => dinhVi();
    window.addEventListener("resize", lai);
    window.addEventListener("scroll", lai, true);   // true: bắt cả cuộn TRONG thanh dọc
    return () => { window.removeEventListener("resize", lai); window.removeEventListener("scroll", lai, true); };
  }, [mo, taiCho, dinhVi]);

  /** Bấm ra ngoài thì đóng. Nghe ở giai đoạn BẮT (capture) để một cú bấm vào nhóm xổ ra khác cũng
   *  đóng được cái này trước khi cái kia mở. */
  useEffect(() => {
    if (!mo) return;
    const ngoai = (e: MouseEvent) => {
      const t = e.target as Node;
      if (boc.current?.contains(t) || bang.current?.contains(t)) return;
      datMo(false);
    };
    document.addEventListener("mousedown", ngoai, true);
    return () => document.removeEventListener("mousedown", ngoai, true);
  }, [mo]);

  const huyHen = () => { if (hen.current) { clearTimeout(hen.current); hen.current = null; } };
  // Rê chuột: chỉ trên máy có chuột THẬT. `hover: none` là màn cảm ứng – ở đó trình duyệt vẫn bắn
  // mouseenter giả sau cú chạm, và bảng sẽ tự mở rồi tự đóng loạn lên.
  const coChuot = () => typeof window !== "undefined" && window.matchMedia
    && window.matchMedia("(hover: hover)").matches;
  // MỞ CHẬM 140ms – đây là câu trả lời cho đúng lý do đã khiến anh Tuấn bỏ lối rê chuột ngày
  // 13/9/2026: "đưa chuột ngang qua thanh dọc để tới chỗ khác là bảng bật ra chắn đường". Chuột đi
  // lướt qua thì trong 140ms nó đã sang chỗ khác và bảng không kịp mở; chuột DỪNG LẠI ở đây mới là
  // ý định vào nhóm. Bỏ độ trễ này là dựng lại đúng cái phiền đã khiến luật cũ bị bỏ.
  const vao = () => {
    if (taiCho || !coChuot()) return;
    huyHen();
    hen.current = setTimeout(() => datMo(true), 140);
  };
  // Đóng CHẬM 220ms: chuột phải đi qua khoảng trống 6px giữa thanh dọc và bảng. Đóng ngay thì bảng
  // biến mất giữa đường và không ai bấm được vào mục nào.
  const ra = () => { if (!taiCho && coChuot()) { huyHen(); hen.current = setTimeout(() => datMo(false), 220); } };
  useEffect(() => huyHen, []);

  const nhan = g.label_ngan || g.label;
  const noiDung = (
    <div ref={bang} className="xo-bang" role="menu" aria-label={g.label}
      style={taiCho ? undefined : { left: toaDo?.left ?? -9999, top: toaDo?.top ?? -9999 }}
      onMouseEnter={vao} onMouseLeave={ra}>
      {/* TC-72 · 19/9/2026 — BỎ DÒNG TIÊU ĐỀ trong bảng xổ ra. Anh Tuấn: "em xoá bỏ chữ kinh
          doanh và chữ điều hành, không lặp lại."
          Tên nhóm đã hiện ở BA chỗ cùng lúc: trên chính cái nút bên cạnh, trong tooltip khi rê
          chuột, và ở dòng tiêu đề này. Ba lần cho một thông tin thì hai lần sau chỉ làm mắt
          người đọc phải lọc.
          THÔNG TIN KHÔNG MẤT: `aria-label={g.label}` ngay trên thẻ này vẫn xướng đúng tên nhóm
          cho trình đọc màn hình — bỏ chữ VẼ RA chứ không bỏ chữ NÓI RA. Đây cùng một nếp với
          TC-69 lúc rút "Nhân sự – Hành chính" thành "HC – NS". */}
      {/* ĐỢT PH-1 · 09/11/2026 — phòng nào đã có đường dẫn riêng thì chip con trỏ thẳng
          vào đó: `/fit`, `/mice`, `/op`, `/guide`. Hỏi `duongCuaPhong` chứ không ghép
          chuỗi `/phan-he/` tại chỗ — phòng chưa dời vẫn về chỗ cũ, và ngày dời thêm một
          phòng thì chỉ sửa bảng trong `lib/duong_phong.ts`, không ai phải nhớ dòng này. */}
      {g.phans!.map((p) => (
        <Link key={p.khoa} href={duongCuaPhong(p.khoa)} className="xo-muc" role="menuitem"
          onClick={() => { datMo(false); dongThanhDoc(); }}>{p.label}</Link>
      ))}
    </div>
  );

  return (
    <div ref={boc} className={"nhom-xo" + (mo ? " mo" : "")} onMouseEnter={vao} onMouseLeave={ra}>
      <button type="button" className={"grp grp-xo" + (dangO ? " on" : "")}
        title={g.label} aria-label={g.label} aria-haspopup="menu" aria-expanded={mo}
        onClick={() => { huyHen(); datMo((m) => !m); }}
        onKeyDown={(e) => {
          if (e.key === "Escape" && mo) { e.stopPropagation(); datMo(false); }
          if (e.key === "ArrowRight" && !mo) datMo(true);
        }}>
        {thu ? <span className="bt"><Hinh ten={g.icon} /></span>
             : <><Hinh ten={g.icon} /><span className="grp-ten">{nhan}</span>
                 <span className="grp-xo-dau" aria-hidden="true">›</span></>}
      </button>
      {/* Ở chế độ tại chỗ thì KHÔNG dùng cổng: bảng phải nằm đúng trong luồng của ngăn kéo để đẩy
          các nhóm dưới xuống, chứ không phủ lên chúng. */}
      {mo && (taiCho ? noiDung
        : typeof document !== "undefined" ? createPortal(noiDung, document.body) : null)}
    </div>
  );
}

/** TÁM NHÓM – tên chính thức theo bản vẽ giao diện navy V1.2, anh Tuấn chốt 12/9/2026.
 *  Tối đa hai cấp, bỏ số thứ tự, nhóm Quản trị đặt cuối, ẩn mục chưa có trang.
 *
 *  LỊCH SỬ HAI LẦN ĐỔI TRONG NGÀY 12/9, ghi cả hai vì tài liệu gửi IT phải đính chính theo:
 *    · Sáng: ĐỔI TÊN bảy nhóm theo bản vẽ, giữ nguyên thứ tự và mọi đường dẫn. Khách hàng & Kinh
 *      doanh -> Kinh doanh · Vận hành -> Điều hành (bỏ chữ "du lịch") · Tài chính -> Tài chính – Kế
 *      toán · Nhân sự & Nội bộ -> Nhân sự – Hành chính · Báo cáo -> Báo cáo – Phân tích · Quản trị
 *      -> Quản trị hệ thống.
 *    · Chiều: LÊN TÁM NHÓM. Thêm "Marketing & PR" đứng thứ hai, và Nhân sự – Hành chính đổi lên
 *      TRƯỚC Tài chính – Kế toán, đúng thứ tự bản vẽ navy V1.2.
 *
 *  DẤU NỐI: bản vẽ navy viết "Nhân sự & Hành chính" và "Tài chính & Kế toán" bằng dấu &, nhưng ở đây
 *  giữ gạch ngang – (en dash) vì đó là dấu anh Tuấn chốt riêng buổi sáng và đã nằm trong tài liệu
 *  v1.2 gửi IT. Riêng "Marketing & PR" dùng & vì PR là chữ viết tắt, "Marketing – PR" đọc sai nghĩa.
 *  Đổi lại toàn bộ sang & là một dòng, nhưng phải đính chính tài liệu lần nữa.
 *
 *  NGUYÊN TẮC XẾP: v1.1 liệt kê mục con theo CHỨC NĂNG NGHIỆP VỤ, không theo đường dẫn. Ở đây chỉ
 *  GOM 53 đường dẫn đang có trong MENU_ROLES vào tám nhóm ấy – KHÔNG thêm mục mới. Khai một mục trỏ
 *  tới trang chưa tồn tại là cổng P11 đỏ ngay, và người dùng thì gặp một đường dẫn hỏng.
 *  Nhóm Marketing & PR vì thế KHÔNG có mục nào mới: nó nhận lại năm mục vốn nằm trong Kinh doanh.
 *
 *  `blocks` giữ ĐÚNG THỨ TỰ của v1.1: một phần tử là một mục (mảng hai phần) hoặc một mục con có
 *  nhóm nhỏ bên trong (đối tượng có label + items). Nếu tách làm hai trường items và sections thì
 *  phải vẽ hết mục rồi mới tới nhóm nhỏ, và thứ tự trong tài liệu không giữ được.
 *
 *  Ba chỗ em tự quyết vì v1.1 không nói, đã ghi rõ để anh lật lại được:
 *    · "Cảnh báo nghiệp vụ", "Ngoại lệ cần xử lý", "Kiểm soát (robot)" vào Quản trị. Chúng là ba
 *      màn hình giám sát, không thuộc sáu mục con v1.1 nêu cho nhóm ấy.
 *    · "Quyết toán" của nhóm Tài chính hiểu là KẾT SỔ KỲ. Quyết toán tour dùng chung trang /tours
 *      với Chuyến, nên để một lối vào ở Vận hành thay vì hai mục cùng trỏ một trang.
 *    · "Khách hàng" và "Nguồn khách" của v1.1 cùng trỏ /leads; gộp làm một mục để không có hai nhãn
 *      khác nhau mở ra đúng một màn hình.
 */
export const GROUPS: Group[] = [
  // "Việc của tôi" và "Chỉ đạo & giao việc" chưa có trang (xem CHUA_XAY). "Việc của tôi" vẫn tới
  // được bằng neo trên thanh ngang, nên không mất lối đi.
  // KHÔNG CÓ mục con (anh Tuấn chốt 12/9/2026: "bỏ Bảng điều hành, không hiện lên ở thanh dọc này").
  // Mục con cũ trỏ đúng trang mà chính thanh "Tổng quan" đang đại diện, nên nó chỉ là một dòng lặp
  // lại tên nhóm. Đường đi KHÔNG mất: `href` bên dưới cho bấm thẳng vào thanh để về trang này.
  { key: "tongquan", label: "Tổng quan", icon: "tongquan", href: "/", blocks: [] },

  // NHÓM THỨ TÁM, thêm 12/9/2026 theo bản vẽ navy V1.2 anh Tuấn chốt. KHÔNG có mục nào mới: năm mục
  // dưới đây được NHẤC NGUYÊN từ hai mục con "Marketing" và "Chăm sóc & khiếu nại" đang nằm trong
  // nhóm Kinh doanh. Đường dẫn không đổi một ký tự nào, nên 53 lối vào của MENU_ROLES giữ nguyên và
  // không ai mất đường đi – chỉ đổi chỗ đứng trong thanh dọc.
  //
  // VÌ SAO CHĂM SÓC VÀ KHIẾU NẠI ĐI THEO MARKETING, không ở lại Kinh doanh: đây là chỗ em tự quyết,
  // ghi ra để anh lật lại được. Hai màn hình ấy làm việc với khách SAU khi đã bán – giữ tiếng và
  // giữ khách, cùng một việc với Nội dung & thương hiệu. Phiếu chăm sóc VẪN tự giao cho nhân viên
  // đã bán như chốt 07/9; đổi nhóm menu không đổi người được giao việc.
  { key: "marketing", label: "Marketing & PR", icon: "marketing", href: "/phan-he/marketing", blocks: [
    // 19/9/2026 · ĐẶT ĐẦU TIÊN, và đó là chủ ý. Trước hôm nay cửa lọc khủng hoảng nằm lẫn trong
    // tab "Thương hiệu & PR" — sâu ba lớp, sau một cái tên không gợi gì tới khủng hoảng. Chính
    // anh Tuấn, người đặt làm nó, mở web mà không thấy; người trực lúc 2 giờ sáng càng không.
    // Một cửa báo động phải biết đường mới mò ra được thì nó không phải cửa báo động.
    ["Khủng hoảng & phản ứng nhanh", "/marketing?tab=thuonghieu"],
    ["Kế hoạch & ngân sách", "/marketing?tab=ngansach"],
    ["Chiến dịch", "/marketing"],
    ["Nội dung & thương hiệu", "/noi-dung"],
    // TC-81 · 24/9/2026. Mục 2.2.2 – sổ báo chí, sự kiện, phát ngôn, và danh bạ KOL/KOC.
    //
    // ĐẶT NGAY SAU "Nội dung & thương hiệu" vì cùng một việc của phòng: một bên là bài mình tự
    // đăng, một bên là bài người khác đăng về mình. Cố ý KHÔNG nhét vào tab của màn hình
    // /marketing: sổ PR đã sống ở đó ba tuần sau một cái tên không gợi gì tới báo chí, và không
    // màn hình nào gọi tới cửa của nó — tức là chưa ai vào được. Cùng bài học với dòng đầu khối.
    ["Báo chí, KOL & sự kiện", "/bao-chi-kol"],
    // TC-77 · 23/9/2026. Nhóm 2.7 – tiền quảng cáo bỏ ra thu về được bao nhiêu doanh thu.
    //
    // Đọc doanh thu bằng ĐÚNG ống số của màn hình Kinh doanh lẻ và màn hình Chủ tịch, không có
    // truy vấn doanh thu riêng nào cho Marketing. Một ống số thì chỉ có một con số, và mọi câu
    // hỏi còn lại là câu hỏi về cách CHIA con số ấy.
    ["Đóng góp doanh thu", "/dong-gop-marketing"],
    // TC-78 · 23/9/2026. Nhóm 2.6 – quãng giữa hai phòng: Marketing giao lead, Sales xử lý.
    //
    // Phép tính hạn xử lý gọi thẳng services/leads, không có bản chép thứ hai. Định nghĩa "quá
    // hạn" đã được dọn về một mối ngày 18/9 để chỗ đếm và chỗ đánh dấu dùng chung một luật; chép
    // nó sang đây là dựng lại đúng cái vừa dọn xong.
    ["Chuyển đổi & phối hợp Sales", "/chuyen-doi-lead"],
    // TC-79 · 24/9/2026. Nhóm 2.8 – bàn cân. Đặt cuối nhóm Marketing vì nó chỉ có nghĩa khi đã
    // có hai vật để cân: màn hình này KHÔNG tự tính doanh thu, tỷ lệ hay chi phí nào của riêng
    // nó, mà gọi lại máy của nhóm 2.6 và 2.7 rồi đặt cạnh những con số người dùng đã tự khai.
    ["Đối soát dữ liệu", "/doi-soat-marketing"],
    { label: "Chăm sóc & khiếu nại", items: [
      ["Chăm sóc sau bán", "/cham-soc"], ["Phản hồi & khiếu nại", "/khieu-nai"]] },
  ] },

  // "Hộp thư" Ở LẠI Kinh doanh dù ba kênh (Zalo OA, vChat, tổng đài) do Marketing dựng: người mở
  // hộp thư mỗi ngày để trả lời khách là nhân viên bán hàng. Phần cấu hình kênh nằm ở Quản trị hệ
  // thống → Tích hợp, đúng chỗ của nó.
  // TC-70 · 18/9/2026: KHÔNG còn `href`. Bấm thẳng vào chữ "Kinh doanh" chỉ xổ ra, không đi đâu –
  // anh Tuấn chọn thế khi em hỏi. Hệ quả phải nói rõ: /phan-he/khachhang (mục lục GỘP hai phòng)
  // mất lối vào từ thanh dọc. Con số hợp nhất KHÔNG mất theo – Báo cáo – Phân tích → "Kinh doanh"
  // trỏ /sales-reports không kèm ?mang=, đúng chỗ xem tổng hai phòng. Cái mất là mục lục, không
  // phải số liệu. Đường dẫn /phan-he/khachhang vẫn sống cho ai đã lưu dấu trang.
  { key: "khachhang", label: "Kinh doanh", icon: "khachhang",
    phans: [{ khoa: "kdle", label: "Kinh doanh lẻ" }, { khoa: "kddoan", label: "Kinh doanh đoàn" }],
    blocks: [
    // ĐỢT PH-1 · 09/11/2026 — hai phòng có lối vào RIÊNG, đứng đầu nhóm. Chủ tịch chốt
    // 08/11/2026: bấm vào phân hệ nào thì ra đúng trang của phòng ấy.
    ["Kinh doanh lẻ", "/fit"],
    ["Kinh doanh đoàn", "/mice"],
    // 24/9/2026 · Bàn làm việc của Phó TGĐ tour đoàn — hàng đợi dự toán đoàn chờ chính ông ký
    // (Điều 4 Văn bản đính chính). ĐỨNG ĐẦU NHÓM, và ba chỗ đặt em đã cân rồi mới chọn chỗ này:
    //
    //   · KHÔNG đặt ở "Tổng quan": anh Tuấn chốt 12/9/2026 nhóm ấy không có mục con nào, và
    //     test_menu canh đúng điều đó. Một quyết định đã chốt thì không lách bằng một mục mới.
    //   · KHÔNG đặt ở "Điều hành": người ký dự toán không đứng cùng phía với phòng trình nó.
    //   · ĐẶT ở "Kinh doanh" vì đúng chức danh của ông: "Phó Tổng giám đốc phụ trách KINH DOANH
    //     tour đoàn". Ông duyệt dự toán với tư cách người chịu trách nhiệm mảng đoàn.
    //
    // Đứng đầu nhóm KHÔNG đẩy mục nào của nhân viên bán hàng xuống: mục này chỉ hiện cho sáu vai
    // khai ở MENU_ROLES["/ptgd-doan"]. Với mọi vai khác, nhóm này bắt đầu bằng "Hộp thư" y như cũ.
    ["Duyệt dự toán đoàn", "/ptgd-doan"],
    // Bàn làm việc của Sale Admin phòng Đoàn — đặt NGAY SAU mục trên vì hai màn hình là hai đầu
    // của cùng một dây chuyền: chị ấy chuyển sang Điều hành, ông ấy ký ở cuối. Cùng nhóm "Kinh
    // doanh" và cùng lý do: vị trí này thuộc Phòng Kinh doanh Đoàn.
    ["Bàn làm việc Sale Admin", "/sales-admin"],
    // Bàn bán tour lẻ — Chủ tịch quyết 25/9/2026. Đặt cạnh hai mục trên vì cùng nhóm "Kinh
    // doanh", nhưng nó là của phòng LẺ: lịch khởi hành do Điều hành mở, phòng Lẻ chỉ bán, và
    // bảng này là thứ họ mở trước khi trả lời khách xin giảm giá.
    ["Bàn bán tour lẻ", "/ban-tour-le"],
    // Đánh giá sau tour — Chủ tịch quyết 25/9/2026. Đặt trong nhóm "Kinh doanh" vì người đọc nó
    // hằng tuần là Kinh doanh và Điều hành; trang KHÁCH tự chấm nằm ở /y-kien/<mã>, ngoài
    // thanh điều hướng — khách không có tài khoản và không nên thấy sơ đồ phân hệ của công ty.
    ["Đánh giá sau tour", "/danh-gia"],
    ["Hộp thư", "/inbox"],
    ["Khách hàng & nguồn khách", "/leads?tab=leads"],
    // KH-3 · 26/10/2026: VTD Rewards — tra điểm khách, áp voucher khách đổi ở cổng vào booking.
    ["VTD Rewards", "/vtd-rewards"],
    // KH-4 · 27/10/2026: việc khách gửi từ cổng — đổi / hủy / hóa đơn (Sales, Kế toán, Sale Admin)
    // và góp ý riêng lãnh đạo (chỉ Chủ tịch + TGĐ trả lời; menu chỉ hiện cho BASE_VIEW).
    ["Yêu cầu khách (cổng)", "/yeu-cau-khach"],
    ["Góp ý riêng lãnh đạo", "/gop-y-lanh-dao"],
    ["OTA: khách sạn & vé máy bay", "/khach-san-ota"],
    ["Đơn phòng OTA (sáu bước Agoda)", "/don-khach-san-ota"],
    ["Đối soát OTA", "/doi-soat-ota"],
    // TC-73 · 19/9/2026. Sơ đồ chi nhánh → phòng → team → người, mỗi phân công có ngày hiệu lực.
    //
    // ĐỨNG NGOÀI hai khối "Lẻ" và "MICE", vì nó là của CẢ HAI phòng: một người có thể ở cây Lẻ,
    // người khác ở cây Đoàn, và màn hình đổi được mảng ngay trên đó. Nhét vào một trong hai khối
    // là buộc phòng kia đi vòng qua menu của phòng bạn để xem sơ đồ của chính mình.
    //
    // Hành chính – Nhân sự mới là người GHI sổ này, nhưng mục menu vẫn treo ở Kinh doanh: người đi
    // tìm "team mình gồm những ai" là nhân viên kinh doanh, và họ tìm ở phân hệ của họ. Quyền ghi
    // nằm ở máy chủ (api/v1/to_chuc_kd.py), không nằm ở chỗ treo mục menu.
    ["Cơ cấu tổ chức", "/to-chuc-kd"],
    // TC-74 · 19/9/2026. Ai được đứng tên một booking: nhân viên khối Kinh doanh, người bộ phận
    // khác đã mở quyền bán (HDV, điều hành, visa), và ĐỐI TÁC ngoài công ty.
    //
    // Đứng ngay dưới "Cơ cấu tổ chức" vì hai màn hình trả lời hai nửa của cùng một câu: bên kia là
    // "ai thuộc đơn vị nào", bên này là "ai được bán".
    ["Người bán hàng", "/nguoi-ban-hang"],
    // TC-76 · 19/9/2026. Doanh thu và chỉ tiêu Kinh doanh lẻ – một màn hình cho cả bốn vai
    // (viết thường chữ "lẻ" theo đúng nếp đặt tên của khối menu này; test_khong_quay_lai_ten_cu
    // quét CẢ dòng chú thích, nên viết hoa ở đây làm phép thử đỏ vì một lý do không có thật)
    // (Giám đốc, Trưởng phòng, Team Leader, Nhân viên); độ sâu do MÁY CHỦ quyết theo phân công,
    // không do màn hình tự chọn. Đứng dưới hai màn hình trên vì nó ĐỌC cả hai: cơ cấu tổ chức
    // cho biết cộng lên đâu, người bán hàng cho biết ai được tính.
    ["Doanh thu & chỉ tiêu KD Lẻ", "/kinh-doanh-le"],
    // Kinh doanh tách làm hai phòng (chỉ đạo 07/9/2026). Mảng nằm ở TOUR chứ không ở booking, và
    // được nhận theo HỢP của hai quy tắc: loại chuyến là đoàn, HOẶC mã tour bắt đầu bằng MICE. Đo
    // 07/9: 115/115 tour có chữ MICE đều là tour đoàn, nên hôm nay hai quy tắc trùng nhau – lấy hợp
    // để mai kia có ai nhập lệch thì tour vẫn không rơi khỏi màn hình của phòng mình.
    // Gộp hai phòng vào MỘT NHÓM không được làm mất việc tách mảng ấy: mỗi phòng vẫn mở đúng
    // ?mang= của mình, không cùng trỏ một danh sách rồi để người dùng tự lọc.
    { label: "Lẻ", items: [
      ["Tour lẻ", "/tours?mang=le"], ["Yêu cầu & booking", "/requests?mang=le"],
      ["Booking & bảo lưu", "/bookings?mang=le"], ["Dịch vụ lẻ", "/non-package"],
      ["Giá & chính sách bán", "/bang-gia"], ["Báo giá", "/bao-gia?mang=kd_le"],
      ["Báo cáo bán hàng", "/sales-reports?mang=le"]] },
    { label: "MICE", items: [
      ["Tour đoàn", "/tours?mang=doan"], ["Yêu cầu & booking", "/requests?mang=doan"],
      ["Booking & bảo lưu", "/bookings?mang=doan"], ["Báo giá đoàn", "/bao-gia?mang=kd_doan"],
      ["Hợp đồng", "/hop-dong-khach"], ["Báo cáo bán hàng", "/sales-reports?mang=doan"]] },
  ] },

  // TC-70 · 18/9/2026: ba đơn vị, không phải ba nhãn cho vui. Xe thuộc pháp nhân Công ty TNHH Vận
  // tải Vietrip, hướng dẫn viên hưởng lương ở công ty mẹ, còn điều hành tour chạy quanh CHUYẾN –
  // ba người quản khác nhau thì ba màn hình. /phan-he/vanhanh vẫn mở được bằng đường dẫn.
  { key: "vanhanh", label: "Điều hành", icon: "vanhanh",
    phans: [{ khoa: "dhtour", label: "Điều hành tour" }, { khoa: "dhxe", label: "Điều hành xe" },
            { khoa: "hdv", label: "Hướng dẫn viên" }],
    blocks: [
    // ĐỢT PH-1 · 09/11/2026 — ba lối vào RIÊNG. `/op` và `/guide` là trang chỉ tiêu của
    // hai phòng. `/xe` thì khác hẳn: nó là BÀN LÀM VIỆC Giám đốc đội xe (PR #744), và nó
    // đã được khai quyền trong `access.py` mà chưa có mục menu nào — `test_menu` đỏ với
    // đúng câu «khai một cánh cửa không có đường đi». Dòng giữa dưới đây là đường đi ấy.
    // `dhxe` KHÔNG đổi chỗ: nó vẫn ở `/phan-he/dhxe`, vào bằng chip `Điều hành xe` ở trên.
    ["Điều hành tour", "/op"],
    ["Bàn làm việc đội xe", "/xe"],
    ["Hướng dẫn", "/guide"],
    ["Sản phẩm tour", "/products"],
    ["Yêu cầu chờ xử lý", "/requests"],
    ["Chuyến & quyết toán", "/tours"],
    // TC-71 · 19/9/2026. Đặt NGAY SAU "Chuyến & quyết toán" vì nó là mặt còn thiếu của đúng màn
    // hình ấy: bên kia là mọi chuyến, bên này là những chuyến còn nợ sổ. Đặt cuối nhóm thì người
    // điều hành phải nhớ là có nó mới đi tìm, mà thứ này đúng ra phải đập vào mắt mỗi ngày.
    ["Sổ chuyến còn nợ", "/so-con-no"],
    ["Sự cố tour", "/su-co-tour"],
    // Lãi lỗ tour đứng NGAY SAU Chuyến vì đó là thứ tự thật của việc: nhập xong dòng chi phí quyết
    // toán thì mới có giá vốn, có giá vốn mới có lãi lỗ. Đặt trước thì người dùng gặp bảng lãi lỗ
    // rỗng trước khi gặp việc phải làm để nó có số.
    ["Lãi lỗ theo tour", "/lai-lo-tour"],
    { label: "Dịch vụ & NCC", items: [
      ["Nhà cung cấp & đặt dịch vụ", "/nha-cung-cap"], ["Cổng nhà cung cấp", "/cong-ncc"], ["Hồ sơ visa", "/visa"],
      // KH-2 · 26/10/2026: Điều hành nhập nhà hàng cho cổng khách; Kinh doanh bật hiện cổng.
      ["Nhà hàng (cổng khách)", "/nha-hang"],
      // KS-13 · 30/10/2026: Điều hành nhập khách sạn hợp tác, loại phòng, giá; TP Điều hành duyệt và bật hiện.
      ["Khách sạn (cổng khách)", "/khach-san-vtd"],
      // TR-1 · 02/11/2026: tour trên kh.vietourist.vn/tours — ghép trang tour vietourist.com.vn, công tắc thanh toán, đơn online.
      ["Tour (cổng khách)", "/tour-online"],
      // TK-1 · 04/11/2026: khách tự thiết kế tour đoàn — thiết kế khách gửi + đơn giá dịch vụ đoàn (giá vốn).
      ["Tour đoàn khách tự thiết kế", "/tour-doan"]] },
    // Xe và hướng dẫn viên tách khỏi Điều hành thành đơn vị riêng (chỉ đạo 07/9/2026). Xe nội bộ
    // thuộc pháp nhân Công ty TNHH Vận tải Vietrip, còn hướng dẫn viên hưởng lương ở công ty mẹ.
    { label: "Xe & tài xế", items: [
      // Hồ sơ đội xe theo đặc tả "Quản lý vận hành xe Vietrip" v1.3: mã xe cố định, lịch sử biển,
      // giấy tờ có hạn và điều kiện khai thác. Màn hình /ops?tab=fleet cũ giữ nguyên cho phần bảng
      // giá và lệnh điều xe.
      ["Hồ sơ xe & điều kiện khai thác", "/doi-xe"], ["Hồ sơ tài xế", "/tai-xe"],
      ["Bảng giá & lệnh", "/ops?tab=fleet"],
      ["Lệnh điều xe", "/lenh-dieu-xe"], ["Chi phí & hiệu quả", "/hieu-qua-doi-xe"],
      ["Lãi lỗ đội xe", "/lai-lo-doi-xe"], ["Việc của tài xế & HDV", "/xe-hdv"]] },
    { label: "Hướng dẫn viên", items: [
      ["Phòng Hướng dẫn", "/huong-dan"], ["Nhân viên phòng tôi", "/nhan-vien-phong-toi"], ["HDV & phân chuyến (cũ)", "/ops?tab=guides"]] },
  ] },

  { key: "nhansu", label: "Nhân sự – Hành chính", label_ngan: "HC – NS", icon: "nhansu",
    href: "/phan-he/nhansu", blocks: [
    ["Hồ sơ nhân sự", "/hr?tab=employees"],
    ["Hợp đồng lao động", "/hop-dong-lao-dong"],
    // HAI muc, HAI doi tuong. "Chấm công & nghỉ phép" la man hinh cua NGUOI CHAM CONG (the
    // cham_cong cua /hr, mo cho sau vai) — Dot C dung the ay 08/10/2026 nhung chua co muc menu
    // nao tro toi, nen no chi vao duoc tu cay phan he. "Đơn nghỉ phép của tôi" la cua cua
    // NGUOI GUI DON, mo cho ca 22 vai. Gop hai muc lam mot thi hoac chin phong khong co duong
    // gui don, hoac 22 vai nhin thay mot muc menu bam vao nhan 403.
    ["Chấm công & nghỉ phép", "/hr?tab=cham_cong"],
    ["Đơn nghỉ phép của tôi", "/cham-cong"],
    ["Lương, thưởng & hoa hồng", "/hr?tab=payroll"],
    ["Đánh giá & sự vụ", "/hr?tab=incidents"],
    ["Báo cáo công việc", "/reports"],
    ["Chính sách & quy trình", "/params"],
    ["IR – Pháp chế", "/ir-phap-che"],
    ["Cổng cổ đông", "/ir-cong-co-dong"],
    ["Gửi yêu cầu Pháp chế", "/gui-phap-che"],
    ["Tài sản & cấp phát", "/tai-san"],
    // 5.9.2 · 09/10/2026 — MỤC RIÊNG, không nhập vào "/tai-san". Mục trên mở cho sáu vai (Kế toán,
    // CNTT, hành chính, HCNS và hai vai nền); mục này mở cho MỌI người làm việc ở đây, vì người đề
    // nghị mua là người của mọi phòng. Một mục menu chở được một tập vai, nên gộp hai việc vào một
    // mục là hoặc chín phòng không thấy đường gửi, hoặc cả công ty nhìn thấy sổ tài sản.
    ["Đề nghị mua", "/de-nghi-mua"],
  ] },

  { key: "taichinh", label: "Tài chính – Kế toán", icon: "taichinh", href: "/phan-he/taichinh", blocks: [
    // TC-41 (16/9/2026) – ĐẶT ĐẦU NHÓM, trên cả Thu và Chi, vì đó là thứ tự thật của việc: đặt chỉ
    // tiêu trước, rồi mới thu và chi để đạt nó. Xếp xuống cuối nhóm thì mục này nằm sau sáu mục
    // nghiệp vụ hằng ngày, và một việc làm mỗi năm một lần mà nằm cuối danh sách thì không ai thấy.
    ["Kế hoạch tháng", "/ke-hoach-thang"],
    ["Thu & đối soát", "/collections"],
    ["Chi & thanh toán", "/expenses"],
    // DH-1 26/10/2026 — hoa hồng đại lý / CTV bán hàng theo D06 (Chủ tịch chốt).
    ["Hoa hồng đối tác (D06)", "/hoa-hong-d06"],
    ["Đặt bàn nhà hàng: tiền & hoàn", "/dat-ban-nha-hang"],
    ["Công nợ", "/cong-no"],
    ["Bảo lưu & hoàn tiền", "/bookings"],
    // Robot A · 11/9/2026. Bảng bốn mốc lũy kế của v1.1 §III (DT-1…DT-4). Đặt NGAY TRÊN mục
    // "Dòng tiền" cũ vì hai màn hình trả lời hai câu khác nhau và người dùng cần thấy chúng cạnh nhau.
    //
    // TÊN "Dòng tiền 4 mốc" LÀ TÊN CHỦ TỊCH CHỐT 11/9/2026, và em cố ý không lấy tên "Dòng tiền" của
    // mục dưới. v1.1 §III gọi màn hình này là "bảng dòng tiền", nhưng §I.2 đã đặt tên "Dòng tiền" cho
    // bảng dự báo 13 tuần, và phép thử của lằn TC-2 canh đúng dòng ấy. Hai mục cùng tên mở ra hai màn
    // hình khác nhau thì tệ hơn một cái tên dài.
    ["Dòng tiền 4 mốc", "/dong-tien"],
    ["Dòng tiền", "/finance?tab=forecast"],
    ["Vay & đầu tư", "/finance?tab=contracts"],
    ["Tài khoản ngân hàng", "/bank-accounts"],
    { label: "Sổ & kỳ kế toán", items: [
      ["Sổ kế toán", "/accounting?tab=journal"], ["Hóa đơn & thuế", "/accounting?tab=invoices"],
      // Kết sổ đứng NGAY TRƯỚC Khóa kỳ vì đó là thứ tự thật của việc: đưa sao kê vào sổ, kết chuyển
      // bốn bước, rồi mới khóa. Xếp ngược lại thì người dùng gặp nút khóa trước khi gặp việc phải làm.
      ["Kết sổ kỳ", "/ket-so"], ["Khóa kỳ", "/accounting?tab=periods"],
      // ĐỢT R4b-2b 23/10/2026 — đứng NGAY SAU "Khóa kỳ" và trước "Quy ước hạch toán":
      // nó là việc phải làm TRƯỚC khi khóa kỳ cho sạch, nhưng KHÔNG chặn khóa kỳ.
      ["Hóa đơn còn thiếu", "/hoa-don-thieu"],
      ["Quy ước hạch toán", "/hach-toan"], ["Hồ sơ kiểm toán", "/ho-so-kiem-toan"],
      // Sổ tỷ giá (16/9/2026). Đứng trong nhóm Sổ & kỳ kế toán chứ không đứng riêng một mục: tỷ giá
      // là một QUY ƯỚC GHI SỔ – cùng họ với "Quy ước hạch toán" – chứ không phải một nghiệp vụ.
      ["Sổ tỷ giá", "/ty-gia"]] },
  ] },


  // Báo cáo tự động theo phòng (09/9/2026): Chủ tịch và TGĐ mở bản toàn công ty ở đây, trưởng phòng
  // mở bản của phòng mình ở CÙNG một đường dẫn – máy chủ cắt theo vai trò. Một đường dẫn cho mọi
  // cấp, không phải mỗi phòng một mục menu.
  //
  // "Kinh doanh" ở đây KHÔNG kèm ?mang=: hai phòng vào báo cáo của mình qua menu nhóm Khách hàng &
  // Kinh doanh. Nếu chỉ có hai lối đó thì không còn đường nào tới con số HỢP NHẤT.
  { key: "baocao", label: "Báo cáo – Phân tích", icon: "baocao", href: "/phan-he/baocao", blocks: [
    ["Điều hành", "/bao-cao"],
    ["Kinh doanh", "/sales-reports"],
    ["Marketing", "/leads?tab=report"],
    ["Tài chính", "/accounting?tab=bctc"],
    ["Báo cáo quản trị", "/robot-reports"],
  ] },

  // ĐẶT CUỐI theo v1.1 §I.2 (tên nhóm đổi theo bản vẽ giao diện 12/9, thứ tự giữ nguyên).
  { key: "quantri", label: "Quản trị hệ thống", icon: "quantri", href: "/phan-he/quantri", blocks: [
    // TC-75 · 19/9/2026. Gộp hai tài khoản trùng của cùng một người.
    //
    // ĐỨNG Ở QUẢN TRỊ HỆ THỐNG chứ không ở Nhân sự, dù HC-NS là người phát hiện ra trùng: nút gộp
    // chuyển dữ liệu giữa hai tài khoản và KHÔNG tách ngược được, nên nó thuộc nhóm những việc chỉ
    // CNTT và Ban Tổng giám đốc bấm. HC-NS đọc được bảng cặp trùng để soát, đó là phần việc của họ.
    ["Tài khoản trùng", "/gop-tai-khoan"],
    ["Tổ chức & đơn vị", "/companies"],
    { label: "Quyền", items: [
      ["Tài khoản & phân quyền", "/access"], ["Vị trí AI & quyền hạn", "/ai-roles"],
      // CG-1 26/10/2026 — hàng chờ duyệt đối tác / cổ đông đăng ký từ cổng kết nối VTD.
      ["Tài khoản bên ngoài", "/tai-khoan-ngoai"]] },
    { label: "Tích hợp", items: [
      ["Đồng bộ Vietrip", "/vietrip"], ["Kết nối MISA và các kênh", "/accounting?tab=misa"],
      ["Đọc chứng từ ảnh", "/doc-chung-tu"], ["Tệp & hình ảnh", "/tep"]] },
    ["Tự động hóa", "/tu-dong-hoa"],
    { label: "Chuẩn hóa dữ liệu", items: [
      ["Nạp dữ liệu", "/nap-du-lieu"],
      // Bàn quyết cột tiền K1/K2. Kế toán là người quyết một cột có phải tiền hay không (chốt 08/9),
      // nên mục này phải nằm ở chỗ Kế toán mở được – Quản trị mở cho cả Kế toán.
      ["Rà soát cột tiền", "/ra-soat-cot-tien"]] },
    // Ba màn hình giám sát. v1.1 không xếp chúng vào mục con nào; để cùng Nhật ký vì cùng một việc:
    // nhìn lại hệ thống đã làm gì và chỗ nào lệch.
    { label: "Kiểm soát & nhật ký", items: [
      ["Cảnh báo nghiệp vụ", "/alerts"], ["Ngoại lệ cần xử lý", "/ngoai-le"],
      ["Kiểm soát (robot)", "/kiem-soat"], ["Nhật ký nghiệp vụ", "/audit"],
      // Đếm lượt mở cửa đọc — Đợt HD-Q2mh. Đứng cạnh "Nhật ký nghiệp vụ" vì cùng một việc: nhìn
      // lại hệ thống đã làm gì. Khác ở chỗ nhật ký ghi thao tác GHI, còn mục này đếm lượt ĐỌC —
      // và trước Đợt HD-Q2a hệ thống không có chỗ nào ghi lượt đọc, nên câu "mỗi ngày mỗi vai mở
      // bao nhiêu phiếu" không trả lời được. Chỉ bốn vai thấy mục này (MENU_ROLES).
      ["Đếm lượt mở cửa đọc", "/dem-luot-doc"],
      // Đợt HD-DG3. Đứng cạnh hai mục trên vì cùng một họ: nhìn lại hệ thống đã làm gì. Khác ở
      // chỗ hai mục kia chỉ ĐỌC, còn mục này có nút BẤM — và nút ấy quyết một lời của khách có
      // lên mạng hay không. Sáu vai thấy mục (MENU_ROLES), ba người bấm được.
      ["Duyệt công bố nhận xét", "/duyet-cong-bo"]] },
  ] },
];

/** Ba mục của CHÍNH người đăng nhập – nằm trên thanh ngang, không thuộc phòng ban nào. Lọc theo
 *  hidden_menus vẫn áp dụng: vai trò không phải nộp báo cáo ngày thì mục đó tự rụng (đính chính
 *  08/9 – bộ mẫu báo cáo ngày chỉ có bảy phòng văn phòng, tài xế và HDV không nộp). Hai mục còn lại
 *  không bao giờ rụng vì chúng nằm trong MAN_HINH_KHONG_DUOC_AN.
 *
 *  Hai tệp phép thử cắt khối GROUPS ra để đọc bằng biểu thức chính quy (test_menu.py và
 *  test_man_hinh_co_cua_nhap.py). Cả hai lấy `export const CA_NHAN` ngay dưới đây làm MỐC KẾT THÚC.
 *  Trước 11/9/2026 chúng bám vào hai thứ khác nhau, và đều là thứ tình cờ đứng sau bảng: chuỗi
 *  "/** Vai trò" và tên hằng "const ROADMAP_ROLES". Bỏ ROADMAP_ROLES là một tệp phép thử vỡ ngay,
 *  báo ValueError không nói gì về nguyên nhân. Mốc mới là MÃ THẬT chứ không phải chú thích: bộ đọc
 *  của tệp kia xoá hết chú thích trước khi tìm mốc. */
export const CA_NHAN: Item[] = [
  ["Báo cáo công việc của tôi", "/reports"],
  ["Phiếu lương của tôi", "/phieu-luong"],
  ["Đổi mật khẩu", "/doi-mat-khau"],
];

const base = (href: string) => href.split("?")[0];
const isOn = (href: string, path: string) => { const b = base(href); return b === "/" ? path === "/" : path.startsWith(b); };
const laMuc = (b: Block): b is Item => Array.isArray(b);

type Toast = { msg: string; err?: boolean } | null;

/** `datChuaLuu` là sổ ghi "màn hình này còn dữ liệu chưa lưu", dùng cho TC-1: đổi đơn vị đang xem
 *  giữa chừng một biểu đang gõ dở là mất việc người ta vừa làm, mà mất im lặng.
 *
 *  Mỗi màn hình có biểu nhập gọi `datChuaLuu(true)` khi người dùng bắt đầu sửa và `datChuaLuu(false)`
 *  sau khi lưu xong. Màn hình chưa gọi thì coi như không có gì để mất – đúng với màn hình chỉ đọc,
 *  và KHÔNG chặn nhầm người dùng ở những chỗ không cần chặn. */
const Ctx = createContext<{
  user: User | null;
  toast: (m: string, err?: boolean) => void;
  datChuaLuu: (co: boolean) => void;
}>({ user: null, toast: () => {}, datChuaLuu: () => {} });
export const useShell = () => useContext(Ctx);

// Trạng thái THU/BUNG của thanh dọc, nhớ theo từng người dùng. Khoá "vtos_menu_mo" (nhóm nào đang
// ghim mở) đã bỏ cùng lối ghim mở, khi bấm thanh phân hệ chuyển thành đi tới trang phân hệ (13/9).
const KHOA_THU = "vtos_menu_thu";

// KS-49 (09/11/2026) — `khongThanhBen`: ẩn thanh dọc, giữ nguyên mọi thứ khác của
// Shell (canh đăng nhập, mật khẩu tạm, toast, Ctx). Dành cho màn hình là MỘT bàn
// làm việc trọn vẹn của một bộ phận, nơi thanh phân hệ của phòng khác chỉ là nhiễu
// — màn /xe của Giám đốc đội xe là trường hợp đầu tiên. Mặc định false: mọi màn
// đang có không đổi gì.
export default function Shell({ children, khongThanhBen = false }:
                              { children: React.ReactNode; khongThanhBen?: boolean }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [t, setT] = useState<Toast>(null);
  const [side, setSide] = useState(false);             // màn hình nhỏ: mở/đóng thanh dọc
  const [menuToi, setMenuToi] = useState(false);       // menu cá nhân trên thanh ngang
  const [thu, setThu] = useState(false);               // thanh dọc thu còn một cột biểu tượng
  const [alerts, setAlerts] = useState(0);
  const path = usePathname();
  const router = useRouter();

  useEffect(() => {
    // CG-3: trên tên miền cổng ngoài, màn VTOS không bao giờ mở — xóa phiên VTOS lỡ lưu, đưa về cổng.
    if (laTenMienCong()) { clearSession(); router.replace(phienCong() ? "/cong" : "/login"); return; }
    const u = getUser(); if (!u) { router.replace("/login"); return; }
    setUser(u); setReady(true);
    // Tài khoản còn mật khẩu tạm: đưa thẳng tới màn hình đổi mật khẩu. Máy chủ đã chặn mọi đường dẫn
    // khác, nên nếu không chuyển hướng ở đây thì người dùng chỉ thấy một loạt lỗi 403 mà không hiểu.
    if (u.must_change_password && path !== "/doi-mat-khau") { router.replace("/doi-mat-khau"); return; }
    // Nhớ trạng thái THU/BUNG THEO NGƯỜI DÙNG. Khoá gắn tên đăng nhập vì một máy dùng chung
    // (máy quầy, máy điều hành) thì trạng thái của người trước không được đè lên người sau.
    try {
      setThu(localStorage.getItem(`${KHOA_THU}_${u.username}`) === "1");
    } catch { /* máy chặn localStorage thì mở mặc định – không phải lỗi */ }
    const h = { Authorization: `Bearer ${localStorage.getItem("vtos_token") || ""}` };
    // làm mới quyền (menu ẩn/hiện) từ máy chủ mỗi lần mở – phòng khi ma trận phân quyền đổi sau khi đăng nhập
    fetch("/api/v1/auth/me", { headers: h }).then((r) => r.ok ? r.json() : null).then((m) => {
      if (!m) return;
      localStorage.setItem("vtos_user", JSON.stringify(m)); setUser(m);
      if (m.must_change_password && path !== "/doi-mat-khau") router.replace("/doi-mat-khau");
    }).catch(() => {});
    fetch("/api/v1/alerts", { headers: h }).then((r) => r.ok ? r.json() : null).then((a) => { if (Array.isArray(a)) setAlerts(a.length); else if (a?.rows) setAlerts(a.tong ?? a.rows.length); }).catch(() => {});
  }, [router, path]);

  const toast = useCallback((msg: string, err?: boolean) => { setT({ msg, err }); setTimeout(() => setT(null), err ? 6500 : 4000); }, []);

  // Dùng ref chứ không dùng state: cờ này chỉ được ĐỌC lúc người dùng bấm đổi đơn vị, không có gì
  // phải vẽ lại theo nó. Để vào state thì mỗi lần gõ một chữ trong biểu là vẽ lại cả khung.
  const chuaLuu = useRef(false);
  const datChuaLuu = useCallback((co: boolean) => { chuaLuu.current = co; }, []);

  /** Thu / bung thanh dọc. §I.2 đòi nhớ trạng thái THEO TỪNG NGƯỜI DÙNG, nên khoá gắn tên đăng
   *  nhập – máy quầy dùng chung thì người trước không đè lên người sau. */
  const doiThu = useCallback(() => {
    setThu((t2) => {
      const moi2 = !t2;
      try { if (user) localStorage.setItem(`${KHOA_THU}_${user.username}`, moi2 ? "1" : "0"); } catch { /* bỏ qua */ }
      return moi2;
    });
  }, [user]);

  /** Lọc theo quyền, giữ nguyên thứ tự và hai cấp. Mục con rỗng thì bỏ mục con; nhóm rỗng thì bỏ
   *  nhóm – không để lại nhãn nhóm mở ra không có gì bên trong. */
  const groups = useMemo(() => {
    const hid = user?.hidden_menus || [];
    const duoc = (h: string) => !hid.includes(base(h));
    return GROUPS.map((g) => {
      const blocks = g.blocks
        .map((b): Block | null => {
          if (laMuc(b)) return duoc(b[1]) ? b : null;
          const items = b.items.filter(([, h]) => duoc(h));
          return items.length ? { ...b, items } : null;
        })
        .filter((b): b is Block => b !== null);
      const dem = blocks.reduce((n, b) => n + (laMuc(b) ? 1 : b.items.length), 0);
      return { ...g, blocks, dem };
      // GIỮ ĐỦ TÁM NHÓM CHO MỌI VAI TRÒ (anh Tuấn chốt 13/9/2026). Trước đó nhóm nào vai này không
      // có màn hình nào thì rụng khỏi menu; bỏ cách ấy vì nó khiến nhân viên không biết hệ thống có
      // những gì và không biết phải xin quyền ở đâu – cứ tưởng phần mềm chưa làm chức năng ấy.
      // Quyền vẫn nguyên: bảng xổ ra chỉ liệt kê màn hình họ VÀO ĐƯỢC, và trang phân hệ KHOÁ những
      // mục không có quyền chứ không giấu. Cái lộ ra là TÊN chức năng, không phải số liệu.
      // Nhóm Tổng quan dẫn thẳng "/" – màn hình ấy ai đăng nhập cũng có (MAN_HINH_MOI_NGUOI).
    });
  }, [user]);

  const caNhan = useMemo(() => {
    const hid = user?.hidden_menus || [];
    return CA_NHAN.filter(([, h]) => !hid.includes(base(h)));
  }, [user]);

  /** KHÔNG CÒN BẢNG XỔ RA KHI RÊ CHUỘT (anh Tuấn chốt 13/9/2026, chiều): thanh phân hệ chỉ làm
   *  MỘT việc – bấm là đi tới trang phân hệ.
   *
   *  Vì sao bỏ: rê chuột ngang qua thanh dọc để tới chỗ khác mà bảng cứ bật ra là bật nhầm, và trên
   *  máy bảng thì không có "rê chuột" nên nửa số người dùng chưa bao giờ thấy nó. Mục lục đầy đủ –
   *  kể cả phần còn nợ và mục không có quyền – nằm ở trang phân hệ, chỗ ấy đọc kỹ được chứ không
   *  phải liếc vội. Toàn bộ mã toạ độ, hẹn giờ đóng chậm và bộ nghe cuộn/đổi cỡ đã gỡ theo.
   */

  if (!ready) return <main className="muted">Đang tải…</main>;

  const lien = (l: string, h: string) => (
    <Link key={l + h} href={h} className={isOn(h, path) ? "on" : ""} onClick={() => setSide(false)}>{l}</Link>
  );

  /** Thanh phân hệ nào đang SÁNG. Không chỉ so với chính đường dẫn của thanh: người dùng đang ở
   *  /leads thì thanh Marketing & PR phải sáng, nếu không thanh dọc không cho biết mình đang đứng
   *  ở đâu trong hệ thống. */
  const dangO = (g: Group & { dem: number }) =>
    (!!g.href && isOn(g.href, path)) ||
    // TC-70: nhóm xổ ra không có href của riêng nó, nên nó sáng khi người dùng đang đứng ở MỘT
    // TRONG các phân hệ con. Thiếu dòng này thì vào "Điều hành xe" xong nhìn lên thanh dọc không
    // thấy nhóm nào sáng – thanh dọc mất hẳn khả năng trả lời "tôi đang ở đâu".
    (g.phans?.some((p) => isOn(`/phan-he/${p.khoa}`, path)) ?? false) ||
    g.blocks.some((b) =>
      laMuc(b) ? isOn(b[1], path) : b.items.some(([, h]) => isOn(h, path)));


  return (
    <Ctx.Provider value={{ user, toast, datChuaLuu }}>
      <div className="top">
        <button type="button" className="burger" onClick={() => setSide((s) => !s)} aria-label="Menu">☰</button>
        {/* Dấu hiệu nhận biết: logo Vietourist Holdings v2, nền TRONG SUỐT (không đặt ảnh nền trắng lên
            thanh navy). alt RỖNG vì liên kết đã mang aria-label – đọc tên hai lần là thừa.
            width/height khai đúng tỉ lệ tệp (1107×269) để trang không giật khi ảnh tải xong. */}
        <Link href="/" className="brand" aria-label="Vietourist Holdings – Hệ thống điều hành, về bảng điều hành">
          {/* LOGO v2 (anh Tuấn duyệt 07/11/2026, bản xem thử «Logo v2 trên VTOS và VTD»): chỉ dùng
              logo Vietourist Holdings, bỏ dấu VTOS. Bản nền tối của bộ v2 (#5A9BD4 · #FF6F96 ·
              #5FAE66 + chữ trắng), đã bỏ ô nền #0B2545 để nằm thẳng trên thanh navy #14538D.
              Bên cạnh là chữ nhỏ «Hệ thống điều hành» để nhân viên biết đang ở VTOS.
              Dấu VTOS v1.0 (thuong-hieu/vtos-logo-*.svg) GIỮ trong kho để tra cứu, không xoá. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/thuong-hieu/v2/khoachu-holdings-nen-trong.svg" alt="" width={1107} height={269} className="brand-logo" />
          <small>HỆ THỐNG ĐIỀU HÀNH</small>
        </Link>
        <span className="bar">
          <ChonDonVi chuaLuu={() => chuaLuu.current} toast={toast} />
          {/* Ô tìm kiếm vẽ như một Ô NHẬP chứ không phải một nút chữ (bản vẽ giao diện 12/9). Vẫn là
              chức năng "sắp có" nên dùng thẻ button: một <input> chưa chạy được thì người dùng gõ vào
              rồi tưởng hệ thống hỏng. */}
          <button type="button" className="o-tim soon" title="Sắp có"
            onClick={() => toast("Tìm kiếm: đang xây dựng")}>
            <Bt d="tim" /><span>Tìm kiếm…</span>
          </button>
          <Link href="/#viec-cua-toi" className="bar-muc"><Bt d="viec" /><span>Công việc</span></Link>
          <Link href="/#cho-toi-duyet" className="bar-muc"><Bt d="duyet" /><span>Chờ duyệt</span></Link>
          {/* THỨ TỰ theo bản vẽ 12/9: … Công việc · Chờ duyệt · Trợ lý AI · chuông · Tài khoản.
              Chuông đứng sát ô tài khoản vì hai thứ ấy đều là của riêng người đang đăng nhập. */}
          <button type="button" className="bar-muc ai soon" title="Sắp có" onClick={() => toast("Trợ lý AI: đang xây dựng")}>
            <Bt d="ai" /><span>Trợ lý AI</span>
          </button>
          {/* Con số trên chuông là TỔNG CẢNH BÁO NGHIỆP VỤ, không phải "số thông báo chưa đọc" mà
              bản vẽ mô tả. Đo 12/9: /alerts/dem và /thong-bao/chua-doc đều trả 404 – hệ thống chưa
              đếm số chưa đọc ở đâu cả. Đổi nhãn sang "chưa đọc" trong khi con số vẫn là tổng cảnh
              báo là dán một cái tên sai lên một con số thật, tệ hơn là để nguyên. Khi nào có cửa
              đếm chưa đọc thì đổi cả số lẫn nhãn một lượt.

              CHẶN TRẦN 99+ ĐÃ BỊ BÁC (anh Tuấn chốt 13/9/2026). Bản vẽ V1.4 ghi tối đa 99+, và
              vòng TC-21 đã làm; anh Tuấn xem rồi và quyết GIỮ NGUYÊN SỐ THẬT của VTOS. Lý do đứng
              được: 1944 là con số nói lên quy mô tồn đọng, còn "99+" thì che mất chính điều ấy –
              một cái chuông đứng ở 99+ suốt nhiều tuần thì không ai biết nó đang là 120 hay 1900.
              Chừng nào chuông còn đếm cảnh báo nghiệp vụ chứ chưa đếm thông báo chưa đọc, thì số
              thật hữu ích hơn số đã chặn trần. Nhãn trợ năng nói rõ đây là cảnh báo nghiệp vụ. */}
          <Link href="/alerts" className="bar-muc" title="Thông báo & cảnh báo nghiệp vụ"
            aria-label={`Cảnh báo nghiệp vụ${alerts > 0 ? `: ${alerts}` : ""}`}>
            <Bt d="chuong" />{alerts > 0 && <b className="so-bao">{alerts}</b>}
          </Link>
          {/* TC-67 · Nút "Giao diện" đứng NGAY TRƯỚC ô tài khoản, cùng cụm với chuông: chuông, giao
              diện và ô tài khoản đều là thứ của RIÊNG người đang đăng nhập, khác với Công việc /
              Chờ duyệt là việc chung. Bảng chọn thì gắn thẳng vào <body> chứ không nằm trong thanh
              này – lý do ghi trong ChonGiaoDien.tsx, và đó là lỗi đã mắc thật một lần. */}
          <ChonGiaoDien user={user} />
          {/* Menu cá nhân: ba mục của chính người đăng nhập, rời khỏi menu trái theo TC-2. */}
          <span style={{ position: "relative" }}>
            <button type="button" className="who" aria-haspopup="menu" aria-expanded={menuToi}
              onClick={() => setMenuToi((m) => !m)}
              style={{ background: "none", border: 0, cursor: "pointer", font: "inherit", color: "inherit" }}>
              <span className="anh-dai-dien" aria-hidden="true">{chuDau(user?.full_name)}</span>
              <span className="who-ten">{tenVaChuc(user)}</span> ▾
            </button>
            {/* `menu-toi` KHÔNG phải lớp trang trí — nó là thứ duy nhất cứu bốn mục này khỏi vô
                hình. Hộp xổ xuống nằm trong `.top .right`, mà `globals.css` tô MỌI liên kết ở
                góc ấy thành `color:#fff` cho hợp thanh điều hướng tối; hộp này thì nền sáng
                (`--vtos-card`), nên không có lớp riêng là chữ trắng trên nền trắng. Bỏ lớp đi
                thì menu vẫn bấm được, vẫn không báo lỗi gì — chỉ là không ai đọc được nó.

                CHÚ THÍCH NÀY ĐỨNG TRÊN DÒNG `menuToi &&`, KHÔNG ĐỨNG DƯỚI — và đó là cả nội dung
                của đợt VA-WEB3 ngày 12/10/2026. Nằm ngay sau dấu mở ngoặc thì một khối chú thích JSX không còn là
                chú thích JSX: JavaScript đọc nó là một OBJECT LITERAL, và cả tệp thôi phân tích
                được. `tsc` báo "JSX expressions must have one parent element" rồi kéo theo tám
                lỗi cú pháp nữa; `next build` chết, nên Vercel không ra bản mới.
                Lọt vào kho được vì việc `web` của CI CHỈ chạy trên PR, không chạy khi đẩy vào
                main — đúng lỗ hổng Đợt LE2e đã ghi ngày 10/10: đợt nào chạm `web/` thì phải chạy
                `npm run build` trước khi đẩy. */}
            {menuToi && (
              <span role="menu" className="menu-toi" onClick={() => setMenuToi(false)}
                style={{ position: "absolute", right: 0, top: "100%", zIndex: 40, minWidth: 220,
                         display: "flex", flexDirection: "column", gap: 2,
                         background: "var(--vtos-card)", color: "var(--vtos-text)",
                         border: "1px solid var(--vtos-line)", borderRadius: 6, padding: 6,
                         boxShadow: "0 6px 18px rgba(0,0,0,.15)" }}>
                {caNhan.map(([l, h]) => lien(l, h))}
                <a href="/login" onClick={() => clearSession()}>Thoát</a>
              </span>
            )}
          </span>
        </span>
      </div>
      <div className="shell">
        {!khongThanhBen && <aside className={"side" + (side ? "" : " hide") + (thu ? " thu" : "")}>
          {/* Nút thu/bung. §I.2: rộng 224–240px, thu còn 56–64px. Ẩn trên màn hình nhỏ vì ở đó thanh
              dọc đã đóng mở bằng nút ☰ – hai cách thu cùng lúc là hai cách mâu thuẫn nhau. */}
          <button type="button" className="thu-nut" onClick={doiThu}
            title={thu ? "Bung thanh menu" : "Thu thanh menu"}
            aria-label={thu ? "Bung thanh menu" : "Thu thanh menu"} aria-expanded={!thu}>
            {thu ? "»" : "«"}
          </button>
          {groups.map((g) => (
            <div key={g.key} className="nhom">
              {/* BẤM LÀ ĐI, KHÔNG PHẢI BUNG (anh Tuấn chốt phương án B, 13/9/2026). Mỗi thanh phân
                  hệ là một đường dẫn tới TRANG PHÂN HỆ – nơi vẽ đủ cây chức năng theo bản vẽ v1.3,
                  mục nào đã có trang và mục nào còn nợ. Trước đây bấm thì ghim mở danh sách tại
                  chỗ; bỏ cách ấy vì một thanh không thể vừa đi vừa bung, và vì cây v1.3 sâu bốn cấp
                  với hơn một trăm mục chưa dựng – thanh dọc chốt tối đa hai cấp, không chứa nổi.

                  TC-70 · 18/9/2026 – LUẬT NÀY NAY CÓ NGOẠI LỆ, không bị bỏ. Sáu nhóm vẫn "bấm là
                  đi" y như 13/9. Hai nhóm Kinh doanh và Điều hành xổ ra, vì chúng không còn đại
                  diện cho MỘT phòng nữa (xem chú thích ở `type Group`). Lý do 13/9 – một thanh
                  không thể vừa đi vừa bung – vẫn đúng, và chính vì nó đúng nên mỗi nhóm vẫn chỉ
                  làm MỘT việc, không có nhóm nào vừa đi vừa bung.

                  Khi THU thì chỉ còn biểu tượng, nhãn nhóm đi vào title và aria-label chứ không mất
                  (§I.2: "biểu tượng phải có chú thích"). */}
              {g.phans
                ? <NhomXo g={g} thu={thu} dangO={dangO(g)} dongThanhDoc={() => setSide(false)} />
                : <Link href={g.href!} className={"grp" + (dangO(g) ? " on" : "")}
                    title={g.label} aria-label={g.label}
                    onClick={() => setSide(false)}>
                    {thu ? <span className="bt"><Hinh ten={g.icon} /></span>
                         : <><Hinh ten={g.icon} /><span className="grp-ten">{g.label_ngan || g.label}</span></>}
                  </Link>}
            </div>
          ))}
        </aside>}
        <main>{children}</main>
      </div>
      {t && <div className={"toast" + (t.err ? " err" : "")} role="status">{t.msg}</div>}
    </Ctx.Provider>
  );
}
