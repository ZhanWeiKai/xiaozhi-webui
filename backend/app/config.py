import os
from .utils.logger import get_logger
import json
from .utils.device import get_client_id, get_mac_address
from .constant.file import BASE_DIR

logger = get_logger(__name__)


class ConfigManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self._default_config = {
            "SERVER_IP": "192.168.0.203",
            "SERVER_PORT": 8000,
            "WEB_PORT": 8002,
            "WS_PROXY_PORT": 5000,
            "BACKEND_PORT": 8081,
            "BIND_HOST": "0.0.0.0",
            "TOKEN_ENABLE": True,
            "TOKEN": "test_token",
        }
        self._config = {}
        self._init_config()

    def _get_dynamic_urls(self) -> dict:
        """根据 SERVER_IP 动态生成所有 URL"""
        server_ip = self._config.get("SERVER_IP", self._default_config["SERVER_IP"])
        server_port = self._config.get("SERVER_PORT", self._default_config["SERVER_PORT"])
        web_port = self._config.get("WEB_PORT", self._default_config["WEB_PORT"])
        ws_proxy_port = self._config.get("WS_PROXY_PORT", self._default_config["WS_PROXY_PORT"])
        backend_port = self._config.get("BACKEND_PORT", self._default_config["BACKEND_PORT"])

        return {
            "WS_URL": f"ws://{server_ip}:{server_port}/xiaozhi/v1",
            "WS_PROXY_URL": f"ws://{server_ip}:{ws_proxy_port}",
            "OTA_VERSION_URL": f"http://{server_ip}:{web_port}/xiaozhi/ota/",
            "BACKEND_URL": f"http://{server_ip}:{backend_port}",
        }

    def _init_config(self) -> None:
        """确保配置文件存在，否则创建并使用默认配置"""
        config_file_path = os.path.join(BASE_DIR, "config", "config.json")

        if not os.path.exists(config_file_path):
            logger.info("本地配置文件不存在，正在创建默认配置: ", config_file_path)
            os.makedirs(os.path.join(BASE_DIR, "config"), exist_ok=True)
            self._default_config["CLIENT_ID"] = get_client_id()
            self._default_config["DEVICE_ID"] = get_mac_address()
            with open(config_file_path, "w") as f:
                json.dump(self._default_config, f, indent=4)

        logger.info(f"正在加载本地配置: {config_file_path}")

        try:
            with open(config_file_path, "r") as f:
                self._config = json.load(f)
        except json.JSONDecodeError:
            logger.warning("配置文件格式错误，正在重置配置")
            with open(config_file_path, "w") as f:
                json.dump(self._default_config, f, indent=4)
            self._config = self._default_config

    def get(self, key: str) -> str | bool | None:
        # 先检查原始配置，再检查动态生成的 URL
        if key in self._config:
            return self._config[key]
        dynamic_urls = self._get_dynamic_urls()
        return dynamic_urls.get(key)

    def get_str(self, key: str, default: str = "") -> str:
        value = self.get(key)
        if value is None:
            return default
        return str(value) if value is not None else default

    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self.get(key)
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)

    def get_int(self, key: str, default: int = 0) -> int:
        value = self.get(key)
        if value is None:
            return default
        try:
            return int(value) if value is not None else default
        except (ValueError, TypeError):
            return default

    def set(self, key: str, value: str | bool) -> None:
        self._config[key] = value

    @property
    def config(self) -> dict:
        """返回合并后的配置：原始配置 + 动态生成的 URL"""
        dynamic_urls = self._get_dynamic_urls()
        # 合并配置，动态 URL 优先
        merged = {**self._config, **dynamic_urls}
        # 使用小写 key 给前端
        return {
            "ws_url": merged.get("WS_URL", ""),
            "ws_proxy_url": merged.get("WS_PROXY_URL", ""),
            "ota_version_url": merged.get("OTA_VERSION_URL", ""),
            "backend_url": merged.get("BACKEND_URL", ""),
            "token_enable": merged.get("TOKEN_ENABLE", True),
            "token": merged.get("TOKEN", ""),
            "device_token": merged.get("DEVICE_TOKEN", merged.get("TOKEN", "")),
            "client_id": merged.get("CLIENT_ID", ""),
            "device_id": merged.get("DEVICE_ID", ""),
        }

    def save_config(self) -> None:
        config_file_path = os.path.join(BASE_DIR, "config", "config.json")
        with open(config_file_path, "w") as f:
            json.dump(self._config, f, indent=4)
