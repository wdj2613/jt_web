import json
import os
from typing import Dict, Any


class Config:
    """配置管理类"""
    
    def __init__(self, config_path: str = 'config.json'):
        self.config_path = config_path
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        # 确保配置文件路径是绝对路径
        abs_config_path = os.path.abspath(self.config_path)
        
        try:
            with open(abs_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"配置文件 {abs_config_path} 未找到，使用默认配置")
            return self._get_default_config()
        except json.JSONDecodeError:
            print(f"配置文件 {abs_config_path} 格式错误，使用默认配置")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "server": {
                "host": "127.0.0.1",
                "port": 5000,
                "debug": False
            },
            "logging": {
                "level": "INFO",
                "file": "logs/app.log"
            },
            "api": {
                "base_url": "http://appapi2.gamersky.com/v5/",
                "timeout": 30
            }
        }
    
    def get(self, key: str, default: Any = None):
        """获取配置值"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_server_config(self) -> Dict[str, Any]:
        """获取服务器配置"""
        return self.get('server', {})
    
    @property
    def host(self) -> str:
        return self.get('server.host', '127.0.0.1')
    
    @host.setter
    def host(self, value: str):
        """设置主机地址"""
        if 'server' not in self._config:
            self._config['server'] = {}
        self._config['server']['host'] = value
    
    @property
    def port(self) -> int:
        return self.get('server.port', 5000)
    
    @port.setter
    def port(self, value: int):
        """设置端口号"""
        if 'server' not in self._config:
            self._config['server'] = {}
        self._config['server']['port'] = value
    
    @property
    def debug(self) -> bool:
        return self.get('server.debug', False)
    
    @debug.setter
    def debug(self, value: bool):
        """设置调试模式"""
        if 'server' not in self._config:
            self._config['server'] = {}
        self._config['server']['debug'] = value

    @property
    def log_file(self) -> str:
        """获取日志文件路径"""
        # 确保日志目录存在
        log_dir = os.path.dirname(self.get('logging.file', 'logs/app.log'))
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        return self.get('logging.file', 'logs/app.log')


# 创建全局配置实例
config = Config()
