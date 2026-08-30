# 阶段 2 Step 5：DB-free CPU Full-Graph Reference Backend 详细实施计划

> 状态：Step 5 已按 v0.2 编码前冻结设计实现；production、独立 hand/slow oracle、全门禁与三路独立代码复审均已收口
> 日期：2026-08-24
> 编码前冻结 SHA-256：`d8850b74cd6995f1f050efbda0e0ed08d2c930ace1163690a105995cdc15112b`
> 前置：Steps 1–4 已在未提交工作树完成；Step 4 最终独立审查 APPROVE
> 范围：总计划第 14 节 Step 5；只交付 pure full-graph CPU reference、hand/slow oracle 与 isolation gates
> 提交边界：本步骤不单独提交、不推送；Step 10 前保持 parent/child 未提交

v0.2 编码前版本冻结 Step 5 的 typed outcome、浮点表达式、遍历顺序、结果展平和验收清单；下文保留规范正文，并在 §17.1 回填最终 as-built。实现没有接 Database、session、snapshot lifecycle、native timing oracle、scatter 或 parent runtime，也不声称 Step 8 fresh-process native parity。

## 1. 编码前 blocker 裁决

### 1.1 不存在的 `CsrResultOrError`

总计划旧 §9 写了不存在的 `compute(const CsrReferenceInput&) -> CsrResultOrError`。当前真实类型只有 `CsrReferenceSupportResult` 与 `CsrComputationResult{variant<CsrTimingResult,CsrComputationCode>}`，无法把十项 unsupported reasons 与 cycle/invariant/numeric 三项 computation code 分层返回。

编码前一次性把 transport wrapper 冻结为：

~~~cpp
struct CsrComputationResult
{
  std::variant<CsrTimingResult, CsrReferenceSupportResult, CsrComputationCode> outcome{CsrComputationCode::kInvariantViolation};

  friend bool operator==(const CsrComputationResult&, const CsrComputationResult&) = default;
};

class CsrCpuReferenceBackend final
{
 public:
  [[nodiscard]] CsrComputationResult compute(const CsrReferenceInput& input) const;
};
~~~

`CsrReferenceSupportResult`仍是独立 typed alternative；wrapper 只承载三种互斥结果，绝不把 unsupported reason 压成 `CsrComputationCode`。该 pre-release 结果修订不改变 reference-input schema、canonical bytes 或六个 fingerprint。

### 1.2 Outcome 唯一优先级

`compute()`必须使用下列唯一决策表；“禁止动作”均指完整`validateReferenceInput()`返回以后不得进入的backend阶段，input validator本身仍必须读取并验证其合同覆盖的load/table/seed等字段：

| input state | compute唯一 outcome | validate后禁止的backend动作 |
|---|---|---|
| `validateReferenceInput()` 非空 | `kInvariantViolation` | 不读 unsupported payload、不跑 FIFO、不分配结果 shape |
| valid，unsupported reasons 非空 | exact `CsrReferenceSupportResult{input.unsupported_reasons}` | 不跑 FIFO，不进入seed/load/table/transfer数值阶段 |
| valid、supported、FIFO incomplete | `kCycle` | 不初始化 arc/result，不运行任何数值 pass |
| valid、supported、FIFO complete、数值成功 | `CsrTimingResult` | 不读取 native output |
| 同上但实际求值产生非法数值 | `kNumericFailure` | 不返回 partial result |
| 同上但内部 shape/state 不变量失败 | `kInvariantViolation` | 不把实现 bug 伪装 numeric/unsupported |

support-first 包括 unsupported 与 active cycle overlap。valid supported complete 输入禁止 SupportResult 和 `kCycle`；valid unsupported 输入禁止 TimingResult及全部 computation code。SupportResult 必须非空、known、stable unique，并与 input reasons 逐项完全相等。

`validateComputationResult()`只验证不复制backend即可外部判定的projection：

- malformed input只接受`kInvariantViolation`，且在variant semantic/FIFO访问前早退；
- valid unsupported只接受逐项exact的SupportResult；
- valid supported FIFO incomplete只接受`kCycle`；
- valid supported FIFO complete结构上允许validator-clean的TimingResult、`kInvariantViolation`或`kNumericFailure`，拒绝SupportResult、`kCycle`、unknown code和valueless variant；
- internal/numeric code是否确有触发理由由hand/slow backend tests证明，validator不得复制table/transfer/pass算法重算理由。

现有 validator 对 unsupported 输入接受任意 known computation code，必须修复并加入全 cross-product contract test。

### 1.3 FIFO runtime 0/1 的窄 seam

`CsrCpuReferenceBackendInternal.hpp`声明仅供core实现与contract test使用的function-pointer型`CsrFifoReplayFunction`及`computeCsrCpuReferenceWithReplay(input, replay)`；`replay != nullptr`是该internal seam的显式precondition，public与tests均必须传非空。internal函数实现完整validate→support→FIFO→compute优先级。public `compute()` body冻结为无额外语句的单一`return computeCsrCpuReferenceWithReplay(input, &replayFifoLevelization);`；不得插入另一编排、bare global/default/mutable hook或第二次helper调用。seam只在private internal header声明，不installed、不进入public include closure，public class API不暴露注入点。

outcome contract注入一个不调用production FIFO的计数stub，锁死：

- malformed：count=0、只返回invariant；
- valid unsupported，包括unsupported+active-cycle或含潜在坏数值：count=0、只返回exact SupportResult；
- valid supported active-cycle：count=1、只返回cycle；
- valid supported complete DAG：count=1、进入result/numeric/invariant求值分支。
- valid supported complete且实际interpolation/propagation overflow：count=1、只返回numeric；
- valid supported输入配complete但内部shape不一致的stub replay：count=1、只返回post-FIFO invariant。

另以supported cycle和complete DAG证明public production path与internal seam显式传`&replayFifoLevelization`逐字段exact相等；结合single-return source gate排除wrapper另跑FIFO或改写outcome。

静态inventory与runtime test并行成立：现有`replayFifoLevelization\(` direct-call shape继续是declaration 1 + definition 1 + 3个既有production consumer=5处；backend只新增`&replayFifoLevelization` address-take exact1。production bare-symbol总数由5增至6，但direct-call shape保持5。Step3/4 gate必须分别锁定这两类，不得机械把旧call-shape改成6；seam计数stub不得引用production symbol。

## 2. 目标、支持集与禁止越界

Step 5 对 valid、supported、complete 的 `CsrReferenceInput`执行完整 graph：

- combinational DAG、no-SPEF；
- Liberty missing/present-empty/0D/1D/2D 与全部 stored table variable；
- positive/none/negative/non-unate/mixed sense；
- max/min × rise/fall data slew、dynamic delay与path；
- legacy max scalar arrival/required/slack；
- input start、ideal clock source、output required；
- parallel、disabled、loop-disabled、multi-root、unreachable但结构有效的节点；
- Arc scalar/transition/input-output/graph/per-child timing-arc cache全部 replacement result；
- whole graph only，不接受 affected subset。

以下仍只 typed return，不计算：parasitic、sequential instance/launch、timing check、CRPR、propagated clock、clock-tree fanout、gating/divider、conditional arc、case analysis。顺序沿 `CsrReferenceUnsupportedReason` enum，不增删 token。

Step 5 禁止：

- include、link或间接可见 `Database/Arc/TimingPoint/TimingArc/TimingTable/DelayCalculator/TimingPropagator/TimingAnalyzer/ClockPropagator/STAInterface`；
- include oracle、capture metadata、snapshot storage/observation、session或scatter；
- 读取/重算 pin capacitance、Net load 或 raw Database traversal；
- 另写 production Kahn、读取 native level/order；
- token allocation、commit、observation、fallback replacement getter/bulk setter；
- native oracle/reference fresh-process differential；该项留 Step 8。

### 2.1 Derived DTO 是唯一数值 truth

valid input内存在为fingerprint/closure/diagnostic保留的冗余模型；production numerical stages不得用它们重建已经导出的derived DTO。逐stage field allow-list冻结：

- Backend编排只可读validator结果、`unsupported_reasons`、FIFO输入及copy `schema_version/source_identity`；
- ResultInitialization的start/ideal-clock阶段只读`nodes`、`ordered_start_ids`、`start_seeds`、`clock_tags`、`clocks`及FIFO replay；
- ArcTransfer只读`arcs[*].kind/eligibility/transfer/output_load`及child `signature.arc_index`；Liberty/table/sense/time/cap均只来自`transfer.children`，load只来自Arc的frozen 2×2 matrix；
- Forward只读CSR adjacency/order、Arc eligibility与已经初始化的result/work state；不得回查raw closure；
- Required的endpoint seed可读`ordered_end_ids`、对应Node scalar arrivals及`endpoint_required.node/clock_period/output_delay`并写Node required；reverse可读reverse `timing_order`、`out_row_offsets/out_arc_ids`、`arcs[*].source/sink/eligibility.data_arrival`、immutable initialized `result.arcs.delays`及Node required并写upstream required；finalize slack可读全部Node arrival/required并写slack；不得从`clocks`或`port_constraints`重解period/delay；
- TableLookup只读传入的`TimingTableModel`及四个scalar query/unit参数。

`referenced_library_cells/instances/cell_pin_capacitances/port_constraints/parasitics`不得进入ArcTransfer，`clocks/port_constraints`不得进入Required；`analysis_context`、lookup maps、raw constraint/library closure除input validation与identity copy外不得进入任何numeric stage。Step5 inventory对每个stage `.cpp`做field-token allow/absent gate，而非只查Database类名。

ignored no-SPEF payload isolation另造两份各自strict-valid、各自identity重算的input，仅改变`slew_derate`、四threshold数组、`is_clear_or_preset`及net `output_load`。两次result必须分别copy自己的source identity；去除identity后全部numeric/presence/row payload bitwise一致，证明这些字段未被错误消费。

## 3. Exact production inventory 与 target 边界

新增 exact 9 个 production 文件，其中 6 个 `.cpp`令 core source 由12增至18：

1. `source/module/timing_csr/CsrTableLookup.hpp`；
2. `source/module/timing_csr/CsrTableLookup.cpp`；
3. `source/module/timing_csr/CsrCpuReferenceBackend.hpp`；
4. `source/module/timing_csr/CsrCpuReferenceBackend.cpp`；
5. `source/module/timing_csr/CsrCpuReferenceBackendInternal.hpp`；
6. `source/module/timing_csr/CsrCpuReferenceResultInitialization.cpp`；
7. `source/module/timing_csr/CsrCpuReferenceArcTransfer.cpp`；
8. `source/module/timing_csr/CsrCpuReferenceForwardPropagation.cpp`；
9. `source/module/timing_csr/CsrCpuReferenceRequiredPropagation.cpp`。

职责冻结：

- `CsrTableLookup.cpp`：唯一 production table interpolation与time/cap单位路径；
- `CsrCpuReferenceBackend.cpp`：只做validate→support→FIFO→阶段编排→typed return；
- `ResultInitialization`：checked shape、sentinel、levels、clock/start seed与path work rows；
- `ArcTransfer`：全 arc初始化、output relation、dynamic lookup、per-child cache；
- `ForwardPropagation`：完整slew/delay pass后再scalar/path pass；
- `RequiredPropagation`：endpoint default/override、reverse required、slack与最终flatten检查；
- private internal header：只声明work state/lane helpers、阶段函数和§1.3窄replay seam，不放第二套算法实现。

`CsrCpuReferenceBackend.hpp`只 include `CsrReferenceTypes.hpp`；`CsrTableLookup.hpp`只 include standard optional 与 `CsrReferenceNativeModels.hpp`。两个 public header均 standalone、任意include order可编译。

`ista_timing_csr_core` direct/interace link inventory保持空；adapter仍exact13 sources，snapshot仍exact3，二者链接与aggregate关系不变。Step 5所有 functional test target只直接链接`ista_timing_csr_core`。

除9个新增production文件外，exact修改既有production：

- `CsrReferenceTypes.hpp`：只扩outcome variant；
- `CsrReferenceValidator.cpp`：只修outcome projection；
- `CsrTimingResultValidator.cpp`：只修clock-source scalar name在无pred/有pred时的native覆盖合同；
- `timing_csr/CMakeLists.txt`：core source 12→18。

## 4. Public table API 与数值合同

冻结API：

~~~cpp
[[nodiscard]] std::optional<double> lookupCsrTimingTable(
    const TimingTableModel& table,
    double input_slew,
    double raw_output_load,
    double time_unit_scale,
    double capacitance_unit_scale);
~~~

返回合同：

- table absent：`nullopt`；
- table present且任一实际求值中间量/结果非有限、cap conversion不安全：direct API返回`nullopt`；只有已通过input validation、实际进入backend numerical stage后才映射`kNumericFailure`；
- present-empty：在完成实际参数scale/conversion检查后返回`0.0`；
- 0D/1D/2D：返回已经乘入/除回time scale并完成native cap conversion的值。

caller/helper逐操作次序冻结：

1. `table.present==false`立即`nullopt`，不检查或运算query/scales；
2. present先只做raw参数finite/nonnegative、正scale与安全范围比较；
3. 先算`capacitance_unit_scale - 1.0`并检查，再取abs；若不满足near-one，按`raw_output_load * capacitance_unit_scale`→finite/range check→`ceil`→range check→`int` cast执行；若满足则直接复制raw load；
4. load conversion完成后才算`input_slew * time_unit_scale`并检查；
5. 以该scaled slew和converted load按§5原表达式运行`findValue`；
6. 最后才以table值除`time_unit_scale`并检查结果。

present-empty也完整执行1之外的raw guard、load conversion、slew scale、findValue返回0与最终除法；不得因values empty提前跳过caller的实际单位路径。每个中间检查只观察刚完成的值，不预计算、重排或融合后续表达式。

调用前 table/load/scales来自valid input；API仍不得对out-of-range double→int做未定义转换。cap branch为：

`validateConvertedLoadRanges()`已使unsafe cap product/ceil/int conversion的CSR成为malformed：public backend必须在table前返回invariant且FIFO0，即使该input同时带unsupported reason也不得support-first；这与direct table API对同样raw参数安全返回`nullopt`不矛盾。valid input的interpolation或slew-scale overflow才是numeric/FIFO1；valid unsupported input即使其数值阶段若执行会overflow也必须Support/FIFO0。

~~~text
abs(capacitance_unit_scale - 1.0) < 1e-6
  ? raw_output_load
  : static_cast<int>(ceil(raw_output_load * capacitance_unit_scale))
~~~

严格小于才直通。binary64 `1.0 + 1e-6` rounded-below与首个`nextafter(...,+inf)`分别KAT；ceil前验证finite、非负、`<= INT_MAX`。

## 5. TimingTable exact evaluator

必须逐表达式复现 `TimingTable::findValue()`：

1. present table先完成caller query/unit的实际数值检查；
2. values empty返回0；
3. axes empty返回values.front；
4. 只有variable1决定换轴：output-cap/constrained使axis0=secondary、axis1=slew，否则axis0=slew、axis1=secondary；variable2不dispatch；
5. region找首个严格`axis[i] > query`，exact knot走右interval，last knot与above走末interval，below走首interval；
6. singleton/少于2点返回`(0,0,0)`；
7. table OOB value按native返回0；
8. 1D线性与2D axis0-major双线性均允许外推；
9. `abs(delta) < 1e-6`才退化取y1，exact epsilon继续计算；
10. 双线性保持native q11/q12/q21/q22和乘加次序，不用`std::lerp`、FMA或代数重排；
11. 最终除以正finite time scale，任何实际中间/结果非法返回numeric failure。

linear表达式逐token冻结为：

~~~text
y1 + ((x - x1) * (y2 - y1) / (x2 - x1))
~~~

bilinear必须先按此顺序建立六个变量，再按native左结合乘加/除法原序求值：

~~~text
x2_x1 = x2 - x1;  y2_y1 = y2 - y1;
x2_x  = x2 - x;   y2_y  = y2 - y;
x_x1  = x - x1;   y_y1  = y - y1;
(q11 * x2_x * y2_y + q21 * x_x1 * y2_y
 + q12 * x2_x * y_y1 + q22 * x_x1 * y_y1) / (x2_x1 * y2_y1)
~~~

x-degenerate分支必须先于y-degenerate；x退化调用`linear(y1,y2,q11,q12,y)`，只有x不退化且y退化才调用`linear(x1,x2,q11,q21,x)`，both-degenerate因此走x分支。`ista_timing_csr_core`与四个Step5 test target均exact加入`-ffp-contract=off`，compile-command gate拒`-ffast-math/-Ofast/-ffp-contract=fast`及reassociation；table hand KAT使用hexfloat literal及`std::bit_cast<std::uint64_t>`比较，不用tolerance掩盖表达式重排。

missing delay table不产生child candidate；missing slew table透传input slew。present-empty是实际0候选，不走fallback。slew threshold、input/output threshold与derate在no-SPEF该native路径不使用。

## 6. Flat lane、sentinel 与 checked allocation

索引只允许以下公式，并在乘加前checked size overflow：

- node/data/clock lane：`(node*2 + analysis)*2 + transition`；
- path row：`(((node*2 + analysis)*2 + path_source)*2 + transition)`；
- arc transition：`(arc*2 + analysis)*2 + input_transition`；
- IO/graph：`transition_lane*2 + output_transition`；
- arc type：`arc*2 + input_transition`；
- timing-child：`(((child_entry*2 + analysis)*2 + input_transition)*2 + output_transition)`。

记`N=nodes.size()`、`E=arcs.size()`、`C=sum(arc.transfer.children.size())`、`L=FIFO非空level数`、`P=flatten后的path entry数`。successful result逐字段exact shape/presence冻结：

| family | fields | exact extent/presence |
|---|---|---|
| levels | offsets / nodes / node_to_level / timing_order | `L+1 / N / N / N` |
| Node | is_clock_point, arrival, required, slack, launch | 每个values/presence均`N`且presence全1 |
| Node optional | clock_name / predecessor_node / predecessor_arc | 每个values/presence均`N`；两pred presence逐项相同；每个resolved ideal-clock source的clock_name必须present |
| effective clock | arrivals, slews, pred_node, pred_delay, pred_transition | 每个values/presence均`4N`；resolved source仅arrival/slew为present +0，三pred全absent |
| physical clock | 同上 | 与effective clock相同exact shape/source-only presence |
| data slew | data_slews | values/presence均`4N` |
| path rows | row_offsets | `8N+1`，首0、末P、单调 |
| path required | clock_tag, arrival, slew, launch, start_node | 每个values/presence均`P`且presence全1 |
| path predecessor | pred_node, pred_arc, pred_delay, pred_transition | 每个values/presence均`P`且四者presence逐项相同 |
| path CRPR | crpr_node, crpr_transition | 每个values/presence均`P`且二者presence逐项相同 |
| Arc scalar | delay, min_delay, max_delay | 每个values/presence均`E`且presence全1 |
| Arc transition | transition_delays | values/presence均`4E`且presence全1 |
| Arc IO/dynamic | input_output_delays / graph_delays | 各values/presence均`8E` |
| Arc type | transition_types | values/presence均`2E` |
| timing child rows | row_offsets / indices | `E+1 / C` |
| timing child cache | delays / fallbacks | 各values/presence均`8C`且两者presence逐项相同 |

successful supported结果的全部Register path rows必须empty，全部CRPR lane必须absent。任一optional absent payload均为类型canonical default：double为bitwise positive-zero、Transition为`kNone`、StrongId为0、string为空、integral/byte为0；presence本身只能0/1。上述表连同空图特例是checked internal shape gate，缺一字段即post-FIFO invariant。

Reset：node arrival=`-inf`、required=`+inf`、slack/launch=`+0`、predecessor/clock absent；data/clock/arc maps按presence合同初始化；path work state arrival=`-inf`、slew/launch/pred-delay=`+0`、transition none。DTO absent payload必须是validator定义的canonical default，特别是Transition absent=`kNone`、double absent为positive-zero bit pattern。

Node scalar/is-clock、Arc scalar/min/max/transition-delay全部required presence=1。其他optional SoA absent payload不得保留poison。result schema/source identity复制input；level offsets/nodes/node-to-level/timing order逐字段复制唯一FIFO replay，timing order恰等于level nodes。

空图的exact shape冻结为：level offsets=`{0}`、level nodes=`{}`、node-to-level=`{}`、timing order=`{}`；path row offsets=`{0}`且entry/tag/required/optional payload数组均为空；timing-child row offsets=`{0}`且indices与所有lane均为空。singleton与unreachable图不得借空图特例省略其required lane。

## 7. Arc 初始化与 output relation

按ArcId顺序初始化全部arc，包括disabled和loop-disabled：

### 7.1 Net

max/min/scalar、transition delay、IO identity均为0；type identity。非identity IO absent。dynamic时graph identity present0、slew透传。

### 7.2 Cell children empty

每analysis/input只有identity output；Max用`delay_max`，Min用`delay_min`；slew透传；timing-child row为空。

### 7.3 Cell children nonempty

clock trigger只读首child：fall只允许fall，rise只允许rise，none默认rise。未触发input不创建IO/type，但其required transition-delay在最终scalar extrema读取时scaffold为0。

output relation：

- 全negative时flip；全positive/none时identity；
- 任一non-unate、`is_clock_arc`，或同时存在任一negative与任一positive/none时按rise、fall枚举；因此none+negative也是two-type mixed；
- 只有任一child对该output存在delay/slew/check table，relation才存在；check-only也能建立relation；
- relation建立后再筛child：flip排除positive/none，nonflip排除negative，non-unate两边均候选；
- relation存在但无delay候选→`transfer.delay`；无slew候选→input slew；
- 该output三类table全absent→relation absent；
- child按input vector顺序，raw min/max fold，无epsilon，exact tie first。

初始化循环顺序 exact：analysis Max→Min，input Rise→Fall，output Rise→Fall，child input order。每个IO写入后，per-analysis transition-delay按raw strict max/min选winner；exact tie不替换。`transition_types`没有analysis维，因此Max阶段可写、Min阶段再覆盖，最终必须等于Min winner；max/min winner不同KAT强制锁定。

nonempty children的初始化delay query逐child冻结：只对该output present delay table调用
`lookupCsrTimingTable(delay_table, +0.0, arc.output_load[analysis][output], time_scale, cap_scale)`。也就是input slew恰为bitwise `+0.0`，load只取冻结的`ArcRecord::output_load`对应2×2 lane；valid supported cell缺该load属于internal invariant。每个实际delay candidate先写自己的timing-child cache并置fallback=1，再参与aggregate IO raw min/max fold。slew/check table只用于建立relation，初始化阶段绝不求值。

dynamic阶段对每个被relation/sense选中的child以source data slew重新查delay与slew；该child首次dynamic delay命中必须无条件覆盖自己的初始化cache并清fallback，即使它最终输掉aggregate graph-delay或sink-slew竞争。后续同child/key才按raw analysis min/max fold。非constant 1D/2D KAT必须使init(+0 slew)与dynamic(nonzero source slew) bitwise不同，并分别覆盖aggregate loser仍更新cache、unreachable/disabled保留初始化fallback。

最终scalar：`max_delay=max(Max/Rise,Max/Fall)`、`min_delay=min(Min/Rise,Min/Fall)`、`delay=max_delay`。缺lane的transition-delay已scaffold0；IO/type仍absent。

## 8. Per-child cache、dynamic delay 与 data slew

`timing_arc_row_offsets/indices`严格保持每arc children及其signed `arc_index`原序。每child×analysis×input×output optional lane：

- initialization第一次实际delay candidate写delay，fallback=1；
- dynamic第一次命中即使值相等也无条件替换并清fallback；
- 后续同key按raw min/max，exact tie first；
- 未动态到达或disabled arc保留fallback=1；
- 无delay table/candidate的lane始终absent，不因slew/check relation伪造cache。

supported后只消费`ArcRecord::output_load[analysis][output]`；绝不从pins/net/caps重算。dynamic只对`eligibility.data_slew`且source slew present的arc执行，顺序为timing order→out row→Max/Rise、Max/Fall、Min/Rise、Min/Fall→output Rise、Fall。

初始化完成后以下字段immutable：`delays/min_delays/max_delays/transition_delays/input_output_delays/transition_types`。dynamic阶段只允许写`graph_delays`、对应child的`timing_arc_delays/timing_arc_fallbacks`及sink `data_slews`；不得用dynamic winner回写scalar、transition或IO初始化map。

init-vs-dynamic KAT使用nonconstant LUT令+0-slew初始化IO与nonzero-source-slew dynamic graph/cache bitwise不同：断言scalar/transition/IO仍保持init，graph与child cache已dynamic且fallback清零。后续scalar arrival与reverse required继续只用immutable init scalar delay。

graph delay首次写；若同key再次写，使用`1e-6` strict-better。sink data slew对所有incoming arc竞争，同样`1e-6` strict-better、阈值内first-wins。负或非有限computed slew立即numeric failure。必须先完成整个graph的slew/delay pass，再运行任何arrival/path。

## 9. Ideal clock 与 start seed

先按`input.clocks`原序、每个clock的`ordered_sources`原序初始化ideal-clock source。每个resolved source在effective/physical clock四lanepresent +0、无pred；其余clock lane absent。`nodes.is_clock_point` required数组精确等于resolved source集合。对该Node的`nodes.clock_names`写首个匹配clock的`map_key`且present；同一clock重复source或后续再次命中不得覆盖首写。这精确对应native CPModel由clock-map entry name构造，而不是embedded field。

resolved source不要求位于`ordered_start_ids`：isolated internal/non-port source可只是FIFO root且没有StartSeed，此时Node scalar arrival仍`-inf`、launch `+0`、pred absent、data_slew全absent，但clock_name仍必须present如上。supported已拒clock fanout，不做clock传播。

若该internal direct source有incoming active data arc但无outgoing，它仍可valid supported。scalar winner照native正常写pred/arrival/launch，并把Node clock_name从initial map key覆盖为upstream source name；effective/physical clock四lane、is_clock_point不变。结果validator必须把owning map-key要求限定在scalar predecessor absent且非start的source；start/no-pred按seed tag，pred present只按predecessor-chain name检查，不得同时强求owning name。

按`ordered_start_ids/start_seeds`原序seed。direct-clock查询必须在`input.clocks`原序中找首个其`ordered_sources`任意位置含该resolved seed NodeId的clock；绝不只看clock的first source，source位于第二项或更后仍命中：

- 四个data-slew lane精确复制seed；
- scalar arrival：path_source present取Max/Rise arrival，否则0；
- scalar launch：若上述first matching clock存在，取其rise edge，否则0；
- scalar clock_name由seed.clock_tag写入且present，覆盖该start Node先前的map-key clock-source初始化；pred absent；
- path_source absent不创建path entry；
- input path每analysis/transition创建exact一个tag entry，arrival/slew/start/tag/CRPR复制seed；
- direct clock path launch只在Max/Fall取fall edge，其余取rise edge；非direct clock取0；
- register path在successful result中不可达，因为任一sequential input已由support gate返回unsupported。

## 10. Scalar arrival 与 ragged path pass

第二个完整forward pass顺序：timing order→out row；每arc先scalar，再按Max/Input、Max/Register、Min/Input、Min/Register→input Rise/Fall→output Rise/Fall→ClockTagId升序处理path。只消费`eligibility.data_arrival`。

Scalar只做legacy Max：

~~~text
candidate = source.arrival + arc.scalar_delay
replace iff sink unreachable or candidate > sink.arrival + 1e-9
~~~

只有finite source scalar arrival才执行add；`-inf` unreachable sentinel直接跳过该arc，不参与算术、也不触发numeric failure。

不round；winner复制source launch/clock并记录source NodeId与ArcId。即使cell无IO relation，scalar仍沿eligible arc用scalar delay传播。

Path delay选择顺序为dynamic graph lane→initialized IO lane→transition delay→analysis min/max scalar fallback。只遍历initialized IO relation的output transition。每edge：

~~~text
candidate = round((source_path.arrival + selected_delay) * 1e15) / 1e15
~~~

只有finite source path arrival才执行add/multiply/round/divide；`-inf` path sentinel直接跳过。

同tag按analysis方向使用`1e-6` strict-better；阈值内first-wins，不同tag共存。winner写pred Node/Arc/delay/input transition、start/launch/tag/CRPR，并复制第二pass开始前已经冻结的sink全局data slew，而不是该path独立arc slew。

内部每path row用按ClockTagId升序的vector/lower_bound或等价ordered结构；flatten后row顺序严格`Node×Analysis×PathSource×Transition`，row内tag严格递增。required path fields全present，optional predecessor/CRPR presence同步。

## 11. Endpoint required、reverse 与 slack

只实现native legacy scalar Max：

1. `default_required=max(0, 所有ordered endpoint的finite scalar arrival)`；
2. 每endpoint先seed default；
3. 对应`EndpointRequiredModel.output_delay[Max]` present时用`clock_period-output_delay_max`覆盖；min-only不影响scalar；
4. reverse timing order、out row，对`eligibility.data_arrival`且sink required finite才计算`source.required=min(current,sink.required-arc.scalar_delay)`；`+inf` unconstrained sink直接跳过，不执行subtract；
5. backward使用初始化scalar delay，不用graph delay、不round；
6. arrival与required均finite才`slack=required-arrival`，否则保留reset0。

负/零clock period、delay、arrival、required是finite合法值。所有endpoint arrival为负时default仍为0。exact required tie保留current。

## 12. Numeric failure 与原子性

实际执行到的每个scale、multiply、ceil、interpolate、divide、fold、add、round、subtract和shape乘法都检查：NaN或computed ±Inf失败；computed slew另要求非负。唯一合法infinity是unreached arrival `-inf`和unconstrained required `+inf` sentinel；二者只由reset建立，并按§10–11 finite guard跳过，绝不作为算术operand产生“合法computed infinity”。

坏候选即使最终会输也numeric failure。disabled arc会初始化，所以其非法初始化值仍失败；未到达arc的dynamic lookup不执行，不凭空失败。`std::bad_alloc`与系统异常传播，不包装成numeric failure。

所有work state local构造；失败只返回code，不返回partial `CsrTimingResult`。backend不调用会二次FIFO的完整result validator；它用checked internal shape/state门返回invariant，tests再独立调用`validateComputationResult/validateTimingResult`。

`validateTimingResult()==empty`只证明shape、canonical sentinel与局部因果约束成立，绝不充当LUT、transfer、winner、required或flatten的数值oracle；成功结果的数值正确性只能由hand literal whole-result/selected-lane KAT和独立slow oracle分别证明。

## 13. Hand literal 与 independent slow oracle

新增 exact test/support 文件：

- `CsrTableLookupContractTest.cpp`；
- `CsrCpuReferenceContractTest.cpp`；
- `CsrCpuReferenceOutcomeContract.cpp`；
- `CsrCpuReferenceArcContract.cpp`；
- `CsrCpuReferencePropagationContract.cpp`；
- `CsrCpuReferencePropertyTest.cpp`；
- `CsrCpuReferenceTestFixture.hpp/.cpp`；
- `CsrCpuReferenceSlowOracle.hpp`；
- `CsrCpuReferenceSlowOracleInternal.hpp`；
- `CsrCpuReferenceSlowOracleTable.cpp`；
- `CsrCpuReferenceSlowOracleTransfer.cpp`；
- `CsrCpuReferenceSlowOraclePropagation.cpp`；
- `CsrCpuReferencePublicHeadersMain.cpp`；
- `public_header/CsrTableLookupHeaderTest.cpp`；
- `public_header/CsrCpuReferenceBackendHeaderTest.cpp`；
- `CsrCpuReferenceHeaderIncludeOrderTest.cpp`；
- `CsrCpuReferenceHeaderReverseIncludeOrderTest.cpp`；
- `CsrCpuReferenceTests.cmake`；
- `CheckCsrStep5SourceInventory.cmake`。

Hand contract expected值必须以literal whole-result/selected-flat-lane写死，不调用slow oracle生成expected。slow oracle只include `CsrReferenceTypes.hpp`与自己的internal header；禁止include/call backend、table lookup、FIFO helper、validator、canonical encoder、native evaluator或oracle类型。

slow oracle独立复制table表达式和transfer规则，用test-only O(VE) FIFO模拟重建root/row order，不读取production level result；小图失败输出seed、canonical graph、root/row/transfer replay参数。随机域避免tie，near-tie只由hand KAT验证。只对row-preserving、no-tie metamorphic变换要求等价，不把任意adjacency permutation视为等价。

test fixture实现独立`requireExactTimingResult`，禁止Step5 hand/property/determinism测试直接使用默认`CsrTimingResult::operator==`。它对presence、offset、ID、enum、string逐值exact，对全部double（包括finite、signed zero与±infinity）按`bit_cast<uint64_t>` exact；property的input-unchanged使用前后canonical bytes而非默认operator==。若Step 8 native lane另用finite tolerance，也必须额外对presence/row/ID/enum/string及signed-zero/infinity bit exact。

whole-result literal至少覆盖§6每个family；另有table-driven comparator canary对levels四字段、Node八SoA、两套clock各五SoA、data slew、path offset及十一SoA、Arc scalar/transition/IO/graph/type/child rows/cache/fallback逐字段各做一次单点mutation并证明comparator拒绝。每个optional family同时mutate presence与absent payload；因此validator通过或默认operator==相等都不能制造假绿。

## 14. Test matrix

### 14.1 Table

absent/present-empty；0D只测valid `(variable1,variable2)=(none,none)`；1D只测variable1三种non-none × variable2 none；2D覆盖variable1三种 × variable2三种non-none共9个valid组合、两种orientation与axis0-major；固定同一non-none variable1/axes/values/query时，仅在三个non-none variable2 token间要求bitwise同值以证明variable2不dispatch，禁止构造`v1=none,v2!=none`非法shape；first/interior/last exact knot；双端外推；axis0/axis1/双singleton；axis delta在1e-6 below/equal/above；x/y/both退化优先级；cap scale near-one边界、ceil整数/非整数/INT_MAX；time scale；hexfloat/bit-pattern表达式判别；direct API present-empty + unsafe cap必须`nullopt`，同一CSR为malformed→invariant/FIFO0；独立valid present-empty + `input_slew*time_scale` overflow及valid interpolation overflow均为numeric/FIFO1；valid unsupported + 潜在数值overflow为exact Support/FIFO0。

### 14.2 Transfer/cache

net、children empty、三类table全无、delay-only/slew-only/check-only、missing rise/fall、present-empty、constant/1D/2D、positive/none/negative/non-unate/mixed及exact `{none,negative}` two-type、非候选child建立relation后sense过滤、clock trigger三态、raw child near tie、Max/Min winner不同、missing trigger scaffold0、2×2 load、fallback init→equal dynamic replacement、aggregate loser child仍更新cache、init IO/scalar immutable而graph/cache dynamic、disabled/unreachable fallback保持；ignored no-SPEF payload成对identity-recomputed isolation。

### 14.3 Propagation/path

empty/singleton/chain/diamond/multi-root、parallel、disabled、loop-disabled、active cycle、unreachable node；无seed但active且complete的DAG全forward保持`-inf` arrival且不报numeric；多个clock中前项不匹配、后项的第二个raw source命中seed，必须使用`input.clocks`首个匹配clock edges；map_key!=embedded KAT覆盖三态：(a) isolated internal resolved source是root但非start、无seed，clock SoA四lane +0、Node name=首匹配map_key、arrival `-inf`/launch +0/pred与data-slew absent且重复source首写；(b) direct start被seed tag覆盖；(c) tag A start经active arc到tag B internal direct source且source无outgoing，sink scalar pred/finite arrival/name=A，而clock SoA与is-clock仍保留B source状态；scalar1e-9与slew/path1e-6 below/equal/above；FIFO/row first winner；same/different tag；tag flatten；正负halfway away-from-zero；global sink slew与path winner来自不同arc；downstream LUT读取完整slew pass winner；scalar沿无IO relation传播而path不传播。

### 14.4 Required/outcome/numeric

output max delay/absent/min-only、无clock/first frozen period、负零period/delay、全负endpoint default0、reverse scalar-vs-graph差异、无endpoint可达component reverse保持`+inf` required且不报numeric、unreachable slack0；malformed、十reason逐项/overlap、unsupported+cycle、malformed+unsupported+active-cycle三重overlap必须invariant/FIFO0、supported cycle；negative slew及table/arrival/round/required/slack overflow；valid interpolation overflow numeric/FIFO1与同值域valid unsupported Support/FIFO0；wrapper outcome cross-product。

### 14.5 Property

`ista_csr_cpu_reference_property_test`固定5个独立CTest：`1/7/42/20260820/0xdeadbeef`，label `ista_property`、timeout60。generator只产valid supported小DAG、parallel与disabled/loop overlay；每seed比较whole result与slow oracle、determinism、input未变、validator通过。

## 15. Targets、CTest 与 wheel

新增4个executable target及exact source inventory：

1. `ista_csr_table_lookup_contract_test`，unit：
   - `CsrTableLookupContractTest.cpp`。
2. `ista_csr_cpu_reference_contract_test`，unit：
   - `CsrCpuReferenceContractTest.cpp`；
   - `CsrCpuReferenceOutcomeContract.cpp`；
   - `CsrCpuReferenceArcContract.cpp`；
   - `CsrCpuReferencePropagationContract.cpp`；
   - `CsrCpuReferenceTestFixture.cpp`。
3. `ista_csr_cpu_reference_property_test`，5个property CTest：
   - `CsrCpuReferencePropertyTest.cpp`；
   - `CsrCpuReferenceTestFixture.cpp`；
   - `CsrCpuReferenceSlowOracleTable.cpp`；
   - `CsrCpuReferenceSlowOracleTransfer.cpp`；
   - `CsrCpuReferenceSlowOraclePropagation.cpp`。
4. `ista_csr_cpu_reference_public_headers_test`，unit：
   - `CsrCpuReferencePublicHeadersMain.cpp`；
   - `public_header/CsrTableLookupHeaderTest.cpp`；
   - `public_header/CsrCpuReferenceBackendHeaderTest.cpp`；
   - `CsrCpuReferenceHeaderIncludeOrderTest.cpp`。
   - `CsrCpuReferenceHeaderReverseIncludeOrderTest.cpp`。

另注册`ista_csr_step5_source_inventory` unit CTest。预计相对Step4新增9个unique CSR tests（4 unit + 5 property）；label可能重叠的cpu/integration计数不用于求和。

四target direct links均exact `ista_timing_csr_core`，compile options `-Wall -Wextra -Werror -pedantic -ffp-contract=off`，core也PRIVATE exact `-ffp-contract=off`；functional/header unit timeout60。wheel composite action显式build四target后再跑既有三个label命令；Step5不新增smoke。

顶层`src/operation/iSTA/test/CMakeLists.txt`紧跟既有`CsrTests.cmake`新增exact入口：

~~~cmake
include("${CMAKE_CURRENT_SOURCE_DIR}/CsrCpuReferenceTests.cmake")
~~~

四target、5个property CTest与`ista_csr_step5_source_inventory`只由该新文件注册；顶层不得重复展开其source清单。

## 16. Isolation 与 exact inventory 连锁

必须同步：

- `timing_csr/CMakeLists.txt`、`CsrIsolationTests.cmake`：core exact12→18 sources及object/file allow-list；
- `CheckCsrCoreIsolation.cmake`：prohibited direct/depfile tokens加入native evaluator、propagator、analyzer、clock、oracle、metadata、snapshot、scatter、interface；
- `CheckCsrStep3SourceInventory.cmake`与`CheckCsrStep4SourceInventory.cmake`：backend成为第4 FIFO consumer，header+definition+4 consumers总 occurrence由5→6；
- Step4 validateReferenceInput callsite inventory加入backend恰一次，existing count相应+1；
- 新增独立Step 5 public-header target并锁定§15 exact inventory；既有Step 4 public-header target及其inventory不变；
- `.github/actions/build-wheel/action.yml`加入四target build；
- 新`CheckCsrStep5SourceInventory.cmake`注册为unit。

Step5 gate冻结：

- production/test exact文件、target source、object与direct-link inventory；既有三production修改必须精确等于§3 allow-list且无额外core source；
- compute和table declaration/definition各exact1；
- backend direct `validateReferenceInput` exact1；public compute body exact single-return address-take `&replayFifoLevelization`一次且无direct call，internal source snippet锁定support在调用`replay(input)`前；
- Step3/4 inventory锁既有`replayFifoLevelization\(` direct-call shape exact5不变，另锁backend address-take exact1及production bare symbol total6；
- 计数stub证明malformed/unsupported运行时FIFO0次，supported cycle/DAG/numeric/post-FIFO-invariant恰1次，且stub不引用production FIFO symbol；
- public cycle/DAG与internal显式传production helper逐字段exact parity，wrapper无第二编排；
- 每个stage `.cpp`按§2.1做derived-field token allow/absent gate，禁止从冗余DTO重新计算Lib/load/constraint；
- ignored no-SPEF字段双input除identity外exact payload parity；
- 9个Step5 production file逐文件gate：`validateReferenceInput`全局exact1且只在Backend.cpp；`&replayFifoLevelization`只在public wrapper exact1；全部禁止`validateTimingResult`、`validateComputationResult`、canonical encoder/fingerprint调用；
- 对6个新增production object做`nm -uC` undefined-symbol gate；只允许Backend object引用input validator与FIFO，全部objects拒result/outcome validator、canonical/fingerprint、native evaluator/oracle/metadata/snapshot/scatter/interface symbol；
- production除唯一FIFO helper外禁止queue/deque/indegree/local Kahn token；
- backend include closure不得出现Database/native evaluator/oracle/metadata/snapshot/scatter/interface；
- slow-oracle project-local include DAG exact：public `SlowOracle.hpp`只include `CsrReferenceTypes.hpp`，internal只include该public header，三个`.cpp`各只includeinternal；standard headers另列allow-list；
- 三个slow-oracle object的source owner、Ninja object与VALID depfile逐个1:1；source、depfile及`nm -uC`均拒backend/table/FIFO/validator/canonical/fingerprint/native symbol，即使手写forward declaration也不能偷调；
- Step5 tests中只有`CsrCpuReferenceOutcomeContract.cpp`可include production `CsrCpuReferenceBackendInternal.hpp`；property、hand、fixture、public-header均禁止production internal helper；
- compute签名无metadata参数，因此不伪造无意义的runtime attach/delete测试；source、object与depfile gate必须逐token禁止`CsrCaptureMetadata`及metadata header，证明backend不存在metadata输入通路；
- core/adapter/snapshot/aggregate link关系不变；
- actual四target SOURCES、Ninja objects、VALID depfile owner三集合必须1:1，且每object仅归属自己的`.cpp`；stale/orphan/multi-owner一律失败；
- `CheckCsrStep5SourceInventory.cmake`在build-local生成safe/poison child selftests，分别证明source-token、synthetic depfile和compiled undefined-oracle-symbol detector会以固定exit/diagnostic拒绝poison并接受safe；临时fixture固定清理且source tree零泄漏；
- 所有Step5 production/test/header/CMake纳入exact-absent `const_cast` gate，禁止写后恢复伪造input unchanged；
- core与四Step5 target compile-command exact含`-ffp-contract=off`且拒fast-math/Ofast/fast-contract；
- exact result comparator的逐字段canary mutation selftest必须全拒；property/controller不得调用默认result operator==；
- 所有Step5新增/重写production、test、header、CMake单文件严格`<700`行；
- source tree无build/result/session/cache/patch泄漏，parent/child diff-check。

## 17. 实施顺序与审查协议

1. [已完成] 修总计划API与本计划，三方设计审查APPROVE；
2. [已完成] 只改types/validator/outcome tests，运行既有core/FIFO/schema contract；
3. [已完成] 实现table helper与literal KAT，独立审查；
4. [已完成] 实现result reset/arc init/cache与hand KAT，独立审查；
5. [已完成] 实现两段forward、required/flatten与whole-result literals，独立审查；
6. [已完成] 实现slow oracle/property，做oracle isolation红队；
7. [已完成] 更新CMake/wheel/exact gates，fresh formal构建；
8. [已完成] 修finding并重复审查直至APPROVE；
9. [已完成] 运行Step5 target、全CSR、legacy/global labels、parent non-PDK与format/type/diff/hygiene门；
10. [已完成] 回填本计划和阶段报告as-built；仍不commit、不push。

### 17.1 As-built（2026-08-24）

实现严格遵循上述编码前 SHA。新增 §3 的 exact 9 个 production 文件，其中6个cpp令 `ista_timing_csr_core` 由12增至18；既有 production 只改 `CsrReferenceTypes.hpp`、`CsrReferenceValidator.cpp`、`CsrTimingResultValidator.cpp` 和 core CMake。adapter仍13 sources、snapshot仍3 sources，direct/interface links与production SCC均未改变。

测试侧交付四个exact executable、5个固定seed property CTest、独立O(VE) slow oracle、逐字段bit-exact result comparator/canary和 `ista_csr_step5_source_inventory`。最终inventory独立hard-code target source与expected object owner，验证16个Step5 test objects（其中3个slow-oracle）与6个production objects、共22个对象的VALID depfile exact singleton ownership；3个slow-oracle子集另受更深source/depfile/`nm`隔离。safe/poison、cross-directory poison、undefined-symbol、line-cap、`-ffp-contract=off` 与no-default-`operator==` gates均通过。

终审修正包括：table cache B1、插值与arrival-addition numeric overflow outcome、supported/unsupported FIFO precedence、result schema，以及identity schema/token/generation/六fingerprint（共9个identity members）的comparator canary、以及object depfile owner false-green。algorithm、test-matrix和fresh red-team三路复审均已闭环，最终无剩余 blocker/major/minor。

最终复证：

| 门禁 | 结果 |
|---|---|
| 四个Step5 exact target freshness build | PASS；`ninja: no work to do` |
| Step5 exact + chained isolation | 13/13 PASS |
| `ctest -R '^ista_csr_'` | 57/57 PASS |
| global labels | unit 73/73、property 15/15、smoke 4/4 |
| parent non-PDK pytest | 1608 passed、8 skipped、4 deselected、13 xfailed |
| Step5 五seed property | 5/5 PASS；`1/7/42/20260820/0xdeadbeef` |
| Ruff check / format check | PASS；format exact 237 files |
| scoped production pyright | PASS；0 errors |
| clang-format 21.1.8 | PASS；changed/new `.cpp`/`.hpp` exact 170 files，dry-run/Werror |
| parent/child tracked diff-check、untracked whitespace与artifact hygiene | PASS；本步未生成source-tree cache，parent既有ignored cache原样保留 |

未修改 Database、adapter source count、snapshot source count、session/interface/pybind、parent Python runtime、Stage 1 record、artifact默认路径或golden；没有commit、没有push。

任一步发现input DTO不能表达native语义，立即停止编码，先修订总计划和本计划并重新双审；不得读取native output补洞。

## 18. 完成条件与明确非声明

完成必须同时满足：

- outcome precedence和十reason exact typed return全绿；
- supported hand whole-result与independent slow oracle全绿；
- table/transfer/pass/required/numeric KAT全绿；
- FIFO唯一production helper为第4 consumer，无第二套Kahn；
- core18 source、四新target、exact object/depfile/header/oracle isolation全绿；
- 全新增文件<700，clang-format/Ruff（若无新Python则现有范围）/diff/hygiene通过；
- 未参与实现的native与contract审查者均APPROVE；
- 文档列出修改了什么、未修改什么、准确测试计数。

Step 5完成仍不表示：Database capture/session已接入、result可scatter、fallback provenance可native replacement、真实native timing differential已完成、GPU path可用或工作树已提交。这些分别属于Steps 6–10。
