# ~/trading_bot_dashboard/dashboard_app.py (修改后)
from flask import Flask, render_template, jsonify, g
import requests
import datetime
import pandas as pd
import sqlite3
import json
import os
import config # <--- 1. 导入新的 config 模块

app = Flask(__name__)

# --- 文件路径配置 (这些保持不变) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'meme_data.db')
HISTORICAL_DATA_PATH = os.path.join(DATA_DIR, 'btc_usd_daily_kraken.csv')

# --- 从 config 模块加载 API 端点 ---
# <--- 2. 从 config 模块获取 API 端点 ---
API_ENDPOINT = config.PREDICTION_API_ENDPOINT

# ... (get_db, close_connection, 和所有 @app.route 保持不变) ...
# ... (你的数据库和路由代码写得很好，无需改动！) ...

# 找到文件末尾的 app.run 部分
if __name__ == '__main__':
    # 确保 data 目录存在
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    # <--- 3. 修改启动方式 ---
    # Flask 会自动根据 FLASK_ENV 环境变量决定 debug 模式
    # 我们从 config 模块获取端口
    # 如果 PREDICTION_API_ENDPOINT 未配置，打印一个警告
    if not API_ENDPOINT:
        print("Warning: PREDICTION_API_ENDPOINT is not set in your .env file.")

    app.run(host='0.0.0.0', port=config.APP_PORT, debug=(config.FLASK_ENV == 'development'))
