# auto-charts

图表工坊，使用 AutoLang / AutoUI 开发的独立应用。

更新：2026-11-01。CHARTS-001 已交付真实CSV、映射、工程保存重开和独立SVG（柱图为冻结基本合同）。CHARTS-002 已交付：中文/特殊字符路径与工程名经 POST body 逐字往返（双端真实UI验收）、小数/负值/零的柱图域·基线·刻度双端统一（独立几何 oracle 对账）、正式独立启动与旧工程/失败保全收口。

## 运行

准备：安装与开发线一致的 `auto` CLI（本仓证据基线 `auto 0.1.0+plan-890-verified-r7-t19-5-g55c98c7`）；从本仓根执行 `auto build -r vm`（VM 轨 ninja 校验，秒级）与 `auto build`（vue 轨 vue-tsc+vite）确认环境完好。

启动（三形态，均为本机独立运行，不依赖 AutoOS 装配）：

```powershell
# vue 前端 + AutoVM HTTP 后端（缺省后端是 a2r rust 轨，本仓不用）
$env:AUTO_BACKEND_IMPL = 'vm'
auto run

# VM 窗口 + VM HTTP 后端（merged 模式无 HTTP 服务器，本仓后端能力需 split）
$env:AUTO_VM_WITH_HTTP = '1'
auto run -r vm

# 纯后端 HTTP（无 UI；探针/联调用）
auto service --server vm
```

- 端口：前端 `17850`、后端 `17851`（`pac.at` `back_port`，可 `-F/-B` 覆盖）；
  `auto service` 固定 `127.0.0.1:8080`。
- 数据目录：`AUTO_CHARTS_DATA` 环境变量 → 缺省 `USERPROFILE/.auto-charts`。
  多实例/验收请各自指向私有目录；本仓只管理本次进程，不清理共享框架缓存。
- 失败语义：端口被占用→启动以非零码明确失败（`bind failed … os error 10048`），
  既有实例不受影响；CLI 缺失/过旧→命令不可见或构建报错，属环境准备问题。
- VM 窗口偶发启动 flake（MCP 未就绪等）为已知环境级现象，重试即可。

共享 StyleKit 已固定在 `vendor/stylekit`，无需相邻 auto-lang 示例目录。

## 基础能力验收（CHARTS-001/002）

```sh
# 后端 HTTP 探针（先启动：AUTO_CHARTS_DATA=<隔离目录> auto service --server vm）
python tests/basic/probe_api.py [base_url]

# 双端真实任务验收：导入 → 列映射 → 图表 → 保存 → 重开 → 导出 SVG
# （含中文/特殊字符往返、小数几何独立 oracle、旧工程与失败保全）
python tests/basic/verify_basic.py --profile vm    # VM 窗口（MCP 驱动）
python tests/basic/verify_basic.py --profile vue   # vue + Playwright
```

`tests/desktop_mcp.py` 为源导入期的演示态脚本（依赖旧 monorepo 布局的
`auto.exe` 相对路径与已退役的流式演示字段），由上收入口取代。

## 来源与组合

来源提交、路径与文件 hash 见 `SOURCE-IMPORT.json`。首次导入提交保留在 `source-sync` 分支；完整 v0.5 恢复后从该基线导入差异，再与产品开发线合并。

AutoOS 通过 [`apps/auto-charts`](https://github.com/auto-stack/auto-os/tree/main/apps/auto-charts) submodule 固定本仓版本；教学 Demo 保留在来源仓。

已有测试随源导入；端口与平台相关测试需要按本仓配置准备运行环境。安装/启动与双端完整功能验收是不同检查项。

## 基本能力补齐计划（2026-10-29）

[CHARTS-001：用户数据到图表、保存与导出](docs/plans/archived/001-data-to-chart.md) 已交付（2026-10-29，r2 复审 pass，reviewed e3375e2）：用户任务能力实现并通过双端验收（见上节），canonical 规范见 [docs/specs/charts/basic-capabilities.md](docs/specs/charts/basic-capabilities.md)。
总状态与前置见 [AutoOS B类总跟踪表](https://github.com/auto-stack/auto-os/blob/main/docs/plans/b-apps-basic-capabilities.md)。基础能力通过后再考虑Linux；A类统一等待 auto-os-distro 完成 Nix＋COSMIC 基础，后续增强另会话。

开发使用独立 clone `D:/autostack/auto-charts` 的 main；AutoOS 内对应子模块仅固定已交付提交，流程见 [App开发与子模块](https://github.com/auto-stack/auto-os/blob/main/docs/design/strategy/app-submodule-workflow.md)。


## 当前后续：独立运行、中文与小数

[CHARTS-002：中文数据传输、小数图形与独立运行收口](docs/plans/archived/002-standalone-unicode-and-decimal-charts.md) 已交付归档（2026-11-02，r1 全 8 任务）：中文/特殊字符路径与工程名经 POST body 逐字往返（决策稿 [standalone-decision](docs/plans/evidence/002/standalone-decision.md) §2）；小数/负值/零域·基线·刻度双端 float 统一，刻度标签 (k,m,e) 整数重构，独立几何 oracle 对账（VM 43/43、Vue 14/14、后端探针 0 失败）；正式独立启动与旧工程/失败保全收口（§4/§7）。VM 轨框架缺口 D1/D2（数字小数数据通道归零、子组件 Init 首挂语义）以字符串数据面 + `key:` 代际绕开，登记于决策稿 §6，owner auto-lang/auto-ui。canonical 规范已落地：[basic-capabilities](docs/specs/charts/basic-capabilities.md)（修订）+ [standalone-runtime](docs/specs/charts/standalone-runtime.md)（新增）。交付统一回归门：VM 43/43、Vue 14/14、probe 0 失败。

[路线图](docs/roadmap-v0.6.md) · [现实现规范](docs/specs/charts/basic-capabilities.md)。应用单独运行验证后再由OS统一计划集成；Linux继续等待Nix＋COSMIC基础。
