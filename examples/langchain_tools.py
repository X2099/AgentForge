# -*- coding: utf-8 -*-
"""
@File    : langchain_tools.py
@Time    : 2025/12/25 18:21
@Desc    : 
"""
from langchain_community.tools import DuckDuckGoSearchRun

search = DuckDuckGoSearchRun()

result = search.invoke("世界第二高峰是哪座?")

print(result)
