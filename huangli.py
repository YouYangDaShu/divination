#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""黄历（每日宜忌、吉时、彭祖百忌、神煞）

依赖 cnlunar 库（农历计算 + 黄历神煞表），所有数据来自传统通胜。
"""

import datetime
from typing import Dict, Optional

import cnlunar


# 时辰名（地支）
SHICHEN_NAMES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
# 时辰对应小时区间（HH 字符串）
SHICHEN_HOURS = ['23-1', '1-3', '3-5', '5-7', '7-9', '9-11',
                 '11-13', '13-15', '15-17', '17-19', '19-21', '21-23']

# 12 神煞 → 吉凶（六甲日吉凶简化版）
DAY_GOD_LEVEL = {
    '青龙': '吉', '明堂': '吉', '金匮': '吉', '天德': '吉', '玉堂': '吉', '司命': '吉',
    '天刑': '凶', '朱雀': '凶', '白虎': '凶', '天牢': '凶', '玄武': '凶', '勾陈': '凶',
}


def _shichen_jixiong(twohour_gz_list, day_gz):
    """根据时辰干支判断每个时辰吉凶。

    最简单方法：用十二建除（建除日推时辰也可），但更通用的是
    时辰天干生克日干 + 时辰地支冲日干 + 黄黑道。
    这里采用「时辰冲日支为凶，时辰与日合为吉」简化版。
    """
    if not twohour_gz_list or not day_gz:
        return [{'name': n, 'hours': h, 'gz': '', 'level': '平'}
                for n, h in zip(SHICHEN_NAMES, SHICHEN_HOURS)]

    day_zhi = day_gz[1] if len(day_gz) >= 2 else ''
    # 地支六冲表
    LIUCHONG = {'子': '午', '丑': '未', '寅': '申', '卯': '酉', '辰': '戌', '巳': '亥',
                '午': '子', '未': '丑', '申': '寅', '酉': '卯', '戌': '辰', '亥': '巳'}
    # 地支六合
    LIUHE = {'子': '丑', '丑': '子', '寅': '亥', '亥': '寅', '卯': '戌', '戌': '卯',
             '辰': '酉', '酉': '辰', '巳': '申', '申': '巳', '午': '未', '未': '午'}
    # 地支三合
    SANHE = {'子': ['申', '辰'], '申': ['子', '辰'], '辰': ['子', '申'],
             '丑': ['巳', '酉'], '巳': ['丑', '酉'], '酉': ['丑', '巳'],
             '寅': ['午', '戌'], '午': ['寅', '戌'], '戌': ['寅', '午'],
             '卯': ['未', '亥'], '未': ['卯', '亥'], '亥': ['卯', '未']}

    out = []
    # twohour_gz_list 长度应是 13，按 0(子时,前一天23-当日1) 1(丑) ... 12(子,当日23-下一天1)
    # 我们取前 12 个对应子丑寅卯...亥
    gz_list = twohour_gz_list[:12]
    for i, (name, hours, gz) in enumerate(zip(SHICHEN_NAMES, SHICHEN_HOURS, gz_list)):
        zhi = gz[1] if len(gz) >= 2 else name
        if LIUCHONG.get(zhi) == day_zhi:
            level = '凶'
            reason = f'冲日支{day_zhi}'
        elif LIUHE.get(zhi) == day_zhi or zhi in SANHE.get(day_zhi, []):
            level = '吉'
            reason = f'合日支{day_zhi}'
        elif zhi == day_zhi:
            level = '吉'
            reason = f'与日支{day_zhi}比和'
        else:
            level = '平'
            reason = ''
        out.append({'name': name, 'hours': hours, 'gz': gz, 'level': level, 'reason': reason})
    return out


def huangli_full(date: Optional[datetime.datetime] = None) -> Dict:
    """获取指定日期的黄历完整信息。

    Args:
        date: 日期 (None 则用当前)
    """
    if date is None:
        date = datetime.datetime.now()

    a = cnlunar.Lunar(date, godType='8char')

    # 24 节气：所有节气 + 距下一节气天数
    next_term_date = a.nextSolarTermDate
    next_term_dt = datetime.datetime(a.nextSolarTermYear, next_term_date[0], next_term_date[1])
    days_to_next = (next_term_dt.date() - date.date()).days

    # 时辰吉凶
    shichen = _shichen_jixiong(a.twohour8CharList, a.day8Char)

    # 财喜方位（cnlunar 返回 ['喜神正南', '财神西南', ...] 格式列表）
    lucky_dirs_raw = a.get_luckyGodsDirection()
    directions = {}
    if isinstance(lucky_dirs_raw, list):
        for item in lucky_dirs_raw:
            # 前 2 字 = 神名，后 2 字 = 方位
            if len(item) >= 4:
                directions[item[:2]] = item[2:]
    elif isinstance(lucky_dirs_raw, dict):
        directions = lucky_dirs_raw

    return {
        'date': date.strftime('%Y-%m-%d'),
        'datetime': date.isoformat(),
        'weekday': a.weekDayCn,
        'lunar': {
            'year': a.lunarYearCn,
            'month': a.lunarMonthCn,
            'day': a.lunarDayCn,
            'season': a.lunarSeasonName,
            'phase_of_moon': a.phaseOfMoon,
        },
        'ganzhi': {
            'year': a.year8Char,
            'month': a.month8Char,
            'day': a.day8Char,
            'hour': a.twohour8Char,
        },
        'zodiac': a.chineseYearZodiac,
        'star_zodiac': a.starZodiac,
        'solar_term': {
            'today': a.todaySolarTerms if a.todaySolarTerms != '无' else None,
            'next': a.nextSolarTerm,
            'next_date': f'{next_term_date[0]}月{next_term_date[1]}日',
            'days_to_next': days_to_next,
        },
        'today_level': {
            'level': a.todayLevel,
            'name': a.todayLevelName,
            'thing_level': a.thingLevelName,
        },
        'good_things': a.goodThing,
        'bad_things': a.badThing,
        'good_gods': a.goodGodName,
        'bad_gods': a.badGodName,
        'today_12_god': {
            'name': a.today12DayGod,
            'level': DAY_GOD_LEVEL.get(a.today12DayGod, '平'),
        },
        'today_12_officer': a.today12DayOfficer,
        'today_28_star': a.today28Star,
        'pengzu_taboo': a.get_pengTaboo(),
        'fetal_god': a.get_fetalGod(),
        'lucky_directions': directions,
        'zodiac_clash': a.chineseZodiacClash,
        'zodiac_win': a.zodiacWin,
        'zodiac_lose': a.zodiacLose,
        'meridians': a.meridians,
        'shichen': shichen,
        'saved_path': None,
    }


if __name__ == "__main__":
    import json
    r = huangli_full()
    print(json.dumps(r, ensure_ascii=False, indent=2))
