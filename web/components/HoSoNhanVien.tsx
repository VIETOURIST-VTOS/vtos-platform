"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** HS-2 · Hồ sơ nhân viên — bấm vào số hồ sơ trên bảng Tài khoản thì mở ra cái này.
 *
 *  MÀN HÌNH NÀY KHÔNG GIỮ MỘT BẢN SAO NÀO CỦA BẢNG QUYỀN, và đó là điều quan trọng nhất ở đây.
 *  Nó vẽ đúng những gì cửa trả về: nhóm nào hiện, trường nào trong nhóm ấy, giá trị đã che hay
 *  chưa — tất cả do máy chủ quyết. Giá trị thật của trường bị che KHÔNG BAO GIỜ tới được tệp này,
 *  nên không có cách nào lộ bằng tab Network, và cũng không có cách nào một lần sửa giao diện
 *  vô tình mở ra thứ không được mở.
 *
 *  Bảng dưới chỉ là TÊN TIẾNG VIỆT của từng trường. Trường chưa có tên thì hiện nguyên khoá máy
 *  chứ KHÔNG bị bỏ — thiếu một dòng chữ không phải lý do để giấu một ô dữ liệu đi.
 */
const TEN_TRUONG: Record<string, string> = {
  staff_code: "Mã nhân viên", full_name: "Họ tên", department: "Phòng", title: "Chức vụ bảng lương",
  position: "Chức danh", sales_group: "Nhóm kinh doanh", office: "Văn phòng", company_id: "Pháp nhân",
  contract_type: "Loại hợp đồng", start_date: "Ngày vào", tham_nien: "Thâm niên",
  active: "Đang làm", ended_on: "Ngày nghỉ việc",
  end_kind: "Loại lý do nghỉ", end_reason: "Lý do nghỉ việc",
  email: "Email cơ quan", zalo_noi: "Zalo nội bộ", phone: "Điện thoại cá nhân",
  username: "Tên đăng nhập", role: "Vai trò", last_login_at: "Đăng nhập lần cuối",
  must_change_password: "Mật khẩu tạm", ngoai_bien_che: "Ngoài biên chế", so_quyen: "Số quyền",
  dob: "Ngày sinh", gender: "Giới tính", id_number: "Số CCCD", id_issued_on: "Ngày cấp",
  id_issued_by: "Nơi cấp", permanent_address: "Hộ khẩu thường trú", current_address: "Chỗ ở hiện tại",
  tax_code: "MST cá nhân", social_insurance_no: "Số sổ BHXH",
  contract_type_hd: "Hợp đồng lao động", contract_end: "Hạn hợp đồng", base_salary: "Lương công việc",
  bhxh_base: "Căn cứ đóng BHXH", probation: "Thử việc", so_nguoi_phu_thuoc: "Người phụ thuộc",
  bank_account: "Tài khoản ngân hàng",
  so_dong_tro_toi: "Tổng số dòng dữ liệu đang trỏ tới", viec_dang_ganh: "Việc đang gánh",
  so_tour: "Tour đang điều hành", so_quyet_toan_giu: "Quyết toán đang giữ",
  so_booking: "Booking đang bán", so_lenh_xe: "Lệnh điều xe", so_visa: "Hồ sơ visa phụ trách",
  so_phan_cong_kd: "Phân công kinh doanh",
  ngay_cong_ky_nay: "Ngày công kỳ này", duoc_xac_nhan_cong: "Được xác nhận công",
  duoc_duyet_nghi: "Được duyệt nghỉ", so_don_cho_duyet: "Đơn nghỉ chờ duyệt",
  ly_do_nghi: "Lý do nghỉ",
  card_no: "Số thẻ nghề nghiệp", card_type: "Loại thẻ", card_expiry: "Hạn thẻ",
  xe_dang_gan: "Xe đang gắn", advance_limit: "Hạn mức tạm ứng", fuel_card_last4: "Thẻ nhiên liệu",
  ctv_contract: "Hợp đồng cộng tác", su_co: "Số sự cố đã báo",
  danh_gia_gan_nhat: "Kỳ đánh giá gần nhất", diem_danh_gia: "Điểm đánh giá",
  tai_san_da_cap: "Tài sản đang giữ",
  nhat_ky: "Nhật ký hồ sơ", nhat_ky_gia_tri: "Nhật ký kèm giá trị",
};

const LUAT_TEN: Record<string, string> = {
  chinh_minh: "hồ sơ của chính mình",
  cay_le: "theo sơ đồ tổ chức Kinh doanh — mảng Lẻ",
  cay_doan: "theo sơ đồ tổ chức Kinh doanh — mảng Đoàn",
  cay_le_toan_bo: "nhìn toàn bộ cây Lẻ",
  cay_doan_toan_bo: "nhìn toàn bộ cây Đoàn",
  cung_phong_luat_yeu: "cùng phòng — LUẬT YẾU, chỉ so tên phòng",
  khac_phong: "khác phòng", ngoai_cay: "ngoài nhánh quản lý",
  khong_phai_vai_dung_dau: "vai này không quản lý ai",
};

function oGiaTri(v: any) {
  if (v === null || v === undefined || v === "") return <span className="muted">—</span>;
  if (typeof v === "boolean") return v ? "có" : "không";
  if (Array.isArray(v)) {
    if (v.length === 0) return <span className="muted">không có dòng nào</span>;
    return <>{v.map((x: any, i: number) =>
      <div key={i} style={{ fontSize: 12 }}>
        {typeof x === "object"
          ? Object.entries(x).map(([k, z]) => `${k}: ${Array.isArray(z) ? z.join(", ") : z}`).join(" · ")
          : String(x)}
      </div>)}</>;
  }
  // HS-12: hai số của một loại việc — đang mở hôm nay, và từ trước tới nay.
  if (typeof v === "object" && "dang_mo" in v && "tong" in v)
    return <span style={{ fontVariantNumeric: "tabular-nums" }}>
      đang mở <b>{v.dang_mo}</b> <span className="muted">· từ trước tới nay {v.tong}</span></span>;
  if (typeof v === "object") return <code style={{ fontSize: 12 }}>{JSON.stringify(v)}</code>;
  return String(v);
}

export default function HoSoNhanVien({ uid, hoTen, onClose }:
  { uid: number; hoTen: string; onClose: () => void }) {
  const [d, setD] = useState<any>(null);
  const [loi, setLoi] = useState("");
  // GIÁ TRỊ ĐÃ HIỆN chỉ sống trong bộ nhớ của lần mở này: đóng hồ sơ là mất, mở lại là một lượt
  // đọc mới và một dòng nhật ký mới. Nhớ lại qua các lần mở thì con số lượt đọc trong nhật ký
  // thấp hơn số lần người ta thực sự nhìn thấy, và nhật ký ấy nói sai.
  const [hien, setHien] = useState<Record<string, any>>({});
  const [dangHien, setDangHien] = useState("");

  async function xinHien(truong: string, ten: string) {
    // MỤC ĐÍCH DO NGƯỜI GÕ, không có danh sách chọn sẵn. Một ô chọn "làm hợp đồng / khai BHXH /
    // khác" thì ai cũng bấm cái đầu tiên, và cột mục đích trong nhật ký thành một cột vô nghĩa.
    const md = prompt(`Xem giá trị thật của «${ten}» để làm gì?\n\n`
      + `Lượt xem này vào nhật ký hồ sơ mang tên bạn, kèm câu bạn ghi ở đây.`);
    if (md === null) return;
    setDangHien(truong);
    try {
      const r = await api<any>(`/employees/tai-khoan/${uid}/hien-truong`,
        { method: "POST", json: { truong, muc_dich: md } });
      setHien((cu) => ({ ...cu, [truong]: r.gia_tri }));
    } catch (e) {
      setLoi(errMsg(e));
    } finally {
      setDangHien("");
    }
  }

  useEffect(() => {
    setD(null); setLoi("");
    api(`/employees/tai-khoan/${uid}/ho-so-theo-vai`)
      .then(setD)
      .catch((e) => setLoi(errMsg(e)));
  }, [uid]);

  return <div style={{ border: "1px solid var(--line, #2a3b55)", borderRadius: 8, padding: 14, marginTop: 14 }}>
    <div className="row" style={{ gap: 10, alignItems: "baseline", marginBottom: 10 }}>
      <h3 style={{ margin: 0 }}>Hồ sơ nhân viên — {hoTen}</h3>
      {d && <span className="muted" style={{ fontSize: 12 }}>
        bạn đang xem với vai <b>{d.vai_nguoi_xem}</b> · {d.nhom_thay.length} nhóm hiện ra
      </span>}
      <button className="act grey" style={{ margin: 0, marginLeft: "auto" }} onClick={onClose}>Đóng</button>
    </div>

    {loi && <p className="muted" style={{ color: "#f2868a" }}>{loi}</p>}
    {!d && !loi && <p className="muted">Đang mở hồ sơ…</p>}

    {d && <>
      {/* VÌ SAO HIỆN DÒNG NÀY: luật phạm vi "cùng phòng" chỉ so một chuỗi chữ, không có cây tổ chức
          và không có ngày hiệu lực. Người xem phải biết mình đang dựa vào cái gì — giấu chỗ yếu đi
          thì ngày nó sai không ai ngờ tới. */}
      {d.luat_pham_vi && d.luat_pham_vi !== "khong_phai_vai_dung_dau" &&
        <p className="muted" style={{ fontSize: 12, marginTop: 0 }}>
          Phạm vi: {LUAT_TEN[d.luat_pham_vi] || d.luat_pham_vi}
          {d.luat_pham_vi === "cung_phong_luat_yeu" && <> — <Tag cls="warn">luật yếu</Tag></>}
        </p>}

      {d.nhom_thay.map((n: any) => <div key={n.ma} style={{ marginBottom: 12 }}>
        <div className="row" style={{ gap: 8, alignItems: "baseline", marginBottom: 4 }}>
          <b style={{ fontSize: 13 }}>{n.ma} · {n.ten}</b>
          {n.quyen === "che" && <Tag cls="warn">đã che</Tag>}
          {n.nhay_cam && <span className="muted" style={{ fontSize: 11 }}>lượt đọc vào nhật ký</span>}
        </div>
        {n.truong.length === 0
          ? <p className="muted" style={{ fontSize: 12, margin: 0 }}>chưa có số liệu nào trong nhóm này</p>
          : <div className="scroll"><table><tbody>
              {n.truong.map((t: string) => <tr key={t}>
                <td style={{ width: 240 }}>{TEN_TRUONG[t] || t}</td>
                <td>
                  {t in hien ? <>{oGiaTri(hien[t])} <Tag cls="warn">đã vào nhật ký</Tag></>
                             : oGiaTri(d.ho_so[t])}
                  {/* Nút chỉ có ở nhóm máy chủ trả về dạng ĐÃ CHE. Nhóm bị từ chối không có
                      dòng nào ở đây để mà bấm, nhóm thấy thẳng thì không có gì để hiện. */}
                  {n.quyen === "che" && !(t in hien) && d.ho_so[t] !== null && d.ho_so[t] !== "" &&
                    <button className="act grey" style={{ margin: 0, marginLeft: 8, padding: "1px 8px" }}
                      disabled={dangHien === t}
                      title="Xem giá trị thật — lượt xem này vào nhật ký hồ sơ"
                      onClick={() => xinHien(t, TEN_TRUONG[t] || t)}>
                      {dangHien === t ? "…" : "Hiện"}
                    </button>}
                </td>
              </tr>)}
            </tbody></table></div>}
      </div>)}

      {/* HS-13 (Chủ tịch duyệt 20/10/2026): trường CÓ cửa nhập mà người này chưa có số — gom theo
          cửa, mỗi cửa một đường mở. Đây là việc của người nhập (HCNS…), không phải của phần mềm. */}
      {d.chua_co_so_lieu?.length > 0 && <div style={{ marginTop: 14, paddingTop: 10, borderTop: "1px solid var(--line, #2a3b55)" }}>
        <b style={{ fontSize: 13 }}>Người này chưa có số ở {d.chua_co_so_lieu.reduce((s: number, c: any) => s + c.truong.length, 0)} trường</b>
        <span className="muted" style={{ fontSize: 12 }}> — cửa nhập đã có:</span>
        {d.chua_co_so_lieu.map((c: any) => <p key={c.cua} className="muted" style={{ fontSize: 12, margin: "4px 0 0" }}>
          <b>{c.cua}</b> ({c.bo_phan}): {c.truong.map((t: string) => TEN_TRUONG[t] || t).join(", ")}{" · "}
          <a href={c.duong}>Mở {c.cua.toLowerCase()} →</a>
        </p>)}
      </div>}

      {/* CÁI CÒN THIẾU PHẢI HIỆN RA. Một ô trống trên màn hình trông y hệt một người chưa khai số
          liệu; danh sách này nói thẳng rằng hệ thống chưa có cửa nhập cho những trường ấy. */}
      {d.thieu_nguon?.length > 0 && <div style={{ marginTop: 14, paddingTop: 10, borderTop: "1px solid var(--line, #2a3b55)" }}>
        <b style={{ fontSize: 13 }}>Hệ thống chưa có cửa nhập cho {d.thieu_nguon.length} trường</b>
        <p className="muted" style={{ fontSize: 12, marginTop: 4 }}>
          Đây là việc còn thiếu của phần mềm, không phải người này chưa khai:{" "}
          {d.thieu_nguon.map((t: string) => TEN_TRUONG[t] || t).join(" · ")}
        </p>
      </div>}
    </>}
  </div>;
}
