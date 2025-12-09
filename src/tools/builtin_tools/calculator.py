# -*- coding: utf-8 -*-
"""
@File    : calculator.py
@Time    : 2025/12/9 11:55
@Desc    : 
"""
import math
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class CalculatorTool:
    """计算器工具"""

    def __init__(self):
        # 安全函数白名单
        self.safe_functions = {
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

    def get_tool_schema(self) -> Dict[str, Any]:
        """获取工具模式"""
        return {
            "name": "calculator",
            "description": "执行数学计算",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，例如: '2 + 3 * 4', 'sqrt(16)', 'sin(pi/2)'"
                    },
                    "variables": {
                        "type": "object",
                        "description": "自定义变量",
                        "additionalProperties": {
                            "type": "number"
                        }
                    }
                },
                "required": ["expression"]
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        """执行计算"""
        expression = arguments.get("expression", "")
        variables = arguments.get("variables", {})

        if not expression:
            return "错误：表达式不能为空"

        logger.info(f"执行计算: {expression}")

        try:
            # 安全检查
            if not self._is_safe_expression(expression):
                return "错误：表达式包含不安全字符或函数"

            # 准备执行环境
            env = {**self.safe_functions, **variables}

            # 安全评估
            result = eval(expression, {"__builtins__": {}}, env)

            # 格式化结果
            if isinstance(result, (int, float)):
                if result == int(result):
                    result_str = str(int(result))
                else:
                    result_str = str(round(result, 10)).rstrip('0').rstrip('.')

                return f"{expression} = {result_str}"
            else:
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

    def _is_safe_expression(self, expression: str) -> bool:
        """检查表达式是否安全"""
        # 允许的字符
        safe_chars = set('0123456789+-*/.()[]{} ,!<>=\'\"')
        safe_chars.update(set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_'))

        # 检查字符
        for char in expression:
            if char not in safe_chars:
                return False

        # 检查危险模式
        dangerous_patterns = [
            '__', 'import', 'eval', 'exec', 'compile',
            'open', 'file', 'os.', 'sys.', 'subprocess'
        ]

        for pattern in dangerous_patterns:
            if pattern in expression:
                return False

        return True
