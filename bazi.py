#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字排盘核心
- 四柱（年月日时）
- 五行统计
- 十神
- 大运（10年一步）
- 流年
- 综合运势
"""

import datetime
from typing import Dict, List, Tuple, Optional
import cnlunar


# 天干
TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
# 地支
DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 天干五行
GAN_WUXING = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
}
# 天干阴阳
GAN_YIN_YANG = {
    "甲": "阳", "丙": "阳", "戊": "阳", "庚": "阳", "壬": "阳",
    "乙": "阴", "丁": "阴", "己": "阴", "辛": "阴", "癸": "阴",
}

# 地支五行
ZHI_WUXING = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木",
    "辰": "土", "巳": "火", "午": "火", "未": "土",
    "申": "金", "酉": "金", "戌": "土", "亥": "水",
}
ZHI_YIN_YANG = {
    "子": "阳", "寅": "阳", "辰": "阳", "午": "阳", "申": "阳", "戌": "阳",
    "丑": "阴", "卯": "阴", "巳": "阴", "未": "阴", "酉": "阴", "亥": "阴",
}

# 地支藏干（主气、中气、余气）
ZHI_CANG_GAN = {
    "子": ["癸"],
    "丑": ["己", "癸", "辛"],
    "寅": ["甲", "丙", "戊"],
    "卯": ["乙"],
    "辰": ["戊", "乙", "癸"],
    "巳": ["丙", "庚", "戊"],
    "午": ["丁", "己"],
    "未": ["己", "丁", "乙"],
    "申": ["庚", "壬", "戊"],
    "酉": ["辛"],
    "戌": ["戊", "辛", "丁"],
    "亥": ["壬", "甲"],
}

# 五行生克
WUXING_SHENG = {"金": "水", "水": "木", "木": "火", "火": "土", "土": "金"}
WUXING_KE = {"金": "木", "木": "土", "土": "水", "水": "火", "火": "金"}

# 五行颜色（前端用）
WUXING_COLOR = {
    "金": "#d4af37",  # 金色
    "木": "#52c41a",  # 绿色
    "水": "#1890ff",  # 蓝色
    "火": "#f5222d",  # 红色
    "土": "#fa8c16",  # 土黄
}


# ============== 神煞 ==============
# 天乙贵人：日干 → 地支
TIAN_YI_GUI_REN = {
    "甲": ["丑", "未"], "戊": ["丑", "未"], "庚": ["丑", "未"],
    "乙": ["子", "申"], "己": ["子", "申"],
    "丙": ["亥", "酉"], "丁": ["亥", "酉"],
    "辛": ["寅", "午"],
    "壬": ["卯", "巳"], "癸": ["卯", "巳"],
}

# 桃花（咸池）：年支或日支 → 桃花地支
TAO_HUA = {
    "申": "酉", "子": "酉", "辰": "酉",  # 申子辰见酉
    "寅": "卯", "午": "卯", "戌": "卯",  # 寅午戌见卯
    "巳": "午", "酉": "午", "丑": "午",  # 巳酉丑见午
    "亥": "子", "卯": "子", "未": "子",  # 亥卯未见子
}

# 驿马：年支或日支 → 驿马地支
YI_MA = {
    "申": "寅", "子": "寅", "辰": "寅",
    "寅": "申", "午": "申", "戌": "申",
    "巳": "亥", "酉": "亥", "丑": "亥",
    "亥": "巳", "卯": "巳", "未": "巳",
}

# 红鸾：年支 → 红鸾
HONG_LUAN = {
    "子": "卯", "丑": "寅", "寅": "丑", "卯": "子",
    "辰": "亥", "巳": "戌", "午": "酉", "未": "申",
    "申": "未", "酉": "午", "戌": "巳", "亥": "辰",
}

# 天喜
TIAN_XI = {
    "子": "酉", "丑": "申", "寅": "未", "卯": "午",
    "辰": "巳", "巳": "辰", "午": "卯", "未": "寅",
    "申": "丑", "酉": "子", "戌": "亥", "亥": "戌",
}

# 文昌：日干 → 文昌
WEN_CHANG = {
    "甲": "巳", "乙": "午", "丙": "申", "丁": "酉",
    "戊": "申", "己": "酉", "庚": "亥", "辛": "子",
    "壬": "寅", "癸": "卯",
}

# 将星：年支或日支 → 将星
JIANG_XING = {
    "申": "子", "子": "子", "辰": "子",
    "寅": "午", "午": "午", "戌": "午",
    "巳": "酉", "酉": "酉", "丑": "酉",
    "亥": "卯", "卯": "卯", "未": "卯",
}

# 华盖
HUA_GAI = {
    "申": "辰", "子": "辰", "辰": "辰",
    "寅": "戌", "午": "戌", "戌": "戌",
    "巳": "丑", "酉": "丑", "丑": "丑",
    "亥": "未", "卯": "未", "未": "未",
}

# 神煞解释
SHEN_SHA_MEANING = {
    "天乙贵人": "命中有贵人扶持，逢凶化吉，遇难成祥",
    "桃花": "异性缘佳，主感情、艺术天赋，须防情劫",
    "驿马": "远行、变动、出差、迁居之星，主奔波也主机遇",
    "红鸾": "婚姻喜事，恋爱、结婚之星",
    "天喜": "喜庆之星，主婚姻、生子、升迁等好事",
    "文昌": "学业、文笔、文凭、聪慧之星",
    "将星": "权威、领导力，主事业有成，权重位高",
    "华盖": "孤高、宗教、玄学、艺术之星，主聪明但易孤独",
}


# ============== 地支合冲刑害 ==============
# 六合
LIU_HE = {
    ("子", "丑"): "土", ("寅", "亥"): "木", ("卯", "戌"): "火",
    ("辰", "酉"): "金", ("巳", "申"): "水", ("午", "未"): "(火土)",
}

# 三合（三合局）
SAN_HE = [
    (("申", "子", "辰"), "水局"),
    (("亥", "卯", "未"), "木局"),
    (("寅", "午", "戌"), "火局"),
    (("巳", "酉", "丑"), "金局"),
]

# 三会（方局）
SAN_HUI = [
    (("寅", "卯", "辰"), "东方木"),
    (("巳", "午", "未"), "南方火"),
    (("申", "酉", "戌"), "西方金"),
    (("亥", "子", "丑"), "北方水"),
]

# 六冲
LIU_CHONG = [
    ("子", "午"), ("丑", "未"), ("寅", "申"),
    ("卯", "酉"), ("辰", "戌"), ("巳", "亥"),
]

# 六害
LIU_HAI = [
    ("子", "未"), ("丑", "午"), ("寅", "巳"),
    ("卯", "辰"), ("申", "亥"), ("酉", "戌"),
]

# 三刑
SAN_XING_GROUPS = [
    (("寅", "巳", "申"), "无恩之刑"),
    (("丑", "戌", "未"), "持势之刑"),
]
# 子卯互刑（无礼）
ZI_MAO_XING = [("子", "卯")]
# 自刑
ZI_XING = ["辰", "午", "酉", "亥"]


# ============== 纳音五行（六十甲子纳音） ==============
NA_YIN = {
    "甲子": "海中金", "乙丑": "海中金",
    "丙寅": "炉中火", "丁卯": "炉中火",
    "戊辰": "大林木", "己巳": "大林木",
    "庚午": "路旁土", "辛未": "路旁土",
    "壬申": "剑锋金", "癸酉": "剑锋金",
    "甲戌": "山头火", "乙亥": "山头火",
    "丙子": "涧下水", "丁丑": "涧下水",
    "戊寅": "城头土", "己卯": "城头土",
    "庚辰": "白蜡金", "辛巳": "白蜡金",
    "壬午": "杨柳木", "癸未": "杨柳木",
    "甲申": "泉中水", "乙酉": "泉中水",
    "丙戌": "屋上土", "丁亥": "屋上土",
    "戊子": "霹雳火", "己丑": "霹雳火",
    "庚寅": "松柏木", "辛卯": "松柏木",
    "壬辰": "长流水", "癸巳": "长流水",
    "甲午": "沙中金", "乙未": "沙中金",
    "丙申": "山下火", "丁酉": "山下火",
    "戊戌": "平地木", "己亥": "平地木",
    "庚子": "壁上土", "辛丑": "壁上土",
    "壬寅": "金箔金", "癸卯": "金箔金",
    "甲辰": "覆灯火", "乙巳": "覆灯火",
    "丙午": "天河水", "丁未": "天河水",
    "戊申": "大驿土", "己酉": "大驿土",
    "庚戌": "钗钏金", "辛亥": "钗钏金",
    "壬子": "桑柘木", "癸丑": "桑柘木",
    "甲寅": "大溪水", "乙卯": "大溪水",
    "丙辰": "沙中土", "丁巳": "沙中土",
    "戊午": "天上火", "己未": "天上火",
    "庚申": "石榴木", "辛酉": "石榴木",
    "壬戌": "大海水", "癸亥": "大海水",
}


# ============== 旬空（六甲旬空） ==============
# 每旬十干，对应空亡两支
XUN_KONG = {
    # 甲子旬
    ("甲子", "乙丑", "丙寅", "丁卯", "戊辰", "己巳", "庚午", "辛未", "壬申", "癸酉"): ("戌", "亥"),
    # 甲戌旬
    ("甲戌", "乙亥", "丙子", "丁丑", "戊寅", "己卯", "庚辰", "辛巳", "壬午", "癸未"): ("申", "酉"),
    # 甲申旬
    ("甲申", "乙酉", "丙戌", "丁亥", "戊子", "己丑", "庚寅", "辛卯", "壬辰", "癸巳"): ("午", "未"),
    # 甲午旬
    ("甲午", "乙未", "丙申", "丁酉", "戊戌", "己亥", "庚子", "辛丑", "壬寅", "癸卯"): ("辰", "巳"),
    # 甲辰旬
    ("甲辰", "乙巳", "丙午", "丁未", "戊申", "己酉", "庚戌", "辛亥", "壬子", "癸丑"): ("寅", "卯"),
    # 甲寅旬
    ("甲寅", "乙卯", "丙辰", "丁巳", "戊午", "己未", "庚申", "辛酉", "壬戌", "癸亥"): ("子", "丑"),
}


def get_na_yin(ganzhi: str) -> str:
    """获取干支的纳音"""
    return NA_YIN.get(ganzhi, "?")


def get_xun_kong(day_ganzhi: str) -> Tuple[str, str]:
    """根据日柱获取旬空"""
    for xun, kong in XUN_KONG.items():
        if day_ganzhi in xun:
            return kong
    return ("?", "?")


# ============== 胎元、命宫、身宫 ==============
def get_tai_yuan(month_gan: str, month_zhi: str) -> str:
    """胎元：月干进一位，月支进三位"""
    gan_idx = (TIANGAN.index(month_gan) + 1) % 10
    zhi_idx = (DIZHI.index(month_zhi) + 3) % 12
    return TIANGAN[gan_idx] + DIZHI[zhi_idx]


def get_ming_gong(month_zhi: str, hour_zhi: str) -> str:
    """命宫：月支+时支算到丑（寅遁）"""
    # 标准命宫法：月将固定为寅起正月，加时支推命宫
    # 简化版：以月支为月将，时支与命宫相加为子（即顺数到亥位）
    # 月支寅=1、卯=2...丑=12
    month_num = (DIZHI.index(month_zhi) - DIZHI.index("寅")) % 12 + 1
    hour_num = (DIZHI.index(hour_zhi) - DIZHI.index("子")) % 12 + 1

    total = month_num + hour_num
    if total <= 14:
        ming_gong_num = 14 - total
    else:
        ming_gong_num = 26 - total

    # 命宫地支
    ming_zhi_idx = (DIZHI.index("寅") + ming_gong_num - 1) % 12
    ming_zhi = DIZHI[ming_zhi_idx]

    # 命宫天干（按五虎遁年起月例）— 简化为按年柱无关，仅返回地支
    return ming_zhi


# ============== 喜用神 ==============
def get_xi_yong(strength_score: float, day_wuxing: str) -> Dict:
    """根据日主强弱，给出喜用神和忌神"""
    # 五行循环
    sheng_table = {"金": "水", "水": "木", "木": "火", "火": "土", "土": "金"}
    ke_table = {"金": "木", "木": "土", "土": "水", "水": "火", "火": "金"}

    # 反推
    bei_sheng = {v: k for k, v in sheng_table.items()}  # 谁生我
    bei_ke = {v: k for k, v in ke_table.items()}  # 谁克我

    same = day_wuxing
    sheng_me = bei_sheng[day_wuxing]  # 印
    me_sheng = sheng_table[day_wuxing]  # 食伤
    me_ke = ke_table[day_wuxing]  # 财
    ke_me = bei_ke[day_wuxing]  # 官杀

    if strength_score >= 4:
        # 身强：泄、克、耗
        return {
            "type": "身强",
            "yong_shen": [me_sheng, me_ke, ke_me],
            "yong_label": "食伤、财、官杀",
            "ji_shen": [same, sheng_me],
            "ji_label": "比劫、印星",
            "advice": f"日主旺，喜{me_sheng}（食伤泄）、{me_ke}（财耗）、{ke_me}（官克）。忌{same}、{sheng_me}（再添助力反成累）。",
        }
    elif strength_score <= -4:
        # 身弱：扶、生
        return {
            "type": "身弱",
            "yong_shen": [same, sheng_me],
            "yong_label": "比劫、印星",
            "ji_shen": [me_sheng, me_ke, ke_me],
            "ji_label": "食伤、财、官杀",
            "advice": f"日主弱，喜{same}（比劫扶）、{sheng_me}（印星生）。忌{me_sheng}（食伤泄）、{me_ke}（财耗）、{ke_me}（官克）。",
        }
    else:
        # 中和
        return {
            "type": "中和",
            "yong_shen": [me_sheng, me_ke],
            "yong_label": "食伤、财（看具体格局）",
            "ji_shen": [],
            "ji_label": "看实际格局取舍",
            "advice": "日主中和，五行相对均衡。具体喜忌需结合月令、地支组合及格局综合判定。",
        }


# ============== 节气精算起运 ==============
# 24节气名（公历近似日期，月份内）
JIE_QI_NAMES = [
    "立春", "雨水", "惊蛰", "春分", "清明", "谷雨",
    "立夏", "小满", "芒种", "夏至", "小暑", "大暑",
    "立秋", "处暑", "白露", "秋分", "寒露", "霜降",
    "立冬", "小雪", "大雪", "冬至", "小寒", "大寒",
]


def get_qi_yun_age(birth: datetime.datetime, gender: str, year_gan: str) -> Dict:
    """精算起运岁数：从出生日数到下一个节（顺）或上一个节（逆），3天=1年"""
    year_yy = GAN_YIN_YANG[year_gan]
    direction = "顺" if (gender == "男" and year_yy == "阳") or (gender == "女" and year_yy == "阴") else "逆"

    # 用 cnlunar 拿当前/下一/上一节
    try:
        lunar = cnlunar.Lunar(birth, godType="8char")
        # cnlunar 提供 nextJieqiName / nextJieqi / dayJieqi 等
        next_jq_name = getattr(lunar, "nextJieqi", None)
        next_jq_dt = None
        last_jq_dt = None

        # 不依赖具体属性名，遍历 24节气日期
        # 用 cnlunar 的 thisYearSolarTermsDic 或 self.solarTermsDic
        try:
            terms = lunar.thisYearSolarTermsDic
        except AttributeError:
            terms = {}

        # 找下一个和上一个节气
        sorted_terms = []
        for name, val in (terms or {}).items():
            if isinstance(val, (list, tuple)) and len(val) >= 2:
                m, d = val[0], val[1]
                hour = val[2] if len(val) > 2 else 12
                try:
                    dt = datetime.datetime(birth.year, m, d, hour)
                except (ValueError, TypeError):
                    continue
                sorted_terms.append((dt, name))
        sorted_terms.sort()

        # 找下一个节（仅含立春/惊蛰/清明/立夏/芒种/小暑/立秋/白露/寒露/立冬/大雪/小寒，"节"为偶数索引）
        # 简化：以12节起运，但cnlunar一律返回所有24，按时间找最近的"节"
        node_names = {"立春", "惊蛰", "清明", "立夏", "芒种", "小暑", "立秋", "白露", "寒露", "立冬", "大雪", "小寒"}

        next_node = None
        last_node = None
        for dt, name in sorted_terms:
            if name not in node_names:
                continue
            if dt > birth:
                if next_node is None:
                    next_node = (dt, name)
            else:
                last_node = (dt, name)

        if direction == "顺" and next_node:
            delta = (next_node[0] - birth).total_seconds() / 86400
            ref_node = next_node[1]
        elif direction == "逆" and last_node:
            delta = (birth - last_node[0]).total_seconds() / 86400
            ref_node = last_node[1]
        else:
            # 退化为简化算法
            return {
                "direction": direction,
                "start_age": 8 if gender == "男" else 7,
                "start_months": 0,
                "method": "简化(无节气数据)",
                "ref_node": "?",
            }

        # 3天1年，1天4月，1时辰10日
        days = delta
        years = int(days // 3)
        remain_days = days - years * 3
        months = round(remain_days * 4)

        return {
            "direction": direction,
            "start_age": years,
            "start_months": months,
            "method": "节气精算(3天=1年)",
            "ref_node": ref_node,
            "days_to_node": round(days, 1),
        }
    except Exception:
        return {
            "direction": direction,
            "start_age": 8 if gender == "男" else 7,
            "start_months": 0,
            "method": "简化",
            "ref_node": "?",
        }


def find_shen_sha(bazi: Dict) -> List[Dict]:
    """查找神煞"""
    day_gan = bazi["day"][0]
    year_zhi = bazi["year"][1]
    day_zhi = bazi["day"][1]

    all_zhi = {
        "年支": bazi["year"][1],
        "月支": bazi["month"][1],
        "日支": bazi["day"][1],
        "时支": bazi["hour"][1],
    }

    found = []

    # 天乙贵人（看日干）
    tygr = TIAN_YI_GUI_REN.get(day_gan, [])
    for pos, zhi in all_zhi.items():
        if zhi in tygr:
            found.append({"name": "天乙贵人", "position": pos, "zhi": zhi, "meaning": SHEN_SHA_MEANING["天乙贵人"]})

    # 文昌（看日干）
    wc = WEN_CHANG.get(day_gan)
    for pos, zhi in all_zhi.items():
        if zhi == wc:
            found.append({"name": "文昌", "position": pos, "zhi": zhi, "meaning": SHEN_SHA_MEANING["文昌"]})

    # 桃花/驿马/将星/华盖（看年支或日支）
    for source_label, source_zhi in [("年支", year_zhi), ("日支", day_zhi)]:
        # 桃花
        th = TAO_HUA.get(source_zhi)
        for pos, zhi in all_zhi.items():
            if zhi == th and pos != source_label:
                found.append({"name": "桃花", "position": f"{pos}(从{source_label})", "zhi": zhi, "meaning": SHEN_SHA_MEANING["桃花"]})
                break
        # 驿马
        ym = YI_MA.get(source_zhi)
        for pos, zhi in all_zhi.items():
            if zhi == ym and pos != source_label:
                found.append({"name": "驿马", "position": f"{pos}(从{source_label})", "zhi": zhi, "meaning": SHEN_SHA_MEANING["驿马"]})
                break
        # 将星
        jx = JIANG_XING.get(source_zhi)
        for pos, zhi in all_zhi.items():
            if zhi == jx:
                found.append({"name": "将星", "position": f"{pos}(从{source_label})", "zhi": zhi, "meaning": SHEN_SHA_MEANING["将星"]})
                break
        # 华盖
        hg = HUA_GAI.get(source_zhi)
        for pos, zhi in all_zhi.items():
            if zhi == hg and pos != source_label:
                found.append({"name": "华盖", "position": f"{pos}(从{source_label})", "zhi": zhi, "meaning": SHEN_SHA_MEANING["华盖"]})
                break

    # 红鸾、天喜（看年支）
    hl = HONG_LUAN.get(year_zhi)
    for pos, zhi in all_zhi.items():
        if zhi == hl:
            found.append({"name": "红鸾", "position": pos, "zhi": zhi, "meaning": SHEN_SHA_MEANING["红鸾"]})
            break
    tx = TIAN_XI.get(year_zhi)
    for pos, zhi in all_zhi.items():
        if zhi == tx:
            found.append({"name": "天喜", "position": pos, "zhi": zhi, "meaning": SHEN_SHA_MEANING["天喜"]})
            break

    # 去重
    seen = set()
    unique = []
    for s in found:
        key = (s["name"], s["zhi"])
        if key not in seen:
            seen.add(key)
            unique.append(s)

    return unique


def find_he_chong(bazi: Dict) -> Dict:
    """查找合冲刑害"""
    positions = ["年", "月", "日", "时"]
    zhis = [bazi[col][1] for col in ["year", "month", "day", "hour"]]

    he = []
    chong = []
    hai = []
    xing = []
    san_he_found = []
    san_hui_found = []

    # 两两组合查
    for i in range(4):
        for j in range(i + 1, 4):
            a, b = zhis[i], zhis[j]
            label = f"{positions[i]}支{a}-{positions[j]}支{b}"

            # 六合
            if (a, b) in LIU_HE:
                he.append({"pair": label, "type": f"六合化{LIU_HE[(a, b)]}", "desc": "和谐相合"})
            elif (b, a) in LIU_HE:
                he.append({"pair": label, "type": f"六合化{LIU_HE[(b, a)]}", "desc": "和谐相合"})

            # 六冲
            if (a, b) in LIU_CHONG or (b, a) in LIU_CHONG:
                chong.append({"pair": label, "desc": "相冲，主变动、矛盾、损伤"})

            # 六害
            if (a, b) in LIU_HAI or (b, a) in LIU_HAI:
                hai.append({"pair": label, "desc": "相害，主小人、暗损"})

            # 子卯刑
            if {a, b} == {"子", "卯"}:
                xing.append({"pair": label, "type": "子卯刑(无礼)", "desc": "主无礼、家庭不和"})

    # 三合
    for combo, name in SAN_HE:
        if all(z in zhis for z in combo):
            san_he_found.append({"combo": "+".join(combo), "name": f"三合{name}", "desc": "三合成局，能量极强"})

    # 三会
    for combo, name in SAN_HUI:
        if all(z in zhis for z in combo):
            san_hui_found.append({"combo": "+".join(combo), "name": f"三会{name}", "desc": "三会方局，五行汇聚"})

    # 三刑
    for combo, name in SAN_XING_GROUPS:
        if all(z in zhis for z in combo):
            xing.append({"pair": "+".join(combo), "type": f"三刑·{name}", "desc": "全见三刑，主刑伤"})

    # 自刑
    for z in ZI_XING:
        cnt = zhis.count(z)
        if cnt >= 2:
            xing.append({"pair": f"{z}{z}", "type": f"自刑({z}{z})", "desc": "重见自刑，主自伤"})

    return {
        "he": he,
        "chong": chong,
        "hai": hai,
        "xing": xing,
        "san_he": san_he_found,
        "san_hui": san_hui_found,
    }


def get_shi_shen(day_gan: str, target_gan: str) -> str:
    """根据日主天干，求其他天干的十神"""
    if day_gan == target_gan: return "比肩"

    day_wx = GAN_WUXING[day_gan]
    target_wx = GAN_WUXING[target_gan]
    day_yy = GAN_YIN_YANG[day_gan]
    target_yy = GAN_YIN_YANG[target_gan]
    same_yy = (day_yy == target_yy)

    # 同我者：比肩(同阴阳)/劫财(异阴阳)
    if day_wx == target_wx:
        return "比肩" if same_yy else "劫财"

    # 我生者：食神(同)/伤官(异)
    if WUXING_SHENG[day_wx] == target_wx:
        return "食神" if same_yy else "伤官"

    # 我克者：偏财(同)/正财(异)
    if WUXING_KE[day_wx] == target_wx:
        return "偏财" if same_yy else "正财"

    # 克我者：七杀(同)/正官(异)
    if WUXING_KE[target_wx] == day_wx:
        return "七杀" if same_yy else "正官"

    # 生我者：偏印(同)/正印(异)
    if WUXING_SHENG[target_wx] == day_wx:
        return "偏印" if same_yy else "正印"

    return "?"


# 十神含义
SHI_SHEN_MEANING = {
    "比肩": "兄弟朋友、同事、合作伙伴。主竞争、独立、自我",
    "劫财": "竞争者、对手。主破财、争夺，但也可助身",
    "食神": "晚辈、才华、口福。主温和、艺术、悠然",
    "伤官": "才华、表现欲。主聪明叛逆、特立独行",
    "正财": "妻子、稳定收入、固定资产。主务实、节俭",
    "偏财": "父亲、横财、偏门财。主豪爽、慷慨、机遇",
    "正官": "丈夫(女命)、领导、正职。主守规矩、责任",
    "七杀": "竞争、压力、武职。主魄力、果断、严厉",
    "正印": "母亲、文凭、贵人。主仁慈、学识、福气",
    "偏印": "继母、副业、偏门技术。主孤独、敏锐、冷静",
}

# 十二长生（衡量天干在地支的能量）
CHANG_SHENG_TABLE = {
    "甲": {"亥": "长生", "子": "沐浴", "丑": "冠带", "寅": "临官", "卯": "帝旺", "辰": "衰", "巳": "病", "午": "死", "未": "墓", "申": "绝", "酉": "胎", "戌": "养"},
    "乙": {"午": "长生", "巳": "沐浴", "辰": "冠带", "卯": "临官", "寅": "帝旺", "丑": "衰", "子": "病", "亥": "死", "戌": "墓", "酉": "绝", "申": "胎", "未": "养"},
    "丙": {"寅": "长生", "卯": "沐浴", "辰": "冠带", "巳": "临官", "午": "帝旺", "未": "衰", "申": "病", "酉": "死", "戌": "墓", "亥": "绝", "子": "胎", "丑": "养"},
    "丁": {"酉": "长生", "申": "沐浴", "未": "冠带", "午": "临官", "巳": "帝旺", "辰": "衰", "卯": "病", "寅": "死", "丑": "墓", "子": "绝", "亥": "胎", "戌": "养"},
    "戊": {"寅": "长生", "卯": "沐浴", "辰": "冠带", "巳": "临官", "午": "帝旺", "未": "衰", "申": "病", "酉": "死", "戌": "墓", "亥": "绝", "子": "胎", "丑": "养"},
    "己": {"酉": "长生", "申": "沐浴", "未": "冠带", "午": "临官", "巳": "帝旺", "辰": "衰", "卯": "病", "寅": "死", "丑": "墓", "子": "绝", "亥": "胎", "戌": "养"},
    "庚": {"巳": "长生", "午": "沐浴", "未": "冠带", "申": "临官", "酉": "帝旺", "戌": "衰", "亥": "病", "子": "死", "丑": "墓", "寅": "绝", "卯": "胎", "辰": "养"},
    "辛": {"子": "长生", "亥": "沐浴", "戌": "冠带", "酉": "临官", "申": "帝旺", "未": "衰", "午": "病", "巳": "死", "辰": "墓", "卯": "绝", "寅": "胎", "丑": "养"},
    "壬": {"申": "长生", "酉": "沐浴", "戌": "冠带", "亥": "临官", "子": "帝旺", "丑": "衰", "寅": "病", "卯": "死", "辰": "墓", "巳": "绝", "午": "胎", "未": "养"},
    "癸": {"卯": "长生", "寅": "沐浴", "丑": "冠带", "子": "临官", "亥": "帝旺", "戌": "衰", "酉": "病", "申": "死", "未": "墓", "午": "绝", "巳": "胎", "辰": "养"},
}


def get_bazi(birth: datetime.datetime) -> Dict:
    """从生辰获取八字"""
    lunar = cnlunar.Lunar(birth, godType="8char")
    year8 = lunar.get_year8Char()
    month8 = lunar.get_month8Char()
    day8 = lunar.get_day8Char()
    hour8 = lunar.get_twohour8Char()

    return {
        "year": (year8[0], year8[1]),
        "month": (month8[0], month8[1]),
        "day": (day8[0], day8[1]),
        "hour": (hour8[0], hour8[1]),
        "lunar_str": f"{lunar.lunarYearCn}{lunar.lunarMonthCn}{lunar.lunarDayCn}",
    }


def count_wuxing(bazi: Dict) -> Dict[str, int]:
    """统计五行数量（含天干+地支主气）"""
    counts = {"金": 0, "木": 0, "水": 0, "火": 0, "土": 0}
    for col in ["year", "month", "day", "hour"]:
        gan, zhi = bazi[col]
        counts[GAN_WUXING[gan]] += 1
        # 地支只取主气
        main_gan = ZHI_CANG_GAN[zhi][0]
        counts[GAN_WUXING[main_gan]] += 1
    return counts


def analyze_strength(bazi: Dict) -> Dict:
    """分析日主强弱（简化版）"""
    day_gan = bazi["day"][0]
    day_wx = GAN_WUXING[day_gan]

    # 计分：同我(比劫)+生我(印)算"扶"，我生(食伤)+我克(财)+克我(官杀)算"耗"
    score = 0
    weight_map = {
        "year_gan": 1, "year_zhi": 1.5,
        "month_gan": 1.5, "month_zhi": 3,  # 月令最重
        "day_gan": 0, "day_zhi": 1.5,
        "hour_gan": 1, "hour_zhi": 1.5,
    }

    detail = []
    for col_name, col_data in [("year", bazi["year"]), ("month", bazi["month"]), ("day", bazi["day"]), ("hour", bazi["hour"])]:
        gan, zhi = col_data
        # 天干
        if col_name != "day":  # 日主自己不计
            gan_wx = GAN_WUXING[gan]
            w = weight_map[f"{col_name}_gan"]
            if gan_wx == day_wx or WUXING_SHENG[gan_wx] == day_wx:
                score += w
                detail.append(f"{col_name}干{gan}({gan_wx})助身 +{w}")
            else:
                score -= w
                detail.append(f"{col_name}干{gan}({gan_wx})耗身 -{w}")

        # 地支主气
        zhi_main = ZHI_CANG_GAN[zhi][0]
        zhi_wx = GAN_WUXING[zhi_main]
        w = weight_map[f"{col_name}_zhi"]
        if zhi_wx == day_wx or WUXING_SHENG[zhi_wx] == day_wx:
            score += w
            detail.append(f"{col_name}支{zhi}({zhi_wx})助身 +{w}")
        else:
            score -= w
            detail.append(f"{col_name}支{zhi}({zhi_wx})耗身 -{w}")

    if score >= 4:
        strength = "身强"
        advice = "宜泄、克、耗：取食伤、财、官杀为用神"
    elif score >= 1:
        strength = "中和偏强"
        advice = "宜走食伤、财官运"
    elif score >= -1:
        strength = "中和"
        advice = "格局平衡，看格局取用"
    elif score >= -4:
        strength = "中和偏弱"
        advice = "宜走比劫、印星运扶身"
    else:
        strength = "身弱"
        advice = "宜扶、生：取比劫、印星为用神"

    return {
        "score": round(score, 1),
        "strength": strength,
        "advice": advice,
        "detail": detail,
    }


def get_da_yun(bazi: Dict, birth: datetime.datetime, gender: str, qi_yun_info: Optional[Dict] = None) -> List[Dict]:
    """大运计算，使用精算起运岁数（如提供）
    阳男阴女顺排，阴男阳女逆排，从月柱开始
    """
    year_gan = bazi["year"][0]
    month_gan, month_zhi = bazi["month"]

    if qi_yun_info:
        direction = qi_yun_info["direction"]
        start_age = qi_yun_info["start_age"]
    else:
        year_yy = GAN_YIN_YANG[year_gan]
        if (gender == "男" and year_yy == "阳") or (gender == "女" and year_yy == "阴"):
            direction = "顺"
        else:
            direction = "逆"
        start_age = 8 if gender == "男" else 7

    # 从月柱开始
    gan_idx = TIANGAN.index(month_gan)
    zhi_idx = DIZHI.index(month_zhi)

    da_yun_list = []
    for i in range(8):  # 排8步大运（80年）
        if direction == "顺":
            gan_idx = (gan_idx + 1) % 10
            zhi_idx = (zhi_idx + 1) % 12
        else:
            gan_idx = (gan_idx - 1) % 10
            zhi_idx = (zhi_idx - 1) % 12

        age_start = start_age + i * 10
        year_start = birth.year + age_start

        gan = TIANGAN[gan_idx]
        zhi = DIZHI[zhi_idx]
        ganzhi = gan + zhi

        da_yun_list.append({
            "ganzhi": ganzhi,
            "gan": gan,
            "zhi": zhi,
            "wuxing": GAN_WUXING[gan] + "/" + ZHI_WUXING[zhi],
            "shi_shen": get_shi_shen(bazi["day"][0], gan),
            "age_start": age_start,
            "age_end": age_start + 9,
            "year_start": year_start,
            "year_end": year_start + 9,
            "chang_sheng": CHANG_SHENG_TABLE.get(bazi["day"][0], {}).get(zhi, "?"),
            "na_yin": get_na_yin(ganzhi),
        })

    return da_yun_list


def get_liu_nian(bazi: Dict, year: int) -> Dict:
    """流年八字"""
    # 1984甲子，每60年一轮
    base = 1984
    diff = (year - base) % 60
    if diff < 0: diff += 60
    gan = TIANGAN[diff % 10]
    zhi = DIZHI[diff % 12]

    return {
        "year": year,
        "ganzhi": gan + zhi,
        "gan": gan,
        "zhi": zhi,
        "wuxing": GAN_WUXING[gan] + "/" + ZHI_WUXING[zhi],
        "shi_shen": get_shi_shen(bazi["day"][0], gan),
        "chang_sheng": CHANG_SHENG_TABLE.get(bazi["day"][0], {}).get(zhi, "?"),
    }


def get_yun_shi_text(shi_shen: str, chang_sheng: str) -> str:
    """根据十神和长生给出运势文字"""
    base_meaning = SHI_SHEN_MEANING.get(shi_shen, "")

    cs_meaning = {
        "长生": "事业起步，新开始，吉",
        "沐浴": "变动起伏，慎防败局",
        "冠带": "事业上升，顺遂",
        "临官": "鼎盛之时，大吉",
        "帝旺": "巅峰之时，但盛极而衰",
        "衰": "运势下滑，宜守",
        "病": "事业受阻，注意健康",
        "死": "运势低迷，宜静",
        "墓": "收藏沉淀，宜守不宜攻",
        "绝": "极度低迷，韬光养晦",
        "胎": "孕育新机，蓄势",
        "养": "蓄积能量，待发",
    }

    return f"{base_meaning}；当前处于「{chang_sheng}」位 — {cs_meaning.get(chang_sheng, '')}"


def full_bazi_chart(birth: datetime.datetime, gender: str = "男") -> Dict:
    """完整八字排盘"""
    bazi = get_bazi(birth)
    day_gan = bazi["day"][0]
    day_zhi = bazi["day"][1]
    day_ganzhi = day_gan + day_zhi

    # 旬空（基于日柱）
    kong_wang = get_xun_kong(day_ganzhi)

    # 四柱十神 + 纳音 + 旬空标记
    columns = []
    for col_name, col_label in [("year", "年柱"), ("month", "月柱"), ("day", "日柱"), ("hour", "时柱")]:
        gan, zhi = bazi[col_name]
        ganzhi = gan + zhi
        cang_gan = ZHI_CANG_GAN[zhi]
        columns.append({
            "label": col_label,
            "gan": gan,
            "zhi": zhi,
            "ganzhi": ganzhi,
            "gan_wuxing": GAN_WUXING[gan],
            "zhi_wuxing": ZHI_WUXING[zhi],
            "gan_yy": GAN_YIN_YANG[gan],
            "zhi_yy": ZHI_YIN_YANG[zhi],
            "shi_shen_gan": "日主" if col_name == "day" else get_shi_shen(day_gan, gan),
            "cang_gan": [{"gan": g, "shi_shen": get_shi_shen(day_gan, g), "wuxing": GAN_WUXING[g]} for g in cang_gan],
            "chang_sheng": CHANG_SHENG_TABLE.get(day_gan, {}).get(zhi, "?"),
            "na_yin": get_na_yin(ganzhi),
            "is_kong": zhi in kong_wang,
        })

    # 五行统计
    wx_counts = count_wuxing(bazi)
    total = sum(wx_counts.values())
    wx_pct = {k: round(v / total * 100, 1) for k, v in wx_counts.items()}

    # 缺什么
    missing = [k for k, v in wx_counts.items() if v == 0]
    weakest = min(wx_counts, key=lambda k: wx_counts[k])
    strongest = max(wx_counts, key=lambda k: wx_counts[k])

    # 强弱
    strength_info = analyze_strength(bazi)

    # 喜用神
    xi_yong = get_xi_yong(strength_info.get("score", 0), GAN_WUXING[day_gan])

    # 胎元、命宫
    month_gan, month_zhi = bazi["month"]
    hour_gan, hour_zhi = bazi["hour"]
    tai_yuan = get_tai_yuan(month_gan, month_zhi)
    ming_gong_zhi = get_ming_gong(month_zhi, hour_zhi)

    # 节气精算起运
    qi_yun_info = get_qi_yun_age(birth, gender, bazi["year"][0])

    # 大运（用精算起运）
    da_yun = get_da_yun(bazi, birth, gender, qi_yun_info)

    # 当前大运（按起运岁数算）
    age = datetime.datetime.now().year - birth.year
    current_da_yun = None
    for dy in da_yun:
        if dy["age_start"] <= age <= dy["age_end"]:
            current_da_yun = dy
            break

    # 流年（最近5年）
    current_year = datetime.datetime.now().year
    liu_nian_list = [get_liu_nian(bazi, y) for y in range(current_year, current_year + 5)]

    # 当年运势
    current_liu_nian = liu_nian_list[0]
    current_yun_shi = get_yun_shi_text(current_liu_nian["shi_shen"], current_liu_nian["chang_sheng"])

    # 神煞
    shen_sha = find_shen_sha(bazi)

    # 合冲刑害
    he_chong = find_he_chong(bazi)

    return {
        "birth": birth.isoformat(),
        "gender": gender,
        "lunar_str": bazi["lunar_str"],
        "columns": columns,
        "day_gan": day_gan,
        "day_wuxing": GAN_WUXING[day_gan],
        "wuxing_counts": wx_counts,
        "wuxing_percent": wx_pct,
        "wuxing_color": WUXING_COLOR,
        "missing": missing,
        "weakest": weakest,
        "strongest": strongest,
        "strength": strength_info,
        "xi_yong": xi_yong,
        "tai_yuan": {"ganzhi": tai_yuan, "na_yin": get_na_yin(tai_yuan)},
        "ming_gong": ming_gong_zhi,
        "kong_wang": list(kong_wang),
        "qi_yun": qi_yun_info,
        "da_yun": da_yun,
        "current_age": age,
        "current_da_yun": current_da_yun,
        "liu_nian": liu_nian_list,
        "current_liu_nian": current_liu_nian,
        "current_yun_shi": current_yun_shi,
        "shen_sha": shen_sha,
        "he_chong": he_chong,
    }
