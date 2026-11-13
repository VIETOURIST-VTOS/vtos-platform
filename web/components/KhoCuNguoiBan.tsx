"use client";
/** GÁN NGƯỜI BÁN cho kho quyết toán cũ T1–T6/2026.
 *
 * VÌ SAO CÓ MÀN HÌNH NÀY
 *
 * Cột SALES trong 604 tệp Excel ghi TÊN NGƯỜI, còn báo cáo doanh số của VTOS gắn vào TÀI KHOẢN.
 * Giữa hai thứ ấy phải có một bước dịch. Máy dịch được phần lớn, nhưng hai loại còn lại chỉ người
 * mới giải: một cách gọi tắt ứng với nhiều người, và một cái tên không có trong danh sách nhân sự.
 *
 * BA ĐIỀU MÀN HÌNH NÀY TỰ BUỘC MÌNH
 *
 * 1. XẾP THEO SỐ DÒNG KHÁCH, không theo bảng chữ cái. Người ngồi gán có việc khác phải làm; gán cái
 *    tên đáng 978 dòng trước cái tên đáng 5 dòng là chênh nhau rất nhiều.
 * 2. BÀY SẴN ỨNG VIÊN khi máy thấy nhiều người cùng ứng. Bắt người ta tự nhớ "Thùy Trang nào" là
 *    cách chắc chắn để họ chọn nhầm.
 * 3. CÓ NÚT "KHÔNG PHẢI NHÂN VIÊN" — để trống CÓ CHỦ Ý. Không có nút ấy thì cái tên "J Travel" cứ
 *    nằm mãi trong danh sách việc còn nợ, và người ta sẽ gán bừa nó cho ai đó để danh sách sạch đi.
 */
import { useEffect, useState } from "react";
import { api, getUser, vnd } from "@/lib/api";
import { errMsg } from "@/components/ui";
import { useHoi } from "@/components/HopHoi";

type Dong = {
  khoa_ten: string;
  ten_trong_tep: string;
  user_id: number | null;
  ten_tai_khoan: string;
  cach_khop: string;
  ung_vien: string[];
  so_dong: number;
  nguoi_gan: string;
};
type Bang = {
  tong_ten: number;
  da_khop: number; dong_da_khop: number;
  can_gan: number; dong_can_gan: number;
  dong: Dong[];
  ghi_chu: string;
};
type GanLai = {
  doi_duoc: { phieu: string; ten_trong_tep: string; ve_tai_khoan: string; tien: number }[];
  con_treo: any[];
  tien_ve_nguoi_that: number;
  ghi_chu: string;
};

const DUOC_XEM = ["chutich", "tgd", "cntt", "tp_dh", "hcns"];

const NHAN_CACH_KHOP: Record<string, string> = {
  dung_ten: "khớp đúng cả họ tên",
  duoi_ten: "khớp đuôi tên",
  duoi_ten_phong_kd: "khớp đuôi tên + là người phòng kinh doanh",
  nguoi_gan: "người gán",
  trung_ten: "nhiều người cùng ứng — cần chọn",
  ngoai_danh_sach: "không có trong danh sách nhân sự",
  khong_phai_ten: "không phải tên người",
};

export default function KhoCuNguoiBan({ onXong }: { onXong?: () => void }) {
  const { xacNhan, nhap, hop } = useHoi();
  const user = getUser();
  const [mo, setMo] = useState(false);
  const [b, setB] = useState<Bang | null>(null);
  const [tk, setTk] = useState<any[]>([]);
  const [gl, setGl] = useState<GanLai | null>(null);
  const [chay, setChay] = useState(false);
  const [loi, setLoi] = useState("");
  const [tin, setTin] = useState("");
  const [chiCanGan, setChiCanGan] = useState(true);

  useEffect(() => {
    if (!mo) return;
    tai();
    api<any[]>("/users").then((r) => setTk(Array.isArray(r) ? r : (r as any).rows || [])).catch(() => {});
  }, [mo]); // eslint-disable-line

  async function tai() {
    setLoi("");
    try {
      setB(await api<Bang>("/quyet-toan-lop3/kho-cu/nguoi-ban"));
      setGl(await api<GanLai>("/quyet-toan-lop3/kho-cu/gan-lai"));
    } catch (e) { setLoi(errMsg(e)); }
  }

  async function gan(khoa: string, uid: number | null) {
    setChay(true); setLoi(""); setTin("");
    try {
      await api("/quyet-toan-lop3/kho-cu/nguoi-ban/gan",
        { method: "POST", json: { khoa_ten: khoa, user_id: uid } });
      await tai();
    } catch (e) { setLoi(errMsg(e)); }
    finally { setChay(false); }
  }

  async function chuyenPhieu() {
    if (!gl?.doi_duoc.length) return;
    if (!await xacNhan(
      `Chuyển ${gl.doi_duoc.length} phiếu đặt (${vnd(gl.tien_ve_nguoi_that) + " đ"}) về đúng người bán?\n\n` +
      `Chỉ đổi chủ phiếu — không nạp lại lô, không đụng dòng khách hay dòng chi.\n` +
      `Việc này ghi vào nhật ký mang tên ${user!.username}.`
    )) return;
    setChay(true); setLoi(""); setTin("");
    try {
      const r = await api<any>("/quyet-toan-lop3/kho-cu/gan-lai",
        { method: "POST", json: { xac_nhan: true } });
      setTin(r.ghi_chu); await tai(); onXong?.();
    } catch (e) { setLoi(errMsg(e)); }
    finally { setChay(false); }
  }

  // Vai trò do MÁY CHỦ quyết định (require_roles). Giấu ở đây chỉ để đỡ rối mắt — giấu nút không
  // phải là phân quyền.
  if (!user || !DUOC_XEM.includes(user.role)) return null;

  const ds = (b?.dong || []).filter((d) => !chiCanGan || (!d.user_id && d.cach_khop !== "nguoi_gan"));

  return (
    <div className="card" style={{ marginBottom: 12, borderLeft: "3px solid #1d4ed8" }}>{hop}
      <button className="link" onClick={() => setMo(!mo)} style={{ fontWeight: 600 }}>
        {mo ? "▾" : "▸"} Gán người bán cho kho quyết toán cũ T1–T6/2026
      </button>

      {mo && (
        <div style={{ marginTop: 10 }}>
          <p className="muted" style={{ marginTop: 0 }}>
            Cột <b>SALES</b> trong tệp quyết toán cũ ghi tên người; báo cáo doanh số thì gắn vào tài
            khoản. Máy khớp được phần chắc chắn, phần còn lại cần người chỉ. <b>Dòng chưa gán vẫn
            tính doanh thu cho công ty</b> — chỉ không vào chỉ tiêu của ai, vì cộng nhầm cho người
            khác tệ hơn là để trống.
          </p>

          {loi && <p className="err">{loi}</p>}
          {tin && <p className="ok">{tin}</p>}

          {b && (
            <>
              <table className="tbl" style={{ maxWidth: 560, marginBottom: 10 }}>
                <tbody>
                  <tr><td>Tên đã có tài khoản</td>
                      <td style={{ textAlign: "right" }}>{b.da_khop}</td>
                      <td style={{ textAlign: "right" }} className="muted">{b.dong_da_khop} dòng khách</td></tr>
                  <tr><td><b>Còn chờ người gán</b></td>
                      <td style={{ textAlign: "right" }}><b>{b.can_gan}</b></td>
                      <td style={{ textAlign: "right" }} className="muted">{b.dong_can_gan} dòng khách</td></tr>
                </tbody>
              </table>

              {gl && gl.doi_duoc.length > 0 && (
                <div className="card" style={{ padding: 10, marginBottom: 10, background: "#f0f9ff" }}>
                  <p style={{ margin: 0 }}>
                    <b>{gl.doi_duoc.length} phiếu đặt</b> ({vnd(gl.tien_ve_nguoi_that) + " đ"}) nay đã
                    tra ra tài khoản và đang chờ chuyển về đúng người bán.
                  </p>
                  <button disabled={chay} onClick={chuyenPhieu} style={{ marginTop: 8 }}>
                    {chay ? "Đang chuyển…" : "Chuyển về đúng người bán"}
                  </button>
                </div>
              )}

              <label className="muted" style={{ display: "block", marginBottom: 6 }}>
                <input type="checkbox" checked={chiCanGan}
                       onChange={(e) => setChiCanGan(e.target.checked)} />{" "}
                chỉ hiện tên còn chờ gán
              </label>

              <div style={{ overflowX: "auto" }}>
                <table className="tbl">
                  <thead>
                    <tr>
                      <th>Tên trong tệp</th>
                      <th style={{ textAlign: "right" }}>Dòng khách</th>
                      <th>Máy khớp</th>
                      <th>Tài khoản</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ds.slice(0, 200).map((d) => (
                      <tr key={d.khoa_ten}>
                        <td><b>{d.ten_trong_tep}</b></td>
                        <td style={{ textAlign: "right" }}>{d.so_dong}</td>
                        <td className="muted">
                          {NHAN_CACH_KHOP[d.cach_khop] || d.cach_khop}
                          {d.ung_vien.length > 1 && (
                            <div style={{ fontSize: 12 }}>
                              ứng viên: {d.ung_vien.map((x) => x.split(":").slice(1).join(":")).join(" · ")}
                            </div>
                          )}
                          {d.nguoi_gan && <div style={{ fontSize: 12 }}>do {d.nguoi_gan} gán</div>}
                        </td>
                        <td>
                          <select disabled={chay} value={d.user_id ?? ""}
                                  onChange={(e) => gan(d.khoa_ten,
                                    e.target.value === "" ? null : Number(e.target.value))}>
                            {/* Để trống CÓ CHỦ Ý là một lựa chọn thật, không phải "chưa làm" */}
                            <option value="">— không phải nhân viên —</option>
                            {tk.map((x: any) => (
                              <option key={x.id} value={x.id}>
                                {x.full_name}{x.active === false ? " (đã nghỉ)" : ""}
                              </option>
                            ))}
                          </select>
                        </td>
                      </tr>
                    ))}
                    {ds.length === 0 && (
                      <tr><td colSpan={4} className="muted">
                        Không còn tên nào chờ gán.
                      </td></tr>
                    )}
                  </tbody>
                </table>
              </div>
              {ds.length > 200 && (
                <p className="muted">… và {ds.length - 200} tên nữa</p>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
