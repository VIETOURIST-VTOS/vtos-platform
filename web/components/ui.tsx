export const Tag = ({ cls = "", children }: { cls?: string; children: React.ReactNode }) => <span className={"tag " + cls}>{children}</span>;
export const Gate = ({ ok, children }: { ok: boolean | null; children: React.ReactNode }) => <div className={"gate " + (ok === null ? "" : ok ? "pass" : "fail")}>{children}</div>;
export function errMsg(e: any): string { return e?.gate ? `CỔNG ${e.gate.replace("CONG_", "").replace(/_/g, "+")} – ${e.message}` : e?.message || "Có lỗi xảy ra"; }
