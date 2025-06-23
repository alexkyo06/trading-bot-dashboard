# ~/trading_bot_dashboard/test_parser.py
import re

# --- 把你的解析逻辑和正则表达式复制到这里 ---
CONTRACT_REGEX = re.compile(r"0x[a-fA-F0-9]{40}")

# --- 粘贴你从日志中复制的真实消息文本 ---
message_text = """
这里粘贴你从 Telegram 频道复制的、包含合约地址的完整消息。
例如：
🚀 New Gem Alert: MoonShot Coin ($MSC) 🚀
This is the next 100x easy!

CA: 0x1234567890123456789012345678901234567890

Chart: https://dexscreener.com/eth/0x...
Telegram: t.me/moonshot
"""

# --- 模拟 extract_and_store_info 函数的核心逻辑 ---
print("--- 启动解析测试 ---")

contracts = list(set(CONTRACT_REGEX.findall(message_text)))
if not contracts:
    print("❌ 失败：在消息中没有找到任何合约地址。")
else:
    print(f"✅ 成功：找到了 {len(contracts)} 个合约地址: {contracts}")

    for contract_address in contracts:
        print(f"\n--- 正在解析合约: {contract_address} ---")
        
        # 测试币名和符号的提取
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
            print(f"  - 币名/符号提取: Name='{token_name}', Symbol='{token_symbol}'")
        else:
            print("  - 币名/符号提取: ❌ 失败，无法匹配名称和符号。")

print("\n--- 解析测试结束 ---")
