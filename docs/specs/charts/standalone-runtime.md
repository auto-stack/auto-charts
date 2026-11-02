# charts 独立运行规范（CHARTS-002 SD-02）

> 状态：随 CHARTS-002 交付落地（2026-11-02 merge）。本 app 独立运行
> 不依赖 AutoOS 装配、Rust 后端或 Linux；OS 组合版本由未来统一集成
> 计划接收（本 app merge 不改 AutoOS pin/父仓 gitlink）。

## 1. 准备

- 安装与开发线一致的 `auto` CLI（证据基线
  `auto 0.1.0+plan-890-verified-r7-t19-5-g55c98c7`，`auto-man` 仓构建）。
- 本仓根健康检查：`auto build -r vm`（VM 轨 ninja 校验，实测清缓存
  后秒级——VM app 由 CLI 解释运行）；`auto build`（vue 轨 vue-tsc +
  vite，冷生成有阶段、分钟级）。
- 共享 StyleKit 固定于 `vendor/stylekit`，无需相邻示例目录。

## 2. 启动形态（全部本机独立）

| 形态 | 命令 | 端口 |
|---|---|---|
| vue 前端 + VM HTTP 后端 | `$env:AUTO_BACKEND_IMPL='vm'; auto run`（`-F/-B` 可覆） | 17850 / 17851 |
| VM 窗口 + VM HTTP 后端 | `$env:AUTO_VM_WITH_HTTP='1'; auto run -r vm`（`-F/-B` 可覆） | 同上 |
| 纯后端 HTTP（无 UI） | `auto service --server vm` | 127.0.0.1:8080 |

- 缺省后端 `auto run`（无 env）为 a2r rust 轨，本仓不可用——一律
  `AUTO_BACKEND_IMPL=vm` 或 `-r vm`。
- 数据目录：`AUTO_CHARTS_DATA` → 缺省 `USERPROFILE/.auto-charts` →
  兜底 `./.auto-charts-data`。多实例/验收各自指向私有目录；本 app 只
  管理本次进程，不清理共享框架缓存。

## 3. 失败语义

- 端口占用：启动非零码明确失败（`bind failed … os error 10048`），
  既有实例不受影响。
- CLI 缺失/过旧：命令不可见或构建报错，属环境准备问题，不静默降级。
- VM 窗口偶发启动 flake（MCP 未就绪）：环境级已知现象，重试即可；
  验收驱动 3 次重拉循环。
- **多会话/多实例共存**：框架启动按端口清场（`kill_process_on_port`，
  Plan 354；保护名单仅 musk.exe/aaid.exe）——并发 VM 窗口必须以
  `-F/-B` 与各自 `AUTOUI_MCP_PORT` 隔离，缺省端口会互杀
  （CHARTS-002 merge 期实录，验收门已固化隔离端口）。

## 4. 验收门（owner 与命令）

| 门 | owner | 命令 | 覆盖 |
|---|---|---|---|
| 后端 HTTP 探针 | work/merge | `AUTO_CHARTS_DATA=<隔离目录> auto service --server vm` 后 `python tests/basic/probe_api.py` | CSV 契约、工程、导出几何容差 oracle、值预算边界（err_value_range/err_cell 相异）、GET 兼容面 |
| 双端真实任务 | work/merge | `python tests/basic/verify_basic.py --profile vm` / `--profile vue` | CH-01 启动就绪、CH-02 中文/`%20` 字面/工程名往返、CH-03 屏幕几何 ±1px+标签逐字、CH-04 旧工程/删源/失败保全/恢复、CH-05 区分性自检、CH-06 全序列 |
| 统一回归 | merge | 冻结基线上三门前置重跑 | 交付前最后 gate（VM 43/43、Vue 14/14、probe 0 失败为 2026-11-02 交付记录） |

- 测试隔离：每次运行创建临时 `AUTO_CHARTS_DATA` 与空闲 MCP/前后端
  端口，不接触真实用户数据；vm 门以 `-F/-B` 隔离端口（§3）。
- 修复期范围纪律：修复轮只跑受影响检查；统一门在冻结基线上由 merge
  执行一次，不逐修复轮重跑。

## 5. 边界

- Linux/Wayland、OS 集成、远程数据源不在本规范（`WAIT_DISTRO_M1`，
  由 OS 统一计划接收）。
- 框架缺口登记（owner 各自仓，app 侧已绕开）：D1 VM 数字小数通道
  归零（auto-lang）、D2 子组件 Init 挂载语义（auto-ui，`key:` 为
  官方重挂载机制）、G-6a/b 查询/POST 双轨分歧（auto-web/auto-lang）、
  G-9 MCP 输入焦点（auto-ui）。详见
  `docs/plans/evidence/002/standalone-decision.md` §6。
