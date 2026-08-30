# 阶段 2 Step 4：Detached Complete Reference Input 详细实施计划

> 状态：v0.2 as-built；Step 4 已本地实现、构建并通过 CSR 48/48，尚未提交或推送
> 日期：2026-08-24
> 前置：Step 1 pure CSR、Step 2 Database graph adapter、Step 3 identity/snapshot pure contract 已完成
> 范围：总计划第 14 节 Step 4；只交付 caller-owned、detached、strict-complete candidate
> 基线：parent ee2563b2d27165d9324d82103cdf28bddb414956；ecc-tools a7355b216b801f72a99d92e77765f49c744148b3
> 提交边界：本步骤不单独提交、不推送；实现与测试仍留在 parent/child 未提交工作树

本计划现同时记录 Step 4 的冻结合同与真实 as-built。完成证据只覆盖 detached complete input、fresh/poison/isolation 与下述 exact inventory；不声称 Step 5 backend、Step 6 scatter/native timing oracle、Step 7 session lifecycle 或数值 parity。

## 1. 阻塞裁决与 schema 冻结

现有类型不能直接 materialize 真实 complete input。编码前必须修正六项 blocker：

1. ArcRecord::output_load 改为 optional 2×2 matrix，以全局二态表达寄生负载不可读；
2. optional path_source 增加 StartSeedAvailability，四种合法组合表达 sequential start而不伪造arrival/slew；
3. raw clock/port/case constraint 使用保序、保重、可 unresolved 的 typed reference，不能只存派生 NodeId；
4. timing-check closure 成为唯一完整真源，per-instance endpoint record只按ordinal引用；
5. TimingTableModel 明确区分 missing、present-empty、0D constant、1D 与 2D；
6. referenced Liberty closure 与 raw parasitic semantic 进入 CsrReferenceInput typed fields，六 payload 只能从 candidate 自身重算。

这些 breaking pre-release 修订已在首个 real complete candidate 前一次性落地；全部 KAT、mutation corpus、storage formula 与 compiled descriptor 已按唯一 1.0.0 shape 重冻。当前构建不接受旧 shape。

## 2. 目标与禁止越界

Step 4 必须从 const Database 和 caller context/token 构造 self-contained candidate，覆盖graph、constraints、timing checks、referenced Liberty、parasitics、start/endpoint、caps、loads、transfers与support reasons；identity固定caller token、generation 0、六个非默认fingerprint；local strict validation后single move-return；建立synthetic+fresh poison和exact CMake门。

Step 4 明确禁止：

- 分配/消费token或接counter/lease；
- 创建、commit或发布snapshot/observation；
- 运行FIFO或因cycle失败；cyclic graph仍返回candidate；
- 链接snapshot、backend、scatter、interface、binding或parent runtime；
- 读取TimingPoint、Arc result maps、Database timing_order、DelayCalculator/cache；
- 新增fallback provenance getter/bulk replacement；这些与native oracle/scatter留Step 6；
- 修改Stage 1十字段record、默认cpu/full或artifact；声称数值parity。
## 3. Self-contained reference schema

### 3.1 StartSeedAvailability 与 structural register

保留StartSeedModel::optional<PathSource>，新增唯一materialization状态：

~~~cpp
enum class StartSeedAvailability : std::uint8_t {
  kMaterialized,
  kUnsupportedSequential,
};
~~~

StartSeedModel继续保存seed_node、path_start_node、clock_tag、2×2 optional arrival/slew、optional CRPR node/transition。只允许四种组合，其余availability/path_source交叉全部非法；candidate unsupported策略令每个sequential instance-pin start的数值lane都absent（不声称native未计算），presence不因其他unsupported reason放宽：

| availability | path_source | arrival | slew | structural fields |
|---|---|---|---|---|
| materialized | null | 四lane全absent | 四lane全present | 只用于nonsequential native-none start；path_start=seed；无CRPR |
| materialized | input | 四lane全present | 四lane全present | nonsequential input start；path_start=seed；无CRPR |
| unsupported-sequential | null | 四lane全absent | 四lane全absent | 任意无register关系的sequential-instance start（含disconnected CK/output/data/other pin）；path_start=seed；无CRPR |
| unsupported-sequential | register | 四lane全absent | 四lane全absent | CK reachable且seed为Instance::clock_pin_name或selected output_pin_name；CK/Q path_start分别selected output/self，CRPR node均为native CK且transition只看selected arc child[0] |

clock reachability只能从typed graph+raw constraints重放，禁止读取is_clock_point或clock result map。顺序为clock map序、每clock ordered raw source原序FIFO、active outgoing raw row序；unresolved source只保留并按native warning语义跳过，disabled/loop-disabled arc跳过，在non-gating sequential clock pin停止。同clock多source/重复/convergence用per-clock visited消重。

successful-full-STA Database是production exporter前提；不同clock map_key汇聚会在native Logger::error处noreturn，因而API前不存在可导出的Database。不得伪造production typed failure或“后clock覆盖”；只允许pure intrinsic validator拒绝人工构造的overlap candidate，并用native full子进程的无result门证明前提。同一map_key的multi-source/duplicate/convergence合法。

clock_tag按以下首个命中项冻结：direct raw source匹配（map序，取该项embedded clock name）→ 任一sequential instance pin取replayed CK owner map_key → 当前clock-point node的reachable owner map_key → nonempty port-constraint clock ref → 首clock map_key → "clk"。clock_tags是所有非空clock map_key、embedded clock name、port clock ref、seed tag与endpoint tag的byte-sort unique union；raw unresolved source不参与reachability但仍进入clock payload。

selected C2Q精确定义为TimingCell.cell_arc_list原序首个is_clock_arc=true项，不按source/graph/disable/reach过滤；存在时Instance::output_pin_name取其sink，否则取port_map byte序首个is_output&&!is_clock port。Instance::clock_pin_name独立取首setup check、无setup则首check，不从C2Q source推断。register iff sequential、native CK reachable且start为CK或selected output；CK/Q path_start分别selected output/self，CRPR node恒为native CK，transition只检查selected arc children[0]：trigger!=none取该值，否则rise（missing/default/empty/none均rise），绝不扫描后续child。reachable CK但selected output为空因NodeId path_start不可表达而malformed_topology；其他sequential start均unsupported-sequential+null、无CRPR。

### 3.2 Optional output_load 全局二态

~~~cpp
using ArcOutputLoadMatrix =
    std::array<std::array<double, kTransitionCount>, kAnalysisCount>;
std::optional<ArcOutputLoadMatrix> ArcRecord::output_load;
~~~

删除has_parasitics；寄生存在严格派生为parasitics.nets非空：

- nets空：每个ArcRecord load都present；真实0是present-zero；
- nets非空：每个ArcRecord都absent；禁止per-net半支持、zero sentinel、RC cache或no-SPEF伪值；
- empty parsed net map用显式empty semantic并回到全present；
- timing-input先编码presence，present才编码四double；absent不编码默认0；
- Step5 backend先过support gate，unsupported不得解引用absent。

no-SPEF load每net只算一次，严格按Net::load_pin_list原序相加：output/inout port取set_load否则0；instance load pin逐analysis/transition取transition cap，缺失取default cap。按arc sink net赋值；禁止arc×fanout重扫。

每个 actual child×load lane 沿用 native binary64 判定 `abs(cap_scale - 1.0) < STA_ERROR`；strict-below 直接使用 load，首个可表示的 `>= STA_ERROR` 值才进入 `ceil` 与 `[0, INT_MAX]` 预检。源码表达式 `1.0 + STA_ERROR` 在 binary64 中实际 round below，`nextafter(...,+∞)` 才进入 ceil 分支。

### 3.3 Raw constraint models

新增RawNodeReference{full_name, optional<NodeId> resolved_node}。ClockConstraintModel保存map_key、embedded_clock_name、ordered RawNodeReference sources、period/edges/propagated等raw字段；PortConstraintModel保存map_key、embedded_port_name、由map_key解析的optional resolved_node及全部presence/value/clock ref；CaseAnalysisConstraintModel保存raw map name、由该name解析的optional resolved_node与case value。

clock/port/case均保留原map/vector顺序、重复、map key与embedded identity不一致及unresolved raw name。raw Database capture接受empty/unresolved source及任意finite period/edge（含负数和0）；NaN/Inf映射illegal_numeric，这不表示public createClock API接受这些值。raw name不可解析时optional NodeId必须absent；一旦present就必须按map-key/full-name从graph唯一解析并exact相等。clock_constraint payload只编码raw identity/value，不编码派生NodeId。

### 3.4 Timing-check endpoint records

新增稳定TimingCheckKind，映射none/setup/hold/recovery/removal/width/period。referenced_library_cells中的ordered check-arc closure是kind/time/transition/children/table唯一完整真源；per-instance ordered record只引用它，不深拷贝instance×Liberty表：

~~~cpp
struct TimingCheckEndpointModel {
  std::string instance_name;
  std::uint64_t referenced_check_ordinal;
  TimingCheckKind check_kind;  // 与closure ordinal交叉校验
  std::string clock_pin_raw_name;
  std::string data_pin_raw_name;
  std::string clock_pin_full_name;
  std::string data_pin_full_name;
  std::optional<NodeId> resolved_clock_node;
  std::optional<NodeId> resolved_data_node;
};
~~~

records严格为instance_map order×referenced check-list ordinal并保序保重；raw local port、kind cross-check须与closure exact，full name无条件按instance:raw_local拼接。clock/data不全局强制resolve；任一full name若能resolve，必须是同instance的non-port node；不可解析（含width/period clock端）保留且不fatal。只有resolved_data_node参与endpoint重算。

保留InstanceRecord::has_timing_checks以减少Step2 wire破坏，但它必须exact-derived为!Instance::get_check_arc_list().empty()并与导出的ordered records交叉一致，不能承载第二份truth。任一record产生timing_check unsupported；endpoint不能依赖NodeRecord::is_data_pin representative bit。

对所有图按GraphBuilder优先级exact重算start：non-gating sequential CK=true；其他clock pin=false；resolved clock source只有input/inout port=true，output port与instance pin=false；其余节点为no-incoming或input/inout port时true。由最后一支形成的unconnected sequential data/other pin start使用unsupported-sequential+null。end先排除clock pin/source，再取no-outgoing、output/inout或任一resolved check data；有outgoing的check data仍是endpoint，ordered vectors与node bool逐项exact。

### 3.5 TimingTable present-empty

| 状态 | shape | native语义 |
|---|---|---|
| missing | present=false，variables none，axes/values空 | delay skip/fallback；slew skip/pass-through |
| present-empty | present=true，values空 | table存在，候选0 |
| 0D constant | present=true，variables none，axes空，values=[x] | x |
| 1D | 一个variable/axis，values exact | native 1D |
| 2D | 两variables/axes，values exact product | native 2D |

present-empty仍验known variables、variable2关系、axis数、finite/strict-increasing；axis可空，跳过nonempty/product/value-count。populated table保持exact product。present-empty delay/slew为0，不走missing fallback；五态canonical KAT必须不同。
### 3.6 Referenced Liberty closure

输入新增referenced_library_cells，按所有instance引用的唯一cell name canonical byte序排列。每项显式missing/present；present保存：

- library name、cell sequential/clock-gating/macro与timing roles；
- 全部ports的name、direction、clock role、default及transition caps；
- ordered cell arcs的source/sink、constant fallback、flags、ordered children；
- ordered check arcs的raw ports、kind/time/clock transition、ordered children；
- child signature/sense/index/transitions/condition、resolved time/cap scales、thresholds/derate；
- delay/slew/check table的presence、variables、axes、values。

closure排除unused cells、power/leakage/comment/area/function、raw pointer和Arc derived maps。per-arc transfer仍为backend输入，并须与closure对应语义一致；unbound unit-delay、empty-child、missing、present-empty、constant、1D/2D各可区分。

### 3.7 Typed raw parasitic semantic

输入新增DB-free typed model：

- top level为raw capacitance/resistance unit strings与ordered nets；
- net按原map byte-order保存map key、embedded name、lumped cap；
- node按原map byte-order保存key、embedded name、cap、x、y；
- resistor vector保留parser原序：source、sink、resistance；
- 数值使用Database已存PF/OHM semantic，全部finite；物理cap/res非负。

nonempty nets要求units完整。nets空规范化为显式empty-domain，忽略残留path/units并要求candidate unit fields空。SPEF path变化不改hash；unit/net/node/cap/coordinate/resistor/order/lumped任一变化须改parasitic component。投影后若typed parasitic nets非空而context.rc_corner=="__no_rc_corner__"，typed capture精确失败invalid_analysis_context，identity赋值与candidate return均为0。

### 3.8 Validator与storage连锁

CsrReferenceValidator.hpp保留既有validateReferenceInput(input)及其他现有validator声明，并新增validateAnalysisContextIntrinsic、validateReferenceInputIntrinsic、validateReferenceInputForSession，四者definition各1。input intrinsic恰调analysis-context intrinsic与唯一validateParasiticContextCrossField各1，再验证closure/load/seed/check/table/mirror/reason及索引/presence/numeric；strict顺序先semantic-safe shape/cross-field、后identity。

validateReferenceInput恰调用validateReferenceInputIntrinsic×1和makeReferenceInputIdentity×1，再要求candidate token非0、generation0及六hash exact；任意nonzero token本身合法。validateReferenceInputForSession只调用validateReferenceInput×1再校验expected_token非0且exact相等，禁止直接调用intrinsic/identity helper；既有其他validateReferenceInput consumers保留。exporter除pre-DB context intrinsic外只调用ForSession×1。全部input validator仍接受cycle且FIFO调用0。

validateTimingResult先走unsupported support gate；若input.unsupported_reasons非空，立即返回unsupported violation，绝不进入seed/load/recurrence semantic分支。validateComputationResult据此表达unsupported；CsrTimingResultValidator/Result tests覆盖no-throw与absent lane。

CsrSnapshotStorage visitor纳入seed availability、optional path-source、timing-check及library/parasitic nested storage；optional<fixed 2×2 matrix>已完整包含在ArcRecord vector元素的sizeof slot中，engaged/disengaged均无独立backing，禁止递归追加计数。same-ABI独立formula-delta oracle同步，snapshot target三source/link不变。

## 4. Detached API、失败与原子构造

### 4.1 Public API

~~~cpp
struct CsrReferenceInputExportFailure {
  CsrCaptureCode code;
};
using CsrReferenceInputExportResult =
    std::variant<CsrReferenceInput, CsrReferenceInputExportFailure>;

[[nodiscard]] CsrReferenceInputExportResult
exportCsrReferenceInputCandidate(
    const Database& database,
    const StaAnalysisContext& canonical_context,
    std::uint64_t caller_session_token);
~~~

token0在任何Database read前抛invalid_argument，且不分配替代token。context先在DB read前strict validate；投影后另做typed context/parasitic cross-field，两处非法均返回invalid_analysis_context且无candidate/identity。其余typed failure无partial：

- key collision → semantic_key_collision；
- NaN/Inf、负cap/res/load、cap ceil越界 → illegal_numeric；
- 除合法present-empty外坏table → invalid_table_shape；
- 可导出Database中的native结构或model invariant → malformed_topology；
- active_cycle在Step4不产生，cycle graph成功；different-clock-map-key overlap只属于API前native no-result前提与artificial pure-candidate rejection。

bad_alloc等资源异常传播。local builder完成前置检查后若validateReferenceInputForSession仍报violation，抛logic_error；不得按violation字符串猜capture code。public API在Step4只有tests/probe调用，production caller精确为0。

### 4.2 原子构造顺序

1. token非0；
2. 调用validateAnalysisContextIntrinsic做strict pre-DB检查；bad context时全部Database getter及exportCsrGraphSnapshot调用均为0；
3. 恰好一次exportCsrGraphSnapshot；
4. local投影constraints/checks/library/parasitics/seeds/endpoints/caps/loads/reasons；
5. 全部semantic-safe cross-field/numeric preflight；adapter恰调validateParasiticContextCrossField×1，在identity前拒绝nonempty SPEF+"__no_rc_corner__"；
6. makeReferenceInputIdentity(local, caller token, 0)内部调用唯一payload builder与makeSnapshotIdentity，identity只赋一次；
7. 对完整local input恰好调用一次validateReferenceInputForSession，validator独立调用同一identity helper重算；
8. 仅成功single move-return。

失败销毁local state。API不得触碰FIFO、counter、snapshot/reducer、observation、commit、binding、backend、scatter或Database write。

## 5. 六payload与identity

### 5.1 唯一builder

新增pure buildReferenceFingerprintPayloads(const CsrReferenceInput&)，忽略source_identity，只读candidate typed fields；不接受caller bytes、arbitrary supplement或默认payload。新增唯一makeReferenceInputIdentity(input, token, generation)，内部调用payload builder与makeSnapshotIdentity；exporter与validateReferenceInput各调用该helper一次，其他production source不得直接组装FingerprintPayloads或为reference input调用makeSnapshotIdentity。

每个payload先写domain/version/empty marker，语义为空也不得empty vector。makeSnapshotIdentity分别hash前五component，再将五hash与payloads.timing_input组合为第六hash。self validator以candidate token/gen重算；bound validator另做session equality，不能把任意nonzero token替换误报为self-identity损坏。

canonicalReferenceInputBytes只用于whole-candidate determinism/poison对比，绝不能塞进timing_input或冒充component。

### 5.2 精确分区

| component | fields |
|---|---|
| topology | constraint-independent NodeKey/ArcKey、dense lookup、CSR/raw row/root、direction/port/instance-cell ownership、arc type/raw disable/loop/rank；ArcKey既有library signature仍属于key |
| clock_constraint | 只含ordered raw clocks/source/period/edges/propagated、port constraint全部presence/value、case analysis；不含resolved ID/mirror |
| library | referenced_library_cells完整raw closure |
| corner | canonical StaAnalysisContext bytes |
| parasitic | typed explicit-empty或完整raw semantic |
| timing_input unique | raw resolved_node、replayed clock owner及所有derived mirror，另含lane/start/end、roles/eligibility、tags/seed、endpoint/check structure、caps/loads/transfer/support |

ordered start/end、derived role/eligibility不得进topology，避免clock drift被误报topology invalidation。

### 5.3 Candidate tamper/reject matrix

| candidate field flip | strict outcome |
|---|---|
| valid canonical field变更但identity不变；任一component/composite SHA篡改 | validateReferenceInput拒绝identity mismatch |
| bad shape/index/presence、raw/resolved/owner/mirror关系、seed/check/load/library/parasitic cross-field | intrinsic在hash前拒绝；只重签identity仍失败且no-throw |
| raw或derived字段变更并原子更新全部等价mirror，再用唯一helper重签 | self validator成功；严格符合5.4 exact changed-set |
| token=0或generation!=0 | self validator拒绝 |
| token A替换为任意nonzero B，字段/hash不变 | self validator成功；ForSession(expected=A)拒绝，expected=B成功 |
| artificial different-clock-map-key overlap | pure intrinsic拒绝malformed candidate；不映射production capture outcome |

每例比较完整input/outcome，失败不得产生partial candidate。real export为caller nonzero token、generation0、六个lowercase nondefault SHA-256。

### 5.4 Raw DB mutation/re-export changed-set matrix

| raw Database mutation | exact changed fingerprints |
|---|---|
| NodeKey、非library ArcKey、CSR/raw row/rank/root/raw flags | topology + timing_input composite |
| ArcKey table presence/variable signature | 原子重导key+closure+transfer；topology + library + composite |
| referenced Liberty axis/value/fallback | 原子重导closure+transfer；library + composite |
| referenced port cap | 原子重导closure+cell_cap，no-SPEF时同时重导load；library + composite |
| referenced check raw port/kind/order | 原子重导closure+ordinal/resolution；library + composite |
| raw clock/port/case constraint | 原子重导constraint+reach/tag/eligibility/seed/reason；clock_constraint + composite，topology不变 |
| context | corner + composite |
| parasitic unit/net/node/resistor/lumped semantic | 原子重导typed model+全arc load absent+reason；parasitic + composite |

逐字段re-export断言列出的set全变、未列component全不变；不存在抽象“derived-only raw mutation”行。reserve/capacity、metadata与poisoned derived output另由isolation gate证明六hash全不变；candidate-tamper与raw-mutation corpus不得混为一个测试。
## 6. Native投影与support completeness

- constraints覆盖clock/port map key与embedded identity、ordered raw names/重复/unresolved、任意finite period/edges、全部port presence/value与case analysis；raw payload不混入resolved ID；
- eligibility唯一公式：active=!disabled&&!loop_disabled；seq_clock_sink=net arc&&sink sequential CK；level=active；arrival=active&&!seq_clock_sink；slew=active&&!(seq_clock_sink&&clock_reachable[sink])；clock=replayed_clock_arc；
- clock overlap按3.1 successful-full前提/native no-result/pure artificial rejection分层；
- divider iff net arc两端均可解析instance pin、source instance引用的TimingCell present且sequential&&!gating&&!macro、sink full_name等于sink owner clock_pin_name；每个net arc is_disabled须exact等于该predicate，loop_disabled独立；不要求source为selected output、arc clock flag、active/reachable/replayed；reason按下表exact iff派生并按enum序去重：
- referenced cell missing/present、all ports/arcs/checks与resolved units完整投影，不扫whole unused library；
- transfer精确区分unbound1.0、bound empty-child delay_min/max、missing fallback、present-empty0、constant、1D/2D；
- endpoint required保存output-delay presence与native clock/fallback规则；period按endpoint tag查clock map_key，未命中取首clock period，再无clock取0，命中值只要求finite并可为负；NaN/Inf为illegal_numeric；timing-check required不伪造numeric；
| reason | exact iff |
|---|---|
| parasitic_net | typed parasitic nets非空 |
| sequential_instance | 任一InstanceRecord为sequential |
| sequential_launch | 任一start seed为register |
| timing_check | 任一per-instance timing-check endpoint record |
| crpr | 任一register seed的CRPR node/transition成对present；XOR非法 |
| propagated_clock | 任一raw clock propagated flag为true |
| clock_tree_fanout | 任一replayed clock arc存在（按当前native/validator实义） |
| clock_gating_or_divider | 任一gating instance或上述divider；不要求reachable，普通replayed clock arc只贡献clock_tree_fanout |
| conditional_timing_arc | 任一referenced child sdf_cond非空 |
| case_analysis | raw case-analysis records非空 |

unsupported仍是成功candidate，不读取或回用native final value；任一reason/mirror单独篡改即使重签也由intrinsic拒绝。

复杂度为O(N+E+K+reachable-clock+referenced-library-bytes+parasitic-bytes)，canonical sorting保留既有log因子；禁止instance×node、arc×fanout、arc×whole-library重扫。

## 7. 文件、target与CMake inventory

### 7.1 Production文件

pure header DAG冻结为Primitives <- NativeModels <- Types，禁止反向include：

- source/data_manager/adapter/csr/CsrReferencePrimitives.hpp：NodeKey/ArcKey、table/library signatures、strong IDs、enums、lane aliases、analysis context与identity primitives；
- source/data_manager/adapter/csr/CsrReferenceNativeModels.hpp：include Primitives，从603行Types移出table/transfer/raw constraint/seed/check/library/parasitic models；
- CsrReferenceTypes.hpp：include NativeModels，只保留input/result/outcome等组合；
- CsrReferenceCanonicalEncoder.hpp/.cpp：从582行CsrFingerprint.cpp移出typed canonical encoder；
- CsrReferenceFingerprintPayload.hpp/.cpp：六component builder与makeReferenceInputIdentity；
- source/module/timing_csr/CsrReferenceNativeModelValidatorInternal.hpp与CsrReferenceNativeModelValidator.cpp：从556行ConstraintValidator移出model/table/presence/numeric/cross-field validation。

窄修改CsrFingerprint.hpp/.cpp与Input/Constraint/TimingResult/Arc validators。Fingerprint.cpp不再增长，新增/重写production、C++ test helper与Python文件均<700行。483行CsrSnapshotTestFixture.cpp及既有634行projection_canonical.py、617行projection_controller_selftest.py均不增长；新增CsrReferenceInputStorageOracle.cpp承接新availability/check/parasitic/load same-ABI公式，test-only独立wire/raw projector拆分见8.1。

adapter新增：

- CsrReferenceInputAdapter.cpp：public API与single-return coordinator；
- CsrReferenceInputAdapterInternal.hpp：local state/helper；
- CsrConstraintExport.cpp；
- CsrClockSeedExport.cpp；
- CsrTimingCheckExport.cpp；
- CsrLibertyExport.cpp；
- CsrLoadExport.cpp；
- CsrParasiticExport.cpp。

adapter窄修改TimingGraphCsrAdapter.hpp；既有六个Step2 source职责不变。snapshot只改CsrSnapshotStorage.cpp，不新增source。

### 7.2 Native const getter闭集

只按实际读取补窄const overload：

- Database.hpp：constraint/parasitic；
- TimingConstraint.hpp：clock/port/case maps；
- TimingClock.hpp：name/source；
- TimingPortConstraint.hpp：port/clock names；
- TimingCell.hpp：library name、port/cell-arc/check lists；
- TimingCellPort.hpp：name/transition caps；
- TimingTable.hpp：axes/values；
- TimingCheckArc.hpp：clock/data ports、timing arc list；
- Net.hpp：driver/load/pin lists；
- Instance.hpp：C2Q arc；
- ParasiticLibrary/Net/Node/Resistor.hpp：strings、maps/vectors、stored semantic。

禁止const_cast、read-side operator[]、STADM、TimingPoint value getter、Arc result/fallback getter；已有const getter不重复改。

### 7.3 Exact production target source/link

ista_timing_csr_core仍DB-free、无direct link，SOURCES精确12：

~~~text
TimingSemanticKey.cpp; CsrFingerprint.cpp; CsrReferenceCanonicalEncoder.cpp;
CsrReferenceFingerprintPayload.cpp; CsrReferenceValidator.cpp;
CsrSnapshotIdentityValidator.cpp; CsrFifoLevelization.cpp;
CsrReferenceInputValidator.cpp; CsrReferenceConstraintValidator.cpp;
CsrReferenceNativeModelValidator.cpp; CsrTimingResultValidator.cpp;
CsrTimingResultArcValidator.cpp
~~~

ista_timing_graph_csr_adapter SOURCES精确13：既有CsrGraphEncoding.cpp、CsrGraphValidator.cpp、TimingGraphCsrAdapter.cpp、TimingGraphCsrArcExport.cpp、TimingGraphCsrAdjacency.cpp、NativeGraphProjection.cpp，加CsrReferenceInputAdapter.cpp、CsrConstraintExport.cpp、CsrClockSeedExport.cpp、CsrTimingCheckExport.cpp、CsrLibertyExport.cpp、CsrLoadExport.cpp、CsrParasiticExport.cpp。direct/interface link仍精确PUBLIC core、PRIVATE database_headers。

ista_timing_csr_snapshot_contract SOURCES仍精确CsrSnapshotStorage.cpp、CsrSnapshotObservationValidator.cpp、CsrSnapshotObservationTransition.cpp，PUBLIC只链接core。Step4不进ista_source/module/interface，不新增adapter→snapshot。

### 7.4 CMake/isolation文件

- 更新core/adapter source/object exact inventory与configure-time same-inventory assertion；snapshot production source/link inventory不变；
- Step4 probe源码唯一为`src/operation/iSTA/test/reference_input/StaCsrReferenceInputProbe.cpp`；Step2 projection目录不得新增或复用同名源码，8-target exact SOURCES、configure/source/depfile inventory与wheel均按前述唯一位置断言；
- 新增CsrReferenceInputTests.cmake、CsrReferenceInputIsolationTests.cmake并由test/CMakeLists显式include；configure期对8个functional target及public-header target逐一断言exact SOURCES、LINK_LIBRARIES/COMPILE_OPTIONS且无extra/transitive伪装；
- test-only CsrReferenceInputRawProjection.hpp唯一拥有DB-free raw DTO/API与enum token表，仅stdlib+Database forward declaration；四个Raw*Projector cpp及8.1允许的test/probe TU可include，production source/depfile include精确0；
- CheckCsrStep4SourceInventory.cmake冻结exporter定义1/production caller0、graph export1；四validator definition各1；input intrinsic→context intrinsic+validateParasiticContextCrossField各1，self→input intrinsic+identity helper各1，ForSession→self×1且direct intrinsic/helper0，exporter→ForSession×1、pre-DB context×1、post-projection crossfield×1；既有self consumer allow-list/count不变；crossfield helper definition1/direct callers仅adapter+input intrinsic，payload builder与makeSnapshotIdentity的reference-input direct caller仅identity helper，identity helper仅exporter+self调用；
- 同一inventory冻结Step4 FIFO调用0、当前三个production consumer不变；Step5/Step7实现后才分别成为计划中的第4/第5 consumer，不得提前增加；
- failure executable证明pre-DB bad context/token时DB getter/graph export/publish均0；SPEF+sentinel时context intrinsic1、graph/parasitic projection/crossfield各1，identity helper/ForSession/publish均0；
- 更新core/adapter/snapshot compiler depfile与allowed header inventory；adapter拒绝singleton/interface/binding/GraphBuilder/propagator/calculator/analyzer/snapshot/backend/scatter及derived result API；
- CsrSnapshotStorageContractTest target追加独立CsrReferenceInputStorageOracle.cpp，CsrSnapshotTestFixture.cpp保持483行；
- wheel逐名build下列8 functional targets及public-header target，再分别运行ista_unit/ista_property/ista_smoke且均用--no-tests=error。

## 8. Formal测试矩阵

### 8.1 八个functional targets与public-header gate

下表SOURCES为八个functional target完整cpp列表；前六CTest均LABELS=ista_unit、TIMEOUT=60，property每seed为ista_property/60，probe只由fresh CTest驱动：

test-only wire精确拆为IndependentEncoding/IndependentGraphEncoding/IndependentModelEncoding三个cpp；raw projection精确拆为RawProjector/RawConstraintProjector/RawLibraryProjector/RawParasiticProjector四个cpp，并共享唯一CsrReferenceInputRawProjection.hpp。前者不调用production encoder/payload helper，后者只读冻结raw allow-list；禁止glob、隐式OBJECT库或表外source。

| target | exact SOURCES | exact direct links |
|---|---|---|
| ista_csr_reference_input_export_contract_test | CsrReferenceInputExportContractTest.cpp; CsrReferenceInputTestFixture.cpp; CsrReferenceInputNativeFixture.cpp; CsrReferenceInputIndependentEncoding.cpp; CsrReferenceInputIndependentGraphEncoding.cpp; CsrReferenceInputIndependentModelEncoding.cpp; CsrReferenceInputRawProjector.cpp; CsrReferenceInputRawConstraintProjector.cpp; CsrReferenceInputRawLibraryProjector.cpp; CsrReferenceInputRawParasiticProjector.cpp | adapter; database_headers |
| ista_csr_reference_input_failure_test | CsrReferenceInputFailureTest.cpp; CsrReferenceInputTestFixture.cpp; CsrReferenceInputNativeFixture.cpp | adapter; database_headers |
| ista_csr_reference_transfer_contract_test | CsrReferenceTransferContractTest.cpp; CsrReferenceInputTestFixture.cpp; CsrReferenceInputNativeFixture.cpp; CsrReferenceInputRawProjector.cpp; CsrReferenceInputRawConstraintProjector.cpp; CsrReferenceInputRawLibraryProjector.cpp; CsrReferenceInputRawParasiticProjector.cpp | adapter; database_headers |
| ista_csr_reference_support_contract_test | CsrReferenceSupportContractTest.cpp; CsrReferenceInputTestFixture.cpp; CsrReferenceInputNativeFixture.cpp; CsrReferenceInputRawProjector.cpp; CsrReferenceInputRawConstraintProjector.cpp; CsrReferenceInputRawLibraryProjector.cpp; CsrReferenceInputRawParasiticProjector.cpp | adapter; database_headers |
| ista_csr_reference_fingerprint_components_test | CsrReferenceFingerprintComponentsTest.cpp; CsrReferenceInputTestFixture.cpp; CsrReferenceInputIndependentEncoding.cpp; CsrReferenceInputIndependentGraphEncoding.cpp; CsrReferenceInputIndependentModelEncoding.cpp | core only |
| ista_csr_reference_poison_isolation_test | CsrReferencePoisonIsolationTest.cpp; CsrReferenceInputTestFixture.cpp; CsrReferenceInputNativeFixture.cpp; CsrReferencePoisonSupport.cpp; CsrReferenceInputRawProjector.cpp; CsrReferenceInputRawConstraintProjector.cpp; CsrReferenceInputRawLibraryProjector.cpp; CsrReferenceInputRawParasiticProjector.cpp | adapter; database_headers |
| ista_csr_reference_input_property_test | CsrReferenceInputPropertyTest.cpp; CsrReferenceInputTestFixture.cpp; CsrReferenceInputNativeFixture.cpp; CsrReferenceInputIndependentEncoding.cpp; CsrReferenceInputIndependentGraphEncoding.cpp; CsrReferenceInputIndependentModelEncoding.cpp; CsrReferenceInputRawProjector.cpp; CsrReferenceInputRawConstraintProjector.cpp; CsrReferenceInputRawLibraryProjector.cpp; CsrReferenceInputRawParasiticProjector.cpp | adapter; database_headers |
| ista_csr_reference_input_probe | reference_input/StaCsrReferenceInputProbe.cpp; CsrReferenceInputNativeFixture.cpp; CsrReferencePoisonSupport.cpp; CsrReferenceInputIndependentEncoding.cpp; CsrReferenceInputIndependentGraphEncoding.cpp; CsrReferenceInputIndependentModelEncoding.cpp; CsrReferenceInputRawProjector.cpp; CsrReferenceInputRawConstraintProjector.cpp; CsrReferenceInputRawLibraryProjector.cpp; CsrReferenceInputRawParasiticProjector.cpp | adapter; ista_interface; ista_source; idm |

新增ista_csr_reference_public_headers_test，exact SOURCES为CsrReferencePublicHeadersMain.cpp，public_header/下Primitives、NativeModels、Types、CanonicalEncoder、FingerprintPayload、Fingerprint、ReferenceValidator、TimingGraphCsrAdapter八个HeaderTest.cpp、CsrReferenceHeaderIncludeOrderTest.cpp及CsrReferenceInputRawProjectionHeaderTest.cpp；direct links精确adapter+database_headers，COMPILE_OPTIONS精确-Wall;-Wextra;-Werror;-pedantic，CTest为ista_unit/60。

八个production HeaderTest及test-only RawProjection HeaderTest各自只含对应header一个include；include-order TU按Types→NativeModels→Primitives逆DAG顺序include三者。configure/source/depfile gate冻结header/TU一一对应、无漏重，并证明core与raw DTO header不因target link偷带Database include。

adapter/database_headers分别指ista_timing_graph_csr_adapter/ista_timing_database_headers，core指ista_timing_csr_core。另注册controller_validation与controller_selftest为ista_unit/60，fresh_process为ista_smoke/300；所有Python CTest统一经cmake -E env PYTHONDONTWRITEBYTECODE=1运行。Step2 controller self-test必须原样重跑，不能修改既有probe/wire schema来伪装Step4 coverage。

### 8.2 Unit/property/negative

- table：missing、present-empty 0D/1D/2D、constant、bad variable/axis/product、五态KAT/native parity；
- raw constraint：map key≠embedded identity、source顺序/重复/unresolved与optional-ID absent/present exact；empty source及raw Database finite负/零/正period/edges成功，NaN/Inf为illegal_numeric；
- load：no-parasitic全present、parasitic全absent、empty map回present、present-zero≠absent、order/scale/INT_MAX边界；
- seed/start：四合法组合/非法交叉、四优先start与sequential absent；first is_clock_arc选取、clock-pin/check独立、missing-C2Q port_map fallback、empty output malformed，children[0] empty/default/none/rise/fall及later-child ignored逐项×reachable/unreachable；覆盖unconnected data/other/internal raw source；
- check：closure-only full truth、instance ordinal/kind mirror、重复/保序/nonrepresentative/outgoing data、raw/full unresolved width/period、has_timing_checks exact-derived；
- parasitic/transfer：逐raw字段、empty规范化、NaN/Inf/negative、missing/unbound/empty-child、table/fallback/sense/threshold/derate/unit；
- support：每reason、overlap、sort/dedup/support-first；gating、reachable/unreachable divider、ordinary replayed clock-only fanout、missing source cell、source非selected output、macro/nonseq/port端、wrong disabled及loop-disabled正交反例；different clock map_key仅native子进程无result；
- API/identity：四validator nested call-count、保留既有self consumers、token0 pre-DB throw、bad context、nonempty SPEF+no-RC投影后invalid_analysis_context且candidate/identity 0、self token替换与ForSession绑定、gen0、cycle成功、资源异常、failure no-partial；
- result/storage：unsupported立即return且no-throw/no absent dereference；fixed optional matrix no recursive backing；visitor与独立same-ABI oracle exact；
- mutation：candidate field-flip/reject矩阵与raw DB mutation/re-export changed-set矩阵逐项独立覆盖；
- property seeds固定1/7/42/20260820/0xdeadbeef，覆盖round-trip、determinism、atomicity、cycle/FIFO0与nonempty shape；
- isolation：source/object/include/depfile/callsite双向exact，每个prohibited symbol/header有negative fixture。

### 8.3 Synthetic poison

逐family poison TimingPoint level/is_clock_point/scalars、effective/physical五组clock maps、data slew/path；Arc scalar及transition/input-output/graph/timing-arc maps；Database timing_order。先逐family证明before/after canary与exact touched mask，再要求pre/post canonicalReferenceInputBytes、source_identity、六hash、raw input projection exact相同且strict-valid。

Step4不得为私有timing_arc_delay_fallback_key_set新增getter。行为canary：对DB Arc用update_timing_arc_delay(..., true)建立fallback；复制Arc，对副本施加普通min/max不会替换而fallback会无条件替换的non-initial update，再从公开timing_arc_delay_map观察差异。它只证明私有provenance被poison而exporter未读；真正getter/bulk replacement留Step6。

### 8.4 Fresh full-STA、exact wire与self-test

不新增checked-in Step4 manifest。严格复用src/operation/iSTA/test/baseline/manifest.json及Step2 load_case_descriptors：每个normalized descriptor exact绑定name/top/expected_clock与tech_lef/cell_lef/liberty/verilog/sdc五条受限路径，逐文件复算declared SHA，再按既有canonical descriptor重算input_case_sha256；chain/diamond descriptor SHA必须不同。runtime repeat_index、run_nonce、canonical context、固定session_token=1和exclusive temp path只由controller逐slot生成，不写回manifest。

schema精确为src/operation/iSTA/test/reference_input/schema/reference_input_result_v1.schema.json与reference_input_controller_v1.schema.json；所有object递归additionalProperties=false。probe exact keys为schema const ista-csr-reference-input-probe/1、name/top/expected_clock、context exact {liberty_corner,temperature,rc_corner}、repeat_index、run_nonce、input_case_sha256、session_token、pre_candidate_wire_hex、post_candidate_wire_hex、pre_raw_projection_hex、post_raw_projection_hex、canaries、complete=true；u64拒绝bool。每个canary exact {family enum,pristine_typed_bytes_hex,before_typed_bytes_hex,after_typed_bytes_hex}，按冻结family序恰好一次；probe schema故意没有candidate/raw/canary SHA或touched mask，任何canned hash字段均因extra key拒绝。

三个Independent*Encoding.cpp输出独立test-only full-candidate envelope，domain固定ista-csr-reference-input-test-wire/1.0.0，按固定顺序编码完整source_identity及CsrReferenceInput每个logical typed field：context、graph/lookup/CSR、raw constraints/check records、referenced closure、raw parasitics、ordered start/end、clock tags/seeds/endpoints、caps/optional loads/transfers/support。它不同于production canonicalReferenceInputBytes，不是持久化格式；三个源及Python侧不得include/import/call production CanonicalEncoder、FingerprintPayload builder或makeReferenceInputIdentity。

四个Raw*Projector.cpp的derived-free allow-list仅含Database graph containers、port/instance及ordered pins/CK/Q/C2Q、net driver/load原序、raw clock/port/case、ordered timing checks、referenced Liberty与raw parasitics；排除TimingPoint、Arc timing/result state、timing_order、native level、effective/physical clock maps和其他derived output。CsrReferenceInputRawProjection.hpp是下表test-only DTO/字段序的唯一真源，不include production types/encoder/payload。

| raw DTO | exact fields/presence order |
|---|---|
| root | nodes, instances, arcs, nets, clock_constraints, port_constraints, case_constraints, timing_checks, referenced_library_cells九个vector，最后optional parasitics |
| node/instance | node={map_key,full_name,is_port,direction,instance_name}；instance={map_key,cell_name,sequential,gating,macro,clock/data/output pin name,ordered pin names,optional selected_clock_arc{source,sink,ordered child trigger}}；presence按首is_clock_arc选择 |
| arc/net | arc={native rank,source,sink,kind,owner,library source/sink port,clock/disabled/loop flags}；net={map_key,name,ordered drivers,ordered loads} |
| constraints/check | clock={map_key,embedded name,ordered raw sources,period,rise/fall edges,propagated}；port={map_key,embedded port,clock,input delay[max,min],input transition,output delay[max,min],output load optionals}；case={map_key,raw name,value}；check={instance,cell,ordinal,kind,raw/full clock,data names} |
| library | {library/cell name,present}; present payload按roles→units/derate/thresholds→port_map byte序→cell_arc_list原序→check arcs；port固定name/direction/clock/output/cap lanes，arc含is_clock_arc及ports/delay/min/max/flags/ordered children，child固定signature/scales/thresholds/rise-fall tables |
| table/parasitic | table={present; if present variable1,variable2,ordered axes,values}；parasitic optional payload={source path,units,ordered nets{map_key,name,total cap,ordered nodes{map_key,name,cap,x,y},ordered resistors{source,sink,resistance}}} |

raw domain是单个length-prefixed string ista-csr-reference-input-raw/1.0.0。u64/count/string byte-length为BE；bool/presence及header显式赋值的每类enum token为u8；optional为00或01+payload；i32按two's-complement bits BE；double为finite-class u8 00+IEEE-754 u64 BE，-0归+0且非finite拒绝。fixed lane顺序按表，map按native byte order，vector保持原序/重复，禁止sort/dedup；decoder checked-count并拒绝bad tag/enum、truncation与trailing byte。

empty-root KAT为9个count=0+absent parasitic：hex `0000000000000022697374612d6373722d7265666572656e63652d696e7075742d7261772f312e302e3000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000`，115 bytes，SHA-256 `572694c6744abdc63d17096251fddc0a7b41381cce8bd9b62432d8e1e191de40`；C++/Python各自literal锁定。另以unresolved duplicate clock、negative/zero edge、missing-C2Q、present-empty table与parasitic order做nonempty cross-language KAT。
complex raw KAT 为1127 bytes、SHA-256 `981c927eea2234d723aed25ae799b30b2a25f6128961c7fece42dd11762a92f5`。deep KAT 另锁定 direct ArcKey byte order：candidate 3410 bytes、SHA-256 `58cf82c5347b1d6bc8f13447690d73bb826d5ff20fb7b9e0eb3865d48c4bcd65`；raw 1114 bytes、SHA-256 `ae73fa8c86ae17fc0a7b2c06cba46813f258f45023591a117f0c93df4fc3a350`。deep raw native role 使用 full name `u:Y`，candidate closure 使用 cell-local `Y`。

canary总数固定17，ordinal即touched bit；common scalar/map编码沿用independent canonical规则，map entry保native key order，clock-map payload内effective先于physical：

| i | exact family token | typed payload field order | required-delta leaves |
|---:|---|---|---|
| 0 | timing_point_level | point key, level i32 | level |
| 1 | timing_point_is_clock_point | point key, bool | is_clock_point |
| 2 | timing_point_scalars | point key, arrival,required,slack,launch_time,predecessor,clock_name,predecessor_arc_idx | arrival, required, slack, launch_time, predecessor, clock_name, predecessor_arc_idx（7项全变） |
| 3 | timing_point_clock_arrival_maps | point key, effective map, physical map | effective map与physical map两侧 |
| 4 | timing_point_clock_slew_maps | point key, effective map, physical map | effective map与physical map两侧 |
| 5 | timing_point_clock_predecessor_maps | point key, effective map, physical map | effective map与physical map两侧 |
| 6 | timing_point_clock_predecessor_arc_delay_maps | point key, effective map, physical map | effective map与physical map两侧 |
| 7 | timing_point_clock_predecessor_transition_maps | point key, effective map, physical map | effective map与physical map两侧 |
| 8 | timing_point_data_slew_map | point key, analysis/transition/value map | data_slew_map |
| 9 | timing_point_path_state_map | point key, analysis/path-source/transition/tag/state map | 每个state固定12项依次全变：arrival:double, slew:double, launch_time:double, start_point:string, predecessor:string, clock_name:string, crpr_clock_pin:string, predecessor_arc_idx:u64, predecessor_arc_delay:double, trans_type:u8 enum, predecessor_trans_type:u8 enum, crpr_clock_trans_type:u8 enum |
| 10 | arc_scalars | arc stable key/rank, delay,delay_max,delay_min | delay, delay_max, delay_min（3项全变） |
| 11 | arc_transition_maps | arc key/rank, trans_delay map, trans_type map | trans_delay map与trans_type map两张 |
| 12 | arc_input_output_delay_map | arc key/rank, analysis/input/output/value map | input_output_delay_map |
| 13 | arc_graph_delay_map | arc key/rank, analysis/input/output/value map | graph_delay_map |
| 14 | arc_timing_arc_delay_map | arc key/rank, timing-arc-index/analysis/input/output/value map | timing_arc_delay_map |
| 15 | arc_timing_arc_fallback_provenance | arc key/rank, copied-Arc behavior booleans ordinary_min_replaced,ordinary_max_replaced,fallback_replaced | fallback_replaced |
| 16 | database_timing_order | ordered full-name vector | timing_order序列 |

每份typed canary domain为ista-csr-reference-input-canary/<token>/1.0.0，随后固定input_case_sha256、repeat_index、run_nonce、session_token、subject count、raw-wire stable subject key及上表payload；TimingPoint按map byte order，Arc按raw rank。outer family须与domain token一致；pristine/before/after binding与subject key/cardinality必须相同，只有选中family payload允许改变。canary double允许固定±Inf class但拒NaN，enum/bool/presence均strict。

controller从解码值按表构造每个family的required set：每family至少一个subject；stable key、subject/key/cardinality与map entry key/order不变；每个required scalar/string/enum及每张required map的每个value leaf都必须before≠after，token 16保持cardinality而序列至少一位置不同；同family未列leaf及未选中的16个family必须typed canonical bytes exact相等。任何required leaf缺失、仍相等或shape漂移均拒绝。
Fresh的token 3–9、11–14若任一required map在native结果中全空，probe须在pristine pre candidate envelope/raw导出后做deterministic canary-local preconditioning：按该pristine raw冻结的native map/rank顺序取首个compatible stable subject，仅向空map插入该family canonical enum/order的first legal key tuple与type-default before value，paired maps两侧分别补齐。不得重跑GraphBuilder/propagator，不得触碰raw或candidate semantic field；全部required map非空后才取canary before，poison只改同shape value。precondition不新增probe声明字段，controller从decoded before与raw inventory独立重算并校验subject/key/entry。
as-built 对 token 14 冻结空 timing-arc map 的 deterministic first-unused i32 fallback key 与 first-legal before value；token 15 冻结 `ordinary_min_replaced=false`、`ordinary_max_replaced=false`、`fallback_replaced=true`，after 只允许 fallback 位变 false。pristine→before 必须严格符合 scaffold 规则，before→after 才参与 one-hot 分类。


Synthetic对每个(i,required leaf)设正交分类case：仅该leaf变化、其余leaf及另16 family exact相等时分类mask仍须1<<i；full-family accept case再合并该行全部required leaf变化，并覆盖native-empty map→precondition→same-shape delta。fresh的17个full-family pair按表序全poison，aggregate恰0x1ffff。probe不输出mask，controller从bytes派生；summary touched_families只能按表序列化置位token。completeness negative对每行逐required leaf构造“其余required已变、该leaf缺失或相等”并必须拒绝，显式覆盖五组effective/physical漏一侧、token 2/10漏任一scalar、token 9漏12项中任一项、token 11漏任一张map、token 15的fallback_replaced缺失或不变；token 15的ordinary_min_replaced或ordinary_max_replaced任一漂移亦拒绝。另覆盖缺失/错误/额外precondition、precondition后仍空或shape漂移、truncated/trailing、wrong domain/outer token、漏重乱序/unknown family、bad shape/enum/bool/double、binding/subject inventory mismatch、one-hot越界、aggregate非0x1ffff及跨run canned pair。

probe真实parse/full，先以controller token/context导出pristine pre candidate envelope/raw，再完成上述derived-only precondition并编码live canary before；随后按17-token序逐leaf poison同shape value、即时编码canary after，最后导出post candidate envelope/raw且只写controller-owned temp。controller校验exit/stderr/schema/echo后独立decode full wire/raw/canary，先验证precondition exact schema/required entries，再重算wire/raw SHA、五component+composite第六hash和token1/gen0；并从raw重算start/end、clock reach/owner/tag、eligibility、seed/CRPR、endpoint/load/transfer/support，逐typed field exact比较，不信probe identity/hash。

controller要求derived-only precondition前后不改变candidate/raw投影，且pre/post wire、raw、identity/六hash exact不变；chain≠diamond、同case repeat稳定，并以raw subject inventory约束canary stable keys。summary exact {schema const ista-csr-reference-input-controller/1,requested_repeats:nonbool uint64>=3,case_results,complete=true}；case恰为chain/diamond各一次，每repeat exact {repeat_index,input_case_sha256,session_token,candidate_wire_sha256,raw_projection_sha256,touched_families}，序号全集无重漏且touched_families恰为上述17-token序。

每个probe校验成功后controller才atomic rename slot temp到owned final；unique run dir要求summary final预先不存在，summary temp经schema与跨repeat/case重验后atomic rename，CTest只接受本次final。selftest另覆盖wrong case/token/gen、candidate/raw/derived mismatch、额外canned hash、exit/stderr/echo、pre/post/chain/repeat drift及summary漏多重/incomplete/stale/non-atomic；并原样重跑Step2 controller validation。此门不运行backend、不声称timing parity。

### 8.5 Exact Python、import DAG与CTest COMMAND

新增目录src/operation/iSTA/test/reference_input，以下每文件<700行且无单一wire/recompute热点：

- `reference_input_bootstrap.py`、`reference_input_model.py`与`reference_input_overlap_controller.py`仅stdlib；bootstrap是唯一可动态读取Step2 `projection_contract.py`的模块。
- `reference_input_canonical.py`仅stdlib；candidate/canary wire依赖model+canonical，raw wire依赖model symbols+canonical，`reference_input_raw_kat.py`仅依赖model。
- graph/transfer/model/fingerprint recompute依次保持model+canonical的窄无环依赖，transfer独立于model oracle；fingerprint不import production payload helper。
- contract依赖bootstrap、三wire、raw_kat及三类oracle；controller仅依赖contract。
- fixture仅依赖model+canonical；negative_cases依赖contract+controller+fixture；selftest依赖contract+controller+negative_cases+fixture。以上exact 17模块构成无环DAG，全部<700行。

既有`src/operation/iSTA/test/projection`下controller/contract/fixture/probe/schema/canonical每个文件逐文件零修改、零Step4逻辑且不得承载Step4 probe；Step4 C++ probe唯一位于`reference_input/StaCsrReferenceInputProbe.cpp`。新目录除bootstrap调用load_case_descriptors外不得import/use任何projection symbol，并对未改的Step2目录原样重跑ista_csr_projection_controller_validation。

CTest COMMAND逐字冻结如下：

- ista_csr_reference_input_controller_validation："${CMAKE_COMMAND}" -E env "PYTHONDONTWRITEBYTECODE=1" "${ISTA_TEST_PYTHON_EXECUTABLE}" "${CMAKE_CURRENT_LIST_DIR}/reference_input/reference_input_contract.py" --probe-schema "${CMAKE_CURRENT_LIST_DIR}/reference_input/schema/reference_input_result_v1.schema.json" --controller-schema "${CMAKE_CURRENT_LIST_DIR}/reference_input/schema/reference_input_controller_v1.schema.json" --self-test；
- ista_csr_reference_input_controller_selftest："${CMAKE_COMMAND}" -E env "PYTHONDONTWRITEBYTECODE=1" "${ISTA_TEST_PYTHON_EXECUTABLE}" "${CMAKE_CURRENT_LIST_DIR}/reference_input/reference_input_controller_selftest.py" --controller "${CMAKE_CURRENT_LIST_DIR}/reference_input/reference_input_controller.py" --manifest "${CMAKE_CURRENT_LIST_DIR}/baseline/manifest.json"；
- ista_csr_reference_input_fresh_process："${CMAKE_COMMAND}" -E env "PYTHONDONTWRITEBYTECODE=1" "${ISTA_TEST_PYTHON_EXECUTABLE}" "${CMAKE_CURRENT_LIST_DIR}/reference_input/reference_input_controller.py" --manifest "${CMAKE_CURRENT_LIST_DIR}/baseline/manifest.json" --probe "$<TARGET_FILE:ista_csr_reference_input_probe>" --run-root "${CMAKE_CURRENT_BINARY_DIR}/reference_input_runs" --repeats 3 --timeout-seconds 120。
- ista_csr_reference_input_native_overlap："${CMAKE_COMMAND}" -E env "PYTHONDONTWRITEBYTECODE=1" "${ISTA_TEST_PYTHON_EXECUTABLE}" "${CMAKE_CURRENT_LIST_DIR}/reference_input/reference_input_overlap_controller.py" --probe "$<TARGET_FILE:ista_csr_reference_input_probe>"；

labels/timeouts分别ista_unit/60、ista_unit/60、ista_unit/180、ista_smoke/300；wheel逐名build8 functional+public-header target后对三label均--no-tests=error，并检查无__pycache__。

## 9. Step 5/6/7/8 边界

- Step5新增pure backend/table lookup，为共享FIFO第4 consumer；先support gate再读seed/load，不接DB/commit/observation；
- Step6才增加fallback provenance const/bulk、完整native oracle、stable-key prevalidation与no-fail scatter；Step4只做行为canary；
- Step7真实分配token/lease与全corner preflight，capture producer为FIFO第5 consumer；incomplete replay唯一映射active_cycle且不commit；随后atomic input+metadata commit、adapter PUBLIC链接snapshot并发布observation；
- Step8才做oracle/reference fresh-process numeric differential；Step4 poison smoke不能替代。

generation0 committed-style identity只表示值合同，不代表commit。Step4出现token allocation、FIFO、snapshot reducer/storage、observation、binding、backend、scatter或fallback getter即越界。

## 10. 实际实施与完成门

1. 已拆 NativeModels header/ModelValidator source，并通过 private `CsrReferenceCanonicalEncoderInternal.hpp` 共享 canonical field append；storage 与旧 KAT 已同步；
2. 已实现 candidate-only 六 payload builder 与 identity 重算；
3. 已补 19 个 advance header 的窄 const getter，并保持 production inventory 为 core 12、adapter 13、snapshot 3；
4. 已完成 unit/property/failure/storage、三态 synthetic poison、19-header `const_cast` detector 及 safe/poison child self-test；
5. 已完成独立 fresh probe、四个 Python CTest COMMAND、exact 17-module DAG、native overlap controller 与 deep KAT；
6. 已通过原 clean formal 的 `^ista_csr_` 48/48、clang-format 21.1.8 exact143/143 dry-run/Werror、source/object/depfile/callsite、生成物与文件行数门；ignored source-bin保留24个旧 `ista_csr_*`，但本步冲突敏感的transfer/poison/storage三件及cp312/cp313均不存在，既有cp311 identity不变；
7. contract/native/CMake finding 均以定点修复和重跑闭环；最终独立实现审查为 APPROVE。

关键 as-built 冻结值：

- raw empty：115 bytes，SHA-256 `572694c6744abdc63d17096251fddc0a7b41381cce8bd9b62432d8e1e191de40`；
- raw complex：1127 bytes，SHA-256 `981c927eea2234d723aed25ae799b30b2a25f6128961c7fece42dd11762a92f5`；
- deep candidate：3410 bytes，SHA-256 `58cf82c5347b1d6bc8f13447690d73bb826d5ff20fb7b9e0eb3865d48c4bcd65`；
- deep raw：1114 bytes，SHA-256 `ae73fa8c86ae17fc0a7b2c06cba46813f258f45023591a117f0c93df4fc3a350`。

unbound cell arc 保持两层 identity：native raw library ports 为空，canonical ArcKey 使用 graph semantic source/sink pin；missing cell 不声明 output role，present-empty cell 可保留 local role。canary 每项 exact 四键为 `family/pristine_typed_bytes_hex/before_typed_bytes_hex/after_typed_bytes_hex`；token 14 冻结空 timing-arc map scaffold，token 15 冻结 ordinary min/max 不替换而 fallback 替换的行为门。

Step 4 现可在 `stage2-report.md` 中写“已实现”；工作树仍未提交、未 push，且不因此宣称整个阶段 2 完成。Step 5+ 仍保持未实现。
