# -*- coding: utf-8 -*-
"""
@File    : tool_nodes.py
@Time    : 2025/12/9 10:18
@Desc    : 
"""
from typing import Dict, Any, List
import json
from ..nodes.base_node import Node
from ..state.base_state import AgentState


class ToolExecutorNode(Node):
    """工具执行节点"""

    def __init__(self, name: str, tool_registry):
        super().__init__(name, "tool_executor", "执行工具调用")
        self.tool_registry = tool_registry

    def execute(self, state: AgentState) -> Dict[str, Any]:
        """执行工具调用"""
        tool_calls = state.get("tool_calls", [])
        tool_outputs = []

        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("arguments", {})

            if tool_name in self.tool_registry:
                try:
                    # 执行工具
                    tool = self.tool_registry[tool_name]
                    output = tool.execute(tool_args)

                    tool_outputs.append({
                        "tool_name": tool_name,
                        "arguments": tool_args,
                        "output": output,
                        "success": True
                    })

                except Exception as e:
                    tool_outputs.append({
                        "tool_name": tool_name,
                        "arguments": tool_args,
                        "output": f"工具执行失败: {str(e)}",
                        "success": False,
                        "error": str(e)
                    })
            else:
                tool_outputs.append({
                    "tool_name": tool_name,
                    "arguments": tool_args,
                    "output": f"未知工具: {tool_name}",
                    "success": False,
                    "error": "Tool not found"
                })

        # 更新状态
        result = {
            "tool_outputs": tool_outputs,
            "last_tool_calls": tool_calls,
            "next_node": "llm"
        }

        # 添加工具输出到消息历史
        if "messages" in state:
            for output in tool_outputs:
                state["messages"].append({
                    "type": "tool",
                    "content": json.dumps(output, ensure_ascii=False),
                    "metadata": {
                        "tool_name": output["tool_name"],
                        "success": output["success"]
                    }
                })

        return result


class ToolSelectorNode(Node):
    """工具选择节点"""

    def __init__(self, name: str, tool_registry):
        super().__init__(name, "tool_selector", "选择合适的工具")
        self.tool_registry = tool_registry

    def execute(self, state: AgentState) -> Dict[str, Any]:
        """选择工具"""
        # 分析当前任务，选择最合适的工具
        current_task = state.get("current_task", "")
        available_tools = list(self.tool_registry.keys())

        # 简单的工具匹配逻辑
        selected_tools = self._match_tools(current_task, available_tools)

        return {
            "selected_tools": selected_tools,
            "available_tools": available_tools,
            "next_node": "tool_executor" if selected_tools else "llm"
        }

    def _match_tools(self, task: str, available_tools: List[str]) -> List[str]:
        """匹配工具"""
        # 简单的关键词匹配
        task_lower = task.lower()
        matched_tools = []

        tool_keywords = {
            "search": ["搜索", "查询", "查找", "search", "query"],
            "calculate": ["计算", "数学", "算", "calculate", "math"],
            "read_file": ["读取", "文件", "打开", "read", "file"],
            "write_file": ["写入", "保存", "写", "write", "save"],
            "web_scrape": ["网页", "抓取", "爬取", "scrape", "crawl"]
        }

        for tool_name in available_tools:
            tool_name_lower = tool_name.lower()

            # 直接匹配
            if any(keyword in task_lower for keyword in tool_name_lower.split('_')):
                matched_tools.append(tool_name)
                continue

            # 关键词匹配
            for category, keywords in tool_keywords.items():
                if category in tool_name_lower:
                    if any(keyword in task_lower for keyword in keywords):
                        matched_tools.append(tool_name)
                        break

        return list(set(matched_tools))
