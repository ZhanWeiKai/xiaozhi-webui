import asyncio
import signal
import websockets
import json
import numpy as np
import requests
from websockets.exceptions import ConnectionClosedOK
from urllib.parse import urlparse, urlencode
from ..utils.device import get_local_ip
from ..utils.audio import pcm_to_opus, decoder, AudioProcessor
from logging import getLogger

logger = getLogger(__name__)

# 内网地址 → 外网地址替换映射（参考 xiaozhi-test）
INTERNAL_EXTERNAL_MAP = {
    "10.88.1.": "xiaozhi-wstest.jamesweb.org/xiaozhi",
}


class WebSocketProxy:
    def __init__(
        self,
        device_id: str,
        client_id: str,
        ota_version_url: str,
        proxy_host: str | None,
        proxy_port: int | None,
        token: str,
    ):
        self.device_id = device_id
        self.client_id = client_id
        self.ota_version_url = ota_version_url
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.token = token
        self.ota_token = ""
        self.websocket_url = ""

        self.audio_processor = AudioProcessor(960)
        self.decoder = decoder
        self.audio_buffer: bytearray = bytearray()
        self.is_first_audio: bool = True
        self.total_samples: int = 0
        self.audio_lock = asyncio.Lock()
        self.shutdown_event = asyncio.Event()

        self._update_ota_address()

    def _replace_internal_url(self, url: str) -> str:
        """内网不可达时替换为外网地址"""
        import socket
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or 80

        try:
            with socket.create_connection((host, port), timeout=3):
                logger.info(f"内网地址可达，直接使用: {host}:{port}")
                return url
        except (socket.timeout, OSError):
            pass

        for internal_prefix, external_domain in INTERNAL_EXTERNAL_MAP.items():
            if internal_prefix in url:
                new_scheme = "wss" if parsed.scheme == "ws" else parsed.scheme
                url = f"{new_scheme}://{external_domain}{parsed.path}"
                if parsed.query:
                    url += f"?{parsed.query}"
                logger.info(f"内网不可达，地址替换: {host} → {external_domain}")
                break
        return url

    def _update_ota_address(self):
        """通过 OTA 接口获取 WebSocket 地址和 token"""
        headers = {
            "Device-Id": self.device_id,
            "Client-Id": self.client_id,
            "Content-Type": "application/json",
        }

        payload = {
            "version": 2,
            "flash_size": 16777216,
            "psram_size": 0,
            "minimum_free_heap_size": 8318916,
            "mac_address": self.device_id,
            "uuid": self.client_id,
            "chip_model_name": "esp32s3",
            "chip_info": {"model": 9, "cores": 2, "revision": 2, "features": 18},
            "application": {
                "name": "xiaozhi",
                "version": "1.1.2",
                "idf_version": "v5.3.2-dirty",
            },
            "partition_table": [],
            "ota": {"label": "factory"},
            "board": {
                "type": "bread-compact-wifi",
                "ip": get_local_ip(),
                "mac": self.device_id,
            },
        }

        try:
            response = requests.post(
                self.ota_version_url,
                headers=headers,
                json=payload,
                timeout=10,
            )

            if response.status_code != 200:
                logger.error(f"OTA 服务器错误: HTTP {response.status_code}")
                raise ValueError(f"OTA 服务器返回错误状态码: {response.status_code}")

            response_data = response.json()
            logger.info(f"OTA 响应: {json.dumps(response_data, indent=2, ensure_ascii=False)}")

            if "websocket" in response_data:
                ws_info = response_data["websocket"]
                ws_url = ws_info.get("url", "")
                self.ota_token = ws_info.get("token", "")

                self.websocket_url = self._replace_internal_url(ws_url)
                logger.info(f"OTA WebSocket 地址: {ws_url} → {self.websocket_url}")
                logger.info(f"OTA Token 已获取: {self.ota_token[:20]}...")
            else:
                logger.error(f"OTA 响应中没有 websocket 信息: {response_data}")
                raise ValueError("OTA 响应中没有 websocket 信息")

        except requests.Timeout:
            logger.error("OTA 请求超时")
            raise ValueError("OTA 请求超时，请稍后重试")

        except requests.RequestException as e:
            logger.error(f"OTA 请求失败: {e}")
            raise ValueError("无法连接到 OTA 服务器，请检查网络连接")

    def _build_ws_url(self) -> str:
        """构建带认证参数的 WebSocket URL"""
        params = {
            "authorization": f"Bearer {self.ota_token}",
            "device-id": self.device_id,
            "client-id": self.client_id,
        }
        separator = "&" if "?" in self.websocket_url else "?"
        return f"{self.websocket_url}{separator}{urlencode(params)}"

    def create_wav_header(self, total_samples):
        """创建 Wave 文件头"""
        header = bytearray(44)

        header[0:4] = b"RIFF"
        header[4:8] = (total_samples * 2 + 36).to_bytes(4, "little")
        header[8:12] = b"WAVE"

        header[12:16] = b"fmt "
        header[16:20] = (16).to_bytes(4, "little")
        header[20:22] = (1).to_bytes(2, "little")
        header[22:24] = (1).to_bytes(2, "little")
        header[24:28] = (16000).to_bytes(4, "little")
        header[28:32] = (32000).to_bytes(4, "little")
        header[32:34] = (2).to_bytes(2, "little")
        header[34:36] = (16).to_bytes(2, "little")

        header[36:40] = b"data"
        header[40:44] = (total_samples * 2).to_bytes(4, "little")

        return header

    async def proxy_handler(self, websocket):
        """来自浏览器的 WebSocket 连接"""
        try:
            ws_url = self._build_ws_url()
            logger.info(f"正在连接 xiaozhi-server: {self.websocket_url}")

            async with websockets.connect(ws_url) as server_ws:
                logger.info("已连接至 xiaozhi-server")
                await self._handle_proxy_communication(websocket, server_ws)

        except ConnectionClosedOK:
            logger.info("xiaozhi-server 正常关闭连接")
        except Exception as e:
            logger.error(f"代理失败: {e}")
        finally:
            logger.info("客户端连接关闭")

    async def _handle_proxy_communication(self, websocket, server_ws):
        """处理代理通信"""
        client_to_server = asyncio.create_task(
            self.handle_client_messages(websocket, server_ws)
        )
        server_to_client = asyncio.create_task(
            self.handle_server_messages(server_ws, websocket)
        )

        done, pending = await asyncio.wait(
            [client_to_server, server_to_client],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()

    async def handle_server_messages(self, server_ws, client_ws):
        """处理来自 xiaozhi-server 的消息"""
        try:
            async for message in server_ws:
                if isinstance(message, str):
                    logger.info(f"[服务端→客户端] {message[:200]}")
                    try:
                        msg_data = json.loads(message)
                        if (
                            msg_data.get("type") == "tts"
                            and msg_data.get("state") == "start"
                        ):
                            if len(self.audio_buffer) > 44:
                                async with self.audio_lock:
                                    chunk_size = (self.total_samples * 2 + 36).to_bytes(
                                        4, "little"
                                    )
                                    subchunk2_size = (self.total_samples * 2).to_bytes(
                                        4, "little"
                                    )
                                    self.audio_buffer[4:8] = chunk_size
                                    self.audio_buffer[40:44] = subchunk2_size
                                    await client_ws.send(bytes(self.audio_buffer))
                            self.audio_buffer = bytearray()
                            self.is_first_audio = True
                            self.total_samples = 0
                        elif (
                            msg_data.get("type") == "tts"
                            and msg_data.get("state") == "stop"
                        ):
                            if len(self.audio_buffer) > 44:
                                async with self.audio_lock:
                                    chunk_size = (self.total_samples * 2 + 36).to_bytes(
                                        4, "little"
                                    )
                                    subchunk2_size = (self.total_samples * 2).to_bytes(
                                        4, "little"
                                    )
                                    self.audio_buffer[4:8] = chunk_size
                                    self.audio_buffer[40:44] = subchunk2_size
                                    await client_ws.send(bytes(self.audio_buffer))
                                    self.audio_buffer = bytearray()
                                    self.is_first_audio = True
                                    self.total_samples = 0

                        await client_ws.send(message)
                    except json.JSONDecodeError:
                        await client_ws.send(message)
                else:
                    async with self.audio_lock:
                        try:
                            pcm_data = self.decoder.decode(message, 960)

                            if pcm_data:
                                samples = len(pcm_data) // 2
                                self.total_samples += samples

                                if self.is_first_audio:
                                    self.audio_buffer.extend(
                                        self.create_wav_header(self.total_samples)
                                    )
                                    self.is_first_audio = False

                                self.audio_buffer.extend(pcm_data)

                                if len(self.audio_buffer) >= 64044:
                                    chunk_size = (self.total_samples * 2 + 36).to_bytes(
                                        4, "little"
                                    )
                                    subchunk2_size = (self.total_samples * 2).to_bytes(
                                        4, "little"
                                    )
                                    self.audio_buffer[4:8] = chunk_size
                                    self.audio_buffer[40:44] = subchunk2_size

                                    await client_ws.send(bytes(self.audio_buffer))

                                    self.audio_buffer = bytearray()
                                    self.is_first_audio = True
                                    self.total_samples = 0

                        except Exception as e:
                            logger.error(f"音频处理错误: {e}")
        except ConnectionClosedOK:
            logger.info("xiaozhi-server 正常关闭连接")
        except Exception as e:
            logger.error(f"服务端消息处理异常: {e}")

    async def handle_client_messages(self, client_ws, server_ws):
        """处理来自客户端的消息"""
        try:
            async for message in client_ws:
                if isinstance(message, str):
                    logger.info(f"[客户端→服务端] {message[:200]}")
                    try:
                        msg_data = json.loads(message)
                        if msg_data.get("type") == "hello":
                            msg_data["token"] = self.token
                            msg_data["device_id"] = self.device_id
                            msg_data["device_name"] = "xiaozhi-webui"
                            msg_data["device_mac"] = self.device_id
                            message = json.dumps(msg_data)
                            logger.info(f"hello 消息已注入认证信息: device_id={self.device_id}")
                    except json.JSONDecodeError:
                        pass
                    await server_ws.send(message)
                else:
                    try:
                        audio_data = np.frombuffer(message, dtype=np.float32)
                        if len(audio_data) > 0:
                            chunks = self.audio_processor.process_audio(
                                audio_data.tobytes()
                            )
                            for chunk in chunks if chunks else []:
                                opus_data = pcm_to_opus(chunk)
                                await server_ws.send(opus_data)
                        else:
                            logger.warning("音频数据为空")
                    except Exception as e:
                        logger.error(f"音频处理错误: {e}")
        except ConnectionClosedOK:
            logger.info("WebSocket 正常关闭 (1000)")
        except Exception as e:
            logger.error(f"客户端信息处理异常: {e}")

    async def main(self):
        """启动代理服务器"""

        def signal_handler(signum=None, frame=None):
            self.shutdown_event.set()

        for sig in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGINT", None)):
            if sig is not None:
                signal.signal(sig, signal_handler)

        try:
            async with websockets.serve(
                self.proxy_handler, self.proxy_host, self.proxy_port
            ):
                logger.info(f"WebSocket 代理已启动: {self.proxy_host}:{self.proxy_port}")
                await self.shutdown_event.wait()

        except asyncio.CancelledError:
            logger.info("代理服务器被取消，正在退出...")
        except Exception as e:
            logger.error(f"代理服务器异常: {e}")
