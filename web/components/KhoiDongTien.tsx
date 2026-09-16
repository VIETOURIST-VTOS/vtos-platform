"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, fmtD, taiTep, vnd } from "@/lib/api";
import { BieuDoCot, type Diem } from "@/components/BieuDo";
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

/** Nhãn ba mức. Màu lấy từ bộ nhận diện: xanh lá đủ · vàng cần chú ý · đỏ còn thiếu. */
function ChipTrangThai({ ma, nhan }: { ma?: string; nhan?: string }) {
  if (!ma || !nhan) return null;
  const cls = ma === "day_du" ? "ok" : ma === "chua_doi_soat" ? "warn" : "red";
  return <span className={"tag " + cls}>{nhan}</span>;
}

const RONG = (vi_sao?: string) => (
  <span className="muted" title={vi_sao || "Chưa có số — khác hẳn với bằng 0"}>Chưa có nguồn</span>
);

function O({ o }: { o: any }) {
  const co = o.gia_tri !== null && o.gia_tri !== undefined && o.gia_tri !== "";
  const hien = !co ? null : o.kieu === "ngay" ? fmtD(String(o.gia_tri)) : vnd(o.gia_tri);
  return (
    <div className={"o-cb" + (co ? " red" : "")}>
      <b>{co ? hien : <span className="muted" style={{ fontSize: 15 }}>Chưa có nguồn</span>}</b>
      <span>{o.nhan}</span>
      {o.vi_sao && <span className="muted" style={{ fontSize: 11 }}>{o.vi_sao}</span>}
      {o.bo_phan && <span className="muted" style={{ fontSize: 11 }}>Bộ phận nối nguồn: {o.bo_phan}</span>}
    </div>
  );
}

/** TC-35 · BIỂU ĐỒ DÒNG TIỀN THUẦN QUA BỐN MỐC.
 *
 *  Bản vẽ V1.4 đặt đúng chỗ này một biểu đồ, kèm câu quy định cách cư xử khi thiếu số:
 *
 *      "Dự báo chưa đủ dữ liệu. Biểu đồ số dư và ngưỡng dự phòng sẽ hiển thị khi có số dư đã đối
 *       soát cùng lịch thu–chi đầy đủ. KHÔNG QUY ĐỔI DỮ LIỆU THIẾU THÀNH SỐ 0."
 *
 *  Câu cuối là luật, không phải lời khuyên. Một đường phẳng ở mức 0 trên biểu đồ dòng tiền đọc ra
 *  là "không có tiền vào ra" — khác hẳn "chưa ai nạp số". Nên THIẾU MỘT MỐC LÀ KHÔNG VẼ, và ghi ra
 *  còn thiếu mốc nào.
 *
 *  NGUỒN SỐ: `k.dong_tien_thuan` / `k.dong_tien_thuan_khoang` — đúng hai trường mà dòng đáy của
 *  bảng đang đọc, nên biểu đồ không thể nói khác bảng ngay dưới nó. Cố ý KHÔNG tự dò dòng "số dư
 *  cuối khoảng" theo tên tiếng Việt: tên đổi một chữ là biểu đồ âm thầm vẽ sang dòng khác.
 *
 *  Biểu đồ đổi theo KIỂU XEM cùng với bảng. Ở kiểu luỹ kế bốn cột chồng nhau nên đây là đường đi
 *  lên của cùng một dòng tiền; ở kiểu từng khoảng bốn cột rời nhau nên đây là bốn lượng độc lập —
 *  chú thích dưới biểu đồ nói rõ đang là kiểu nào.
 */
/** TC-40 · DÙNG BỘ BIỂU ĐỒ CHUNG, và thêm một câu ĐỌC HỘ.
 *
 *  Anh Tuấn chốt 15/9/2026: "dòng tiền rất quan trọng, cần có số và biểu đồ phân tích". Hai việc:
 *
 *   1. Biểu đồ bỏ bản vẽ tay ở đây, gọi `BieuDoCot` của components/BieuDo.tsx. Bản vẽ tay cũ đúng
 *      về hình nhưng là bản chép thứ tư của cùng một phép tính trục — và bốn bản chép thì sớm
 *      muộn lệch nhau. Bộ chung còn có thứ bản vẽ tay không có: trục tung ghi mốc, lưới mờ, nhãn
 *      số trên từng cột.
 *   2. Thêm một câu đọc hộ. Đây là khối quan trọng nhất màn hình, mà bốn con số bốn mốc thì phải
 *      tự so trong đầu mới ra được điều đáng lo. Câu ấy chỉ ĐỌC LẠI số máy chủ gửi — nó nói mốc
 *      nào âm sớm nhất và thiếu bao nhiêu, không tính ra chỉ tiêu mới nào.
 */
function docHoDongTien(cot: any[], v: (number | null | undefined)[], khoang: boolean): string {
  const co = cot.map((c, i) => ({ ten: c.ten, gt: v[i] }))
    .filter((x) => typeof x.gt === "number") as { ten: string; gt: number }[];
  if (co.length === 0) return "";
  const am = co.filter((x) => x.gt < 0);
  if (am.length === 0) {
    return khoang
      ? `Cả ${co.length} khoảng đều dương — không khoảng nào thu không đủ bù chi.`
      : `Dòng tiền luỹ kế dương ở cả ${co.length} mốc.`;
  }
  // Mốc ÂM SỚM NHẤT là điều đáng lo nhất, vì nó là hạn phải xoay tiền. Cột thứ tự trong `cot` đã
  // là thứ tự thời gian, nên phần tử âm đầu tiên chính là mốc sớm nhất — không cần sắp lại.
  const dau = am[0];
  const sau = am.length > 1 ? ` (${am.length}/${co.length} mốc âm)` : "";
  return khoang
    ? `Thu không đủ bù chi từ khoảng ${dau.ten}, thiếu ${vnd(Math.abs(dau.gt))}${sau}.`
    : `Dòng tiền luỹ kế âm từ mốc ${dau.ten}, thiếu ${vnd(Math.abs(dau.gt))}${sau}.`;
}

/** Bốn mốc dòng tiền thuần.
 *
 *  Bản vẽ V1.4 đặt đúng chỗ này một biểu đồ, kèm câu quy định cách cư xử khi thiếu số:
 *
 *      "Dự báo chưa đủ dữ liệu. Biểu đồ số dư và ngưỡng dự phòng sẽ hiển thị khi có số dư đã đối
 *       soát cùng lịch thu–chi đầy đủ. KHÔNG QUY ĐỔI DỮ LIỆU THIẾU THÀNH SỐ 0."
 *
 *  Câu cuối là luật, không phải lời khuyên. Một đường phẳng ở mức 0 trên biểu đồ dòng tiền đọc ra
 *  là "không có tiền vào ra" — khác hẳn "chưa ai nạp số". Bộ biểu đồ chung giữ đúng luật ấy: mốc
 *  thiếu là một ô trống có khung nét đứt, không phải một cột cao 0.
 *
 *  NGUỒN SỐ: `k.dong_tien_thuan` / `k.dong_tien_thuan_khoang` — đúng hai trường mà dòng đáy của
 *  bảng đang đọc, nên biểu đồ không thể nói khác bảng ngay dưới nó. Cố ý KHÔNG tự dò dòng "số dư
 *  cuối khoảng" theo tên tiếng Việt: tên đổi một chữ là biểu đồ âm thầm vẽ sang dòng khác.
 *
 *  Biểu đồ đổi theo KIỂU XEM cùng với bảng. Ở kiểu luỹ kế bốn cột chồng nhau nên đây là đường đi
 *  lên của cùng một dòng tiền; ở kiểu từng khoảng bốn cột rời nhau nên đây là bốn lượng độc lập —
 *  chú thích dưới biểu đồ nói rõ đang là kiểu nào.
 */
function BieuDoBonMoc({ cot, so, khoang, vi_sao }: {
  cot: any[]; so: Record<string, number | null | undefined>; khoang: boolean; vi_sao?: string;
}) {
  const gt = cot.map((c: any) => so?.[c.ma]);
  const diem: Diem[] = cot.map((c: any, i: number) => ({
    nhan: c.ten,
    gt: gt[i] === null || gt[i] === undefined ? null : Number(gt[i]),
  }));
  const thieu = cot.filter((c: any, i: number) => gt[i] === null || gt[i] === undefined);
  const doc = docHoDongTien(cot, gt as any, khoang);
  return (
    <>
      <BieuDoCot
        ten={`Dòng tiền thuần qua bốn mốc`}
        phu={khoang ? "trong từng khoảng — bốn cột rời nhau" : "luỹ kế — bốn cột chồng lên nhau"}
        diem={diem}
        ai="Kế toán" cua="/dong-tien/nguon" cua_ten="Nguyên nhân · bộ phận · cửa nhập"
        chan={<>
          {/* CÂU ĐỌC HỘ ĐỨNG TRƯỚC mọi chú thích khác: nó là điều người đọc cần biết, còn phần
              còn lại là cách đọc hình. */}
          {doc && <><b>{doc}</b>{" "}</>}
          {thieu.length > 0 && <>
            Còn thiếu {thieu.length}/{cot.length} mốc: {thieu.map((c: any) => c.ten).join(" · ")}.
            {vi_sao ? " " + vi_sao : ""} Không quy đổi dữ liệu thiếu thành số 0.
          </>}
          {/* KHÔNG nhắc lại "vạch đậm là mốc 0": `BieuDoCot` tự in câu ấy khi có cột âm. Trên ảnh
              dựng ra hai câu gần y hệt nhau đứng liền nhau. */}
        </>} />
    </>
  );
}

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
  const muc = d.am ? "red" : d.duoi_nguong ? "warn" : "ok";
  const nhan = d.am ? "ÂM — không đủ tiền trả"
    : d.duoi_nguong ? "Dưới ngưỡng dự phòng" : "Trên ngưỡng dự phòng";
  return (
    <div className={"dt-day " + muc}>
      <div className="dt-day-so">
        <b>{vnd(d.gia_tri)}</b>
        <span className="muted">
          Số dư thấp nhất dự kiến · tuần {d.tuan} ({fmtD(String(d.tu_ngay))})
        </span>
      </div>
      <div className="dt-day-phu">
        <span className={"tag " + muc}>{nhan}</span>
        {d.thieu_so_voi_nguong > 0 && (
          <span className="muted">Thiếu {vnd(d.thieu_so_voi_nguong)} so với mức dự phòng</span>
        )}
        {/* Đường đi tới chỗ sửa: dự báo dựng từ booking, đề nghị chi, lịch vay và bảng kế hoạch
            thu–chi do Kế toán gõ. Ranh giới 09/9 — màn hình này chỉ bày, cửa nhập nằm ở đó. */}
        <Link className="the-cua" href="/finance?tab=forecast">Dự báo 13 tuần · cửa nhập →</Link>
      </div>
    </div>
  );
}

export default function KhoiDongTien({ day }: { day?: any }) {
  const { toast } = useShell();
  const [dsPn, setDsPn] = useState<any[]>([]);
  const [pn, setPn] = useState<number | null>(null);
  const [k, setK] = useState<any>(null);
  const [an, setAn] = useState(false);   // vai này không mở khối dòng tiền → không vẽ gì
  // Mặc định LUỸ KẾ, không phải kiểu mới. Kiểu luỹ kế là kiểu đã in ra trong tài liệu v1.1 và là
  // kiểu người đọc đang quen; đổi mặc định là hôm sau có người đọc bảng mới bằng thói quen cũ.
  const [khoang, setKhoang] = useState(false);
  const [dangXuat, setDangXuat] = useState(false);

  useEffect(() => {
    api("/dong-tien/meta")
      .then((r: any) => {
        // Xếp theo thứ tự đã chốt (VTD trước) chứ không theo bảng chữ cái của máy chủ: mở màn hình
        // ra mà con số đầu tiên đập vào mắt là của một pháp nhân nhỏ thì đó là con số ít cần nhất.
        // Ghi rõ kiểu phần tử: `r` là any nên nếu để suy diễn, T rơi về đúng ràng buộc {code} và
        // `ds[0].id` không còn tồn tại dưới mắt trình biên dịch (CI/web bắt đỏ lần đầu).
        const ds = xepDonVi<DonViChon>(r.phap_nhan || []);
        setDsPn(ds);
        if (ds.length) setPn(ds[0].id);
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

  const cot = k.cot || [];
  const nCot = cot.length;
  const tt = k.tom_tat_trang_thai || {};

  /** Số của một dòng ở kiểu xem đang chọn. Dòng MỨC không có số theo khoảng nên luôn lấy `so`. */
  const soCua = (d: any) => (khoang && d.la_dong_chay ? d.so_khoang : d.so) || {};

  return (
    <section style={{ marginBottom: 14 }}>
      <DayDuBao d={day} />
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: 8 }}>
        <h2 style={{ margin: 0 }}>Dòng tiền — bốn mốc {khoang ? "trong từng khoảng" : "lũy kế"}</h2>
        <div className="dt-kieu" role="group" aria-label="Kiểu xem bốn mốc">
          <button type="button" className={"act" + (khoang ? " grey" : "")}
            aria-pressed={!khoang} onClick={() => setKhoang(false)}>Lũy kế</button>
          <button type="button" className={"act" + (khoang ? "" : " grey")}
            aria-pressed={khoang} onClick={() => setKhoang(true)}>Trong từng khoảng</button>
        </div>
        {dsPn.length > 1 && (
          <select value={pn ?? ""} onChange={(e) => setPn(Number(e.target.value))}
            style={{ width: "auto", minWidth: 220 }} aria-label="Pháp nhân đang xem">
            {dsPn.map((c) => <option key={c.id} value={c.id}>{c.code} – {c.name}</option>)}
          </select>)}
        <span style={{ flex: 1 }} />
        {/* NÚT XUẤT EXCEL THẬT (14/9/2026). Trước đây nó chỉ hiện câu "đang xây dựng" — một nút
            hứa rồi không làm còn tệ hơn không có nút, vì lần sau người dùng không tin nút nào nữa.
            Tệp do MÁY CHỦ dựng từ đúng gói mà màn hình này đang đọc, nên Excel không thể nói khác
            màn hình; và máy chủ ghi một dòng nhật ký cho mỗi lần xuất. */}
        <button type="button" className="act grey" disabled={dangXuat || !pn}
          onClick={async () => {
            if (!pn) return;
            setDangXuat(true);
            try { toast("Đã tải " + await taiTep(`/dong-tien/khung/${pn}/excel`)); }
            catch (e: any) { toast(e?.message || "Không xuất được Excel", true); }
            finally { setDangXuat(false); }
          }}>{dangXuat ? "Đang dựng tệp…" : "Xuất Excel"}</button>
      </div>

      <p className="muted" style={{ marginTop: 0 }}>{k.cau_pham_vi}</p>

      {/* DÒNG TÓM TẮT NGUỒN SỐ — phần "một nhãn thay cho cột cửa nhập" của phương án dung hoà.
          Đếm theo DÒNG CÓ CỬA (bỏ dòng tự cộng), vì dòng tự cộng không ai nhập được. */}
      <p className="dt-tomtat">
        <b>Nguồn số:</b>{" "}
        <span className="tag ok">{tt.day_du ?? 0} đầy đủ</span>{" "}
        <span className="tag warn">{tt.chua_doi_soat ?? 0} chưa đối soát</span>{" "}
        <span className="tag red">{tt.con_thieu ?? 0} còn thiếu</span>{" "}
        {/* Quá hạn tách riêng khỏi ba mức trạng thái: "còn thiếu" nói dòng chưa có số, "quá hạn"
            nói đã lỡ mốc 24 giờ Chủ tịch chốt. Gộp hai cái vào một nhãn là mất đúng cái khác biệt
            khiến người ta phải đứng dậy làm ngay. */}
        {(k.so_qua_han ?? 0) > 0 && <><span className="tag red">{k.so_qua_han} quá hạn</span>{" "}</>}
        <Link className="the-cua" href="/dong-tien/nguon">Nguyên nhân · bộ phận · cửa nhập →</Link>
      </p>

      {/* TC-40 · BỐN Ô CẢNH BÁO GIỮ NGUYÊN — anh Tuấn chốt 15/9/2026: "số 6 dòng tiền em giữ
          nguyên". Em có đề xuất gỡ bốn ô này (chúng đang ghi "Chưa có nguồn" và lặp lại dòng tóm
          tắt ngay trên), anh Tuấn không đồng ý và khối 06 giữ đúng như cũ. Ghi lại để vòng sau
          không ai gỡ chúng đi lần nữa với cùng một lý do. */}
      <div className="bon-o">{(k.canh_bao || []).map((o: any) => <O key={o.ma} o={o} />)}</div>

      {/* ═══ TC-35 · BIỂU ĐỒ TRƯỚC, BẢNG SAU NÚT ═══════════════════════════════════════════════
          Anh Tuấn chỉ ra 15/9/2026: bảng 14 dòng × 4 mốc "không cần chi tiết ra màn hình, đưa vào
          nút click, ở ngoài để con số báo cáo tổng". Đối chiếu lại thì BẢN VẼ V1.4 vốn đã làm đúng
          như thế: khối này trong bản vẽ chỉ có bốn ô tổng, một biểu đồ, và một nút "Cấu trúc chi
          tiết dòng tiền →". Không có bảng nào trên màn hình.

          Đo hậu quả của cách cũ: khối dòng tiền đổ cả bảng ra làm trang Chủ tịch cao 8.192px so với
          2.791px của bản vẽ. Người mở trang phải cuộn qua bảng mới thấy khối kế tiếp.

          VÌ SAO GẤP TẠI CHỖ chứ không dời hẳn sang /dong-tien: màn hình ấy CÓ "Bảng bốn mốc" nhưng
          KHÔNG có nút đổi kiểu xem (luỹ kế ↔ từng khoảng) và KHÔNG có nút Xuất Excel. Dời đi là âm
          thầm bỏ mất hai tính năng — trong đó nút Excel vừa sửa xong ở vòng TC-28. Gấp lại thì giữ
          đủ, mà khối vẫn co về đúng chiều cao bản vẽ. Nút sang màn hình chi tiết vẫn có, đúng bản vẽ. */}
      <BieuDoBonMoc cot={cot}
        so={(khoang ? k.dong_tien_thuan_khoang : k.dong_tien_thuan) || {}}
        khoang={khoang} vi_sao={k.vi_sao_khong_co_so_cuoi} />

      <p className="dt-nut-chi-tiet">
        <Link className="the-cua" href="/dong-tien">Cấu trúc chi tiết dòng tiền →</Link>
      </p>

      <details className="dt-gap">
        <summary>Bảng bốn mốc — {(k.dong || []).length} dòng · {nCot} mốc</summary>
      <div className="panel wrap">
        <table>
          <thead><tr>
            <th style={{ minWidth: 240 }}>Dòng tiền</th>
            {cot.map((c: any) => <th key={c.ma} className="num">{c.ten}
              <div className="muted" style={{ fontWeight: 400, fontSize: 11 }}>
                {/* Ngày đầu ĐỔI theo kiểu xem: luỹ kế thì mọi cột cùng bắt đầu từ ngày báo cáo,
                    theo khoảng thì cột sau bắt đầu ngay sau ngày kết thúc của cột trước. In sai
                    ngày ở đây là người đọc cộng nhầm hai khoảng chồng nhau.

                    CẢ HAI ĐẦU LẤY CHUỖI ĐÃ ĐỊNH DẠNG SẴN CỦA MÁY CHỦ (tu_hien · den_hien ·
                    tu_hien_khoang). fmtD chỉ là lối lui khi máy chủ chưa gửi chuỗi ấy. Trộn hai
                    nơi định dạng thì ra đúng cái ô đã gặp: "14/09/2026 – 20-09-2026". */}
                {khoang
                  ? (c.tu_hien_khoang || fmtD(c.tu_ngay_khoang || c.tu_ngay))
                  : (c.tu_hien || fmtD(c.tu_ngay))}
                {" – "}{c.den_hien || fmtD(c.den_ngay)}</div></th>)}
            <th style={{ minWidth: 130 }}>Nguồn số</th>
          </tr></thead>
          <tbody>
            {(k.dong || []).map((d: any) => (
              <tr key={d.ma}>
                <td>{d.ten}</td>
                {d.mot_moc
                  ? <td className="num" colSpan={nCot} style={{ textAlign: "right" }}>
                      {d.so_mot_moc === null || d.so_mot_moc === undefined
                        ? RONG(d.vi_sao_rong)
                        : <>{vnd(d.so_mot_moc)} <span className="muted" style={{ fontSize: 11 }}>
                            (một mốc, không theo khoảng)</span></>}
                    </td>
                  : cot.map((c: any) => <td key={c.ma} className="num">
                      {soCua(d)[c.ma] === null || soCua(d)[c.ma] === undefined
                        ? RONG(d.vi_sao_rong || d.bo_phan_chiu_trach_nhiem)
                        : vnd(soCua(d)[c.ma])}
                    </td>)}
                <td style={{ fontSize: 11.5 }}>
                  {d.tu_tinh
                    ? <span className="muted">Tự cộng</span>
                    : <ChipTrangThai ma={d.trang_thai} nhan={d.nhan_trang_thai} />}
                  {khoang && d.la_dong_chay === false && !d.mot_moc &&
                    <div className="muted" style={{ marginTop: 3 }}>mức tại mốc</div>}
                </td>
              </tr>))}
            <tr>
              <td><b>{k.ten_dong_thuan}</b></td>
              {cot.map((c: any) => {
                const t = ((khoang ? k.dong_tien_thuan_khoang : k.dong_tien_thuan) || {})[c.ma];
                return <td key={c.ma} className="num"><b>
                  {t === null || t === undefined ? RONG(k.vi_sao_khong_co_so_cuoi) : vnd(t)}
                </b></td>;
              })}
              <td />
            </tr>
          </tbody>
        </table>

        {/* CÂU NHẮC ĐỔI THEO KIỂU XEM. Giữ nguyên một câu cho cả hai kiểu là chắc chắn sai một
            nửa số lần: luỹ kế thì cộng bốn cột là sai, theo khoảng thì cộng bốn cột lại đúng. */}
        <p className="muted" style={{ fontSize: 12, marginBottom: 0 }}>
          {khoang ? k.cong_bon_cot_khi_xem_khoang : k.cong_bon_cot_la_sai}</p>
        {k.vi_sao_khong_co_so_cuoi && <p className="muted" style={{ fontSize: 12, marginBottom: 0 }}>
          {k.vi_sao_khong_co_so_cuoi}</p>}
        <p className="muted" style={{ fontSize: 12, marginBottom: 0 }}>
          Tập dòng và tên dòng đáy do MÁY CHỦ cắt theo vai đang đăng nhập (SEC-02); màn hình không
          lọc gì thêm. Số làm tròn đến đồng, dòng tổng cộng từ các dòng đã làm tròn.
          {k.doi_soat_den_ngay ? ` Đối soát đến ${fmtD(String(k.doi_soat_den_ngay))}.` : ""}
        </p>
      </div>
      </details>
    </section>
  );
}
