#!/usr/bin/env python3
# verify_basic.py — CHARTS-001 基础能力验收调度入口（T-05）。
#
# 双 profile 真实任务验收（AC-01..04）：导入真实 CSV → 列映射 → 图表 →
# 保存 → 重开 → 导出 SVG，含独立 CSV/几何/XML oracle 与失败路径。
#   --profile vm   : `auto run -r vm` 真实窗口 + AUTOUI_MCP_PORT 驱动
#   --profile vue  : `AUTO_BACKEND_IMPL=vm auto run`(:17850) + Playwright chromium
#
# 隔离：每次运行创建临时 AUTO_CHARTS_DATA 数据目录与空闲 MCP/前端端口，
# 不接触真实用户数据。记录源码/工具版本、fixture hash 与逐项结果。
# 任何 FAIL 以退出码 1 结束。
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


def make_fixtures(root):
    """V-01/V-02 素材：BOM+中文+引号内逗号换行；[-5,0,10] 正负零与转义。"""
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
    for k, p in fx.items():
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
        text = self.call("autoui_find", kind="input")
        ids = re.findall(r"input (vnode_\d+)", text)
        if not ids:
            return False
        for attempt in range(4):
            self.call("autoui_action", element_id=ids[0], action="press")
            time.sleep(0.4)
            self.call("autoui_type", text=value)
            time.sleep(0.6)
            st = self.state("csvPath")
            got = st.get("csvPath", "").strip('"').replace("\\\\", "/").replace("\\", "/")
            want = value.replace("\\", "/")
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


def verify_vm(fx, data_dir):
    mcp_port = pick_free_port(19520)
    # AUTO_VM_WITH_HTTP=1 → split 模式：真实 VM HTTP 后端（lazy back 孵化）
    # + VM 窗口（run_vm.rs PLAN-026 路径）；merged 模式无 HTTP 服务器。
    env = {**os.environ, "AUTOUI_MCP_PORT": str(mcp_port),
           "AUTO_CHARTS_DATA": data_dir, "AUTO_VM_WITH_HTTP": "1"}
    # 窗口启动是环境级 flake（desktop_mcp.py 同款：MCP 不 bind 时杀掉重拉）
    proc = None
    d = None
    for attempt in range(3):
        if proc is not None:
            proc.kill()
            time.sleep(1.5)
        proc = subprocess.Popen([AUTO_BIN, "run", "-r", "vm"], cwd=REPO, env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
    check("vm: window ready after retries", d is not None)
    try:
        if d is None:
            raise RuntimeError("window failed to start after 3 attempts")
        st = d.state("statusMsg", "datasetLoaded", "chartType")
        # ---- 空态 ----
        st = d.state("statusMsg", "datasetLoaded", "chartType")
        check("vm: startup empty state", st.get("datasetLoaded") == "false"
              and "导入" in st.get("statusMsg", ""), st)
        check("vm: default chartType=bar", st.get("chartType") == '"bar"', st)

        # ---- V-01 导入（BOM/中文/引号内逗号换行）----
        typed = d.type_into_input("CSV", fx["rich"])
        check("vm: path typed", typed)
        time.sleep(0.3)
        d.press_button("导入")
        time.sleep(1.2)
        st = d.state("datasetLoaded", "statusMsg", "statusErr")
        check("vm: rich import loaded", st.get("datasetLoaded") == "true", st)
        check("vm: rich import ok status", st.get("statusErr") == "false"
              and "已导入" in st.get("statusMsg", ""), st)

        # ---- 列映射：类别=月份(0) 数值=桌面(1) ----
        # （headerRows 为记录列表，读状态会挂 MCP——映射改按按钮序驱动）
        def press_nth(label, n):
            text = d.call("autoui_find", kind="button", label=label)
            ids = re.findall(r"button (vnode_\d+)", text)
            if len(ids) <= n:
                return False
            d.call("autoui_action", element_id=ids[n], action="press")
            return True
        check("vm: set index col", press_nth("类别", 0))
        time.sleep(1.0)
        # 数值按钮按列序: nth(1)=桌面(含 "1,200" 负例)
        check("vm: set value col1", press_nth("数值", 1))
        time.sleep(1.2)
        st = d.state("chartReady", "statusMsg", "statusErr")
        check("vm: mapping blocked on bad cell", st.get("chartReady") == "false", st)

        # ---- 屏幕端几何（AC-02 组件侧）：符号域合同同式复算 ----
        # rich: v1 列 = [1200(千分位? 无→"1,200" 非法!), ...] —— 注意:
        # fixture 的 "1,200" 引号内含逗号 → 单元格为 "1,200" → 非法数值!
        # 这是刻意的负例：映射 v0=桌面 列 → err_cell 行2 列1。
        st = d.state("chartReady", "statusMsg")
        check("vm: comma-number cell rejected with row/col",
              st.get("chartReady") == "false" and "err_cell" in st.get("statusMsg", "")
              and "行2" in st.get("statusMsg", "") and "列1" in st.get("statusMsg", ""), st)
        # 改映射:摘除桌面(nth(1) 再按)→ 勾移动(nth(2)) → [-300,0,25.5] 出图
        check("vm: unset value col1", press_nth("数值", 1))
        time.sleep(0.8)
        check("vm: set value col2", press_nth("数值", 2))
        time.sleep(1.2)
        st = d.state("chartReady", "statusMsg")
        check("vm: remap to col2 valid", st.get("chartReady") == "true", st)
        geo = {}
        for _ in range(8):
            geo = d.state("barBaseY", "barGrid", "barTick4", "barTick3", "barTick2", "barTick1", "barTick0")
            gp = geo.get("barGrid", "")
            if gp.startswith('"') and "H550" in gp:
                break
            time.sleep(0.8)
        # v1'=移动 列: 值 [-300,0,25.5] vmin=-300 vmax=25.5→hundredths 端
        # 组件 int 域:值来自字符串 d[f] — "25.5" 在组件 int 几何下…
        # 组件接收 int(记录值为字符串时 VM 动态读取)。冻结合同:组件刻度
        # 阶梯与基线公式与导出一致;此处断言基线 < 260(负值存在)与含负刻度。
        baseline = geo.get("barBaseY", "")
        try:
            bv = float(baseline.strip('"'))
        except Exception:
            bv = -1
        check("vm: signed baseline above bottom", 20 < bv < 260, geo)
        neg_tick = False
        for k in ("barTick4", "barTick3", "barTick2", "barTick1", "barTick0"):
            v = geo.get(k, "").strip('"')
            if v.startswith("-"):
                neg_tick = True
        check("vm: negative y tick present", neg_tick, geo)

        # ---- V-03 保存（工程名已由导入预填）→ 列表 → 打开 ----
        st = d.state("projName")
        check("vm: project name prefilled", st.get("projName", "") not in ('""', ''), st)
        d.press_button("保存")
        time.sleep(1.2)
        st = d.state("statusMsg", "statusErr")
        check("vm: save ok", st.get("statusErr") == "false"
              and "已保存" in st.get("statusMsg", ""), st)
        d.press_button("刷新列表")
        time.sleep(1.0)
        st = d.state("statusMsg")
        check("vm: project listed", "工程列表已刷新(1" in st.get("statusMsg", ""), st)
        check("vm: reopen project", d.press_button("打开"))
        time.sleep(1.2)
        st = d.state("datasetLoaded", "chartReady", "projName", "statusMsg")
        check("vm: reopened project ready", st.get("datasetLoaded") == "true"
              and st.get("chartReady") == "true"
              and "已打开工程" in st.get("statusMsg", "")
              and st.get("projName", "") not in ('', '""'), st)

        # ---- 导出（源仍在；再删源后按工程导出）----
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
        os.remove(fx["rich"])
        d.press_button("导出 SVG")
        time.sleep(1.5)
        st = d.state("statusMsg", "statusErr")
        check("vm: export by project after source removed",
              st.get("statusErr") == "false" and "已导出" in st.get("statusMsg", ""), st)

        # ---- 负例：坏单元格（导入结构合法→映射期明确拒绝）----
        d.type_into_input("CSV", fx["bad"])
        d.press_button("导入")
        time.sleep(1.2)
        st = d.state("statusMsg", "datasetLoaded")
        check("vm: bad cell structurally imported",
              "已导入" in st.get("statusMsg", "") and st.get("datasetLoaded") == "true", st)
        d.press_button("类别")
        time.sleep(0.8)
        text = d.call("autoui_find", kind="button", label="数值")
        ids = re.findall(r"button (vnode_\d+)", text)
        if len(ids) > 1:
            d.call("autoui_action", element_id=ids[1], action="press")
        else:
            d.press_button("数值")
        time.sleep(1.2)
        st = d.state("statusMsg", "chartReady")
        check("vm: bad cell rejected at mapping",
              "err_cell" in st.get("statusMsg", "") and st.get("chartReady") == "false", st)
        # ---- 空文件：导入拒绝，当前数据保留 ----
        d.type_into_input("CSV", fx["empty"])
        d.press_button("导入")
        time.sleep(1.2)
        st = d.state("statusMsg", "datasetLoaded")
        check("vm: empty file rejected, data kept",
              "导入失败" in st.get("statusMsg", "") and st.get("datasetLoaded") == "true", st)
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
        for _ in range(60):
            time.sleep(1)
            try:
                urllib.request.urlopen(base, timeout=2)
                up = True
                break
            except Exception:
                pass
        check("vue: dev server up", up, base)
        if not up:
            return
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()
            page.goto(base, wait_until="networkidle")
            # 空态
            body = page.inner_text("body")
            check("vue: startup empty state", "导入" in body and "尚无数据" in body, body[:200])
            # V-01 导入
            page.fill("input", fx["signed"])
            page.get_by_role("button", name="导入", exact=True).click()
            page.wait_for_timeout(1200)
            body = page.inner_text("body")
            check("vue: signed import loaded", "已导入" in body, body[:200])
            # 映射：类别 col0、数值 col1、col2
            idx_btns = page.get_by_role("button", name="类别", exact=True)
            idx_btns.nth(0).click()
            page.wait_for_timeout(800)
            val_btns = page.get_by_role("button", name="数值", exact=True)
            val_btns.nth(1).click()
            page.wait_for_timeout(800)
            val_btns = page.get_by_role("button", name="数值", exact=True)
            val_btns.nth(2).click()
            page.wait_for_timeout(1200)
            body = page.inner_text("body")
            check("vue: mapping valid", "映射有效" in body, body[:200])
            # 图表渲染（组件柱为 path 元素；导出 SVG 才是 rect）
            n_bars = page.locator("svg path[fill]").count()
            check("vue: bars rendered on screen", n_bars >= 3, n_bars)
            # 保存
            page.fill("input >> nth=1", "验收工程Vue")
            page.get_by_role("button", name="保存", exact=True).click()
            page.wait_for_timeout(1200)
            body = page.inner_text("body")
            check("vue: save ok", "已保存" in body, body[:200])
            # 打开（刷新列表 → 打开）
            page.get_by_role("button", name="刷新列表", exact=True).click()
            page.wait_for_timeout(900)
            page.get_by_role("button", name="打开", exact=True).first.click()
            page.wait_for_timeout(1200)
            body = page.inner_text("body")
            check("vue: reopen ready", "已打开工程" in body, body[:200])
            # 导出（显式路径便于断言）
            out = os.path.join(data_dir, "vue-export.svg")
            page.fill("input >> nth=2", out)
            page.get_by_role("button", name="导出 SVG", exact=True).click()
            page.wait_for_timeout(1500)
            body = page.inner_text("body")
            check("vue: export ok", "已导出 SVG" in body, body[:200])
            if os.path.exists(out):
                with open(out, "r", encoding="utf-8") as f:
                    svg = f.read()
                check("vue: exported svg oracle head",
                      svg.startswith("<?xml") and svg.count("<rect") == 8, len(svg))
            # 删源后按工程再导出
            os.remove(fx["signed"])
            page.get_by_role("button", name="导出 SVG", exact=True).click()
            page.wait_for_timeout(1500)
            body = page.inner_text("body")
            check("vue: export after source removed", "已导出 SVG" in body, body[:200])
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
