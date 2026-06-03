#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解梦本：双视角解梦（周公传统 + 心理学）

调用配置的 AI 模型。返回结构化 JSON：
{
  "dream_text": "原梦境",
  "datetime": "...",
  "mood_on_wake": "醒来情绪标签",
  "context": "用户当下处境（可选）",
  "zhougong": {"symbols": [...], "interpretation": "..."},
  "psychology": {"archetypes": [...], "interpretation": "..."},
  "summary": "综合给你的话",
  "suggestions": [...]
}
"""

from __future__ import annotations
import os
import json
import re
import datetime
from typing import Dict, Optional

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

LLM_BASE = KIRO_BASE
LLM_KEY = KIRO_KEY
LLM_MODEL = KIRO_MODEL

# ===== Prompt =====
SYSTEM_PROMPT = """你是一位融合传统文化与现代心理学的解梦顾问。

工作流程：
1. 用「周公解梦」传统象征体系（动物、自然、人事、行为等典籍含义）解读
2. 用心理学视角（弗洛伊德潜意识/荣格原型/认知神经科学）解读
3. 综合给出落地建议

写作风格：
- 直白不绕弯，不要 "可能"、"或许" 满天飞
- 不夸大不渲染恐怖，不下"大凶"这种结论
- 不算命，是分析
- 用户是中国人，例子用中文语境

输出严格 JSON，字段如下：
{
  "zhougong": {
    "symbols": ["梦中关键象征 1", "象征 2", ...],   // 3-6 个
    "interpretation": "传统象征解读，2-4 句"
  },
  "psychology": {
    "archetypes": ["原型/防御机制/情绪 1", ...],     // 2-4 个
    "interpretation": "心理学解读，2-4 句"
  },
  "summary": "综合两方观点给用户的一句话总结，直接说人话",
  "suggestions": [
    "可执行的建议 1",
    "建议 2",
    "建议 3"
  ]
}

只返回 JSON，不要任何其他文字、不要代码块标记。"""


def _build_user_prompt(dream_text: str, mood: str = "", context: str = "") -> str:
    parts = [f"【梦境】\n{dream_text}"]
    if mood:
        parts.append(f"【醒来情绪】{mood}")
    if context:
        parts.append(f"【近期处境/线索】{context}")
    parts.append("\n请按 system 要求返回 JSON。")
    return "\n\n".join(parts)


def _extract_json(text: str) -> Dict:
    """从 LLM 返回里抠 JSON。容忍代码块包裹。"""
    text = text.strip()
    # 去 ```json ... ``` 包裹
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        text = m.group(1)
    # 找第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def interpret_dream(
    dream_text: str,
    mood: str = "",
    context: str = "",
    timeout: int = 120,
) -> Dict:
    """调用 LLM 解梦，返回结构化结果。

    Raises:
        ValueError: 输入空梦境
        requests.HTTPError: API 错误
        json.JSONDecodeError: 解析失败
    """
    # 检查配置是否完整
    if not LLM_BASE or not LLM_KEY:
        raise ValueError("AI 未配置，请在 config.py 中设置 AI_API_BASE 和 AI_API_KEY")
    
    dream_text = (dream_text or "").strip()
    if not dream_text:
        raise ValueError("梦境内容不能为空")

    user_prompt = _build_user_prompt(dream_text, mood, context)
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 2000,
    }
    headers = {
        "Authorization": f"Bearer {LLM_KEY}",
        "Content-Type": "application/json",
    }

    resp = requests.post(
        f"{LLM_BASE}/chat/completions",
        json=payload,
        headers=headers,
        timeout=timeout,
    )
    resp.raise_for_status()
    # 防上游网关 Content-Type 不带 charset 导致 latin-1 误解
    data = json.loads(resp.content.decode("utf-8"))
    content = data["choices"][0]["message"]["content"]
    parsed = _extract_json(content)

    # 标准化字段（防 LLM 缺字段）
    parsed.setdefault("zhougong", {})
    parsed["zhougong"].setdefault("symbols", [])
    parsed["zhougong"].setdefault("interpretation", "")
    parsed.setdefault("psychology", {})
    parsed["psychology"].setdefault("archetypes", [])
    parsed["psychology"].setdefault("interpretation", "")
    parsed.setdefault("summary", "")
    parsed.setdefault("suggestions", [])

    return parsed


def dream_full(
    dream_text: str,
    mood: str = "",
    context: str = "",
    dream_date: Optional[str] = None,
) -> Dict:
    """完整解梦流程（含元数据封装）。"""
    interpretation = interpret_dream(dream_text, mood, context)
    now = datetime.datetime.now()
    return {
        "dream_text": dream_text,
        "mood_on_wake": mood or "",
        "context": context or "",
        "dream_date": dream_date or now.strftime("%Y-%m-%d"),
        "datetime": now.isoformat(),
        "model": LLM_MODEL,
        **interpretation,
    }


if __name__ == "__main__":
    # 自测
    sample = "我梦见自己掉进一口很深的井，井里都是水但我没淹死，往上看井口很小很远"
    r = dream_full(sample, mood="醒来有点紧张但松了口气")
    print(json.dumps(r, ensure_ascii=False, indent=2))
