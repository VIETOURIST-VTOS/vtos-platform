"use client";
import Shell from "@/components/Shell";
import { DeNghiMua } from "@/components/DeNghiMuaCapPhat";

/** 5.9.2 Đề nghị mua — màn hình riêng, dựng 09/10/2026.
 *
 *  VÌ SAO KHÔNG GẮN VÀO /tai-san: người đề nghị mua là người của MỌI phòng, còn /tai-san chỉ mở cho
 *  Kế toán, CNTT, hành chính và HCNS. Gắn vào đó thì chín phòng còn lại không có đường gửi và họ sẽ
 *  nhắn Zalo như hôm nay. Cửa mở mà người không với tới thì cửa ấy chưa tồn tại.
 *
 *  Mở MÀN HÌNH rộng không phải mở QUYỀN: duyệt vẫn chỉ TGĐ / Chủ tịch, ghi đã chi vẫn chỉ Kế toán —
 *  chặn ở tầng dịch vụ, và mỗi chỗ chặn có một phép thử gọi sai vai để chắc nó trả 403.
 */
export default function Page() { return <Shell><DeNghiMua /></Shell>; }
