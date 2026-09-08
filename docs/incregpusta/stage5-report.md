# 阶段 5 报告：CPU targeted Dual-CSR 与 direct-view full timing

> 2026-09-08 冗余清理：删除遗留 recovery 链与重复 factory/publish 校验；OFF 性能入口只读 native 构建信息；ON 诊断使用现有 controller。 详见 [清理报告](stage0-6-redundancy-cleanup-report.md)；以下阶段验收数据继续表示历史结果。

> 当前开发协议补充（开发检查分离）：重复 aggregate/index/resolver 验证、narrow capture 审计和 execution trace 全量 payload 归 ON；局部 descriptor 适用性、必要 active-edge 数量及发布身份始终保留。 后续改动必读 [开发检查规范](development-guidelines.md)，双模式实测与历史验收的区别见 [本轮实施报告](debug-checks-implementation-report.md)。原阶段验收数字保留为历史记录。

> 状态：完成；功能实现、production runtime/controller differential、Release 1 warm-up + 6 raw timing smoke、GCC 14功能矩阵、parent pytest、ASan/UBSan核心边界检查及最终独立全diff审查均已闭合
> 日期：2026-09-02
> 基线：Stage 4 parent `ace28d79e19647c6f4866a339cc6faa7dca61fa9`，ecc-tools `eff4706f77a882d84317341f78e567ef5262b6d1`
> 完成提交：ecc-tools child `11ae6d767a4e7dc25b3504326fd7b383e1a711e5`；parent由本报告、总体计划和submodule pointer所在的本地提交承载；均不push
> 范围：CPU targeted Dual-CSR 图更新、持久 BaseOut/BaseIn/AuxOut、typed descriptor/rollback、direct-view full CPU levelization/propagation，以及 fresh CPU/full differential；不含 mixed levelization、CUDA、affected-cone propagation、物理 IDB 提交或 speedup 结论
> 验收原则：功能正确性优先；topology、payload、level、timing、generation、rollback 与 source isolation 逐字段闭合。hash、raw object/depfile 与数量 inventory 只作辅助，不能替代功能证据

## 1. 当前结论

Stage 5 已实现 generation-0 一次性 full typed anchor，以及之后每批只消费 semantic plan、committed resolver/index、局部 candidate capture 与 verified descriptor 的 targeted Dual-CSR 更新路径。persistent state把逻辑 ArcId 与 Base physical slot分离：BaseOut/BaseIn允许 tombstone replacement，既有source无法放入Base的新增forward arc进入AuxOut，new-node rows只在尾部append；logical ArcId只append，不因physical slot复用而复活。

full CPU levelizer和propagator已泛化为 `ActiveCsrEdgeView`/`TimingPayloadView`，Dual实现直接遍历 `BaseOut ∪ AuxOut` 与 `BaseIn`。本阶段仍有意执行full levelization和full propagation；“incremental”只描述图结构与相关timing input payload的targeted更新，不描述affected-cone propagation。

transaction以完整committed aggregate staged后一次publish，正常结束与失败路径都要求installed native candidate回滚baseline。targeted batch区间的合同是native full reference export、host snapshot rebuild和fallback均为0；fresh oracle只在独立one-shot process运行，不向descriptor、resolver或state提供答案。

Stage 5全部门禁现已闭合。DB-free core、updater telemetry、Python controller自测、GCC 14 production probe、frozen synthetic/real全prefix differential、Release timing smoke、parent冻结STA/non-PDK pytest与修复后Stage 2–5功能矩阵均已通过实际运行。narrow capture只对完整affected row中的unchanged peer开放committed exact-key回查，未知、新建或staged不一致节点仍拒绝；reference wire温度与start-seed raw顺序也已按C++权威合同闭合。ASan/UBSan核心与异常边界矩阵无诊断，最终独立全diff审查结论为无保留APPROVE。

## 2. 已交付功能

### 2.1 DB-free Dual-CSR core

- `DualCsrState`拥有nodes、append-only arc slots、BaseOut、BaseIn、AuxOut、extent/capacity、generation与update telemetry。
- generation 0由唯一合法的full `CsrReferenceInput`构造；正常batch不得再次调用baseline factory。
- immutable descriptor覆盖node/arc append、logical deactivate、Base forward/reverse replacement、Aux rows、payload/reference delta与ArcGroupIndexDelta。
- updater先在detached state完成allocation、apply与全量intrinsic validation，再将verified aggregate交给transaction publish；容量不足或任何swap前故障不写committed state。
- BaseOut与BaseIn对active ArcId严格转置；BaseOut与AuxOut不重叠；inactive ArcId不出现在active adjacency；Aux row source mapping严格互逆。
- capacity grow采用可验证的元素槽数；allocator capacity不是跨平台golden。

### 2.2 Stable identity、parallel arcs 与行语义

- `StableArcRef`只表达creation/history身份，不把历史parallel ordinal当作current active `ArcKey` authority。
- current key由candidate局部native顺序和共享parallel-ordinal分配产生；partial-group survivor可从stable ordinal 1合法重编号为current ordinal 0。
- ArcGroupIndex按base覆盖完整active group并要求current ordinals连续；resolver/index/state分别闭合，避免用跨进程dense ID或raw rank授权publish。
- descriptor v1.2的三类row evidence从真实BaseOut+Aux/BaseIn shadow逐批消费：owner覆盖、expected→replacement membership、forward/reverse全局双射、每行唯一性与exact FIFO均单独验证。
- generation-0 typed anchor保存完整baseline事实；反向replay必须逐字段回到anchor，不能只比较摘要。

### 2.3 Native narrow capture 与transaction

- pre-candidate阶段只从semantic edits、committed resolver/keyed view/index和exact before-state生成move-only pending capability。
- candidate apply/execute后，narrow capture只读affected bases、局部native adjacency与计划内payload；不调用full graph/reference export。
- verified capture把StableArcRef、ArcId、candidate record/payload和current key逐项绑定后，才能构造verified descriptor并进入core stage。
- committed aggregate包含graph、timing、resolver、ArcGroupIndex、identity、generation与traces；publish是完整aggregate的一次可见性动作。
- first batch从baseline create candidate；后续batch clone累计carrier后回滚旧carrier，再apply/install新batch；run结束最终回滚baseline。
- source artifact、primary IDB与one-shot loader隔离沿用Stage 4合同；fresh与targeted进程只交换semantic input identity和最终sealed receipt。

### 2.4 Direct-view timing 与receipt

- generic levelizer/backend只依赖DB-free edge/payload views；flat与Dual实现进入同一遍历入口。
- Dual timing result独立保存presence/value、level/order、forward/required propagation、path与predecessor语义；inactive lanes必须absent/default。
- functional receipt只按NodeKey/ArcKey比较active语义，不含session-local dense IDs、physical tombstone或raw fingerprint。
- structural receipt单独保存stable high-water、inactive history、Base/Aux physical rows、capacity与telemetry；transaction receipt保存session/generation、typed anchor、descriptor/semantic trace、phase、cleanup与operation counters。
- controller对每个prefix使用targeted、fresh oracle和comparator三个角色，跨进程只比较functional receipt；structural/transaction在targeted进程内验证。

## 3. 已闭合的正确性证据

### 3.1 Controller与descriptor语义

以下项已由独立只读审计逐项复验，且controller self-test实际exit 0：

- 三类row evidence真实执行owner、双射、expected→replacement与FIFO验证；同一source两条arc交换顺序的canary被拒绝。
- generation-0 `out_arc_ids`交换canary实际调用anchor validator并断言拒绝。
- traversal all-zero和plus-one tamper均调用traversal validator并断言拒绝。
- ArcGroup current ordinal gap canary实际修改输入、调用validator并断言拒绝。
- created survivor stable ordinal 1→current ordinal 0正例被接受；correlated StableArcRef tamper仍被拒绝。
- 首批expected row的`WRONG_CELL`负例经controller self-test调用reference replay validator并被拒绝。
- affected native row中的unchanged peer只允许通过committed `NodeKey → NodeId` exact回查；live `ExistingNodeRef`、slot、name和before extent必须一致。positive committed peer、slot shift与unknown/new peer三态canary均在GCC 14 strict target通过。
- `analysis_context.temperature`按C++ wire合同端到端保持canonical string；`25`和sentinel正例通过，number/bool、`-0`、外空白、leading zero、trailing-zero小数、exponent、NaN与Inf均被拒绝。
- functional receipt按NodeKey canonical-sort的start seeds会先验证唯一且exact cover `ordered_starts`，再恢复raw严格序列；乱序正例可恢复，duplicate/missing/extra均拒绝，anchor/reverse仍使用exact vector比较。

这组证据针对语义字段和行序本身，不依赖hash。controller中未调用的旧schema validator已移除，traversal canary拆到独立self-test helper；相关Python文件均低于700物理行。最新GCC 14 controller self-test为CTest #99 PASS；frozen synthetic #100覆盖2个prefix、frozen real #101覆盖1个prefix，二者均PASS且targeted/fresh使用新PID、role stderr为空。

### 3.2 Core、updater与resource observation

- Dual-CSR core/updater在configured strict flags下完成独立对象构建与updater telemetry CTest运行。
- C++ resource observation从真实vector `size()`、`capacity()`和`sizeof(T)`采集，不由Python猜测capacity。
- 每个published batch记录tombstone ratio、requested/executed strategy，以及10个核心vector的logical elements、capacity elements、element size与estimated reserved bytes。
- Python validator要求10个buffer按冻结顺序完整出现，验证`logical <= capacity`与`reserved == capacity * element_size`，并同structural receipt的真实extent交叉闭合。
- requested strategy固定为`cpu/incremental/error`；executed strategy固定为`cpu/targeted_dual_csr/none/full_graph`，同时与full export/rebuild/fallback counters及propagation scope交叉验证。

C++ resource schema与Python strict validator已逐字段对齐，独立telemetry审计结论为APPROVE、无finding。production controller与timing JSON现已实际验证：每个published generation都有一项observation，冻结策略、tombstone ratio及10-vector真实capacity/sizeof乘积全部闭合。

### 3.3 Timing证据合同

- 每批phase timing严格要求generation chain及`pre_candidate_prepare`、`candidate_apply_execute`、`post_candidate_capture`、`dual_csr_update`、`full_levelization`、`full_propagation`、`invariant`、`verify`、`publish`九个独立非负时长。
- missing `verify_ms`与negative `invariant_ms` canary均被controller self-test拒绝。
- `fresh_oracle_ms`由外部child process wall clock单列，只用于correctness运行成本记录，不计入incremental phase。
- Release smoke固定1次warm-up和至少6个raw samples；每个sample顺序运行targeted与fresh child，并在保存timing前完成完整functional/source/rollback/counter验证。
- environment fingerprint记录OS、CPU、affinity、Python、probe、trace、build config，以及CMake compiler ID/version；不以binary hash作为验收条件。

Release smoke CTest #102实际PASS，产物为`/home/shigure/code/ecc/chipcompiler/thirdparty/ecc-tools/build-ista-step5-gcc14/src/operation/iSTA/test/stage5-timing-smoke/timing-smoke.json`。独立JSON断言结果为warm-up 1、raw 6、raw phase records 12、raw resource observations 12、14个child PID全部唯一，14个role stderr均为空；所有九phase有限且非负，functional/source/rollback均true，full-export/fallback counters均为0。

6个raw `targeted_wall_ms`为`[46.793545, 47.023932, 45.42225, 44.018989, 44.905266, 44.080503]`；对应`fresh_oracle_ms`为`[33.31683, 34.568026, 34.037853, 33.263563, 34.012375, 32.996184]`。environment fingerprint记录Release、GNU 14.3.0、13th Gen Intel Core i7-13700H、20 logical/affinity CPUs，以及13,440,376-byte probe。

这些是完整保存的raw工程smoke证据，不做统计显著性、speedup或break-even结论。JSON明确记录`functional_correctness_primary=true`、`hash_used_as_acceptance=false`、`performance_claims_made=false`与`speedup_or_break_even_reported=false`。

### 3.4 异常域修复与功能矩阵

完整回归初跑发现CTest #119 `ista_csr_graph_export_failure_test`为唯一真实功能失败：graph export复用shared library-signature projector时，非法`TransType::kNone`触发的`ReferenceExportAbort(kInvalidTableShape)`越过graph API边界。Stage 4合同要求此类native graph畸形返回`CsrGraphExportFailure{kMalformedTopology}`，因此fixture与期望均保持不变。

修复只位于`projectLibrarySignatures()`这个graph→reference交界：捕获精确的`ReferenceExportAbort`后转为graph-domain `malformed()`；没有在public graph boundary增加宽泛catch，也没有改变reference exporter自身的failure code/phase。回归除原unknown map key外，还覆盖unknown timing sense、trigger/check transition和table variable。修复后#119、graph/reference正反合同与完整Stage 2功能矩阵均通过。

GCC 14.3.0 strict Release树登记208项CTest。按功能分组复跑结果为：Stage 2 70/70、Stage 3 16/16、Stage 4 19/19、Stage 5主组13/13、narrow/committed-peer 2/2、generic/public headers 4/4；各命令累计124/124，扣除4项交叉重复后为120/120个唯一功能测试，0 fail、0 skip。Release timing smoke #102已单独闭合，未为异常修复重复采样或改变raw证据。

辅助/环境项与功能结论分列：

- 全仓`all`构建到78%时，`py_idb`因系统Python 3.12 multiarch `pyconfig.h`缺失停止；`ecc_bin`已link，这不是Stage 2–5功能源码失败。
- 4项历史source inventory期待值滞后（#135、#152、#168、#173）；另6项检查硬要求Ninja而当前严格树为Unix Makefiles（#153、#164–#167、#178）。
- 源树14个旧`.pyc`已精确清理；#90随后只剩其既有Ninja前置限制，不再报告缓存污染。

这些静态数量、生成器和外围binding环境事实均保留在报告中，但不替代或推翻逐语义字段、fresh replay、rollback及source isolation的功能证据。

## 4. 工具链说明：GCC 13误报与GCC 14严格树

原有GCC 13严格树在重新编译冻结Stage 4 `BufferTraceCanonicalEncoding.cpp`时，把`std::visit`返回variant内部vector引用报告为`-Werror=dangling-reference`。variant owner在整个使用期存活，且该文件与Stage 4封存提交无diff；这是工具链对标准库访问路径的误报，不是Stage 5 resource telemetry造成的生命周期错误。

为保持冻结边界，Stage 4 source没有被修改，也没有关闭Stage 5 strict warnings。曾评估Clang严格树，但本机只有libgomp、没有匹配libomp；真实parallel-region链接会产生未解析`__kmpc_*`，因此没有用手工定义`_OPENMP`或混用runtime伪造合规构建。

最终选择全新out-of-tree GCC 14.3.0 Release树`build-ista-step5-gcc14`：

- C/C++ compiler来自同一Nix GCC 14 wrapper；
- OpenMP使用真实`-fopenmp`；
- Boost、Flex、Zlib、Tcl header/library均使用精确Nix路径，不把整个`/usr/include`加入Nix libstdc++编译；
- Stage 5 targets继续使用`-Wall -Wextra -Werror -pedantic -ffp-contract=off`；
- timing JSON已保存`GNU`及实际compiler version，具体值以下文runtime产物为准。

当前状态：GCC 14 production probe 已完整link，binary为`bin/ista_dual_csr_production_fresh_probe`，大小13,440,376 bytes。原`unplanned_dependency(6)`已通过committed exact-key peer fallback修复，并由unknown/new/staged mismatch负例守住窄化边界；direct targeted synthetic/real prefix-1、controller全prefix及timing smoke均已通过。timing fingerprint实际保存`GNU`和`14.3.0`。

### 4.1 ASan/UBSan检查

sanitizer使用独立`CMD_BUILD=ON`构建树，避免覆盖shared production probe。项目原生`SANITIZER=ON`会把directory-level ASan选项注入精确`COMPILE_OPTIONS` inventory，配置期即被合同拒绝；因此保留该证据后，采用等价的显式C/C++及linker instrumentation。GCC 14 Release优化又分别在libstdc++ vector初始化和合法`std::nullopt`路径触发`-Werror=array-bounds`/`-Werror=maybe-uninitialized`编译期误报；未增加任何`-Wno`，改用Debug继续运行时检查，目标自身strict flags保持不变。

- ASan：`-fsanitize=address -fno-omit-frame-pointer`，`ASAN_OPTIONS=detect_leaks=1:halt_on_error=1:abort_on_error=1`；#16–#20、#119、#140共7/7 PASS，全部ELF实际依赖`libasan.so.8`，无ASan/LSan诊断。
- UBSan：`-fsanitize=undefined -fno-sanitize-recover=all -fno-omit-frame-pointer`，`UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1`；#16–#19、#119、#140、#148共7/7 PASS，抽查核心/边界ELF实际依赖`libubsan.so.1`，无UBSan诊断。

native/production sanitizer目标会继续拉入iDB/iCTS、Tcl、lefdef、HiGHS等外围全仓依赖；在精确Nix include补齐后仍形成大范围非Stage 5编译，因此按比例风险停止扩张，不宣称native/probe sanitizer结果。其生产路径由GCC 14 strict Release probe、frozen synthetic/real全prefix differential、120/120功能矩阵和rollback/source-isolation证据覆盖。sanitizer构建未修改tracked源码或shared production probe；外围构建重链的Git-ignored lefdef静态库作为透明环境事实保留，未冒充源码洁净证据。

## 5. 验收记录与闭合门禁

本轮功能门在`/home/shigure/code/ecc/chipcompiler/thirdparty/ecc-tools`以同一纯Nix/GCC 14环境串行执行：

- controller self-test：`env PATH=/nix/store/3z956lqdd5symanwacfa63l4bzcvcbnv-tcl-8.6.16/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin LD_LIBRARY_PATH=/nix/store/61a1nwx3w6rqyaisj5rn1sal1981apm7-zlib-1.3.2/lib:/nix/store/41ym1jm1b7j3rhglk82gwg9jml26z1km-gcc-14.3.0-lib/lib:/nix/store/3z956lqdd5symanwacfa63l4bzcvcbnv-tcl-8.6.16/lib PYTHONDONTWRITEBYTECODE=1 ctest --test-dir build-ista-step5-gcc14 -R '^ista_dual_csr_trace_controller_selftest$' --output-on-failure -j1`。
- frozen differential：同一`env`前缀后运行`ctest --test-dir build-ista-step5-gcc14 -R '^ista_dual_csr_frozen_(synthetic|real)_differential$' --output-on-failure -j1`。
- Release timing：同一`env`前缀后运行`ctest --test-dir build-ista-step5-gcc14 -R '^ista_dual_csr_release_timing_smoke$' --output-on-failure -j1`。

parent pytest在`/home/shigure/code/ecc`运行，显式禁止Python字节码和pytest cache写入。冻结STA的12文件清单来自Stage 2提交`49f1bc9`的exact changed tests，逐文件collection合计227；实际命令为：

```bash
env PYTHONDONTWRITEBYTECODE=1 /usr/bin/time -f WALL_SECONDS=%e .venv/bin/python -m pytest -p no:cacheprovider \
  test/tools/ecc/test_module_timing.py \
  test/tools/ecc/test_module_timing_snapshot.py \
  test/tools/ecc/test_runner.py \
  test/tools/ecc/test_runner_sta_mode.py \
  test/tools/ecc/test_runner_sta_snapshot.py \
  test/tools/ecc/test_sta_session.py \
  test/tools/ecc/test_sta_session_snapshot.py \
  test/tools/ecc/test_sta_signoff.py \
  test/tools/ecc/test_sta_snapshot.py \
  test/tools/ecc/test_sta_snapshot_context.py \
  test/tools/ecc/test_sta_snapshot_schema.py \
  test/tools/ecc/test_sta_snapshot_transition.py -q
env PYTHONDONTWRITEBYTECODE=1 /usr/bin/time -f WALL_SECONDS=%e .venv/bin/python -m pytest -p no:cacheprovider \
  test/ --ignore=test/examples/test_soc.py -m "not pdk" -q
```

冻结STA结果为227/227 PASS（pytest 0.83s，wall 1.23s）。non-PDK全量结果为1665 passed、8 skipped、4 deselected、13 xfailed、2 warnings（pytest 19.94s，wall 20.47s）；两条warning均为第三方`jsonrpcserver`/`importlib.resources` legacy API deprecation，无功能失败。测试前后`git status --short --ignore-submodules=all`完全一致，没有新增tracked/untracked测试副产物。

| 门禁 | 状态 | 实际证据 |
|---|---|---|
| Python/controller self-test与`WRONG_CELL`负例 | PASS | CTest #99，1/1 PASS；typed/reference replay/row/traversal/ordinal canary全部执行 |
| Core/updater/resource observation专项 | PASS | 最终GCC 14 target/CTest输出摘要 |
| GCC 14 strict production probe link | PASS | `bin/ista_dual_csr_production_fresh_probe`，13,440,376 bytes，GNU 14.3.0 strict Release |
| frozen synthetic differential | PASS | CTest #100，2 prefixes；summary：`build-ista-step5-gcc14/src/operation/iSTA/test/stage5-controller/synthetic/run-ak83xf4y/controller-summary.json` |
| frozen real differential | PASS | CTest #101，1 prefix；summary：`build-ista-step5-gcc14/src/operation/iSTA/test/stage5-controller/real/run-td9d3y1p/controller-summary.json` |
| Release timing smoke | PASS | CTest #102；1 warm-up + 6 raw，12 phase/12 resource observations；artifact：`build-ista-step5-gcc14/src/operation/iSTA/test/stage5-timing-smoke/timing-smoke.json` |
| Stage 5功能CTest matrix | PASS | 主组13/13、narrow/peer 2/2、generic/public 4/4；#102另行PASS |
| Stage 4/3/2回归 | PASS | Stage 4 19/19、Stage 3 16/16、Stage 2 70/70；全分组120/120唯一功能测试 |
| parent冻结STA/non-PDK pytest | PASS | 冻结STA 227/227；non-PDK 1665 passed、8 skipped、4 deselected、13 xfailed、2个第三方deprecation warnings；无失败、无测试副产物 |
| sanitizer核心/异常边界 | PASS | ASan 7/7、UBSan 7/7，无诊断；native/probe范围限制如4.1节 |
| 最终独立代码审查 | APPROVE | 无保留；无功能、语义、ownership、事务原子性或source-isolation blocker |

所有PASS均来自实际命令或保存产物；辅助inventory、生成器和外围binding限制已单列。production runtime曾暴露的schema、ordering与#119异常域问题均保留根因并在修复后完整回归，没有通过修改报告措辞掩盖失败。

## 6. 已知限制与无性能结论

- Stage 4两条buffer trace按算法会用tombstone replacement或new-node Base row，合法Aux edge数应为0；Aux overflow/persist/clear由独立Stage 5-only DB-free microcase证明，不把该fixture冒充production buffer insertion。
- propagation仍是`full_graph`，levelization仍是full direct-view；Stage 6才实现mixed incremental levelization，Stage 10才讨论affected-cone、CUDA、cross-layer publish和正式性能。
- Stage 5不commit native Database或物理IDB；native candidate只是隔离mutation/capture载体，并须最终rollback baseline。
- supported mutation仍受Stage 4 frozen semantic edits与NoParasitic等policy约束；真实parasitic、general remove/reconnect和物理放置不在本阶段成功路径。
- vector host bytes是`capacity * sizeof(element)`的shallow storage estimate，不含allocator metadata、对象深层分配或跨平台golden含义。
- fresh oracle wall time、targeted wall time和各phase raw samples只证明计时机制可运行、执行策略与rollback证据可保存。Stage 5不报告speedup、break-even、论文可比性或规模外推。
- hash、raw dense ID、object/depfile与数量inventory不作为功能PASS来源；真实forbidden dependency或所有权边界泄漏仍是独立架构阻断。

## 7. Stage 6 handoff

Stage 6只应依赖已冻结的generic `ActiveCsrEdgeView`/`TimingPayloadView`、Dual实现、append-only high-water、active ArcId/payload、generation与telemetry。它不得重新decode flat CSR、重新full-export native graph、假定Aux为空，或把历史StableArcRef ordinal当current active key。

Stage 5保留full direct-view levelization/propagation作为Stage 6 mixed builder的功能oracle。本报告第5节门禁已闭合、最终独立审查无remaining finding；child已提交，本报告随parent本地提交承载。现在可按已APPROVE的Stage 6详细计划进入mixed levelization实现，仍不push。

## 2026-09-05 第二轮清理同步

typed JSON validator 删除已无调用的 helper，以及只由自测触达的 reference library 副本；原 library/temperature 正负例改用实际执行的 `validate_reference_value()`，reference replacement chain 也直接调用该入口。功能 wire/schema 不变。 验证与范围说明见[第二轮清理报告](stage0-stage6-second-cleanup-report.md)。
