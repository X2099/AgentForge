# -*- coding: utf-8 -*-
"""
@File    : langchain_kb.py
@Time    : 2025/12/9
@Desc    : 基于LangChain标准组件的知识库实现
"""
from typing import List, Dict, Any, Optional, Sequence
from pathlib import Path
import asyncio
import logging

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_community.embeddings import OpenAIEmbeddings, HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma, FAISS
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    CSVLoader,
    UnstructuredMarkdownLoader,
    BSHTMLLoader,
)
from langchain_community.document_loaders import Docx2txtLoader

logger = logging.getLogger(__name__)


class LangChainKnowledgeBase:
    """
    基于LangChain标准组件的知识库
    
    使用LangChain的标准组件：
    - Document: LangChain标准文档类型
    - Embeddings: LangChain嵌入接口
    - VectorStore: LangChain向量存储
    - TextSplitter: LangChain文本分割器
    - DocumentLoaders: LangChain文档加载器
    """
    
    def __init__(
        self,
        name: str,
        embedding: Optional[Embeddings] = None,
        vector_store: Optional[Any] = None,
        text_splitter: Optional[TextSplitter] = None,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        """
        初始化知识库
        
        Args:
            name: 知识库名称
            embedding: 嵌入器（如果为None，使用OpenAI默认）
            vector_store: 向量存储（如果为None，自动创建Chroma）
            text_splitter: 文本分割器（如果为None，使用RecursiveCharacterTextSplitter）
            persist_directory: 持久化目录
            collection_name: 集合名称
        """
        self.name = name
        self.persist_directory = persist_directory or f"./data/knowledge_bases/{name}"
        
        # 初始化嵌入器
        if embedding is None:
            try:
                self.embedding = OpenAIEmbeddings()
            except Exception:
                logger.warning("OpenAI嵌入器初始化失败，使用本地嵌入器")
                self.embedding = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
                )
        else:
            self.embedding = embedding
        
        # 初始化文本分割器
        if text_splitter is None:
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
                length_function=len,
            )
        else:
            self.text_splitter = text_splitter
        
        # 初始化向量存储
        if vector_store is None:
            collection_name = collection_name or name
            Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
            
            try:
                # 尝试加载已存在的向量存储
                self.vector_store = Chroma(
                    collection_name=collection_name,
                    embedding_function=self.embedding,
                    persist_directory=self.persist_directory,
                )
                logger.info(f"加载已存在的向量存储: {self.name}")
            except Exception:
                # 创建新的向量存储
                self.vector_store = Chroma(
                    collection_name=collection_name,
                    embedding_function=self.embedding,
                    persist_directory=self.persist_directory,
                )
                logger.info(f"创建新的向量存储: {self.name}")
        else:
            self.vector_store = vector_store
        
        # 文档统计
        self.document_count = 0
        
    def _get_loader(self, file_path: str):
        """根据文件类型获取相应的加载器"""
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        loader_map = {
            ".pdf": PyPDFLoader,
            ".txt": TextLoader,
            ".md": UnstructuredMarkdownLoader,
            ".markdown": UnstructuredMarkdownLoader,
            ".docx": Docx2txtLoader,
            ".csv": CSVLoader,
            ".html": BSHTMLLoader,
            ".htm": BSHTMLLoader,
        }
        
        loader_class = loader_map.get(suffix)
        if loader_class is None:
            raise ValueError(f"不支持的文件类型: {suffix}")
        
        return loader_class(file_path)
    
    def add_documents(
        self,
        file_paths: List[str],
        batch_size: int = 10,
        show_progress: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        添加文档到知识库（同步）
        
        Args:
            file_paths: 文件路径列表
            batch_size: 批处理大小
            show_progress: 是否显示进度
            metadata: 额外的元数据
            
        Returns:
            处理统计信息
        """
        all_documents = []
        processed_files = []
        failed_files = []
        
        total_files = len(file_paths)
        
        if show_progress:
            print(f"开始处理 {total_files} 个文件...")
        
        # 加载文档
        for i, file_path in enumerate(file_paths, 1):
            try:
                if show_progress:
                    print(f"[{i}/{total_files}] 加载: {file_path}")
                
                loader = self._get_loader(file_path)
                documents = loader.load()
                
                # 添加文件路径到元数据
                for doc in documents:
                    doc.metadata["source"] = str(file_path)
                    if metadata:
                        doc.metadata.update(metadata)
                
                # 分割文档
                split_documents = self.text_splitter.split_documents(documents)
                all_documents.extend(split_documents)
                
                processed_files.append({
                    "path": file_path,
                    "original_docs": len(documents),
                    "split_docs": len(split_documents)
                })
                
                logger.info(f"成功处理文件: {file_path}, 生成 {len(split_documents)} 个chunk")
                
            except Exception as e:
                error_msg = f"处理文件失败 {file_path}: {str(e)}"
                logger.error(error_msg)
                failed_files.append({
                    "path": file_path,
                    "error": str(e)
                })
        
        # 添加到向量存储
        if all_documents:
            if show_progress:
                print(f"添加 {len(all_documents)} 个文档块到向量存储...")
            
            try:
                self.vector_store.add_documents(all_documents)
                self.document_count += len(all_documents)
                self.vector_store.persist()
                
                if show_progress:
                    print(f"成功添加 {len(all_documents)} 个文档块")
            except Exception as e:
                logger.error(f"添加文档到向量存储失败: {str(e)}")
        
        return {
            "total_files": total_files,
            "processed_files": len(processed_files),
            "failed_files": len(failed_files),
            "total_chunks": len(all_documents),
            "document_count": self.document_count,
            "processed_files_detail": processed_files,
            "failed_files_detail": failed_files
        }
    
    async def add_documents_async(
        self,
        file_paths: List[str],
        batch_size: int = 10,
        show_progress: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        异步添加文档到知识库
        
        Args:
            file_paths: 文件路径列表
            batch_size: 批处理大小
            show_progress: 是否显示进度
            metadata: 额外的元数据
            
        Returns:
            处理统计信息
        """
        all_documents = []
        processed_files = []
        failed_files = []
        
        total_files = len(file_paths)
        
        if show_progress:
            print(f"开始异步处理 {total_files} 个文件...")
        
        # 异步加载文档
        async def load_file(file_path: str):
            try:
                loader = self._get_loader(file_path)
                # 文档加载可能需要在线程池中执行
                loop = asyncio.get_event_loop()
                documents = await loop.run_in_executor(None, loader.load)
                
                # 添加元数据
                for doc in documents:
                    doc.metadata["source"] = str(file_path)
                    if metadata:
                        doc.metadata.update(metadata)
                
                # 分割文档
                split_documents = await loop.run_in_executor(
                    None,
                    self.text_splitter.split_documents,
                    documents
                )
                
                return {
                    "success": True,
                    "path": file_path,
                    "documents": split_documents,
                    "original_count": len(documents),
                    "split_count": len(split_documents)
                }
            except Exception as e:
                return {
                    "success": False,
                    "path": file_path,
                    "error": str(e)
                }
        
        # 并发加载文档（控制并发数）
        semaphore = asyncio.Semaphore(5)  # 最多5个并发
        
        async def load_with_semaphore(file_path):
            async with semaphore:
                return await load_file(file_path)
        
        tasks = [load_with_semaphore(fp) for fp in file_paths]
        results = await asyncio.gather(*tasks)
        
        # 处理结果
        for i, result in enumerate(results, 1):
            if show_progress:
                print(f"[{i}/{total_files}] 处理: {result['path']}")
            
            if result["success"]:
                all_documents.extend(result["documents"])
                processed_files.append({
                    "path": result["path"],
                    "original_docs": result["original_count"],
                    "split_docs": result["split_count"]
                })
            else:
                failed_files.append({
                    "path": result["path"],
                    "error": result["error"]
                })
        
        # 批量添加到向量存储
        if all_documents:
            if show_progress:
                print(f"添加 {len(all_documents)} 个文档块到向量存储...")
            
            try:
                # 向量存储的add_documents可能不是异步的，使用线程池
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.vector_store.add_documents(all_documents)
                )
                await loop.run_in_executor(None, self.vector_store.persist)
                
                self.document_count += len(all_documents)
                
                if show_progress:
                    print(f"成功添加 {len(all_documents)} 个文档块")
            except Exception as e:
                logger.error(f"添加文档到向量存储失败: {str(e)}")
        
        return {
            "total_files": total_files,
            "processed_files": len(processed_files),
            "failed_files": len(failed_files),
            "total_chunks": len(all_documents),
            "document_count": self.document_count,
            "processed_files_detail": processed_files,
            "failed_files_detail": failed_files
        }
    
    def search(
        self,
        query: str,
        k: int = 4,
        filter_dict: Optional[Dict] = None
    ) -> List[Document]:
        """
        搜索知识库
        
        Args:
            query: 查询文本
            k: 返回结果数量
            filter_dict: 过滤条件
            
        Returns:
            相关文档列表
        """
        try:
            # 使用向量存储的相似度搜索
            if filter_dict:
                results = self.vector_store.similarity_search_with_score(
                    query,
                    k=k,
                    filter=filter_dict
                )
            else:
                results = self.vector_store.similarity_search_with_score(query, k=k)
            
            # 提取文档和分数
            documents = []
            for doc, score in results:
                doc.metadata["similarity_score"] = float(score)
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            return []
    
    async def search_async(
        self,
        query: str,
        k: int = 4,
        filter_dict: Optional[Dict] = None
    ) -> List[Document]:
        """异步搜索知识库"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.search, query, k, filter_dict)
    
    def as_retriever(
        self,
        search_type: str = "similarity",
        search_kwargs: Optional[Dict[str, Any]] = None
    ) -> BaseRetriever:
        """
        创建Retriever接口
        
        Args:
            search_type: 搜索类型（similarity, mmr等）
            search_kwargs: 搜索参数
            
        Returns:
            LangChain Retriever
        """
        search_kwargs = search_kwargs or {"k": 4}
        return self.vector_store.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        try:
            # 尝试获取集合统计信息
            if hasattr(self.vector_store, "_collection"):
                count = self.vector_store._collection.count()
            else:
                count = self.document_count
        except Exception:
            count = self.document_count
        
        return {
            "name": self.name,
            "document_count": count,
            "persist_directory": self.persist_directory,
            "embedding_model": str(self.embedding) if hasattr(self.embedding, "__class__") else "unknown",
            "vector_store_type": type(self.vector_store).__name__
        }
    
    def delete_documents(self, ids: List[str]):
        """删除文档"""
        if hasattr(self.vector_store, "delete"):
            self.vector_store.delete(ids)
            self.vector_store.persist()
            logger.info(f"删除 {len(ids)} 个文档")
        else:
            logger.warning("向量存储不支持删除操作")

