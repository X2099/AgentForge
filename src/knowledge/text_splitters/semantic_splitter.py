# -*- coding: utf-8 -*-
"""
@File    : semantic_splitter.py
@Time    : 2025/12/8 16:43
@Desc    : 
"""
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
from .base_splitter import BaseTextSplitter


class SemanticTextSplitter(BaseTextSplitter):
    """基于语义的文本分割器"""

    def __init__(self,
                 chunk_size: int = 500,
                 chunk_overlap: int = 50,
                 model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
                 threshold: float = 0.5):
        super().__init__(chunk_size, chunk_overlap)
        self.model_name = model_name
        self.threshold = threshold
        self.model = None

    def _load_model(self):
        """懒加载模型"""
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)

    def split_text(self, text: str) -> List[str]:
        """基于语义分割文本"""
        self._load_model()

        # 首先按句子分割
        sentences = self._split_into_sentences(text)

        if len(sentences) <= 1:
            return [text]

        # 计算句子嵌入
        sentence_embeddings = self.model.encode(sentences)

        # 计算句子间的相似度
        chunks = []
        current_chunk = []
        current_length = 0

        for i, sentence in enumerate(sentences):
            sentence_len = len(sentence)

            if not current_chunk:
                # 第一个句子
                current_chunk.append(sentence)
                current_length += sentence_len
            else:
                # 计算与当前chunk的语义相似度
                last_embedding = sentence_embeddings[i - 1]
                current_embedding = sentence_embeddings[i]
                similarity = np.dot(last_embedding, current_embedding) / (
                        np.linalg.norm(last_embedding) * np.linalg.norm(current_embedding)
                )

                # 如果相似度高且长度允许，添加到当前chunk
                if (similarity > self.threshold and
                        current_length + sentence_len <= self.chunk_size):
                    current_chunk.append(sentence)
                    current_length += sentence_len
                else:
                    # 保存当前chunk
                    chunks.append(' '.join(current_chunk))

                    # 处理重叠
                    if self.chunk_overlap > 0 and chunks:
                        overlap_sentences = self._get_overlap_sentences(
                            current_chunk, self.chunk_overlap
                        )
                        current_chunk = overlap_sentences + [sentence]
                        current_length = sum(len(s) for s in current_chunk)
                    else:
                        current_chunk = [sentence]
                        current_length = sentence_len

        # 添加最后一个chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """将文本分割成句子"""
        # 简单的句子分割，可以根据需要替换为更复杂的NLP库
        import re

        # 中英文句子结束符
        sentence_endings = r'(?<=[。！？.?!])\s+'
        sentences = re.split(sentence_endings, text)

        # 移除空句子
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def _get_overlap_sentences(self, sentences: List[str], max_overlap: int) -> List[str]:
        """获取重叠的句子"""
        overlap_sentences = []
        overlap_length = 0

        for sentence in reversed(sentences):
            sentence_len = len(sentence)
            if overlap_length + sentence_len <= max_overlap:
                overlap_sentences.insert(0, sentence)
                overlap_length += sentence_len
            else:
                break

        return overlap_sentences
