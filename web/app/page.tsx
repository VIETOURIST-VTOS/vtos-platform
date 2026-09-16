"use client";
import { useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, pct } from "@/lib/api";
import { errMsg } from "@/components/ui";
import KhoiDongTien from "@/components/KhoiDongTien";
import { KhoiHieuQuaXe, KhoiPhaiThu, KhoiPhaiTra } from "@/components/KhoiV14";
import {
  KhoiKinhDoanhLe, KhoiKinhDoanhDoan, KhoiBaoCaoNgay,
} from "@/components/KhoiKinhDoanh";
import {
  DongLoc, KhoiQuyetDinh, HangThe, TieuDe, dem, type The,
} from "@/components/DauManHinh01";
import {
  KhoiDoanhThu, KhoiLoiNhuan, KhoiTonDongMuc,
} from "@/components/KhoiSauO";
import { bieuDoCua } from "@/components/BaKhuBieuDo";

function Dash() {
  const { user } = useShell();
  const [d, setD] = useState<any>(null);
  // Trước đây lỗi bị nuốt bằng .catch(() => {}) nên máy chủ trả 500 mà người dùng chỉ thấy
  // "Đang tải…" đứng im vĩnh viễn – lỗi PostgreSQL ngày 07/9 sống sót nhiều ngày vì đúng chỗ này.
  const [loi, setLoi] = useState<string>("");
  const tai = () => { setLoi(""); api("/dashboard").then(setD).catch((e) => setLoi(errMsg(e) || "Không tải được bảng điều khiển")); };
  useEffect(tai, []);
  if (loi) return <div className="panel" style={{ borderColor: "var(--red)" }}>
    <b style={{ color: "var(--red)" }}>Không tải được bảng điều khiển.</b>
    <div className="muted" style={{ margin: "6px 0" }}>{loi}</div>
    <div className="muted">Các màn hình khác vẫn dùng được. Nếu lặp lại, báo CNTT kèm nguyên văn dòng trên.</div>
    <button className="act" onClick={tai}>Thử lại</button>
  </div>;
  if (!d) return <p className="muted">Đang tải…</p>;
  const c = d.counts || {};
  const k = d.kpis || {}; const sec = d.sections || {};
  /* Cửa sổ ngày khởi hành do MÁY CHỦ khai (services/dashboard.py · SO_NGAY_SAP_KHOI_HANH). Màn
     hình chỉ đọc — gõ lại con số ở đây là mở đường cho hai nơi nói khác nhau, đúng lỗi vừa sửa ở
     đầu cột bảng dòng tiền. Lối lui 14 chỉ dùng khi máy chủ cũ chưa trả trường này. */
  const soNgayKH = sec.sap_khoi_hanh_so_ngay ?? 14;

  /* KỲ BÁO CÁO — SỬA 16/9/2026 (TC-42), và sửa ngược lại quyết định 13/9.
     Bản 13/9 chốt "màn hình 01 chỉ theo THÁNG, quý và năm xem ở báo cáo chi tiết", vì lúc ấy máy
     chủ mới tính theo tháng và một ô chọn ba kỳ sẽ là lời hứa suông. Nay máy chủ cộng được quý và
     năm từ chính các tháng (`services/xu_huong.doc_theo_ky`), nên ô chọn ấy có số thật đằng sau —
     và anh Tuấn chốt 16/9 là "doanh thu và lợi nhuận phân ra theo tháng, quý, năm".
     Chỉ HAI ô lớn ấy có ba kỳ: tồn kho cộng không được, và bốn ô chọn kỳ trên cùng một màn hình
     thì không ô nào còn đáng bấm. */
  const kh = k.ke_hoach_thang;

  /* NĂM THẺ SỐ NHỎ — anh Tuấn chốt 16/9/2026: "các phần tour đang bán, tour chờ quyết toán, tour
     sắp khởi hành, đội xe hôm nay, marketing đưa xuống vị trí dưới".

     KHÔNG có biểu đồ trên năm thẻ này, và đó là lựa chọn chứ không phải thiếu sót. Đây là những
     con số chỉ để LIẾC: 349 tour đang bán, 93 tour sắp khởi hành — đọc xong là xong, không phải
     đặt cạnh kỳ trước hay cạnh kế hoạch mới hiểu. Thêm hình vào chúng là kéo mắt khỏi sáu ô lớn
     phía trên, nơi có những con số thật sự cần nghĩ. */
  const the: The[] = [
    { nhan: "Tour đang bán", so: dem(c.da_duyet ?? 0),
      duoi: `${d.n_tours ?? 0} tour trên hệ thống · chưa có sức chứa từng chuyến nên chưa tính được chỗ còn (Điều hành)` },
    { nhan: "Tour chờ quyết toán", so: dem((c.ket_thuc || 0) + (c.da_dong_so || 0)),
      duoi: `${sec.qua_han_qt?.length ?? 0} chuyến quá hạn quyết toán`,
      do: (sec.qua_han_qt?.length ?? 0) > 0 },
    { nhan: "Tour sắp khởi hành", so: dem(sec.sap_khoi_hanh?.length),
      duoi: `${soNgayKH} ngày tới`, ai: "Điều hành", cua: "/tours" },
    { nhan: "Đội xe hôm nay", so: null, ai: "Đội xe", cua: "/doi-xe",
      duoi: "Đang chạy / đủ điều kiện · xe trống · bảo dưỡng" },
    { nhan: "Marketing & PR", phu: "Khách tiềm năng mới", so: null,
      ai: "Marketing", cua: "/leads?tab=leads",
      duoi: "Đã chuyển Kinh doanh · đã chốt" },
  ];

  /* Biểu đồ dựng một lần, giao cho từng khối tự bày. Khối nào chưa đủ số thì nhận `null` và chỉ
     hiện ô số của nó — ô số vốn đã ghi "Chưa kết nối" kèm bộ phận và cửa nhập. */
  const bd = bieuDoCua(sec);

  return (<>
    <TieuDe vai={user?.role} ten_vai={user?.role_name} />
    <DongLoc />

    {/* ══ TC-42 · SÁU Ô LỚN, RỒI MỚI ĐẾN NHỮNG CON SỐ ĐỂ LIẾC (anh Tuấn chốt 16/9/2026) ═══════
        "8 ô này anh muốn thay đổi vị trí — doanh thu, lợi nhuận trước thuế, dòng tiền, phải thu,
         phải trả, tồn đọng cần xử lý: 6 ô này làm biểu đồ lớn lên, chia ra các chart khác nhau
         theo cấu trúc; phần doanh thu và lợi nhuận phân ra theo tháng, quý, năm. Giảm từ 8 ô
         xuống còn 6 ô. Các phần tour đang bán, tour chờ quyết toán, tour sắp khởi hành, đội xe
         hôm nay, marketing đưa xuống vị trí dưới."

        RANH GIỚI GIỮA HAI NHÓM KHÔNG PHẢI LÀ ĐỘ QUAN TRỌNG, MÀ LÀ CÁCH ĐỌC:
          · Sáu ô trên là con số phải NGHĨ mới hiểu — chỉ có nghĩa khi đặt cạnh kỳ trước, cạnh kế
            hoạch, hoặc chia theo cơ cấu. "Doanh thu 4,3 tỷ" một mình thì không ai nói được là tốt
            hay xấu.
          · Năm thẻ dưới là con số chỉ để LIẾC. Đọc xong là xong.

        BA KHỐI CHUYỂN LÊN, KHÔNG NHÂN BẢN. Dòng tiền · Phải thu · Phải trả trước đây nằm rời phía
        dưới; nay chúng LÀ ba trong sáu ô. Giữ cả hai chỗ là để một con số nằm hai nơi — đúng cái
        anh Tuấn bảo bỏ ở vòng TC-40 ("các mục lặp lại thì bỏ hết"). */}

    <KhoiQuyetDinh ds={d.approvals || []} vai={user?.role} />

    <div className="mh01-sau-o">
      <KhoiDoanhThu ba_ky={sec.ba_ky} ke_hoach={kh} so_chuyen={k.so_chuyen_thang} />
      <KhoiLoiNhuan ba_ky={sec.ba_ky} ke_hoach={kh} />
      <KhoiDongTien />
      <KhoiPhaiThu ds={sec.phai_thu_theo_han} chua_co_han={sec.phai_thu_chua_co_han}
        vi_sao={sec.phai_thu_vi_sao} bieu_do={bd.phai_thu} />
      <KhoiPhaiTra ds={sec.phai_tra_theo_han} qua_han={sec.phai_tra_qua_han}
        chua_co_han={sec.phai_tra_chua_co_han} vi_sao={sec.phai_tra_vi_sao} bieu_do={bd.phai_tra} />
      <KhoiTonDongMuc d={sec.ton_dong_theo_muc} />
    </div>

    <HangThe ds={the} />

    <KhoiHieuQuaXe d={sec.hieu_qua_xe} theo_ky={sec.hieu_qua_xe_theo_ky} />

    {/* Ba khối kinh doanh & nội bộ xếp một hàng: cả ba đều ngắn sau khi bỏ bảng, và đọc cạnh nhau
        thì thấy được bức tranh "bán hàng · lợi nhuận · kỷ luật nội bộ" trong một cái nhìn. */}
    <div className="mh01-hang-3">
      <KhoiKinhDoanhLe ds={sec.kd_le} bieu_do={bd.kd_le} />
      <KhoiKinhDoanhDoan d={sec.kd_doan} bieu_do={bd.kd_doan} />
      <KhoiBaoCaoNgay d={sec.bao_cao_ngay} bieu_do={bd.bao_cao_ngay} />
    </div>

    <p className="muted">Ngưỡng biên đang áp dụng {pct(d.threshold)} · Robot chạy mỗi 10 phút; CNTT có thể chạy tay ở trang Cảnh báo.</p>
  </>);
}
export default function Page() { return <Shell><Dash /></Shell>; }
