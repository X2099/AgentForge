# LLM集成模块重构说明

## 重构目标

将LLM集成模块重构为直接使用LangChain框架的标准实现，简化代码并提高兼容性。

## 主要变更

### 1. LLM客户端重构 ✅

**文件**: `src/llm/llm_client.py`

- **之前**: 自定义的Provider抽象层，需要实现多个接口
- **现在**: 直接使用LangChain的`ChatOpenAI`、`ChatAnthropic`等标准ChatModel

**主要改进**:
- 使用LangChain标准的`BaseChatModel`接口
- 支持`ChatOpenAI`和`ChatAnthropic`
- 自动消息格式转换（字典 ↔ LangChain BaseMessage）
- 原生支持工具绑定（`bind_tools`）
- 统一的同步/异步接口

### 2. 消息格式统一 ✅

- 直接使用LangChain的`BaseMessage`类型
- 自动转换字典格式消息为LangChain消息
- 返回标准的`AIMessage`对象

### 3. 工具集成 ✅

- 使用LangChain的`BaseTool`类型
- 通过`bind_tools()`方法绑定工具
- 自动处理工具调用的解析和执行

### 4. 配置管理 ✅

**文件**: `src/llm/config/llm_config.py`

- 简化配置管理
- 支持OpenAI和Anthropic配置
- 环境变量支持

## 使用示例

### 创建LLM客户端

```python
from src.llm import LLMClient, LLMConfig

# 方式1: 直接创建
client = LLMClient(
    provider_type="openai",
    model_name="gpt-3.5-turbo",
    api_key="your-api-key",
    temperature=0.7
)

# 方式2: 使用配置管理器
config = LLMConfig()
client = config.create_client(
    provider="openai",
    model="gpt-4"
)
```

### 调用LLM

```python
from langchain_core.messages import HumanMessage

# 同步调用
messages = [HumanMessage(content="你好")]
response = client.chat(messages)
print(response.content)

# 异步调用
response = await client.achat(messages)
print(response.content)
```

### 使用工具

```python
from langchain_core.tools import tool

@tool
def get_weather(city: str) -> str:
    """获取天气"""
    return f"{city}的天气：晴朗"

# 调用时绑定工具
messages = [HumanMessage(content="北京天气怎么样？")]
response = client.chat(messages, tools=[get_weather])

# 检查工具调用
if response.tool_calls:
    for tool_call in response.tool_calls:
        print(f"调用工具: {tool_call.name}")
```

## 兼容性说明

### 向后兼容

新的`LLMClient`保持了类似的接口，但返回类型从自定义的`ChatResponse`改为LangChain的`AIMessage`：

- ✅ `chat()` / `achat()` 方法保持相同
- ✅ 支持相同的参数（temperature, max_tokens, tools等）
- ❌ `get_content()` 方法已移除（直接使用`response.content`）
- ❌ `get_tool_calls()` 方法已移除（直接使用`response.tool_calls`）

### 迁移指南

**之前**:
```python
response = client.chat(messages)
content = response.get_content()
tool_calls = response.get_tool_calls()
```

**现在**:
```python
response = await client.achat(messages)
content = response.content
tool_calls = response.tool_calls  # 如果存在
```

## 依赖更新

新增依赖：
- `langchain-openai~=0.2.0` - OpenAI集成
- `langchain-anthropic~=0.2.0` - Anthropic集成

## 架构改进

### 之前的问题

1. **复杂的抽象层**: 需要实现多个Provider接口
2. **消息格式不统一**: 自定义消息格式，需要转换
3. **工具集成复杂**: 需要手动处理工具调用

### 重构后的优势

1. **直接使用LangChain**: 利用成熟的框架和生态
2. **标准化消息格式**: 使用LangChain标准消息类型
3. **原生工具支持**: LangChain原生工具绑定
4. **更好的兼容性**: 与LangGraph完美集成
5. **更少的代码**: 减少了大量自定义实现

## 已更新的模块

- ✅ `src/llm/llm_client.py` - 重构为LangChain实现
- ✅ `src/llm/config/llm_config.py` - 更新配置管理
- ✅ `src/core/agents/langgraph_agent.py` - 适配新的LLM客户端
- ✅ `src/workflows/conversation_workflow.py` - 适配新接口
- ✅ `src/workflows/rag_workflow.py` - 适配新接口
- ✅ `requirements.txt` - 添加LangChain依赖

## 注意事项

1. **异步接口**: 推荐使用`achat()`进行异步调用
2. **消息格式**: 可以使用字典或LangChain BaseMessage
3. **工具调用**: 工具必须是LangChain `BaseTool`类型
4. **错误处理**: 使用标准的LangChain异常处理

## 后续优化

1. 支持更多提供商（如本地模型）
2. 添加流式响应优化
3. 完善错误处理和重试机制
4. 添加性能监控

