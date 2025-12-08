# -*- coding: utf-8 -*-
"""
@File    : kb_manager.py
@Time    : 2025/12/8 17:22
@Desc    : 
"""
import json
import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path

from .knowledge_base import KnowledgeBase


class KnowledgeBaseManager:
    """知识库管理器"""

    def __init__(self, config_dir: str = "./configs/knowledge_bases"):
        """
        初始化知识库管理器

        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.knowledge_bases: Dict[str, KnowledgeBase] = {}
        self.load_configs()

    def load_configs(self):
        """加载所有知识库配置"""
        config_files = list(self.config_dir.glob("*.yaml")) + list(self.config_dir.glob("*.json"))

        for config_file in config_files:
            try:
                if config_file.suffix == ".yaml":
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                else:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)

                kb_name = config.get("name", config_file.stem)
                self.create_knowledge_base(config, load_existing=True)

            except Exception as e:
                print(f"加载配置失败 {config_file}: {str(e)}")

    def create_knowledge_base(self,
                              config: Dict[str, Any],
                              load_existing: bool = True) -> KnowledgeBase:
        """
        创建知识库

        Args:
            config: 知识库配置
            load_existing: 是否加载已存在的向量存储

        Returns:
            知识库实例
        """
        kb_name = config["name"]

        if kb_name in self.knowledge_bases:
            print(f"知识库 '{kb_name}' 已存在，使用现有实例")
            return self.knowledge_bases[kb_name]

        # 创建知识库
        kb = KnowledgeBase(config)

        # 如果向量存储已存在且配置了加载现有，可以在这里加载
        if load_existing:
            # 检查向量存储是否存在
            vector_store_config = config.get("vector_store", {})
            persist_dir = vector_store_config.get("persist_directory", f"./data/vector_stores/{kb_name}")

            if Path(persist_dir).exists():
                print(f"检测到已存在的向量存储，知识库 '{kb_name}' 已加载")
                # 这里可以加载文档数量等统计信息
                # 实际应用中需要从向量存储中获取

        self.knowledge_bases[kb_name] = kb

        # 保存配置
        self._save_config(kb_name, config)

        return kb

    def get_knowledge_base(self, name: str) -> Optional[KnowledgeBase]:
        """获取知识库"""
        return self.knowledge_bases.get(name)

    def list_knowledge_bases(self) -> List[Dict[str, Any]]:
        """列出所有知识库"""
        result = []

        for name, kb in self.knowledge_bases.items():
            stats = kb.get_stats()
            result.append({
                "name": name,
                "description": stats.get("description", ""),
                "document_count": stats.get("document_count", 0),
                "last_updated": stats.get("last_updated"),
                "is_initialized": stats.get("is_initialized", False)
            })

        return result

    def delete_knowledge_base(self, name: str, delete_data: bool = False):
        """
        删除知识库

        Args:
            name: 知识库名称
            delete_data: 是否删除数据文件
        """
        if name not in self.knowledge_bases:
            raise ValueError(f"知识库 '{name}' 不存在")

        kb = self.knowledge_bases[name]

        if delete_data:
            # 删除向量存储数据
            stats = kb.get_stats()
            vector_store_stats = stats.get("vector_store", {})
            persist_dir = vector_store_stats.get("persist_directory")

            if persist_dir and Path(persist_dir).exists():
                import shutil
                try:
                    shutil.rmtree(persist_dir)
                    print(f"已删除向量存储数据: {persist_dir}")
                except Exception as e:
                    print(f"删除向量存储数据失败: {str(e)}")

        # 删除配置
        config_file = self.config_dir / f"{name}.yaml"
        if config_file.exists():
            config_file.unlink()

        # 从内存中移除
        del self.knowledge_bases[name]

    def _save_config(self, name: str, config: Dict[str, Any]):
        """保存配置到文件"""
        config_file = self.config_dir / f"{name}.yaml"

        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    def bulk_add_documents(self,
                           kb_name: str,
                           file_paths: List[str],
                           **kwargs) -> Dict[str, Any]:
        """
        批量添加文档到知识库

        Args:
            kb_name: 知识库名称
            file_paths: 文件路径列表
            **kwargs: 其他参数传递给add_documents

        Returns:
            处理统计信息
        """
        if kb_name not in self.knowledge_bases:
            raise ValueError(f"知识库 '{kb_name}' 不存在")

        kb = self.knowledge_bases[kb_name]
        return kb.add_documents(file_paths, **kwargs)

    def search(self,
               kb_name: str,
               query: str,
               k: int = 4,
               filter_dict: Optional[Dict] = None) -> List[Document]:
        """
        搜索知识库

        Args:
            kb_name: 知识库名称
            query: 查询文本
            k: 返回结果数量
            filter_dict: 过滤条件

        Returns:
            相关文档列表
        """
        if kb_name not in self.knowledge_bases:
            raise ValueError(f"知识库 '{kb_name}' 不存在")

        kb = self.knowledge_bases[kb_name]
        return kb.search(query, k, filter_dict)
