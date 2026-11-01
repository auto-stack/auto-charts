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
2. **数值**：双端统一 float（VM float 实测 **f32**、`.to_string()` ≈%.8g；
   修正 T-00 初判 f64，证据见 §3）；后端解析由定点百位升级为十进制→float
   （≥0.001 量级区分）；域/基线/刻度/柱几何全部 float 化；刻度标签
   (k,m,e) 整数重构；屏幕端组件数据面改吃 `rows_frag` 字符串单元（VM 轨
   JSON 数字小数在数据通道归零，§6-D1）+ 调用位 `key:` 绑数据代际强制
   重算（§6-D2）；001 的整数截断手术退役。oracle 以 Python f64 独立复算
   （屏幕 ±1px、导出 ±0.01px），标签按同式整数重构逐字对账。
3. **启动**：三形态实测全部可用（`auto service --server vm`、
   `AUTO_BACKEND_IMPL=vm auto run`、`AUTO_VM_WITH_HTTP=1 auto run -r vm`）；
   README 固化准备/启动命令；端口占用实测明确失败非零不碰既有实例。
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

## 3. 数值策略实测（探针 P4 + 实现期修正）

`GET /api/v1/px_float` 实测输出（T-00）：

```json
{"sum":[1050253722,0.3],"y":"122.85714","t1":"0.001","t2":"0.002","cmp":1,"distinct":1,"big":"10000000","neg":"-0.5","hundredth":"25.5"}
```

T-02 实现期以 `px_ticks` 透视修正一项 T-00 判读：**VM float = f32**
（非 f64）。证据：`raw - raw/1e7` 实际改变值（`0.0005 → 0.00049999997`，
f32 ulp ≈5.8e-11）；阶梯种子 `1/10/10/10/10 = 0.00009999999`；f32 同样
解释 T-00 全部输出（`0.1+0.2→"0.3"`、`122.85714`=%.8g(f32(122.857143))）。

| 事实 | 证据 | 冻结纪律 |
|---|---|---|
| float 拼接陷阱 | `" + s + "`（无 to_string）输出 `1050253722`（f32 位型重解释） | 浮点进字符串**必须** `.to_string()`/插值 |
| 宽度 | f32（约 7 位十进制有效数字） | `0.001` vs `0.002` 可区分（cmp=1）；`10000000.001→"10000000"`——超出 f32 表示的差异不承诺 |
| 输出格式 | `122.857142857 → "122.85714"`（≈8 位有效数字） | `.to_string()` ≈ `%.8g`；oracle 几何容差 ±0.01px/±1px 远宽于该精度 |
| 标签噪声 | f32 档位种子使 k·step 浮点路径经 %.8g 输出 `0.00049999997` | **刻度标签 = (k,m,e) 整数重构**（`label_of_k`，双端同式），与 float 宽度无关；oracle 以同式整数重构对账 |
| 阶梯边界 | 除法种子在 5e-4 边界跌档（`base*5 ≥ raw` 差 1 ulp 失败） | 阶梯含负指数档（Spec 公式 k∈ℤ）+ 1e-7 相对边界容差；相邻档差 ≥1.6× 不会误选 |
| 001 门漂移 | 001 probe 断言 `y="122.85713"`，当前运行时输出 `122.85714` | 旧断言随运行时格式漂移失效，T-04 改容差/整数重构断言 |

**冻结策略**：数值解释统一 float（VM=f32；oracle 以 Python f64 独立复算，
容差吸收宽度差）；语法仍 `[+-]?digits[.digits]`（无指数）；后端
`parse_dec_hundredths`（int 百位）退役，新增十进制→float 解析（整数部分
int 累积 >9 位→err_value_range；小数逐位累积至 15 位，其后差异低于表示
精度）；`|v| ≤ 10,000,000`。域/步长/刻度/柱几何双端全部 float 化（组件
侧数据面吃 `rows_frag` 字符串单元 + 组件内 `parse_decimal`，见 §6-D1）；
全零退化 [0,100]；基线 y(0)；刻度标签 `label_of_k(k,m,e)` 整数重构
（"0.0005"、"-0.5"、"0.0015"）；屏幕 ≤5 刻度自底向上、导出全量的既有
合同不变。CSV 原文存储面（rows_frag）仍逐字字符串，不改写。
（注：001 Spec §3「全零退化为 [0,1]」与实现 [0,100] 不符，SD-01 修文字。）

## 4. 独立启动（AC-01）

三形态本会话全部实测启动成功（§1）。README 固化：

- 准备：安装 `auto` CLI；本仓根 `auto build -r vm`（VM 轨 ninja 校验，
  实测清缓存后 0.4s——VM app 由 CLI 解释运行）；vue 轨 `auto build`
  （vue-tsc + vite）或 `auto run` 即时生成 dev 工程。
- 启动：vue+VM HTTP：`$env:AUTO_BACKEND_IMPL='vm'; auto run`（:17850/:17851，
  `-F/-B` 可覆）；VM 窗口+VM HTTP：`$env:AUTO_VM_WITH_HTTP='1'; auto run -r vm`；
  纯后端：`auto service --server vm`（8080）。
- 隔离：`AUTO_CHARTS_DATA` 指向本次进程私有目录；只管理本次进程，不清理
  共享框架 target。
- 错误分类实测：端口占用→`Error: × bind failed … (os error 10048)` 退出
  码 1，既有实例不受影响；坏 tool→命令不可见即失败；VM 窗口启动为环境级
  flake（001 已案），验收驱动 3 次重拉。

## 5. 预算对账（与 Spec 差异，T-00 逐项核对 + T-02 补充）

| 维度 | 001 Spec/实现 | 本轮实测 | 处置 |
|---|---|---|---|
| 文件 ≤10MiB、行 ≤10000、列 ≤64、数值列 1..4 | 一致 | 源码 `csv.at`/`chart_project.at` 与 Spec 一致 | 不变 |
| 单元格值域 `\|v\| ≤ 10,000,000` | 百位定点 i32 | float 化后语义不变 | SD-01 修改「定点百位」表述为 float 精度策略 |
| 屏幕整数域（G-8）/导出百位 | 已声明边界 | 本轮废除该边界，双端同 float | SD-01 修改 |
| CJK 查询参数（G-6b）/GET+query（G-6a） | 已声明边界（owner auto-lang→实际 auto-web） | 本轮以 POST body 闭合 app 层；框架缺陷原样登记 | SD-01 修改；owner 记 auto-web |
| 工程 slug/名称长度 | "≤64 字符"（实为 UTF-8 字节语义） | 逐字节切片拼接丢弃 CJK（`a中b→ab`、全 CJK 坍缩 `chart` 互撞） | slug 改整体 replace 折叠；slug/名称预算 ≤192 字节（≈64 CJK 字符）；SD-01 记录 |
| 全零退化域 | Spec 文字 [0,1] | 实现自 001 起为 [0,100] | SD-01 修 Spec 文字 |

## 6. 框架缺口（具名，T-01/T-02 实现期实测；owner=auto-lang/auto-ui/auto-web；本计划全部绕开，不阻塞）

| # | 缺口 | 实测证据 | app 侧决策 |
|---|---|---|---|
| D1 | VM 轨 app→组件数据通道上 JSON 数字的小数形态静默归零（整数存活） | cjk 图表现 [0,80,0]（120.5/95.25→0）；sdec [-0.5,0,0.5] 全零退化 [0,100]；vue 轨同数据正常 | bar-chart 数据面改吃 `rows_frag` 字符串单元（`rowsText` prop），组件内 `parse_decimal` 解析——字符串通道逐字保真（CJK 已证） |
| D2 | VM 轨子组件 Init 只在首挂派发（PLAN-536 收敛为挂载语义），数据/映射变更不重算 | sdec→tiny 后组件状态停留前图（dec 读出 cjk 刻度） | 用框架既有挂载身份语义：调用位 `key:` prop 绑数据/映射代际（`chartEpoch`），key 变化即重发 Init（os-config 016 明文支持）；实测 sdec→tiny 后图表重算 ✓ |
| G-6a/b | （001 已登记）query 解码 latin-1/`+`→空格；双轨 POST 语义分歧 | 本轮 P1b/c 复现 | 全业务参数迁 POST body（§2），框架不改 |
| G-9（新） | VM 窗口 MCP 输入焦点仅首个 input 可靠（press ids[1..n] 不移焦） | type MARKER 打三个 input 全落 csvPath | VM 验收单输入流设计（001 同款）；导出失败用例改由缺省路径制造（目录占位）；vue 轨 Playwright 可填任意输入 |

## 7. 实现期已闭合的假说（原 T-00 §6）

1. VM 轨 `Http.post(url, str)` 真窗实测 ✓（VM-RED→GREEN：`已导入 3 行`）。
2. POST 响应双层编码消费与 GET 对称 ✓（两轨全流程通过）。
3. 屏幕端 float 几何与独立 oracle 一致 ✓（VM 43/43 含 CH-03 三用例；
   vue 14/14 含 tiny ±1px；导出 oracle 48/48）。
4. 删源重开/失败保全 ✓（CH-04 两轨：目录占位失败→既有导出不动→恢复
   后同一导出成功；旧 v1 工程打开+内嵌导出 ✓）。
