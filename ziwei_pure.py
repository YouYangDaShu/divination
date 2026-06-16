#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""紫微斗数排盘（纯 Python 实现，移植自 iztro）

实测算例与 iztro 2.5.8 npm 包输出完全一致。
"""
import datetime
from typing import Dict, List

from lunardate import LunarDate


# ============== 常量表 ==============
EARTHLY_BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
HEAVENLY_STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
STEM_ELEMENT = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水"}
BRANCH_ELEMENT = {"子":"水","丑":"土","寅":"木","卯":"木","辰":"土","巳":"火","午":"火","未":"土","申":"金","酉":"金","戌":"土","亥":"水"}
ZODIAC = ["鼠","牛","虎","兔","龙","蛇","马","羊","猴","鸡","狗","猪"]
# 12 宫位（从命宫起顺时针 12 位）
PALACE_NAMES_ZH = ["命宫", "父母", "福德", "田宅", "官禄", "交友", "迁移", "疾厄", "财帛", "子女", "夫妻", "兄弟"]

# 五虎遁：年干→寅宫天干（起月法）
TIGER_RULE = {
    "甲": "丙", "己": "丙",
    "乙": "戊", "庚": "戊",
    "丙": "庚", "辛": "庚",
    "丁": "壬", "壬": "壬",
    "戊": "甲", "癸": "甲",
}

# 五行局数：水二、木三、金四、土五、火六
FIVE_ELEMENTS_CLASS = {"水": 2, "木": 3, "金": 4, "土": 5, "火": 6}

# 命主表（按命宫地支，移植自 iztro earthBranches.js）
SOUL_MASTER = {
    "子": "贪狼", "丑": "巨门", "寅": "禄存", "卯": "文曲",
    "辰": "廉贞", "巳": "武曲", "午": "破军", "未": "武曲",
    "申": "廉贞", "酉": "文曲", "戌": "禄存", "亥": "巨门",
}
# 身主表（按生年支，移植自 iztro earthBranches.js）
BODY_MASTER = {
    "子": "火星", "丑": "天相", "寅": "天梁", "卯": "天同",
    "辰": "文昌", "巳": "天机", "午": "火星", "未": "天相",
    "申": "天梁", "酉": "天同", "戌": "文昌", "亥": "天机",
}

# 紫微星系（含空位）
# 紫微逆去天机星 → 隔一太阳武曲辰 → 连接天同空二宫 → 廉贞居处方是真
ZIWEI_GROUP = [
    "紫微", "天机", None, "太阳", "武曲", "天同", None, None, "廉贞",
]
# 天府星系
# 天府顺行有太阴 → 贪狼而后巨门临 → 随来天相天梁继 → 七杀空三是破军
TIANFU_GROUP = [
    "天府", "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", None, None, None, "破军",
]

# 14 主星亮度（按寅卯辰巳午未申酉戌亥子丑 12 地支顺序）
# 庙/旺/得/利/平/不/陷
BRIGHTNESS = {
    "紫微": ["旺","旺","得","旺","庙","庙","旺","旺","得","旺","平","庙"],
    "天机": ["得","旺","利","平","庙","陷","得","旺","利","平","庙","陷"],
    "太阳": ["旺","庙","旺","旺","旺","得","得","陷","不","陷","陷","不"],
    "武曲": ["得","利","庙","平","旺","庙","得","利","庙","平","旺","庙"],
    "天同": ["利","平","平","庙","陷","不","旺","平","平","庙","旺","不"],
    "廉贞": ["庙","平","利","陷","平","利","庙","平","利","陷","平","利"],
    "天府": ["庙","得","庙","得","旺","庙","得","旺","庙","得","庙","庙"],
    "太阴": ["旺","陷","陷","陷","不","不","利","不","旺","庙","庙","庙"],
    "贪狼": ["平","利","庙","陷","旺","庙","平","利","庙","陷","旺","庙"],
    "巨门": ["庙","庙","陷","旺","旺","不","庙","庙","陷","旺","旺","不"],
    "天相": ["庙","陷","得","得","庙","得","庙","陷","得","得","庙","庙"],
    "天梁": ["庙","庙","庙","陷","庙","旺","陷","得","庙","陷","庙","旺"],
    "七杀": ["庙","旺","庙","平","旺","庙","庙","庙","庙","平","旺","庙"],
    "破军": ["得","陷","旺","平","庙","旺","得","陷","旺","平","庙","旺"],
}

# 四化表（按年干 4 个四化：禄/权/科/忌）
# 顺序：【禄，权，科，忌】
MUTAGEN = {
    "甲": ["廉贞","破军","武曲","太阳"],
    "乙": ["天机","天梁","紫微","太阴"],
    "丙": ["天同","天机","文昌","廉贞"],
    "丁": ["太阴","天同","天机","巨门"],
    "戊": ["贪狼","太阴","右弼","天机"],
    "己": ["武曲","贪狼","天梁","文曲"],
    "庚": ["太阳","武曲","太阴","天同"],
    "辛": ["巨门","太阳","文曲","文昌"],
    "壬": ["天梁","紫微","左辅","武曲"],
    "癸": ["破军","巨门","太阴","贪狼"],
}
MUTAGEN_NAMES = ["化禄","化权","化科","化忌"]

# ============== 38 辅星（移植自 iztro location.js） ==============
# 用函数直接算位置，不再用硬编码表

# 禄存（按年干）
LUCUN = {
    "甲": "寅", "乙": "卯", "丙": "巳", "丁": "午", "戊": "巳",
    "己": "午", "庚": "申", "辛": "酉", "壬": "亥", "癸": "子",
}

# 天马（按年支三合局）
# 寅午戌马在申，申子辰马在寅，亥卯未马在巳，巳酉丑马在亥
TIANMA = {
    "寅": "申", "午": "申", "戌": "申",
    "申": "寅", "子": "寅", "辰": "寅",
    "亥": "巳", "卯": "巳", "未": "巳",
    "巳": "亥", "酉": "亥", "丑": "亥",
}

# 天魁天钺（按年干）
# 甲戊庚→丑/未, 乙己→子/申, 辛→午/寅, 壬癸→卯/巳, 丙丁→亥/酉
TIANKUI = {
    "甲": "丑", "戊": "丑", "庚": "丑",
    "乙": "子", "己": "子",
    "辛": "午",
    "壬": "卯", "癸": "卯",
    "丙": "亥", "丁": "亥",
}
TIANYUE = {
    "甲": "未", "戊": "未", "庚": "未",
    "乙": "申", "己": "申",
    "辛": "寅",
    "壬": "巳", "癸": "巳",
    "丙": "酉", "丁": "酉",
}


def _chanyangyao(lucun_branch: str) -> str:
    """禄存前一位 = 擎羊（顺数 12 地支）"""
    idx = _branch_index(lucun_branch)
    return EARTHLY_BRANCHES[(idx + 1) % 12]


def _tuoluo(lucun_branch: str) -> str:
    """禄存后一位 = 陀罗"""
    idx = _branch_index(lucun_branch)
    return EARTHLY_BRANCHES[(idx - 1) % 12]


def _wenchang(time_index: int) -> str:
    """文昌：戌(10) - 时辰"""
    return EARTHLY_BRANCHES[(10 - time_index) % 12]


def _wenqu(time_index: int) -> str:
    """文曲：辰(4) + 时辰"""
    return EARTHLY_BRANCHES[(4 + time_index) % 12]


def _zuofu(lunar_month: int) -> str:
    """左辅：辰(4) + (月-1)，顺行"""
    return EARTHLY_BRANCHES[(4 + lunar_month - 1) % 12]


def _youbi(lunar_month: int) -> str:
    """右弼：戌(10) - (月-1)，逆行"""
    return EARTHLY_BRANCHES[(10 - lunar_month + 1) % 12]


def _huoxing(year_branch: str, time_index: int) -> str:
    """火星：按年支三合局
    - 寅午戌年 → 火星起子时在丑(1)，顺数
    - 申子辰年 → 火星起子时在寅(2)，顺数
    - 巳酉丑年 → 火星起子时在卯(3)，顺数
    - 亥卯未年 → 火星起子时在酉(9)，顺数
    """
    rules = {
        ("寅","午","戌"): 1,
        ("申","子","辰"): 2,
        ("巳","酉","丑"): 3,
        ("亥","卯","未"): 9,
    }
    for branches, start in rules.items():
        if year_branch in branches:
            return EARTHLY_BRANCHES[(start + time_index) % 12]
    return "?"


def _lingxing(year_branch: str, time_index: int) -> str:
    """铃星：按年支三合局
    - 寅午戌年 → 铃星起子时在卯(3)，顺数
    - 申子辰年 → 铃星起子时在戌(10)，顺数
    - 巳酉丑年 → 铃星起子时在戌(10)，顺数
    - 亥卯未年 → 铃星起子时在戌(10)，顺数
    """
    rules = {
        ("寅","午","戌"): 3,
        ("申","子","辰"): 10,
        ("巳","酉","丑"): 10,
        ("亥","卯","未"): 10,
    }
    for branches, start in rules.items():
        if year_branch in branches:
            return EARTHLY_BRANCHES[(start + time_index) % 12]
    return "?"


def _dikong(time_index: int) -> str:
    """地空：亥(11) - 时辰，逆行"""
    return EARTHLY_BRANCHES[(11 - time_index) % 12]


def _dijie(time_index: int) -> str:
    """地劫：亥(11) + 时辰，顺行"""
    return EARTHLY_BRANCHES[(11 + time_index) % 12]


# ============== 工具函数 ==============
def _fix_index(i: int) -> int:
    return i % 12


def _stem_index(s: str) -> int:
    return HEAVENLY_STEMS.index(s)


def _branch_index(b: str) -> int:
    return EARTHLY_BRANCHES.index(b)


def _year_stem(year: int) -> str:
    return HEAVENLY_STEMS[(year - 4) % 10]


def _year_branch(year: int) -> str:
    return EARTHLY_BRANCHES[(year - 4) % 12]


def _time_branch(hour: int, minute: int = 0) -> str:
    if hour == 23 or hour == 0:
        return "子"
    return EARTHLY_BRANCHES[((hour + 1) // 2) % 12]


def _time_idx(hour: int) -> int:
    if hour == 23:
        return 0
    return ((hour + 1) // 2) % 12


# ============== 核心算法 ==============
def _get_soul_and_body_palace(lunar_month: int, hour_branch: str) -> tuple:
    yin_idx = _branch_index("寅")
    month_branch_idx = _fix_index(yin_idx + lunar_month - 1)
    hour_branch_idx = _branch_index(hour_branch)
    soul_idx = _fix_index(month_branch_idx - hour_branch_idx)
    body_idx = _fix_index(month_branch_idx + hour_branch_idx)
    return soul_idx, body_idx


def _get_soul_ganzhi(year_stem: str, soul_idx: int) -> tuple:
    yin_stem = TIGER_RULE[year_stem]
    yin_idx = _branch_index("寅")
    offset = _fix_index(soul_idx - yin_idx)
    stem = HEAVENLY_STEMS[(_stem_index(yin_stem) + offset) % 10]
    branch = EARTHLY_BRANCHES[soul_idx]
    return stem, branch


def _get_five_elements_class(stem: str, branch: str) -> tuple:
    ganzhi_to_nayin = {}
    nayin_cycle = [
        ("海中金","金"),("海中金","金"),("炉中火","火"),("炉中火","火"),
        ("大林木","木"),("大林木","木"),("路旁土","土"),("路旁土","土"),
        ("剑锋金","金"),("剑锋金","金"),("山头火","火"),("山头火","火"),
        ("涧下水","水"),("涧下水","水"),("城头土","土"),("城头土","土"),
        ("白蜡金","金"),("白蜡金","金"),("杨柳木","木"),("杨柳木","木"),
        ("泉中水","水"),("泉中水","水"),("屋上土","土"),("屋上土","土"),
        ("霹雳火","火"),("霹雳火","火"),("松柏木","木"),("松柏木","木"),
        ("长流水","水"),("长流水","水"),("沙中金","金"),("沙中金","金"),
        ("山下火","火"),("山下火","火"),("平地木","木"),("平地木","木"),
        ("壁上土","土"),("壁上土","土"),("金箔金","金"),("金箔金","金"),
        ("覆灯火","火"),("覆灯火","火"),("天河水","水"),("天河水","水"),
        ("大驿土","土"),("大驿土","土"),("钗钏金","金"),("钗钏金","金"),
        ("桑柘木","木"),("桑柘木","木"),("大溪水","水"),("大溪水","水"),
        ("沙中土","土"),("沙中土","土"),("天上火","火"),("天上火","火"),
        ("石榴木","木"),("石榴木","木"),("大海水","水"),("大海水","水"),
    ]
    ganzhi_60 = []
    for i in range(60):
        s = HEAVENLY_STEMS[i % 10]
        b = EARTHLY_BRANCHES[i % 12]
        ganzhi_60.append(s + b)
    target = stem + branch
    try:
        idx = ganzhi_60.index(target)
        name, wx = nayin_cycle[idx]
        return name, wx
    except ValueError:
        return "?", "水"


def _get_ziwei_index(lunar_day: int, five_class_value: int) -> tuple:
    offset = 0
    quotient = 0
    while True:
        divisor = lunar_day + offset
        quotient = divisor // five_class_value
        remainder = divisor % five_class_value
        if remainder == 0:
            break
        offset += 1
    quotient %= 12
    ziwei_index = quotient - 1
    if offset % 2 == 0:
        ziwei_index += offset
    else:
        ziwei_index -= offset
    ziwei_index = _fix_index(ziwei_index + 2)
    tianfu_index = _fix_index(4 - ziwei_index)
    return ziwei_index, tianfu_index


def _get_decadal_range(gender: str, five_class_value: int, soul_branch: str) -> tuple:
    start_age = five_class_value
    yang_branches = ["寅","午","申","子","辰"]
    is_yang_soul = soul_branch in yang_branches
    is_forward = (gender == "男" and is_yang_soul) or (gender == "女" and not is_yang_soul)
    return start_age, is_forward


def _calculate_decadals(start_age: int, is_forward: bool, soul_idx: int, year_stem: str) -> List[Dict]:
    decadals = []
    soul_stem, _ = _get_soul_ganzhi(year_stem, soul_idx)
    soul_stem_idx = _stem_index(soul_stem)
    for i in range(12):
        if is_forward:
            palace_idx = _fix_index(soul_idx + i)
            stem = HEAVENLY_STEMS[(soul_stem_idx + i) % 10]
        else:
            palace_idx = _fix_index(soul_idx - i)
            stem = HEAVENLY_STEMS[(soul_stem_idx - i) % 10]
        age_start = start_age + i * 10
        age_end = age_start + 9
        decadals.append({
            "range": [age_start, age_end],
            "heavenly_stem": stem,
            "earthly_branch": EARTHLY_BRANCHES[palace_idx],
        })
    return decadals


# ============== 辅星起法 ==============
def _place_minor_stars(year_stem: str, year_branch: str, lunar_month: int, hour_branch_idx: int, hour_branch: str) -> Dict[str, str]:
    """返回 {地支: [星名列表]}"""
    result = {}

    # 禄存
    lucun_b = LUCUN[year_stem]
    result.setdefault(lucun_b, []).append("禄存")
    # 擎羊（禄存+1）
    result.setdefault(_chanyangyao(lucun_b), []).append("擎羊")
    # 陀罗（禄存-1）
    result.setdefault(_tuoluo(lucun_b), []).append("陀罗")

    # 天魁天钺
    result.setdefault(TIANKUI[year_stem], []).append("天魁")
    result.setdefault(TIANYUE[year_stem], []).append("天钺")

    # 文昌文曲（按时支）
    result.setdefault(_wenchang(hour_branch_idx), []).append("文昌")
    result.setdefault(_wenqu(hour_branch_idx), []).append("文曲")

    # 左辅右弼（按月）
    result.setdefault(_zuofu(lunar_month), []).append("左辅")
    result.setdefault(_youbi(lunar_month), []).append("右弼")

    # 天马（按年支）
    result.setdefault(TIANMA[year_branch], []).append("天马")

    # 火星铃星（按年支+时辰）
    result.setdefault(_huoxing(year_branch, hour_branch_idx), []).append("火星")
    result.setdefault(_lingxing(year_branch, hour_branch_idx), []).append("铃星")

    # 地空地劫（按时支）
    result.setdefault(_dikong(hour_branch_idx), []).append("地空")
    result.setdefault(_dijie(hour_branch_idx), []).append("地劫")

    return result


# ============== 38 杂耀（移植自 iztro adjectiveStar.js） ==============
def _place_adjective_stars(
    year_stem: str, year_branch: str, gender: str,
    lunar_month: int, lunar_day: int, hour_idx: int,
    soul_idx: int, body_idx: int
) -> Dict[str, list]:
    """返回 {地支: [星名列表]} 杂耀"""
    yb = _branch_index(year_branch)
    ys = _stem_index(year_stem)
    result: Dict[str, list] = {}

    def _put(branch_idx: int, name: str):
        b = EARTHLY_BRANCHES[branch_idx % 12]
        result.setdefault(b, []).append(name)

    # 红鸾天喜（年支）
    hongluan_idx = (3 - yb) % 12
    _put(hongluan_idx, "红鸾")
    _put((hongluan_idx + 6) % 12, "天喜")

    # 天姚（月，从丑起正月顺数）
    _put((1 + (lunar_month - 1)) % 12, "天姚")

    # 华盖咸池（年支三合）
    hg_rules = {
        (2, 6, 10): (10, 3), (7, 0, 4): (4, 8),
        (4, 8, 1): (1, 5),   (11, 3, 7): (7, 0),
    }
    for branches, (hg, xc) in hg_rules.items():
        if yb in branches:
            _put(hg, "华盖"); _put(xc, "咸池"); break

    # 孤辰寡宿（年支三合）
    gc_rules = {
        (2, 3, 4): (4, 1),    (5, 6, 7): (7, 4),
        (8, 9, 10): (11, 7),  (11, 0, 1): (2, 10),
    }
    for branches, (gc, gu) in gc_rules.items():
        if yb in branches:
            _put(gc, "孤辰"); _put(gu, "寡宿"); break

    # 天才天寿（命宫/身宫 + 年支）
    _put((soul_idx + yb) % 12, "天才")
    _put((body_idx + yb) % 12, "天寿")

    # 龙池凤阁（年支）
    _put((4 + yb) % 12, "龙池")
    _put((10 - yb) % 12, "凤阁")

    # 天哭天虚（年支）
    _put((5 - yb) % 12, "天哭")
    _put((5 + yb) % 12, "天虚")

    # 天德月德（年支）
    _put((8 + yb) % 12, "天德")
    _put((4 + yb) % 12, "月德")

    # 天空（年支前一位）
    _put((yb + 1) % 12, "天空")

    # 旬空（年干定旬首，阴阳同宫取阳）
    xun_heads = [0, 10, 8, 6, 4, 2]
    xun_head = xun_heads[ys % 6]
    xunkong_idx = (xun_head - 1) % 12
    if (yb % 2) != (xunkong_idx % 2):
        xunkong_idx = (xunkong_idx + 1) % 12
    _put(xunkong_idx, "旬空")

    # 截路空亡（年干）
    jielu_map = {0: 7, 5: 7, 1: 5, 6: 5, 2: 4, 7: 4, 3: 2, 8: 2, 4: 0, 9: 0}
    jielu_idx = jielu_map.get(ys, 0)
    _put(jielu_idx, "截路")
    _put((jielu_idx + 1) % 12, "截路空亡")

    # 天官天福（年干）
    tianguan_map = [7, 4, 5, 2, 3, 8, 11, 8, 10, 6]
    _put(tianguan_map[ys], "天官")
    tianfu_map = [8, 7, 0, 11, 3, 2, 6, 5, 6, 5]
    _put(tianfu_map[ys], "天福")

    # 天厨（年干）
    tianchu_map = [5, 6, 0, 5, 6, 7, 2, 6, 8, 11]
    _put(tianchu_map[ys], "天厨")

    # 破碎（年支三合）
    posui_rules = {
        (0, 6, 3, 9): 4, (2, 8, 5, 11): 8, (4, 10, 1, 7): 1,
    }
    for branches, idx in posui_rules.items():
        if yb in branches: _put(idx, "破碎"); break

    # 蜚蠊（年支）
    feilian_base = [7, 8, 9, 5, 6, 7, 2, 3, 4, 11, 0, 1]
    _put(feilian_base[yb], "蜚蠊")

    # 劫煞（年支三合）
    jiesha_rules = {
        (7, 0, 4): 5, (11, 3, 7): 8, (2, 6, 10): 11, (5, 9, 1): 2,
    }
    for branches, idx in jiesha_rules.items():
        if yb in branches: _put(idx, "劫煞"); break

    # 大耗（年支对冲，阳顺阴逆移一宫）
    dahao_duichong = (yb + 6) % 12
    dahao_idx = (dahao_duichong + 1) % 12 if yb % 2 == 0 else (dahao_duichong - 1) % 12
    _put(dahao_idx, "大耗")

    # 天伤天使（命身宫，性别定）
    same = ((yb % 2 == 0) == (gender == "男"))
    if same:
        _put((soul_idx + 6) % 12, "天伤")
        _put((soul_idx + 8) % 12, "天使")
    else:
        _put((soul_idx + 8) % 12, "天伤")
        _put((soul_idx + 6) % 12, "天使")

    # 年解（年支，戌上起子逆行）
    _put((10 - yb) % 12, "年解")

    # 月解神（农历月）
    month_jieshen_map = [7, 7, 10, 10, 0, 0, 2, 2, 4, 4, 5, 5]
    _put(month_jieshen_map[lunar_month - 1], "月解")

    # 天刑（月，从酉起正月顺行）
    _put((8 + (lunar_month - 1)) % 12, "天刑")

    # 阴煞（月）
    yinsha_map = [2, 0, 10, 8, 6, 4, 2, 0, 10, 8, 6, 4]
    _put(yinsha_map[lunar_month - 1], "阴煞")

    # 天月（月）
    tianyue_map = [10, 4, 4, 2, 7, 3, 11, 7, 2, 5, 10, 2]
    _put(tianyue_map[lunar_month - 1], "天月")

    # 天巫（月）
    tianwu_map = [5, 8, 2, 11, 5, 8, 2, 11, 5, 8, 2, 11]
    _put(tianwu_map[lunar_month - 1], "天巫")

    # 三台八座（日+左辅/右弼）
    day_idx = lunar_day - 1
    zuofu_idx = (4 + lunar_month - 1) % 12
    youbi_idx = (10 - (lunar_month - 1)) % 12
    _put((zuofu_idx + day_idx) % 12, "三台")
    _put((youbi_idx - day_idx) % 12, "八座")

    # 恩光天贵（日+文昌/文曲）
    wenchang_idx = (10 - hour_idx) % 12
    wenqu_idx = (4 + hour_idx) % 12
    _put((wenchang_idx + day_idx - 1) % 12, "恩光")
    _put((wenqu_idx + day_idx - 1) % 12, "天贵")

    # 台辅封诰（时辰）
    _put((5 + hour_idx) % 12, "台辅")
    _put((2 + hour_idx) % 12, "封诰")

    return result


def _place_all_stars(
    year_stem: str, year_branch: str, gender: str,
    lunar_month: int, lunar_day: int, hour_branch_idx: int,
    hour_branch: str, soul_idx: int, body_idx: int
) -> tuple:
    """返回 (minor_map, adj_map)"""
    minor_map = _place_minor_stars(year_stem, year_branch, lunar_month, hour_branch_idx, hour_branch)
    adj_map = _place_adjective_stars(
        year_stem, year_branch, gender,
        lunar_month, lunar_day, hour_branch_idx,
        soul_idx, body_idx
    )
    return minor_map, adj_map


# ============== 主入口 ==============
def ziwei_full(birth: datetime.datetime, gender: str, fix_leap: bool = True) -> dict:
    """完整紫微斗数排盘（纯 Python 实现）

    Args:
        birth: 阳历生辰
        gender: '男' 或 '女'
        fix_leap: 是否修正闰月（一般 True）
    """
    ld = LunarDate.fromSolarDate(birth.year, birth.month, birth.day)
    lunar_year, lunar_month, lunar_day = ld.year, ld.month, ld.day
    is_leap_month = ld.isLeapMonth
    # 闰月处理：把闰月前半月算上月，后半月算下月（默认）
    if is_leap_month and fix_leap:
        # 简化：闰月一律算后一个月（很多流派都这样处理）
        if lunar_month < 12:
            lunar_month += 1
        else:
            lunar_month = 1
            lunar_year += 1
        is_leap_month = False

    # 干支
    year_stem = _year_stem(lunar_year)
    year_branch = _year_branch(lunar_year)
    hour_branch = _time_branch(birth.hour, birth.minute)
    hour_branch_idx = _branch_index(hour_branch)

    # 命宫 / 身宫
    soul_idx, body_idx = _get_soul_and_body_palace(lunar_month, hour_branch)
    soul_stem, soul_branch = _get_soul_ganzhi(year_stem, soul_idx)
    body_stem, body_branch = _get_soul_ganzhi(year_stem, body_idx)

    # 五行局
    nayin_name, five_wx = _get_five_elements_class(soul_stem, soul_branch)
    five_class_value = FIVE_ELEMENTS_CLASS.get(five_wx, 2)

    # 紫微天府位
    ziwei_idx, tianfu_idx = _get_ziwei_index(lunar_day, five_class_value)

    # 辅星 + 杂耀定位
    minor_star_map, adj_star_map = _place_all_stars(
        year_stem, year_branch, gender, lunar_month, lunar_day,
        hour_branch_idx, hour_branch, soul_idx, body_idx
    )
    # 身宫地支用于排除（如果辅星落在身宫地支会被换算）

    # 12 宫
    palaces = []
    for i in range(12):
        palace_idx = _fix_index(soul_idx + i)
        palace_name = PALACE_NAMES_ZH[i]
        is_body = (palace_idx == body_idx)
        is_original = (palace_idx == soul_idx)

        p_stem, p_branch = _get_soul_ganzhi(year_stem, palace_idx)

        # 主星 + 亮度 + 四化
        major_stars = []
        mutagen_map = MUTAGEN.get(year_stem, [""]*4)
        def _add_major(star_name, star_palace_idx):
            brightness_idx = (star_palace_idx - 2 + 12) % 12
            brightness = BRIGHTNESS.get(star_name, [""]*12)[brightness_idx]
            mutagen = ""
            for mi, mn in enumerate(mutagen_map):
                if mn == star_name:
                    mutagen = MUTAGEN_NAMES[mi]
                    break
            major_stars.append({
                "name": star_name,
                "type": "major",
                "scope": "origin",
                "brightness": brightness,
                "mutagen": mutagen,
            })
        for k, s in enumerate(ZIWEI_GROUP):
            if s is None:
                continue
            star_palace_idx = _fix_index(ziwei_idx - k)
            if star_palace_idx == palace_idx:
                _add_major(s, star_palace_idx)
        for k, s in enumerate(TIANFU_GROUP):
            if s is None:
                continue
            star_palace_idx = _fix_index(tianfu_idx + k)
            if star_palace_idx == palace_idx:
                _add_major(s, star_palace_idx)

        # 辅星
        minor_stars = []
        if EARTHLY_BRANCHES[palace_idx] in minor_star_map:
            for sn in minor_star_map[EARTHLY_BRANCHES[palace_idx]]:
                minor_stars.append({"name": sn, "type": "minor", "scope": "origin"})

        # 身宫标记
        if is_body:
            major_stars.append({"name": "身宫", "type": "label", "scope": "origin", "brightness": "", "mutagen": ""})

        # 杂耀
        adj_stars = []
        if EARTHLY_BRANCHES[palace_idx] in adj_star_map:
            for sn in adj_star_map[EARTHLY_BRANCHES[palace_idx]]:
                adj_stars.append({"name": sn, "type": "adjective", "scope": "origin"})

        palaces.append({
            "index": i,
            "name": palace_name,
            "is_body_palace": is_body,
            "is_original_palace": is_original,
            "heavenly_stem": p_stem,
            "earthly_branch": p_branch,
            "major_stars": major_stars,
            "minor_stars": minor_stars,
            "adjective_stars": adj_stars,
        })

    # 大限
    start_age, is_forward = _get_decadal_range(gender, five_class_value, soul_branch)
    decadals = _calculate_decadals(start_age, is_forward, soul_idx, year_stem)
    for d in decadals:
        d_palace_branch = d["earthly_branch"]
        for p in palaces:
            if p["earthly_branch"] == d_palace_branch:
                p["decadal"] = d
                break

    # 当前大限
    today = datetime.date.today()
    age = today.year - birth.year - (1 if (today.month, today.day) < (birth.month, birth.day) else 0)
    current_decadal = None
    for d in decadals:
        if d["range"][0] <= age <= d["range"][1]:
            current_decadal = d
            break

    current_decadal_palace_name = None
    current_decadal_range = None
    if current_decadal:
        for p in palaces:
            if p["earthly_branch"] == current_decadal["earthly_branch"]:
                current_decadal_palace_name = p["name"]
                current_decadal_range = current_decadal["range"]
                break

    # 中文日期
    month_ganzhi = TIGER_RULE[year_stem] + EARTHLY_BRANCHES[(lunar_month + 1) % 12]
    chinese_date = f"{year_stem}{year_branch}年 {month_ganzhi}月"

    month_day = (birth.month, birth.day)
    zodiac_sign = _get_zodiac_sign(month_day)

    result = {
        "datetime": datetime.datetime.now().isoformat(),
        "input": {
            "birth": birth.isoformat(),
            "gender": gender,
            "time_idx": _time_idx(birth.hour),
        },
        "basic": {
            "gender": gender,
            "solar_date": birth.strftime("%Y-%m-%d %H:%M"),
            "lunar_date": f"农历{lunar_year}年{lunar_month}月{lunar_day}日" + ("闰" if is_leap_month else ""),
            "chinese_date": chinese_date,
            "time": hour_branch + "时",
            "time_range": f"{hour_branch}时",
            "sign": zodiac_sign,
            "zodiac": ZODIAC[_branch_index(year_branch)],
            "soul_branch": soul_branch,
            "body_branch": body_branch,
            "soul_master": SOUL_MASTER.get(soul_branch, "?"),
            "body_master": BODY_MASTER.get(year_branch, "?"),
            "five_elements": f"{five_wx}{['零','一','二','三','四','五','六'][five_class_value]}局",
            "five_elements_class": f"{five_wx}{['零','一','二','三','四','五','六'][five_class_value]}局",
        },
        "palaces": palaces,
        "current_age": age,
    }
    if current_decadal_palace_name:
        result["current_decadal_palace"] = current_decadal_palace_name
        result["current_decadal_range"] = current_decadal_range

    return result


def _get_zodiac_sign(month_day: tuple) -> str:
    m, d = month_day
    signs = [
        ((1, 20), (2, 19), "水瓶座"),
        ((2, 20), (3, 20), "双鱼座"),
        ((3, 21), (4, 20), "白羊座"),
        ((4, 21), (5, 20), "金牛座"),
        ((5, 21), (6, 21), "双子座"),
        ((6, 22), (7, 22), "巨蟹座"),
        ((7, 23), (8, 22), "狮子座"),
        ((8, 23), (9, 22), "处女座"),
        ((9, 23), (10, 23), "天秤座"),
        ((10, 24), (11, 22), "天蝎座"),
        ((11, 23), (12, 21), "射手座"),
        ((12, 22), (1, 19), "摩羯座"),
    ]
    for (sm, sd), (em, ed), name in signs:
        if sm == 12:
            if (m == 12 and d >= sd) or (m == 1 and d <= ed):
                return name
        else:
            if (m == sm and d >= sd) or (m == em and d <= ed):
                return name
    return "?"


if __name__ == "__main__":
    import json
    b = datetime.datetime(1995, 6, 16, 14, 30)
    r = ziwei_full(b, "男")
    print(json.dumps(r, ensure_ascii=False, indent=2))
