# -*- coding: utf-8 -*-
"""
LLM集成模块 - 基于LangChain实现
"""
from .llm_client import LLMClient
from .config.llm_config import LLMConfig

__all__ = ["LLMClient", "LLMConfig"]
