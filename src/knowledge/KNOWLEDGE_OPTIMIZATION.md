# 知识库模块优化方案

## 当前问题分析

### 1. ❌ 未使用LangChain标准组件
- 自定义Document类，而非LangChain的`Document`
- 自定义向量存储接口，而非LangChain的`VectorStore`
- 自定义嵌入器接口，而非LangChain的`Embeddings`
- 自定义文本分割器，而非LangChain的`TextSplitter`

### 2. ❌ 集成度不够
- RAG工作流中的检索逻辑过于简单
- 没有使用LangChain的Retriever接口
- 缺少高级检索功能（如多查询检索、父文档检索等）

### 3. ❌ 异步支持不足
- 文档加载、嵌入、检索都是同步操作
- 缺少批量异步处理

### 4. ❌ 缺少LangGraph集成
- 知识库检索应该作为标准的LangGraph节点
- 应该支持与记忆模块的集成

## 优化方案

### 方案1: 使用LangChain标准组件（推荐）✅

#### 1.1 使用LangChain Document

```python
# 替换自定义Document
from langchain_core.documents import Document

# LangChain Document结构：
# Document(page_content: str, metadata: Dict[str, Any])
```

#### 1.2 使用LangChain VectorStore

```python
# 使用LangChain的标准向量存储
from langchain_community.vectorstores import Chroma, FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings

# 直接使用LangChain的向量存储实现
vector_store = Chroma(
    collection_name="my_kb",
    embedding_function=OpenAIEmbeddings(),
    persist_directory="./data/chroma"
)
```

#### 1.3 使用LangChain TextSplitter

```python
# 使用LangChain的标准文本分割器
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)
```

#### 1.4 使用LangChain DocumentLoaders

```python
# 使用LangChain的文档加载器
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
    BSHTMLLoader
)
```

### 方案2: 使用LangChain Retrievers ✅

#### 2.1 使用标准Retriever接口

```python
from langchain_core.retrievers import BaseRetriever

# 从向量存储创建Retriever
retriever = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 4}
)

# 支持高级检索
from langchain.retrievers import (
    ContextualCompressionRetriever,
    MultiQueryRetriever,
    ParentDocumentRetriever
)
```

### 方案3: 异步优化 ✅

#### 3.1 异步文档加载

```python
async def load_documents_async(file_paths: List[str]):
    """异步加载文档"""
    tasks = [load_single_document_async(path) for path in file_paths]
    return await asyncio.gather(*tasks)
```

#### 3.2 异步嵌入

```python
async def embed_documents_async(texts: List[str]):
    """异步嵌入文档"""
    # 使用LangChain的异步嵌入
    embeddings = await embedder.aembed_documents(texts)
    return embeddings
```

### 方案4: 创建LangGraph检索节点 ✅

#### 4.1 标准化检索节点

```python
def create_knowledge_retrieval_node(
    retriever: BaseRetriever,
    k: int = 4
):
    """创建知识检索节点"""
    async def retrieval_node(state: AgentState) -> Dict[str, Any]:
        # 从状态中提取查询
        query = extract_query_from_state(state)
        
        # 使用Retriever检索
        documents = await retriever.aget_relevant_documents(query)
        
        return {
            "retrieved_documents": documents,
            "retrieved_context": format_documents(documents)
        }
    
    return retrieval_node
```

## 实施步骤

### 阶段1: 基础重构
1. ✅ 替换Document为LangChain Document
2. ✅ 使用LangChain的向量存储实现
3. ✅ 使用LangChain的嵌入器
4. ✅ 使用LangChain的文本分割器

### 阶段2: 高级功能
1. ✅ 实现LangChain Retriever接口
2. ✅ 添加异步支持
3. ✅ 创建LangGraph检索节点

### 阶段3: 优化和集成
1. ✅ 与记忆模块集成
2. ✅ 添加高级检索策略
3. ✅ 性能优化

## 预期收益

1. **更好的兼容性**: 与LangChain生态无缝集成
2. **更丰富的功能**: 利用LangChain的成熟功能
3. **更少的代码**: 减少自定义实现
4. **更好的性能**: 异步支持和优化
5. **更容易扩展**: 使用标准接口


