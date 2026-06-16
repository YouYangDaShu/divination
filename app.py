#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Flask 后端：六爻 + 小六壬（纯排盘版，不含 AI 和 Obsidian 导出）"""

import datetime
import logging
import os
from flask import Flask, render_template, request, jsonify
from flask_compress import Compress
from lunardate import LunarDate  # 提到顶部，避免每次调用重新 import

from core import liuyao_full, xiao_liu_ren_full, export_to_obsidian
from bazi import full_bazi_chart
from he_hun import he_hun_full
from ziwei import ziwei_full
from meihua import meihua_full
from qimen import qimen_full
from huangli import huangli_full
from dream import dream_full
from ratelimit import rate_limited, get_stats, init_db

app = Flask(__name__, static_folder="static", template_folder="templates")
Compress(app)  # gzip 压缩 CSS/JS（CSS 55KB / JS 66KB 公网加载会快很多）
init_db()

# ===== 日志：捕获 traceback 便于排查 =====
logging.basicConfig(
    filename=os.path.join(os.path.dirname(__file__), "divination.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("divine_api")


# ===== 错误响应统一封装 =====
def err(msg, code=400):
    return jsonify({"error": msg}), code


# ===== 农历转公历 =====
def _lunar_to_solar(year, month, day, is_leap, hour, minute):
    """农历转公历，失败返回友好错误"""
    try:
        ld = LunarDate(year, month, day, is_leap)
        solar = ld.toSolarDate()
        return datetime.datetime(solar.year, solar.month, solar.day, hour, minute)
    except ValueError:
        return err("农历日期不存在（如闰月不对或日期超出范围）", 400)
    except Exception:
        log.exception("lunar_to_solar failed")
        return err("农历日期转换失败，请检查输入", 400)


# ===== 日期范围校验 =====
def _validate_birth(year, month, day, hour, minute):
    """校验年月日时分是否在合理范围内。不通过返回 err tuple，通过返回 None。"""
    if not (1900 <= int(year) <= 2100):
        return err("年份超出范围（1900-2100）", 400)
    if not (1 <= int(month) <= 12):
        return err("月份超出范围（1-12）", 400)
    if not (1 <= int(day) <= 31):
        return err("日期超出范围（1-31）", 400)
    if not (0 <= int(hour) <= 23):
        return err("小时超出范围（0-23）", 400)
    if not (0 <= int(minute) <= 59):
        return err("分钟超出范围（0-59）", 400)
    return None


def _should_save(data) -> bool:
    """是否保存到 Obsidian。公网请求一律不保存。"""
    if request.headers.get("X-Forwarded-For"):
        return False
    return bool(data.get("save_obsidian", True))



# ===== 路由 =====
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/liuyao", methods=["POST"])
@rate_limited("liuyao")
def api_liuyao():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    result = liuyao_full(question)
    if _should_save(data):
        try:
            export_to_obsidian(result, "liuyao")
        except Exception:
            log.exception("export_to_obsidian liuyao failed")
    return jsonify(result)


@app.route("/api/xiaoliuren", methods=["POST"])
@rate_limited("xiaoliuren")
def api_xiaoliuren():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    result = xiao_liu_ren_full(question, use_lunar=True)
    if _should_save(data):
        try:
            export_to_obsidian(result, "xiaoliuren")
        except Exception:
            log.exception("export_to_obsidian xiaoliuren failed")
    return jsonify(result)


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
        calendar_type = data.get("calendar", "solar")
        is_leap = bool(data.get("is_leap", False))

        if gender not in ("男", "女"):
            gender = "男"

        v = _validate_birth(year, month, day, hour, minute)
        if v:
            return v

        if calendar_type == "lunar":
            r = _lunar_to_solar(year, month, day, is_leap, hour, minute)
            if isinstance(r, tuple):
                return r  # error response
            birth = r
        else:
            birth = datetime.datetime(year, month, day, hour, minute)

        result = full_bazi_chart(birth, gender)
        result["input_calendar"] = calendar_type
        if _should_save(data):
            try:
                export_to_obsidian(result, "bazi")
            except Exception:
                log.exception("export_to_obsidian bazi failed")
        return jsonify(result)
    except (ValueError, TypeError):
        return err("出生日期参数无效，请检查年月日时分是否填写正确")
    except ImportError as e:
        log.exception("api_bazi missing module")
        return err(f"八字排盘模块缺失：{e.name}", 503)
    except Exception:
        log.exception("api_bazi unexpected error")
        return err("八字排盘异常，请重试", 500)


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

        if gender1 not in ("男", "女"):
            gender1 = "男"
        if gender2 not in ("男", "女"):
            gender2 = "女"

        result = he_hun_full(birth1, gender1, birth2, gender2)
        if _should_save(data):
            try:
                export_to_obsidian(result, "hehun")
            except Exception:
                log.exception("export_to_obsidian hehun failed")
        return jsonify(result)
    except ValueError:
        return err("合婚参数有误，请检查双方出生信息")
    except ImportError as e:
        log.exception("api_he_hun missing module")
        return err(f"合婚模块缺失：{e.name}", 503)
    except Exception:
        log.exception("api_he_hun unexpected error")
        return err("合婚计算异常，请重试", 500)


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

        v = _validate_birth(year, month, day, hour, minute)
        if v:
            return v

        if calendar_type == "lunar":
            r = _lunar_to_solar(year, month, day, is_leap, hour, minute)
            if isinstance(r, tuple):
                return r
            birth = r
        else:
            birth = datetime.datetime(year, month, day, hour, minute)

        result = ziwei_full(birth, gender)
        result["input_calendar"] = calendar_type
        if _should_save(data):
            try:
                export_to_obsidian(result, "ziwei")
            except Exception:
                log.exception("export_to_obsidian ziwei failed")
        return jsonify(result)
    except (ValueError, TypeError):
        return err("出生日期参数无效，请检查年月日时分")
    except ImportError as e:
        log.exception("api_ziwei missing module")
        return err(f"紫微斗数模块缺失：{e.name}，请 pip install py-iztro", 503)
    except Exception:
        log.exception("api_ziwei unexpected error")
        return err("紫微排盘异常，请重试", 500)


@app.route("/api/meihua", methods=["POST"])
@rate_limited("meihua")
def api_meihua():
    """梅花易数排卦"""
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
        if _should_save(data):
            try:
                export_to_obsidian(result, "meihua")
            except Exception:
                log.exception("export_to_obsidian meihua failed")
        return jsonify(result)
    except (ValueError, TypeError):
        return err("参数错误，数字起卦请填两个 1-99 的数字")
    except ImportError as e:
        log.exception("api_meihua missing module")
        return err(f"梅花易数模块缺失：{e.name}", 503)
    except Exception:
        log.exception("api_meihua unexpected error")
        return err("梅花易数计算异常，请重试", 500)


@app.route("/api/qimen", methods=["POST"])
@rate_limited("qimen")
def api_qimen():
    """奇门遁甲排盘"""
    data = request.get_json(silent=True) or {}
    try:
        question = data.get("question", "").strip()
        option = int(data.get("option", 2))
        if option not in (1, 2):
            option = 2

        birth = None
        if data.get("year"):
            year = int(data.get("year"))
            month = int(data.get("month", 1))
            day = int(data.get("day", 1))
            hour = int(data.get("hour", 0))
            minute = int(data.get("minute", 0))
            v = _validate_birth(year, month, day, hour, minute)
            if v:
                return v
            birth = datetime.datetime(year, month, day, hour, minute)

        result = qimen_full(birth=birth, option=option, question=question)
        if _should_save(data):
            try:
                export_to_obsidian(result, "qimen")
            except Exception:
                log.exception("export_to_obsidian qimen failed")
        return jsonify(result)
    except (ValueError, TypeError):
        return err("参数错误，时间参数请检查")
    except RuntimeError as e:
        # 奇门特有的模块依赖缺失错误（kinqimen/ephem）
        log.exception("api_qimen runtime error")
        return err(str(e), 503)
    except ImportError as e:
        log.exception("api_qimen missing module")
        return err(f"奇门遁甲模块缺失：{e.name}，请 pip install kinqimen ephem", 503)
    except Exception:
        log.exception("api_qimen unexpected error")
        return err("奇门起局异常，请重试", 500)


@app.route("/api/huangli", methods=["POST"])
@rate_limited("huangli")
def api_huangli():
    """每日黄历查询"""
    data = request.get_json(silent=True) or {}
    try:
        d = data.get("date", "")
        if d:
            try:
                date_obj = datetime.datetime.strptime(d, "%Y-%m-%d")
            except ValueError:
                return err("日期格式错误，应为 YYYY-MM-DD")
        else:
            date_obj = datetime.datetime.now()

        result = huangli_full(date_obj)
        if _should_save(data):
            try:
                export_to_obsidian(result, "huangli")
            except Exception:
                log.exception("export_to_obsidian huangli failed")
        return jsonify(result)
    except Exception:
        log.exception("api_huangli unexpected error")
        return err("黄历查询异常，请重试", 500)


@app.route("/api/dream", methods=["POST"])
@rate_limited("dream")
def api_dream():
    """解梦（纯排盘版，不含 AI）"""
    data = request.get_json(silent=True) or {}
    try:
        dream_text = (data.get("dream_text") or "").strip()
        if not dream_text:
            return err("梦境内容不能为空")
        if len(dream_text) > 2000:
            return err("梦境太长（最多 2000 字），建议分段解梦")

        mood = (data.get("mood") or "").strip()[:50]
        context = (data.get("context") or "").strip()[:200]
        dream_date = (data.get("dream_date") or "").strip()

        result = dream_full(dream_text, mood=mood, context=context, dream_date=dream_date)
        if _should_save(data):
            try:
                export_to_obsidian(result, "dream")
            except Exception:
                log.exception("export_to_obsidian dream failed")
        return jsonify(result)
    except ValueError:
        return err("解梦参数有误")
    except Exception:
        log.exception("api_dream unexpected error")
        return err("解梦异常，请重试", 500)


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/stats")
def api_stats():
    """公开统计"""
    return jsonify(get_stats())


# ===== 出生信息解析（合婚/通用） =====
def _parse_birth(prefix: str, data: dict):
    """从 data 里读取出生信息，兼容展平和嵌套两种格式"""
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
        r = _lunar_to_solar(year, month, day, is_leap, hour, minute)
        if isinstance(r, tuple):
            raise ValueError("农历日期有误")
        return r
    return datetime.datetime(year, month, day, hour, minute)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5066))
    print(f"\n 玄机阁占卜系统运行中：http://127.0.0.1:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
