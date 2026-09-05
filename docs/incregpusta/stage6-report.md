# 阶段 6 报告：CPU mixed incremental levelization reference

> 状态：完成；功能实现、production/fresh differential、typed recovery、active-payload边界、相关回归、ASan/UBSan及最终独立全diff审查均已闭合
> 日期：2026-09-02
> 基线：Stage 5 parent `8d7b642b94ff136d804539453ef484ba5d870034`，ecc-tools `11ae6d767a4e7dc25b3504326fd7b383e1a711e5`
> 完成提交：ecc-tools child `b8bfc3a79930b0be146ac26ca10dc0e99115f1fc`；parent由本报告、详细计划和submodule pointer所在的后续本地提交承载；均不push
> 范围：CPU targeted Dual-CSR + mixed incremental levelization + full CPU propagation；不含CUDA、affected-cone propagation、native/IDB commit、物理跨层事务或speedup结论
> 验收原则：功能正确性、typed语义、fresh replay和可重复回归为主；hash、fingerprint、source/object/count inventory只作辅助，不扩张为无上限“哈希攻防”

## 1. 当前结论

Stage 6已把`cpu/incremental`从Stage 5的“targeted Dual-CSR + full levelization + full propagation”推进为“targeted Dual-CSR + mixed incremental levelization + full propagation”。mixed算法只读取current `ActiveCsrEdgeView`与previous合法levels；full propagation只消费reconstructed caller-supplied levels，不暗中再次进入full levelizer。

成功域保持为mixed-order-compatible。actual graph为真实cycle时返回`kActualCycle`；actual仍为DAG但old-level quotient需要逆序时返回`kOldLevelOrderConflict`；view error、mapping overflow、indegree/processed-count与reconstruction不变量均为typed failure。合法但不紧凑的levels允许publish，不能因与fresh full具体层布局不同而判错。

transaction路径同时完成了Stage 5 full与Stage 6 mixed的typed factory、sealed execution trace和mode-dispatched recovery。每个descriptor恰有一条真实执行记录；full真实入口delta=1，mixed/external路径delta=0，correctness cases fallback=0。production publish不读取fresh答案，外部controller只在两侧sealed后做rank-free逐字段比较。

最终GCC 14 strict Release统一Stage 6标签14/14通过，Ninja Stage 5/6 source isolation 2/2通过；ASan、UBSan各8/8无诊断；parent冻结STA 227/227和non-PDK 1665项通过。最终独立全diff审查结论为`APPROVE`，无remaining blocker、major或minor。

## 2. 已交付功能

### 2.1 Pure mixed levelization

- tagged类型区分virtual old level、new actual node与mixed vertex，所有边界、往返和checked arithmetic由独立mapping test冻结。
- builder以previous level压缩old nodes并建立virtual chain；old→new、new→old、new→new形成mixed precedence，old→old验证previous严格顺序。
- actual endpoint parallel dedup与virtual proxy alias dedup分开计数；BaseOut与AuxOut在同一generic active traversal中处理，eligibility来自payload而非storage kind猜测。
- corrected Kahn以去重后indegree为权威，frontier确定性排序；actual classifier只负责区分actual cycle与quotient conflict，不生成可publish levels，也不触发full backend。
- reconstruction输出当前全部actual NodeId的完整permutation、offsets与1-based inverse；通用validator重验view error、complete、无空层、permutation/inverse与全部eligible edge inequality。
- fixed seeds `1, 7, 42, 20260901, 0xdeadbeef`覆盖成功样本、actual-cycle、old-order conflict、四类edge、parallel/proxy、Base/Aux、eligible mask、malformed previous/mapping与原子不变；oracle独立于builder实现。

### 2.2 Caller-supplied backend与真实入口证据

CSR CPU backend新增external-level overload。它先调用DB-free `validateCsrFifoLevelization()`，再按给定levels完成初始化、forward与required propagation；原full overload保持为独立oracle。

full-levelizer operation guard位于generic真实入口，flat overload不重复计数。focused正控证明full backend delta恰为1；合法external levels delta为0；malformed external levels在传播前失败且delta仍为0。该值由move-only guard在factory内封口，调用者和JSON不能伪造。

### 2.3 Typed factory、transaction与failure matrix

`makeMixedLevelizedDualCsrAnalysisState()`只接受verified capability与previous levels。factory内部按顺序重验exact-before graph/resolver/index/identity、descriptor delta、updater结果、mixed pipeline、external propagation与intrinsic state；公开API不能注入descriptor、timing、levels、telemetry或post identity。

`LevelizationExecutionTrace`改为sealed immutable class，私有构造并只暴露getter，携带generation、mode、levels、traversal、full entry delta、fallback、supplied-level validation与mixed telemetry。coordinator只publish完整verified aggregate，并在swap前再次逐字段绑定exact-before。

故障矩阵真实覆盖：

- stale exact-before；
- 错误`ArcGroupIndexDelta`；
- updater conflict；
- external propagation的intrinsic timing failure。

四类均保留exact `DualCsrStageFailureOrigin`、`DualCsrViolationCode`、field/message及committed aggregate不变。测试专用fault adapter只修改detached move-only batch/descriptor，不给production factory增加绕过参数。

### 2.4 Receipt与production/fresh controller

Stage 6 functional receipt将graph/reference、timing与levelization职责分开。graph/reference与normalized semantic trace逐字段exact；timing numeric沿用Stage 2 tolerance；targeted/fresh levelization各自验证，不比较raw dense ID、physical slot或具体层布局。

execution binding从baseline reference nodes `{id,key}` 与逐代descriptor node appends重建dense `NodeId → NodeKey`。每代按offset、NodeKey→level inverse与逐层精确NodeKey集合绑定execution levels；same-level FIFO顺序与canonical顺序不同是合法正例，跨层换序、traversal tamper和低于旧tolerance的semantic float tamper均被拒绝。

equal-cost predecessor不接受任意winner，而是由graph与numeric证据导出admissible winner set。`legal_noncompact`只作为report-only观察值，不授权错误level，也不进入committed/recovery equality。

frozen controller覆盖：

- `synthetic_two_batch`两个prefix；第二批把第一批新增node按old/virtual处理；
- `real_buffer_fanout`一个prefix；
- targeted、fresh、comparator为隔离process，角色stderr为空；
- 每批mixed build/Kahn/reconstruct均真实执行，full entry delta=0、fallback=0，最终功能收据与fresh CPU/full等价。

### 2.5 Recovery与active-payload边界

mode recovery覆盖`g1=kFullStage5 → g2=kMixedStage6 → poison → 新session rebind/replay → 下一批mixed`。token发生变化，deterministic graph/timing/resolver/index/identity/levels/execution trace精确恢复；wall-clock不进入state或exact equality。

active-payload microcase使用合同合法的`in → A → (2条parallel cell arcs) → Y → n0 → fanout loads`。真实capture plan必须发现multiplicity>1同-base group；删去一个peer capability后，真实reader返回exact `kArcMultiplicityMismatch`，committed aggregate逐字段不变。随后合法capture/build继续成功。

该microcase还覆盖active survivor current ordinal 0、inactive historical ordinal 0 key collision和inactive poison。三个独立session分别执行mixed poison0、mixed poison97与public full poison0；mixed结果不受inactive payload影响，最终功能收据与独立public full全字段相等。level/trace只在同mode内精确比较，不跨mode错误要求层布局一致。

## 3. 验收记录

### 3.1 GCC 14 strict Release

主验证树为Ninja Release，GNU 14.3.0；Stage 6 production/test targets使用：

```text
-Wall -Wextra -Werror -pedantic -ffp-contract=off
```

统一标签命令使用`PYTHONDONTWRITEBYTECODE=1`及所需Tcl/Zlib/GCC runtime路径，结果为14/14 PASS：6项pure mapping/builder/Kahn/reconstruction/pipeline/property、transaction、external backend、functional receipt、controller selftest、synthetic/real differential、mode recovery和active-payload microcase。

额外回归中，legacy structured batch、真实partial deactivation及active-payload为#30/#31/#181，均PASS。Stage 5与Stage 6 source-isolation在Ninja树2/2 PASS；late-stage oracle allowlist只接受明确test target与精确test-only source，production include扫描仍为阻断门。

### 3.2 Stage 2–5与parent回归

GCC 14 broad范围复跑153项，首轮147项PASS。唯一功能项`ista_timing_dual_csr_structured_batch_test`因运行时未找到`libtcl8.6.so`失败，补回已配置Nix Tcl runtime路径后PASS，因此功能/语义项合计148/148。

其余5项是既有硬编码辅助inventory：buffer Stage 4 object mapping、reference-input raw DTO objects、CSR core object count、snapshot include allowlist、adapter object count。这些在后续targets与增量编译树上期待值滞后；功能路径、fresh replay与source isolation主证据均通过，因此按总体原则如实单列，不继续修改数量常量或把清单绿灯冒充功能修复。

parent测试在`/home/shigure/code/ecc`运行，前后`git status --short --ignore-submodules=all`一致，只保留用户已有`CLAUDE.md`与Stage 1–2会议报告：

- 冻结12文件STA清单：227/227 PASS，1.29s，wall 1.85s；
- non-PDK：1665 passed、8 skipped、4 deselected、13 xfailed、2 warnings，20.27s，wall 20.86s；
- 两个warning均为第三方`jsonrpcserver/importlib.resources` legacy API deprecation；
- 全程`PYTHONDONTWRITEBYTECODE=1`、`-p no:cacheprovider`，无新增测试副产物。

### 3.3 Sanitizer

ASan与UBSan在独立GCC 14树各强制重建并运行相同8项：6项pure算法/property、external-level backend、functional receipt。

- ASan：`detect_leaks=1:halt_on_error=1:abort_on_error=1`，8/8 PASS，无ASan/LSan诊断；抽查四类binary均加载`libasan.so.8`。
- UBSan：`halt_on_error=1:print_stacktrace=1`，8/8 PASS，无UBSan诊断；抽查四类binary均加载`libubsan.so.1`。

两棵树共享源码根`bin/lib`输出，验证时按sanitizer分别强制覆盖并立即`ldd`+CTest，避免把另一棵树的较新binary误作证据。native/Tcl全依赖sanitizer未继续扩张；其高风险功能由strict Release transaction、active-payload、recovery和production/fresh differential覆盖。

### 3.4 Hygiene与独立审查

- `git diff --check`无输出；
- 所有变更文件少于700物理行，最大为699/698/689；
- 无`__pycache__`、`.pyc`、`.orig`、`.rej`、`.patch`或`.bak`残留；
- CTest两套Stage 6标签均选中同一14项，避免pure/transaction遗漏；
- 最终独立全diff审查结论`APPROVE`，无remaining blocker、major或minor。

## 4. 边界与无性能结论

- propagation仍是full graph；Stage 10才讨论affected-cone。
- mixed成功域不支持需要重排previous old-level相对顺序的任意DAG；此类返回typed conflict，不fallback伪装成功。
- Stage 6不commit native Database/IDB，candidate仍须rollback baseline。
- receipt中的timing和mixed phase duration只用于观察；wall-clock不进入publish或recovery equality。
- 未进行正式warm-up/sample性能实验，不报告speedup、break-even、论文规模可比性或外推。
- hash、raw dense ID、physical slot、对象数量及depfile不是功能PASS来源；真实production dependency泄漏仍保持独立阻断。

## 5. Stage 7 handoff

Stage 7可在保持`ISTA_ENABLE_CUDA=OFF`默认CPU兼容的前提下，开始可选CUDA构建与GPU full baseline。它应复用Stage 2 CPU/full functional oracle、Stage 5 Dual语义和本阶段level/timing receipt边界；不得把CPU mixed实现冒充GPU执行，也不得跳过真实device、synchronization与逐字段CPU/GPU等价门。

Stage 6 child已在`IncreGPUSTA`本地提交为`b8bfc3a79930b0be146ac26ca10dc0e99115f1fc`，未push。parent随后只提交本报告、详细计划与submodule pointer，不夹带用户已有修改。

## 2026-09-05 第二轮清理同步

mixed pipeline 统一通过 `runCpuIncrementalLevelization()` 自由函数调用，删除无状态静态类包装。确定性 trace 类型移至 mixed 模块并被运行遥测复用；transaction 仍只持久化确定性基类，计数恒等式只保留一份。耗时与 `legal_noncompact` 继续排除在持久化及恢复等价之外，JSON wire 不变。 验证与范围说明见[第二轮清理报告](stage0-stage6-second-cleanup-report.md)。
