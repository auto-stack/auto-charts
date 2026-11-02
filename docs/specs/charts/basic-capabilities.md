# charts 基础能力规范（CHARTS-001/002）

> 状态：随 CHARTS-001 交付落地（SD-01/SD-02），并随 CHARTS-002 修订
> （中文传输、float 数值与几何统一、slug/名称预算、独立启动——SD-01/02，
> 2026-11-02 merge 落地）。此前本 app 无 canonical 模块规范；根 `SPEC.md`
> 为源导入期的 Demo 再生描述（frontend-only/内存演示态），仅作历史来源，
> 不约束本规范已实现能力。

## 1. 用户任务（v1 范围）

从一份用户 CSV 到一张可对外使用的图，全程真实数据：

1. **导入**：输入 CSV 文件路径（显式路径；文件选择器非 v1 范围），
   后端读取并解析，结构校验失败明确拒绝。业务参数经 POST body 传输
   （见 §5 传输），中文/空格/URL 特殊字符路径逐字保真。
2. **列映射**：指定恰好 1 个类别列 + 1..4 个数值列（拒绝式上限，
   第 5 个数值列明确报错）；映射变更经后端对全部所选单元格数值校验，
   坏值报记录号+列号（err_cell），不置 0、不静默丢行。
3. **图表**：屏幕端由官方 bar-chart 组件消费真实数据（柱图几何合同
   冻结于 §3；line/area/donut 组件对同一数据可用但几何合同只对柱图
   冻结）。数据/映射变更后图表重算（调用位 `key:` 代际语义）。
4. **保存**：工程以 `schema_version=1` JSON 落盘于数据目录
   `projects/<slug>.json`，**内嵌全量数据**（headers/rows/keys/recs 转
   义片段）与映射；删除源 CSV 后可重开。同名保存覆盖自身；slug 被其他
   名占用报 err_exists，不静默覆盖。中文工程名逐字往返（CH-02 验收）。
5. **重开**：工程列表（损坏文件以 `corrupt:true` 在列，不静默丢弃）；
   打开走内嵌数据（POST body 传 id，中文 slug 安全），信任保存时已验
   映射。
6. **导出**：独立 SVG（`<?xml … ?><svg xmlns …>`），几何与数据一致；
   显式输出路径或缺省 `exports/<slug>.svg`；写入采用备份+暂存读回校验+
   提交+失败还原协议；失败明确报错且不覆盖旧文件、不声称成功。
7. **空态与示例**：普通启动为空态引导；示例数据仅显式「载入示例」
   入口；导入/工程/示例互斥替换当前数据集；任一失败保留当前有效数据。

## 2. 数据契约

- CSV：UTF-8（BOM 可选剥除）、RFC4180（引号内逗号/换行/双引号转义
  逐字保留；引号外 \r\n、\n、孤立 \r 结束记录）；表头=首记录，列数
  不一致报 err_shape（记录号，表头=1）；空/纯空白报 err_empty；
  引号闭合后杂散字符报 err_quote。
- 预算（拒绝式，无静默截断）：文件 ≤ 10 MiB（err_file_too_large）；
  数据行 ≤ 10,000（err_too_many_rows）；列 ≤ 64（err_too_many_cols）；
  数值列 1..4；单元格数值 **|v| < 10,000,000**（≥ 1e7 → err_value_range，
  与语法错误 err_cell 为相异错误码；边界判定在精确十进制整数部分上
  进行，先于 float 舍入）；数值语法 `[+-]?digits[.digits]`（无指数，
  整数部分必需）。
- 数值解释（CHARTS-002 冻结）：双端统一 float（VM float 实测 f32，
  约 7 位十进制有效数字）；十进制文本 → float 逐位累积至 15 位，其后
  差异低于表示精度（不承诺任意精度）；至少 0.1/0.2、±0.5、25.5 及
  0.001/0.002 可区分。刻度标签按 (k,m,e) 整数重构（`label_of_k`），
  与 float 宽度无关，oracle 同式对账。超出 f32 表示的差异不承诺
  （如 10000000.001 不可与 1e7 区分）。
- 工程名/Slug：名称非空、≤ 192 UTF-8 字节（≈64 个中文字符）；slug
  保留字母/数字/-/_ 与中文等其余字符，Windows 保留字符与空格折叠为
  `-`（整体 replace 折叠，不逐字节切片——切片拼接会丢弃 CJK），收缩
  连续 `-`、去首尾 `-`、≤192 字节；空结果 → "chart"。名称/slug 长度
  按 UTF-8 字节语义计。
- 数据集信封（import 响应）：`headers_frag`/`rows_frag`（转义 JSON
  数组串，存储与导出面，单元格逐字字符串）、`keys_frag`（去重列键）、
  `recs_frag`（对象行；数值形态单元格以 JSON 数字输出）。
  **组件消费注意**：VM 轨 app→组件数据通道上 JSON 数字的小数形态会
  静默归零（框架缺口 D1，owner auto-lang）——bar-chart 数据面以
  `rows_frag` 字符串单元透传（`rowsText` prop），组件内
  `parse_decimal` 解析；字符串通道逐字保真。
- 列键去重序：重复/空表头取 `base` → `base#2` → `base#3`…（自然序，
  首个冲突后从 #2 起）；空表头以 `c<下标>` 兜底。
- 工程 v1 文档：`schema_version/name/slug/source_path/index_col/
  value_cols[4]/created_at/headers_frag/rows_frag/keys_frag/recs_frag/
  row_count/col_count`。

## 3. 几何合同（柱图；屏幕端与导出同式，oracle 可独立复算）

视窗 `0 0 560 300`；绘图区 x 40..550、y 20..260。域/基线/刻度/柱几何
双端全部 float 运算（无整数截断——CHARTS-002 废除 001 的屏幕整数域
边界 G-8 与导出百位定点）。

- 带符号值域：`vmin = min(0, 数据最小值)`、`vmax = max(0, 最大值)`；
  `y(v) = 260 − (v − vmin)/span × 240`，span = vmax − vmin（全零退化
  为 [0,100]）；基线 = y(0)（正/零值柱自基线向上，负值向下）。
- 刻度：阶梯 `{1,2,5}·10^k`（k∈ℤ，含负指数档），step 为 ≥ span/4 的
  最小值（1e-7 相对边界容差，防除法种子 ulp 跌档）；tick = k·step
  乘法求值（免连加漂移）；导出全量刻度，屏幕端 ≤5 槽自底向上填。
- 柱：slot = 510/n，槽内 inner = 0.6·slot 等分到在场系列（紧凑编号，
  色板 #2563eb/#16a34a/#d97706/#dc2626）；x 轴类别标签 ≤20 等距抽样，
  XML 转义（& < > "）；不拼用户 HTML。
- oracle 容差：导出坐标 ±0.01px，屏幕端 DOM/MCP 读数 ±1px；刻度标签
  逐字对账（整数重构式）。

## 4. 已声明边界（非缺陷即合同）

- **传输（CHARTS-002）**：业务参数端点（import/validate/save/export/
  project_get）为 `POST` + 单一 `payload str` 整体 body 参数；VM 轨
  原样发送 JSON 对象文本，vue 轨 `JSON.stringify` 外包 JSON 字符串壳，
  端点按首字节（`"` vs `{`）剥壳。原 GET+query 端点保留（兼容承诺），
  仅 ASCII 安全值可用，前端不再使用；其缺陷（`+`→空格、%XX latin-1
  乱码、`&` 截断）为框架既有行为，owner auto-web。
- **组件数据通道（D1，owner auto-lang）**：VM 轨 JSON 数字小数在
  app→组件通道静默归零——柱图以字符串单元消费（§2），其余组件
  （line/area/donut）仍吃数字 `recs`，小数在 VM 轨屏幕端不保真
  （几何合同未对它们冻结）。
- **组件重算（D2）**：VM 轨子组件 Init 只在挂载派发（PLAN-536 挂载
  身份语义）——柱图调用位 `key:` 绑数据/映射代际（`chartEpoch`），
  key 变化即重发 Init；这是框架明文支持的重挂载语义。
- **VM 窗口并发**：框架启动按端口清场（`kill_process_on_port`）——
  多会话/多实例必须以 `-F/-B`（及各自 MCP 端口）隔离，否则互杀；
  VM 窗口偶发启动 flake 属环境级现象，验收驱动 3 次重拉。
- **VM 轨 MCP 输入焦点**：仅首个 input 可靠聚焦（G-9）；验收设计为
  单输入打字流。
- 环形图（非 v1 冻结件）契约：数值需非负且合计 > 0；负值/零合计渲染
  显式提示文案而非几何；图例/tooltip 标签内 CR/LF 折叠为空格。
- 单写入者；无跨进程锁；时钟能力缺失期间 `created_at` 为空串。
- 性能不设承诺：10 MiB/万行在预算内被接受但解析为逐字符扫描，
  不做速度声明。

## 5. 传输与错误码（CHARTS-002 冻结）

- POST body：`{"path":…}`（import）、`{"path","index_col","v0..v3"}`
  （validate）、`+{"name"}`（save）、`+{"project_id","out_path"}`
  （export）、`{"id"}`（project_get）。前端以 `json_escape_cell` 同款
  手工转义构造对象文本。
- 错误码（相异、可分类）：`err_cell`（语法）、`err_value_range`
  （≥1e7）、`err_shape/err_empty/err_quote/err_file_too_large/
  err_too_many_rows/err_too_many_cols/err_not_found/err_is_dir/
  err_no_index/err_no_values/err_bad_col/err_dup_col/err_name/
  err_exists/err_write/err_export_write/err_render/err_read`。
- 字符串返回端点 HTTP 体为双层编码 JSON 字符串（历史裁定）；前端
  `Http.post` 返回后 `json.parse` 一次（vue 轨 `.json()` 已剥一层）。
