# -*- coding: utf-8 -*-
"""
@File    : openai_embedder.py
@Time    : 2025/12/8 16:54
@Desc    : 
"""
import openai
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential
from .base_embedder import BaseEmbedder


class OpenAIEmbedder(BaseEmbedder):
    """OpenAI嵌入模型"""

    def __init__(self,
                 model: str = "text-embedding-3-small",
                 api_key: str = None,
                 base_url: str = None,
                 dimensions: int = None):
        """
        初始化OpenAI嵌入器

        Args:
            model: 模型名称
            api_key: OpenAI API密钥
            base_url: API基础URL（用于代理）
            dimensions: 嵌入维度（仅支持部分模型）
        """
        self.model = model
        self.dimensions = dimensions

        # 初始化客户端
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入文档"""
        if not texts:
            return []

        # 分批处理，避免超过token限制
        batch_size = 100  # OpenAI推荐批量大小
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                    dimensions=self.dimensions
                )

                batch_embeddings = [data.embedding for data in response.data]
                embeddings.extend(batch_embeddings)

            except Exception as e:
                raise Exception(f"OpenAI嵌入请求失败: {str(e)}")

        return embeddings

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimensions
            )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"OpenAI查询嵌入失败: {str(e)}")
