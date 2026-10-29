# charts 基础能力规范（CHARTS-001）

> 状态：随 CHARTS-001 交付落地（SD-01/SD-02）。此前本 app 无 canonical
> 模块规范；根 `SPEC.md` 为源导入期的 Demo 再生描述（frontend-only/内存
> 演示态），仅作历史来源，不约束本规范已实现能力。

## 1. 用户任务（v1 范围）

从一份用户 CSV 到一张可对外使用的图，全程真实数据：

1. **导入**：输入 CSV 文件路径（显式路径；文件选择器非 v1 范围），
   后端读取并解析，结构校验失败明确拒绝。
2. **列映射**：指定恰好 1 个类别列 + 1..4 个数值列（拒绝式上限，
   第 5 个数值列明确报错）；映射变更经后端对全部所选单元格数值校验，
   坏值报记录号+列号（err_cell），不置 0、不静默丢行。
3. **图表**：屏幕端由官方 bar-chart 组件消费真实数据（首版交付柱状图；
   line/area/donut 组件对同一数据可用但几何合同只对柱图冻结）。
4. **保存**：工程以 `schema_version=1` JSON 落盘于数据目录
   `projects/<slug>.json`，**内嵌全量数据**（headers/rows/keys/recs 转
   义片段）与映射；删除源 CSV 后可重开。同名保存覆盖自身；slug 被其他
   名占用报 err_exists，不静默覆盖。
5. **重开**：工程列表（损坏文件以 `corrupt:true` 在列，不静默丢弃）；
   打开走内嵌数据，信任保存时已验映射。
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
  数值列 1..4；|值| ≤ 10,000,000（err_value_range）；数值语法
  `[+-]?digits[.digits]`（无指数；err_cell 报行列与原文）。
- 数据集信封（import 响应）：`headers_frag`/`rows_frag`（转义 JSON
  数组串，存储与导出面，单元格逐字字符串）、`keys_frag`（去重列键）、
  `recs_frag`（对象行；数值形态单元格以 JSON 数字输出供组件消费）。
- 列键去重序：重复/空表头取 `base` → `base#2` → `base#3`…（自然序，
  首个冲突后从 #2 起）；空表头以 `c<下标>` 兜底。
- 工程 v1 文档：`schema_version/name/slug/source_path/index_col/
  value_cols[4]/created_at/headers_frag/rows_frag/keys_frag/recs_frag/
  row_count/col_count`。

## 3. 几何合同（柱图；屏幕端与导出同式，oracle 可独立复算）

视窗 `0 0 560 300`；绘图区 x 40..550、y 20..260。

- 带符号值域：`vmin = min(0, 数据最小值)`、`vmax = max(0, 最大值)`；
  `y(v) = 260 − (v − vmin)/span × 240`，span = vmax − vmin（全零退化
  为 [0,1]）；基线 = y(0)（正/零值柱自基线向上，负值向下）。
- 刻度：阶梯 `{1,2,5}·10^k`，step 为 ≥ span/4 的最小值；屏幕端 ≤5 槽
  （自顶填充），导出全量刻度。
- 柱：slot = 510/n，槽内 inner = 0.6·slot 等分到在场系列（紧凑编号，
  色板 #2563eb/#16a34a/#d97706/#dc2626）；x 轴类别标签 ≤20 等距抽样，
  XML 转义（& < > "）；不拼用户 HTML。
- 值语义：定点百位（×100）整数预算（i32 安全域）；导出坐标 float
  输出（oracle 容差 ±0.01px）。

## 4. 已声明边界（非缺陷即合同）

- **屏幕端整数几何（G-8）**：柱图组件值域/刻度按整数预算；小数数值
  单元格在值域计算中截断取整（柱高仍按原始值精确绘制），不再中止
  Init（2026-10-29 修复前：小数使 Init 中止不出图）。含小数数据的
  刻度标签为截断整数值；导出 SVG 按定点百位精确渲染，为精确工件。
  浮点值域原生支持的框架缺口登记 auto-ui/auto-lang。
- **CJK 查询参数（G-6b）**：查询值 %XX 解码为逐字节 latin-1（框架），
  vue 轨 fetch 自动 percent-encode → CJK 文件路径/工程名在 vue 轨降级；
  VM 轨原始 UTF-8 正常。owner：auto-lang。
- Http body 双轨分歧（G-6a）：vue=对象/VM=字符串 → 本仓 API 全部
  GET+query（标量）。owner：auto-lang。
- 单写入者；无跨进程锁；时钟能力缺失期间 `created_at` 为空串。
- 性能不设承诺：10 MiB/万行在预算内被接受但解析为逐字符扫描，
  不做速度声明。
