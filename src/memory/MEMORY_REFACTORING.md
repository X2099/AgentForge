# Memory模块重构说明

## 重构目标

将memory模块重构为使用LangGraph标准的长短期记忆机制。

## 主要变更

### 1. 记忆管理器重构 ✅

**文件**: `src/memory/memory_manager.py` (新建)

- **之前**: 自定义的记忆存储系统，需要手动管理记忆的保存和检索
- **现在**: 基于LangGraph Checkpointer的标准实现

**主要改进**:
- 使用LangGraph的`BaseCheckpointSaver`进行长期记忆管理
- 短期记忆通过StateGraph的`messages`字段自动管理
- 提供记忆总结和检索功能
- 简化的配置和接口

### 2. 记忆节点重构 ✅

**文件**: `src/memory/memory_nodes.py` (新建)

- **之前**: 自定义的记忆节点实现
- **现在**: 标准化的LangGraph节点函数

**主要节点**:
- `create_memory_retrieval_node`: 从长期记忆中检索相关记忆
- `create_memory_summarization_node`: 自动总结历史对话
- `create_memory_update_node`: 更新长期记忆
- `create_memory_truncation_node`: 管理短期记忆（消息截断）

### 3. 架构简化 ✅

- 删除了旧的`langgraph_memory.py`和`langgraph_nodes.py`
- 删除了`short_term`目录
- 统一的记忆管理接口

## LangGraph记忆机制

### 短期记忆

**通过StateGraph的messages字段自动管理**:
- 消息自动通过`add_messages` reducer合并
- 由LangGraph自动处理消息历史
- 无需手动管理消息列表

```python
# 在状态中，messages会自动合并
state = {
    "messages": Annotated[Sequence[BaseMessage], add_messages],
    ...
}
```

### 长期记忆

**通过Checkpointer保存和检索**:
- 使用`SqliteSaver`或`MemorySaver`保存检查点
- 每个`thread_id`对应一个会话的长期记忆
- 可以检索历史检查点获取相关记忆

```python
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn(sqlite3.connect("memory.db"))
compiled_graph = graph.compile(checkpointer=checkpointer)
```

## 使用示例

### 创建带记忆的Agent

```python
from src.core.agents.langgraph_agent import LangGraphAgentBuilder
from src.llm.config.llm_config import LLMConfig
from src.memory import MemoryManager, MemoryConfig
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

# 创建记忆管理器
checkpointer = SqliteSaver.from_conn(sqlite3.connect("memory.db"))
memory_config = MemoryConfig(checkpointer=checkpointer)
memory_manager = MemoryManager(memory_config)

# 创建Agent
llm_client = LLMConfig().create_client()
builder = LangGraphAgentBuilder(
    agent_name="memory_agent",
    llm_client=llm_client
)

# 添加记忆节点（可选）
from src.memory import create_memory_retrieval_node, create_memory_summarization_node

memory_retrieval = create_memory_retrieval_node(memory_manager, llm_client)
memory_summarization = create_memory_summarization_node(memory_manager, llm_client)

builder.add_node("memory_retrieval", memory_retrieval)
builder.add_node("memory_summarization", memory_summarization)

# 编译时传入checkpointer
agent = builder.compile(checkpointer=checkpointer)

# 使用时，记忆会自动保存和检索
result = await agent.ainvoke(
    {"messages": [HumanMessage(content="你好")]},
    config={"configurable": {"thread_id": "session_1"}}
)
```

### 在图中集成记忆节点

```python
# 在build方法中添加记忆节点
def build(self):
    # 添加记忆检索节点
    memory_retrieval = create_memory_retrieval_node(self.memory_manager, self.llm_client)
    self.add_node("memory_retrieval", memory_retrieval)
    
    # 添加消息截断节点
    memory_truncation = create_memory_truncation_node(self.memory_manager)
    self.add_node("memory_truncation", memory_truncation)
    
    # 构建流程
    self.set_entry_point(START)
    self.add_edge(START, "memory_retrieval")
    self.add_edge("memory_retrieval", "memory_truncation")
    self.add_edge("memory_truncation", "agent")
    
    # 添加记忆总结节点（在对话结束时）
    if self.memory_manager.config.summarization_threshold > 0:
        memory_summarization = create_memory_summarization_node(
            self.memory_manager,
            self.llm_client
        )
        self.add_node("memory_summarization", memory_summarization)
        self.add_edge("agent", "memory_summarization")
        self.add_edge("memory_summarization", END)
    else:
        self.add_edge("agent", END)
```

## 记忆工作流程

### 短期记忆流程

1. 消息添加到状态 → LangGraph自动通过`add_messages`合并
2. 消息截断 → `memory_truncation_node`确保消息数量在限制内
3. 自动管理 → 无需手动处理

### 长期记忆流程

1. **记忆检索**: 从历史检查点中检索相关记忆
2. **对话执行**: 使用检索到的记忆增强上下文
3. **记忆保存**: 图执行时自动保存检查点
4. **记忆总结**: 当消息过多时自动总结并压缩

## 配置说明

### MemoryConfig

```python
@dataclass
class MemoryConfig:
    checkpointer: Optional[BaseCheckpointSaver] = None  # Checkpointer实例
    max_message_history: int = 50  # 短期记忆：保留的最近消息数
    summarization_threshold: int = 20  # 触发总结的消息数阈值
    retrieval_k: int = 5  # 检索相关记忆的数量
```

### 使用不同的Checkpointer

```python
# 内存存储（开发/测试）
from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()

# SQLite存储（生产环境）
from langgraph.checkpoint.sqlite import SqliteSaver
checkpointer = SqliteSaver.from_conn(sqlite3.connect("memory.db"))

# 配置记忆管理器
memory_config = MemoryConfig(checkpointer=checkpointer)
memory_manager = MemoryManager(memory_config)
```

## 主要改进

### 之前的问题

1. **复杂的自定义实现**: 需要手动管理记忆的保存和检索
2. **不标准**: 不使用LangGraph的标准机制
3. **难以扩展**: 自定义的抽象层难以扩展

### 重构后的优势

1. **标准化**: 使用LangGraph标准的Checkpointer机制
2. **自动管理**: 短期记忆由LangGraph自动管理
3. **易于集成**: 与LangGraph图无缝集成
4. **更少的代码**: 减少了大量自定义实现
5. **更好的性能**: 利用LangGraph的优化

## 已更新的模块

- ✅ `src/memory/memory_manager.py` - 新建，基于LangGraph标准
- ✅ `src/memory/memory_nodes.py` - 新建，标准化节点函数
- ✅ `src/memory/__init__.py` - 更新导出
- ✅ `src/core/agents/agent_manager.py` - 更新导入
- ❌ `src/memory/langgraph_memory.py` - 已删除
- ❌ `src/memory/langgraph_nodes.py` - 已删除
- ❌ `src/memory/short_term/` - 已删除

## 注意事项

1. **Checkpointer自动保存**: 图的检查点由LangGraph在执行时自动保存，无需手动调用
2. **thread_id管理**: 使用`thread_id`区分不同的会话
3. **消息格式**: 确保消息使用LangChain的`BaseMessage`类型
4. **异步节点**: 记忆节点通常是异步的

## 后续优化

1. 添加语义检索（使用向量数据库）
2. 改进记忆总结质量
3. 添加记忆重要性评分
4. 支持记忆的过期和清理

