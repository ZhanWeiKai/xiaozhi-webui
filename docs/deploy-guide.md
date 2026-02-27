# Xiaozhi WebUI 部署指南

## 更新日志

### 2026-02-27: HTTPS 部署与 Cloudflare Tunnel 配置

**问题背景**：
- AudioWorklet API 需要在「安全上下文」中运行
- HTTP + 非本地 IP 被视为不安全上下文，导致 AudioWorklet 被禁用
- 语音对话功能无法在 WebView 中使用

**解决方案**：
- 配置 Cloudflare Tunnel 提供 HTTPS 访问
- 域名：`xiaozhi.jamesweb.org`
- WebSocket：`xiaozhi-ws.jamesweb.org`

**修改内容**：
1. 前端配置 hardcode 为 HTTPS 地址
2. Android WebView URL 改为 `https://xiaozhi.jamesweb.org`
3. 添加自动清除旧 localStorage 缓存的逻辑

**相关提交**：
- `xiaozhi-webui`: HTTPS 配置更新
- `XiaozhiApp`: WebView URL 更新为 HTTPS

---

## 服务器信息

| 项目 | 值 |
|------|-----|
| 服务器 IP (LAN) | `10.88.1.141` |
| 服务器 IP (Tailscale) | `100.69.157.38` |
| 用户名 | `axonex` |
| 架构 | ARM64 |
| 域名 | `jamesweb.org` (Cloudflare) |

---

## 当前部署情况

### 端口分配

| 端口 | 服务 | 访问地址 |
|------|------|----------|
| 8100 | WebUI (Tailscale) | `http://100.69.157.38:8100` |
| 8888 | WebUI (备用) | `http://100.69.157.38:8888` |
| 8081 | FastAPI 后端 | `http://100.69.157.38:8081` |
| 5000 | WebSocket 代理 | `ws://100.69.157.38:5000` |
| 8000 | xiaozhi-server | `ws://100.69.157.38:8000/xiaozhi/v1` |
| 8002 | OTA 服务 | `http://100.69.157.38:8002/xiaozhi/ota/` |

### 8100 端口部署

- **路径**: `/var/www/xiaozhi-webui/`
- **访问**: `http://100.69.157.38:8100`
- **配置**: Hardcoded（无需 localStorage）
- **用途**: 主要使用，Android WebView 默认连接此端口

### 8888 端口部署

- **用途**: 备用端口

---

## Cloudflare Tunnel 配置（HTTPS）

> **目的**: 解决 AudioWorklet 需要安全上下文（HTTPS）的问题

### 问题背景

```
AudioWorklet 需要「安全上下文」(Secure Context):
  ✅ https://
  ✅ http://localhost
  ❌ http://100.69.157.38  ← 当前情况
```

### 解决方案

使用 Cloudflare Tunnel 提供 HTTPS 访问，不影响现有 8100/8888 端口。

### 配置步骤

#### 第 1 步：安装 cloudflared (ARM64)

```bash
# SSH 到服务器
ssh axonex@10.88.1.141

# 下载 ARM64 版本
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb

# 安装
sudo dpkg -i cloudflared.deb
```

#### 第 2 步：登录 Cloudflare

```bash
cloudflared tunnel login
```

在浏览器中打开输出的 URL，授权 `jamesweb.org` 域名。

#### 第 3 步：创建隧道

```bash
cloudflared tunnel create xiaozhi-webui
```

隧道 ID: `6b50289d-9aed-4f66-8e57-16e8be9a8b76`

#### 第 4 步：创建配置文件

```bash
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << 'EOF'
tunnel: 6b50289d-9aed-4f66-8e57-16e8be9a8b76
credentials-file: /etc/cloudflared/6b50289d-9aed-4f66-8e57-16e8be9a8b76.json

ingress:
  - hostname: xiaozhi.jamesweb.org
    service: http://localhost:8100
  - service: http_status:404
EOF
```

#### 第 5 步：复制配置到系统目录

```bash
sudo mkdir -p /etc/cloudflared
sudo cp ~/.cloudflared/config.yml /etc/cloudflared/
sudo cp ~/.cloudflared/6b50289d-9aed-4f66-8e57-16e8be9a8b76.json /etc/cloudflared/
```

#### 第 6 步：创建 DNS 记录

```bash
cloudflared tunnel route dns xiaozhi-webui xiaozhi.jamesweb.org
```

#### 第 7 步：配置 systemd 服务（开机自启）

```bash
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

#### 验证

```bash
# 检查服务状态
sudo systemctl status cloudflared

# 测试访问
curl -I https://xiaozhi.jamesweb.org
```

### 最终效果

```
https://xiaozhi.jamesweb.org
        │
        ▼ Cloudflare 边缘节点 (HTTPS)
        │
        ▼ Cloudflare Tunnel (加密)
        │
        ▼ 远程服务器 (10.88.1.141)
        │
        ▼ localhost:8100 (WebUI)
```

### 访问地址

| 类型 | 地址 |
|------|------|
| HTTPS (推荐) | https://xiaozhi.jamesweb.org |
| HTTP (Tailscale) | http://100.69.157.38:8100 |

### 对现有部署的影响

| 端口 | 影响 |
|------|------|
| 8100 | **无影响** - Tunnel 只是代理到 localhost:8100 |
| 8888 | **无影响** - 保持原样 |
| 其他服务 | **无影响** - 隧道只代理 xiaozhi.jamesweb.org |

---

## Android WebView 配置

### 项目路径

`C:\claude-project\xiaozhi-webui\XiaozhiApp`

### GitHub 仓库

https://github.com/ZhanWeiKai/xiaozhi-android-webview

### 当前配置

```java
// MainActivity.java:22
private static final String URL = "http://100.69.157.38:8100";
```

### 更新为 HTTPS（Tunnel 配置完成后）

```java
private static final String URL = "https://xiaozhi.jamesweb.org";
```

---

## 前端配置 (Hardcoded)

文件: `xiaozhi-webui/src/stores/setting.ts`

```typescript
const DEFAULT_CONFIG = {
  ws_url: "ws://100.69.157.38:8000/xiaozhi/v1",
  ws_proxy_url: "ws://100.69.157.38:5000",
  ota_version_url: "http://100.69.157.38:8002/xiaozhi/ota/",
  backend_url: "http://100.69.157.38:8081",
  token_enable: true,
  token: "N9tieuHFjJ_u2BYkJuzzXxhXV_8-5MYSl_pmQX-HnY.1770887401",
  device_id: "48:45:e6:cf:b7:2d"
}
```

> **TODO**: 配置 HTTPS 后，需要更新 WebSocket 代理地址
