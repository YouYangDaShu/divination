#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""梅花易数排卦

支持两种起卦方式：
1. 数字起卦：用户报两个数（或自动用时间起）—— 上卦数 / 下卦数 / 动爻
2. 时间起卦：年(地支序号) + 月 + 日 = 上卦数；再 + 时辰 = 下卦数；总和 mod 6 = 动爻

约定：bin6 自下而上（与 core.py 一致）
  bin6[0]=初爻(第1爻), bin6[5]=上爻(第6爻)
  下卦 = bin6[:3]（自下而上3位，即 BAGUA key）
  上卦 = bin6[3:]

核心：
- 八宫八卦序（乾1兑2离3震4巽5坎6艮7坤8）
- 上卦数 mod 8（0→8）  下卦数 mod 8（0→8）
- (上+下+时) mod 6 (0→6) 决定动爻位
- 体用关系：动爻在上卦 → 上卦为用，下卦为体；反之亦然
- 体用生克：用生体最吉，体克用次吉，用克体最凶
- 互卦：取本卦 234 爻为下、345 爻为上
- 错卦：本卦六爻全反
- 综卦：本卦上下颠倒
"""

import datetime
from typing import Tuple, Dict, Optional

# 复用 core 里的 BAGUA / GUA_64
from core import BAGUA, GUA_64

# 八卦 → 卦数（先天数，自下而上3位 bin）
GUA_NUM_TO_BIN = {
    1: "111",  # 乾
    2: "110",  # 兑（自下而上：下阳上阳上阴）
    3: "101",  # 离
    4: "100",  # 震（自下而上：下阳上阴上阴）
    5: "011",  # 巽（自下而上：下阴上阳上阳）
    6: "010",  # 坎
    7: "001",  # 艮（自下而上：下阴上阴上阳）
    8: "000",  # 坤
}
GUA_BIN_TO_NUM = {v: k for k, v in GUA_NUM_TO_BIN.items()}

# 五行生克
WUXING_SHENG = {"金": "水", "水": "木", "木": "火", "火": "土", "土": "金"}  # 生
WUXING_KE = {"金": "木", "木": "土", "土": "水", "水": "火", "火": "金"}  # 克

# 地支序号（用于年起卦）
DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
DIZHI_NUM = {z: i + 1 for i, z in enumerate(DIZHI)}


def _to_8(n: int) -> int:
    """卦数：余 8，0 → 8"""
    n = n % 8
    return 8 if n == 0 else n


def _to_6(n: int) -> int:
    """动爻：余 6，0 → 6"""
    n = n % 6
    return 6 if n == 0 else n


def _flip_yao(bin6: str, pos: int) -> str:
    """翻转第 pos 爻（1=最下/初爻，6=最上/上爻）

    bin6 自下而上：bin6[0]=初爻, bin6[5]=上爻。
    第 pos 爻的索引 = pos - 1。
    """
    chars = list(bin6)
    idx = pos - 1
    chars[idx] = "1" if chars[idx] == "0" else "0"
    return "".join(chars)


def _gua_info(bin6: str) -> Dict:
    """根据 6 位 bin (自下而上) 返回完整卦信息"""
    lower = bin6[:3]   # 自下而上 1-3 爻 = 下卦 (BAGUA key)
    upper = bin6[3:]   # 自下而上 4-6 爻 = 上卦

    name, judgment, meaning = ("?", "?", "?")
    if bin6 in GUA_64:
        info = GUA_64[bin6]
        name, judgment, meaning = info[0], info[1], info[2]

    upper_info = BAGUA.get(upper, ("?", "?", "?", "?"))
    lower_info = BAGUA.get(lower, ("?", "?", "?", "?"))

    return {
        "bin": bin6,
        "name": name,
        "judgment": judgment,
        "meaning": meaning,
        "upper_gua": upper_info[0],
        "upper_xiang": upper_info[1],
        "upper_symbol": upper_info[2],
        "upper_wuxing": upper_info[3],
        "lower_gua": lower_info[0],
        "lower_xiang": lower_info[1],
        "lower_symbol": lower_info[2],
        "lower_wuxing": lower_info[3],
    }


def _hu_gua(bin6: str) -> str:
    """互卦：本卦 234 爻为新下卦，345 爻为新上卦。

    bin6 自下而上：第1=bin6[0], ..., 第6=bin6[5]
    新 bin6 = 新初爻..新上爻
            = 原第2 + 原第3 + 原第4 + 原第3 + 原第4 + 原第5
            = bin6[1] + bin6[2] + bin6[3] + bin6[2] + bin6[3] + bin6[4]
    """
    return bin6[1] + bin6[2] + bin6[3] + bin6[2] + bin6[3] + bin6[4]


def _cuo_gua(bin6: str) -> str:
    """错卦：6 爻全反"""
    return "".join("1" if c == "0" else "0" for c in bin6)


def _zong_gua(bin6: str) -> str:
    """综卦：爻序整体颠倒（原第1爻↔第6爻）

    自下而上反过来 = 仍是 6 位字符串，新第1爻=原第6爻。
    """
    return bin6[::-1]


def _ti_yong_relation(ti_wx: str, yong_wx: str) -> Tuple[str, str]:
    """体用关系判断
    返回 (关系名, 吉凶等级)
    等级：极吉/吉/平/凶/极凶

    梅花易数体用要诀：
    - 用生体：他人/外事来生我，最吉
    - 体克用：我克制对方/事情可掌控，吉
    - 比和：同五行，吉（次吉）
    - 体生用：我泄气给对方，凶
    - 用克体：对方克制我，极凶
    """
    if ti_wx == yong_wx:
        return ("比和", "吉")
    if WUXING_SHENG.get(yong_wx) == ti_wx:
        return ("用生体", "极吉")
    if WUXING_SHENG.get(ti_wx) == yong_wx:
        return ("体生用", "凶")
    if WUXING_KE.get(ti_wx) == yong_wx:
        return ("体克用", "吉")
    if WUXING_KE.get(yong_wx) == ti_wx:
        return ("用克体", "极凶")
    return ("无明显生克", "平")


def meihua_full(num1: Optional[int] = None,
                num2: Optional[int] = None,
                question: str = "",
                use_time: bool = False) -> Dict:
    """梅花易数完整起卦。

    Args:
        num1: 第一个数（用于上卦），None 时随机
        num2: 第二个数（用于下卦），None 时随机
        question: 所问之事
        use_time: True 则改用当前时间起卦（覆盖 num1/num2）
    """
    import random
    now = datetime.datetime.now()

    if use_time or (num1 is None and num2 is None):
        # 时间起卦：年(支序)+月+日 → 上卦； +时辰 → 下卦
        hour = now.hour
        if hour == 23:
            shichen = 1
        else:
            shichen = ((hour + 1) // 2) % 12 + 1
        # 简化：用 (年 - 1900) % 12 + 1 作为年支序号 (1900 是庚子年)
        year_zhi_idx = (now.year - 1900) % 12 + 1  # 1-12
        month = now.month
        day = now.day
        upper_n = _to_8(year_zhi_idx + month + day)
        lower_n = _to_8(year_zhi_idx + month + day + shichen)
        dong_yao = _to_6(year_zhi_idx + month + day + shichen)
        method = f"时间起卦：年支序{year_zhi_idx} + 月{month} + 日{day} = 上卦数；再 + 时辰{shichen} = 下卦数"
        num1_used = year_zhi_idx + month + day
        num2_used = num1_used + shichen
    else:
        if num1 is None:
            num1 = random.randint(1, 100)
        if num2 is None:
            num2 = random.randint(1, 100)
        upper_n = _to_8(num1)
        lower_n = _to_8(num2)
        dong_yao = _to_6(num1 + num2)
        method = f"数字起卦：{num1} ÷ 8 余{upper_n} = 上卦；{num2} ÷ 8 余{lower_n} = 下卦；({num1}+{num2}) ÷ 6 余{dong_yao} = 动爻"
        num1_used = num1
        num2_used = num2

    upper_bin = GUA_NUM_TO_BIN[upper_n]   # 自下而上 3 位
    lower_bin = GUA_NUM_TO_BIN[lower_n]   # 自下而上 3 位
    # ben_bin 自下而上 6 位 = 下卦在前 + 上卦在后
    ben_bin = lower_bin + upper_bin

    # 变卦：本卦动爻翻转
    bian_bin = _flip_yao(ben_bin, dong_yao)

    # 互卦、错卦、综卦
    hu_bin = _hu_gua(ben_bin)
    cuo_bin = _cuo_gua(ben_bin)
    zong_bin = _zong_gua(ben_bin)

    # 体用关系：动爻在下卦(1-3) → 下卦为用、上卦为体；动爻在上卦(4-6) → 上卦为用、下卦为体
    if dong_yao <= 3:
        ti_pos = "上卦"
        yong_pos = "下卦"
        ti_gua = BAGUA[upper_bin][0]
        ti_wx = BAGUA[upper_bin][3]
        yong_gua = BAGUA[lower_bin][0]
        yong_wx = BAGUA[lower_bin][3]
    else:
        ti_pos = "下卦"
        yong_pos = "上卦"
        ti_gua = BAGUA[lower_bin][0]
        ti_wx = BAGUA[lower_bin][3]
        yong_gua = BAGUA[upper_bin][0]
        yong_wx = BAGUA[upper_bin][3]

    relation_name, relation_level = _ti_yong_relation(ti_wx, yong_wx)

    return {
        "datetime": now.isoformat(),
        "question": question,
        "method": method,
        "input": {
            "num1": num1_used,
            "num2": num2_used,
            "use_time": use_time,
        },
        "calc": {
            "upper_n": upper_n,
            "lower_n": lower_n,
            "dong_yao": dong_yao,
        },
        "ben_gua": _gua_info(ben_bin),
        "bian_gua": _gua_info(bian_bin),
        "hu_gua": _gua_info(hu_bin),
        "cuo_gua": _gua_info(cuo_bin),
        "zong_gua": _gua_info(zong_bin),
        "ti_yong": {
            "ti_position": ti_pos,
            "ti_gua": ti_gua,
            "ti_wuxing": ti_wx,
            "yong_position": yong_pos,
            "yong_gua": yong_gua,
            "yong_wuxing": yong_wx,
            "relation": relation_name,
            "level": relation_level,
        },
        "saved_path": None,
    }


if __name__ == "__main__":
    import json
    # 时间起卦
    r = meihua_full(use_time=True, question="测试")
    print(json.dumps(r, ensure_ascii=False, indent=2))
