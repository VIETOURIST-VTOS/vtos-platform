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
import { KhoiTonDongMuc } from "@/components/KhoiSauO";
import KhoiKetQuaKinhDoanh from "@/components/KhoiKetQuaKinhDoanh";
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
  const sec = d.sections || {};   // `d.kpis` không còn ai đọc từ TC-44 — xem ghi chú bên dưới.
  /* Cửa sổ ngày khởi hành do MÁY CHỦ khai (services/dashboard.py · SO_NGAY_SAP_KHOI_HANH). Màn
     hình chỉ đọc — gõ lại con số ở đây là mở đường cho hai nơi nói khác nhau, đúng lỗi vừa sửa ở
     đầu cột bảng dòng tiền. Lối lui 14 chỉ dùng khi máy chủ cũ chưa trả trường này. */
  const soNgayKH = sec.sap_khoi_hanh_so_ngay ?? 14;

  /* KỲ BÁO CÁO — SỬA 16/9/2026 (TC-42), rồi sửa lần nữa cùng ngày (TC-44).
     Bản 13/9 chốt "màn hình 01 chỉ theo THÁNG". TC-42 mở ra ba kỳ vì máy chủ đã cộng được quý và
     năm. TC-44 đưa hẳn hai ô ấy sang khối Kết quả kinh doanh, nơi chúng dùng CHUNG một bộ chọn kỳ
     và tự gọi `/bao-cao/ket-qua-kinh-doanh` — nên ở đây không còn phải chuyền `ke_hoach_thang`
     xuống nữa; kế hoạch đi thẳng từ máy chủ vào khối ấy.

     MỘT CÂU MẤT ĐI, VÀ ĐÓ LÀ CHỦ Ý: dòng "N chuyến đã quyết toán trong tháng" (`k.so_chuyen_thang`)
     không theo sang khối mới được, vì con số ấy là của THÁNG HIỆN TẠI còn khối mới xem được bất kỳ
     tháng nào của bất kỳ năm nào. Đặt nó dưới biểu đồ tháng 3/2026 là dán một con số của tháng 9
     vào chỗ nó không thuộc về. Muốn có lại thì máy chủ phải đếm chuyến THEO KỲ — ghi ra đây để
     việc còn thiếu nằm trong mã, không nằm trong trí nhớ. */

  /* SÁU THẺ SỐ NHỎ — anh Tuấn chốt 16/9/2026 theo bản vẽ v3.0 (trước đó là năm).

     KHÔNG có biểu đồ trên sáu thẻ này, và đó là lựa chọn chứ không phải thiếu sót. Đây là những
     con số chỉ để LIẾC — đọc xong là xong, không phải đặt cạnh kỳ trước hay cạnh kế hoạch mới
     hiểu. Thêm hình vào chúng là kéo mắt khỏi những con số thật sự cần nghĩ ở phía trên.

     "ĐANG BÁN" VÀ "ĐANG CHẠY" LÀ HAI CÂU HỎI KHÁC NHAU, và tách chúng ra làm lộ một điều: hệ
     thống KHÔNG có trạng thái "đang chạy" — một chuyến giữ trạng thái `da_duyet` suốt từ lúc mở
     bán qua cả hành trình. Nên phép chia là theo NGÀY, làm ở máy chủ
     (`services/dem_tour.theo_giai_doan`), và hệ quả phải nói trước: con số "Tour đang bán" NHỎ ĐI
     so với bản hôm qua, vì những đoàn đang trên đường đã tách sang thẻ bên cạnh.

     NHÓM THỨ BA — chuyến đã qua ngày về mà trạng thái vẫn là "đã duyệt" — không có thẻ riêng,
     nhưng CÓ CHỖ HIỆN: nó là dòng phụ của thẻ Chờ quyết toán, vì đó chính là việc còn thiếu (Điều
     hành chưa bấm kết thúc thì tiền của chuyến ấy chưa vào hàng đợi quyết toán). Bỏ nó đi thì hai
     con số đầu cộng lại không bằng tổng đã duyệt, và chỗ chênh biến mất lặng lẽ. */
  const gd = sec.tour_giai_doan || {};
  const xe = sec.xe_hom_nay || {};
  const chuaDongSo = gd.da_ve_chua_dong_so;

  const the: The[] = [
    { nhan: "Tour đang bán", so: dem(gd.dang_ban),
      duoi: "Đã duyệt, chưa tới ngày khởi hành · chưa có sức chứa từng chuyến nên chưa tính được chỗ còn (Điều hành)",
      ai: "Điều hành", cua: "/tours" },
    { nhan: "Tour đang chạy", so: dem(gd.dang_chay),
      duoi: "Đang trong hành trình hôm nay · chưa có sổ sự cố chuyến nên chưa đếm được chuyến cần xử lý (Điều hành)",
      ai: "Điều hành", cua: "/tours" },
    { nhan: "Tour sắp khởi hành", so: dem(sec.sap_khoi_hanh?.length),
      duoi: `${soNgayKH} ngày tới`, ai: "Điều hành", cua: "/tours" },
    { nhan: "Tour chờ quyết toán", so: dem((c.ket_thuc || 0) + (c.da_dong_so || 0)),
      duoi: `${sec.qua_han_qt?.length ?? 0} chuyến quá hạn quyết toán`
        + (typeof chuaDongSo === "number" && chuaDongSo > 0
           ? ` · ${chuaDongSo} chuyến đã qua ngày về mà chưa đóng sổ (Điều hành)` : ""),
      do: (sec.qua_han_qt?.length ?? 0) > 0 || (chuaDongSo ?? 0) > 0 },
    /* XE ĐANG ĐI — cùng luật với tour: lịch hôm nay trùng lịch điều xe. `co_nguon` phân biệt
       "hôm nay không điều xe nào" (số THẬT, bằng 0) với "chưa ai nhập bảng xe" (chưa có nguồn);
       không có nó thì hai việc khác hẳn nhau hiện ra y hệt một con số 0. */
    { nhan: "Xe đang đi", so: xe.co_nguon ? dem(xe.dang_chay) : null,
      ai: "Đội xe", cua: "/doi-xe",
      duoi: xe.co_nguon
        ? `${xe.o_bai} xe nằm bãi trên ${xe.dieu_duoc} xe điều được`
          + (xe.bat_thuong > 0 ? ` · ${xe.bat_thuong} xe có bất thường` : "")
          + (xe.lech > 0 ? ` · ${xe.lech} lệnh điều xe trỏ tới xe không còn điều được (Đội xe)` : "")
        : "Xe đang chạy hôm nay · xe nằm bãi · xe có bất thường",
      do: (xe.bat_thuong ?? 0) > 0 || (xe.lech ?? 0) > 0 },
    { nhan: "Khách tiềm năng mới", so: null,
      ai: "Marketing", cua: "/leads?tab=leads",
      duoi: "Chưa bàn giao Kinh doanh · quá hạn bàn giao" },
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

    {/* TC-44 · Doanh thu và Lợi nhuận trước thuế GỘP thành MỘT khối rộng hết bề ngang, theo bản
        vẽ anh Tuấn gửi 16/9/2026. Hai ô ấy rời khỏi lưới sáu ô vì hai lẽ: chúng dùng CHUNG một bộ
        chọn kỳ (để không bao giờ xảy ra cảnh doanh thu đang xem quý còn lợi nhuận đang xem tháng),
        và mười hai cột mỗi hình cần bề ngang gấp đôi một ô lưới.

        Sáu con số của anh Tuấn KHÔNG mất đi: hai con số đầu nằm trong khối này, bốn con số còn lại
        ở lưới ngay dưới. Đổi CÁCH BÀY, không đổi danh sách. */}
    <KhoiKetQuaKinhDoanh />

    <div className="mh01-sau-o">
      {/* TC-48 · đáy của dự báo 13 tuần. Máy chủ tính (`kpis.so_du_thap_nhat`), màn hình chỉ bày —
          ranh giới 09/9. Vai nào không được xem khối dòng tiền thì `kpis` không mang trường này về,
          nên không có nhánh ẩn/hiện nào ở đây: cắt hàng nằm trong truy vấn, đúng luật SEC-02. */}
      <KhoiDongTien day={d.kpis?.so_du_thap_nhat} />
      <KhoiPhaiThu ds={sec.phai_thu_theo_han} chua_co_han={sec.phai_thu_chua_co_han}
        vi_sao={sec.phai_thu_vi_sao} bieu_do={bd.phai_thu} />
      {/* TC-45: bỏ `qua_han` — quá hạn nay là nhóm đầu trong bảy nhóm, không còn ô riêng. */}
      <KhoiPhaiTra ds={sec.phai_tra_theo_han}
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
