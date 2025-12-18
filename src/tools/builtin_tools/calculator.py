# -*- coding: utf-8 -*-
"""
@Desc    : LangChain 原生格式的计算器工具
"""
import logging
import math
from typing import Dict, Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# 参数模式
class CalculatorArgs(BaseModel):
    expression: str = Field(..., description="数学表达式，例如 '2 + 3 * 4', 'sqrt(16)', 'sin(pi/2)'")
    variables: Optional[Dict[str, float]] = Field(default=None, description="可选的自定义变量")


SAFE_FUNCTIONS = {
    'sqrt': math.sqrt,
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'asin': math.asin,
    'acos': math.acos,
    'atan': math.atan,
    'log': math.log,
    'log10': math.log10,
    'exp': math.exp,
    'pi': math.pi,
    'e': math.e,
    'abs': abs,
    'round': round,
    'ceil': math.ceil,
    'floor': math.floor,
}


def _is_safe_expression(expression: str) -> bool:
    # 允许的字符
    safe_chars = set('0123456789+-*/.()[]{} ,!<>=\'"')
    safe_chars.update(set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_'))

    for char in expression:
        if char not in safe_chars:
            return False

    dangerous_patterns = [
        '__', 'import', 'eval', 'exec', 'compile',
        'open', 'file', 'os.', 'sys.', 'subprocess'
    ]
    return not any(pattern in expression for pattern in dangerous_patterns)


def _calculate(expression: str, variables: Optional[Dict[str, float]] = None) -> str:
    if not expression:
        return "错误：表达式不能为空"

    logger.info(f"执行计算: {expression}")

    if not _is_safe_expression(expression):
        return "错误：表达式包含不安全字符或函数"

    env = {**SAFE_FUNCTIONS, **(variables or {})}
    try:
        result = eval(expression, {"__builtins__": {}}, env)
        if isinstance(result, (int, float)):
            if result == int(result):
                result_str = str(int(result))
            else:
                result_str = str(round(result, 10)).rstrip('0').rstrip('.')
            return f"{expression} = {result_str}"
        return f"结果: {result}"
    except ZeroDivisionError:
        return "错误：除以零"
    except ValueError as e:
        return f"计算错误: {str(e)}"
    except SyntaxError:
        return "错误：表达式语法错误"
    except Exception as e:
        logger.error(f"计算失败: {str(e)}")
        return f"计算失败: {str(e)}"


calculator_tool = StructuredTool.from_function(
    func=_calculate,
    name="calculator",
    description="执行数学计算，支持常用三角/对数/指数等函数",
    args_schema=CalculatorArgs,
)

__all__ = ["calculator_tool", "CalculatorArgs"]
