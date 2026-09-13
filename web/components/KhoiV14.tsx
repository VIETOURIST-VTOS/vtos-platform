"use client";
/** SÁU KHỐI CÒN LẠI CỦA BẢN VẼ V1.4 – màn hình 01 (13/9/2026).
 *
 *  Bản vẽ xếp tám khối; VTOS đã có 01 phạm vi/kỳ, 02 cần quyết định, 03 tám thẻ, và 06 dòng tiền
 *  (dựng theo hình khác, xem ghi chú cuối tệp). Tệp này dựng phần còn lại:
 *
 *    04b  Hiệu quả đội xe trong kỳ
 *    04c  Tồn đọng theo bộ phận
 *    05a  Phải thu theo hạn thanh toán   – 5 nhóm KHÔNG trùng nhau
 *    05b  Phải trả theo hạn thanh toán   – 5 nhóm + quá hạn theo dõi riêng
 *    07   Rủi ro trọng yếu
 *    08   Tiến độ báo cáo & kết luận chỉ đạo
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  RANH GIỚI 09/9 – ĐỌC TRƯỚC KHI SỬA TỆP NÀY
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Sáu khối này HÔM NAY CHƯA CÓ MỘT CON SỐ NÀO. Máy chủ chưa có bảng cho chúng. Đó là lý do mỗi ô
 *  đều ghi "Chưa kết nối" kèm BỘ PHẬN phải nhập và CỬA NHẬP để đi tới.
 *
 *  Bản vẽ chỉ ghi "Chưa kết nối". VTOS ghi thêm bộ phận và cửa nhập, vì một ô trống không nói ai
 *  chịu trách nhiệm thì nó nằm đó mãi: ai đọc cũng nghĩ người khác lo. Đây là chỗ VTOS làm HƠN bản
 *  vẽ, có chủ đích.
 *
 *  TUYỆT ĐỐI KHÔNG điền số mẫu, số ước lượng, hay số suy ra từ khối khác để "cho đỡ trống". Một con
 *  số trên bảng điều hành Chủ tịch là một con số ông ấy sẽ dùng để quyết.
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *
 *  HỢP ĐỒNG VỚI MÁY CHỦ nằm ngay dưới, ở các `type`. Làn viết máy chủ chỉ cần trả đúng những trường
 *  ấy trong /api/v1/dashboard; khối nào chưa có thì để thiếu, màn hình tự hiện "Chưa kết nối" chứ
 *  không vỡ.
 */
import Link from "next/link";
import { Tag } from "@/components/ui";

/* ─────────────────────────────── HỢP ĐỒNG DỮ LIỆU ─────────────────────────────── */

/** 04b · Hiệu quả đội xe trong kỳ. Bốn chỉ số + một trạng thái chốt sổ.
 *  CẢNH BÁO NGHIỆP VỤ ghi trong bản vẽ, giữ nguyên: xe không có lệnh CHƯA CHẮC sẵn sàng, và công
 *  suất tính trên thời gian xe CÓ THỂ khai thác chứ không phải trên số ngày trong kỳ. */
export type HieuQuaXe = {
  ngay_xe_hoat_dong?: number | null;
  cong_suat_khai_thac?: number | null;   // phần trăm, 0–100
  km_chay_rong?: number | null;
  chi_phi_moi_km?: number | null;        // đồng
  da_chot?: boolean;                      // kỳ đã khoá sổ hay chưa
};

/** 04c · Tồn đọng theo bộ phận. MỖI HỒ SƠ CHỈ TÍNH MỘT LẦN (bản vẽ nhấn mạnh): một hồ sơ phát ba
 *  cảnh báo vẫn là một hồ sơ, cộng cả ba là thổi phồng con số. Việc chống trùng làm Ở MÁY CHỦ. */
export type DongTonDong = {
  bo_phan: string;
  ho_so_qua_han?: number | null;
  ho_so_lau_nhat?: string | null;        // ví dụ "42 ngày" hoặc mã hồ sơ
  nguoi_chiu_trach_nhiem?: string | null;
  han_khac_phuc?: string | null;
};

/** 05 · Một nhóm hạn thanh toán. `nhan` là tên nhóm, `mo_ta` là định nghĩa khoảng – in ra màn hình
 *  để không ai phải đoán "2 tuần" tính từ đâu. */
export type NhomHan = { nhan: string; mo_ta: string; so?: number | null };

/** 07 · Rủi ro trọng yếu. Hai mức: cần quyết định (thuộc thẩm quyền Chủ tịch) và cần theo dõi.
 *  Nghiệp vụ thường ngày KHÔNG lên đây – bản vẽ ghi rõ, và đó cũng là lý do khối này khác khối
 *  "Tồn đọng cần xử lý" ở trên. */
export type RuiRo = {
  noi_dung: string;
  muc?: "quyet_dinh" | "theo_doi";
  muc_anh_huong?: string | null;
  don_vi?: string | null;
  nguoi_xu_ly?: string | null;
  han_khac_phuc?: string | null;
  tien_do?: string | null;
};

/** 08 · Tiến độ báo cáo & kết luận chỉ đạo. Theo dõi hồ sơ chưa chốt và việc làm theo chỉ đạo. */
export type DongTienDo = {
  ho_so: string;
  don_vi?: string | null;
  han?: string | null;
  tien_do?: string | null;
  buoc_tiep?: string | null;
};

/* ────────────────────────── MẢNH DÙNG CHUNG ────────────────────────── */

/** Ô rỗng chuẩn của màn hình này: nói CHƯA CÓ GÌ, AI phải nhập, và ĐI ĐÂU để nhập.
 *  Ba thứ ấy đi liền nhau; thiếu một cái là ô trống trở thành việc không ai nhận. */
function ChuaNoi({ ai, cua, cua_ten }: { ai: string; cua?: string; cua_ten?: string }) {
  return (
    <span className="v14-chua">
      <span className="tag">Chưa kết nối</span>
      <span className="muted"> · {ai} nhập</span>
      {cua && <Link className="the-cua" href={cua}>{cua_ten || "Cửa nhập"} →</Link>}
    </span>
  );
}

function DauKhoi({ ten, phu, id }: { ten: string; phu: string; id?: string }) {
  return (
    <div className="mh01-dau" id={id}>
      <h2>{ten}</h2>
      <span className="tag">{phu}</span>
    </div>
  );
}

/** Bảng chưa có dòng nào: vẫn VẼ ĐỦ ĐẦU CỘT rồi mới nói chưa kết nối.
 *  Vì sao không giấu bảng đi: đầu cột chính là bản mô tả việc còn nợ – nhìn vào là biết máy chủ
 *  phải trả những trường gì. Giấu đi thì đến lúc dựng lại phải đi tìm bản vẽ. */
function BangRong({ cot, ghi_chu, ai, cua, cua_ten }:
  { cot: string[]; ghi_chu: string; ai: string; cua?: string; cua_ten?: string }) {
  return (
    <>
      <div className="wrap">
        <table className="v14-bang">
          <thead><tr>{cot.map((c) => <th key={c}>{c}</th>)}</tr></thead>
          <tbody>
            <tr><td colSpan={cot.length} className="v14-trong">
              <ChuaNoi ai={ai} cua={cua} cua_ten={cua_ten} />
            </td></tr>
          </tbody>
        </table>
      </div>
      <p className="muted v14-ghi">{ghi_chu}</p>
    </>
  );
}

/* ───────────────────────── 04b · HIỆU QUẢ ĐỘI XE ───────────────────────── */

export function KhoiHieuQuaXe({ d }: { d?: HieuQuaXe | null }) {
  const o = d || {};
  const so = (x: any, duoi = "") =>
    x === null || x === undefined || x === "" ? null : `${x}${duoi}`;
  const cot: [string, string | null][] = [
    ["Ngày xe hoạt động", so(o.ngay_xe_hoat_dong)],
    ["Công suất khai thác", so(o.cong_suat_khai_thac, "%")],
    ["Km chạy rỗng", so(o.km_chay_rong)],
    ["Chi phí / km", so(o.chi_phi_moi_km, " đ")],
  ];
  return (
    <section className="panel" id="hieu-qua-doi-xe">
      <DauKhoi ten="Hiệu quả đội xe trong kỳ" phu="Theo kỳ đang chọn" />
      <div className="v14-o-ds">
        {cot.map(([nhan, gt]) => (
          <div key={nhan} className={"v14-o" + (gt === null ? " rong" : "")}>
            <div className="v14-o-nhan">{nhan}</div>
            <div className="v14-o-so">{gt ?? "—"}</div>
          </div>
        ))}
        {/* Ô này là TRẠNG THÁI, không phải con số – nên không dùng phông chữ số. Phông số sinh ra
            để cột số dóng thẳng hàng; đặt một chữ tiếng Việt vào đó thì chữ giãn ra trông như lỗi. */}
        <div className="v14-o rong">
          <div className="v14-o-nhan">Kết quả đã chốt</div>
          <div className="v14-o-so v14-o-chu">{o.da_chot ? "Đã chốt" : "Chưa chốt"}</div>
        </div>
      </div>
      {cot.every(([, g]) => g === null) &&
        <p className="v14-ghi"><ChuaNoi ai="Đội xe" cua="/doi-xe" cua_ten="Cửa nhập đội xe" /></p>}
      {/* Hai câu cảnh báo nghiệp vụ của bản vẽ. Giữ nguyên vì cả hai đều là chỗ dễ đọc sai con số. */}
      <p className="muted v14-ghi">
        Xe không có lệnh <b>chưa chắc</b> sẵn sàng; công suất tính trên thời gian xe <b>có thể</b>
        {" "}khai thác, không phải trên số ngày trong kỳ. Hướng dẫn viên vẫn được quản lý riêng.
      </p>
    </section>
  );
}

/* ───────────────────────── 04c · TỒN ĐỌNG THEO BỘ PHẬN ───────────────────────── */

export function KhoiTonDongBoPhan({ ds }: { ds?: DongTonDong[] | null }) {
  const co = ds || [];
  const cot = ["Bộ phận", "Hồ sơ quá hạn", "Hồ sơ lâu nhất", "Người chịu trách nhiệm", "Hạn khắc phục"];
  const ghi = "Mỗi hồ sơ chỉ tính MỘT lần: một hồ sơ phát ba cảnh báo vẫn là một hồ sơ. Việc chống cộng trùng làm ở máy chủ, không làm ở màn hình.";
  return (
    <section className="panel" id="ton-dong-bo-phan">
      <DauKhoi ten="Tồn đọng theo bộ phận" phu="Mỗi hồ sơ chỉ tính một lần" />
      {co.length === 0
        ? <BangRong cot={cot} ghi_chu={ghi} ai="Công nghệ thông tin" cua="/alerts" cua_ten="Trang cảnh báo" />
        : <>
            <div className="wrap">
              <table className="v14-bang">
                <thead><tr>{cot.map((c) => <th key={c}>{c}</th>)}</tr></thead>
                <tbody>
                  {co.map((r) => (
                    <tr key={r.bo_phan}>
                      <td><b>{r.bo_phan}</b></td>
                      <td className="num">{r.ho_so_qua_han ?? "—"}</td>
                      <td>{r.ho_so_lau_nhat || <span className="muted">—</span>}</td>
                      <td>{r.nguoi_chiu_trach_nhiem || <span className="muted">chưa gán</span>}</td>
                      <td>{r.han_khac_phuc || <span className="muted">chưa đặt</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="muted v14-ghi">{ghi}</p>
          </>}
    </section>
  );
}

/* ───────────────────────── 05 · PHẢI THU & PHẢI TRẢ THEO HẠN ───────────────────────── */

/** NĂM NHÓM KHÔNG TRÙNG NHAU, và đó là điểm khác hẳn bảng dòng tiền bốn mốc LŨY KẾ ở khối 06.
 *  Ở đây một đợt thanh toán rơi vào ĐÚNG MỘT nhóm, nên cộng năm nhóm lại ra tổng công nợ; ở bảng
 *  dòng tiền thì cột 14 ngày đã chứa trọn cột 7 ngày, cộng vào là sai.
 *
 *  Hai tháng và ba tháng tính theo THÁNG LỊCH từ ngày báo cáo, không mặc định 60/90 ngày (bản vẽ
 *  ghi rõ). Hạn rơi ĐÚNG ngày báo cáo thuộc nhóm sắp đến hạn đầu tiên, không thuộc nhóm quá hạn. */
const PHAI_THU: NhomHan[] = [
  { nhan: "Quá hạn", mo_ta: "Hạn thanh toán trước ngày báo cáo" },
  { nhan: "2 tuần", mo_ta: "Từ ngày báo cáo đến hết ngày +14" },
  { nhan: "4 tuần", mo_ta: "Sau 2 tuần đến hết ngày +28" },
  { nhan: "2 tháng", mo_ta: "Sau 4 tuần đến hết mốc +2 tháng lịch" },
  { nhan: "Dài hạn", mo_ta: "Sau mốc 2 tháng" },
];
const PHAI_TRA: NhomHan[] = [
  { nhan: "1 tuần", mo_ta: "Từ ngày báo cáo đến hết ngày +7" },
  { nhan: "2 tuần", mo_ta: "Sau 1 tuần đến hết ngày +14" },
  { nhan: "4 tuần", mo_ta: "Sau 2 tuần đến hết ngày +28" },
  { nhan: "3 tháng", mo_ta: "Sau 4 tuần đến hết mốc +3 tháng lịch" },
  { nhan: "Dài hạn", mo_ta: "Sau mốc 3 tháng" },
];

function KhoiHan({ ten, khung, ds, ai, cua, cua_ten, chan, id }: {
  ten: string; khung: NhomHan[]; ds?: Record<string, number | null> | null;
  ai: string; cua: string; cua_ten: string; chan?: React.ReactNode; id: string;
}) {
  const s = ds || {};
  return (
    <section className="panel" id={id}>
      <DauKhoi ten={ten} phu="5 nhóm không trùng nhau" />
      <div className="v14-han-ds">
        {khung.map((n) => {
          const gt = s[n.nhan];
          const rong = gt === null || gt === undefined;
          return (
            <div key={n.nhan} className={"v14-han" + (rong ? " rong" : "")}>
              <div className="v14-han-nhan">{n.nhan}</div>
              <div className="v14-han-so">{rong ? "—" : gt.toLocaleString("vi-VN")}</div>
              {rong && <span className="tag">Chưa kết nối</span>}
              <div className="v14-han-mo">{n.mo_ta}</div>
            </div>
          );
        })}
      </div>
      {chan}
      <p className="v14-ghi"><ChuaNoi ai={ai} cua={cua} cua_ten={cua_ten} /></p>
      <p className="muted v14-ghi">
        Năm nhóm <b>không lũy kế và không trùng nhau</b>, nên cộng cả năm ra đúng tổng công nợ —
        khác bảng dòng tiền bốn mốc bên trên, ở đó cột sau đã chứa trọn cột trước. Mốc tháng tính
        theo <b>tháng lịch</b> từ ngày báo cáo, không mặc định 60 hay 90 ngày. Hạn rơi đúng ngày báo
        cáo thuộc nhóm sắp đến hạn đầu tiên. Khoản <b>chưa có hạn</b> theo dõi riêng, không tự xếp
        vào Dài hạn.
      </p>
    </section>
  );
}

export function KhoiPhaiThu({ ds }: { ds?: Record<string, number | null> | null }) {
  return <KhoiHan id="phai-thu" ten="Phải thu theo hạn thanh toán" khung={PHAI_THU} ds={ds}
    ai="Kế toán" cua="/ra-soat-cot-tien" cua_ten="Cửa nhập công nợ phải thu" />;
}

export function KhoiPhaiTra({ ds, qua_han }: {
  ds?: Record<string, number | null> | null; qua_han?: number | null;
}) {
  /* PHẢI TRẢ QUÁ HẠN THEO DÕI RIÊNG, không cộng vào nhóm 1 tuần (bản vẽ ghi rõ). Gộp vào là một
     khoản đã trễ trông giống một khoản sắp tới hạn – hai việc khác hẳn nhau về mức khẩn. */
  const chan = (
    <div className="v14-quahan">
      <b>Phải trả quá hạn:</b>{" "}
      {qua_han === null || qua_han === undefined
        ? <><span className="the-so do v14-qh-so">—</span> <span className="tag">Chưa kết nối</span></>
        : <span className="the-so do v14-qh-so">{qua_han.toLocaleString("vi-VN")}</span>}
      <div className="muted">Theo dõi riêng, <b>không cộng</b> vào nhóm 1 tuần.</div>
    </div>
  );
  return <KhoiHan id="phai-tra" ten="Phải trả theo hạn thanh toán" khung={PHAI_TRA} ds={ds}
    ai="Kế toán" cua="/nha-cung-cap" cua_ten="Cửa nhập công nợ phải trả" chan={chan} />;
}

/* ───────────────────────── 07 · RỦI RO TRỌNG YẾU ───────────────────────── */

export function KhoiRuiRo({ ds }: { ds?: RuiRo[] | null }) {
  const co = ds || [];
  const cot = ["Nội dung", "Mức ảnh hưởng", "Đơn vị", "Người xử lý", "Hạn khắc phục", "Tiến độ"];
  const ghi = "Chỉ trình việc cần quyết định hoặc cần theo dõi ở cấp lãnh đạo; cảnh báo thường ngày nằm lại ở phòng ban. Lỗi gom theo VẤN ĐỀ và ĐƠN VỊ, không trình hàng trăm dòng cùng loại.";
  return (
    <section className="panel" id="rui-ro">
      <DauKhoi ten="Rủi ro trọng yếu" phu="Đã gom nhóm" />
      <div className="v14-muc-ds">
        <span className="tag red">Cần quyết định</span>
        <span className="muted">hồ sơ thuộc thẩm quyền Chủ tịch</span>
        <span className="tag warn">Cần theo dõi</span>
        <span className="muted">rủi ro lớn, đã có người xử lý và hạn</span>
      </div>
      {co.length === 0
        ? <BangRong cot={cot} ghi_chu={ghi} ai="Các phòng ban" cua="/ngoai-le" cua_ten="Cửa nhập ngoại lệ" />
        : <>
            <div className="wrap">
              <table className="v14-bang">
                <thead><tr>{cot.map((c) => <th key={c}>{c}</th>)}</tr></thead>
                <tbody>
                  {co.map((r, i) => (
                    <tr key={i}>
                      <td>
                        <b>{r.noi_dung}</b>{" "}
                        {r.muc === "quyet_dinh"
                          ? <Tag cls="red">Cần quyết định</Tag>
                          : <Tag cls="warn">Cần theo dõi</Tag>}
                      </td>
                      <td>{r.muc_anh_huong || <span className="muted">—</span>}</td>
                      <td>{r.don_vi || <span className="muted">—</span>}</td>
                      <td>{r.nguoi_xu_ly || <span className="muted">chưa gán</span>}</td>
                      <td>{r.han_khac_phuc || <span className="muted">chưa đặt</span>}</td>
                      <td>{r.tien_do || <span className="muted">—</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="muted v14-ghi">{ghi}</p>
          </>}
    </section>
  );
}

/* ───────────────────────── 08 · TIẾN ĐỘ BÁO CÁO & KẾT LUẬN CHỈ ĐẠO ───────────────────────── */

export function KhoiTienDoBaoCao({ ds }: { ds?: DongTienDo[] | null }) {
  const co = ds || [];
  const cot = ["Hồ sơ / kết luận", "Đơn vị phụ trách", "Hạn", "Tiến độ", "Bước tiếp theo"];
  const ghi = "Theo dõi hồ sơ chưa chốt và công việc thực hiện theo chỉ đạo. Một dòng ở đây là một việc có người chịu và có hạn — không phải một ghi chú.";
  return (
    <section className="panel" id="tien-do-bao-cao">
      <DauKhoi ten="Tiến độ báo cáo &amp; kết luận chỉ đạo" phu="Theo trách nhiệm" />
      {co.length === 0
        ? <BangRong cot={cot} ghi_chu={ghi} ai="Văn phòng Hội đồng quản trị" cua="/reports" cua_ten="Trang báo cáo" />
        : <>
            <div className="wrap">
              <table className="v14-bang">
                <thead><tr>{cot.map((c) => <th key={c}>{c}</th>)}</tr></thead>
                <tbody>
                  {co.map((r, i) => (
                    <tr key={i}>
                      <td><b>{r.ho_so}</b></td>
                      <td>{r.don_vi || <span className="muted">—</span>}</td>
                      <td>{r.han || <span className="muted">chưa đặt</span>}</td>
                      <td>{r.tien_do || <span className="muted">—</span>}</td>
                      <td>{r.buoc_tiep || <span className="muted">—</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="muted v14-ghi">{ghi}</p>
          </>}
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════════════════
 * KHỐI 06 – DÒNG TIỀN: KHÔNG DỰNG Ở ĐÂY, CÓ LÝ DO
 *
 * VTOS đã có components/KhoiDongTien.tsx, lấy số từ làn Dòng tiền. Bản vẽ V1.4 muốn một hình khác:
 * bốn mốc 7/14/30/60 KHÔNG lũy kế, bảng chi tiết chuyển sang trang riêng, và thay cột "Cửa nhập –
 * bộ phận" bằng ba trạng thái Đầy đủ / Còn thiếu / Chưa đối soát.
 *
 * Anh Tuấn đã chốt phương án dung hoà cho khối ấy ngày 13/9. Nhưng nó đụng SỐ của làn khác, không
 * phải việc của lớp giao diện — dựng một khối thứ hai ở đây là có hai chỗ cùng nói về dòng tiền mà
 * không chỗ nào là chỗ thật. Để nguyên khối cũ, và đổi nó trong một vòng riêng cùng làn Dòng tiền.
 * ═══════════════════════════════════════════════════════════════════════════════════════════ */
