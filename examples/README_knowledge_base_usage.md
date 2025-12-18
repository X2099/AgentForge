# 知识库使用指南

这个指南将帮助你了解如何在 AgentForge 项目中使用知识库功能。

## 知识库架构

项目包含完整的知识库系统：

```
src/knowledge/
├── kb_manager.py          # 知识库管理器
├── knowledge_base.py      # 知识库核心类
├── kb_database.py         # 数据库接口
├── document_loaders/      # 文档加载器
├── embeddings/           # 嵌入模型
├── vector_stores/        # 向量存储
└── text_splitters/       # 文本分割器
```

## 快速开始

### 1. 基本使用

```python
from src.knowledge.kb_manager import KnowledgeBaseManager

# 初始化管理器
kb_manager = KnowledgeBaseManager(use_database=True)

# 创建知识库
kb_config = {
    "name": "my_kb",
    "chunk_size": 500,
    "chunk_overlap": 50,
    "embedder": {
        "embedder_type": "sentence_transformers",
        "model_name": "all-MiniLM-L6-v2"
    },
    "vector_store": {
        "store_type": "chroma",
        "collection_name": "my_kb"
    }
}

kb = kb_manager.create_knowledge_base(kb_config)
```

### 2. 添加文档

```python
# 批量添加文档
file_paths = [
    "./docs/document1.pdf",
    "./docs/document2.txt",
    "./docs/document3.md"
]

stats = kb_manager.bulk_add_documents(
    kb_name="my_kb",
    file_paths=file_paths
)

print(f"添加了 {stats['valid_chunks']} 个文档片段")
```

### 3. 搜索知识库

```python
# 搜索相关内容
results = kb_manager.search(
    kb_name="my_kb",
    query="你想搜索的内容",
    k=5  # 返回前5个结果
)

for doc in results:
    print(f"内容: {doc.content}")
    print(f"来源: {doc.metadata.get('source')}")
    print(f"相似度: {doc.metadata.get('similarity_score')}")
```

## API 接口使用

### 创建知识库

```python
from src.api.api_compat import create_knowledge_base
from src.api.models import KnowledgeBaseRequest

request = KnowledgeBaseRequest(
    kb_name="api_kb",
    chunk_size=500,
    chunk_overlap=50,
    file_paths=["./docs/sample.pdf"]  # 可选：立即添加文档
)

result = await create_knowledge_base(request)
```

### 搜索知识库

```python
from src.api.api_compat import search_knowledge_base

results = await search_knowledge_base(
    kb_name="api_kb",
    query="搜索查询",
    k=5
)

for doc in results["results"]:
    print(f"内容: {doc['content']}")
    print(f"相似度: {doc['score']}")
```

## 在 RAG Agent 中使用

```python
from src.agents.rag_agent import create_rag_agent
from src.config import SystemConfig
from src.knowledge.kb_manager import KnowledgeBaseManager

# 配置 LLM
config = SystemConfig()
llm = config.create_client(provider="deepseek")

# 获取知识库
kb_manager = KnowledgeBaseManager()
kb = kb_manager.get_knowledge_base("my_kb")

# 创建 RAG Agent
agent = create_rag_agent(
    llm=llm,
    knowledge_base=kb,
    system_prompt="你是一个基于知识库的AI助手",
    checkpointer=InMemorySaver()
)

# 使用 Agent
result = await agent.ainvoke({
    "messages": [HumanMessage(content="关于某某话题的问题")],
    "query": "关于某某话题的问题"
})
```

## 配置选项

### 嵌入模型配置

```python
# 本地嵌入模型
embedder_config = {
    "embedder_type": "sentence_transformers",
    "model_name": "all-MiniLM-L6-v2"  # 轻量级，快速
    # 或 "paraphrase-multilingual-MiniLM-L12-v2" 多语言
    # 或 "text2vec-large-chinese" 中文专用
}

# OpenAI 嵌入模型
embedder_config = {
    "embedder_type": "openai",
    "model_name": "text-embedding-3-small"
}
```

### 向量存储配置

```python
# Chroma（推荐，持久化存储）
vector_store_config = {
    "store_type": "chroma",
    "collection_name": "kb_name",
    "persist_directory": "./data/vector_stores/kb_name"
}

# FAISS（内存存储）
vector_store_config = {
    "store_type": "faiss",
    "index_path": "./data/vector_stores/kb_name.index"
}
```

### 文本分割配置

```python
# 递归分割器
text_splitter_config = {
    "splitter_type": "recursive",
    "chunk_size": 500,
    "chunk_overlap": 50,
    "separators": ["\n\n", "\n", " ", ""]
}

# 语义分割器（实验性）
text_splitter_config = {
    "splitter_type": "semantic",
    "chunk_size": 500,
    "min_chunk_size": 100
}
```

## 支持的文件格式

- **文本文件**: `.txt`, `.md`, `.markdown`
- **Office文档**: `.docx`
- **PDF文档**: `.pdf`
- **网页内容**: 通过URL加载

## 运行演示

```bash
# 运行完整演示
python examples/knowledge_base_usage_demo.py

# 或者运行特定部分的演示
python examples/create_rag_agent_demo.py  # 包含知识库部分
```

## 故障排除

### 1. 嵌入模型加载失败

**问题**: `ModuleNotFoundError` 或下载失败
**解决**:
```bash
# 安装 sentence-transformers
pip install sentence-transformers

# 如果网络问题，可以指定本地缓存
export TRANSFORMERS_CACHE=./cache
```

### 2. 向量存储初始化失败

**问题**: Chroma 或 FAISS 初始化失败
**解决**:
- 确保数据目录有写权限
- 检查磁盘空间
- 对于 Chroma，确保安装了 `chromadb`

### 3. 文档处理失败

**问题**: 某些文档无法加载
**解决**:
- 检查文件是否存在且可读
- 对于PDF，确保安装了 `pypdf`
- 对于DOCX，确保安装了 `python-docx`

### 4. 搜索无结果

**问题**: 搜索返回空结果
**解决**:
- 检查知识库是否成功创建并添加了文档
- 尝试不同的查询方式
- 检查嵌入模型和查询是否匹配

## 性能优化

### 1. 选择合适的嵌入模型

- **快速检索**: `all-MiniLM-L6-v2` (速度快，质量一般)
- **高质量**: `text-embedding-3-small` (OpenAI，质量好但需API)
- **中文优化**: `text2vec-large-chinese` (中文内容推荐)

### 2. 调整分块参数

```python
# 短文档推荐
chunk_size: 300-500
chunk_overlap: 50-100

# 长文档推荐
chunk_size: 1000-1500
chunk_overlap: 100-200
```

### 3. 数据库模式

```python
# 生产环境推荐使用数据库
kb_manager = KnowledgeBaseManager(use_database=True)

# 开发/测试可以使用内存模式
kb_manager = KnowledgeBaseManager(use_database=False)
```

## 扩展开发

### 添加新的文档加载器

```python
# 在 document_loaders/ 下添加新加载器
class CustomLoader(BaseLoader):
    def load(self, file_path: str) -> List[Document]:
        # 实现加载逻辑
        pass
```

### 添加新的嵌入模型

```python
# 在 embeddings/ 下添加新嵌入器
class CustomEmbedder(BaseEmbedder):
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        # 实现嵌入逻辑
        pass
```

## 相关文件

- `examples/knowledge_base_usage_demo.py` - 完整使用演示
- `examples/create_rag_agent_demo.py` - RAG集成演示
- `src/knowledge/kb_manager.py` - 知识库管理器
- `src/api/api_compat.py` - API接口
- `src/api/routes/knowledge_base_routes.py` - API路由实现
