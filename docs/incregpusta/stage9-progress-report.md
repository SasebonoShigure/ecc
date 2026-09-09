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
