# 占卜系统配置文件
# 复制此文件为 config.py 并填入你自己的配置

# AI 解读配置（可选功能）
# 如果不配置，AI 解读功能将被禁用，但排盘功能仍可正常使用

# AI API 配置
AI_API_BASE = ""  # 例如：https://api.openai.com/v1
AI_API_KEY = ""   # 你的 API Key
AI_MODEL = ""     # 例如：gpt-3.5-turbo, claude-haiku-4.5 等

# 支持的 AI 服务示例：
# OpenAI:    AI_API_BASE = "https://api.openai.com/v1"
# Claude:    AI_API_BASE = "https://api.anthropic.com/v1"  (需要适配)
# DeepSeek:  AI_API_BASE = "https://api.deepseek.com/v1"
# 本地模型:  AI_API_BASE = "http://localhost:11434/v1"

# Flask 配置
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5066
FLASK_DEBUG = False

# 保存到 Obsidian（可选）
# 如果你使用 Obsidian，可以配置笔记库路径
# OBSIDIAN_VAULT_PATH = ""  # 例如：/path/to/obsidian/vault
