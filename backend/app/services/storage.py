"""Lưu trữ tệp hồ sơ (tài liệu Visa) – một lớp mỏng, hai nền: thư mục cục bộ và kho đối tượng S3.

Vì sao có tệp này: ổ đĩa của Render là TẠM, deploy lại là mất. Hộ chiếu và sao kê của khách không được phép
nằm trên chỗ có thể bốc hơi. Chủ tịch chọn phương án kho đối tượng (Cloudflare R2 / Amazon S3) ngày 06/9/2026.

Nguyên tắc:
  - Gọi ở một chỗ duy nhất (app/services/visa.py) nên sau này đổi nền lưu trữ không phải sờ vào nghiệp vụ.
  - Đường dẫn (khóa) do hệ thống sinh từ id + băm nội dung, KHÔNG lấy theo tên tệp khách đặt.
  - Đọc ra luôn ĐỐI CHIẾU LẠI sha256 đã ghi trong CSDL. Tệp mất hay bị đổi thì báo lỗi rõ, không im lặng
    trả về nội dung sai – kế toán và hồ sơ pháp lý không chấp nhận dữ liệu "gần đúng".
  - `durable` cho biết nền hiện tại có bền vững qua lần deploy sau không, để giao diện cảnh báo được.
"""
import hashlib
import os
from dataclasses import dataclass
from app.core.config import settings


class StorageError(RuntimeError):
    """Lỗi tầng lưu trữ – tách khỏi lỗi nghiệp vụ để API trả đúng mã và thông điệp."""


@dataclass
class Stored:
    key: str
    size: int
    checksum: str


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class LocalStorage:
    """Thư mục trên máy đang chạy. Dùng cho máy lập trình và cho kiểm thử.

    KHÔNG bền vững trên Render: mỗi lần deploy là một máy mới, thư mục cũ biến mất."""
    kind = "local"
    durable = False

    def __init__(self, root: str):
        self.root = root or os.path.join(os.getcwd(), "visa_docs")
        os.makedirs(self.root, exist_ok=True)

    def _path(self, key: str) -> str:
        return os.path.join(self.root, key.replace("/", "_"))

    def put(self, key: str, data: bytes, content_type: str = "") -> Stored:
        with open(self._path(key), "wb") as f:
            f.write(data)
        return Stored(key=key, size=len(data), checksum=_sha(data))

    def get(self, key: str) -> bytes:
        try:
            with open(self._path(key), "rb") as f:
                return f.read()
        except OSError as ex:
            raise StorageError(f"Không đọc được tệp đã lưu ({ex.__class__.__name__})")

    def exists(self, key: str) -> bool:
        return os.path.exists(self._path(key))

    # ── KS-16f: tải tệp lớn (video) theo từng phần — bộ nhớ máy chủ chỉ giữ MỘT phần mỗi lần ──────────
    def mp_bat_dau(self, key: str, content_type: str = "") -> str:
        return "local"

    def mp_phan(self, key: str, upload_id: str, so: int, data: bytes) -> str:
        with open(self._path(key) + f".phan{so:05d}", "wb") as f:
            f.write(data)
        return hashlib.md5(data).hexdigest()

    def mp_xong(self, key: str, upload_id: str, phan: list[tuple[int, str]]) -> int:
        tong = 0
        with open(self._path(key), "wb") as out:
            for so, _etag in sorted(phan):
                pp = self._path(key) + f".phan{so:05d}"
                with open(pp, "rb") as f:
                    while True:
                        b = f.read(1 << 20)
                        if not b:
                            break
                        out.write(b); tong += len(b)
                os.remove(pp)
        return tong

    def mp_huy(self, key: str, upload_id: str) -> None:
        d = os.path.dirname(self._path(key)); goc = os.path.basename(self._path(key))
        for f in os.listdir(d):
            if f.startswith(goc + ".phan"):
                os.remove(os.path.join(d, f))

    def duong_tep(self, key: str) -> str:
        """Đường dẫn trên đĩa — để phát video có hỗ trợ tua (Range)."""
        return self._path(key)

    def link_tam(self, key: str, giay: int = 3600, kieu: str = "") -> str | None:
        return None

    def xoa(self, key: str) -> None:
        try:
            os.remove(self._path(key))
        except OSError:
            pass

    def describe(self) -> dict:
        return {"kind": self.kind, "durable": False, "noi_luu": self.root,
                "canh_bao": "Đang lưu vào thư mục của máy chủ. Trên Render thư mục này MẤT sau mỗi lần "
                            "deploy – chỉ dùng để chạy thử, không dùng cho tài liệu thật của khách."}


class S3Storage:
    """Kho đối tượng theo chuẩn S3: Cloudflare R2, Amazon S3, Backblaze B2…

    Cùng một giao thức nên đổi nhà cung cấp chỉ là đổi endpoint và khóa, không phải sửa mã nguồn."""
    kind = "s3"
    durable = True

    def __init__(self, bucket: str, endpoint: str = "", region: str = "auto",
                 key_id: str = "", secret: str = ""):
        self.bucket, self.endpoint, self.region = bucket, endpoint, region or "auto"
        self._key_id, self._secret = key_id, secret
        self._client = None

    @property
    def client(self):
        """Dựng client ở lần dùng ĐẦU TIÊN, không dựng lúc khởi động.

        Đo trên máy này: import boto3 tốn 25 MB, tạo client thêm 15 MB – tổng 40 MB, đúng 8% của máy 512 MB.
        Phần lớn yêu cầu vào VTOS không đụng tới tệp nào, nên không có lý do bắt cả hệ thống gánh 40 MB đó
        từ lúc khởi động. Máy càng sát ngưỡng thì mỗi chục MB tiết kiệm được càng đáng giá cho thao tác nặng
        của phân hệ khác."""
        if self._client is None:
            try:
                import boto3
                from botocore.config import Config
            except ImportError:  # pragma: no cover - chỉ xảy ra khi thiếu thư viện
                raise StorageError("Thiếu thư viện boto3 – thêm vào requirements.txt rồi deploy lại")
            # R2 chỉ chấp nhận chữ ký phiên bản 4 và region "auto"; cấu hình này cũng đúng với Amazon S3.
            self._client = boto3.client(
                "s3", endpoint_url=self.endpoint or None, region_name=self.region,
                aws_access_key_id=self._key_id or None, aws_secret_access_key=self._secret or None,
                config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}))
        return self._client

    def put(self, key: str, data: bytes, content_type: str = "") -> Stored:
        try:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=data,
                                   ContentType=content_type or "application/octet-stream")
        except Exception as ex:
            raise StorageError(f"Không ghi được lên kho lưu trữ: {ex}")
        return Stored(key=key, size=len(data), checksum=_sha(data))

    def get(self, key: str) -> bytes:
        try:
            return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except Exception as ex:
            raise StorageError(f"Không đọc được tệp trên kho lưu trữ: {ex}")

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    # ── KS-16f: multipart S3 — mỗi phần ≥5 MB (trừ phần cuối); bộ nhớ chỉ giữ một phần ─────────────────
    def mp_bat_dau(self, key: str, content_type: str = "") -> str:
        try:
            return self.client.create_multipart_upload(Bucket=self.bucket, Key=key,
                                                       ContentType=content_type or "application/octet-stream")["UploadId"]
        except Exception as ex:
            raise StorageError(f"Không mở được phiên tải lên kho lưu trữ: {ex}")

    def mp_phan(self, key: str, upload_id: str, so: int, data: bytes) -> str:
        try:
            return self.client.upload_part(Bucket=self.bucket, Key=key, UploadId=upload_id, PartNumber=so, Body=data)["ETag"]
        except Exception as ex:
            raise StorageError(f"Không ghi được phần {so} lên kho lưu trữ: {ex}")

    def mp_xong(self, key: str, upload_id: str, phan: list[tuple[int, str]]) -> int:
        try:
            self.client.complete_multipart_upload(Bucket=self.bucket, Key=key, UploadId=upload_id,
                                                  MultipartUpload={"Parts": [{"PartNumber": so, "ETag": et} for so, et in sorted(phan)]})
            return int(self.client.head_object(Bucket=self.bucket, Key=key)["ContentLength"])
        except Exception as ex:
            raise StorageError(f"Không ghép được tệp trên kho lưu trữ: {ex}")

    def mp_huy(self, key: str, upload_id: str) -> None:
        try:
            self.client.abort_multipart_upload(Bucket=self.bucket, Key=key, UploadId=upload_id)
        except Exception:
            pass

    def duong_tep(self, key: str) -> str | None:
        return None

    def link_tam(self, key: str, giay: int = 3600, kieu: str = "") -> str | None:
        """Đường xem tạm có chữ ký (hết hạn sau `giay`) — trình duyệt phát / tua thẳng từ kho, máy chủ không gánh băng thông."""
        try:
            p = {"Bucket": self.bucket, "Key": key}
            if kieu:
                p["ResponseContentType"] = kieu
            return self.client.generate_presigned_url("get_object", Params=p, ExpiresIn=giay)
        except Exception as ex:
            raise StorageError(f"Không tạo được đường xem video: {ex}")

    def xoa(self, key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except Exception:
            pass

    def describe(self) -> dict:
        # CỐ Ý không chạm tới self.client: xem tình trạng kho không được kéo theo 40 MB thư viện.
        return {"kind": self.kind, "durable": True,
                "noi_luu": f"{self.endpoint or 'AWS S3'} / {self.bucket}", "canh_bao": ""}


def build_storage():
    """Chọn nền lưu trữ theo cấu hình. Khai đủ bucket + khóa thì dùng kho đối tượng, không thì dùng thư mục."""
    mode = (getattr(settings, "VISA_STORAGE", "") or "auto").lower()
    bucket = getattr(settings, "S3_BUCKET", "") or ""
    key_id = getattr(settings, "S3_ACCESS_KEY_ID", "") or ""
    secret = getattr(settings, "S3_SECRET_ACCESS_KEY", "") or ""
    want_s3 = mode == "s3" or (mode == "auto" and bucket and key_id and secret)
    if want_s3:
        if not (bucket and key_id and secret):
            raise StorageError("Đặt VISA_STORAGE=s3 thì phải có đủ S3_BUCKET, S3_ACCESS_KEY_ID, "
                               "S3_SECRET_ACCESS_KEY")
        return S3Storage(bucket, getattr(settings, "S3_ENDPOINT_URL", "") or "",
                         getattr(settings, "S3_REGION", "auto") or "auto", key_id, secret)
    return LocalStorage(getattr(settings, "VISA_DOC_DIR", "") or "")


_CACHE = {}


def storage():
    """Một thể hiện dùng chung cho cả tiến trình (client S3 giữ sẵn kết nối, tạo mới mỗi lần rất tốn)."""
    if "s" not in _CACHE:
        _CACHE["s"] = build_storage()
    return _CACHE["s"]


def reset_storage():
    """Dùng trong kiểm thử khi đổi cấu hình giữa chừng."""
    _CACHE.clear()


def doc_key(case_id: int, doc_id: int, checksum: str) -> str:
    """Khóa lưu tệp. Không lấy tên tệp khách đặt làm định danh, và không đoán được khóa của hồ sơ khác."""
    return f"visa/{case_id}/{doc_id}-{checksum[:16]}"


def put_document(case_id: int, doc_id: int, data: bytes, content_type: str = "") -> Stored:
    return storage().put(doc_key(case_id, doc_id, _sha(data)), data, content_type)


def get_document(key: str, expected_checksum: str = "") -> bytes:
    """Đọc tệp và ĐỐI CHIẾU băm. Lệch băm nghĩa là tệp đã bị đổi hoặc lẫn – dừng lại chứ không trả về."""
    data = storage().get(key)
    if expected_checksum and _sha(data) != expected_checksum:
        raise StorageError("Nội dung tệp không khớp mã kiểm tra đã ghi khi nộp – tệp có thể đã bị thay đổi "
                           "hoặc lẫn với tệp khác. Không trả về nội dung này.")
    return data
