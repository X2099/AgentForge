# -*- coding: utf-8 -*-
"""
@File    : api_demo.py
@Time    : 2025/12/24 9:51
@Desc    : 
"""
import asyncio

import sys
from pathlib import Path
from pprint import pprint

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from src.api.api_compat import list_knowledge_bases


async def main():
    result = await list_knowledge_bases()
    pprint(result)


if __name__ == '__main__':
    asyncio.run(main())
