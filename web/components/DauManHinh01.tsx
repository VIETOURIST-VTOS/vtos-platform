"use client";
/** MÀN HÌNH 01 – phần đầu theo bản vẽ "Bảng điều hành Chủ tịch" V1.2 (12/9/2026).
 *
 *  Ba khối, đúng thứ tự bản vẽ:
 *    01  Phạm vi · kỳ báo cáo · thời điểm cập nhật
 *    02  Cần quyết định – tối đa 5 hồ sơ
 *    03  Tám thẻ chỉ tiêu kinh doanh & vận hành
 *
 *  BẢN TGĐ (SEC-02) KHÔNG PHẢI MỘT MÀN HÌNH KHÁC. Cùng một trang, đổi ba thứ: tên trang theo vai,
 *  nhãn phạm vi, và tập dòng do MÁY CHỦ cắt. Ở đây tuyệt đối không có câu nào kiểu
 *  `if (vai === "tgd") ẩn ...`: dòng bị ẩn ở trình duyệt thì vẫn đã rời khỏi máy chủ, ai mở công cụ
 *  nhà phát triển cũng đọc được – SEC-02 gọi đó là lỗi đỏ, và test_tc8 canh đúng chỗ ấy.
 *
 *  RANH GIỚI 09/9 GIỮ NGUYÊN: thẻ nào máy chủ chưa có nguồn thì ghi "Chưa có nguồn" kèm CỬA NHẬP –
 *  đường dẫn tới màn hình mà bộ phận phụ trách gõ số vào. Không lấy 0 thay cho "chưa ai nhập".
 */
import Link from "next/link";
import { useEffect, useState } from "react";
import { vnd } from "@/lib/api";

/** Tên trang theo vai. Bản vẽ V1.2 vẽ cho Chủ tịch; anh Tuấn chốt 12/9 làm luôn bản TGĐ. */
const TEN_TRANG: Record<string, string> = {
  chutich: "Bàn làm việc Chủ tịch HĐQT",
  tgd: "Bảng điều hành Tổng giám đốc",
};

/** Màn hình 01 CHỈ hiển thị theo THÁNG (anh Tuấn chốt 13/9/2026). Quý và năm xem ở báo cáo chi
 *  tiết, không nhét vào đây.
 *
 *  Vì sao không để một ô chọn có sẵn ba mức: /dashboard mới tính theo tháng. Một ô chọn có "Quý"
 *  và "Năm" mà bấm vào chỉ ra "chưa có nguồn" là một lời hứa suông ngay trên màn hình đầu tiên –
 *  thà nói thẳng chỗ xem quý và năm nằm ở đâu. */

/** Một thẻ chỉ tiêu.
 *  `so` là null nghĩa là CHƯA CÓ NGUỒN – khác hẳn 0. Khi ấy thẻ đòi `cua` (đường dẫn cửa nhập) và
 *  `ai` (bộ phận phải nhập), để người đọc biết đi hỏi ai chứ không chỉ thấy một ô trống. */
export type The = {
  nhan: string; phu?: string; so: string | null; duoi?: string;
  /** TC-98 · đường tới trang chi tiết; có thì thẻ có số hiện nút "Xem chi tiết →". */
  chi_tiet?: string;
  cua?: string; ai?: string; do?: boolean;
  xu_huong?: XuHuong | null;
};

/** TC-36 · Chuỗi xu hướng của một thẻ. Máy chủ (`services/xu_huong.py`) đã quyết xong ba việc khó
 *  — lấy kỳ nào, kỳ nào rỗng, có đủ điểm để vẽ không — nên màn hình chỉ vẽ, không tự xét. */
export type XuHuong = {
  ten?: string; dinh_dang?: string;
  diem: { ky: string; gia_tri: number | null }[];
  du_ve: boolean; so_ky_co_so?: number; vi_sao?: string;
  so_sanh?: { ky: string; ky_truoc: string; chenh: number;
              phan_tram: number | null; tang: boolean; giam: boolean } | null;
};

/** Tên kỳ "2026-08" → "08/2026". Đọc "2026-08" trên nhãn cột thì phải dịch trong đầu mỗi lần. */
const tenKy = (ky: string) => { const [y, m] = ky.split("-"); return `${m}/${y}`; };

/* TC-42 (16/9/2026) – câu đọc hộ phần kế hoạch RỜI khỏi tệp này.
   Nó theo hai ô lớn Doanh thu và Lợi nhuận sang components/KhoiSauO.tsx, nơi nó thành
   `docHoKeHoachKy` và biết thêm một việc mà bản cũ không biết: kế hoạch CHỈ có cho kỳ tháng, nên
   bấm sang Quý thì phải nói ra điều đó thay vì im lặng vẽ một vạch mốc dựng từ kế hoạch tháng.
   Giữ lại một bản ở đây là để hai bản cùng nói về một con số, và ngày chúng lệch nhau thì màn
   hình có hai câu trả lời cho cùng một câu hỏi. */

/** BIỂU ĐỒ NHỎ TRÊN THẺ — cột, không phải đường.
 *
 *  Vì sao CỘT: chuỗi này có ô trống thật (kỳ chưa ai lưu báo cáo), và ô trống là chuyện bình
 *  thường chứ không phải ngoại lệ. Đường gấp khúc phải hoặc nối liền qua chỗ trống — tức bịa ra
 *  một đoạn dữ liệu — hoặc đứt quãng trông như lỗi vẽ. Cột thì kỳ nào không có số là chỗ ấy trống,
 *  đọc ra ngay và không gây hiểu nhầm.
 *
 *  MỘT DÃY, KHÔNG CHÚ GIẢI: cả biểu đồ chỉ có một chỉ tiêu, và tên nó là tên thẻ ngay phía trên.
 *  Thêm một hộp chú giải ghi lại đúng cái tên ấy là thêm chữ mà không thêm tin.
 *
 *  KHÔNG GHI SỐ TRÊN TỪNG CỘT: sáu con số nhỏ chen nhau thì không đọc được cái nào. Con số lớn của
 *  kỳ đang chạy đã nằm ngay trên; từng kỳ xem bằng cách rê chuột.
 */
function BieuDoNho({ xh }: { xh: XuHuong }) {
  const diem = xh.diem || [];
  if (!xh.du_ve) {
    return <div className="the-xh-rong muted">{xh.vi_sao || "Chưa đủ dữ liệu để vẽ xu hướng."}</div>;
  }
  const v = diem.map((d) => d.gia_tri).filter((x): x is number => x !== null);
  const max = Math.max(...v, 0), min = Math.min(...v, 0);
  const bien = max - min || 1;
  const H = 30;
  // Mốc 0 nằm đúng chỗ của nó. Vẽ mọi cột từ đáy khung thì một kỳ LỖ trông như một kỳ lãi ít.
  const y0 = Math.round(H * (max / bien));
  const ss = xh.so_sanh;
  return (
    <div className="the-xh">
      <div className="the-xh-cot" style={{ height: H }}>
        {/* MỖI KỲ MỘT Ô RIÊNG, và thanh định vị TRONG ô ấy. Bản đầu đặt thanh định vị tuyệt đối
            thẳng trong lưới: thanh bị nhấc khỏi dòng lưới nên cả sáu thanh trải hết bề ngang và
            chồng lên nhau thành MỘT vệt dài. Dựng ra ảnh mới thấy — đọc mã thì trông vẫn đúng. */}
        {diem.map((d) => {
          // Ô TRỐNG THẬT vẫn chừa đúng chỗ của nó. Bỏ ô đi thì sáu kỳ trông như bốn kỳ liền nhau
          // và khoảng cách thời gian bị bóp méo.
          if (d.gia_tri === null) {
            return <span key={d.ky} className="the-xh-o" title={`${tenKy(d.ky)}: chưa có số`} />;
          }
          const cao = Math.max(2, Math.round((Math.abs(d.gia_tri) / bien) * H));
          const am = d.gia_tri < 0;
          return (
            <span key={d.ky} className="the-xh-o"
              title={`${tenKy(d.ky)}: ${d.gia_tri.toLocaleString("vi-VN")}`}>
              <span className={"the-xh-thanh" + (am ? " am" : "")}
                style={{ height: cao, top: am ? y0 : y0 - cao }} />
            </span>
          );
        })}
        <span className="the-xh-truc0" style={{ top: y0 }} />
      </div>
      {/* TC-40 · ĐỌC HỘ THÀNH CÂU, không chỉ một mũi tên và một tỉ lệ.
          Anh Tuấn chốt 15/9/2026: tám thẻ phải có "biểu đồ và số + phân tích". Bản cũ in
          "▲ 25.0% 08/2026 so với 07/2026" — đúng nhưng phải tự dịch trong đầu, và khi phần trăm
          không tính được (kỳ trước bằng 0) thì nó ra "= —", đọc như một lỗi hiển thị.

          Câu ở đây chỉ DIỄN ĐẠT LẠI con số máy chủ đã tính (`so_sanh`), không tính thêm gì —
          ranh giới 09/9 giữ nguyên. Chênh lệch TUYỆT ĐỐI luôn nói được, kể cả khi phần trăm
          không tồn tại; nên nó đứng trước, và phần trăm chỉ là phần trong ngoặc.

          MŨI TÊN ĐI KÈM CHỮ, không chỉ có màu: người không phân biệt được đỏ–xanh vẫn phải đọc
          được chiều. Và ghi rõ so với KỲ NÀO — "so với kỳ trước" mà không nói kỳ nào là một câu
          không kiểm được. */}
      {ss && <div className="the-xh-ss">
        <span className={"the-xh-mui" + (ss.tang ? " tang" : ss.giam ? " giam" : "")}>
          {ss.tang ? "▲ tăng" : ss.giam ? "▼ giảm" : "= không đổi"}
        </span>
        {typeof ss.chenh === "number" && ss.chenh !== 0 && (
          <span className="the-xh-chenh"> {Math.abs(ss.chenh).toLocaleString("vi-VN")}</span>
        )}
        {ss.phan_tram !== null && ss.phan_tram !== undefined && (
          <span className="muted"> ({Math.abs(ss.phan_tram * 100).toFixed(1)}%)</span>
        )}
        <span className="muted"> so với {tenKy(ss.ky_truoc)}</span>
      </div>}
    </div>
  );
}

export function TheChiTieu({ t }: { t: The }) {
  const rong = t.so === null;
  return (
    <div className={"the-ct" + (rong ? " rong" : "")}>
      <div className="the-nhan">{t.nhan}</div>
      {t.phu && <div className="the-phu">{t.phu}</div>}
      <div className={"the-so" + (t.do ? " do" : "")}>{rong ? "—" : t.so}</div>
      {rong
        ? <div className="the-thieu">
            <span className="tag">Chưa có nguồn</span>
            {t.ai && <span className="muted"> · {t.ai} nhập</span>}
            {t.cua && <Link className="the-cua" href={t.cua}>Cửa nhập →</Link>}
          </div>
        : t.duoi && <div className="the-duoi">{t.duoi}</div>}
      {!rong && t.chi_tiet && <Link className="the-cua the-chi-tiet" href={t.chi_tiet}>Xem chi tiết →</Link>}
      {/* Biểu đồ đặt DƯỚI dòng mô tả: con số lớn vẫn là thứ đọc trước, xu hướng là thứ đọc sau.
          Thẻ chưa có số thì cũng chưa có xu hướng — không vẽ một dãy cột rỗng dưới một ô trống. */}
      {!rong && t.xu_huong && <BieuDoNho xh={t.xu_huong} />}
    </div>
  );
}

/** Ngày báo cáo = NGÀY HÔM NAY THEO LỊCH MÁY (anh Tuấn chốt 12/9), lấy trong useEffect chứ không
 *  tính lúc dựng: tính lúc dựng thì bản vẽ ở máy chủ và bản vẽ ở trình duyệt lệch nhau một nhịp và
 *  React kêu hydration mismatch – lỗi chỉ hiện trong console, không ai thấy. */
export function useHomNay(): string {
  const [s, setS] = useState("");
  useEffect(() => {
    const d = new Date();
    setS(d.toLocaleDateString("vi-VN", { weekday: "long", day: "2-digit", month: "2-digit", year: "numeric" }));
  }, []);
  return s;
}

/** Nhãn tháng báo cáo, lấy từ lịch máy. */
export function tenThang(): string {
  const d = new Date();
  return `Tháng ${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
}

/* TC-62 · `DongLoc` ĐÃ XOÁ — anh Tuấn chốt 18/9/2026: "gộp thành 1 thanh ngang, bỏ bớt chú
   thích không quan trọng".

   Trước vòng này đầu trang là BA tầng: dòng đường dẫn (VTOS / Không gian lãnh đạo / …), tầng tiêu
   đề kèm câu phụ "Kết quả · Phải thu · Phải trả · Dòng tiền · Quyết định", rồi hàng lọc. Ba tầng
   ấy cao gần bằng một khối số thật, mà không tầng nào mang một con số nào.

   Nay cả ba gộp vào `TieuDe` thành MỘT thanh. Thứ bỏ hẳn: dòng đường dẫn (tên trang lặp lại ngay
   dòng dưới), câu phụ liệt kê các khối (cuộn xuống là thấy chúng), và nhãn "Đơn vị tiền: đồng"
   (mọi con số trên màn hình đều là đồng và đã định dạng sẵn).

   XOÁ chứ không để lại hàm không ai gọi — cùng bài học với `O` ở TC-57 và bốn lớp CSS mồ côi ở
   TC-60: một thành phần không ai gọi vẫn qua mọi phép kiểm, và vòng sau có người dựng lại nó. */

/** ĐẦU TRANG — MỘT THANH NGANG DUY NHẤT (TC-62).
 *
 *  Thanh này mang đúng bốn thứ, và mỗi thứ phải trả lời được câu "bỏ đi thì ai mất gì":
 *
 *  1. TÊN TRANG — người mở lần đầu biết mình đang ở đâu.
 *  2. KỲ BÁO CÁO + cửa "Quý và năm →". Mọi con số bên dưới thuộc về kỳ ghi ở đây; không ghi ra
 *     thì hai người cùng nhìn một màn hình mà hiểu hai kỳ khác nhau.
 *  3. PHẠM VI + NGÀY BÁO CÁO. Ngày báo cáo là mốc phân nhóm của mọi bảng theo hạn ở dưới.
 *  4. NÚT IN / LƯU PDF — việc thật, không phải trang trí: Chủ tịch mang bảng này vào phòng họp.
 *     Kiểu in nằm ở globals.css; giấy là môi trường khác, không phải màn hình thu nhỏ.
 *
 *  BA NHÃN CHỮ ĐÃ XUỐNG CHỖ RÊ CHUỘT ("Kỳ báo cáo · Phạm vi · Ngày báo cáo"): chúng dài gần bằng
 *  chính ba giá trị chúng giới thiệu.
 *
 *  KHÔNG lấy huy hiệu "Giao diện xanh navy" ở góc phải bản vẽ: đó là nhãn của TÀI LIỆU THIẾT KẾ
 *  tự mô tả mình, dán lên trang thật thì thành một ô chữ không ai bấm được và không nói gì thêm.
 */
export function TieuDe({ vai, ten_vai, quyet_dinh }: {
  vai?: string; ten_vai?: string;
  /** TC-65 · Hồ sơ đang chờ chính người đang xem quyết. Xem chú thích dài ngay trên. */
  /** ĐỢT E12 13/10/2026 — một dòng có thể mang theo `chi_tiet` thay vì một đường dẫn. Dòng như
   *  thế KHÔNG phải việc chờ bấm mà là điều cần ĐỌC LẠI: bấm vào xổ ra ngay tại chỗ, không đi
   *  trang khác. Dẫn sang màn hình riêng thì phải mở một khoá menu mới, tức xin thêm quyền cho
   *  một loạt vai mà chưa ai ký — đúng cái việc bảng ấy sinh ra để canh. */
  quyet_dinh?: { href: string; label: string; chi_tiet?: any }[];
}) {
  const ten = TEN_TRANG[vai || ""] || `Bảng điều hành · ${ten_vai || ""}`;
  const cho = quyet_dinh || [];
  const homNay = useHomNay();
  /* ══ VH-24 · 12/11/2026 — Chủ tịch duyệt bản xem trước, chốt «1.1.1» ═══════════════════════════════
     "duyệt chi và công việc em đưa toàn bộ về [thanh ngang], hiện theo số khi có đề nghị mới; [đầu trang]
      em chỉ giữ BÀN LÀM VIỆC CHỦ TỊCH HĐQT to rõ và hiệu ứng ánh sáng giống của giám đốc đội xe, các ghi
      chú khác em bỏ hết"
     Nên đầu trang chỉ còn TÊN BÀN (in hoa, chuyển màu, vệt sáng lướt — cùng kiểu `/xe`) và MỘT ô ngày.
     Hàng nút việc chờ (TC-65), ô tháng, cửa sang quý/năm và nút in rời khỏi đây:
       · việc chờ lên hai nút «Công việc» / «Chờ duyệt» trên thanh ngang (Shell, `GET /dashboard/dem`);
       · in vẫn bằng Ctrl+P — kiểu in viết sẵn ở globals.css không đổi.
     Bảng ký quyền (dòng mang `chi_tiet`) là dòng ĐỂ ĐỌC: nút «Chờ duyệt» dẫn về `/#ky-quyen`, và khối đọc
     ấy mở ra ngay dưới tiêu đề khi địa chỉ mang neo đó. */
  const [xo, setXo] = useState<number | null>(null);
  useEffect(() => {
    const doc = () => {
      const i = window.location.hash === "#ky-quyen" ? cho.findIndex((a) => a.chi_tiet) : -1;
      setXo(i >= 0 ? i : null);
    };
    doc();
    window.addEventListener("hashchange", doc);
    return () => window.removeEventListener("hashchange", doc);
  }, [cho]);
  return (<>
    <div className="mh01-ban">
      <h1 className="mh01-ban-ten" title="Phạm vi: Vietourist — công ty mẹ">{ten}</h1>
      <div className="mh01-ban-ngay"><span>Hôm nay</span>{homNay || "…"}</div>
    </div>

    {/* ĐỢT E12 13/10/2026 — khối xổ ra của dòng đang mở. Nằm NGOÀI thanh ngang vì nó là một BẢNG,
        không phải một nút: nhét vào trong thanh thì thanh vỡ dòng trên màn hẹp. */}
    {xo !== null && cho[xo]?.chi_tiet && (() => {
      const d: any = cho[xo].chi_tiet;
      return (<div className="panel" style={{ margin: "8px 0 14px" }}>
        <h3 style={{ margin: "0 0 2px" }}>{d.ten}</h3>
        <p className="muted" style={{ margin: "0 0 10px" }}>{d.can_cu}</p>
        <div className="wrap"><table><tbody>
          <tr><td style={{ width: 230 }} className="muted">Vai được nới</td>
              <td><b>{d.ten_vai}</b> <span className="muted">({d.vai})</span></td></tr>
          <tr><td className="muted">Thấy mọi cửa của</td><td>{d.ten_vai_cha || "—"}</td></tr>
          <tr><td className="muted">Tổng cửa mở được</td>
              <td><b>{d.cua_tong}</b> <span className="muted">= {d.cua_dich_danh} cửa khai đích danh
              + {d.cua_mo_het} cửa mở cho mọi người đã đăng nhập</span></td></tr>
          <tr><td className="muted">Trong đó, nhờ MỘT dòng ký</td>
              <td><b>{d.cua_nho_ke_thua}</b> cửa <span className="muted">— khai ở {d.khai_o}</span></td></tr>
          <tr><td className="muted">Đảo lại quyết định</td><td className="muted">{d.dao_lai}</td></tr>
          <tr><td className="muted">Người ký · ngày</td><td>{d.nguoi_ky} · {d.ngay_ky}</td></tr>
        </tbody></table></div>
        <p className="muted" style={{ margin: "12px 0 4px" }}><b>{d.cua_luong_da_ky.length} cửa chạm
          DỮ LIỆU CÁ NHÂN</b> — bảng lương, hồ sơ nhân sự, BHXH, giảm trừ gia cảnh. {d.can_cu_cua_luong}.
          Khai thành danh sách chứ không để phép suy tự lo: một quyền mở ra do hệ quả của một dòng suy
          là một quyền không ai rà được, còn khai ra thì thêm một cửa lương nữa là phép thử ĐỎ chứ
          không lọt vào im lặng.</p>
        <div className="wrap"><table>
          <thead><tr><th style={{ width: 100 }}>Phương thức</th><th>Đường dẫn</th></tr></thead>
          <tbody>{d.cua_luong_da_ky.map((c: any, k: number) => (
            <tr key={k}><td className="mono">{c.phuong_thuc}</td><td className="mono">{c.duong_dan}</td></tr>
          ))}</tbody>
        </table></div>
      </div>);
    })()}
  </>
  );
}

/* ══════════════════════════════════════════════════════════════════════════════════════════════
   TC-65 · `KhoiQuyetDinh` ĐÃ XOÁ — hàng nút chờ quyết nhập vào `TieuDe` (anh Tuấn 18/9/2026:
   "gom lại thành 1 thanh ngang, bỏ chữ chờ chủ tịch quyết").

   LUẬT CŨ GIỮ NGUYÊN MỘT CHỮ, và phải giữ: KHÔNG GIỚI HẠN SỐ HỒ SƠ (anh Tuấn chốt 13/9/2026).
   Bản vẽ V1.2 ghi "tối đa 5 hồ sơ ưu tiên", nhưng cắt ở năm nghĩa là hồ sơ thứ sáu nằm ngoài tầm
   mắt người duy nhất được quyết nó — mà thứ tự ưu tiên thì máy chủ chưa xếp, nên "năm cái đầu"
   chỉ là năm cái ngẫu nhiên. `TieuDe` vì thế `map` toàn bộ danh sách, không `slice`.

   Thứ bỏ đi là BA dòng chữ giới thiệu: tiêu đề "Cần Chủ tịch quyết định", thẻ nhãn "N hồ sơ đang
   chờ", và câu "không có hồ sơ nào đang chờ ở vai trò này". Cái đầu lặp lại điều tên trang đã nói;
   cái thứ hai đếm đúng số nút đứng ngay cạnh nó; cái thứ ba in một câu "không có việc" mỗi ngày.

   XOÁ chứ không để lại hàm không ai gọi — cùng bài học với `O` ở TC-57 và `DongLoc` ở TC-62. */

/** Khối 03 – tám thẻ. Bản vẽ xếp hai hàng bốn thẻ trên màn rộng; ở đây để lưới tự xuống dòng theo
 *  bề rộng thật, vì khoá cứng bốn cột thì trên màn 1280px chữ bị cắt. */
/** HÀNG THẺ SỐ — đổi tên từ `TamThe` ngày 16/9/2026 (TC-42), và đổi tên là có lý do.
 *
 *  Anh Tuấn chuyển sáu trong tám thẻ thành sáu Ô LỚN có biểu đồ, năm mục còn lại xuống một hàng
 *  thẻ nhỏ. Một hàm tên `TamThe` mà bày năm thẻ là một lời nói dối nhỏ nằm ngay trong mã: người
 *  đọc mã ba tháng sau sẽ đếm tám và đi tìm ba thẻ không tồn tại. Số lượng thẻ nay là việc của nơi
 *  gọi, nên tên hàm không được nhắc tới nó nữa.
 */
export function HangThe({ ds }: { ds: The[] }) {
  return <div className="mh01-the">{ds.map((t) => <TheChiTieu key={t.nhan + (t.phu || "")} t={t} />)}</div>;
}

/** Số tiền cho thẻ: rỗng thì trả null để thẻ tự ghi "Chưa có nguồn", không in "0 đ". */
export function tien(x: any): string | null {
  return x === null || x === undefined || x === "" ? null : vnd(x);
}

/** Số đếm cho thẻ. Cùng quy ước: undefined là chưa có nguồn, 0 là đã đếm và bằng không. */
export function dem(x: any): string | null {
  return x === null || x === undefined || x === "" ? null : String(x);
}
