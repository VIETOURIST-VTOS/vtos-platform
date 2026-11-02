"use client";
/* DK-4 · MÀN SÁU TRẠNG THÁI HỒ SƠ cho đối tác / cổ đông (Chủ tịch «làm luôn» 02/11/2026).

   Máy chủ đã có đủ sáu trạng thái (models/cong_ngoai.TRANG_THAI_NGOAI) từ CG-1, nhưng màn chỉ in một
   dòng chữ «Trạng thái tài khoản: …» — người gửi hồ sơ không biết mình đang ở bước mấy, ai đang cầm
   hồ sơ, và phải làm gì tiếp. Màn này trả lời đúng ba câu ấy.

   CHỈ ĐỌC `toi` máy chủ trả về — không tự suy trạng thái, không gọi cửa nào. Hai trạng thái «Từ chối» và
   «Đã khoá» không đăng nhập được (cong_ngoai.dang_nhap trả 403 kèm lý do ở màn đăng nhập), nên ở đây chúng
   chỉ hiện trong bảng chú giải để người đọc biết đường đi trọn vẹn. */

const TEN: Record<string, string> = {
  ho_so: "Chưa gửi hồ sơ", cho_duyet: "Chờ duyệt", bo_sung: "Cần bổ sung",
  hoat_dong: "Đang hoạt động", tu_choi: "Từ chối", khoa: "Đã khoá",
};

const Y_NGHIA: Record<string, string> = {
  ho_so: "Tài khoản đã tạo, chưa gửi hồ sơ — điền và gửi hồ sơ bên dưới.",
  cho_duyet: "Hồ sơ đã tới Vietourist, đang đối chiếu. Không cần làm gì thêm.",
  bo_sung: "Vietourist trả hồ sơ kèm lý do — sửa theo lý do rồi gửi lại.",
  hoat_dong: "Đã duyệt — không gian riêng của bạn đã mở.",
  tu_choi: "Hồ sơ không được chấp nhận — lý do gửi kèm, liên hệ Vietourist nếu cần.",
  khoa: "Tài khoản tạm khoá — lý do gửi kèm, liên hệ Vietourist để mở lại.",
};

/* Ai cầm hồ sơ — khớp NGUOI_DUYET ở services/cong_ngoai.py. Đổi một bên thì đổi cả hai. */
function nguoiDuyet(toi: any): string {
  if (toi.loai === "co_dong") return "IR – Pháp chế";
  if (toi.loai_doi_tac === "dai_ly" || toi.loai_doi_tac === "ctv_ban_hang") return "Giám đốc Kinh doanh";
  return "Phòng Điều hành / Giám đốc Kinh doanh";        // nhà cung cấp, hoặc chưa chọn loại đối tác
}

function gio(s?: string) {
  return s ? String(s).slice(0, 16).replace("T", " ") : "";
}

const CSS = `
#vtd-access .tths{border:1px solid #dfe6ef;border-radius:14px;padding:14px 16px;margin:10px 0 14px;background:#fbfdff;color:#142a43}
#vtd-access .tths-dau{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center}
#vtd-access .tths-y{font-size:14px;color:#3b5068}
#vtd-access .tths-nhan{display:inline-block;font-size:12px;font-weight:700;border-radius:999px;padding:3px 10px;white-space:nowrap}
#vtd-access .tths-ho_so{background:#eef3f8;color:#3b5068}
#vtd-access .tths-cho_duyet{background:#fbf1dc;color:#8a5a00}
#vtd-access .tths-bo_sung{background:#fde8d7;color:#a24a00}
#vtd-access .tths-hoat_dong{background:#e3f3ea;color:#1d7a4a}
#vtd-access .tths-tu_choi,#vtd-access .tths-khoa{background:#fbe3ec;color:#a8145c}
#vtd-access .tths-duong{list-style:none;margin:14px 0 6px;padding:0;display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
#vtd-access .tths-duong li{position:relative;display:flex;flex-direction:column;gap:2px;padding-top:34px;font-size:13px;color:#52677f}
#vtd-access .tths-duong li:before{content:"";position:absolute;top:13px;left:28px;right:-8px;height:2px;background:#dfe6ef}
#vtd-access .tths-duong li:last-child:before{display:none}
#vtd-access .tths-duong li.xong:before{background:#1d7a4a}
#vtd-access .tths-so{position:absolute;top:0;left:0;width:28px;height:28px;border-radius:50%;display:grid;place-items:center;font-weight:700;font-size:13px;background:#eef3f8;color:#52677f;border:2px solid #dfe6ef}
#vtd-access .tths-duong li.xong .tths-so{background:#1d7a4a;border-color:#1d7a4a;color:#fff}
#vtd-access .tths-duong li.hien .tths-so{background:#fff;border-color:#c98a00;color:#8a5a00}
#vtd-access .tths-duong li.loi .tths-so{background:#a8145c;border-color:#a8145c;color:#fff}
#vtd-access .tths-duong li.hien .tths-ten,#vtd-access .tths-duong li.loi .tths-ten{font-weight:700;color:#142a43}
#vtd-access .tths-phu{font-size:12px;color:#7a8ca1}
#vtd-access .tths-chu-giai{margin-top:8px;font-size:13px}
#vtd-access .tths-chu-giai summary{cursor:pointer;color:#1f5f9e;font-weight:600}
#vtd-access .tths-chu-giai ul{list-style:none;padding:0;margin:8px 0 0;display:grid;gap:6px}
#vtd-access .tths-chu-giai li{color:#3b5068}
#vtd-access .tths-chu-giai li.dang{font-weight:700;color:#142a43}
@media (max-width:560px){#vtd-access .tths-duong{grid-template-columns:1fr 1fr;row-gap:14px}#vtd-access .tths-duong li:nth-child(2):before{display:none}}
`;

export default function TrangThaiHoSo({ toi }: { toi: any }) {
  const tt: string = toi.trang_thai;
  const doiTac = toi.loai === "doi_tac";
  // Bốn bước trên đường đi; bước hiện tại tính từ trạng thái máy chủ trả về.
  const buoc = [
    { ten: "Tạo tài khoản", phu: "Đã xác minh liên hệ" },
    { ten: doiTac ? "Gửi hồ sơ đối tác" : "Gửi hồ sơ xác minh", phu: tt === "bo_sung" ? "Cần bổ sung" : "" },
    { ten: doiTac ? "Vietourist duyệt" : "IR xác minh sổ cổ đông", phu: nguoiDuyet(toi) },
    { ten: doiTac ? "Mở không gian đối tác" : "Mở không gian cổ đông", phu: "" },
  ];
  const dang = tt === "ho_so" || tt === "bo_sung" ? 1 : tt === "cho_duyet" || tt === "tu_choi" ? 2 : tt === "hoat_dong" ? 4 : 1;
  const hong = tt === "tu_choi" || tt === "khoa";

  return (
    <div className="tths" data-trang-thai={tt}>
      <style>{CSS}</style>
      <div className="tths-dau">
        <span className={`tths-nhan tths-${tt}`}>{TEN[tt] || tt}</span>
        <span className="tths-y">{Y_NGHIA[tt] || ""}</span>
      </div>

      <ol className="tths-duong">
        {buoc.map((b, i) => {
          const xong = i < dang;
          const hien = i === dang && !hong;
          const loi = i === dang && hong;
          return (
            <li key={b.ten} className={xong ? "xong" : hien ? "hien" : loi ? "loi" : "cho"}>
              <span className="tths-so">{xong ? "✓" : loi ? "!" : i + 1}</span>
              <span className="tths-ten">{b.ten}</span>
              {b.phu && <span className="tths-phu">{b.phu}</span>}
            </li>
          );
        })}
      </ol>

      {tt === "cho_duyet" && (
        <div className="cong-ok">
          Hồ sơ gửi lúc {gio(toi.gui_ho_so_luc)} · người duyệt: <b>{nguoiDuyet(toi)}</b>. Kết quả hiện ngay tại đây
          khi bạn đăng nhập lại.
        </div>
      )}
      {tt === "bo_sung" && (
        <div className="cong-loi">
          <b>Vietourist cần bổ sung:</b> {toi.ly_do || "chưa ghi lý do — liên hệ Vietourist"}. Sửa hồ sơ bên dưới rồi bấm
          «Gửi hồ sơ».
        </div>
      )}
      {hong && toi.ly_do && <div className="cong-loi"><b>Lý do:</b> {toi.ly_do}</div>}

      <details className="tths-chu-giai">
        <summary>Sáu trạng thái của hồ sơ</summary>
        <ul>
          {Object.keys(TEN).map((k) => (
            <li key={k} className={k === tt ? "dang" : ""}>
              <span className={`tths-nhan tths-${k}`}>{TEN[k]}</span> {Y_NGHIA[k]}
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
