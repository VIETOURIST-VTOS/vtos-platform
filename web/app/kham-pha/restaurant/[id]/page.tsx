"use client";
// KS-16q · kh.vietourist.vn/restaurant/<id> — mở thẳng một mục, đường dẫn chia sẻ được.
import TrangRieng from "@/components/cong/TrangRieng";

export default function Trang({ params }: { params: { id: string } }) { return <TrangRieng dang="restaurant" id={params.id} />; }
