// 玄机阁 - 占卜网页 JS

let currentMode = "xiaoliuren";
let selectedGender = "男";
let selectedCalendar = "solar";

// 各模式简介：用途 + 适合场景
const MODE_INTRO = {
    xiaoliuren: { p: "民间最简便的随身占卜，掐指一算就出结果。", s: "适合：临时小事、出门前看吉凶、找东西、等人。" },
    liuyao: { p: "三枚铜钱六次掷，传统起卦最详尽，含纳甲六亲世应。", s: "适合：具体之事的具体走向，如求财、问病、官非、迁居。" },
    bazi: { p: "出生年月日时四柱推命，看一生命格基础。", s: "适合：性格分析、事业方向、运势节奏、五行喜忌。" },
    hehun: { p: "双方八字对比，看命理契合度。", s: "适合：恋人/夫妻配对、相亲参考。" },
    ziwei: { p: "紫微斗数排盘，十二宫位主星定格局。", s: "适合：人生格局、十年大限、宫位分析。看更细的人格剖面。" },
    meihua: { p: "宋代邵雍体系，数字/时辰起卦看体用生克。", s: "适合：当下之事的吉凶趋势、事情该不该做。" },
    qimen: { p: "天地人神四盘合一，被称为帝王之术。", s: "适合：决策、布局、择方向、看大局走势。" },
    huangli: { p: "传统通胜每日宜忌、吉时凶时、神煞方位。", s: "适合：选日子、定时辰、查冲煞、看方位。" },
    dream: { p: "周公传统象征 + 心理学原型双视角解梦。", s: "适合：醒来还记得的梦、压在心里的梦、反复做的梦。" },
};

function updateModeIntro(mode) {
    const info = MODE_INTRO[mode];
    if (!info) return;
    const p = document.getElementById("intro-purpose");
    const s = document.getElementById("intro-suit");
    if (p) p.textContent = info.p;
    if (s) s.textContent = info.s;
}
// ============== 初始化 ==============
document.addEventListener("DOMContentLoaded", () => {
    initStars();
    initModeTabs();
    initGenderTabs();
    initCalendarTabs();
    initDatePickers();
    initButtons();
    loadStats();
});

// 加载人气统计数字（公开展示）
async function loadStats() {
    try {
        const res = await fetch("/api/stats");
        if (!res.ok) return;
        const data = await res.json();
        if (handleRateLimit(res, data)) { const _l = document.getElementById("loading"); if (_l) _l.classList.add("hidden"); return; }
        const total = data.total || 0;
        if (total > 0) {
            const el = document.getElementById("statsTotal");
            const banner = document.getElementById("statsBanner");
            if (el) el.textContent = total.toLocaleString("zh-CN");
            if (banner) banner.style.display = "";
        }
    } catch (e) { /* 统计失败不影响主功能 */ }
}

// 统一处理限流响应：是 429 就弹提示并返回 true（调用方应中止后续渲染）
function handleRateLimit(res, data) {
    if (res.status === 429) {
        const msg = (data && data.message) || "今日免费占卜次数已用完，明天再来吧～";
        alert(msg);
        return true;
    }
    return false;
}

// ===== AI 解读：全局注入处境 + 自动渲染（零侵入，不改 8 个渲染函数）=====
// 当前激活输入区里的处境框值
function getActiveContext() {
    // 找当前可见 input-section 内的 .ai-context 文本框
    const sections = document.querySelectorAll(".input-section");
    for (const sec of sections) {
        if (sec.classList.contains("hidden")) continue;
        const box = sec.querySelector(".ai-context");
        if (box && box.value.trim()) return box.value.trim();
    }
    return "";
}

// 包装全局 fetch：给占卜 POST 自动塞 user_context；响应里有 ai_reading 就渲染
(function () {
    const _origFetch = window.fetch.bind(window);
    const DIVINE_APIS = ["/api/liuyao","/api/xiaoliuren","/api/bazi","/api/he_hun",
                         "/api/ziwei","/api/meihua","/api/qimen","/api/huangli"];
    window.fetch = async function (url, opts) {
        opts = opts || {};
        const isDivine = typeof url === "string" && DIVINE_APIS.some(a => url.indexOf(a) >= 0);
        if (isDivine && opts.method === "POST" && opts.body) {
            try {
                const payload = JSON.parse(opts.body);
                const ctx = getActiveContext();
                if (ctx) payload.user_context = ctx;
                opts.body = JSON.stringify(payload);
            } catch (e) { /* 非 JSON body，跳过 */ }
        }
        const res = await _origFetch(url, opts);
        // 占卜成功响应：克隆读出 ai_reading，渲染后追加到结果区
        if (isDivine && res.ok) {
            res.clone().json().then(data => {
                if (data && data.ai_reading) renderAiReading(data.ai_reading);
            }).catch(() => {});
        }
        return res;
    };
})();

// 把 AI 解读渲染成卡片，追加到结果区末尾。
// 轮询等原渲染函数把结果填进去（它们有 sleep+innerHTML 覆盖），再追加，避免被覆盖。
function renderAiReading(text) {
    const safe = String(text)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\n/g, "<br>");
    let tries = 0;
    const timer = setInterval(() => {
        tries++;
        const container = document.getElementById("result-content");
        const hasResult = container && container.children.length > 0;
        // 结果区已有内容（原渲染跑完），或等够 20 次（4 秒）兜底
        if (hasResult || tries > 20) {
            clearInterval(timer);
            if (!container) return;
            if (container.querySelector(".ai-reading-card")) return; // 去重
            const card = document.createElement("div");
            card.className = "result-card ai-reading-card";
            card.innerHTML = `<div class="ai-reading-title">🔮 AI 结合你的处境解读</div>
                <div class="ai-reading-body">${safe}</div>
                <div class="ai-reading-foot">— 仅供娱乐参考，路在自己脚下 —</div>`;
            container.appendChild(card);
            card.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
    }, 200);
}

function initStars() {
    const stars = document.getElementById("stars");
    for (let i = 0; i < 50; i++) {
        const s = document.createElement("div");
        s.className = "star";
        s.style.left = Math.random() * 100 + "%";
        s.style.top = Math.random() * 100 + "%";
        s.style.setProperty("--dur", (Math.random() * 3 + 2) + "s");
        s.style.animationDelay = Math.random() * 3 + "s";
        stars.appendChild(s);
    }
}

function initModeTabs() {
    document.querySelectorAll(".mode-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".mode-tab").forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            currentMode = tab.dataset.mode;

            // 切换输入区
            const inputDivine = document.getElementById("input-divine");
            const inputBazi = document.getElementById("input-bazi");
            const inputHehun = document.getElementById("input-hehun");
            const inputMeihua = document.getElementById("input-meihua");
            const inputQimen = document.getElementById("input-qimen");
            const inputHuangli = document.getElementById("input-huangli");
            const inputDream = document.getElementById("input-dream");

            inputDivine.classList.add("hidden");
            inputBazi.classList.add("hidden");
            inputHehun.classList.add("hidden");
            inputMeihua?.classList.add("hidden");
            inputQimen?.classList.add("hidden");
            inputHuangli?.classList.add("hidden");
            inputDream?.classList.add("hidden");

            if (currentMode === "bazi") {
                inputBazi.classList.remove("hidden");
                _setBaziButton("bazi");
            } else if (currentMode === "ziwei") {
                inputBazi.classList.remove("hidden");
                _setBaziButton("ziwei");
            } else if (currentMode === "hehun") {
                inputHehun.classList.remove("hidden");
            } else if (currentMode === "meihua") {
                inputMeihua?.classList.remove("hidden");
            } else if (currentMode === "qimen") {
                inputQimen?.classList.remove("hidden");
            } else if (currentMode === "huangli") {
                inputHuangli?.classList.remove("hidden");
            } else if (currentMode === "dream") {
                inputDream?.classList.remove("hidden");
            } else {
                inputDivine.classList.remove("hidden");
            }

            // 更新简介
            updateModeIntro(currentMode);

            // 清空结果
            document.getElementById("result-section").classList.add("hidden");
        });
    });
}

function _setBaziButton(mode) {
    const btn = document.getElementById("bazi-btn");
    if (!btn) return;
    if (mode === "ziwei") {
        btn.querySelector(".btn-text").textContent = "排紫微盘";
        btn.querySelector(".btn-icon").textContent = "";
        btn.dataset.mode = "ziwei";
    } else {
        btn.querySelector(".btn-text").textContent = "排 盘";
        btn.querySelector(".btn-icon").textContent = "";
        btn.dataset.mode = "bazi";
    }
}

function initGenderTabs() {
    // 八字单人性别（在 .gender-tabs 但不在 .hehun-gender 内）
    document.querySelectorAll(".input-card .gender-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            // 只切换同一容器内的按钮
            const container = tab.closest(".gender-tabs");
            if (!container) return;
            container.querySelectorAll(".gender-tab").forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
        });
    });

    // cal-tab 同样
    document.querySelectorAll(".input-card .cal-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            const container = tab.closest(".gender-tabs");
            if (!container) return;
            container.querySelectorAll(".cal-tab").forEach(t => t.classList.remove("active"));
            tab.classList.add("active");

            // 闰月显示控制（hehun 用 person-specific id）
            const person = container.dataset.person;
            const isLunar = tab.dataset.cal === "lunar";
            if (person === "p1") {
                document.getElementById("p1-leap-wrap")?.classList.toggle("hidden", !isLunar);
            } else if (person === "p2") {
                document.getElementById("p2-leap-wrap")?.classList.toggle("hidden", !isLunar);
            } else {
                // 八字主体
                document.getElementById("leap-wrap")?.classList.toggle("hidden", !isLunar);
            }

            // 同时刷新对应日期下拉的天数
            if (typeof updateDayOptions === "function") {
                if (person) {
                    updateHehunDayOptions(person);
                } else {
                    updateDayOptions();
                }
            }
        });
    });
}

function initCalendarTabs() {
    // 已合并到 initGenderTabs，保留为空兼容旧调用
}

function initDatePickers() {
    const yearSel = document.getElementById("birth-year");
    const monthSel = document.getElementById("birth-month");
    const daySel = document.getElementById("birth-day");
    const hourSel = document.getElementById("birth-hour");
    const minuteSel = document.getElementById("birth-minute");

    const currentYear = new Date().getFullYear();

    // 年份：当前年到1900，倒序
    yearSel.innerHTML = "";
    for (let y = currentYear; y >= 1900; y--) {
        const opt = document.createElement("option");
        opt.value = y;
        opt.textContent = y + "年";
        yearSel.appendChild(opt);
    }
    yearSel.value = "1995";

    // 月份 1-12
    monthSel.innerHTML = "";
    for (let m = 1; m <= 12; m++) {
        const opt = document.createElement("option");
        opt.value = m;
        opt.textContent = m + "月";
        monthSel.appendChild(opt);
    }
    monthSel.value = "6";

    // 日：根据年月动态
    updateDayOptions();
    daySel.value = "15";

    // 时 0-23
    hourSel.innerHTML = "";
    const shichenLabels = {
        0: "(子时)", 1: "(丑时)", 2: "(丑时)", 3: "(寅时)", 4: "(寅时)",
        5: "(卯时)", 6: "(卯时)", 7: "(辰时)", 8: "(辰时)", 9: "(巳时)",
        10: "(巳时)", 11: "(午时)", 12: "(午时)", 13: "(未时)", 14: "(未时)",
        15: "(申时)", 16: "(申时)", 17: "(酉时)", 18: "(酉时)", 19: "(戌时)",
        20: "(戌时)", 21: "(亥时)", 22: "(亥时)", 23: "(子时)",
    };
    for (let h = 0; h < 24; h++) {
        const opt = document.createElement("option");
        opt.value = h;
        opt.textContent = String(h).padStart(2, "0") + "时 " + shichenLabels[h];
        hourSel.appendChild(opt);
    }
    hourSel.value = "14";

    // 分 0-59
    minuteSel.innerHTML = "";
    for (let m = 0; m < 60; m++) {
        const opt = document.createElement("option");
        opt.value = m;
        opt.textContent = String(m).padStart(2, "0") + "分";
        minuteSel.appendChild(opt);
    }
    minuteSel.value = "30";

    // 年月变化时重新算日数
    yearSel.addEventListener("change", updateDayOptions);
    monthSel.addEventListener("change", updateDayOptions);
}

function updateDayOptions() {
    const yearSel = document.getElementById("birth-year");
    const monthSel = document.getElementById("birth-month");
    const daySel = document.getElementById("birth-day");
    const oldDay = parseInt(daySel.value || "1");

    const year = parseInt(yearSel.value);
    const month = parseInt(monthSel.value);

    let maxDay;
    if (selectedCalendar === "lunar") {
        // 农历最多30天
        maxDay = 30;
    } else {
        // 阳历按月份算
        maxDay = new Date(year, month, 0).getDate();
    }

    daySel.innerHTML = "";
    for (let d = 1; d <= maxDay; d++) {
        const opt = document.createElement("option");
        opt.value = d;
        opt.textContent = d + "日";
        daySel.appendChild(opt);
    }
    daySel.value = Math.min(oldDay, maxDay);
}

function initButtons() {
    document.getElementById("divine-btn").addEventListener("click", divine);
    document.getElementById("bazi-btn").addEventListener("click", () => {
        const mode = document.getElementById("bazi-btn").dataset.mode || "bazi";
        if (mode === "ziwei") {
            divineZiwei();
        } else {
            divineBazi();
        }
    });
    document.getElementById("hehun-btn")?.addEventListener("click", divineHehun);
    document.getElementById("question").addEventListener("keypress", e => {
        if (e.key === "Enter") divine();
    });

    // 梅花起卦按钮
    document.getElementById("meihua-btn")?.addEventListener("click", divineMeihua);
    // 梅花起卦方式切换
    document.querySelectorAll(".meihua-mode-tab").forEach(t => {
        t.addEventListener("click", () => {
            document.querySelectorAll(".meihua-mode-tab").forEach(x => x.classList.remove("active"));
            t.classList.add("active");
            const isNum = t.dataset.mhmode === "num";
            document.getElementById("meihua-num-inputs").classList.toggle("hidden", !isNum);
        });
    });

    // 奇门起局按钮
    document.getElementById("qimen-btn")?.addEventListener("click", divineQimen);
    // 奇门起局方法切换
    document.querySelectorAll(".qimen-opt-tab").forEach(t => {
        t.addEventListener("click", () => {
            document.querySelectorAll(".qimen-opt-tab").forEach(x => x.classList.remove("active"));
            t.classList.add("active");
        });
    });

    // 黄历查询按钮
    document.getElementById("huangli-btn")?.addEventListener("click", divineHuangli);

    // 解梦按钮
    document.getElementById("dream-btn")?.addEventListener("click", interpretDream);

    // 初始化合婚 select
    initHehunSelects();

    // 初始化模式简介
    updateModeIntro(currentMode);
}

// ============== 起卦（小六壬/六爻） ==============
async function divine() {
    const question = document.getElementById("question").value.trim();
    const saveObsidian = true;

    const resultSection = document.getElementById("result-section");
    const loading = document.getElementById("loading");
    const content = document.getElementById("result-content");
    const coinToss = document.getElementById("coin-toss");
    const spinner = document.getElementById("spinner");
    const loadingText = document.getElementById("loading-text");

    resultSection.classList.remove("hidden");
    loading.classList.remove("hidden");
    content.innerHTML = "";

    // 六爻显示铜钱动画，小六壬显示太极
    if (currentMode === "liuyao") {
        coinToss.classList.remove("hidden");
        spinner.classList.add("hidden");
        loadingText.textContent = "铜钱起卦，天机推演...";
        coinToss.classList.add("tossing");
        await sleep(1600);
        coinToss.classList.remove("tossing");
    } else {
        coinToss.classList.add("hidden");
        spinner.classList.remove("hidden");
        loadingText.textContent = "天机推演中...";
        await sleep(1200);
    }

    try {
        const endpoint = currentMode === "liuyao" ? "/api/liuyao" : "/api/xiaoliuren";
        const res = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question, save_obsidian: saveObsidian }),
        });
        const data = await res.json();
        if (handleRateLimit(res, data)) { const _l = document.getElementById("loading"); if (_l) _l.classList.add("hidden"); return; }

        loading.classList.add("hidden");
        coinToss.classList.add("hidden");
        spinner.classList.remove("hidden");

        if (currentMode === "liuyao") {
            content.innerHTML = renderLiuyao(data);
        } else {
            content.innerHTML = renderXiaoLiuRen(data);
        }
        resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
        loading.classList.add("hidden");
        content.innerHTML = `<div class="result-card" style="color: #ff6b6b;">起卦失败：${err.message}</div>`;
    }
}

// ============== 八字排盘 ==============
async function divineBazi() {
    const year = parseInt(document.getElementById("birth-year").value);
    const month = parseInt(document.getElementById("birth-month").value);
    const day = parseInt(document.getElementById("birth-day").value);
    const hour = parseInt(document.getElementById("birth-hour").value);
    const minute = parseInt(document.getElementById("birth-minute").value);
    const isLeap = document.getElementById("leap-month").checked;

    const resultSection = document.getElementById("result-section");
    const loading = document.getElementById("loading");
    const content = document.getElementById("result-content");
    const coinToss = document.getElementById("coin-toss");
    const spinner = document.getElementById("spinner");
    const loadingText = document.getElementById("loading-text");

    resultSection.classList.remove("hidden");
    loading.classList.remove("hidden");
    content.innerHTML = "";
    coinToss.classList.add("hidden");
    spinner.classList.remove("hidden");
    loadingText.textContent = "推算四柱八字...";

    await sleep(1000);

    try {
        const res = await fetch("/api/bazi", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                year, month, day, hour, minute,
                gender: selectedGender,
                calendar: selectedCalendar,
                is_leap: isLeap,
            }),
        });
        const data = await res.json();
        if (handleRateLimit(res, data)) { const _l = document.getElementById("loading"); if (_l) _l.classList.add("hidden"); return; }

        loading.classList.add("hidden");

        if (data.error) {
            content.innerHTML = `<div class="result-card" style="color: #ff6b6b;">${data.error}</div>`;
            return;
        }

        content.innerHTML = renderBazi(data);

        // 八字记录只保存时间，不保存任何敏感信息
        // 触发五行进度条动画
        setTimeout(() => {
            document.querySelectorAll(".wuxing-bar-fill").forEach(b => {
                b.style.width = b.dataset.width;
            });
        }, 100);

        resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
        loading.classList.add("hidden");
        content.innerHTML = `<div class="result-card" style="color: #ff6b6b;">排盘失败：${err.message}</div>`;
    }
}

// ============== 紫微斗数 ==============
async function divineZiwei() {
    const year = parseInt(document.getElementById("birth-year").value);
    const month = parseInt(document.getElementById("birth-month").value);
    const day = parseInt(document.getElementById("birth-day").value);
    const hour = parseInt(document.getElementById("birth-hour").value);
    const minute = parseInt(document.getElementById("birth-minute").value);
    const isLeap = document.getElementById("leap-month").checked;

    const resultSection = document.getElementById("result-section");
    const loading = document.getElementById("loading");
    const content = document.getElementById("result-content");
    const coinToss = document.getElementById("coin-toss");
    const spinner = document.getElementById("spinner");
    const loadingText = document.getElementById("loading-text");

    resultSection.classList.remove("hidden");
    loading.classList.remove("hidden");
    content.innerHTML = "";
    coinToss.classList.add("hidden");
    spinner.classList.remove("hidden");
    loadingText.textContent = "推演紫微星盘...";

    await sleep(1000);

    try {
        const res = await fetch("/api/ziwei", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                year, month, day, hour, minute,
                gender: selectedGender,
                calendar: selectedCalendar,
                is_leap: isLeap,
            }),
        });
        const data = await res.json();
        if (handleRateLimit(res, data)) { const _l = document.getElementById("loading"); if (_l) _l.classList.add("hidden"); return; }

        loading.classList.add("hidden");

        if (data.error) {
            content.innerHTML = `<div class="result-card" style="color: #ff6b6b;">${data.error}</div>`;
            return;
        }

        content.innerHTML = renderZiwei(data);
        resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
        loading.classList.add("hidden");
        content.innerHTML = `<div class="result-card" style="color: #ff6b6b;">排盘失败：${err.message}</div>`;
    }
}

// ============== 渲染：紫微命盘 ==============
function renderZiwei(d) {
    const b = d.basic || {};
    const palaces = d.palaces || [];

    // 头部信息
    const head = `
        <div class="result-card ziwei-head">
            <h2 class="ziwei-title"> 紫微斗数命盘</h2>
            <div class="ziwei-meta-grid">
                <div><span class="zw-k">阳历</span> ${b.solar_date || ""} ${b.time_range || ""}</div>
                <div><span class="zw-k">农历</span> ${b.lunar_date || ""}</div>
                <div><span class="zw-k">八字</span> ${b.chinese_date || ""}</div>
                <div><span class="zw-k">星座 / 生肖</span> ${b.sign || ""} · 属${b.zodiac || ""}</div>
                <div><span class="zw-k">命主 / 身主</span> ${b.soul_master || ""} / ${b.body_master || ""}</div>
                <div><span class="zw-k">五行局</span> ${b.five_elements || ""}</div>
                <div><span class="zw-k">命宫地支</span> ${b.soul_branch || ""}</div>
                <div><span class="zw-k">身宫地支</span> ${b.body_branch || ""}</div>
            </div>
            ${d.current_age != null && d.current_decadal_palace ? `
                <div class="ziwei-current-decadal">
                     当前虚岁 <strong>${d.current_age}</strong>，所行大限：
                    <strong>${d.current_decadal_palace}宫</strong>
                    （${d.current_decadal_range ? d.current_decadal_range[0] + "-" + d.current_decadal_range[1] + "岁" : ""}）
                </div>
            ` : ""}
        </div>
    `;

    // 12 宫位 grid
    const palaceCards = palaces.map(p => {
        const flags = [];
        if (p.is_original_palace) flags.push('<span class="zw-flag zw-flag-life">命宫</span>');
        if (p.is_body_palace) flags.push('<span class="zw-flag zw-flag-body">身宫</span>');
        const isCurrent = (p.name === d.current_decadal_palace);
        if (isCurrent) flags.push('<span class="zw-flag zw-flag-current">当前大限</span>');

        const decRng = (p.decadal && p.decadal.range && p.decadal.range.length === 2)
            ? `${p.decadal.range[0]}-${p.decadal.range[1]}岁` : "";

        const majors = (p.major_stars || []).map(s =>
            `<span class="zw-star zw-star-major">${s}</span>`).join("");
        const minors = (p.minor_stars || []).map(s =>
            `<span class="zw-star zw-star-minor">${s}</span>`).join("");
        const adjs = (p.adjective_stars || []).slice(0, 6).map(s =>
            `<span class="zw-star zw-star-adj">${s}</span>`).join("");

        return `
            <div class="ziwei-palace ${isCurrent ? 'is-current' : ''}">
                <div class="zw-pal-head">
                    <span class="zw-pal-name">${p.name}</span>
                    <span class="zw-pal-stem">${p.stem || ""}${p.branch || ""}</span>
                </div>
                ${flags.length ? `<div class="zw-pal-flags">${flags.join("")}</div>` : ""}
                ${decRng ? `<div class="zw-pal-decadal">大限 ${decRng}</div>` : ""}
                ${majors ? `<div class="zw-pal-stars-row">${majors}</div>` : ""}
                ${minors ? `<div class="zw-pal-stars-row">${minors}</div>` : ""}
                ${adjs ? `<div class="zw-pal-stars-row zw-pal-adj-row">${adjs}</div>` : ""}
            </div>
        `;
    }).join("");

    return `
        ${head}
        <div class="ziwei-palaces-grid">${palaceCards}</div>
        <div class="result-card ziwei-tip">
            <p> 紫微斗数共 12 宫位，主星亮度（庙/旺/得/利/平/不/陷）反映星曜在该宫的能量强弱。</p>
            <p> 看命盘核心顺序：<strong>命宫 → 身宫 → 当前大限宫 → 三方四正</strong>。</p>
            <p> 想要进一步解盘？把这个页面的截图或本次命盘 ID 给我，我用文字给你讲透。</p>
        </div>
    `;
}

// ============== 渲染：神煞 ==============
function renderShenSha(list) {
    if (!list || list.length === 0) {
        return `<h3 class="section-title">神煞</h3>
                <div class="summary-text" style="color: var(--text-secondary);">本命无明显神煞</div>`;
    }

    const tagsHTML = list.map(s => {
        // 区分吉凶
        const goodOnes = ["天乙贵人", "文昌", "将星", "红鸾", "天喜", "驿马"];
        const isGood = goodOnes.includes(s.name);
        const cls = isGood ? "shen-sha-good" : "shen-sha-neutral";
        return `
            <div class="shen-sha-card ${cls}">
                <div class="shen-sha-name"> ${s.name}</div>
                <div class="shen-sha-pos">${s.position} · ${s.zhi}</div>
                <div class="shen-sha-meaning">${s.meaning}</div>
            </div>
        `;
    }).join("");

    return `
        <h3 class="section-title">神煞</h3>
        <div class="shen-sha-grid">${tagsHTML}</div>
    `;
}

// ============== 渲染：合冲刑害 ==============
function renderHeChong(hc) {
    if (!hc) return "";

    const items = [];

    if (hc.san_he && hc.san_he.length > 0) {
        hc.san_he.forEach(x => items.push({
            type: "三合", color: "good",
            text: `<strong>${x.combo}</strong> · ${x.name}`, desc: x.desc,
        }));
    }
    if (hc.san_hui && hc.san_hui.length > 0) {
        hc.san_hui.forEach(x => items.push({
            type: "三会", color: "good",
            text: `<strong>${x.combo}</strong> · ${x.name}`, desc: x.desc,
        }));
    }
    if (hc.he && hc.he.length > 0) {
        hc.he.forEach(x => items.push({
            type: "六合", color: "good",
            text: `<strong>${x.pair}</strong> · ${x.type}`, desc: x.desc,
        }));
    }
    if (hc.chong && hc.chong.length > 0) {
        hc.chong.forEach(x => items.push({
            type: "六冲", color: "bad",
            text: `<strong>${x.pair}</strong>`, desc: x.desc,
        }));
    }
    if (hc.hai && hc.hai.length > 0) {
        hc.hai.forEach(x => items.push({
            type: "六害", color: "bad",
            text: `<strong>${x.pair}</strong>`, desc: x.desc,
        }));
    }
    if (hc.xing && hc.xing.length > 0) {
        hc.xing.forEach(x => items.push({
            type: "刑", color: "bad",
            text: `<strong>${x.pair}</strong> · ${x.type}`, desc: x.desc,
        }));
    }

    if (items.length === 0) {
        return `<h3 class="section-title">合冲刑害</h3>
                <div class="summary-text" style="color: var(--jade);">命局平和，无明显合冲刑害</div>`;
    }

    const itemsHTML = items.map(x => `
        <div class="hc-item hc-${x.color}">
            <span class="hc-tag">${x.type}</span>
            <span class="hc-text">${x.text}</span>
            <span class="hc-desc">${x.desc}</span>
        </div>
    `).join("");

    return `
        <h3 class="section-title">合冲刑害</h3>
        <div class="hc-list">${itemsHTML}</div>
    `;
}

// ============== 渲染：八字 ==============
function renderBazi(d) {
    const pillarsHTML = d.columns.map(c => `
        <div class="pillar ${c.label === '日柱' ? 'is-day' : ''} ${c.is_kong ? 'is-kong' : ''}">
            <div class="pillar-label">${c.label}${c.is_kong ? '<span class="kong-tag">空</span>' : ''}</div>
            <div class="pillar-shi-shen">${c.shi_shen_gan}</div>
            <div class="pillar-gan wx-${c.gan_wuxing}">${c.gan}</div>
            <div class="pillar-zhi wx-${c.zhi_wuxing}">${c.zhi}</div>
            <div class="pillar-cang-gan">
                ${c.cang_gan.map(cg => `<span class="wx-${cg.wuxing}">${cg.gan}</span><sub>${cg.shi_shen.charAt(0)}</sub>`).join(" ")}
            </div>
            <div class="pillar-chang-sheng">${c.chang_sheng}</div>
            <div class="pillar-na-yin">${c.na_yin}</div>
        </div>
    `).join("");

    const wxBars = ["金", "木", "水", "火", "土"].map(wx => {
        const pct = d.wuxing_percent[wx];
        const cnt = d.wuxing_counts[wx];
        const color = d.wuxing_color[wx];
        return `
            <div class="wuxing-bar">
                <div class="wuxing-bar-label wx-${wx}">${wx}</div>
                <div class="wuxing-bar-track">
                    <div class="wuxing-bar-fill" style="width: 0%; background: ${color};" data-width="${pct}%">
                        ${cnt}个 (${pct}%)
                    </div>
                </div>
            </div>
        `;
    }).join("");

    let missingHTML = "";
    if (d.missing.length > 0) {
        missingHTML = `<span class="wuxing-tag warning"> 缺：${d.missing.join("、")}</span>`;
    }

    // 喜用神卡片
    const xy = d.xi_yong;
    const yongTags = (xy.yong_shen || []).map(w => `<span class="wx-tag wx-${w}">${w}</span>`).join("");
    const jiTags = (xy.ji_shen || []).map(w => `<span class="wx-tag wx-${w} ji">${w}</span>`).join("");
    const xiYongHTML = `
        <h3 class="section-title">喜用神</h3>
        <div class="xi-yong-card">
            <div class="xi-yong-row">
                <span class="xi-yong-label">命局</span>
                <span class="xi-yong-value">${xy.type}</span>
            </div>
            <div class="xi-yong-row">
                <span class="xi-yong-label">喜用</span>
                <span class="xi-yong-tags">${yongTags || '<em>看格局</em>'} <span class="xi-yong-text">（${xy.yong_label}）</span></span>
            </div>
            ${jiTags ? `
            <div class="xi-yong-row">
                <span class="xi-yong-label">忌神</span>
                <span class="xi-yong-tags">${jiTags} <span class="xi-yong-text">（${xy.ji_label}）</span></span>
            </div>
            ` : ''}
            <div class="xi-yong-advice">${xy.advice}</div>
        </div>
    `;

    // 胎元 / 命宫 / 旬空 / 起运
    const qy = d.qi_yun;
    const extraInfoHTML = `
        <h3 class="section-title">胎元 · 命宫 · 旬空 · 起运</h3>
        <div class="extra-info-grid">
            <div class="extra-info-card">
                <div class="extra-info-label">胎元</div>
                <div class="extra-info-value">${d.tai_yuan.ganzhi}</div>
                <div class="extra-info-sub">${d.tai_yuan.na_yin}</div>
            </div>
            <div class="extra-info-card">
                <div class="extra-info-label">命宫</div>
                <div class="extra-info-value">${d.ming_gong}</div>
                <div class="extra-info-sub">命宫地支</div>
            </div>
            <div class="extra-info-card">
                <div class="extra-info-label">旬空</div>
                <div class="extra-info-value">${(d.kong_wang || []).join('、')}</div>
                <div class="extra-info-sub">六甲空亡</div>
            </div>
            <div class="extra-info-card">
                <div class="extra-info-label">起运</div>
                <div class="extra-info-value">${qy.start_age}岁${qy.start_months ? qy.start_months+'月' : ''}</div>
                <div class="extra-info-sub">${qy.direction}排 · ${qy.ref_node !== '?' ? '至'+qy.ref_node : ''} ${qy.method.includes('精算') ? '[选]' : '约'}</div>
            </div>
        </div>
    `;

    let currentDaYunHTML = "";
    if (d.current_da_yun) {
        const dy = d.current_da_yun;
        currentDaYunHTML = `
            <div class="current-yun-card">
                <div class="current-yun-title">当前大运 · ${dy.age_start}-${dy.age_end}岁</div>
                <div class="current-yun-ganzhi">${dy.ganzhi}</div>
                <div class="current-yun-meta">十神：${dy.shi_shen} · 五行：${dy.wuxing} · 长生：${dy.chang_sheng} · 纳音：${dy.na_yin}</div>
            </div>
        `;
    }

    const ln = d.current_liu_nian;
    const currentLiuNianHTML = `
        <div class="current-yun-card">
            <div class="current-yun-title">${ln.year}年流年</div>
            <div class="current-yun-ganzhi">${ln.ganzhi}</div>
            <div class="current-yun-meta">十神：${ln.shi_shen} · 长生：${ln.chang_sheng}</div>
            <div class="current-yun-text">${d.current_yun_shi}</div>
        </div>
    `;

    // 大运表（加纳音列）
    const dayunRows = d.da_yun.map(dy => {
        const isCurrent = (dy.age_start <= d.current_age && d.current_age <= dy.age_end);
        return `
            <div class="yun-row yun-row-6 ${isCurrent ? 'is-current' : ''}">
                <div class="yun-cell yun-age">${dy.age_start}-${dy.age_end}岁</div>
                <div class="yun-cell"><span class="yun-ganzhi">${dy.ganzhi}</span></div>
                <div class="yun-cell yun-shi-shen">${dy.shi_shen}</div>
                <div class="yun-cell">${dy.wuxing}</div>
                <div class="yun-cell yun-chang-sheng">${dy.chang_sheng}</div>
                <div class="yun-cell yun-na-yin">${dy.na_yin}</div>
            </div>
        `;
    }).join("");

    // 流年表（最近5年）
    const liuNianRows = d.liu_nian.map((ln, i) => `
        <div class="yun-row ${i === 0 ? 'is-current' : ''}">
            <div class="yun-cell yun-age">${ln.year}年</div>
            <div class="yun-cell"><span class="yun-ganzhi">${ln.ganzhi}</span></div>
            <div class="yun-cell yun-shi-shen">${ln.shi_shen}</div>
            <div class="yun-cell">${ln.wuxing}</div>
            <div class="yun-cell yun-chang-sheng">${ln.chang_sheng}</div>
        </div>
    `).join("");

    return `
        <div class="result-card">
            <div class="result-header">
                <div class="result-gua-name">八 字 排 盘</div>
                <div class="result-meta">
                    <span>${d.gender}</span>·<span>${d.lunar_str}</span>·<span>当前 ${d.current_age} 岁</span>
                </div>
            </div>

            <h3 class="section-title">四柱（含纳音）</h3>
            <div class="bazi-pillars">${pillarsHTML}</div>

            <h3 class="section-title">日主与命局</h3>
            <div class="summary-text">
                日主 <strong class="wx-${d.day_wuxing}" style="font-size: 1.2em;">${d.day_gan}（${d.day_wuxing}）</strong> ·
                <strong style="color: var(--gold-bright);">${d.strength.strength}</strong>
                （得分 ${d.strength.score}）
                <br><br>
                <span style="color: var(--text-secondary);">${d.strength.advice}</span>
            </div>

            <h3 class="section-title">五行分布</h3>
            <div class="wuxing-bars">${wxBars}</div>
            <div class="wuxing-summary">
                <span class="wuxing-tag">最旺：<strong class="wx-${d.strongest}">${d.strongest}</strong></span>
                <span class="wuxing-tag">最弱：<strong class="wx-${d.weakest}">${d.weakest}</strong></span>
                ${missingHTML}
            </div>

            ${xiYongHTML}
            ${extraInfoHTML}

            ${currentDaYunHTML}
            ${currentLiuNianHTML}

            ${renderShenSha(d.shen_sha)}
            ${renderHeChong(d.he_chong)}

            <h3 class="section-title">八步大运</h3>
            <div class="yun-table">
                <div class="yun-row yun-row-6 header">
                    <div>年龄</div><div>干支</div><div>十神</div><div>五行</div><div>长生</div><div>纳音</div>
                </div>
                ${dayunRows}
            </div>

            <h3 class="section-title">未来五年流年</h3>
            <div class="yun-table">
                <div class="yun-row header">
                    <div>年份</div><div>干支</div><div>十神</div><div>五行</div><div>长生</div>
                </div>
                ${liuNianRows}
            </div>

            <div class="bian-gua-tip" style="margin-top: 24px;">
                 <strong>说明</strong>：四柱八字基于公历转农历计算。强弱、十神、大运、纳音、旬空、胎元命宫、喜用神为标准算法；起运岁数按节气精算（3天1年）。神煞合冲为传统断法参考，复杂格局需综合判断。
            </div>
        </div>
    `;
}

// ============== 渲染：小六壬 ==============
function renderXiaoLiuRen(data) {
    const r = data.result;
    const time = formatTime(data.datetime);

    let savedHTML = "";
    if (data.saved_path) {
        savedHTML = `<div class="saved-toast"> 已保存到 Obsidian：${data.saved_path.split('/').pop()}</div>`;
    }

    return `
        <div class="result-card">
            <div class="result-header">
                <div class="result-gua-name">${r.color} 《${r.name}》</div>
                <div class="result-meta">
                    <span>${r.element}</span>·<span>${time}</span>·<span>${data.lunar_str}</span>·<span>${data.shichen}时</span>
                </div>
                <div class="result-level level-${r.level}">${r.level}</div>
            </div>

            ${data.question ? `
                <h3 class="section-title">所问之事</h3>
                <p class="summary-text">${escapeHtml(data.question)}</p>
            ` : ""}

            <h3 class="section-title">起卦过程</h3>
            <div class="process-list">
                ${data.process.map(p => `
                    <div class="process-item">
                        <span class="process-step">${p.step}</span>
                        <span class="process-desc">${p.desc}</span>
                        <span class="process-result">${p.result}</span>
                    </div>
                `).join("")}
            </div>

            <h3 class="section-title">卦辞</h3>
            <div class="gua-judgment">${r.judgment}</div>

            <h3 class="section-title">白话解读</h3>
            <div class="summary-text">${r.summary}</div>

            <h3 class="section-title">各事项分析</h3>
            <div class="analysis-grid">
                <div class="analysis-item">
                    <span class="analysis-label"> 感情</span>
                    <span class="analysis-value">${r.love}</span>
                </div>
                <div class="analysis-item">
                    <span class="analysis-label"> 事业</span>
                    <span class="analysis-value">${r.career}</span>
                </div>
                <div class="analysis-item">
                    <span class="analysis-label"> 财运</span>
                    <span class="analysis-value">${r.wealth}</span>
                </div>
                <div class="analysis-item">
                    <span class="analysis-label"> 健康</span>
                    <span class="analysis-value">${r.health}</span>
                </div>
            </div>

            <h3 class="section-title">宜</h3>
            <div class="tags">
                ${r.good_for.map(t => `<span class="tag">${t}</span>`).join("")}
            </div>

            ${savedHTML}
        </div>
    `;
}

// ============== 渲染：六爻 ==============
function renderLiuyao(data) {
    const bg = data.ben_gua;
    const time = formatTime(data.datetime);

    let savedHTML = "";
    if (data.saved_path) {
        savedHTML = `<div class="saved-toast"> 已保存到 Obsidian：${data.saved_path.split('/').pop()}</div>`;
    }

    const yaoRows = [...data.yao_details].reverse().map(y => {
        const cls = [
            "yao-row",
            y.marker === "世" ? "is-shi" : "",
            y.marker === "应" ? "is-ying" : "",
            y.is_changing ? "is-changing" : "",
        ].filter(Boolean).join(" ");
        return `
            <div class="${cls}">
                <span class="yao-pos">${y.name}</span>
                <span class="yao-symbol">${y.symbol}</span>
                <span class="yao-dizhi">${y.dizhi}</span>
                <span class="yao-liuqin">${y.liuqin}</span>
                <span class="yao-marker">${y.marker || ""}</span>
                <span class="yao-changing">${y.is_changing ? "动" : ""}</span>
            </div>
        `;
    }).join("");

    let bianHTML = "";
    if (data.has_change && data.bian_gua) {
        const bi = data.bian_gua;
        bianHTML = `
            <div class="bian-gua-section">
                <h3 class="section-title">变卦</h3>
                <div class="gua-symbol-container">
                    <div class="gua-name-big">《${bi.name}》</div>
                    <div class="gua-info">${bi.gong}宫</div>
                </div>
                <div class="gua-judgment">${bi.judgment || "无卦辞"}</div>
                <div class="summary-text">${bi.meaning}</div>
                <div class="bian-gua-tip">
                     变爻：第 ${bi.change_yaos.join("、")} 爻 — 本卦为现状，变卦为结果，变爻为关键转折
                </div>
            </div>
        `;
    } else {
        bianHTML = `<div class="bian-gua-tip" style="margin-top: 24px;">无变爻 · 事态稳定，按本卦判断</div>`;
    }

    return `
        <div class="result-card">
            <div class="result-header">
                <div class="result-gua-name">《${bg.name}》</div>
                <div class="result-meta">
                    <span>${bg.gong}宫</span>·<span>${bg.gua_class}</span>·<span>${time}</span>
                </div>
            </div>

            ${data.question ? `
                <h3 class="section-title">所问之事</h3>
                <p class="summary-text">${escapeHtml(data.question)}</p>
            ` : ""}

            <h3 class="section-title">本卦</h3>
            <div class="gua-symbol-container">
                <div class="gua-name-big">${bg.name}</div>
                <div class="gua-info">
                    上卦 ${bg.upper[2]} ${bg.upper[0]}(${bg.upper[1]}) · 下卦 ${bg.lower[2]} ${bg.lower[0]}(${bg.lower[1]})
                </div>
                <div class="yao-stack">${yaoRows}</div>
            </div>

            <div class="gua-detail-list">
                <div class="gua-detail-item">
                    <span class="gua-detail-label">卦辞</span>${bg.judgment}
                </div>
                <div class="gua-detail-item">
                    <span class="gua-detail-label">本宫</span>${bg.gong}宫 (${bg.gong_wuxing})
                </div>
                <div class="gua-detail-item">
                    <span class="gua-detail-label">世爻</span>第 ${bg.shi_pos} 爻
                </div>
                <div class="gua-detail-item">
                    <span class="gua-detail-label">应爻</span>第 ${bg.ying_pos} 爻
                </div>
            </div>

            <h3 class="section-title">释义</h3>
            <div class="summary-text">${bg.meaning}</div>

            ${bianHTML}

            ${savedHTML}
        </div>
    `;
}

// ============== 历史记录 ==============




// ============== 工具 ==============
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function formatTime(iso, compact = false) {
    const d = new Date(iso);
    const pad = n => String(n).padStart(2, "0");
    if (compact) {
        return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    }
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function escapeHtml(s) {
    if (!s) return "";
    return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

// ============== 合婚 ==============
function initHehunSelects() {
    const currentYear = new Date().getFullYear();

    ["p1", "p2"].forEach(p => {
        const yearSel = document.getElementById(`${p}-year`);
        const monthSel = document.getElementById(`${p}-month`);
        const daySel = document.getElementById(`${p}-day`);
        const hourSel = document.getElementById(`${p}-hour`);
        const minuteSel = document.getElementById(`${p}-minute`);

        if (!yearSel) return;

        // 年份
        for (let y = currentYear; y >= 1900; y--) {
            const opt = document.createElement("option");
            opt.value = y;
            opt.textContent = y + "年";
            yearSel.appendChild(opt);
        }
        yearSel.value = 1995;

        // 月份
        for (let m = 1; m <= 12; m++) {
            const opt = document.createElement("option");
            opt.value = m;
            opt.textContent = m + "月";
            monthSel.appendChild(opt);
        }

        // 日数
        updateHehunDayOptions(p);
        yearSel.addEventListener("change", () => updateHehunDayOptions(p));
        monthSel.addEventListener("change", () => updateHehunDayOptions(p));

        // 小时（带时辰标注）
        const shichen = ["子", "子", "丑", "丑", "寅", "寅", "卯", "卯", "辰", "辰", "巳", "巳",
                         "午", "午", "未", "未", "申", "申", "酉", "酉", "戌", "戌", "亥", "亥"];
        for (let h = 0; h < 24; h++) {
            const opt = document.createElement("option");
            opt.value = h;
            opt.textContent = `${String(h).padStart(2, "0")}时（${shichen[h]}）`;
            hourSel.appendChild(opt);
        }

        // 分钟
        for (let mn = 0; mn < 60; mn += 5) {
            const opt = document.createElement("option");
            opt.value = mn;
            opt.textContent = String(mn).padStart(2, "0") + "分";
            minuteSel.appendChild(opt);
        }
    });

    // 默认 p2 年份不一样
    const p2Year = document.getElementById("p2-year");
    if (p2Year) p2Year.value = 1996;
}

function updateHehunDayOptions(p) {
    const yearSel = document.getElementById(`${p}-year`);
    const monthSel = document.getElementById(`${p}-month`);
    const daySel = document.getElementById(`${p}-day`);
    if (!yearSel || !daySel) return;

    const year = parseInt(yearSel.value);
    const month = parseInt(monthSel.value);

    // 当前历法
    const calContainer = document.querySelector(`.hehun-cal[data-person="${p}"]`);
    const isLunar = calContainer?.querySelector(".cal-tab.active")?.dataset.cal === "lunar";

    let maxDay = 31;
    if (isLunar) {
        maxDay = 30;
    } else {
        maxDay = new Date(year, month, 0).getDate();
    }

    const oldDay = parseInt(daySel.value) || 1;
    daySel.innerHTML = "";
    for (let d = 1; d <= maxDay; d++) {
        const opt = document.createElement("option");
        opt.value = d;
        opt.textContent = d + "日";
        daySel.appendChild(opt);
    }
    daySel.value = Math.min(oldDay, maxDay);
}

function getHehunPersonData(p) {
    const genderContainer = document.querySelector(`.hehun-gender[data-person="${p}"]`);
    const calContainer = document.querySelector(`.hehun-cal[data-person="${p}"]`);

    const gender = genderContainer?.querySelector(".gender-tab.active")?.dataset.gender || "男";
    const calendar = calContainer?.querySelector(".cal-tab.active")?.dataset.cal || "solar";

    return {
        [`${p}_gender`]: gender,
        [`${p}_calendar`]: calendar,
        [`${p}_year`]: parseInt(document.getElementById(`${p}-year`).value),
        [`${p}_month`]: parseInt(document.getElementById(`${p}-month`).value),
        [`${p}_day`]: parseInt(document.getElementById(`${p}-day`).value),
        [`${p}_hour`]: parseInt(document.getElementById(`${p}-hour`).value),
        [`${p}_minute`]: parseInt(document.getElementById(`${p}-minute`).value),
        [`${p}_leap`]: document.getElementById(`${p}-leap`)?.checked || false,
    };
}

async function divineHehun() {
    const resultSection = document.getElementById("result-section");
    const loading = document.getElementById("loading");
    const content = document.getElementById("result-content");

    resultSection.classList.remove("hidden");
    loading.classList.remove("hidden");
    content.innerHTML = "";

    const payload = {
        ...getHehunPersonData("p1"),
        ...getHehunPersonData("p2"),
    };

    try {
        const res = await fetch("/api/he_hun", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (handleRateLimit(res, data)) { const _l = document.getElementById("loading"); if (_l) _l.classList.add("hidden"); return; }

        if (data.error) {
            content.innerHTML = `<div class="result-card"><p style="color:#ff6666;">${data.error}</p></div>`;
            return;
        }

        content.innerHTML = renderHehun(data);
        // 滚动结果
        resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
        content.innerHTML = `<div class="result-card"><p style="color:#ff6666;">请求失败：${e.message}</p></div>`;
    } finally {
        loading.classList.add("hidden");
    }
}

function renderHehun(d) {
    const p1 = d.person1;
    const p2 = d.person2;

    // 评分进度条（满分 100）
    const score = d.total_score;
    const pct = Math.max(0, Math.min(100, ((score + 50) / 150) * 100));

    const personCard = (p, label) => `
        <div class="hehun-result-person">
            <div class="hehun-rp-label">${label}</div>
            <div class="hehun-rp-meta">${p.gender} · 属${p.sheng_xiao} · ${p.lunar_str}</div>
            <div class="hehun-rp-bazi">${p.bazi}</div>
            <div class="hehun-rp-day">日主 <strong class="wx-${p.day_wuxing}">${p.day_gan}（${p.day_wuxing}）</strong> · ${p.strength}</div>
        </div>
    `;

    const detailRows = d.details.map(item => {
        const levelClass = {
            "大吉": "lv-da-ji", "吉": "lv-ji", "中性": "lv-ping", "平": "lv-ping",
            "小凶": "lv-xiao-xiong", "凶": "lv-xiong", "大凶": "lv-da-xiong",
        }[item.level] || "lv-ping";

        const scoreSign = item.score > 0 ? "+" : "";
        const youTa = (item.you && item.ta) ? `<div class="hehun-row-pair">${item.you} ↔ ${item.ta}</div>` : "";

        return `
            <div class="hehun-detail-row ${levelClass}">
                <div class="hehun-row-head">
                    <span class="hehun-row-cat">${item.category}</span>
                    <span class="hehun-row-level">${item.level}</span>
                    <span class="hehun-row-score">${scoreSign}${item.score}</span>
                </div>
                ${youTa}
                <div class="hehun-row-desc">${item.desc}</div>
            </div>
        `;
    }).join("");

    const blessingsHTML = d.blessings.length ? `
        <div class="hehun-summary-block hehun-bless">
            <h4> 吉处</h4>
            <ul>${d.blessings.map(b => `<li>${b}</li>`).join("")}</ul>
        </div>
    ` : "";

    const issuesHTML = d.issues.length ? `
        <div class="hehun-summary-block hehun-issue">
            <h4> 不合处</h4>
            <ul>${d.issues.map(i => `<li>${i}</li>`).join("")}</ul>
        </div>
    ` : "";

    return `
        <div class="result-card">
            <div class="result-header">
                <div class="result-gua-name"> 八 字 合 婚</div>
            </div>

            <div class="hehun-persons-grid">
                ${personCard(p1, " 第一人")}
                <div class="hehun-versus">合</div>
                ${personCard(p2, " 第二人")}
            </div>

            <h3 class="section-title">总评</h3>
            <div class="hehun-total-card" style="border-color:${d.rating_color};">
                <div class="hehun-total-rating" style="color:${d.rating_color};">${d.rating}</div>
                <div class="hehun-total-score">${d.total_score} 分</div>
                <div class="hehun-total-bar">
                    <div class="hehun-total-bar-fill" style="width:${pct}%; background:${d.rating_color};"></div>
                </div>
                <div class="hehun-total-verdict">${d.verdict}</div>
            </div>

            <h3 class="section-title">六大维度详情</h3>
            <div class="hehun-detail-list">${detailRows}</div>

            ${blessingsHTML}
            ${issuesHTML}

            <div class="bian-gua-tip" style="margin-top:24px;">
                 <strong>说明</strong>：合婚算法综合生肖、日干、日支（夫妻宫）、五行互补、纳音、喜用神 6 大传统维度。<strong>评分仅供参考</strong>，命理不能完全决定缘分，相处的真心和经营才是关键。
            </div>
        </div>
    `;
}


// ============== 梅花易数 ==============
async function divineMeihua() {
    const question = document.getElementById("meihua-question").value.trim();
    const saveObsidian = true;
    const activeMode = document.querySelector(".meihua-mode-tab.active")?.dataset.mhmode || "time";
    const useTime = activeMode === "time";

    let payload = { question, save_obsidian: saveObsidian, use_time: useTime };
    if (!useTime) {
        const n1 = parseInt(document.getElementById("meihua-num1").value);
        const n2 = parseInt(document.getElementById("meihua-num2").value);
        if (!n1 || !n2) {
            alert("请填两个数字");
            return;
        }
        payload.num1 = n1;
        payload.num2 = n2;
    }

    const resultSection = document.getElementById("result-section");
    const loading = document.getElementById("loading");
    const resultContent = document.getElementById("result-content");
    resultSection.classList.remove("hidden");
    loading.classList.remove("hidden");
    resultContent.innerHTML = "";
    document.getElementById("coin-toss")?.classList.add("hidden");

    try {
        const res = await fetch("/api/meihua", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (handleRateLimit(res, data)) { const _l = document.getElementById("loading"); if (_l) _l.classList.add("hidden"); return; }
        if (data.error) {
            resultContent.innerHTML = `<div class="error"> ${data.error}</div>`;
        } else {
            resultContent.innerHTML = renderMeihua(data);
        }
    } catch (e) {
        resultContent.innerHTML = `<div class="error"> 请求失败：${e.message}</div>`;
    } finally {
        loading.classList.add("hidden");
    }
}

function renderMeihua(d) {
    const bg = d.ben_gua, bian = d.bian_gua, hu = d.hu_gua, cuo = d.cuo_gua, zong = d.zong_gua;
    const ty = d.ti_yong, calc = d.calc;

    const guaCard = (label, g, isMain) => `
        <div class="meihua-gua-card${isMain ? ' meihua-gua-main' : ''}">
            <div class="meihua-gua-label">${label}</div>
            <div class="meihua-gua-name">${g.name}</div>
            <div class="meihua-gua-symbol">
                <span class="meihua-trigram">${g.upper_symbol}</span>
                <span class="meihua-trigram">${g.lower_symbol}</span>
            </div>
            <div class="meihua-gua-meta">上${g.upper_gua}（${g.upper_xiang}）/ 下${g.lower_gua}（${g.lower_xiang}）</div>
            <div class="meihua-gua-judg">${g.judgment}</div>
        </div>`;

    const levelColor = {
        '极吉': '#3a9d23', '吉': '#7bb950', '比和': '#7bb950',
        '平': '#8b8b8b', '凶': '#d97706', '极凶': '#c2410c'
    };
    const lvColor = levelColor[ty.level] || '#8b8b8b';

    const savedBlock = d.saved_path
        ? `<div class="saved-tip"> 已保存到 Obsidian：<code>${d.saved_path.split('/').pop()}</code></div>`
        : '';

    return `
        <div class="meihua-result">
            <div class="meihua-header">
                <div class="meihua-title"> 梅花易数 · ${bg.name} 之 ${bian.name}</div>
                <div class="meihua-method">${d.method}</div>
                <div class="meihua-method"><strong>动爻位</strong>：第 ${calc.dong_yao} 爻</div>
                ${d.question ? `<div class="meihua-method"><strong>所问</strong>：${d.question}</div>` : ''}
            </div>

            <div class="meihua-tiyong">
                <div class="meihua-tiyong-row">
                    <span class="meihua-tiyong-label">体卦</span>
                    <span>${ty.ti_position} ${ty.ti_gua}（${ty.ti_wuxing}）</span>
                    <span class="meihua-tiyong-hint">— 我方/自身</span>
                </div>
                <div class="meihua-tiyong-row">
                    <span class="meihua-tiyong-label">用卦</span>
                    <span>${ty.yong_position} ${ty.yong_gua}（${ty.yong_wuxing}）</span>
                    <span class="meihua-tiyong-hint">— 对方/外事</span>
                </div>
                <div class="meihua-tiyong-relation" style="border-color:${lvColor};">
                    <span class="meihua-relation-name">${ty.relation}</span>
                    <span class="meihua-relation-level" style="background:${lvColor};">${ty.level}</span>
                </div>
            </div>

            <h3 class="section-title">五卦合参</h3>
            <div class="meihua-gua-grid">
                ${guaCard('本卦（现状）', bg, true)}
                ${guaCard('变卦（结果）', bian, false)}
                ${guaCard('互卦（过程）', hu, false)}
                ${guaCard('错卦（反面）', cuo, false)}
                ${guaCard('综卦（对方视角）', zong, false)}
            </div>

            <div class="meihua-tips">
                 <strong>梅花要诀</strong>：体用是吉凶骨架——用生体最吉，体克用次吉，比和平稳，体生用泄气，用克体最凶。
                五卦合参，本卦看眼前，变卦看结局，互卦看过程，错综看反向参考。
            </div>

            ${savedBlock}
        </div>
    `;
}


// ============== 奇门遁甲 ==============
async function divineQimen() {
    const question = document.getElementById("qimen-question").value.trim();
    const saveObsidian = true;
    const opt = parseInt(document.querySelector(".qimen-opt-tab.active")?.dataset.qmopt || "2");

    const payload = { question, save_obsidian: saveObsidian, option: opt };

    const resultSection = document.getElementById("result-section");
    const loading = document.getElementById("loading");
    const resultContent = document.getElementById("result-content");
    resultSection.classList.remove("hidden");
    loading.classList.remove("hidden");
    resultContent.innerHTML = "";
    document.getElementById("coin-toss")?.classList.add("hidden");

    try {
        const res = await fetch("/api/qimen", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (handleRateLimit(res, data)) { const _l = document.getElementById("loading"); if (_l) _l.classList.add("hidden"); return; }
        if (data.error) {
            resultContent.innerHTML = `<div class="error"> ${data.error}</div>`;
        } else {
            resultContent.innerHTML = renderQimen(data);
        }
    } catch (e) {
        resultContent.innerHTML = `<div class="error"> 请求失败：${e.message}</div>`;
    } finally {
        loading.classList.add("hidden");
    }
}

function renderQimen(d) {
    const palaces = d.palaces;
    const zhifu = d.zhifu;

    // 九宫排版（标准九宫格：南上北下，左东右西，中宫居中）
    // 位置 → 宫
    // [巽 离 坤]
    // [震 中 兑]
    // [艮 坎 乾]
    const layoutOrder = ['巽', '离', '坤', '震', '中', '兑', '艮', '坎', '乾'];
    const palaceMap = {};
    palaces.forEach(p => { palaceMap[p.gong] = p; });

    const levelColor = (lv) => ({ '吉': '#3a9d23', '平': '#8b8b8b', '凶': '#c2410c' }[lv] || '#999');

    const cells = layoutOrder.map(gn => {
        const p = palaceMap[gn] || { gong: gn };
        if (p.gong === '中') {
            // 中宫不放门/星/神
            return `
                <div class="qm-cell qm-center">
                    <div class="qm-gong">中宫</div>
                    <div class="qm-gan">天:${p.sky_gan || '—'} 地:${p.earth_gan || '—'}</div>
                </div>`;
        }
        return `
            <div class="qm-cell">
                <div class="qm-shen" style="color:${levelColor(p.shen_level)};">${p.shen}</div>
                <div class="qm-star" style="color:${levelColor(p.star_level)};">${p.star}</div>
                <div class="qm-gan-row">
                    <span class="qm-sky">${p.sky_gan}</span>
                    <span class="qm-earth">${p.earth_gan}</span>
                </div>
                <div class="qm-gate" style="color:${levelColor(p.gate_level)};">${p.gate}</div>
                <div class="qm-gong">${p.gong}<span class="qm-dir">·${p.direction}</span></div>
            </div>`;
    }).join('');

    const savedBlock = d.saved_path
        ? `<div class="saved-tip"> 已保存到 Obsidian：<code>${d.saved_path.split('/').pop()}</code></div>`
        : '';

    return `
        <div class="qimen-result">
            <div class="qimen-header">
                <div class="qimen-title"> 奇门遁甲 · ${d.paiju}</div>
                <div class="qimen-meta">
                    <span><strong>干支</strong>：${d.ganzhi}</span>
                    <span><strong>节气</strong>：${d.jieqi}</span>
                    <span><strong>排法</strong>：${d.method}</span>
                </div>
                ${d.question ? `<div class="qimen-method"><strong>所问</strong>：${d.question}</div>` : ''}
            </div>

            <div class="qimen-zhifu">
                <div class="qm-zf-row">
                    <span class="qm-zf-label">值符</span>
                    <span>${zhifu['值符星']} 落 <strong>${zhifu['值符宫']}</strong>宫</span>
                    <span class="qm-zf-hint">值符天干: ${zhifu['值符天干'].join(' / ')}</span>
                </div>
                <div class="qm-zf-row">
                    <span class="qm-zf-label">值使</span>
                    <span>${zhifu['值使门']} 落 <strong>${zhifu['值使宫']}</strong>宫</span>
                    <span class="qm-zf-hint">天乙: ${d.tianyi}</span>
                </div>
                <div class="qm-zf-row">
                    <span class="qm-zf-label">旬空</span>
                    <span>日空 ${d.xunkong['日空']} / 时空 ${d.xunkong['时空']}</span>
                    <span class="qm-zf-hint">旬首: ${d.xunshou}</span>
                </div>
                <div class="qm-zf-row">
                    <span class="qm-zf-label">马星</span>
                    <span>天马 ${d.mastar['天马']} · 丁马 ${d.mastar['丁马']} · 驿马 ${d.mastar['驿马']}</span>
                </div>
            </div>

            <h3 class="section-title">九宫盘</h3>
            <div class="qm-grid">
                ${cells}
            </div>

            <div class="qm-legend">
                <span><strong>每宫上→下</strong>：八神 / 九星 / 天盘干 地盘干 / 八门 / 宫位·方位</span>
            </div>

            <div class="meihua-tips">
                 <strong>奇门要诀</strong>：开/休/生为吉门，伤/惊/死为凶门，杜/景为平门。
                求财看生门、出行看驿马、求人看值使。值符所到之宫为最尊位。
            </div>

            ${savedBlock}
        </div>
    `;
}


// ============== 黄历 ==============
async function divineHuangli() {
    const date = document.getElementById("huangli-date").value;

    const resultSection = document.getElementById("result-section");
    const loading = document.getElementById("loading");
    const resultContent = document.getElementById("result-content");
    resultSection.classList.remove("hidden");
    loading.classList.remove("hidden");
    resultContent.innerHTML = "";
    document.getElementById("coin-toss")?.classList.add("hidden");

    try {
        const res = await fetch("/api/huangli", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ date })
        });
        const data = await res.json();
        if (handleRateLimit(res, data)) { const _l = document.getElementById("loading"); if (_l) _l.classList.add("hidden"); return; }
        if (data.error) {
            resultContent.innerHTML = `<div class="error"> ${data.error}</div>`;
        } else {
            resultContent.innerHTML = renderHuangli(data);
        }
    } catch (e) {
        resultContent.innerHTML = `<div class="error"> 请求失败：${e.message}</div>`;
    } finally {
        loading.classList.add("hidden");
    }
}

function renderHuangli(d) {
    const lunar = d.lunar;
    const gz = d.ganzhi;
    const sc = d.shichen;
    const dirs = d.lucky_directions || {};

    const goodList = (d.good_things || []).map(s => `<span class="hl-tag hl-good">${s}</span>`).join('');
    const badList = (d.bad_things || []).map(s => `<span class="hl-tag hl-bad">${s}</span>`).join('');
    const goodGods = (d.good_gods || []).slice(0, 8).map(s => `<span class="hl-god-tag hl-good-god">${s}</span>`).join('');
    const badGods = (d.bad_gods || []).slice(0, 8).map(s => `<span class="hl-god-tag hl-bad-god">${s}</span>`).join('');

    const levelColor = (lv) => ({ '吉': '#3a9d23', '平': '#8b8b8b', '凶': '#c2410c' }[lv] || '#888');

    const shichenRows = sc.map(s => `
        <div class="hl-sc-cell" style="border-left:3px solid ${levelColor(s.level)};">
            <div class="hl-sc-name">${s.name}时</div>
            <div class="hl-sc-hours">${s.hours}点</div>
            <div class="hl-sc-gz">${s.gz}</div>
            <div class="hl-sc-level" style="color:${levelColor(s.level)};">${s.level}</div>
            ${s.reason ? `<div class="hl-sc-reason">${s.reason}</div>` : ''}
        </div>
    `).join('');

    const dirRows = Object.entries(dirs).map(([k, v]) =>
        `<div class="hl-dir-row"><span class="hl-dir-label">${k}</span><span>${v}</span></div>`
    ).join('');

    const term = d.solar_term;
    const termInfo = term.today
        ? `今日是 <strong>${term.today}</strong>`
        : `距下一节气 <strong>${term.next}</strong>（${term.next_date}）还有 <strong>${term.days_to_next}</strong> 天`;

    return `
        <div class="huangli-result">
            <div class="huangli-header">
                <div class="huangli-title"> ${d.date} · ${d.weekday}</div>
                <div class="huangli-meta">
                    农历 ${lunar.year} ${lunar.month}${lunar.day} · ${lunar.season} · ${lunar.phase_of_moon}
                </div>
                <div class="huangli-meta">
                    <strong>${gz.year}年 ${gz.month}月 ${gz.day}日</strong> · 生肖${d.zodiac} · ${d.star_zodiac}
                </div>
                <div class="huangli-meta-term">${termInfo}</div>
            </div>

            <div class="hl-summary">
                <div class="hl-summary-item">
                    <div class="hl-summary-label">今日总评</div>
                    <div class="hl-summary-value">${d.today_level.thing_level}</div>
                </div>
                <div class="hl-summary-item">
                    <div class="hl-summary-label">十二建除</div>
                    <div class="hl-summary-value">${d.today_12_officer}日</div>
                </div>
                <div class="hl-summary-item">
                    <div class="hl-summary-label">十二神煞</div>
                    <div class="hl-summary-value" style="color:${levelColor(d.today_12_god.level)};">
                        ${d.today_12_god.name}（${d.today_12_god.level}）
                    </div>
                </div>
                <div class="hl-summary-item">
                    <div class="hl-summary-label">廿八星宿</div>
                    <div class="hl-summary-value">${d.today_28_star}</div>
                </div>
            </div>

            <h3 class="section-title">宜</h3>
            <div class="hl-things-grid">${goodList || '<span class="hl-empty">无</span>'}</div>

            <h3 class="section-title">忌</h3>
            <div class="hl-things-grid">${badList || '<span class="hl-empty">无</span>'}</div>

            <h3 class="section-title">十二时辰吉凶</h3>
            <div class="hl-shichen-grid">${shichenRows}</div>

            <h3 class="section-title">方位 / 神煞</h3>
            <div class="hl-info-row">
                <div class="hl-info-card">
                    <div class="hl-info-title"> 财喜方位</div>
                    ${dirRows || '<div class="hl-empty">无</div>'}
                </div>
                <div class="hl-info-card">
                    <div class="hl-info-title"> 冲煞 / 喜忌</div>
                    <div class="hl-dir-row"><span class="hl-dir-label">冲煞</span><span>${d.zodiac_clash}</span></div>
                    <div class="hl-dir-row"><span class="hl-dir-label">三合</span><span>${d.zodiac_win}</span></div>
                    <div class="hl-dir-row"><span class="hl-dir-label">破日</span><span>${d.zodiac_lose}</span></div>
                </div>
            </div>

            <div class="hl-info-row">
                <div class="hl-info-card">
                    <div class="hl-info-title"> 吉神</div>
                    <div class="hl-god-list">${goodGods || '<span class="hl-empty">无</span>'}</div>
                </div>
                <div class="hl-info-card">
                    <div class="hl-info-title"> 凶神</div>
                    <div class="hl-god-list">${badGods || '<span class="hl-empty">无</span>'}</div>
                </div>
            </div>

            <h3 class="section-title">彭祖百忌 / 胎神 / 经络</h3>
            <div class="hl-pengzu">
                <div class="hl-pengzu-row"><strong>彭祖百忌</strong>：${d.pengzu_taboo || '无'}</div>
                <div class="hl-pengzu-row"><strong>胎神占位</strong>：${d.fetal_god || '无'}</div>
                <div class="hl-pengzu-row"><strong>今日经络</strong>：${d.meridians || '无'}</div>
            </div>

            <div class="meihua-tips">
                 <strong>说明</strong>：黄历宜忌出自《通书》，吉时是按时辰地支与日支的合冲关系简化推算（合吉冲凶比和吉）。
                重要事项决策仅供参考，更专业的择吉需结合生辰八字。
            </div>
        </div>
    `;
}


// ============== 解梦 ==============
async function interpretDream() {
    const dreamText = document.getElementById("dream-text").value.trim();
    const mood = document.getElementById("dream-mood").value.trim();
    const context = document.getElementById("dream-context").value.trim();

    if (!dreamText) {
        alert("梦境内容不能为空哦");
        return;
    }
    if (dreamText.length > 2000) {
        alert("梦境太长了（最多 2000 字），分段做");
        return;
    }

    const resultSection = document.getElementById("result-section");
    const loading = document.getElementById("loading");
    const loadingText = document.getElementById("loading-text");
    const resultContent = document.getElementById("result-content");
    resultSection.classList.remove("hidden");
    loading.classList.remove("hidden");
    resultContent.innerHTML = "";
    document.getElementById("coin-toss")?.classList.add("hidden");
    if (loadingText) loadingText.textContent = "AI 正在解读你的梦境...";

    try {
        const res = await fetch("/api/dream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                dream_text: dreamText,
                mood: mood,
                context: context,
                save_obsidian: true,
            }),
        });
        const data = await res.json();
        if (handleRateLimit(res, data)) { const _l = document.getElementById("loading"); if (_l) _l.classList.add("hidden"); return; }
        if (data.error) {
            resultContent.innerHTML = `<div class="error">${escapeHtml(data.error)}</div>`;
        } else {
            resultContent.innerHTML = renderDream(data);
        }
    } catch (e) {
        resultContent.innerHTML = `<div class="error">请求失败：${escapeHtml(e.message)}</div>`;
    } finally {
        loading.classList.add("hidden");
    }
}

function renderDream(d) {
    const z = d.zhougong || {};
    const p = d.psychology || {};
    const symbols = (z.symbols || []).map(s =>
        `<span class="dream-tag dream-tag-trad">${escapeHtml(s)}</span>`
    ).join('');
    const archetypes = (p.archetypes || []).map(s =>
        `<span class="dream-tag dream-tag-psych">${escapeHtml(s)}</span>`
    ).join('');
    const suggestions = (d.suggestions || []).map(s =>
        `<li>${escapeHtml(s)}</li>`
    ).join('');

    const meta = [];
    if (d.mood_on_wake) meta.push(`<span class="dream-meta-item">情绪：${escapeHtml(d.mood_on_wake)}</span>`);
    if (d.context) meta.push(`<span class="dream-meta-item">处境：${escapeHtml(d.context)}</span>`);

    return `
        <div class="dream-result">
            <div class="dream-header">
                <div class="dream-title">解梦</div>
                <div class="dream-meta">${meta.join('')}</div>
            </div>

            <div class="dream-original">
                <div class="dream-section-label">梦境原文</div>
                <div class="dream-original-text">${escapeHtml(d.dream_text || '')}</div>
            </div>

            <div class="dream-card dream-card-trad">
                <h3 class="dream-card-title">周公视角</h3>
                ${symbols ? `<div class="dream-tags">${symbols}</div>` : ''}
                <p class="dream-text">${escapeHtml(z.interpretation || '')}</p>
            </div>

            <div class="dream-card dream-card-psych">
                <h3 class="dream-card-title">心理学视角</h3>
                ${archetypes ? `<div class="dream-tags">${archetypes}</div>` : ''}
                <p class="dream-text">${escapeHtml(p.interpretation || '')}</p>
            </div>

            <div class="dream-card dream-card-summary">
                <h3 class="dream-card-title">综合给你的话</h3>
                <p class="dream-summary-text">${escapeHtml(d.summary || '')}</p>
            </div>

            ${suggestions ? `
            <div class="dream-card dream-card-suggestions">
                <h3 class="dream-card-title">落地建议</h3>
                <ul class="dream-suggestions">${suggestions}</ul>
            </div>
            ` : ''}

            <div class="dream-tips">
                解梦仅供参考，不是命理预言。记录已自动存入 Obsidian。
            </div>
        </div>
    `;
}
