#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用 AI 解读模块：盘由程序精确排，AI 只结合求测者处境做白话解读。

用法：ai_interpret("六爻", result_dict, "我95年生，最近想换工作")
- 用户没填处境（user_context 为空）时，调用方不应调用本模块（纯排盘即可）。
- 走配置的 AI 模型，快且便宜。失败返回 None，不影响主排盘结果。
"""
from __future__ import annotations

import os
import json
import requests

# 尝试从 config.py 加载配置，否则使用环境变量
try:
    from config import AI_API_BASE as KIRO_BASE, AI_API_KEY as KIRO_KEY, AI_MODEL as KIRO_MODEL
    if not KIRO_BASE or not KIRO_KEY:
        raise ValueError("配置为空")
except (ImportError, ValueError):
    KIRO_BASE = os.environ.get("AI_API_BASE", "")
    KIRO_KEY = os.environ.get("AI_API_KEY", "")
    KIRO_MODEL = os.environ.get("AI_MODEL", "gpt-3.5-turbo")

# result 里对解读无用、不必喂给模型的字段（省 token + 防泄露本地路径）
_DROP_KEYS = {"saved_path", "save_error", "model", "datetime", "trace", "ai_reading"}

MAX_RESULT_CHARS = 6000  # 排盘结果摘要喂给模型的上限
MAX_CONTEXT_CHARS = 500  # 用户处境文字上限

SYSTEM_PROMPT = """你是一位融合中国传统文化与现代心理学的文化解读顾问，为娱乐性质的传统文化体验网站服务。

任务说明：
- 下面会给你一份「传统文化排盘数据」（已由程序按传统民俗规则推算生成）和「用户写的处境」。
- 请把这份排盘数据当作一种传统文化符号系统，结合用户的处境，给一段温暖的白话解读，类似传统文化爱好者之间的趣味交流。
- 这是文化娱乐内容，不是预测、不是宿命论。重点是借传统文化的意象，给用户一些积极的心理疏导和生活提醒。

写作要求：
- 直接说人话，像一位通透的长辈在聊天点拨，不绕弯、不堆术语。
- 不下「大凶」「必败」这类负面死结论；强调主动权和选择权始终在用户自己手里。
- 不替用户做重大人生决定，只顺着传统文化的意象给方向和宽慰。
- 落点温和、给人力量，带一点中国传统文化的韵味。
- 篇幅 150-300 字，一两段，不要分点列清单。
- 用中文。"""


def _compact_result(result: dict) -> str:
    """把排盘结果裁剪成喂给模型的紧凑文本。"""
    if not isinstance(result, dict):
        return str(result)[:MAX_RESULT_CHARS]
    cleaned = {k: v for k, v in result.items() if k not in _DROP_KEYS}
    try:
        text = json.dumps(cleaned, ensure_ascii=False)
    except Exception:
        text = str(cleaned)
    if len(text) > MAX_RESULT_CHARS:
        text = text[:MAX_RESULT_CHARS] + "…(已截断)"
    return text


def ai_interpret(divine_type: str, result: dict, user_context: str, timeout: int = 60):
    """结合排盘结果 + 求测者处境，返回一段白话解读。失败返回 None。"""
    # 检查配置是否完整
    if not KIRO_BASE or not KIRO_KEY:
        return None
    
    user_context = (user_context or "").strip()[:MAX_CONTEXT_CHARS]
    if not user_context:
        return None

    result_text = _compact_result(result)
    user_prompt = (
        f"【占卜类型】{divine_type}\n\n"
        f"【排盘结果（程序精确推算，请据此解读）】\n{result_text}\n\n"
        f"【求测者的处境/想问的事】\n{user_context}\n\n"
        "请按 system 要求，结合排盘结果给这位求测者一段白话解读。"
    )

    payload = {
        "model": KIRO_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.75,
        "max_tokens": 800,
    }
    headers = {
        "Authorization": f"Bearer {KIRO_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            f"{KIRO_BASE}/chat/completions",
            json=payload, headers=headers, timeout=timeout,
        )
        resp.raise_for_status()
        data = json.loads(resp.content.decode("utf-8"))
        content = (data["choices"][0]["message"]["content"] or "").strip()
        return content or None
    except Exception:
        return None
