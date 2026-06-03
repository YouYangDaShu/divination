#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""占卜系统：Cookie 限流 + 调用量统计（SQLite 单文件，零运维）

- 限流：每设备（浏览器 Cookie）整站合计每天 3 次。只对公网请求生效，本地直连不限。
- 统计：每个接口累计调用数，永久累加，喂给网页人气数字。

线程安全：Flask 默认多线程，SQLite 用 check_same_thread=False + 每次操作短连接。
"""
from __future__ import annotations

import os
import sqlite3
import secrets
import datetime
import threading
from pathlib import Path
from functools import wraps
from flask import request, jsonify, make_response, g

DB_PATH = Path(__file__).parent / "divine_stats.db"
COOKIE_NAME = "divine_dev"
DAILY_LIMIT = int(os.environ.get("DIVINE_DAILY_LIMIT", "3"))
COOKIE_MAX_AGE = 365 * 24 * 3600  # 1 年

# 所有需要限流+统计的算卦接口（中文名用于统计展示）
DIVINE_ENDPOINTS = {
    "liuyao": "六爻",
    "xiaoliuren": "小六壬",
    "bazi": "八字排盘",
    "he_hun": "八字合婚",
    "ziwei": "紫微斗数",
    "meihua": "梅花易数",
    "qimen": "奇门遁甲",
    "huangli": "黄历",
    "dream": "解梦",
}

_init_lock = threading.Lock()
_initialized = False


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")  # 并发读写更稳
    return conn


def init_db() -> None:
    global _initialized
    with _init_lock:
        if _initialized:
            return
        conn = _connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS device_usage (
                    device_id TEXT NOT NULL,
                    day       TEXT NOT NULL,
                    count     INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (device_id, day)
                );
                CREATE TABLE IF NOT EXISTS endpoint_stats (
                    endpoint TEXT PRIMARY KEY,
                    total    INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            conn.commit()
        finally:
            conn.close()
        _initialized = True


def _today() -> str:
    return datetime.date.today().isoformat()


def _is_public_request() -> bool:
    """是否来自公网（经过 Caddy 反代）。本地直连不带 X-Forwarded-For。"""
    return bool(request.headers.get("X-Forwarded-For"))


def _get_or_set_device_id(resp=None) -> str:
    """从 Cookie 取设备 id；没有就生成一个，标记到 g 等响应时种下。"""
    dev = request.cookies.get(COOKIE_NAME)
    if dev and len(dev) >= 16:
        return dev
    # 新设备：生成并标记，由 after_request 种 Cookie
    dev = secrets.token_urlsafe(24)
    g._new_device_id = dev
    return dev


def _get_count(device_id: str) -> int:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT count FROM device_usage WHERE device_id=? AND day=?",
            (device_id, _today()),
        ).fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


def _increment(device_id: str, endpoint: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            """INSERT INTO device_usage (device_id, day, count) VALUES (?, ?, 1)
               ON CONFLICT(device_id, day) DO UPDATE SET count = count + 1""",
            (device_id, _today()),
        )
        conn.execute(
            """INSERT INTO endpoint_stats (endpoint, total) VALUES (?, 1)
               ON CONFLICT(endpoint) DO UPDATE SET total = total + 1""",
            (endpoint,),
        )
        conn.commit()
    finally:
        conn.close()


def get_stats() -> dict:
    """返回 {total, items:[{key,name,count}...]}，供网页人气展示。"""
    init_db()
    conn = _connect()
    try:
        rows = dict(conn.execute("SELECT endpoint, total FROM endpoint_stats").fetchall())
    finally:
        conn.close()
    items = []
    total = 0
    for key, name in DIVINE_ENDPOINTS.items():
        c = int(rows.get(key, 0))
        total += c
        items.append({"key": key, "name": name, "count": c})
    items.sort(key=lambda x: x["count"], reverse=True)
    return {"total": total, "items": items}


def rate_limited(endpoint: str):
    """装饰器：套在算卦路由上。公网请求做 Cookie 限流 + 计数；本地直连只计数不限流。"""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            init_db()
            public = _is_public_request()
            device_id = _get_or_set_device_id()

            if public:
                used = _get_count(device_id)
                if used >= DAILY_LIMIT:
                    resp = make_response(
                        jsonify({
                            "error": "limit_reached",
                            "message": f"今日免费占卜次数已用完（每天 {DAILY_LIMIT} 次），明天再来吧～",
                            "limit": DAILY_LIMIT,
                            "used": used,
                        }),
                        429,
                    )
                    return _attach_cookie(resp)

            # 放行：执行真正的算卦逻辑
            result = fn(*args, **kwargs)
            # 成功才计数（避免参数错误也扣次数）
            status = result[1] if isinstance(result, tuple) else 200
            if status == 200:
                _increment(device_id, endpoint)
            return _attach_cookie(result)
        return wrapper
    return decorator


def _attach_cookie(resp):
    """如果本次是新设备，把 Cookie 种下去。"""
    dev = getattr(g, "_new_device_id", None)
    if not dev:
        return resp
    # resp 可能是 (body, status) 元组或 Response
    if isinstance(resp, tuple):
        body = make_response(*resp)
    else:
        body = make_response(resp)
    body.set_cookie(
        COOKIE_NAME, dev,
        max_age=COOKIE_MAX_AGE,
        httponly=True, samesite="Lax",
    )
    return body
