# create_rag_agent 演示说明

这个演示文件展示了如何使用 `create_rag_agent` 函数创建和配置 RAG（检索增强生成）工作流。

## 功能特性

### 基础演示 (`demo_basic_rag_agent`)
- ✅ 配置 LLM 客户端
- ✅ 加载可用工具
- ✅ **自动查找并配置现有知识库**
- ✅ 创建带知识库的 RAG agent（如果有知识库）
- ✅ 执行简单对话
- ✅ 显示执行结果和状态信息

### 知识库演示 (`demo_rag_with_knowledge_base`)
- ✅ 初始化知识库管理器
- ✅ 创建/使用测试知识库
- ✅ 创建带知识库的 RAG agent
- ✅ 执行基于知识库的查询
- ✅ 显示检索结果和来源信息

## 运行方法

### 1. 安装依赖
确保项目依赖已安装：
```bash
pip install -r requirements.txt
```

### 2. 配置环境变量
根据你的 LLM 提供商设置相应的环境变量：
```bash
# DeepSeek
export DEEPSEEK_API_KEY=your_api_key

# 或者 OpenAI
export OPENAI_API_KEY=your_api_key
```

### 3. 运行演示
```bash
cd /path/to/AgentForge
python examples/create_rag_agent_demo.py
```

## 预期输出

演示会显示：
1. 配置过程和状态
2. 创建 agent 的过程
3. **知识库演示部分会优先使用现有的知识库**
   - 如果有现有知识库，会自动选择第一个使用
   - 如果没有现有知识库，会创建一个示例知识库并添加演示文档
4. 执行对话的结果
5. 工作流执行信息（文档数量、来源等）

## 注意事项

- 如果缺少某些依赖（如向量数据库），知识库演示可能会被跳过
- 演示使用了内存模式的检查点保存器，不需要外部数据库
- **知识库演示会优先使用现有的知识库**，如果希望使用特定的知识库，可以预先创建
- 可以根据需要修改 LLM 提供商和参数配置

## 预先准备知识库（可选）

如果你希望演示使用特定的知识库，可以提前创建：

```python
# 使用知识库使用演示创建知识库
python examples/knowledge_base_usage_demo.py

# 或者直接创建
from src.knowledge.kb_manager import KnowledgeBaseManager

kb_manager = KnowledgeBaseManager()
kb_config = {
    "name": "my_kb",
    "embedder": {"embedder_type": "sentence_transformers"},
    "vector_store": {"store_type": "chroma"}
}
kb = kb_manager.create_knowledge_base(kb_config)
kb_manager.bulk_add_documents("my_kb", ["your_documents.pdf"])
```

## 自定义配置

你可以在演示中修改以下参数：

```python
# 修改 LLM 配置
llm = config.create_client(
    provider="openai",  # 或 "anthropic", "deepseek"
    temperature=0.7,
    max_tokens=1000,
)

# 修改系统提示词
system_prompt="你的自定义提示词"

# 修改测试查询
test_query = "你的测试问题"
```

## 故障排除

1. **ImportError**: 确保项目路径正确添加
2. **API 错误**: 检查 API 密钥和网络连接
3. **依赖缺失**: 安装相应的 Python 包

## 相关文件

- `src/agents/rag_agent.py` - RAG agent 实现
- `src/config/system_config.py` - 系统配置
- `src/tools/tool_manager.py` - 工具管理器
