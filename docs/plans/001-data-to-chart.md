---
plan_id: CHARTS-001
status: execution_done
feature_name: data-to-chart
author: [Codex]
created_at: 2026-10-29
updated_at: 2026-10-29
plan_revision: 2
current_step: 5
total_steps: 7
supersedes_spec_components: []
new_spec_components: [docs/specs/charts/basic-capabilities.md]
touched_goals: []
---

# CHARTS-001：用户数据到图表、保存与导出

## 0. 变更摘要

将固定 monthly/seed 图表演示补为读取用户 CSV 的最小图表工具。

本轮只起草执行合同：没有实施功能、运行功能验收或将本app升为A类。auto-charts 的基本能力补齐不依赖 auto-os-distro；Linux 支持另等 Nix＋COSMIC 基础完成，增强设计另会话。

## 1. 目标

导入一份用户 CSV，指定类别列和数值列，生成一张真实图表，保存后重开，并输出可在外部打开的图。

非目标：实时数据连接、远程数据库、仪表盘编排、统计分析、复杂交互和 Linux 适配。首版柱状图为最低交付，既有其他图表不额外承诺全格式导入；输出固定独立 SVG。

## 2. 架构方案

应用逻辑继续纯 `.at`，前端/后端沿 AutoUI 现有结构；本仓为主导仓。应用工作检出固定 `D:/autostack/auto-charts`（独立开发clone），工作分支 `main`；执行/复审共用此检出，一个写入者。**复用该独立clone，不在组合子模块内并行开发，不建任何junction/symlink**。框架缺口在实际owner仓另立前置并按其worktree纪律执行，不在app手写Rust、修改生成Rust或绕过公开SDK。

导入数据/映射/图表规格版本化保存，与展示颜色/CSS分离。CSV支持UTF-8（含可选BOM）、逗号、双引号转义和引号内换行；类别列+至少一数值列，缺/非法数值明确报行列错误，不静默当0或演示数据。保存工程应内嵌足够数据或明确受管副本，删除源CSV后仍可重开已保存图。SVG使用可移植中文文字/转义，不直接拼用户HTML。

跨仓总表：[B类基本能力总跟踪表](https://github.com/auto-stack/auto-os/blob/main/docs/plans/b-apps-basic-capabilities.md)。源Spec以所属仓 `docs/specs/` 为准；当前没有该app的canonical模块规范，旧根 `SPEC.md`（如有）只是历史Demo观察/再生描述，不能据此宣布真实功能已完成。新规范路径将在实际复审/merge后落地，本轮不写入已实现Spec。

## 3. 技术栈

Auto / AutoUI、当前匹配的AutoLang/AutoUI/AutoMan工具组合、各app已有widget/store/API；具体存储与平台接缝由T-01用实际源码和探针确认。Vue / VM 两端均需真实任务验收，不因某一后端不通就删掉原任务；如必须显式指定 server=vm 等启动profile，应先验证并记录到执行入口/README，不能静默换成mock。

## 4. 需求分析与背景调查

授权：用户于2026-10-29要求建立总跟踪表、复用Notes/Reader/Blog现有计划，并为其余B类应用准备基本能力补齐计划。此处授权的是**计划准备和必要的文档/组合版本登记**，不宣称已授权/完成本计划具体功能实现，不推定全量竞品复刻或Linux开发已启动。

交付授权（2026-10-29）：用户以 `/goal 完成计划001` + `/auto-plan-goal PLAN-001` 授予全链条执行授权：work（含本检出内实现/构建/测试）、review、限额内修复、merge（canonical Spec/ledger/归档/清理/落地检查）。后续阶段继承此授权，不再重复询问。

2026-10-29用户明确改用 `D:/autostack/<产品仓名>` 独立clone开发，先push应用再更新子模块pin；此修订仅更新工作位置、跨仓链接和交付状态描述，功能目标、T-01..07依赖、work验收与Spec增量不变，不重置任务。旧开发位置被此用户决定替代。

冻结的观察基线：`b1d14690751d89912f3ec0fd271caf48ff58b01a`（在本app `main` fetch origin后ff核对）；执行前重新核对HEAD/pin/WIP并记录变化。主产品统计为27个去重产品，B类9个；AutoJade旧名Jade Garden不重复计数。

现有 app.at 内嵌 seed/monthly，Tick 追加模拟数据；已有真实图表几何组件，但没有用户导入/工程保存/导出。SPEC.md 明确 frontend-only/in-memory。

已读来源（源码/文档观察，不是本轮实测）：

- `src/front/app.at`：SHA256 `6c62b74bc5eaddada9945efd427ac9329f28c20d2eba4e0e845264fd2a7ea857`。
- `SPEC.md`：SHA256 `70fcbbe64d1639de58b45efdc945c1f6d9b30f864086e4096cfb3334e3f2127a`。
- `src/front/components/bar_chart.at`：SHA256 `8b619ac3161a8aab927e22d87fa50eae5cce9265daefc6ca24a984b7078eec73`。
- `src/front/components/chart_geom.at`：SHA256 `78a02b598d169d0caa278a32aa913be1800ab76a02084a9c389f3ea64aa58863`。
- `tests/desktop_mcp.py`：SHA256 `67a2b8a8269f2108846d5c360389316cd397b985636eb61a84c469fb6d73be64`。

## 5. 详细设计

### 执行入口和依赖

首个就绪任务仅T-01：在上述应用检出核对版本、清单、当前工具链、真实API与测试入口，用隔离数据跑能力探针。输出允许后续实现依赖的接口与不支持项；缺口需具名指向owner/前置计划及关闭条件。不得假造未存在API、跳过基础正确性，或以“将来Linux会解决”替代当前端的基本能力。

T-02..04按下列任务依赖顺序推进；T-05将本节拟议测试做成真实可复现入口，T-06/07保持未来阶段未勾选。合并后只有基础合同的全部必需工作/复审通过且父仓pin指向交付版本，才更新总表分类。发布包/所有Linux发行版不在本计划的成功声明里。

### 规范增量

| delta_id | action | docs/specs target | before/after rule | rationale | AC |
|---|---|---|---|---|---|
| SD-01 | add | `docs/specs/charts/basic-capabilities.md`（新） | Demo/未定义 → 本计划首版用户任务、数据模型和准确支持范围 | 以真实基本能力作为产品准入 | AC-01/02 |
| SD-02 | add | 同上，失败/恢复及交互节 | 未定义 → 保存/输出/失败、重启和两端行为的可验合同 | 防止假成功、旧数据丢失和单端冒充 | AC-03/04 |

根README/历史SPEC在实现落地时反链canonical目标，保留历史来源、不覆盖未经审查的旧约定；本计划不在draft阶段修改canonical知识或ledger。

## 6. 测试设计

本轮没有执行下列功能测试。先以真实应用入口和真实文件/服务为准，既有脚本若只验证演示数据，需要补有辨别力的真实数据正反例；禁止仅把UI文案变绿或用相同生产函数生成期望值。

| case_id | AC/task与责任 | 输入/设置 | 实际入口 | 必须观察的结果 |
|---|---|---|---|---|
| V-01 | T-01..05 / AC-01..04；由T-05制作永久回放 | CSV含BOM/中文/引号内逗号和换行 | 真实导入入口 | 独立CSV解析器核对单元格；错误报行列而不偷偷拆行/置0。 |
| V-02 | T-01..05 / AC-01..04；由T-05制作永久回放 | [-5,0,10]与重复标签、字符<& | 映射→真实图表→SVG输出 | 独立几何和XML oracle核方向/比例/转义；输出能在外部渲染。 |
| V-03 | T-01..05 / AC-01..04；由T-05制作永久回放 | 已保存工程，移走源CSV，再制造写失败 | 真实保存→重启→导出 | 已保存图仍可恢复；失败不覆盖旧工程、不声称已导出。 |

测试隔离：所有文件/数据库/服务均使用临时用户数据目录及明确测试端口，不接触真实用户数据；占用端口/不可写/损坏时明确失败。多个实例/取消/退出与恢复按本计划声明范围验证。资源预算若需限制，T-01明确单位/语义/拒绝或截断结果并在dependent实现前冻结；没有提出上限不等于无限规模承诺，不以隐藏硬上限代替验收。

可复现入口（**均由T-05新增/接通**）：`python tests/basic/verify_basic.py --profile vue`、`python tests/basic/verify_basic.py --profile vm`。入口应实际调用应用后端与两端UI，记录源码/工具/依赖版本、fixture hash及运行结果；不得仅调内存helper替代。按可用工具复用现有Playwright或VM MCP/autoui-verifier驱动。T-01记录真实启动命令、数据env、端口与适用CLI参数；两端都要证实实际支持的用户任务。

角色：本轮仅起草，没有派执行/复审agent。实现与最终复审按四技能分阶段；无明确独立上下文时如实声明并从工件重建，不能自称独立或擅自创建新会话/agent。只改app不触auto-lang crates时禁止跑其cargo t/docs_gen；框架前置按owner自己的门档验证。

## 7. 验收标准

| ID | owner_stage | observable / verification |
|---|---|---|
| AC-01 | work | 真实CSV：用户导入含中文/引号/逗号/换行的 CSV，指定类别及数值列后得到对应柱图；空文件、缺列和坏数值明确拒绝。 |
| AC-02 | work | 几何正确：独立已知数组核对零/正/负值、类别和柱高/方向；不只断言SVG节点存在，既有样例不污染用户数据。 |
| AC-03 | work | 保存与导出：保存项目→退出→移走源CSV→重开仍一致；SVG可独立解析和显示，标签/数值映射与数据一致。 |
| AC-04 | work | 失败与双端：导入/保存/导出失败保留当前有效项目，不写假成功；Vue/VM均完成实际数据导入→映射→保存重开→导出。 |
| AC-05 | review | 冻结已提交实现与依赖，逐个重验AC-01..04和独立反例；核对SD-01/02与范围、实际证据，输出明确review结论；未闭项不可忽略。 |
| AC-06 | merge | 通过对应最终门后交付main并推送，父仓gitlink和组合验证可追溯；canonical/ledger/归档收尾完成，组合子模块显式detached，独立开发clone留在main；总表有证据地标A，A类Linux仍等待发行版前置。 |

## 8. 执行步骤

- [x] T-01（owner_stage=work；依赖 无；AC-01..04）：基线与全路径探针：验证文件选择或显式路径读取、健全CSV解析、版本化工程存储、当前柱图组件的值域/负值/零值处理和SVG真实输出；冻结数据/资源预算。不能用 split(逗号) 代替约定CSV输入，也不以截图充当图表导出。若需后端，17851 为候选。 输出新文件 `docs/plans/evidence/001/capability-decision.md`，记录可用API、版本/资源边界、缺项owner和最小闭环。[✅ 已完成]（2026-10-29：决策文档已落盘；auto CLI=v0.0.20-117；VM轨 run+MCP 实测通过（port 19511 state/snapshot）；vue轨需 AUTO_BACKEND_IMPL=vm + back_port:17851（pac.at 已加）；vue build 25 TS 错=生成器推断缺陷 G-2（donut 形态规避）；负值柱图越界 G-4→T-03 扩符号域；预算冻结：10MiB/万行/64列/1..4数值列/拒绝式）
- [x] T-02（owner_stage=work；依赖 T-01；AC-01..04）：输入与项目数据：新增 CSV/图表项目模块及接口（拟议 src/back/csv.at / chart_project.at / api.at）；数据与列映射校验，保存可恢复的工程。[✅ 已完成]（2026-10-29：三模块落地+tests/basic/probe_api.py 35/35 PASS（`auto service --server vm` 直启，AUTO_CHARTS_DATA 隔离）；RFC4180/BOM/引号换行/行列错误定位/坏单元格行列/工程保存列表读取/同名覆盖/异名冲突/按工程与按源导出/删源后导出全通；运行时语义发现（fs int 谓词+errno 写、substr 字节切、json.parse bool）记入 capability-decision §3.1；commit 见 git log）
- [ ] T-03（owner_stage=work；依赖 T-02；AC-01..04）：图表与输出：复用 components/bar_chart.at，确认从真实数据映射到几何；保存规格并导出独立 SVG，类别/中文/XML特殊字符正确。
- [x] T-04（owner_stage=work；依赖 T-03；AC-01..04）：界面去演示化：增加导入、列映射、保存重开/导出和错误状态；样例仅显式入口，普通启动空态；用户数据模式不再由模拟Tick覆盖。[✅ 已完成]（2026-10-29：app.at 重写为导入→映射→图表→保存/重开→导出全流程+错误状态行；流式 Tick/Play/Pause/滑窗退役；示例仅显式入口；VM 窗口端到端 26/26 PASS（tests/basic/verify_basic.py --profile vm）；样式修复：iced 列子级 flex-1 纵向填满问题（保存/导出改 col_btn_primary，导入保留行内 flex-1））
- [x] T-05（owner_stage=work；依赖 T-02..04；AC-01..04）：完成独立数据/失败回放和两端真实UI验收，新建 `tests/basic/verify_basic.py` 调度入口（可复用既有脚本），同时保存命令/输入hash/真实结果与原始失败；准备 canonical Spec 增量，提交实现，转 execution_done。[✅ 已完成]（2026-10-29：verify_basic.py 双端全绿 vm 26/26 + vue 10/10，probe_api.py 35/35（GET+query 化后最终回归）；fixture sha256 与逐项结果落 test-results/verify_basic_{vm,vue}.json；canonical Spec 增量草案 docs/specs/charts/basic-capabilities.md（SD-01/02）；README 记录双轨启动 profile 与验收入口；desktop_mcp.py 标注为源导入期遗留）
- [ ] T-06（owner_stage=review；依赖 T-05；AC-05）：在同一app检出暂停实现，按冻结提交、真实数据和独立反例最终复审；核对Spec增量与双端结果，说明上下文独立性限制；未满足返回修复，不将数据错误降为债务。
- [ ] T-07（owner_stage=merge；依赖 T-06；AC-06）：完成实际提交/推送/父仓gitlink验证，沉淀canonical Spec与derived ledger、归档；刷新总表A/B与证据，组合子模块显式detach，独立开发clone留在main。Linux仍等待发行版门，不因文档或脚本存在宣布已可用。

## 9. 复审记录

- 历史 r1起草回执见 `b3973f0694e3fc4a83aa33671fb3d3c1b067fc54`；其开发位置/收尾状态描述由本次修订替代，既有功能与验收合同保留。
- stage: new | plan_id: CHARTS-001 | plan_revision: 2 | outcome: pass（独立clone路径修订就绪；功能未实施/未验收） | next: work/T-01（另行执行）。
- 本次只改工作位置、跨仓链接与AC-06/T-07的检出收尾说明，不变更基础能力要求；独立clone开发，组合子模块只固定已交付版本。
- 本轮核对源码/Spec缺口、历史任务、路径、基线和计划唯一性；未执行实现/功能测试，所有7项任务保持未勾选；通过的是草案结构/相互引用检查，不是产品验收。
- stage: work | plan_id: CHARTS-001 | plan_revision: 2 | round: 1 | outcome: pass（execution_done） | worktree: D:/autostack/auto-charts（独立开发 clone） | branch: main | base_commit: d5f5535 | code_commit: b49aff6 | dependency_revisions: stylekit=vendor 固定 | task_ids: T-01..T-05 | evidence: docs/plans/evidence/001/capability-decision.md + test-results/verify_basic_vm.json(26/26) + verify_basic_vue.json(10/10) + probe_api 35/35 | blockers: 无 | next_responsible_role: review（T-06，同一检出行内独立上下文复审）
- work 阶段交付：RFC4180 CSV 导入（BOM/中文/引号内逗号换行逐字保留；行列/数值负例明确报错）、列映射校验（1 类别+1..4 数值，拒绝式预算）、带符号域柱图（屏幕组件与导出 SVG 同一几何合同，刻度 {1,2,5}·10^k，基线 y(0)）、版本化工程存储（内嵌数据，删源可重开，同名覆盖/异名冲突明确）、独立 SVG 导出（备份+暂存读回+提交写协议）、界面去演示化（空态启动/示例显式入口/流式演示退役）、GET+query API（G-6a 双轨 body 分歧规避）、浮点容忍屏幕端（G-8 修复：值域取整、柱高原值）。
- 框架缺口具名登记（capability-decision §3.1/3.2）：G-1 auto info 损坏、G-2 vue 生成器 var 推断+float.to_int、G-3 a2r 轨不可用、G-4 无 rename/remove、G-5 shadcn 脚手架依赖裁剪、G-6a Http body 双轨分歧、G-6b 查询 %XX latin-1 乱码（vue 轨 CJK 降级）、G-7 MCP 输入焦点、G-8 屏幕端整数几何（已修复中止问题，小数刻度取整）。legacy desktop_mcp.py 为源导入期演示脚本，由 verify_basic.py 取代。

## 10. 待澄清事项

无必须先向用户确认的产品身份问题；技术可行性与资源边界由 T-01 冻结，缺口保持具名阻塞。
