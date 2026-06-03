#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
占卜核心逻辑：六爻 + 小六壬
- 农历自动转换 (cnlunar)
- 六爻：世应、六亲、纳甲、地支
- Obsidian 导出
"""

import random
import datetime
import os
import json
from typing import List, Dict, Tuple, Optional

import cnlunar


# ==================== 八卦 ====================
BAGUA = {
    "111": ("乾", "天", "乾", "金"),
    "110": ("兑", "泽", "兑", "金"),
    "101": ("离", "火", "离", "火"),
    "100": ("震", "雷", "震", "木"),
    "011": ("巽", "风", "巽", "木"),
    "010": ("坎", "水", "坎", "水"),
    "001": ("艮", "山", "艮", "土"),
    "000": ("坤", "地", "坤", "土"),
}

# 八宫卦序，决定卦的归宫（用于六亲分析）
# 每宫八卦：本宫卦、一世、二世、三世、四世、五世、游魂、归魂
# 索引对应世爻位置：0(本宫=六世)、1、2、3、4、5、6(游魂=四世)、7(归魂=三世)
BAGONG = {
    "乾": ["111111", "011111", "001111", "000111", "000011", "000001", "000101", "111101"],
    "兑": ["110110", "010110", "000110", "001110", "001010", "001000", "001100", "110100"],
    "离": ["101101", "001101", "011101", "010101", "010001", "010011", "010111", "101111"],
    "震": ["100100", "000100", "010100", "011100", "011000", "011010", "011110", "100110"],
    "巽": ["011011", "111011", "101011", "100011", "100111", "100101", "100001", "011001"],
    "坎": ["010010", "110010", "100010", "101010", "101110", "101100", "101000", "010000"],
    "艮": ["001001", "101001", "111001", "110001", "110101", "110111", "110011", "001011"],
    "坤": ["000000", "100000", "110000", "111000", "111100", "111110", "111010", "000010"],
}

# 每宫五行
GONG_WUXING = {"乾": "金", "兑": "金", "离": "火", "震": "木", "巽": "木", "坎": "水", "艮": "土", "坤": "土"}

# 世爻位置索引（0=初爻，5=上爻）
SHI_YAO_POS = {0: 5, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 3, 7: 2}

# 纳甲：每宫每爻配地支（自下而上）
NAJIA_DIZHI = {
    "乾": ["子", "寅", "辰", "午", "申", "戌"],   # 内卦乾(子寅辰)，外卦乾(午申戌)
    "坤": ["未", "巳", "卯", "丑", "亥", "酉"],   # 坤
    "震": ["子", "寅", "辰", "午", "申", "戌"],   # 震 同乾下
    "巽": ["丑", "亥", "酉", "未", "巳", "卯"],
    "坎": ["寅", "辰", "午", "申", "戌", "子"],
    "离": ["卯", "丑", "亥", "酉", "未", "巳"],
    "艮": ["辰", "午", "申", "戌", "子", "寅"],
    "兑": ["巳", "卯", "丑", "亥", "酉", "未"],
}

# 地支五行
DIZHI_WUXING = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
    "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水",
}

# 六亲生克：以本宫五行为"我"
# 同我者兄弟，生我者父母，我生者子孙，克我者官鬼，我克者妻财
def get_liuqin(gong_wuxing: str, yao_wuxing: str) -> str:
    sheng = {"金": "水", "水": "木", "木": "火", "火": "土", "土": "金"}
    ke = {"金": "木", "木": "土", "土": "水", "水": "火", "火": "金"}
    if yao_wuxing == gong_wuxing: return "兄弟"
    if sheng[yao_wuxing] == gong_wuxing: return "父母"
    if sheng[gong_wuxing] == yao_wuxing: return "子孙"
    if ke[yao_wuxing] == gong_wuxing: return "官鬼"
    if ke[gong_wuxing] == yao_wuxing: return "妻财"
    return "?"


# ==================== 六十四卦 ====================
GUA_64 = {
    "111111": ("乾为天", "元亨利贞", "刚健中正，自强不息。大吉之象。"),
    "110111": ("天泽履", "履虎尾", "如履薄冰，谨慎则吉。"),
    "101111": ("天火同人", "志同道合", "团结合作，吉。"),
    "100111": ("天雷无妄", "无妄不正", "顺其自然，不可妄动。"),
    "011111": ("天风姤", "邂逅之象", "意外相遇，慎防小人。"),
    "010111": ("天水讼", "争讼之象", "纠纷争执，宜和解，不宜诉讼。"),
    "001111": ("天山遁", "遁世退避", "退避保身，亨通。"),
    "000111": ("天地否", "否塞不通", "闭塞不通，凶。"),
    "111110": ("泽天夬", "决断之时", "果断行事，刚柔并济。"),
    "110110": ("兑为泽", "悦泽之象", "和悦顺利，吉。"),
    "101110": ("泽火革", "变革之道", "顺时而变，吉。"),
    "100110": ("泽雷随", "随顺时势", "顺势而为，吉。"),
    "011110": ("泽风大过", "栋桡之象", "非常之时，宜有非常之举。"),
    "010110": ("泽水困", "困境守贞", "凶。困顿之中，守正待时。"),
    "001110": ("泽山咸", "感应交融", "两情相悦，吉。"),
    "000110": ("泽地萃", "聚集兴旺", "群贤毕至，吉。"),
    "111101": ("火天大有", "富有大业", "丰盛富足，大吉。"),
    "110101": ("火泽睽", "意见相左", "分歧不合，小心。"),
    "101101": ("离为火", "光明附丽", "光明柔顺，吉。"),
    "100101": ("火雷噬嗑", "破除障碍", "果断决之，吉。"),
    "011101": ("火风鼎", "鼎新立业", "革故鼎新，大吉。"),
    "010101": ("火水未济", "未成之事", "渐成之象，宜耐心。"),
    "001101": ("火山旅", "漂泊在外", "羁旅他乡，小亨。"),
    "000101": ("火地晋", "进取顺利", "渐进向上，吉。"),
    "111100": ("雷天大壮", "强壮之时", "刚强壮盛，宜守正。"),
    "110100": ("雷泽归妹", "勉强从事", "凶。不当之合，慎之。"),
    "101100": ("雷火丰", "丰盛之极", "盛极而衰，需警觉。"),
    "100100": ("震为雷", "震动惊恐", "雷霆万钧，警惕则吉。"),
    "011100": ("雷风恒", "恒久之道", "持之以恒，吉。"),
    "010100": ("雷水解", "解困释难", "困境得解，吉。"),
    "001100": ("雷山小过", "小有过越", "矫枉过正，可。"),
    "000100": ("雷地豫", "和悦欢乐", "顺时而动，宜行动。"),
    "111011": ("风天小畜", "密云不雨", "小有积蓄，待时而动。"),
    "110011": ("风泽中孚", "诚信之道", "至诚感人，吉。"),
    "101011": ("风火家人", "家和万事兴", "齐家有道，吉。"),
    "100011": ("风雷益", "增益之道", "得天助益，大吉。"),
    "011011": ("巽为风", "顺从入伏", "谦顺有利，小吉。"),
    "010011": ("风水涣", "涣散重聚", "化险为夷，吉。"),
    "001011": ("风山渐", "循序渐进", "稳步上升，吉。"),
    "000011": ("风地观", "观察等待", "宜静观其变。"),
    "111010": ("水天需", "需者须也", "等待时机，守正以待，吉。"),
    "110010": ("水泽节", "节制有度", "适度而行，吉。"),
    "101010": ("水火既济", "事已成", "已成之事，慎守为吉。"),
    "100010": ("水雷屯", "始生艰难", "万事开头难，须坚守正道。"),
    "011010": ("水风井", "井养不穷", "稳定持久，平。"),
    "010010": ("坎为水", "习坎重险", "重重险阻，须诚信坚守。"),
    "001010": ("水山蹇", "艰难险阻", "凶。前路艰难，宜守。"),
    "000010": ("水地比", "亲比团结", "亲和相处，吉。"),
    "111001": ("山天大畜", "大畜养德", "蓄积大业，大吉。"),
    "110001": ("山泽损", "损己利人", "舍小求大，吉。"),
    "101001": ("山火贲", "文饰之象", "外表光鲜，宜守正。"),
    "100001": ("山雷颐", "养正则吉", "养生养德，吉。"),
    "011001": ("山风蛊", "整顿革新", "积弊须除，需改革。"),
    "010001": ("山水蒙", "蒙以养正", "需启蒙学习，渐进有成。"),
    "001001": ("艮为山", "止于至善", "适可而止，吉。"),
    "000001": ("山地剥", "剥落衰败", "凶。事物剥落，宜守。"),
    "111000": ("地天泰", "天地交泰", "通达顺利，大吉之象。"),
    "110000": ("地泽临", "临下亲民", "逐步壮大，吉。"),
    "101000": ("地火明夷", "韬光养晦", "光明受伤，宜藏锋。"),
    "100000": ("地雷复", "否极泰来", "复归正道，吉。"),
    "011000": ("地风升", "升腾向上", "渐次高升，大吉。"),
    "010000": ("地水师", "师出有名", "众人之事，得贤将则吉。"),
    "001000": ("地山谦", "谦受益", "谦虚自守，处处吉。"),
    "000000": ("坤为地", "厚德载物", "柔顺中正，承载万物。利守不利攻。"),
}



# ==================== 小六壬 ====================
XIAO_LIU_REN = [
    {
        "name": "大安",
        "element": "木",
        "color": "[吉]",
        "level": "大吉",
        "judgment": "事事昌，求财在坤方。失物去不远，宅舍保安康。行人身未动，疾病主无妨。将军回田野，仔细更推详。",
        "summary": "万事顺遂，求财得，失物近，病无碍，行人未动。",
        "good_for": ["求财", "婚姻", "出行平安", "病情趋稳", "失物近寻"],
        "love": "感情和睦稳定，单身者近期有缘",
        "career": "职场稳定，宜守不宜攻，按部就班",
        "wealth": "财运平稳，正财有利",
        "health": "身体无大碍，注意保养",
    },
    {
        "name": "留连",
        "element": "水",
        "color": "",
        "level": "凶",
        "judgment": "事难成，求谋日未明。官事只宜缓，去者未回程。失物南方去，急寻方可寻。更须防口舌，人口且太平。",
        "summary": "事多拖延，谋事未明，宜耐心等待。",
        "good_for": ["延期", "等待", "暂缓决定"],
        "love": "感情有阻碍，需要时间，单身者缘分未到",
        "career": "工作进展缓慢，项目易拖延",
        "wealth": "求财不顺，回款慢",
        "health": "病情反复，需长期调理",
    },
    {
        "name": "速喜",
        "element": "火",
        "color": "[凶]",
        "level": "大吉",
        "judgment": "喜来临，求财向南行。失物申未午，逢人路上寻。官事有福德，病者无禁忌。田宅六畜吉，行人有信音。",
        "summary": "喜事临门，求财顺利，行人即至，失物速得。",
        "good_for": ["喜事", "求财", "升职", "好消息", "行人归"],
        "love": "感情火热进展快，单身者近期有桃花",
        "career": "职场喜讯，升迁加薪有望",
        "wealth": "横财速至，宜把握",
        "health": "病情转好，速愈",
    },
    {
        "name": "赤口",
        "element": "金",
        "color": "",
        "level": "凶",
        "judgment": "主口舌，是非须慎防。失物急去寻，行人有惊慌。鸡犬多作怪，病者出西方。更须防咒诅，恐怕染瘟殃。",
        "summary": "口舌是非，须防争吵和小人，做事易生波折。",
        "good_for": ["谨言慎行", "避免争执", "暂停决策"],
        "love": "感情多争吵，易冷战，单身者有烂桃花",
        "career": "同事关系紧张，注意言辞",
        "wealth": "财来财去，慎防破财",
        "health": "注意口腔、呼吸道，情绪波动",
    },
    {
        "name": "小吉",
        "element": "水",
        "color": "[平]",
        "level": "吉",
        "judgment": "最相当，路上好商量。阴人来报喜，失物在坤方。行人即便至，交易甚是强。凡事皆和合，病者叩穹苍。",
        "summary": "诸事和谐，交易顺利，与人合作有利。",
        "good_for": ["合作", "交易", "婚姻", "调解", "求人办事"],
        "love": "感情和睦，宜表白结合，单身者贵人介绍",
        "career": "合作顺利，谈判有利",
        "wealth": "偏财有利，合伙得财",
        "health": "病情轻微，调理可愈",
    },
    {
        "name": "空亡",
        "element": "土",
        "color": "",
        "level": "大凶",
        "judgment": "事不祥，阴人多乖张。求财无利益，行人有灾殃。失物寻不见，官事有刑伤。病人逢暗鬼，析祷保安康。",
        "summary": "诸事不顺，求财无利，宜静不宜动。",
        "good_for": ["静心反思", "暂停大事", "祈福消灾"],
        "love": "感情有变，恐有第三者或分手",
        "career": "项目易黄，求职受阻",
        "wealth": "破财之兆，慎防上当",
        "health": "需重视健康，及时就医",
    },
]


# ==================== 六爻起卦 ====================
def toss_coins() -> int:
    """三枚铜钱：阳3阴2，总和 6/7/8/9"""
    return sum(random.choice([2, 3]) for _ in range(3))


def get_yao_info(yv: int) -> Dict:
    """爻值 → 信息"""
    if yv == 6:
        return {"value": 6, "yin_yang": "阴", "is_old": True, "symbol": "▬▬ ╳ ▬▬", "desc": "老阴(变阳)"}
    if yv == 7:
        return {"value": 7, "yin_yang": "阳", "is_old": False, "symbol": "▬▬▬▬▬▬▬", "desc": "少阳"}
    if yv == 8:
        return {"value": 8, "yin_yang": "阴", "is_old": False, "symbol": "▬▬   ▬▬", "desc": "少阴"}
    if yv == 9:
        return {"value": 9, "yin_yang": "阳", "is_old": True, "symbol": "▬▬▬○▬▬▬", "desc": "老阳(变阴)"}
    return {"value": yv, "yin_yang": "?", "is_old": False, "symbol": "?", "desc": "?"}


def yao_to_bin(yv: int, changed: bool = False) -> str:
    """爻 → 二进制位（自下而上）。changed=True 时变爻反向。"""
    if yv == 7: return "1"
    if yv == 8: return "0"
    if yv == 9: return "0" if changed else "1"
    if yv == 6: return "1" if changed else "0"
    return "?"


def find_gong(gua_bin: str) -> Tuple[str, int]:
    """查找卦所属宫和世爻类别(0-7)"""
    for gong, gua_list in BAGONG.items():
        if gua_bin in gua_list:
            return gong, gua_list.index(gua_bin)
    return "?", -1


def get_gua_name(gua_bin: str) -> Tuple[str, str, str]:
    """获取卦名、卦辞、释义"""
    if gua_bin in GUA_64:
        return GUA_64[gua_bin]
    # 兜底：根据上下卦组合
    upper = gua_bin[3:]
    lower = gua_bin[:3]
    u = BAGUA.get(upper, ("?",))[0]
    l = BAGUA.get(lower, ("?",))[0]
    return (f"{u}{l}卦", "", "卦象未收录详细释义")


def liuyao_full(question: str = "") -> Dict:
    """六爻完整起卦：含世应、六亲、纳甲"""
    yao_values = [toss_coins() for _ in range(6)]

    # 本卦
    ben_bin = "".join(yao_to_bin(v) for v in yao_values)
    ben_name, ben_judg, ben_meaning = get_gua_name(ben_bin)

    # 归宫
    gong, gua_idx = find_gong(ben_bin)
    gong_wx = GONG_WUXING.get(gong, "?")
    shi_pos = SHI_YAO_POS.get(gua_idx, 5)
    ying_pos = (shi_pos + 3) % 6

    # 纳甲（地支）
    # 内卦(下三爻)用下卦地支前3，外卦(上三爻)用上卦地支后3
    upper_bin = ben_bin[3:]
    lower_bin = ben_bin[:3]
    upper_gong = BAGUA.get(upper_bin, ("?",))[0]
    lower_gong = BAGUA.get(lower_bin, ("?",))[0]

    dizhi_list = []
    if lower_gong in NAJIA_DIZHI:
        dizhi_list.extend(NAJIA_DIZHI[lower_gong][:3])  # 内卦初二三
    else:
        dizhi_list.extend(["?"] * 3)
    if upper_gong in NAJIA_DIZHI:
        dizhi_list.extend(NAJIA_DIZHI[upper_gong][3:])  # 外卦四五六
    else:
        dizhi_list.extend(["?"] * 3)

    # 六爻信息
    yao_details = []
    for i, yv in enumerate(yao_values):
        info = get_yao_info(yv)
        dz = dizhi_list[i]
        yao_wx = DIZHI_WUXING.get(dz, "?")
        liuqin = get_liuqin(gong_wx, yao_wx) if gong_wx != "?" and yao_wx != "?" else "?"
        is_shi = (i == shi_pos)
        is_ying = (i == ying_pos)
        marker = "世" if is_shi else ("应" if is_ying else "")
        yao_details.append({
            "pos": i + 1,
            "name": ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"][i],
            "symbol": info["symbol"],
            "yin_yang": info["yin_yang"],
            "is_changing": info["is_old"],
            "desc": info["desc"],
            "dizhi": dz,
            "wuxing": yao_wx,
            "liuqin": liuqin,
            "marker": marker,
        })

    # 变卦
    has_change = any(v in (6, 9) for v in yao_values)
    bian_info = None
    if has_change:
        bian_bin = "".join(yao_to_bin(v, changed=True) for v in yao_values)
        bn, bj, bm = get_gua_name(bian_bin)
        bian_gong, _ = find_gong(bian_bin)
        change_yaos = [i + 1 for i, v in enumerate(yao_values) if v in (6, 9)]
        bian_info = {
            "bin": bian_bin,
            "name": bn,
            "judgment": bj,
            "meaning": bm,
            "gong": bian_gong,
            "change_yaos": change_yaos,
        }

    # 卦类描述
    gua_class = ["六冲卦(本宫)", "一世卦", "二世卦", "三世卦", "四世卦", "五世卦", "游魂卦", "归魂卦"][gua_idx] if gua_idx >= 0 else "?"

    return {
        "question": question,
        "datetime": datetime.datetime.now().isoformat(),
        "yao_values": yao_values,
        "ben_gua": {
            "bin": ben_bin,
            "name": ben_name,
            "judgment": ben_judg,
            "meaning": ben_meaning,
            "gong": gong,
            "gong_wuxing": gong_wx,
            "gua_class": gua_class,
            "upper": BAGUA.get(upper_bin, ("?", "?", "?", "?")),
            "lower": BAGUA.get(lower_bin, ("?", "?", "?", "?")),
            "shi_pos": shi_pos + 1,
            "ying_pos": ying_pos + 1,
        },
        "yao_details": yao_details,
        "has_change": has_change,
        "bian_gua": bian_info,
    }


# ==================== 小六壬起卦 ====================
def hour_to_shichen(h: int) -> Tuple[int, str]:
    """小时转时辰索引和名称：子=0(23-1), 丑=1(1-3) ..."""
    names = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    if h == 23 or h == 0:
        idx = 0
    else:
        idx = (h + 1) // 2
    return idx, names[idx]


def xiao_liu_ren_full(question: str = "", use_lunar: bool = True) -> Dict:
    """小六壬：默认用农历起卦"""
    now = datetime.datetime.now()

    if use_lunar:
        try:
            lunar = cnlunar.Lunar(now, godType="8char")
            lunar_month = lunar.lunarMonth
            lunar_day = lunar.lunarDay
            lunar_str = f"农历 {lunar.lunarYearCn}{lunar.lunarMonthCn}{lunar.lunarDayCn}"
        except Exception:
            lunar_month = now.month
            lunar_day = now.day
            lunar_str = "(农历转换失败，用公历)"
    else:
        lunar_month = now.month
        lunar_day = now.day
        lunar_str = "(使用公历)"

    shichen_idx, shichen_name = hour_to_shichen(now.hour)

    # 起卦
    p1 = (lunar_month - 1) % 6
    p2 = (p1 + lunar_day - 1) % 6
    p3 = (p2 + shichen_idx) % 6

    result = XIAO_LIU_REN[p3].copy()

    return {
        "question": question,
        "datetime": now.isoformat(),
        "lunar_str": lunar_str,
        "lunar_month": lunar_month,
        "lunar_day": lunar_day,
        "shichen": shichen_name,
        "shichen_idx": shichen_idx,
        "process": [
            {"step": "月起大安", "desc": f"从「大安」起{lunar_month}月", "result": XIAO_LIU_REN[p1]["name"]},
            {"step": "日起月落", "desc": f"从「{XIAO_LIU_REN[p1]['name']}」起{lunar_day}日", "result": XIAO_LIU_REN[p2]["name"]},
            {"step": "时起日落", "desc": f"从「{XIAO_LIU_REN[p2]['name']}」起{shichen_name}时", "result": XIAO_LIU_REN[p3]["name"]},
        ],
        "result": result,
    }


# ==================== Obsidian 导出 ====================
def format_ziwei_markdown(r: Dict) -> str:
    basic = r.get("basic", {})
    palaces = r.get("palaces", [])
    lines = []
    lines.append(f"# 紫微斗数命盘 · {basic.get('solar_date','')} {basic.get('time','')}")
    lines.append("")
    lines.append(f"- 性别：{basic.get('gender','')}")
    lines.append(f"- 阳历：{basic.get('solar_date','')} {basic.get('time_range','')}")
    lines.append(f"- 农历：{basic.get('lunar_date','')}")
    lines.append(f"- 八字：{basic.get('chinese_date','')}")
    lines.append(f"- 星座：{basic.get('sign','')} | 生肖：{basic.get('zodiac','')}")
    lines.append(f"- 命主：{basic.get('soul_master','')} | 身主：{basic.get('body_master','')} | 五行局：{basic.get('five_elements','')}")
    lines.append(f"- 命宫地支：{basic.get('soul_branch','')} | 身宫地支：{basic.get('body_branch','')}")
    cur_age = r.get("current_age")
    cur_palace = r.get("current_decadal_palace")
    cur_range = r.get("current_decadal_range") or []
    if cur_age is not None and cur_palace:
        rng = f"{cur_range[0]}-{cur_range[1]}" if len(cur_range) == 2 else "?"
        lines.append(f"- 当前虚岁：{cur_age}，所行大限：**{cur_palace}宫** ({rng})")
    lines.append("")
    lines.append("## 十二宫位")
    lines.append("")
    for p in palaces:
        flags = []
        if p.get("is_body_palace"): flags.append("身宫")
        if p.get("is_original_palace"): flags.append("命宫")
        flag_str = f" · {' · '.join(flags)}" if flags else ""
        lines.append(f"### {p['name']}宫{flag_str}")
        lines.append(f"- 干支：{p.get('stem','')}{p.get('branch','')}")
        d = p.get("decadal") or {}
        rng = d.get("range") or []
        if len(rng) == 2:
            lines.append(f"- 大限：{rng[0]}-{rng[1]} 岁")
        if p.get("major_stars"):
            lines.append(f"- 主星：{', '.join(p['major_stars'])}")
        if p.get("minor_stars"):
            lines.append(f"- 辅星：{', '.join(p['minor_stars'])}")
        if p.get("adjective_stars"):
            lines.append(f"- 杂曜：{', '.join(p['adjective_stars'])}")
        lines.append("")
    lines.append("---")
    lines.append(f"_排盘时间：{r.get('datetime','')}_  ")
    lines.append("_工具：玄机阁 · 紫微斗数_")
    return "\n".join(lines)


def format_meihua_markdown(r: Dict) -> str:
    """梅花易数 markdown 模板"""
    bg = r["ben_gua"]
    bian = r["bian_gua"]
    hu = r["hu_gua"]
    cuo = r["cuo_gua"]
    zong = r["zong_gua"]
    ty = r["ti_yong"]
    calc = r["calc"]
    md = [
        "---",
        f"date: {r['datetime']}",
        f"type: 梅花易数",
        f"question: {r['question'] or '无'}",
        f"gua: {bg['name']}",
        f"tags: [占卜, 梅花易数, {bg['name']}]",
        "---",
        "",
        f"# 梅花易数 - {bg['name']} 之 {bian['name']}",
        "",
        f"**所问之事**：{r['question'] or '无'}  ",
        f"**占卜时间**：{r['datetime']}  ",
        f"**起卦方法**：{r['method']}  ",
        f"**动爻位**：第 {calc['dong_yao']} 爻",
        "",
        "## 五卦合参",
        "",
        f"| 卦类 | 卦名 | 上卦 | 下卦 | bin |",
        f"| --- | --- | --- | --- | --- |",
        f"| 本卦 | {bg['name']} | {bg['upper_gua']}{bg['upper_symbol']} | {bg['lower_gua']}{bg['lower_symbol']} | {bg['bin']} |",
        f"| 变卦 | {bian['name']} | {bian['upper_gua']}{bian['upper_symbol']} | {bian['lower_gua']}{bian['lower_symbol']} | {bian['bin']} |",
        f"| 互卦 | {hu['name']} | {hu['upper_gua']}{hu['upper_symbol']} | {hu['lower_gua']}{hu['lower_symbol']} | {hu['bin']} |",
        f"| 错卦 | {cuo['name']} | {cuo['upper_gua']}{cuo['upper_symbol']} | {cuo['lower_gua']}{cuo['lower_symbol']} | {cuo['bin']} |",
        f"| 综卦 | {zong['name']} | {zong['upper_gua']}{zong['upper_symbol']} | {zong['lower_gua']}{zong['lower_symbol']} | {zong['bin']} |",
        "",
        f"## 体用关系",
        "",
        f"- **体卦**：{ty['ti_position']} {ty['ti_gua']}（{ty['ti_wuxing']}） — 代表自己/我方",
        f"- **用卦**：{ty['yong_position']} {ty['yong_gua']}（{ty['yong_wuxing']}） — 代表对方/外事",
        f"- **关系**：{ty['relation']} —— **{ty['level']}**",
        "",
        "## 卦辞",
        "",
        f"- 本卦《{bg['name']}》：{bg['judgment']}。{bg['meaning']}",
        f"- 变卦《{bian['name']}》：{bian['judgment']}。{bian['meaning']}",
        f"- 互卦《{hu['name']}》：{hu['judgment']}。{hu['meaning']}",
        "",
        "## 解读要点",
        "",
        "梅花易数以**体用生克 + 五卦象意**综合判断：",
        "- 本卦看现状，变卦看结果，互卦看过程，错卦看反面，综卦看对方视角。",
        "- 体用关系是吉凶骨架，再以卦象、卦辞补血肉。",
        "",
    ]
    return "\n".join(md)


def format_qimen_markdown(r: Dict) -> str:
    """奇门遁甲 markdown 模板"""
    palaces = r['palaces']
    zhifu = r['zhifu']
    md = [
        "---",
        f"date: {r['datetime']}",
        f"type: 奇门遁甲",
        f"question: {r['question'] or '无'}",
        f"paiju: {r['paiju']}",
        f"jieqi: {r['jieqi']}",
        f"tags: [占卜, 奇门遁甲, {r['paiju']}]",
        "---",
        "",
        f"# 奇门遁甲 - {r['paiju']}",
        "",
        f"**所问之事**：{r['question'] or '无'}  ",
        f"**起局时间**：{r['datetime']}  ",
        f"**排盘方法**：{r['method']}  ",
        f"**干支**：{r['ganzhi']}  ",
        f"**节气**：{r['jieqi']}  ",
        f"**旬首**：{r['xunshou']}  日空 {r['xunkong']['日空']} / 时空 {r['xunkong']['时空']}",
        "",
        "## 值符值使",
        "",
        f"- **值符天干**：{'/'.join(zhifu['值符天干'])}",
        f"- **值符**：{zhifu['值符星']} 落 {zhifu['值符宫']}宫",
        f"- **值使**：{zhifu['值使门']} 落 {zhifu['值使宫']}宫",
        f"- **天乙**：{r['tianyi']}",
        f"- **马星**：天马 {r['mastar']['天马']} / 丁马 {r['mastar']['丁马']} / 驿马 {r['mastar']['驿马']}",
        "",
        "## 九宫盘",
        "",
        "| 宫 | 方位 | 天盘 | 地盘 | 八门 | 九星 | 八神 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for p in palaces:
        md.append(
            f"| {p['gong']} | {p['direction']} | {p['sky_gan']} | {p['earth_gan']} | "
            f"{p['gate']}（{p['gate_level']}） | {p['star']}（{p['star_level']}） | "
            f"{p['shen']}（{p['shen_level']}） |"
        )
    md.extend([
        "",
        "## 解读要点",
        "",
        "**奇门用神选用**（按所问之事）：",
        "- 求财：看用神临**生门**或乙木（财星），落宫旺相吉",
        "- 出行：看**驿马**所在之宫，开/休/生门吉，杜/景/惊/死/伤凶",
        "- 求人：看**值使门**所到之宫，及对方所属用神",
        "- 谋事：看**值符**与所问对应天干的关系",
        "- 紧急：看**天乙**所在之宫为最吉位",
        "",
        "**九星五行旺衰**：星临旺相之宫为旺，星与宫干相生相和则吉。",
        "",
        "**八门吉凶**：开休生为吉门，杜景为平门，惊死伤为凶门。",
        "",
    ])
    return "\n".join(md)


def format_huangli_markdown(r: Dict) -> str:
    """黄历 markdown 输出"""
    lunar = r.get("lunar", {})
    gz = r.get("ganzhi", {})
    sc_list = r.get("shichen", [])
    dirs = r.get("lucky_directions", {})
    term = r.get("solar_term", {})
    lvl = r.get("today_level", {})
    today_god = r.get("today_12_god", {})

    md = [
        f"# 黄历 · {r.get('date', '')}",
        "",
        "## 基本信息",
        f"- **公历**：{r.get('date', '')} {r.get('weekday', '')}",
        f"- **农历**：{lunar.get('year', '')} {lunar.get('month', '')}{lunar.get('day', '')} · {lunar.get('season', '')} · {lunar.get('phase_of_moon', '')}",
        f"- **干支**：{gz.get('year', '')}年 {gz.get('month', '')}月 {gz.get('day', '')}日 {gz.get('hour', '')}时",
        f"- **生肖**：{r.get('zodiac', '')} | **星座**：{r.get('star_zodiac', '')}",
    ]

    if term.get("today"):
        md.append(f"- **今日节气**：{term.get('today')}")
    else:
        md.append(f"- **节气**：距 {term.get('next', '')}（{term.get('next_date', '')}）还有 {term.get('days_to_next', '')} 天")

    md.extend([
        "",
        "## 今日总评",
        f"- **十二建除**：{r.get('today_12_officer', '')}日",
        f"- **十二神煞**：{today_god.get('name', '')}（{today_god.get('level', '')}）",
        f"- **廿八星宿**：{r.get('today_28_star', '')}",
        f"- **吉凶倾向**：{lvl.get('thing_level', '')}",
        "",
        "## 宜",
        "  ".join(r.get("good_things", [])) or "无",
        "",
        "## 忌",
        "  ".join(r.get("bad_things", [])) or "无",
        "",
        "## 十二时辰吉凶",
    ])

    for s in sc_list:
        mark = "[吉]吉" if s.get("level") == "吉" else ("[凶]凶" if s.get("level") == "凶" else "平")
        reason = f"（{s['reason']}）" if s.get('reason') else ""
        md.append(f"- {s.get('name', '')}时（{s.get('hours', '')}点）{s.get('gz', '')} {mark}{reason}")

    md.extend([
        "",
        "## 方位与冲煞",
    ])
    for k, v in dirs.items():
        md.append(f"- **{k}**：{v}")
    md.append(f"- **冲煞**：{r.get('zodiac_clash', '')}")
    md.append(f"- **三合**：{r.get('zodiac_win', '')}")
    md.append(f"- **破日**：{r.get('zodiac_lose', '')}")

    md.extend([
        "",
        "## 神煞",
        f"- **吉神**：{ '、'.join(r.get('good_gods', [])) or '无' }",
        f"- **凶神**：{ '、'.join(r.get('bad_gods', [])) or '无' }",
        "",
        "## 彭祖百忌 / 胎神 / 经络",
        f"- **彭祖百忌**：{r.get('pengzu_taboo', '无')}",
        f"- **胎神占位**：{r.get('fetal_god', '无')}",
        f"- **今日经络**：{r.get('meridians', '无')}",
        "",
        "---",
        f"*生成于 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
    ])

    return "\n".join(md)


def export_to_obsidian(record: Dict, kind: str) -> Optional[str]:
    """导出占卜记录到 Obsidian
    kind: 'liuyao' or 'xiaoliuren'
    """
    vault = os.path.expanduser("~/Documents/Obsidian Vault")
    if not os.path.isdir(vault):
        return None

    folder = os.path.join(vault, "占卜记录")
    os.makedirs(folder, exist_ok=True)

    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d-%H%M%S")

    if kind == "liuyao":
        gua = record["ben_gua"]["name"]
        question_short = (record["question"] or "无题")[:20]
        filename = f"{timestamp}-六爻-{question_short}.md"
        content = format_liuyao_markdown(record)
    elif kind == "ziwei":
        basic = record.get("basic", {})
        date_short = (basic.get("solar_date") or "无日期")[:10]
        gender_short = basic.get("gender", "")
        filename = f"{timestamp}-紫微-{date_short}-{gender_short}.md"
        content = format_ziwei_markdown(record)
    elif kind == "meihua":
        gua = record["ben_gua"]["name"]
        question_short = (record["question"] or "无题")[:20]
        filename = f"{timestamp}-梅花-{question_short}.md"
        content = format_meihua_markdown(record)
    elif kind == "qimen":
        question_short = (record["question"] or "无题")[:20]
        filename = f"{timestamp}-奇门-{question_short}.md"
        content = format_qimen_markdown(record)
    elif kind == "huangli":
        date_str = record.get("date", now.strftime("%Y-%m-%d"))
        filename = f"{timestamp}-黄历-{date_str}.md"
        content = format_huangli_markdown(record)
    elif kind == "dream":
        date_str = record.get("dream_date") or now.strftime("%Y-%m-%d")
        text_short = (record.get("dream_text") or "无题")[:20].replace("/", "-")
        filename = f"{timestamp}-解梦-{date_str}-{text_short}.md"
        content = format_dream_markdown(record)
    else:
        gua = record["result"]["name"]
        question_short = (record["question"] or "无题")[:20]
        filename = f"{timestamp}-小六壬-{question_short}.md"
        content = format_xiaoliuren_markdown(record)

    filepath = os.path.join(folder, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath


def format_liuyao_markdown(r: Dict) -> str:
    bg = r["ben_gua"]
    md = [
        "---",
        f"date: {r['datetime']}",
        f"type: 六爻",
        f"question: {r['question'] or '无'}",
        f"gua: {bg['name']}",
        f"tags: [占卜, 六爻, {bg['gong']}宫]",
        "---",
        "",
        f"# 六爻占卜 - {bg['name']}",
        "",
        f"**所问之事**：{r['question'] or '无'}  ",
        f"**占卜时间**：{r['datetime']}  ",
        "",
        "## 本卦",
        "",
        f"### 《{bg['name']}》（{bg['gong']}宫·{bg['gua_class']}）",
        "",
        f"- **卦辞**：{bg['judgment']}",
        f"- **释义**：{bg['meaning']}",
        f"- **上卦**：{bg['upper'][2]} {bg['upper'][0]}({bg['upper'][1]})",
        f"- **下卦**：{bg['lower'][2]} {bg['lower'][0]}({bg['lower'][1]})",
        f"- **本宫五行**：{bg['gong_wuxing']}",
        f"- **世爻**：第{bg['shi_pos']}爻，**应爻**：第{bg['ying_pos']}爻",
        "",
        "### 六爻详情（自上而下）",
        "",
        "| 爻位 | 符号 | 阴阳 | 地支 | 五行 | 六亲 | 世应 | 变 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for d in reversed(r["yao_details"]):
        md.append(
            f"| {d['name']} | `{d['symbol']}` | {d['yin_yang']} | {d['dizhi']} | {d['wuxing']} | {d['liuqin']} | {d['marker'] or '-'} | {'[选]动' if d['is_changing'] else '-'} |"
        )
    md.append("")

    if r["has_change"]:
        bi = r["bian_gua"]
        md.extend([
            "## 变卦",
            "",
            f"### 《{bi['name']}》（{bi['gong']}宫）",
            "",
            f"- **卦辞**：{bi['judgment']}",
            f"- **释义**：{bi['meaning']}",
            f"- **变爻**：第 {', '.join(map(str, bi['change_yaos']))} 爻",
            "",
            "**断卦原则**：本卦为现状，变卦为结果，变爻为关键转折。",
            "",
        ])
    else:
        md.extend(["## 无变爻", "", "事态稳定，按本卦判断。", ""])

    md.append("---")
    md.append(" 占卜仅供参考，关键还是自己的努力与判断。")
    return "\n".join(md)


def format_dream_markdown(r: Dict) -> str:
    """解梦记录的 Obsidian markdown 渲染。"""
    z = r.get("zhougong", {}) or {}
    p = r.get("psychology", {}) or {}
    suggestions = r.get("suggestions", []) or []
    text_short = (r.get("dream_text") or "")[:30]
    md = [
        "---",
        f"date: {r.get('dream_date', '')}",
        f"datetime: {r.get('datetime', '')}",
        f"type: 解梦",
        f"mood: {r.get('mood_on_wake', '')}",
        f"tags: [解梦, 梦境, 心理]",
        "---",
        "",
        f"#  解梦 - {text_short}{'…' if len(r.get('dream_text','')) > 30 else ''}",
        "",
        f"**梦境日期**：{r.get('dream_date', '')}  ",
        f"**记录时间**：{r.get('datetime', '')}  ",
    ]
    if r.get("mood_on_wake"):
        md.append(f"**醒来情绪**：{r['mood_on_wake']}  ")
    if r.get("context"):
        md.append(f"**近期处境**：{r['context']}  ")
    md.extend([
        "",
        "## 梦境原文",
        "",
        f"> {r.get('dream_text', '')}",
        "",
        "##  周公视角",
        "",
    ])
    symbols = z.get("symbols") or []
    if symbols:
        md.append(f"**关键象征**：{' / '.join(symbols)}")
        md.append("")
    md.append(z.get("interpretation", "（无解读）"))
    md.extend([
        "",
        "##  心理学视角",
        "",
    ])
    archetypes = p.get("archetypes") or []
    if archetypes:
        md.append(f"**原型/机制**：{' / '.join(archetypes)}")
        md.append("")
    md.append(p.get("interpretation", "（无解读）"))
    md.extend([
        "",
        "## 综合给你的话",
        "",
        f"> {r.get('summary', '')}",
        "",
    ])
    if suggestions:
        md.append("## 落地建议")
        md.append("")
        for s in suggestions:
            md.append(f"- {s}")
        md.append("")
    md.extend([
        "---",
        f"*模型：{r.get('model', '')}*",
        " 解梦仅供参考，不是命理预言。",
    ])
    return "\n".join(md)


def format_xiaoliuren_markdown(r: Dict) -> str:
    res = r["result"]
    md = [
        "---",
        f"date: {r['datetime']}",
        f"type: 小六壬",
        f"question: {r['question'] or '无'}",
        f"gua: {res['name']}",
        f"level: {res['level']}",
        f"tags: [占卜, 小六壬, {res['name']}]",
        "---",
        "",
        f"# 小六壬 - {res['color']} 《{res['name']}》",
        "",
        f"**所问之事**：{r['question'] or '无'}  ",
        f"**占卜时间**：{r['datetime']}  ",
        f"**{r['lunar_str']} {r['shichen']}时**",
        "",
        "## 起卦过程",
        "",
    ]
    for p in r["process"]:
        md.append(f"- **{p['step']}**：{p['desc']} → 落「{p['result']}」")
    md.extend([
        "",
        f"## 所得卦：《{res['name']}》（{res['element']}·{res['level']}）",
        "",
        f"### 卦辞",
        "",
        f"> {res['judgment']}",
        "",
        f"### 白话",
        "",
        res["summary"],
        "",
        "### 各事项分析",
        "",
        f"- **感情**：{res['love']}",
        f"- **事业**：{res['career']}",
        f"- **财运**：{res['wealth']}",
        f"- **健康**：{res['health']}",
        "",
        f"### 宜",
        "",
        " / ".join(res["good_for"]),
        "",
        "---",
        " 占卜仅供参考，三思而后行。",
    ])
    return "\n".join(md)


# ==================== CLI 入口 ====================
if __name__ == "__main__":
    import sys
    print("=" * 60)
    print("中国传统占卜（增强版）")
    print("=" * 60)
    print("1. 六爻 (含世应/六亲/纳甲)")
    print("2. 小六壬 (含农历)")
    print("3. 两个都来")
    print("0. 退出")

    try:
        choice = input("\n选择 (0-3): ").strip()
        question = input("所问之事 (可留空): ").strip()
    except (EOFError, KeyboardInterrupt):
        sys.exit(0)

    if choice in ("1", "3"):
        r = liuyao_full(question)
        print("\n" + format_liuyao_markdown(r))
        path = export_to_obsidian(r, "liuyao")
        if path: print(f"\n 已导出到 Obsidian: {path}")

    if choice in ("2", "3"):
        r = xiao_liu_ren_full(question)
        print("\n" + format_xiaoliuren_markdown(r))
        path = export_to_obsidian(r, "xiaoliuren")
        if path: print(f"\n 已导出到 Obsidian: {path}")
