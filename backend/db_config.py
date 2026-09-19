"""
数据库连接配置（统一入口）
========================
所有模块从此文件 import，避免多处硬编码数据库配置。

环境变量覆盖规则：
  Docker 部署时通过 docker-compose.yml 设置环境变量，自动切换为生产库。
  本地开发时不设环境变量，使用下方的默认值。

密码安全：
  支持 DB_PASSWORD_BASE64 环境变量（base64 编码），优先级高于 DB_PASSWORD。
  使用方法：echo -n "你的密码" | base64  → 将结果设到 .env 的 DB_PASSWORD_BASE64。
"""

import os
import base64
from pathlib import Path

from dotenv import load_dotenv

# 本地开发：读取项目根目录 .env（Docker 场景由 docker-compose 注入环境变量，不依赖此文件）
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _get_password(env_key: str, env_key_b64: str, default: str) -> str:
    """优先取 base64 编码的密码，其次取明文密码，最后用默认值。"""
    b64 = os.getenv(env_key_b64, "")
    if b64:
        return base64.b64decode(b64).decode("utf-8")
    return os.getenv(env_key, default)


# 业务数据库（本地开发默认值，可通过环境变量覆盖）
DB_CONFIG_CCCK = {
    "host": os.getenv("DB_HOST", "122.51.39.235"),
    "port": int(os.getenv("DB_PORT", "54321")),
    "dbname": os.getenv("DB_NAME", "garden_wms"),
    "user": os.getenv("DB_USER", "garden_wms"),
    "password": _get_password("DB_PASSWORD", "DB_PASSWORD_BASE64", "123456"),
}

def _get_env(first_key: str, second_key: str, default: str) -> str:
    """优先取 first_key 环境变量，其次取 second_key，最后用默认值。"""
    val = os.getenv(first_key, "")
    if val:
        return val
    return os.getenv(second_key, default)


# BI 快照目标数据库（10.239.192.131 KingbaseES，每日定时任务落表）
DB_CONFIG_BI = {
    "host": os.getenv("DB_BI_HOST", "10.239.192.131"),
    "port": int(os.getenv("DB_BI_PORT", "54321")),
    "dbname": os.getenv("DB_BI_NAME", "garden_wms"),
    "user": os.getenv("DB_BI_USER", "garden_wms"),
    "password": _get_password("DB_BI_PASSWORD", "DB_BI_PASSWORD_BASE64", "garden_wms@2025"),
}

# ERP 源数据库（生产环境 10.239.192.229，导入物料目录时使用）
# 环境变量优先级：DB_ERP_* > DB_* > 默认值
DB_CONFIG = {
    "host": _get_env("DB_ERP_HOST", "DB_HOST", "122.51.39.235"),
    "port": int(_get_env("DB_ERP_PORT", "DB_PORT", "54321")),
    "dbname": _get_env("DB_ERP_NAME", "DB_NAME", "garden_wms"),
    "user": _get_env("DB_ERP_USER", "DB_USER", "garden_wms"),
    "password": _get_password("DB_PASSWORD", "DB_PASSWORD_BASE64", "123456"),
}
