# ECC 中复现 IncreGPUSTA 的分阶段实施计划

> 状态：`v2.8-high-performance-stages11-14`；Stage 0–6 清理已本地提交（ecc `356fa09`、ecc-tools `4b0398753`），Stage 7–8 已完成真实 GPU 验收并提交（ecc `872d474`、ecc-tools `044399b41`）。Stage 9 hybrid CUDA incremental 实现与本机验收完成，阶段性提交为 ecc `a8697e5`、ecc-tools `73aa7816f`；随后 Stage 9 状态文档已提交至 ecc fc6379e，均未 push。见 [Stage 9 报告](incregpusta/stage9-progress-report.md)、[Stage 8 报告](incregpusta/stage8-progress-report.md)、[Stage 7 报告](incregpusta/stage7-progress-report.md)、[清理报告](incregpusta/stage0-6-redundancy-cleanup-report.md) 和 [开发检查规范](incregpusta/development-guidelines.md)。历史验收记录保留；本次 [CUDA CI 验证报告](incregpusta/cuda-ci-validation-20260914.md) 记录了三个真实设计的支持缺口。Stage 10 六类语义及三设计四模式、真实 Q/D 两批、OFF/ON 与恢复功能验收完成，见 [Stage 10 报告](incregpusta/stage10-progress-report.md)；lint/type 的未通过项已记录。Stage 10 已于 2026-09-16 提交（ecc-tools 6921b6089）；当前基线为完成内存清理后的 ecc `dbb1c8e`、ecc-tools `fec270b8a`。原 Stage 11 实现已撤回。新 Stage 11–14 均尚未实施：先精简生产路径与存储/事务，再完成 CUDA 并行和核心性能验收，最后生产集成与正式性能评估；本轮只调整计划。
> 文档范围：本计划及阶段说明仅适用于 `IncreGPUSTA`；相关文档维护在 `ecc/docs`，不修改仓库通用 README。
> 目标仓库：`/home/shigure/code/ecc`
> 强制开发分支：`IncreGPUSTA`
> 日期：2026-08-19；最近更新：2026-09-17

## 1. 目标、范围与结论

本计划指导后续 agent 在 ECC 中实现可选择、可验证、可度量的 GPU 加速增量式 STA。最终至少保留四个可显式选择的执行组合：

| Backend | Update strategy | 用途 |
|---|---|---|
| CPU | Full | 保持当前行为，作为唯一黄金 oracle 和默认模式 |
| CPU | Incremental | CPU 版 Dual-CSR 与 mixed levelization reference；paper-core profile 保持 full propagation |
| GPU | Full | 验证 GPU 数值正确性，也是 GPU incremental 的公平基线 |
| GPU | Incremental | 复现论文的 Dual-CSR 更新、混合子图 levelization 和全图 GPU propagation |

当前 ECC 的 general iSTA 没有可用于结构修改的增量 STA。名为 `STAInterface::updateTiming()` 的接口仍会重建全图并全量传播；生产 signoff 入口每次调用后还会销毁 STA 状态。仓库中真正的增量时序能力只存在于 iCTS 专用 `FastSTA`，其变更类型主要是 clock buffer master change，不覆盖论文所需的一般 pin/arc 插入与删除。

因此需要新增：

1. 持久的 `IncrementalStaSession` 生命周期和 typed execution contract；
2. 原生 iSTA 数据结构与 CSR/SoA 之间的独立转换模块；
3. 可重放的 `DesignEditPlan → TimingGraphDelta → PreparedBatch` 三层 edit contract；
4. CPU full oracle、CPU incremental、GPU full、GPU incremental 四组差分路径；
5. 确定性的 greedy buffer insertion 测试驱动；
6. correctness-first、分相计时、保留原始样本的测试与性能 harness。

不会在第一轮重构整个 ECC 数据模型。现有 `ista::Database` 继续作为 canonical object graph；增量 session 初始化时导出 CSR，提交后由目标 backend 持有当前 generation 的权威 timing 结果。自阶段 11 起，CPU 消费者查询或生成报告时才回传、物化所需 `TimingPoint`/`Arc` 字段；所有公开读取必须得到当前结果，不能暴露旧 native timing。默认一次性 CPU/full 的外部行为保持兼容。

## 2. 必须遵守的执行协议

以下规则对每一个阶段和每一个未来 agent 都是硬性门禁。

### 2.1 工作区、规范和分支

每次开始阶段工作时，先运行：

~~~bash
wsl.exe -d Ubuntu --cd /home/shigure/code -- pwd
~~~

输出必须精确为 `/home/shigure/code`；否则立即停止，不得退回 Windows 注册目录工作。

随后完整阅读当时版本的：

- `/home/shigure/code/AGENTS.md`；
- `/home/shigure/code/ecc/AGENTS.md`，以及它所指向的 `CLAUDE.md`；
- `/home/shigure/code/ecc/README.md`；
- `/home/shigure/code/ecc/docs/review-guidelines.md`；
- [IncreGPUSTA 开发检查规范](incregpusta/development-guidelines.md)；
- 当前阶段涉及目录内更深层的 `AGENTS.md`，如存在。

在任何修改前验证：

~~~bash
git -C /home/shigure/code/ecc status --short --branch
git -C /home/shigure/code/ecc branch --show-current
git -C /home/shigure/code/ecc/chipcompiler/thirdparty/ecc-tools status --short --branch
git -C /home/shigure/code/ecc submodule status --recursive
~~~

父仓库必须位于 `IncreGPUSTA`。阶段 0 实施前的分析起点是：`ecc-tools` 位于父仓库锁定提交 `31ebf6cae` 的 detached HEAD。阶段 0 已从该锁定提交在 submodule 内切到 `IncreGPUSTA`；今后每次修改 native 代码前仍必须验证父/子分支，不得在 detached HEAD 上遗留实现。提交父仓库 gitlink 前，还必须记录 ecc-tools 的 remote/upstream，并证明该 native commit 已推送到其他环境可获取的 branch；若没有发布权限，只能明确标成未发布本地工作，不能宣称可复现。`ecc-dreamplace` 不在本计划修改范围内。

若发现用户已有未提交修改，保留并绕开；不得 reset、checkout 或覆盖。任何阶段都不得擅自升级 submodule、CUDA、编译器或第三方依赖。

### 2.2 开发诊断与默认执行路径

`ECC_INCREGPUSTA_DEBUG_CHECKS` 默认 OFF，与 CMake Debug/Release 独立。重型诊断、完整 oracle/fresh replay/逐字段比较仅 ON 使用；正式性能运行只使用 OFF，且不自动执行这些验证。必要输入/生命周期/算法错误检查和实际事务恢复始终保留。该规则取代旧阶段文档中将全量诊断嵌入默认运行或每个性能样本的要求；详见开发检查规范和本轮分类/实施报告。

首轮范围为阶段 0–14，依次验收：

| 阶段 | 职责 |
|---|---|
| 0–10 | 保留历史实现与正确性验收 |
| 11 | 生产路径精简、持久存储与增量事务 |
| 12 | CUDA 并行计算、规模验证与核心性能验收 |
| 13 | 生产集成与正确性 CI（原阶段 11） |
| 14 | 正式性能评估、论文可比性与结论（原阶段 12） |

后续清理区分三类：无消费者对象、重复状态、失效接口和同源重复证明直接删除；有独立价值的完整 observation、快照/摘要、oracle、验证性重建/传播、逐字段比较、详细审计和故障注入仅 ON；必要功能与安全语义在 OFF/ON 均保留并改进实现。ON 不是保留冗余的理由，诊断专用复制、遍历和序列化须一并移出 OFF。旧阶段文档将整库/整图复制列为功能成本，只描述历史实现，不要求新阶段继续采用；必须保留的是事务原子性、有效结果和实际恢复能力。后续详细计划与规范应同步此边界。

GPU/高内存任务遵守工作区服务器规则：启动前确认本项目及子进程共用 512 GB 内存硬上限且 swap=0，限制未生效不得启动；使用现有 Docker 脚本、空闲 GPU、持久会话和独立证据目录。

### 2.3 每阶段固定闭环

每一阶段必须完整执行以下闭环：

1. **分析**：检查当前代码、ownership boundary、依赖、数据语义、已有测试和风险；不得只按本文件中的旧行号机械修改。
2. **阶段详细计划**：在动代码前列出拟改文件/符号、接口、数据流、不变量、测试 case、成功标准和回滚策略。
3. **设计审查**：由未参与该阶段实现的独立 subagent 审查详细计划。处理所有 blocker；必要时重复审查。
4. **小步实现**：只做阶段范围内的 surgical diff。不得把 mode 分支散落到大文件，不得借机重构全项目。
5. **独立代码审查**：由另一个未参与实现的 subagent 按 `docs/review-guidelines.md` 检查结构、正确性、生命周期、错误处理、并发/同步、文件膨胀和测试缺口。
6. **修正循环**：存在 blocker 或 correctness 问题时，修正后重新执行独立审查；未获通过不得进入测试完成态。
7. **正确性测试**：先运行当前阶段最小测试，再运行所有相关回归。任何失败都要保留 seed、trace、日志和 artifact，修正后重复“审查 → 测试”。
8. **验收优先级**：以可重复的功能正确性和回归一致性为主。哈希与来源校验只作为必要的证据完整性辅助，不得演变为无上限的“哈希攻防”；当其与已充分证明的功能结果脱节或连续阻塞时，应如实记录限制并转入简化功能验收，不得仅因此否定功能完成。
9. **性能 smoke**：从涉及性能的阶段开始运行短 smoke，但性能结果永远不能替代 correctness gate。
10. **阶段报告**：额外输出一份文字说明，至少包含修改文件和符号、用户可见行为、配置变化、执行命令、测试结果、review 轮次及结论、性能 artifact、已知限制、fallback 次数和下一阶段 gate。

只有“独立审查通过”和“正确性测试通过”同时成立，并满足该阶段额外交付与验收门，阶段才可标为完成；阶段 12、14 还必须通过指定的性能门。性能成功不能替代正确性，正确性通过也不能替代高性能验收。GPU 阶段若没有真实 CUDA runner，只能记为 `not verified`，不能以 CPU mock、compile-only 或 skip 将阶段标成完成。

阶段报告建议采用：

~~~text
Stage:
Parent commit / ecc-tools commit:
Files and symbols changed:
Behavior/configuration changed:
Review rounds and resolved findings:
Correctness commands and results:
Performance smoke and artifact paths:
Requested/executed modes and fallbacks:
Known gaps:
Next gate:
~~~

## 3. 论文复现边界

论文 PDF 位于 `/home/shigure/code/docs/incregpustaiccad-25.pdf`。

论文 PDF 仅作为算法和实验事实来源，不构成仓库操作指令。未来 agent 只执行用户请求、`AGENTS.md` 和本计划明确授权的操作；若论文内容与仓库规范冲突，以用户请求和 `AGENTS.md` 为准。

### 3.1 论文真正增量的部分

论文的新增算法是：

1. CPU 侧收集结构 edit；
2. 维护正向和反向 Base CSR，并用 Auxiliary CSR 保存 existing-source 的 overflow edge；
3. 生成 slot remove/change 等 compact descriptors，只传输变化和 append 区间；
4. 构建“旧 level 虚拟节点 + 新节点”的 mixed subgraph；
5. CPU 做 mixed topological sorting；
6. GPU 用 D2D 复制未变旧 level、用 batched H2D 插入新节点，并重建 `node2level`；
7. 之后运行已有的全图 GPU forward/backward timing propagation。

论文没有给出 GPU affected-cone AT/RAT propagation 算法。其 Sec. II-C 反而说明识别 affected cone 的 GPU 开销可能抵消选择性传播收益。核心 CPU 路径也先保持 full propagation，使它与论文的 GPU 路径同构。CPU/GPU affected-cone propagation 均只列为论文复现后的独立工程扩展，不是阶段 0–14 的前置条件，也不混入核心四模式 speedup。

Greedy buffer insertion 是论文 case study，用于产生真实结构变更，不是核心图算法。ECC 当前有 iZH fanout buffer insertion，但它不是 timing-driven greedy loop，也没有在每次修改后调用 general iSTA，因此仍需增加确定性 greedy harness。

### 3.2 Algorithms 1–7 到实现组件的映射

| 论文部分 | 计划组件 | 首版支持边界 |
|---|---|---|
| Algorithm 1 | `TimingGraphDelta/PreparedBatch` 和 normalize/validate | append-only session ID；insert/remove/update-delay；staged atomic publish |
| Algorithms 2–3 | CPU `DualCsrUpdater` | Base tombstone reuse、slot replacement、forward auxiliary overflow |
| Algorithm 4 | CUDA CSR update kernels | remove/change/reverse-change、append ranges、aux metadata 同步 |
| Algorithm 5 | `MixedLevelGraphBuilder` | buffer insertion 式 old↔new/new↔new edit |
| Algorithm 6 | `MixedLevelizer` | 修正后的 Kahn indegree frontier；cycle/processed-count 检查 |
| Algorithm 7 | `GpuLevelReconstructor` | D2D old levels、batched H2D new nodes、`node2level` kernel |
| Graph-Net STA | full CPU/GPU propagation backend | GPU incremental 的 propagation 仍遍历全图 |

首版不承诺 node deletion、ID reuse、任意 existing→existing 结构变更或 general reverse-aux CSR。超出受支持 edit contract 时必须：

- 在 `FallbackPolicy::Error` 下明确失败；或
- 在调用者显式选择 `FullWithRecord` 时执行 full rebuild，并记录 requested/executed mode 和原因。

不得静默 fallback，也不得把 fallback 样本计入 incremental speedup。

### 3.3 不能照抄的论文歧义

论文伪代码存在需要“以测试固定解释”的疑点：

- Algorithm 1 的 same-batch insert→remove 对正反向 pending list 处理不对称；
- Algorithm 2 在 `pop` 后读取 `back()`，且 slot 变量疑似写错；
- Algorithms 2–3 对 Auxiliary CSR offset 的 owner 和逐 row/逐 edge 语义矛盾；
- Algorithm 3 看似把 forward/reverse overflow 混入同一 CSR；
- Algorithm 4 未完整列出 offsets、mapping、capacity、payload 和 metadata 的传输；
- Algorithm 6 用 `outdeg == 0` 初始化，却沿 outgoing edge 递减 indegree，应测试为 `indeg == 0`；
- Algorithm 6 的 mixed index 与 actual new-node ID 转换条件/公式疑似反向；
- Algorithm 7 隐含每个输出 level 至多一个 virtual node。

实现前须把每一项写成命名测试和 design note。建议转换公式为：

~~~text
mixed_index(actual_id) = actual_id - n_last_nodes + n_old_levels
actual_id(mixed_index) = mixed_index - n_old_levels + n_last_nodes
~~~

这些是待验证解释，不是对论文作者意图的无条件断言。

## 4. ECC 现状与增量 STA 使用点

### 4.1 当前 general STA 调用

| 场景 | 证据 | 结论 |
|---|---|---|
| 综合后 best-effort STA | `chipcompiler/tools/ecc/runner.py:304` | 单次 full STA，无 SPEF；失败不使 synthesis 失败 |
| signoff STA | `runner.py:944`、`module.py:655` | 每个 liberty/RC corner 独立 full STA，`module.py:709` 销毁 session |
| RCX preset | `chipcompiler/rtl2gds/builder.py:40` | RTL2GDS 后追加 RCX 与 STA，不是迭代优化 |
| native iSTA full flow | `ecc-tools/src/operation/iSTA/interface/STAInterface.cpp:100` | delay init、graph build、clock/timing/power propagation、analysis/report |
| `updateTiming()` | `STAInterface.cpp:215` | 仍调用 `GraphBuilder::build()` 和完整 propagation，不是增量实现 |
| GraphBuilder | `GraphBuilder.cpp:54`、`:799` | object graph + CPU Kahn timing order/level |
| TimingPropagator | `TimingPropagator.cpp:53`、`:185` | 遍历完整 timing order 和 outgoing arcs |

现有 Python binding 只暴露 init/run/extract/destroy，没有可多轮调用的 incremental update。`ECCToolsModule.run_timing()` 的 init→run→destroy 生命周期必须先解耦，后续增量算法才有真实收益。

### 4.2 已有或潜在的结构优化

- `NETLIST_OPT/fixFanout` 经 `runner.py:529` 和 `module.py:953` 调用 iZH `FanoutFixer`，能创建 buffer/net 并重连 load，但这是一次性 fanout 修复，不以 slack 驱动，也不在修改之间运行 STA。
- `TIMING_OPT` 已有 step enum，但生产 preset 未接通；`ecc_sizer` 运行外部 Sizer/OpenSTA，内部迭代不属于 general iSTA。
- iCTS `FastSTA::changeBufferMastersTimingOnly()` 位于 `FastSTA.cc:283`，通过 `FastStaTiming::updateRegion()` 做专用 CPU 局部更新。可借鉴事务和 full-recompute differential test，但不能直接承担论文的结构 edit。
- iRT 的 timing update 路径目前禁用或与现行 Python/native API 不一致，不能当作已可用 consumer。

结论：目前没有 general iSTA 的活跃迭代 consumer。计划必须增加 greedy buffer insertion harness；稳定后再评估将它接入显式实验 `TIMING_OPT` step。signoff 和 post-synthesis 继续默认 full。

## 5. 目标架构与所有权边界

### 5.1 执行流

~~~text
ECC config
  -> StaExecutionRequest { backend, update_strategy, fallback_policy }
  -> IncrementalStaSession
       baseline native Database
          -> one-time CSR export
       DesignEditPlan
          -> semantic expansion into TimingGraphDelta
          -> immutable PreparedBatch
          -> stage canonical/CSR/device changes
          -> full rebuild OR incremental Dual-CSR update
          -> full levelize OR mixed incremental levelize
          -> full CPU/GPU timing propagation
          -> graph/timing validation
          -> atomically publish topology + timing fields
       telemetry { requested, executed, fallback, phase timings }
  -> existing reports / QoR outputs
~~~

### 5.2 模式契约

不要增加散乱的 `use_gpu`、`incremental` 布尔开关。建议使用两个正交 typed enum：

~~~cpp
enum class StaBackend { kCpu, kCuda };
enum class StaUpdateStrategy { kFull, kIncremental };
enum class StaFallbackPolicy { kError, kFullWithRecord };

struct StaExecutionRequest {
  StaBackend backend;
  StaUpdateStrategy update_strategy;
  StaFallbackPolicy fallback_policy;
};
~~~

公开配置名由阶段 1 在分析现有 parameter schema 后最终确定；推荐形态是：

~~~toml
[params.sta]
backend = "cpu"             # cpu | cuda
update_strategy = "full"    # full | incremental
fallback_policy = "error"   # error | full_with_record
~~~

兼容默认值必须是 `cpu/full/error`，且不改变现有输出。每次运行输出：

- `requested_backend` / `requested_update_strategy`；
- `executed_backend` / `executed_update_strategy`；
- `fallback_to_full` / `fallback_reason`；
- `propagation_scope`，避免把论文的 full GPU propagation 错报为 affected-cone。

请求 CUDA 而构建或设备不可用时，默认明确报错；只有显式 fallback policy 才能回退。benchmark 和 incremental correctness case 强制 `error`。

四种组合在每个 mutation batch 后的执行语义必须精确且互斥：

~~~text
cpu/full:
  apply semantic edit to a fresh/canonical full-run view
  -> native full graph rebuild
  -> full CPU levelization and propagation

cpu/incremental:
  targeted host Dual-CSR update
  -> CPU mixed levelization
  -> full CPU propagation

cuda/full:
  apply canonical edit
  -> full CSR re-export/rebuild
  -> full required H2D
  -> full GPU levelization and propagation

cuda/incremental:
  CPU normalize and descriptor generation
  -> targeted device Dual-CSR update
  -> CPU mixed topo + GPU level reconstruction
  -> full GPU propagation
~~~

`cuda/full` 每轮保留完整 CSR 重建、必要图数据 H2D、full levelization 和 full propagation，不能用增量图更新代替 full 语义。自阶段 11–12 起，full/incremental 同等复用不可变模型与分配容量，共用优化后的传播实现；不得保留低效 full 来制造增量收益。`cuda/incremental` 的 CPU Dual-CSR shadow 只作独立 ON oracle。普通样本保存实际模式和轻量分相计时、传输及分配事实；完整 phase trace/逐点证明属于 ON 或独立开发剖析，不嵌入正式性能采样。

若用户对无 mutation 的一次性 signoff 请求 incremental，系统只能完成 baseline full，必须记录：

~~~text
requested_update_strategy = incremental
executed_update_strategy = full
execution_kind = baseline_only
incremental_batch_executed = false
fallback_policy = "error"
fallback_to_full = false
fallback_reason = "not_applicable_no_mutation"
~~~

此类运行可产生正确 signoff artifacts，但不能生成或参与 incremental speedup。benchmark 必须至少包含一个非空、无 fallback 的 edit batch才可报告 incremental 性能。

### 5.3 建议新增模块

最终文件名和 owner 只是候选，必须由各阶段分析和 ECC review 确认。优先新建小模块，不继续膨胀 `chipcompiler/tools/ecc/module.py`、`runner.py`、`STAInterface.cpp`、`TimingPropagator.cpp` 或 `DelayCalculator.cpp`。

父仓库建议：

~~~text
chipcompiler/tools/ecc/sta_mode.py
chipcompiler/tools/ecc/incremental_sta_runner.py
test/tools/ecc/test_module_timing_modes.py
test/integration/test_incremental_sta_flow.py
~~~

`ecc-tools` 建议：

~~~text
src/operation/iSTA/source/data_manager/adapter/csr/
  TimingGraphCsr.*
  TimingGraphCsrAdapter.*
  TimingResultScatter.*

src/operation/iSTA/source/module/incremental_timing/
  IncrementalStaSession.*
  TimingGraphDelta.*
  PreparedBatch.*
  IncrementalStaCoordinator.*
  DualCsrUpdater.*
  MixedLevelizer.*
  CsrCpuReferenceBackend.*
  IncrementalGpuBackend.*       # 仅 CUDA target

src/operation/iSTA/benchmark/
  IncrementalStaBenchmark.*
  BenchmarkSchema.*
~~~

生产级物理 buffer mutation primitive 应在 iZH，而不是 iSTA：

~~~text
src/operation/iZH/source/module/greedy_buffer_inserter/
~~~

iZH 只负责创建 instance/net、重连 pin、合法化和明确的物理 apply/undo primitive。slack 排序、候选评分、STA session 循环和 trace orchestration 初期属于 benchmark/experimental timing-opt coordinator；阶段 13 根据真实集成再决定长期 owner。iSTA 只负责 timing graph/session。早期 synthetic harness 可直接构造 canonical timing deltas，但必须与 real-design workload 分开标记。

### 5.4 Session 生命周期

~~~text
create
  -> initialize_full_baseline
  -> export_csr_once
  -> [begin
      -> normalize + validate immutable edit
      -> stage canonical/CSR/device changes in shadow state or reversible log
      -> execute timing on staged view
      -> check required safety; full diagnostic proofs only ON
      -> atomically publish topology + authoritative timing results
      -> bump generation + commit
      -> materialize current-generation results when consumed] x N
  -> close
~~~

要求：

- stable dense `NodeId`/`ArcId`；新节点 append，首版不复用 ID；
- graph generation/fingerprint 防止旧结果写回已变化的 object graph；
- coordinator 独占 prepare→validate→stage→execute→verify→publish 状态机；iZH 不拥有 STA session，iSTA 不拥有物理优化策略；
- publish 前失败丢弃未发布结果并撤销实际修改，不改变 committed generation；生产使用修改范围的撤销记录、稳定所有权和可复用工作缓冲，不要求每批完整 Database/Liberty 克隆或设备图复制；
- publish 后若发生不可恢复异常，必须 poison/invalid session，并从最后 committed design 状态显式 full rebuild/reinitialize；该状态可由持久基线和必要编辑记录恢复，不要求每批完整快照，恢复前禁止继续增量运行；
- 阶段 0–10 的 semantic timing harness 中，isolated iSTA Database、host CSR 和 device CSR 的可见 topology/timing 在同一 publish 边界切换；此历史行为保持记录。阶段 11–12 改为原子发布当前 generation 的权威结果，native timing 按需物化；这些阶段均不修改生产 `EngineDB/IDB`，不得宣称完成物理 insertion；
- 同 generation 已物化字段可缓存；新提交使旧缓存失效，查询须绑定当前 generation 并避免混合读取。不得返回旧 native timing，也不得调用 CPU full 重算来代替目标 backend 的结果；
- session invalidation、capacity growth、unsupported edit 和 full fallback 都进入 telemetry；
- signoff 多 corner 不能错误共享 corner-specific timing arrays；是否共享只读 topology 必须单独证明后再做。

阶段 13 的 real-design 生产集成路径必须把事务扩展为：

~~~text
EngineDB/IDB topology
  + placement/legalization state
  + RC/parasitic state
  + iSTA Database
  + host/device CSR
~~~

上述层级必须统一 stage/publish，或为每层提供经过 ON fail-injection 验证的 reverse log；任一层失败时全部回滚，OFF 保留真实失败处理。publish 后不可恢复故障 poison 整个跨层 session，并从最后 committed design checkpoint 重建。没有完成这一门禁前，greedy 只生成/re放 semantic trace。

### 5.5 Clock、power、report 与 SDF 后处理契约

首版 incremental contract 只接受 data-net structural edits。clock net/clock constraint、library、corner 或 clock topology 变化必须按 policy error/full-with-record。data-only session 可复用 baseline clock state，但要用 clock/constraint/corner fingerprint 守卫；fingerprint 变化立即 invalidate，不能使用陈旧 clock state。

timing publish 不等于完整 ECC STA artifact 发布。调用现有查询/artifact surface 时，先按需回传并物化当前 generation 所需结果，再执行必要的 TimingAnalyzer、PowerPropagator/PowerAnalyzer、timing/power reporters 和 SDF writer；不得再次 CPU full propagation 掩盖目标 backend 的结果。允许只在最终 batch 生成 artifact，但不能复用或发布上一 batch 的 power/report/SDF。缺少某个必需 artifact 能力时应失败或明确未生成。

后处理规则：

- full/incremental correctness 都检查 clock fingerprint 和 artifact generation；
- power/timing report/SDF 至少有一个 ownership-local integration golden case；
- `postprocess_ms` 单列，不计入 `update_core_ms`；
- 消费者实际请求的查询/报告成本计入 `consumer_step_ms`；`artifact_step_ms` 延伸至全部所需 artifacts 原子发布，用于完整 flow 比较；
- benchmark 可以跳过非必需 report I/O，但 production safety checks 和 generation validation 不能关闭。

## 6. CSR 转换与增量数据结构

### 6.1 Adapter contract

`TimingGraphCsrAdapter` 至少提供：

~~~text
export_snapshot(Database) -> CsrSnapshot
decode_graph(CsrSnapshot) -> CanonicalGraphView
scatter_results(CsrTimingResults, Database, expected_generation)
validate_round_trip(Database, CsrSnapshot)
~~~

阶段 2 还必须提供 `CsrCpuReferenceBackend`：它从 CSR 自行执行 full levelization、full forward/backward propagation，再把新计算的结果 scatter 回原结构并与 native CPU/full 逐点比较。只导出 CSR 后原样写回 native 已有结果不算通过转换边界。

完整 CSR snapshot 至少包含：

- dense node/arc IDs 与 pin name/original arc index 反向映射；
- outgoing 和 incoming Base CSR；
- edge-aligned payload：`ArcId`、delay/type/disabled flags/active mask；
- level offsets、level node array、`node2level`；
- timing SoA：analysis type × transition × path/clock source 所需字段；
- start/end point、clock/data arc、loop-disabled 等现有语义；
- version、logical size、capacity 和 sentinel 定义。

export 只能读 Database；scatter 只能修改声明的 timing 结果字段。`Database → CSR → decode` 必须保留 parallel arcs，不能只用 `(src,dst)` 当 edge identity。

阶段 2 允许每轮完整转换以先建立正确性原型，但从 Dual-CSR 阶段开始，session 只能在初始化或明确 full rebuild 时完整 export。正常增量轮次只更新变化并发布权威 timing 结果，CPU 消费时才按需 scatter；不得每批完整转换或无消费者地构造全部 native 结果。

### 6.2 Dual-CSR

至少维护：

~~~text
BaseOut { row_offsets, dst, arc_id, payload, active/tombstone }
BaseIn  { row_offsets, src, arc_id, payload, active/tombstone }
AuxOut  { row_offsets, dst, arc_id, payload, source_to_aux_row }
LevelCsr { level_offsets, level_nodes, node_to_level }
~~~

论文对 reverse auxiliary 语义不清。首版采用可验证的窄 contract：

- buffer insertion 所造成的 existing destination fan-in 必须是一删一增，可在 `BaseIn` 原 slot 替换；
- existing source 的剩余新增 outgoing edges 进入 `AuxOut`；
- 不平衡 reverse fan-in、任意 old→old 或其他超界 edit 明确 error/full fallback；
- 若真实 workload 证明需要 general reverse overflow，再新增独立 `AuxIn`，不能把正反 edge 混入一个 CSR。

每个声称受支持的 buffer insertion batch 都必须在 prepare 阶段证明 reverse edit 可一删一增复用 `BaseIn` slot；不能证明时立即按 policy error 或 full-with-record。首版成果应准确称为“论文 buffer-insertion workload 的兼容子集”，不得宣称支持任意 Algorithms 1–4 edit。

不变量：

- Base CSR 满足 `row_offsets.size() == V + 1`；Aux CSR 按 aux-row 数检查 offsets。两者 offsets 均首项 0、单调、末项等于各自 physical edge-array size；
- active logical edge 只存在于 Base 或 Aux 一次；
- decoded outgoing 与 incoming 是严格转置，`ArcId` 和 payload 一致；
- `source_to_aux_row == -1` 当且仅当 source 没有 Aux row；
- tombstone、slot replacement 和 descriptor 不发生冲突写；
- capacity 不足有显式 grow/rebuild 行为及 telemetry；
- batch commit 后 pending buffers 清空，持久 Aux edge 不丢失。

### 6.3 三层 edit contract 与跨 session identity

真实 buffer insertion 不能只表示为 `AddNode/InsertArc`。必须分成三层：

~~~text
DesignEditPlan
  BufferInsertionMutation {
    original_net, moved_sinks, library_cell,
    placement_inputs, rc_inputs
  }

  -> validated semantic expansion

TimingGraphDelta {
  AddInstance, AddTimingPoint, AddCellArc, AddNetArc,
  RemoveNetArc, ReconnectSink,
  InvalidateLoad, InvalidateParasitic, InvalidateArcDelay
}

  -> normalize + resolve session IDs

PreparedBatch {
  host slot changes, append ranges, reverse changes,
  device descriptors, expected generations
}
~~~

`DesignEditPlan` 由 experimental coordinator 拥有，iZH 提供物理 mutation/undo primitive；`TimingGraphDelta` 和 `PreparedBatch` 由 iSTA coordinator 拥有。阶段 3 必须交付 native graph mutator/translator，不能只交 JSON trace。

跨模式 fixed trace 保存 semantic key，而不是 dense ID：instance/pin/net 名、arc kind/library identity、parallel ordinal，以及新对象 creation token。每个 fresh session 将 semantic key 解析为本 session 的 dense `NodeId/ArcId`；baseline fingerprint 不匹配时拒绝 replay。dense ID 只承诺在单 session 内稳定。

normalize/prepare 必须：

- 记录 batch-start `n_last_nodes`，新 dense ID 只 append；
- normalize duplicate、insert→remove、remove→insert 和 invalidation；
- 校验 endpoint、parallel arc identity、DAG/cycle、reverse one-for-one 和支持范围；
- 同时生成 forward/reverse edits及电气量 invalidation；
- 保留 immutable、版本化的编辑/恢复记录及 seed、semantic keys；必要输入身份复用已验证绑定，诊断用 pre/post 全图摘要仅 ON，不为每批记录重新扫描全图；
- 支持 shadow/reversible staging、publish 前实际撤销和 ON fail injection；
- synthetic trace 可携带固定 delay，但必须标记 `semantic_workload_kind=synthetic`；
- real-design trace 记录 library/RC 输入和 topology edit，各模式必须自行重算 delay/slew/load，不得重放预制 timing 答案。

## 7. Greedy buffer insertion 驱动

由于 ECC 没有 general iSTA 的活跃迭代 consumer，阶段 4 必须实现一个确定性 greedy buffer insertion fixed-trace harness，并在阶段 13 接入实验 `TIMING_OPT` 并增加 closed-loop。

### 7.1 论文可复现部分

- 按 slack 排序 critical nets；
- 选择 top-k；
- 评估 pin `p` 前的候选位置；
- 使用论文的 Elmore gain 形式：

~~~text
Gain = Rupstream,p * (Cload,p - Cbuf)
       - Rbuf * Cbuf
       - delaybuf
~~~

- 批量插入并重新计算受影响 net delay；
- 提供 top-1000×1、top-100×10 和 buffer-count sweep profile。

论文未给候选生成、buffer library 参数、正 gain 接受规则、tie-break、legalization、随机种子和完整 RC 定义。ECC 实现必须把这些标注为“工程定义”，写入配置和 trace，不能伪称来自论文。建议固定 tie-break 为 stable net/pin/buffer ID，并只接受明确正 gain；最终规则须由该阶段设计审查确认。

### 7.2 两类 workload

- **Fixed trace**：由 CPU full/reference 生成 edit trace，四模式从相同 baseline 重放。用于公平 correctness 和性能比较。
- **Closed loop greedy**：每轮由本模式 timing 重新选择 critical nets。用于最终优化效果；浮点 tie 可能使后续 edit 分叉，结果必须与 fixed-trace 分开报告。

微型 mutation tests 不依赖 greedy；greedy 集成也不能替代逐节点 STA oracle。

## 8. Correctness harness

### 8.1 测试落点

原生测试：

~~~text
chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/test/incremental/
  TimingCsrRoundTripTest.cpp
  TimingGraphDeltaTest.cpp
  PreparedBatchTest.cpp
  DualCsrUpdaterTest.cpp
  MixedLevelizerTest.cpp
  IncrementalStaOracleTest.cpp
  IncrementalStaPropertyTest.cpp
~~~

使用 CTest labels：`ista_unit`、`ista_property`、`ista_integration`、`ista_gpu`。当前 iSTA 只有一个自带 `main()` 的 CTest；可先沿用现有轻量方式，除非阶段分析证明复用仓库 GTest 更合适。不要仅为此引入新 test framework。

Python/API：

- `test/tools/ecc/test_module_timing_modes.py`：配置解析、typed forwarding、非法组合、requested/executed mode、fallback 和无 GPU 契约；
- `test/integration/test_incremental_sta_flow.py`：真实设计/PDK/greedy loop，标记 `integration,pdk,slow`。

性能 executable：

- `chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/benchmark/ista_incremental_benchmark`；
- dataset 通过 `--manifest` 或明确 CLI/env 传入；禁止 fixture 内硬编码本机绝对路径。

### 8.2 四模式 oracle 流程

以下完整 oracle/比较只用于 ON 开发验收；独立 OFF/ON 等价测试从测试入口读取真实结果。普通性能入口不执行这些步骤。每个 correctness case：

1. 固化一个 design snapshot、semantic trace 和 baseline fingerprint；
2. 四模式分别从该 snapshot 启动 fresh session，必要时使用独立进程隔离全局 singleton；在证明安全前不得假设 `DataManager` 或含内部指针的 `Database` 可深拷贝；
3. 每个 session 将 semantic keys 解析为自己的 dense IDs，并重放相同累计 edits；
4. 每个 batch 的 CPU/full oracle 从 fresh init 重放截至该 batch 的累计 edits；只有 reset/rebuild API 已通过重复性测试后才可复用进程；
5. CPU incremental、GPU full、GPU incremental 分别运行，不能继承另一模式的 native/device state；
6. 每轮立即比较，不只比较最终 WNS/TNS；
7. incremental-path 专项 case 要求 `fallback_to_full == false`；
8. 开发验收用实际 phase trace 核对第 5.2 节模式语义，普通样本只保留实际执行记录和轻量遥测。

比较项：

- 所有 timing point 的 arrival、required、slack、data slew；
- min/max、rise/fall、path-source/clock-source 等实际维度；
- arc delay/graph delay；
- WNS、TNS、violation count、path-group summary；
- predecessor pin/arc；相等路径需固定 tie-break 或验证等价代价；
- node/arc count、stable ID mapping、canonical graph hash；
- NaN、遗漏节点、shape mismatch 和意外 infinity 一律失败。

CPU double 路径先使用可解释的严格 tolerance；GPU tolerance 必须按 dtype、单位和 operation order 通过实验校准后固化，并在每份结果中记录。不得用宽泛百分比掩盖错误。

### 8.3 CSR/level 不变量

- Base `row_offsets.size() == V + 1`；Aux offsets 长度按 aux-row contract 检查；
- outgoing 等于 canonical outgoing，incoming 为严格转置；
- parallel arcs、disabled/loop-disabled/clock flags 不丢失；
- export-only 不修改 Database；
- no-op round-trip canonical snapshot 相等；
- scatter 只改 timing fields；
- level array 包含每个 active node 恰好一次；
- `node2level` 与 level array 互逆；
- 定义唯一 `LevelizationEdgeView`/eligibility predicate，与 `GraphBuilder::isDisableArc` 等实际传播语义一致；所有 CPU/GPU levelizer 和测试共享它；
- 每条 eligible levelization edge 满足 `level(u) < level(v)`，disabled、loop-broken 或 non-propagating arc 不被误判；
- mixed topo processed count 等于 mixed vertex count；
- 每个 reconstructed level 的 virtual-node 约束被显式检查。

### 8.4 图与 mutation 覆盖

- chain、diamond、reconvergent、parallel arcs、high fanout；
- disconnected components、多 start/end、clock/data 混合；
- old→new、new→old、new→new、超界 old→old；
- Base removal、slot replacement、tombstone reuse、Aux overflow 和 Aux 清空；
- insert→remove、duplicate edits、delay-only、empty batch；
- cycle injection、capacity exhaustion、fail injection/rollback；
- 固定 seed 随机 DAG 和可重放失败 trace；
- affected fraction 扫描 0.01%、0.1%、1%、5%、10%、25%、50%、100%。

Metamorphic tests：

- empty edit 不改变任何结果；
- insert 后 remove 恢复 graph/timing；
- normalize 后等价 batch permutation 得到相同结果；
- CPU/GPU 从同一 snapshot 得到等价结果；
- unsupported edit 不得留下部分 mutation。

## 9. 性能统计框架

### 9.1 机器可读 schema

原始样本写 `incremental_sta_samples.json`，汇总写 `incremental_sta_summary.json` 和扁平 CSV。至少包含：

~~~text
schema_version
run_metadata:
  parent_sha, ecc_tools_sha, dirty, build_type, compiler, flags
  debug_checks_enabled
  cpu_model, omp_threads, actual_cpu_threads
  cuda_runtime, driver, gpu_name, compute_capability
  seed, timestamp, dataset_manifest_hash
case:
  design, corner, vertices, arcs, levels
  mutation_kind, batch_size, changed_nodes, changed_arcs
  affected_fraction, buffers_inserted
  trace_hash, baseline_graph_hash, consumer_requirements
  semantic_workload_kind, comparability_status
mode:
  requested_backend, requested_update_strategy, fallback_policy
  executed_backend, executed_update_strategy
  execution_kind, propagation_scope
  incremental_batch_executed
  fallback_to_full, fallback_reason
batch_sample:
  cold_or_warm, warmup, repetition
  setup_ms, csr_export_ms, mutation_normalize_ms
  cpu_csr_update_ms, descriptor_h2d_ms, gpu_csr_kernel_ms
  base_append_ms, aux_rebuild_ms
  mixed_graph_ms, mixed_toposort_ms
  level_d2d_ms, level_h2d_ms, node2level_ms
  delay_ms, forward_ms, backward_ms, result_d2h_ms
  scatter_back_ms
  verify_safety_ms, update_core_ms, session_step_ms
  query_materialization_ms, consumer_step_ms
  postprocess_ms, artifact_step_ms
  h2d_bytes, d2h_bytes, d2d_bytes, kernel_launches
  allocation_count, capacity_fallback
run_aggregate:
  process_setup_ms, cuda_context_ms, baseline_build_ms
  all_batches_ms, close_ms, cold_end_to_end_ms
correctness:
  comparison  # not_run in ordinary OFF performance samples
  pass, mismatch_count, max_abs_error, max_rel_error  # null when not_run
  wns_delta, tns_delta, tolerance  # null when not_run
diagnostics:
  status  # not_run when diagnostic collection is absent
  visited_vertices, processed_arcs, tombstone_ratio, aux_edges  # null when not_run
summary:
  n, min, median, p95, max, mad, mean, stddev
  speedup_vs_cpu_full, speedup_vs_cpu_incremental, speedup_vs_gpu_full
  speedup_ci95_lower, speedup_ci95_upper
~~~

普通性能输出 `debug_checks_enabled=false`；正确性比较和详细诊断均为 `not_run`，相关值为空，不能填固定成功值。访问或结构字段只因诊断才可取得时，不得为填 schema 在 OFF 增加扫描；必要输入身份复用已验证绑定，不为每批遥测重新计算全图摘要。复用现有输出入口，字段迁移显式升级 schema 并同步仓内消费者，不新增通用统计框架。

### 9.2 测量规则

- CPU wall time 用 `std::chrono::steady_clock`；
- async copy/kernel 用同一 stream 上 CUDA events；
- end-to-end timer 结束前确认必需设备工作和结果传输完成；利用正确的 stream/event 依赖，不为计时重复插入 host 同步；
- H2D、kernel、D2H、scatter 与 total 分开；
- CUDA context、初次分配和 CSR build 单列 cold/setup；稳态实际发生的分配/扩容仍计入该批次，不能移出计时来制造收益；
- 必需的 generation/hash、descriptor bounds、事务 publish 前安全检查计入 `verify_safety_ms` 和 `session_step_ms`；
- differential oracle、debug decode 和逐点比较仅在独立开发验收运行；正式性能进程不启动 oracle；JSON/日志输出不计 core，消费者实际需要的 report I/O 必须计入相应端到端口径；
- 正式 benchmark 只接受 debug checks OFF，ON 在采样前拒绝；必要生产检查始终执行；
- 四模式交错/轮转采样，记录硬件、线程、编译 flags；
- 保留所有 raw repetitions，不只保留均值；
- root `Monitor` 和 step-level `runtime_seconds` 粒度不足，不作为 kernel benchmark 数据源；
- 独立 run dir，避免 `DataManager::buildConfig()` 清理 STA temp dir 导致样本互相覆盖。

计时边界区分提交与实际消费；对同一结果需求使用相同边界比较，禁止混比：

~~~text
update_core_ms:
  immutable PreparedBatch 已加载后，到该 backend 必需的 graph update、
  levelization、propagation 和结果可用；
  full 模式包含完整图重建和必要传输，允许复用不可变模型与容量。

session_step_ms:
  公共 begin_batch API 到权威结果 publish/commit；
  包含 normalize、adapter、提交必需传输和生产安全检查。

query_materialization_ms:
  该批消费者请求所需的 D2H、解包和 native scatter/物化耗时；
  同 generation 命中缓存也如实记录，不漏计首次物化。

consumer_step_ms:
  该批编辑开始到消费者取得该轮声明需要的全部结果；
  包含编辑准备、session_step_ms、必要查询物化及消费者请求的分析/后处理；
  是阶段 12、14 的主要加速验收口径。

artifact_step_ms:
  同一批请求开始到全部所需当前 generation artifacts 原子发布；
  包含提交、必要物化及 clock/power/analyzer/report/SDF 后处理。

cold_end_to_end_ms:
  run-level aggregate；包含 process/session 初始化、CUDA context、
  baseline CSR、全部 batches 和 close，不写入单个 batch sample。
~~~

speedup 必须明确同名字段（`update_core_ms`、`session_step_ms`、`consumer_step_ms`、`artifact_step_ms` 或 run-level `cold_end_to_end_ms`），使用相同输入/trace、结果需求、dtype、构建优化设置和固定硬件配置；各模式采用合理生产线程配置并记录实际线程数。禁止用 kernel 时间除以 CPU end-to-end，也不能把回传/物化推迟到计时后。greedy selection、必要查询和产物成本按真实消费口径计入，core 分解另列；oracle 不进入性能进程。

提供三个 profile：

1. **paper-protocol profile**：只复现 top-1000×1、top-100×10、每项 3 次 mean 和 buffer-count sweep 的协议形状，不声称复现论文原数字；
2. **exact-paper profile**：只有取得原始 dataset/library/trace 并记录 hash 后才能启用；
3. **engineering profile**：默认 warmup 5、repeat 30；主报 median/p95/MAD、配对加速比及 95% 置信区间，并保留 cold/warm。验收配置及配对统计方法在优化前冻结；更短 smoke 不替代工程性能门。

每份输出写 `comparability_status = exact | protocol_only | non_comparable`。

buffer-count sweep 至少覆盖 1、10、100、1K、10K、100K；同时报告真实 changed-node/edge 和 affected fraction。优化前冻结代表性规模、trace、消费者结果需求和必过用例，不得看结果后挑样本。阶段 12、14 的必过用例分别要求 CUDA/full 相对 native CPU/full、CUDA/incremental 相对优化后的 CUDA/full 的 `consumer_step_ms` 配对加速比 95% 置信区间下界大于 1。记录所有负结果、交叉点和资源受限点，不要求每个小设计或所有规模更快；未满足指定性能门不得标记高性能完成。回归比较只在相同硬件指纹和稳定 runner 上进行；普通 PR 不以绝对时延失败。

### 9.3 论文数值只作背景

论文参考环境是 Ubuntu 18.04、GCC 9.3、CUDA 11.5、双 Xeon Gold 6230、RTX 2080 Ti、503 GB DDR4，并使用 Thrust、Taskflow 和 TAU15-derived workloads。论文每项运行 3 次取 mean；其报告的 GPU incremental 相对 GPU full 平均 speedup 为单轮 1.78×、十轮 2.20×，最高分别为 2.55×、3.06×；这些不是本项目 pass/fail threshold。

论文没有提供 TAU15 派生数据、随机 netlist/library 参数或 seed。硬件、数据或 workload 不一致时，数值差异不能判为实现失败；只能在 `comparability_status` 和限制说明中陈述。

## 10. 分阶段路线图

每个阶段都要套用第 2.3 节闭环；下面的“先分析”是该阶段必须回答的专属问题。

### 阶段 0：冻结 baseline、语义与可执行门禁

**先分析**

- 当前 pinned parent/submodule SHA、编译方式和可用测试；
- `Database`/`TimingPoint` 的单位、sentinel、min/max、rise/fall、clock/path-source 语义；
- 现有 full STA 的确定性和报告产物；
- `DataManager` singleton、`Database` 内部指针、`GraphBuilder::build()` 重复调用是否追加/泄漏状态，以及安全 reset/rebuild 的可能性；
- Clock/Power Propagator、Timing/Power Analyzer、Reporter、SDFWriter 和 `publish_sta_artifacts()` 的 generation/必需 artifact 契约；
- 当前 CI 为什么未运行 native iSTA CTest。

**交付**

- baseline manifest、CPU full golden cases；完整 snapshot 和可解码 artifact 采用逐字段/容差比较，输入内容只在 fresh-process 身份绑定处计算摘要，只有不可语义解码的 binary artifact 保留内容 SHA；
- 实验目录/JSON schema v1；
- CTest label scaffold 和一条 CPU smoke；
- feature support matrix，列明首版/后续/不支持 edit。

**正确性门**

- 当前 full STA 回归全绿；
- baseline 重跑结果在已定义规则下稳定；
- fresh-process 重复 full run 不产生重复 arc、adjacency 追加或跨 run 状态泄漏；若复用式 reset 尚不安全，oracle 明确采用 fresh process/session；
- parent 和 submodule 均有明确 branch/commit 记录。

**阶段报告重点**

记录环境、golden artifact、未覆盖 timing 维度和 native CI 缺口。本阶段不改变 STA 行为。

### 阶段 1：Typed mode、session 接口与默认兼容

**先分析**

- `sta.max_paths` 的 schema/CLI/data flow；
- `run_timing()`、`run_sta()`、Python binding 和 `STAInterface` 生命周期；
- 是否拆出新的 runner/module，避免大文件继续增长。

**交付**

- typed backend/update/fallback contract；
- `IncrementalStaSession` 空壳和 RAII/context-manager 生命周期；
- CPU/full 接通现有实现；
- 其余组合返回清晰 `unsupported`，无 silent fallback；
- requested/executed telemetry。

**正确性门**

- 默认配置与改前产物一致；
- 四组合配置可解析，尚未实现的组合按契约失败；
- 无 mutation 的 incremental 请求记录 `baseline_only`，不误报 incremental 执行或 speedup；
- init/close、异常清理、多 corner 隔离测试通过。

**阶段报告重点**

列出配置/API 兼容性和尚未实现模式，不得声称已有增量能力。

### 阶段 2：Native ↔ CSR 转换模块

**先分析**

- Database 中 node/arc/adjacency/timing-order 的真正 owner；
- parallel/disabled/loop/clock arc 和 timing state 的编码；
- scatter 回写最小字段集及 lifetime。

**交付**

- outgoing/incoming/level CSR 和 stable ID maps；
- full export、decode、result scatter；
- graph generation/fingerprint；
- `CsrCpuReferenceBackend`：在 CSR 上自行 full levelize、full forward/backward propagation，再 scatter；
- round-trip validator 和 property tests。

**正确性门**

- fixed 和 randomized DAG 全部 CSR invariants 通过；
- native→CSR→decode graph 精确相等；
- no-op scatter 不改变未声明字段；
- CSR full reference 新计算并 scatter 后，与 native CPU/full 逐点 timing 等价。

**阶段报告重点**

报告内存开销、转换时间、ID 规则和仍未进入 CSR 的语义字段。

### 阶段 3：三层 edit contract、事务 coordinator 与 full-recompute oracle

**先分析**

- iZH 的 Instance/Pin/Net/IDB edit 如何展开为 iSTA timing point、cell/net arc、load/parasitic/delay invalidation；
- `DesignEditPlan → TimingGraphDelta → PreparedBatch` 的 owners 和 semantic-key 解析；
- shadow/undo、publish point、poison/rebuild、cycle policy、ID append 和 graph generation；
- canonical Database、host CSR 和 device CSR 的 staged/published 状态边界。

**交付**

- native graph mutator/translator 和三层 typed contract；
- coordinator 的 prepare/validate/stage/execute/verify/publish 状态机；
- versioned JSON trace 和 deterministic DAG/mutation generator；
- semantic-key→session-ID resolver、baseline fingerprint；
- 对每 batch 从 fresh session 重放累计 edits 的 CPU/full reference path；
- 四模式 harness 骨架使用相同 design snapshot/trace，各模式状态隔离。

**正确性门**

- 所有 edit 原语与 edge-case tests 通过；
- real-design expansion 覆盖 instance、timing point、cell/net arc 和电气 invalidation；
- 每次 mutation 后 canonical graph/电气量与 fresh rebuild oracle 一致；
- publish 前 fail injection 不留下半更新；publish 后故障会 poison session 并可从 committed snapshot 恢复；
- failure seed/trace 可一条命令重放。

**阶段报告重点**

报告三层 ownership、事务恢复策略、semantic identity、支持与 fallback edit 集、trace schema 和 graph hash。

### 阶段 4：确定性 buffer insertion trace generator/replayer

**先分析**

- iZH `FanoutFixer` 可复用的物理 mutation primitive 与不能复用的 policy；
- 论文未说明的候选生成、positive-gain、tie-break、library/RC 和 legality 规则；
- synthetic fixed-delay trace 与 real-design semantic trace 的隔离；
- fresh CPU/full session 生成和重放累计 edits 的成本。

**交付**

- deterministic greedy candidate selector 和 fixed-trace generator；
- synthetic micro traces 与至少一个小 real-design semantic trace；
- trace manifest/hash、stable creation tokens 和 replayer；
- real-design snapshot 只用于生成语义 edit，并在 isolated iSTA staged view 中重放；本阶段不提交 `EngineDB/IDB`、placement 或 RC 物理变更；
- 此阶段只使用 CPU/full 与 CSR full reference，不实现 closed-loop 多模式优化。

**正确性门**

- trace 在多个 fresh session 中解析为等价 canonical edits；
- real-design trace 由各 run 自行重算 delay/slew/load，不携带预制答案；
- 每轮 CPU/full 与 CSR full reference 的 topology、电气量和 timing 等价；
- 测试断言阶段 4 不修改源 `EngineDB/IDB` 或物理 checkpoint；
- reverse edit 的一删一增 contract 被逐 batch 证明，超界 edit 按 policy 处理。

**阶段报告重点**

区分论文给定规则与 ECC 工程定义；冻结供阶段 5–9 共用的 fixed traces，并报告 nets、buffers、semantic edits、hash 和可比性状态。

### 阶段 5：CPU Dual-CSR 增量图更新

**先分析**

- Algorithms 1–4 的歧义和首版窄 contract；
- Base capacity、tombstone、Aux row、正反 graph owner；
- descriptor 冲突、pending buffer 清理和 rollback。

**交付**

- CPU `DualCsrUpdater`；
- remove/change/reverse-change/append descriptors；
- Base/Aux decoded view 与 invariants；
- frozen fixed traces 上做 targeted CSR update；full CPU levelization + full CPU propagation 暂时保持，以隔离图更新。

**正确性门**

- 每 batch 后 Base∪Aux 等于 canonical graph；
- outgoing/incoming 严格一致；
- tombstone reuse、Aux overflow/clear、multiple batches、capacity grow 通过；
- targeted CPU CSR update 后立即运行 full CPU levelization/propagation，每 batch 所有 timing fields 与 fresh CPU/full 等价；
- Stage 4 frozen buffer traces 验证 targeted Base update；独立 Stage 5-only add-only storage microcase 必须真实产生 Aux overflow/clear，并证明 levelizer/propagator 直接遍历 `Base ∪ Aux`，不能只验证 decoded graph。该 microcase 仅验证 Algorithms 1–4 存储路径，不得冒充 production buffer trace；
- 论文疑似笔误对应的命名回归全部通过。

**阶段报告重点**

报告 physical/logical edge count、tombstone ratio、Aux size、fallback 和重建次数。

### 阶段 6：CPU mixed incremental levelization reference

**先分析**

- Algorithms 5–7 的 actual/mixed ID 和 virtual-level 语义；
- old→old、edge removal、非最紧凑但合法 level 的处理；
- `LevelizationEdgeView` 与 native disabled/loop-broken/non-propagating arc 语义；
- 阶段 4 frozen traces 是否完整覆盖 old↔new/new↔new。

**交付**

- CPU mixed graph builder、corrected Kahn levelizer、CPU reconstruction oracle；
- `cpu/incremental` 使用 targeted Dual-CSR + CPU mixed levelization + full CPU propagation；
- 与阶段 2 CSR full reference、native CPU/full 的逐 batch differential harness；
- paper-core CPU profile，禁止混入 affected-cone propagation。

**正确性门**

- level permutation、inverse map、所有 eligible edge level inequality 通过；
- cycle 和 processed-count 错误明确失败；
- 阶段 4 fixed traces 真实触发 Dual-CSR 和 mixed path；
- 每轮 timing 与 CPU/full 等价，无 incremental-case fallback。

**阶段报告重点**

报告每轮 mixed graph 大小、old/new levels、合法但非最紧凑 level、full-vs-incremental levelization 时间和 fallback；此阶段完成 CPU 上与论文 GPU 路径同构的 reference。

### 阶段 7：可选 CUDA 构建与 GPU full baseline

状态：已验收；见 [详细计划](incregpusta/stage7-detailed-plan.md) 和 [实施报告](incregpusta/stage7-progress-report.md)。当前为串行 GPU 正确性基线，不声明加速。

**先分析**

- ecc-tools 当前 CMake/C++20/OpenMP 结构和 wheel 构建；
- CUDA toolkit/architecture/runtime 检测、stream/error policy；
- timing dtype、operation order、CPU/GPU tolerance；
- GPU CI runner 与 artifact 存储。

**交付**

- `ISTA_ENABLE_CUDA=OFF` 默认的独立 optional target；
- CUDA 未启用不影响 CPU build/package；
- CUDA 明确启用但 toolkit/device 不可用时清晰失败；
- `cuda/full` 在每个 frozen-trace batch 后完整重建/导出 CSR、完整 H2D、full GPU levelization/propagation；
- CUDA event + synchronized end-to-end telemetry。

**正确性门**

- CPU-only build/test 不回归；
- GPU full 在真实 GPU 上与 CPU full 逐点等价；
- phase trace 证明每轮确实执行 full CSR rebuild/copy，未复用 incremental device state；
- active-set=all、多个 graph shape、cold/warm 均验证；
- compute-sanitizer 或该环境等价内存检查纳入手动/nightly。

**阶段报告重点**

记录完整硬件/驱动/toolkit/build flags，不把 compile-only 当 GPU 验证。

### 阶段 8：GPU targeted Dual-CSR 更新

状态：2026-09-09 已完成独立审查、ON/OFF 真实 GPU 与生产 trace 验收；见 [详细计划](incregpusta/stage8-detailed-plan.md) 和 [实施与验收报告](incregpusta/stage8-progress-report.md)。生产策略为 targeted-full-levelization；通用 cuda/incremental 留在 Stage 9。初始化的两次 export/pack、每批零全量 host 调用及实际传输/分配成本已单独记录。

**先分析**

- descriptor layout、coalescing、slot conflict；
- offsets/mapping/payload/capacity metadata 的同步；
- append/aux buffer ownership、stream 和 error ordering；
- CPU descriptor generation 与 CPU Dual-CSR correctness shadow 的计时隔离。

**交付**

- remove/change/reverse-change kernels；
- Base append、Aux/offset/mapping/metadata copy；
- device CSR debug decode/hash；
- 生产被测路径只在 CPU normalize/generate descriptors 后更新 device；CPU Dual-CSR shadow 在独立 oracle run 或 timed region 外执行；
- 此阶段仍用 full GPU levelization/propagation，隔离 CSR update。

**正确性门**

- 每 batch device decoded graph 等于 CPU Dual-CSR/canonical graph；
- zero/small/overflow/capacity/failure cases 通过；
- targeted device update 后立即运行 full GPU levelization/propagation，每 batch 与 `cuda/full` 和 fresh `cpu/full` 的所有 timing fields 等价；
- 至少一个真实 Aux overflow trace 断言 GPU levelizer/propagator 读取 `Base ∪ Aux`；
- H2D/D2H/D2D bytes 与实际变化一致；
- CUDA error/sync/rollback 不留下可继续使用的坏 session。

**阶段报告重点**

报告 kernel launch、传输字节、allocation、capacity fallback 和 device validation 方法。

### 阶段 9：Hybrid incremental levelization 与端到端 GPU incremental

状态：2026-09-09 已完成 canonical CPU mixed → GPU reconstruction → full GPU propagation → 原子 native/device publish。独立设计/代码审查、CUDA ON/OFF 与默认无 CUDA 回归、fixed trace 双 full oracle、硬件故障/恢复、sanitizer、真实调用/分配/子进程剖析通过；全仓类型失败另行如实记录。见 [详细计划](incregpusta/stage9-detailed-plan.md) 和 [实施与验收报告](incregpusta/stage9-progress-report.md)。通用未编辑 session 为 baseline_only/full，physical/greedy 集成仍属 Stage 13。

**先分析**

- CPU mixed topo 输出到 GPU level storage 的 ownership；
- D2D overlap、H2D batching/order、offset publish 和 `node2level` rebuild；
- propagation 前的 stream synchronization；
- GPU full 与 incremental 的相同 trace 比较方法。

**交付**

- old level D2D、新 node batched H2D、`node2level` kernel；
- `cuda/incremental` 端到端：

~~~text
PreparedBatch
 -> CPU descriptor generation + targeted device Dual-CSR update
 -> CPU mixed graph/toposort
 -> GPU level reconstruction
 -> full GPU forward/backward propagation
 -> verify + native result publish
~~~

- requested/executed/fallback/propagation-scope 完整 telemetry。

**正确性门**

- level invariants 和 CPU reconstruction oracle 全过；
- 每个 fixed-trace batch 与 CPU/full、GPU/full 逐点等价；
- 所有目标 incremental cases `fallback_to_full == false`；
- phase trace 证明没有在 timed GPU path 中重复执行 CPU Dual-CSR shadow；
- 真实 GPU correctness suite 和 fixed-trace buffer insertion flow 通过。

**阶段报告重点**

明确 propagation 是全图；分别报告 update、levelization、propagation、scatter 和 total。

### 阶段 10：补齐功能与真实设计验证

状态：2026-09-15 实现与功能验收完成；2026-09-16 已提交（ecc-tools 6921b6089）。六类语义在既有 ideal-clock contract 下接通；xtea、usb、zipdiv 完成四模式 baseline、真实 Q/D 两批编辑、独立 fresh native 对照、OFF/ON 等价及恢复后继续提交。范围与未通过的 lint/type 检查见 [Stage 10 报告](incregpusta/stage10-progress-report.md)，实施方案见 [详细计划](incregpusta/stage10-detailed-plan.md)。[2026-09-14 CUDA CI 报告](incregpusta/cuda-ci-validation-20260914.md) 保留为实施前支持缺口的历史证据。

**先分析**

- 逐项分析六类语义：顺序实例（`sequential_instance`）、顺序发射（`sequential_launch`）、时序检查（`timing_check`）、CRPR（`crpr`）、时钟树扇出（`clock_tree_fanout`）、条件时序弧（`conditional_timing_arc`）；
- 以 native CPU STA 为语义依据，追踪共享 CSR 表达、CPU reference/incremental 和 CUDA 路径中的导出、计算、结果发布及必要失效处理，不能仅移除 CUDA 入口的拒绝；
- 明确 baseline clock state 与 data-only edits 的依赖、更新和失效边界；本阶段不扩展为完整 native CPU STA 能力对齐，physical/greedy 集成与跨层事务属于阶段 13；阶段 11–12 先完成默认路径、存储/事务和并行计算；正式性能评估和结论属于阶段 14。

**交付**

- 补齐六类语义所需的共享 CSR、CPU reference/incremental 与 CUDA 能力，沿用现有模式接口、默认 CPU/full 和默认 OFF 的 `ECC_INCREGPUSTA_DEBUG_CHECKS`；
- 仅在实现及针对性验证完成后解除对应 unsupported 拒绝；保留范围外能力的明确拒绝，以及必要输入、生命周期、数值、cycle、回滚与恢复检查；
- 为 xtea、usb、zipdiv 准备相同输入下的四模式验证及真实、多批次 data-only buffer insertion frozen trace；编辑提交在 isolated iSTA Database 与 host/device CSR 内完成，不宣称生产 EngineDB/IDB 物理 insertion；
- 完整 oracle 和逐字段诊断比较限于开发验收，生产路径内的重型诊断仅 ON 执行；普通性能入口保持 OFF、不启动 oracle，ON 构建在采样前明确拒绝。

**正确性门**

- 保留三个设计的原综合网表、约束和 ICS55 配置，使用 post-synthesis、无 SPEF 输入；不得删除寄存器、修改约束、关闭必要检查或抽取组合子电路来绕过限制；
- 使用相同依赖、GCC/CUDA 和 Release 优化设置的独立 OFF/ON 构建；隔离 native binding，并核对实际加载路径及只读构建状态。每个设计分别验证 CPU/full、CPU/incremental、CUDA/full、CUDA/incremental；
- 未编辑初始化单独记录为 baseline/baseline_only，不计为增量批次；每个设计必须完成多批次 frozen trace，目标 incremental 路径实际执行 incremental，不得静默退回 full；
- 每批与独立 fresh native CPU/full 比较拓扑、timing、winner 和适用的时序检查结果，同时验证公开 QOR、timing paths、level 合法性及 requested/executed mode、fallback；level 合法性不要求不同合法层次划分逐字段相同；
- 六类语义的针对性测试、失败回滚、恢复后继续提交和 CUDA 内存检查通过；独立开发验收比较 OFF/ON 的功能结果，排除计时、诊断字段与 session 实例身份，完整比较不加入普通性能运行。

**阶段报告重点**

记录六类能力的支持矩阵、三设计四模式结果、实际增量证据、失败与修复及剩余限制。分别标明“通过”“不支持”“失败”“未执行”，不得将正确拒绝或 baseline 成功计为增量验收通过；未取得的等价性或性能证据如实列出。

### 阶段 11：生产路径精简、持久存储与增量事务

状态：尚未实施；以 Stage 10 完成及内存清理后的 ecc `dbb1c8e`、ecc-tools `fec270b8a` 为基线。仅改变既有语义的执行与存储方式，不扩展 STA 支持范围。

**先分析**

- 沿 Stage 0–10 的调用者和消费者分类：无用/同源重复功能删除，独立诊断仅 ON，必要功能保留并改进实现；不能按函数名批量关闭；
- 跟踪 snapshot/observation、before-state、恢复历史、Liberty/模型、图/结果缓冲及 native 查询的所有权、生命周期和复制；
- 区分事务安全语义与当前采用的整库/整图复制，设计真实回滚、poison、恢复及按需结果发布，不增加通用策略/事务框架。

**交付**

- 删除无消费者对象、重复状态、失效接口、同源重复证明及其专用测试；ON 也不保留无独立验证价值的功能；
- 完整 observation、诊断快照/摘要、oracle、验证性重建/传播、逐字段比较、详细访问审计与故障注入仅 ON；连同专用复制、遍历和序列化一起移出 OFF；
- 删除 CPU incremental baseline 后仅服务测试的附加 CSR capture/FIFO；CUDA 计算实际需要的 CSR 输入始终保留；
- 功能状态与 observation 分离，取消状态判断所依赖的完整诊断对象和重复 levels；删除持久重复的 `active_arc_mask`，validator 读取实际图，保留真正 activity/tombstone；
- 缩小或在受控生命周期内借用 `ExpectedBeforeBinding` 的真实依赖，避免完整 graph/index 复制；恢复历史保留必要编辑/模式，取消每批整段复制，独立恢复证明仅 ON；
- 共享会话内不可变 Liberty/模型，分离实例负载与可变 timing；负载更新不重复打包、追加或上传未变表；
- 使用实际修改范围的撤销记录、稳定所有权和结果工作缓冲，取消每批完整 Database/Liberty 克隆及设备图复制；复用设备容量、stream/events、上传/计算 scratch，容量足够时不重分配整套设备状态，扩容单列；
- 取消全局 Arc 重排及全量前驱重映，维护确定的候选顺序和受影响邻接；减少 metadata、Aux 映射及 before-state 重复维护，必要全图算法成本如实计量；
- 处理重复 seed、空路径槽和多 clock-tag 存储放大，保留全部实际有效路径身份，不截断维度；
- 按第 5.4–5.5 节提交权威结果并按需回传/物化；同 generation 复用缓存，新提交使旧缓存失效。所有公开查询得到当前结果，不读旧 native timing，不以 CPU full 重算替代 CUDA 结果；
- trace runner 的 baseline 恢复仅是样本生命周期，生产成功提交不自动撤销；默认一次性 CPU/full 兼容，不新增运行期 debug 开关。

**正确性门**

- 独立 Release OFF/ON 下验证正常连续批次、查询前后继续编辑、重复查询、完整报告、真实失败回滚和恢复后继续提交；
- 输入边界、session/generation/owner、局部 expected-value、容量/数值/cycle、原子提交、poison 和实际恢复均在 OFF 保留；公共任意输入 validator 不因减少内部复制而失效；
- ON 保留独立 fresh native CPU/full、逐字段及恢复等价证明；独立验收比较 OFF/ON 当前 generation 的实际公开结果；
- 代表性调用、分配和传输剖析证明 OFF 无诊断专用工作、无每批整库/设备图事务复制、无未变表重传，容量足够时复用设备存储；扩容/撤销/释放不泄漏或复用失效绑定；
- 相关 native/parent 回归、严格构建、修改文件 lint/type 和差异检查完成，实际基线失败另列；不得以源码字符串、对象清单或固定返回计数代替运行证据。

**阶段报告重点**

记录删除/ON/保留改造分类、所有权与接口迁移、按需查询行为和实际复制/分配证据；区分功能工作与诊断，不把简短 usage 变成验证日志。

### 阶段 12：CUDA 并行计算、规模验证与核心性能验收

状态：尚未实施；Stage 11 验收后开展。保持增量图/分层与全图传播，不加入 affected-cone AT/RAT 或 auto policy。

**先分析**

- 传播、full levelization、三个 CSR patch kernel 的依赖与写入归属，包含时钟、顺序发射和时序检查；不能仅增大 launch 参数；
- 确定候选顺序与 epsilon/舍入/winner/前驱/路径语义，识别共享可变状态及同步边界；
- 在优化前冻结代表性规模、真实/合成 trace、消费者结果需求、合理 CPU 线程配置、统计方法和必过性能用例；小设计只承担对应功能/交叉点验证。

**交付**

- 替换单线程 propagation、full levelizer 和三个 CSR patch kernel；正向按层、反向按逆层，同层节点并行、节点内候选顺序确定、结果写入归属明确；
- 保持现有数值与 winner 语义，不用无序 atomic max/min 替代；时钟、顺序发射、时序检查纳入并行，按实际 clock domain 遍历，避免每个 clock 扫描全图；
- CUDA/full 与 CUDA/incremental 共用优化后的传播；full 保留完整图重建、分层和传播，同时同等复用不可变模型和分配容量；
- 保留 CPU mixed 构造/Kahn 与 GPU reconstruction 分工；区分必要算法遍历与可通过增量维护消除的重复工作；
- 合并小传输、减少不必要同步，先保证上传数据生命周期与 stream/event 依赖；用运行剖析验证实际并行度、分配、传输和同步；
- 复用现有性能入口输出第 9 节消费者端到端指标，不用延迟回传、减少结果需求或低效 full 对照制造收益。

**正确性门**

- 独立 Release OFF/ON，保留独立 native CPU/full oracle、xtea/usb/zipdiv 原输入与 ICS55 配置、真实 Q/D 多批次、winner/paths/时序检查、实际模式、恢复及跨构建等价；
- 覆盖宽层、高扇入/扇出、汇聚、epsilon-chain、并行弧、多时钟、多 tag、长批次和容量增长；执行适用的 CUDA 内存及并发检查；
- OFF 正式采样不启动 oracle/完整诊断，ON 采样前拒绝；实际失败、未支持和未执行如实分类，不放宽 tolerance、丢字段或关闭必要检查换取速度；
- 按第 9.2 节冻结口径交错运行，工程验收默认预热 5 次、采样 30 次，主要比较包含必要回传/物化/后处理的 `consumer_step_ms`；
- 必过用例的 CUDA/full 对 native CPU/full、CUDA/incremental 对优化后 CUDA/full 两项配对加速比 95% 置信区间下界均大于 1；不要求论文倍数或所有规模更快，未达性能门不得标记本阶段或高性能实现完成。

**阶段报告重点**

给出实际并行与存储行为、分相/消费者耗时、内存规模、两项收益及置信区间、交叉点和全部负结果；明确全图传播仍是算法范围，不以 kernel 时间冒充端到端收益。

### 阶段 13：生产集成与正确性 CI

状态：尚未实施；由原 Stage 11 顺延，必须先通过新 Stage 11–12。原 Stage 11 实现已撤回，其草案不作为本阶段已批准的详细计划；实施前重新分析和审阅。

**先分析**

- 在 CTS 和基线 legalization 完成后、routing 前接入实验 TIMING_OPT；
- 树形 pre-route RC、propagated clock、CRPR 在 native/reference/CUDA 的语义与失效边界；
- EngineDB/IDB、placement、RC、native STA、host/device CSR 的共同提交与恢复，以及消费者需要的结果；
- 复用 Stage 11–12 的持久存储、增量事务、按需物化和并行计算；不注册 GitHub runner，不重建独立诊断/执行框架。

**交付**

- 显式 opt-in `incregpusta_experimental` preset；普通 preset、signoff/post-synthesis 默认仍 cpu/full；
- 根据合法化坐标和工艺参数估算 RC，支持固定 propagated clock tree；仅在验证后解除对应 unsupported；
- 每批仅移动新 buffer，复用候选选择器、合法化和事务/恢复机制；新增 RC/时钟功能不重新引入整库复制、重复 baseline、串行全图传播或默认诊断；
- fixed physical trace 通过四模式 correctness 后接入 closed-loop greedy，分别记录实际批次和停止原因；
- 实现 `EngineDB/IDB + placement/legalization + RC/parasitic + iSTA Database + host/device CSR` 的 stage/publish/rollback；
- 当前 generation 的 final-batch power/timing report/SDF 按需物化，输出完整后发布 artifact manifest；
- PR CPU fast、native source-build、手动 CPU integration 和 GPU correctness 工作流，以及现有服务器验收；
- 独立阶段报告与简短 usage；关闭实验 preset 即回到原流程。

**正确性门**

- 三个设计 xtea、usb、zipdiv 保持原输入及 ICS55 配置，另建 post-CTS 合法化 checkpoint；四模式实际执行多批次物理 trace；
- ON 每批对独立 fresh native CPU/full 比较拓扑、timing、winner、适用时序检查、公开 QOR 和 paths，验证 level 合法性及实际模式；
- greedy 非空 edit 实际执行目标 incremental，不静默 full；无候选与 baseline 不计增量通过；
- 发布前后故障不留下物理/timing/CSR 分叉，或 poison 后从 committed checkpoint 重建并继续提交；
- 查询、输出后继续提交及恢复后输出正确；final-batch artifacts 来自当前 generation，产物失败不发布旧结果；
- 默认流程、既有 artifacts、OFF/ON 等价、CPU/GPU 回归和 CUDA 内存检查通过；必要失败处理始终保留；
- 独立 Release OFF/ON 隔离 binding，核对真实构建状态；运行剖析确认 Stage 11–12 的默认路径和并行实现没有回退；完整生产性能结论由 Stage 14 验收。

**阶段报告重点**

记录生产入口、语义支持矩阵、物理事务、fixed trace/greedy 实际结果、按需查询与产物、CI 和独立审阅；列明未通过或未执行项，不提前宣称生产性能验收完成。

### 阶段 14：正式性能评估、论文可比性与结论

状态：尚未实施；由原 Stage 12 顺延，Stage 13 正确性稳定后开展。本轮只维护计划，不启动实验。

**先分析**

- benchmark 输入许可、可分发性、runner 稳定性及与论文输入/参数/硬件的差异；
- 四模式同一 trace、结果需求下的加载、恢复、提交、按需物化、消费者及 artifact 计时边界；
- 扩大真实设计、规模、批次和实际影响比例，预先冻结生产必过性能用例；不把 full propagation 描述为 affected-cone。

**交付**

- 复用 benchmark manifest、原始 JSON/CSV、汇总器、复现说明及手动 Release/OFF 工作流；
- engineering、paper-protocol、exact-paper profiles 和 comparability status；缺少论文原始输入时 exact-paper 为未执行；
- 四模式重放相同冻结 trace；1、10、100、1K、10K、100K buffers 及不同实际影响比例，合成/真实、fixed trace/closed-loop 分开报告；
- 工程验收统一默认预热 5 次、采样 30 次，保留全部原始样本；固定构建、线程、设备、输入和结果需求，保留加载、恢复及清理；
- cold/warm、core、提交、查询物化、消费者、artifact 和 cold end-to-end 同边界结果，复验生产消费者收益。

**正确性门**

- 性能入口只接受 OFF，ON 采样前拒绝；不启动 oracle、不生成完整诊断 receipt，比较/诊断为 `not_run`；
- 独立功能验收先于采样；在生产必过用例上按第 9.2 节复验 CUDA/full 对 native CPU/full、CUDA/incremental 对优化后 CUDA/full 的显著正收益；
- 保存原始样本、环境、trace、命令和失败复现，不外推超时或资源受限点，不改变消费者需求或排除必要成本；
- 保留全部负结果、交叉点和论文可比性限制，不要求每个小设计或所有规模都快；未通过指定收益门不能以“测量完成”代替高性能验收。

**阶段报告重点**

给出生产性能结论适用范围、置信区间、负结果及剩余研究项；auto policy 仅在数据充分后另行提案。

## 11. CI 分层

1. **PR CPU fast gate**
   Python mode/config tests + native CSR/unit/small property CTest；无 PDK、无 GPU、固定小 seed。
2. **PR native source-build gate**
   当前父仓库默认 CI 不运行 CTest，需在 ecc-tools CI 或 ECC `build-all` job 显式执行 `ista_unit|ista_property`。
3. **Nightly/manual CPU integration**
   `integration,pdk,slow`、真实 design、greedy loop、更多 seeds；上传 correctness JSON 和失败 traces。
4. **Self-hosted GPU correctness gate**
   synthetic + 至少一个真实 design，运行 GPU full/incremental。无 GPU 只能明确 skip/not-run，不能算通过。
5. **Stage 12 / Stage 14 manual performance gate**
   Stage 12 验收核心消费者收益，Stage 14 复验生产收益与论文可比性；Release/OFF、固定 runner、上传 raw JSON/CSV 和置信区间，按预先冻结用例判断。普通 PR 不采用跨硬件绝对时延门禁。

示意命令，执行前须按实际 target 名更新：

~~~bash
cmake -S chipcompiler/thirdparty/ecc-tools \
  -B chipcompiler/thirdparty/ecc-tools/build-ista \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_TESTING=ON \
  -DISTA_ENABLE_CUDA=OFF

cmake --build chipcompiler/thirdparty/ecc-tools/build-ista \
  --target ista_incremental_tests -j"$(nproc)"

ctest --test-dir chipcompiler/thirdparty/ecc-tools/build-ista \
  -L ista_unit --output-on-failure

uv run pytest test/tools/ecc/test_module_timing_modes.py -q
uv run pytest test/integration/test_incremental_sta_flow.py \
  -m "integration and pdk and slow" -q
~~~

## 12. 总体验收标准

全部满足后才称“ECC 中复现完成”：

- 主验收门是可重复的功能正确性、语义正确性和回归一致性；哈希、对象指纹及 source/object/count inventory 只作边界和证据完整性辅助，不得替代功能证据、单独阻断已证明正确的功能验收，也不得扩张为无上限的“哈希攻防”。
- 默认 cpu/full 的 API、flow 和 artifact 保持兼容；
- CPU/GPU 与 full/incremental 均可显式选择；
- 请求模式、实际模式和 fallback 永远可见；
- native object graph 仍是 canonical，不发生全项目数据结构重构；
- CSR adapter round-trip、Dual-CSR、mixed levelization 不变量全绿；
- 每个 semantic edit batch 后，目标模式与 fresh-session CPU/full 逐点 timing 等价；
- greedy harness 真实插入 buffer，并分别支持 fixed-trace 与 closed-loop；
- gpu/incremental 路径实现论文式增量 update + levelization + full propagation；
- data-only/clock-edit contract、跨层 physical transaction 和 current-generation power/report/SDF 后处理均通过 integration gate；
- GPU correctness 在真实设备上通过，传播/full levelization/CSR patch 的实际并行执行由运行剖析验证；
- Stage 11 的默认路径无诊断专用工作和每批完整事务复制，按需查询返回当前 generation，稳态存储复用和扩容行为取得实际证据；
- Stage 12、14 按预先冻结的消费者需求和用例分别通过核心/生产性能门，CUDA/full 对 native CPU/full、CUDA/incremental 对优化后 CUDA/full 均有显著正收益；保留原始样本、置信区间、负结果与 break-even，正确性通过不能替代该门；
- 每阶段均有独立 subagent 审查记录、修正循环、测试记录和文字变更说明；
- 父仓库与 ecc-tools 的 `IncreGPUSTA` 分支/commit/gitlink 可达且清晰；工作树无未解释的本阶段改动，并保留用户已有修改。

## 13. 明确推迟的研究项

以下不属于首轮论文复现：

- CPU/GPU affected-cone AT/RAT propagation；
- 基于 workload 自动选择 full/incremental；
- general reverse Auxiliary CSR；
- node deletion/ID reuse；
- arbitrary old→old edit；
- CSR compaction/tombstone reclamation；
- 多 corner 共享 device topology；
- 与外部 Sizer/OpenSTA 内部迭代深度耦合。

只有阶段 9–13 正确性稳定且阶段 12、14 性能门通过、数据充分后，才可单独提案。即使将来增加 `auto`，手动 full/incremental 选择仍必须保留。

## 14. 本计划自身的审阅记录

### 前置并行分析

- 论文算法审计 subagent：核验 9 页论文、Algorithms 1–7、实验设置和伪代码歧义；
- ECC 调用链 subagent：核验 general iSTA、iCTS FastSTA、iZH FanoutFixer、TIMING_OPT、iRT 和 submodule branch；
- 测试/性能 subagent：核验 pytest/CTest/CI、oracle、schema、GPU runner 门禁。

### 独立计划审阅

- Round 1：两名未参与撰写的 subagent 均给出 `request changes`，无普通代码修改参与。主要意见是增加 CSR CPU reference、隔离 fresh sessions、建立三层 edit/事务 contract、精确定义四模式与计时边界、拆分 greedy/mixed-levelization、后移 affected-cone、修正 level eligibility，并增加 submodule commit 可达性门禁；以上意见已纳入 `v0.2`。
- Round 2：新的独立 subagent 给出 `request changes`，确认 Round 1 核心修改已闭合，但要求补齐 clock/power/report/SDF 后处理、real-design 跨层物理事务、阶段 5/8 的即时 timing gate，以及生产安全校验与 differential oracle 的计时区分；以上意见已纳入 `v0.3`。
- Round 3：第三名新的独立 subagent 完整终审，结论 `APPROVE`，无 blocker、无 major；确认用户要求、论文边界、ECC ownership、阶段闭环、后处理、跨层事务和计时口径均已闭合。

### 阶段 1 详细设计审查

- [阶段 1 详细计划](incregpusta/stage1-detailed-plan.md) 已冻结为 `v1.0`；经过六轮独立审查与修正，最终三名审查者均给出 `APPROVE`，无 remaining finding。
- 阶段 1 已在本地完成：parent 与 native 独立代码审查均最终 `APPROVE`，正确性回归和阶段报告已闭环；parent 与 ecc-tools 本地提交分别为 `ee2563b2d27165d9324d82103cdf28bddb414956` 与 `a7355b216b801f72a99d92e77765f49c744148b3`，均未推送。详见[阶段 1 报告](incregpusta/stage1-report.md)。

### 阶段 2 完成状态

- [阶段 2 详细计划](incregpusta/stage2-detailed-plan.md)、Steps 2–9冻结计划和[阶段 2 报告](incregpusta/stage2-report.md)已记录as-built边界、审查与回归结果。
- 简化功能验收确认18/18 native/reference/scatter/rerun pair一致，当前字节完整CSR回归79/79、parent非PDK回归1667 passed；指标为`non_comparable`，不宣称speedup。
- 原v0.31严格POST→report-transition→FINAL在三次正式候选后仍未封口；按用户预先授权停止扩张哈希审核，以功能正确性收口。parent/child本地提交分别为`49f1bc99ed8a4126a6f4da2bfd3236cdb04df4e9`与`5609a3c932e7bcb6cfb2a2ee765f472e0615e395`，均未推送。

### 阶段 3 完成状态

- [阶段 3 详细计划](incregpusta/stage3-detailed-plan.md)与[阶段 3 报告](incregpusta/stage3-report.md)已记录as-built contract、native candidate、transaction/full-exact receipt、fresh oracle/recovery和边界。
- 删除2项源码清单/字符串扫描门禁后，Stage 3 `^ista_timing_edit_` 功能集14/14通过；Stage 2最小真实兼容路径33/33通过，覆盖GraphBuilder、projection、scatter、real differential与full baseline。
- 完成结论以raw Database/resolver/trace/host CSR/native timing/CSR full逐字段一致和fresh process重放为依据；不以trace hash、源码SHA或CTest数量常量替代功能证据。
- 阶段 3仍只执行CPU/full并明确拒绝未实现模式，不宣称incremental或GPU性能；不修改EngineDB/IDB物理状态。

### 阶段 4 完成状态

- [阶段 4 详细计划](incregpusta/stage4-detailed-plan.md)已冻结为v1.0，[阶段 4 报告](incregpusta/stage4-report.md)记录selector、fixed trace、one-shot production replay、source isolation和as-built边界。
- 删除2项精确source/object/Ninja inventory后，Stage 4 `^ista_buffer_` 功能集18/18、Stage 3功能回归14/14通过；历史parent冻结STA 227/227与non-PDK 1665项、Stage 2完整兼容集中74项功能/真实流程均通过。
- Stage 2原5项共享Ninja对象记录/全局CTest数量冻结属于静态实现清单，已在Stage 0–6过度防御清理中删除；real differential fresh-process、projection、scatter、reference input和binding功能路径继续通过。
- 完成结论来自native CPU/full↔CSR full timing、raw Database/resolver/host CSR、三个fresh child、五件source artifact和primary IDB投影逐字段一致；integrity hash不替代这些证据。
- 当前仍只执行CPU/full，real trace为`non_comparable/engineering_rc_no_physical`；不宣称Dual-CSR、GPU、物理提交或speedup。

### 阶段 5 完成状态

- [阶段 5 详细计划](incregpusta/stage5-detailed-plan.md)已冻结为v1.0，[阶段 5 报告](incregpusta/stage5-report.md)记录targeted Dual-CSR、direct-view full timing、production differential、rollback/source isolation、telemetry与as-built边界。
- generation-0 typed anchor与后续narrow verified descriptor隔离成立；BaseOut/BaseIn/AuxOut直接视图、append-only logical identity、parallel group重编号和九字段transaction publish均通过语义验证。
- GCC 14 strict Release功能矩阵120/120唯一测试、frozen synthetic/real全prefix differential、1 warm-up + 6 raw timing smoke、parent冻结STA 227/227及non-PDK 1665项均通过；ASan/UBSan核心与异常边界各7/7无诊断。
- #119 reference异常越过graph API的真实回归已在shared projector精确交界局部修复并完整回归；旧inventory和Ninja生成器绑定已在Stage 0–6过度防御清理中删除，`py_idb`系统Python header缺失仍作为环境限制单列，不覆盖功能结论。
- 完成结论来自topology、payload、level、timing、generation、rollback、fresh replay和source unchanged逐字段闭合；不宣称mixed levelization、affected-cone、GPU、物理提交、speedup或break-even。ecc-tools本地提交为`11ae6d767a4e7dc25b3504326fd7b383e1a711e5`，未推送。

### 阶段 6 完成状态

- [阶段 6 详细计划](incregpusta/stage6-detailed-plan.md)已更新为v1.0 as-built，[阶段 6 报告](incregpusta/stage6-report.md)记录pure mixed builder/Kahn/reconstruction、caller-supplied backend、typed factory/execution trace、production/fresh controller、recovery与active-payload边界。
- `cpu/incremental`已真实执行targeted Dual-CSR + mixed incremental levelization + full CPU propagation；full入口delta=1、mixed/external delta=0、correctness fallback=0，synthetic两批与real一批均与独立fresh CPU/full功能等价。
- GCC 14 strict Release统一Stage 6功能标签14/14、Stage 5功能标签5/5和13个Stage 5/6关键目标构建通过；历史ASan/UBSan各8/8、parent冻结STA 227/227与non-PDK 1665项通过。硬编码inventory已删除，不再把目标声明的镜像清单作为验收门。
- active-payload真实覆盖parallel same-base peer omission的`kArcMultiplicityMismatch`、aggregate不变、inactive key collision/poison隔离与独立public full等价；mode recovery完成full→mixed→rebind/replay→继续下一批。
- 最终独立全diff审查`APPROVE`，无remaining blocker/major/minor。parent/child本地提交分别为`48c09f84f4abfa60c95c0e4b7809c96ee31f97e3`与`b8bfc3a79930b0be146ac26ca10dc0e99115f1fc`，均未推送；不宣称affected-cone、CUDA、物理提交、speedup或break-even。

### 阶段 0–6 过度防御清理

- ecc-tools清理提交`8eed90e86c934052f2eb10a8c114f7e41f6db7df`共修改105个文件，净变化为690行新增、11569行删除；删除目标SOURCES/LINK_LIBRARIES/COMPILE_OPTIONS自比较、CTest数量、对象文件、Ninja生成器、source SHA、AST/源码字符串及link-closure等静态实现清单，同时保留strict compile flags和功能、属性、事务、恢复及fresh-process测试。
- Stage 0删除topology/config/full-snapshot诊断哈希和manifest固定输入哈希，完整snapshot与artifact逐字段/容差比较成为权威；projection删除没有边界消费者的输入复合哈希；reference-input删除父端传入、子端原样回显的blind hash chain；CSR session改为把已验证legacy projection/FIFO原始字节与每个session/repeat直接对照，并增加“稳定一致但错误”负例。
- Stage 3/4删除重复raw/snapshot/replay receipt SHA、`IntegrityReceipt`、`frozen_artifact_digest`及其encoder/schema/validator链；Stage 5/6删除无消费者的hash-as-acceptance布尔字段和静态ownership/link-closure门禁。
- 保留确有语义用途的Stage 2 `CsrSnapshotIdentity`、Stage 3 `ComponentFingerprints`、real-differential子进程对实际输入文件的独立重算绑定、source artifact内容校验及不可语义解码binary artifact SHA；这些摘要只防止跨generation/session或跨进程误绑定，不替代功能比较。
- 最终Nix/GCC 14 Release/Ninja重新configure通过；Stage 0–4 focused功能集55/55及projection/real-differential边界集5/5通过，Stage 5/6联合功能标签25/25通过（Stage 5 4/4、Stage 6 14/14）。首次联合标签中18项因目标尚未构建而`Not Run`，明确构建18/18后原样复跑全绿，没有把缺二进制计作功能通过。
- 12个现存变更JSON全部解析通过，全部变更Python通过实质lint，`git diff --check`通过且无`__pycache__`残留；功能终审与哈希边界终审均`APPROVE`，blocker/major/minor均为0。

阶段 0–6 已完成，当前可进入阶段 7；详见[阶段 0–6 过度防御清理报告](incregpusta/stage0-stage6-defense-cleanup-report.md)。剩余阶段不得跳过，后续仍须执行第2.2节闭环，继续以功能正确性为主且不得扩张无上限哈希攻防。

### 阶段 0–6 第二轮复杂度清理（2026-09-05）

本轮按用户要求只做本地提交：ecc-tools `c40b57b5086acddb118e0107928c82ea21084eb3`；parent 为本计划所在提交并同步 gitlink。均未 push，属于未发布本地工作。

第二轮清理直接构建 signoff 最终运行项，合并 Stage 6 确定性遥测字段及恒等式校验，统一 mixed pipeline 自由函数入口，并删除无调用的校验 helper、让测试复用实际 reference validator。功能边界、JSON wire、事务与恢复语义不变。具体实现、回归状态和本地工作状态以[第二轮清理报告](incregpusta/stage0-stage6-second-cleanup-report.md)为准；该补充不重新宣称 Stage 7 或 GPU 验证完成。

## 15. Material Passport

- **Origin**：`academic-research-suite` 的 experiment-planning/reproducibility 工作流；`pdf` skill 的 PDF 读取与视觉核验流程。
- **Mode**：repository-grounded reproduction and experiment plan。
- **Created**：2026-08-19。
- **Source paper**：*IncreGPUSTA: GPU-Accelerated Incremental Static Timing Analysis for Iterative Design Flows*，9 页 PDF。
- **PDF verification**：页数声明、枚举和 reader count 均为 9；全文提取并逐页渲染检查；SHA-256 `5eaf161a2cdfb8930f1e0a9f4e2d6b98f7f192570ee68d7f75b90df0a384d097`。
- **Repository verification**：计划分析开始时父仓库与 submodule 均干净、`ecc-tools` 为 detached HEAD；阶段 0 结束时 parent/child 本地提交为`447e15517ab0af95e403a19956f215876fb08283`/`f1b1351a18d862b086de8b191f51ee5a1688638b`；阶段 1 为`ee2563b2d27165d9324d82103cdf28bddb414956`/`a7355b216b801f72a99d92e77765f49c744148b3`；阶段 2 为`49f1bc99ed8a4126a6f4da2bfd3236cdb04df4e9`/`5609a3c932e7bcb6cfb2a2ee765f472e0615e395`；阶段 3 为`8787d4b1a6743169a2ff4dcb4c173832577dbd8c`/`5877ba0671da77ee6a69ad9765f1d9c761923965`；阶段 4 为`ace28d79e19647c6f4866a339cc6faa7dca61fa9`/`eff4706f77a882d84317341f78e567ef5262b6d1`；阶段 5 为`8d7b642b94ff136d804539453ef484ba5d870034`/`11ae6d767a4e7dc25b3504326fd7b383e1a711e5`；阶段 6 为`48c09f84f4abfa60c95c0e4b7809c96ee31f97e3`/`b8bfc3a79930b0be146ac26ca10dc0e99115f1fc`；Stage 0–6过度防御清理为`ab27ca9b8ddc53fe5a7d7f8d690d6f1b903d13c5`/`8eed90e86c934052f2eb10a8c114f7e41f6db7df`。以上提交均在`IncreGPUSTA`且尚未推送；各阶段辅助静态限制已如实记录，完成结论始终以功能正确性、fresh replay和source unchanged为主证据，哈希仅作artifact身份辅助，不扩张为无上限攻防。
- **External-data status**：论文的 TAU15-derived 数据、随机 netlist/library 生成参数和 seeds 未随 PDF 提供；绝对 WNS/TNS 和原始 insertion trace 不能仅凭论文复现。
- **Version**：`v1.9-stage0-6-function-first-cleanup-verified`。
