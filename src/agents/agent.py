# -*- coding: utf-8 -*-
"""
@File    : agent.py
@Time    : 2025/12/26 16:16
@Desc    : 
"""
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.store.base import BaseStore
from langgraph.types import Checkpointer


def create_langchain_agent(
        model: str | BaseChatModel,
        tools: list[BaseTool] | None = None,
        system_prompt: str | None = None,
        checkpointer: Checkpointer | None = None,
        store: BaseStore | None = None
):
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
        store=store
    )
