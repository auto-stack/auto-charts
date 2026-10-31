---
plan_id: CHARTS-002
status: drafting
feature_name: "中文数据传输、小数图形与独立运行收口"
author: [Codex]
created_at: 2026-10-31
updated_at: 2026-10-31
plan_revision: 1
current_step: 0
total_steps: 8
base_branch: main
base_commit: a5aa170c564f22a42f7a518a6d02d28650f15d32
depends_on: ["CHARTS-001"]
supersedes_spec_components: ["docs/specs/charts/basic-capabilities.md"]
new_spec_components: ["docs/specs/charts/standalone-runtime.md"]
touched_goals: []
---

# CHARTS-002：中文数据传输、小数图形与独立运行收口

## 0. 变更摘要

复用001的CSV→映射→图表→工程→SVG闭环，补齐中文路径/工程名传输与小数值域/刻度的基本可用性，固定正式独立启动和真实双端门。001及其历史计数保持原样；不引入新的图表生态或OS依赖。

## 1. 目标

用户从本机含中文、空格和URL特殊字符的目录导入CSV，用中文工程名保存、删源后重开并导出；Vue与原生VM结果逐字一致。柱图对受支持正/负/小数/零数据具有正确域、基线和刻度，屏幕与导出符合独立几何oracle。

非目标：远程数据源、实时仪表盘、新图种、任意精度数学、多写者仓储、Rust后端全映射、OS集成与Linux。保留VM HTTP为正式后端选择，不把改Rust作为本包启动前置。

## 2. 架构方案

开发、内部检查和最终复审顺序使用同一个 `D:/autostack/auto-charts` 独立 clone、`main` 分支；不新建应用 worktree、不在 AutoOS 子模块中实现，一 app 一写入者，复审时暂停实现写入。框架变更必须在实际 owner 仓另走其 Plan/worktree 规约；本计划不自动取得框架源写入权。

用户本轮授权（2026-10-31）：建立后续计划、更新本 app README/roadmap、提交与推送这些文档；**暂不实施，不更新 AutoOS 子模块**。后续实施需另行进入 work。应用验收与交付不以 AutoOS 装配或 Linux 为前置；Linux 仍 `WAIT_DISTRO_M1`。OS 组合版本由未来统一集成计划接收，本计划 merge 只交付 app，不改父仓 gitlink、manifest 或 `.gitmodules`。

实现保持纯 `.at`，复用公开 SDK 与既有测试；不手写业务 Rust、不改生成 Rust/Vue 或临时生成目录来交付修复。`docs/specs/` 是现实现单源；下面的规范增量只是提案，本轮不写 canonical Spec、旧 ledger 或手工索引。原始截图/日志/报告本地保存，Plan 记录命令、退出码、版本/hash 和摘要；不提交新的非 Markdown 证据附件。

保持 `csv.at`/`chart_project.at` 和v1工程内嵌数据；修复前后可打开已有工程，失败不覆盖旧工程或导出。运输层优先复用当前公开Http/JSON/查询绑定；不能用仅ASCII文件名的限制绕过中文任务，不能复制一个私有HTTP栈。框架确有缺陷时按当前owner提最小前置，其他应用任务不等待它。

## 3. 技术栈

应用 `.at`、AutoVM HTTP、现有BarChart/SVG；Vue Playwright、原生MCP、Python独立CSV/XML/几何oracle。复用 `tests/basic/verify_basic.py`、`probe_api.py`、001的原有几何oracle与CSV预算，不泛化到未冻结的line/area/donut。

## 4. 需求分析与背景调查

- 已观察：前端在GET query中直接拼接path/name/out_path，服务端import/save/export走GET标量；001因旧Http body分歧这样规避。Vue fetch percent编码CJK，当前auto-web `server_route.rs::url_decode`仍逐字节转char；G-6b不能视为已关闭。
- 已观察：屏幕bar_chart Init将小数文本截成int求域/刻度；后端 `chart_project.at::parse_dec_hundredths`读全部小数但仅保留前两位。当前已接受的更长小数存在屏幕/导出不同精度，需同时固定数据解释与展示，不能只改标签。
- 001支持≤10MiB、≤10000行、≤64列、1..4数值列、绝对值预算10000000；实际边界与Spec有差异时T-00明确逐项对账，不静默收窄已有合法输入。正常有符号/零/CSV引用/删除源后重开与输出失败保全是回归。
- 当前中文解码与HTTP生成实际owner为auto-web；001内auto-lang旧归属只保留历史。已有公开JSON体或UTF-8修复是否可用由T-00先核实，不预建框架仓或重做Web生态。

| 源文件 | SHA256（完整值） |
|---|---|
| `docs/specs/charts/basic-capabilities.md` | `e466ffd748594987271488b74fc44397516ed682149f460d1724bc582ce237de` |
| `docs/plans/evidence/001/capability-decision.md` | `915831940861476ed5cee79ba0a37f6239f984d55b9f33b6fbc89035dcf94663` |
| `src/back/api.at` | `ba6e7de789ca837e3e08680a3a2254a2904414addc9ee3bac8037de85298f03a` |
| `src/back/chart_project.at` | `00484b53c018bbc41a64e3c243f37173142c422ba4c55715db4b7580890a837d` |
| `src/front/app.at` | `8e30ea78780639fd03dfaf91851e501823396475a1293c0707e9439aab3db28c` |
| `src/front/components/bar_chart.at` | `7845b3b4bd3a405f875191c6a70b58c2830d54813c35e312b06f9fafc897ffca` |
| `tests/basic/verify_basic.py` | `a6c53cec0e0aab285ac94914e94a775096b83233ed8b06328fd1210f59625959` |
| `auto-web` 观察版本 | `c48924f3381e775b8435c3989e739df347570f2c` |
| `D:/autostack/auto-web/crates/auto-web/src/api_gen.rs` | `364d347f22f72290d1595ca887867e458294f6092fb5776d6cbcac1c4aeb1aa5` |
| `D:/autostack/auto-web/crates/auto-web/src/http_server/server_route.rs` | `5e5ccda16f1c242e5772e537ff1db8616b148e081a2db0c07486f9398e4b1a45` |

## 5. 详细设计

1. **T-00 决策稿（新增）** `docs/plans/evidence/002/standalone-decision.md`：固定CLI/tool/当前API版本，探测Vue/VM的UTF-8 query/JSON body全链路、已存在公共API、正式split启动/冷准备及预算，给出app接缝或最小auto-web前置。表明每一条已观察结论与尚待运行验证假说。
2. **传输一致性**：路径/名字/CSV内容在客户端→绑定→文件/工程→回读全过程逐字保留。CJK、空格、`+ & # % ? =`和百分号字面量分别有合法对照，不做双重decode或将字面`+`误作空格。变更类save/export优先迁到现有可用POST体；若现有SDK不支持，T-00先闭合最小前置，不以长期有副作用GET和手工ASCII转义洗绿。已有v1工程格式兼容，不承诺旧有缺陷API永远不变。
3. **小数与几何**：CSV原文存储不被改写；数据解释在屏幕/导出一致，零域退化不吞非零小数，负值基线正确，刻度不重复/不误标整数。T-00冻结现有浮点/可证定点策略及其实际精度，至少0.1/0.2、±0.5、25.5及0.001/0.002必须可区分；不能继续静默截断后声称原值精确。任意精度不承诺，超过可表示精度必须明示策略，不能临时禁用所有小数。
4. **独立启动**：正式VM HTTP split profile，不依赖OS；README统一给Windows可执行准备/启动命令。无app target/gen缓存的准备有阶段和有界超时，坏tool/端口冲突明确失败，只管理本次进程/隔离数据，不清共享框架target。
5. **永久门**：扩展原有 `python tests/basic/verify_basic.py --profile vue|vm`，新增传输/几何用例由T-04落地；独立oracle从CSV原值计算域/基线/逐柱坐标并解析输出XML，不以两端使用同一错误算法相等为通过。工程成功存盘后删除源CSV重开继续导出，失败后下一次合法保存必须成功。

### 规范增量

| delta_id | add/modify/retire | docs/specs/... target | before/after rule | rationale | acceptance IDs |
|---|---|---|---|---|---|
| SD-01 | modify | docs/specs/charts/basic-capabilities.md | 中文降级/整数域/百位截断 → 正式传输、共同明确精度、双工件真实几何及兼容 | 修真实用户数据可用性 | AC-02/03/04 |
| SD-02 | add | docs/specs/charts/standalone-runtime.md | 新增准备/split启动、预算、当前owner与双端永久门 | 独立启动可复验 | AC-01/05 |

## 6. 测试设计

CH-01..06均owner_stage=work，T-04在既有门中使其可执行，拟补测试数据/断言路径为新建并明确与旧API预算门整合；本轮不生成fixture或运行产品。

| Case ID | AC / invariant | 输入/入口 | 区分性 oracle / 预期 | 覆盖边界 |
|---|---|---|---|---|
| CH-01 | AC-01 | 无app构建缓存的文档准备＋Vue/原生独立split启动；占用端口/坏tool | 实际页面/窗口与后端就绪、data_dir正确；失败非零且不碰既有实例 | 不要求Rust后端 |
| CH-02 | AC-02 | 真实UI填中文目录、中文工程名，空格/+&#%?=文件名分别作为有效路径；往返两次 | 后端实际打开的文件sha与独立读源一致，磁盘/重开名字逐字相等；%2520与空格不混淆 | Windows合法文件名；字面?在平台不合法时测工程名/公开绑定层 |
| CH-03 | AC-03 | [0.1,0.2]、[-0.5,0,0.5]、[-300,0,25.5]、[0.001,0.002]、全零、四系列 | 独立计算域/基线/柱坐标；屏幕±1px、SVG±0.01px；不等数据不得塌成同柱或截整数域 | 容差基于560×300逻辑视窗，其他缩放先归一 |
| CH-04 | AC-04 | 旧v1工程、删源重开、坏CSV/非法数值/不可写导出及预算边界 | 旧工程保真；失败旧文件/有效数据hash不变；恢复后下一次保存/导出成功 | 保留001预算与错误分类 |
| CH-05 | AC-02/03/05 | 解码旧字节算法、强制整数域/百位截断的隔离反例 | 中文/小数区分性断言失败，总门非零；还原合法对照通过 | 不在生产库作变异 |
| CH-06 | AC-05 | 原有双端CSV→映射→工程→SVG全流程＋新用例 | 必需实际UI任务均执行，无skip/pending/零场景，错误不被示例数据覆盖 | 柱图合同，非全部图种 |

最终review在同一clone以独立上下文复核真实传输和独立几何oracle；不自动新建agent/chat，不执行无关语言全仓Cargo。

## 7. 验收标准

- AC-01（owner_stage=work）：正式独立VM HTTP双端准备/启动和故障语义明确，CH-01通过。
- AC-02（owner_stage=work）：中文/特殊字符的路径与名字经真实UI及服务端逐字保真，CH-02通过；不得仅API raw UTF-8成功而Vue失败。
- AC-03（owner_stage=work）：合法小数的域/基线/刻度与柱高真实正确，屏幕/SVG符合独立oracle与精度说明，CH-03通过。
- AC-04（owner_stage=work）：既有工程、CSV预算/错误、删源重开及失败后恢复保全成立，CH-04通过。
- AC-05（owner_stage=work）：旧/新真实双端门和CH-05/06完整执行，反例可检测，SD候选与README/roadmap符合结果。
- AC-06（owner_stage=review）：冻结提交独立复审AC-01..05、SD-01/02和实际框架消费版本。
- AC-07（owner_stage=merge）：本app规范/归档/计数/提交push闭合；不动旧001或AutoOS pin。

## 8. 执行步骤

- [ ] T-00（owner_stage=work；依赖001交付；AC-01/02/03）：完成传输/数值/启动全路径有界探针，冻结精度、预算及最小owner前置，不先重写CSV/HTTP栈。
- [ ] T-01（owner_stage=work；依赖T-00及真实必要前置；AC-02）：修前端/API传输接缝，先建立CH-02反例再实现、回放，保留v1工程。
- [ ] T-02（owner_stage=work；依赖T-00；AC-03）：统一屏幕/导出的合法数值解释、域/基线/刻度，建立CH-03独立oracle并排除旧截断反例。
- [ ] T-03（owner_stage=work；依赖T-00/01/02；AC-01/04）：收口正式独立准备/启动、错误分类、旧工程/失败恢复，不增加OS依赖。
- [ ] T-04（owner_stage=work；依赖T-03；AC-05）：扩展原有双profile门，跑CH-01..06及必要旧预算/几何回归、反控；准备SD候选。
- [ ] T-05（owner_stage=work；依赖T-04；AC-01..05）：复核漂移、精度与兼容证据、README/roadmap，提交execution_done。
- [ ] T-06（owner_stage=review；依赖T-05；AC-06）：同clone独立上下文最终复审，源码相同不替代独立数值/字节对账。
- [ ] T-07（owner_stage=merge；依赖T-06 pass；AC-07）：仅app规范/归档/提交push收尾，AutoOS版本留未来统一计划。

## 9. 复审记录

- stage: new | plan_id: CHARTS-002 | plan_revision: 1 | outcome: pass（仅有界 T-00 就绪，产品与双端验收未执行） | next: work/T-00（等待后续实施指令）。
- 现有归档计划、Spec 与源码保持原样；旧验收只证明其冻结版本与已声明范围。应用提交/push 不升级 AutoOS 组合版本。

## 10. 待澄清事项

本次规划没有待用户重新确认的产品方向。T-00 负责核实技术能力与实际 owner，决策稿必须先闭合再进入依赖实现。若探针显示必须改变目标、降低必需验收或扩大跨仓写入范围，报告具体证据并保留受影响任务未完成；不得用占位、跳过、API 预操作或历史总数替代必需用户任务。
