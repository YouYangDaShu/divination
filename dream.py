# ===== 解梦模块（纯排版）=====
# 只出梦境结构化数据，解读由 Hermes 完成

import datetime
from typing import Dict, Optional


def dream_full(
    dream_text: str,
    mood: str = "",
    context: str = "",
    dream_date: Optional[str] = None,
) -> Dict:
    """解梦接口 - 只返回梦境元数据，不做任何解读。"""
    now = datetime.datetime.now()
    return {
        "dream_text": dream_text,
        "mood_on_wake": mood or "",
        "context": context or "",
        "dream_date": dream_date or now.strftime("%Y-%m-%d"),
        "datetime": now.isoformat(),
    }
