# -*- coding: utf-8 -*-
"""CN-1 · Bước dùng chung cho các phép thử chạy chuỗi bảng lương.

Từ 21/10/2026 phòng chưa được duyệt công thì bảng lương CHẶN. Phép thử nào muốn đi hết chuỗi lương
phải đi qua đúng hai bước thật — HCNS xác nhận, TGĐ duyệt — bằng chính cửa HTTP, không chèn dòng
vào bảng: chèn dòng thì phép thử xanh cả khi cửa hỏng.
"""


def duyet_cong(client, period, login, hcns="hcns", duyet="tgd"):
    r = client.get("/api/v1/attendance/xac-nhan-cong", params={"period": period}, headers=login(hcns))
    assert r.status_code == 200, r.text
    for k in r.json()["phong"]:
        if k["trang_thai"] == "da_duyet":
            continue
        a = client.post(f"/api/v1/attendance/xac-nhan-cong/{period}/{k['phong']}/hcns", headers=login(hcns))
        assert a.status_code == 200, a.text
        b = client.post(f"/api/v1/attendance/xac-nhan-cong/{period}/{k['phong']}/duyet", headers=login(duyet))
        assert b.status_code == 200, b.text
