# xiaozhi-webui 项目总结

## 项目概况

xiaozhi-webui 是一个使用 **Python + Vue3** 实现的小智语音 Web 端，前后端分离架构。旨在通过代码学习和在没有硬件条件下体验 AI 小智的对话功能。

## 系统要求

- Python 3.9+（后端 pyproject.toml 要求 >=3.12）
- Node.js 18+
- pnpm（前端包管理器，推荐）
- uv（Python 包管理器）
- 支持的操作系统：Windows 10+、macOS 10.15+、Linux

## 编译/启动步骤

### 1. 安装前端依赖

```bash
pnpm install
```

### 2. 安装后端依赖

```bash
cd backend
uv sync
cd ..
```

### 3. 启动项目

**一键启动（推荐）：**

```bash
pnpm dev
```

这会用 `concurrently` 同时启动前后端服务，终端可以看到带颜色区分的前后端日志输出。

**分别启动：**

```bash
# 前端
pnpm dev:frontend

# 后端
pnpm dev:backend
```

**手动分别启动：**

```bash
# 前端
pnpm install
pnpm dev:frontend

# 后端
cd backend
uv run main.py
```

### 4. 访问页面

浏览器打开 `http://localhost:5173`

## 端口说明

| 服务 | 默认端口 |
|------|---------|
| 前端 | 5173    |
| 后端 | 5000    |

## 技术栈

**前端**

- 框架：Vue3 + TypeScript + Pinia
- 构建工具：Vite
- 包管理器：pnpm
- UI 组件：Element Plus
- Web API：WebSocket、Web Audio API、AudioWorklet

**后端**

- Python>=3.12 + FastAPI
- 包管理器：uv

**开发工具**

- concurrently：同时运行前后端服务
- TypeScript：类型安全
- Less：CSS 预处理器

## 项目结构

```
├── backend/                            # 后端目录
│   ├── app/
│   |   ├── constant/                   # 常量
│   |   ├── proxy/                      # websocket 代理
│   |   ├── router/                     # 路由
│   |   ├── utils/                      # 工具函数
│   │   └── config.py                   # 配置
│   ├── libs/                           # 第三方库文件
│   ├── main.py                         # 后端入口
│   ├── pyproject.toml                  # Python 项目配置
│   └── uv.lock                         # Python 依赖锁定文件
├── src/                                # 前端源码目录
│   ├── assets/                         # 静态资源
│   ├── components/                     # Vue 组件
│   ├── services/                       # 模块化服务
│   ├── stores/                         # 全局状态管理
│   ├── types/                          # TypeScript 类型定义
│   ├── App.vue                         # 前端入口组件
│   └── main.ts                         # 前端入口文件
├── public/                             # 公共静态资源
├── package.json                        # 前端项目配置
├── pnpm-lock.yaml                      # 前端依赖锁定文件
├── vite.config.ts                      # Vite 配置
└── tsconfig.json                       # TypeScript 配置
```

## 连接链路分析

### 完整连接链路

```
Vue 前端  ──WebSocket──>  Python 后端  ──WebSocket──>  xiaozhi-server
(localhost:5173)        (localhost:5000)               (OTA 动态获取地址)
```

### 1. 前端 Vue → 后端 (5000)

**配置来源：浏览器 localStorage**

通过 Pinia store `src/stores/setting.ts` 管理，关键字段：

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `wsProxyUrl` | `ws://localhost:5000` | WebSocket 代理地址 |

**连接流程：**

1. **App.vue** `onMounted` 启动时，从 localStorage 加载配置
2. 如果没有配置，弹出输入框提示用户输入，默认值 `ws://localhost:5000`
3. 调用 `wsService.connect(settingStore.wsProxyUrl)` 建立连接
4. `src/services/WebSocketManager.ts` 用原生 `new WebSocket(url)` 连接
5. 连接成功后发送 `hello` 消息（含音频参数：opus/16000Hz）
6. 断线自动 3 秒重连

### 2. 后端 Python → xiaozhi-server

**配置来源：`backend/config/config.json`**

```json
{
    "WS_PROXY_URL": "ws://0.0.0.0:5000",
    "OTA_VERSION_URL": "https://xiaozhi.jamesweb.org/api/ota/",
    "TOKEN": "B88nOio0ygF_UlrdHsPlcB1LZymu6So30SOO5_h2MD8.1770014637",
    "CLIENT_ID": "c0031d0d-a87e-4bf3-bb6d-e8911964d909",
    "DEVICE_ID": "80:08:34:2c:4f:98"
}
```

**设备标识自动生成（`app/utils/device.py`）：**
- `DEVICE_ID`：取本机 MAC 地址
- `CLIENT_ID`：随机生成 UUID

## xiaozhi-test 连接分析（源码级）

### 项目类型

纯 **JavaScript/HTML5** 浏览器端应用，无后端服务器。

### 连接链路

```
浏览器  ──WebSocket──>  xiaozhi-server
                         (通过 OTA 获取地址)
```

### 第一步：OTA 请求（ota-connector.js）

```
POST https://xiaozhi.jamesweb.org/api/ota/
Headers: Device-Id=<MAC>, Client-Id=<CLIENT_ID>, Content-Type: application/json
Body: 设备信息 JSON
```

返回：
```json
{
    "websocket": {
        "url": "ws://10.88.1.x:8000/xiaozhi/v1",
        "token": "OTA_GENERATED_TOKEN"
    },
    "activation": {
        "code": "402410",
        "message": "http://10.88.1.141\n402410"
    }
}
```

### 第二步：构建 WebSocket URL（ota-connector.js）

内网地址替换 → 拼接 URL query params：

```
wss://xiaozhi-wstest.jamesweb.org/xiaozhi/v1?authorization=Bearer <OTA_TOKEN>&device-id=<MAC>&client-id=<CLIENT_ID>
```

### 第三步：发送 hello 消息（websocket.js）

WebSocket 连接建立后，发送：

```json
{
    "type": "hello",
    "device_id": "<MAC>",
    "device_name": "Web测试设备",
    "device_mac": "<MAC>",
    "token": "<USER_TOKEN>",
    "features": { "mcp": true }
}
```

## xiaozhi-server 认证机制（源码级，已验证）

### 认证架构：只有一套 Token

经过阅读 xiaozhi-server 源码（`websocket_server.py` + `auth.py` + `ota_handler.py`），确认认证流程如下：

```
┌──────────────────────────────────────────────────────┐
│                  唯一 Token（OTA Token）               │
│                                                      │
│  生成方: xiaozhi-server OTA 接口（ota_handler.py）     │
│  算法:   HMAC-SHA256(auth_key, "client_id|device_id|ts") │
│  传递:   URL query params → authorization=Bearer <token> │
│  校验:   websocket_server._handle_auth()              │
│  验证参数: verify_token(token, client_id, device_id)   │
│  有效期:  30 天                                        │
└──────────────────────────────────────────────────────┘
```

**关键点：服务端只校验 URL params 里的 `authorization` token，不校验 hello 消息里的 token。**

### 源码证据 1：OTA 生成 token（ota_handler.py）

```python
# ota_handler.py - handle_post()
client_id = request.headers.get("client-id", "")  # 必须传 Client-Id！
device_id = request.headers.get("device-id", "")

if self.auth_enable:
    # 服务端用 auth_key + client_id + device_id 实时生成 token
    token = self.auth.generate_token(client_id, device_id)

return_json["websocket"] = {
    "url": self._get_websocket_url(local_ip, websocket_port),
    "token": token,  # ← 这就是认证 token
}
```

### 源码证据 2：Token 生成算法（auth.py）

```python
# auth.py - AuthManager
def generate_token(self, client_id: str, username: str) -> str:
    ts = int(time.time())
    content = f"{client_id}|{username}|{ts}"
    signature = self._sign(content)  # HMAC-SHA256(secret_key, content)
    token = f"{signature}.{ts}"
    return token
```

### 源码证据 3：WebSocket 认证（websocket_server.py）

```python
# websocket_server.py - _handle_auth()
async def _handle_auth(self, websocket):
    if self.auth_enable:
        headers = dict(websocket.request.headers)
        device_id = headers.get("device-id", None)     # 从 URL params 获取
        client_id = headers.get("client-id", None)     # 从 URL params 获取

        token = headers.get("authorization", "")       # 从 URL params 获取
        if token.startswith("Bearer "):
            token = token[7:]

        # 用 client_id + device_id 验证 token 的 HMAC 签名
        auth_success = self.auth.verify_token(
            token, client_id=client_id, username=device_id
        )
        if not auth_success:
            raise AuthenticationError("Invalid token")
```

### 源码证据 4：Token 验证算法（auth.py）

```python
# auth.py - verify_token()
def verify_token(self, token: str, client_id: str, username: str) -> bool:
    sig_part, ts_str = token.split(".")
    ts = int(ts_str)

    # 检查是否过期
    if int(time.time()) - ts > self.expire_seconds:
        return False

    # 用同样的参数重新签名，比对是否一致
    expected_sig = self._sign(f"{client_id}|{username}|{ts}")
    if not hmac.compare_digest(sig_part, expected_sig):
        return False

    return True
```

### 完整认证流程

```
1. 客户端 POST OTA 接口
   Headers: { Device-Id: "<MAC>", Client-Id: "<UUID>" }
                          ↓
2. OTA 服务端生成 token
   auth.generate_token(client_id="<UUID>", username="<MAC>")
   → token = HMAC-SHA256(auth_key, "<UUID>|<MAC>|<timestamp>") + "." + timestamp
                          ↓
3. OTA 返回
   { "websocket": { "url": "ws://...", "token": "<OTA_TOKEN>" } }
                          ↓
4. 客户端构建 WebSocket URL
   ws://server?authorization=Bearer <OTA_TOKEN>&device-id=<MAC>&client-id=<UUID>
                          ↓
5. WebSocket 握手，服务端提取 URL params
   device-id, client-id, authorization → headers
                          ↓
6. 服务端验证
   verify_token(
       token=<OTA_TOKEN>,
       client_id=<UUID>,      ← 必须与 OTA 请求时一致
       username=<MAC>          ← 必须与 OTA 请求时一致
   )
   → 重新签名比对 → 认证通过/失败
```

### 关键结论

1. **认证只用 OTA 返回的 token** — 通过 URL params `authorization` 传递
2. **client-id 和 device-id 必须一致** — OTA 请求时和 WebSocket 连接时必须相同，否则签名验证失败
3. **OTA 请求必须带 Client-Id header** — 否则 OTA 报错 `ClientID为空`
4. **hello 消息里的 token 不参与认证** — 服务端 `_handle_auth` 只校验 URL params
5. **TOKEN 字段（B88...）的真正用途** — 仅用于 hello 消息体的 `token` 字段，属于应用层信息，WebSocket 连接认证不依赖它

### 之前理解的错误（已纠正）

| 错误理解 | 正确理解 |
|---------|---------|
| 两套 token（OTA token + 用户 token） | 认证只用 OTA token，用户 token 不参与 WebSocket 认证 |
| hello 消息里的 token 用于服务端认证 | 服务端 `_handle_auth` 只校验 URL params 的 authorization |
| config.json 的 TOKEN 字段用于连接认证 | TOKEN 字段只注入到 hello 消息体，不用于 WebSocket 握手认证 |
| OTA 请求不需要 Client-Id | OTA 必须带 Client-Id，否则报错 |

## OTA 动态连接改造方案（参考 xiaozhi-test）

### 改造目标

1. 通过 OTA 动态获取 WebSocket URL（替代硬编码 `WS_URL`）
2. 认证方式：URL params 传 OTA token + device-id + client-id
3. 前端精简：移除 token 相关 UI 和 store 字段
4. OTA 请求必须带 `Device-Id` 和 `Client-Id` 两个 header

### 改造后的 config.json

```json
{
    "WS_PROXY_URL": "ws://0.0.0.0:5000",
    "OTA_VERSION_URL": "https://xiaozhi.jamesweb.org/api/ota/",
    "TOKEN": "B88nOio0ygF_UlrdHsPlcB1LZymu6So30SOO5_h2MD8.1770014637",
    "CLIENT_ID": "c0031d0d-a87e-4bf3-bb6d-e8911964d909",
    "DEVICE_ID": "80:08:34:2c:4f:98"
}
```

说明：
- 删除了 `WS_URL`（改为 OTA 动态获取）
- 删除了 `TOKEN_ENABLE`（不再需要）
- 保留 `TOKEN`（注入到 hello 消息体）
- 保留 `CLIENT_ID` 和 `DEVICE_ID`（OTA 请求和 WebSocket 连接都用）

### 需要改动的文件

#### 1. `backend/app/config.py`

删除 `WS_URL`、`TOKEN_ENABLE`，保留 `OTA_VERSION_URL`、`TOKEN`。

#### 2. `backend/app/proxy/websocket_proxy.py` — 核心改造

- **`__init__`**：接收 `token`（用于 hello 消息），初始化 `ota_token`（从 OTA 获取）
- **`_update_ota_address()`**：OTA POST 携带 `Device-Id` + `Client-Id` headers，提取 `websocket.url` + `websocket.token`
- **`_replace_internal_url()`**：内网不可达时替换为外网地址（`xiaozhi-wstest.jamesweb.org/xiaozhi`）
- **`_build_ws_url()`**：拼接 `?authorization=Bearer <OTA_TOKEN>&device-id=<MAC>&client-id=<UUID>`
- **`handle_client_messages()`**：拦截 hello 消息，注入 token + device_id + device_mac

#### 3. `backend/app/proxy/process_handler.py`

适配新参数：删除 `websocket_url` 和 `token_enable`，只传 `token`。

#### 4. 前端精简

- `src/stores/setting.ts`：删除 `tokenEnable`、`token` 字段
- `src/components/Setting/index.vue`：删除 Token 开关和输入框

### 改造后的完整连接流程

```
1. 后端启动 → 读取 config.json（OTA_VERSION_URL + CLIENT_ID + DEVICE_ID）
2. OTA POST → Headers 携带 Device-Id=<MAC> + Client-Id=<UUID> → 获取 websocket.url + ota_token
3. 内网不可达时自动替换为外网地址（xiaozhi-wstest.jamesweb.org/xiaozhi）
4. 构建 WebSocket URL:
   wss://server/xiaozhi/v1?authorization=Bearer <OTA_TOKEN>&device-id=<MAC>&client-id=<UUID>
5. WebSocket 连接 xiaozhi-server → 服务端 verify_token(OTA_TOKEN, client_id, device_id) → 认证通过
6. 前端连接 ws://localhost:5000 → 发送 hello（音频参数）
7. 后端拦截 hello → 注入 token + device_id + device_mac → 转发给 xiaozhi-server
8. 双向通信开始
```

## 功能特点

- 文字聊天：像微信好友一样聊天
- 语音聊天：和小智进行语音对话，支持打断
- 自动配置：通过 OTA 动态获取 WebSocket 地址，避免硬编码
- 反馈动效：（语音对话时）用户的说话波形 + 小智回答时的头像缩放动画
- 移动适配：支持移动端配置服务器地址

---

## 部署到服务器

### 服务器信息

- SSH: `axonex@10.88.1.144`
- 后端目录: `~/xiaozhi-webui/backend/`
- 前端目录: `/var/www/xiaozhi-webui/`（nginx 托管，端口 8100）

### 服务器 config.json（不要用本地的值覆盖）

```json
{
    "WS_PROXY_URL": "ws://0.0.0.0:5000",
    "OTA_VERSION_URL": "http://127.0.0.1:8002/xiaozhi/ota/",
    "TOKEN": "ggQFhyfnK0jwksonYA8TAEg9BX6ke9OPrRS7MwT8Hg4.1772628453",
    "CLIENT_ID": "4904b5d9-262a-46b7-9b3b-792205fb8689",
    "DEVICE_ID": "52:45:c6:a0:f1:d8"
}
```

### 部署步骤（标准流程）

```bash
# 1. 本地构建前端
pnpm build-only

# 2. 停止旧后端
ssh axonex@10.88.1.144 "pkill -9 -f 'python.*main.py'; fuser -k 5000/tcp 2>/dev/null; fuser -k 8081/tcp 2>/dev/null"

# 3. 备份服务器 config.json
ssh axonex@10.88.1.144 "cp ~/xiaozhi-webui/backend/config/config.json ~/xiaozhi-webui/backend/config/config.json.bak"

# 4. 删除旧代码，重新上传（避免旧文件残留）
ssh axonex@10.88.1.144 "rm -rf ~/xiaozhi-webui/backend/app ~/xiaozhi-webui/backend/libs"
scp -r backend/app backend/libs backend/main.py backend/pyproject.toml \
    axonex@10.88.1.144:~/xiaozhi-webui/backend/

# 5. 确认 config.json 未被覆盖（若被覆盖则从备份恢复）
ssh axonex@10.88.1.144 "cat ~/xiaozhi-webui/backend/config/config.json"

# 6. 覆盖前端文件
scp -r dist/* axonex@10.88.1.144:/tmp/webui-frontend-new/
ssh axonex@10.88.1.144 "sudo rm -rf /var/www/xiaozhi-webui/* && sudo cp -r /tmp/webui-frontend-new/* /var/www/xiaozhi-webui/ && sudo chown -R www-data:www-data /var/www/xiaozhi-webui"

# 7. 重启 nginx
ssh axonex@10.88.1.144 "sudo nginx -t && sudo systemctl restart nginx"

# 8. 启动后端
ssh axonex@10.88.1.144 "cd ~/xiaozhi-webui/backend && nohup ./venv/bin/python main.py > ~/xiaozhi-webui/backend.log 2>&1 &"

# 9. 验证
ssh axonex@10.88.1.144 "tail -30 ~/xiaozhi-webui/backend.log"
```

### 实际部署记录（2026-04-09）

1. **本地构建前端**：`pnpm build-only`，产物在 `dist/`

2. **停止旧后端**：服务器上 root 的 `python main.py` 进程需要 sudo 杀掉，杀掉后会自动重启

3. **备份 config.json**：`cp config.json config.json.bak`

4. **覆盖后端代码**：`scp -r backend/app backend/libs backend/main.py backend/pyproject.toml` 到服务器

5. **踩坑 - 旧文件残留**：`scp -r` 只上传不删除，服务器上旧的 `app/router/`、`app/constants.py` 还在，导致 `ImportError`。解决：删掉 `app/` 和 `libs/` 重新上传

6. **踩坑 - config.json 是旧格式**：服务器上还带着 `WS_URL`、`TOKEN_ENABLE` 等旧字段，重写为新格式

7. **踩坑 - OTA 端口错误**：文档写的 `8003` 返回 404，实际 OTA 接口在 `8002`，改了 `OTA_VERSION_URL`

8. **覆盖前端文件**：上传 `dist/*` 到 `/tmp/webui-frontend-new/`，然后 `sudo rm -rf /var/www/xiaozhi-webui/*` 后复制过去

9. **重启 nginx**：`sudo systemctl restart nginx`（没改配置）

10. **启动后端**：`nohup ./venv/bin/python main.py > backend.log 2>&1 &`

11. **验证成功**：日志显示 OTA 获取到 WebSocket 地址和 Token，代理在 `0.0.0.0:5000` 启动
