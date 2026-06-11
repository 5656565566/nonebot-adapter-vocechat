from collections import OrderedDict

from nonebot.utils import logger_wrapper

log = logger_wrapper("vocechat")

class MessageCache:
    def __init__(self, max_size):
        """
        初始化消息缓存

        参数:
            max_size (int): 缓存的最大容量
        """
        if max_size <= 0:
            raise ValueError("缓存大小必须为正整数")
        self.max_size = max_size
        self.cache = OrderedDict()  # 有序字典用于维护插入顺序

    def add(self, key, value):
        """
        添加消息到缓存中

        参数:
            key: 消息的键
            value: 消息的值
        """
        # 如果键已存在，先删除以更新其位置
        if key in self.cache:
            del self.cache[key]
        # 如果缓存已满，删除最老的消息
        elif len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)
        self.cache[key] = value

    def get(self, key, default=None):
        """
        安全获取消息

        参数:
            key: 要获取的消息的键
            default: 如果键不存在时返回的默认值

        返回:
            与键关联的值，如果键不存在则返回默认值
        """
        return self.cache.get(key, default)

    def __contains__(self, key):
        """检查键是否存在于缓存中"""
        return key in self.cache

    def __len__(self):
        """返回当前缓存中的消息数量"""
        return len(self.cache)

    def clear(self):
        """清空缓存"""
        self.cache.clear()

    def items(self):
        """返回缓存中的所有键值对"""
        return self.cache.items()

    def keys(self):
        """返回缓存中的所有键"""
        return self.cache.keys()

    def values(self):
        """返回缓存中的所有值"""
        return self.cache.values()

def get_mime_type(file_bytes: bytes):
    """通过文件的魔术数字检测文件MIME类型"""
    if len(file_bytes) < 4:
        return "application/octet-stream"

    # 图片类型
    image_types = (
        ((b"\xFF\xD8\xFF",), "image/jpeg"),
        ((b"\x89PNG\r\n\x1a\n",), "image/png"),
        ((b"GIF87a", b"GIF89a"), "image/gif"),
        ((b"BM",), "image/bmp"),
        ((b"\x00\x00\x01\x00",), "image/x-icon"),
        ((b"II*\x00", b"MM\x00*"), "image/tiff"),
        ((b"\x49\x49\x2A\x00", b"\x4D\x4D\x00\x2A"), "image/tiff"),
        ((b"\x0A",), "image/pcx"),
    )
    if mime_type := _match_magic(file_bytes, image_types):
        return mime_type

    # 文档类型
    if file_bytes.startswith(b"%PDF"):
        return "application/pdf"
    if file_bytes.startswith(b"PK\x03\x04"):  # ZIP格式(也可能是docx, xlsx等)
        return _get_zip_mime_type(file_bytes)

    document_types = (
        (
            (b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1",),
            "application/vnd.ms-office",  # 旧的MS Office文档(.doc, .xls等)
        ),
        ((b"{\\rtf",), "application/rtf"),
    )
    if mime_type := _match_magic(file_bytes, document_types):
        return mime_type

    # 音频/视频类型
    riff_type = _get_riff_mime_type(file_bytes)
    if riff_type:
        return riff_type

    media_types = (
        ((b"ID3",), "audio/mpeg"),
        ((b"\xFF\xFB", b"\xFF\xF3", b"\xFF\xF2"), "audio/mpeg"),  # MP3
        ((b"OggS",), "audio/ogg"),
        ((b"fLaC",), "audio/flac"),
        ((b"\x00\x00\x00\x20\x66\x74\x79\x70",), "video/mp4"),
        ((b"\x1A\x45\xDF\xA3",), "video/webm"),  # 也可能是matroska
    )
    if mime_type := _match_magic(file_bytes, media_types):
        return mime_type

    # 压缩文件
    archive_types = (
        ((b"\x1F\x8B\x08",), "application/gzip"),
        ((b"BZh",), "application/x-bzip2"),
        ((b"\xFD7zXZ\x00",), "application/x-xz"),
        ((b"Rar!\x1A\x07\x00", b"Rar!\x1A\x07\x01\x00"), "application/vnd.rar"),
        ((b"7z\xBC\xAF\x27\x1C",), "application/x-7z-compressed"),
    )
    if mime_type := _match_magic(file_bytes, archive_types):
        return mime_type

    # 可执行文件和库
    executable_types = (
        ((b"MZ",), "application/x-msdownload"),  # Windows可执行文件
        ((b"\x7FELF",), "application/x-executable"),  # Linux可执行文件
    )
    if mime_type := _match_magic(file_bytes, executable_types):
        return mime_type

    # 文本和源代码
    text_type = _get_text_mime_type(file_bytes)
    if text_type:
        return text_type

    # 其他类型
    other_types = (
        ((b"\x00\x01\x00\x00",), "application/x-font-ttf"),
        ((b"\x46\x4F\x4E\x54",), "application/x-font"),
        (
            ((b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"),),
            "application/x-zerosize",  # 可能是空文件
        ),
    )
    if mime_type := _match_magic(file_bytes, other_types):
        return mime_type

    return "application/octet-stream"  # 默认返回未知二进制流类型


def _match_magic(
    file_bytes: bytes,
    magic_types: tuple[tuple[tuple[bytes, ...], str], ...],
) -> str | None:
    for signatures, mime_type in magic_types:
        if file_bytes.startswith(signatures):
            return mime_type
    return None


def _get_zip_mime_type(file_bytes: bytes) -> str:
    # 需要进一步检查是否是Office文档
    office_types = (
        (
            b"word/",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        (b"xl/", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        (
            b"ppt/",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ),
    )
    if len(file_bytes) <= 30:
        return "application/zip"

    zip_header = file_bytes[:1024]
    for marker, mime_type in office_types:
        if marker in zip_header:
            return mime_type
    return "application/zip"


def _get_riff_mime_type(file_bytes: bytes) -> str | None:
    if not file_bytes.startswith(b"RIFF") or len(file_bytes) <= 8:
        return None
    if file_bytes[8:12] == b"WAVE":
        return "audio/wav"
    if file_bytes[8:12] == b"AVI ":
        return "video/x-msvideo"
    return None


def _get_text_mime_type(file_bytes: bytes) -> str | None:
    if file_bytes.startswith((b"#!", b"\xEF\xBB\xBF", b"\xFE\xFF", b"\xFF\xFE")):
        return "text/plain"

    prefix = file_bytes[:100].lower()
    if b"<?xml" in prefix:
        return "application/xml"
    if b"<!doctype html" in prefix or b"<html" in prefix:
        return "text/html"

    return None
