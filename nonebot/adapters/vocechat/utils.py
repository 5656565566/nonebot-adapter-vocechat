from nonebot.utils import logger_wrapper

log = logger_wrapper("vocechat")

def get_mime_type(file_bytes: bytes):
    """通过文件的魔术数字检测文件MIME类型"""
    if len(file_bytes) < 4:
        return 'application/octet-stream'
    
    # 图片类型
    if file_bytes.startswith(b'\xFF\xD8\xFF'):
        return 'image/jpeg'
    elif file_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    elif file_bytes.startswith(b'GIF87a') or file_bytes.startswith(b'GIF89a'):
        return 'image/gif'
    elif file_bytes.startswith(b'BM'):
        return 'image/bmp'
    elif file_bytes.startswith(b'\x00\x00\x01\x00'):
        return 'image/x-icon'
    elif file_bytes.startswith(b'II*\x00') or file_bytes.startswith(b'MM\x00*'):
        return 'image/tiff'
    elif file_bytes.startswith(b'\x49\x49\x2A\x00') or file_bytes.startswith(b'\x4D\x4D\x00\x2A'):
        return 'image/tiff'
    elif file_bytes.startswith(b'\x0A'):
        return 'image/pcx'
    
    # 文档类型
    elif file_bytes.startswith(b'%PDF'):
        return 'application/pdf'
    elif file_bytes.startswith(b'PK\x03\x04'):  # ZIP格式(也可能是docx, xlsx等)
        # 需要进一步检查是否是Office文档
        if len(file_bytes) > 30 and b'word/' in file_bytes[:1024]:
            return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif len(file_bytes) > 30 and b'xl/' in file_bytes[:1024]:
            return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif len(file_bytes) > 30 and b'ppt/' in file_bytes[:1024]:
            return 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        else:
            return 'application/zip'
    elif file_bytes.startswith(b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'):
        return 'application/vnd.ms-office'  # 旧的MS Office文档(.doc, .xls等)
    elif file_bytes.startswith(b'{\\rtf'):
        return 'application/rtf'
    
    # 音频/视频类型
    elif file_bytes.startswith(b'RIFF') and len(file_bytes) > 8 and file_bytes[8:12] == b'WAVE':
        return 'audio/wav'
    elif file_bytes.startswith(b'ID3'):
        return 'audio/mpeg'
    elif file_bytes.startswith(b'\xFF\xFB') or file_bytes.startswith(b'\xFF\xF3') or file_bytes.startswith(b'\xFF\xF2'):
        return 'audio/mpeg'  # MP3
    elif file_bytes.startswith(b'OggS'):
        return 'audio/ogg'
    elif file_bytes.startswith(b'fLaC'):
        return 'audio/flac'
    elif file_bytes.startswith(b'RIFF') and len(file_bytes) > 8 and file_bytes[8:12] == b'AVI ':
        return 'video/x-msvideo'
    elif file_bytes.startswith(b'\x00\x00\x00\x20\x66\x74\x79\x70'):
        return 'video/mp4'
    elif file_bytes.startswith(b'\x1A\x45\xDF\xA3'):
        return 'video/webm'  # 也可能是matroska
    
    # 压缩文件
    elif file_bytes.startswith(b'\x1F\x8B\x08'):
        return 'application/gzip'
    elif file_bytes.startswith(b'BZh'):
        return 'application/x-bzip2'
    elif file_bytes.startswith(b'\xFD7zXZ\x00'):
        return 'application/x-xz'
    elif file_bytes.startswith(b'Rar!\x1A\x07\x00') or file_bytes.startswith(b'Rar!\x1A\x07\x01\x00'):
        return 'application/vnd.rar'
    elif file_bytes.startswith(b'7z\xBC\xAF\x27\x1C'):
        return 'application/x-7z-compressed'
    
    # 可执行文件和库
    elif file_bytes.startswith(b'MZ'):
        return 'application/x-msdownload'  # Windows可执行文件
    elif file_bytes.startswith(b'\x7FELF'):
        return 'application/x-executable'  # Linux可执行文件
    
    # 文本和源代码
    elif file_bytes.startswith(b'#!') or file_bytes.startswith(b'\xEF\xBB\xBF') or file_bytes.startswith(b'\xFE\xFF') or file_bytes.startswith(b'\xFF\xFE'):
        return 'text/plain'
    elif b'<?xml' in file_bytes[:100].lower():
        return 'application/xml'
    elif b'<!doctype html' in file_bytes[:100].lower() or b'<html' in file_bytes[:100].lower():
        return 'text/html'
    elif file_bytes.startswith(b'\xFE\xFF') or file_bytes.startswith(b'\xFF\xFE'):
        return 'text/plain'  # Unicode文本
    
    # 其他类型
    elif file_bytes.startswith(b'\x00\x01\x00\x00'):
        return 'application/x-font-ttf'
    elif file_bytes.startswith(b'\x46\x4F\x4E\x54'):
        return 'application/x-font'
    elif file_bytes.startswith(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'):
        return 'application/x-zerosize'  # 可能是空文件
    
    return 'application/octet-stream'  # 默认返回未知二进制流类型