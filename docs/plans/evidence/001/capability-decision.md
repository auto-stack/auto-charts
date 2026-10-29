# CHARTS-001 T-01 能力决策（capability decision）

基线：`d5f5535`（main，独立 clone `D:/autostack/auto-charts`，干净）。
探针日期：2026-10-29。所有结论来自本 clone 实测命令与运行输出，非历史文档转述。

## 1. 工具链与启动入口（冻结）

| 项 | 实测值 |
|---|---|
| auto CLI | `D:/autostack/auto-man/target/debug/auto.exe`，`--version` = `auto 0.1.0+v0.0.20-117-g873fa23` |
| VM 轨（窗口+VM 后端） | `auto run -r vm`；构建 `auto build -r vm` 通过（ninja, exit 0） |
| VM MCP 驱动 | env `AUTOUI_MCP_PORT=<port>`；`POST /mcp` JSON-RPC（autoui_state / autoui_snapshot / autoui_action / autoui_find）实测可用（本探针 port 19511，state/snapshot 均返回真实 UI 树） |
| Vue 轨 dev | `AUTO_BACKEND_IMPL=vm auto run` → vite :17850，HTTP 200，`<title>图表</title>` |
| Vue 轨缺省后端 | `auto run`（无 env）失败：`vue backend start failed: backend Cargo.toml missing`——run_vue.rs（auto-ui）`AUTO_BACKEND_IMPL` 缺省 `rust`（a2r 轨），与本仓裁定同 reader F-07：不建 rust-workspace，Vue 轨一律 `AUTO_BACKEND_IMPL=vm` |
| 后端端口 | pac.at 增加 `back_port: 17851`（计划候选值）；CLI 注入 `AUTO_HTTP_PORT/AUTO_HTTP_BASE`，前端相对路径 `/api/*` 经 vite proxy / VM 运行时路由到后端 |
| Vue 浏览器驱动 | node v25.2.1、pnpm 11.6.0、Playwright chromium（ms-playwright 缓存含 chromium-1228/1234/1243/1248）已就位 |
| 测试隔离 | env `AUTO_CHARTS_DATA`（本计划数据目录覆写， reader `AUTO_READER_DATA` 同配方）→ 缺省 `USERPROFILE/.auto-charts` → 兜底 `./.auto-charts-data` |

## 2. 框架缺口（具名，owner=auto-lang/auto-man/auto-ui；不阻塞本计划，已有 app 侧规避）

| # | 缺口 | 实测证据 | app 侧决策 |
|---|---|---|---|
| G-1 | `auto info` 子命令无条件读历史文件 `.am/pac.atom.at` 报错（automan.rs:951） | charts/reader 两仓复现，exit 非 0 | 不用 `auto info`；以 `auto build`/`auto run` 为准 |
| G-2 | vue 生成器对「str 初值后被 List 索引重赋值」的 var 推断为 number：`var name = f`（for-in List\<str\> 循环变量）→ 生成 `let name: number = f`，25 个 TS2322/2345（Area/Bar/LineChart.vue）；donut 用 `var name = lv`（动态索引初值，生成无类型注 let）不受影响 | `auto build` 输出（25 errors）；gen/front/vue 源码行比对 | 组件源码改写为动态索引初值形态（donut 同款），`auto build` 转绿；G-2 本体登记 auto-lang owner |
| G-3 | a2r Rust 后端轨不可用（动态 JSON 映射缺口群，reader T-00 已登记） | `auto run` 缺省 rust 后端失败（rust-workspace 从未生成，本仓不建） | 全部后端逻辑走 AutoVM HTTP 轨 |
| G-4 | 运行时无 fs.rename/fs.remove 原子原语（a2r 映射集仅 exists/read_text/write_text/create_dir/mkdir_all/file_size/is_dir/read_dir/dir_names/append_text/copy_recursive） | reader library.at T-00 记录 + 本轮 API 面核对 | 工程与导出写入用「备份+暂存读回校验+提交+失败还原」协议（reader F-06 同款），如实声明非断电级原子 |

## 3. 运行时 API 面（冻结，VM 轨实测来源：reader 运行中仓 + 本轮冒烟）

- 后端端点：`src/back/api.at` 中 `#[api(method="GET|POST|PUT|DELETE", path="/api/...")] pub fn`；路径参数 `:id` 与形参同名绑定；查询参数按名传。
- 后端纪律（reader T-00/T-01 实测裁定，全盘沿用）：非 api 模块不构造 api 端点类型，公开面用标量与 JSON 字符串；fn 实参不用 struct/List；拼接链每步 ≤2 操作数；`json.parse` 数组用 for-in 遍历（len()/索引有在册缺陷 F-8）；写侧手工转义、读侧 `json.parse`（`json.encode` 对动态 map 在 VM 轨只回内部句柄）。
- 字符串：`len/substr/find/replace/trim/split/to_int/to_string/parse` 足够实现 RFC4180 逐字符解析。
- 前端调后端：`Http.get_json/post/put/delete`（双轨可用；`use back.api` 在 VM 轨不可解析——reader PLAN-043 先例）；VM handler 由调度器 park/resume，HTTP 调用不冻结 UI。
- 前端 widget：`input`（value/oninput(str msg)/onenter/placeholder）、`button`、`checkbox`、`text`、`svg` 直通——导入路径输入、列映射、导出路径输入均无需新 widget。

## 4. 现有柱图组件能力边界（T-03 输入）

- `bar_chart.at`：band scale，vmax 仅从 0 向上取正 max；负值 ytop 越界 viewBox、全负数据 domain 退化为 4 且刻度无负半轴；零值正常（零高柱）。
- 系列槽位固定 4（segs0..3），x 标签 ≤20 等距抽样；图例点击已带系列可见性开关。
- 决策：T-03 将组件 Init 扩展为带符号域（vmin/vmax、基线 y、含负刻度），导出 SVG 由后端按同一几何合同独立渲染（`chart_project.at::render_bar_svg`），双工件共享数据面、分别被 V-02 独立 oracle 核对。

## 5. 数据/资源预算（冻结，拒绝式，无静默截断）

| 维度 | 冻结值 | 语义 |
|---|---|---|
| CSV 文件大小 | ≤ 10 MiB | 超出拒绝（err=file_too_large），不部分导入 |
| 数据行数 | ≤ 10,000（不含表头） | 超出拒绝并报首个越界行号 |
| 列数 | ≤ 64 | 超出拒绝 |
| 数值列选择 | 1..4 | 柱图系列槽位上限；UI 在第 5 个勾选时明确拒绝 |
| 类别列 | 恰好 1 | 必选；未设/重复设置以前选为准（UI 显式高亮当前类别列） |
| 单元格数值 | trim 后可为 int/十进制 float（含负号）；空/非法 → 报 err_cell（含行、列、原文），不置 0、不丢行 | 导入失败整体拒绝，不产生部分数据集 |
| 编码 | UTF-8（BOM 可选，剥除）；含中文/引号/逗号/引号内换行 | read_text 按 UTF-8；非法 UTF-8 明确报错 |
| 工程内嵌数据 | 全量行内嵌于工程 JSON（无外部引用） | 删除源 CSV 后重开一致（AC-03） |
| 工程名 | 非空，≤64 字符；同存 `projects/<slug>.json`，slug 冲突明确报错不覆盖（除非同名保存回同一工程 id） | 列表 + 显式打开 |
| 导出 SVG | 显式路径（UI 预填建议路径）或缺省 `<data>/exports/<slug>.svg`；目标不可写报错不覆盖旧文件 | 写前备份协议，失败保留旧导出 |
| 并发/多实例 | 单写入者（本计划范围）；测试各 profile 独立 `AUTO_CHARTS_DATA` 临时目录 | 无跨进程锁 |

## 6. 测试入口约定（T-05 落地目标）

- vm profile：`AUTO_CHARTS_DATA=<tmp> AUTOUI_MCP_PORT=<free> auto run -r vm`，Python 经 MCP 驱动真实窗口完成 导入→映射→保存→重开→导出，状态断言 + snapshot SVG 路径 d 属性独立 oracle。
- vue profile：`AUTO_CHARTS_DATA=<tmp> AUTO_BACKEND_IMPL=vm auto run`（:17850）+ Playwright chromium 驱动同一任务流；导出文件 oracle 与 vm 共用。
- 启动 profile 已实测并记录于 §1；README 同步（T-04/T-05 承诺）。
