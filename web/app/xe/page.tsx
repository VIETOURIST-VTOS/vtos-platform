"use client";
import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, pct } from "@/lib/api";
import { errMsg } from "@/components/ui";
import { BieuDoDuong } from "@/components/BieuDo";
import ChiPhiKyPanel from "@/components/doixe/ChiPhiKyPanel";
import TrangPhanHe from "@/components/TrangPhanHe";

/** Màn điều hành đội xe — `/xe`. Bố cục v3.3 (anh Tuấn duyệt 09/11/2026).
 *
 *  Anh Tuấn chốt 08/11/2026: màn RIÊNG của đội xe, không cột dọc bên trái, không phân hệ phòng
 *  khác. Shell vẫn bọc (canh đăng nhập, mật khẩu tạm, toast) nhưng ẩn thanh dọc — cờ
 *  `khongThanhBen`.
 *
 *  BỐ CỤC v3.3 — bốn điều bản vẽ chốt, ghi lại vì chúng ĐẢO một quyết định cũ:
 *    1. NĂM MỤC NGHIỆP VỤ trên một hàng ngang, và BỎ mục "Bàn làm việc" khỏi hàng ấy. Tổng quan
 *       không phải một mục ngang hàng với bốn mục kia — nó là chỗ đứng mặc định, nên lối về nó là
 *       nút «Tổng quan» ở đầu hàng chứ không phải một tab thứ sáu.
 *    2. ĐỔI NỘI DUNG TẠI CHỖ. Chọn một nghiệp vụ thì vùng nội dung đổi và CHỈ hiện mục con của
 *       nghiệp vụ ấy. Không mở cả danh mục ở cột bên, không nhảy sang trang khác rồi mất chỗ đang
 *       đứng.
 *    3. HAI NÚT NHẬP CHÍNH chỉ xuất hiện MỘT LẦN, trên tổng quan. Trước bản này mỗi nghiệp vụ có
 *       một cụm thao tác nhanh riêng; lặp lại thì người dùng không biết bấm cái nào là "thật".
 *    4. BIỂU ĐỒ CHIẾM TOÀN CHIỀU NGANG, HÀNG ĐỢI VIỆC ĐẶT DƯỚI BIỂU ĐỒ.
 *       ĐÂY LÀ CHỖ ĐẢO LẠI KS-43/44 (08/11/2026), và lý do cũ vẫn đáng đọc: "doanh thu là thứ
 *       giám đốc XEM, hàng đợi là thứ giám đốc LÀM", nên hàng đợi từng đứng trên cùng. Bản v3.3
 *       chọn ngược: nhìn toàn đội trước, rồi mới tới việc. Ghi cả hai bên ở đây để lần sau ai
 *       muốn đảo lại còn biết mình đang đảo cái gì, chứ không tưởng là sửa một chỗ chưa ai nghĩ.
 *
 *  MỘT CỬA cho cả màn: GET /fleet/ban-lam-viec?ky= trả đủ các vùng. Bốn cửa thì bốn lần chờ, và
 *  bốn cơ hội để hai vùng trên cùng một màn nói hai con số khác nhau.
 *
 *  Ô KỲ CHỈ CÓ HAI MŨI TÊN, KHÔNG CÓ CHỖ GÕ. Lỗi thật trên màn Lãi lỗ: gõ «102026» thì ô hiện
 *  October 2026 nhưng thân trang vẽ kỳ 2026-01 với số gộp lạ (796.985.460 đ, 226 ngày khai thác).
 *  Gốc là component gọi API ở trạng thái tháng gõ dở. Ở đây kỳ là một giá trị YYYY-MM đổi bằng số
 *  tháng, không bao giờ đi qua trạng thái gõ dở.
 *
 *  CHƯA NHẬP ≠ BẰNG 0 — khoản thiếu đeo nhãn vàng, không bao giờ hiện 0. Luật này đã cứu tháng 10
 *  khỏi đọc sai 84,5 tr (KS-36) và 77 tr lương (KS-41). */

const MAU: Record<string, { cham: string; chu: string }> = {
  do:    { cham: "#be2f2f", chu: "#be2f2f" },
  cam:   { cham: "#a66a00", chu: "#a66a00" },
  vang:  { cham: "#c9a227", chu: "#6b5415" },
  trang: { cham: "#fff",    chu: "#5b6b82" },
};

/** Đổi kỳ bằng SỐ THÁNG — không đi qua chuỗi gõ dở. */
function doiKy(ky: string, buoc: number) {
  let [n, t] = ky.split("-").map(Number);
  t += buoc;
  while (t > 12) { t -= 12; n += 1; }
  while (t < 1) { t += 12; n -= 1; }
  return `${String(n).padStart(4, "0")}-${String(t).padStart(2, "0")}`;
}
const kyDoc = (ky: string) => ky.split("-").reverse().join(" / ");
const kyNgan = (ky: string) => ky.slice(5) + "/" + ky.slice(2, 4);

/** Nhãn dùng chung cho mọi chỗ có thể thiếu số. */
const ChuaNhap = () => (
  <span className="tag" style={{ background: "#fdf6e7", color: "#a66a00", fontWeight: 700 }}>
    CHƯA NHẬP
  </span>
);

/** NĂM NHÓM NGHIỆP VỤ của v3.3 — và mọi đường dẫn ở đây đều là MÀN HÌNH CÓ THẬT.
 *
 *  Không dựng màn mới nào: bản v3.3 §11 gọi đợt này là "nối giao diện với chức năng hiện có".
 *  Mỗi mục con trỏ vào đúng cửa đang chạy, kể cả khi cửa ấy là một TAB của /doi-xe. */
type Muc = { ten: string; toi: string; ghi?: string };
const NHOM: { ma: string; ten: string; tom: string; muc: Muc[] }[] = [
  { ma: "dieu-xe", ten: "Điều xe", tom: "Đề nghị xe · lịch và lệnh · tài xế nhận lệnh", muc: [
    { ten: "Lịch & lệnh điều xe", toi: "/lenh-dieu-xe" },
    { ten: "Đề nghị xe", toi: "/lenh-dieu-xe/de-nghi", ghi: "Điều hành tour gửi sang sau khi dự toán được duyệt" },
    { ten: "Lập lệnh điều xe", toi: "/lenh-dieu-xe/lap-lenh" },
    { ten: "Tài xế chưa nhận lệnh", toi: "/lenh-dieu-xe/chua-nhan", ghi: "Hạn nhận: trước giờ khởi hành 24 giờ" },
    { ten: "Xe hôm nay", toi: "/doi-xe/xe-hom-nay" },
  ] },
  { ma: "xe-tai-xe", ten: "Xe & tài xế", tom: "Hồ sơ xe · hồ sơ tài xế · chủ xe và hợp đồng", muc: [
    { ten: "Hồ sơ xe & điều kiện khai thác", toi: "/doi-xe" },
    { ten: "Hồ sơ tài xế", toi: "/tai-xe" },
    { ten: "Chủ xe & quyết toán", toi: "/doi-xe?tab=quyettoan" },
    { ten: "Phạt tài xế", toi: "/doi-xe/phat-tai-xe" },
    { ten: "Việc của tài xế & HDV", toi: "/xe-hdv" },
  ] },
  { ma: "bao-cao", ten: "Báo cáo & chi phí", tom: "Nhật trình chuyến · đề xuất chi · quyết toán · công nợ", muc: [
    { ten: "Nhật trình chuyến", toi: "/doi-xe?tab=chuyen", ghi: "Nơi nhập báo cáo từng xe" },
    { ten: "Đối soát nguồn ngoài", toi: "/doi-xe?tab=giaodich", ghi: "Nơi lập đề xuất chi" },
    { ten: "Công nợ đội xe", toi: "/doi-xe?tab=congno" },
    { ten: "Lãi lỗ đội xe", toi: "/lai-lo-doi-xe", ghi: "Ba tầng chi phí và chi phí kỳ" },
  ] },
  { ma: "bao-duong", ten: "Bảo dưỡng & sự cố", tom: "Lịch bảo dưỡng · báo hỏng · giá dầu và định mức", muc: [
    { ten: "Bảo dưỡng & sửa chữa", toi: "/doi-xe?tab=bao-duong" },
    { ten: "Báo hư hỏng xe", toi: "/doi-xe?tab=bao-hong" },
    { ten: "Giá dầu & định mức", toi: "/doi-xe/gia-dau" },
    { ten: "Sự cố tour", toi: "/su-co-tour" },
  ] },
  { ma: "hieu-qua", ten: "Hiệu quả", tom: "Công suất · tiêu hao · kết quả từng xe", muc: [
    { ten: "Hiệu quả khai thác", toi: "/hieu-qua-doi-xe" },
    { ten: "Lãi lỗ đội xe", toi: "/lai-lo-doi-xe" },
    { ten: "Nhìn lại — thuê xe ngoài khi xe nhà đậu", toi: "/doi-xe?tab=nhin-lai" },
  ] },
];

/** HAI CỬA NHẬP CHÍNH. Cả hai là cửa ĐANG CHẠY trên /doi-xe, không phải form mới dựng ở đây —
 *  `?mo=` chỉ bảo màn ấy bật sẵn đúng biểu mẫu, để giám đốc không phải tự tìm tab rồi tìm nút. */
const CUA_NHAP: { ten: string; toi: string; ghi: string }[] = [
  { ten: "Lập đề xuất chi", toi: "/doi-xe?tab=giaodich&mo=de-xuat-chi",
    ghi: "Mở thẳng biểu mẫu đề xuất chi trên màn Đội xe" },
  { ten: "Nhập báo cáo từng xe", toi: "/doi-xe?tab=chuyen&mo=phieu-chi-phi",
    ghi: "Mở thẳng phiếu chi phí chuyến trên màn Đội xe" },
];

/** Ngăn kéo: xử lý tại chỗ, đóng lại là bàn tự đọc lại số. */
const NGAN_KEO: Record<string, { ten: string; toi: string; nhan: string }> = {
  "quyet-toan": { ten: "Quyết toán chuyến", toi: "/doi-xe", nhan: "Mở bảng quyết toán" },
  "chi-phi-ky": { ten: "Nhập chi phí kỳ", toi: "/lai-lo-doi-xe", nhan: "Mở sổ chi phí kỳ" },
  "ho-so-xe":   { ten: "Hồ sơ xe", toi: "/doi-xe", nhan: "Mở hồ sơ xe" },
  "bao-duong":  { ten: "Bảo dưỡng", toi: "/doi-xe", nhan: "Mở tab bảo dưỡng" },
  "de-xuat":    { ten: "Đề xuất chờ duyệt", toi: "/requests", nhan: "Mở màn đề xuất" },
};

function BanLamViecXe() {
  const { user, toast } = useShell();
  const [ky, setKy] = useState(() => new Date().toISOString().slice(0, 7));
  const [d, setD] = useState<any>(null);
  const [dang, setDang] = useState(true);
  const [keo, setKeo] = useState<string | null>(null);
  /** `null` = đang ở TỔNG QUAN. Khác null = mã nhóm nghiệp vụ đang mở. */
  const [nhom, setNhom] = useState<string | null>(null);

  /** Vai này có được vào màn /xe không — hỏi `hidden_menus` của phiên, tức lời của chính
   *  ma trận quyền ở access.py. Không dựng danh sách vai thứ hai ở web, và không thêm một
   *  cửa hỏi quyền nữa: câu trả lời đã nằm sẵn trong trình duyệt từ lúc đăng nhập. */
  const khongCoQuyen = (user?.hidden_menus || []).includes("/xe");

  const doc = useCallback(async (k: string) => {
    setDang(true);
    try { setD(await api(`/fleet/ban-lam-viec?ky=${k}`)); }
    catch (e) { toast(errMsg(e), true); }
    finally { setDang(false); }
  }, [toast]);

  useEffect(() => { if (!khongCoQuyen) doc(ky); }, [ky, doc, khongCoQuyen]);
  useEffect(() => {
    if (!keo) return;
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setKeo(null); };
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [keo]);

  const hd = d?.hang_doi, sk = d?.so_ky, xe = d?.xe_hom_nay, db = d?.dien_bien;
  const k = keo ? NGAN_KEO[keo] : null;
  const nhomMo = nhom ? NHOM.find((n) => n.ma === nhom) : null;

  /** Hai đường cùng một đơn vị VND trên MỘT trục — đúng luật 4 của bộ biểu đồ dùng chung.
   *  Công suất là phần trăm nên KHÔNG vào đây: nó đứng riêng ở khối số. */
  const diemDB = db?.diem || [];
  const nhanDB = diemDB.map((p: any) => kyNgan(p.ky));
  const chuoi = (truong: string) => diemDB.map((p: any) => ({
    nhan: kyNgan(p.ky), gt: p.co_so ? (p[truong] ?? null) : null,
  }));
  const kyChuaDu = diemDB.filter((p: any) => p.co_so && !p.du_chi_phi_ky);

  // THIẾU QUYỀN: nói rõ, và dừng ở đây. Không vẽ thanh nghiệp vụ, không vẽ hai nút nhập —
  // một cái khung đầy đủ mà rỗng ruột đọc ra như phần mềm hỏng.
  if (khongCoQuyen) return (
    <div className="panel">
      <h1 style={{ marginTop: 0 }}>Điều hành đội xe</h1>
      <p><b>Màn hình này của Công ty TNHH Vận tải Vietrip.</b> Vai trò của bạn chưa được mở
        quyền vào đây, nên VTOS không tải số liệu đội xe.</p>
      <p className="muted">Nếu bạn cần xem, xin quyền ở <b>Quản trị hệ thống → Tài khoản &amp;
        phân quyền</b>. Đây không phải lỗi hệ thống, và cũng không phải màn hình chưa dựng.</p>
      <p><Link href="/">← Về trang tổng CRM</Link></p>
    </div>
  );

  return (<>
    {/* ① NĂM MỤC NGHIỆP VỤ — một hàng ngang, không có mục "Bàn làm việc" (v3.3).
        Lối về tổng quan là nút đầu hàng; lối ra khỏi đội xe nằm cuối hàng, vì màn này
        ẩn thanh dọc nên nếu đây không có thì người dùng chỉ còn nút Back của trình duyệt. */}
    <nav aria-label="Nghiệp vụ đội xe"
         style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 14,
                  borderBottom: "1px solid #dce3ec" }}>
      <button type="button" onClick={() => setNhom(null)}
        aria-current={nhom === null ? "page" : undefined}
        style={{ padding: "8px 12px", border: 0, background: "none", cursor: "pointer",
                 fontWeight: nhom === null ? 700 : 400,
                 borderBottom: nhom === null ? "3px solid #1d5bbf" : "3px solid transparent" }}>
        Tổng quan
      </button>
      {NHOM.map((n) => (
        <button key={n.ma} type="button" onClick={() => setNhom(n.ma)} title={n.tom}
          aria-current={nhom === n.ma ? "page" : undefined}
          style={{ padding: "8px 12px", border: 0, background: "none", cursor: "pointer",
                   fontWeight: nhom === n.ma ? 700 : 400,
                   borderBottom: nhom === n.ma ? "3px solid #1d5bbf" : "3px solid transparent" }}>
          {n.ten}
        </button>))}
      <Link href="/" style={{ padding: "8px 12px", marginLeft: "auto" }}>Trang tổng CRM →</Link>
    </nav>

    <div style={{ display: "flex", flexWrap: "wrap", gap: 14, alignItems: "flex-end",
                  justifyContent: "space-between", marginBottom: 18 }}>
      <div>
        <h1 style={{ margin: "0 0 4px" }}>Điều hành đội xe</h1>
        <p className="muted" style={{ margin: 0 }}>
          Công ty TNHH Vận tải Vietrip · chỉ dữ liệu đội xe
        </p>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span className="muted">Kỳ</span>
        <button type="button" aria-label="Kỳ trước" onClick={() => setKy(doiKy(ky, -1))}>‹</button>
        <strong style={{ minWidth: 92, textAlign: "center" }}>{kyDoc(ky)}</strong>
        <button type="button" aria-label="Kỳ sau" onClick={() => setKy(doiKy(ky, 1))}>›</button>
      </div>
    </div>

    {/* ② MỘT NGHIỆP VỤ ĐANG MỞ — vùng nội dung đổi TẠI CHỖ, chỉ hiện mục con của nghiệp vụ ấy. */}
    {nhomMo && <section>
      <h2 style={{ marginTop: 0 }}>{nhomMo.ten}</h2>
      <p className="muted">{nhomMo.tom}</p>
      <div>
        {nhomMo.muc.map((m) => (
          <div key={m.toi + m.ten}
               style={{ borderTop: "1px solid #e6eaf0", padding: "12px 0",
                        display: "flex", flexWrap: "wrap", gap: 12, alignItems: "baseline" }}>
            <Link href={m.toi} style={{ flex: "999 1 300px", fontWeight: 600 }}>{m.ten}</Link>
            {m.ghi && <span className="muted">{m.ghi}</span>}
          </div>))}
      </div>
      <p className="muted" style={{ marginTop: 14 }}>
        Mỗi mục trên mở đúng màn hình đang chạy của VTOS — đợt này nối lối đi, chưa dựng màn mới.
      </p>
    </section>}

    {/* ③ TỔNG QUAN */}
    {!nhomMo && <>
      {dang && !d && <p className="muted">Đang đọc số…</p>}

      {/* HAI NÚT NHẬP CHÍNH — chỉ xuất hiện MỘT LẦN trên cả màn (v3.3). */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 18 }}>
        {CUA_NHAP.map((c) => (
          <Link key={c.toi} href={c.toi} title={c.ghi}
                style={{ padding: "10px 16px", borderRadius: 8, background: "#1d5bbf",
                         color: "#fff", fontWeight: 700, textDecoration: "none" }}>
            {c.ten}
          </Link>))}
      </div>

      {/* SỐ CỦA KỲ + XE HÔM NAY */}
      {sk && xe && <div style={{ display: "flex", flexWrap: "wrap", gap: 18, marginBottom: 18 }}>
        <section style={{ flex: "999 1 520px", minWidth: 0 }}>
          <h2 style={{ marginTop: 0 }}>Số đội xe kỳ {kyDoc(sk.ky)}</h2>
          <table><tbody>
            <tr><td>Doanh thu</td><td style={{ textAlign: "right" }}><strong>{vnd(sk.doanh_thu)}</strong></td></tr>
            <tr><td className="muted">− Chi phí của xe (gồm chi phí chuyến)</td>
                <td style={{ textAlign: "right" }} className="muted">{vnd(sk.chi_phi_xe)}</td></tr>
            <tr><td className="muted">− Chi phí của đội (bãi xe, điện nước, BHXH…)</td>
                <td style={{ textAlign: "right" }} className="muted">{vnd(sk.chi_phi_cua_doi)}</td></tr>
            {/* v3.3 §8: lợi nhuận khi chưa đủ nhóm chi phí thì PHẢI đọc là TẠM TÍNH. */}
            <tr><td><strong>LỢI NHUẬN ĐỘI XE{sk.chua_nhap?.length > 0 ? " (tạm tính)" : ""}</strong></td>
                <td style={{ textAlign: "right" }}>
                  <strong>{vnd(sk.loi_nhuan)}</strong> <span className="muted">({pct(sk.bien_loi_nhuan)})</span>
                </td></tr>
          </tbody></table>

          {/* CHƯA NHẬP ≠ BẰNG 0 — nêu TÊN nhóm thiếu, không hiện 0. */}
          {sk.chua_nhap?.length > 0 && <p style={{ marginTop: 10 }}>
            <ChuaNhap />{" "}
            <span className="muted">
              {sk.chua_nhap.map((n: any) => n.ten).join(" · ")} — kỳ này chưa có số, nên lợi nhuận ở
              trên đang cao hơn thực tế. Đó là THIẾU SỐ, không phải bằng 0.
            </span>
          </p>}

          <p className="muted" style={{ marginBottom: 0 }}>
            {sk.so_xe_co_chay}/{sk.tong_xe} xe có chạy trong kỳ
          </p>

          {/* CÔNG SUẤT — phần trăm, nên đứng RIÊNG chứ không vào biểu đồ tiền (v3.3 §8).
              Mẫu số đếm tới ngày nào thì nói ra ngày ấy: 52% của nửa tháng đọc như 52% cả tháng
              là một con số sai mà không ai nhìn thấy nó sai. */}
          {sk.cong_suat && <p style={{ marginBottom: 0 }}>
            <strong>Công suất {sk.cong_suat.ty_le !== null && sk.cong_suat.ty_le !== undefined
              ? `${sk.cong_suat.ty_le}%` : "—"}</strong>{" "}
            <span className="muted">
              {sk.cong_suat.den_ngay
                ? `tính đến ${sk.cong_suat.den_ngay} — kỳ đang chạy dở, chưa so được với kỳ đã trọn`
                : "cả kỳ"}
              {sk.cong_suat.tieu_hao ? ` · tiêu hao ${sk.cong_suat.tieu_hao} l/100km` : ""}
            </span>
            {sk.cong_suat.vi_sao_thieu && <> <ChuaNhap />{" "}
              <span className="muted">{sk.cong_suat.vi_sao_thieu}</span></>}
          </p>}
        </section>

        <section style={{ flex: "400 1 320px", minWidth: 0 }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "baseline",
                        justifyContent: "space-between" }}>
            <h2 style={{ marginTop: 0 }}>Xe hôm nay</h2>
            <span className="muted">{xe.doc_luc ? `đọc lúc ${xe.doc_luc}` : "chưa đọc được"}</span>
          </div>
          <p>
            <strong>{xe.dang_di ?? "—"}</strong> đang đi ·{" "}
            <strong>{xe.o_bai ?? "—"}</strong> ở bãi ·{" "}
            <strong>{xe.khong_khop ?? "—"}</strong> không khớp
          </p>
          {/* Không bao giờ im lặng hiện 0: nói rõ nguồn và tuổi số. */}
          {xe.canh_bao && <p style={{ color: "#a66a00" }}>{xe.canh_bao}</p>}
          {xe.danh_sach?.map((x: any) => (
            <div key={x.bien || x.xe} style={{ borderTop: "1px solid #e6eaf0", padding: "8px 0" }}>
              <strong>{x.bien || x.xe}</strong>{x.tai_xe ? ` · ${x.tai_xe}` : ""}
              {x.tour && <div className="muted">{x.tour}</div>}
            </div>))}
        </section>
      </div>}

      {/* ④ BIỂU ĐỒ — TOÀN CHIỀU NGANG (v3.3). Dùng bộ biểu đồ dùng chung của VTOS, không vẽ tay:
          bộ ấy đã giữ sẵn mấy luật v3.3 đòi — rỗng khác không, dưới hai điểm thì không vẽ, trục
          bắt đầu từ 0, và MỘT trục tung. */}
      {db && <section style={{ marginBottom: 18 }}>
        {db.luu_y && <p style={{ color: "#a66a00" }}><strong>Lưu ý:</strong> {db.luu_y}</p>}
        <BieuDoDuong
          ten="Diễn biến đội xe" phu="doanh thu và lợi nhuận theo kỳ"
          nhan={nhanDB} dinh_dang="tien"
          ds={[
            { ten: "DOANH THU", lop: "d3", diem: chuoi("doanh_thu") },
            { ten: "LỢI NHUẬN", lop: "d1", diem: chuoi("loi_nhuan") },
          ]}
          ai="Đội xe" cua="/lai-lo-doi-xe" cua_ten="Lãi lỗ đội xe"
          chan={kyChuaDu.length
            ? <span>Kỳ chưa nhập đủ chi phí:{" "}
                {kyChuaDu.map((p: any) => `${kyNgan(p.ky)} (${p.vi_sao_chua_du})`).join(" · ")}
                {" "}— biên của những kỳ ấy đang đọc CAO hơn thực tế.</span>
            : undefined}
        />
        {!db.du_ve && db.vi_sao && <p className="muted">{db.vi_sao}</p>}
      </section>}

      {/* ⑤ HÀNG ĐỢI VIỆC — v3.3 đặt DƯỚI biểu đồ (xem chú thích đầu tệp: đây là chỗ đảo lại
          thứ tự của KS-43/44). */}
      {hd && <section style={{ marginBottom: 18 }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "baseline",
                      justifyContent: "space-between", marginBottom: 8 }}>
          <h2 style={{ margin: 0 }}>Việc cần xử lý</h2>
          <span className="muted">
            {hd.so_viec_cua_toi} việc · <strong style={{ color: "#be2f2f" }}>{hd.so_do} đỏ</strong>
            {hd.so_cho_nguoi_khac > 0 && ` · ${hd.so_cho_nguoi_khac} đang chờ người khác`}
          </span>
        </div>

        {hd.viec.length === 0
          ? <p className="muted">Không có việc nào đang mở. Đây là số thật, không phải thiếu nguồn.</p>
          : hd.viec.map((v: any) => (
            <div key={v.ma} style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center",
                                     padding: "12px 0", borderBottom: "1px solid #e6eaf0" }}>
              <span aria-hidden="true" style={{ width: 10, height: 10, borderRadius: "50%",
                flex: "0 0 10px", background: (MAU[v.muc] || MAU.vang).cham,
                border: v.muc === "trang" ? "2px solid #afbcce" : undefined }} />
              <span style={{ flex: "999 1 320px", minWidth: 0 }}>
                <strong style={{ display: "block" }}>{v.tieu_de}</strong>
                <span className="muted">{v.mo_ta}</span>
              </span>
              {/* Quyền ẩn NÚT, không ẩn VIỆC: giám đốc vẫn thấy tiền đang treo kể cả khi chưa
                  được bấm. Giấu việc đi thì tiền treo biến mất khỏi tầm mắt người duy nhất
                  quan tâm đến nó. */}
              {v.bam_duoc && v.ngan_keo
                ? <button type="button" onClick={() => setKeo(v.ngan_keo)}>{v.nhan_nut}</button>
                : <span className="muted"><strong>{v.nhan_nut}</strong></span>}
            </div>))}

        {hd.bo_do_hong?.length > 0 && <p style={{ color: "#a66a00" }}>
          {hd.bo_do_hong.length} bộ dò lỗi ({hd.bo_do_hong.join(", ")}) — hàng đợi đang thiếu dòng,
          báo CNTT.
        </p>}
      </section>}

      {/* ⑥ TRANG PHÂN HỆ ĐIỀU HÀNH XE — trước là một TRANG RIÊNG (/phan-he/dhxe), nay nằm
          ngay đây (KS-56). Gắn lại CHÍNH thân trang ấy nên không mất khối nào: vai xem được
          báo cáo vẫn có BÀN LÀM VIỆC PHÒNG và BẢNG CHỈ TIÊU phòng đội xe, vai không xem được
          vẫn ra thẳng mục lục. `khongChip` bỏ dãy chip phân hệ phòng khác.
          `Suspense` BẮT BUỘC: /xe là đường dẫn TĨNH, còn `TrangPhanHe` gọi `useSearchParams`. */}
      <section style={{ marginTop: 26, borderTop: "1px solid #e6eaf0", paddingTop: 18 }}>
        <Suspense fallback={<p className="muted">Đang tải…</p>}>
          <TrangPhanHe khoa="dhxe" khongChip />
        </Suspense>
      </section>
    </>}

    {/* NGĂN KÉO */}
    {k && <>
      <div onClick={() => setKeo(null)}
           style={{ position: "fixed", inset: 0, background: "rgba(14,42,82,.42)", zIndex: 40 }} />
      <aside role="dialog" aria-modal="true" aria-label={k.ten}
             style={{ position: "fixed", top: 0, right: 0, bottom: 0, width: "min(720px, 94vw)",
                      background: "#fff", zIndex: 41, overflowY: "auto", padding: 22,
                      boxShadow: "-12px 0 28px rgba(14,42,82,.22)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start",
                      gap: 12, marginBottom: 14 }}>
          <div>
            <h2 style={{ margin: 0 }}>{k.ten}</h2>
            <p className="muted" style={{ margin: 0 }}>Kỳ {kyDoc(ky)}</p>
          </div>
          <button type="button" aria-label="Đóng ngăn kéo" onClick={() => setKeo(null)}>✕</button>
        </div>
        {/* NGĂN KÉO GẮN LẠI CHÍNH KHỐI CỦA MÀN CÓ SẴN, không dựng form thứ hai.
            `ChiPhiKyPanel` là tab «Chi phí kỳ» của /lai-lo-doi-xe chuyển nguyên văn ra. Ghi hay
            gỡ xong nó gọi `onDoiSo` để bàn đọc lại số của mình.
            Ngăn kéo nào CHƯA có khối dùng chung thì vẫn đưa thẳng sang màn đang chạy. */}
        {hd?.viec.filter((v: any) => v.ngan_keo === keo).map((v: any) => (
          <p key={v.ma}><strong>{v.tieu_de}</strong><br /><span className="muted">{v.mo_ta}</span></p>
        ))}
        {keo === "chi-phi-ky"
          ? <ChiPhiKyPanel ky={ky} onDoiSo={() => doc(ky)} />
          : <p><Link href={k.toi}>{k.nhan} →</Link></p>}
        <p className="muted">Đóng ngăn kéo thì bàn tự đọc lại số.</p>
        <button type="button" onClick={() => { setKeo(null); doc(ky); }}>Xong — đọc lại số</button>
      </aside>
    </>}
  </>);
}

export default function Page() {
  return <Shell khongThanhBen><BanLamViecXe /></Shell>;
}
