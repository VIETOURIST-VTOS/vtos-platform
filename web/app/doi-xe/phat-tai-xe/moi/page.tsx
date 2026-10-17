"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, getUser } from "@/lib/api";
import { errMsg } from "@/components/ui";
import ThanhViec, { baoDaDoi, docUrl } from "@/components/ThanhViec";

/** GHI PHẠT TÀI XẾ — màn TOÀN MÀN, không còn thanh dọc bên trái (luật 2 anh Tuấn chốt 16/10/2026).
 *
 *  BA ĐIỀU KHÔNG ĐƯỢC LÀM HỎNG, cả ba đã ghi trong mô hình `PhatTaiXe` từ đợt DX-3:
 *
 *  1. KỲ LƯƠNG KHAI RIÊNG, MÁY KHÔNG SUY TỪ NGÀY. Một lỗi ngày 29 có thể được chốt vào kỳ sau nếu
 *     bảng lương kỳ này đã khoá, và suy hộ là trừ nhầm tháng của một con người. Vì thế ô kỳ ở đây
 *     KHÔNG tự chạy theo ô ngày — gõ ngày 29/10 mà kỳ vẫn là 2026-11 là chuyện hợp lệ.
 *  2. CHUYẾN VÀ XE ĐỂ TRỐNG ĐƯỢC. Không phải lỗi nào cũng gắn vào một chuyến — đi muộn, không mặc
 *     đồng phục. Màn không được bắt, và không được âm thầm điền một giá trị mặc định.
 *  3. KHOẢN PHẠT VÀO LƯƠNG, KHÔNG VÀO GIÁ VỐN XE. Ô "Xe" ở đây chỉ để TRUY xem lỗi xảy ra trên xe
 *     nào; nó không đẩy một đồng nào vào chi phí của chiếc xe ấy.
 *
 *  LÝ DO LÀ CHỮ NGƯỜI TA SẼ ĐỌC LẠI. Tài xế thắc mắc thì câu này là câu trả lời, nên nó bắt buộc
 *  và giới hạn 300 ký tự theo đúng cột `ly_do` String(300) — đếm ngay trên màn chứ không để máy chủ
 *  trả về lỗi sau khi người ta đã gõ xong.
 *
 *  AI GHI ĐƯỢC: `GHI_PHAT = ("cntt", "gd_doi_xe")` khai ở `api/v1/fleet.py`. Vai khác mở màn này
 *  thì thấy nói thẳng là không ghi được, chứ không thấy một biểu mẫu gõ xong rồi ăn 403.
 */

const GHI_PHAT = ["cntt", "gd_doi_xe"];
const TOI_DA_LY_DO = 300;

const DUONG = <><a href="/">VTOS</a> · <a href="/phan-he/dhxe">Đội xe</a> · <a href="/doi-xe/phat-tai-xe">Phạt tài xế</a> · Ghi phạt</>;

const homNay = () => new Date().toISOString().slice(0, 10);
const kyNay = () => {
  const d = new Date();
  return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0");
};

function GhiPhat() {
  const { toast } = useShell();
  const vai = getUser()?.role || "";
  const duocGhi = GHI_PHAT.includes(vai);

  const [tx, setTx] = useState<any[]>([]);
  const [driverId, setDriverId] = useState("");
  const [ky, setKy] = useState(() => docUrl().get("ky") || kyNay());
  const [ngay, setNgay] = useState(homNay);
  const [soTien, setSoTien] = useState("");
  const [lyDo, setLyDo] = useState("");
  const [tripId, setTripId] = useState("");
  const [vehicleId, setVehicleId] = useState("");
  const [xe, setXe] = useState<any[]>([]);
  const [dangLuu, setDangLuu] = useState(false);

  /* Danh sách tài xế lấy từ cửa `/fleet/tai-xe-chon` — CÙNG NHÓM API với màn cha "/doi-xe".
     Không gọi `/api/v1/tai-xe` dù nó có sẵn: nhóm ấy không nằm trong MAN_HINH_API của "/doi-xe",
     nên gọi nó là vỡ hàng rào quyền của chính màn này. */
  const nap = useCallback(async () => {
    try {
      const [a, b] = await Promise.all([api<any>("/fleet/tai-xe-chon"), api<any>("/fleet/xe")]);
      setTx(a?.rows || []);
      setXe(b?.rows || b || []);
    } catch (e) { toast(errMsg(e), true); }
  }, [toast]);
  useEffect(() => { nap(); }, [nap]);

  const soDa = Number(String(soTien).replace(/[^\d]/g, "")) || 0;
  const thieu = !driverId || !ky || !ngay || soDa <= 0 || !lyDo.trim();

  const luu = async () => {
    if (thieu || dangLuu) return;
    setDangLuu(true);
    try {
      await api("/fleet/phat-tai-xe", {
        method: "POST",
        json: {
          driver_id: Number(driverId),
          ky,
          ngay,
          so_tien: soDa,
          ly_do: lyDo.trim(),
          trip_id: tripId ? Number(tripId) : null,
          vehicle_id: vehicleId ? Number(vehicleId) : null,
        },
      });
      /* Tab sổ phạt đang mở ở đâu đó không biết tab này vừa ghi gì — luật 5. */
      baoDaDoi("vừa ghi một phiếu phạt");
      toast("Đã ghi phiếu phạt vào kỳ " + ky);
      window.location.href = "/doi-xe/phat-tai-xe?ky=" + encodeURIComponent(ky);
    } catch (e) { toast(errMsg(e), true); setDangLuu(false); }
  };

  const viec = [
    {
      nhan: dangLuu ? "Đang lưu…" : "Lưu phiếu phạt",
      href: "#",
      chinh: true,
      len: true,
      tat: !duocGhi
        ? "Chỉ Giám đốc đội xe ghi phiếu phạt."
        : thieu ? "Còn thiếu tài xế, kỳ lương, ngày, số tiền hoặc lý do." : "",
    },
    { nhan: "‹ Lên một cấp", href: "/doi-xe/phat-tai-xe?ky=" + encodeURIComponent(ky), len: true },
  ];

  return (<>
    <ThanhViec toanMan duong={DUONG} viec={viec} />
    <h1>Ghi phạt tài xế</h1>

    {!duocGhi && <p className="panel">
      Vai <b>{getUser()?.role_name || vai}</b> không ghi được phiếu phạt. Cửa <span className="mono">POST
      /fleet/phat-tai-xe</span> chỉ mở cho Giám đốc đội xe. Anh/chị vẫn xem được{" "}
      <a href="/doi-xe/phat-tai-xe">sổ phạt</a>.
    </p>}

    {duocGhi && <>
      <form onSubmit={(e) => { e.preventDefault(); luu(); }}>
        <div className="panel">
          <div className="grid2">
            <div>
              <label htmlFor="p-tx">Tài xế *</label>
              <select id="p-tx" value={driverId} onChange={(e) => setDriverId(e.target.value)}>
                <option value="">— chọn tài xế —</option>
                {tx.map((t) => <option key={t.id} value={t.id}>{t.ho_ten}{t.code ? " · " + t.code : ""}</option>)}
              </select>
              <p className="muted">Lấy từ hồ sơ nhân sự, không gõ tay. Người không thuộc bộ phận đội xe
                thì máy chủ từ chối.</p>
            </div>

            <div>
              <label htmlFor="p-ky">Kỳ lương sẽ trừ *</label>
              <input id="p-ky" type="month" value={ky} onChange={(e) => setKy(e.target.value)} />
              <p className="muted">Dạng YYYY-MM, và <b>không chạy theo ô Ngày</b>: lỗi cuối tháng có thể
                phải chốt vào kỳ sau nếu kỳ này đã khoá.</p>
            </div>

            <div>
              <label htmlFor="p-ngay">Ngày xảy ra *</label>
              <input id="p-ngay" type="date" value={ngay} onChange={(e) => setNgay(e.target.value)} />
            </div>

            <div>
              <label htmlFor="p-tien">Số tiền (đ) *</label>
              <input id="p-tien" type="text" inputMode="numeric" value={soTien}
                onChange={(e) => setSoTien(e.target.value)} placeholder="300000" />
              {soDa > 0 && <p className="muted">{soDa.toLocaleString("vi-VN")} đ</p>}
            </div>
          </div>

          <label htmlFor="p-ly">Lý do * <span className="muted">({lyDo.length}/{TOI_DA_LY_DO})</span></label>
          <textarea id="p-ly" value={lyDo} maxLength={TOI_DA_LY_DO} rows={3}
            onChange={(e) => setLyDo(e.target.value)}
            placeholder="Đi muộn điểm hẹn 25 phút, đoàn phải dời giờ khởi hành." />
          <p className="muted">Câu này là câu tài xế sẽ đọc lại khi thắc mắc. Viết một câu đủ hiểu.</p>
        </div>

        <div className="panel">
          <h3>Gắn chuyến hoặc xe — để trống được</h3>
          <p className="muted">Không phải lỗi nào cũng gắn vào một chuyến: đi muộn, không mặc đồng phục.
            Hai ô này để trống thì khoản phạt vẫn hợp lệ. Ô Xe chỉ để TRUY lỗi xảy ra trên xe nào —
            nó không cộng một đồng nào vào chi phí của chiếc xe ấy.</p>
          <div className="grid2">
            <div>
              <label htmlFor="p-ch">Chuyến</label>
              <input id="p-ch" type="number" min={1} value={tripId}
                onChange={(e) => setTripId(e.target.value)} placeholder="mã chuyến, để trống nếu không gắn" />
            </div>
            <div>
              <label htmlFor="p-xe">Xe</label>
              <select id="p-xe" value={vehicleId} onChange={(e) => setVehicleId(e.target.value)}>
                <option value="">— không gắn xe —</option>
                {xe.map((v: any) => (
                  <option key={v.id} value={v.id}>{v.plate || v.code}{v.seats ? " · " + v.seats + " chỗ" : ""}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <button className="act" type="submit" disabled={thieu || dangLuu}>
          {dangLuu ? "Đang lưu…" : "Lưu phiếu phạt"}
        </button>
      </form>
    </>}
  </>);
}

export default function Page() { return <Shell><GhiPhat /></Shell>; }
