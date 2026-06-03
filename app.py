#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Flask 后端：六爻 + 小六壬 + 八字 + 紫微 + 梅花 + 奇门 + 黄历 + 解梦"""

import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from core import liuyao_full, xiao_liu_ren_full, export_to_obsidian
from bazi import full_bazi_chart
from he_hun import he_hun_full
from ziwei import ziwei_full
from meihua import meihua_full
from qimen import qimen_full
from huangli import huangli_full
from dream import dream_full
from ratelimit import rate_limited, get_stats, init_db
from ai_reading import ai_interpret
import datetime

# 加载配置
try:
    from config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG
except ImportError:
    FLASK_HOST = os.environ.get("FLASK_HOST", "127.0.0.1")
    FLASK_PORT = int(os.environ.get("FLASK_PORT", 5066))
    FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

app = Flask(__name__, static_folder="static", template_folder="templates")
init_db()


def should_save(data) -> bool:
    """是否保存到 Obsidian。公网请求（经 Caddy 反代）一律不保存，
    避免陌生人的占卜记录污染笔记库。本地直连保留原行为。"""
    if request.headers.get("X-Forwarded-For"):
        return False
    return bool(data.get("save_obsidian", True))


def attach_ai(divine_type: str, result, data):
    """只要用户填了问题（心中所问 question）或处境（user_context），
    就调 AI 结合排盘结果做白话解读，塞进 result['ai_reading']。
    两者都填则合并喂给 AI。都没填则跳过（纯排盘）。AI 失败不影响主结果。"""
    if not isinstance(result, dict):
        return result
    question = (data.get("question") or "").strip()
    ctx = (data.get("user_context") or "").strip()
    # 合并：心中所问 + 处境框，任一有值即触发
    parts = []
    if question:
        parts.append(f"我想问的事：{question}")
    if ctx:
        parts.append(f"我的具体处境：{ctx}")
    merged = "；".join(parts)
    if merged:
        reading = ai_interpret(divine_type, result, merged)
        if reading:
            result["ai_reading"] = reading
    return result


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/liuyao", methods=["POST"])
@rate_limited("liuyao")
def api_liuyao():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    save = should_save(data)

    result = liuyao_full(question)

    saved_path = None
    if save:
        saved_path = export_to_obsidian(result, "liuyao")

    result["saved_path"] = saved_path
    attach_ai("六爻", result, data)
    return jsonify(result)


@app.route("/api/xiaoliuren", methods=["POST"])
@rate_limited("xiaoliuren")
def api_xiaoliuren():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    save = should_save(data)

    result = xiao_liu_ren_full(question, use_lunar=True)

    saved_path = None
    if save:
        saved_path = export_to_obsidian(result, "xiaoliuren")

    result["saved_path"] = saved_path
    attach_ai("小六壬", result, data)
    return jsonify(result)


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/stats")
def api_stats():
    """公开统计：总占卜次数 + 各项目分项次数。供网页人气展示。"""
    return jsonify(get_stats())


@app.route("/api/bazi", methods=["POST"])
@rate_limited("bazi")
def api_bazi():
    """八字排盘"""
    data = request.get_json(silent=True) or {}

    try:
        year = int(data.get("year", 1995))
        month = int(data.get("month", 1))
        day = int(data.get("day", 1))
        hour = int(data.get("hour", 0))
        minute = int(data.get("minute", 0))
        gender = data.get("gender", "男")
        calendar_type = data.get("calendar", "solar")  # solar 或 lunar
        is_leap = bool(data.get("is_leap", False))

        if gender not in ("男", "女"):
            gender = "男"

        # 农历转阳历
        if calendar_type == "lunar":
            try:
                from lunardate import LunarDate
                ld = LunarDate(year, month, day, is_leap)
                solar = ld.toSolarDate()
                birth = datetime.datetime(solar.year, solar.month, solar.day, hour, minute)
            except Exception as e:
                return jsonify({"error": f"农历日期无效：{e}"}), 400
        else:
            birth = datetime.datetime(year, month, day, hour, minute)

        result = full_bazi_chart(birth, gender)
        result["input_calendar"] = calendar_type
        attach_ai("八字排盘", result, data)
        return jsonify(result)
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"日期参数错误：{e}"}), 400


def _parse_birth(prefix: str, data: dict) -> datetime.datetime:
    """从 data 里读出生信息，兼容两种格式：
    1) 展平: prefix_year, prefix_month ...
    2) 嵌套: data[prefix] = {year, month, ...}
    """
    # 优先嵌套
    nested = data.get(prefix)
    if isinstance(nested, dict):
        year = int(nested.get("year", 1995))
        month = int(nested.get("month", 1))
        day = int(nested.get("day", 1))
        hour = int(nested.get("hour", 0))
        minute = int(nested.get("minute", 0))
        cal = nested.get("calendar", "solar")
        is_leap = bool(nested.get("leap", False) or nested.get("is_leap", False))
    else:
        year = int(data.get(f"{prefix}_year", 1995))
        month = int(data.get(f"{prefix}_month", 1))
        day = int(data.get(f"{prefix}_day", 1))
        hour = int(data.get(f"{prefix}_hour", 0))
        minute = int(data.get(f"{prefix}_minute", 0))
        cal = data.get(f"{prefix}_calendar", "solar")
        is_leap = bool(data.get(f"{prefix}_leap", False))

    if cal == "lunar":
        from lunardate import LunarDate
        ld = LunarDate(year, month, day, is_leap)
        solar = ld.toSolarDate()
        return datetime.datetime(solar.year, solar.month, solar.day, hour, minute)
    return datetime.datetime(year, month, day, hour, minute)


@app.route("/api/he_hun", methods=["POST"])
@rate_limited("he_hun")
def api_he_hun():
    """八字合婚"""
    data = request.get_json(silent=True) or {}
    try:
        birth1 = _parse_birth("p1", data)
        gender1 = data.get("p1_gender", "男")
        birth2 = _parse_birth("p2", data)
        gender2 = data.get("p2_gender", "女")

        if gender1 not in ("男", "女"): gender1 = "男"
        if gender2 not in ("男", "女"): gender2 = "女"

        result = he_hun_full(birth1, gender1, birth2, gender2)
        attach_ai("八字合婚", result, data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"合婚计算失败：{e}"}), 400


@app.route("/api/ziwei", methods=["POST"])
@rate_limited("ziwei")
def api_ziwei():
    """紫微斗数排盘"""
    data = request.get_json(silent=True) or {}
    try:
        year = int(data.get("year", 1995))
        month = int(data.get("month", 1))
        day = int(data.get("day", 1))
        hour = int(data.get("hour", 0))
        minute = int(data.get("minute", 0))
        gender = data.get("gender", "男")
        calendar_type = data.get("calendar", "solar")
        is_leap = bool(data.get("is_leap", False))

        if gender not in ("男", "女"):
            gender = "男"

        # 农历转阳历
        if calendar_type == "lunar":
            try:
                from lunardate import LunarDate
                ld = LunarDate(year, month, day, is_leap)
                solar = ld.toSolarDate()
                birth = datetime.datetime(solar.year, solar.month, solar.day, hour, minute)
            except Exception as e:
                return jsonify({"error": f"农历日期无效：{e}"}), 400
        else:
            birth = datetime.datetime(year, month, day, hour, minute)

        result = ziwei_full(birth, gender)
        result["input_calendar"] = calendar_type

        save = should_save(data)
        if save:
            try:
                result["saved_path"] = export_to_obsidian(result, "ziwei")
            except Exception:
                result["saved_path"] = None
        attach_ai("紫微斗数", result, data)
        return jsonify(result)
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"日期参数错误：{e}"}), 400
    except Exception as e:
        return jsonify({"error": f"紫微计算失败：{e}"}), 500


@app.route("/api/meihua", methods=["POST"])
@rate_limited("meihua")
def api_meihua():
    """梅花易数排卦：数字起卦或时间起卦"""
    data = request.get_json(silent=True) or {}
    try:
        question = data.get("question", "").strip()
        use_time = bool(data.get("use_time", False))
        num1 = data.get("num1")
        num2 = data.get("num2")
        if num1 is not None:
            num1 = int(num1)
        if num2 is not None:
            num2 = int(num2)

        result = meihua_full(num1=num1, num2=num2, question=question, use_time=use_time)

        save = should_save(data)
        if save:
            try:
                result["saved_path"] = export_to_obsidian(result, "meihua")
            except Exception:
                result["saved_path"] = None
        attach_ai("梅花易数", result, data)
        return jsonify(result)
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"参数错误：{e}"}), 400
    except Exception as e:
        return jsonify({"error": f"梅花易数计算失败：{e}"}), 500


@app.route("/api/qimen", methods=["POST"])
@rate_limited("qimen")
def api_qimen():
    """奇门遁甲（时家奇门）排盘。默认用当前时间起局。"""
    data = request.get_json(silent=True) or {}
    try:
        question = data.get("question", "").strip()
        # option: 1=拆补 2=置闰，默认置闰
        option = int(data.get("option", 2))
        if option not in (1, 2):
            option = 2

        # 起卦时间：默认当前
        birth = None
        if data.get("year"):
            year = int(data.get("year"))
            month = int(data.get("month", 1))
            day = int(data.get("day", 1))
            hour = int(data.get("hour", 0))
            minute = int(data.get("minute", 0))
            birth = datetime.datetime(year, month, day, hour, minute)

        result = qimen_full(birth=birth, option=option, question=question)

        save = should_save(data)
        if save:
            try:
                result["saved_path"] = export_to_obsidian(result, "qimen")
            except Exception:
                result["saved_path"] = None
        attach_ai("奇门遁甲", result, data)
        return jsonify(result)
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"参数错误：{e}"}), 400
    except Exception as e:
        return jsonify({"error": f"奇门起局失败：{e}"}), 500


@app.route("/api/huangli", methods=["POST"])
@rate_limited("huangli")
def api_huangli():
    """每日黄历查询"""
    data = request.get_json(silent=True) or {}
    try:
        # 默认查今天
        d = data.get("date", "")
        if d:
            try:
                date_obj = datetime.datetime.strptime(d, "%Y-%m-%d")
            except ValueError:
                return jsonify({"error": f"日期格式错误，应为 YYYY-MM-DD"}), 400
        else:
            date_obj = datetime.datetime.now()

        result = huangli_full(date_obj)
        # 默认保存到 Obsidian
        save = should_save(data)
        if save:
            try:
                from core import export_to_obsidian
                result["saved_path"] = export_to_obsidian(result, "huangli")
            except Exception:
                result["saved_path"] = None
        attach_ai("黄历", result, data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"黄历查询失败：{e}"}), 500


@app.route("/api/dream", methods=["POST"])
@rate_limited("dream")
def api_dream():
    """解梦本：双视角解梦（周公传统 + 心理学）"""
    data = request.get_json(silent=True) or {}
    try:
        dream_text = (data.get("dream_text") or "").strip()
        if not dream_text:
            return jsonify({"error": "梦境内容不能为空"}), 400
        if len(dream_text) > 2000:
            return jsonify({"error": "梦境太长（最多 2000 字），分段做"}), 400

        mood = (data.get("mood") or "").strip()[:50]
        context = (data.get("context") or "").strip()[:200]
        dream_date = (data.get("dream_date") or "").strip()

        result = dream_full(dream_text, mood=mood, context=context, dream_date=dream_date)

        save = should_save(data)
        if save:
            try:
                from core import export_to_obsidian
                result["saved_path"] = export_to_obsidian(result, "dream")
            except Exception as e:
                result["saved_path"] = None
                result["save_error"] = str(e)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        import traceback
        return jsonify({
            "error": f"解梦失败：{e}",
            "trace": traceback.format_exc().splitlines()[-3:],
        }), 500


if __name__ == "__main__":
    print(f"\n🔮 占卜系统运行中：http://{FLASK_HOST}:{FLASK_PORT}\n")
    print("📋 功能列表：六爻 | 小六壬 | 八字 | 紫微 | 梅花 | 奇门 | 黄历 | 解梦")
    print("💡 AI 解读功能需要在 config.py 中配置 AI_API_KEY\n")
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=FLASK_DEBUG)
