# ECC IncreGPUSTA 阶段 4 详细实施计划

> 当前开发协议补充（开发检查分离）：保存的编辑记录、执行模式和 generation 继续用于真实恢复；完整 fresh oracle、逐字段 receipt 和故障注入归 ON。 后续改动必读 [开发检查规范](development-guidelines.md)，双模式实测与历史验收的区别见 [本轮实施报告](debug-checks-implementation-report.md)。原阶段验收数字保留为历史记录。

> 状态：实现、独立审查与正确性验收完成 v1.0；Stage 3 contract/native transaction/fresh oracle保持冻结，Stage 4以功能逐字段一致、one-shot fresh replay与source unchanged完成收口
> 基线：Stage 3 完成本地提交 parent `8787d4b1a6743169a2ff4dcb4c173832577dbd8c`，ecc-tools `5877ba0671da77ee6a69ad9765f1d9c761923965`
> 交付：Stage 4 ecc-tools 已封存为 `eff4706f77a882d84317341f78e567ef5262b6d1`；parent 提交在本报告入库后创建，均不推送
> 范围：确定性 greedy selector、fixed semantic trace generator/replayer、synthetic micro traces、真实小设计 trace、CPU/full 与 CSR full 逐批比较；不做多模式 closed-loop 优化或物理提交
> 验收原则：功能 equality、fresh replay 与源设计不变是主证据；trace hash 仅标识冻结文件，不进行无上限哈希攻防

## 1. 阶段目标与硬前置

阶段 4 把论文中的 buffer insertion 规则固化为可重复、可审计的 fixed semantic traces。generator 可以在唯一 CPU/full reference 上逐轮重新观察与选择；trace 冻结后，所有 replay lane 只重放相同 edits，不再重新选点。每个 batch 在 Stage 3 isolated iSTA candidate 中执行 native full 与 CSR full，并在多个独立one-shot probe process/session中证明语义等价。

硬前置：Stage 3 的 native translator/mutator、shadow publish、stable creation token、fresh cumulative CPU/full oracle和 recovery必须已通过。未满足时 Stage 4 停止，不得退化为直接改 JSON、`CsrReferenceInput` 或 detached mock graph。Stage 4 只能在自己的 runtime/test adapter 中消费 Stage 3 已冻结 API，不得为 replay 修改 Stage 3 core、扩大 authority 可见性或增加可逃逸的 session/context seam。

## 2. iZH 与物理边界结论

现有 `iZH::FanoutFixer::fix()` 不可复用：它直接访问全局 IDB，使用 `std::set<IdbNet*>` 指针排序和跨调用 `static new_idx`，先断开 loads 后创建对象，没有 slack/gain/tie-break/undo/失败原子性。阶段 4 不调用、不链接、不包装它。

阶段 10 将来可复用的仅是 IDB create/connect/disconnect/remove 等物理 primitive；阶段 4 的 selector、policy、naming、trace 与 replayer 全部放在 benchmark/experimental coordinator。真实 design snapshot只读，replay 只进入 isolated iSTA staged view，绝不 commit EngineDB/IDB/placement/RC 物理变化。

## 3. 模块与 target

```text
src/operation/iSTA/benchmark/buffer_trace/
  BufferTraceTypes.hpp
  GreedyBufferCandidateSelector.{hpp,cpp}
  BufferTraceCanonicalEncoding.{hpp,cpp}
  BufferTraceValidationRules.{hpp,cpp}
  BufferTraceJson.{hpp,cpp}
  NativeBufferObservationExtractor.{hpp,cpp}
  BufferFixedTraceGenerator.{hpp,cpp}
  FreshBaselineRunner.{hpp,cpp}
  BufferReplayContext.{hpp,cpp}
  BufferTraceReplayer.{hpp,cpp}
  CMakeLists.txt

src/operation/iSTA/benchmark/schema/
  buffer_fixed_trace_v1.schema.json
  buffer_trace_contract_manifest_v1.json
  buffer_trace_profile_contract.py
  validate_buffer_fixed_trace.py

src/operation/iSTA/test/
  BufferTraceTests.cmake

src/operation/iSTA/test/timing_edit/
  BufferCandidateSelectorTest.cpp
  BufferTraceContractTest.cpp
  BufferTraceObservationExtractorTest.cpp
  BufferTraceReplayerTest.cpp
  BufferTraceParasiticBoundaryTest.cpp
  BufferTraceProductionFreshAdapter.{hpp,cpp}
  BufferTraceProductionFreshSupport.{hpp,cpp}
  BufferTraceProductionGainValidator.{hpp,cpp}
  BufferTraceCsrJson.{hpp,cpp}
  BufferTraceReceiptJson.{hpp,cpp}
  BufferTraceProductionFreshProbe.cpp
  CheckBufferTraceStage4Isolation.cmake
  buffer_trace_controller.py
  buffer_trace_first_empty_test.py
  buffer_trace_terminal_empty_test.py
  buffer_trace_preloader_rejection_test.py
  buffer_trace_functional_check.py
  validate_buffer_trace_manifest.py
  fixtures/buffer_fanout/{tech.lef,cell.lef,stage4.lib,design.v,design.sdc}
  fixtures/buffer_two_batch/{design.v,design.sdc}
  fixtures/buffer_no_gain/{design.v,design.sdc}
  fixtures/buffer_terminal_empty/{design.v,design.sdc}
  traces/{synthetic_two_batch.json,real_buffer_fanout.json,manifest.json}
  traces/templates/{synthetic_two_batch.template.json,real_buffer_fanout.template.json}
```

Target 分层：

```text
ista_buffer_trace_contract
  sources = BufferTraceCanonicalEncoding.cpp,
            BufferTraceValidationRules.cpp,
            BufferTraceJson.cpp,
            GreedyBufferCandidateSelector.cpp
  direct links = ista_timing_edit_contract, ista_timing_csr_core
  DB/IDB-free

ista_buffer_trace_runtime
  sources = BufferFixedTraceGenerator.cpp,
            BufferReplayContext.cpp,
            BufferTraceReplayer.cpp,
            FreshBaselineRunner.cpp,
            NativeBufferObservationExtractor.cpp
  public direct links = ista_buffer_trace_contract,
                        ista_timing_edit_transaction,
                        ista_timing_edit_native
  private direct links = ista_timing_graph_csr_adapter,
                         ista_timing_database_headers
```

`BufferTraceCanonicalEncoding` 必须组合调用 Stage 3 的 CreationToken、StableRef、DesignEditPlan 与 baseline identity canonical encoder，不再实现第二套编码。`ista_buffer_trace_contract` 的全闭包禁止 `ista_interface/ista_source/idm/iZH/pybind/CUDA`；`ista_buffer_trace_runtime` 不得把这些 target 作为 direct link 或源码依赖。冻结的 Stage 3 `ista_timing_edit_native` 所带既有 `ista_interface/ista_source` 静态传递闭包不算 Stage 4 越界，但 `idm/iZH/pybind/CUDA` 仍不得进入 runtime 闭包。只有真实 fixture probe 可以为只读加载 baseline 直接链接 `ista_interface/ista_source/idm`，其 object/undefined symbols 不得包含 IDB create/connect/disconnect/remove/save。

Stage 4 runtime不编译或友元化任何 Stage 3 test seam。`BufferTraceProductionFreshAdapter` 是 Stage 4 test target 独占的薄适配层：它调用现有 `ProductionFreshSessionLoader`，但所有 replay work 都必须在该 loader 的 callback 与同一个 OperationGuard 内完成。Stage 3 core、transaction、receipt、session probe和其 CMake inventory均不属于 Stage 4 文件所有权。

唯一允许看见 Stage 3 test seam 的 target 是 one-shot test executable `ista_buffer_trace_production_fresh_probe`，不是 `ista_buffer_trace_runtime` 或可复用library。它不链接另一个probe executable，而是按现有 production oracle 已证明的方式直接复编所需test support；CMake必须逐项冻结以下exact source/direct-link inventory与strict options：

```cmake
set(ISTA_BUFFER_TRACE_PROBE_SOURCES
    timing_edit/BufferTraceProductionFreshProbe.cpp
    timing_edit/BufferTraceProductionFreshAdapter.cpp
    timing_edit/BufferTraceProductionFreshSupport.cpp
    timing_edit/BufferTraceProductionGainValidator.cpp
    timing_edit/BufferTraceCsrJson.cpp
    timing_edit/BufferTraceReceiptJson.cpp
    timing_edit/oracle/ProductionFreshSessionLoader.cpp
    timing_edit/StaTimingEditSessionProbeAccess.cpp
    timing_edit/StaTimingEditCsrReceiptProbe.cpp
    CsrNativeTimingOracleReader.cpp
    CsrNativeTimingOracleNodeReader.cpp
    CsrNativeTimingOracleArcReader.cpp
    CsrTimingResultFromNativeOracle.cpp)
set(ISTA_BUFFER_TRACE_PROBE_LINKS
    ista_buffer_trace_runtime
    ista_timing_edit_transaction
    ista_timing_edit_native
    ista_timing_graph_csr_adapter
    ista_timing_database_headers
    ista_interface
    ista_source
    ista_data_manager
    ista_delay_calculator
    idm)
```

include directories精确复用test根、`timing_edit`与`timing_edit/oracle`；compile options固定 `-Wall -Wextra -Werror -pedantic -ffp-contract=off`。其中 `CsrTimingResultFromNativeOracle.cpp` 与三个 `CsrNativeTimingOracle*Reader.cpp` 是 full-exact proof所需的Stage 2 native materializer source closure，不得以伪造结果替换。inventory gate同时断言 `ista_buffer_trace_runtime` 的sources、direct links、link closure与undefined symbols均不含 `ProductionFreshSessionLoader`、`StaTimingEditSessionProbeAccess`、`StaTimingEditCsrReceiptProbe` 或这些Stage 2 test materializer symbols。

## 4. 论文规则与 ECC 工程规则

论文明确给出的内容：按 slack 选择 critical nets、top-k profile、在候选 pin 前插 buffer、Elmore 近似 gain、batch 后重新计算 affected timing，以及 `top-1000×1`、`top-100×10` 与 buffer sweep 的实验轮廓。

论文未明确、由 ECC 显式冻结的 engineering definition：candidate 枚举、data-only/single-driver legality、正 gain、binary64 求值与 tie-break、library/port、RC/placement、seed、每 net 每 batch限制、creation token和fallback policy。报告必须逐项区分 paper rule 与 engineering rule。

版本化 selection profile exact字段为 `id/top_k/rounds/max_total_insertions/analysis/operating_point/rc_profile`：

| profile | 语义 | comparability |
|---|---|---|
| `paper_protocol_top1000_x1` | `top_k=1000, rounds=1`，仅冻结协议形状 | `protocol_only` |
| `paper_protocol_top100_x10` | `top_k=100, rounds=10`，每轮 full后重观察 | `protocol_only` |
| `engineering_smoke` | 小 fixture 的有限 top-k/rounds/target count | `non_comparable` |

buffer-count sweep编码为 target-count profile，不另写 selector。每轮在空 batch、达到 rounds或达到 `max_total_insertions` 时停止并记录唯一 stop reason；小 fixture只验证协议与停止语义，不声称完成论文规模。

## 5. Deterministic greedy selector

### 5.1 Native observation 与候选枚举

```cpp
struct BufferCandidateObservation {
  timing_edit::StableNetRef net;
  timing_edit::StableNodeRef driver;
  timing_edit::StableNodeRef candidate_pin;
  std::vector<timing_edit::StableNodeRef> moved_sinks;
  std::optional<MaterializedSetupTiming> setup_timing;
  double upstream_resistance_kohm;
  double candidate_load_pf;
  double buffer_capacitance_pf;
  double buffer_resistance_kohm;
  double buffer_delay_ns;
  LibraryCellRef buffer;
  PlacementInputs placement;
  RcInputs rc;
};
```

`NativeBufferObservationExtractor` 只读已完成 native CPU/full 的 `Database`。v1 对每个合法 single-driver data net、每个合法 instance-input sink `p`、每个合法 buffer cell 生成一项，固定 `candidate_pin=p`、`moved_sinks={p}`，不做多-sink clustering。setup timing 只接受 `TimingPoint` 中存在 `AnalysisType::kMax` path-state bucket、该 bucket 至少有一条 finite arrival，且 aggregate scalar `arrival/required/slack` 不全为默认零的情形；这三个 scalar 进入 `MaterializedSetupTiming`，selector 再逐项检查 finite，并要求按 binary64 顺序 `required-arrival == slack`。missing point、missing max、min-only 或 aggregate 三项全零保留合法结构候选但令 `setup_timing=nullopt`，generation evaluation 固定为 `decision=rejected`、`rejection_reason=timing_not_materialized`、`numeric=null`；finite max path 配合非 finite aggregate scalar固定为 `non_finite_timing`，不一致的 scalar slack 固定为 `slack_mismatch`。clock `TimingPoint`、sequential/clock-gating sink instance、instance 声明的 clock pin 与 Liberty clock port 在候选构造前直接过滤，因此这些对象不会产生 generation evaluation receipt；不得把“无 candidate”误写成带稳定 rejection reason 的 candidate receipt。`net_slack` 取该 net 已物化候选的最小 setup slack。

buffer legality固定为：combinational、非 sequential/clock/gating/tri-state，exact一个 data input与一个 output，输出 Boolean function为输入恒等，且二者间存在 positive-unate graph timing arc。library/cell/port和每个 operand来源进入generation receipt。

### 5.2 Gain、单位与求值顺序

统一单位为 kΩ、pF、ns，利用 `kΩ × pF = ns`。`Cload` 与 `Cbuf` 取所选 sink/buffer input rise/fall capacitance的 finite nonnegative max；`delaybuf` 在 profile固定的 input-slew/output-load operating point上用现有 `CsrTableLookup` 分别求 rise/fall再取 max；无物理 RC 时 `Rupstream/Rbuf` 来自版本化 engineering RC profile，仅用于选择。所有 R/C/delay非负。

```text
delta_capacitance = Cload - Cbuf
benefit = Rupstream,p * delta_capacitance
penalty = Rbuf * Cbuf
gain = (benefit - penalty) - delaybuf
```

每一步检查 finite，任一中间 overflow/NaN/Inf返回 typed numeric error。target固定 `-ffp-contract=off`，禁止 fast-math、reassociate和FMA收缩。仅 `gain > +0.0` 接受；`±0`与负数拒绝。selector不写 Database，也不把 gain当 replay timing输入。

positive-gain fixture不得写死 expected gain。测试必须从实际 Liberty closure读取 sink/buffer capacitance，用 production `CsrTableLookup` 在 profile operating point查询 rise/fall delay，按上述 binary64 顺序计算每个 operand与最终 gain，并断言其 finite 且严格大于 `+0.0`；generation receipt中的值必须逐字段等于这次实际计算。fixture的cap与engineering RC profile可以为形成正值而设计，但不能以常量 gain、预制 lookup结果或绕过table lookup来保证通过。

### 5.3 排序、top-k 与冲突

1. critical net key：`net_slack ascending`、StableNetRef canonical bytes、driver canonical bytes；先取 profile `top_k`；
2. 每个 critical net内部按 `gain descending`，exact tie依次 candidate pin bytes、library、cell、input port、output port；取第一个正 gain candidate；
3. accepted跨 net顺序严格等于 critical-net顺序，每 net每 batch最多一个；
4. 非法候选在排序前剔除；accepted之间出现共享 moved sink、StableRef、token或materialized name冲突时整批 typed error，不 silently choose next；
5. real v1的seed固定0；selector没有随机ranking分支，synthetic seed仅作为稳定输入写入CreationToken/trace，source-artifact recipe独立确定性物化；
6. input permutation、fresh process与重复运行必须产出相同 accepted order和trace。

## 6. Creation token 与对象命名

直接复用 Stage 3 `CreationToken` 与 `StableNodeRef/StableNetRef/StableArcRef`，Stage 4 不重声明 schema或编码。对象 role 区分 instance/output-net/pin:<port>/cell-arc:<library ordinal>/old-net-arc/new-net-arc。名称沿用 Stage 3 原样格式 `__ista_buf_b<batch>_e<accepted>` 与 `__ista_net_b<batch>_e<accepted>`（十进制、不补零），生成前检查 baseline和前批 collision。trace保存token和语义refs，不保存dense ID、pointer、native rank。replayer在每个one-shot child的fresh session中重新解析token→本地NodeKey/net name→session slot。

至少一条两 batch trace要求 batch 1创建 output net，batch 2以 `CreatedNetRef{batch1 token, role=output-net}` 作为 `original_net` 再次分裂，验证 new→new resolver、reverse和append-only slot。

## 7. Fixed trace schema

两个正交字段固定为 `selection_mode=fixed_trace` 与 `semantic_workload_kind=synthetic|real_design`。可回放公共头必须携带首写前校验和结果分型所需、但不泄露 selector operand 的字段；Artifact在C++与JSON都使用严格 tagged union：

```cpp
struct ReplayHeader {
  std::uint32_t schema_version;       // v1 == 1
  SelectionMode selection_mode;       // fixed_trace
  SemanticWorkloadKind workload_kind; // synthetic | real_design
  ProfileId profile_id;
  ComparabilityStatus comparability_status;
  std::optional<ComparabilityReason> comparability_reason;
};
struct SyntheticArtifactRecipe {
  TechLefRecipe tech_lef;
  CellLefRecipe cell_lef;
  LibertyRecipe liberty;
  VerilogRecipe verilog;
  SdcRecipe sdc;
  std::string top;
};
struct SyntheticReplayPayload {
  SyntheticArtifactRecipe source_recipe;
  std::vector<DesignEditPlan> batches;
};
struct RealReplayPayload {
  SourceArtifactRefs artifacts;
  BaselineSemanticIdentity baseline;
  std::vector<DesignEditPlan> batches;
};
using ReplayPayload = std::variant<SyntheticReplayPayload, RealReplayPayload>;
struct ReplayProgram {
  ReplayHeader header;
  ReplayPayload workload;
};
struct BufferTraceArtifact {
  ReplayProgram replay;
  GenerationReceipt generation_only;
  IntegrityReceipt integrity;
};
```

JSON用 `ReplayProgram.workload` discriminator + `oneOf`，每层 `additionalProperties:false`，并交叉验证 header `workload_kind` 与 payload alternative 一致。replayer API只接收 `ReplayProgram` 投影，类型上看不到 selector operands、gain/slack/load receipts或expected timing答案；`GenerationReceipt`可保存这些生成证据，但修改它不得改变replay结果。`schema_version/profile_id/selection_mode/comparability` 只来自 replay-safe header；generation-only receipt 不得覆盖它们。功能验收比较canonical objects/timing，integrity hash只确认读到同一冻结artifact。

### 7.1 Synthetic variant

`SyntheticArtifactRecipe` 只描述生成source artifacts所需的tech layer/site、cell macro/pin、Liberty cell/pin/table、模块拓扑、时钟约束与top name，不保存原生 Database、derived graph或任何 timing结果。schema与C++类型都必须有五个不可省略、不可互换的named roles：`tech_lef/cell_lef/liberty/verilog/sdc`。每次fresh replay都在该one-shot probe独占的唯一临时目录中确定性生成五个不同regular files；尤其 `tech_lef` 与 `cell_lef` 必须是内容和canonical path均独立的两份LEF，禁止把同一路径重复填入两个loader slot。把五个路径与top投影为 `FreshBaselineArtifacts` 后交给与real payload完全相同的 production loader；全部artifact必须活到loader callback结束，进程产生值语义receipt后才能清理。loader负责真实 parse/elaborate/GraphBuilder/native full/CSR full，synthetic不得调用直接 Database factory。

v1拒绝 arbitrary net-result matrix、arrival/slew/load/required/slack答案、lookup答案、预制CSR row/FIFO、直接 `CsrReferenceInput` 或 serialized Database 注入。recipe只允许可由五件source files表达的输入；至少一条两 batch trace覆盖 old→new/new→new。测试逐一破坏/缺失五种artifact并把两份LEF故意alias，必须在callback前得到typed materialization/load rejection，而不是退回canned baseline。
实际负例精确为五个role逐一使用missing path，加一例cell LEF symlink canonical-alias到tech LEF，共六个独立fresh process；相同字符串路径alias由C++ contract与JSON/schema层拒绝。两类alias均不得进入loader work，且五件原始source的path、size与exact bytes保持不变。

### 7.2 Real-design variant

`RealReplayPayload`只保存source artifacts、baseline identity与semantic edits。其构造器与JSON交叉验证必须把 replay-safe header 精确限定为 `comparability_status=non_comparable`、`comparability_reason=engineering_rc_no_physical`；缺失、不同reason或伪称 `exact/protocol_only` 一律在首写前拒绝，不在payload中复制第二份可冲突字段。因为 Stage 3 `DesignEditPlan` 的 typed contract 必含环境分型，每个 real replay batch 必须精确写入无参数标签 `rc_inputs=NoParasiticRcInputs{}` 与 `placement_inputs=UnplacedInputs{}`；二者只声明 native no-parasitic/unplaced 语义，不含 selector 数值。Stage 4成功fixture固定 `parasitics=absent`，每批CSR export的 `unsupported_reasons.empty()`；Liberty与pin capacitance负责实际load/cell delay/slew重算。`Rupstream/Rbuf/operating_point` 数值仅在 generation receipt 中驱动 Elmore 选择，绝不进入 replay program 或 timing 模型。真实parasitic输入精确走Stage3 `full_with_record`、不发布且不冻结为成功trace。

## 8. Generator

`ista_buffer_trace_runtime` 中的 generator只在generation阶段使用唯一CPU/full observation：

1. fresh baseline full；
2. `NativeBufferObservationExtractor`按§5生成候选；
3. selector按profile top-k与固定全序选择；
4. 生成Stage3 `DesignEditPlan`；
5. isolated candidate中full recompute并发布；
6. 保存semantic edit与generation-only receipt；
7. 若未达到stop condition，下一round从已发布结果重新观察。

profile逐项冻结 `top_k/rounds/max_total_insertions/operating_point/rc_profile`；每round后必须full重算。空accepted batch、达到rounds或总插入上限分别记录稳定stop reason。generator与replayer都只能通过 `FreshBaselineRunner::withFreshBaseline` 进入fresh基线，synthetic generation同样先生成tech LEF、cell LEF、Liberty、Verilog、SDC五件source artifacts并走production loader。冻结后replayer不运行selector。生成成本分列baseline init/native full/enumeration/selection/apply/full，只报告成本，不宣称增量speedup。

`empty_accepted_batch` 只有在此前已经形成至少一个非空batch时，才能作为正常 `GenerationReceipt` 的终止原因。若首轮即无accepted candidate，则没有可冻结或回放的artifact；generator必须在任何plan apply、native execute或publish之前抛出 `BufferGenerationError{kInvalidArtifact}`，稳定诊断为 `empty_accepted_batch: no replayable batch was generated`。该失败不得构造zero-batch `ReplayProgram`。

## 9. Replayer

```cpp
struct PendingVerifiedBatch;

class BufferReplayContext final {
 public:
  BufferReplayContext(const BufferReplayContext&) = delete;
  BufferReplayContext& operator=(const BufferReplayContext&) = delete;
  BufferReplayContext(BufferReplayContext&&) = delete;
  BufferReplayContext& operator=(BufferReplayContext&&) = delete;

 private:
  friend class BufferTraceProductionFreshAdapter;
  friend ReplayReceipt replayTracePrefix(BufferReplayContext&,
                                          const ReplayProgram&,
                                          std::size_t);
  // Stack-only, non-owning references to the guarded session/context/authority,
  // Database, coordinator and CSR input; construction is callback-local only.
  BufferReplayContext(/* guarded non-escaping view */);
  ~BufferReplayContext();
  // Adapter-bound synchronous callable proves CSR full exactness, then moves
  // the opaque proof directly into VerifiedPublishBundle and publishes.
  void proveSealAndPublish(PendingVerifiedBatch&& pending);
};

using BufferReplayWork
    = std::function<ReplayReceipt(BufferReplayContext&)>;

class FreshBaselineRunner {
 public:
  virtual ~FreshBaselineRunner() = default;
  virtual ReplayReceipt withFreshBaseline(
      const ReplayProgram& program,
      BufferReplayWork work) = 0;
};

ReplayReceipt replayTracePrefix(BufferReplayContext& context,
                                const ReplayProgram& program,
                                std::size_t last_batch);
```

`withFreshBaseline(program, work)` 是唯一生命周期入口，不返回 owning context。`FreshBaselineRunner` 只定义 Stage 4 自有 callback接口，不引用 Stage 3 test类型；当前阶段由 Stage 4 test executable中的 `BufferTraceProductionFreshAdapter` 实现。adapter为synthetic生成五件临时source artifacts或读取real refs，然后调用 production fresh loader；loader成功进入callback后，它先核对五项artifact evidence与generation-zero baseline identity，调用 `StaTimingEditSessionProbeAccess::captureSnapshotForTesting` 后立即 `releaseSnapshotForMutation`，取得 `stateSignal(view.session)`，构建generation-zero host snapshot/resolver，并在callback栈上创建 `TimingEditCoordinator`。随后它构造stack-only、不可复制、不可移动、constructor/destructor均非public的 `BufferReplayContext`，同步且恰好一次调用work，不保留work，并在callback返回前按逆序销毁context/coordinator；artifact物化或loader失败时work调用零次且不构造两者。

context只借用同一fresh session的coordinator、analysis context、transaction generation、Database、CSR input/runner与 `NativeExecutionAuthority`；禁止heap factory、`unique_ptr<BufferReplayContext>`、缓存authority、返回reference/span/pointer，或经callback捕获、全局保存等方式把context及其borrow带出guard。每批native full后，replayer只能调用context的private同步 `proveSealAndPublish`：由adapter在test `.cpp` 中绑定的guarded callable调用 `StaTimingEditSessionProbeAccess::proveCsrFullExact(authority, host_snapshot, database, target_generation)`，不返回opaque move-only `CsrFullExactReceipt`，而是在同一调用栈立即把它move进 `VerifiedPublishBundle` 并调用 `coordinator.publish(authority, ...)`。异常路径在guard内rollback/poison；context与 `ReplayReceipt` 均不得拥有、缓存或序列化proof。runtime library只看到Stage 4自有的private callable边界，不include、不引用、不链接三个Stage 3 test seam。

精确调用链为 `FreshBaselineRunner::withFreshBaseline(program, work)`（adapter override）→ five-artifact materialization → `ProductionFreshSessionLoader::run(artifacts, callback)` → baseline capture/release + `stateSignal` + stack coordinator/context → `work(context)` → private `proveSealAndPublish`。work调用 `replayTracePrefix`，使prepare→translate→execute→build host snapshot→full CSR proof→seal→publish全部发生在同一callback/authority生命周期。若现有loader或probe API不能满足这条边界，Stage 4停止并报告Stage 3前置不闭合，不得修改Stage 3 core或通过新增Stage 3 test friend扩大权限。synthetic与real必须使用这一个adapter，不得各自实现session/bootstrap/proof路径。

### 9.1 One-shot fresh process边界

`BufferTraceProductionFreshProbe.cpp` 是一次性CLI：一次启动只接受一个完整generator命令，或一个 `(trace, cumulative_prefix, repetition)` replay命令；二者不可在同一进程组合。正常命令只构造一个adapter并调用一次 `withFreshBaseline`，adapter源码中也只有一个 `ProductionFreshSessionLoader::run` call site。进程先在callback内完成全部批次，再把不含borrow/proof的值语义功能receipt与独立run envelope写出并退出。

adapter维护process-local one-shot状态 `unused→entered→finished`：第一次调用在进入artifact materialization前原子占用；同进程第二次调用必须在接触artifact、IDM、STA或loader之前返回typed `fresh_process_reuse_rejected`，不能尝试“清理后再用”。专门的 `--self-test-double-invocation` 在第一次成功后发起第二次调用，断言typed rejection且loader invocation count仍精确为1。inventory/depfile检查保证probe中不存在绕过adapter的第二个loader call site。

`buffer_trace_controller.py` 是唯一多次运行编排者。每个完整generator run启动一个全新probe进程；对每个replay cumulative prefix，三个fresh证据分别启动三个互不复用的probe进程并逐字段比较三份功能receipt，因此“3次fresh”等于“3个进程”，不是同一进程三次调用loader。每个child独占临时artifact/run目录，父controller只接收退出状态和值语义输出。`child_pid/loader_invocation_count/one_shot_state` 只进入noncanonical run envelope：controller要求三个PID互异且count均为1，但这些process-local字段不进入trace、功能receipt、canonical equality或integrity hash。

这里不宣称 `ProductionFreshSessionLoader::run` teardown了全局IDM/DataManager。现有loader会close `IncrementalStaSession` 并destroy `STAInterface`，但没有可依赖的IDM/DataManager reset合同；fresh隔离的权威边界是child process退出。任何把同进程第二次load、手工singleton reset或仅更换session token当作fresh证据的实现都不合格。

固定顺序：首写前从 `ReplayHeader` 核对schema/selection mode/profile/workload/comparability、再核对source/baseline identity；进入callback-scoped context；逐批解析StableRef/token；交给Stage3 translator；验证reverse一删一增与parallel唯一；isolated native CPU/full；重新export并运行CSR full；逐字段比较topology/electrical/timing；在guard内通过Stage3 publish或rollback/poison；仅返回prefix/generation/op counts、功能观察值以及原样来自 replay-safe header 的comparability/reason/replay command。context token/generation mismatch在首写前typed reject。

Stage 4只运行CPU/full execution mode与CSR full correctness oracle。`cpu/incremental`、`gpu/full`、`gpu/incremental`请求typed reject；不做closed-loop多模式优化。

## 10. 真实 fixture 与 source isolation

新增独立 high-fanout combinational fixture，五件source artifact固定为不同路径的tech LEF、cell LEF、Liberty、Verilog、SDC；可复制冻结 `stage0.lib` 中 `BUF_X1`、`OR2_X1` 语义和既有tech/cell LEF内容，但不得修改阶段2 manifest/fixture，也不得用同一个LEF路径兼任两种role。fixture包含一根驱动至少4个不同 `OR2_X1` data input pin的data net，其余OR2输入由合法独立信号驱动；`parasitics=absent`。OR2 input cap、BUF input cap、BUF timing table与版本化 `Rupstream/Rbuf` 必须让§5.2的实际 `CsrTableLookup` 计算得到稳定正gain，测试运行时重新计算并断言正值，不保存或硬编码expected gain。该结构还必须产生非平凡Liberty+pin-cap load/delay/slew变化。每批CSR export必须supported且`unsupported_reasons.empty()`；遇真实parasitic只产出`full_with_record`失败receipt。

production loader进入callback后，以 `dmInst->get_idb_design()` 作为必须存在的权威 primary IDB；若其为空，立即 typed fail。`dmInst->get_netlist_idb_design()` 只作为可选 logical/netlist view，不能代替 primary IDB，也不能作为 source-unchanged 的唯一证据。guarded generation/replay前后分别比较 primary IDB 的 design name、instance name/master/type/status/orient/location、instance/IO pin direction 与 pin→net、net type/driver/sorted loads、完整 wire/segment/layer/point/via/rect 投影及对象/连接/placement/wire计数；optional view 若存在也按同一投影比较，并要求 `spef_reader_present=false`。同时逐字段比较 isolated iSTA `Database` closure、host CSR/source identity，以及五件 input artifact 的 role、logical name、canonical path、size 与 exact bytes。这里不宣称存在单独的“完整 EngineDB projector”，也不以 pointer identity 或 hash 代替上述功能比较。

同时比较输入artifacts bytes/metadata和fixture目录inventory。哈希只附带，不替代结构投影与byte equality。任何 `fix_fanout`、layout edit、create/connect/disconnect/remove/save/write DEF调用均失败。

`comparability_status` 严格属于 `{exact, protocol_only, non_comparable}`。本真实fixture固定 `non_comparable`，另记 `comparability_reason=engineering_rc_no_physical`；工程R仅用于selector近似，STA timing模型来自Liberty+pin cap，二者差异在报告中明确。

## 11. Correctness tests

### 11.1 Selector

- input permutation、exact tie、stable bytes order、top-k/rounds/stop reason；
- scalar max/setup slack抽取、single-sink moved set、buffer恒等功能legality；
- arrival/required/slack 三者 materialized 检查、默认零 slack 排除、native `required-arrival` 舍入一致性与稳定 rejection reason；
- kΩ/pF/ns单位、逐步求值、positive/`±0`/negative/NaN/Inf/overflow；positive fixture必须调用实际 `CsrTableLookup`、逐字段核对operands并计算断言 `gain > +0.0`，不得比较硬编码gain；
- accepted跨net顺序、冲突整批reject、real seed=0与synthetic fixed seeds。

### 11.2 Schema/identity

- strict version/unknown field、Stage3 CreationToken/StableNetRef复用；
- dense ID/native rank/pointer拒绝；token collision/前向引用/baseline mismatch；
- C++ variant/JSON oneOf；synthetic recipe每次生成不同canonical path的tech LEF、cell LEF、Liberty、Verilog、SDC并由production loader成功物化，缺失任一role或两LEF alias都typed reject；real header只能是`non_comparable/engineering_rc_no_physical`；
- replay projection不含generation-only operands或expected timing答案；
- synthetic schema/constructor拒绝Database/CSR/FIFO与arrival/slew/load/required/slack/table-lookup答案；
- 篡改GenerationReceipt的gain/slack/load证据不改变replay结果；
- manifest identity与可重复canonical serialization。

### 11.3 Replay

- synthetic source-artifact micro与two-batch created-net→created-net；synthetic/real经同一个production loader adapter；real high-fanout至少4个OR2 input loads且no-parasitic；
- 每个cumulative prefix由controller启动至少3个独立one-shot probe进程，逐字段证明三次fresh process/session解析等价edits；
- 每批native CPU/full与CSR full的reference input、topology、adjacency、electrical closure、timing result逐字段一致，CSR `unsupported_reasons.empty()`；每个fresh replay还逐字段比较committed identity、cumulative semantic trace、resolver、raw Database closure与host CSR；
- context copy/move/heap construction必须编译期失败；adapter测试证明baseline capture/release、`stateSignal`、coordinator、work与private proof→bundle→publish均位于loader callback/单一guard内，callback返回后无authority/context/receipt borrow存活；
- one-shot self-test证明同进程首次调用只触发一次loader，第二次在loader前得到`fresh_process_reuse_rejected`；controller测试证明三次fresh使用三个child PID且每个noncanonical run envelope记录的loader invocation count均为1；
- real run先故意破坏derived timing字段（不进入Stage3 `Poisoned` session状态），再full rerun恢复，证明无canned answers；
- 真实parasitic精确`full_with_record`且零发布；reverse一删一增及out-of-contract policy；
- 首轮空选由production probe的负gain路径触发，在callback内证明typed `kInvalidArtifact`、coordinator仍为Idle、generation为0、累计batch为空、session write/native execute/publish均为0且source identity/Database逐字段不变；已有batch后的terminal empty仍必须保存并核对该轮numeric evaluation；
- source EngineDB/IDB、physical checkpoint与artifacts exact unchanged；失败trace一条命令重放。

### 11.4 Property

固定 seeds `1, 7, 42, 20260831, 0xdeadbeef` 只驱动测试端 selector candidate input permutation；selector本身没有随机ranking分支。对每个 seed，原序与置乱输入的selection必须逐字段相同；跨 seed 的 accepted语义顺序与完整evaluation receipt相同，CreationToken只有契约规定的seed字段随输入变化、其余字段一致。DAG/rollback 与 fault injection 由 Stage 3 定向回归和 Stage 4 parasitic boundary 覆盖，multi-batch token 与 `CreatedNetRef` 由 deterministic contract/replayer/production-controller 覆盖；不得把这些 deterministic cases 记作 property-seed 覆盖。随机覆盖服务于语义边界，不搜索特定 hash。

## 12. CTest 与隔离门禁

新增：

- build-only helper `ista_buffer_trace_production_fresh_probe` — 仅由下列controller/self-test启动，不作为可复用library；
- `ista_buffer_candidate_selector_test` — `ista_unit`；
- `ista_buffer_trace_contract_test` — `ista_unit`；
- `ista_buffer_trace_observation_extractor_test` — `ista_unit`；
- `ista_buffer_trace_parasitic_full_boundary` — `ista_unit`；
- `ista_buffer_trace_schema_validation` — `ista_unit`；
- `ista_buffer_trace_fixture_manifest` — `ista_unit`；
- `ista_buffer_trace_replayer_test` — `ista_unit`；
- `ista_buffer_trace_property_seed_*` — `ista_property`；
- `ista_buffer_trace_stage4_inventory` — `ista_unit`；
- `ista_buffer_trace_controller_selftest` — `ista_unit`；
- `ista_buffer_trace_one_shot_reuse_reject` — `ista_integration;ista_cpu`；
- `ista_buffer_trace_first_empty_generation` — `ista_integration;ista_cpu`；
- `ista_buffer_trace_terminal_empty_generation` — `ista_integration;ista_cpu`；
- `ista_buffer_trace_preloader_rejection` — `ista_integration;ista_cpu`；
- `ista_buffer_trace_fresh_process` — `ista_integration;ista_cpu;ista_smoke`；
- `ista_buffer_trace_source_isolation` — `ista_integration;ista_smoke`；

实际注册20个unique Stage 4 CTest；label统计为14个unit、5个property、6个integration、2个smoke，label可重叠。production probe仅为build-only helper，不直接注册CTest。

Inventory/object/depfile/nm 门禁：pure contract不可见 Database/STAInterface/IDM/iZH/pybind/CUDA；runtime/replayer不可见三个Stage3 test seam及Stage2 native materializer，且不可见 EngineDB/IDB mutation symbol或 `izh_fanout_fixer`；只有exact-inventory的 `ista_buffer_trace_production_fresh_probe` executable可复编这些test sources并只读加载IDM。probe源码必须只有adapter内一个loader call site，禁止 create/connect/disconnect/remove/save；controller只spawn probe，不链接C++ runtime/test seam。Stage 4 diff不得包含Stage 3 core/transaction/receipt/session probe或其CMake文件。每个新增文件必须严格少于 700 物理行，Python只用stdlib，不改 flake/lock/第三方依赖。

验收判定先看功能证据：同一prefix在至少3个独立one-shot child process/session中的resolved edits、raw Database closure、host CSR、CSR reference input和CPU/full↔CSR full timing必须逐字段一致，并证明source artifacts/EngineDB/IDB不变；controller另从noncanonical run envelope断言PID互异且每个child的loader invocation count为1。hash只能标识本次读取的是哪组冻结artifact、帮助定位报告；hash相等不能替代任一功能比较，hash不同也不能被碰撞搜索或自定义归一化“修复”。

回归顺序：

1. `ctest -R '^ista_buffer_' --output-on-failure`；
2. Stage 3 `^ista_timing_edit_`；
3. Stage 2 `^ista_csr_`；
4. iSTA unit/property/integration/smoke labels；
5. controller显式启动每prefix三次one-shot fresh replay，并运行source isolation与same-process reuse reject；CTest `--repeat`仅作稳定性回归，不计作fresh独立性证据；
6. parent 12 个 STA 定向 pytest；
7. parent non-PDK 全量。

最终as-built结果：

| 门禁 | 结果 |
|---|---|
| Stage 4 `^ista_buffer_` | 20/20 PASS |
| Stage 4 unit/property/integration/smoke | 14/14、5/5、6/6、2/2 PASS |
| Stage 3 `^ista_timing_edit_` | 16/16 PASS |
| Stage 2 `^ista_csr_` | 74/79功能与真实流程通过；4项旧对象dep记录缺失、1项旧全局CTest数量冻结单列 |
| parent 12个冻结STA pytest | 227/227 PASS |
| parent non-PDK | 1665 passed、8 skipped、4 deselected、13 xfailed、2 warnings，无失败 |
| 独立代码审查 | `APPROVE`，无blocker/major/minor |

Stage 2五项静态门不作为功能失败隐藏或改摘要绕过；binding contract在匹配构建时Python 3.11 runtime后通过，real differential fresh-process等真实路径通过。详细证据见 `stage4-report.md`。

## 13. 交付报告与冻结信息

`stage4-report.md` 必须报告：

- paper rule 与 engineering rule逐项对照；
- synthetic/real traces、seed/profile与 comparability status；
- 每批 nets、buffers、moved sinks、semantic op counts、reverse contract；
- native/CSR/fresh replay逐字段 equality；
- one-shot child PID、每child唯一loader调用与same-process第二次调用typed rejection证据；
- real load/delay/slew重新计算证据；
- source EngineDB/IDB与physical checkpoint不变证据；
- trace integrity hash仅作为artifact identity辅助，正确性结论引用逐字段功能equality与fresh replay证据；
- fresh replay成本，不做增量性能结论；
- 阶段 5–9 使用的冻结 trace paths与schema version。

阶段 4 单独闭环：child实现/测试提交；parent只提交gitlink、`stage4-detailed-plan.md`、`stage4-report.md`与总体计划状态更新；排除用户既有文件，不push。

## 14. 实施步骤与停止条件

1. [完成] Stage 3 完成并冻结 typed contract/native transaction/fresh oracle；
2. [完成] 冻结 selector numeric/tie/legality与 trace tagged union；
3. [完成] 独立设计审查 `APPROVE`；
4. [完成] 实现 pure selector、canonical encoding与schema；
5. [完成] 实现五件artifact的synthetic multi-batch generator/trace；
6. [完成] 新增 real high-fanout fixture并生成 semantic trace；
7. [完成] 实现exact-inventory one-shot probe、private CSR proof消费、replayer、三进程controller与source isolation；
8. [完成] 完成定向/Stage3/Stage2/parent回归与独立代码审查；
9. [完成] 冻结 traces并更新报告/总体计划；child与parent按阶段边界创建本地提交，不push。

全部停止条件已以functional fields、typed lifecycle、fresh processes与source unchanged闭合。Stage 2五项历史静态门按第12节如实记录；没有通过修改旧hash或冻结计数掩盖。

以下任一存在时不得宣告阶段 4 完成：Stage 3前置未通过；Stage 4修改Stage 3 core；runtime看见test seam/materializer；probe source/link inventory不精确；baseline capture/release、`stateSignal`、coordinator或opaque proof消费离开loader callback/guard；authority/context/receipt逃逸；synthetic没有生成不同路径的tech LEF、cell LEF、Liberty、Verilog、SDC，绕过production loader或注入Database/CSR/timing答案；同一进程第二次调用loader未在调用前typed reject；把loader close/`STAInterface` destroy误称为IDM/DataManager teardown；三次fresh不是三个child process；调用 iZH/IDB写路径；real payload不是`non_comparable/engineering_rc_no_physical`；positive gain未由实际 `CsrTableLookup` 重算；real high-fanout少于4个OR2 input loads；selector/replayer混在一起；creation token不稳定；fresh process语义不一致；每批未比较native/CSR的结构、电气和timing；source物理状态未逐字段证明不变；reverse非一删一增；只以hash作为正确性结论；closed-loop多模式优化混入fixed trace。
