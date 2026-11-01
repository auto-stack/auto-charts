# CHARTS-002 T-00 决策稿（standalone decision）

基线：`e5e91a9`（main，独立 clone `D:/autostack/auto-charts`，干净）。
探针日期：2026-11-01。所有结论来自本 clone 实测命令与运行输出（探针脚本
与原始输出在 `D:/autostack/plan-artifacts/plan-002/probes/`，不入仓），
非历史文档转述。来源版本：auto CLI `0.1.0+plan-890-verified-r7-t19-5-g55c98c7`
（`D:/autostack/auto-man/target/debug/auto.exe`）；auto-web `ec9c4ba`（读源
核对 `server_route.rs::url_decode`/`http_server.rs::bind_api_args_by_name`）。

## 0. 结论摘要（冻结）

1. **传输**：全部带业务参数端点（import/validate/save/export/get_project）
   迁移为 `POST` + 单一 `payload str` 整体 body 参数；前端以
   `json_escape_cell` 手工转义构造 JSON 对象文本，`Http.post(url, bodyText)`
   发送。VM 轨原样发送字符串（UTF-8 逐字到达）；vue 轨 `JSON.stringify`
   外包一层 JSON 字符串壳，端点按首字节（`"` vs `{`）剥壳后 `json.parse`。
   结构性端点（status/projects 列表）保留 GET。
2. **数值**：双端统一 float（VM float 实测 f64 语义、`.to_string()` 输出
   约 8 位有效数字）；后端解析由定点百位升级为十进制→float（≥0.001 量级
   区分）；域/基线/刻度/柱几何全部 float 化（屏幕与导出同式）；屏幕端
   `bar_chart.at` Init 的整数截断手术退役。oracle 以 Python float64 独立
   复算（屏幕 ±1px、导出 ±0.01px）。
3. **启动**：三形态实测全部可用（`auto service --server vm`、
   `AUTO_BACKEND_IMPL=vm auto run`、`AUTO_VM_WITH_HTTP=1 auto run -r vm`）；
   README 固化准备/启动命令；错误分类（端口占用/坏 tool）在 T-03 收口。
4. **owner 边界**：不写 auto-web/auto-lang/auto-ui；查询解码缺陷
   （`+`→空格、%XX latin-1）登记为框架既有缺陷，本计划以 POST body 绕开，
   不修复框架。AutoOS 组合版本不动。

## 1. 工具链（实测冻结）

| 项 | 实测值 |
|---|---|
| auto CLI | `auto 0.1.0+plan-890-verified-r7-t19-5-g55c98c7` |
| VM HTTP service | `auto service --server vm`（隔离 `AUTO_CHARTS_DATA` 实测 8080，status ok，即时解析 api.at） |
| Vue 轨 | `AUTO_BACKEND_IMPL=vm auto run -F/-B` 实测起来（Playwright 驱动） |
| VM 轨窗口 | `AUTOUI_MCP_PORT=<free> AUTO_VM_WITH_HTTP=1 auto run -r vm` 实测起来（MCP 驱动，1 次内就绪） |
| Python | 3.14.2（playwright 可用）；Node v25.2.1；pnpm 11.6.0 |

## 2. 传输链路实测（探针 P1/P2/P3 + 双轨真 UI）

### 2.1 服务端绑定（VM HTTP，auto-web ec9c4ba）

| 探针 | 请求形态 | 结果 | 判定 |
|---|---|---|---|
| P1a | GET query，原始 UTF-8 CJK（Python 原始字节直发） | 逐字到达 `中文目录/工程名` | 仅证明服务端不再二次破坏原始 UTF-8 |
| P1b | GET query，字面 `+` | 解码为空格 `a b` | **缺陷**：`+` 值经 query 必坏 |
| P1c | GET query，%XX 编码 CJK（vue fetch 实际产物） | latin-1 乱码 `ä¸­æ` | **G-6b 未修复**（owner auto-web） |
| P1d | GET query，字面 `&` | query 结构断裂，值截断 | 结构性不可用 |
| P2a | POST JSON body 标量参数（`v/w str`） | **逐字到达**（含 `+ & # ? = % "`） | **UTF-8 安全线** |
| P2b | POST body 含换行/引号 | 逐字到达 | 转义链完整 |
| P2c | POST body 为 JSON 字符串标量 | 400 `missing param` | 字符串外壳喂不进按名绑定 |
| P3  | POST 任意 body + 单一 str 形参 | **整个 body 逐字到达**（whole-body 容忍） | 设计所选通道 |
| P3b | POST 字符串标量 + 单 str 形参 | 到达（带 JSON 引号壳，len 含壳） | vue 外壳可端点内剥离 |

### 2.2 前端双轨实测（真实 UI，CH-02 反例先行）

| 状态 | vue 轨 | VM 轨 |
|---|---|---|
| **红态（迁移前，GET+query）** | `中文 目录+A&B#C%D=E` 路径导入失败：`err_not_found ... ä¸­æ å½ A`（乱码+`+`→空格+`&`截断三重破坏） | 同路径导入失败：`file not found: ä¸­æ...`（**当前 VM 运行时 Http 客户端对非 ASCII 查询自行百分号编码**——001 时「VM 原始 UTF-8 正常」的结论已漂移，两轨现均红） |
| **POST record 字面量探针** | **绿**：`已导入 3 行 × 2 列`（CJK/`+&#%=` 路径逐字到达） | **红**：`file not found: 18443647848969734425`（record→内部句柄串，001 G-6a 在当前版本复现） |

结论：`Http.post(url, record)` 双轨不兼容（VM 坏）；`Http.post(url, str)`
VM 轨原样发送（shim_http_post 经 `VMConvertible→String`，str 为恒等），
vue 轨外包 JSON 字符串壳——两端点内剥壳即可单源兼容。**冻结**：
迁移端点一律 `POST` + 单 `payload str` 形参（形参名不与 body 键重名，
走 whole-body 容忍路径，已由 P3 证实）；端点内：trim 后首字节 `"` →
`json.parse` 剥壳取内层字符串，再 `json.parse` 取对象；首字节 `{` →
直接 `json.parse`。前端 body 构造沿用本仓手工转义纪律
（`json_escape_cell`；`+ s` 浮点直拼禁令见 §3）。

`json.from_value` 仅 VM 轨实现（auto-ui-compiler 全库无翻译），排除；
`Http.post_json` vue 轨无翻译，排除；GET+query 对 CJK/`+`/`&`/# 值两轨
皆不可用，排除。

### 2.3 兼容承诺

v1 工程格式与既有合法 GET API 不变（保留原 GET 端点同时存在，过渡期
不删除；T-01 起前端全部走 POST）。旧有缺陷（query 解码）不承诺永久不变。

## 3. 数值策略实测（探针 P4 + 源核对）

`GET /api/v1/px_float` 实测输出：

```json
{"sum":[1050253722,0.3],"y":"122.85714","t1":"0.001","t2":"0.002",
 "cmp":1,"distinct":1,"big":"10000000","neg":"-0.5","hundredth":"25.5"}
```

| 事实 | 证据 | 冻结纪律 |
|---|---|---|
| float 拼接陷阱 | `" + s + "`（无 to_string）输出 `1050253722`（f64 位型重解释） | 浮点进字符串**必须** `.to_string()` |
| 输出格式 | `122.85714285714286 → "122.85714"`（8 位有效数字，四舍五入） | `.to_string()` ≈ `%.8g`；oracle 容差按此校准（±0.01px 远宽于 8 位精度） |
| 小数区分 | `0.001` vs `0.002`：串不等、`>` 成立（distinct=1, cmp=1） | f64 语义满足计划必需用例 |
| 大值精度 | `10000000.001 → "10000000"` | 超出 8 位有效数字的差异不承诺（|v| 接近 1e7 预算上限时小数尾部不保） |
| 001 门漂移 | 001 probe 断言 `y="122.85713"`，当前运行时输出 `122.85714` | 旧断言随运行时格式漂移失效，T-04 以容差断言（非字面串）重建 |

**冻结策略**：数值解释统一 float（f64）；语法仍 `[+-]?digits[.digits]`
（无指数）；后端 `parse_dec_hundredths`（int 百位）退役，新增十进制→float
解析：整数部分 int 累积（>9 位→err_value_range），小数部分逐位累积至
15 位（其后差异低于 f64 表示精度，不承诺）；`|v| ≤ 10,000,000` float 比较。
域/步长/刻度/柱几何（`vmin/vmax/span/step/y(v)`）双端全部 float 化，
全零退化仍为 [0,1]；基线 y(0)；刻度标签 `to_string()`（0.001→"0.001"、
±0.5→"-0.5"/"0.5"、0.0005→"0.0005"），tick==0 归一为 "0"；屏幕 ≤5 刻度、
导出全量刻度的既有合同不变。CSV 原文存储面（rows_frag）仍逐字字符串，
不改写。

## 4. 独立启动（AC-01）

三形态本会话全部实测启动成功（§1）。README 固化：

- 准备：安装 `auto` CLI；本仓根 `auto build -r vm`（VM 轨产物，ninja）；
  vue 轨由 `auto run` 即时生成 dev 工程（无独立预构建步骤）。
- 启动：vue+VM HTTP：`$env:AUTO_BACKEND_IMPL='vm'; auto run`（:17850/:17851，
  `-F/-B` 可覆）；VM 窗口+VM HTTP：`$env:AUTO_VM_WITH_HTTP='1'; auto run -r vm`；
  纯后端：`auto service --server vm`（8080）。
- 隔离：`AUTO_CHARTS_DATA` 指向本次进程私有目录；只管理本次进程，不清理
  共享框架 target。
- 错误分类（T-03 收口并落 README）：端口占用→启动明确失败非零，不碰
  既有实例；坏 tool（CLI 缺失/版本不符）→明确失败；冷准备（首次生成/
  构建）有界超时提示。

## 5. 预算对账（与 Spec 差异，T-00 逐项核对）

| 维度 | 001 Spec/实现 | 本轮实测 | 处置 |
|---|---|---|---|
| 文件 ≤10MiB、行 ≤10000、列 ≤64、数值列 1..4 | 一致 | 源码 `csv.at`/`chart_project.at` 与 Spec 一致 | 不变 |
| 单元格值域 `|v| ≤ 10,000,000` | 百位定点 i32 | float 化后语义不变 | SD-01 修改「定点百位」表述为 float 精度策略 |
| 屏幕整数域（G-8）/导出百位 | 已声明边界 | 本轮废除该边界，双端同 float | SD-01 修改 |
| CJK 查询参数（G-6b）/GET+query（G-6a） | 已声明边界（owner auto-lang→实际 auto-web） | 本轮以 POST body 闭合 app 层；框架缺陷原样登记 | SD-01 修改；owner 记 auto-web |

## 6. 尚待运行验证的假说（实现期闭合）

1. VM 轨 `Http.post(url, str)` 真窗实测（shim 源码判读为恒等发送；T-01
   CH-02 回放闭合）。
2. vue/VM `json.parse` 对 str 端点双层编码的既有消费模式在 POST 响应上
   对称（001 已证 GET；T-01 回放闭合）。
3. 屏幕端 float 域在 VM 组件 Init 的渲染结果与独立 oracle 一致（T-02
   CH-03 闭合）。
4. 删源重开/失败保全在 POST 迁移后保持（T-03/T-04 CH-04 闭合）。
