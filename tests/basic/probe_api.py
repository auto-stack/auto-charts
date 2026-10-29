#!/usr/bin/env python3
# probe_api.py — CHARTS-001 后端 HTTP 探针（stdlib only）。
# 前置：`auto service --server vm`（或 auto run 懒孵化后端）已在本机端口运行，
#       AUTO_CHARTS_DATA 指向隔离目录。
# 用法：python tests/basic/probe_api.py [base_url]
#       base_url 缺省 http://127.0.0.1:8080
# 输出：PASS/FAIL 行 + 摘要；任何 FAIL 退出码 1。
import json
import os
import socket
import sys
import tempfile
import urllib.request


def q(s):
    # 查询值编码：仅 % 与空格；CJK 保持原始 UTF-8（服务端 %XX 按 latin-1 解）
    return s.replace('%', '%25').replace(' ', '%20')

BASE = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PROBE_BASE", "http://127.0.0.1:8080")
FAILS = []


def _raw_request(method, path):
    """原始 UTF-8 请求行（http.client 只能 ASCII；服务端 %XX 解码按
    latin-1 逐字节会乱码——G-6b，故 CJK 查询值走原始 UTF-8 字节）。"""
    host, port = urllib.request.urlparse(BASE).hostname, urllib.request.urlparse(BASE).port or 80
    payload = (method + " " + path + " HTTP/1.1\r\nHost: " + host
               + "\r\nConnection: close\r\n\r\n").encode("utf-8")
    s = socket.create_connection((host, port), timeout=60)
    s.sendall(payload)
    buf = b""
    while True:
        chunk = s.recv(65536)
        if not chunk:
            break
        buf += chunk
    s.close()
    head, _, body = buf.partition(b"\r\n\r\n")
    return body.decode("utf-8", "replace")


def req(method, path, body=None, raw=False):
    data = None if body is None else json.dumps(body).encode("utf-8")
    try:
        (path).encode("ascii")
        nonascii = False
    except UnicodeEncodeError:
        nonascii = True
    if nonascii and method == "GET" and data is None:
        text = _raw_request(method, path)
    else:
        r = urllib.request.Request(BASE + path, data=data, method=method)
        if data:
            r.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(r, timeout=60) as resp:
            text = resp.read().decode("utf-8")
    if raw:
        return text
    v = json.loads(text)
    if isinstance(v, str):  # str 端点双层编码（reader 同款）
        v = json.loads(v)
    return v


def check(cond, name, detail=""):
    if cond:
        print("PASS " + name)
    else:
        FAILS.append(name)
        print("FAIL " + name + (" :: " + str(detail)[:400] if detail else ""))


def main():
    data_dir = os.environ.get("AUTO_CHARTS_DATA", "")
    tmp = tempfile.mkdtemp(prefix="charts-probe-") if not data_dir else None
    workdir = data_dir if data_dir else tmp
    os.makedirs(workdir, exist_ok=True)

    # 0. status
    st = req("GET", "/api/v1/status")
    check(st.get("ok") is True, "status ok", st)

    # NOTE: 导入/校验/保存/导出为 GET+query（双轨 Http body 编码分歧，G-6）。
    # 1. 基本 CSV（UTF-8 中文表头 + 负值 + 零）
    csv_path = os.path.join(workdir, "basic.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("名称,一月,二月\nA,10,20\nB,-5,0\nC,2.5,1\n")
    ds = req("GET", "/api/v1/import?path=" + q(csv_path))
    check(ds.get("ok") is True, "import basic ok", ds)
    check(ds.get("headers_frag") == '["名称","一月","二月"]', "headers frag", ds.get("headers_frag"))
    check(ds.get("row_count") == 3 and ds.get("col_count") == 3, "counts 3x3", ds)
    rows = json.loads(ds["rows_frag"])
    check(rows[1][1] == "-5" and rows[2][1] == "2.5", "cells verbatim", rows)

    # 2. BOM + 引号内逗号/换行/双引号
    csv2 = os.path.join(workdir, "quoted.csv")
    with open(csv2, "w", encoding="utf-8-sig", newline="") as f:
        f.write('label,note,val\n"has,comma","line1\nline2","say ""hi"""\nx,y,3\n')
    ds2 = req("GET", "/api/v1/import?path=" + q(csv2))
    check(ds2.get("ok") is True, "import quoted ok", ds2)
    r2 = json.loads(ds2["rows_frag"])
    check(r2[0][0] == "has,comma", "comma in quotes", r2)
    check(r2[0][1] == "line1\nline2", "newline in quotes kept", r2)
    check(r2[0][2] == 'say "hi"', "escaped quotes folded", r2)
    check(ds2.get("headers_frag") == '["label","note","val"]', "BOM stripped", ds2.get("headers_frag"))

    # 3. 坏数值：明确行列，不置 0
    csv3 = os.path.join(workdir, "badnum.csv")
    with open(csv3, "w", encoding="utf-8") as f:
        f.write("cat,v\nok,1\nbad,abc\n")
    vr = req("GET", "/api/v1/validate?path=" + q(csv3) + "&index_col=0&v0=1&v1=-1&v2=-1&v3=-1")
    check(vr.get("ok") is False and vr.get("err_code") == "err_cell", "bad cell rejected", vr)
    check(vr.get("err_row") == 3 and vr.get("err_col") == 1, "bad cell row/col", vr)

    # 4. 形状错误（ragged 行）
    csv4 = os.path.join(workdir, "ragged.csv")
    with open(csv4, "w", encoding="utf-8") as f:
        f.write("a,b\n1,2\n3\n")
    ds4 = req("GET", "/api/v1/import?path=" + q(csv4))
    check(ds4.get("ok") is False and ds4.get("err_code") == "err_shape" and ds4.get("err_row") == 3,
          "ragged row reported", ds4)

    # 5. 空文件
    csv5 = os.path.join(workdir, "empty.csv")
    open(csv5, "w", encoding="utf-8").close()
    ds5 = req("GET", "/api/v1/import?path=" + q(csv5))
    check(ds5.get("ok") is False and ds5.get("err_code") == "err_empty", "empty rejected", ds5)

    # 6. 缺文件
    ds6 = req("GET", "/api/v1/import?path=" + q(os.path.join(workdir, "nope.csv")))
    check(ds6.get("ok") is False and ds6.get("err_code") == "err_not_found", "missing file", ds6)

    # 7. 保存工程（内嵌数据）→ 列表 → 读取
    sv = req("GET", "/api/v1/save?name=" + q("探针工程 One")
             + "&path=" + q(csv_path) + "&index_col=0&v0=1&v1=2&v2=-1&v3=-1")
    check(sv.get("ok") is True, "save ok", sv)
    pid = sv.get("id", "")
    check(pid != "", "save id nonzero", sv)
    ls = req("GET", "/api/v1/projects")
    check(any(p.get("id") == pid and p.get("corrupt") is False for p in ls.get("projects", [])),
          "project listed", ls)
    gp = req("GET", "/api/v1/projects/" + pid)
    check(gp.get("schema_version") == 1 and gp.get("name") == "探针工程 One", "get project", gp)
    check(gp.get("rows_frag") == ds.get("rows_frag"), "data embedded verbatim", gp)

    # 8. 同名覆盖 vs 异名冲突
    sv2 = req("GET", "/api/v1/save?name=" + q("探针工程 One")
             + "&path=" + q(csv_path) + "&index_col=0&v0=1&v1=-1&v2=-1&v3=-1")
    check(sv2.get("ok") is True and sv2.get("id") == pid, "same-name save overwrites own", sv2)
    sv3 = req("GET", "/api/v1/save?name=" + q("探针工程/One")
             + "&path=" + q(csv_path) + "&index_col=0&v0=1&v1=-1&v2=-1&v3=-1")
    check(sv3.get("ok") is False and sv3.get("err_code") == "err_exists", "slug collision explicit", sv3)

    # 9. 导出 SVG（按工程）→ 删源后仍可导出（V-03 语义）
    out1 = os.path.join(workdir, "probe-export.svg")
    ex = req("GET", "/api/v1/export?project_id=" + pid + "&path=&name=&index_col=0&v0=1&v1=2&v2=-1&v3=-1&out_path=" + q(out1))
    check(ex.get("ok") is True, "export by project ok", ex)
    with open(out1, "r", encoding="utf-8") as f:
        svg = f.read()
    check(svg.startswith("<?xml") and "<svg" in svg and "</svg>" in svg, "svg well-formed head", svg[:80])
    check('fill="#2563eb"' in svg and 'fill="#16a34a"' in svg, "two series bars present", svg)
    os.remove(csv_path)  # 删源
    out2 = os.path.join(workdir, "probe-export-2.svg")
    ex2 = req("GET", "/api/v1/export?project_id=" + pid + "&path=&name=&index_col=0&v0=1&v1=2&v2=-1&v3=-1&out_path=" + q(out2))
    check(ex2.get("ok") is True, "export after source removed", ex2)

    # 10. 按源导出 + 缺源明确报错
    ex3 = req("GET", "/api/v1/export?project_id=&path=" + q(csv_path)
              + "&name=x&index_col=0&v0=1&v1=-1&v2=-1&v3=-1&out_path=")
    check(ex3.get("ok") is False and ex3.get("err_code") == "err_not_found", "export by moved source fails clearly", ex3)

    # 11. SVG 内容 oracle：[-5,0,10] 方向/比例/转义
    csv7 = os.path.join(workdir, "signed.csv")
    with open(csv7, "w", encoding="utf-8") as f:
        f.write('cat,v1,v2\n"neg,<tag>&",10,-20\nzero,0,0\npos,-5,15\n')
    vr7 = req("GET", "/api/v1/validate?path=" + q(csv7) + "&index_col=0&v0=1&v1=2&v2=-1&v3=-1")
    check(vr7.get("ok") is True, "signed data validates", vr7)
    out3 = os.path.join(workdir, "signed.svg")
    ex4 = req("GET", "/api/v1/export?project_id=&path=" + q(csv7)
              + "&name=signed&index_col=0&v0=1&v1=2&v2=-1&v3=-1&out_path=" + q(out3))
    check(ex4.get("ok") is True, "signed export ok", ex4)
    with open(out3, "r", encoding="utf-8") as f:
        ssvg = f.read()
    check("&amp;" in ssvg and "&lt;" in ssvg, "xml escape", ssvg)
    check(ssvg.count("<rect") == 8, "six bars + two legend swatches", ssvg.count("<rect"))
    # 独立几何 oracle（同式复算）：vmin=-20,vmax=15,span=35；
    # y(v)=260-(v+20)/35*240；neg 行 v2=-20 → rect 应锚在基线 y0≈122.857 且向下延伸
    y0 = 260 - (0 + 20) / 35 * 240
    check('y="122.85713"' in ssvg, "negative bars anchored at computed baseline", ssvg)
    check(abs(y0 - 122.85714285714286) < 1e-6, "oracle sanity", y0)
    check('height="137.14287"' in ssvg, "negative bar height (20/35*240)", ssvg)
    check('height="102.85713"' in ssvg, "positive bar height (15/35*240)", ssvg)
    check('height="0"' in ssvg, "zero bar renders zero height", ssvg)

    print("-" * 50)
    total_fail = len(FAILS)
    print(f"probe fails={total_fail}")
    if FAILS:
        for f_ in FAILS:
            print("  ! " + f_)
        sys.exit(1)


if __name__ == "__main__":
    main()
