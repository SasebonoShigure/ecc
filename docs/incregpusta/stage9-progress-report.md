# Stage 9 实施进度（未验收）

2026-09-09 开始。当前基线 ecc 872d474、ecc-tools 044399b41；用户授权执行整个 Stage 9。

已核对实际 worktree：子仓库干净；父仓库保留用户 CLAUDE.md 和四份既有未跟踪报告，无仍运行的 Stage 9 构建。

[详细设计草案](stage9-detailed-plan.md) 已写入并交独立设计 reviewer 审查。复用 Stage 6 canonical mixed builder/Kahn 与 Stage 8 device/native transaction，计划逐批 CPU mixed graph→GPU old-level D2D/new-node H2D/node2level→全图 GPU propagation。无需 CPU Dual-CSR correctness shadow。

尚未修改实现、尚未执行 Stage 9 correctness gate；不将 Stage 8 验收结果作为 Stage 9 完成证据。当前两套 Release CUDA ON/OFF 构建配置已核对，后续日志保存各 build/stage9-evidence/，禁止只存临时目录。用户随后授权 commit，本次仅提交设计草案与进度报告，不 push。

## 独立设计审查结果

审查结论为 REQUEST CHANGES，以下两项尚未解决，实施前须修订并复审：

1. 明确 topology traversal 的真实 Base/Aux 归属来源。现有 ArcBinding 不保存 storage kind，仅补 eligibility 不足；不得伪造 payload 或将所有 binding 标为 Base。ActualDagCycleClassifier 也须复用窄入口。
2. 明确受控 builder→Kahn 的验证归属。当前公共 Kahn 入口无条件完整验证 graph 和 result，直接复用会在 OFF 路径留下重复证明。外部输入校验和必要边界、processed count、indegree underflow、cycle 检查仍须保留。

后续计划还须明确三个 fallback 验收：DAG order conflict 在 Error 下拒绝、同例在 FullWithRecord 下真实 full 成功、actual cycle 在 FullWithRecord 下仍失败且不发布；CPU mixed build/Kahn 等待时间不能计入 GPU reconstruction。

本次提交不包含实现代码或 Stage 9 测试结果，也不代表设计审查通过。

## 第二轮设计批准与核心实现（仍未验收）

独立设计 reviewer 已批准第二轮计划，两个初始 blocker 及 fallback/计时边界均已写入详细计划。实现已开始，先完成 canonical topology traversal、借用上一代 levels 的内部入口，以及真实 CUDA mixed reconstruction；没有建立 CPU Dual-CSR 或 timing shadow。

当前实现使用旧 level D2D、单份 new-node/position 批量 H2D 和并行 node2level kernel，随后复用既有全图 GPU propagation。patch status、roots 输入、范围/cycle/数值/owner 检查保留；CPU reconstruction oracle 和独立 level proof 仅 ON。下一步为生产 trace/mode/Python/controller 集成及完整验收。

已执行的局部验证（均不替代最终 Stage 9 验收）：

- ON canonical mixed 严格构建完成；首轮属性测试暴露 high-water overflow 错误分类被 previous-level 检查提前遮蔽，已恢复原优先级，第二轮 7/7 通过。
- CUDA 首轮编译暴露新 mixed 类型的头引用遗漏，已修复；Release ON 的原 full 与新增 mixed session 实机测试 2/2 通过。
- 独立 Release OFF 严格构建及 core GPU/CPU 边界测试 4/4 通过。与 ON 使用现有相同 GCC、CUDA 和依赖，没有升级。
- 独立代码 reviewer 审查当前核心范围，发现 Kahn result validator 内部仍重复 graph 全检。已拆开内部 result proof 与公开 graph+result validator，复核后批准核心范围；此修复后仍须重编译回归。
- 根据审查意见新增 300 个新节点的 mixed case，以实际完整 levels 读回覆盖跨 CUDA block 插入和逆映射；尚待执行。

证据位于 ecc-tools/build-incregpusta-cuda-{on,off}/stage9-evidence/ 的 mixed-build、mixed-tests、cuda-build、cuda-tests 系列日志，失败与修复重跑分文件保留。当前 runtime/controller 正在修改，未完成最终独立审查、sanitizer、性能/调用剖析、跨构建及 parent 验收。后续实现不自动沿用此次文档 commit 授权，不 push。


## 生产集成阶段性提交（2026-09-09，仍未完成验收）

用户再次授权 commit。本次提交当前 Stage 9 实现、测试、Python 接口及修订设计，不 push；上文“尚未修改实现”“尚待执行”和仅文档提交描述保留为历史记录，以本节为当前状态。用户已有 CLAUDE.md 修改和四份独立报告不纳入提交。

生产 frozen trace 已接入 CPU canonical mixed build/Kahn → GPU old-level D2D、新节点批量 H2D、并行 node2level → 全图 GPU propagation，并记录真实 requested/executed/fallback。通用 CUDA session 的初始计算仍如实报告 baseline_only/full；它没有新增编辑 API。默认 OFF 不创建 CPU reconstruction oracle，ON 保留独立 fresh CPU/full、GPU/full 对照和 level 合法性检查。

真实 fallback policy 已提取为模块内部函数，生产 replayer 与 native 测试调用同一实现：仅 old-level order conflict 可显式 full 重试；先销毁失败候选，再分配 full 候选；cycle 不回退。测试覆盖 Error 拒绝、FullWithRecord 实际成功、cycle 拒绝，以及各分支后继续提交。独立代码 reviewer 已批准这次提取及测试，没有提交前 blocker。

已完成验证：

- 最终新增 helper、测试和 probe 在相同既有 GCC/CUDA/Release 的独立 ON/OFF 构建成功；各运行 mixed session、真实 fallback policy、synthetic 两批 trace 和 real buffer fanout，共各 4/4 通过。ON 执行独立诊断对照，OFF 执行性能采样。证据为两构建 stage9-evidence/commit-build.log 和 commit-tests.log。
- mixed session 已通过 300 新节点跨 block 插入、实际 order conflict 和 eligibility 更新。此前原 full/mixed 及 execution contract 回归也通过，见 integration-tests.log、review-fixes-tests.log。
- 同输入 ON/OFF 实际设备读回 generation 0–2 的拓扑、levels、完整 timing 一致，见 cross-build.json 和 ON 的 cross-build-verdict.json。
- ON mixed session 的 memcheck、initcheck 均为 0 errors，见 mixed-memcheck.log、mixed-initcheck.log；该结果不涵盖最后新增的独立 fallback executable。
- Parent session/mode 相关测试 72 passed，见 parent-session-r2.log。修改的 Python 文件 Ruff 检查通过。

实际失败及修复：除上文 mixed 错误优先级和头引用问题外，生产 probe 构建暴露 preparer 对整个 device session 头的额外耦合，已将 patch 类型移入窄头；runtime 补齐其实际消费的 execution contract target 依赖。Parent 首轮 3 failed/69 passed：两个测试误写只读属性，另一个暴露新增 reason 未同步 schema，均已修复后得到上述 72 passed。独立审查还发现性能结果未绑定请求 prefix，以及 full 重试同时持有失败候选；分别修复为请求批数及连续 generation 检查、先释放再重试。早期 Ruff 问题已修复。一次构建命令误用了不存在的 execution contract target，改为 ista_execution_contract_test 后成功。提交前第一次命令因 PowerShell 引号在启动 WSL 构建前失败，改为通过标准输入传递脚本后上述双模式构建与测试成功。

仍待验收：成功 mixed 路径调用剖析、fallback 分配顺序与 cycle 无 full kernel 的运行证据、实际 controller 错误 canary/子进程审计、最后新增 fallback executable 的 sanitizer、真实 Python binding 双模式检查、完整相关 parent/native 回归和类型检查，以及开发规范、检查分类和总计划的最终同步。本次没有宣称完整类型检查或 Stage 9 验收通过，也不从局部性能样本推导加速结论。
