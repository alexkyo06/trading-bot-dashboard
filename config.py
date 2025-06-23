# ~/trading_bot_dashboard/config.py (修改后)
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# --- Telegram API 配置 ---
# 从环境变量中读取，如果不存在则为 None
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
PHONE_NUMBER = os.getenv("TELEGRAM_PHONE_NUMBER")
SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME", "default_session") # 提供一个默认值

# --- 目标频道列表 ---
# 从环境变量中读取并解析为列表
_target_chats_str = os.getenv("TARGET_CHATS", "")
TARGET_CHATS = [chat.strip() for chat in _target_chats_str.split(',') if chat.strip()]

# --- 数据库和其他配置 ---
# 从环境变量读取，并转换为整数，如果不存在则使用默认值 100
MAX_ITEMS_PER_TABLE = int(os.getenv("MAX_ITEMS_PER_TABLE", 100))

# --- Flask 和其他应用配置 ---
FLASK_ENV = os.getenv("FLASK_ENV", "production")
APP_PORT = int(os.getenv("APP_PORT", 5001))
PREDICTION_API_ENDPOINT = os.getenv("PREDICTION_API_ENDPOINT")


# --- 启动时检查关键配置是否存在 ---
def validate_config():
    required_vars = {
        "TELEGRAM_API_ID": API_ID,
        "TELEGRAM_API_HASH": API_HASH,
        "TELEGRAM_PHONE_NUMBER": PHONE_NUMBER,
        "TARGET_CHATS": TARGET_CHATS
    }
    missing_vars = [key for key, value in required_vars.items() if not value]
    if missing_vars:
        raise ValueError(f"Missing required configuration in .env file: {', '.join(missing_vars)}")

print("Configuration loaded.")
# 你可以在主程序启动时调用 validate_config() 来确保所有配置都已设置
