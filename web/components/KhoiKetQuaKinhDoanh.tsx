"use client";
/** KẾT QUẢ KINH DOANH — hai thẻ cạnh nhau, một bộ chọn kỳ dùng chung.
 *
 *  Dựng theo bản vẽ anh Tuấn gửi 16/9/2026: *"em điều chỉnh chart doanh thu và lợi nhuận trước
 *  thuế như bản vẽ và chọn đúng tông màu của VTOS, và áp dụng từ năm 2026 về sau"*.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  MỘT BỘ CHỌN KỲ CHO CẢ HAI THẺ — ĐÂY LÀ ĐIỀU QUAN TRỌNG NHẤT CỦA BẢN VẼ
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Bản cũ (TC-42) cho mỗi ô một bộ nút Tháng/Quý/Năm riêng. Nó chạy được, nhưng nó cho phép một
 *  trạng thái không ai muốn: doanh thu đang xem QUÝ còn lợi nhuận đang xem THÁNG, hai con số nằm
 *  cạnh nhau như thể so được với nhau. Không con số nào sai; cái sai là phép trừ mà người đọc tự
 *  làm trong đầu giữa chúng. Gộp thành MỘT bộ chọn là bỏ hẳn trạng thái ấy đi, chứ không phải dặn
 *  người dùng đừng rơi vào nó.
 *
 *  Vì cùng một kỳ, hai thẻ mới chia được với nhau con số thứ ba: BIÊN LỢI NHUẬN = lợi nhuận ÷
 *  doanh thu. Phép chia ấy chỉ có nghĩa khi tử và mẫu cùng kỳ — nên nó nằm được ở đây mà không
 *  nằm được ở bản cũ.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  HAI THANG ĐO RIÊNG, KHÔNG PHẢI HAI TRỤC TRÊN MỘT HÌNH
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Lợi nhuận nhỏ hơn doanh thu chừng mười lần. Vẽ chung một hình thì cột lợi nhuận dẹp thành một
 *  vạch sát đáy; vẽ chung một hình với hai trục tung thì chỗ hai đường cắt nhau là do người vẽ
 *  chọn thang chứ không do số liệu (luật 4 ở đầu components/BieuDo.tsx). Nên: HAI hình, mỗi hình
 *  một thang, và nói thẳng điều đó ở câu chân — chứ không để người đọc so chiều cao cột của hình
 *  này với hình kia.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  ĐƠN VỊ KHÔNG ĐỨNG MỘT CHỖ TRÊN ĐẦU TRỤC
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Bản vẽ ghi "Đơn vị: tỷ đồng" ở chân. Bộ biểu đồ VTOS đi xa hơn một bước: mỗi nhãn trục TỰ mang
 *  đơn vị của nó ("1,8 tỷ", "600 tr"), nên một chuỗi vắt qua hai bậc đơn vị vẫn đọc đúng — thứ mà
 *  một dòng "Đơn vị: tỷ đồng" cố định làm sai. Vì vậy không thêm nhãn đơn vị trên đầu trục: thêm
 *  vào là in đơn vị hai lần, và lần cố định ấy sẽ có ngày nói khác nhãn bên cạnh nó.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  TỆP NÀY KHÔNG TÍNH GÌ CẢ (ranh giới 09/9 giữ nguyên)
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Tổng kỳ, tỉ lệ đạt, biên lợi nhuận, đường kế hoạch, kỳ đang chạy: tất cả do
 *  `services/ket_qua_kinh_doanh.bang()` trả về. Ở đây chỉ chọn trường nào vào hình nào và diễn đạt
 *  lại thành câu. Kể cả NGÀY HÔM NAY cũng lấy từ máy chủ (`ky_hien_tai`), không đọc đồng hồ máy
 *  người dùng.
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { errMsg } from "@/components/ui";
import { BieuDoCot, ChuGiai, gonSo, type Diem } from "@/components/BieuDo";

type Ky = "thang" | "quy" | "nam";
const BA_KY: { ma: Ky; ten: string }[] = [
  { ma: "thang", ten: "Tháng" }, { ma: "quy", ten: "Quý" }, { ma: "nam", ten: "Năm" },
];

const CUA = "/ke-hoach-thang";

/** "2026-08" → "Tháng 8/2026" · "2026-Q3" → "Quý 3/2026" · "2026" → "Năm 2026". */
function tenKyDai(ky: string): string {
  const s = String(ky);
  if (s.includes("-Q")) { const [y, q] = s.split("-Q"); return `Quý ${q}/${y}`; }
  if (s.includes("-")) { const [y, m] = s.split("-"); return `Tháng ${Number(m)}/${y}`; }
  return `Năm ${s}`;
}

/** Số thứ tự của kỳ trong năm: tháng 1–12, quý 1–4, năm thì 1. */
function soTrongNam(ky: string): number {
  const s = String(ky);
  if (s.includes("-Q")) return Number(s.split("-Q")[1]);
  if (s.includes("-")) return Number(s.split("-")[1]);
  return 1;
}

/** Ghép lại mã kỳ từ ba mảnh. Định dạng phải KHỚP máy chủ ("2026-09", "2026-Q3", "2026") — máy
 *  chủ từ chối mã sai bề rộng bằng lỗi 422 chứ không đoán hộ, nên chỗ ghép là chỗ duy nhất. */
function ghepKy(kind: Ky, nam: number, so: number): string {
  if (kind === "nam") return String(nam);
  if (kind === "quy") return `${nam}-Q${so}`;
  return `${nam}-${String(so).padStart(2, "0")}`;
}

/** Số kỳ con mà năm ấy ĐÃ CÓ: năm đã qua thì đủ 12 tháng / 4 quý, năm đang chạy thì chỉ tới kỳ
 *  hiện tại. Bày ra tháng 11 khi đang là tháng 9 là dẫn người ta tới một hình rỗng. */
function soKyCua(kind: Ky, nam: number, ky_hien_tai: string): number {
  const day = kind === "quy" ? 4 : 12;
  const nam_nay = Number(String(ky_hien_tai).slice(0, 4));
  if (nam < nam_nay) return day;
  if (nam > nam_nay) return 1;
  return soTrongNam(ky_hien_tai);
}

function tenKyCon(kind: Ky, so: number): string {
  return kind === "quy" ? `Quý ${so}` : `Tháng ${so}`;
}

/** Phần trăm đọc được: 1,0217 → "102,2%". Một chữ số lẻ, vì chữ số thứ hai không đổi được quyết
 *  định nào mà lại làm con số dài thêm. */
function phanTram(x: number | null | undefined): string | null {
  if (x === null || x === undefined) return null;
  return `${(x * 100).toLocaleString("vi-VN", { maximumFractionDigits: 1 })}%`;
}

/** Mười hai cột của một chỉ tiêu.
 *
 *  GHI SỐ Ở BỐN CỘT ĐÁNG CHÚ Ý — Chủ tịch chốt 12/10/2026.
 *
 *  Trước hôm nay chỉ ghi ở cột ĐẦU và cột CUỐI của kỳ. Lý do cũ vẫn đúng và vẫn giữ: mười hai con
 *  số chen nhau trên một khung rộng 400px thì không đọc được cái nào. Nhưng hai con số ấy chỉ trả
 *  lời "kỳ này bắt đầu ở đâu, kết thúc ở đâu" — còn câu người điều hành hỏi trước tiên khi nhìn
 *  một dãy mười hai cột là "tháng nào cao nhất, tháng nào thấp nhất". Chiều cao cột cho thấy cột
 *  nào cao, nhưng KHÔNG cho biết cao bao nhiêu, và đó đúng là lúc người ta phải rê chuột từng cột.
 *
 *  Nên thêm CAO NHẤT và THẤP NHẤT. Bốn, không phải mười hai: bốn con số trên mười hai vị trí thì
 *  khoảng cách tối thiểu giữa hai nhãn vẫn đủ rộng ở khung hẹp nhất.
 *
 *  CHỈ GHI SỐ, KHÔNG GHI CHỮ (Chủ tịch chốt cùng ngày, sau khi xem bản dựng thử). Bản dựng thử có
 *  thêm chữ ĐẦU · CUỐI · CAO NHẤT · THẤP NHẤT dưới mỗi số để nói vì sao cột ấy được chọn; Chủ tịch
 *  bỏ. Con số tự nói được, còn bốn mẩu chữ thì chiếm đúng chỗ mà hình cần để thở.
 *
 *  `Set` KHÔNG phải để cho gọn: một tháng có thể vừa là cột cuối vừa là cột thấp nhất — đúng cảnh
 *  tháng 10/2026, tháng mới chạy được một phần. Lúc ấy phải ra MỘT nhãn, không phải hai nhãn chồng
 *  khít lên nhau thành một vệt chữ không đọc nổi.
 *
 *  Dùng VỊ TRÍ cột làm mốc, không dùng số tháng: nhãn "cuối" tự chạy theo dữ liệu, nên tháng sau
 *  khi T11 có chuyến khởi hành thì nó tự nhảy sang T11 mà không ai phải sửa một dòng nào.
 */
function diemTu(ct: any, cot2?: any): Diem[] {
  const cot: any[] = ct?.cot || [];
  const trong = cot
    .map((c, i) => i)
    .filter((i) => cot[i].trong_ky && cot[i].gia_tri !== null && cot[i].gia_tri !== undefined);
  const ghi = new Set<number>();
  if (trong.length) {
    const gt = (i: number) => Number(cot[i].gia_tri);
    // Vòng lặp thường, KHÔNG dùng `reduce` — và đây là một lựa chọn, không phải thói quen.
    // `test_tc42_sau_o_lon` cấm `reduce(` trên hai tệp này để màn hình không tự GỘP số nghiệp vụ.
    // Phép chọn dưới đây không gộp gì: nó so sánh rồi trả về một VỊ TRÍ CỘT, không đẻ ra con số
    // nào. Nhưng hàng rào ấy soi theo chữ, nên viết `reduce` ở đây là bắt người sau phải phân biệt
    // hai thứ trông giống hệt nhau — và sớm muộn có người phân biệt sai theo chiều nguy hiểm.
    let cao = trong[0];
    let thap = trong[0];
    for (const i of trong) {
      if (gt(i) > gt(cao)) cao = i;
      if (gt(i) < gt(thap)) thap = i;
    }
    ghi.add(trong[0]);
    ghi.add(trong[trong.length - 1]);
    ghi.add(cao);
    ghi.add(thap);
  }
  const kh: (number | null)[] | null = ct?.ke_hoach || null;
  // TC-47 · `cot2` là chỉ tiêu thứ hai của CÙNG hình dưới (lợi nhuận trước thuế đứng cạnh lợi
  // nhuận tour). Ghép ở đây, theo VỊ TRÍ tháng, chứ không ghép ở máy chủ: máy chủ trả mỗi chỉ tiêu
  // một dãy độc lập, và dãy nào cũng đủ 12 tháng — nên vị trí i của hai dãy chắc chắn cùng tháng.
  const c2: any[] = cot2?.cot || [];
  return cot.map((c, i) => ({
    nhan: `T${c.thang}`,
    gt: c.gia_tri === null || c.gia_tri === undefined ? null : Number(c.gia_tri),
    ghi: `Tháng ${c.thang}`,
    mo: !c.trong_ky,
    nhan_so: ghi.has(i),
    ke_hoach: kh && kh[i] !== null && kh[i] !== undefined ? Number(kh[i]) : null,
    cho: c.cho === null || c.cho === undefined ? null : Number(c.cho),
    gt2: c2[i] && c2[i].gia_tri !== null && c2[i].gia_tri !== undefined
      ? Number(c2[i].gia_tri) : null,
  }));
}

/* ══════════════════════════════════════════════════════════════════════════════════════════════
 * TC-49 · MỘT LUẬT BỊ ĐẢO CHIỀU — GHI RA ĐÂY ĐỂ VÒNG SAU KHÔNG LẶNG LẼ ĐẢO NGƯỢC LẠI
 * ══════════════════════════════════════════════════════════════════════════════════════════════
 * Chỗ này từng có hằng `CHUA_VE` và hai nhánh `duVeCot(...) ? <BieuDoCot/> : <p>{CHUA_VE}</p>`,
 * kèm lý do của luật TC-40: "HỎI TRƯỚC KHI VẼ, chứ không để bộ biểu đồ dựng khung rỗng của nó —
 * ô số ngay trên đã ghi '—' kèm bộ phận và cửa nhập rồi, một khung rỗng nói lại điều ấy cách đó
 * bốn chục pixel là hai khung nói cùng một chuyện."
 *
 * Lý do ấy ĐÚNG khi chỉ MỘT khối chưa có số: lúc ấy khung rỗng đúng là thừa.
 * Nó SAI khi CẢ MÀN HÌNH chưa có số — và đó mới là tình trạng thật của VTOS hôm nay.
 *
 * Anh Tuấn mở trang thật ngày 17/9/2026: "trên màn hình chưa có biểu đồ, và giao diện chưa giống
 * file ảnh anh gửi". Cả hai vế đều từ luật cũ mà ra: mọi khối cùng lúc co lại thành văn xuôi, và
 * bảng điều hành không còn ra hình dáng một bảng điều hành. Anh duyệt bản thử giao diện rồi chốt
 * "đưa lên web đúng y chang vậy".
 *
 * NÊN: luôn vẽ hình. Chưa có số thì `BieuDoCot` tự trả khung rỗng mang đủ mười hai nhãn tháng.
 * Ranh giới 09/9 KHÔNG hề bị nới — khung rỗng không có cột nào cao lên, không con số nào được
 * bịa; nó chỉ giữ chỗ và nói ai nạp, cửa nào.
 */

/** Con số lớn của một thẻ, kèm kỳ của nó.
 *
 *  ══════════════════════════════════════════════════════════════════════════════════════════════
 *  TC-62 · BA CÂU ĐỌC HỘ XUỐNG CHỖ RÊ CHUỘT — anh Tuấn chốt 18/9/2026
 *  ══════════════════════════════════════════════════════════════════════════════════════════════
 *  "bỏ bớt chú thích không quan trọng … chỉ giữ lại chữ kế hoạch tháng và mũi tên để cho CHỦ TỊCH
 *  nhập vào."
 *
 *  Trước vòng này mỗi con số kéo theo một câu dài bên dưới ("Đi được 87% mục tiêu 52 tỷ · còn 3
 *  tháng", "Biên lợi nhuận 20%", "Thu trừ chi của chính những chuyến đã đóng số…"). Ba câu ấy cộng
 *  lại dài hơn cả ba con số chúng chú thích, và chúng đứng đúng giữa con số và cái hình — tức là
 *  chen vào giữa hai thứ người ta mở màn hình ra để xem.
 *
 *  KHÔNG XOÁ NỘI DUNG, CHỈ ĐỔI CHỖ ĐỨNG. Mục tiêu kỳ, tỉ lệ đạt, biên lợi nhuận đều là SỐ THẬT do
 *  máy chủ trả về; xoá hẳn là bỏ mất một câu trả lời, đúng cái mà luật "rỗng khác không" chặn. Nên
 *  chúng thành `title` trên chính con số: rê chuột lên "45,06 tỷ" là đọc được kỳ ấy so với kế
 *  hoạch thế nào, còn màn hình thì chỉ còn con số và cái hình.
 */
/** LN-1 (21/10/2026) — Ô RỖNG NÓI NGAY TRONG Ô VÌ SAO, thay cho một dấu gạch trần.
 *
 *  Đo trên hệ thật sáng 21/10: ô «Lợi nhuận trước thuế» in «—» đứng cạnh 26,7 tỷ, không một chữ
 *  nào nói vì sao. Lý do THẬT có sẵn trong dữ liệu (`con_thieu.thang_chua_ghi_so`) và ĐÃ được in
 *  ra — nhưng in ở dòng ghi chú `.kqkd-thieu`, mà màn hình Chủ tịch ẩn hết ghi chú theo đúng lệnh
 *  anh Tuấn chốt 29/9/2026 ("trên màn hình chủ tịch em xoá hết các ghi chú"). Nên câu trả lời bị
 *  ẩn cùng mọi thứ khác, và còn lại một dấu gạch đọc ra như ô hỏng.
 *
 *  Đây đúng vòng HQ-1b đã chữa cho ô Công suất khai thác hôm 13/10: câu trả lời phải nằm TRONG
 *  chính ô ấy, không nằm ở một dòng chữ bên cạnh — dòng chữ thì ẩn được, ô thì không.
 *
 *  `thieu` rỗng thì ô vẫn in dấu gạch như cũ: rỗng-vì-lý-do-khác là chuyện khác, và bịa một câu
 *  giải thích cho nó còn tệ hơn dấu gạch. */
type ThieuOSo = { ai: string; vi_sao: string; cua: string };

function OSo({ gt, nhan, chu, thieu }: {
  gt: number | null; nhan: string; chu: string; thieu?: ThieuOSo | null;
}) {
  return (
    <div className="o6-so" title={chu}>
      {gt === null && thieu ? (
        // Cỡ chữ đặt tại chỗ, KHÔNG thêm lớp vào globals.css: tệp ấy đang có làn khác giữ, và
        // một dòng CSS cho đúng một ô thì ở ngay cạnh ô ấy dễ đọc hơn là ở cuối một tệp 1.500 dòng.
        <Link className="the-cua" href={thieu.cua} style={{ fontSize: "calc(15/14*1rem)" }}>
          chờ {thieu.ai}<span className="muted"> · {thieu.vi_sao}</span>
        </Link>
      ) : (
        <b className={"o6-lon" + (gt === null ? " rong" : "")}>
          {gt === null ? "—" : gonSo(gt, "tien")}
        </b>
      )}
      <span className="muted o6-nhan">{nhan}</span>
    </div>
  );
}

export default function KhoiKetQuaKinhDoanh() {
  const [kind, setKind] = useState<Ky>("nam");
  // `ky === ""` nghĩa là "để máy chủ chọn kỳ đang chạy". Không tự dựng mã kỳ từ đồng hồ máy người
  // dùng: máy ấy có thể sai ngày, và một màn hình điều hành lệch một tháng thì không ai phát hiện.
  const [ky, setKy] = useState<string>("");
  const [d, setD] = useState<any>(null);
  const [loi, setLoi] = useState<string>("");

  useEffect(() => {
    let bo = false;
    setLoi("");
    api(`/bao-cao/ket-qua-kinh-doanh?kind=${kind}${ky ? `&ky=${encodeURIComponent(ky)}` : ""}`)
      // KHÔNG chép `r.ky` ngược vào ô trạng thái: `ky` là câu HỎI gửi đi, `d.ky` là câu TRẢ LỜI
      // nhận về. Chép ngược lại thì mỗi lần đổi bề rộng phải gọi máy chủ hai lượt — lượt hai chỉ để
      // hỏi lại đúng điều vừa được trả lời.
      .then((r) => { if (!bo) setD(r); })
      .catch((e) => { if (!bo) setLoi(errMsg(e) || "Không tải được kết quả kinh doanh"); });
    return () => { bo = true; };
  }, [kind, ky]);

  // ĐỔI BỀ RỘNG THÌ TRẢ KỲ VỀ CHO MÁY CHỦ CHỌN LẠI. Giữ nguyên năm rồi tự suy ra quý tương ứng là
  // việc đoán: bấm từ "Tháng 9" sang "Quý" thì Quý 3 hay quý gần nhất đã đóng? Máy chủ có đúng một
  // câu trả lời cho câu ấy (`ky_mac_dinh`), và để nó trả lời thì cả hệ thống chỉ có một luật.
  const doiKind = (k: Ky) => { setKind(k); setKy(""); };

  const nam = d?.nam;
  const ky_ht: string = d?.ky_hien_tai || "";
  const so_nay = d ? soTrongNam(d.ky) : 1;
  const so_toi_da = d && nam ? soKyCua(kind, nam, ky_ht) : 1;

  const doiNam = (n: number) => setKy(ghepKy(kind, n, Math.min(so_nay, soKyCua(kind, n, ky_ht))));
  const doiSo = (s: number) => setKy(ghepKy(kind, nam, s));

  const dieu_khien = (
    <div className="kqkd-dieu">
      <div className="v14-ky" role="group" aria-label="Bề rộng kỳ của khối Kết quả kinh doanh">
        {BA_KY.map((k) => (
          <button key={k.ma} type="button"
            className={"v14-ky-nut" + (kind === k.ma ? " chon" : "")}
            aria-pressed={kind === k.ma} onClick={() => doiKind(k.ma)}>{k.ten}</button>
        ))}
      </div>
      {d && (
        <>
          <label className="kqkd-chon">
            <span className="muted">Năm</span>
            <select value={nam} onChange={(e) => doiNam(Number(e.target.value))}>
              {(d.nam_chon_duoc || [nam]).map((n: number) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </label>
          {/* Ô chọn kỳ con KHÔNG có nhãn hiện ra, chỉ có aria-label: từng lựa chọn đã mang sẵn chữ
              "Quý 3" / "Tháng 9", nên một nhãn "Quý" đứng cạnh đọc thành "Quý Quý 3". */}
          {kind !== "nam" && (
            <label className="kqkd-chon">
              <select value={so_nay} aria-label={kind === "quy" ? "Quý" : "Tháng"}
                onChange={(e) => doiSo(Number(e.target.value))}>
                {Array.from({ length: so_toi_da }, (_, i) => i + 1).map((s) => (
                  <option key={s} value={s}>{tenKyCon(kind, s)}</option>
                ))}
              </select>
            </label>
          )}
        </>
      )}
    </div>
  );

  if (loi || !d) {
    return (
      <section className="panel" id="ket-qua-kinh-doanh">
        {/* MỘT KHUNG khi chưa có gì để bày, HAI KHUNG khi đã có — vì lúc chưa tải được thì hai
            khung rỗng cạnh nhau chỉ nói lại cùng một câu "đang tải" hai lần. */}
        <div className="mh01-dau"><h2>Doanh thu và lợi nhuận</h2></div>
        {dieu_khien}
        {loi
          ? <p className="muted">
              <span className="tag">Chưa kết nối</span> {loi}{" "}
              <Link className="the-cua" href={CUA}>Kế hoạch tháng →</Link>
            </p>
          : <p className="muted">Đang tải…</p>}
      </section>
    );
  }

  const ct: any[] = d.chi_tieu || [];
  const dt = ct.find((c) => c.ma === "doanh_thu");
  const lt = ct.find((c) => c.ma === "loi_nhuan_tour");
  const ln = ct.find((c) => c.ma === "loi_nhuan_truoc_thue");
  const tong = d.tong_ky || {};
  const soTong = (x: any) => (x === null || x === undefined ? null : Number(x));
  const so_dt = soTong(tong.doanh_thu);
  const so_lt = soTong(tong.loi_nhuan_tour);
  const so_ln = soTong(tong.loi_nhuan_truoc_thue);
  const th = d.con_thieu || {};

  // "ĐẾN HÔM NAY" PHẢI ĐI KÈM CON SỐ CỦA KỲ ĐANG CHẠY, không phải một chú thích ở đâu đó. Tổng chín
  // tháng và tổng mười hai tháng nhìn giống hệt nhau nếu không có mấy chữ này.
  const con_lai = Number(d.so_thang_trong_ky || 0) - Number(d.so_thang_da_troi || 0);

  // "(3/3 tháng)" là câu nói dối tinh vi ở kỳ QUÝ ĐANG CHẠY: quý 3 xem ngày 16/9 có đủ ba tháng
  // trong danh sách, nhưng tháng 9 mới đi được nửa. Kê phân số ấy ra thì người đọc hiểu là quý đã
  // đủ ngày. Nên chỉ kê khi CÒN tháng chưa trôi; còn lại thì mấy chữ "đến hôm nay" nói đủ.
  const nhan_ky = !d.dang_chay
    ? tenKyDai(d.ky)
    : con_lai > 0
      ? `${tenKyDai(d.ky)} · đến hôm nay (${d.so_thang_da_troi}/${d.so_thang_trong_ky} tháng)`
      : `${tenKyDai(d.ky)} · đến hôm nay`;

  const mt = d.muc_tieu || {};
  const ty_le = phanTram(d.ty_le_dat);
  // "ĐẠT" VÀ "ĐI ĐƯỢC" LÀ HAI CÂU KHÁC NHAU, và đây là chỗ dễ nói sai nhất của cả khối.
  //
  // Tỉ lệ luôn là (thực hiện đến nay) ÷ (mục tiêu CẢ KỲ) — máy chủ không chia mục tiêu năm cho 12
  // rồi nhân 9, vì không ai duyệt một mục tiêu chín tháng. Con số ấy đúng. Nhưng gọi nó là "đạt"
  // khi kỳ mới đi hai phần ba đường là để người đọc so nó với 100% và kết luận là đang hụt —
  // trong khi 75% sau chín tháng có thể là đúng tiến độ.
  //
  // Nên: kỳ ĐÃ ĐÓNG mới nói "đạt"; kỳ ĐANG CHẠY nói "đi được", kèm số tháng còn lại để người đọc
  // tự đặt con số vào đúng chỗ của nó.
  const cau_ke_hoach = !mt.du
    ? `Chưa có mục tiêu ${tenKyDai(d.ky).toLowerCase()} — Hội đồng quản trị nhập ở Kế hoạch tháng`
      + ((mt.thieu || []).length ? `; còn thiếu ${(mt.thieu || []).slice(0, 2).join(", ")}` : "")
      + "."
    : !ty_le
      ? `Mục tiêu ${gonSo(Number(mt.gia_tri), "tien")} · chưa tính được tỉ lệ đạt.`
      : d.dang_chay
        ? `Đi được ${ty_le} mục tiêu ${gonSo(Number(mt.gia_tri), "tien")}`
          + (con_lai > 0 ? ` · còn ${con_lai} tháng` : "")
        : `Đạt ${ty_le} kế hoạch · Mục tiêu ${gonSo(Number(mt.gia_tri), "tien")}`;

  const bien = phanTram(d.bien_loi_nhuan);
  const cau_bien = bien
    ? `Biên lợi nhuận ${bien}`
    : "Chưa tính được biên lợi nhuận — cần cả doanh thu và lợi nhuận của cùng kỳ này.";

  // Cả ba bề rộng dùng CÙNG mười hai cột; chỉ khi kỳ chọn hẹp hơn năm thì mới có phần "tô đậm".
  const diem_dt = diemTu(dt);
  const diem_lai = diemTu(lt, ln);   // TC-47 · hình dưới: hai cột đứng cạnh, cùng một trục tung

  // CÂU NÓI RA PHẦN CÒN THIẾU. Cột chính chỉ gồm chuyến ĐỦ SỐ, nên nếu không nói thì người đọc
  // tưởng cột ấy là toàn bộ tháng. Không có gì thiếu thì KHÔNG in dòng này: một dòng "0 chuyến
  // thiếu" lặp lại mỗi lần mở màn hình sẽ dạy người ta thôi đọc nó, và đúng hôm có số thật thì
  // mắt lướt qua luôn.
  const thieu_gv = Number(th.chuyen_thieu_gia_von || 0);
  const thieu_pn = Number(th.chuyen_chua_gan_phap_nhan || 0);
  // TC-68 · Tháng chưa có một bút toán nào. Đây là lý do THẬT của ô "Lợi nhuận trước thuế" rỗng;
  // nói ra ở đây chứ không để người đọc tự đoán từ một dấu gạch.
  const chua_ghi: string[] = Array.isArray(th.thang_chua_ghi_so) ? th.thang_chua_ghi_so : [];
  // LN-1 · Cùng một sự thật, nói ở HAI chỗ cho hai loại người đọc: `cau_thieu` bên dưới là câu
  // đầy đủ cho màn hình có ghi chú; `ln_thieu` là bản rút gọn nhét vừa trong ô, cho màn hình Chủ
  // tịch đã ẩn ghi chú. KHÔNG bỏ câu dài đi: ở màn hình khác nó vẫn là chỗ nói đủ đầu đuôi.
  const ln_thieu = so_ln === null && chua_ghi.length ? {
    ai: String(th.ai_ghi_so || "Kế toán"),
    vi_sao: (chua_ghi.length > 1 ? "các tháng " : "tháng ")
      + chua_ghi.map((t) => soTrongNam(t)).join(", ")
      + "/" + String(chua_ghi[0]).slice(0, 4) + " chưa có bút toán",
    cua: "/accounting",
  } : null;
  // ══ TC-71 · 19/9/2026 — NHÃN CƠ SỞ CỦA CON SỐ GỘP ═══════════════════════════════════════════
  // Anh Tuấn chốt 18/9: doanh thu GỘP cả chuyến chưa đóng sổ. Hệ quả em đã nói trước với anh và
  // ghi lại ở đây để không ai phải hỏi lại: con số ấy KHÔNG còn khớp sổ kế toán và không khớp
  // BCTC. Nên nó bắt buộc đi kèm hai thứ — phần đã đóng sổ (con số khớp sổ), và phần chưa đóng
  // sổ (chỗ chênh). Thiếu hai thứ ấy thì VTOS và BCTC báo hai con số doanh thu khác nhau mà không
  // ai chỉ ra được chênh nằm ở đâu, và người hỏi đầu tiên sẽ là kiểm toán.
  const chua_dong = Number(th.chuyen_chua_dong_so || 0);
  const tien_chua_dong = Number(th.tien_chua_dong_so || 0);
  const tien_da_dong = Number(th.tien_da_dong_so || 0);
  const cau_thieu = thieu_gv || thieu_pn || chua_ghi.length || chua_dong ? (
    <p className="muted v14-ghi kqkd-thieu">
      {chua_ghi.length > 0 && (
        // NÊU ĐÍCH DANH THÁNG NÀO, không phải "3 tháng chưa có số": người đi bù cần biết mở tháng
        // nào ra nhập. Và đi kèm một LỐI TẮT sang đúng cửa — ranh giới 09/9/2026 nói mỗi con số
        // phải có một cửa nhập; ở đây cửa đã có sẵn, cái thiếu là đường dẫn tới nó.
        <>Chưa có bút toán nào của Vietourist trong{" "}
          <b>{chua_ghi.length > 1 ? "các tháng " : "tháng "}
            {chua_ghi.map((t) => soTrongNam(t)).join(", ")}/{String(chua_ghi[0]).slice(0, 4)}</b>
          {" "}— nên <b>Lợi nhuận trước thuế</b> để trống, KHÔNG phải bằng 0.{" "}
          <b>{th.ai_ghi_so || "Kế toán"}</b> nhập tay hoặc nạp từ MISA ở{" "}
          <Link className="the-cua" href="/accounting">Chứng từ ghi sổ →</Link>{" "}</>
      )}
      {/* 08/10/2026 — BỎ HAI CHỮ "ĐÃ ĐÓNG SỐ" KHỎI CÂU DƯỚI, và đó là việc sửa cho ĐÚNG chứ
          không phải cho gọn. Trước hôm nay, chuyến chưa đóng số không bao giờ rơi vào ô
          `chuyen_thieu_gia_von`: `apply_tours` ghi số 0 vào `actual_cost` nên máy đọc được "giá
          vốn 0 đồng" và xếp chúng vào cột chính. Bản vá KQ-2 đổi 0-đồng-ở-chuyến-chưa-quyết-toán
          thành RỖNG, nên từ nay ô này gồm CẢ chuyến đã chạy xong mà chưa đóng số. Giữ nguyên câu
          cũ là nói với Chủ tịch rằng mọi chuyến trong đó đã đóng số — một câu sai mà không có
          con số nào sai, đúng kiểu sai khó tìm nhất.

          VÀ VÌ SAO CHÚ THÍCH NÀY ĐỨNG NGOÀI KHỐI chứ không nằm trong như bản đầu: phép thử
          `test_kq1_man_hinh_khong_in_thang_con_so_tien` cắt khối JSX này ra bằng một cửa sổ
          2000 ký tự kể từ `{thieu_gv > 0 && (`. Nhét thêm bảy dòng chú thích vào TRONG khối đẩy
          câu "chưa biết doanh thu" ra ngoài cửa sổ ấy, và phép thử đỏ lên — nó tưởng màn hình đã
          bỏ mất câu ấy. CI bắt được; bản đo trên cây sạch của em chạy thiếu đúng tệp này. */}
      {thieu_gv > 0 && (
        // TC-71 · 06/10/2026 — SỐ 0 Ở ĐÂY KHÔNG CÓ NGHĨA LÀ KHÔNG ĐỒNG NÀO.
        //
        // Đo trên hệ thật hôm nay: 19 chuyến đã đóng số mà chưa có giá vốn, và màn hình in
        // "(0 doanh thu)". Người đọc hiểu là mười chín chuyến ấy không đáng bao nhiêu, nên bỏ qua.
        // Sự thật ngược lại: chính chú thích của `ket_qua_that.dt_thieu_gia_von` đã ghi rằng doanh
        // thu của những chuyến ấy "vẫn có thể rỗng nốt", nên con số 0 là PHẦN ĐÃ BIẾT bằng không —
        // tức là CHƯA BIẾT GÌ CẢ, không phải biết rằng bằng không.
        //
        // Đây đúng là luật mà kho mã này nhắc đi nhắc lại ở chỗ khác: `KsDiem.diem` để rỗng chứ
        // không chấm 0, `bon_so_tien` trả None chứ không trả 0, `chua_phan_bo` rỗng khác 0. Ô duy
        // nhất chưa theo luật ấy lại là ô nằm trên màn hình Chủ tịch.
        <>Còn <b>{thieu_gv} chuyến</b> chưa có giá vốn
          {Number(th.tien_thieu_gia_von || 0) > 0
            ? <> ({gonSo(Number(th.tien_thieu_gia_von), "tien")} doanh thu)</>
            : <> (<b>chưa biết doanh thu</b> — những chuyến này cũng chưa ghi doanh thu, nên đây là
              số chuyến chứ không phải số tiền)</>} — doanh thu của chúng ĐÃ vào con số trên
          (Chủ tịch chốt 08/10/2026: lấy số liệu y chang của Vietrip) và là khúc mờ ở phần trên
          cây cột, nhưng <b>chưa vào lợi nhuận</b> vì chưa có giá vốn để trừ.{" "}
          <b>{th.ai_nhap_gia_von}</b> nhập ở cửa đóng số.{" "}</>
      )}
      {/* TC-71 · CHỖ CHÊNH VỚI SỔ KẾ TOÁN. Đặt TRƯỚC hai dòng dưới vì đây là khoản lớn nhất và là
          thứ trả lời câu "vì sao VTOS 116 tỷ mà BCTC 85 tỷ". */}
      {chua_dong > 0 && (
        <>Doanh thu trên đây là <b>doanh thu vận hành</b> — gộp cả chuyến chưa đóng sổ, nên{" "}
          <b>không khớp sổ kế toán</b>. Phần đã đóng sổ:{" "}
          <b>{gonSo(tien_da_dong, "tien")}</b>; còn <b>{chua_dong} chuyến</b> đã chạy xong chưa đóng
          sổ ({gonSo(tien_chua_dong, "tien")}). <b>{th.ai_dong_so || "Điều hành"}</b> đóng sổ ở{" "}
          <Link className="the-cua" href="/so-con-no">Sổ chuyến còn nợ →</Link>{" "}</>
      )}
      {thieu_pn > 0 && (
        // TC-71 · CÂU NÀY BỊ ĐẢO NGHĨA, không phải sửa chữ cho gọn. Trước 18/9: chuyến chưa gán
        // pháp nhân KHÔNG cộng vào Vietourist. Từ 18/9 anh Tuấn chốt quy về Vietourist cố định,
        // nên nay chúng ĐÃ cộng vào. Để nguyên câu cũ là để màn hình nói ngược sự thật.
        <>Trong đó <b>{thieu_pn} chuyến</b> ({gonSo(Number(th.tien_chua_gan_phap_nhan || 0), "tien")})
          chưa ai gán pháp nhân, đang <b>quy về Vietourist theo quy tắc mặc định</b>.{" "}
          <b>{th.ai_gan_phap_nhan}</b> gắn đè được nếu chuyến thuộc pháp nhân khác.</>
      )}
    </p>
  ) : null;

  const phu_hinh = kind === "nam"
    ? `Cả 12 tháng ${nam}`
    : `12 tháng ${nam} · tô đậm ${tenKyDai(d.ky).toLowerCase()}`;

  /* ════════════════════════════════════════════════════════════════════════════════════════════
   * TC-62 · MỘT KHỐI CHUNG TÁCH THÀNH HAI KHUNG — VÀ MỘT LUẬT CỦA TC-47 BỊ ĐẢO CHIỀU
   * ════════════════════════════════════════════════════════════════════════════════════════════
   * Anh Tuấn chốt 17/9/2026: "hình 2 tách biểu đồ doanh thu và lợi nhuận ra riêng cho đẹp", rồi
   * duyệt bản vẽ thử ngày 18/9 ("khung em vừa vẽ ok").
   *
   * MẶT CŨ (TC-47, 16/9/2026) — ghi lại nguyên văn vì nó đúng vào lúc ấy: hai hình XẾP DỌC và DÙNG
   * CHUNG TRỤC NGANG. Hình trên bật `an_nhan_x` để giấu hàng nhãn tháng, hình dưới hiện, nên cột
   * tháng 9 của hình trên nằm đúng trên cột tháng 9 của hình dưới và đọc được theo CHIỀU DỌC:
   * "tháng ấy doanh thu cao mà lãi thì không".
   *
   * MẶT MỚI: hai KHUNG riêng, mỗi khung một trục ngang đầy đủ. Cái mất là lối đọc dọc ấy. Cái được
   * là ba thứ, và cộng lại chúng lớn hơn:
   *   · Hai khung riêng thì KHÔNG CÒN CÁM DỖ so chiều cao cột của hình này với hình kia — điều mà
   *     bản cũ phải dặn bằng một câu chữ ở chân khối ("thang đo riêng: đừng so chiều cao"). Một bố
   *     cục tự chặn được cái sai thì hơn một câu dặn đừng sai.
   *   · Mỗi khung mang đủ nhãn tháng của nó, nên in ra hai trang giấy vẫn đọc được từng trang.
   *   · Doanh thu và Lợi nhuận là hai trong SÁU Ô LỚN của bản vẽ V1.4; gộp chúng vào một khung là
   *     sáu ô ấy trên màn hình chỉ còn năm khung.
   *
   * KỲ VẪN LÀ MỘT — ĐÂY LÀ ĐIỀU KHÔNG ĐƯỢC LÀM HỎNG. Bộ chọn Tháng/Quý/Năm vẫn nằm ở MỘT chỗ và
   * vẫn chi phối cả hai khung, vì cả hai khung do cùng thành phần này dựng ra từ cùng một trạng
   * thái. Tách thành hai thành phần có trạng thái riêng là dựng lại đúng trạng thái mà TC-44 sinh
   * ra để bỏ: doanh thu đang xem QUÝ còn lợi nhuận đang xem THÁNG. Và biên lợi nhuận — phép chia
   * chỉ có nghĩa khi tử và mẫu cùng kỳ — cũng mất theo.
   *
   * Người đọc vẫn thấy hai khung cùng kỳ mà không cần một câu chú thích nào: kỳ được in ngay cạnh
   * mỗi con số ("Năm 2026 · đến hôm nay").
   */
  const kq_dt = (
    <section className="panel" id="ket-qua-kinh-doanh">
      {/* KHÔNG gắn thẻ "Năm/Quý/Tháng" cạnh tên khối: nút đang bật ở ngay dòng dưới đã nói điều
          ấy, và một màn hình nói cùng một việc hai lần thì lần thứ hai chỉ tổ làm người đọc dừng
          lại kiểm xem hai chỗ có khớp nhau không. */}
      <div className="mh01-dau"><h2>Doanh thu</h2></div>
      {dieu_khien}
      <div className="kqkd-dau-hinh">
        <OSo gt={so_dt} nhan={nhan_ky} chu={cau_ke_hoach} />
      </div>
      {/* TC-49 · KHÔNG còn nhánh thay hình bằng một đoạn chữ. `BieuDoCot` tự quyết đủ số hay
          chưa và tự vẽ khung rỗng mang đủ mười hai nhãn tháng — nhờ vậy khối giữ đúng hình
          dáng lúc chưa có số, và ngày số về thì nó tự đầy lên chứ không phải đổi bố cục. */}
      <BieuDoCot ten="Doanh thu từng tháng" phu={phu_hinh} diem={diem_dt}
        ai="Điều hành" cua="/tours" cua_ten="Cửa đóng số quyết toán"
        ten_duong="kế hoạch tháng" ten_cho="doanh thu chuyến chưa có giá vốn"
        chuGiai={<ChuGiai ds={[
          { ten: "Thực hiện", lop: "" },
          { ten: "Chưa có giá vốn", lop: "cho" },
          { ten: "Kế hoạch", lop: "duong" },
        ]} />} />
      {cau_thieu}
    </section>
  );

  const kq_ln = (
    <section className="panel" id="loi-nhuan">
      <div className="mh01-dau"><h2>Lợi nhuận</h2></div>
      <div className="kqkd-dau-hinh">
        <div className="kqkd-hai-so">
          <OSo gt={so_lt} nhan={`Lợi nhuận tour · ${nhan_ky}`}
            chu="Thu trừ chi của chính những chuyến đã đóng số — chưa gánh chi phí chung." />
          <OSo gt={so_ln} nhan={`Lợi nhuận trước thuế · ${nhan_ky}`} chu={cau_bien}
            thieu={ln_thieu} />
        </div>
      </div>
      {/* THEO DẤU, không theo mức: người đọc tìm ở hình này đúng một điều — tháng nào lỗ. Còn
          doanh thu thì KHÔNG bật `theo_dau`: doanh thu âm là chuyện hoàn/huỷ, tô nó cùng màu
          với "lỗ" là trộn hai khái niệm khác hẳn nhau. */}
      <BieuDoCot ten="Lợi nhuận từng tháng" phu={phu_hinh} diem={diem_lai} theo_dau
        ai="Điều hành và Kế toán" cua="/tours" cua_ten="Cửa đóng số quyết toán"
        ten_cot2="lợi nhuận trước thuế"
        chuGiai={<ChuGiai ds={[
          { ten: "Lợi nhuận tour", lop: "lai" },
          { ten: "LN trước thuế", lop: "hai" },
          { ten: "Lỗ", lop: "lo" },
        ]} />} />
      {/* CỬA NHẬP CỦA CHỦ TỊCH — thứ DUY NHẤT còn lại ở chân khối (anh Tuấn 18/9/2026: "chỉ giữ
          lại chữ kế hoạch tháng và mũi tên để cho CHỦ TỊCH nhập vào"). Đoạn văn cũ ở đây nói ba
          việc, và cả ba nay đã có chỗ nói đúng hơn: phạm vi Vietourist ghi trên thanh đầu trang,
          "thang đo riêng" do chính hai khung riêng nói hộ, đơn vị đọc ngay trên nhãn trục. */}
      <p className="muted v14-ghi kqkd-cua">
        <Link className="the-cua" href={CUA}>Kế hoạch tháng →</Link>
      </p>
    </section>
  );

  return (<>{kq_dt}{kq_ln}</>);
}
