#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""紫微斗数排盘 (基于 py-iztro)

核心：调用 py-iztro 计算 12 宫位 + 主星 + 辅星 + 大限/小限 + 流年。
返回结构化 JSON，前端按"圆桌十二宫"或"扁平十二宫"渲染均可。
"""

import datetime
from typing import Optional


def _to_dict(obj):
    """递归把 pydantic 模型转 dict（兼容 v1/v2）。"""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return obj


def ziwei_full(birth: datetime.datetime, gender: str, fix_leap: bool = True) -> dict:
    """完整紫微斗数排盘。

    Args:
        birth: 阳历生辰
        gender: '男' 或 '女'
        fix_leap: 是否修正闰月（一般 True）
    """
    from py_iztro import Astro

    astro = Astro()
    # 时辰索引：子=0, 丑=1, ..., 亥=11，按真太阳时小时映射
    # py-iztro 的时辰参数是 0-11
    h = birth.hour
    # 23:00-00:59 子时(0)，01:00-02:59 丑时(1)，...
    if h == 23:
        time_idx = 0
    else:
        time_idx = ((h + 1) // 2) % 12

    solar_str = birth.strftime("%Y-%m-%d")
    chart = astro.by_solar(solar_str, time_idx, gender, fix_leap, "zh-CN")
    data = _to_dict(chart)

    # 简化输出
    result = {
        "datetime": datetime.datetime.now().isoformat(),
        "input": {
            "birth": birth.isoformat(),
            "gender": gender,
            "time_idx": time_idx,
        },
        "basic": {
            "gender": data.get("gender"),
            "solar_date": data.get("solar_date"),
            "lunar_date": data.get("lunar_date"),
            "chinese_date": data.get("chinese_date"),  # 八字
            "time": data.get("time"),
            "time_range": data.get("time_range"),
            "sign": data.get("sign"),  # 星座
            "zodiac": data.get("zodiac"),  # 生肖
            "soul_branch": data.get("earthly_branch_of_soul_palace"),
            "body_branch": data.get("earthly_branch_of_body_palace"),
            "soul_master": data.get("soul"),  # 命主
            "body_master": data.get("body"),  # 身主
            "five_elements": data.get("five_elements_class"),  # 五行局
        },
        "palaces": [],
    }

    # 整理 12 宫
    for p in data.get("palaces", []):
        major_stars = [s.get("name") + (s.get("brightness") or "") + (("[" + s["mutagen"] + "]") if s.get("mutagen") else "")
                       for s in (p.get("major_stars") or [])]
        minor_stars = [s.get("name") + (s.get("brightness") or "") for s in (p.get("minor_stars") or [])]
        adj_stars = [s.get("name") for s in (p.get("adjective_stars") or [])]

        result["palaces"].append({
            "index": p.get("index"),
            "name": p.get("name"),  # 命/兄弟/夫妻/...
            "is_body_palace": p.get("is_body_palace"),
            "is_original_palace": p.get("is_original_palace"),
            "stem": p.get("heavenly_stem"),
            "branch": p.get("earthly_branch"),
            "major_stars": major_stars,
            "minor_stars": minor_stars,
            "adjective_stars": adj_stars,
            "changsheng12": p.get("changsheng12"),
            "boshi12": p.get("boshi12"),
            "jiangqian12": p.get("jiangqian12"),
            "suiqian12": p.get("suiqian12"),
            "decadal": p.get("decadal"),  # {range:[a,b], stem, branch}
            "ages": p.get("ages"),  # 该宫小限对应的年龄列表
        })

    # 找当前年龄所在的大限宫
    today = datetime.date.today()
    age = today.year - birth.year - (
        1 if (today.month, today.day) < (birth.month, birth.day) else 0
    )
    result["current_age"] = age
    for p in result["palaces"]:
        d = p.get("decadal") or {}
        rng = d.get("range") or []
        if len(rng) == 2 and rng[0] <= age <= rng[1]:
            result["current_decadal_palace"] = p["name"]
            result["current_decadal_range"] = rng
            break

    return result


# 便于命令行测试
if __name__ == "__main__":
    import json
    b = datetime.datetime(2000, 10, 29, 1, 0)
    r = ziwei_full(b, "男")
    print(json.dumps(r, ensure_ascii=False, indent=2))
