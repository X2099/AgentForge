# -*- coding: utf-8 -*-
"""
@File    : stdio_transport.py
@Time    : 2025/12/9 11:48
@Desc    : STDIO传输
"""
import sys
import json
import asyncio
from typing import AsyncGenerator, Optional, Callable, Any
import logging
from pathlib import Path

from ..schemas.messages import MCPMessageParser, MCPMessage

logger = logging.getLogger(__name__)


class StdioTransport:
    """STDIO传输实现"""

    def __init__(self,
                 stdin=None,
                 stdout=None,
                 stderr=None):
        """
        初始化STDIO传输

        Args:
            stdin: 标准输入流
            stdout: 标准输出流
            stderr: 标准错误流
        """
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self.stderr = stderr or sys.stderr

        # 缓冲处理
        self.buffer = ""
        self.buffer_lock = asyncio.Lock()

        # 消息处理回调
        self.message_handler: Optional[Callable[[MCPMessage], Any]] = None

        logger.info("STDIO传输初始化完成")

    async def read_message(self) -> Optional[MCPMessage]:
        """读取消息"""
        try:
            # 读取一行
            line = await self._read_line()
            if not line:
                return None

            # 解析消息
            message = MCPMessageParser.parse_message(line)
            logger.debug(f"收到消息: {message}")
            return message

        except Exception as e:
            logger.error(f"读取消息失败: {str(e)}")
            return None

    async def _read_line(self) -> Optional[str]:
        """读取一行"""
        try:
            if hasattr(self.stdin, 'readline'):
                if asyncio.iscoroutinefunction(self.stdin.readline):
                    line = await self.stdin.readline()
                else:
                    # 在事件循环中运行阻塞调用
                    line = await asyncio.get_event_loop().run_in_executor(
                        None, self.stdin.readline
                    )

                if line:
                    return line.rstrip('\n')
            return None
        except Exception as e:
            logger.error(f"读取行失败: {str(e)}")
            return None

    async def write_message(self, message: MCPMessage) -> bool:
        """写入消息"""
        try:
            # 序列化消息
            serialized = MCPMessageParser.serialize_message(message)

            # 添加换行符
            output = serialized + '\n'

            # 写入输出流
            if hasattr(self.stdout, 'write'):
                if asyncio.iscoroutinefunction(self.stdout.write):
                    await self.stdout.write(output)
                else:
                    # 在事件循环中运行阻塞调用
                    await asyncio.get_event_loop().run_in_executor(
                        None, lambda: self.stdout.write(output)
                    )

                if hasattr(self.stdout, 'flush'):
                    if asyncio.iscoroutinefunction(self.stdout.flush):
                        await self.stdout.flush()
                    else:
                        await asyncio.get_event_loop().run_in_executor(
                            None, self.stdout.flush
                        )

            logger.debug(f"发送消息: {message}")
            return True

        except Exception as e:
            logger.error(f"写入消息失败: {str(e)}")
            return False

    async def write_error(self, error_message: str):
        """写入错误消息到stderr"""
        try:
            if self.stderr:
                if hasattr(self.stderr, 'write'):
                    if asyncio.iscoroutinefunction(self.stderr.write):
                        await self.stderr.write(error_message + '\n')
                    else:
                        await asyncio.get_event_loop().run_in_executor(
                            None, lambda: self.stderr.write(error_message + '\n')
                        )

                    if hasattr(self.stderr, 'flush'):
                        if asyncio.iscoroutinefunction(self.stderr.flush):
                            await self.stderr.flush()
                        else:
                            await asyncio.get_event_loop().run_in_executor(
                                None, self.stderr.flush
                            )
        except Exception as e:
            logger.error(f"写入错误消息失败: {str(e)}")

    async def listen(self,
                     message_handler: Callable[[MCPMessage], Any],
                     exit_on_close: bool = True):
        """
        监听消息

        Args:
            message_handler: 消息处理函数
            exit_on_close: 输入关闭时是否退出
        """
        self.message_handler = message_handler

        logger.info("开始监听STDIO消息")

        try:
            while True:
                # 读取消息
                message = await self.read_message()
                if message is None:
                    if exit_on_close:
                        logger.info("输入流关闭，退出监听")
                        break
                    else:
                        await asyncio.sleep(0.1)
                        continue

                # 处理消息
                try:
                    if self.message_handler:
                        await self.message_handler(message)
                except Exception as e:
                    logger.error(f"处理消息失败: {str(e)}")

        except KeyboardInterrupt:
            logger.info("收到中断信号，停止监听")
        except Exception as e:
            logger.error(f"监听失败: {str(e)}")

    async def close(self):
        """关闭传输"""
        # STDIO传输通常不需要特殊清理
        logger.info("STDIO传输关闭")


class AsyncStdioTransport(StdioTransport):
    """异步STDIO传输"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

    async def setup(self):
        """设置异步流"""
        try:
            # 创建异步流
            loop = asyncio.get_event_loop()
            self._reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(self._reader)

            # 将标准输入连接到reader
            await loop.connect_read_pipe(lambda: protocol, self.stdin)

            # 创建writer用于标准输出
            transport, protocol = await loop.connect_write_pipe(
                asyncio.streams.FlowControlMixin,
                self.stdout
            )
            self._writer = asyncio.StreamWriter(
                transport, protocol, self._reader, loop
            )

            logger.info("异步STDIO传输设置完成")

        except Exception as e:
            logger.error(f"设置异步STDIO传输失败: {str(e)}")
            raise

    async def read_message(self) -> Optional[MCPMessage]:
        """异步读取消息"""
        if not self._reader:
            await self.setup()

        try:
            # 读取一行
            line_bytes = await self._reader.readline()
            if not line_bytes:
                return None

            line = line_bytes.decode('utf-8').rstrip('\n')

            # 解析消息
            message = MCPMessageParser.parse_message(line)
            logger.debug(f"收到消息: {message}")
            return message

        except Exception as e:
            logger.error(f"异步读取消息失败: {str(e)}")
            return None

    async def write_message(self, message: MCPMessage) -> bool:
        """异步写入消息"""
        if not self._writer:
            await self.setup()

        try:
            # 序列化消息
            serialized = MCPMessageParser.serialize_message(message)

            # 写入并刷新
            self._writer.write((serialized + '\n').encode('utf-8'))
            await self._writer.drain()

            logger.debug(f"发送消息: {message}")
            return True

        except Exception as e:
            logger.error(f"异步写入消息失败: {str(e)}")
            return False

    async def close(self):
        """关闭异步传输"""
        try:
            if self._writer:
                self._writer.close()
                await self._writer.wait_closed()
        except Exception as e:
            logger.error(f"关闭异步STDIO传输失败: {str(e)}")

        logger.info("异步STDIO传输关闭")
