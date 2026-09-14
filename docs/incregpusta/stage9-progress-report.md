# Stage 9 实施与验收报告

当前状态：Stage 9 实现和本机验收完成；最终结果见文末“最终验收”。下文保留各次未验收进度和失败记录。

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


## 最终验收（2026-09-09）

实现已在 ecc-tools `73aa7816f`、ecc `a8697e5` 阶段性提交。本次继续工作补齐验收和旧测试适配，保留未提交差异，不自动 commit/push。Stage 9 在本机验收完成；不包含 Stage 10 physical/greedy 集成，也不声称当前串行 propagation 已获得加速。

### 实现边界与独立审查

每个真实 frozen edit 执行 native descriptor/targeted device patch → CPU canonical mixed build/Kahn → GPU old-level D2D、新节点批量 H2D、并行逆映射 → full GPU forward/backward propagation → 原子 native/device 发布。全图传播、Database 隔离副本和 device D2D 事务成本保留。binding 仅保存必要拓扑元数据，未引入 CPU Dual-CSR/timing shadow。默认仍 cpu/full、CUDA build OFF、debug checks OFF。

独立设计二轮批准，独立代码审查覆盖 canonical core、生产 runtime/controller、真实 fallback、最终硬件/绑定回归修复；均无未解决 blocker。审查促成的重复 proof、prefix 信任和失败候选释放问题已修复。通用 Python API 无编辑时仍为 baseline_only/full，不冒充执行过 incremental batch；实际编辑由 frozen runtime 负责。

### 正确性、构建和失败重跑

所有证据相对子仓库，保存于 `build-incregpusta-cuda-on/stage9-evidence/`（ON）、`build-incregpusta-cuda-off/stage9-evidence/`（OFF）和 `build-incregpusta-off/stage9-evidence/`（默认无 CUDA）。三者同为现有 GCC 14.3 Release；两套 CUDA 使用同一 nvcc 12.8.93、RTX 4070 Laptop GPU，未升级依赖。

| 要求 | 实际证据及结果 |
|---|---|
| 全 iSTA CUDA/ON 回归 | `native-regression-build.log` 严格构建成功；首轮 185 passed/2 failed（旧 session 与 Python binding 恒拒绝 CUDA 假设）。修复后 `final-regression-tests.log` 7/7，包括两项失败、新 no-device、mixed 硬件错误和两条生产 trace。未将首轮报告改成全绿。 |
| 全 iSTA CUDA/OFF 回归 | `native-regression-tests.log` 首轮 151 passed/1 failed/28 Disabled；失败因运行期间更新 binding CLI、CTest 尚未重新生成参数。重新配置后 `final-regression-tests.log` 4 passed/1 Disabled。OFF 诊断测试未执行不计通过。 |
| 默认 CUDA OFF 回归 | `final-regression-build.log` 全 iSTA 和 binding 构建成功；首次 141 passed/1 Not Run/28 Disabled，原因是配置前生成的构建目标列表遗漏新 topology target。补编后 `default-missing-target-test.log` 1/1。`default-ldd.log` 确认 native 无 CUDA 依赖。 |
| CPU canonical mixed 与输入/生命周期 | 上述 native 回归覆盖 old/new、proxy/parallel、cycle/old-order conflict、malformed previous、empty、多批次、容量/边界、stale/owner、CPU scatter 和 rollback；ON 保留 property、fresh/source isolation 和故障诊断，OFF 保留功能及必要拒绝路径。 |
| 真实 GPU mixed/fallback | `commit-tests.log` 两模式各 4/4；300 新节点跨 block 重建、Base/Aux、eligibility 更新、数值/cycle、所有权和连续提交；production fallback 三例 Error 拒绝、FullWithRecord 真 full、cycle 拒绝，均验证随后健康提交。 |
| 每批独立 CPU/full、CUDA/full | ON `synthetic-r1/`、`real-buffer-r1/` 和最终 CTest 输出逐 prefix 比较所有 timing/winner 字段，独立验证 levels、source physical/artifact isolation、真实回滚。目标 trace 全部 requested/executed incremental、full_graph、无 fallback。 |
| 跨构建实际值与模式 | `final-cross-build-verdict.json` 汇总真实设备 generations 0–2 topology/levels/完整 timing 的 ON/OFF 相等、逐批 execution/generation/输入尺寸相等，以及实际 Python QOR/paths 相等。比较排除计时、诊断和 session 实例身份，不并入性能采样。 |
| 真实 Python API | 两套 binding 顺序重编、分别保存。`python-acceptance.log` 与各 `python-*.log`：CUDA inc/full、CPU/full 的两次 diamond 生命周期、unsupported analysis 后健康运行、no-device 全通过；默认构建 `python-cpu-incremental.log`、`python-cuda-incremental-unavailable.log` 分别验证 CPU baseline 和 CUDA typed unsupported。 |
| 硬件错误和恢复 | ON `ordered-hardware-fault-replay.json`：实际非法设备地址+sync 使 mixed stage/debug 失败、origin poison、sibling 拒绝；该进程退出后，独立健康进程按 mixed trace 重放并对 CPU/full、GPU/full。不是在损坏 context 中继续。 |
| sanitizer | ON mixed session 与最后独立 fallback executable 的 memcheck/initcheck 均 0 errors，见 `mixed-{memcheck,initcheck}.log`、`fallback-{memcheck,initcheck}.log`。真实 fault 实验不拿来要求 sanitizer 零错误。 |
| Parent 回归 | `parent-non-pdk.log`：1679 passed、6 skipped、4 deselected、13 xfailed，2 条依赖 deprecation warnings。最终新增测试仅修改 mock 方式后 `parent-session-r3.log` 35 passed。 |
| lint/type | 修改 Python 的 Ruff 通过；生产 Python mode/session/smoke 的 `production-python-type.log` 通过，controller 用实际模块搜索路径检查后通过 `controller-type-r2.log`。全仓 `parent-full-type.log` exit 1，2140 diagnostics；所选测试文件还存在 31 项，已用 Stage 9 前 `872d474` 内容在 `parent-test-type-baseline.log` 复现同 31 项。本轮新测试的两项已修复。另对原生 `PythonBindingContractTest.py` 检查得到 1 项 `ecc_py` unresolved-import（无静态类型声明，`binding-test-type.log`），真实 binding CTest 已通过；不为消除此项引入假 stub 或 ignore。不宣称全仓类型检查通过。 |

### 实际调用、分配和传输证据

OFF `mixed-call-profile/` 保存真实二进制符号、GDB 命令、调用栈、API 方向/字节和 workload；使用 `run-mixed-profile.py` 复现。两批 prepare/candidate/stage、canonical mixed build/Kahn、新节点 kernel、node2level 和 propagation 均实际命中。批次区间 CPU full/FIFO/DualUpdater、完整 export/pack、CPU reconstruction、GPU full levelizer、device debug readback 与完整 scatter diagnostic 均为零。该结论来自运行断点，不来自源码字符串或固定计数返回值。

两批实际 `cudaMalloc` 共 60 次、`cudaMemcpyAsync` 98 次，H2D/D2H/D2D 分别 8936/21384/25624 bytes，精确对应真实 telemetry。初始化另有 44 次分配、2 次 export/pack、2 次 full levelize，不纳入逐批零调用结论。

OFF `fallback-call-profile/` 用真实 production helper 和真实 patch，记录 `cudaMalloc` 返回指针与 `cudaFree`：full 重试开始时失败 mixed 候选存活分配为 0；Error/cycle 首次 policy 各仅一次 stage、零 full levelizer，FullWithRecord 实际第二次 stage 中一次 full levelizer。`run-fallback-profile.py`、原始各分支日志和 verdict 保存。实际 full 对照、发布后 mixed 继续由 native fallback test 验证，不用计数授权发布。

### OFF 性能与原始阶段时间

`controller-behavior-audit.json` 的真实 Popen 记录证明 OFF 仅 build-info、warmup 和 3 个 incremental-performance 样本，无 oracle/receipt；ON 只 build-info 即拒绝采样，旧成功输出清除。真实 child 输出经 timing、层号、device-equivalence、缺批破坏均被拒绝；OFF 样本自报缩短 prefix 和不连续 generation 也被拒绝。结果文件明确 `correctness_comparison=not_run`。

以下是 OFF `controller-process-audit/sample-0.json` 的未插桩原始样本，单位 ms。它是入口及阶段计时验证，不是统计性能结论。

| batch | update GPU | CPU build | CPU Kahn | CPU plan | GPU reconstruction | propagation GPU | scatter | batch total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1（8 nodes/7 arcs） | 0.386016 | 0.042678 | 0.001821 | 0.000764 | 0.289408 | 0.187392 | 0.047466 | 2.162888 |
| 2（12 nodes/11 arcs） | 0.085088 | 0.005061 | 0.001662 | 0.000874 | 0.080320 | 0.299008 | 0.051764 | 2.897642 |

batch total 包含 native prepare/install、编码/分配、传输及同步，不能用表中部分阶段相加替代。GPU reconstruction event 从 CPU plan 后才开始；levelization_total 另包含 CPU build/Kahn/plan。完整 process 原始样本还包含加载和清理。每批 launches=6 的当前值是实测，不是固定数量验收门禁。

### 复现与范围

从 ecc 根使用 bare flake：`nix --extra-experimental-features nix-command --extra-experimental-features flakes develop --command ...`；实际 CUDA 设置 `LD_LIBRARY_PATH=/usr/lib/wsl/lib`，Python 使用既有 3.11 和选定构建的 `python/` 包。`run-native-regression.py`、`run-final-regressions.py` 保存 native 构建/CTest 范围；`run-python-acceptance.py`、`controller-behavior-audit.py` 保存真实入口与故障 canary。构建日志保留全部首次失败与修复后重跑，未覆盖写成功。

注意共用 bin 的 ecc_py 输出：各构建的测试必须加载对应产物。本次 binding CTest 新增实际 CUDA/debug 状态核验，防止混用；完成默认构建验收后已恢复本轮开始时的 Release/CUDA/debug-OFF 共用产物，三套 isolated package 均保留。

开发规范、检查分类、Stage 6 复用说明、总计划和 Stage 9 详细计划已同步。通用 README、用户 CLAUDE.md 和四份独立报告保持原样。Stage 9 的验收范围已闭合；全仓既有类型问题和 Stage 10 物理跨层集成不被此结论覆盖。
