#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""奇门遁甲（时家奇门）排盘

封装 kinqimen 库，输出标准 9 宫盘 + 简体中文。
默认使用「置閏」流派（传统主流派）。

输出包含：
- 干支（年月日时）
- 排局（陽遁X局上中下元 / 陰遁X局X元）
- 節氣
- 值符值使
- 9 宫盘：每宫的 天盘干、地盘干、八门、九星、八神
- 旬空、馬星
- 暗干、長生運（可选）
"""

import datetime
from typing import Dict, Optional

# kinqimen 间接依赖 ephem，ephem 在 Python 3.14 上 C 扩展编译失败。
# 改成 lazy import：只在真正排奇门盘时才加载，其它命理 API 不受影响。
def _load_Qimen():
    try:
        from kinqimen.kinqimen import Qimen
        return Qimen
    except ImportError as e:
        raise RuntimeError(
            "奇门遁甲模块依赖 kinqimen + ephem，当前 Python 环境装不上。"
            "占卜系统的其它 7 个 API（六爻/小六壬/八字/合婚/紫微/梅花/黄历）正常可用。"
        ) from e


# 单字繁→简映射（仅用于"自由文本"如 "陽遁五局上元 / 小滿"）
# 注意：1 个繁体字只映射成 1 个简体字，永不映射成多字串
SINGLE_T2S = {
    '陽': '阳', '陰': '阴',
    '節': '节', '氣': '气',
    '滿': '满', '寒': '寒', '熱': '热',
    '時': '时', '門': '门',
    '盤': '盘',
    '驛': '驿', '馬': '马',
    '臨': '临', '輔': '辅',
    '長': '长', '運': '运',
    '絕': '绝', '養': '养',
    '沖': '冲', '離': '离', '兌': '兑',
}

GONG_SIMP = {'乾': '乾', '坎': '坎', '艮': '艮', '震': '震',
             '巽': '巽', '離': '离', '坤': '坤', '兌': '兑', '中': '中'}

GATE_SIMP = {'休': '休', '生': '生', '傷': '伤', '杜': '杜',
             '景': '景', '死': '死', '驚': '惊', '開': '开'}

STAR_SIMP = {'英': '英', '蓬': '蓬', '任': '任', '輔': '辅',
             '沖': '冲', '禽': '禽', '心': '心', '柱': '柱'}


def _t2s(s):
    """繁→简（逐字单字映射，不替换多字短语）"""
    if s is None:
        return s
    if isinstance(s, str):
        return ''.join(SINGLE_T2S.get(c, c) for c in s)
    if isinstance(s, dict):
        return {_t2s(k): _t2s(v) for k, v in s.items()}
    if isinstance(s, (list, tuple)):
        return type(s)(_t2s(x) for x in s)
    return s


def _gong_simp(g):
    return GONG_SIMP.get(g, _t2s(g))


def _gate_simp(g):
    return GATE_SIMP.get(g, _t2s(g))


def _star_simp(g):
    return STAR_SIMP.get(g, _t2s(g))


# 八神：kinqimen 用单字简写（符蛇陰合勾雀地天），下面给出全名
SHEN_FULL_NAME = {
    '符': '值符', '蛇': '螣蛇', '陰': '太阴', '合': '六合',
    '勾': '白虎', '雀': '玄武', '地': '九地', '天': '九天',
}

# 九星全称（统一简体）
STAR_FULL = {
    '英': '天英', '蓬': '天蓬', '任': '天任', '輔': '天辅',
    '沖': '天冲', '禽': '天禽', '心': '天心', '柱': '天柱',
}

# 八门全称
GATE_FULL = {
    '休': '休门', '生': '生门', '傷': '伤门', '杜': '杜门',
    '景': '景门', '死': '死门', '驚': '惊门', '開': '开门',
}

# 八门吉凶
GATE_LEVEL = {
    '休': '吉', '生': '吉', '開': '吉',
    '杜': '平', '景': '平',
    '傷': '凶', '死': '凶', '驚': '凶',
}

# 九星吉凶
STAR_LEVEL = {
    '英': '凶', '蓬': '凶', '任': '吉', '輔': '吉',
    '沖': '吉', '禽': '吉', '心': '吉', '柱': '凶',
}

# 八神吉凶
SHEN_LEVEL = {
    '符': '吉', '蛇': '凶', '陰': '吉', '合': '平',
    '勾': '凶', '雀': '凶', '地': '吉', '天': '吉',
}

# 九宫方位（顺时针：自下而上 + 顺时针流转）
# 北坎 → 东北艮 → 东震 → 东南巽 → 南离 → 西南坤 → 西兑 → 西北乾 → 中
GONG_DIRECTIONS = {
    '坎': '正北', '艮': '东北', '震': '正东', '巽': '东南',
    '離': '正南', '坤': '西南', '兌': '正西', '乾': '西北', '中': '中宫',
}


def qimen_full(birth: Optional[datetime.datetime] = None,
               option: int = 2,
               question: str = "") -> Dict:
    """奇门遁甲完整排盘

    Args:
        birth: 起卦时间。None 则用当前
        option: 1=拆补法 / 2=置闰法（默认）
        question: 所问之事
    """
    if birth is None:
        birth = datetime.datetime.now()

    qm = _load_Qimen()(birth.year, birth.month, birth.day, birth.hour, birth.minute)
    raw = qm.pan(option)

    # 9 宫表（按顺时针：坎东北艮东震东南巽南离西南坤西兑西北乾，最后中）
    # 注意：星/门/神的"全名/吉凶"是预先映射好的标准简体字符串，不再走 _t2s
    palaces = []
    for gong in ['坎', '艮', '震', '巽', '離', '坤', '兌', '乾', '中']:
        sky_gan = raw['天盤'].get(gong, '')
        earth_gan = raw['地盤'].get(gong, '')
        gate = raw['門'].get(gong, '')
        star = raw['星'].get(gong, '')
        shen = raw['神'].get(gong, '')

        gate_level = GATE_LEVEL.get(gate, '')
        star_level = STAR_LEVEL.get(star, '')
        shen_level = SHEN_LEVEL.get(shen, '')

        palaces.append({
            'gong': _gong_simp(gong),
            'direction': GONG_DIRECTIONS.get(gong, ''),
            'sky_gan': sky_gan,           # 天干本身繁简一致
            'earth_gan': earth_gan,
            'gate': GATE_FULL.get(gate, gate),
            'gate_short': _gate_simp(gate),
            'gate_level': gate_level,
            'star': STAR_FULL.get(star, star),
            'star_short': _star_simp(star),
            'star_level': star_level,
            'shen': SHEN_FULL_NAME.get(shen, shen),
            'shen_short': SHEN_FULL_NAME.get(shen, shen),
            'shen_level': shen_level,
        })

    zhifu = raw['值符值使']
    # 值符值使中星宫/门宫的值是繁体单字，转成全名 + 简体
    zhifu_star = zhifu.get('值符星宮', ['', ''])
    zhifu_gate = zhifu.get('值使門宮', ['', ''])
    zhifu_star_full = STAR_FULL.get(zhifu_star[0], zhifu_star[0]) if zhifu_star else ''
    zhifu_star_gong = _gong_simp(zhifu_star[1]) if len(zhifu_star) > 1 else ''
    zhifu_gate_full = GATE_FULL.get(zhifu_gate[0], zhifu_gate[0]) if zhifu_gate else ''
    zhifu_gate_gong = _gong_simp(zhifu_gate[1]) if len(zhifu_gate) > 1 else ''

    return {
        'datetime': birth.isoformat(),
        'question': question,
        'method': '置闰' if option == 2 else '拆补',
        'ganzhi': _t2s(raw.get('干支', '')),
        'paiju': _t2s(raw.get('排局', '')),
        'jieqi': _t2s(raw.get('節氣', '')),
        'xunshou': raw.get('旬首', ''),
        'xunkong': {
            '日空': raw.get('旬空', {}).get('日空', ''),
            '时空': raw.get('旬空', {}).get('時空', ''),
        },
        'zhifu': {
            '值符天干': zhifu.get('值符天干', []),
            '值符星': zhifu_star_full,
            '值符宫': zhifu_star_gong,
            '值使门': zhifu_gate_full,
            '值使宫': zhifu_gate_gong,
        },
        'tianyi': STAR_FULL.get(raw.get('天乙', ''), raw.get('天乙', '')),
        'mastar': {
            '天马': raw.get('馬星', {}).get('天馬', ''),
            '丁马': raw.get('馬星', {}).get('丁馬', ''),
            '驿马': raw.get('馬星', {}).get('驛馬', ''),
        },
        'palaces': palaces,
        'saved_path': None,
    }


if __name__ == "__main__":
    import json
    r = qimen_full(question="测试奇门")
    print(json.dumps(r, ensure_ascii=False, indent=2))
