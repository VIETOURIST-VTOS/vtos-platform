"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, getUser } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** NHÂN VIÊN PHÒNG TÔI — lối vào hồ sơ cho người đứng đầu một phòng (đợt CUA-1, 22/10/2026).
 *
 *  VÌ SAO MÀN NÀY TỒN TẠI. Cửa `GET /api/v1/employees/phong-toi` có từ đợt HS-4, nhưng nút bấm duy
 *  nhất dẫn tới hồ sơ lại nằm trên màn quản trị Tài khoản — màn mà trưởng phòng không mở được.
 *  Quyền có, lối vào không. Chính ghi chú của cửa ấy nói ra: *"thiếu cửa này thì trưởng phòng chỉ
 *  mở được hồ sơ khi đã biết sẵn mã tài khoản, tức là trên thực tế họ không mở được."*
 *
 *  MÀN CHỈ XEM. Không có cửa ghi nào ở đây, và đó là CỐ Ý: hồ sơ nhân viên nhập ở Nhân sự. Khai
 *  trong nhóm `HO_SO_NGUOI` của `test_man_hinh_co_cua_nhap.py`, câu nhóm ấy phải trả lời là «số
 *  trên hồ sơ này vào hệ thống qua cửa nào của HCNS» — và màn hình nói thẳng câu ấy ở cuối trang,
 *  chứ không để người đọc tự đoán.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  KHÔNG KHOÁ CỨNG DANH SÁCH CỘT — đây là luật, không phải cách viết cho nhanh
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *
 *  Máy chủ cắt từng dòng qua `cat_ho_so_theo_vai`: vai nào thấy được trường nào thì trường ấy mới
 *  có trong phản hồi. Ghi chú của cửa dặn đúng chỗ này: *"danh sách KHÔNG có bảng cột riêng, vì
 *  bảng riêng bao giờ cũng là bảng rộng hơn."*
 *
 *  Nên màn hình dựng cột TỪ CHÍNH những khoá máy chủ trả về. Khoá cứng một danh sách cột là tự
 *  dựng một bảng rộng hơn phạm vi của vai: hôm nay nó hiện ô trống, ngày máy chủ nới một trường
 *  thì nó hiện luôn trường ấy cho mọi vai mà không ai khai gì.
 *
 *  LUẬT PHẠM VI PHẢI NÓI RA. Phản hồi mang `luat_pham_vi` để màn hình nói danh sách này dựa vào
 *  đâu: cây tổ chức Kinh doanh (có ngày hiệu lực) hay chỉ so tên phòng (luật yếu). Hai luật cho
 *  ra hai danh sách khác nhau, và một trưởng phòng đọc danh sách mà không biết nó dựng bằng luật
 *  nào thì không biết mình đang thiếu ai.
 */

const NHAN: Record<string, string> = {
  full_name: "Họ tên",
  code: "Mã nhân viên",
  role: "Vai",
  role_name: "Vai",
  department: "Phòng ban",
  position: "Chức danh",
  username: "Tài khoản",
  email: "Thư điện tử",
  phone: "Điện thoại",
  ngay_vao: "Ngày vào",
  ngay_nghi: "Ngày nghỉ",
  trang_thai: "Trạng thái",
  id: "#",
};

/* Thứ tự ưu tiên khi bày cột. Khoá nào máy chủ trả mà không có trong đây thì xuống cuối, theo
   đúng thứ tự máy chủ đưa — không bỏ, vì bỏ là giấu một trường vai ấy ĐƯỢC thấy. */
const THU_TU = ["code", "full_name", "role_name", "role", "position", "department",
                "username", "phone", "email", "ngay_vao", "trang_thai"];

const LUAT: Record<string, { chu: string; manh: boolean }> = {
  cay_kd: { chu: "cây tổ chức Kinh doanh, có ngày hiệu lực", manh: true },
  ngoai_cay: { chu: "ngoài cây tổ chức — ghép thêm theo phòng", manh: false },
  cung_phong_luat_yeu: { chu: "chỉ so tên phòng (luật yếu)", manh: false },
  chua_gan_phong: { chu: "người xem chưa được gắn phòng nào", manh: false },
};

function docLuat(ma: string) {
  if (!ma) return { chu: "máy chủ không nói rõ luật nào", manh: false };
  return LUAT[ma] || { chu: ma, manh: true };
}

function NhanVienPhongToi() {
  const { toast } = useShell();
  const [d, setD] = useState<any>(undefined);
  const vai = getUser();

  const nap = useCallback(async () => {
    try {
      setD(await api<any>("/employees/phong-toi"));
    } catch (e) {
      toast(errMsg(e), true);
      setD(null);
    }
  }, [toast]);
  useEffect(() => { nap(); }, [nap]);

  const nguoi: any[] = d?.nguoi || [];

  /* Cột dựng từ hợp của mọi khoá có mặt trong các dòng — không phải từ dòng đầu tiên: máy chủ cắt
     theo vai chứ không theo người, nhưng một dòng thiếu dữ liệu vẫn có thể thiếu khoá. */
  const khoa: string[] = (() => {
    const co = new Set<string>();
    nguoi.forEach((r) => Object.keys(r || {}).forEach((k) => co.add(k)));
    co.delete("id");
    const uu = THU_TU.filter((k) => co.has(k));
    const con = [...co].filter((k) => !uu.includes(k));
    return [...uu, ...con];
  })();

  const luat = docLuat(d?.luat_pham_vi || "");

  return (<>
    <h1>Nhân viên phòng tôi</h1>

    {d === undefined && <p className="muted">Đang tải…</p>}

    {d === null && <p className="panel">
      Không đọc được danh sách. Nếu vai của anh/chị không quản lý ai thì máy chủ trả 403 — màn này
      chỉ dành cho người đứng đầu một phòng.
    </p>}

    {d && d.duoc === false && <p className="panel">
      <b>{d.ly_do || "Vai này không quản lý ai"}.</b>{" "}
      <span className="muted">Màn này dành cho người đứng đầu một phòng. Vai hiện tại:{" "}
      {vai?.role_name || vai?.role || "—"}.</span>
    </p>}

    {d && d.duoc !== false && <>
      <div className="panel" style={{ display: "flex", gap: 18, flexWrap: "wrap", alignItems: "baseline" }}>
        <div>
          <div className="muted">Số người</div>
          <b style={{ fontSize: "calc(20/14*1rem)" }}>{d.so_nguoi ?? nguoi.length}</b>
        </div>
        <div style={{ minWidth: 0 }}>
          <div className="muted">Danh sách này dựng bằng luật nào</div>
          <b>{luat.chu}</b>{" "}
          {luat.manh ? <Tag cls="ok">luật mạnh</Tag> : <Tag cls="warn">luật yếu</Tag>}
          {!luat.manh && <div className="muted">
            Luật yếu thì danh sách có thể thiếu người: một chữ viết hoa lệch trong tên phòng là hai
            người khác phòng. Gắn người vào cây tổ chức Kinh doanh thì danh sách mới đủ.
          </div>}
        </div>
      </div>

      {nguoi.length ? <div className="wrap"><table>
        <thead><tr>
          {khoa.map((k) => <th key={k}>{NHAN[k] || k}</th>)}
          <th>Hồ sơ</th>
        </tr></thead>
        <tbody>{nguoi.map((r, i) => (
          <tr key={r.id ?? i}>
            {khoa.map((k) => (
              <td key={k}>
                {r[k] === null || r[k] === undefined || r[k] === ""
                  ? <span className="muted">—</span>
                  : String(r[k])}
              </td>
            ))}
            <td>
              {/* Người là hướng dẫn viên thì có trang hồ sơ riêng; người khác thì chưa có trang
                  riêng nào, và nói thẳng là chưa có hơn là dựng một liên kết chết. */}
              {r.position === "hdv"
                ? <a href={`/ho-so-hdv/${r.id}`} target="_blank" rel="noopener">Hồ sơ HDV →</a>
                : <span className="muted">—</span>}
            </td>
          </tr>))}</tbody>
      </table></div>
        : <p><Tag cls="warn">danh sách rỗng</Tag> Không có ai trong phạm vi của vai này.
          {!luat.manh && " Với luật yếu, rỗng chưa chắc là không có người — xem câu ở trên."}</p>}

      {/* CÂU TRẢ LỜI CHO NHÓM `HO_SO_NGUOI`: số trên màn này vào hệ thống qua cửa nào.
          In ra màn hình, không chỉ để trong khai báo phép thử — người đọc cần biết đi đâu để sửa. */}
      <h2>Số trên màn này sửa ở đâu</h2>
      <p className="muted">
        Màn này <b>chỉ xem</b>. Mọi trường ở trên nhập tại <b>Nhân sự → Hồ sơ nhân viên</b>; phòng
        ban và cấp trên gắn ở <b>Tổ chức Kinh doanh</b>. Không có cửa ghi ở đây là cố ý: thêm cửa
        ghi thứ hai cho cùng một dữ liệu là thêm một chỗ để hai bên ghi lệch nhau.
      </p>
    </>}
  </>);
}

export default function Page() { return <Shell><NhanVienPhongToi /></Shell>; }
