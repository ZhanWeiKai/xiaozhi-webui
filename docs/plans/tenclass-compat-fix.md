# 适配 xiaozhi.me (tenclass) 官方服务修复方案

## 问题描述

当前项目连接 `wss://api.tenclass.net/xiaozhi/v1/` 时，WebSocket 连接建立后发送 hello 消息即被服务端关闭（code 1000）。而官方 xiaozhi-webui 项目可以正常连接。

## 根本原因

对比官方项目（`xiaozhi-webui-official`）和当前项目，发现 3 个关键差异：

### 差异 1：认证传递方式（核心问题）

**当前项目**：把认证信息拼到 URL query params 里
```python
# 错误：拼到 URL
wss://api.tenclass.net/xiaozhi/v1/?authorization=Bearer xxx&device-id=xxx
async with websockets.connect(ws_url) as server_ws:
```

**官方项目**：通过 WebSocket HTTP headers 传递
```python
# 正确：放在 headers
headers = {
    "Device-Id": self.device_id,
    "Client-Id": self.client_id,
    "Protocol-Version": "1",
    "Authorization": f"Bearer {self.token}"
}
async with websockets.connect(self.websocket_url, additional_headers=self.headers) as server_ws:
```

tenclass 服务器只认 headers，不认 URL params，所以直接踢掉连接。

### 差异 2：hello 消息处理

**当前项目**：拦截 hello 消息，注入 token / device_id / device_mac
```python
if msg_data.get("type") == "hello":
    msg_data["token"] = self.token
    msg_data["device_id"] = self.device_id
    msg_data["device_name"] = "xiaozhi-webui"
    msg_data["device_mac"] = self.device_id
```

**官方项目**：原样转发，不修改
```python
if isinstance(message, str):
    await server_ws.send(message)
```

### 差异 3：配置字段

| 字段 | 当前项目 | 官方项目 |
|------|---------|---------|
| `WS_URL` | 无（通过 OTA 获取） | 有，直接写死 |
| `TOKEN_ENABLE` | 无 | 有，控制是否发 Authorization |
| `TOKEN` | 从 OTA 获取，注入 hello | 从 config 读取，放 headers |
| 认证方式 | URL params + hello 注入 | WebSocket headers |

## 修改方案

### 修改文件

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `backend/app/config.py` | 修改 | 恢复 `WS_URL`、`TOKEN_ENABLE` 字段 |
| `backend/app/proxy/websocket_proxy.py` | 修改 | 认证改用 headers，hello 不修改，支持直接 WS_URL |
| `backend/app/proxy/process_handler.py` | 修改 | 传入 `websocket_url`、`token_enable` |
| `backend/config/config.json` | 修改 | 新增 `WS_URL`、`TOKEN_ENABLE` 字段 |

### 不需要改的文件

- `App.vue` — 不动
- 前端组件 — 不动
- `main.py` — 不动

---

### 具体改动 1：`backend/app/config.py`

恢复 `_default_config` 中被删除的字段：

```python
self._default_config = {
    "WS_URL": "wss://api.tenclass.net/xiaozhi/v1/",
    "WS_PROXY_URL": "ws://0.0.0.0:5000",
    "OTA_VERSION_URL": "https://api.tenclass.net/xiaozhi/ota/",
    "TOKEN_ENABLE": True,
    "TOKEN": "",
}
```

改动点：
- 新增 `WS_URL`，默认值 `wss://api.tenclass.net/xiaozhi/v1/`
- 新增 `TOKEN_ENABLE`，默认值 `true`
- `TOKEN` 默认值改为空字符串

---

### 具体改动 2：`backend/app/proxy/websocket_proxy.py`

#### 2.1 修改构造函数 `__init__`

```python
def __init__(
    self,
    device_id: str,
    client_id: str,
    websocket_url: str,      # 新增：直接 WebSocket 地址
    ota_version_url: str,
    proxy_host: str | None,
    proxy_port: int | None,
    token_enable: bool,       # 新增
    token: str,
):
    self.device_id = device_id
    self.client_id = client_id
    self.websocket_url = websocket_url
    self.ota_version_url = ota_version_url
    self.proxy_host = proxy_host
    self.proxy_port = proxy_port
    self.token_enable = token_enable
    self.token = token

    # ... 音频相关字段保持不变 ...

    # 构建 WebSocket 连接头（替代原来的 _build_ws_url）
    self.headers = {
        "Device-Id": self.device_id,
        "Client-Id": self.client_id,
        "Protocol-Version": "1",
    }
    if self.token_enable:
        self.headers["Authorization"] = f"Bearer {self.token}"

    self._update_ota_address()
```

#### 2.2 修改 `_update_ota_address` 方法

只做 OTA 检查，不再从中获取 websocket URL：

```python
def _update_ota_address(self):
    """检查 OTA 服务器连接，获取 MQTT 等信息"""
    headers = {"Device-Id": self.device_id, "Content-Type": "application/json"}

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

        if "mqtt" in response_data:
            logger.debug(f"MQTT 信息: {response_data['mqtt']}")
        # 不再从 OTA 获取 websocket URL，直接使用 config 中的 WS_URL

    except requests.Timeout:
        logger.error("OTA 请求超时")
        raise ValueError("OTA 请求超时，请稍后重试")
    except requests.RequestException as e:
        logger.error(f"OTA 请求失败: {e}")
        raise ValueError("无法连接到 OTA 服务器，请检查网络连接")
```

#### 2.3 删除 `_build_ws_url` 方法

整个方法删掉，不再需要。

#### 2.4 修改 `proxy_handler` 方法

```python
async def proxy_handler(self, websocket):
    """来自浏览器的 WebSocket 连接"""
    try:
        logger.info(
            f"正在连接 xiaozhi-server: {self.websocket_url}"
        )
        async with websockets.connect(
            self.websocket_url, additional_headers=self.headers
        ) as server_ws:
            logger.info(f"已连接至 xiaozhi-server")
            await self._handle_proxy_communication(websocket, server_ws)

    except Exception as e:
        logger.error(f"代理失败: {e}")
    finally:
        logger.info("客户端连接关闭")
```

改动点：
- `websockets.connect(ws_url)` → `websockets.connect(self.websocket_url, additional_headers=self.headers)`
- 不再调用 `self._build_ws_url()`

#### 2.5 修改 `handle_client_messages` 方法

hello 消息原样转发，不再注入 token / device_id：

```python
async def handle_client_messages(self, client_ws, server_ws):
    """处理来自客户端的消息"""
    try:
        async for message in client_ws:
            if isinstance(message, str):
                logger.info(f"[客户端→服务端] {message[:200]}")
                await server_ws.send(message)  # 原样转发，不修改
            else:
                # ... 音频处理代码保持不变 ...
    except Exception as e:
        logger.error(f"客户端信息处理异常: {e}")
```

改动点：删除 hello 消息拦截和注入逻辑，直接 `await server_ws.send(message)`。

#### 2.6 删除不再使用的 import

```python
# 删除这行，不再需要
from urllib.parse import urlparse, urlencode
```

---

### 具体改动 3：`backend/app/proxy/process_handler.py`

```python
def run_proxy():
    """在单独的进程中运行代理服务器"""
    try:
        configuration = ConfigManager()
        ws_proxy_url = configuration.get_str("WS_PROXY_URL")
        proxy = WebSocketProxy(
            device_id=configuration.get_str("DEVICE_ID"),
            client_id=configuration.get_str("CLIENT_ID"),
            websocket_url=configuration.get_str("WS_URL"),          # 新增
            ota_version_url=configuration.get_str("OTA_VERSION_URL"),
            proxy_host=urlparse(ws_proxy_url).hostname,
            proxy_port=urlparse(ws_proxy_url).port,
            token_enable=configuration.get_bool("TOKEN_ENABLE"),     # 新增
            token=configuration.get_str("TOKEN"),
        )

        asyncio.run(proxy.main())

    except KeyboardInterrupt:
        logger.info("代理进程收到中断信号")
    except Exception as e:
        logger.error(f"代理进程异常: {e}")
```

---

### 具体改动 4：`backend/config/config.json`

```json
{
    "WS_URL": "wss://api.tenclass.net/xiaozhi/v1/",
    "WS_PROXY_URL": "ws://0.0.0.0:5000",
    "OTA_VERSION_URL": "https://api.tenclass.net/xiaozhi/ota/",
    "TOKEN_ENABLE": true,
    "TOKEN": "",
    "CLIENT_ID": "c0031d0d-a87e-4bf3-bb6d-e8911964d909",
    "DEVICE_ID": "80:08:34:2c:4f:98"
}
```

## 改动汇总

```
1. config.py          → 恢复 WS_URL、TOKEN_ENABLE 字段
2. process_handler.py → 传入 websocket_url、token_enable 参数
3. websocket_proxy.py → 3 大改动：
   a. 认证方式：URL params → WebSocket headers
   b. hello 消息：拦截注入 → 原样转发
   c. WebSocket 地址：OTA 动态获取 → config 直接配置
4. config.json        → 新增 WS_URL、TOKEN_ENABLE 字段
```

## 注意事项

- `TOKEN_ENABLE: true` + `TOKEN: ""` 时，headers 里会带上 `Authorization: Bearer `（空 token），tenclass 测试服可能允许空 token
- 如果 tenclass 要求必须有 token，需要先在智控台注册设备获取 token
- `WS_URL` 直接写在 config.json 里，不走 OTA 获取地址
- OTA 请求仍然保留，用于检查连接和获取 MQTT 信息（参考官方项目行为）
