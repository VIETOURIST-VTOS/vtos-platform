"use client";
/** TRANG PHÂN HỆ – anh Tuấn chốt phương án B ngày 13/9/2026.
 *
 *  Bấm một thanh phân hệ trên menu dọc thì mở trang này: mục lục đầy đủ của phân hệ ấy theo bản vẽ
 *  "VTOS · Cấu trúc phân hệ đề xuất V1.3", mỗi mục ghi rõ ĐÃ CÓ TRANG hay CHƯA DỰNG.
 *
 *  VÌ SAO KHÔNG NHỒI CÂY NÀY VÀO MENU: v1.3 sâu bốn cấp và liệt kê 184 mục, VTOS thật có 62 trang.
 *  Menu chốt tối đa hai cấp (§I.2). Nhồi vào là vừa phá đặc tả vừa dựng hơn một trăm đường dẫn hỏng;
 *  ẩn phần chưa dựng đi thì không ai còn thấy hệ thống đang nợ những gì. Trang này giải cả hai.
 *
 *  RANH GIỚI 09/9 VẪN NGUYÊN: trang chỉ đọc CẤU TRÚC từ web/lib/cay_phan_he.ts, không gọi máy chủ,
 *  không hiển thị một con số nghiệp vụ nào. Nó là mục lục, không phải báo cáo.
 */
import Link from "next/link";
import { useParams } from "next/navigation";
import Shell, { useShell } from "@/components/Shell";
import { CAY_PHAN_HE, PHAN_HE_CON, timPhanHe, demMuc, laNhan, type MucCay } from "@/lib/cay_phan_he";

/** TC-70 · 18/9/2026 — DANH SÁCH CHIP CHUYỂN NHANH phải khớp với thanh dọc, không phải với
 *  CAY_PHAN_HE. Từ 18/9 Kinh doanh và Điều hành không còn là một màn hình: chúng xổ ra 2 và 3 phân
 *  hệ con. Nếu chip vẫn liệt kê hai phân hệ cha thì người đang đứng ở "Điều hành xe" nhìn xuống
 *  không thấy chip nào sáng, và bấm chip "Điều hành" lại rơi về mục lục gộp mà menu đã bỏ.
 *
 *  Phân hệ cha nào CÓ con thì thay bằng các con, giữ đúng thứ tự cha; cha nào không có con thì để
 *  nguyên. Nhờ vậy thêm hay bớt một phân hệ con sau này chỉ phải sửa PHAN_HE_CON, không phải sửa
 *  chỗ này. */
const CHIP_PHAN_HE = CAY_PHAN_HE.flatMap((p) => {
  const con = PHAN_HE_CON.filter((c) => c.cha === p.khoa);
  return con.length
    ? con.map((c) => ({ khoa: c.khoa, ma: p.ma, ten: c.ten }))
    : [{ khoa: p.khoa, ma: p.ma, ten: p.ten }];
});

/** `khoa` là trạng thái CỦA PHIÊN NÀY, không phải thuộc tính của cây – nên nó sống ở đây chứ không
 *  vào cay_phan_he.ts. Cùng một mục, người này khoá người kia mở. */
type MucKhoa = MucCay & { khoa?: boolean; con?: MucKhoa[] };

/** Một dòng của cây. Mục có đường dẫn thì cả dòng bấm được; mục chưa dựng vẫn hiện đủ mã và tên –
 *  đó là phần việc còn nợ, giấu đi thì không ai đòi. */
function Dong({ m, cap }: { m: MucKhoa; cap: number }) {
  const noi = m.tab || m.khoa ? null : m.href;
  const than = (
    <>
      <span className="cay-ma">{m.ma}</span>
      <span className="cay-ten">{m.ten}</span>
      {m.them && <span className="cay-co them">ngoài v1.3</span>}
      {m.chuyen && <span className="cay-co chuyen">mã v1.3: {m.ma}</span>}
      {/* TC-70 · 18/9/2026: nhánh này còn nằm ở phân hệ con anh em. Nói ra chứ không để người đọc
          tưởng màn hình ấy của riêng phòng mình – hộp thư và hồ sơ khách là của cả hai phòng bán
          hàng, sửa ở đây thì bên kia thấy ngay. */}
      {m.chung && <span className="cay-co chung">dùng chung</span>}
      {m.tab ? <span className="cay-tt tab">Tab trong trang</span>
        : m.khoa ? <span className="cay-tt cam">Không có quyền</span>
          : m.href ? <span className="cay-tt co">Đã có →</span>
            : laNhan(m) ? <span className="cay-tt nhan">Nhóm chức năng</span>
              : <span className="cay-tt chua">Chưa dựng</span>}
    </>
  );
  return (
    <>
      {noi
        ? <Link href={noi} className={"cay-dong co cap" + cap}>{than}</Link>
        : <div className={"cay-dong cap" + cap + (m.khoa ? " cam" : "")}>{than}</div>}
      {m.con?.map((c) => <Dong key={c.ma} m={c} cap={cap + 1} />)}
    </>
  );
}

/** KHOÁ, KHÔNG GIẤU (anh Tuấn chốt 13/9/2026, áp dụng cho MỌI vai trò kể cả tài xế, hướng dẫn viên
 *  và chuyên viên visa). Mục nào vai trò này không có quyền thì vẫn hiện đủ mã và tên, nhưng xám và
 *  không bấm được.
 *
 *  Vì sao không giấu: giấu thì nhân viên không biết hệ thống có những gì, và khi cần thì không biết
 *  phải xin quyền ở đâu – họ tưởng phần mềm chưa làm chức năng ấy. Cái lộ ra ở đây là TÊN chức
 *  năng, không phải số liệu; trang này không gọi máy chủ và không hiện một con số nghiệp vụ nào. */
function khoaTheoQuyen(ds: MucCay[], an: string[]): MucKhoa[] {
  const cam = (h?: string) => !!h && an.includes(h.split("?")[0].split("#")[0]);
  return ds.map((m) => ({
    ...m,
    khoa: cam(m.href) || undefined,
    con: m.con ? khoaTheoQuyen(m.con, an) : undefined,
  }));
}

function Trang({ khoa }: { khoa: string }) {
  const { user } = useShell();
  const an = user?.hidden_menus || [];
  const goc = timPhanHe(khoa);
  const ph = goc ? { ...goc, con: khoaTheoQuyen(goc.con, an) } : undefined;
  if (!ph) return (
    <div className="panel">
      <b>Không có phân hệ này.</b>
      <p className="muted">Đường dẫn /phan-he/{khoa} không khớp phân hệ nào của VTOS – cả tám phân hệ
        chính lẫn năm phân hệ con (Kinh doanh lẻ, Kinh doanh đoàn, Điều hành tour, Điều hành xe,
        Hướng dẫn viên).</p>
      <Link href="/">Về bảng điều hành</Link>
    </div>
  );
  const d = demMuc(ph.con);
  return (
    <>
      {/* Chuyển nhanh sang phân hệ khác mà không phải quay lên menu dọc. */}
      <nav className="cay-chuyen" aria-label="Các phân hệ khác">
        {CHIP_PHAN_HE.map((p) => (
          <Link key={p.khoa} href={`/phan-he/${p.khoa}`}
            className={"cay-chip" + (p.khoa === ph.khoa ? " on" : "")}>
            <b>{p.ma}</b> {p.ten}
          </Link>
        ))}
      </nav>

      <header className="cay-dau">
        <div className="cay-dau-ma">{ph.ma}</div>
        <div>
          <h1>{ph.ten}</h1>
          <p className="cay-tom">{ph.tom_tat}</p>
        </div>
        <div className="cay-dem">
          <b>{d.co}/{d.tong}</b>
          <span>màn hình đã dựng</span>
        </div>
      </header>

      <p className="cay-chu">
        Mục lục chức năng theo bản vẽ <b>Cấu trúc phân hệ V1.3</b> (12/9/2026). Mục ghi <b>Đã có</b>
        {" "}bấm vào là mở màn hình thật; mục ghi <b>Chưa dựng</b> là phần còn nợ, chưa có trang trong
        VTOS. Dòng ghi <b>Tab trong trang</b> là tab bên trong một màn hình, và <b>Nhóm chức năng</b>
        {" "}là nhãn gom nhóm – cả hai đều không tính vào số màn hình.
      </p>
      <p className="cay-chu">
        Mục ghi <b>Không có quyền</b> là màn hình đã có, nhưng vai trò của bạn chưa được mở. Xin quyền
        ở <b>Quản trị hệ thống → Tài khoản & phân quyền</b>; số màn hình đã dựng ở trên đếm cả những
        mục ấy, vì chúng tồn tại thật.
      </p>

      <div className="cay">
        {ph.con.map((m) => <Dong key={m.ma} m={m} cap={0} />)}
      </div>

      <p className="muted cay-cuoi">
        Trang này là MỤC LỤC cấu trúc, không phải báo cáo – không có số liệu nghiệp vụ nào ở đây.
        Số liệu nằm trong từng màn hình, và mỗi con số đều phải có một cửa nhập hoặc cửa tải cho bộ
        phận phụ trách.
      </p>
    </>
  );
}

/** Lấy khoá bằng useParams chứ không nhận qua tham số `params`: Next 15 đổi `params` thành Promise
 *  còn Next 14 thì không, và trang này là client component nên useParams chạy đúng ở cả hai. */
export default function Page() {
  const p = useParams<{ khoa: string }>();
  return <Shell><Trang khoa={String(p?.khoa || "")} /></Shell>;
}
