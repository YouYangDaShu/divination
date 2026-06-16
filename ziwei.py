#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""紫微斗数排盘（通过 Node 桥接调 iztro 本体）

所有星曜（主星+辅星+杂耀+四化+亮度+大限+长生12神）一次性全对，永远不会抄错。
"""
import datetime
import json
import os
import subprocess

_BRIDGE_SCRIPT = os.path.join(os.path.dirname(__file__), "ziwei_bridge.js")
_NODE_BIN = "/home/youyang/.local/bin/node"

# 生肖表
ZODIAC = ["鼠","牛","虎","兔","龙","蛇","马","羊","猴","鸡","狗","猪"]
EARTHLY_BRANCHES = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]


def _hour_to_time_index(hour: int, minute: int = 0) -> int:
    """把 24 小时制转成时辰索引 0-11（0=子,1=丑,...,11=亥）"""
    if hour == 23 or hour == 0:
        return 0  # 子时
    return ((hour + 1) // 2) % 12


def _get_zodiac_sign(month: int, day: int) -> str:
    signs = [
        ((1, 20), (2, 19), "水瓶座"), ((2, 20), (3, 20), "双鱼座"),
        ((3, 21), (4, 20), "白羊座"), ((4, 21), (5, 20), "金牛座"),
        ((5, 21), (6, 21), "双子座"), ((6, 22), (7, 22), "巨蟹座"),
        ((7, 23), (8, 22), "狮子座"), ((8, 23), (9, 22), "处女座"),
        ((9, 23), (10, 23), "天秤座"), ((10, 24), (11, 22), "天蝎座"),
        ((11, 23), (12, 21), "射手座"), ((12, 22), (1, 19), "摩羯座"),
    ]
    for (sm, sd), (em, ed), name in signs:
        if sm == 12:
            if (month == 12 and day >= sd) or (month == 1 and day <= ed):
                return name
        else:
            if (month == sm and day >= sd) or (month == em and day <= ed):
                return name
    return "?"


def ziwei_full(birth: datetime.datetime, gender: str, fix_leap: bool = True) -> dict:
    """完整紫微斗数排盘（调 iztro Node 库）

    Args:
        birth: 阳历生辰
        gender: '男' 或 '女'
        fix_leap: 是否修正闰月（iztro 默认 True）
    """
    solar_date = birth.strftime("%Y-%m-%d")
    time_index = _hour_to_time_index(birth.hour, birth.minute)

    # 调 Node 桥接脚本
    cmd = [_NODE_BIN, _BRIDGE_SCRIPT, solar_date, str(time_index), gender]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10,
            cwd=os.path.dirname(__file__)
        )
    except FileNotFoundError:
        raise ImportError(f"Node.js 未找到: {_NODE_BIN}，请安装 Node.js")

    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        raise RuntimeError(f"iztro 排盘失败: {stderr}")

    try:
        raw = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise RuntimeError("iztro 输出解析失败")

    return _to_frontend_format(raw, birth, gender)


def _to_frontend_format(raw: dict, birth: datetime.datetime, gender: str) -> dict:
    """把 iztro 原始 JSON 转成前端期望的嵌套格式"""
    palaces = []
    for p in raw.get("palaces", []):
        # 主星：name + brightness + mutagen
        majors = []
        for s in p.get("majorStars", []):
            parts = [s.get("name", "")]
            b = s.get("brightness", "")
            m = s.get("mutagen", "")
            if b:
                parts.append(b)
            if m:
                parts.append(m)
            majors.append("".join(parts))

        # 辅星：name + brightness
        minors = []
        for s in p.get("minorStars", []):
            parts = [s.get("name", "")]
            b = s.get("brightness", "")
            if b:
                parts.append(b)
            minors.append("".join(parts))

        # 杂耀：name only
        adjs = [s.get("name", "") for s in p.get("adjectiveStars", [])]

        palaces.append({
            "index": p.get("index"),
            "name": p.get("name"),
            "stem": p.get("heavenlyStem", ""),
            "branch": p.get("earthlyBranch", ""),
            "is_body_palace": p.get("isBodyPalace", False),
            "is_original_palace": p.get("isOriginalPalace", False),
            "major_stars": majors,
            "minor_stars": minors,
            "adjective_stars": adjs,
            "decadal": p.get("decadal"),
            "changsheng12": p.get("changsheng12", ""),
            "boshi12": p.get("boshi12", ""),
            "jiangqian12": p.get("jiangqian12", ""),
            "suiqian12": p.get("suiqian12", ""),
            "ages": p.get("ages"),
        })

    # 计算当前年龄和大限
    today = datetime.date.today()
    age = today.year - birth.year - (1 if (today.month, today.day) < (birth.month, birth.day) else 0)
    # 虚岁 = 实岁 + 1
    virtual_age = age + 1

    current_decadal_palace = None
    current_decadal_range = None
    for p in palaces:
        d = p.get("decadal")
        if d and d.get("range") and len(d["range"]) == 2:
            if d["range"][0] <= virtual_age <= d["range"][1]:
                current_decadal_palace = p["name"]
                current_decadal_range = d["range"]
                break

    # 命主/身主
    soul_master = raw.get("soul", "")
    body_master = raw.get("body", "")
    # 命宫地支/身宫地支
    soul_branch = raw.get("earthlyBranchOfSoulPalace", "")
    body_branch = raw.get("earthlyBranchOfBodyPalace", "")
    # 五行局
    five_elements = raw.get("fiveElementsClass", "")
    # 星座
    sign = raw.get("sign", "") or _get_zodiac_sign(birth.month, birth.day)
    # 生肖
    zodiac = raw.get("zodiac", "")

    result = {
        "datetime": datetime.datetime.now().isoformat(),
        "input": {
            "birth": birth.isoformat(),
            "gender": gender,
            "time_idx": _hour_to_time_index(birth.hour, birth.minute),
        },
        "basic": {
            "gender": gender,
            "solar_date": birth.strftime("%Y-%m-%d %H:%M"),
            "lunar_date": raw.get("lunarDate", ""),
            "chinese_date": raw.get("chineseDate", ""),
            "time": raw.get("time", ""),
            "time_range": raw.get("timeRange", ""),
            "sign": sign,
            "zodiac": zodiac,
            "soul_branch": soul_branch,
            "body_branch": body_branch,
            "soul_master": soul_master,
            "body_master": body_master,
            "five_elements": five_elements,
            "five_elements_class": five_elements,
        },
        "palaces": palaces,
        "current_age": age,
        "current_virtual_age": virtual_age,
    }
    if current_decadal_palace:
        result["current_decadal_palace"] = current_decadal_palace
        result["current_decadal_range"] = current_decadal_range

    return result


# 便于命令行测试
if __name__ == "__main__":
    b = datetime.datetime(1995, 6, 16, 14, 30)
    r = ziwei_full(b, "男")
    print(json.dumps(r, ensure_ascii=False, indent=2))
