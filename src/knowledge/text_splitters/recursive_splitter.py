# -*- coding: utf-8 -*-
"""
@File    : recursive_splitter.py
@Time    : 2025/12/8 16:39
@Desc    : 
"""
from typing import List
from .base_splitter import BaseTextSplitter


class RecursiveTextSplitter(BaseTextSplitter):
    """递归文本分割器（类似LangChain的RecursiveCharacterTextSplitter）"""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50, separators: List[str] = None):
        super().__init__(chunk_size, chunk_overlap)

        if separators is None:
            separators = [
                "\n\n",  # 双换行
                "\n",  # 单换行
                "。",  # 中文句号
                "！",  # 中文感叹号
                "？",  # 中文问号
                "；",  # 中文分号
                "，",  # 中文逗号
                ". ",  # 英文句号
                "! ",  # 英文感叹号
                "? ",  # 英文问号
                "; ",  # 英文分号
                ", ",  # 英文逗号
                " ",  # 空格
                ""  # 无分隔符（字符级分割）
            ]
        self.separators = separators

    def split_text(self, text: str) -> List[str]:
        """递归分割文本"""

        # 递归分割函数
        def _split_recursive(chunk: str, separators: List[str]) -> List[str]:
            if not chunk:
                return []

            # 尝试当前分隔符
            separator = separators[0]
            if separator:
                splits = chunk.split(separator)
            else:
                splits = list(chunk)

            # 合并小片段
            good_splits = []
            current_split = ""

            for s in splits:
                if separator:
                    combined = current_split + separator + s if current_split else s
                else:
                    combined = current_split + s

                if len(combined) <= self.chunk_size:
                    current_split = combined
                else:
                    if current_split:
                        good_splits.append(current_split)
                    current_split = s

            if current_split:
                good_splits.append(current_split)

            # 如果片段仍然太大，使用下一个分隔符
            final_splits = []
            for split_text in good_splits:
                if len(split_text) <= self.chunk_size:
                    final_splits.append(split_text)
                else:
                    if len(separators) > 1:
                        final_splits.extend(_split_recursive(split_text, separators[1:]))
                    else:
                        # 最后的分隔符，直接按长度分割
                        final_splits.extend(self._split_by_length(split_text))

            return final_splits

        # 主分割逻辑
        chunks = _split_recursive(text, self.separators)

        # 处理重叠
        for i in range(len(chunks)):
            if i > 0 and self.chunk_overlap > 0:
                overlap_start = max(0, len(chunks[i - 1]) - self.chunk_overlap)
                overlap_text = chunks[i - 1][overlap_start:]

                # 确保重叠文本有意义（不在单词中间截断）
                overlap_text = self._adjust_overlap(overlap_text, chunks[i])
                chunks[i] = overlap_text + chunks[i]

            # 确保chunk不超过最大长度
            if len(chunks[i]) > self.chunk_size:
                chunks[i] = chunks[i][:self.chunk_size]

        # 移除空chunk
        final_chunks = [chunk for chunk in chunks if chunk.strip()]

        return final_chunks

    def _split_by_length(self, text: str) -> List[str]:
        """按固定长度分割"""
        return [text[i:i + self.chunk_size] for i in range(0, len(text), self.chunk_size)]

    def _adjust_overlap(self, overlap_text: str, next_chunk: str) -> str:
        """调整重叠文本，使其更合理"""
        # 尝试在句子边界处截断
        sentence_endings = ['。', '！', '？', '.', '!', '?', '\n']

        for ending in sentence_endings:
            if ending in overlap_text:
                # 找到最后一个句子结束的位置
                last_pos = overlap_text.rfind(ending)
                if last_pos != -1:
                    return overlap_text[:last_pos + len(ending)]

        # 尝试在空格处截断
        if ' ' in overlap_text:
            last_space = overlap_text.rfind(' ')
            if last_space != -1:
                return overlap_text[:last_space + 1]

        # 如果没有合适的边界，直接返回
        return overlap_text
