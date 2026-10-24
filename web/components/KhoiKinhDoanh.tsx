"use client";
/** BA KHỐI KINH DOANH & NỘI BỘ của màn hình Chủ tịch — anh Tuấn chốt giữ 15/9/2026.
 *
 *  Kinh doanh Lẻ · Kinh doanh Đoàn · Báo cáo ngày (Điều 12).
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  VÌ SAO GOM BA KHỐI NÀY VÀO MỘT TỆP
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Trước vòng này ba khối nằm thẳng trong `page.tsx`, mỗi khối một khối JSX dài với bảng riêng.
 *  Anh Tuấn chốt mỗi khối phải có "biểu đồ và số + phân tích" — tức mỗi khối thêm một hình, một
 *  câu đọc hộ, và bỏ bảng. Để nguyên trong page.tsx thì trang chủ phình ra và không còn đọc được
 *  bố cục màn hình chỉ bằng cách liếc qua tệp.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  BẢNG ĐI, BIỂU ĐỒ ĐẾN — VÀ VÌ SAO KHÔNG MẤT GÌ
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Bảng cũ liệt kê từng nhân viên một dòng: tên, số tiền, tỉ lệ đạt mốc. Biểu đồ thanh ngang nói
 *  đúng ba thứ ấy, thêm được thứ tự và độ lớn tương đối mà bảng không nói, và ngắn hơn hẳn. Danh
 *  sách đầy đủ vẫn còn nguyên ở /sales-reports — chỗ của nó, nơi người ta đi tìm nó.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  "PHÂN TÍCH" LÀ ĐỌC HỘ CON SỐ MÁY CHỦ ĐÃ TÍNH, KHÔNG PHẢI NHẬN XÉT
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Ranh giới 09/9 giữ nguyên: màn hình KHÔNG tính ra con số nghiệp vụ mới. Câu đọc hộ ở đây chỉ
 *  đếm lại những dòng máy chủ gửi (bao nhiêu người, ai cao nhất, bao nhiêu người âm) và nói thành
 *  câu. Đó là việc của màn hình. Còn "tháng này tốt hay xấu" thì cần một kế hoạch tháng để so, mà
 *  kế hoạch tháng chưa có cửa nhập — nên màn hình KHÔNG nói câu ấy.
 */
import Link from "next/link";
import { gonSo, type Thanh } from "@/components/BieuDo";

function Dau({ ten, phu }: { ten: string; phu?: string }) {
  return (
    <div className="mh01-dau">
      <h2>{ten}</h2>
      {phu && <span className="tag">{phu}</span>}
    </div>
  );
}

/** Câu đọc hộ cho một bảng xếp hạng. Chỉ đếm lại dòng máy chủ gửi — không tính chỉ tiêu mới.
 *  Trả về chuỗi rỗng khi không có gì đáng nói: một câu "có 0 người" không giúp ai cả. */
/** TC-98 · Doanh thu của phòng (anh Tuấn 29/9/2026): tháng này và lũy kế năm, do máy chủ tính
 *  (`sections.doanh_thu_phong`, services/dashboard.doanh_thu_phong). Màn hình chỉ bày. */
/* QT-3 24/10/2026 — số chuyến đi qua chuẩn Việt. Trước đây nối thẳng nên lũy kế năm hiện
   `1250 chuyến`, cạnh ô tiền `135,8 tỷ` của chính nó — hai cách viết số trong một khối. */
const dem = (x: any) =>
  typeof x === "number" ? x.toLocaleString("vi-VN") : (x ?? "");

function DoanhThuPhong({ p, ky, nam }: { p?: any; ky?: string; nam?: number }) {
  if (!p) return null;
  const thang = ky ? `${ky.slice(5, 7)}/${ky.slice(0, 4)}` : "tháng này";
  return (
    <div className="kd-dt">
      <div className="kd-dt-o">
        <div className="kd-dt-nhan">Doanh thu tháng {thang}</div>
        <div className="kd-dt-so">{gonSo(Number(p.thang) || 0, "tien")}</div>
        <div className="kd-dt-phu">{dem(p.chuyen_thang)} chuyến</div>
      </div>
      <div className="kd-dt-o">
        <div className="kd-dt-nhan">Lũy kế năm {nam ?? ""}</div>
        <div className="kd-dt-so">{gonSo(Number(p.nam) || 0, "tien")}</div>
        <div className="kd-dt-phu">{dem(p.chuyen_nam)} chuyến</div>
      </div>
    </div>
  );
}

export function docHoXepHang(ds: Thanh[], don_vi: "doanh thu" | "lợi nhuận"): string {
  const co = ds.filter((h) => typeof h.gt === "number") as { ten: string; gt: number }[];
  if (co.length === 0) return "";
  const xep = [...co].sort((a, b) => b.gt - a.gt);
  const dan = xep[0];
  const am = co.filter((h) => h.gt < 0).length;
  const khong = co.filter((h) => h.gt === 0).length;
  const phan: string[] = [`${co.length} người có ${don_vi} trong kỳ`];
  if (dan.gt > 0) phan.push(`cao nhất là ${dan.ten} với ${gonSo(dan.gt, "tien")}`);
  // Số người ÂM và số người BẰNG 0 là hai việc khác nhau: âm là lỗ, 0 là chưa có chuyến nào chốt.
  if (am > 0) phan.push(`${am} người đang âm`);
  if (khong > 0) phan.push(`${khong} người chưa có chuyến nào quyết toán`);
  return phan.join(" · ") + ".";
}

export function KhoiKinhDoanhLe({ ds, bieu_do, dt }: { ds?: any[] | null; bieu_do?: any; dt?: any }) {
  const co = ds || [];
  const thanh: Thanh[] = co.map((r: any) => ({
    ten: r.sales, gt: r.revenue === null || r.revenue === undefined ? null : Number(r.revenue),
  }));
  const doc = docHoXepHang(thanh, "doanh thu");
  return (
    <section className="panel" id="kd-le">
      <Dau ten="Kinh doanh Lẻ" phu="doanh thu tính chỉ tiêu tháng" />
      <DoanhThuPhong p={dt?.le} ky={dt?.ky} nam={dt?.nam} />
      {co.length === 0
        ? <p className="muted">Chưa có chuyến nào quyết toán trong tháng.</p>
        : <>
            {bieu_do}
            {doc && <p className="muted v14-ghi">{doc}</p>}
          </>}
      <p className="muted v14-ghi">
        Phòng Lẻ hưởng theo <b>mốc doanh thu</b> chuyến đã quyết toán.{" "}
        <Link className="the-cua" href="/sales-reports?mang=le">Danh sách đầy đủ →</Link>
      </p>
    </section>
  );
}

export function KhoiKinhDoanhDoan({ d, bieu_do, dt }: { d?: any | null; bieu_do?: any; dt?: any }) {
  const rows = d?.rows || [];
  const thanh: Thanh[] = rows.map((r: any) => ({
    ten: r.sales,
    gt: r.profit_share === null || r.profit_share === undefined ? null : Number(r.profit_share),
  }));
  const doc = docHoXepHang(thanh, "lợi nhuận");
  return (
    <section className="panel" id="kd-doan">
      <Dau ten="Kinh doanh Đoàn (MICE)" phu="lợi nhuận chia tháng" />
      <DoanhThuPhong p={dt?.doan} ky={dt?.ky} nam={dt?.nam} />
      {rows.length === 0
        ? <p className="muted">Chưa có chuyến đoàn nào quyết toán trong tháng.</p>
        : <>
            {bieu_do}
            {doc && <p className="muted v14-ghi">{doc}</p>}
          </>}
      {/* HAI KHỐI NÀY KHÔNG SO THẲNG ĐƯỢC VỚI NHAU, và câu ấy phải nằm ngay đây chứ không ở chỗ
          khác: hai khối cạnh nhau, cùng đơn vị đồng, cùng kiểu biểu đồ — không nói ra thì người
          đọc đương nhiên so, và so một bên doanh thu với một bên lợi nhuận là so hai thứ khác hẳn. */}
      <p className="muted v14-ghi">
        Phòng Đoàn hưởng theo <b>chia lợi nhuận</b>, không theo mốc doanh thu như phòng Lẻ — nên
        con số ở đây là <b>lợi nhuận</b>, không so thẳng được với khối Kinh doanh Lẻ. Số chính thức
        nằm ở bảng lương.{" "}
        {typeof d?.so_chuyen === "number" && <>{d.so_chuyen} chuyến đoàn đã quyết toán trong tháng.{" "}</>}
        <Link className="the-cua" href="/sales-reports?mang=doan">Danh sách đầy đủ →</Link>
      </p>
    </section>
  );
}

export function KhoiBaoCaoNgay({ d, bieu_do }: { d?: any | null; bieu_do?: any }) {
  if (!d) {
    return (
      <section className="panel" id="bao-cao-ngay">
        <Dau ten="Báo cáo ngày (Điều 12)" phu="tháng này" />
        <p className="muted">
          <span className="tag">Chưa kết nối</span> Máy chủ chưa trả tỉ lệ nộp báo cáo ngày.{" "}
          <Link className="the-cua" href="/reports">Trang báo cáo →</Link>
        </p>
      </section>
    );
  }
  const ty = typeof d.ty_le_nop === "number" ? d.ty_le_nop : null;
  return (
    <section className="panel" id="bao-cao-ngay">
      <Dau ten="Báo cáo ngày (Điều 12)" phu="tháng này" />
      {bieu_do}
      <p className="muted v14-ghi">
        {d.nhan_su} nhân sự · {d.ngay_lam_viec} ngày làm việc
        {ty !== null && <> · tỉ lệ nộp <b>{Math.round(ty * 100)}%</b></>}
        {/* "Thiếu 2 ngày liên tiếp" là con số ĐÁNG LO nhất trong khối, vì nó là ngưỡng kỷ luật —
            nên nó được tô, không nằm lẫn trong dãy chữ xám. */}
        {typeof d.thieu_2_ngay === "number" && d.thieu_2_ngay > 0 && (
          <> · <b className="v14-canh">{d.thieu_2_ngay}</b> lượt thiếu 2 ngày liên tiếp</>
        )}
        {" "}<Link className="the-cua" href="/reports">Xem tổng hợp →</Link>
      </p>
    </section>
  );
}
