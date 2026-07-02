"""文档解析组件：PDF/Word → 纯文本"""

import io
from core.logger import get_logger
from core.exceptions import DocumentParseError, UnsupportedFormatError
from utils.file_utils import detect_file_type

logger = get_logger(__name__)


def parse_pdf(file_bytes: bytes) -> str:
    """解析 PDF 文件，提取纯文本"""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise DocumentParseError("PyMuPDF 未安装，请运行: pip install PyMuPDF")

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        text = "\n".join(text_parts)
        if not text.strip():
            raise DocumentParseError("PDF 文件中未提取到文本内容，可能是扫描件或图片型 PDF")
        logger.info(f"PDF 解析完成，共 {len(doc)} 页，{len(text)} 字符")
        return text
    except DocumentParseError:
        raise
    except Exception as e:
        logger.error(f"PDF 解析失败: {e}")
        raise DocumentParseError(f"PDF 解析失败: {e}")


def parse_docx(file_bytes: bytes) -> str:
    """解析 Word 文档，提取纯文本"""
    try:
        from docx import Document
    except ImportError:
        raise DocumentParseError("python-docx 未安装，请运行: pip install python-docx")

    try:
        doc = Document(io.BytesIO(file_bytes))
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text.strip())
        text = "\n".join(text_parts)
        if not text.strip():
            raise DocumentParseError("Word 文档中未提取到文本内容")
        logger.info(f"Word 解析完成，共 {len(text_parts)} 个段落，{len(text)} 字符")
        return text
    except DocumentParseError:
        raise
    except Exception as e:
        logger.error(f"Word 解析失败: {e}")
        raise DocumentParseError(f"Word 解析失败: {e}")


def parse(file_bytes: bytes, filename: str) -> str:
    """
    统一解析入口，根据文件扩展名分发。

    Args:
        file_bytes: 文件的原始字节
        filename: 文件名（用于判断类型）

    Returns:
        提取的纯文本

    Raises:
        UnsupportedFormatError: 不支持的文件格式
        DocumentParseError: 解析失败
    """
    file_type = detect_file_type(filename)

    if file_type == "pdf":
        return parse_pdf(file_bytes)
    elif file_type == "docx":
        return parse_docx(file_bytes)
    else:
        raise UnsupportedFormatError(filename)
