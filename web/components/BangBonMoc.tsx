"use client";
import { useCallback, useEffect, useState } from "react";
import { api, fmtD, taiTep, vnd } from "@/lib/api";
import { BieuDoCot, type Diem } from "@/components/BieuDo";
import { useShell } from "@/components/Shell";

/** BẢNG BỐN MỐC — hình, bảng, nút đổi kiểu xem và nút Xuất Excel, gộp thành MỘT khối.
 *
 *  ══════════════════════════════════════════════════════════════════════════════════════════════
 *  TC-63 · KHỐI NÀY RỜI MÀN HÌNH CHỦ TỊCH VỀ VỚI MÀN HÌNH DÒNG TIỀN
 *  ══════════════════════════════════════════════════════════════════════════════════════════════
 *  "em chuyển qua gộp với dòng tiền hoặc là ẩn khỏi màn hình chủ tịch"   — anh Tuấn, 18/9/2026
 *
 *  Hôm trước anh Tuấn hỏi: "bảng 4 mốc đó trùng với bảng dòng tiền và bảng phải thu phải trả?".
 *  Đếm ra thì TRÙNG, và trùng theo BA cách đếm khác nhau trên cùng một màn hình:
 *    · bảng bốn mốc đọc chứng từ thô theo NGÀY CAM KẾT, gộp thành bốn mốc luỹ kế;
 *    · Phải thu / Phải trả đọc SỔ NGHĨA VỤ dựng trên chính những chứng từ ấy, chia bảy nhóm hạn;
 *    · hình 13 tuần đọc `forecast_13w`, chia theo TUẦN.
 *  Ba cách đếm cùng một dòng tiền, đứng cạnh nhau trên một màn hình, là ba con số mà người đọc sẽ
 *  cộng hoặc trừ lẫn nhau trong đầu — và phép tính ấy không có đáp án đúng.
 *
 *  GỘP, CHỨ KHÔNG XOÁ — và đây là chỗ phải cân nhắc thật. Bảng bốn mốc mang theo HAI thứ mà màn
 *  hình /dong-tien trước vòng này KHÔNG có: nút đổi kiểu xem (luỹ kế ↔ trong từng khoảng) và nút
 *  Xuất Excel. Xoá thẳng khối khỏi màn hình Chủ tịch là âm thầm bỏ mất hai tính năng — đúng cái
 *  lỗi mà luật "rỗng khác không" và bài học TC-61 sinh ra để chặn. Nên cả khối chuyển nguyên vẹn
 *  sang /dong-tien, thay cho bảng bốn mốc CŨ ở đó.
 *
 *  VÌ SAO THAY CHỨ KHÔNG ĐẶT CẠNH: /dong-tien vốn đã có một "Bảng bốn mốc" dựng từ
 *  `/dong-tien/bang`. Khối này dựng từ `/dong-tien/khung`, mà `khung_dong_tien.ghep()` nhận CHÍNH
 *  `bang` ấy làm đầu vào rồi bổ sung trạng thái nguồn số, số theo từng khoảng và dòng đáy — tức nó
 *  là tập CHA. Để cả hai là chuyển cái trùng từ màn hình này sang màn hình khác, không phải bỏ nó.
 *
 *  KHỐI NÀY KHÔNG LỌC GÌ HẾT. Máy chủ trả đúng tập dòng của vai đang đăng nhập (SEC-02), kể cả
 *  tên dòng đáy; trình duyệt vẽ đúng những gì nhận được. Một câu kiểu `if (vai === "tgd") ẩn dòng
 *  vay` ở đây là SEC-02 đã hỏng — dòng bị ẩn vẫn ĐÃ rời khỏi máy chủ.
 *
 *  HAI ĐIỀU KHÔNG LÀM
 *  1. Không hiện "0 đ" thay cho "chưa có số". Ô rỗng ghi "Chưa có nguồn" kèm tên bộ phận phải
 *     nhập — người đọc biết đi hỏi ai, thay vì tin một con số không có thật.
 *  2. Không cộng bốn cột Ở KIỂU LUỸ KẾ. Bốn cột lũy kế từ cùng một ngày nên chồng lên nhau; cộng
 *     lại ra một con số lớn gấp mấy lần thực tế. Câu nhắc nằm ngay dưới bảng, và nó ĐỔI theo kiểu
 *     xem đang chọn — ở kiểu "trong từng khoảng" thì bốn cột rời nhau nên cộng lại LẠI ĐÚNG.
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

/** TC-40 · CÂU ĐỌC HỘ.
 *
 *  Anh Tuấn chốt 15/9/2026: "dòng tiền rất quan trọng, cần có số và biểu đồ phân tích". Bốn con số
 *  bốn mốc thì phải tự so trong đầu mới ra được điều đáng lo, nên có một câu nói hộ: mốc nào âm
 *  sớm nhất và thiếu bao nhiêu. Câu ấy chỉ ĐỌC LẠI số máy chủ gửi, không tính ra chỉ tiêu mới nào.
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

/** Hình bốn mốc dòng tiền thuần.
 *
 *  Bản vẽ V1.4 kèm câu quy định cách cư xử khi thiếu số:
 *
 *      "Dự báo chưa đủ dữ liệu. Biểu đồ số dư và ngưỡng dự phòng sẽ hiển thị khi có số dư đã đối
 *       soát cùng lịch thu–chi đầy đủ. KHÔNG QUY ĐỔI DỮ LIỆU THIẾU THÀNH SỐ 0."
 *
 *  Câu cuối là luật, không phải lời khuyên. Một đường phẳng ở mức 0 trên biểu đồ dòng tiền đọc ra
 *  là "không có tiền vào ra" — khác hẳn "chưa ai nạp số". Bộ biểu đồ chung giữ đúng luật ấy: mốc
 *  thiếu là một ô trống có khung nét đứt, không phải một cột cao 0.
 *
 *  NGUỒN SỐ: `k.dong_tien_thuan` / `k.dong_tien_thuan_khoang` — đúng hai trường mà dòng đáy của
 *  bảng đang đọc, nên hình không thể nói khác bảng ngay dưới nó. Cố ý KHÔNG tự dò dòng "số dư cuối
 *  khoảng" theo tên tiếng Việt: tên đổi một chữ là hình âm thầm vẽ sang dòng khác.
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
    <BieuDoCot
      ten="Dòng tiền thuần qua bốn mốc"
      phu={khoang ? "trong từng khoảng — bốn cột rời nhau" : "luỹ kế — bốn cột chồng lên nhau"}
      diem={diem}
      ai="Kế toán" cua="/dong-tien/nguon" cua_ten="Nguyên nhân · bộ phận · cửa nhập"
      chan={<>
        {/* CÂU ĐỌC HỘ ĐỨNG TRƯỚC mọi chú thích khác: nó là điều người đọc cần biết, còn phần còn
            lại là cách đọc hình. */}
        {doc && <><b>{doc}</b>{" "}</>}
        {thieu.length > 0 && <>
          Còn thiếu {thieu.length}/{cot.length} mốc: {thieu.map((c: any) => c.ten).join(" · ")}.
          {vi_sao ? " " + vi_sao : ""} Không quy đổi dữ liệu thiếu thành số 0.
        </>}
        {/* KHÔNG nhắc lại "vạch đậm là mốc 0": `BieuDoCot` tự in câu ấy khi có cột âm. Trên ảnh
            dựng ra hai câu gần y hệt nhau đứng liền nhau. */}
      </>} />
  );
}

/** Khối đầy đủ: hàng thao tác · hình · bảng · ba câu chân.
 *
 *  `pn` do trang gọi truyền vào — trang /dong-tien có ô chọn pháp nhân của chính nó, và khối này
 *  KHÔNG dựng thêm một ô chọn thứ hai: hai ô chọn cùng một thứ trên một màn hình là hai người cùng
 *  nhìn một trang mà đang xem hai pháp nhân khác nhau.
 */
export default function BangBonMoc({ pn }: { pn: number | null }) {
  const { toast } = useShell();
  const [k, setK] = useState<any>(null);
  const [an, setAn] = useState(false);   // vai này không mở khối dòng tiền → không vẽ gì
  // Mặc định LUỸ KẾ, không phải kiểu mới. Kiểu luỹ kế là kiểu đã in ra trong tài liệu v1.1 và là
  // kiểu người đọc đang quen; đổi mặc định là hôm sau có người đọc bảng mới bằng thói quen cũ.
  const [khoang, setKhoang] = useState(false);
  const [dangXuat, setDangXuat] = useState(false);

  const tai = useCallback(async () => {
    if (!pn) return;
    try { setK(await api(`/dong-tien/khung/${pn}`)); }
    catch (e: any) {
      if (e?.status === 403) setAn(true);
      else toast(e?.message || "Không tải được bảng bốn mốc", true);
    }
  }, [pn, toast]);
  useEffect(() => { tai(); }, [tai]);

  if (an || !k || !k.xem_duoc) return null;

  const cot = k.cot || [];
  const nCot = cot.length;
  const tt = k.tom_tat_trang_thai || {};

  /** Số của một dòng ở kiểu xem đang chọn. Dòng MỨC không có số theo khoảng nên luôn lấy `so`. */
  const soCua = (d: any) => (khoang && d.la_dong_chay ? d.so_khoang : d.so) || {};

  return (
    <section className="panel" id="bang-bon-moc">
      <div className="mh01-dau"><h2>Bảng bốn mốc</h2></div>

      {/* HÀNG THAO TÁC: kiểu xem · tình trạng nguồn số · nút xuất. Cùng một hàng vì cả ba đều là
          việc người dùng LÀM với bảng ngay dưới, không phải con số để đọc. */}
      <div className="dt-hang">
        <span className="dt-nhan-nho">Kiểu xem</span>
        <div className="dt-kieu" role="group" aria-label="Kiểu xem bốn mốc">
          <button type="button" className={"act" + (khoang ? " grey" : "")}
            aria-pressed={!khoang} onClick={() => setKhoang(false)}>Lũy kế</button>
          <button type="button" className={"act" + (khoang ? "" : " grey")}
            aria-pressed={khoang} onClick={() => setKhoang(true)}>Trong từng khoảng</button>
        </div>
        {/* TÓM TẮT NGUỒN SỐ — đếm theo DÒNG CÓ CỬA (bỏ dòng tự cộng), vì dòng tự cộng không ai
            nhập được. */}
        <span className="muted dt-nhan-nho-mo">Nguồn số</span>
        <span className="tag ok">{tt.day_du ?? 0} đầy đủ</span>
        <span className="tag warn">{tt.chua_doi_soat ?? 0} chưa đối soát</span>
        <span className="tag red">{tt.con_thieu ?? 0} còn thiếu</span>
        {/* Quá hạn tách riêng khỏi ba mức trạng thái: "còn thiếu" nói dòng chưa có số, "quá hạn"
            nói đã lỡ mốc 24 giờ Chủ tịch chốt. Gộp hai cái vào một nhãn là mất đúng cái khác biệt
            khiến người ta phải đứng dậy làm ngay. */}
        {(k.so_qua_han ?? 0) > 0 && <span className="tag red">{k.so_qua_han} quá hạn</span>}
        <span className="dt-day-day" />
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

      {/* Hình đứng TRƯỚC bảng: hình trả lời "bốn mốc đi lên hay đi xuống", bảng trả lời "dòng nào
          làm nên điều đó". Đảo thứ tự là bắt người đọc đi qua mười bốn dòng số trước khi thấy hình
          dáng của chúng — cùng lý lẽ đã dùng ở TC-59. */}
      <BieuDoBonMoc cot={cot}
        so={(khoang ? k.dong_tien_thuan_khoang : k.dong_tien_thuan) || {}}
        khoang={khoang} vi_sao={k.vi_sao_khong_co_so_cuoi} />

      <div className="wrap">
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
    </section>
  );
}
