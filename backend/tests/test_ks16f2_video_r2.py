# -*- coding: utf-8 -*-
"""KS-16f2 · Tải video lên kho R2 (S3) — lỗi CRM 31/10/2026: bước «bắt đầu tải» trả 500, không lưu được video.

  R2 trả UploadId multipart dài hơn 300 ký tự → cột `ma_tai` (VARCHAR 300) tràn trên PostgreSQL. Cột đổi sang TEXT;
  lỗi lưu bản ghi thì bỏ phiên tải trên kho và báo rõ. Phép thử chạy cả đường S3 (client giả) từ đầu tới cuối.
  Đặt TEST_PG_URL để chạy trên PostgreSQL thật.
"""
import os

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

MB = 1024 * 1024
DAI = "R2" + "x" * 698          # UploadId 700 ký tự


class _R2Gia:
    def __init__(self):
        self.mo, self.phan, self.tep, self.huy = {}, {}, {}, []

    def create_multipart_upload(self, Bucket, Key, ContentType):
        self.mo[Key] = ContentType
        return {"UploadId": DAI}

    def upload_part(self, Bucket, Key, UploadId, PartNumber, Body):
        assert UploadId == DAI
        self.phan[(Key, PartNumber)] = Body
        return {"ETag": f'"et{PartNumber}"'}

    def complete_multipart_upload(self, Bucket, Key, UploadId, MultipartUpload):
        assert UploadId == DAI
        self.tep[Key] = b"".join(self.phan[(Key, p["PartNumber"])] for p in MultipartUpload["Parts"])

    def head_object(self, Bucket, Key):
        return {"ContentLength": len(self.tep[Key])}

    def abort_multipart_upload(self, Bucket, Key, UploadId):
        self.huy.append(Key)

    def generate_presigned_url(self, op, Params, ExpiresIn):
        return f"https://r2.example/{Params['Key']}?sig=1"

    def put_object(self, Bucket, Key, Body, ContentType):
        self.tep[Key] = Body


@pytest.fixture()
def db(monkeypatch):
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.models.core import User
    from app.services import nha_hang as N, storage as ST
    from tests.test_at1_am_thuc import HN
    kho = ST.S3Storage("vtos", "https://r2.example", "auto", "k", "s")
    kho._client = _R2Gia()
    ST._CACHE["s"] = kho
    url = os.environ.get("TEST_PG_URL", "")
    e = create_engine(url, future=True) if url else create_engine("sqlite://", future=True, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.drop_all(e)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("dh", "nv_dh"), ("tp", "tp_dh"), ("kd", "nv_kd")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x"))
    s.commit()
    monkeypatch.setattr(N, "_hom_nay", lambda: HN)
    s._kho = kho._client
    yield s
    s.close(); Base.metadata.drop_all(e); ST._CACHE.clear()


def _u(s, ten):
    from app.models.core import User
    return s.execute(select(User).where(User.username == ten)).scalars().one()


def test_tai_video_len_r2_ma_tai_dai(db):
    from app.services import video_dich_vu as V
    from tests.test_ks13_khach_san_vtd import _ks
    k = _ks(db)
    dh = _u(db, "dh")
    kt = 10 * MB
    v = V.bat_dau(db, dh, "khach_san_vtd", k.id, {"ten_tep": "Tong-quan.mp4", "kich_thuoc": kt, "thoi_luong": 30.03,
                                                 "nguon": "KS gửi", "xac_nhan_quyen": True, "loai": "tong_quan"})
    assert v.ma_tai == DAI and v.trang_thai == "dang_tai"
    V.nhan_phan(db, dh, v.id, 1, b"a" * V.PHAN_BYTE)
    V.nhan_phan(db, dh, v.id, 2, b"b" * (kt - V.PHAN_BYTE))
    v = V.xong(db, dh, v.id)
    assert v.trang_thai == "hien" and v.kich_thuoc == kt and v.la_gioi_thieu
    assert len(db._kho.tep[v.khoa_luu]) == kt and db._kho.mo[v.khoa_luu] == "video/mp4"
    ds = V.ds(db, dh, "khach_san_vtd", k.id)
    assert [x["id"] for x in ds["video"]] == [v.id] and ds["chuan"][0]["co"]
    from urllib.parse import parse_qs, urlparse
    t = parse_qs(urlparse(ds["video"][0]["xem"]).query).get("t", [""])[0]
    assert V.tep_xem(db, v.id, "khach_san_vtd", t)["url"].startswith("https://r2.example/video/khach_san_vtd/")


def test_luu_loi_thi_bo_phien_tai(db, monkeypatch):
    from app.services import video_dich_vu as V
    from tests.test_ks13_khach_san_vtd import _ks
    k = _ks(db)
    dh = _u(db, "dh")
    goc = db.commit
    monkeypatch.setattr(db, "commit", lambda: (_ for _ in ()).throw(RuntimeError("hỏng")))
    with pytest.raises(V.LoiVideo, match="RuntimeError") as e:
        V.bat_dau(db, dh, "khach_san_vtd", k.id, {"ten_tep": "a.mp4", "kich_thuoc": MB, "nguon": "x", "xac_nhan_quyen": True})
    assert e.value.status == 500 and len(db._kho.huy) == 1
    monkeypatch.setattr(db, "commit", goc)
