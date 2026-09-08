# 阶段 2 完成报告：Step 1–9 本地实现与简化功能验收

> 2026-09-08 冗余清理：受控 levels 的完整证明归属生成路径；任意外部 levels 仍完整验证。 详见 [清理报告](stage0-6-redundancy-cleanup-report.md)；以下阶段验收数据继续表示历史结果。

> 当前开发协议补充（开发检查分离）：实际快照、scatter、失效身份与公共输入校验始终保留，已受控对象的重复扫描与深拷贝归 ON。 后续改动必读 [开发检查规范](development-guidelines.md)，双模式实测与历史验收的区别见 [本轮实施报告](debug-checks-implementation-report.md)。原阶段验收数字保留为历史记录。

> 状态：阶段 2 功能实现与简化验收完成；Steps 1–8 通过代码复审与回归，Step 9 按用户授权以功能正确性收口
> 日期：2026-08-31
> 提交状态：Step 10 仅创建 parent 与 ecc-tools 本地提交，不推送；本报告以所在 parent 提交为准

## 1. 结论

阶段 2 的 Steps 1–9 已完成。Step 1 冻结 Database-free pure CSR contract；Step 2 增加只读真实 `ista::Database` 结构 adapter与identity-free graph snapshot；Step 3 增加identity/FIFO/storage/normative observation pure contract；Step 4 从 `const Database&`、caller canonical context与nonzero token原子导出detached generation-0 complete candidate。

Step 2保留canonical dense ID、native traversal rank、parallel ordinal、BaseOut/BaseIn row order和root/start/end顺序；Step 3/4冻结唯一FIFO与candidate-only六fingerprint。adapter、snapshot contract与core保持窄target，不聚合进interface/source legacy SCC。

Step 5实现DB-free `CsrCpuReferenceBackend::compute()`：按malformed→unsupported→FIFO cycle→post-FIFO invariant→numeric→success优先级，执行完整table/arc transfer、slew/delay、scalar/path arrival、legacy required/slack并返回detached `CsrTimingResult`。literal hand KAT与不复用backend/table/FIFO/validator的独立O(VE) slow oracle共同验证，production不读取Database/native output。

Step 6增加Arc timing-arc fallback provenance typed bulk state、semantic-keyed完整native timing oracle，以及stable-key scatter的全量prevalidation、detached preparation与no-fail publish。成功/失败矩阵、零写入、原子性、current drift、raw-bit capture seam及scatter后native rerun均由动态KAT锁定。

Step 7按v0.3冻结设计完成真实process-local session token与exclusive Database authority、generation-0 one-shot capture/commit、ready/released observation、binding及parent transport。全corner strict immutable preflight在任何capability/subflow/engine/artifact动作前完成；每cornersink只接收本角context与observation，legacy harden collector及Stage 1十字段execution record保持兼容。

Step 8按v0.15冻结设计完成真实fresh-process native/reference differential。oracle lane只输出native timing-state wire；reference lane在同一fixture完成full baseline后poison timing-state，重新导出candidate，执行DB-free backend、stable-key scatter与native canary rerun。controller在两个临时lane上独立重解码、重算并比较chain、diamond和extended supported三类case，普通验收共9 pair/18 child；30项公开负例、same-fd/no-clobber发布、全局回滚与进程cleanup均由自测和fresh矩阵锁定。

Step 9按用户预先授权在三次正式完整候选均未完成严格POST→report-transition→FINAL来源封口后，停止继续扩张哈希攻防，转入简化功能验收。第3次候选`BBXZ6jkc9zDZ`的真实fresh-process链已完整通过capture、context、reducer与独立recheck：3个case×6 repeats形成18 pair/36 lanes，controller summary为`complete=true`；18/18 pair的native oracle timing、DB-free reference timing、stable-key scatter后timing及native rerun timing逐对象完全一致，18次scatter全部`success`，无`current_capture_error`或`invalidation_reason`。

Step 9只接受功能正确性和描述性smoke结果。所有聚合行均为`comparability_status=non_comparable`；报告只给出原始分阶段延迟、描述性median/p95及modeled host bytes，不宣称speedup、统计稳定性、RSS/heap峰值或跨机器可比性。严格POST/FINAL未完成这一事实不被简化验收隐藏。

Step 7 frozen plan SHA-256为`2996e2d8f558c7707290e7978fc9b6a1f0ce5f4ba680f201083b0829c5627313`。native、parent、gate三路最终代码复审均明确`APPROVE`；四个KAT、唯一umbrella inventory、controller validation、fresh-process session lane及global unit/property/smoke 84/20/6全部通过。

Step 8 current frozen plan为v0.15、713行，SHA-256 `2246cc8ce01d4952b7e8435275907327ef21446e15a4a47629f39febe9abbdc0`；设计双审、Python终审、C++/CMake终审及两处全局回归修复复审均明确`APPROVE`。最终CSR 79/79、global unit/property/smoke 87/20/7、Stage0/1 focused及parent non-PDK全量回归均通过。历史v0.14 SHA为`604dd5427d2ba1003ff4e22ae0ab3e5760148331fd1fcebf1e33ae2d9c402be2`，不作为当前基线。

本轮证据现覆盖Steps 1–9的数据、结构、observation、complete input、pure CSR full-graph算法、受控native timing-state write-back、production session lifecycle、fresh-process native/backend数值与raw provenance差分，以及6-repeat描述性采集。它仍不证明generation>0、mutation/Dual-CSR、affected-cone或CUDA speedup。总计划编码前复审 SHA-256 为 `052ae59be69c4ad097d716d279275d19b75940ca07567e481f565d95b9f7aa64`，Step 3 v0.4 为 `188d1184ec0e16f62339c484df515aed08fe5e722fc32fc1f308adcb44e2b050`，Step 5 v0.2为 `d8850b74cd6995f1f050efbda0e0ed08d2c930ace1163690a105995cdc15112b`，Step 6 v0.7为 `d36e4831626093b8a12813ac2053bdd0a6baae4b77c22ebefed2ecfd94804daa`，Step 7 v0.3为 `2996e2d8f558c7707290e7978fc9b6a1f0ce5f4ba680f201083b0829c5627313`，Step 8 v0.15为 `2246cc8ce01d4952b7e8435275907327ef21446e15a4a47629f39febe9abbdc0`，Step 9 v0.31为`1f9677f9d027dc534bc2e422a49ad4c8aa6114553b81289d8ce23910463529ac`。

## 2. 已交付边界

### 2.1 Step 1：pure CSR foundation

- `CsrReferenceInput`、flat-SoA `CsrTimingResult` 及 capture/support/computation/scatter typed outcome；
- NodeKey、ArcKey、library arc signature、native-order parallel ordinal 和公开 enum token；
- versioned、domain-separated、big-endian canonical encoder 与自包含 SHA-256；
- input/result/outcome strict validator，覆盖 shape、presence、sentinel、order、derived reason 与 recurrence；
- `ista_timing_csr_core` 及 compiler-dependency isolation gate。

### 2.2 Step 2：Database graph adapter

- identity-free、non-committable `CsrGraphSnapshot`，以及严格 snapshot validator；
- `exportCsrGraphSnapshot(const Database&)`、`decodeNativeGraphProjection(...)` 和结构 oracle API；
- canonical NodeId/ArcId、exact instance ownership、native traversal rank 与 parallel ordinal；
- 稀疏 native adjacency 归一化、BaseOut/BaseIn exact transpose、ordered roots/starts/ends；
- bound timing-graph arc signature 校验，以及缺 cell/空 cell-arc-list 时的 unbound Cartesian fallback；
- active cycle 可结构化导出；test-only oracle保留 GraphBuilder 的 partial order/level 语义；
- projection/oracle 独立 canonical bytes、SHA-256 与 strict independent decoder；
- independent raw Database projector、FIFO oracle、fixed fixtures、property seeds 和 fresh-process controller；
- `ista_timing_database_headers` 与 `ista_timing_graph_csr_adapter` 两个窄 target，以及 actual source/object/depfile 双向 isolation 门；
- native model 所需的窄 `const` getter，不改变 Database owner 或 full STA lifecycle。

### 2.3 Step 3：identity 与 snapshot observation pure contract

- identity syntax 与 Stage 2 committed generation-0 两层 validator，以及 C++/Python exact raw analysis context canonical fingerprint；
- 唯一 Database-free FIFO replay helper，三个现有 production consumer 的 exact source inventory，以及 complete metadata validation；
- 从真实 `size/capacity` 即时派生的九 buffer extent、counts、support/timing/capacity 与 modeled host bytes visitor；
- typed ready/invalidated/released observation、scatter rejection、invalidation、无 partial-success builder 与共享 first-reason policy；
- reference/scatter/invalidation/release pure reducers，以及 `optional before + action -> optional after` transition validator；
- strict JSON Schema、共享 duplicate/NaN/Infinity-safe engine、四 lane corpus manifest 与 40 条 compiled-contract descriptor parity；
- parent frozen dataclass、self-contained parser/validator/transition API；未接 parent session、module、runner 或 artifact 流程；
- 独立 `ista_timing_csr_snapshot_contract` target，以及 core/adapter/snapshot source-object-depfile、target-property 和 Step 3 source-inventory isolation 门。

### 2.4 Step 4：detached complete reference input

- `exportCsrReferenceInputCandidate(const Database&, const StaAnalysisContext&, uint64_t)` 及 context→intrinsic→self identity→session bound 四层 validation；
- pure header DAG `Primitives <- NativeModels <- Types`、private shared `CsrReferenceCanonicalEncoderInternal.hpp`、candidate-only 六 payload；
- raw/canonical unbound split、binary64 `STA_ERROR` boundary、present-empty table、global optional load、structural seed/C2Q、check closure、Liberty/parasitic 与 support reasons；
- exact 17-module Python oracle/controller、四个 `PYTHONDONTWRITEBYTECODE=1` CTest COMMAND、三态四键17-token canary、native overlap controller；
- empty/complex raw KAT、3410B candidate/1114B raw deep KAT；
- 19 advance header 与 production/test `const_cast` absent gate、safe/poison detector self-test、source/object/depfile/callsite isolation；
- public-header + 8 functional targets、fresh/poison/property/failure/storage 与 legacy CSR 回归。

### 2.5 Step 5：DB-free full-graph CPU reference

- 三态 `CsrComputationResult` transport与exact outcome priority，十项unsupported reason保持typed alternative；
- 唯一production table interpolation/unit-conversion helper，以及result initialization、arc transfer、双forward、required/slack五阶段；
- Step 3 FIFO helper的private function-pointer seam，malformed/unsupported FIFO0、cycle/DAG/numeric/post-FIFO invariant FIFO1；
- bit-exact whole-result comparator与逐字段canary、literal hand KAT、五seed property和独立O(VE) slow oracle；
- core exact12→18，四个test executable、16个test objects（其中3个slow-oracle）与6个production objects、共22个对象的source/object/VALID-depfile exact owner gate；
- `-ffp-contract=off`、undefined-symbol、safe/poison、public-header/include-order、行数维护性状态与wheel等价门。

### 2.6 Step 6：stable-key timing-result scatter

- Arc新增typed timing-arc delay/fallback state与唯一private friend `noexcept` replacement；publisher只做scalar assignment与swap；
- semantic-keyed native timing oracle逐字段读取全部允许写回的TimingPoint、Arc与timing order状态；
- scatter按owner/committed guard→current identity drift→result priority→stable key/predecessor→detached preparation→no-fail publish执行，所有失败`writes_applied=0`；
- success显式覆盖empty、multi-root chain、singleton、diamond、parallel、disabled、loop-disabled和idempotence；failure覆盖完整guard/drift/result/capture/numeric矩阵；
- atomicity fault sweep、bit-exact forbidden canary及rerun probe证明首写前拒绝、完整恢复和fallback provenance可继续被native更新；
- adapter exact13→17且direct links/SCC不变；Step6 11/11、chained 7/7、CSR 68/68与global 78/20/5通过。

### 2.7 Step 7：production session lifecycle 与 parent transport

- raw context在token/lease/Database之前strict validation；有效session取得process-local nonzero monotonic token，失败烧号，`UINT64_MAX`后sticky exhausted且不wrap/reuse；
- `CsrSessionSnapshotAdapter`原子构造detached input、metadata及ready/released twins；success、typed failure与throw-first都永久消费generation-0 one-shot capture；
- `StaCsrSessionContext`固定awaiting-capture→ready/capture-failed→released状态机，reference/scatter只接受owner token，release幂等且released handoff在cleanup之前完成；
- `STAInterface`把legacy run、session run/copy/reference/scatter/close统一置于同一个exclusive guard；same-thread递归、foreign context、queued second-validation和close/destroy竞态均在Database访问前受控拒绝；
- scatter以detached preparation及Database+observation joint no-fail publish提交，失败保持零native写入和原observation；
- binding只读暴露`session_token`与`csr_snapshot_observation`，parent逐层核对native handle、context与observation token，closed getter不触发singleton；
- parent在构造native config前冻结analysis context；`run_sta()`使用strict immutable full-corner preflight及per-corner observation sink，`run_harden()`继续保持legacy collector合同；
- 四个新KAT、Step 7 umbrella/controller/fresh-process lane与chained isolation证明上述lifecycle、并发、binding、transport及legacy projection兼容。

### 2.8 Step 8：fresh-process native/backend differential

- 两个opaque probe分别持有native oracle与reference pipeline，controller不链接或导入native实现；
- 三个case、3 repeats形成9 pair/18 child；每次锁定argv、PID/nonce、raw bytes、六fingerprint、generation 0、canary与observation；
- reference lane在导出前poison全部允许写回状态，candidate只来自首次successful full build；compute/scatter后重新运行native stages并与oracle逐semantic key比较；
- signed zero、NaN/Inf、near-tie、unsupported、stale identity、ArcKey、raw provenance、summary与事务失败均有独立公开负例；
- pair和summary采用same-directory temporary、same-fd validation、hardlink no-clobber及失败全局rollback；双lane超时/退出/pipe错误均terminate→wait→kill→reap；
- 七个Python职责文件、三个native/wire场景target、Step 8 Workflow/Isolation/Targets静态门及wheel action形成exact owner闭环。

### 2.9 Step 9：6-repeat描述性采集与简化功能验收

- 候选`BBXZ6jkc9zDZ`使用warmup repeat 0与measured repeats 1–5；raw timing/storage各18行，aggregate为3 case×3 phase共9行，每行`n=5`；
- 18/18 pair通过oracle/reference、scatter、rerun、level-order与stabilization一致性；每repeat的`writes_applied`固定为chain 246、diamond 341、supported_branches 884；
- 18份observation全部`generation=0`、`reference_supported=true`、`unsupported_reasons=[]`；
- 描述性median/p95毫秒如下：

| case | conversion/export | reference | prevalidation/scatter preparation |
|---|---:|---:|---:|
| chain | 0.491054 / 0.514364 | 0.147089 / 0.151819 | 0.641513 / 0.875291 |
| diamond | 0.600062 / 0.669193 | 0.189311 / 0.260055 | 0.761502 / 1.064920 |
| supported_branches | 1.578909 / 1.735450 | 0.627046 / 0.756532 | 2.316908 / 2.360535 |

- storage在各case的6 repeats内完全一致：chain为9 nodes/7 arcs/8 levels、modeled logical/capacity `20150/24752` bytes；diamond为12/11/8、`30812/37594` bytes；supported_branches为31/29/10、`81200/92301` bytes；每个case均只有一次`initial_allocate` capacity event；
- summary SHA为`a8d73659caafd66880ee8c427ebc6ba0837440400c70c200e7abcbed696ff84b`；timing/storage/aggregate文件SHA依次为`dc5f0a08d74015e7af13c8b152070f42c481c0150f50ab806fd5d14b696d8273`、`6f46dc42c5f3fda9ccaeea9c5ffdbe4dacc2863a88589a4e1ee7bcb413c01479`、`69fbaf77061c7887c5512838b3fa6a2f8b1f985dcbd086c1b668012eb76c38f0`；独立recheck对三组rowset重算一致；
- `comparability_status=non_comparable`，上述时间只用于本机smoke观察，不用于相对性能结论。

### 2.10 明确未交付

- generation>0、mutation batch、Dual-CSR与affected-cone propagation；
- CUDA backend或speedup；
- cross-process token唯一性或host-byte/timing golden。

Stage 1固定10字段execution record、默认 `cpu/full/error` 行为、artifact路径和golden均未修改。Step 7只在incremental/full-baseline成功capture时发布generation-0 committed snapshot；full模式仍保持observation为`None`。

## 3. 修改范围与 target 边界

### 3.1 ECC parent

- `chipcompiler/tools/ecc/sta_snapshot.py`：冻结 dataclass/enum、analysis-context fingerprint、observation parser 与 public validation/transition API；
- `chipcompiler/tools/ecc/_sta_snapshot_validation.py`：承载窄内部 validation/reducer 实现，保持公开模块职责清晰；
- `test/tools/ecc/test_sta_snapshot*.py`：覆盖 context、schema/parser、typed observation、transition、ASCII/UTF-8 KAT 与 child manifest parity；
- `chipcompiler/tools/ecc/sta_session.py`：context-before-config、native token/observation binding、ready/released transition与failure terminal cleanup；
- `chipcompiler/tools/ecc/module.py`、`sta_signoff.py`：strict preflight、per-corner immutable context与隔离sink；
- `test_sta_session_snapshot.py`、`test_module_timing_snapshot.py`、`test_sta_signoff.py`、`test_runner_sta_snapshot.py`：transport、preflight、sink和legacy harden兼容回归；
- `docs/incregpusta/stage2-{detailed,step2,step3,step4,step5,step6,step7,step8,step9}-plan.md` 与本报告：步骤1–9记录as-built；Step 8 v0.15冻结SHA为`2246cc8ce01d4952b7e8435275907327ef21446e15a4a47629f39febe9abbdc0`，Step 9 v0.31冻结SHA为`1f9677f9d027dc534bc2e422a49ad4c8aa6114553b81289d8ce23910463529ac`。

parent的Stage 1 execution record、默认backend/mode/status、最终artifact顺序和legacy harden collector均未改变；旧`test_runner.py`只机械迁出四个STA block并保持413行/SHA `6845d6ad7b73dce116e61602cc846bea186e39f85c46d21eda96dc4437035805`。Step 10按child-first顺序先封存child，再由本报告所在parent提交记录gitlink；该gitlink指向child提交`5609a3c932e7bcb6cfb2a2ee765f472e0615e395`。

### 3.2 ecc-tools child

Step 10的child-first本地提交已封存阶段2的Steps 1–8实现；Step 9只使用这些功能完成隔离采集与验收。主要职责如下：

- `source/data_manager/adapter/csr/`：pure types/key/fingerprint、graph DTO/projection、complete input、native timing oracle、stable-key scatter及Step 7 `CsrSessionSnapshotAdapter`；
- `source/module/timing_csr/`：pure validators、identity/FIFO，以及Step 5 table lookup和full-graph CPU reference五阶段；`ista_timing_csr_core` exact18 sources；
- `source/module/timing_csr_snapshot/`：storage visitor、normative observation、static validator 与 transition reducer；
- `source/data_manager/advance/*.hpp`：除Step 2/4窄 `const` getter外，Step 6仅给Arc增加typed timing-arc delay/fallback state与唯一private friend replacement；
- `interface/`：`StaCsrSessionContext`、`IncrementalStaSession` lifecycle、exclusive authority与机械拆出的`STAInterfaceOperations.cpp`；
- `test/Csr*`、`StaCsr*`：既有contract/native fixtures、backend/slow oracle、scatter矩阵，以及Step 7 adapter/context/lifecycle/binding KAT；
- `test/CsrCpuReferenceSlowOracle*.cpp`：与production table/FIFO/backend/validator隔离的独立O(VE) oracle；
- `test/reference_input/`、`test/projection/`、`test/timing_scatter/`与`test/csr_session/`：既有fresh/rerun assets及Step 7 session contract/controller/self-test；
- `test/real_differential/`：Step 8 model/wire/contract/controller/self-test、两个opaque native probe与wire/scenario合同；
- `test/reference_input/reference_input_{candidate_wire,recompute_transfer}.py`：Step 8窄inverse codec与transfer重算owner；
- `benchmark/schema/`：strict JSON/schema engine、observation schema、四 lane corpus、manifest 与 compiled parity runner；
- source/data-manager/module/interface/test CMake和wheel action：窄target、exact source/object/depfile/undefined-symbol/guard/CTest JSON inventory、Step 8三probe/wire target与显式CI build/test。

adapter 的直接依赖固定为：

```text
ista_timing_graph_csr_adapter
  PUBLIC  -> ista_timing_csr_core
             ista_timing_csr_snapshot_contract
  PRIVATE -> ista_timing_database_headers
```

Step 3 snapshot target 的依赖固定为：

```text
ista_timing_csr_snapshot_contract
  PUBLIC -> ista_timing_csr_core
```

snapshot contract仍不聚合进`ista_source`或`ista_module`；adapter PUBLIC链接core/snapshot，`ista_interface`仅PRIVATE直接链接adapter，未形成新SCC。Ninja depfile gate逐object验证allow-list：core/snapshot拒绝Database；旧17个adapter object拒绝snapshot，只有新bridge允许冻结snapshot public headers；publisher单独允许observation header，interface与binding也受exact depfile/header allow-list约束。

## 4. 关键实现决策

### 4.1 语义 identity 与 exact projection

- NodeId/ArcId 只在 snapshot 内 dense；raw pointer、Database vector index 和 timing library地址不作为稳定 identity。
- instance pin 的 NodeKey 严格满足 `full_name == instance_name + ":" + pin_name`；port 使用空 instance name。
- canonical NodeKey/ArcKey 决定 dense ID；parallel ordinal按 native traversal rank 分组重放，复杂度为 O(E log E)。
- instance/map/internal name、pin ownership、cell/net owner、bound pointer membership 和四方 library port identity均在导出/validator层验证。
- known node 缺少 native adjacency map key表示空 row；额外 unknown key、坏 index、重复或缺 arc、方向错误均拒绝。
- start/end role 本步只保真 Database 当前 vector与派生 bit；逻辑 completeness延至读取 constraint 的 Step 4。

### 4.2 Bound 与 unbound cell arc

- bound child 必须属于 owner cell 的 arc list、是 timing-graph arc，并满足 raw ports、endpoint local pin和 pointed `TimingCellArc` ports 一致；
- delay/slew signature只接受 rise/fall key，check table map及不可编码状态在本步拒绝；
- unbound fallback 仅在 cell 不存在或 owner cell arc list为空时成立，且必须为 null pointer、空 raw library ports和 ordered input×output Cartesian product；
- fallback 导出按 owner预分组，arc ownership使用索引查询，避免 O(F×E) 或 O(p³) 扫描。

### 4.3 只读性与复杂度

exporter API 使用 `const Database&`；native container读取使用 `find`，不会用 `operator[]` 隐式插入。导出前后 independent raw projection bytes/hash必须完全相同。

实现审查曾发现每个 instance全扫 node/pin、fallback每条 arc重复扫描 owner pin等真实规模退化。最终实现使用 instance-name→row、node owner和ordered-pin owner索引；新增 8192-instance与128×128 fallback规模回归用例，并由静态复杂度审查约束算法形态。

### 4.4 Step 3 的唯一真源与 pure 边界

generic identity syntax 接受任意 `u64 generation`，Stage 2 committed identity 再收紧为 generation 0；outer/current/previous 使用 committed 层，foreign rejection source 使用 syntax 层。raw analysis context 的字段、顺序和 normalization 在 C++/Python 共享 ASCII 与 UTF-8 known-answer。

level metadata 只能来自唯一 FIFO replay helper；当前三个 production consumer 及调用次数由 source-inventory CTest 精确冻结，禁止 local Kahn。九个 buffer extent 只能从 input/metadata 的真实 `size/capacity` 派生，caller 不能手填 metrics；`host_bytes` 明确只是 schema v1 modeled estimate。

单个 released object 只验证静态 shape；历史合法性由 pure reducer 和 before/action/after transition validator 证明。C++ contract descriptor、manifest、JSON Schema 与 parent parser 逐字段对齐，但 parent runtime 不读取 child asset，Step 3 也不创建 production snapshot owner。

### 4.5 Step 4 complete-input、canary与独立oracle边界

canonical encoder公开API与fingerprint payload通过private internal header共享同一field append实现；Python只独立复现canonical语义，不import production encoder。unbound raw ports保持空而canonical key规范化semantic pins；native full-name roles与cell-local closure roles不混用。load scale按binary64原生阈值判断。

fresh controller独立decode candidate/raw/canary并重算graph/model/transfer/fingerprint；canary为pristine/before/after三态四键，token14 scaffold与token15 fallback behavior分别门禁。deep KAT锁定ArcKey direct-byte order、CSR/lookup/六hash；它是input/oracle一致性证据，不是timing numeric parity。

### 4.6 Step 5 pure backend与oracle边界

public `compute()`只把Step 3 FIFO helper地址传给private seam；内部固定validate→support→FIFO→五stage→typed return。table lookup逐操作冻结unit conversion/interpolation顺序；两段forward分别完成slew/delay与scalar/path，required按reverse FIFO order使用初始化 `Arc::delay`，所有success result从canonical sentinel重建而不继承poison。

hand fixture锁定native语义literal；slow oracle单独实现table、transfer与O(VE) propagation，source/depfile/`nm -uC`拒production backend/table/FIFO/validator/canonical/fingerprint/native symbol。结果比较逐字段检查shape/ID/enum/string及每个double bit pattern，property以canonical input bytes证明input unchanged。

## 5. 审查与修正循环

### 5.1 Step 2 设计审查

Step 1 后的 graph、native API、target/SCC、controller和跨阶段审计指出：完整 input和完整 timing oracle不能在 Step 2用默认值伪造；adapter也不能直接链接 legacy `ista_data_manager` target。修订后 Step 2 只发布 graph snapshot/projection，完整 input延至 Step 4，完整 timing oracle延至 Step 6，session聚合延至 Step 7。

三路复审还冻结了 native sparse adjacency、unbound fallback iff条件、map/internal identity、signature-only规则、active-cycle partial oracle、exact wire schema、per-case manifest fingerprint和controller-owned temp→atomic rename协议。最终均以当前规范正文独立 APPROVE。

### 5.2 Step 2 实现与测试审查

实现审查发现并闭环：instance-pin NodeKey 缺少冒号关系、validator/exporter的 O(I×N) 扫描、fallback O(p³) recount，以及过早存在的 `CsrCommittedSnapshot`。对应修复均进入生产 invariant与定点/规模测试，没有通过放宽 validator 或测试绕过。

fresh-process 环境曾在 child flake shell中出现 Tcl/glibc混链。根因是用 GCC15/glibc2.42 的 child shell复用 ECC 根 flake生成的 GCC14/glibc2.40 build目录；从 `/home/shigure/code/ecc` 的根 flake环境构建后 probe编译、链接和运行均通过。这是环境闭包不匹配，不是 CSR target或代码缺陷。

最终独立代码 reviewer 重建并运行全部 `^ista_csr_` 测试，确认 fresh run产生唯一目录和6个nonce repeat artifact；同 case hash稳定，chain/diamond shape与hash互异。代码、测试和边界无剩余 blocker、major或minor。

### 5.3 Step 3 设计、实现与门禁审查

Step 3 v0.4 在编码前完成独立设计复审，冻结 identity 分层、九 buffer 单一真源、exact FIFO、optional transition、schema/parser lane 和 target 边界。实现复审发现并闭环：重复 first-invalidation policy、过大的 test CMake、缺少 production consumer/valueless guard/static-assert exact inventory、缺少 C++ UTF-8 KAT，以及 callback 可绕过 descriptor 与非 sole-primary negative case。修复后共享 policy helper、拆分 CMake、source inventory、descriptor-driven fixture/evaluator 和完整 correctness matrix 均进入正式门禁。

最终 C++ reviewer 对 9 个 core 与 3 个 snapshot translation unit 执行严格 Werror/pedantic compile，并检查 5 个 public header、6 个 contract executable 和全量回归，结论 `APPROVE`、0 finding。schema/parent 与 CMake/isolation 独立 reviewer 同样 `APPROVE`，无剩余 blocker、major 或 minor。

### 5.4 Step 4 实现与formal审查

实现审查闭环了shared encoder字段漂移、binary64阈值措辞、unbound raw/full-local role、ArcKey direct-byte排序与child signature fingerprint domain等finding；修复后deep candidate重冻为3410B/`58cf82…bcd65`、raw为1114B/`ae73fa…3a350`。fresh real probe authoritative relink后controller validation/fresh均通过；const_cast safe/poison自测、overlap无result门、storage oracle及全部inventory/isolation均通过。

最终独立 reviewer 对实际树给出 `APPROVE`，无剩余 finding。

### 5.5 Step 5 实现、红队与终审

实现与复审闭环了table cache B1、插值overflow与arrival-addition overflow的真实production路径、support/cycle FIFO precedence、clock-source name合同、result schema及9个identity member comparator canary。最终source inventory不从actual反推expected，逐个验证16个test objects（其中3个slow-oracle）与6个production objects、共22个owner；slow-oracle子集另受更深隔离，并以cross-directory poison拒绝路径过滤false-green。

algorithm、test-matrix和fresh red-team三路独立复审均已收口；最终red-team独立重跑exact target、13项Step5/chained gate、五seed、`nm`、artifact与行数维护性状态后APPROVE，无剩余blocker/major/minor。

### 5.6 Step 6 实现、矩阵补强与终审

实现与红队闭环了publisher潜在throw、derived scalar/path overflow、rerun Database副本raw `TimingCellArc*`悬挂、supported chain roots、普通disabled与loop-disabled混淆、parallel fixture非法net-load重复、capture seam对NaN/Inf/signed-zero折叠，以及success capture重复约48次SHA等问题。最终publish只含scalar assignment/swap，成功capture在Step 4冻结约束下为17次SHA。

success/failure/atomicity/lifecycle/inventory多路审查逐项补齐singleton、multi-root、parallel、disabled、loop-disabled、strict-valid unsupported guard与current-capture-success证据。最终两路独立reviewer重建目标、运行冻结11项、检查publisher `nm`、format/行数维护性状态/artifact并均给出APPROVE，无剩余finding。

### 5.7 Step 7 实现补强与三路终审

native复审补齐capture throw-first永久消费one-shot、独立run-vs-scatter成功排序，并恢复机械迁移到`STAInterfaceOperations.cpp`的legacy helper精确diagnostic/log语义；lifecycle在init/close cleanup同时抛出时先缓存released handoff并提交closed，再形成诊断。parent复审锁定failure terminal内部native/context/observation清空与closed状态；gate复审补齐18个adapter object、PUBLIC snapshot edge、bridge/publisher dep allow-list及CTest JSON numeric timeout比较。

fresh session lane发现Liberty parser状态不能直接跨顺序native session复用，最终在启动incremental lane前重新读取Liberty完成staging；legacy缺省projection payload及controller协议保持原样，probe最终SHA-256固定为`ce5f3cdc6baf7bbd90ecbf62aab843191d4fde3d7e3b1f7037758a18e08a9bff`，compat文件SHA为`0da3a1b22ffd0ece8198c97854a78e9db342af42c5daad45ebfafb1c9f8fb414`。

native、parent、gate三路最终reviewer均对最终工作树给出`APPROVE`。parent独立复审另运行102个targeted pytest及Ruff check/format、scoped ty；无剩余blocker、major或minor。

### 5.8 Step 8 实现、全局红灯与终审

Step 8历史v0.14先完成设计双审，再由native/CMake与Python两路终审复核opaque边界、wire codec、Popen cleanup、same-fd/no-clobber事务、30项公开负例、Ruff/clang与source inventory；final-closure修复后当前基线冻结为v0.15。七个Python文件最终行数为701/710/706/554/1446/703/702，Workflow/Isolation为786/838；这些数字是维护性建议的状态，不是hard gate。超出建议值来自strict wire/schema、真实Popen/transaction fault matrix和exact provenance inventory，reviewer未发现具体职责混杂或不可读问题，因此明确`APPROVE`；未为压缩行数删除断言、动态生成测试或合并不相关职责。

首次完整`^ista_csr_`回归为76/79，暴露三个此前被窄测试遮蔽的问题：FIFO complete/cycle诊断与frozen manifest不一致；identity schema/session/generation/source比较使用`else if`导致overlap只报告一个typed violation；#119构建产物使用Nix loader却嵌入host Python/expat closure。前两项以最小生产修复闭环：FIFO双向exact message统一，四个identity比较改为顺序独立`if`且scatter仍按typed priority选择；独立复审确认无exact-count或Step3/5/6语义扩散。

#119只对被`.gitignore`忽略的本地`bin/ista_csr_snapshot_binding_contract_test`设置`/lib64/ld-linux-x86-64.so.2` interpreter；最终构建后产物SHA为`bb8241d635c57cf6789bc98b4ec319ca143d147aaa648b21e46c8d3878b9057f`。这是本地build artifact runtime closure workaround，不是源码/CMake修改，也不作为portable wheel证明。

修复后定向#57/#61/#63/#82/#102/#103/#111、Step3–7结构回放、完整CSR chain和三个global label均通过。最终独立修复复审对`CsrReferenceValidator.cpp` SHA `c2449b040be6dee5ff4f4958aebe1c1a00e9ef22b8b45cc1a4e3224b6d40133d`及`CsrTimingResultValidator.cpp` SHA `787ba9be00d96ca369ad966936028d9c702a85645b5a70043c94293632afe110`给出`APPROVE`，无blocker/major/minor。

### 5.9 Step 9正式候选与简化收口

三次正式完整候选都未完成原v0.31的POST→report-transition→FINAL严格来源封口。第1次`8mer1IrHuffA`在capture summary validation阶段拒绝C++合法finite-float词法与Python lexical CANON的差异；binary64值相同。第2次`HSBTG3ktCGcP`的capture/context/reducer/recheck功能链全绿，但POST provenance因`rowset keys differ`拒绝。

第3次`BBXZ6jkc9zDZ`的inner provenance工具返回0，并成功生成POST manifest与primary；外层wrapper随后在`primary_publish`阶段以`capture.records[4].payload evidence directory`拒绝。该记录角色为`summary`，按真实设计指向sibling runroot `step9-controller-run.BBXZ6jkc9zDZ.V3`中的controller result；冻结supervisor镜像策略却要求capture/context/reducer/recheck域内所有ref的直接父目录等于evidence directory。producer接受真实runroot summary而wrapper拒绝同一路径，属于审核路径策略冲突，不是controller、数值比较、reference、scatter或recheck失败。

因此不存在POST completion envelope、report transition或FINAL，不能声称严格provenance成功。POST manifest/primary/inner/outer SHA依次为`374722ee627c98d29351dbee21cbf4690a67e4c96e2b19d5e8cf18e26c4ec15e`、`b0f8e77a213550eaca7b4a29b861720705d96e148b5e96026340296641a1197c`、`7fa0082dd16c034f31ae8af70675ff1ece09177880c457875215309d8b35b9e5`、`0f05d9b62dc1ef7d8c306089e31d3483b4c83443a9ff608f1a5684696225e252`；精确错误文本SHA为`e43900cd38e6077bf1a9da7f25e260ec5e8bdc387fccb08f9e6c6b28be4c5f8e`。用户要求的三轮上限已用尽，后续不再重跑或扩张这套封口，而以完整功能回归、差分一致性和结果一致性完成验收。

## 6. 正确性与回归结果

所有最终结果均在格式化后的工作树重新构建和执行：

| 门禁 | 结果 |
|---|---|
| CMake configure，`BUILD_TESTING=ON` | PASS |
| wheel动作精确目标构建 | 54 targets PASS；最终重链后`ninja: no work to do` |
| Step 8 current v0.15 | fresh `until-fail:3`为3/3 PASS（96.35s、97.08s、96.15s）；CSR/global/Stage0/1/Ruff门禁均通过 |
| Step3–7 chained isolation/inventory | 9/9 PASS，40.27s |
| 完整`^ista_csr_`当前字节 | 79/79 PASS，159.56s；真实fresh-process差分86.58s |
| final global labels（最终重链后） | unit 87/87（78.60s）、property 20/20（0.08s）、smoke 7/7（109.18s） |
| Stage0 / Stage1 focused | 41/41、495/495 PASS |
| parent Stage2定向 | 227 passed，1.36s |
| parent non-PDK全量 | 1667 passed、6 skipped、4 deselected、13 xfailed、2 warnings，21.20s |
| parent canonical Ruff / scoped ty | 17文件check/format PASS；`sta_snapshot.py sta_session.py sta_signoff.py` ty PASS |
| Step 8 local pinned Ruff | `ruff 0.14.13`，exact七文件check PASS、7 files already formatted |
| wheel child-root pinned Ruff | `uvx --from ruff==0.14.13 ruff` exact argv check/format PASS |
| strict C++ Werror/pedantic、`nm`、VALID depfile | PASS；三个Step 8 target无越界native oracle依赖 |
| clang-format 21.1.8 | 239个Git-visible changed/new `.cpp`/`.hpp` PASS；237普通文件，2个刻意反序include probe使用`--sort-includes=0` |
| reference_input / legacy projection / session fresh | PASS；原Step4–7兼容payload、Liberty staging和probe SHA保持冻结 |
| snapshot schema/corpus/compiled parity与safe/poison | PASS；compiled-contract parity 40 descriptors |
| Step 9简化功能验收 | PASS；18/18 pair、36 lanes、capture/context/reducer/recheck及三rowset独立重算一致 |
| Step 9严格POST/FINAL | NOT ACCEPTED；外层`primary_publish`路径策略冲突，未生成completion envelope或FINAL |
| parent/child tracked diff-check、全untracked whitespace与artifact hygiene | PASS |
| plan-review cache修复 | intent `a3df8abbdf29e14eb2f2209f3412e2bdcda859a107affc1dc5d98538b97b17a3`、completion `dad7d36e85c3889f7d7ce05dec333667e79f14ba624efb7bcd506c4b557f4974`；`all_post_absent=true` |
| 行数维护性状态 | 非hard gate；actual、超出原因及review裁决已记录，正确性/证据/可读性/可审计性优先 |

Step 1 的 SHA-256 empty/`abc`/55-byte/56-byte边界与 canonical known answers继续通过。更新后的 instance-pin NodeKey/ArcKey known-answer也由独立 Python重算：

- NodeKey：96 bytes，`389c0aca91c42de7d599100001b56fe03695fdfde1dc42de330263ea59bffd05`；
- ArcKey：428 bytes，`aa58e450651fd1ce78f82d0eecf07297d60bfcd9250d1acf26413085971fd247`。

- raw empty：115B，`572694c6744abdc63d17096251fddc0a7b41381cce8bd9b62432d8e1e191de40`；
- raw complex：1127B，`981c927eea2234d723aed25ae799b30b2a25f6128961c7fece42dd11762a92f5`；
- deep candidate：3410B，`58cf82c5347b1d6bc8f13447690d73bb826d5ff20fb7b9e0eb3865d48c4bcd65`；
- deep raw：1114B，`ae73fa8c86ae17fc0a7b2c06cba46813f258f45023591a117f0c93df4fc3a350`。

child Git-visible/unignored artifact scan clean，没有build/result/session/cache/patch泄漏。parent仅保留8月18–20日已存在且被忽略的旧 `__pycache__`，本轮未生成、未删除；无outer-env unit复跑后 `baseline/__pycache__` 仍不存在。既有ignored source-bin历史产物未被当作门禁证据或清理目标。

## 7. 提交与后续边界

Step 9已按v0.31冻结计划完成6-repeat采集，并在三次严格候选失败后依用户授权以简化功能口径收口。第3次候选的capture/context/reducer/recheck与结果一致性均通过；严格POST/FINAL未通过且不再重试。Step 10随后按child-first、parent-second创建本地提交；本报告所在parent提交完成阶段2本地封存，提交后只做只读审计，不联网、不fetch、不push。

Step 4仍是detached candidate，Step 5仍是Database-free detached backend，Step 6仍只提供lower-level受控write-back；Step 7组合真实token、exclusive owner、capture/commit与parent observation，Step 8/9只增加隔离的验收与描述性证据，不改变production调用路径。Step 10本地提交使用已确认的全局身份和Git当前时间戳；parent报告不预写自身commit SHA，以本报告所在提交作为最终锚点。

## 2026-09-05 第二轮清理同步

signoff 预检现直接构建最终 `StaSignoffRunItem` tuple，删除中间 source model、重复 config 路径验证、重复 context 规范化及由非空输入约束已保证的末端空结果分支。源文件、corner 顺序、目标碰撞和副作用隔离合同不变。Stage 2 real-differential 同时删除无调用的 schema_ref。 验证与范围说明见[第二轮清理报告](stage0-stage6-second-cleanup-report.md)。
