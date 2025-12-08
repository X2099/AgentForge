# -*- coding: utf-8 -*-
"""
@File    : txt_loader.py
@Time    : 2025/12/8 16:18
@Desc    : 
"""
from typing import List, Optional
import chardet
from .base_loader import BaseDocumentLoader, Document


class TxtLoader(BaseDocumentLoader):
    """纯文本文件(.txt)加载器"""

    def __init__(self, file_path: str, encoding: str = None,
                 auto_detect_encoding: bool = True):
        """
        初始化TXT加载器

        Args:
            file_path: 文件路径
            encoding: 指定编码，如'utf-8', 'gbk'等
            auto_detect_encoding: 是否自动检测编码
        """
        super().__init__(file_path, encoding or "utf-8")
        self.auto_detect_encoding = auto_detect_encoding
        self.detected_encoding = None

    def load(self) -> List[Document]:
        """加载TXT文档"""
        try:
            # 检测文件编码
            encoding = self._detect_encoding() if self.auto_detect_encoding else self.encoding

            # 读取文件内容
            content = self._read_file_with_encoding(encoding)

            # 预处理文本
            content = self._preprocess_text(content)

            # 创建文档
            metadata = {
                "source": str(self.file_path),
                "file_type": "txt",
                "encoding": encoding,
                "file_size": self.file_path.stat().st_size,
                "line_count": content.count('\n') + 1
            }

            # 尝试提取标题
            title = self._extract_title(content)
            if title:
                metadata["title"] = title

            document = Document(
                content=content,
                metadata=metadata
            )

            return [document]

        except UnicodeDecodeError as e:
            raise Exception(f"解码失败，请尝试其他编码。错误: {str(e)}")
        except FileNotFoundError:
            raise Exception(f"文件不存在: {self.file_path}")
        except Exception as e:
            raise Exception(f"加载TXT文件失败: {str(e)}")

    def _detect_encoding(self) -> str:
        """自动检测文件编码"""
        try:
            # 读取文件前一部分来检测编码
            with open(self.file_path, 'rb') as f:
                raw_data = f.read(10000)  # 读取前10KB进行检测

            if not raw_data:
                return self.encoding  # 文件为空，使用默认编码

            # 使用chardet检测编码
            result = chardet.detect(raw_data)
            detected_encoding = result['encoding']
            confidence = result['confidence']

            # 记录检测结果
            self.detected_encoding = {
                "encoding": detected_encoding,
                "confidence": confidence
            }

            # 选择编码
            if detected_encoding and confidence > 0.7:
                # 如果是常见的编码，直接使用
                common_encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030',
                                    'ascii', 'iso-8859-1', 'windows-1252']

                if detected_encoding.lower().replace('-', '') in [
                    enc.lower().replace('-', '') for enc in common_encodings
                ]:
                    return detected_encoding

            # 如果检测不可靠，尝试常见编码
            return self._try_common_encodings()

        except Exception:
            # 如果检测失败，使用默认编码
            return self.encoding

    def _try_common_encodings(self) -> str:
        """尝试常见编码"""
        common_encodings = [
            'utf-8',
            'gbk',
            'gb2312',
            'gb18030',
            'big5',  # 繁体中文
            'shift_jis',  # 日文
            'euc-kr',  # 韩文
            'iso-8859-1',
            'windows-1252',
            'ascii'
        ]

        # 尝试读取第一行来判断编码
        for encoding in common_encodings:
            try:
                with open(self.file_path, 'r', encoding=encoding, errors='strict') as f:
                    f.readline()  # 尝试读取一行
                return encoding  # 成功读取，返回该编码
            except (UnicodeDecodeError, UnicodeError):
                continue

        # 所有常见编码都失败，使用utf-8并忽略错误
        return 'utf-8'

    def _read_file_with_encoding(self, encoding: str) -> str:
        """使用指定编码读取文件"""
        # 先尝试严格模式
        try:
            with open(self.file_path, 'r', encoding=encoding, errors='strict') as f:
                return f.read()
        except UnicodeDecodeError:
            # 严格模式失败，使用忽略错误模式
            try:
                with open(self.file_path, 'r', encoding=encoding, errors='ignore') as f:
                    return f.read()
            except Exception as e:
                raise Exception(f"无法使用编码 {encoding} 读取文件: {str(e)}")

    def _preprocess_text(self, content: str) -> str:
        """预处理文本内容"""
        if not content:
            return ""

        # 移除BOM（字节顺序标记）
        if content.startswith('\ufeff'):
            content = content[1:]

        # 规范化换行符
        content = content.replace('\r\n', '\n').replace('\r', '\n')

        # 移除多余的空行（保留最多两个连续空行）
        lines = content.split('\n')
        processed_lines = []
        empty_line_count = 0

        for line in lines:
            stripped_line = line.rstrip()
            if not stripped_line:
                empty_line_count += 1
                if empty_line_count <= 2:  # 最多保留两个连续空行
                    processed_lines.append(stripped_line)
            else:
                empty_line_count = 0
                processed_lines.append(stripped_line)

        return '\n'.join(processed_lines)

    def _extract_title(self, content: str) -> Optional[str]:
        """从文本中提取标题"""
        if not content:
            return None

        # 方法1：使用文件名（不含扩展名）
        title_from_filename = self.file_path.stem
        if title_from_filename and len(title_from_filename) > 1:
            return title_from_filename

        # 方法2：从内容第一行提取
        lines = content.split('\n')
        for line in lines:
            stripped_line = line.strip()
            if stripped_line:
                # 检查第一行是否像标题（长度适中，不以特殊字符开头）
                if 2 <= len(stripped_line) <= 100:
                    # 移除常见的标题标记
                    title = stripped_line.lstrip('#*=- ').rstrip(' =-#*')
                    if title:
                        return title
                break

        return None

    def load_with_lines(self) -> List[str]:
        """
        按行加载文本文件（特殊用途）

        Returns:
            文本行列表
        """
        encoding = self._detect_encoding() if self.auto_detect_encoding else self.encoding

        try:
            with open(self.file_path, 'r', encoding=encoding, errors='ignore') as f:
                lines = [line.rstrip('\n') for line in f]
            return lines
        except Exception as e:
            raise Exception(f"按行读取文件失败: {str(e)}")

    def load_as_single_document_per_line(self) -> List[Document]:
        """
        每行作为一个独立文档加载

        Returns:
            文档列表，每行一个文档
        """
        lines = self.load_with_lines()
        documents = []

        for line_num, line in enumerate(lines, 1):
            if line.strip():  # 跳过空行
                metadata = {
                    "source": str(self.file_path),
                    "file_type": "txt",
                    "line_number": line_num,
                    "total_lines": len(lines)
                }

                document = Document(
                    content=line,
                    metadata=metadata
                )
                documents.append(document)

        return documents


if __name__ == '__main__':
    loader = TxtLoader(r"D:\Coding\MyData\大模型技术栈-实战与应用.txt")
    docs = loader.load()
    print(docs)
