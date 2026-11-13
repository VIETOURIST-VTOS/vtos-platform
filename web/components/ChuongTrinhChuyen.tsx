"use client";
import { useEffect, useState } from "react";
import { api, getUser } from "@/lib/api";
import { useHoi } from "@/components/HopHoi";

/** 4.4.2 Chương trình của từng chuyến — tab «Chương trình» trên trang chi tiết chuyến.
 *
 *  MÀN HÌNH NÀY BÀY HAI BẢN CẠNH NHAU, và đó là điểm chính của nó: bản của CHUYẾN (sửa được) và
 *  bản của SẢN PHẨM (chỉ xem). Người điều hành nhìn thấy mình đang lệch khỏi bản mẫu ở chỗ nào.
 *
 *  Nút «Đề xuất tách» KHÔNG tự ghi: nó in ra bản tách để đọc, bấm nhận mới ghi, và chỉ ghi vào
 *  ngày đang rỗng. Một bản tách sai nhưng gọn gàng thì không ai đọc lại lần thứ hai.
 */
const T = (b: boolean) => (b ? "✓" : "—");

export default function ChuongTrinhChuyen({ tourId }: { tourId: number }) {
  const { xacNhan, nhap, hop } = useHoi();
  const u = getUser();
  const [d, setD] = useState<any>(null);
  const [dx, setDx] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const [moBanGoc, setMoBanGoc] = useState(false);

  async function nap() {
    setLoi("");
    try { setD(await api(`/chuong-trinh/${tourId}`)); }
    catch (e: any) { setLoi(String(e?.message || e)); }
  }
  useEffect(() => { nap(); /* eslint-disable-next-line */ }, [tourId]);

  const suaDuoc = ["chutich", "tgd", "bks", "robot_ks", "tp_dh", "nv_dh", "cntt"]
    .includes(u?.role || "");

  async function mo() {
    try { await api(`/chuong-trinh/${tourId}/mo`, { method: "POST" }); nap(); }
    catch (e: any) { setLoi(String(e?.message || e)); }
  }

  async function xemDeXuat() {
    try { setDx(await api(`/chuong-trinh/${tourId}/de-xuat-tach`)); }
    catch (e: any) { setLoi(String(e?.message || e)); }
  }

  async function nhanDeXuat() {
    try { await api(`/chuong-trinh/${tourId}/nhan-de-xuat`, { method: "POST" }); setDx(null); nap(); }
    catch (e: any) { setLoi(String(e?.message || e)); }
  }

  async function luu(ngayThu: number, o: any) {
    const ly_do = d?.da_khoi_hanh
      ? (await nhap("Chuyến đã khởi hành — sửa chương trình thì phải ghi lý do:") || "")
      : "";
    if (d?.da_khoi_hanh && !ly_do.trim()) { setLoi("Chuyến đã khởi hành, phải ghi lý do."); return; }
    try { await api(`/chuong-trinh/${tourId}/ngay/${ngayThu}`, { method: "PUT", json: { ...o, ly_do } }); nap(); }
    catch (e: any) { setLoi(String(e?.message || e)); }
  }

  async function themNgay() {
    try { await api(`/chuong-trinh/${tourId}/them-ngay`, { method: "POST" }); nap(); }
    catch (e: any) { setLoi(String(e?.message || e)); }
  }

  if (!d) return (<section><p className="muted">Đang nạp…</p>{loi && <p className="loi">{loi}</p>}</section>);

  return (
    <section>{hop}
      <h2>Chương trình chuyến {d.ma_chuyen}</h2>
      <p className="muted">
        Chương trình <b>của riêng chuyến này</b>, không phải của sản phẩm. Nó được <b>chép một lần</b> rồi
        sống độc lập: sửa chương trình sản phẩm sau đó <b>không</b> đổi chuyến này — nếu không, một đoàn
        đã đi xong sẽ bị viết lại lịch trình và bản khách cầm trong tay không còn khớp với bản trên hệ thống.
      </p>
      {loi && <p className="loi">{loi}</p>}

      {d.rows.length === 0 && suaDuoc && (
        <div className="the">
          <p>Chuyến này chưa có khung chương trình.</p>
          <button onClick={mo}>Dựng khung {d.so_ngay_cua_chuyen} ngày (rỗng)</button>
        </div>
      )}

      {d.lech_so_ngay?.co_lech && (
        <p className="canh-bao"><b>Lệch số ngày:</b> {d.lech_so_ngay.ly_do}</p>
      )}
      {d.lech_voi_san_pham?.co_lech && (
        <p className="canh-bao"><b>Sản phẩm đã đổi:</b> {d.lech_voi_san_pham.ly_do}</p>
      )}
      {d.ngay_trong?.length > 0 && (
        <p className="canh-bao">
          <b>Ngày chưa soạn:</b> {d.ngay_trong.join(", ")} — chương trình chưa gửi khách được.
        </p>
      )}

      <p className="muted">
        Nguồn: <b>{d.nguon_ten}</b>
        {d.chep_luc && <> · chụp bản sản phẩm lúc {new Date(d.chep_luc).toLocaleString("vi-VN")}</>}
      </p>

      {d.rows.length > 0 && (
        <table className="bang">
          <thead>
            <tr><th>Ngày</th><th>Tiêu đề</th><th>Nội dung</th><th>S/T/Tối</th>
                <th>Khách sạn</th><th>Phương tiện</th><th></th></tr>
          </thead>
          <tbody>
            {d.rows.map((r: any) => (
              <tr key={r.id} className={r.trong ? "canh-bao" : ""}>
                <td>{r.ngay_thu}<div className="muted">{r.ngay}</div></td>
                <td>
                  {suaDuoc
                    ? <input defaultValue={r.tieu_de}
                             onBlur={(e) => e.target.value !== r.tieu_de && luu(r.ngay_thu, { tieu_de: e.target.value })} />
                    : r.tieu_de}
                </td>
                <td>
                  {suaDuoc
                    ? <textarea defaultValue={r.noi_dung} rows={3}
                                onBlur={(e) => e.target.value !== r.noi_dung && luu(r.ngay_thu, { noi_dung: e.target.value })} />
                    : <pre style={{ whiteSpace: "pre-wrap", fontSize: 12 }}>{r.noi_dung}</pre>}
                  {r.lan_sua_sau_khoi_hanh > 0 && (
                    <div className="muted">
                      đã sửa {r.lan_sua_sau_khoi_hanh} lần sau khi khởi hành — lý do gần nhất:{" "}
                      {r.ly_do_sua_gan_nhat}
                    </div>
                  )}
                </td>
                <td>{T(r.bua_sang)}/{T(r.bua_trua)}/{T(r.bua_toi)}</td>
                <td>
                  {suaDuoc
                    ? <input defaultValue={r.khach_san}
                             onBlur={(e) => e.target.value !== r.khach_san && luu(r.ngay_thu, { khach_san: e.target.value })} />
                    : r.khach_san}
                </td>
                <td>{r.phuong_tien}</td>
                <td className="muted">{r.sua_boi}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {suaDuoc && d.rows.length > 0 && (
        <div className="hang">
          <button onClick={themNgay}>Thêm một ngày</button>
          <button onClick={xemDeXuat}>Đề xuất tách từ bản sản phẩm</button>
        </div>
      )}

      {dx && (
        <div className="the">
          <h3>Bản đề xuất — chưa ghi gì</h3>
          <p className="muted">{dx.ly_do}</p>
          {dx.tach_duoc && (<>
            <ul>{dx.rows.map((r: any) => (
              <li key={r.ngay_thu}><b>Ngày {r.ngay_thu}</b> — {r.tieu_de}</li>))}
            </ul>
            <p className="muted">Bấm nhận chỉ ghi vào <b>ngày đang rỗng</b>; ngày đã soạn giữ nguyên.</p>
            <button onClick={nhanDeXuat}>Nhận bản đề xuất</button>{" "}
          </>)}
          <button onClick={() => setDx(null)}>Đóng</button>
        </div>
      )}

      {d.ban_san_pham_goc && (
        <div className="the">
          <button onClick={() => setMoBanGoc(!moBanGoc)}>
            {moBanGoc ? "Ẩn" : "Xem"} bản sản phẩm đã chụp lúc chép
          </button>
          {moBanGoc && <pre style={{ whiteSpace: "pre-wrap", fontSize: 12 }}>{d.ban_san_pham_goc}</pre>}
        </div>
      )}
    </section>
  );
}
