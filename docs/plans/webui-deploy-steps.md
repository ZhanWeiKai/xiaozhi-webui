# WebUI 服务器部署步骤

## 一、前端更新

```bash
# 1. 本地构建
cd C:\claude-project\xiaozhi-webui\xiaozhi-webui-4-9\xiaozhi-webui
pnpm build-only

# 2. 上传到服务器临时目录
scp -r dist/* axonex@100.69.157.38:/tmp/webui-frontend/

# 3. 在服务器上执行（需要 sudo）
sudo rm -rf /var/www/xiaozhi-webui/*
sudo cp -r /tmp/webui-frontend/* /var/www/xiaozhi-webui/
sudo chown -R www-data:www-data /var/www/xiaozhi-webui
```

## 二、后端更新

```bash
# 1. 本地上传修改的文件到服务器
scp backend/app/xxx.py axonex@100.69.157.38:/tmp/

# 2. 替换到两个位置（容器内 + 宿主机）
ssh axonex@100.69.157.38
docker cp /tmp/xxx.py xiaozhi-webui-backend:/app/app/xxx.py
cp /tmp/xxx.py ~/xiaozhi-webui/backend/app/xxx.py

# 3. 重启容器
docker restart xiaozhi-webui-backend
```

## 注意事项

| 事项 | 说明 |
|------|------|
| 前端 | 纯静态文件，替换即生效，无需重启 |
| 后端 | 需要替换容器内文件 + 重启，同时更新宿主机备份 |
| 配置文件 | 挂载在 `/app/config`，直接改宿主机 `~/xiaozhi-webui/backend/config/`，重启即生效 |
| 容器重建 | `docker restart` 只对当前容器生效，`docker compose up -d` 重建会回滚到镜像里的旧代码，需重新构建镜像才永久生效 |

## 访问地址

| 服务 | 地址 |
|------|------|
| WebUI 前端 | https://xiaozhi.jamesweb.org |
| WebSocket 代理 | wss://xiaozhi-ws.jamesweb.org |
| xiaozhi-server WebSocket | wss://xiaozhi-wstest.jamesweb.org/xiaozhi/v1 |
| 智控台 | http://100.69.157.38:8002/ |
