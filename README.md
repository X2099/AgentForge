# AgentForge — 基于 LangGraph 的 AI 智能体产品实践

**AgentForge** 是一个真实可运行的 AI 应用，采用产品化方式呈现 **LangGraph 框架的工程实践方法**。  
它不仅是一个 Demo，更是一套可扩展、可部署、有完整 UI 的智能体产品模板，用于探索：

- 如何在实际产品中使用 LangGraph 构建智能体  
- 如何组织 Agent 状态、工具、RAG、工作流  
- 如何将 LangGraph 与 Web UI、用户会话、知识库系统结合  
- 如何把智能体工程化为一个真正可用的应用  

本项目适合作为：

- 🧠 LangGraph 实战入门  
- 🛠️ 企业级智能体系统的参考框架  
- 🚀 个人开源作品集（展示工程能力）  
- 🧪 Agent 研发与实验平台  

---

## 🌟 核心功能（产品化）

### 🧠 1. 智能体对话（基于 LangGraph）
- 多轮对话状态管理  
- 工具调用链（Function Calling）  
- 插拔式工具系统（Search、Web API、计算函数等）  
- 可视化工作流（规划 → 执行）  

### 📚 2. 知识库（RAG）
- 文档上传（PDF / TXT / Markdown / DOCX）  
- 自动切片、Embedding  
- 向量检索（FAISS）  
- 与 Agent 对话无缝融合  

### 🔧 3. 工具系统
- 定义 Python 函数 → 自动注册为工具  
- 在 LangGraph 节点中被调用  
- 可扩展第三方 API 工具（搜索、天气、数据库等）

### 🖥️ 4. Streamlit Web UI
- 产品级多会话聊天界面  
- 知识库管理后台  
- 模型开关 & 参数配置  
- 执行链路显示（未来版本）  

---

## 🏗️ 为什么要用 LangGraph？

本项目展示 LangGraph 在真实产品中的三个关键价值：

### 1. **可控性强的对话流程**
你可以显式地定义：
- 节点（工具节点、RAG 节点、模型代理节点）  
- 条件分支  
- 循环（tool-retry）  
- 规划 & 执行模式  

### 2. **可追踪、可调试**
通过图结构可以清晰看到智能体的执行链路。

### 3. **可扩展、可维护**
相比“端到端 Prompt 方式”，LangGraph 更适合生产环境和团队协作。

---

## 📁 项目结构

```
AgentForge/
├── agent/          # Agent 逻辑
├── rag/            # RAG 管线：加载、切片、向量化、检索
├── ui/             # Streamlit 前端
├── config/         # 配置相关
└── README.md
```