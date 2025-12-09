# -*- coding: utf-8 -*-
"""
@File    : base_prompt.py
@Time    : 2025/12/9 10:47
@Desc    : 
"""
from typing import Dict, Any, Optional, List
from abc import ABC
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class BasePrompt(ABC):
    """Prompt基类"""

    def __init__(self,
                 name: str,
                 template: str,
                 description: str = "",
                 variables: Optional[Dict[str, Any]] = None,
                 examples: Optional[List[Dict[str, Any]]] = None):
        """
        初始化Prompt

        Args:
            name: Prompt名称
            template: 模板字符串
            description: 描述
            variables: 变量定义
            examples: 示例列表
        """
        self.name = name
        self.template = template
        self.description = description
        self.variables = variables or {}
        self.examples = examples or []

    def render(self, **kwargs) -> str:
        """渲染Prompt"""
        try:
            # 检查必需变量
            missing_vars = []
            for var_name, var_info in self.variables.items():
                if var_info.get("required", False) and var_name not in kwargs:
                    missing_vars.append(var_name)

            if missing_vars:
                raise ValueError(f"缺少必需变量: {missing_vars}")

            # 渲染模板
            rendered = self.template.format(**kwargs)

            # 添加示例（如果存在）
            if self.examples and kwargs.get("include_examples", True):
                examples_text = self._format_examples()
                rendered = f"{rendered}\n\n{examples_text}"

            return rendered

        except KeyError as e:
            logger.error(f"渲染Prompt失败，缺少变量: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"渲染Prompt失败: {str(e)}")
            raise

    def _format_examples(self) -> str:
        """格式化示例"""
        if not self.examples:
            return ""

        examples_text = "示例：\n"
        for i, example in enumerate(self.examples, 1):
            examples_text += f"\n示例 {i}:\n"

            # 输入
            if "input" in example:
                examples_text += f"输入: {example['input']}\n"

            # 输出
            if "output" in example:
                examples_text += f"输出: {example['output']}\n"

        return examples_text

    def validate_variables(self, **kwargs) -> bool:
        """验证变量"""
        for var_name, var_value in kwargs.items():
            if var_name in self.variables:
                var_info = self.variables[var_name]

                # 检查类型
                expected_type = var_info.get("type", "str")
                if expected_type == "str":
                    if not isinstance(var_value, str):
                        return False
                elif expected_type == "int":
                    if not isinstance(var_value, int):
                        return False
                elif expected_type == "list":
                    if not isinstance(var_value, list):
                        return False
                elif expected_type == "dict":
                    if not isinstance(var_value, dict):
                        return False

        return True

    def get_info(self) -> Dict[str, Any]:
        """获取Prompt信息"""
        return {
            "name": self.name,
            "description": self.description,
            "variables": self.variables,
            "example_count": len(self.examples),
            "template_preview": self.template[:200] + "..." if len(self.template) > 200 else self.template
        }


class PromptManager:
    """Prompt管理器"""

    def __init__(self, prompts_dir: str = "./prompts"):
        self.prompts_dir = Path(prompts_dir)
        self.prompts: Dict[str, BasePrompt] = {}

        # 加载所有Prompt
        self.load_prompts()

    def load_prompts(self):
        """加载所有Prompt"""
        # 确保目录存在
        self.prompts_dir.mkdir(parents=True, exist_ok=True)

        # 查找Prompt文件
        prompt_files = list(self.prompts_dir.glob("*.json")) + \
                       list(self.prompts_dir.glob("*.yaml")) + \
                       list(self.prompts_dir.glob("*.yml"))

        for prompt_file in prompt_files:
            try:
                prompt = self._load_prompt_file(prompt_file)
                self.prompts[prompt.name] = prompt
                logger.info(f"加载Prompt成功: {prompt.name}")
            except Exception as e:
                logger.error(f"加载Prompt失败 {prompt_file}: {str(e)}")

    def _load_prompt_file(self, file_path: Path) -> BasePrompt:
        """从文件加载Prompt"""
        if file_path.suffix == ".json":
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:  # .yaml or .yml
            import yaml
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

        return BasePrompt(
            name=data.get("name", file_path.stem),
            template=data["template"],
            description=data.get("description", ""),
            variables=data.get("variables", {}),
            examples=data.get("examples", [])
        )

    def get_prompt(self, name: str) -> Optional[BasePrompt]:
        """获取Prompt"""
        return self.prompts.get(name)

    def list_prompts(self) -> List[Dict[str, Any]]:
        """列出所有Prompt"""
        return [prompt.get_info() for prompt in self.prompts.values()]

    def add_prompt(self, prompt: BasePrompt):
        """添加Prompt"""
        self.prompts[prompt.name] = prompt

        # 保存到文件
        self._save_prompt(prompt)

    def _save_prompt(self, prompt: BasePrompt):
        """保存Prompt到文件"""
        data = {
            "name": prompt.name,
            "template": prompt.template,
            "description": prompt.description,
            "variables": prompt.variables,
            "examples": prompt.examples
        }

        file_path = self.prompts_dir / f"{prompt.name}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def remove_prompt(self, name: str):
        """移除Prompt"""
        if name in self.prompts:
            del self.prompts[name]

            # 删除文件
            for ext in [".json", ".yaml", ".yml"]:
                file_path = self.prompts_dir / f"{name}{ext}"
                if file_path.exists():
                    file_path.unlink()
                    break
