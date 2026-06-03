# -*- coding: utf-8 -*-
"""
八字合婚 · 六大维度
1. 生肖（年支）合冲刑害
2. 日柱天干五合
3. 日柱地支六合/六冲/相害
4. 五行互补
5. 纳音相生相克
6. 喜用互补
"""

import datetime
from typing import Dict, List
from bazi import (
    full_bazi_chart, GAN_WUXING, ZHI_WUXING, WUXING_SHENG, WUXING_KE,
    LIU_HE, LIU_CHONG, LIU_HAI, SAN_HE, SAN_HUI,
    SAN_XING_GROUPS, ZI_MAO_XING, ZI_XING, get_na_yin,
)


# 生肖（地支序）
SHENG_XIAO = {
    "子": "鼠", "丑": "牛", "寅": "虎", "卯": "兔",
    "辰": "龙", "巳": "蛇", "午": "马", "未": "羊",
    "申": "猴", "酉": "鸡", "戌": "狗", "亥": "猪",
}

# 天干五合
GAN_HE = {
    ("甲", "己"): "土", ("己", "甲"): "土",
    ("乙", "庚"): "金", ("庚", "乙"): "金",
    ("丙", "辛"): "水", ("辛", "丙"): "水",
    ("丁", "壬"): "木", ("壬", "丁"): "木",
    ("戊", "癸"): "火", ("癸", "戊"): "火",
}

# 天干相冲
GAN_CHONG = [
    ("甲", "庚"), ("乙", "辛"), ("丙", "壬"), ("丁", "癸"),
]

# 天干相克（甲克戊、乙克己等）
GAN_KE = {
    ("甲", "戊"), ("乙", "己"), ("丙", "庚"), ("丁", "辛"),
    ("戊", "壬"), ("己", "癸"), ("庚", "甲"), ("辛", "乙"),
    ("壬", "丙"), ("癸", "丁"),
}


def check_zhi(z1: str, z2: str) -> Dict:
    """检查两个地支的关系"""
    if z1 == z2:
        return {"type": "同支", "level": "中性", "desc": f"皆为{z1}（{SHENG_XIAO[z1]}）", "score": 0}

    # 六冲
    for a, b in LIU_CHONG:
        if (z1, z2) == (a, b) or (z2, z1) == (a, b):
            return {"type": "六冲", "level": "大凶", "desc": f"{z1}{z2}相冲", "score": -25}

    # 六害
    for a, b in LIU_HAI:
        if (z1, z2) == (a, b) or (z2, z1) == (a, b):
            return {"type": "六害", "level": "凶", "desc": f"{z1}{z2}相害", "score": -15}

    # 三刑
    if {z1, z2}.issubset(set(["寅", "巳", "申"])) and z1 != z2:
        return {"type": "三刑", "level": "凶", "desc": f"{z1}{z2}互刑（无恩之刑）", "score": -15}
    if {z1, z2}.issubset(set(["丑", "未", "戌"])) and z1 != z2:
        return {"type": "三刑", "level": "凶", "desc": f"{z1}{z2}互刑（恃势之刑）", "score": -15}
    if (z1, z2) in [("子", "卯"), ("卯", "子")]:
        return {"type": "相刑", "level": "凶", "desc": f"{z1}{z2}相刑（无礼之刑）", "score": -12}

    # 六合
    if (z1, z2) in LIU_HE:
        wx = LIU_HE[(z1, z2)]
        return {"type": "六合", "level": "大吉", "desc": f"{z1}{z2}六合化{wx}", "score": 25}
    if (z2, z1) in LIU_HE:
        wx = LIU_HE[(z2, z1)]
        return {"type": "六合", "level": "大吉", "desc": f"{z1}{z2}六合化{wx}", "score": 25}

    # 三合（部分）
    for combo, label in SAN_HE:
        if z1 in combo and z2 in combo:
            return {"type": "三合", "level": "吉", "desc": f"{z1}{z2}属{''.join(combo)}{label}", "score": 18}

    # 三会
    for combo, label in SAN_HUI:
        if z1 in combo and z2 in combo:
            return {"type": "三会", "level": "吉", "desc": f"{z1}{z2}属{''.join(combo)}{label}", "score": 15}

    return {"type": "中性", "level": "平", "desc": f"{z1}{z2}无特殊关系", "score": 0}


def check_gan(g1: str, g2: str) -> Dict:
    """检查两个天干的关系"""
    if g1 == g2:
        return {"type": "同干", "level": "中性", "desc": f"皆为{g1}", "score": 0}

    # 五合
    if (g1, g2) in GAN_HE:
        return {"type": "五合", "level": "大吉", "desc": f"{g1}{g2}合化{GAN_HE[(g1, g2)]}", "score": 22}

    # 相冲
    for a, b in GAN_CHONG:
        if (g1, g2) == (a, b) or (g2, g1) == (a, b):
            return {"type": "相冲", "level": "凶", "desc": f"{g1}{g2}相冲", "score": -15}

    # 相克
    if (g1, g2) in GAN_KE:
        return {"type": "克泄", "level": "小凶", "desc": f"{g1}克{g2}", "score": -8}
    if (g2, g1) in GAN_KE:
        return {"type": "克泄", "level": "小凶", "desc": f"{g2}克{g1}", "score": -8}

    # 相生
    g1_wx = GAN_WUXING[g1]
    g2_wx = GAN_WUXING[g2]
    if WUXING_SHENG[g1_wx] == g2_wx:
        return {"type": "相生", "level": "吉", "desc": f"{g1}({g1_wx})生{g2}({g2_wx})", "score": 12}
    if WUXING_SHENG[g2_wx] == g1_wx:
        return {"type": "相生", "level": "吉", "desc": f"{g2}({g2_wx})生{g1}({g1_wx})", "score": 12}

    return {"type": "中性", "level": "平", "desc": f"{g1}{g2}无特殊关系", "score": 0}


def check_wuxing_complement(c1: Dict, c2: Dict) -> Dict:
    """五行互补检查"""
    missing1 = set(c1["missing"])
    missing2 = set(c2["missing"])

    has1 = set(k for k, v in c1["wuxing_counts"].items() if v > 0)
    has2 = set(k for k, v in c2["wuxing_counts"].items() if v > 0)

    # 对方补我的缺
    he_补我 = list(missing1 & has2)  # 我缺的，他有
    我补他 = list(missing2 & has1)  # 他缺的，我有

    score = 0
    desc_lines = []

    if he_补我:
        score += len(he_补我) * 8
        desc_lines.append(f"对方为你补：{ '、'.join(he_补我) }")
    if 我补他:
        score += len(我补他) * 8
        desc_lines.append(f"你为对方补：{ '、'.join(我补他) }")

    if not he_补我 and not 我补他:
        # 都没缺
        if not missing1 and not missing2:
            desc_lines.append("双方五行均齐，各自圆满")
            score = 5
        else:
            desc_lines.append(f"五行互补不明显（你缺{ '、'.join(c1['missing']) or '无'}，他缺{'、'.join(c2['missing']) or '无'}）")

    # 双方都旺一个、且都缺另一个 — 极不互补
    if c1["strongest"] == c2["strongest"] and c1["weakest"] == c2["weakest"]:
        score -= 5
        desc_lines.append(f" 双方同旺{c1['strongest']}同弱{c1['weakest']}，五行偏向相似")

    return {
        "score": min(score, 25),  # 最多 25
        "he_补我": he_补我,
        "我补他": 我补他,
        "desc": "；".join(desc_lines) or "—",
    }


def check_na_yin(ny1: str, ny2: str) -> Dict:
    """纳音相生相克（日柱纳音）"""
    # 纳音五行：取末字提取属性
    # 海中金、剑锋金、白蜡金、沙中金、金箔金、钗钏金 = 金
    # 炉中火、山头火、覆灯火、天河水(水)... 这里取最后一个字判断
    def na_yin_wx(ny: str) -> str:
        last = ny[-1]
        return last if last in "金木水火土" else "?"

    wx1 = na_yin_wx(ny1)
    wx2 = na_yin_wx(ny2)

    if wx1 == "?" or wx2 == "?":
        return {"score": 0, "desc": f"纳音 {ny1} / {ny2} 无法识别", "level": "平"}

    if wx1 == wx2:
        return {"score": 8, "desc": f"双方纳音同为{wx1}（{ny1} / {ny2}）", "level": "吉"}

    if WUXING_SHENG[wx1] == wx2:
        return {"score": 12, "desc": f"你的{ny1}({wx1})生对方{ny2}({wx2})", "level": "大吉"}
    if WUXING_SHENG[wx2] == wx1:
        return {"score": 12, "desc": f"对方{ny2}({wx2})生你{ny1}({wx1})", "level": "大吉"}

    if WUXING_KE[wx1] == wx2:
        return {"score": -10, "desc": f"你的{ny1}({wx1})克对方{ny2}({wx2})", "level": "凶"}
    if WUXING_KE[wx2] == wx1:
        return {"score": -10, "desc": f"对方{ny2}({wx2})克你{ny1}({wx1})", "level": "凶"}

    return {"score": 3, "desc": f"双方纳音平和（{ny1} / {ny2}）", "level": "平"}


def check_xi_yong(c1: Dict, c2: Dict) -> Dict:
    """喜用神互补"""
    yong1 = set(c1["xi_yong"]["yong_shen"])
    yong2 = set(c2["xi_yong"]["yong_shen"])
    ji1 = set(c1["xi_yong"]["ji_shen"])
    ji2 = set(c2["xi_yong"]["ji_shen"])

    # 对方旺的五行
    str1 = c1["strongest"]
    str2 = c2["strongest"]

    score = 0
    desc_lines = []

    # 对方所旺正是我喜用
    if str2 in yong1:
        score += 12
        desc_lines.append(f"[选] 对方旺{str2}恰是你喜用")
    if str1 in yong2:
        score += 12
        desc_lines.append(f"[选] 你旺{str1}恰是对方喜用")

    # 对方所旺却是我忌神
    if str2 in ji1:
        score -= 8
        desc_lines.append(f"[否] 对方旺{str2}却是你忌神")
    if str1 in ji2:
        score -= 8
        desc_lines.append(f"[否] 你旺{str1}却是对方忌神")

    # 喜用相同 — 同需求
    common_yong = yong1 & yong2
    if common_yong:
        score += 5
        desc_lines.append(f"双方共同喜用：{'、'.join(common_yong)}")

    return {
        "score": max(min(score, 20), -15),
        "desc": "；".join(desc_lines) or "喜用互补不明显",
    }


def he_hun_full(birth1: datetime.datetime, gender1: str,
                birth2: datetime.datetime, gender2: str) -> Dict:
    """完整合婚分析"""
    c1 = full_bazi_chart(birth1, gender1)
    c2 = full_bazi_chart(birth2, gender2)

    # 1. 生肖（年支）
    year_zhi1 = c1["columns"][0]["zhi"]
    year_zhi2 = c2["columns"][0]["zhi"]
    sx1, sx2 = SHENG_XIAO[year_zhi1], SHENG_XIAO[year_zhi2]
    sx_check = check_zhi(year_zhi1, year_zhi2)
    sx_result = {
        "category": "生肖",
        "you": f"属{sx1}（{year_zhi1}）",
        "ta": f"属{sx2}（{year_zhi2}）",
        "type": sx_check["type"],
        "level": sx_check["level"],
        "desc": sx_check["desc"],
        "score": sx_check["score"],
    }

    # 2. 日柱天干（夫妻宫主气）
    day_gan1 = c1["columns"][2]["gan"]
    day_gan2 = c2["columns"][2]["gan"]
    gan_check = check_gan(day_gan1, day_gan2)
    gan_result = {
        "category": "日干",
        "you": f"日干{day_gan1}({GAN_WUXING[day_gan1]})",
        "ta": f"日干{day_gan2}({GAN_WUXING[day_gan2]})",
        "type": gan_check["type"],
        "level": gan_check["level"],
        "desc": gan_check["desc"],
        "score": gan_check["score"],
    }

    # 3. 日柱地支（夫妻宫）
    day_zhi1 = c1["columns"][2]["zhi"]
    day_zhi2 = c2["columns"][2]["zhi"]
    zhi_check = check_zhi(day_zhi1, day_zhi2)
    zhi_result = {
        "category": "夫妻宫",
        "you": f"日支{day_zhi1}",
        "ta": f"日支{day_zhi2}",
        "type": zhi_check["type"],
        "level": zhi_check["level"],
        "desc": zhi_check["desc"],
        "score": zhi_check["score"],
    }

    # 4. 五行互补
    wx_check = check_wuxing_complement(c1, c2)
    wx_result = {
        "category": "五行互补",
        "desc": wx_check["desc"],
        "score": wx_check["score"],
        "level": "吉" if wx_check["score"] >= 12 else ("平" if wx_check["score"] >= 0 else "凶"),
    }

    # 5. 纳音（日柱）
    na_yin1 = c1["columns"][2]["na_yin"]
    na_yin2 = c2["columns"][2]["na_yin"]
    ny_check = check_na_yin(na_yin1, na_yin2)
    ny_result = {
        "category": "日柱纳音",
        "you": na_yin1,
        "ta": na_yin2,
        "desc": ny_check["desc"],
        "score": ny_check["score"],
        "level": ny_check["level"],
    }

    # 6. 喜用互补
    xy_check = check_xi_yong(c1, c2)
    xy_result = {
        "category": "喜用互补",
        "desc": xy_check["desc"],
        "score": xy_check["score"],
        "level": "吉" if xy_check["score"] >= 10 else ("平" if xy_check["score"] >= 0 else "凶"),
    }

    # 总分（加权）
    total_score = (
        sx_result["score"]
        + gan_result["score"]
        + zhi_result["score"]
        + wx_result["score"]
        + ny_result["score"]
        + xy_result["score"]
    )

    # 评级（满分约 +135，下限约 -85）
    if total_score >= 60:
        rating = "上上签"
        rating_color = "#d4af37"  # 金色
        verdict = "天作之合，五行互补，命理大吉。"
    elif total_score >= 35:
        rating = "上等"
        rating_color = "#a8dadc"  # 玉色
        verdict = "命理相合，互补有助，是良配。"
    elif total_score >= 15:
        rating = "中上"
        rating_color = "#76c893"  # 浅绿
        verdict = "整体匹配良好，小处需磨合。"
    elif total_score >= -5:
        rating = "中等"
        rating_color = "#888"
        verdict = "无明显冲突，但缘分需经营。"
    elif total_score >= -25:
        rating = "中下"
        rating_color = "#cd853f"  # 棕黄
        verdict = "存在不合处，宜谨慎相处。"
    else:
        rating = "下等"
        rating_color = "#c44"
        verdict = "命理冲克较多，相处会较辛苦。"

    # 整理简明结论
    issues = []
    blessings = []
    for r in [sx_result, gan_result, zhi_result, wx_result, ny_result, xy_result]:
        if r["score"] >= 12:
            blessings.append(f"{r['category']}：{r.get('desc', r.get('type', ''))}")
        elif r["score"] <= -10:
            issues.append(f"{r['category']}：{r.get('desc', r.get('type', ''))}")

    return {
        "person1": {
            "birth": birth1.isoformat(),
            "gender": gender1,
            "lunar_str": c1["lunar_str"],
            "bazi": " ".join(col["ganzhi"] for col in c1["columns"]),
            "day_gan": day_gan1,
            "day_wuxing": GAN_WUXING[day_gan1],
            "sheng_xiao": sx1,
            "strength": c1["strength"]["strength"],
        },
        "person2": {
            "birth": birth2.isoformat(),
            "gender": gender2,
            "lunar_str": c2["lunar_str"],
            "bazi": " ".join(col["ganzhi"] for col in c2["columns"]),
            "day_gan": day_gan2,
            "day_wuxing": GAN_WUXING[day_gan2],
            "sheng_xiao": sx2,
            "strength": c2["strength"]["strength"],
        },
        "details": [sx_result, gan_result, zhi_result, wx_result, ny_result, xy_result],
        "total_score": total_score,
        "rating": rating,
        "rating_color": rating_color,
        "verdict": verdict,
        "blessings": blessings,
        "issues": issues,
    }


if __name__ == "__main__":
    import json
    r = he_hun_full(
        datetime.datetime(1995, 6, 15, 14, 30), "男",
        datetime.datetime(1996, 8, 22, 10, 0), "女",
    )
    print(json.dumps(r, ensure_ascii=False, indent=2))
