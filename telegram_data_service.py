# ~/trading_bot_dashboard/telegram_data_service.py (Corrected for Python 3.8 and using config.py)
import asyncio
import re
import json
import sqlite3
import os
from telethon import TelegramClient, events
from datetime import datetime, timezone
import config # 导入我们的新配置文件

# --- 从 config.py 读取配置 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'meme_data.db')

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    print(f"Created data directory: {DATA_DIR}")

# --- SQLite 辅助函数 (同步) ---
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 信号表 (Strong Signals)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract TEXT UNIQUE NOT NULL,
            token_name TEXT,
            token_symbol TEXT,
            social_mentions INTEGER DEFAULT 0,
            source_channel TEXT,
            message_text TEXT,
            links TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        # 新币实时流表 (Live Feed)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS feed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract TEXT UNIQUE NOT NULL,
            token_name TEXT,
            token_symbol TEXT,
            chain_id TEXT,
            dex_id TEXT,
            source_channel TEXT,
            message_text TEXT,
            links TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        # 日志表 (Bot Logs)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        conn.commit()
        print("Database initialized successfully.")
    except sqlite3.Error as e:
        print(f"SQLite error during init: {e}")
    finally:
        if conn:
            conn.close()

def add_log_sync(level, message):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO bot_logs (level, message, timestamp) VALUES (?, ?, ?)",
                    (level, message, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        # 清理旧日志
        cursor.execute(f"DELETE FROM bot_logs WHERE id <= (SELECT MAX(id) - {config.MAX_ITEMS_PER_TABLE} FROM bot_logs)")
        conn.commit()
    except sqlite3.Error as e:
        print(f"SQLite error adding log: {e}")
    finally:
        if conn:
            conn.close()

def add_signal_or_feed_item_sync(table_name, item_data):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if not item_data.get('contract'):
            print(f"Skipping item, contract is missing: {item_data.get('token_name', 'Unknown')}")
            return False

        fields_map = {
            "signals": ["contract", "token_name", "token_symbol", "social_mentions", "source_channel", "message_text", "links", "timestamp"],
            "feed": ["contract", "token_name", "token_symbol", "chain_id", "dex_id", "source_channel", "message_text", "links", "timestamp"]
        }
        columns = fields_map[table_name]
        placeholders = ', '.join(['?'] * len(columns))
        values = []
        for col in columns:
            if col == "links":
                values.append(json.dumps(item_data.get(col, [])))
            else:
                values.append(item_data.get(col))

        sql = f"INSERT OR IGNORE INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        cursor.execute(sql, tuple(values))
        conn.commit()

        if cursor.rowcount > 0:
            cursor.execute(f"DELETE FROM {table_name} WHERE id <= (SELECT MAX(id) - {config.MAX_ITEMS_PER_TABLE} FROM {table_name})")
            conn.commit()
            return True
        return False
    except sqlite3.Error as e:
        print(f"SQLite error adding item to {table_name}: {e}")
        add_log_sync("ERROR", f"Failed to add item to {table_name}: {e} - Data: {str(item_data)[:200]}")
        return False
    finally:
        if conn:
            conn.close()

# --- 正则表达式 ---
CONTRACT_REGEX = re.compile(r"0x[a-fA-F0-9]{40}")
DEXSCREENER_REGEX = re.compile(r"https://dexscreener\.com/[\w/-]+")
POOCOIN_REGEX = re.compile(r"https://poocoin\.app/tokens/[\w]+")

# --- 异步函数 ---
async def extract_and_store_info(message_text, source_channel_title):
    loop = asyncio.get_running_loop()
    contracts = list(set(CONTRACT_REGEX.findall(message_text)))
    if not contracts:
        return 0

    dex_links = list(set(DEXSCREENER_REGEX.findall(message_text) + POOCOIN_REGEX.findall(message_text)))
    items_added_count = 0

    for contract_address in contracts:
        token_name = "Unknown Token"
        token_symbol = "N/A"
        match_name_symbol = re.search(
            r"([A-Za-z\s]{3,30}\w*)\s*(?:\(([$A-Z0-9]{2,6})\))?.*?" + re.escape(contract_address),
            message_text, re.IGNORECASE | re.DOTALL
        )
        if not match_name_symbol:
             match_name_symbol = re.search(
                r"Name:\s*([A-Za-z\s]{3,30}\w*).*?Symbol:\s*([$A-Z0-9]{2,6}).*?" + re.escape(contract_address),
                message_text, re.IGNORECASE | re.DOTALL
             )
        if match_name_symbol:
            token_name = match_name_symbol.group(1).strip()
            if match_name_symbol.group(2):
                token_symbol = match_name_symbol.group(2).strip().upper()
        
        chain_id = "ETH"
        dex_id = "Unknown DEX"
        if any("bsc" in link or "pancakeswap" in link for link in dex_links):
            chain_id = "BSC"
            dex_id = "PancakeSwap"
        elif any("polygon" in link or "quickswap" in link for link in dex_links):
            chain_id = "POLYGON"
            dex_id = "QuickSwap"
        
        if dex_links and dex_id == "Unknown DEX" and "dexscreener.com" in dex_links[0]:
            dex_id = "DexScreener"

        item = {
            "contract": contract_address,
            "token_name": token_name,
            "token_symbol": token_symbol,
            "source_channel": source_channel_title,
            "message_text": message_text[:1500],
            "links": dex_links,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "chain_id": chain_id,
            "dex_id": dex_id,
            "social_mentions": 0,
        }

        is_signal = any(kw in message_text.lower() for kw in ["gem", "alpha", "100x", "low cap", "undervalued"])
        table_to_add = "signals" if is_signal else "feed"

        added_successfully = await loop.run_in_executor(None, add_signal_or_feed_item_sync, table_to_add, item)

        if added_successfully:
            items_added_count += 1
            print(f"  Added to {table_to_add}: {contract_address[:10]}... ({token_name}) from {source_channel_title}")
            await loop.run_in_executor(None, add_log_sync, "INFO", f"Added {token_name} ({contract_address[:6]}) to {table_to_add} from {source_channel_title}")
        else:
            print(f"  Skipped or failed to add to {table_to_add}: {contract_address[:10]}... ({token_name})")

    return items_added_count

# --- 主逻辑 ---
client = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH, system_version="4.16.30-vxCUSTOM")

@client.on(events.NewMessage(chats=config.TARGET_CHATS))
async def new_message_handler(event):
    loop = asyncio.get_running_loop()
    message = event.message
    chat = await event.get_chat()
    chat_title = getattr(chat, 'title', getattr(chat, 'username', str(chat.id)))

    log_message_short = message.text[:100].replace('\n', ' ') + "..." if message.text else "Empty message or media"
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] New message from '{chat_title}': {log_message_short}")
    await loop.run_in_executor(None, add_log_sync, "INFO", f"Received message from '{chat_title}': {log_message_short}")
# 添加这行用于调试的日志
    if message.text:
        await loop.run_in_executor(None, add_log_sync, "DEBUG", f"Full message from '{chat_title}':\n---\n{message.text}\n---")
    if message.text:
        items_added = await extract_and_store_info(message.text, chat_title)
        if items_added > 0:
            print(f"  Processed {items_added} item(s) from '{chat_title}' message.")
    else:
        print(f"  Skipping non-text message from '{chat_title}'.")
        await loop.run_in_executor(None, add_log_sync, "DEBUG", f"Skipped non-text message from '{chat_title}'.")

async def main(loop):
    await loop.run_in_executor(None, init_db)
    await loop.run_in_executor(None, add_log_sync, "INFO", "Telegram Data Service starting...")
    print("Telegram Data Service starting. Connecting to Telegram...")

    try:
        await client.start(phone=lambda: config.PHONE_NUMBER)
        print("Successfully connected to Telegram. Listening for messages...")
        await loop.run_in_executor(None, add_log_sync, "INFO", "Successfully connected to Telegram.")
    except Exception as e:
        print(f"Failed to connect to Telegram: {e}")
        await loop.run_in_executor(None, add_log_sync, "ERROR", f"Failed to connect to Telegram: {e}")
        return

    await client.run_until_disconnected()

if __name__ == '__main__':
    config.validate_config()

    print(f"Database will be at: {DB_PATH}")
    event_loop = asyncio.get_event_loop()
    try:
        event_loop.run_until_complete(main(event_loop))
    except KeyboardInterrupt:
        print("Service stopped by user.")
        add_log_sync("INFO", "Service stopped by user.")
    finally:
        if client.is_connected():
            if not event_loop.is_closed():
                event_loop.run_until_complete(client.disconnect())
        if not event_loop.is_closed():
            event_loop.close()
        print("Telegram client disconnected. Exiting.")
