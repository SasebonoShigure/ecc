# ECC IncreGPUSTA 阶段 2 详细实施计划

> 2026-09-08 冗余清理：受控 levels 的完整证明归属生成路径；任意外部 levels 仍完整验证。 详见 [清理报告](stage0-6-redundancy-cleanup-report.md)；以下阶段验收数据继续表示历史结果。

> 当前开发协议补充（开发检查分离）：实际快照、scatter、失效身份与公共输入校验始终保留，已受控对象的重复扫描与深拷贝归 ON。 后续改动必读 [开发检查规范](development-guidelines.md)，双模式实测与历史验收的区别见 [本轮实施报告](debug-checks-implementation-report.md)。原阶段验收数字保留为历史记录。

> 状态：实施中；步骤 1–8 已本地完成并通过最终门禁/代码复审，Step 9 v0.15 exact bytes已冻结并正在同一SHA双审
> 实施进度：步骤 1–8 见 [stage2-report.md](stage2-report.md) 与各step计划；Step 8 v0.14见 [stage2-step8-plan.md](stage2-step8-plan.md)，SHA `604dd5427d2ba1003ff4e22ae0ab3e5760148331fd1fcebf1e33ae2d9c402be2`；Step 9 v0.15 review candidate见 [stage2-step9-plan.md](stage2-step9-plan.md)，SHA `c6aa9a71c942fc5f6a217c33d5649560b61018d4699723963d105b969c78c598`；v0.5 SHA `ff7b3e91fc3cca4ee6a0aec414650c2a3cc61afa92bd96bfc38dd21ae4224054` 仅为历史编码前基线
> 已批准设计基线：总计划编码前复审 SHA-256 为 `052ae59be69c4ad097d716d279275d19b75940ca07567e481f565d95b9f7aa64`；Step 3 v0.4 为 `188d1184ec0e16f62339c484df515aed08fe5e722fc32fc1f308adcb44e2b050`；Step 5 v0.2为 `d8850b74cd6995f1f050efbda0e0ed08d2c930ace1163690a105995cdc15112b`；Step 6 v0.7为 `d36e4831626093b8a12813ac2053bdd0a6baae4b77c22ebefed2ecfd94804daa`；Step 7 v0.3为 `2996e2d8f558c7707290e7978fc9b6a1f0ce5f4ba680f201083b0829c5627313`；Step 8 v0.14为 `604dd5427d2ba1003ff4e22ae0ab3e5760148331fd1fcebf1e33ae2d9c402be2`
> 当前进度：Step 8 as-built exact 4/4、CSR 79/79、global unit/property/smoke 87/20/7、Stage0/1与parent non-PDK均通过，设计/代码/全局修复独立复审全部`APPROVE`；owner行数为维护性建议。Step 9 v0.15 candidate SHA `c6aa9a71c942fc5f6a217c33d5649560b61018d4699723963d105b969c78c598` 正在双审，尚未运行或实现
> 基线：parent `ee2563b2d27165d9324d82103cdf28bddb414956`，ecc-tools `a7355b216b801f72a99d92e77765f49c744148b3`
> 分支：parent 与 ecc-tools 均为 `IncreGPUSTA`
> 范围：Native ↔ CSR/SoA、稳定语义 ID、generation/fingerprint、独立 CPU/full CSR reference、受控 scatter；不实现 mutation、Dual-CSR 或 CUDA

## 1. 阶段目标

阶段 2 在现有 `ista::Database` 与后续 CPU/GPU 增量算法之间建立一个显式、可验证的数据转换层。它必须能把当前 session 的 timing graph、传播输入和 timing 状态转成拥有自身生命周期的 CSR/SoA snapshot，使用纯 CSR CPU backend 从不可变输入重新执行全图 levelization、正向传播和反向传播，再把结果按严格 allow-list 写回当前 Database。

本阶段要证明的是数据边界和全量 CSR reference 正确，不是增量性能。`cpu/incremental` 在没有 mutation 时仍返回阶段 1 的 `baseline_only` 10 字段 execution record；CSR capture、reference 验证或 scatter 都不允许把它改写成 `incremental_update`，也不得报告 speedup。

## 2. 非目标与禁止事项

本阶段明确不做：

- 不接受 edit batch，不修改 netlist、Pin、Instance、Net 或 Arc 拓扑；
- 不实现论文的 Dual-CSR insertion/update、混合子图 levelization 或 affected-cone propagation；
- 不添加 CUDA target、device allocation、kernel 或 GPU 性能数字；
- 不把 `STAInterface::updateTiming()` 冒充增量 STA；
- 不重构整个 iSTA Database；只在 CSR reference 前导出、计算后受控回写；
- 不改阶段 1 固定 10 字段 `StaExecutionRecord`，不改 benchmark schema v1；
- 不用现有 arrival、slew、graph delay、required 或 level 作为 reference backend 的计算输入；
- 不为尚未发生的 grow/rebuild/invalidation 伪造 telemetry；
- 不让默认 `cpu/full` 承担 CSR 转换的时间或内存开销。

## 3. 已核验的现状

### 3.1 Canonical owner 与生命周期

iSTA 没有独立的 `TimingGraph` 类。canonical owner 是 `DataManager` 按值持有的 `ista::Database`：

- `pin_map` 和 `timing_point_map` 持有节点语义与 timing result；
- `arc_list` 按值持有 Arc；outgoing/incoming adjacency 保存 `arc_list` 的 vector index；
- `timing_order_list`、start/end point list 和 TimingPoint level 由 GraphBuilder 生成；
- TimingLibrary、TimingConstraint、ParasiticLibrary 与 Instance/Net 同样属于当前 Database；
- DataManager 在 session initialize/close 中创建和销毁，因此任何 CSR handle 只能属于当前 session。

GraphBuilder rebuild 会清空并重建 Arc vector 和 adjacency。Arc 还保存指向 TimingLibrary 内部对象的 raw `TimingCellArc*`。因此 vector index、地址和 raw pointer 都不能作为稳定 ID，也不能跨 graph rebuild、library reload、corner 或 session 保存。

### 3.2 Native 传播语义

当前 full pipeline 的相关顺序为 GraphBuilder → ClockPropagator → TimingPropagator → TimingAnalyzer。需要保持的关键差异包括：

- levelization 忽略 disabled/loop-disabled arc，root level 为 1；
- data arrival 还会停止在进入 sequential clock pin 的 net arc；
- data slew 的停止条件与 arrival 不完全相同；
- clock propagation 有独立的 clock-point、physical/effective state 和 eligibility；
- cell delay/output slew 由 input slew、output load、transition sense 和 Liberty table 动态计算；
- no-SPEF net arc 的 delay 为 0，slew 透传；
- scalar arrival 使用初始化后的 `Arc::delay`，path state 使用 analysis/input/output transition 对应的动态 graph delay；
- path state 维度为 analysis × input/register source × rise/fall × launch-clock tag；
- endpoint required 可能依赖 output delay、clock period/arrival、timing-check LUT、data/clock slew 和 CRPR。

因此仅导出 native 最终 graph delay 或 sink slew，再写回相同值，会形成 false-green，不能称为 CSR full reference。

### 3.3 阶段 1 接口约束

阶段 1 的 Python/C++ execution record 都严格校验 exact 10 keys。native session public state 也固定为 created/initialized/baseline_executed/poisoned/closed。阶段 2 使用独立的 snapshot identity/observation 和内部 CSR substate，不扩充 execution record，也不增加顶层 session state token。

legacy 与 typed session 共用 `STAInterface` owner lease。CSR export/scatter 必须经过相同 session token gate，不能从 pybind 或新 singleton 绕过 owner 检查。

## 4. 阶段 2 数值支持边界

### 4.1 Graph round-trip 支持

导出、decode 和结构 round-trip 必须保存全部节点、全部 parallel arc，以及 disabled、loop-disabled、clock arc。结构导出不因 CPU reference 暂不支持某种数值语义而丢边。

### 4.2 `CsrCpuReferenceBackend` 首版支持集

首版 reference 对下列输入执行完整全图计算：

- 有向无环的 combinational timing graph；
- no-SPEF net，net delay 为 0、slew 透传；
- Liberty scalar/1D/2D delay 和 transition table，完整复现当前 stored enum 的 `kNone` native default、input transition、output capacitance 与 constrained transition；
- positive-unate、negative-unate 与 non-unate transition relation；
- cell output load，由 downstream input-pin capacitance 与 output-port `set_load` 计算；
- max/min × rise/fall；
- input-port startpoint、`set_input_delay`、`set_input_transition`；
- output-port endpoint、`set_output_delay` 与关联 ideal clock period；
- 没有图 fanout 的 ideal clock source；
- parallel、disabled 与 loop-disabled arc 的存储和 eligibility；
- scalar arrival/predecessor/launch/clock、data slew、input path state、scalar required/slack；
- Arc 初始化 delay map、动态 graph delay map 和 per-library-timing-arc delay map。

对 supported input，backend 必须计算完整 graph，不接受 affected-node 子集。

### 4.3 首版必须 typed reject 的语义

失败分为四个互不混用的 typed 层级；各层 enum token 和 reason set 都按下列声明顺序稳定排序、去重：

- `CsrCaptureCode`：`malformed_topology`、`semantic_key_collision`、`illegal_numeric`、`invalid_table_shape`、`invalid_analysis_context`、`active_cycle`；失败时没有 committed snapshot；
- `CsrReferenceUnsupportedReason`：`parasitic_net`、`sequential_instance`、`sequential_launch`、`timing_check`、`crpr`、`propagated_clock`、`clock_tree_fanout`、`clock_gating_or_divider`、`conditional_timing_arc`、`case_analysis`；graph/encoding 有效，snapshot 仍可用于结构 round-trip；
- `CsrComputationCode`：direct/synthetic core input 仍可返回 `cycle`、`invariant_violation` 或 `numeric_failure`；没有 result。production capture 会把同一 Kahn 的 `cycle` 映射为 `CsrCaptureCode::active_cycle`，不会 commit snapshot；
- `CsrScatterCode`：`success`、`invalid_state`、`snapshot_invalidated`、`schema_mismatch`、`session_mismatch`、`generation_mismatch`、`source_identity_mismatch`、`shape_mismatch`、`result_numeric_invalid`、`id_mapping_mismatch`、`predecessor_mismatch`；所有非 success 都携带 `writes_applied=0`。

上述四组是互相独立的 enum/result 类型。`invalid_state` 包括 snapshot 尚未建立或 session 已关闭；它不写 observation event。`snapshot_invalidated` 另携带 `CsrInvalidationReason`，其余 scatter reject 才可形成 `last_rejection`。不得把这些 token 塞进 Stage 1 的 `StaSessionStatusCode` 或 fallback/capability reason。

Step 5的`CsrComputationResult`只作为transport wrapper，其`outcome`精确为`variant<CsrTimingResult,CsrReferenceSupportResult,CsrComputationCode>`；SupportResult仍是独立typed alternative。compute唯一优先级为malformed/intrinsic shape→invariant、valid unsupported→exact SupportResult、supported FIFO incomplete→cycle、post-FIFO checked internal shape/state→invariant、实际算术非法→numeric、否则detached timing result；unsupported与cycle overlap必须support-first。validator只验证该表中外部可判定的分支，不重算backend数值算法。

以下任一存在时，结构 round-trip 仍可运行，但数值 reference 必须在修改 Database 前返回 `CsrReferenceUnsupportedReason`：

- SPEF/parasitic net、RC waveform、ceff 或 Arnoldi/DMP；
- sequential instance、C2Q、setup/hold/recovery/removal、register path source 或 CRPR；
- propagated clock、clock-tree fanout 或 clock gating/divider；
- `sdf_cond` 非空的 conditional/SDF timing arc，或已编码的 case-analysis constraint family；

NaN、非法 infinity、坏 table shape、semantic-key 冲突属于 capture invalid。production capture 在 commit 前执行 pure Kahn，未被 loop-disabled mask 消除的 cycle 精确映射为 `active_cycle`、无 record/snapshot/observation；`CsrComputationCode::cycle` 只保留给未经过 production capture 的 direct/synthetic core input。二者都不得伪装成 unsupported。

当前 canonical model 只有 `sdf_cond`，没有可靠的 SDF-origin discriminator；因此不声明独立 `sdf_timing_arc` reason，非空条件统一映射`conditional_timing_arc`，无法识别的来源不伪造 telemetry。当前 `TimingTableVariableType` 也只保存`kNone`和上述三种已支持值，raw未知/缺省来源在wrap时已折叠为`kNone`；reference精确复现native对全部stored enum的行为，不声明不可达的`unsupported_table_variable`。每个保留的unsupported reason和多reason overlap都必须有detector fixture，验证声明顺序、去重和零写入。任何失败都不允许回用native最终值，阶段报告必须逐项列出实际reason。

`clock_tree_overlap`和`multi_driver`不属于capture后的CSR unsupported：现有full pipeline分别在ClockPropagator和GraphBuilder中通过`STALOG.error`于capture前终止进程，无法返回snapshot/reason。阶段2不伪造typed result，也不改变该既有cpu/full行为；两类负例只允许在独立子进程中验证“无record/snapshot/observation/成功标记”，controller即使看到既有`exit(0)`也必须因缺少完整result而判失败。若未来修复native fatal路径，必须另行设计preflight/lifecycle并重新审查。overlap身份严格按不同clock map_key汇聚判定；同一map_key的multi-source/duplicate/convergence合法。

## 5. 模块边界

### 5.1 纯数据与 Database adapter

在 `src/operation/iSTA/source/data_manager/adapter/csr/` 新增 Database bridge：

- `CsrGraphTypes.hpp`：Step 2 identity-free、non-committable graph snapshot；不含完整timing input；
- `NativeGraphProjection.hpp`：Step 2 exact structural round-trip DTO；
- `CsrReferencePrimitives.hpp`：唯一拥有NodeKey/ArcKey、table/library signatures、稳定enum/strong ID、analysis context与identity primitives；
- `CsrReferenceNativeModels.hpp`：只定义依赖Primitives的raw constraint/table/transfer/seed/check/library/parasitic typed models；
- `CsrReferenceTypes.hpp`：只组合`CsrReferenceInput`、`CsrTimingResult`与outcome，不重定义primitive/native model，也不含oracle、singleton、Database raw pointer或module header；
- `CsrCaptureMetadata.hpp`：session-owned capture Kahn level buffers与观测容量；backend include tree不可见；
- `CsrNativeGraphOracle.hpp`：Step 2 test-only semantic-keyed native timing order/node level；不含timing result；
- `CsrNativeTimingOracle.hpp`：Step 6 fallback provenance可读后才新增完整semantic-keyed timing oracle；
- `TimingSemanticKey.{hpp,cpp}`：NodeKey、ArcKey、parallel ordinal 与解析器；
- `CsrReferenceCanonicalEncoder.{hpp,cpp}`：唯一拥有typed canonical full-input encoder；
- `CsrFingerprint.{hpp,cpp}`：只拥有SHA-256、component domain hash与makeSnapshotIdentity；
- `CsrReferenceFingerprintPayload.{hpp,cpp}`：唯一拥有六payload builder与makeReferenceInputIdentity；
- `TimingGraphCsrAdapter.*`：Step 2只做Database → graph snapshot与structural decode；Step 4才组装完整reference input；
- `TimingResultScatter.{hpp,cpp}`：完整 prevalidation、stable-key re-resolution 与 allow-list scatter。

新增无link的`ista_timing_database_headers`与独立`ista_timing_graph_csr_adapter`；adapter只依赖pure core和header target，不链接已有legacy SCC中的`ista_data_manager`，Step 2也不加入`ista_source/module/interface`。Step 7才由interface单向链接adapter。adapter public API接收`const Database&`，必要native model只补窄const getter，禁止`const_cast`、`operator[]`读取、STADM和任何Database写入。

Step 2的graph snapshot、test-only graph oracle、capture metadata与完整reference input没有继承、variant或隐式转换。Step 4只在local complete input完成identity和strict validation后single move-return detached candidate；不publish或commit。

Step 3新增独立pure `ista_timing_csr_snapshot_contract PUBLIC -> ista_timing_csr_core`，只含metadata/storage/observation/transition，不被adapter/source/module/interface聚合。identity与唯一FIFO helper属于core。Step 7才允许adapter `PUBLIC -> snapshot-contract`；所有reducer/storage调用由adapter source封装，interface仍只有一条直接`PRIVATE -> adapter`边。

Step 4 detached complete-input API由caller传入已canonical context和nonzero token；adapter不分配token、不commit、不发布observation且不链接snapshot-contract。Step 7才由session真实分配token并发布ready observation。

### 5.2 纯 CSR 算法

在 `src/operation/iSTA/source/module/timing_csr/` 新增：

- `CsrTableLookup.{hpp,cpp}`：复制 snapshot-owned table 后的确定性插值、time/cap单位转换与checked numeric return；
- `CsrCpuReferenceBackend.{hpp,cpp}`：唯一public compute API，只编排validate→support→FIFO→pure stages→typed return；
- `CsrCpuReferenceBackendInternal.hpp`：private work-state/lane/stage declarations，不承载第二套算法；
- `CsrCpuReferenceResultInitialization.cpp`、`CsrCpuReferenceArcTransfer.cpp`：checked shape/sentinel/seed及全arc init/dynamic/per-child cache；
- `CsrCpuReferenceForwardPropagation.cpp`、`CsrCpuReferenceRequiredPropagation.cpp`：先完整slew/delay、再scalar/path，最后endpoint/reverse required/slack与flatten；
- 上述新增exact9个production文件、6个cpp，令`ista_timing_csr_core` source由12增至18；core links仍空，adapter13/snapshot3及aggregate关系不变；
- `CsrReferenceValidator.{hpp,cpp}`：保留validateReferenceInput与全部现有validator API，再新增validateAnalysisContextIntrinsic、validateReferenceInputIntrinsic、validateReferenceInputForSession；四definition各1，调用层为context→input-intrinsic→self validateReferenceInput→session bound。
- `CsrSnapshotIdentityValidator.cpp`：identity syntax与Stage 2 committed generation-0两层validator；
- `CsrFifoLevelization.{hpp,cpp}`：唯一DB-free FIFO replay；最终production call site精确为computation-result validator、timing-result validator、metadata validator、Step 5 backend和Step 7 capture producer，input validator不拒active cycle。

新增 `ista_timing_csr_core` target，只获得 `CsrReferenceTypes.hpp` 所在窄 include directory，不直接或传递链接 `ista_data_manager`、其他 iSTA module 或 `ista_interface`；标准库之外只可使用无反向依赖的窄 toolkit helper。Step 2的独立adapter只链接pure core与无link header target；Step 7才由interface单向组合，不能形成新target环。

pure backend 源不得 include `Database/Arc/TimingPoint/TimingArc/TimingTable/DelayCalculator/TimingPropagator/TimingAnalyzer/ClockPropagator/STAInterface`、oracle、capture metadata、snapshot或scatter。CI 除源码 `rg` 外读取 compiler depfile/include graph 验证这些 header 未被间接带入；不能通过 inline `TimingTable::findValue()` 偷用 native evaluator。

### 5.3 Session context

在 `src/operation/iSTA/interface/StaCsrSessionContext.{hpp,cpp}` 持有当前session的committed `CsrReferenceInput`、独立`CsrCaptureMetadata`、identity、observation和CSR substate。`IncrementalStaSession`只委托capture/observation/test-only reference-and-scatter，不把转换逻辑堆入现有cpp。

`STAInterface` 只增加窄的 token-gated Database access/export/scatter core且不缓存 CSR。Step 7由adapter public依赖snapshot-contract，interface只直接`PRIVATE -> ista_timing_graph_csr_adapter`，不得直接链接snapshot-contract。新源与测试优先保持低于 700 行，既有超大文件优先只接受窄调用点。

owner行数决策：阶段2中的500/550/700等数字全部是维护性建议，不是独立hard gate。功能正确性、证据完整性、清晰职责、可读性与可审计性优先；必要时可超过建议值，并在对应step plan/report记录actual行数、理由与review结论。不得为了行数做高成本或晦涩压缩、删除断言/失败路径、引入动态反查或合并不相关职责；reviewer不得仅以物理行数拒绝。

## 6. Stable key、dense ID 与 traversal contract

### 6.1 NodeKey

NodeKey 是 versioned structured tuple：

```text
{kind: port|instance_pin, full_name, instance_name, pin_name}
```

Stage 2 初次 export 按 canonical encoded NodeKey 排序，分配连续 `NodeId [0,N)`。ID只在当前session/snapshot内有效；跨session只比较NodeKey。Stage 2不冻结mutation后的append/no-reuse实现，因为仅靠重算parallel ordinal无法区分旧/new完全相同的edge。Stage 3必须升级schema，在mutation publish前分配creation token，并引入append-only slot ID、active mask/tombstone后再承诺不复用。

### 6.2 ArcKey 与 library semantic signature

ArcKey 的 base tuple：

```text
{source NodeKey, sink NodeKey, arc_type, owner_name,
 library_source_port, library_sink_port,
 ordered_library_arc_semantic_signature, parallel_ordinal}
```

cell arc 的 ordered library signature逐child TimingArc保存`library_name、arc_idx、sense、trigger_transition、check_transition、sdf_cond、rise/fall table presence与variable-type token`；net arc使用空signature。数值table axis/value、delay、slew、load和flags不进入key，只进入input fingerprint。这样conditional arc即使数值reference拒绝，也能做结构区分。

`parallel_ordinal` 的域是除ordinal外base tuple完全相同的Arc，顺序严格采用`Database::arc_list`当前vector顺序。`native_arc_traversal_rank`同样记录该vector位置，仅属于当前snapshot。disabled/loop/clock flags是payload，不属于key。Arc vector index/raw pointer从不进入持久key；scatter用ArcKey重新解析当前vector index。

初次ArcId按encoded ArcKey排序分配连续`[0,E)`，但ArcId顺序不决定遍历。每个BaseOut/BaseIn row必须分别保存native outgoing/incoming adjacency中的原始Arc顺序；`ordered_root_ids`严格按`timing_point_map`的pin full-name顺序过滤eligible indegree-zero节点生成。row/root顺序进入topology fingerprint并驱动native-equivalent first-wins。

GraphBuilder在缺失/空Liberty cell arc时可生成raw library ports为空且`TimingCellArc*==nullptr`的合法constant fallback cell arc。其versioned canonical ArcKey把library source/sink规范化为endpoint pin name，ordered library signature为空；projection比较该规范语义而非raw空串。raw仅空一端、null/pointer与raw identity不一致或foreign library pointer均为malformed，不能静默丢arc或伪造unsupported。

## 7. `CsrReferenceInput`、oracle与round-trip投影

Step 2不构造完整input，而先导出只含node/instance、无eligibility/transfer/load graph arc、lookup、BaseOut/BaseIn、ordered root/start/end的`CsrGraphSnapshot`。identity/context/constraint/seed/endpoint/cap/load/reason均不存在。Step 4才组合成strict-complete `CsrReferenceInput`。

### 7.1 Reference input的唯一字段

`CsrReferenceInput`只含backend可读字段：

- ordered node/arc records中的semantic key，以及反向ID map；
- `out_row_offsets/out_arc_ids`、`in_row_offsets/in_arc_ids`，row内顺序精确保留native adjacency；
- `ordered_root_ids`及ordered start/end vectors；root不允许backend按NodeKey重排；
- per ArcId source/destination、type、clock/disabled/loop flags和四类eligibility；
- node structural role、port direction、instance cell/role、pin/net关系及每个instance的ordered pin NodeId vector；
- typed raw clock/port/case constraints（map key、embedded identity、保序/保重/unresolved reference）、closure-ordinal timing-check records、referenced-library closure、typed raw parasitic semantic、StartSeedAvailability+optional PathSource、endpoint/cap/transfer与global-optional output load；
- analysis、transition、path-source、seed-availability与clock-tag稳定tokens；寄生存在只由typed nets派生，不保留has_parasitics双真源；
- schema与source identity。

logical size/capacity不存入input。observation的九个buffer extent由visitor即时读取`input.nodes/input.arcs`、四个out/in CSR vectors与metadata三个level vectors；caller不能手填或缓存metrics。
它不含native timing order、level、capture level metadata、TimingPoint timing state、任何Arc result map、path group、summary或report result。Step 2的`CsrNativeGraphOracle`只保存test-only native order/level；Step 6的`CsrNativeTimingOracle`才保存完整timing outputs。backend的public/private header均看不到两类oracle或capture metadata定义。

### 7.2 Path-state ragged layout

`clock_tags[]`按UTF-8 byte序排序并分配ClockTagId。lane固定展开顺序为`NodeId × Analysis(max,min) × PathSource(input,register) × Transition(rise,fall)`，`path_row_offsets[lane_count+1]`索引entry数组。每项保存tag ID、arrival/slew/launch、start/predecessor NodeId、predecessor ArcId/delay、current/predecessor transition、optional CRPR NodeId/transition及presence。

同clock tag的多个startpoint按native strict-better/first-wins合并；不同tag在同lane保留多entry。虽然首版数值support拒绝register launch，布局和结构oracle仍能表示register row。

### 7.3 Exact round-trip的规范投影

Step 2的“exact round-trip”只指versioned `NativeGraphProjection`结构子投影，不宣称重建整个Database。它包含：

- ordered NodeKey及pin full/net/instance/name、direction、is_port；
- ordered instance name/cell及per-instance ordered pin NodeKey vector和sequential/clock-gating/clock/data/output role；
- ordered ArcKey、traversal rank、endpoints、owner/library ports/type/flags和library signature；
- outgoing/incoming每行ordered ArcKey；
- ordered root/start/end vectors；

Step 4 complete candidate覆盖graph、constraints/checks、referenced library、typed parasitics、seed/endpoint/load/transfer/support；Step 2仍只用独立raw projector比较structural projection，不得由同一blob/builder自我compare。

native level/order只存在于Step 2 test-only `CsrNativeGraphOracle`，不属于structural round-trip equality；完整timing output oracle到Step 6才实现。decode不得调用backend/Kahn。Step 2 structural exporter允许active cycle；production capture Kahn仍在后续commit前映射`active_cycle`。

### 7.4 CSR invariants

row offset必须单调、首项0、末项E、ArcId范围合法；BaseOut/BaseIn是同一ArcId multiset的精确转置，同时各自row order必须等于projection；ordered start/end/root无非法或重复ID。backend计算的level buckets恰含每节点一次，eligible arc满足`level(dst)>level(src)`。raw names允许unresolved且对应optional ID必须absent；任一present typed ID都必须唯一解析并与raw key/full name exact一致。

result SoA使用独立presence bits区分missing、真实0与±infinity；NaN非法。clock、data和path state的每一维都必须shape-exact。

### 7.5 Capture-only level metadata

`CsrCaptureMetadata`只包含capture Kahn新生成的`level_offsets`、`level_nodes`、`node_to_level`；flattened `level_nodes`同时给出capture timing order。它由session snapshot独立持有，不进入`CsrReferenceInput`、source fingerprint、round-trip projection或`compute()`。observation的level count和三个level buffer容量只从该metadata读取；node/arc buffer从input nodes/arcs读取。

Step 3抽取唯一core FIFO helper；capture metadata validator要求replay complete且三个vector逐项相等，空图精确为`{0},{},{}`。core target的compiler depfile/include graph仍看不到`CsrCaptureMetadata.hpp`；snapshot-contract调用helper验证metadata。detached测试逐字段修改metadata，断言input canonical bytes、全部source fingerprints和backend result不变。

`host_bytes`是observation schema v1定义的modeled input+metadata storage，不是allocator/RSS。它穷举两者全部dynamic字段，明确包含input顶层schema string、identity version+六hash、analysis context三string这11个root string backing；root只计一次、vector/string backing按size/capacity递归、checked u64 overflow。任何non-None observation的logical/capacity均>0且logical<=capacity，不作跨ABI golden。Step 3 storage test另用不调用production visitor的同ABI runtime `sizeof`/capacity exact formula-delta oracle，冻结root/slot/backing计数、reserved不递归、nested dynamic、SSO与zero terminator增加量。

## 8. Immutable transfer、fallback与required输入

### 8.1 Cell/net transfer

每个cell Arc深拷贝TimingCellArc的`delay/delay_min/delay_max`、clock/disable/clear-preset结构标志以及ordered child TimingArc。每个child保存sense、arc index、trigger/check transition、time/cap scale、threshold/derate、每个rise/fall delay/slew table的presence、variable types、axes与values。

reference必须复现empty timing-arc list、缺失rise/fall delay或slew table、mixed-sense candidate selection、TimingCellArc constant fallback、非单位cap scale时`ceil(load*scale)`、native插值/外推与`STA_ERROR`比较。每一fallback分支都有手算literal golden；只与STADC互相对照不足以通过。

output load为optional 2×2 matrix：typed parasitic nets为空时所有arc present并按Net::load_pin_list原序精确求和；任一parasitic时所有arc absent。present-zero与absent不同，禁止per-net半支持、RC cache或zero sentinel。
TimingTable区分missing、present-empty、0D constant、1D/2D；present-empty候选为0而非fallback。cap-scale 按 binary64 原生 `abs(scale-1.0) < STA_ERROR` 分支，rounded-below 与首个 nextafter-above 分别验证；ceil 前预检 `[0,INT_MAX]`。no-SPEF net仍delay 0、slew透传。

### 8.2 Start/clock/endpoint model

四seed组合不变。selected C2Q=cell_arc_list首is_clock_arc项（不按source/graph/disable/reach过滤）；有则output_pin_name=sink，否则port_map byte序首nonclock output。clock_pin_name独立来自首setup check/否则首check。register iff sequential、native CK reachable且start为CK或selected output；CK/Q path-start=output/self，CRPR node=CK，transition只看selected child[0] non-none否则rise；空output的reachable CK为malformed_topology。其余sequential start unsupported+null且数值absent。四级start及first-arc/port fallback/child[0]×reachability fixtures精确冻结。

RawNodeReference保留full name与optional NodeId；raw name可unresolved且optional absent，present ID必须按map key/full name唯一解析并exact相等。clock保存map_key、embedded name及raw source原序；raw Database empty/unresolved及任意finite负/零/正period/edge可capture，NaN/Inf为illegal_numeric，但public createClock仍可拒。direct source tag取embedded name，其余reachable owner取map_key，clock_tags为全部非空map/embedded/port/seed/endpoint tag的byte-sort union。

successful-full-STA Database是Step4 exporter前提；不同clock map_key overlap只由native子进程无完整result证明，不伪造production typed failure。pure validator可拒绝artificial overlap candidate。

eligibility唯一公式为active=!disabled&&!loop_disabled、seq_clock_sink=net arc&&sink sequential CK、level=active、arrival=active&&!seq_clock_sink、slew=active&&!(seq_clock_sink&&clock_reachable[sink])、clock=replayed_clock_arc。

十项reason不变。divider iff net arc两端可解析instance pin、source TimingCell present且sequential&&!gating&&!macro、sink full_name==sink owner clock_pin_name；net arc is_disabled须exact等于divider，loop-disabled独立，不要求selected output/clock flag/active/reach/replay。clock_gating_or_divider iff任一gating或divider；unreachable divider仍有reason，普通replayed clock arc只fanout。

referenced-library closure是check kind/time/transition/children/table唯一truth；instance record只存closure ordinal、raw/full endpoint、optional resolved IDs与kind mirror，保序保重/unresolved。has_timing_checks exact-derived为native instance check-list非空；只有resolved data参与endpoint重算。

output-port endpoint保存output-delay presence/value；period按最终tag查clock map_key，未命中取首clock period，无clock取0，命中只要求finite并可为负。self层恰调用input intrinsic+identity helper各1，ForSession只调用self，exporter只调用ForSession并保留pre-DB context gate；既有self consumers不删。投影后nonempty SPEF+"__no_rc_corner__"为invalid_analysis_context且无candidate/identity。unsupported result support-first，fixed optional load无递归backing；完整合同见[Step 4计划](stage2-step4-plan.md)。
### 8.3 Step 4 as-built

Step 4 保持 pure header DAG `Primitives <- NativeModels <- Types`，通过 private `CsrReferenceCanonicalEncoderInternal.hpp` 让 canonical encoder 与 fingerprint payload 共用 field append；production inventory 为 core 12、adapter 13、snapshot 3。storage contract exact 三 source，`CsrSnapshotTestFixture.cpp` 保持483行。19个 advance header 与 Step 4 production/test inventory 均受同一 `const_cast` absent detector、build-local safe/poison child self-test约束。

raw/canonical 对 unbound cell arc 分层：native raw library ports为空，canonical ArcKey使用semantic source/sink pin；missing cell不能声明output role，present-empty cell可保留local role。reference_input 为 exact 17-module无环DAG，只有bootstrap动态读取Step2 projection；四个Python CTest COMMAND为controller validation、controller selftest、native overlap与fresh process，全部统一 `ISTA_TEST_PYTHON_EXECUTABLE` 和 `PYTHONDONTWRITEBYTECODE=1`。

canary每项exact四键 `family/pristine/before/after`，token14冻结空timing-arc map scaffold，token15冻结fallback behavior。raw KAT为115B/`572694…de40`和1127B/`981c92…a92f5`；deep candidate为3410B/`58cf82c5347b1d6bc8f13447690d73bb826d5ff20fb7b9e0eb3865d48c4bcd65`，deep raw为1114B/`ae73fa8c86ae17fc0a7b2c06cba46813f258f45023591a117f0c93df4fc3a350`。Step 4 clean formal 的 `^ista_csr_` 48/48、clang-format 21.1.8 exact143/143 dry-run/Werror通过；ignored source-bin保留24个旧 `ista_csr_*`，本步冲突敏感三件及cp312/cp313均不存在，cp311 identity不变；Step 5已在后续独立实现，Step 6+仍未实现。


## 9. CPU/full CSR reference算法与遍历语义

backend唯一public签名为`CsrCpuReferenceBackend::compute(const CsrReferenceInput&) const -> CsrComputationResult`；wrapper的三种alternative与优先级按§4.3冻结：

1. 恰调用一次`validateReferenceInput`；malformed只返回`invariant_violation`且不跑FIFO；
2. valid input若unsupported reasons非空，立即返回逐项exact、非空、stable-unique的`CsrReferenceSupportResult`，不读load/table/seed且support胜过cycle；
3. supported input恰调用一次Step 3唯一`CsrFifoLevelization` helper；input validator已验证`ordered_root_ids`恰等于eligible indegree-zero集合，helper按该顺序与BaseOut row原始顺序FIFO replay，未complete返回`cycle`；backend不得另写Kahn且不读取native level/order；
4. private function-pointer replay seam的计数stub必须证明malformed/unsupported运行时FIFO0次、supported cycle/DAG恰1次；public API不暴露注入点，production仍只有唯一helper；
5. checked shape/state失败返回`invariant_violation`，实际求值出现NaN、computed非法infinity、负slew或overflow返回`numeric_failure`；bad_alloc等资源异常传播；
6. 初始化全部result为frozen sentinels，根据immutable clock/start model seed；
7. 按新timing order完成全图data slew/delay pass，计算Arc初始化delay、timing-arc delay/fallback provenance与动态图delay；
8. 再完成全图scalar arrival和analysis/source/transition/tag path-state pass；
9. forward完成后解析endpoint required，按reverse timing order全图传播legacy scalar required；
10. 计算scalar slack，验证predecessor ArcId、transition和tag引用；
11. 返回带immutable `source_identity` 的detached `CsrTimingResult`。完整逐字段算法、API与KAT见[Step 5计划](stage2-step5-plan.md)。

比较规则逐字段冻结：

| result | winner rule | tie行为 |
|---|---|---|
| per-library timing-arc cache、初始化`trans_delay/trans_type` | raw `<`/`>`，无epsilon | exact tie first-wins |
| 同一TimingCellArc内child delay/output-slew候选归并 | 收集后raw numeric min/max，无epsilon | 只返回标量值，不声明child identity winner |
| dynamic graph delay、data slew、path arrival | `STA_ERROR=1e-6` strict-better | 差值不超过epsilon时first-wins |
| legacy scalar arrival | candidate必须大于current `1e-9`以上 | 其余first-wins |
| legacy scalar required backward | direct `std::min(current, sink-required - Arc::delay)` | direct min |

clock/path每边相加后使用`std::round(x*1e15)/1e15`，正负halfway均按C++ `std::round` away-from-zero测试。scalar backward使用初始化`Arc::delay`而不是dynamic graph delay。max/min×rise/fall只适用于slew/delay/path，required/slack仍是当前native legacy scalar。

result reset值同native：TimingPoint arrival=`-inf`、required=`+inf`、slack/launch=`0`、level=`0`、predecessor/clock为空、predecessor arc缺失编码并在scatter恢复为`size_t::max()`、所有maps empty、clock-point=false；TimingPathState arrival=`-inf`、slew/launch/predecessor-arc-delay=`0`、strings empty、predecessor arc缺失、三种transition=`none`。Arc result maps先清空后按transfer初始化；不能沿用poison/native旧值。

### 9.1 不可绕过的oracle隔离

Step 8真实differential使用两个fresh-process lane：oracle lane只输出Step 6完成的`CsrNativeTimingOracle`；reference lane运行同一parse/full setup后，先poison Database全部scatter timing outputs和level/order，再调用Step 4完成的`exportCsrReferenceInputCandidate()`，然后compute/scatter。controller只按semantic key比较两lane；oracle对象从不进入reference进程。

另有compile-time门保证backendtarget看不到oracle类型；测试修改独立oracle的每个字段不改变backend result。production的baseline capture虽然不poison，但调用同一field-allow-listed exporter，且以该两进程测试证明没有output读取通路。

exact tie、`<1e-6` near-tie、parallel tie fixture必须验证FIFO order、slew winner、downstream LUT与predecessor。禁止同时要求任意adjacency permutation下fingerprint/output不变；row order是冻结的timing语义。

### 9.2 Step 5 as-built

Step 5严格按编码前冻结 SHA-256 `d8850b74cd6995f1f050efbda0e0ed08d2c930ace1163690a105995cdc15112b` 实现。新增9个production文件（6 cpp），core12→18；既有production只改outcome types、outcome/result validator与core CMake。adapter13、snapshot3、direct/interface links和production SCC不变，不接Database/session/scatter/native output。

四个exact executable、5个固定seed property、hand whole-result KAT与不复用backend/table/FIFO/validator的O(VE) slow oracle均通过。Step5及chained isolation 13/13、全CSR 57/57、global unit/property/smoke 73/15/4全部通过；parent non-PDK为1608 passed、8 skipped、4 deselected、13 xfailed。algorithm、test-matrix和fresh red-team三路终审闭环，object/depfile owner、numeric overflow outcome与逐字段identity comparator canary的最终修正均已复证。

## 10. Scatter allow-list、fallback provenance与stale gate

### 10.1 完整可写字段

Stage 2 scatter只允许写由`CsrTimingResult`完整替换的字段：

- TimingPoint level、is_clock_point、scalar arrival/required/slack、launch、clock name、predecessor和predecessor arc；
- TimingPoint effective `_clock_arrival_map`、`_clock_slew_map`、`_clock_predecessor_map`、`_clock_predecessor_arc_delay_map`、`_clock_predecessor_trans_type_map`；
- TimingPoint physical对应的`_physical_clock_arrival_map`、`_physical_clock_slew_map`、`_physical_clock_predecessor_map`、`_physical_clock_predecessor_arc_delay_map`、`_physical_clock_predecessor_trans_type_map`；
- data slew map、ragged path state map；
- Arc scalar/max/min delay、transition/input-output/graph/timing-arc delay maps、transition map以及timing-arc fallback provenance；
- Database timing order list。

为避免`Arc::set_timing_arc_delay_map()`清除隐藏语义，Arc新增窄typed bulk state：`{delay_map, fallback_key_set}`的const getter与一次性replacement setter。backend按native initialization/dynamic-replacement规则计算fallback set；disabled/unreached arc仍保留fallback key。测试在scatter后再次执行dynamic update/full propagation，结果必须与fresh native一致。

禁止写topology、Pin/Instance/Net、adjacency、ordered start/end、Arc key字段/flags/raw pointer、TimingLibrary、TimingConstraint、ParasiticLibrary、power、summary、path groups和report/SDF config。

### 10.2 首写前验证与发布

result携带完整immutable `source_identity`。scatter在任何写入前验证active owner token、source/current token+generation、schema/shape/logical/capacity、presence/sentinel、全部NodeKey/ArcKey/predecessor引用、重新计算的component/composite fingerprints，以及ArcKey到当前vector index的全量唯一解析。

失败优先级固定为：lifecycle/owner `invalid_state` → 重算current identity并按 topology、clock_constraint、library、corner、parasitic、timing_input 的顺序返回`CsrInvalidationReason` → result schema → source session → generation → source identity fingerprints → shape/capacity/presence → numeric → Node/Arc ID mapping → predecessor。这样当前Database漂移总会先使snapshot失效，而单纯foreign/malformed result在current identity未漂移时只形成rejection。

所有replacement容器和native-index解析先在detached state完成；确认其move/swap对当前allocator为noexcept后，才进入无失败publish段。Stage 2保证全部可预测stale/shape/key错误首写前拒绝且`writes_applied=0`。Stage 3仍负责包含topology mutation的通用transaction，不把本次timing-state replacement夸大为edit transaction。

foreign/malformed result但当前Database未漂移时，记录`last_rejection`并保持ready；重新计算发现当前canonical input漂移时记录`last_invalidation`、snapshot转invalidated、顶层session转poisoned。close先revoke为released，再销毁DataManager；close后export/reference/scatter先返回invalid-state，不能触碰singleton。

### 10.3 Step 6 as-built

Step 6严格按v0.7冻结 SHA-256 `d36e4831626093b8a12813ac2053bdd0a6baae4b77c22ebefed2ecfd94804daa` 实现。Arc增加typed timing-arc delay/fallback state及唯一private friend no-fail replacement；adapter新增semantic-keyed完整native timing oracle，以及拆分为orchestration、validation、preparation、publish的stable-key scatter。publish前完成current capture、identity/result/key/predecessor与checked numeric validation，publish段只执行scalar assignment和`noexcept` swap。

success matrix显式覆盖empty、multi-root chain、singleton、diamond、parallel、disabled、loop-disabled与idempotence；failure matrix覆盖guard、六类current drift、result priority、capture phase failure、raw-bit NaN/Inf/signed-zero preservation、derived overflow与全量零写入。native rerun probe在scatter后重绑Database副本中的raw `TimingCellArc*`并重跑传播，验证fallback provenance可继续被native动态更新。

最终冻结Step6 11/11、chained isolation/inventory 7/7、全CSR 68/68、global unit/property/smoke 78/20/5均通过；atomicity与rerun各repeat3通过。两路最终独立复审均APPROVE；Step 4要求的identity/validator各一次保留，staged component hash消除重复后成功capture为冻结约束下17次SHA而非原约48次。

### 10.4 Step 7 冻结设计

Step 7 v0.3 详细计划以 SHA-256 `2996e2d8f558c7707290e7978fc9b6a1f0ce5f4ba680f201083b0829c5627313` 原样冻结。native、parent、tests 三路独立设计复审均明确 `APPROVE`；实现范围固定为真实session token与exclusive authority、generation-0 one-shot capture/commit、ready/released observation、binding、parent transport、全corner strict preflight及隔离sink。fresh-process native/backend数值差分仍属于Step 8。

冻结审查同步勘误三项总计划合同：malformed result identity必须先归入schema/source-null；binding同时暴露只读session token与observation；legacy signoff collector只供`run_harden()`，`run_sta()`只消费新的strict immutable preflight。其余Step 1–6冻结合同不回退。

## 11. Identity、fingerprint、analysis context与generation

### 11.1 `CsrSnapshotIdentity`

identity exact fields为`fingerprint_schema_version:str`、`session_token:uint64`、`graph_generation:uint64`及六个fingerprint：`topology`、`clock_constraint`、`library`、`corner`、`parasitic`、`timing_input`。version首版固定`1.0.0`。

identity syntax允许任意u64 generation；Stage 2 committed identity在syntax之上固定generation 0。input/result/outer/current/previous使用committed层，foreign rejection source使用syntax层。不得再以一个generic validator把所有identity强制generation 0。

fingerprint使用256-bit SHA-256，编码为64个小写十六进制字符；不能使用或截断成`std::hash`。SHA实现以标准空串、`abc`和长消息向量测试，canonical payload另有固定known-answer golden。

canonical encoding使用domain tag/version、固定大端整数、length-prefix string/container和固定enum token。float按IEEE-754 bits编码，`-0`规范为`+0`，允许的±infinity有固定token，NaN拒绝。

`session_token`是当前进程内唯一、非0的uint64 counter；不承诺跨进程唯一。counter将溢出到0时，新session在取得lease前失败且不复用token。fresh-process首个token可以同为1；同进程顺序session必须不同。跨进程controller只按semantic keys/fingerprints比较，不断言token不同。

### 11.2 Fingerprint exact input/output边界

| component | 必须进入 | 必须排除 |
|---|---|---|
| topology | constraint-independent NodeKey/ArcKey、lookup、BaseOut/BaseIn raw row与root顺序、direction/port/instance-cell ownership、arc type/raw flags/rank | ordered start/end、derived role/eligibility、pointer/capacity/level/output；ArcKey既有library signature仍属key |
| library | candidate内referenced-cell closure：roles、ports、cell/check arcs、fallback、ordered child、tables、units/threshold/derate | unused cell、power/function、raw pointer、Arc result maps |
| clock_constraint | ordered raw clocks/source/period/edges/propagated、port presence/value、case analysis | effective/physical result、derived start/eligibility |
| corner | exact canonical `StaAnalysisContext` | sanitized label/path |
| parasitic | candidate内typed explicit-empty或ordered raw units/net/node/resistor/lumped semantic | SPEF path、DelayCalculator/cache/result |
| timing_input | 前五hash的composite加唯一payload：raw resolved IDs/replayed clock owner及全部derived mirror、start/end、roles/eligibility、tags/seed/endpoint/check structure/caps/optional loads/transfer/support | whole `canonicalReferenceInputBytes()` shortcut、scatter fields、oracle/config |

唯一buildReferenceFingerprintPayloads只读candidate typed fields；唯一makeReferenceInputIdentity内部调用它和makeSnapshotIdentity，exporter/validator各调用一次。validateReferenceInput自证token非0/gen0/六hash，validateReferenceInputForSession另绑定expected token；caller bytes、外置supplement、default payload与has_parasitics双真源均禁止。
mutation分成candidate field-flip/reject和raw DB mutation/re-export changed-set两矩阵。ArcKey table signature原子更新key+closure+transfer并改topology+library+composite；axis/value/fallback、port cap与check raw分别原子重导等价字段组；clock raw改clock+composite而topology不变；parasitic raw改parasitic+composite。poison derived family后六hash与whole candidate bytes全不变。

### 11.3 Exact raw analysis context

独立于Stage1三字段request，binding initialize接收exact mapping：

```text
{liberty_corner: non-empty str,
 temperature: canonical decimal str | "__unspecified_temperature__",
 rc_corner: non-empty str}
```

signoff使用未sanitize的raw corner/RC名称。liberty/RC运行时要求exact str、非空且无首尾空白；temperature normalizer只接受exact `str|int|float|Decimal`，拒绝bool、自定义`__str__`、NaN/Inf和string edge whitespace。numeric/string用`Decimal(str(x))`解析，输出无指数/尾零并把`-0`规范成`0`，所以25与25.0均为`"25"`。传入native binding的三个值已经全是canonical string。direct/post-synthesis未提供语义时显式使用`__direct__`、`__unspecified_temperature__`、`__no_rc_corner__`；实际有SPEF时no-RC sentinel非法。

parent post-synthesis/direct入口先resolve context，再做artifact discard或engine/factory调用。`run_harden()`继续且只消费legacy `collect_sta_signoff_items()`；`run_sta()`不调用该legacy collector，而只消费新的strict immutable全corner preflight。strict preflight对全部corner做context规范化、SPEF/raw-RC一致性和纯只读输入校验，全部成功后才调用唯一一次`get_eda_instance`；两条路径不得互调或共享可变dict。因此第二corner非法时第一corner也尚未运行，engine和artifact均为零副作用。

native factory只解析Stage1 request并创建无token的`created` handle，不读/递增token counter、不取lease。binding `initialize`先对exact三键canonical string做strict validation；成功后才分配下一nonzero token、取得owner lease并调用production initialize。非法context会调用binding initialize一次，但token/counter、lease、DataManager和production-operation callback均保持0；context随后immutable。合法context发生lease/init失败时token不复用。不同raw context必须改变corner/composite hash。

Step 3 的通用 context 编码及历史 KAT 见 [Step 3 计划](stage2-step3-plan.md#42-parent-staanalysiscontext)。2026-09-14 修正：`canonicalAnalysisContextBytes` 的 `analysis-context` payload 与生产快照的 `reference-corner-payload` 不同；Python `corner_fingerprint()` 必须使用后者（含 empty marker）再执行外层 `corner-fingerprint` hash。旧通用 payload/component KAT 保留为历史记录，不再称为 observation 指纹。生产 direct/ASCII/UTF-8 KAT 和真实 binding 生命周期同时验收。Step 4 detached 测试由 caller 传入 context/token；真实 token 分配和全 corner preflight 仍由 Step 7 实现。

### 11.4 Generation、capture与capacity

- created/initialized没有committed snapshot，generation不存在；
- incremental session在full pipeline成功后执行one-shot export、validate及Step 3共享FIFO helper，结果写入独立candidate metadata，全部成功才把input+metadata一次commit generation 0；incomplete映射`active_cycle`并按run failure路径丢弃candidate；
- 第二次capture返回CSR-local `invalid_state`，不修改snapshot/observation/counter；property读取永远只读；
- no-mutation baseline、reference/scatter、full recompute、capacity、rejection、invalidation和close均不bump；
- empty/no-op batch未来拒绝且不bump；只有Stage3有效edit原子publish成功才恰好+1；
- fresh session是新process-local token与generation 0。

每个非None Stage 2 observation都源自恰好一次successful capture，因此`capacity.last_action`固定`initial_allocate`、`capacity.event_count`固定1，并在invalidated/released后保持。它不是allocator call count，observation读取不改变它。本阶段不产生grow/rebuild/capacity_fallback。每个buffer仅记录实际vector的logical/capacity；correctness只golden `logical<=capacity`。

## 12. Normative snapshot observation、状态与binding

### 12.1 Exact schema v1

root允许null或下述object；object每层都等价于`additionalProperties=false`。`u64`要求`type(x) is int`、`0<=x<=2^64-1`且先拒bool；session token还要求>0。`ms`接受非bool JSON int/float，规范成finite非负float；hash为64-char lowercase hex。

```json
{
  "schema_version": "1.0.0",
  "state": "ready",
  "identity": {
    "fingerprint_schema_version": "1.0.0",
    "session_token": 1,
    "graph_generation": 0,
    "topology_fingerprint": "<sha256>",
    "clock_constraint_fingerprint": "<sha256>",
    "library_fingerprint": "<sha256>",
    "corner_fingerprint": "<sha256>",
    "parasitic_fingerprint": "<sha256>",
    "timing_input_fingerprint": "<sha256>"
  },
  "counts": {"nodes": 0, "arcs": 0, "levels": 0},
  "buffers": {
    "node_keys": {"logical_size": 0, "capacity": 0},
    "arc_keys": {"logical_size": 0, "capacity": 0},
    "out_row_offsets": {"logical_size": 1, "capacity": 1},
    "out_arc_ids": {"logical_size": 0, "capacity": 0},
    "in_row_offsets": {"logical_size": 1, "capacity": 1},
    "in_arc_ids": {"logical_size": 0, "capacity": 0},
    "level_offsets": {"logical_size": 1, "capacity": 1},
    "level_nodes": {"logical_size": 0, "capacity": 0},
    "node_to_level": {"logical_size": 0, "capacity": 0}
  },
  "capacity": {"last_action": "initial_allocate", "event_count": 1},
  "support": {"reference_supported": true, "unsupported_reasons": []},
  "timing_ms": {"export": 0.0, "reference": null, "scatter": null},
  "host_bytes": {"logical": 1, "capacity": 1},
  "last_rejection": null,
  "last_invalidation": null
}
```

示例host bytes的1/1只表示nonzero schema形状，不是ABI golden。`state`只允许`ready|invalidated|released`。outer/current/previous identity使用committed generation 0；foreign rejection source只要求identity syntax。九个buffer logical exact为node_keys=N、arc_keys=E、两组row offsets=N+1、两组arc IDs=E、level offsets=L+1、level nodes/node_to_level=N；`N==0 iff L==0`、`N==0 => E==0`，非空图`1<=L<=N`，所有+1 checked，capacity均不小于logical。`capacity`精确为`initial_allocate/1`。`reference_supported`恰等于reason list为空，token按stable enum顺序唯一排列。

`host_bytes.logical/capacity`由schema v1同一explicit visitor从完整input+metadata即时计算，均>0且logical<=capacity。vector slots、nested arrays/tables/strings逐层计入，SSO按versioned model处理；overflow拒绝。它不表示allocator/RSS，不作为跨ABI/cross-run golden；跨run只比较input canonical bytes/fingerprint。Step 3用独立同ABI exact formula/delta oracle逐项证明visitor没有重复root/backing、递归reserved slot或增加string terminator。

`last_rejection`非null时exact shape为`{reason,writes_applied,source,current}`；reason为八项mismatch code，writes为integer u64 const0，且`timing_ms.scatter`非null。current逐字段等于outer committed identity。result identity的坏fingerprint schema version、token 0或任一非64位小写SHA-256 hash都必须优先分类为schema mismatch并强制source=null，即使同时存在generation/shape错误也不后移；只有完整syntax-valid identity才继续按token→generation→六hash分类。其余非-schema source必须syntax-valid，shape/numeric/ID/predecessor的source exact等于current。closed/no-snapshot的`invalid_state`只作为operation result返回，不形成event。

`last_invalidation`非null时exact shape为`{reason,writes_applied,previous_identity,current_fingerprints}`，writes为integer u64 const0且scatter timing非null；previous等于outer committed identity。current exact六hash/null，按topology→clock_constraint→library→corner→parasitic→timing_input的第一个null/difference唯一分类。

### 12.2 Observation state invariants

- `ready`：identity有效，last_invalidation必须null；foreign/malformed result可更新last_rejection但不改变identity/generation；
- `invalidated`：last_invalidation必须非null、last_rejection必须null，identity保留最后committed值，session同时poisoned；
- `released`：close前先revoke，除state token外逐字段保留ready或invalidated的最后identity/metrics/event组合，不制造新event；任何native CSR操作返回`invalid_state/writes_applied=0`，observation不变；
- capture前、cpu/full、capture失败、无snapshot close均返回None；optional release允许`None→None`，不伪造object；
- reference/scatter未执行时对应timing_ms为null；执行过才为finite值，真实0允许写0；
- observation读取不改变state、capacity action、event或timing。

允许的event组合只有：ready可为`(rejection=null|object,invalidation=null)`；invalidated必须为`(null,object)`；released精确保留close前两者之一。其余组合一律contract error。

action stable token精确为`read|reference_measurement|scatter_rejection|scatter_success|invalidation|release`并使用typed payload。read在None/ready/invalidated/released都合法且逐字段相等；release允许None→None或ready/invalidated→released。完整矩阵是None允许read+release、ready允许六action、invalidated允许read+一次release、released只允许read；其他mutating action与二次release拒绝。每次rejection覆盖旧event并设置scatter timing；successful scatter清event并设置timing；reference只更新reference timing；current drift接收scatter duration、原子清rejection并写invalidation/state。C++所有action入口先拒绝`valueless_by_exception`并返回field=`action`的violation，禁止`bad_variant_access`。single-object parser不声称能证明历史，pure reducer和before/after/action validator验证exact changed/preserved fields。

transition/schema corpus用冻结field path、structured category与baseline+lane-specific mutation recipe；普通JSON不伪装non-string key、NaN/Inf或unknown C++ enum。五个C++ executable逐案输出含recipe/action/expected field/category/message的exact 10列compiled-contract descriptor，与manifest逐字段比较，禁止只比case ID。具体taxonomy、priority与API见Step 3计划。

native binding只暴露只读`session_token: int | None`与`csr_snapshot_observation: dict | None`，不暴露完整CSR/raw pointer/reference/scatter。Python wrapper在active时解析ready/invalidated object或None，并用只读token独立证明observation属于当前native handle；close成功后、native handle释放前读取并缓存released/None，并调用Step 3公开transition validator对比close前后。strict parser逐层拒绝non-string/missing/extra key、bool-as-int、坏version/token/hash、NaN/Inf、负值及cross-field矛盾。

### 12.3 Session/capture/reference/scatter状态矩阵

| 操作 | 成功/失败 | 顶层state | record | observation |
|---|---|---|---|---|
| cpu/full full pipeline成功 | success | baseline_executed | 原`full_update`10字段 | None |
| cpu/incremental full+capture成功 | success | baseline_executed | capture commit后才原子返回`baseline_only`10字段 | ready/gen0 |
| full pipeline失败 | existing `run_failed` | poisoned | 无 | None |
| full成功、capture invalid/active_cycle/throw | existing `run_failed` | poisoned | 无，不能先逃逸 | None |
| reference unsupported | CSR-local unsupported result | baseline_executed不变 | 不产生新record | ready/support reasons |
| direct/test-only reference computation失败 | CSR-local computation result | 已有session state不变 | 不产生新record | 若已有snapshot则ready；detached core无observation |
| foreign/malformed scatter reject | CSR-local rejection | baseline_executed不变 | 不产生新record | ready+last_rejection |
| current DB/input drift | CSR-local invalidation | poisoned | 不产生新record | invalidated |
| close及close后CSR调用 | existing close contract；后者`invalid_state/0 writes` | closed | 无 | released历史observation或None，后续调用不改变它 |

reference/scatter C++ API不绑定Python，不扩`StaSessionStatusCode`、capability reason或parent exception translator。capture属于baseline run的一部分，失败使用现有run_failed和现有primary/cleanup exception chaining；close仍精确一次。

### 12.4 Parent 无破坏 observation transport

`IncrementalStaSession.run_full_baseline()`先校验原10字段record，再在返回前读取并strict-parse active observation：cpu/full必须为None；cpu/incremental必须为ready/gen0、token与本session一致，且`corner_fingerprint`等于wrapper用同一versioned canonical `StaAnalysisContext` encoder独立算出的期望值。坏active dict使record不能逃逸。`close()`成功后再读取/parse/cache released dict才丢native handle；released observation除`state: ready|invalidated -> released`外，必须与close前缓存的active observation逐字段相等。close或released contract失败沿用Stage1异常链，调用方得不到成功结果。

`ECCToolsModule.run_timing()`保留原`StaExecutionRecord`返回类型，只新增可选immutable sink：`Callable[[StaAnalysisContext, StaSnapshotObservation | None], None]`。正常顺序固定为context preflight → native with-body active validation → successful close/released validation → sink恰调用一次 → `publish_sta_artifacts` → return record；cpu/full sink值为None。sink异常与坏released dict都禁止artifact publish。

runner为每个已预解析corner建立局部sink并把context/observation成对记录、输出日志；禁止缓存在`ECCToolsModule`实例或使用“last observation”，避免多corner串值。默认调用不传sink时返回类型、artifact和日志兼容Stage1。

## 13. 拟修改文件与提交边界

### 13.1 ecc-tools

- 新增上述`source/data_manager/adapter/csr/*`与`source/module/timing_csr/*`；
- 新增`source/module/timing_csr_snapshot/*` pure target、observation/storage/transition与独立isolation gate；
- 修改source/data_manager/module CMake，新增pure core、无link database header target与独立adapter；Step 3 snapshot target不进legacy聚合，Step 7 adapter public链接snapshot target、interface只direct链接adapter；
- 新增`interface/StaCsrSessionContext.{hpp,cpp}`；
- 窄修改`IncrementalStaSession.{hpp,cpp}`、`STAInterface.{hpp,cpp}`、`Arc.hpp`和interface CMake；
- 窄修改`py_ista.{h,cpp}`、`py_register_ista.h`增加analysis context与只读observation；
- 新增round-trip/fingerprint/generation/storage/observation/reference/property/real-probe tests与snapshot JSON Schema/corpus；
- 修改test CMake和wheel action显式build targets并运行unit/property/smoke。

### 13.2 ECC parent

- 新增`chipcompiler/tools/ecc/sta_snapshot.py`与private validation helper，集中context、observation frozen dataclass/enum、strict parser与transition contract；
- 窄修改`sta_session.py`、`module.py`、`runner.py`转发context、执行active/released validation并通过optional sink记录；
- 新增`test/tools/ecc/test_sta_snapshot.py`及窄session/mode/corner tests，不增长669行`test_runner.py`；
- 更新stage0 feature matrix、本详细计划和新增stage2 report。

### 13.3 Workspace外部权威文档

权威计划已于 2026-09-05 迁入 ECC parent 的 [docs/incregpusta-implementation-plan.md](../incregpusta-implementation-plan.md)，可以随 parent 文档提交承载。后续顺序为：child本地commit → 更新 parent code/docs/gitlink 及权威计划中的阶段状态与 child SHA → parent本地commit → 独立只读包装审计。parent report和权威计划使用“本报告/计划所在提交”避免自引用SHA；此前仓库外计划的回填流程仅作为历史记录。

包装审计检查两仓branch/status/direct parent/`git show --check`、gitlink、untracked/generated泄漏、upstream和本地remote-tracking refs是否包含HEAD；只陈述本地可见证据，不联网、不push。

不修改PDK parameter template，不增加公开mode配置，不修改default report/QoR/power/SDF路径和内容。

## 14. 循序实施步骤

每个步骤都必须先分析并列出该步骤的详细修改计划，修改后由未参与实现的subagent独立审查；有finding就修正并重复审查，然后运行该步骤测试。每个步骤结束额外输出“修改了什么、未修改什么、测试结果”的文字记录。

1. 冻结pure reference types、独立oracle type、semantic key、canonical encoder/SHA和strict validators；只做synthetic unit tests。
2. 实现identity-free graph snapshot、Database structural projection、ordered BaseOut/BaseIn、root/start/end、test-only level/order graph oracle和structural round-trip；不构造完整reference input、不commit、不scatter。详细见`stage2-step2-plan.md`。
3. 实现identity syntax/committed generation-0、双层context fingerprint、唯一FIFO metadata、modeled storage、typed action/reducer、rejection/invalidation与optional observation的pure schema/parity；不从partial graph产生production snapshot。详细见`stage2-step3-plan.md`。
4. [已实现] 按[Step 4计划](stage2-step4-plan.md)修订self-contained schema，再由caller token/context导出gen0 strict candidate；successful-full Database为前提，cycle成功且FIFO调用0，不分配token、不commit/observation、不链接snapshot，production caller为0。typed failure无partial，六payload从candidate唯一重算，synthetic/fresh independent raw-projector poison及exact CMake门已通过；工作树未提交、未push。
5. [已实现、终审通过] 按[Step 5计划](stage2-step5-plan.md)修订三态outcome与validator优先级，以private seam address-take复用Step 3唯一FIFO helper，交付core18的全图slew/delay、arrival/path、legacy scalar required/slack；literal hand与不复用backend/table/FIFO/validator的独立O(VE) slow oracle、全门禁和三路代码复审均通过。
6. [已实现、终审通过] 按[Step 6计划](stage2-step6-plan.md)交付Arc fallback provenance typed bulk state、semantic-keyed完整native timing oracle、stable-key re-resolution、完整prevalidation/no-fail publish、stale零写入及scatter后native重跑；冻结11项、全CSR/global门禁与两路最终独立复审均通过。
7. [已实现、终审通过] 按[Step 7计划](stage2-step7-plan.md)接入typed session token allocation、one-shot capture/commit、binding、raw context和parent observation；adapter public链接snapshot-contract并发布ready/released，保持cpu/full默认兼容与multi-corner隔离。
8. [已实现、终审通过] 按[Step 8计划](stage2-step8-plan.md)使用oracle/reference两类fresh-process lane完成真实chain/diamond/extended supported数值差分、30项公开负例及Stage0/1 golden回归。
9. [详细设计双审中] 按[Step 9计划](stage2-step9-plan.md)在build tree生成七个stdlib证据工具，以6 repeats执行warmup1/measured5，产出18 timing/18 storage/9 aggregate并更新阶段报告；只报告`non_comparable`描述性数据。
10. child、parent依次本地提交，外部权威计划回填SHA，再独立包装审计；不push。

任何步骤若发现现有canonical model无法表达所需输入，必须先修订本计划并重新独立设计审查，不能把native output临时改名为input绕过门禁。

## 15. Correctness 与 property 测试

### 15.1 Unit/structural

- NodeKey/ArcKey/library signature known answers、parallel ordinal、full-name root/FIFO/row traversal order；
- SHA-256标准向量和canonical-byte golden；
- empty/singleton/chain/diamond/multi-root/parallel/disabled/loop-disabled以及active-cycle negative DAG；
- BaseOut/BaseIn转置、row offsets、FIFO level buckets、ordered start/end、projection round-trip；
- missing与真实0、±infinity、NaN rejection；
- Liberty empty/missing-table/constant fallback、0D/1D/2D interpolation/extrapolation、ceil cap conversion、positive/negative/non-unate/mixed sense；
- output load和transfer每个分支的手算literal golden；native DelayCalculator parity只在Step 8 fresh-process differential执行，不是Step 5 gate；
- child TimingArc delay/slew raw min/max在`1e-6`内外的near-tie，与sink incoming-arc的`STA_ERROR` winner分开验证；
- port/instance-pin混合root汇聚、exact/near tie、parallel first-wins及downstream LUT；
- timing-arc/trans-delay在`1e-6`内外的raw strict winner，与graph/slew/path epsilon winner分开验证；
- 两input共享clock tag与不同clock tag的ragged path layout；
- clock-point及effective/physical各五组map完整replacement；
- timing-arc fallback provenance与scatter后再次dynamic update/full propagation；
- capture/unsupported/computation/scatter四层error code稳定顺序；现有stored table variable全部可达而无伪造unsupported reason；
- clock overlap与multi-driver仅在独立子进程验证capture前失败；同一clock map_key多source合法、不同map_key汇聚无完整result，`exit(0)`也必须判测试失败；
- backend target/include graph看不到oracle/native evaluator；修改oracle不影响result；
- backend target/include graph也看不到capture metadata；修改metadata不影响input bytes/fingerprint/backend result；
- parent/native observation exact schema、raw-context preflight和capture无record失败路径。
- optional load全局二态、seed四组合/四级start、output_pin_name fallback及C2Q trigger×reachability、unconnected sequential starts、raw optional-ID/finite clock、closure-check与present-empty表；
- typed parasitic/referenced-Liberty逐字段、gating/divider/fanout正反例；SPEF+no-RC invalid context、candidate-tamper与raw DB re-export矩阵分离；
- 四validator nested call graph、既有self consumers、token0/context/self-vs-bound identity/typed failure/no-partial、cycle candidate成功且Step4 FIFO0；
- synthetic逐family与fresh chain/diamond pre/post candidate/raw projection exact；test-only raw projector、独立decoder/hash、input_case绑定、atomic controller与negative self-test共同拒绝canned假绿。

结构、enum、presence、sentinel、semantic key、row order及predecessor exact比较；NaN失败，±infinity按符号exact。synthetic数值使用`abs=rel=1e-12`，real fixtures使用manifest的`abs=rel=1e-9`，公式`|a-b| <= abs + rel*max(|a|,|b|)`。算法内部`1e-6/1e-9/1e-15 round`不是测试tolerance。

### 15.2 Random property

固定seed生成小DAG、parallel arc和disabled/loop overlay。每个seed注册独立`ista_property` CTest并设timeout；失败打印seed、canonical graph与最小replay参数，不使用`random_device`。验证projection round-trip、transpose、FIFO levelization、reference determinism、no-op scatter和row-order-sensitive near-tie。

数值property使用一套不include/reuse backend helper的简单O(VE)/level-DP slow oracle。只在无tie且保持row contract的metamorphic变换下要求相同结果；任意adjacency permutation不再被当作等价输入。

### 15.3 Stale/atomicity matrix

逐项覆盖session mismatch、generation mismatch、六类source-identity component篡改、topology、clock/constraint、library、raw corner、parasitic、shape、ID mapping、predecessor、numeric invalid和session closed。每个失败都比较完整scatter allow-list和forbidden-field snapshot，断言`writes_applied=0`；不能只检查一个sentinel。parser逐reason验证source/current完整identity关系并拒绝bool-as-int。

跨corner矩阵至少包括：同graph不同raw context、同label不同library、同label不同SPEF、同进程顺序same-input session不同token。fresh-process相同input只要求content fingerprints相同，不比较process-local token。A result写B均须首写前拒绝。

parent非法context须在artifact/engine/factory前失败；所有signoff context先验证，第二corner坏也断言engine与两cornerartifact零变化。direct native非法context允许factory和binding initialize方法各调用一次，但token counter/lease/production initialize/DB调用为0；随后合法session取得未消费的next token。另测SPEF+no-RC、首尾空白、`Decimal(str(x))`、`-0→0`。

capture failure必须无record/observation、poisoned后close一次；坏active observation不得让record逃逸，坏released或sink不得发布artifact；默认return仍是record，cpu/full observation None，两cornercontext/observation不得串值；body/close双失败沿用Stage1 chaining。

### 15.4 真实 differential

controller对hermetic chain/diamond及新增supported branch fixture，各运行至少3组fresh oracle/reference lane：

1. oracle lane运行现有native CPU/full，只输出semantic-keyed oracle；
2. reference lane运行同一parse/full setup，poison全部scatter timing output、fallback provenance、level/order；
3. poison后才export `CsrReferenceInput`，pure backend重算并scatter；
4. controller跨进程比较projection/key/level/order/predecessor exact和数值tolerance；
5. forbidden fields canonical hash不变，source fingerprints在poison前后不变，generation保持0；
6. reference lane scatter后再跑一次native dynamic/full路径，与fresh oracle一致；
7. repeats的content fingerprints稳定；不比较跨进程token。

除chain/diamond外，hermetic fixture或native-backed scenario必须覆盖计划宣称的non-unate、parallel/disabled/loop-disabled、multi-root/clock-tag与near-tie分支；未获得native-backed证据的branch必须在报告中降为synthetic-only，不得笼统声称native parity。

若fixture只覆盖input path/port endpoint，报告必须明确；不得据此声称sequential/CRPR已通过。

Step 2另有独立structural projection smoke：只比较graph projection与native timing order/level，禁止读取timing数值或声称native timing parity。该smoke不能代替本节Step 8 differential。

## 16. CI 与回归门

child CTest：

- `ista_unit`：Step 2现有48项基础上增加五个identity/FIFO/storage/observation/transition executable及schema/compiled-contract descriptor parity contract；
- `ista_property`：固定小seed、`--no-tests=error`；
- `ista_smoke`：现有binding/baseline加独立CSR real probe；
- wheel action显式build每个新增executable后分别跑三个label。
- core target compiler depfile/include graph gate证明没有oracle/data-manager/module header泄漏，actual target source集合与被检查object集合完全相等；
- Step 2 adapter另有target-property与Ninja depfile gate：直接依赖仅pure core+无link header target，不加入legacy SCC，不可见interface/propagator/analyzer/scatter/backend。
- Step 3 snapshot target direct link只含core，不进aggregates；source/object/depfile exact gate拒绝graph adapter/native/interface/backend/scatter；core和adapter各自增加snapshot header prohibited门。
- Step 4 as-built冻结Primitives <- NativeModels <- Types、private shared encoder internal header与ModelValidator；core12、adapter13、snapshot3及links不变；public-header+8 functional executable、19-header const_cast safe/poison detector与source/object/depfile/callsite isolation全绿。
- Step 4 fresh冻结full-candidate/raw DTO、empty+complex raw KAT、3410B candidate/1114B raw deep KAT、17-token三态typed canary one-hot/0x1ffff及token14/15行为门；reference_input exact17 Python DAG只有bootstrap接触Step2 projection，四COMMAND统一ISTA_TEST_PYTHON_EXECUTABLE/PYTHONDONTWRITEBYTECODE。Step 4 clean formal `^ista_csr_`为48/48，clang-format 21.1.8 exact143/143；ignored source-bin旧产物口径按§8.3冻结，Step 6+仍未实现。
- Step 5 as-built：core12→18 exact sources、typed support/computation priority、exact result shape、table/arc/two-forward/clock/required/numeric合同、4个test executable与5 property seeds均已实现；Step3/4 FIFO direct-call shape保持5，backend address-take1、production bare symbol6，validateReferenceInput consumer同步+1。slow-oracle/source/object/depfile/nm/self-poison/line-cap exact gate通过；最终CSR 57/57、global unit/property/smoke 73/15/4、parent non-PDK 1608 passed。
- Step 6 as-built：adapter13→17 exact sources但direct links/SCC不变；Arc唯一private friend replacement、oracle objects、scatter validation/preparation/publish owner、publisher undefined-symbol和header include-order均受门禁。success/failure/atomicity/rerun/property/source-inventory全绿；最终Step6/chained/CSR/global unit/property/smoke为11/11、7/7、68/68、78/20/5，atomicity与rerun repeat3通过。

parent：

- strict parser/session/corner tests；
- `test/tools/ecc`和`test/cli/params`定向回归；
- 全部non-PDK pytest；
- Ruff check/format、scoped ty和diff-check。

发布门还包括clang-format dry-run、按§5.3记录新增文件actual行数与具体维护性finding、source tree无untracked build/session/result泄漏、Stage0/1 golden hash不变。单纯超过行数建议不阻断发布；外部PDK/GPU不可作为hermetic gate。

## 17. 性能与可观测性

阶段 2只做conversion/reference/scatter smoke，不宣称speedup。使用steady clock分别记录export、reference、prevalidation/scatter；记录node/arc/level数、versioned modeled host logical/capacity bytes、每vector capacity和high-level capacity event count，不声称allocator/heap/RSS。至少warmup 1次、measured 5次，报告原始repetitions、中位数和p95；build-tree JSON不提交为golden。

性能结果必须注明机器/compiler/build type/thread数。fallback/unsupported case不进入性能汇总。benchmark schema v1不变；若未来需要持久化snapshot observation，另起versioned schema。

## 18. 审查协议

设计审查至少由两名未参与实现的subagent分别覆盖：

- graph/CSR/transfer/reference/scatter正确性；
- session/generation/fingerprint/corner/binding/CI兼容性。

任何blocker/major/minor finding都要修改计划并由原reviewer复查，直到双方APPROVE才编码。

实现后再次拆分parent/native独立代码审查。reviewer必须实际读取最终diff并独立运行相关unit/property/smoke；false-green、文件规模、生成物泄漏和默认artifact变化均为阻断项。测试或审查失败就修正并重复，不能只记录失败。

## 19. 阶段完成条件

只有以下全部满足才可写“阶段 2 完成”：

- 详细计划获至少两名独立reviewer最终APPROVE；
- `NativeTimingGraphProjection↔CSR` exact round-trip与独立slow-oracle property全绿；
- reference lane在poison native output后才export input并完成重算；
- chain/diamond及声明supported的扩展fixture，reference+scatter与独立native CPU/full oracle逐点等价；
- stale/session/corner/fingerprint rejection全部零写入；
- cpu/full默认artifact与Stage0/1 golden不变；
- execution record仍为原10字段，baseline_only不误报incremental；
- parent/native代码审查最终APPROVE；
- unit/property/smoke、parent non-PDK、format/type/diff门通过；
- 阶段报告列出修改文件、测试数字、转换时间/内存、ID/generation规则和typed unsupported语义；
- ecc-tools先于parent建立本地`IncreGPUSTA`提交，parent gitlink精确，均未push。

若独立reference的输入建模、poison differential或scatter零写入任一未通过，阶段 2必须保持未完成状态，未来agent不得进入Stage 3。
