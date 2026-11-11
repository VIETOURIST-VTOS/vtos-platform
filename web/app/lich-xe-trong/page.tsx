"use client";
import Shell from "@/components/Shell";
import LichXe90 from "@/components/doixe/LichXe90";

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

 *
 *  ═══ VH-17 · 11/11/2026 — NAY LÀ «LỊCH XE 90 NGÀY» CHO LÃNH ĐẠO VÀ TRƯỞNG PHÒNG ══════════════════
 *  Chủ tịch duyệt bản xem trước: lịch xe «theo lịch xe 90 ngày của GĐ đội xe», mở từ nút vàng NHỎ trên
 *  thanh ngang ở mọi bàn làm việc của Chủ tịch, TGĐ, P.TGĐ, GĐ KD và các trưởng phòng. Màn này nay vẽ
 *  ĐÚNG thành phần `LichXe90` của /xe (một lưới, một phép tính ở máy chủ, không vẽ lần hai) — gồm lưới
 *  xe × ngày, khoảng trống và công suất tuần. Cửa đọc nới từ `/khoang-trong` lên `/lich-xe-tuong-lai`
 *  (vẫn MỘT tiền tố, không mở cả `/api/v1/fleet`). Điều Chủ tịch chốt ở XE-KD-1 «không xem tour» vẫn
 *  giữ: tên tour trên ô Sheet chỉ trả cho vai đội xe — máy chủ cắt (fleet.lich_xe_tuong_lai), không giấu
 *  ở đây. «Giữ xe cho tour» chỉ hiện với vai gửi được đề nghị xe (máy chủ trả lời ở /de-nghi-xe/meta).
 */

export default function Page() {
  return <Shell>
    <section className="panel">
      <LichXe90 mo={(toi) => window.location.assign(toi)} />
    </section>
  </Shell>;
}
