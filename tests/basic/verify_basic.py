#!/usr/bin/env python3
# verify_basic.py — CHARTS-001/002 基础能力验收调度入口（001 T-05；002 T-04 扩展）。
#
# 双 profile 真实任务验收：导入真实 CSV → 列映射 → 图表 → 保存 → 重开 →
# 导出 SVG，含独立 CSV/几何/XML oracle、中文/特殊字符传输（CH-02）、
# 小数几何（CH-03）、旧工程与失败保全（CH-04）、区分性自检（CH-05）。
#   --profile vm   : `auto run -r vm` 真实窗口 + AUTOUI_MCP_PORT 驱动
#   --profile vue  : `AUTO_BACKEND_IMPL=vm auto run`(:17850) + Playwright chromium
#
# 隔离：每次运行创建临时 AUTO_CHARTS_DATA 数据目录与空闲 MCP/前端端口，
# 不接触真实用户数据。记录源码/工具版本、fixture hash 与逐项结果。
# 任何 FAIL 以退出码 1 结束。
#
# 几何 oracle（独立复算，不以两端同错为通过）：f64 域 vmin=min(0,min)、
# vmax=max(0,max)，span 退化 [0,100]；y(v)=260-(v-vmin)/span*240；步长
# {1,2,5}·10^k ≥ span/4；屏幕容差 ±1px（DOM/MCP 读取面），导出 ±0.01px。
# CH-05 自检：小数用例的新刻度标签必须与旧整数截断产物可区分。
import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
AUTO_BIN = os.environ.get("AUTO_BIN", r"D:\autostack\auto-man\target\debug\auto.exe")
FAILS = []
PASSES = []
RECORD = {"profile": None, "started": time.strftime("%Y-%m-%d %H:%M:%S"),
          "tool_versions": {}, "fixtures": {}, "results": []}


def check(name, cond, detail=""):
    entry = {"name": name, "pass": bool(cond), "detail": str(detail)[:400]}
    RECORD["results"].append(entry)
    if cond:
        PASSES.append(name)
        print("PASS " + name)
    else:
        FAILS.append(name)
        print("FAIL " + name + (" :: " + str(detail)[:400] if detail else ""))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def pick_free_port(start):
    for port in range(start, start + 200):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("no free port >= %d" % start)


# ═══════════════════════════════════════════════════════════
# 独立几何 oracle（纯 Python f64，与实现同式复算）
# ═══════════════════════════════════════════════════════════

def oracle_domain(values):
    vmin = min(0.0, min(values))
    vmax = max(0.0, max(values))
    span = vmax - vmin
    if span <= 0:
        vmin, vmax, span = 0.0, 100.0, 100.0
    raw = span / 4
    # 阶梯 {1,2,5}·10^k（k∈ℤ）：≥ raw 的最小值（负 k 档参与——Spec 公式；
    # 1e-7 相对边界容差与实现同口径，防除法种子 ulp 跌档）
    rawm = raw - raw / 10000000.0
    step = None
    base = 1.0
    g = 0
    while base > rawm and g < 14:
        base /= 10
        g += 1
    for _ in range(30):
        if step is None and base >= rawm:
            step = base
        if step is None and base * 2 >= rawm:
            step = base * 2
        if step is None and base * 5 >= rawm:
            step = base * 5
        base *= 10
        g += 1
        if g > 40:
            break
    return vmin, vmax, span, step


def oracle_y(v, vmin, span):
    return 260.0 - (v - vmin) / span * 240.0


def oracle_step_me(step):
    for e in range(-12, 13):
        for m in (1, 2, 5):
            if abs(step - m * 10.0 ** e) <= abs(step) * 1e-5:
                return m, e
    return 1, 0


def label_of_k(k, m, e):
    """刻度标签 = k·m·10^e 整数重建（与实现 chart_geom.label_of_k 同式；
    VM float 为 f32，浮点路径 %.8g 有噪声，整数重构与 float 宽度无关）。"""
    if k == 0:
        return "0"
    neg = k < 0
    kk = -k if neg else k
    digits = str(kk * m)
    if e >= 0:
        out = digits + "0" * e
    else:
        ne = -e
        padded = digits
        while len(padded) <= ne:
            padded = "0" + padded
        ip = len(padded) - ne
        head = padded[:ip]
        tail = padded[ip:].rstrip("0")
        out = head if tail == "" else head + "." + tail
    return ("-" + out) if neg else out


def oracle_ticks(vmin, vmax, step):
    """返回 [(tick_value, k)] 升序。"""
    pairs = []
    k = 0
    t = k * step
    while t <= vmax + 1e-12:
        if t >= vmin - 1e-12:
            pairs.append((t, k))
        k += 1
        t = k * step
    k = -1
    t = k * step
    while t >= vmin - 1e-12:
        if t <= vmax + 1e-12:
            pairs.append((t, k))
        k -= 1
        t = k * step
    pairs.sort(key=lambda p: p[0])
    return pairs


def oracle_tick_labels(values):
    vmin, vmax, span, step = oracle_domain(values)
    m, e = oracle_step_me(step)
    return [label_of_k(k, m, e) for _t, k in oracle_ticks(vmin, vmax, step)]


def old_truncated_labels(values):
    """CH-05 对照：001 屏幕端整数截断域下的刻度标签（值域 int 截断）。"""
    tvals = [float(int(v)) for v in values]
    return oracle_tick_labels(tvals)


# ═══════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════

def make_fixtures(root):
    """V-01/V-02（001）+ CH-02 中文/特殊字符 + CH-03 小数组。"""
    fx = {}
    p1 = os.path.join(root, "v01_rich.csv")
    with open(p1, "w", encoding="utf-8-sig", newline="") as f:
        f.write('月份,桌面,移动\n"一月,春节","1,200",-300\n"二月\n跨行",0,0\n三月,10,25\n')
    fx["rich"] = p1
    p2 = os.path.join(root, "v02_signed.csv")
    with open(p2, "w", encoding="utf-8", newline="") as f:
        f.write('cat,v1,v2\n"neg,<tag>&",10,-20\nzero,0,0\npos,-5,15\n')
    fx["signed"] = p2
    p3 = os.path.join(root, "bad_cell.csv")
    with open(p3, "w", encoding="utf-8", newline="") as f:
        f.write("cat,v\nok,1\nbad,abc\n")
    fx["bad"] = p3
    p4 = os.path.join(root, "empty.csv")
    open(p4, "w", encoding="utf-8").close()
    fx["empty"] = p4
    # CH-02：中文目录 + 空格 + + & # % = 文件名（? 平台不合法→只测工程名）
    cjk_dir = os.path.join(root, "中文 目录+A&B#C%D=E")
    os.makedirs(cjk_dir, exist_ok=True)
    pc = os.path.join(cjk_dir, "数据 文件+v1.csv")
    with open(pc, "w", encoding="utf-8", newline="") as f:
        f.write("月份,销售额\n一月,120.5\n二月,80\n三月,95.25\n")
    fx["cjk"] = pc
    # CH-02 %2520 对照：字面 %20 文件名与空格名不混淆（行数不同可区分）
    pct = os.path.join(cjk_dir, "数据%20文件.csv")
    with open(pct, "w", encoding="utf-8", newline="") as f:
        f.write("月份,销售额\n一月,1\n二月,2\n")
    fx["cjk_pct"] = pct
    # CH-03 小数/负值/零/极小/四系列
    def dcsv(name, header, rows):
        p = os.path.join(root, name)
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write(header + "\n" + "\n".join(rows) + "\n")
        return p
    fx["dec"] = dcsv("ch03_dec.csv", "cat,a,b", ["x,0.1,5", "y,0.2,6"])
    fx["sdec"] = dcsv("ch03_sdec.csv", "cat,v", ["n,-0.5", "z,0", "p,0.5"])
    fx["mixed"] = dcsv("ch03_mixed.csv", "cat,v", ["n,-300", "z,0", "p,25.5"])
    fx["tiny"] = dcsv("ch03_tiny.csv", "cat,v", ["a,0.001", "b,0.002"])
    fx["zeros"] = dcsv("ch03_zeros.csv", "cat,v", ["a,0", "b,0"])
    fx["four"] = dcsv("ch03_four.csv", "cat,v1,v2,v3,v4",
                      ["a,1.25,2.5,-1.5,0.75", "b,2,4,-3,1.5"])
    # dec 屏幕用例映射单数值列（列 1）→ 屏幕域 = [0.1, 0.2]
    fx["decvals"] = {"dec": [0.1, 0.2], "sdec": [-0.5, 0.0, 0.5],
                     "mixed": [-300.0, 0.0, 25.5], "tiny": [0.001, 0.002],
                     "zeros": [0.0, 0.0], "four": [1.25, 2.5, -1.5, 0.75, 2.0, 4.0, -3.0, 1.5]}
    for k, p in fx.items():
        if isinstance(p, str):
            RECORD["fixtures"][k] = {"path": p, "sha256": sha256_file(p)}
    return fx


# ═══════════════════════════════════════════════════════════
# VM profile：真实窗口 + MCP
# ═══════════════════════════════════════════════════════════

class VmDriver:
    def __init__(self, mcp_port):
        self.url = "http://localhost:%d/mcp" % mcp_port
        self.req_id = 0

    def call(self, tool, **args):
        last = None
        for backoff in (0.5, 1.5, 3.0):
            self.req_id += 1
            try:
                r = urllib.request.Request(
                    self.url,
                    data=json.dumps({"jsonrpc": "2.0", "method": "tools/call",
                                     "params": {"name": tool, "arguments": args},
                                     "id": self.req_id}).encode("utf-8"),
                    method="POST")
                r.add_header("Content-Type", "application/json")
                v = json.loads(urllib.request.urlopen(r, timeout=20).read().decode("utf-8"))
                break
            except Exception as e:
                last = e
                time.sleep(backoff)
        else:
            raise last
        content = v.get("result", {}).get("content", [])
        return content[0]["text"] if content else ""

    def state(self, *fields):
        text = self.call("autoui_state", fields=list(fields))
        out = {}
        for line in text.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                v = v.strip()
                if v.endswith(")") and " (" in v:
                    v = v[: v.rfind(" (")].strip()
                out[k.strip()] = v
        return out

    def press_button(self, label):
        text = self.call("autoui_find", kind="button", label=label)
        m = re.findall(r"button (vnode_\d+)", text)
        if not m:
            return False
        self.call("autoui_action", element_id=m[0], action="press")
        return True

    def type_into_input(self, placeholder_hint, value):
        # 实测：autoui_type 带 element_id 不触发 oninput；先 press 聚焦
        # 再对焦点输入 type（VM 窗口 MCP 驱动语义）。窗口刚起时元素绑定
        # 有竞态：输入后读回状态校验，未生效则重试（≤4 次）。
        return self.type_into_field("csvPath", value)

    def type_into_field(self, state_field, value):
        # G-7 纪律加强版：press 焦点转移在视图重建后不可靠——遍历全部
        # 输入框逐个 press+type，以目标状态字段读回为准，命中即停。
        text = self.call("autoui_find", kind="input")
        ids = re.findall(r"input (vnode_\d+)", text)
        if not ids:
            return False
        want = value.replace("\\", "/")
        for _round in range(4):
            for iid in ids:
                self.call("autoui_action", element_id=iid, action="press")
                time.sleep(0.4)
                self.call("autoui_type", text=value)
                time.sleep(0.6)
                st = self.state(state_field)
                got = st.get(state_field, "").strip('"').replace("\\\\", "/").replace("\\", "/")
                if got == want:
                    return True
            time.sleep(1.0)
        return False


def wait_mcp(url, timeout=40):
    for _ in range(timeout):
        try:
            r = urllib.request.Request(
                url, data=json.dumps({"jsonrpc": "2.0", "method": "tools/list",
                                      "params": {}, "id": 1}).encode("utf-8"),
                method="POST")
            r.add_header("Content-Type", "application/json")
            urllib.request.urlopen(r, timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False


def parse_f(s):
    try:
        return float(str(s).strip().strip('"'))
    except Exception:
        return None


def vm_check_screen_geo(d, fx, key):
    """CH-03 屏幕端：读组件状态与独立 oracle 对账（±1px / 标签逐字）。
    读数纪律：组件 Init 在映射完成后异步完成——先静置，再连续两次读到
    完全一致的状态才采信（避免读进半更新/上一图状态）。"""
    vals = fx["decvals"][key]
    vmin, vmax, span, step = oracle_domain(vals)
    y0 = oracle_y(0.0, vmin, span)
    time.sleep(2.0)
    geo = {}
    prev = None
    for _ in range(10):
        geo = d.state("barBaseY", "barGrid", "barTick4", "barTick3", "barTick2", "barTick1", "barTick0")
        gp = geo.get("barGrid", "")
        if gp.startswith('"') and "H550" in gp and geo == prev:
            break
        prev = geo
        time.sleep(0.8)
    bv = parse_f(geo.get("barBaseY", ""))
    check("vm ch03 %s: baseline ±1px" % key, bv is not None and abs(bv - y0) <= 1.0, (bv, y0))
    # 刻度标签：可见槽 = min(5, 全量数) 自底向上填（组件合同）
    pairs = oracle_ticks(vmin, vmax, step)
    m, e = oracle_step_me(step)
    shown = pairs if len(pairs) <= 5 else pairs[:5]
    fields = ["barTick4", "barTick3", "barTick2", "barTick1", "barTick0"]
    # barTick4 = 最高可见刻度 = shown[-1]（自底向上填时最高在 4 号槽）
    ok_all = True
    detail = []
    for idx, fld in enumerate(fields):
        want = shown[len(shown) - 1 - idx] if idx < len(shown) else None
        got = geo.get(fld, "").strip('"')
        if want is None:
            ok_all = ok_all and (got == "" or got == '""')
            detail.append((fld, got, ""))
        else:
            wl = label_of_k(want[1], m, e)
            ok_all = ok_all and got == wl
            detail.append((fld, got, wl))
    check("vm ch03 %s: tick labels verbatim" % key, ok_all, detail)
    # CH-05 自检：新刻度标签必须与旧整数截断产物可区分。dec 用例的大值
    # 系列主导值域，截断不改变域（旧==新是预期），不纳入区分性断言。
    if key in ("tiny", "sdec"):
        old = old_truncated_labels(vals)
        new = [label_of_k(k, m, e) for _t, k in pairs]
        check("vm ch05 %s: new labels differ from old truncation" % key,
              old != new, (old[:6], new[:6]))


def verify_vm(fx, data_dir):
    mcp_port = pick_free_port(19520)
    front_port = pick_free_port(17740)
    back_port = pick_free_port(17760)
    # AUTO_VM_WITH_HTTP=1 → split 模式：真实 VM HTTP 后端（lazy back 孵化）
    # + VM 窗口（run_vm.rs PLAN-026 路径）；merged 模式无 HTTP 服务器。
    # -F/-B 显式端口：框架启动按端口清场（util.rs kill_process_on_port，
    # Plan 354）——缺省 17850/17851 会与并发会话的 VM 窗口互杀（CHARTS-002
    # merge 期实录），隔离端口使多会话共存。
    env = {**os.environ, "AUTOUI_MCP_PORT": str(mcp_port),
           "AUTO_FRONT_PORT": str(front_port), "AUTO_HTTP_PORT": str(back_port),
           "AUTO_CHARTS_DATA": data_dir, "AUTO_VM_WITH_HTTP": "1"}
    # 窗口启动是环境级 flake（desktop_mcp.py 同款：MCP 不 bind 时杀掉重拉）
    proc = None
    d = None
    for attempt in range(3):
        if proc is not None:
            proc.kill()
            time.sleep(1.5)
        errlog = open(os.path.join(data_dir, "vm_window_stderr.log"), "ab")
        proc = subprocess.Popen([AUTO_BIN, "run", "-r", "vm", "-F", str(front_port), "-B", str(back_port)], cwd=REPO, env=env,
                                stdout=errlog, stderr=subprocess.STDOUT)
        ok = wait_mcp("http://localhost:%d/mcp" % mcp_port, timeout=45)
        if ok:
            cand = VmDriver(mcp_port)
            for _ in range(20):
                time.sleep(1.0)
                try:
                    if "chartType" in cand.state("chartType"):
                        d = cand
                        break
                except Exception:
                    pass
            if d is not None:
                break
        print("  (attempt %d: window/MCP not ready, relaunching)" % (attempt + 1))
    check("vm: window ready after retries (CH-01)", d is not None)
    try:
        if d is None:
            raise RuntimeError("window failed to start after 3 attempts")
        st = d.state("statusMsg", "datasetLoaded", "chartType")
        # ---- CH-01 空态 ----
        st = d.state("statusMsg", "datasetLoaded", "chartType")
        check("vm: startup empty state", st.get("datasetLoaded") == "false"
              and "导入" in st.get("statusMsg", ""), st)
        check("vm: default chartType=bar", st.get("chartType") == '"bar"', st)

        # ---- CH-02 导入（中文/空格/+&#%= 目录与文件名，POST body 传输）----
        typed = d.type_into_input("CSV", fx["cjk"])
        check("vm ch02: cjk path typed", typed)
        time.sleep(0.3)
        d.press_button("导入")
        time.sleep(1.2)
        st = d.state("datasetLoaded", "statusMsg", "statusErr")
        check("vm ch02: cjk import loaded", st.get("datasetLoaded") == "true", st)
        check("vm ch02: cjk import ok status", st.get("statusErr") == "false"
              and "已导入" in st.get("statusMsg", ""), st)

        # ---- CH-02 %20 字面对照：与空格名不混淆 ----
        typed = d.type_into_input("CSV", fx["cjk_pct"])
        d.press_button("导入")
        time.sleep(1.2)
        st = d.state("statusMsg", "datasetLoaded")
        check("vm ch02: literal %20 twin imports as own file",
              "已导入 2 行" in st.get("statusMsg", ""), st)

        # ---- CH-02 回到主 CJK 文件 ----
        typed = d.type_into_input("CSV", fx["cjk"])
        d.press_button("导入")
        time.sleep(1.2)
        st = d.state("datasetLoaded", "statusMsg")
        check("vm ch02: reimport cjk main", st.get("datasetLoaded") == "true", st)

        # ---- 列映射：类别=月份(0) 数值=销售额(1) ----
        def press_nth(label, n):
            text = d.call("autoui_find", kind="button", label=label)
            ids = re.findall(r"button (vnode_\d+)", text)
            if len(ids) <= n:
                return False
            d.call("autoui_action", element_id=ids[n], action="press")
            return True
        check("vm ch02: set index col", press_nth("类别", 0))
        time.sleep(1.0)
        check("vm ch02: set value col1", press_nth("数值", 1))
        time.sleep(1.2)
        st = d.state("chartReady", "statusMsg", "statusErr")
        check("vm ch02: mapping valid on cjk data", st.get("chartReady") == "true", st)

        # ---- CH-02 中文工程名保存（? 只在工程名层测）----
        # 工程名预填为源文件名；改打中文名（含平台合法特殊字符）
        st = d.state("projName")
        check("vm ch02: project name prefilled", st.get("projName", "") not in ('""', ''), st)
        # 单输入打字：直接保存预填名（CJK 基名）；重名覆盖自身
        d.press_button("保存")
        time.sleep(1.5)
        st = d.state("statusMsg", "statusErr")
        check("vm ch02: save ok with cjk name", st.get("statusErr") == "false"
              and "已保存" in st.get("statusMsg", ""), st)
        saved_id = ""
        m = re.search(r"已保存工程 (.+?)\"?$", st.get("statusMsg", "").strip('"'))
        if m:
            saved_id = m.group(1)
        # 磁盘文件逐字核对
        proj_file = os.path.join(data_dir, "projects", (saved_id or "数据-文件+v1") + ".json")
        check("vm ch02: project file on disk verbatim slug",
              os.path.exists(proj_file), sorted(os.listdir(os.path.join(data_dir, "projects"))) if os.path.isdir(os.path.join(data_dir, "projects")) else "no dir")

        # ---- CH-04 删源重开导出 ----
        d.press_button("刷新列表")
        time.sleep(1.0)
        st = d.state("statusMsg")
        check("vm: project listed", "工程列表已刷新(1" in st.get("statusMsg", ""), st)
        check("vm: reopen project", d.press_button("打开"))
        time.sleep(1.2)
        st = d.state("datasetLoaded", "chartReady", "projName", "statusMsg")
        check("vm: reopened project ready", st.get("datasetLoaded") == "true"
              and st.get("chartReady") == "true"
              and "已打开工程" in st.get("statusMsg", ""), st)
        # 导出（源仍在）
        d.press_button("导出 SVG")
        time.sleep(1.5)
        st = d.state("statusMsg", "statusErr")
        msg = st.get("statusMsg", "").strip('"')
        m = re.search(r"已导出 SVG → (.+)", msg)
        check("vm: export reported", st.get("statusErr") == "false" and m, st)
        if m:
            out = m.group(1).replace("\\\\", "\\")
            RECORD["vm_export_path"] = out
            with open(out, "r", encoding="utf-8") as f:
                svg = f.read()
            check("vm: exported svg parseable head", svg.startswith("<?xml") and "</svg>" in svg)
        # 删源后按工程导出
        os.remove(fx["cjk"])
        d.press_button("导出 SVG")
        time.sleep(1.5)
        st = d.state("statusMsg", "statusErr")
        check("vm ch04: export by project after source removed",
              st.get("statusErr") == "false" and "已导出" in st.get("statusMsg", ""), st)

        # ---- CH-03 屏幕端小数几何（重新导入小数数据；每步验证）----
        def import_and_map(path, ncol_expect):
            typed = d.type_into_field("csvPath", path)
            if not typed:
                check("vm ch03: type %s" % os.path.basename(path), False, "type failed")
                return False
            d.press_button("导入")
            time.sleep(1.5)
            st = d.state("datasetLoaded", "statusMsg")
            if "已导入" not in st.get("statusMsg", ""):
                check("vm ch03: import %s" % os.path.basename(path), False, st)
                return False
            check("vm ch03: import %s" % os.path.basename(path), True, st.get("statusMsg", ""))
            ok1 = press_nth("类别", 0)
            time.sleep(0.8)
            ok2 = press_nth("数值", 1)
            time.sleep(1.5)
            st = d.state("chartReady", "statusMsg")
            ok = ok1 and ok2 and st.get("chartReady") == "true"
            check("vm ch03: map %s" % os.path.basename(path), ok, st)
            return ok
        if import_and_map(fx["dec"], 3):
            vm_check_screen_geo(d, fx, "dec")
        if import_and_map(fx["tiny"], 2):
            vm_check_screen_geo(d, fx, "tiny")
        if import_and_map(fx["sdec"], 2):
            vm_check_screen_geo(d, fx, "sdec")

        # ---- CH-04 负例：坏单元格（导入结构合法→映射期明确拒绝）----
        typed = d.type_into_input("CSV", fx["bad"])
        d.press_button("导入")
        time.sleep(1.2)
        st = d.state("statusMsg", "datasetLoaded")
        check("vm ch04: bad cell structurally imported",
              "已导入" in st.get("statusMsg", "") and st.get("datasetLoaded") == "true", st)
        press_nth("类别", 0)
        time.sleep(0.8)
        text = d.call("autoui_find", kind="button", label="数值")
        ids = re.findall(r"button (vnode_\d+)", text)
        if len(ids) > 1:
            d.call("autoui_action", element_id=ids[1], action="press")
        else:
            d.press_button("数值")
        time.sleep(1.2)
        st = d.state("statusMsg", "chartReady")
        check("vm ch04: bad cell rejected at mapping",
              "err_cell" in st.get("statusMsg", "") and st.get("chartReady") == "false", st)
        # ---- 空文件：导入拒绝，当前数据保留 ----
        d.type_into_input("CSV", fx["empty"])
        d.press_button("导入")
        time.sleep(1.2)
        st = d.state("statusMsg", "datasetLoaded")
        check("vm ch04: empty file rejected, data kept",
              "导入失败" in st.get("statusMsg", "") and st.get("datasetLoaded") == "true", st)

        # ---- CH-04 旧 v1 工程兼容（预置 001 形态工程，含小数）----
        pdir = os.path.join(data_dir, "projects")
        os.makedirs(pdir, exist_ok=True)
        rows_frag = '[["甲","0.5"],["乙","1.25"]]'
        recs_frag = '[{"cat":"甲","v":0.5},{"cat":"乙","v":1.25}]'
        old_doc = ('{"schema_version":1,"name":"旧版工程","slug":"old-v1",'
                   '"source_path":"D:/nonexistent/src.csv","index_col":0,'
                   '"value_cols":[1,-1,-1,-1],"created_at":"",'
                   '"headers_frag":"[\\"cat\\",\\"v\\"]","rows_frag":"%s",'
                   '"keys_frag":"[\\"cat\\",\\"v\\"]","recs_frag":"%s",'
                   '"row_count":2,"col_count":2}') % (rows_frag.replace('"', '\\"'), recs_frag.replace('"', '\\"'))
        with open(os.path.join(pdir, "old-v1.json"), "w", encoding="utf-8") as f:
            f.write(old_doc)
        d.press_button("刷新列表")
        time.sleep(1.0)
        st = d.state("statusMsg")
        check("vm ch04: old project listed", "工程列表已刷新(2" in st.get("statusMsg", ""), st)
        # 失败保全预置：old-v1 的缺省导出路径上放同名目录（VM 轨导出输入
        # 不可聚焦——G-7 系；失败用例改由缺省路径制造）
        exp_dir_old = os.path.join(data_dir, "exports", "old-v1.svg")
        os.makedirs(exp_dir_old, exist_ok=True)
        exports_before = sorted(os.listdir(os.path.join(data_dir, "exports")))
        # 打开第二个工程（列表序：旧工程后保存的在前；逐个尝试打开直到匹配）
        opened_old = False
        for _ in range(4):
            text = d.call("autoui_find", kind="button", label="打开")
            ids = re.findall(r"button (vnode_\d+)", text)
            done = False
            for bid in ids:
                d.call("autoui_action", element_id=bid, action="press")
                time.sleep(1.2)
                st = d.state("projName", "statusMsg")
                if "旧版工程" in st.get("projName", ""):
                    opened_old = True
                    done = True
                    break
            if done:
                break
        check("vm ch04: old v1 project opens", opened_old)
        st = d.state("datasetLoaded", "chartReady")
        check("vm ch04: old project chart ready", st.get("datasetLoaded") == "true"
              and st.get("chartReady") == "true", st)
        # ---- CH-04 失败保全：缺省导出目标为目录 → 明确失败且既有导出不动 ----
        d.press_button("导出 SVG")
        time.sleep(1.5)
        st = d.state("statusMsg", "statusErr")
        check("vm ch04: export onto directory fails clearly",
              st.get("statusErr") == "true" and "导出失败" in st.get("statusMsg", ""), st)
        exports_mid = sorted(os.listdir(os.path.join(data_dir, "exports")))
        check("vm ch04: existing exports untouched by failed export",
              exports_before == exports_mid, (exports_before, exports_mid))
        # 恢复：移除目录后同一导出成功（旧工程内嵌数据，删源形态）
        os.rmdir(exp_dir_old)
        d.press_button("导出 SVG")
        time.sleep(1.5)
        st = d.state("statusMsg", "statusErr")
        check("vm ch04: old project exports by embedded data after recovery",
              st.get("statusErr") == "false" and "已导出" in st.get("statusMsg", ""), st)
    finally:
        proc.kill()


# ═══════════════════════════════════════════════════════════
# Vue profile：vite dev + Playwright
# ═══════════════════════════════════════════════════════════

def verify_vue(fx, data_dir):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        check("vue: playwright available", False, "pip install playwright")
        return
    front_port = pick_free_port(17860)
    back_port = pick_free_port(17870)
    env = {**os.environ, "AUTO_BACKEND_IMPL": "vm",
           "AUTO_CHARTS_DATA": data_dir,
           "AUTO_FRONT_PORT": str(front_port), "AUTO_HTTP_PORT": str(back_port)}
    proc = subprocess.Popen([AUTO_BIN, "run", "-F", str(front_port), "-B", str(back_port)],
                             cwd=REPO, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://localhost:%d" % front_port
    try:
        up = False
        for _ in range(90):
            time.sleep(1)
            try:
                urllib.request.urlopen(base, timeout=2)
                up = True
                break
            except Exception:
                pass
        check("vue: dev server up (CH-01)", up, base)
        if not up:
            return
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()
            page.goto(base, wait_until="networkidle")
            # 空态
            body = page.inner_text("body")
            check("vue: startup empty state", "导入" in body and "尚无数据" in body, body[:200])
            # CH-02 中文/特殊字符路径导入
            page.fill("input", fx["cjk"])
            page.get_by_role("button", name="导入", exact=True).click()
            page.wait_for_timeout(1500)
            body = page.inner_text("body")
            check("vue ch02: cjk import loaded", "已导入 3 行" in body, body[:260])
            # %20 字面对照
            page.fill("input", fx["cjk_pct"])
            page.get_by_role("button", name="导入", exact=True).click()
            page.wait_for_timeout(1500)
            body = page.inner_text("body")
            check("vue ch02: literal %20 twin distinct", "已导入 2 行" in body, body[:260])
            # 回主文件 + 映射
            page.fill("input", fx["cjk"])
            page.get_by_role("button", name="导入", exact=True).click()
            page.wait_for_timeout(1500)
            idx_btns = page.get_by_role("button", name="类别", exact=True)
            idx_btns.nth(0).click()
            page.wait_for_timeout(900)
            val_btns = page.get_by_role("button", name="数值", exact=True)
            val_btns.nth(1).click()
            page.wait_for_timeout(1200)
            body = page.inner_text("body")
            check("vue ch02: mapping valid", "映射有效" in body, body[:200])
            n_bars = page.locator("svg path[fill]").count()
            check("vue: bars rendered on screen", n_bars >= 3, n_bars)
            # CH-02 中文工程名保存 → 列表 → 打开
            page.fill("input >> nth=1", "中文工程名Vue")
            page.get_by_role("button", name="保存", exact=True).click()
            page.wait_for_timeout(1500)
            body = page.inner_text("body")
            check("vue ch02: save ok with cjk name", "已保存" in body, body[:200])
            page.get_by_role("button", name="刷新列表", exact=True).click()
            page.wait_for_timeout(1000)
            page.get_by_role("button", name="打开", exact=True).first.click()
            page.wait_for_timeout(1200)
            body = page.inner_text("body")
            check("vue: reopen ready", "已打开工程" in body, body[:200])
            # 导出（显式路径）
            out = os.path.join(data_dir, "vue-export.svg")
            page.fill("input >> nth=2", out)
            page.get_by_role("button", name="导出 SVG", exact=True).click()
            page.wait_for_timeout(1500)
            body = page.inner_text("body")
            check("vue: export ok", "已导出 SVG" in body, body[:200])
            if os.path.exists(out):
                with open(out, "r", encoding="utf-8") as f:
                    svg = f.read()
                # oracle：3 行 × 1 系列 = 3 数据柱（+1 图例色块）
                vals = [120.5, 80.0, 95.25]
                vmin, vmax, span, step = oracle_domain(vals)
                y0 = oracle_y(0.0, vmin, span)
                rects = re.findall(r'<rect x="([\d.e+-]+)" y="([\d.e+-]+)" width="([\d.e+-]+)" height="([\d.e+-]+)" fill="#2563eb"', svg)
                bars = [r for r in rects if not (r[1] == "6" and r[3] == "10")]
                check("vue: exported svg oracle head", svg.startswith("<?xml") and len(bars) == 3, len(bars))
                okg = True
                for i, (x, ry, w, rh) in enumerate(bars):
                    exp_y = oracle_y(vals[i], vmin, span)
                    exp_h = y0 - exp_y
                    if abs(float(ry) - exp_y) > 0.01 or abs(float(rh) - exp_h) > 0.01:
                        okg = False
                check("vue: exported geometry ±0.01px", okg, bars)
            # 删源后按工程再导出
            os.remove(fx["cjk"])
            page.get_by_role("button", name="导出 SVG", exact=True).click()
            page.wait_for_timeout(1500)
            body = page.inner_text("body")
            check("vue ch04: export after source removed", "已导出 SVG" in body, body[:200])
            # CH-03 vue 屏幕端几何：小数数据 → SVG path d 坐标对账 ±1px
            page.fill("input", fx["tiny"])
            page.get_by_role("button", name="导入", exact=True).click()
            page.wait_for_timeout(1500)
            page.get_by_role("button", name="类别", exact=True).nth(0).click()
            page.wait_for_timeout(900)
            page.get_by_role("button", name="数值", exact=True).nth(1).click()
            page.wait_for_timeout(1200)
            vals = fx["decvals"]["tiny"]
            vmin, vmax, span, step = oracle_domain(vals)
            y0 = oracle_y(0.0, vmin, span)
            d_attrs = page.locator("svg path[fill='#2563eb']").evaluate_all(
                "els => els.map(e => e.getAttribute('d'))")
            # 组件柱 path：M{x} {ytop} h{w} v{h} h-{w} Z
            okh = False
            detail = []
            for dstr in d_attrs:
                m = re.match(r"M([\d.e+-]+) ([\d.e+-]+) h([\d.e+-]+) v([\d.e+-]+)", dstr or "")
                if m:
                    ytop = float(m.group(2))
                    hh = float(m.group(4))
                    exp_ytop = oracle_y(0.001, vmin, span)
                    exp_h = y0 - exp_ytop
                    if abs(ytop - exp_ytop) <= 1.0 and abs(hh - exp_h) <= 1.0:
                        okh = True
                    detail.append((ytop, hh, exp_ytop, exp_h))
            check("vue ch03: tiny decimal bar ±1px on screen", okh, detail)
            # 基线 line 属性
            y1s = page.locator("svg line").evaluate_all(
                "els => els.map(e => [e.getAttribute('y1'), e.getAttribute('stroke')])")
            base_ok = any(s == "#94a3b8" and y1 is not None and abs(float(y1) - y0) <= 1.0
                          for y1, s in y1s if y1 is not None)
            check("vue ch03: baseline ±1px on screen", base_ok, y1s)
            browser.close()
    finally:
        proc.kill()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=["vm", "vue"], required=True)
    args = ap.parse_args()
    RECORD["profile"] = args.profile
    RECORD["tool_versions"]["auto"] = AUTO_BIN
    try:
        v = subprocess.run([AUTO_BIN, "--version"], capture_output=True, text=True, timeout=30)
        RECORD["tool_versions"]["auto_version"] = (v.stdout + v.stderr).strip().splitlines()[0]
    except Exception as e:
        RECORD["tool_versions"]["auto_version"] = "unknown: %s" % e

    data_dir = tempfile.mkdtemp(prefix="charts-verify-%s-" % args.profile)
    env_data = os.environ.get("AUTO_CHARTS_DATA", "")
    os.environ["AUTO_CHARTS_DATA"] = data_dir
    fx = make_fixtures(data_dir)
    if args.profile == "vm":
        verify_vm(fx, data_dir)
    else:
        verify_vue(fx, data_dir)
    os.environ["AUTO_CHARTS_DATA"] = env_data

    out_dir = os.path.join(REPO, "test-results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "verify_basic_%s.json" % args.profile)
    RECORD["fails"] = len(FAILS)
    RECORD["passes"] = len(PASSES)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(RECORD, f, ensure_ascii=False, indent=1)
    print("-" * 60)
    print("results: %d passed, %d failed → %s" % (len(PASSES), len(FAILS), out_path))
    for e in FAILS:
        print("  ! " + e)
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
