"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, fmtD, vnd } from "@/lib/api";
import { BieuDoDuong, type Diem } from "@/components/BieuDo";
import { useShell } from "@/components/Shell";
import { xepDonVi, type DonViChon } from "@/lib/thu_tu_don_vi";

/** Màn hình 01 · Tổng quan điều hành — khối dòng tiền bốn mốc và bốn ô cảnh báo.
 *
 *  MỘT ĐIỀU QUAN TRỌNG HƠN CẢ BỐ CỤC: khối này KHÔNG lọc gì hết.
 *
 *  Máy chủ trả về đúng tập dòng của vai đang đăng nhập (/dong-tien/khung), kể cả tên dòng đáy.
 *  Trình duyệt vẽ ra đúng những gì nhận được. Nếu một ngày nào đó ở đây xuất hiện một câu kiểu
 *  `if (vai === "tgd") ẩn dòng vay` thì SEC-02 đã hỏng: dòng bị ẩn vẫn ĐÃ rời khỏi máy chủ, và ai
 *  mở công cụ nhà phát triển cũng đọc được. Phép thử test_tc8 canh đúng chuyện đó.
 *
 *  HAI ĐIỀU KHÔNG LÀM
 *  1. Không hiện "0 đ" thay cho "chưa có số". Ô rỗng ghi "Chưa có nguồn" kèm tên bộ phận phải
 *     nhập — người đọc biết đi hỏi ai, thay vì tin một con số không có thật.
 *  2. Không cộng bốn cột Ở KIỂU LUỸ KẾ. Bốn cột lũy kế từ cùng một ngày nên chồng lên nhau; cộng
 *     lại ra một con số lớn gấp mấy lần thực tế. Câu nhắc nằm ngay dưới bảng, và nó ĐỔI theo kiểu
 *     xem đang chọn — ở kiểu "trong từng khoảng" thì bốn cột rời nhau nên cộng lại LẠI ĐÚNG.
 *
 *  HAI THỨ THÊM NGÀY 14/9/2026 (phương án dung hoà anh Tuấn chốt 13/9)
 *
 *  · CỘT TRẠNG THÁI BA MỨC thay cho cột "Cửa nhập · bộ phận". Bản vẽ V1.4 đòi bỏ hẳn cột cửa nhập
 *    khỏi trang Chủ tịch; bỏ hẳn thì ngược ranh giới 09/9. Nên trang này chỉ còn MỘT nhãn ba mức,
 *    còn nguyên nhân · bộ phận · cửa nhập chuyển sang trang /dong-tien/nguon.
 *
 *  · NÚT ĐỔI KIỂU XEM luỹ kế ↔ trong từng khoảng. Bản vẽ muốn bốn mốc không luỹ kế. Số trong từng
 *    khoảng là HIỆU của hai cột luỹ kế liền nhau — máy chủ tính, không tính ở trình duyệt. Ba dòng
 *    MỨC (tiền đầu kỳ · số dư cuối khoảng · thiếu so với dự phòng) giữ nguyên số ở cả hai kiểu và
 *    mang cờ la_dong_chay=false, vì chúng là mức tại mốc chứ không phải lượng tiền chảy qua.
 */

/* ══════════════════════════════════════════════════════════════════════════════════════════════
   TC-63 · BẢNG BỐN MỐC ĐÃ RỜI KHỐI NÀY, VỀ VỚI MÀN HÌNH DÒNG TIỀN
   ══════════════════════════════════════════════════════════════════════════════════════════════
   "em chuyển qua gộp với dòng tiền hoặc là ẩn khỏi màn hình chủ tịch"   — anh Tuấn, 18/9/2026

   ĐI CÙNG NHAU SANG components/BangBonMoc.tsx, không xoá thứ nào: hình bốn mốc `BieuDoBonMoc`,
   câu đọc hộ `docHoDongTien`, nhãn ba mức `ChipTrangThai`, ô rỗng `RONG`, bảng 14 dòng, nút đổi
   kiểu xem (luỹ kế ↔ trong từng khoảng) và nút Xuất Excel.

   VÌ SAO ĐI CẢ CỤM: hai cái nút ấy KHÔNG có ở đâu khác trong hệ thống. Xoá khối khỏi màn hình
   Chủ tịch mà bỏ chúng lại là âm thầm mất hai tính năng — đúng cái lỗi TC-61 đã ghi ra khi cân
   nhắc chuyện này lần đầu. Chúng điều khiển CÁI BẢNG, nên chúng theo bảng.

   MÀN HÌNH CHỦ TỊCH GIỮ LẠI GÌ: hình 13 tuần (trả lời "ba tháng tới tiền đi thế nào"), dải chú
   thích hai hàng, bốn ô mốc dự báo, và cửa "Cấu trúc chi tiết dòng tiền →" dẫn sang chỗ bảng bốn
   mốc đang đứng. Tóm tắt NGUỒN SỐ vẫn ở lại — nó là cảnh báo, không phải bảng số.

   LÝ DO SÂU HƠN (anh Tuấn hỏi 17/9, đã đếm): bảng bốn mốc TRÙNG với hai khối khác ngay trên cùng
   màn hình, theo ba cách đếm khác nhau — bốn mốc luỹ kế theo ngày cam kết, Phải thu/Phải trả theo
   bảy nhóm hạn, hình 13 tuần theo tuần. Ba con số cùng một dòng tiền đứng cạnh nhau là ba con số
   người đọc sẽ cộng trừ lẫn nhau trong đầu, mà phép tính ấy không có đáp án đúng. */

/* TC-57 · Ô CẢNH BÁO `O` ĐÃ GỠ cùng với bốn ô dùng nó (anh Tuấn chốt 17/9/2026 — xem chú thích
   tại chỗ gỡ, trong thân khối). Xoá luôn hàm thay vì để lại: một thành phần không ai gọi vẫn qua
   được mọi phép kiểm, và vòng sau có người dựng lại bốn ô ấy chỉ vì thấy hàm còn nằm đó. */

/** TC-48 · ĐÁY CỦA DỰ BÁO 13 TUẦN — anh Tuấn chốt 17/9/2026: "để đáy thấp nhất, bỏ số tuần 13".
 *
 *  ĐÂY LÀ CON SỐ ĐẦU TIÊN CỦA KHỐI, đứng trên bảng bốn mốc. Bốn mốc trả lời "tiền đang ở đâu";
 *  dòng này trả lời "ba tháng tới có lúc nào hết tiền không" — và câu thứ hai mới là câu bắt người
 *  đọc phải làm gì đó ngay hôm nay.
 *
 *  BA MỨC, KHÔNG PHẢI HAI (xem luật 4 ở `finance.day_thap_nhat`):
 *    · âm            – không đủ tiền trả, vỡ kế hoạch                    → đỏ
 *    · dưới ngưỡng   – vẫn trả được nhưng thủng lớp đệm dự phòng         → vàng
 *    · trên ngưỡng   – đáy vẫn còn trên mức dự phòng                     → xanh
 *  Gộp hai mức đầu làm một thì một công ty sắp mất khả năng chi trả trông y hệt một công ty mỏng
 *  đệm — hai tình huống đòi hai hành động khác hẳn nhau.
 *
 *  CHƯA CÓ SỐ THÌ KHÔNG VẼ GÌ. Không in "0 đ": 0 đồng trên khối dòng tiền đọc ra là "sắp hết
 *  tiền", tức bịa ra đúng cái cảnh báo nguy hiểm nhất từ một chỗ trống.
 */
function DayDuBao({ d }: { d: any }) {
  if (!d || d.gia_tri === null || d.gia_tri === undefined) return null;
  /* ══════════════════════════════════════════════════════════════════════════════════════════
     TC-65 · YÊN THÌ IM, NGUY THÌ NÓI — anh Tuấn 18/9/2026: "hình 3 xoá hoặc ẩn khỏi màn hình
     chủ tịch", kèm ảnh chụp đúng hàng này ở trạng thái XANH ("Trên ngưỡng dự phòng").
     ══════════════════════════════════════════════════════════════════════════════════════════
     ẨN, KHÔNG XOÁ, và ẩn có điều kiện. Ba lý do, theo đúng thứ tự quan trọng:

     1. Ở trạng thái XANH, hàng này nói lại đúng điều hình ngay trên nó đã vẽ: đường TỒN nằm trên
        vạch ngưỡng. Một dòng chữ báo "mọi thứ ổn" in ra mỗi ngày dạy người ta thôi đọc chỗ ấy —
        và đúng hôm nó đổi sang đỏ thì mắt cũng lướt qua luôn. Bỏ nó đi làm nó MẠNH hơn.

     2. Ở trạng thái ĐỎ ("ÂM — không đủ tiền trả") hay VÀNG ("dưới ngưỡng dự phòng") thì đây là
        dòng quan trọng nhất cả màn hình: nó nói tuần nào hết tiền và thiếu bao nhiêu. Xoá hẳn là
        bỏ mất đúng cái cảnh báo ấy — không được.

     3. Con số và tuần KHÔNG mất ở trạng thái xanh: rê chuột lên điểm thấp nhất của đường TỒN là
        đọc được. Và cửa nhập dự báo cũng không mất — `Hinh13Tuan` đã mang sẵn `cua` của nó.

     Nếu một vòng sau muốn bỏ hẳn, phải trả lời được: lúc dòng tiền âm thì ai nói cho Chủ tịch
     biết, và nói ở đâu. */
  if (!d.am && !d.duoi_nguong) return null;
  const muc = d.am ? "red" : d.duoi_nguong ? "warn" : "ok";
  const nhan = d.am ? "ÂM — không đủ tiền trả"
    : d.duoi_nguong ? "Dưới ngưỡng dự phòng" : "Trên ngưỡng dự phòng";
  /* TC-60 (17/9/2026) · MỘT HÀNG, KHÔNG CÒN MỘT KHỐI RIÊNG.
     Anh Tuấn: "gom lại thành 2 hàng ở dưới biểu đồ cho gọn". Con số này là HÀNG THỨ NHẤT của dải
     chú thích — nó vẫn giữ vạch màu bên trái (ba mức: đỏ · vàng · xanh), vì mức độ phải đọc được
     trước cả con số; thứ bỏ đi là khoảng đệm trên dưới và cái xuống dòng của nhãn trạng thái. */
  return (
    <div className={"dt-hang dt-day " + muc}>
      <b className="dt-day-so">{vnd(d.gia_tri)}</b>
      <span className="muted dt-day-nhan">
        Số dư thấp nhất · tuần {d.tuan} ({fmtD(String(d.tu_ngay))})
      </span>
      <span className={"tag " + muc}>{nhan}</span>
      {d.thieu_so_voi_nguong > 0 && (
        <span className="muted">Thiếu {vnd(d.thieu_so_voi_nguong)} so với mức dự phòng</span>
      )}
      <span className="dt-day-day" />
      {/* Đường đi tới chỗ sửa: dự báo dựng từ booking, đề nghị chi, lịch vay và bảng kế hoạch
          thu–chi do Kế toán gõ. Ranh giới 09/9 — màn hình này chỉ bày, cửa nhập nằm ở đó. */}
      <Link className="the-cua" href="/finance?tab=forecast">Dự báo 13 tuần · cửa nhập →</Link>
    </div>
  );
}

/** Pháp nhân của MÀN HÌNH 01: luôn là Vietourist mẹ (VTD) — anh Tuấn chốt 17/9/2026.
 *
 *  "Em bỏ hết pháp nhân, chỉ chọn Vietourist; khi nào cần xem pháp nhân thì vào Báo cáo tài chính
 *   tổng hợp."
 *
 *  Tìm theo MÃ chứ không lấy `ds[0]`: `xepDonVi` xếp VTD lên đầu, nhưng dựa vào một hàm xếp để
 *  quyết định màn hình Chủ tịch đang nói về công ty nào là đặt một con số tiền lên một quy ước
 *  sắp xếp. Đổi thứ tự trong THU_TU_MA là đổi luôn công ty — mà không có lỗi nào báo.
 *
 *  Vẫn giữ `xepDonVi` cho lối lui: vai nào không được xem VTD thì nhận pháp nhân đầu tiên theo
 *  đúng thứ tự đã chốt, thay vì nhận bừa phần tử đầu mảng máy chủ trả về.
 */
function vietouristMe(ds: DonViChon[]): DonViChon | null {
  return ds.find((c) => (c.code || "").trim().toUpperCase() === "VTD") || ds[0] || null;
}

/** TC-59 · BIỂU ĐỒ BA ĐƯỜNG — THU · CHI · TỒN, theo bản mẫu anh Tuấn gửi 17/9/2026.
 *
 *  TC-57 (sáng cùng ngày) dựng chỗ này thành một hình CỘT chỉ vẽ số dư cuối tuần. Hình ấy trả lời
 *  được "tuần nào thấp nhất", nhưng không trả lời được "vì sao thấp" — mà đó mới là câu người
 *  đọc phải trả lời trước khi làm gì. Ba đường cùng khung thì đọc ra ngay: tuần nào chi vượt thu,
 *  đường tồn tụt theo đúng tuần ấy.
 *
 *  LUẬT TC-57 BỊ ĐẢO, GHI LẠI CẢ HAI VẾ. TC-57 chọn cột với lý lẽ của `BieuDoCot`: dữ liệu VTOS
 *  có lỗ hổng, và đường nối liền qua chỗ trống là vẽ ra một giá trị không tồn tại. Lý lẽ ấy vẫn
 *  đúng và KHÔNG bị bỏ — `BieuDoDuong` không nối qua chỗ trống, gặp `null` là đường đứt. Thứ đổi
 *  là số chuỗi: ba chuỗi × mười ba tuần là ba mươi chín cột cạnh nhau, không đọc nổi cái nào.
 *
 *  RỖNG KHÁC KHÔNG, ở đây cũng vậy: chưa có dự báo thì không vẽ gì — không vẽ một khung 13 tuần
 *  dí sát đáy, vì một đường phẳng ở 0 đọc ra là "sắp hết tiền" chứ không phải "chưa có số".
 *
 *  MÁY CHỦ BẢN CŨ chưa gửi `thu` / `chi` từng tuần thì hai đường ấy không đủ hai điểm và không
 *  được vẽ, còn đường TỒN vẫn vẽ bình thường. Không suy `thu` từ hiệu hai số dư liền nhau: hiệu
 *  ấy là thu TRỪ chi, gọi nó là "thu" thì con số sai mà hình vẫn trông đúng.
 */
function Hinh13Tuan({ d }: { d?: any }) {
  const tuan: any[] = d?.tuan || [];
  if (!tuan.length) return null;
  const nhan = tuan.map((w) => `T${w.tuan}`);
  /** Một cột của `tuan[]` thành chuỗi điểm. Thiếu trường (máy chủ bản cũ) → `null`, không → 0. */
  const chuoi = (khoa: string): Diem[] => tuan.map((w, i) => ({
    nhan: nhan[i],
    gt: w[khoa] === null || w[khoa] === undefined ? null : Number(w[khoa]),
  }));
  return (
    <BieuDoDuong
      ten="Biến động dòng tiền" phu="dự báo 13 tuần"
      nhan={nhan} dinh_dang="tien" doi_xung
      ds={[
        { ten: "THU", lop: "d1", diem: chuoi("thu") },
        { ten: "CHI", lop: "d2", diem: chuoi("chi") },
        { ten: "TỒN", lop: "d3", diem: chuoi("so_du") },
      ]}
      /* Ngưỡng dự phòng là một ĐƯỜNG trên cùng trục, không phải một con số ghi bên cạnh: mắt đọc
         "tuần nào chạm ngưỡng" bằng cách nhìn đường TỒN cắt xuống dưới vạch, không bằng cách so
         từng con số với một con số nhớ trong đầu. Chỉ vẽ khi máy chủ có ngưỡng — không bịa. */
      moc={typeof d?.nguong === "number" ? { gt: d.nguong, nhan: "ngưỡng dự phòng" } : null}
      /* TC-60 · KHÔNG CÒN CÂU CHÂN. Anh Tuấn chụp đúng ba câu chú thích của khối này và bảo xoá
         (17/9/2026). Ba câu ấy đúng nhưng chúng giải thích cách ĐỌC hình cho người đọc lần đầu,
         mà người đọc màn hình này mở nó mỗi ngày. Chú giải THU · CHI · TỒN ở đầu hình vẫn còn,
         nên danh tính ba đường không mất.
         Con số ngưỡng thì KHÔNG được mất theo: nó chuyển vào nhãn rê chuột của chính vạch ấy
         (`BieuDoDuong` dựng từ `moc.nhan` + giá trị), chứ không biến khỏi màn hình. */
      /* TC-65 · CỬA SANG MÀN HÌNH DÒNG TIỀN ĐỨNG NGAY CẠNH TÊN HÌNH — anh Tuấn 18/9/2026: "đưa
         chữ cấu trúc chi tiết dòng tiền lên kề bên chữ dự báo dòng tiền 13 tuần".
         Trước vòng này nó là một đoạn văn một dòng nằm dưới đáy khối, cách khung biểu đồ một dải
         trống rộng bằng nửa màn hình — anh Tuấn chụp đúng dải trống ấy. Đưa lên cạnh tên hình thì
         hết dải trống, và cửa đọc ra ngay là "chi tiết CỦA chính cái đang xem". */
      ben_ten={<Link className="the-cua" href="/dong-tien">Cấu trúc chi tiết dòng tiền →</Link>}
      ai="Kế toán" cua="/finance?tab=forecast" cua_ten="Cửa nhập dự báo 13 tuần" />
  );
}

/** Bốn con số của CÙNG MỘT PHÉP CÂN: đầu kỳ + dự kiến thu − dự kiến chi = cuối tuần 13.
 *
 *  Máy chủ cộng cả bốn (`sections.du_bao_13_tuan`) chứ không để màn hình cộng — để màn hình tự
 *  cộng là mở đường cho bốn con số không còn cân nhau mà chẳng ai biết. Ranh giới 09/9: máy chủ
 *  tính, màn hình bày.
 *
 *  Bốn ô đứng SAU biểu đồ: hình trả lời "có tuần nào hụt không", bốn số trả lời "vì sao". Đảo thứ
 *  tự là bắt người đọc cộng trừ trước khi biết mình có cần cộng trừ hay không.
 */
function BonMocDuBao({ d }: { d?: any }) {
  if (!d) return null;
  const o = (ten: string, gt: any, dau = "") => (
    <div className="dt-moc-o">
      <b>{gt === null || gt === undefined ? "—" : dau + vnd(Math.abs(Number(gt)))}</b>
      <small>{ten}</small>
    </div>
  );
  /* TC-60 · CÂU "PHÉP CÂN" ĐÃ XOÁ theo chốt 17/9. Phép cân vẫn còn — nó nằm ở dấu + và − in
     ngay trước hai con số giữa, và ở thứ tự bốn ô đọc từ trái sang. Câu chữ chỉ nói lại điều bốn
     cái nhãn đã nói. Ràng buộc "tổng mười ba tuần của hai đường = hai ô giữa" chuyển hẳn về phép
     thử canh (test_tc59) — chỗ nó không thể bị ai đọc lướt qua. */
  return (
    <div className="dt-moc">
      {o("Tiền đầu kỳ", d?.dau_ky)}
      {o("Dự kiến thu", d?.tong_thu, "+")}
      {o("Dự kiến chi", d?.tong_chi, "−")}
      {o("Cuối tuần 13", d?.cuoi_ky)}
    </div>
  );
}

export default function KhoiDongTien({ day, du_bao }: { day?: any; du_bao?: any }) {
  const { toast } = useShell();
  const [pn, setPn] = useState<number | null>(null);
  const [k, setK] = useState<any>(null);
  const [an, setAn] = useState(false);   // vai này không mở khối dòng tiền → không vẽ gì

  useEffect(() => {
    api("/dong-tien/meta")
      .then((r: any) => {
        // Ghi rõ kiểu phần tử: `r` là any nên nếu để suy diễn, T rơi về đúng ràng buộc {code} và
        // `.id` không còn tồn tại dưới mắt trình biên dịch (CI/web bắt đỏ lần đầu).
        const c = vietouristMe(xepDonVi<DonViChon>(r.phap_nhan || []));
        if (c) setPn(c.id);
        else setAn(true);
      })
      .catch(() => setAn(true));   // 403: vai này không xem khối dòng tiền – im lặng, không báo lỗi
  }, []);

  const tai = useCallback(async () => {
    if (!pn) return;
    try { setK(await api(`/dong-tien/khung/${pn}`)); }
    catch (e: any) { if (e?.status === 403) setAn(true); else toast(e?.message || "Không tải được khối dòng tiền", true); }
  }, [pn, toast]);
  useEffect(() => { tai(); }, [tai]);

  if (an || !k) return null;
  if (!k.xem_duoc) return null;

  // CHỈ CÒN ĐỌC PHẦN TÓM TẮT của gói khung. `cot`, `dong`, `dong_tien_thuan` theo bảng bốn mốc
  // sang /dong-tien; ở đây giữ đúng cái cảnh báo "nguồn số" và số dòng quá hạn.
  const tt = k.tom_tat_trang_thai || {};

  return (
    <section style={{ marginBottom: 14 }}>
      {/* ═══ TC-59 · MỘT KHUNG DUY NHẤT: HÌNH · CHÚ THÍCH · BỐN MỐC ════════════════════════════
          "em thiet ke lai cho anh biểu đồ giống nhu hình mẫu 1, và gòm hinh 2 lai cho gọn nằm
           trong khung cua biểu đồ dòng tiền o phan chú thich bên dưới biểu đồ ... nối liền với
           biều đồ hình 4"                                       — anh Tuấn, 17/9/2026

          TRƯỚC VÒNG NÀY chỗ này là BA mảnh rời có khe hở giữa: con số đáy dự báo đứng riêng trên
          cùng, rồi tiêu đề + nút đổi kiểu + Xuất Excel + dòng "Nguồn số", rồi mới tới biểu đồ và
          bốn ô. Ba khe hở ấy đọc ra là ba khối khác nhau — trong khi cả ba nói về đúng một dòng
          tiền, và con số đáy chính là điểm thấp nhất của cái đường đang vẽ ngay dưới nó.

          NAY MỘT VIỀN, và thứ tự đảo lại: HÌNH TRƯỚC, CHỮ SAU. Hình trả lời "ba tháng tới tiền
          đi thế nào"; phần chữ bên dưới nói con số đáy là bao nhiêu, số liệu lấy từ đâu, còn
          thiếu nguồn nào. Đặt chữ lên trước là bắt người đọc đọc chú thích của một hình họ chưa
          nhìn thấy. */}
      <div className="dt-gop">
        <Hinh13Tuan d={du_bao} />

        {/* ═══ TC-60 · ĐÚNG HAI HÀNG, KHÔNG HƠN ════════════════════════════════════════════
            "em xoa nhung chú thich này, va gom lại thành 2 hàng ở dưới biểu đồ cho gọn"
                                                                    — anh Tuấn, 17/9/2026

            Hàng 1 là CON SỐ: đáy dự báo, tuần nào, mức so với ngưỡng, và cửa nhập dự báo.
            Hàng 2 là THAO TÁC: kiểu xem bốn mốc, tình trạng nguồn số, và nút xuất.

            Chia theo "số / thao tác" chứ không theo thứ tự cũ: mắt đọc con số trước, và tay chỉ
            chạm tới hàng dưới khi đã quyết định làm gì. Trộn hai loại vào một hàng là bắt người
            đọc lướt qua mấy cái nút trước khi tới được con số. */}
        <div className="dt-chan">
          <DayDuBao d={day} />

          <div className="dt-hang">
            {/* TC-63 · NÚT ĐỔI KIỂU XEM VÀ NÚT XUẤT EXCEL ĐÃ THEO BẢNG BỐN MỐC SANG /dong-tien.
                Cả hai điều khiển CÁI BẢNG; bảng đi rồi mà để nút ở lại thì chúng không còn điều
                khiển gì trên màn hình này.

                TÓM TẮT NGUỒN SỐ THÌ Ở LẠI, và đây là ranh giới của vòng này: nó không phải một
                bảng số, nó là CẢNH BÁO — "còn ba dòng chưa ai nạp" là việc Chủ tịch phải giao
                người làm, đọc xong là xong, đúng loại thông tin màn hình này giữ.
                Đếm theo DÒNG CÓ CỬA (bỏ dòng tự cộng), vì dòng tự cộng không ai nhập được. */}
            <span className="muted dt-nhan-nho-mo">Nguồn số</span>
            <span className="tag ok">{tt.day_du ?? 0} đầy đủ</span>
            <span className="tag warn">{tt.chua_doi_soat ?? 0} chưa đối soát</span>
            <span className="tag red">{tt.con_thieu ?? 0} còn thiếu</span>
            {/* Quá hạn tách riêng khỏi ba mức trạng thái: "còn thiếu" nói dòng chưa có số, "quá
                hạn" nói đã lỡ mốc 24 giờ Chủ tịch chốt. Gộp hai cái vào một nhãn là mất đúng cái
                khác biệt khiến người ta phải đứng dậy làm ngay. */}
            {(k.so_qua_han ?? 0) > 0 && <span className="tag red">{k.so_qua_han} quá hạn</span>}
            <Link className="the-cua" href="/dong-tien/nguon">Nguyên nhân · cửa nhập →</Link>
            {/* TC-55 · Ô CHỌN PHÁP NHÂN ĐÃ GỠ, và TC-60 gỡ luôn câu `k.cau_pham_vi` từng đứng
                dưới nó: câu ấy nói "bảng này gồm toàn bộ dòng tiền của pháp nhân đang xem", mà
                đầu màn hình đã ghi "Phạm vi: Vietourist — công ty mẹ". Hai câu cùng nói một điều
                thì câu thứ hai chỉ làm khối dài thêm. */}
          </div>
        </div>

        {/* NỐI LIỀN, KHÔNG CÁCH: bốn mốc nằm trong cùng viền với hình và dải chú thích — chúng là
            tổng mười ba tuần của chính hai đường THU và CHI ở trên. Tách ra thành khung riêng là
            mời người đọc coi chúng như hai bộ số không liên quan. */}
        <BonMocDuBao d={du_bao} />
      </div>


      {/* ═══ TC-63 → TC-65 · BẢNG BỐN MỐC SANG /dong-tien, RỒI CỬA DẪN SANG CŨNG ĐI THEO ═════
          TC-63 (18/9/2026): cả khối bốn mốc chuyển sang /dong-tien, chỉ để lại ở đây một đoạn văn
          mang cửa "Cấu trúc chi tiết dòng tiền →".
          TC-65 (cùng ngày, sau khi anh Tuấn chụp màn hình): đoạn văn ấy nằm một mình dưới đáy
          khối, cách khung biểu đồ một dải trống rộng gần cả màn hình — anh Tuấn chụp đúng dải
          trống và bảo lấp. Cửa nay đứng NGAY CẠNH tên hình 13 tuần (`ben_ten` ở `Hinh13Tuan`),
          nên đoạn văn này xoá hẳn và dải trống đi theo nó. */}
    </section>
  );
}
