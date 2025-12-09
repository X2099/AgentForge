# -*- coding: utf-8 -*-
"""
@File    : local_provider.py
@Time    : 2025/12/9 10:36
@Desc    : 
"""
from typing import List, Dict, Any, Optional, AsyncGenerator
from typing import Generator as SyncGenerator
import time
import logging
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import asyncio
from threading import Lock

from .base_provider import BaseProvider
from ..schemas.messages import ChatRequest, ChatResponse, StreamResponse

logger = logging.getLogger(__name__)


class LocalProvider(BaseProvider):
    """本地模型提供商（使用Hugging Face Transformers）"""

    def __init__(self,
                 model_name: str = "Qwen/Qwen2.5-7B-Instruct",
                 model_path: Optional[str] = None,
                 device: Optional[str] = None,
                 load_in_8bit: bool = False,
                 load_in_4bit: bool = False,
                 trust_remote_code: bool = True,
                 **kwargs):
        """
        初始化本地模型提供商

        Args:
            model_name: 模型名称（Hugging Face路径）
            model_path: 本地模型路径
            device: 运行设备（cpu/cuda）
            load_in_8bit: 是否8bit量化
            load_in_4bit: 是否4bit量化
            trust_remote_code: 是否信任远程代码
            **kwargs: 其他参数
        """
        super().__init__(model_name=model_name, **kwargs)
        self.model_path = model_path or model_name
        self.load_in_8bit = load_in_8bit
        self.load_in_4bit = load_in_4bit
        self.trust_remote_code = trust_remote_code

        # 自动选择设备
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        # 线程安全锁
        self._lock = Lock()

        # 加载模型（延迟加载）
        self.tokenizer = None
        self.model = None
        self._is_loaded = False

    def _initialize_client(self):
        """延迟初始化模型（在实际使用时加载）"""
        logger.info(f"本地模型提供商初始化 - 模型: {self.model_name}, 设备: {self.device}")

    def _ensure_loaded(self):
        """确保模型已加载"""
        if not self._is_loaded:
            with self._lock:
                if not self._is_loaded:
                    self._load_model()
                    self._is_loaded = True

    def _load_model(self):
        """加载模型和tokenizer"""
        try:
            logger.info(f"开始加载模型: {self.model_path}")

            # 加载tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=self.trust_remote_code
            )

            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            # 准备加载参数
            load_kwargs = {
                "trust_remote_code": self.trust_remote_code,
                "device_map": "auto" if self.device == "cuda" else None,
            }

            # 量化配置
            if self.load_in_8bit:
                load_kwargs["load_in_8bit"] = True
            elif self.load_in_4bit:
                load_kwargs["load_in_4bit"] = True

            # 加载模型
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                **load_kwargs
            )

            # 如果不自动映射设备，手动移动
            if self.device != "auto" and hasattr(self.model, "to"):
                self.model.to(self.device)

            # 设置为评估模式
            self.model.eval()

            logger.info(f"模型加载完成: {self.model_path}, 参数量: {self.model.num_parameters():,}")

        except Exception as e:
            logger.error(f"加载模型失败: {str(e)}")
            raise

    def _call_api(self, request: ChatRequest) -> ChatResponse:
        """调用本地模型"""
        self._ensure_loaded()

        try:
            start_time = time.time()

            # 准备输入
            prompt = self._format_prompt(request.messages)

            # Tokenize
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=self._get_max_context_length() - request.max_tokens if request.max_tokens else self._get_max_context_length()
            )

            # 移动到设备
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # 生成参数
            generate_kwargs = {
                "max_new_tokens": request.max_tokens or 512,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "do_sample": request.temperature > 0,
                "pad_token_id": self.tokenizer.pad_token_id,
                "eos_token_id": self.tokenizer.eos_token_id,
            }

            # 生成
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    **generate_kwargs
                )

            # 解码
            response_text = self.tokenizer.decode(
                outputs[0][len(inputs['input_ids'][0]):],
                skip_special_tokens=True
            )

            # 计算tokens
            prompt_tokens = inputs['input_ids'].shape[1]
            completion_tokens = outputs.shape[1] - prompt_tokens

            # 创建响应
            response = ChatResponse(
                id=f"local_{int(time.time())}",
                created=int(time.time()),
                model=self.model_name,
                choices=[{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    },
                    "finish_reason": "stop"
                }],
                usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens
                }
            )

            # 更新统计
            self._update_stats(response)

            elapsed = time.time() - start_time
            logger.info(f"本地模型生成完成 - 耗时: {elapsed:.2f}s, "
                        f"Tokens: {completion_tokens}")

            return response

        except Exception as e:
            logger.error(f"本地模型生成失败: {str(e)}")
            raise

    async def _acall_api(self, request: ChatRequest) -> ChatResponse:
        """异步调用本地模型（在线程池中运行）"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._call_api, request)

    def _call_stream_api(self, request: ChatRequest) -> SyncGenerator[StreamResponse, None, None]:
        """本地模型流式生成（简化实现）"""
        # 本地模型流式生成较复杂，这里返回非流式结果
        response = self._call_api(request)

        # 模拟流式响应
        content = response.get_content() or ""
        chunk_size = 10  # 每次返回10个字符

        for i in range(0, len(content), chunk_size):
            yield StreamResponse(
                id=response.id,
                object="chat.completion.chunk",
                created=response.created,
                model=response.model,
                choices=[{
                    "index": 0,
                    "delta": {
                        "content": content[i:i + chunk_size]
                    },
                    "finish_reason": None if i + chunk_size < len(content) else "stop"
                }]
            )

        # 发送结束信号
        yield StreamResponse(
            id=response.id,
            object="chat.completion.chunk",
            created=response.created,
            model=response.model,
            choices=[{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        )

    async def _acall_stream_api(self, request: ChatRequest) -> AsyncGenerator[StreamResponse, None]:
        """异步流式生成"""
        for chunk in self._call_stream_api(request):
            yield chunk

    def _format_prompt(self, messages: List[Dict[str, Any]]) -> str:
        """格式化提示词"""
        # 根据模型类型格式化提示
        prompt_parts = []

        for msg in messages:
            role = msg.role
            content = msg.content

            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"Human: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
            elif role == "tool":
                prompt_parts.append(f"Tool: {content}")

        prompt_parts.append("Assistant:")
        return "\n\n".join(prompt_parts)

    def calculate_cost(self, tokens: int) -> float:
        """本地模型无成本"""
        return 0.0

    def _get_max_context_length(self) -> int:
        """获取最大上下文长度"""
        # 常见模型上下文长度
        context_lengths = {
            "Qwen/Qwen2.5-7B-Instruct": 32768,
            "Qwen/Qwen2.5-14B-Instruct": 32768,
            "THUDM/chatglm3-6b": 8192,
            "baichuan-inc/Baichuan2-7B-Chat": 4096,
            "internlm/internlm2-chat-7b": 32768,
            "mistralai/Mistral-7B-Instruct": 32768,
            "meta-llama/Llama-2-7b-chat-hf": 4096,
        }

        for model_pattern, length in context_lengths.items():
            if model_pattern in self.model_name:
                return length

        return 4096  # 默认值

    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return [
            "Qwen/Qwen2.5-7B-Instruct",
            "Qwen/Qwen2.5-14B-Instruct",
            "THUDM/chatglm3-6b",
            "baichuan-inc/Baichuan2-7B-Chat",
            "internlm/internlm2-chat-7b",
            "mistralai/Mistral-7B-Instruct",
            "meta-llama/Llama-2-7b-chat-hf",
        ]

    def count_tokens(self, text: str) -> int:
        """计算token数量"""
        self._ensure_loaded()
        tokens = self.tokenizer.encode(text, add_special_tokens=False)
        return len(tokens)
