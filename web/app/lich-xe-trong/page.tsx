"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";
import { errMsg } from "@/components/ui";

/** LỊCH XE TRỐNG ĐỂ BÁN — màn của phòng Kinh doanh. Đợt XE-KD-1 · 11/11/2026, Chủ tịch duyệt.
 *
 *  ═══ VÌ SAO CÓ MÀN NÀY, VÀ VÌ SAO NÓ KHÔNG PHẢI MỘT DÒNG KHAI QUYỀN ════════════════════════
 *  Làn Phân quyền gửi sang: «cửa /khoang-trong đã có (PR #784), chỉ cần khai cho gd_kd và tp_kd
 *  trong access.py». Nhưng hàng rào `test_p11` của kho đòi: khai quyền cho một màn hình thì màn
 *  hình ấy PHẢI TỒN TẠI. Hàng rào ấy dựng ngày 08/9/2026 sau đúng một chuyện: một chức năng được
 *  khai quyền đầy đủ, 19 phép thử xanh, mà người dùng không có đường vào. Nên việc này là dựng
 *  một màn hình thật, và đây là nó.
 *
 *  ═══ CHỈ XEM, VÀ CHỈ MỘT CỬA ══════════════════════════════════════════════════════════════
 *  Màn này gọi ĐÚNG MỘT đường: `/fleet/lich-xe-tuong-lai/khoang-trong`. Cổng phân quyền của kho
 *  chặn theo TIỀN TỐ đường dẫn, nên khai `/api/v1/fleet` như các màn đội xe đang khai là mở toàn
 *  bộ API đội xe — lãi lỗ, chi phí, tài xế — cho phòng Kinh doanh. Trái hẳn điều Chủ tịch chốt:
 *  «chỉ xem khoảng trống và công suất tuần, không xem lưới xe/tour». Nên `access.py` khai đúng
 *  một tiền tố dài, và màn này cũng chỉ gọi đúng một cửa ấy.
 *
 *  ═══ KHÔNG CÓ CỬA NHẬP, VÀ CHỈ ĐƯỢC RA ĐƯỢC TỪNG CỬA ══════════════════════════════════════
 *  Mọi con số dưới đây đã có sẵn trong hệ thống, không ai phải gõ thêm. Cửa nhập của từng thứ
 *  nằm ở màn của ĐỘI XE, không ở đây, và nói ra chỗ của chúng là điều kiện để màn này được khai
 *  vào nhóm «chỉ xem» của `test_man_hinh_co_cua_nhap`:
 *
 *      ngày có lệnh   ← Lệnh điều xe       · cửa: Điều hành → Lệnh điều xe → Lập lệnh
 *      đề nghị chờ    ← Đề nghị xe         · cửa: Điều hành → Lệnh điều xe → Đề nghị xe
 *      xe bị chặn     ← Báo hỏng phải dừng · cửa: Đội xe → tab Báo hỏng
 *      số chỗ, biển   ← Hồ sơ xe           · cửa: Đội xe → Hồ sơ xe
 *
 *  ═══ CHƯA XÁC ĐỊNH ≠ 0 ════════════════════════════════════════════════════════════════════
 *  Máy chủ trả `cong_suat = null` khi không có xe khả dụng nào để làm mẫu số. In «0%» vào chỗ ấy
 *  là nói với người bán rằng tuần ấy trống trơn — trong khi sự thật là chưa tính được. Luật này
 *  của kho đã cứu tháng 10 hai lần (KS-36, KS-41), nên màn này giữ đúng nó.
 */

type Khoang = { xe: string; so_cho: number; tu: string; den: string; so_ngay: number; cuoi_tuan: boolean };
type Tuan = { tu: string; den: string; nhan: string; cong_suat: number | null };
type So = { tu: string; den: string; khoang_trong: Khoang[]; tuan: Tuan[];
            nguong_thap: number; cong_suat_30: number | null };

const ngay = (s: string) => {
  const d = new Date(s);
  return isNaN(d.getTime()) ? s : `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}`;
};

/** Nhãn dùng chung cho mọi chỗ máy chủ trả `null`. Không bao giờ in 0 vào đây. */
const ChuaXacDinh = () => (
  <span className="tag" style={{ background: "#fdf6e7", color: "#a66a00", fontWeight: 700 }}>
    CHƯA XÁC ĐỊNH
  </span>
);

function LichXeTrong() {
  const [d, setD] = useState<So | null>(null);
  const [loi, setLoi] = useState("");
  const [dang, setDang] = useState(true);

  useEffect(() => {
    api("/fleet/lich-xe-tuong-lai/khoang-trong")
      .then((r: any) => setD(r))
      .catch((e) => setLoi(errMsg(e)))
      .finally(() => setDang(false));
  }, []);

  return (<>
    <h1>Lịch xe trống để bán</h1>
    <p className="muted">
      Xe nào còn trống trong 90 ngày tới, và tuần nào công suất thấp — để phòng Kinh doanh đẩy bán
      đúng chỗ. Màn này CHỈ XEM: không có lưới xe theo tour, không có giá, không có chi phí.
    </p>

    {dang && <p className="muted">Đang đọc số…</p>}

    {loi && <div className="panel">
      <p style={{ color: "var(--red)", marginTop: 0 }}><b>Không đọc được số.</b> {loi}</p>
      <p className="muted" style={{ marginBottom: 0 }}>
        Nếu báo thiếu quyền, xin quyền ở <b>Quản trị hệ thống → Tài khoản &amp; phân quyền</b>.
        Đây không phải lỗi hệ thống và cũng không phải màn hình chưa dựng.
      </p>
    </div>}

    {d && <>
      <section className="panel">
        <h2 style={{ marginTop: 0 }}>Công suất 30 ngày tới</h2>
        <p style={{ fontSize: 34, fontWeight: 700, margin: "4px 0", color: "var(--navy)" }}>
          {d.cong_suat_30 === null ? <ChuaXacDinh /> : `${d.cong_suat_30}%`}
        </p>
        <p className="muted" style={{ marginBottom: 0 }}>
          Ngày-xe đã có lệnh chia cho ngày-xe khả dụng, từ {ngay(d.tu)} đến {ngay(d.den)}.
          Xe đang có báo hỏng «phải dừng xe» không nằm trong mẫu số, và cũng không được tính là
          trống ngày nào — chưa biết ngày sửa xong thì không ai bán được nó.
        </p>
      </section>

      <section className="panel">
        <h2 style={{ marginTop: 0 }}>Công suất từng tuần</h2>
        <p className="muted">
          Tuần dưới {d.nguong_thap}% tô vàng: còn nhiều chỗ để đẩy bán.
        </p>
        <div style={{ overflowX: "auto" }}>
          <table><thead><tr>
            <th>Tuần</th><th>Từ</th><th>Đến</th><th className="num">Công suất</th>
          </tr></thead><tbody>
            {d.tuan.map((t) => {
              const thap = t.cong_suat !== null && t.cong_suat < d.nguong_thap;
              return <tr key={t.nhan + t.tu} style={thap ? { background: "#fdf6e7" } : undefined}>
                <td><b>{t.nhan}</b></td>
                <td>{ngay(t.tu)}</td>
                <td>{ngay(t.den)}</td>
                <td className="num">{t.cong_suat === null ? <ChuaXacDinh /> : `${t.cong_suat}%`}</td>
              </tr>;
            })}
          </tbody></table>
        </div>
      </section>

      <section className="panel">
        <h2 style={{ marginTop: 0 }}>Khoảng trống từ 2 ngày liền trở lên</h2>
        {d.khoang_trong.length === 0
          ? <p className="muted">Không có khoảng trống nào từ 2 ngày trở lên trong 90 ngày tới.</p>
          : <>
            <p className="muted">
              {d.khoang_trong.length} khoảng. Khoảng có cuối tuần đánh dấu riêng — đó là chỗ tour
              ngắn bán chạy nhất.
            </p>
            <div style={{ overflowX: "auto" }}>
              <table><thead><tr>
                <th>Xe</th><th className="num">Số chỗ</th><th>Từ</th><th>Đến</th>
                <th className="num">Số ngày</th><th>Cuối tuần</th>
              </tr></thead><tbody>
                {d.khoang_trong.map((k, i) => (
                  <tr key={`${k.xe}-${k.tu}-${i}`}>
                    <td><b>{k.xe}</b></td>
                    <td className="num">{k.so_cho}</td>
                    <td>{ngay(k.tu)}</td>
                    <td>{ngay(k.den)}</td>
                    <td className="num">{k.so_ngay}</td>
                    <td>{k.cuoi_tuan ? "có" : ""}</td>
                  </tr>))}
              </tbody></table>
            </div>
          </>}
      </section>

      <p className="muted">
        Số ở đây đọc từ lệnh điều xe, đề nghị xe, báo hỏng và hồ sơ xe — không ai nhập tay vào màn
        này. Sai số thì sửa ở cửa gốc của nó bên Đội xe và Điều hành, sửa ở đây là dựng bản thứ hai
        để hai nơi lệch nhau.
      </p>
    </>}
  </>);
}

export default function Page() { return <Shell><LichXeTrong /></Shell>; }
