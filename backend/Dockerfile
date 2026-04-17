FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖（opus）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopus-dev && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY pyproject.toml .
RUN pip install --no-cache-dir websockets numpy requests colorlog opuslib

# 复制代码
COPY app/ app/
COPY libs/ libs/
COPY main.py .

# 配置文件通过 volume 挂载，不打包进镜像
VOLUME /app/config

EXPOSE 5000

CMD ["python", "main.py"]
