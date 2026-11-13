"use client";
/** ĐÓNG SỐ BÙ CHO KHO QUYẾT TOÁN CŨ — bảng điều khiển chạy THEO LÔ.
 *
 * VÌ SAO CÓ Ô NÀY
 *
 * Cửa đóng số bù đã có từ 17/9/2026 nhưng CHƯA CÓ MÀN HÌNH: muốn bấm thì phải mở bảng điều khiển
 * trình duyệt và gõ lệnh gọi API. Một cửa ghi vào 476 chuyến mà chỉ bấm được bằng cách gõ lệnh là
 * một cửa chỉ mình người viết nó dùng được — Chủ tịch ký thay các phòng ban thì Chủ tịch phải bấm
 * được, và phải NHÌN THẤY mình đang ký cái gì trước khi bấm.
 *
 * VÌ SAO CHẠY THEO LÔ, VÀ VÌ SAO VÒNG LẶP NẰM Ở ĐÂY CHỨ KHÔNG PHẢI Ở MÁY CHỦ
 *
 * Đo 19/9/2026 trên hệ thật: gọi một lần cho cả 476 chuyến thì cổng cắt giữa chừng và trả về một
 * trang HTML — trình duyệt chỉ thấy "Unexpected token '<'". Giao dịch bị huỷ trọn nên dữ liệu
 * không hỏng, nhưng nút thì không bao giờ bấm xong.
 *
 * Nay mỗi lần gọi là MỘT GIAO DỊCH nhỏ: xử một lô, ghi nhật ký, chốt, trả về `con_lai` và con trỏ
 * `bo_qua_tiep`. Màn hình gọi tiếp cho tới khi `con_lai` = 0. Để vòng lặp ở đây có ba cái được mà
 * để ở máy chủ không có: người bấm THẤY tiến độ, DỪNG được giữa chừng, và mỗi lô đã xong là đã
 * chốt — mất mạng hay đóng máy thì phần đã làm vẫn sạch, mở lại bấm tiếp chứ không làm lại từ đầu.
 *
 * CON TRỎ `bo_qua` LÀ CHỖ DỄ LÀM SAI NHẤT
 *
 * Chuyến KHÔNG đóng được (thiếu dòng chi, doanh thu 0) vẫn khớp điều kiện lấy lô và luôn đứng đầu
 * hàng. Không truyền con trỏ lại thì lô sau lấy đúng chúng, đóng được 0 chuyến, `con_lai` không
 * giảm — màn hình quay vòng mãi mãi. Cửa gỡ y hệt, với những chuyến Điều hành đã đóng THẬT mà cửa
 * này phải giữ nguyên (đo 17/9/2026: 82 chuyến, nhiều hơn một lô). Nên con trỏ phải được truyền
 * lại Y NGUYÊN, và `TRAN_LO` ở dưới là cái phanh cuối cùng nếu máy chủ trả về con trỏ sai.
 */
import { useState } from "react";
import { api, getUser } from "@/lib/api";
import { errMsg } from "@/components/ui";
import { useHoi } from "@/components/HopHoi";

const DUOC_XEM = ["chutich", "tgd", "cntt", "tp_dh"];

// Phanh. Ở 50 chuyến một lô thì 476 chuyến hết mươi lô; 100 lô là đã sai ở đâu đó, và thà dừng
// lại báo cho người bấm còn hơn gọi máy chủ mãi không thôi.
const TRAN_LO = 100;

type Ky = { ky: string; so_chuyen: number; doanh_thu: number; gia_von: number; lai: number };
type Xem = {
  ung_vien: number; con_lai: number; moi_lo: number; bo_qua: number; bo_qua_tiep: number;
  se_dong: number; khong_dong_duoc: number; vi_sao_khong_dong: Record<string, number>;
  theo_ky: Ky[]; tong_doanh_thu: number; tong_gia_von: number; ghi_chu: string;
};
type Chay = Xem & { da_dong: number; message: string };
type Go = {
  se_go: number; da_go: number; giu_lai_do_dong_that: number;
  con_lai: number; bo_qua_tiep: number; message: string;
};

const tien = (n: number) => (n || 0).toLocaleString("vi-VN") + " đ";

export default function KhoCuDongSoBu({ onXong }: { onXong?: () => void }) {
  const { xacNhan, nhap, hop } = useHoi();
  const user = getUser();
  const [mo, setMo] = useState(false);
  const [moiLo, setMoiLo] = useState(50);
  const [xem, setXem] = useState<Xem | null>(null);
  const [dangChay, setDangChay] = useState(false);
  const [tien_do, setTienDo] = useState("");
  const [tin, setTin] = useState("");
  const [loi, setLoi] = useState("");

  // Vai trò do MÁY CHỦ quyết định (require_roles ở /kho-cu/dong-so-bu). Giấu nút chỉ để đỡ rối
  // mắt — giấu không phải là phân quyền.
  if (!user || !DUOC_XEM.includes(user.role)) return null;

  async function nhinTruoc() {
    setDangChay(true); setLoi(""); setTin(""); setTienDo("");
    try {
      setXem(await api<Xem>(`/quyet-toan-lop3/kho-cu/dong-so-bu/xem?moi_lo=${moiLo}&bo_qua=0`));
    } catch (e) { setLoi(errMsg(e)); }
    finally { setDangChay(false); }
  }

  async function dong() {
    if (!await xacNhan(
      `ĐÓNG SỐ BÙ cho kho quyết toán cũ?\n\n` +
      `• Chạy theo lô ${moiLo} chuyến, gọi tiếp cho tới hết.\n` +
      `• Mốc kỳ lấy theo NGÀY KẾT THÚC của từng chuyến — tiền rơi vào tháng nó phát sinh,\n` +
      `  không dồn vào tháng bấm nút.\n` +
      `• Chủ tịch ký thay các phòng ban. Mỗi lô ghi một dòng nhật ký mang tên ${user!.username}.\n\n` +
      `Bấm nhầm thì gỡ lại được bằng nút "Gỡ" ngay dưới.`
    )) return;

    setDangChay(true); setLoi(""); setTin(""); setTienDo("");
    let bo_qua = 0, tong = 0, lo = 0, con_lai = -1, loi_nhan = "";
    try {
      while (lo < TRAN_LO) {
        const r = await api<Chay>("/quyet-toan-lop3/kho-cu/dong-so-bu",
          { method: "POST", json: { xac_nhan: true, moi_lo: moiLo, bo_qua } });
        tong += r.da_dong; lo += 1; bo_qua = r.bo_qua_tiep;
        con_lai = r.con_lai; loi_nhan = r.message || "";
        setTienDo(`Lô ${lo} · đã đóng ${tong} chuyến · còn ${con_lai} chưa xét`);
        if (con_lai <= 0) break;
      }
      if (con_lai > 0) {
        setLoi(`Dừng ở lô ${lo} cho an toàn — vẫn còn ${con_lai} chuyến chưa xét. ` +
               `${tong} chuyến đã đóng thì ĐÃ CHỐT, không mất. Bấm lại để chạy tiếp.`);
      } else {
        setTin(`Đã đóng số ${tong} chuyến qua ${lo} lô. ${loi_nhan}`);
      }
    } catch (e) {
      // Mỗi lô đã xong là đã chốt ở máy chủ, nên hỏng ở lô sau KHÔNG kéo lô trước về.
      setLoi(`${errMsg(e)} — dừng ở lô ${lo + 1}. ${tong} chuyến đã đóng vẫn giữ nguyên, bấm lại để chạy tiếp.`);
    } finally { setDangChay(false); setXem(null); onXong?.(); }
  }

  async function go() {
    if (!await xacNhan(
      `GỠ phần CỬA NÀY đã đóng số?\n\n` +
      `• Trả chuyến về "kết thúc", xoá doanh thu / giá vốn / mốc kỳ do cửa bù ghi.\n` +
      `• KHÔNG đụng chuyến Điều hành đã đóng số THẬT — cửa gỡ nhận ra bằng mốc kỳ và giữ lại.\n` +
      `• Chạy theo lô ${moiLo} chuyến. Ghi nhật ký mang tên ${user!.username}.`
    )) return;

    setDangChay(true); setLoi(""); setTin(""); setTienDo("");
    let bo_qua = 0, tong = 0, giu = 0, lo = 0, con_lai = -1;
    try {
      while (lo < TRAN_LO) {
        const r = await api<Go>("/quyet-toan-lop3/kho-cu/dong-so-bu/go",
          { method: "POST", json: { xac_nhan: true, moi_lo: moiLo, bo_qua } });
        tong += r.da_go; giu = Math.max(giu, r.bo_qua_tiep); lo += 1; bo_qua = r.bo_qua_tiep;
        con_lai = r.con_lai;
        setTienDo(`Lô ${lo} · đã gỡ ${tong} chuyến · còn ${con_lai} chưa xét`);
        if (con_lai <= 0) break;
      }
      if (con_lai > 0) {
        setLoi(`Dừng ở lô ${lo} cho an toàn — còn ${con_lai} chuyến chưa xét. ${tong} chuyến đã gỡ thì đã chốt.`);
      } else {
        setTin(`Đã gỡ ${tong} chuyến qua ${lo} lô. Giữ nguyên ${giu} chuyến đã đóng số THẬT.`);
      }
    } catch (e) {
      setLoi(`${errMsg(e)} — dừng ở lô ${lo + 1}. ${tong} chuyến đã gỡ vẫn giữ nguyên, bấm lại để chạy tiếp.`);
    } finally { setDangChay(false); setXem(null); onXong?.(); }
  }

  return (
    <div className="card" style={{ marginBottom: 12, borderLeft: "3px solid #0369a1" }}>{hop}
      <button className="link" onClick={() => setMo(!mo)} style={{ fontWeight: 600 }}>
        {mo ? "▾" : "▸"} Kho quyết toán cũ — đóng số bù (Chủ tịch ký thay)
      </button>

      {mo && (
        <div style={{ marginTop: 10 }}>
          <p className="muted" style={{ marginTop: 0 }}>
            Chuyến kho cũ đã nạp xong nhưng chưa ai <b>đóng số</b>, nên doanh thu và giá vốn của
            chúng chưa lên báo cáo. Cửa này đóng số thay, và <b>mốc kỳ lấy theo ngày kết thúc của
            chính chuyến</b> — tiền rơi vào tháng nó phát sinh chứ không dồn vào tháng bấm nút.
          </p>
          <p className="muted">
            Chạy <b>theo lô</b>: mỗi lô là một giao dịch riêng, xong là chốt. Dừng giữa chừng thì
            phần đã làm vẫn sạch, mở lại bấm tiếp chứ không làm lại từ đầu.
          </p>

          <div className="row" style={{ gap: 8, marginTop: 8, flexWrap: "wrap", alignItems: "center" }}>
            <label className="muted">Mỗi lô&nbsp;
              <input type="number" min={1} max={500} value={moiLo} style={{ width: 70 }}
                     onChange={(e) => setMoiLo(Math.max(1, Math.min(500, +e.target.value || 50)))} />
              &nbsp;chuyến
            </label>
            <button disabled={dangChay} onClick={nhinTruoc}>
              {dangChay ? "Đang đếm…" : "Xem trước một lô"}
            </button>
          </div>

          {tien_do && <p className="muted" style={{ marginTop: 8 }}><b>{tien_do}</b></p>}
          {loi && <p className="err" style={{ marginTop: 8 }}>{loi}</p>}
          {tin && <p className="ok" style={{ marginTop: 8 }}>{tin}</p>}

          {xem && (
            <div style={{ marginTop: 12 }}>
              <p className="muted">{xem.ghi_chu}</p>
              <table className="tbl" style={{ maxWidth: 560 }}>
                <tbody>
                  <tr><td>Xét trong lô này</td>
                      <td style={{ textAlign: "right" }}>{xem.ung_vien}</td></tr>
                  <tr><td><b>Đóng được</b></td>
                      <td style={{ textAlign: "right" }}><b>{xem.se_dong}</b></td></tr>
                  <tr><td>Không đóng được</td>
                      <td style={{ textAlign: "right" }}>{xem.khong_dong_duoc}</td></tr>
                  <tr><td>Chưa xét (các lô sau)</td>
                      <td style={{ textAlign: "right" }}>{xem.con_lai}</td></tr>
                  <tr><td>Doanh thu của lô</td>
                      <td style={{ textAlign: "right" }}>{tien(xem.tong_doanh_thu)}</td></tr>
                  <tr><td>Giá vốn của lô</td>
                      <td style={{ textAlign: "right" }}>{tien(xem.tong_gia_von)}</td></tr>
                </tbody>
              </table>

              {xem.theo_ky.length > 0 && (
                <>
                  <p className="muted" style={{ marginTop: 10, marginBottom: 4 }}>
                    Tiền của lô này rơi vào những tháng nào:
                  </p>
                  <table className="tbl" style={{ maxWidth: 560 }}>
                    <thead><tr><th>Tháng</th><th style={{ textAlign: "right" }}>Chuyến</th>
                      <th style={{ textAlign: "right" }}>Doanh thu</th>
                      <th style={{ textAlign: "right" }}>Giá vốn</th></tr></thead>
                    <tbody>
                      {xem.theo_ky.map((k) => (
                        <tr key={k.ky}>
                          <td>{k.ky}</td>
                          <td style={{ textAlign: "right" }}>{k.so_chuyen}</td>
                          <td style={{ textAlign: "right" }}>{tien(k.doanh_thu)}</td>
                          <td style={{ textAlign: "right" }}>{tien(k.gia_von)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}

              {xem.khong_dong_duoc > 0 && (
                <details style={{ marginTop: 8 }}>
                  <summary className="muted">
                    {xem.khong_dong_duoc} chuyến trong lô KHÔNG đóng được — bấm xem vì sao
                  </summary>
                  <ul className="muted" style={{ marginTop: 6 }}>
                    {Object.entries(xem.vi_sao_khong_dong).map(([v, n]) => (
                      <li key={v}>{v} — <b>{n}</b> chuyến</li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          )}

          {/* Nút ghi chỉ sống SAU khi đã xem — con số hiện ra là con số máy chủ vừa đếm. */}
          <div className="row" style={{ gap: 8, marginTop: 12, flexWrap: "wrap" }}>
            <button disabled={dangChay || !xem} onClick={dong}>
              {dangChay ? "Đang chạy…" : "Đóng số bù — chạy hết theo lô"}
            </button>
            <button className="danger" disabled={dangChay} onClick={go}>
              {dangChay ? "Đang chạy…" : "Gỡ lại phần cửa này đã đóng"}
            </button>
          </div>
          <p className="muted" style={{ marginTop: 6, fontSize: 12 }}>
            Nút gỡ không cần xem trước: nó chỉ trả lại đúng phần chính cửa này ghi, và luôn giữ
            nguyên chuyến Điều hành đã đóng số thật.
          </p>
        </div>
      )}
    </div>
  );
}
