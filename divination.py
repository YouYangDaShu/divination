#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中国传统占卜工具：六爻 + 小六壬
============================
- 六爻：基于《周易》六十四卦，铜钱起卦
- 小六壬：诸葛马前课，时辰起卦
"""

import random
import datetime
from typing import List, Dict, Tuple


# ==================== 六十四卦 ====================
GUA_64 = {
    "111111": ("乾为天", "元亨利贞，自强不息", "大吉，刚健中正，万事顺遂"),
    "000000": ("坤为地", "厚德载物，柔顺中正", "吉，宜守不宜攻"),
    "010001": ("水雷屯", "始生艰难，贞下起元", "凶中带吉，须忍耐"),
    "100010": ("山水蒙", "蒙以养正，圣功也", "需启蒙学习，渐进"),
    "010111": ("水天需", "需者，须也，等待时机", "需耐心等待，吉"),
    "111010": ("天水讼", "讼，有孚，窒惕中吉", "争讼之象，宜和解"),
    "000010": ("地水师", "师出有名，丈人吉", "众人之事，主帅得力"),
    "010000": ("水地比", "比，吉。原筮元永贞", "亲和团结，吉"),
    "110111": ("风天小畜", "密云不雨，小有畜养", "小有所得，待时而动"),
    "111011": ("天泽履", "履虎尾，不咥人，亨", "履险如夷，谨慎吉"),
    "000111": ("地天泰", "天地交而万物通", "大吉，通达顺利"),
    "111000": ("天地否", "否之匪人，不利君子贞", "凶，闭塞不通"),
    "111101": ("天火同人", "同人于野，亨", "志同道合，团结吉"),
    "101111": ("火天大有", "大有，元亨", "大吉，富有得志"),
    "001000": ("地山谦", "谦谦君子，卑以自牧", "吉，谦受益"),
    "000100": ("雷地豫", "豫，利建侯行师", "和悦欢乐，宜有所行动"),
    "011001": ("泽雷随", "随，元亨利贞，无咎", "顺势而为，吉"),
    "100110": ("山风蛊", "蛊，元亨而天下治也", "需整顿革新"),
    "000011": ("地泽临", "临，元亨利贞", "吉，逐步壮大"),
    "110000": ("风地观", "观，盥而不荐，有孚顒若", "观察等待，宜静"),
    "101001": ("火雷噬嗑", "颐中有物曰噬嗑", "破除障碍，吉"),
    "100101": ("山火贲", "贲，亨。小利有攸往", "文饰之象，小利"),
    "100000": ("山地剥", "剥，不利有攸往", "凶，剥落衰败"),
    "000001": ("地雷复", "复，亨。出入无疾", "吉，否极泰来"),
    "111001": ("天雷无妄", "无妄，元亨利贞", "顺乎自然，吉"),
    "100111": ("山天大畜", "大畜，利贞，不家食吉", "大吉，蓄积大业"),
    "100001": ("山雷颐", "颐，贞吉。养正则吉", "养生养德，吉"),
    "011110": ("泽风大过", "大过，栋桡，利有攸往", "非常之时，宜变"),
    "010010": ("坎为水", "习坎，有孚，维心亨", "险中带吉，须诚信"),
    "101101": ("离为火", "离，利贞，亨", "光明附丽，吉"),
    "001011": ("泽山咸", "咸，亨，利贞，取女吉", "感应交融，吉"),
    "110100": ("雷风恒", "恒，亨，无咎", "持久之道，吉"),
    "111100": ("天山遁", "遁，亨，小利贞", "退避保身，吉"),
    "001111": ("雷天大壮", "大壮，利贞", "强壮之时，宜守正"),
    "101000": ("火地晋", "晋，康侯用锡马蕃庶", "吉，进取顺利"),
    "000101": ("地火明夷", "明夷，利艰贞", "韬光养晦，凶"),
    "110101": ("风火家人", "家人，利女贞", "家和万事兴，吉"),
    "101011": ("火泽睽", "睽，小事吉", "意见相左，小心"),
    "001010": ("水山蹇", "蹇，利西南，不利东北", "艰难险阻，凶"),
    "010100": ("雷水解", "解，利西南", "解困释难，吉"),
    "100011": ("山泽损", "损，有孚，元吉", "损己利人，吉"),
    "110001": ("风雷益", "益，利有攸往，利涉大川", "增益之道，大吉"),
    "011111": ("泽天夬", "夬，扬于王庭", "决断之时，刚柔并济"),
    "111110": ("天风姤", "姤，女壮，勿用取女", "邂逅之象，慎"),
    "000110": ("泽地萃", "萃，亨。王假有庙", "聚集兴旺，吉"),
    "011000": ("地风升", "升，元亨", "大吉，升迁向上"),
    "010110": ("泽水困", "困，亨，贞，大人吉", "困境守贞，凶"),
    "011010": ("水风井", "井，改邑不改井", "井养不穷，平稳"),
    "101110": ("泽火革", "革，已日乃孚", "变革之道，吉"),
    "011101": ("火风鼎", "鼎，元吉，亨", "大吉，鼎新立业"),
    "001100": ("震为雷", "震，亨。震来虩虩", "震动惊恐，警惕"),
    "100100": ("艮为山", "艮其背，不获其身", "止于至善，吉"),
    "110010": ("风山渐", "渐，女归吉，利贞", "循序渐进，吉"),
    "001011": ("雷泽归妹", "归妹，征凶，无攸利", "勉强从事，凶"),
    "101100": ("雷火丰", "丰，亨。王假之", "丰盛之极，盛极而衰"),
    "001101": ("火山旅", "旅，小亨", "漂泊在外，小吉"),
    "110110": ("巽为风", "巽，小亨，利有攸往", "顺从入伏，小吉"),
    "011011": ("兑为泽", "兑，亨，利贞", "悦泽之象，吉"),
    "110011": ("风水涣", "涣，亨。王假有庙", "涣散重聚，吉"),
    "010011": ("水泽节", "节，亨。苦节不可贞", "节制有度，吉"),
    "110011": ("风泽中孚", "中孚，豚鱼吉", "诚信之道，吉"),
    "001110": ("雷山小过", "小过，亨，利贞", "小有过越，可"),
    "010101": ("水火既济", "既济，亨小，利贞", "事已成，慎守"),
    "101010": ("火水未济", "未济，亨。小狐汔济", "未成之事，渐成"),
}


# ==================== 八卦 ====================
BAGUA = {
    "111": "乾 乾(天)",
    "110": "兑 兑(泽)",
    "101": "离 离(火)",
    "100": "震 震(雷)",
    "011": "巽 巽(风)",
    "010": "坎 坎(水)",
    "001": "艮 艮(山)",
    "000": "坤 坤(地)",
}


# ==================== 小六壬 ====================
XIAO_LIU_REN = [
    {
        "name": "大安",
        "element": "木",
        "color": "[吉]",
        "judgment": "事事昌，求财在坤方。失物去不远，宅舍保安康。行人身未动，疾病主无妨。将军回田野，仔细更推详。",
        "summary": "吉。万事顺遂，求财得，失物近，病无碍，行人未动。",
        "good_for": ["求财", "婚姻", "出行平安", "病情趋稳", "失物近寻"],
    },
    {
        "name": "留连",
        "element": "水",
        "color": "",
        "judgment": "事难成，求谋日未明。官事只宜缓，去者未回程。失物南方去，急寻方可寻。更须防口舌，人口且太平。",
        "summary": "凶中带平。事多拖延，谋事未明，宜耐心等待。",
        "good_for": ["延期", "等待", "暂缓决定"],
    },
    {
        "name": "速喜",
        "element": "火",
        "color": "[凶]",
        "judgment": "喜来临，求财向南行。失物申未午，逢人路上寻。官事有福德，病者无禁忌。田宅六畜吉，行人有信音。",
        "summary": "大吉。喜事临门，求财顺利，行人即至，失物速得。",
        "good_for": ["喜事", "求财", "升职", "好消息", "行人归"],
    },
    {
        "name": "赤口",
        "element": "金",
        "color": "",
        "judgment": "主口舌，是非须慎防。失物急去寻，行人有惊慌。鸡犬多作怪，病者出西方。更须防咒诅，恐怕染瘟殃。",
        "summary": "凶。口舌是非，须防争吵和小人，做事易生波折。",
        "good_for": ["谨言慎行", "避免争执", "暂停决策"],
    },
    {
        "name": "小吉",
        "element": "水",
        "color": "[平]",
        "judgment": "最相当，路上好商量。阴人来报喜，失物在坤方。行人即便至，交易甚是强。凡事皆和合，病者叩穹苍。",
        "summary": "吉。诸事和谐，交易顺利，与人合作有利。",
        "good_for": ["合作", "交易", "婚姻", "调解", "求人办事"],
    },
    {
        "name": "空亡",
        "element": "土",
        "color": "",
        "judgment": "事不祥，阴人多乖张。求财无利益，行人有灾殃。失物寻不见，官事有刑伤。病人逢暗鬼，析祷保安康。",
        "summary": "大凶。诸事不顺，求财无利，宜静不宜动。",
        "good_for": ["静心反思", "暂停大事", "祈福消灾"],
    },
]


# ==================== 六爻起卦 ====================
def toss_coins() -> int:
    """模拟掷三枚铜钱，返回爻象。

    阳面=3，阴面=2
    三阳=9 老阳(变阴)，两阳一阴=8 少阴，一阳两阴=7 少阳，三阴=6 老阴(变阳)
    返回: 6/7/8/9
    """
    coins = [random.choice([2, 3]) for _ in range(3)]
    return sum(coins)


def get_yao_symbol(yao_value: int) -> Tuple[str, str, bool]:
    """根据爻值返回符号、说明、是否变爻"""
    if yao_value == 6:  # 老阴
        return "▬▬ ▬▬ ×", "老阴 (变阳)", True
    elif yao_value == 7:  # 少阳
        return "▬▬▬▬▬▬", "少阳", False
    elif yao_value == 8:  # 少阴
        return "▬▬ ▬▬", "少阴", False
    elif yao_value == 9:  # 老阳
        return "▬▬▬▬▬▬ ○", "老阳 (变阴)", True
    return "?", "未知", False


def yao_to_binary(yao_value: int, get_changed: bool = False) -> str:
    """爻值转二进制"""
    if yao_value in (7, 9):  # 阳
        return "0" if get_changed and yao_value == 9 else "1"
    else:  # 阴
        return "1" if get_changed and yao_value == 6 else "0"


def liuyao_divination(question: str = "") -> str:
    """六爻起卦"""
    output = []
    output.append("╔" + "═" * 58 + "╗")
    output.append("║" + "六爻占卜（铜钱起卦法）".center(46) + "║")
    output.append("╚" + "═" * 58 + "╝")

    if question:
        output.append(f"\n【所问之事】{question}")

    now = datetime.datetime.now()
    output.append(f"【占卜时间】{now.strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 起卦：从下往上六爻
    yao_values = []
    output.append("【起卦过程】（自下而上，初爻→上爻）")
    for i in range(6):
        yv = toss_coins()
        yao_values.append(yv)
        symbol, desc, _ = get_yao_symbol(yv)
        output.append(f"  第{i+1}爻：{symbol}  ({desc})")

    # 本卦
    ben_gua_bin = "".join([yao_to_binary(v) for v in yao_values])
    # 显示卦象（自上而下）
    output.append("\n【本卦】")
    for i in range(5, -1, -1):
        symbol, _, _ = get_yao_symbol(yao_values[i])
        output.append(f"  {symbol}")

    # 查卦
    if ben_gua_bin in GUA_64:
        name, judgment, meaning = GUA_64[ben_gua_bin]
        output.append(f"\n  卦名：《{name}》")
        output.append(f"  卦辞：{judgment}")
        output.append(f"  释义：{meaning}")
    else:
        output.append(f"\n  二进制：{ben_gua_bin}（卦象库未收录该卦）")

    # 上下卦
    upper = ben_gua_bin[3:]
    lower = ben_gua_bin[:3]
    output.append(f"\n  上卦：{BAGUA.get(upper, upper)}")
    output.append(f"  下卦：{BAGUA.get(lower, lower)}")

    # 变卦
    has_change = any(v in (6, 9) for v in yao_values)
    if has_change:
        bian_gua_bin = "".join([yao_to_binary(v, get_changed=True) for v in yao_values])
        output.append("\n【变卦】")
        for i in range(5, -1, -1):
            ch = bian_gua_bin[i]
            sym = "▬▬▬▬▬▬" if ch == "1" else "▬▬ ▬▬"
            output.append(f"  {sym}")
        if bian_gua_bin in GUA_64:
            name2, judgment2, meaning2 = GUA_64[bian_gua_bin]
            output.append(f"\n  变卦：《{name2}》")
            output.append(f"  卦辞：{judgment2}")
            output.append(f"  释义：{meaning2}")

        # 变爻提示
        change_yaos = [i+1 for i, v in enumerate(yao_values) if v in (6, 9)]
        output.append(f"\n  变爻：第 {', '.join(map(str, change_yaos))} 爻")
        output.append("  断卦：本卦为现状，变卦为结果，变爻为关键转折")
    else:
        output.append("\n【无变爻】事态稳定，按本卦判断即可。")

    output.append("\n" + "═" * 60)
    output.append(" 占卜仅供参考，关键还是自己的努力与判断。")

    return "\n".join(output)


# ==================== 小六壬起卦 ====================
def xiao_liu_ren_divination(
    question: str = "",
    month: int | None = None,
    day: int | None = None,
    hour: int | None = None,
) -> str:
    """小六壬占卜（诸葛马前课）

    起法：从大安起月，按月数到当前月；从落处起日，按日数到当前日；
         从落处起时辰，按时辰数到当前时辰，落处即所占之卦。
    """
    output = []
    output.append("╔" + "═" * 58 + "╗")
    output.append("║" + "小六壬（诸葛马前课）".center(48) + "║")
    output.append("╚" + "═" * 58 + "╝")

    if question:
        output.append(f"\n【所问之事】{question}")

    now = datetime.datetime.now()
    if month is None: month = now.month
    if day is None: day = now.day
    if hour is None:
        # 转换为时辰（0-11，子时=0）
        h = now.hour
        # 子(23-1)=0, 丑(1-3)=1, 寅(3-5)=2 ...
        if h == 23 or h == 0:
            shichen_idx = 0
        else:
            shichen_idx = (h + 1) // 2
        hour = shichen_idx

    shichen_names = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    shichen_name = shichen_names[hour] if 0 <= hour < 12 else "?"

    output.append(f"【占卜时间】{now.strftime('%Y-%m-%d %H:%M:%S')}")
    output.append(f"【农历参考】{month}月{day}日 {shichen_name}时\n")

    # 起卦：从大安开始，按"月→日→时辰"顺数
    # 1. 月数：从大安(0)起，数到 month，落点 = (month - 1) % 6
    p1 = (month - 1) % 6
    # 2. 日数：从 p1 起，数到 day，落点 = (p1 + day - 1) % 6
    p2 = (p1 + day - 1) % 6
    # 3. 时辰：从 p2 起，数到 hour+1（子时为第1个），落点 = (p2 + hour) % 6
    p3 = (p2 + hour) % 6

    output.append("【起卦过程】")
    output.append(f"  ① 月起大安：从「大安」起{month}月 → 落「{XIAO_LIU_REN[p1]['name']}」")
    output.append(f"  ② 日起月落：从「{XIAO_LIU_REN[p1]['name']}」起{day}日 → 落「{XIAO_LIU_REN[p2]['name']}」")
    output.append(f"  ③ 时起日落：从「{XIAO_LIU_REN[p2]['name']}」起{shichen_name}时 → 落「{XIAO_LIU_REN[p3]['name']}」")

    # 结果
    result = XIAO_LIU_REN[p3]
    output.append("\n" + "─" * 60)
    output.append(f"【所得之卦】{result['color']} 《{result['name']}》（{result['element']}）")
    output.append("─" * 60)
    output.append(f"\n【卦辞】\n  {result['judgment']}")
    output.append(f"\n【白话】\n  {result['summary']}")
    output.append(f"\n【宜】{' / '.join(result['good_for'])}")

    output.append("\n" + "═" * 60)
    output.append(" 占卜仅供参考，三思而后行。")

    return "\n".join(output)


# ==================== 命令行接口 ====================
def main():
    import sys
    print("\n" + "═" * 60)
    print(" " * 18 + " 中国传统占卜 ")
    print("═" * 60)
    print("\n请选择占卜方式：")
    print("  1. 六爻 (周易铜钱起卦，复杂详细)")
    print("  2. 小六壬 (诸葛马前课，时辰起卦)")
    print("  3. 两个都来一次")
    print("  0. 退出\n")

    try:
        choice = input("请输入选择 (0-3): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n退出。")
        return

    if choice == "0":
        return

    try:
        question = input("\n请输入你想问的事情 (可留空): ").strip()
    except (EOFError, KeyboardInterrupt):
        question = ""

    print()
    if choice == "1":
        print(liuyao_divination(question))
    elif choice == "2":
        print(xiao_liu_ren_divination(question))
    elif choice == "3":
        print(xiao_liu_ren_divination(question))
        print("\n\n")
        print(liuyao_divination(question))
    else:
        print("无效选择。")


if __name__ == "__main__":
    main()
