# ECC IncreGPUSTA 阶段 2 Step 8 详细实施计划

> 状态：v0.15 producer-scratch closure review candidate；补齐真实probe scratch清理、final-only publication与失败隔离合同
> v0.15 变更：`sta/`是producer-owned opaque scratch；publication在首次hardlink前以全lane零变更预检、fd-relative symlink-safe删除与dir-fsync闭合；权限只接受exact `{0700,0755}`，成功lane最终只含final JSON；本文件actual=713，超过700建议不构成失败
> v0.14 历史：不得为满足500/550/700行建议而做高成本、晦涩或削弱证据的压缩，任何gate/reviewer不得仅因行数拒绝；超过建议是为完整保留owner裁决与证据语义，review结论由本SHA对应的外部review receipt记录
> v0.13 历史：在v0.12完整inverse/合法mutation/case-distinct KAT基础上补齐selftest唯一enum-only reference-model边；exact七仅指修改/Ruff文件且不扩成八个
> 依据：`stage2-detailed-plan.md` §9.1、§14、§15.4、§16、§18、§19；Step 3–7 冻结计划
> 范围：test-only real differential fixture、两个 child、wire/controller、CTest 与门禁；不改 production C++/Python、Stage 0/1 golden 或公开配置
> 核心证明：独立 fresh process 中，native CPU/full oracle 与 poison-before-export 的纯 backend/scatter lane 按 semantic key 等价；post-scatter native rerun 可覆盖 canary 并恢复 oracle
> 审计原则：先冻结 wire/process/fixture 合同，再列 source/target，最后编码；任何未满足 witness 都 hard fail，不 skip/xfail/降级

## 1. 裁决、边界与冻结基线

### 1.1 真实隔离合同

Step 8 新增两个 executable，但不再声称“两个 binary 的 dependency closure 隔离”。`ista_interface`、adapter 和 direct link 的传递闭包可使 oracle binary 含有未调用的 backend/scatter 符号；`nm` 全 binary 无符号断言不是本步证据。

必须同时成立的合同是：

- 每个 case/repeat 同时启动 oracle/reference 两个 fresh PID；PID、address space、`Database`、session、token、DTO、cwd、run-dir、temp 均不共享。
- oracle 新增 TU 不调用 reference export/build/compute/scatter/poison/readback；oracle main 只调用 opaque `readAndEncodeNativeTiming(const Database&) -> NeutralWire`。
- 只有 `CsrRealDifferentialOracleEncoding.cpp` include/call native oracle reader；其余 oracle 新增 TU 看不到 oracle DTO。
- reference target 不编译、不链接、不使用任何 `CsrNativeTimingOracle*` test object，也不调用 native-oracle materializer/reader。
- reference backend 输入只来自 poison 后首次成功的 `snapshot.input`；result encoder 只读 detached result，scatter 只消费 snapshot/result；immediate/rerun readback 不成为 backend 输入。
- source 清单、object owner、compile depfile、direct undefined-call 检查证明 TU/data-flow 隔离；runtime receipt 证明实际 executable/cwd/run-dir/temp/PID/argv 路径。
- oracle binary 即使传递含未调用 backend/scatter 符号也不构成失败；新增 oracle object 对这些符号的直接引用才失败。

两个 probe 都可复用 parse/full、scenario 和 neutral-wire test support；共享只表示相同 source bytes，不表示同进程或共享对象。

### 1.2 范围与保守选择

不扩展当前 685 行的 `projection/StaCsrProjectionProbe.cpp`，也不扩展 694 行的 `timing_scatter/StaCsrTimingScatterRerunProbe.cpp`。新工作优先拆分为职责清楚、便于review的文件，500/550/700行仅作为维护性建议。

owner优先级覆盖本计划其他行数措辞：正确性、完整失败语义、真实KAT、可读性与可审计性高于物理行数。超过建议值时记录actual行数、超出的具体原因和review裁决即可；不得为降行数合并不相关职责、引入动态反查/生成、删除断言或压缩成难审代码。格式、license、Ruff/clang、artifact hygiene与功能门禁仍是hard gate。

本步不修改 `source/**`、`interface/**`、`src/interface/python/**`、parent `chipcompiler/tools/ecc/**`、Stage 0 manifest/golden、Stage 1 record/schema、Step 2/7 controller。若必须改 production API、canonical DTO 或算法，立即停止，先修总计划与本计划并重新双审。

不声明 sequential/CRPR、SPEF/parasitic、propagated clock、clock gating/divider、conditional/case-analysis、mutation、generation>0、CUDA/GPU、Dual-CSR、speedup、allocator/RSS、跨进程 token 或 host-capacity golden。

### 1.3 进入条件与 concrete SHA

进入编码前 Step 3–7 全门禁通过；Step 6 计划 SHA 为 `d36e4831626093b8a12813ac2053bdd0a6baae4b77c22ebefed2ecfd94804daa`，Step 7 计划 SHA 为 `2996e2d8f558c7707290e7978fc9b6a1f0ce5f4ba680f201083b0829c5627313`。下列 bytes 由 Step 8 workflow gate hard-code：

| 冻结对象 | SHA-256 |
|---|---|
| `baseline/manifest.json` | `c2cf7aac05719ba7b437b45918cc11ade5fec68f2727135facaa46b7b4f4b47b` |
| `baseline/golden/chain.json` | `a29b1afe4353f34da3c6bbfa6712d58650bd5e85b97884b2df735c18087c74f7` |
| `baseline/golden/diamond.json` | `dfed7bc52f3e5e985127eed3a1a6d76e91649f8704f50188d08a2f0b4b8fea16` |
| `projection/projection_default_compat_v1.json` | `0da3a1b22ffd0ece8198c97854a78e9db342af42c5daad45ebfafb1c9f8fb414` |
| `interface/StaExecutionContract.hpp` | `3985aef36766576a57440a875fcfca2a5e118d2d3b77168e5bdefbb4f1edae1d` |
| `interface/StaExecutionContract.cpp` | `ef437cb0ba026440a0d41579f58162e62f1b9ece343770221a8665f7e32cc514` |
| `test/StaExecutionContractTest.cpp` | `239e93d25a3e94f882369bd70a5f298f28587b1bcb289f7fc34b89bed746a0fe` |
| `benchmark/schema/incremental_sta_samples_v1.schema.json` | `7ed5a94f536aaa11e7471e082efe3610be44b644782de3e9ddb3d3e28ca44045` |
| Step 7 `EXPECTED_PROBE_SHA256` | `ce5f3cdc6baf7bbd90ecbf62aab843191d4fde3d7e3b1f7037758a18e08a9bff` |
| Step 7 `EXPECTED_COMPAT_SHA256` | `0da3a1b22ffd0ece8198c97854a78e9db342af42c5daad45ebfafb1c9f8fb414` |
| Step 7 `EXPECTED_SESSION_CONTRACT_SHA256` | `0ff13a91b9bb741215f6186ae1c5ce935e920c529ab075c5771a42500862698a` |
| Step 7 `EXPECTED_SESSION_CONTROLLER_SHA256` | `8c095eab9159b372a48d4ed97f4a11ded9ac37122ed3c5ce4a923980512d5fab` |
| Step 7 `EXPECTED_SESSION_SELFTEST_SHA256` | `515dc87189027524447d79bc1d459b38c3b5bd64c5f7730578b811c8024916c4` |

编码开始后任一值漂移即失败，不能自动更新 expected。

## 2. Case descriptor、输入 bytes 与 child argv

### 2.1 Baseline 与 extended descripto

chain/diamond继续由冻结的 `reference_input_bootstrap.load_case_descriptors()` 加载，各自 `expected_clocks` exact `["vclk"]`、长度1；其五输入、既有domain/`input_case_sha256`不变，Stage0 fingerprint/golden不重写。Step8新domain只用于extended。

新增 `real_differential/manifest.json` root exact keys：

~~~text
schema, domain, baseline_manifest, baseline_manifest_sha256,
tolerances, extended_cases, coverage_claims
~~~

`schema` 为 `ista-csr-real-differential-manifest/1.0.0`，`domain` 为 `ista-csr-real-differential-input-case/1.0.0`，`extended_cases` 长度 exact 1；`tolerances` exact `{absolute,relative}`，两值都须 type exact non-bool `int|float`、finite/nonnegative且 JSON value exact `1e-9`、binary64 exact `3e112e0be826d695`（拒 bool/NaN/±Inf/negative/±0/signed-zero/任一bit或value drift）。`model.load_manifest` 是 expected tolerance literal 唯一owner；controller/contract/comparison/summary全流程只消费同一 immutable bundle 两值，禁止默认值、fallback或第二份 `1e-9` literal。extended descriptor exact keys：

~~~text
name, top, expected_clocks, inputs, non_unate_anchor,
disabled_anchor, parallel_anchor, loop_disabled_witness,
data_roots, clock_tags, near_tie
~~~

`inputs` exact 五键及 value exact 两键 `path,sha256`，canonical byte order 固定为：

~~~text
tech_lef, cell_lef, liberty, verilog, sdc
~~~

`tech_lef.path`允许且只允许exact bytes `../baseline/fixtures/stage0_tech.lef`，resolve必须exact等于冻结 `baseline/fixtures/stage0_tech.lef` realpath且SHA为 `2d9ad7b970cf857f56eb4ccbac359c1683cef16d8e0cea6c218ff9392af958dc`。其余四path指向新增fixture，仍禁空段/`.`/`..`、absolute/symlink，resolve为manifest subtree内regular read-only input。

extended `expected_clocks` exact两个不同UTF-8 string、按raw bytes递增；baseline编码exact `["vclk"]`，extended例如 `["vclk_a","vclk_b"]`。compact JSON使用 `ensure_ascii=false`、separator `,`/`:`、无空格/尾换行；controller与child各自strict decode/re-encode并验证bytes+SHA及case cardinality 1/2。

`non_unate_anchor`、`disabled_anchor`、`parallel_anchor` 都是 exact unique descriptor：

~~~text
instance, cell, source_pin, sink_pin, owner_name,
library_source_port, library_sink_port
~~~

三者 instance/cell/branch 分离；disabled cell exact `DISABLE_X1` 且仅使用一次，parallel anchor不能是该cell。`loop_disabled_witness` exact keys为 `source,sink,owner_name,minimum_count`；`data_roots` 是两个 exact NodeKey descriptor；`clock_tags` exact等于排序后的两clock名。

`near_tie` exact keys：

~~~text
join_node, row_first_arc, row_second_arc, analysis,
path_source, transition, clock_tag, secondary_root,
secondary_clock_tag, lower_exclusive, upper_exclusive
~~~

bounds固定lower=`1e-9`/upper=`1e-6`，canonical big-endian IEEE-754 binary64 bits exact `3e112e0be826d695`/`3eb0c6f7a0b5ed8d`；两值须finite、sign=0、nonzero、lower<upper，明确拒绝±0/signed-zero。manifest不存arrival/delay/diff/winner/rank/predecessor literal。

extended aggregate SHA依次写domain/version、name/top、排序clocks、五组 `label,path,sha256`、三个anchor、loop/roots/tags、near-tie identity及上述两个binary64 bit strings；integer big-endian、string为U64长度+UTF-8。controller和child独立从verified bytes重算，不信manifest聚合值/echo。

### 2.2 Exact child argv

每 lane argv 顺序和项数冻结为：

~~~text
<oracle-or-reference-probe>
--descriptor-manifest <absolute regular file>
--tech-lef <absolute verified file>
--cell-lef <absolute verified file>
--liberty <absolute verified file>
--verilog <absolute verified file>
--sdc <absolute verified file>
--top <exact string>
--case-name <chain|diamond|supported_branches>
--expected-clocks-json <exact compact JSON bytes>
--repeat-index <canonical decimal U64>
--input-case-sha256 <64 lower hex>
--run-nonce <32 lower hex>
--run-dir <lane-private absolute dir>
--result-temp <lane-private basename>
~~~

child 还须 independently 检查 manifest realpath/SHA、五 input realpath/SHA、descriptor/argv 一致、repeat/nonce/temp 语法，且在 result echo 保存 canonical argv vector、clock-bytes SHA、resolved input path+SHA。controller 对 echo 与自己保存的 bytes 逐项 exact。

### 2.3 Pair slot、deadline 与 publication

manifest `case_count` exact3；controller对`N=repeats>=3`派生`pair_count=case_count*N=3N`、`lane_count=2*pair_count=6N`，禁止从目录反推。Step8 ordinary/#126传N=3并锁9pair/18child，Step9传N=6并锁18pair/36child。

controller root、`pair_count` slots及nonce-bound basename exact：

~~~text
<run-root>/real-differential-<controller-pid>-<controller_run_nonce>/
  slot-000-<case>-r<repeat>/oracle/{.oracle-result-<oracle_nonce>.tmp,sta/,oracle-result.json}
  slot-000-<case>-r<repeat>/reference/{.reference-result-<reference_nonce>.tmp,sta/,reference-result.json}
  {.real-differential-controller-<controller_run_nonce>.tmp,real-differential-controller-result.json}
~~~

`controller-pid==os.getpid()`；controller生成32hex nonce，`os.mkdir(root,0700)`须exclusive（EEXIST即fail、不换nonce），以`O_DIRECTORY|O_NOFOLLOW`持root dirfd并fchmod/assert0700；ordinal按case order×repeat升序覆盖`[0,pair_count)`，basename用`slot-{ordinal:03d}-<case>-r<repeat>`，每个slot/lane exclusive mkdirat并持dirfd/fchmod/assert0700。root+`pair_count`slot+`lane_count`lane dirfd贯穿launch/validation、N=3可选matrix、publication/rollback；layout完成、success、rollback及最终close前都按exact lane→slot→root集合fsync，唯一reverse-order`finally`close，任何漏项/提前close/reopen fail。

controller nonce singleton与`lane_count` lane nonce set严格disjoint，nonce cardinality exact`lane_count`。temp由writer `openat(O_CREAT|O_EXCL|O_NOFOLLOW,0600)`、fchmod/assert0600、写完fsync；controller从既有lane dirfd对nonce basename只做一次 `openat(O_RDONLY|O_NOFOLLOW)`，在同一fd上fstat→strict duplicate/trailing decode→fstat，锁regular/current uid/mode0600/nlink1及不变 `(dev,ino,size)`，保存dev+ino并禁止Path reopen；fixed final虽不含nonce，须由该inode及validated payload `run_nonce`绑定。两lane只共享verified read-only inputs/executables。

每个probe在自己的`--run-dir`下生成`sta/`；它是producer-owned opaque scratch，不是measurement artifact、lane final或consumer authority。child成功且尚未publication时，每个lane inventory必须exact `{nonce-bound temp,sta}`。`sta` root须经lane dirfd no-follow检查为同filesystem、current uid的真实目录，permission mode只允许exact `{0700,0755}`：正式`umask 077`运行产生0700，既有默认本地运行可产生0755；任何其他mode都在首次删除前拒绝，不得泛化成任意owner-accessible mode。

`commit_validated_run`是全lane scratch preflight/removal、pair hardlink、reload/revalidate、summary write/link、global rollback与错误聚合的唯一transaction owner。它先对全部lane完成Phase A零变更预检：重绑temp inode、锁lane metadata/inventory及`sta` root identity；任一lane malformed时所有`sta/`保持原样且hardlink调用0。全量预检通过后才进入Phase B：逐lane复验已保存identity，要求`shutil.rmtree.avoids_symlink_attacks`为true，以exact `shutil.rmtree("sta",dir_fd=lane_fd)`删除opaque tree，随后`fsync(lane_fd)`并验证inventory exact只剩temp。后代symlink只解除自身，禁止跟随到lane外。36个scratch全部删除且全部temp再次重绑后，才允许首次hardlink。

publication phase hook exact顺序为`validate_two_temps→remove_probe_sta→probe_sta_removed→link_oracle→link_reference→unlink_temps→validate_lane_inventory→validate_two_finals→reload→revalidate→summary_last→summary-write→summary-link→complete`。`validate_lane_inventory`要求每个成功lane exact只含其final JSON；summary仍last。`sta/`删除、lane fsync或删除后inventory验证任一步失败都发生在首次hardlink前：不发布final/summary，保留该run root作失败审计并隔离，禁止把部分scratch清理后的run重试或消费。成功run也不得残留`sta/`、temp或extra entry。

每 pair 在第一次 `Popen` 前取一个 monotonic deadline。两个 `Popen` 尽快连续启动后共同 drain stdout/stderr；result `process_id` 必须是 exact non-bool integer 且等于该对象 `Popen.pid`，pair PID 必须不同。禁止按 case/repeat 推断 PID 唯一。

launch、timeout、schema、exit、pipe、temp 或任意 pair validation 失败时，对已启动且存活的两进程执行同一 cleanup：

1. `terminate()` 全部 live child；
2. 在共同 deadline/短 bounded cleanup deadline 内 drain pipes 并 wait；
3. 对仍 live child `kill()`；
4. 再 bounded `communicate()/wait()`，drain EOF 并 reap 两个 child；
5. cleanup 失败也保留原因并使 controller nonzero。

不能串行launch/只杀失败lane。`pair_count` pair two-temp/cross-lane/repeat、7参positive summary及仅N=3 flag可选matrix全绿后，ordinary 3-repeat、Step9 6-repeat与#126 matrix-success各唯一exact1调用高层`commit_validated_run`；它是pair hardlink→reload/revalidate→summary write/same-fd validate/link→global rollback循环与错误聚合唯一transaction owner，低层link/unlink/fsync/writer仅leaf且不得复制编排。lane用持有dirfd的`os.link(...,src_dir_fd=...,dst_dir_fd=...,follow_symlinks=False)`no-clobber，link前fstat/后lstat dev+ino exact保存值。summary writer以`O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW`,0600创建并保留fd，writer wrapper禁提前close（`os.write`或`closefd=False`等价），write→fsync→`lseek(0)`后同fd fstat→strict duplicate/trailing decode→`validate_controller_summary(summary,bundle,repeats,controller_pid,controller_nonce,(oracle_exe,reference_exe),contexts)`→fstat，锁mode0600/current uid/nlink1并保存不变`(dev,ino,size,mode,uid,nlink)`，禁止Path reopen；hardlink前再fstat、后lstat同inode，swap/symlink/reopen fail。首次hardlink后任意later pair/reload/revalidate/summary write/validate/link/check失败均best-effort两轮删除本run全部lane finals及summary temp/final，再fsync root+`pair_count`slots+`lane_count`lanes，聚合原始及所有unlink/fsync/close错误；summary-last hardlink/no-clobber，失败保留root。

## 3. Extended native fixture 与 deterministic transform

### 3.1 Full setup 与 branch separation

两lane复用exact option parser、analysis context `{slow,25,__no_rc_corner__}` 和 `IncrementalStaSession({cpu,full,error})`。parse/full须得 `full_update`、无fallback、CPU/full observation None、nonzero token、nonempty nodes/arcs/endpoints/order，并按case验证chain/diamond clock exact1、extended exact2。

extended fixture 只含 supported combinational cells、ideal clocks、no SPEF。其 branch 固定分离：

- `session.initialize()` 完成parse/link并wrap Database，session为 `kInitialized`，尚未运行production GraphBuilder；此时descriptor对应bound graph Arc count exact 0。
- 两lane都由existing friend `StaCsrSessionProbeAccess` 调private `acquireUse(StaOwner::session(token),...,StaSessionState::kInitialized)` 持guard；extended唯一解析 `DISABLE_X1` existing `TimingCellArc`，只把该member disabled false→true，chain/diamond no-op。
- pre-full receipt exact keys `phase,state,guard_owner,token_nonzero,descriptor,library_match_count,library_size_before,library_size_after,member_address_stable,disabled_before,disabled_after,bound_graph_arc_count`；值锁 `pre_full,kInitialized,session,true,...,1,N,N,true,false,true,0`。
- 随后才调用一次真实 `runFullBaseline`；production GraphBuilder自然创建唯一bound graph Arc并继承disabled=true，同时一次性计算level/order。test-only transform与rerun helper不得direct调用GraphBuilder。
- full后disabled source无clock/input-delay/startpoint seed或finite timing candidate，data-slew/path maps exact empty、required `+inf`；disabled Arc exact四witness为`graph_delay_typed_empty=true,input_output_delay_initialized=true,timing_arc_delay_initialized=true,timing_arc_fallback_initialized=true`，fallback nonempty且为timing-arc delay-map subset；不要求source脱离结构root closure。
- parallel anchor source的outgoing在clone前exact仅该anchor且anchor为row tail；clone后用独立test-only active-graph FIFO replay从Arc flags/adjacency重算levels/order，禁止读取saved level/order作输入。
- parallel anchor 与 near-tie 位于其他 active reachable branch；secondary-root/tag branch 又与 near-tie scalar join 分离。

任一 phase/guard/receipt/seed/initialization/row-tail/branch witness 不成立即 hard fail，不能靠清值或重排修补。

### 3.2 Transform exact mutation

scenario分为已冻结的pre-full library disable和post-full parallel-only transform；oracle/reference调用顺序同构。full后、任何 raw/identity/oracle/export 前仅执行：

1. 唯一解析full产生的disabled graph cell Arc，验证其bound member就是pre-full receipt对象且member/graph两flag true；不再写disabled flag。
2. 验证library vector size/member address仍与pre-full receipt一致；不新增、复制、erase、reserve、relocate library member，不disable net Arc。
3. 在不同 cell/instance唯一解析active parallel anchor，要求graph/member active、不同于disabled member，source outgoing exact 1且anchor为row tail。
4. 仅把该graph Arc按值复制一次，保留同一 `TimingCellArc*`；append `Database::arc_list`，再把新rank各append一次到source outgoing和sink incoming。
5. original/copy都active、base相同、active ordinal0/1；运行FIFO replay并将其canonical levels/order bytes与production GraphBuilder保存的 `TimingPoint.level`+`database_timing_order` byte-exact比较；不复制library member或混入disabled Arc。

禁止detached `TimingCellArc`、disabled net、parallel-disabled、复制两次或重排已有row/order。loop-disabled只来自本次production full的真实loop GraphBuilder结果。

pre-full disable改变library raw/fingerprint，post-full clone改变graph raw/topology fingerprint；两lane完成相同两phase后才取pre-poison raw/oracle/source identity，不与input-only pretransform值比较。reference链内四raw/六hash exact，post-canary也不变。

### 3.3 Machine witness 与 near-tie

每 child 输出 semantic receipt；controller 不比较地址值，只比较 descriptor、canonical keys、counts、flags、ordinals、adjacency ranks和“同 member/不同 member”关系。exact witnesses：

- disabled：pre-full receipt exact；post-full library/graph/use count1/1/1、同member、两flag true、非net/parallel；source无seed/candidate、data-slew/path empty、required`+inf`；Arc exact`graph_delay_typed_empty=true,input_output_delay_initialized=true,timing_arc_delay_initialized=true,timing_arc_fallback_initialized=true`，fallback nonempty且为timing-arc delay-map subset。
- level/order：FIFO replay不读native saved值，receipt含native/replay canonical bytes+SHA且exact；snapshot/backend/scatter/rerun node level/order再与该fresh oracle exact。
- parallel：descriptor分离；pre outgoing exact `[anchor]`/row-tail，post `[ordinal0,ordinal1]`；base equal、active2/disabled0、同member，两adjacency各新增1；replay证明append未改变level/order。
- non-unate：独立 anchor sense exact non-unate，输入 rise/fall 对应输出 lane 都 present。
- loop-disabled：非上述两 anchor，count 至少 manifest minimum；active subgraph DAG。
- disabled Arc state：相关poison fields确被改写；immediate scatter完整record恢复fresh oracle；rerun不覆盖该Arc且record保持scatter值，最终full wire仍等oracle。
- multi-root/tag：两个 data root exact；两 clock tag exact、有各自 path witness。
- near-tie：同一 data root/`clock_tag` 分叉重汇合；两个候选的 analysis/path_source/transition/tag exact相同。

controller 从实际 timing wire 和 exact incoming row 重算 near-tie：对每个候选取 predecessor/source path arrival，加该 Arc 对相同 analysis/transition 选择出的 delay，得到 candidate；验证 `1e-9 < abs(c0-c1) < 1e-6`。它据实际数值/analysis direction 重算 strict scalar winner、按实际 row order 重算 epsilon path winner，并核对 scalar/path predecessor NodeKey+ArcKey；不信 manifest 的数值或赢家。

`secondary_root` 只产生 `secondary_clock_tag` 的独立 path；controller 以 reachability和join incoming candidates证明它不进入 near-tie join、不参与上述 scalar 竞争。两个 tag 不得冒充 sequential launch/CRPR coverage。

### 3.4 Coverage report

native-backed exact：

~~~text
chain, diamond, non_unate, parallel, disabled, loop_disabled,
multi_root, clock_tag, near_tie, post_scatter_rerun
~~~

synthetic-only typed reject 只引用既有 Step 4/5 tests，不在本 fixture 伪造：

~~~text
parasitic_net, sequential_instance, sequential_launch, timing_check,
crpr, propagated_clock, clock_tree_fanout, clock_gating_or_divider,
conditional_timing_arc, case_analysis
~~~

native fatal/out-of-model 为 `clock_tree_overlap,multi_driver`；not-claimed 为 `sequential_native_parity,crpr_native_parity,mutation,generation_gt_zero,cuda,dual_csr,speedup`。native-backed witness 缺失必须 CTest fail，不能自动降为 synthetic-only。

## 4. Lane phase、poison 与 native rerun

### 4.1 Existing-graph native API/RAII

test-only `runNativeExistingGraphTiming(Database&)` 固定：

1. `ScopedDelayRun` 构造调用 `DelayCalculator::getInst().init()`，析构无异常调用 `destroy()`；
2. `ScopedNativeSingleton<ClockPropagator>` 调 `initInst()`，`getInst().propagate()`，析构 `destroyInst()`；
3. 同型 scope 调 `TimingPropagator::initInst/getInst().propagate/destroyInst`；
4. 同型 scope 调 `TimingAnalyzer::initInst/getInst().analyze/destroyInst`。

scope逆序cleanup；任一stage失败仍析构且child nonzero。helper接受既有Database，禁止GraphBuilder/topology rebuild/level-order mutation/Power/Reporter/SDF；仅此rerun helper与post-full transform direct `GraphBuilder` occurrence 0，production `runFullBaseline`仍exact一次。parallel transform后调用一次、post-canary再一次。

### 4.2 Oracle lane

guarded Database callback exact：

probe outer phase exact `initialize→pre-full guarded disable/no-op→release guard→runFullBaseline→post-full guarded callback`，两lane同构。callback内：
1. verify disabled inheritance；parallel transform/no-op；FIFO replay receipt；
2. `runNativeExistingGraphTiming`；
3. 调 opaque `readAndEncodeNativeTiming(database)`；
4. callback 返回、session close exact once、写 oracle temp。

`StaCsrRealOracleProbe.cpp` 只 include `CsrRealDifferentialOracleEncoding.hpp` 并调用 opaque function；只有 `CsrRealDifferentialOracleEncoding.cpp` include `CsrNativeTimingOracleTestSupport.hpp`、调用 `readNativeTimingOracle` 并立即转 neutral wire。oracle TU 不得出现 snapshot/reference/backend/scatter/poison/readback API。oracle output 不含 candidate/raw/reference identity/token/backend/scatter 数据。

### 4.3 Reference lane exact orde

guarded Database callback：

1. outer phase同§4.2；callback先verify disabled inheritance、parallel transform/no-op、FIFO replay，再 `runNativeExistingGraphTiming`；
2. independent raw projector 编码 `pre_poison_raw_wire` 与 SHA；此时 candidate encoder 调用数必须 0；
3. poison exact 17 family；重投 raw，byte/SHA exact；
4. 第一次且唯一一次 `buildCsrSessionSnapshot(database,context,token)`；
5. 仅在首次 build 成功且 snapshot/input strict-valid 后，由唯一 call owner `CsrRealDifferentialReferenceEncoding.cpp` 调 `canonicalIndependentReferenceInputBytes(snapshot.input)`，输出 actual candidate wire+SHA；
6. 要求 decoded identity 使用该进程 actual nonzero token、generation 0、unsupported empty；
7. `computeCsrSessionReference(*snapshot)`，先从 detached result 编码 `reference_timing`；
8. `scatterCsrSessionTimingResult` success，验证 writes、current六hash、无 rejection/invalidation；
9. direct Database readback 编码 `scattered_timing`，保存 `observation.ready_post_scatter` 与 raw/fingerprint；
10. 注入 `4.5` guaranteed-overwrite canary，编码 `canary_timing` 并再取 raw/六hash；
11. `runNativeExistingGraphTiming`，direct readback `rerun_timing`，再取 raw/六hash；
12. release snapshot，保存 `observation.released`；callback 返回、session close once、写 reference temp。

`buildCsrSessionSnapshot` 前上述 call exact 0；production `canonicalReferenceInputBytes`（domain `ista-csr-canonical/reference-input/1.0.0` 且排除 `source_identity`）禁止使用。必须复用既有 `CsrReferenceInputIndependentEncoding.cpp`、`CsrReferenceInputIndependentGraphEncoding.cpp`、`CsrReferenceInputIndependentModelEncoding.cpp` 三 TU，产生含 actual identity 的 `ista-csr-reference-input-test-wire/1.0.0`，与现有 decoder exact 配对；禁止复制实现或 prebuild 调用。build 前也禁止 backend/native readback；unsupported reason 非空时 hard fail，compute/scatter/readback 调用数 0；本步不输出 unsupported 数值。

### 4.4 Poison 与 forbidden chain

poison token exact 17、顺序固定：

~~~text
timing_point_level
timing_point_is_clock_point
timing_point_scalars
timing_point_clock_arrival_maps
timing_point_clock_slew_maps
timing_point_clock_predecessor_maps
timing_point_clock_predecessor_arc_delay_maps
timing_point_clock_predecessor_transition_maps
timing_point_data_slew_map
timing_point_path_state_map
arc_scalars
arc_transition_maps
arc_input_output_delay_map
arc_graph_delay_map
arc_timing_arc_delay_map
arc_timing_arc_fallback_provenance
database_timing_orde
~~~

每项 `before_sha256 != after_sha256`，family 漏/多/乱序/empty canary 均失败。independent raw wire 覆盖 graph flags/ranks、instance/net、constraint/check、referenced Liberty closure、parasitic，排除 derived timing。

`forbidden_projection` exact keys `pre_poison,post_poison,post_scatter,post_canary,post_rerun,projection_call_receipt`；每checkpoint exact `{raw_wire_hex,raw_sha256}`且必须是该phase新投影的actual bytes。receipt为五个exact `{checkpoint,call_ordinal}`，顺序如上、ordinal 0..4、各project+encode call count1。
controller逐份验SHA/strict decode；`source_wires.pre_poison_*`须byte-exact等于首checkpoint。main四点为pre/post-poison/post-scatter/post-rerun，canary为第五点，五份bytes/SHA exact相同；只复制先前wire/hash、漏call或错序均fail。
六content hash provenance按§5.3逐checkpoint重算，generation始终0。

### 4.5 Guaranteed-overwrite derived canary

保存 immediate `scattered_timing` 后才注入 canary。runtime 先按 semantic key 选择每个 native stage 在该 fixture 中必写且当前 present 的 derived field：

- DelayCalculator：仅active reachable bound cell Arc的scalar/transition/graph/timing-arc delay及fallback provenance；
- ClockPropagator：具名 clock point 的 `is_clock_point`、effective/physical clock arrival/slew/predecessor lane；
- TimingPropagator：具名 reachable data point 的 scalar arrival/launch/predecessor、data slew和path-state lane；
- TimingAnalyzer：具名 endpoint 的 required/slack lane。

禁止选择disabled/loop-disabled Arc、level、`database_timing_order`、topology、adjacency、constraint、library、parasitic或任何非必写optional field。每类至少一个active exact field，注入合法且异于oracle/scatter的值；`canary_timing`必须同时不等两者。

canary receipt证明active/reachable/present、before/after不同、stage owner、post-rerun overwritten；raw/六hash不变。disabled Arc严禁选中，rerun后其record须等immediate scatter；最终完整wire等fresh oracle。

## 5. Wire、schema、comparison 与 repeat

### 5.1 Probe root 与 source wire

probe schema 为 `ista-csr-real-differential-probe/1.0.0`，递归拒 extra key。oracle root exact：

~~~text
schema, lane, case, top, expected_clocks, repeat_index,
run_nonce, input_case_sha256, process_id, argv_receipt,
scenario, timing, complete
~~~

reference root exact：

~~~text
schema, lane, case, top, expected_clocks, repeat_index,
run_nonce, input_case_sha256, process_id, argv_receipt,
scenario, source_wires, identity, poison, forbidden_projection,
coverage, scatter, observation, reference_timing, scattered_timing,
canary_timing, rerun_timing, complete
~~~

`source_wires` exact keys：

~~~text
pre_poison_raw_wire_hex, pre_poison_raw_sha256,
snapshot_candidate_wire_hex, snapshot_candidate_sha256
~~~

child对两份bytes自算SHA；controller重算并strict decode，且pre-poison source wire等于forbidden首checkpoint。candidate必须是首次successful build的actual `snapshot.input`，不得pre-export/重建。

### 5.2 Neutral timing wire

`NeutralWire` root exact `timing_order,out_rows,in_rows,nodes,arcs`。rows 按真实 graph adjacency 保存 ArcKey，不能按 key resort 后伪造 rank；nodes/arcs 分别按 canonical NodeKey/ArcKey bytes排序。

NodeKey exact `kind,full_name,instance_name,pin_name`；ArcKey exact `source,sink,kind,owner_name,library_source_port,library_sink_port,ordered_library_arc_semantic_signature,parallel_ordinal`。records 覆盖 level/clock flag、scalar arrival/required/slack/launch、optional clock/predecessor、effective/physical clock lanes、data slew、ragged path state，以及 Arc scalar/transition/input-output/graph/timing-arc delay、transition和fallback provenance。

optional 显式 null；finite 编码 `{kind:"finite",value,negative_zero}`，±infinity用 `pos_inf/neg_inf`，NaN非法。bool不能作number。wire contract test固定 empty/rich/near-tie/parallel/disabled/canary known-answer与duplicate/extra/trailing/NaN negative cases。

### 5.3 Fingerprint recomputation

controller必须取 `forbidden_projection` 五个checkpoint各自actual `raw_wire_hex/raw_sha256` 与同一actual snapshot candidate；逐份验SHA/decode后依次调用既有：

~~~text
reference_input_raw_wire.decode_raw_wire
reference_input_candidate_wire.decode_candidate_wire  # encode_full_candidate_wire仅供selftest mutation/KAT
reference_input_recompute_graph.recompute_graph
reference_input_recompute_model.recompute_model  # internally transfer exact 1
reference_input_recompute_fingerprint.recompute_identity
~~~

它从 decoded candidate 取得 actual token 和 generation，不注入 controller token；要求 token nonzero、generation exact 0。重算六hash exact：

~~~text
topology_fingerprint
clock_constraint_fingerprint
library_fingerprint
corner_fingerprint
parasitic_fingerprint
timing_input_fingerprint
~~~

六hash来源冻结，不允许production re-export或沿用旧wire/hash：

- snapshot：同一decoded candidate分别与actual pre-poison、actual post-poison raw完整跑exact `raw→graph→model(内部transfer exact1)→fingerprint`；两结果须等candidate source/root identity。
- scatter-current：只取scatter attempt的actual `current_fingerprints`，并与snapshot六hashexact；不得用controller checkpoint值冒充。
- post-scatter/post-canary/post-rerun：各自actual raw与同一decoded candidate完整重跑同一exact pipeline，逐项等snapshot六hash；post-scatter还等ready/released observation identity。
- contract对`reference_input_recompute_transfer` direct import/call exact0；Workflow读取`reference_input_recompute_model.py` source锁其为transfer唯一owner、import exact1、每次model调用内部transfer exact1且order `raw→graph→model(内部transfer exact1)→fingerprint`。任一decoder/recompute rejection、receipt错序/call-count或hash provenance不符都终止pair。

### 5.4 Cross-process correctness 与 repeats

fresh oracle 对 `reference_timing`、`scattered_timing`、`rerun_timing` 比较；backend 对 immediate scatter也比较。key、row、order、level、ordinal、enum、bool、presence、predecessor exact；finite double满足：

~~~text
abs(a-b) <= absolute + relative * max(abs(a),abs(b))
~~~

±infinity符号、signed-zero signbit exact；tolerance 不适用于结构或 integer。`canary_timing` 必须明确不等三份正确 wire。

跨 repeat 稳定性只比较同 case 的上述六个 content hash；不比较整个 candidate bytes/raw bytes、token、PID、nonce、capacity、timing或整份 wire。within-repeat 的 raw/fingerprint/cross-lane correctness仍全验。三个 case topology hash两两不同；chain/diamond的 baseline `input_case_sha256` 保持原值。

controller `--repeats` 接受任意 `>=3`。Step 8 CTest 用 3，全部 correctness repeats；Step 9 用 6，repeat 0标记 warmup、1–5 measured。summary保留每次原始 `export/reference/scatter` timing、host logical/capacity和role，不用 timing golden、跨repeat equality或性能阈值判 correctness。

### 5.5 Observation exact schema

`observation` exact keys `ready_post_scatter,released`；两者都含：

~~~text
schema_version, state, identity, counts, buffers, capacity,
support, timing_ms, host_bytes, last_rejection, last_invalidation
~~~

- identity exact九键：`fingerprint_schema_version,session_token,graph_generation` 加六hash；token等actual，generation 0。
- counts exact `nodes,arcs,levels`，全positive且levels<=nodes。
- buffers exact九键：`node_keys,arc_keys,out_row_offsets,out_arc_ids,in_row_offsets,in_arc_ids,level_offsets,level_nodes,node_to_level`；每项 exact `logical_size,capacity`，logical按CSR公式、capacity>=logical。
- capacity exact `last_action,event_count`，值 `initial_allocate,1`。
- support exact `reference_supported,unsupported_reasons`，值 `true,[]`。
- timing_ms exact `export,reference,scatter`；ready时三者 finite/nonnegative且non-null。
- host_bytes exact `logical,capacity`，positive且logical<=capacity。
- `last_rejection,last_invalidation` 都 null。

`ready_post_scatter.state=="ready"`；`released` 除 `state=="released"` 外，identity/counts/buffers/capacity/support/timing_ms/host_bytes/events必须 byte-for-byte相同。timing/host 仅为原始观测，不是 correctness golden。

## 6. 文件、target 与 CTest inventory

### 6.1 新增文件

目录 `src/operation/iSTA/test/real_differential/` 新增 C++：

~~~text
CsrRealDifferentialWire.hpp
CsrRealDifferentialWire.cpp
CsrRealDifferentialProbeSupport.hpp
CsrRealDifferentialProbeSupport.cpp
CsrRealDifferentialScenario.hpp
CsrRealDifferentialScenario.cpp
CsrRealDifferentialOracleEncoding.hpp
CsrRealDifferentialOracleEncoding.cpp
StaCsrRealOracleProbe.cpp
CsrRealDifferentialReferenceEncoding.hpp
CsrRealDifferentialReferenceEncoding.cpp
CsrRealDifferentialNativeReadback.hpp
CsrRealDifferentialNativeReadback.cpp
CsrRealDifferentialNativeNodeReadback.cpp
CsrRealDifferentialNativeArcReadback.cpp
StaCsrRealReferenceProbe.cpp
CsrRealDifferentialWireContractTest.cpp
~~~

同目录新增：

~~~text
real_differential_model.py
real_differential_wire_contract.py
real_differential_contract.py
real_differential_controller.py
real_differential_controller_selftest.py
schema/real_differential_probe_v1.schema.json
schema/real_differential_controller_v1.schema.json
manifest.json
fixtures/supported_branches_cells.lef
fixtures/supported_branches.lib
fixtures/supported_branches.v
fixtures/supported_branches.sdc
CsrRealDifferentialTests.cmake
CheckCsrStep8SourceInventory.cmake
CheckCsrStep8Targets.cmake
CheckCsrStep8Isolation.cmake
CheckCsrStep8Workflow.cmake
~~~

umbrella只顺序include Targets/Isolation/Workflow。Python只用stdlib并受控复用loader/full codec/recompute；别名`wire=real_differential_wire_contract`，DAG中的`model=real_differential_model,reference model=reference_input_model`；exact DAG为`model→baseline loader; wire→stdlib+model+baseline_contract; contract→wire+reference codec/recompute; controller→contract+selftest; selftest→contract+model+wire+candidate codec+reference model(enum-only)`。selftest先经model bootstrap后，只允许显式direct import/call `decode_candidate_wire,encode_full_candidate_wire`及exact `from reference_input_model import UnsupportedReason`，对reference model其他symbol/module access exact0；该model保持既有未修改依赖，不入exact七修改/Ruff文件。contract保留normal decoder调用，controller/model/wire direct codec调用0；全部Step8模块对`reference_input_wire_fixture.encode_candidate_wire`的import/call exact0。argparse把`--self-test`与`--public-negative-self-test`置于mutually-exclusive group；前者lazy→`run_self_test(api)`，后者的mutual-exclusion/`repeats==3`约束在layout/Popen前但不import；#126完成9pair+positive 7参summary后、commit前才lazy import/call`run_public_negative_matrix(...)`；default/normal/Step9 import/call0，同时flags或public flag repeats drift必须launch0。selftest对controller static/dynamic/importlib/`__import__`/`sys.modules` lookup及runtime反查0。
两类bootstrap owner严格分离：`model._bootstrap_sibling_paths`是sibling path唯一owner，exact `_TEST_ROOT=Path(__file__).resolve().parent.parent`、`_BASELINE_ROOT=_TEST_ROOT/"baseline"`、`_REFERENCE_ROOT=_TEST_ROOT/"reference_input"`，须canonical existing directory并按BASELINE后REFERENCE各`sys.path.insert(0,...)`一次（最终prefix REFERENCE,BASELINE）；无PROJECTION/其他root，wire先model再baseline_contract、contract先wire再reference recompute且自身path mutation0。controller `_load_selftest_runner`是selftest dynamic-import唯一owner/唯一literal`importlib.import_module("real_differential_controller_selftest")`call-site；拒`__import__/exec/eval`、nonliteral/其他owner。`run_self_test(api)`只收frozen/read-only exact5-field`SelfTestApi={manifest_path,baseline_manifest_path,spawn_and_drain,prepare_layout,commit_validated_run}`；selftest以phase hook直接poison真实commit入口，禁止复制transaction/rollback loop，低层leaf不入api。public matrix只收真实records、immutable validation contexts/canonical bytes、slots及read-only completed-handle tuple，不收launch/publish/write/rollback/fsync callback或whole module。
`wire`唯一owner且contract re-export`DifferentialContractError`，只承载stdlib strict schema recursion及NeutralWire/NodeKey/ArcKey/scenario基础validation/normalization；contract保留argv/raw→candidate/extended/canary/cross-lane/repeat/summary/public entrypoint，禁复制。公开exact test API`parse_strict_json_for_test(bytes)`、`validate_schema_for_test(schema,instance,exact_store)`递归审全部nested位置及未引用`$defs`；shape/position表冻结：`$schema`仅root且为exact Draft2020-12 URI string，`$id`仅root且为exact-store nonempty id string，`title` string；`$defs/properties`为string-key object-of-schema且子键是数据名；`$ref`为exact-store id/fragment string；`type`为recognized `{null,boolean,integer,number,string,array,object}` string或nonempty unique recognized list；`required`为unique string list；`oneOf/prefixItems`为nonempty schema list；`items/additionalProperties`只允exact bool或schema；`pattern`为可编译string；`minimum/maximum`为finite nonbool number且共存时min<=max；`minItems/maxItems`为nonbool nonnegative int且共存时min<=max；`const`为strict JSON value，`enum`为nonempty type-sensitive unique strict JSON values；array/object/string/number assertions只在compatible position。`$ref`/`oneOf`与siblings合取；每keyword/shape/position及组合accept/reject KAT。unknown/future keyword、foreign/missing/cyclic ref、非法Pointer escape或store/fragment drift统一唯一error；helper/contract各<700，controller/selftest各<550。

### 6.2 修改既有文件

child exact窄改：

- `test/CMakeLists.txt`：在 Step 7 tests 后 include `CsrRealDifferentialTests.cmake`。
- `CheckCsrReferenceInputIsolation.cmake`：global raw allow-list仅加 reference target 的 probe、poison与四 RawProjector objects；Step 4 exact 9 targets/71 objects不变。
- `CheckCsrStep6SourceInventory.cmake`：按 `7.2` 精确迁移且最终 <700。
- `CheckCsrStep7Targets.cmake`：按 `6.5` 迁移 Step 8 count/name detector；Step 7 自身定义不变。
- `reference_input/reference_input_candidate_wire.py`在既有完整strict decoder旁增加全仓唯一完整inverse `encode_full_candidate_wire`：逐字段/顺序/optional/vector与C++ canonical bytes对称；既有不完整`reference_input_wire_fixture.encode_candidate_wire`保持不变且Step8调用0。round-trip固定manifest顺序`chain,diamond,supported_branches`各repeat0 reference record，以actual `snapshot_candidate_wire_hex`及匹配SHA取case-distinct bytes并逐份decode→encode_full byte-exact；`reference_input_recompute_transfer.py`仍按raw rank、owner ports、ordered library signature在unique cell closure唯一match，same-member复用允许，所有missing/ambiguous/drift hard fail。
- `CsrRealDifferentialTests.cmake` reference source property exact加入既有三encoder TU；controller_validation与fresh_process两个Python CTest command dependencies均exact七路径`model,wire_contract,contract,controller,selftest,reference_input_candidate_wire.py,reference_input_recompute_transfer.py`，fresh argv exact含`--public-negative-self-test`；`.github/actions/build-wheel/action.yml` build三target/核same sources且各运行unit/property/smoke一次，拒`__pycache__`。

本实现不改其他文件；总计划/report回填由主流程在本计划双审/实现门完成后另行处理。

### 6.3 Exact target source/link

`ISTA_STEP8_COMMON_SOURCES` exact：

~~~text
real_differential/CsrRealDifferentialWire.cpp
real_differential/CsrRealDifferentialProbeSupport.cpp
real_differential/CsrRealDifferentialScenario.cpp
~~~

`ista_csr_real_oracle_probe` exact C++ objects来自：

~~~text
real_differential/StaCsrRealOracleProbe.cpp
real_differential/CsrRealDifferentialOracleEncoding.cpp
<COMMON>
CsrNativeTimingOracleReader.cpp
CsrNativeTimingOracleNodeReader.cpp
CsrNativeTimingOracleArcReader.cpp
~~~

并列 header source `CsrNativeSemanticKeyTestSupport.hpp,CsrNativeTimingOracleTestSupport.hpp`。OracleEncoding opaque边界后唯一 oracle DTO-dependent object exact四个：

~~~text
CsrRealDifferentialOracleEncoding.cpp.o
CsrNativeTimingOracleReader.cpp.o
CsrNativeTimingOracleNodeReader.cpp.o
CsrNativeTimingOracleArcReader.cpp.o
~~~

`ista_csr_real_reference_probe` exact C++ objects来自：

~~~text
real_differential/StaCsrRealReferenceProbe.cpp
real_differential/CsrRealDifferentialReferenceEncoding.cpp
real_differential/CsrRealDifferentialNativeReadback.cpp
real_differential/CsrRealDifferentialNativeNodeReadback.cpp
real_differential/CsrRealDifferentialNativeArcReadback.cpp
<COMMON>
CsrReferenceInputIndependentEncoding.cpp
CsrReferenceInputIndependentGraphEncoding.cpp
CsrReferenceInputIndependentModelEncoding.cpp
CsrReferencePoisonSupport.cpp
CsrReferenceInputRawProjector.cpp
CsrReferenceInputRawConstraintProjector.cpp
CsrReferenceInputRawLibraryProjector.cpp
CsrReferenceInputRawParasiticProjector.cpp
~~~

实现期 inventory correction：reference cpp objects `13→16`，三 target cpp objects 总计 `23→26`，只增加复用上述三个 existing test-wire encoder objects。reference source property不得含任何 native oracle header/object。`ista_csr_real_differential_wire_contract_test` 只含 WireContractTest+Wire objects。两个 probe direct links exact `ista_timing_graph_csr_adapter,ista_timing_database_headers,ista_interface,ista_source,idm`；wire test direct link `ista_timing_graph_csr_adapter`。这不是 dependency-closure 隔离声明。

三target compile options exact `-Wall;-Wextra;-Werror;-pedantic;-ffp-contract=off`，禁 fast-math/Ofast；两个 probe 不直接注册 CTest。

### 6.4 Exact CTest

| name | command要点 | label | timeout |
|---|---|---|---:|
| `ista_csr_real_differential_wire_contract_test` | 同名exe，无参数 | `ista_unit` | 60 |
| `ista_csr_real_differential_controller_validation` | controller `--self-test` | `ista_unit` | 60 |
| `ista_csr_step8_source_inventory` | `cmake -P CheckCsrStep8SourceInventory.cmake` | `ista_unit` | 120 |
| `ista_csr_real_differential_fresh_process` | controller+两target+两manifest+run-root+repeats3+timeout120+exact `--public-negative-self-test` | `ista_smoke` | 2400 |

Step 8 exact增量为 3 unit、0 property、1 smoke；Step 7 baseline `84/20/6` 后配置总数 exact `87/20/7`。所有Python CTest environment exact `PYTHONDONTWRITEBYTECODE=1`。

### 6.5 Step 7 target gate迁移

计数owner单一：全局 `87/20/7` 与加法等式只由新 `CheckCsrStep8Targets.cmake` 断言；`CheckCsrStep7Targets.cmake` 不重复拥有post-Step8总数，只保护pre-Step8 baseline和Step7 inventory。

`CheckCsrStep7Targets.cmake` 保留Step7 exact 6unit+1smoke及 `STEP7_BASELINE=84/20/6`；只新增exact `STEP8_EXPECTED` 三unit+一smoke exclusion set：

- 从current CTest JSON识别并移除Step8四项，证明剩余pre-Step8 catalog仍为 `84/20/6`；
- safe fixture含 frozen Step 7 set+exact Step 8 increment必须 pass；
- poison fixture对Step7或Step8 exclusion任一missing/extra/mislabel、或还原baseline漂移必须fixed diagnostic+exit1；
- Step 7 既有6unit+1smoke的定义、排序与单独计数断言 byte语义不变。

`CheckCsrStep8Targets.cmake` hard-code `STEP8_INCREMENT=3/0/1`、exact Step8 set、当前总数 `87/20/7` 及 `84/20/6+3/0/1`；expected不从actual反推。session/process reviewer须明确裁决两gate owner分离无重复/矛盾。

## 7. Gate、negative matrix 与行数上限

### 7.1 Source/object/depfile/runtime evidence

`CheckCsrStep8Targets.cmake` hard-code target source property、cpp object count/owner、direct links/options/includes、CTest与global counts；expected不能从actual生成。fresh Ninja build 后保存并校验：

- `compile_commands.json` 的 source→object command；
- `ninja -t deps`/depfile 的 object→header closure；
- object path、source path、depfile path全为canonical build/source路径；
- SourceInventory hard-codeexact七修改Python路径、含selftest→reference model enum-only edge的DAG、两bootstrap/error/API bundle、candidate codec与transfer窄改owner。gate分工唯一：Targets锁七dependency与两Python CTest exact command（fresh必须含public flag）；Isolation只静态锁AST DAG/bootstrap/error/lazy import及local/CI Ruff exact executable/cwd/version/七argv/action bytes与safe/poison，并锁`UnsupportedReason`唯一direct enum import/无其他reference-model access；真实exit唯一归local acceptance/wheel action。Workflow锁same-fd/transaction/matrix、exact pipeline，并读取candidate codec/model/transfer source锁`encode_full_candidate_wire`全仓唯一definition、Step8对fixture encoder import/call0、manifest顺序三case-distinct repeat0 actual round-trip及transfer唯一owner/signature/reuse/failures，且只核其七source集合与Isolation Ruff集合一致。Workflow优先保持<700；超出只报告actual与具体维护性理由，不得仅按行数失败。safe/poison拒任一missing/extra/path替换、反向边、额外root/path owner、whole module、expected/read/ruff集合非exact七或彼此不一致；
- oracle main仅undefined-ref opaque encoder；OracleEncoding才ref native reader；所有 oracle新增object无reference API direct ref；
- reference objects/header depfile无 `CsrNativeTimingOracle*`，无native oracle reader/materializer；
- neutral Wire object无 Database/oracle/backend/scatter/snapshot；
- Targets锁 reference exact 三 independent encoder source/object、reference 16及三target 26 cpp objects；Isolation锁 `CsrRealDifferentialReferenceEncoding.cpp.o` 为 `canonicalIndependentReferenceInputBytes` 唯一 call-site owner且无 Database/readback、三 encoder object/depfile与 test-wire domain exact、production encoder/domain source/ref及复制实现 exact 0；readback无 backend/result encoder；
- runtime receipt的 executable realpath等 `Popen.args[0]`，child argv/cwd/run-dir/temp realpath与controller预期exact。

不得用 binary-level “不存在backend符号”替代这些证据。

### 7.2 Chained allow-list exact migration

Step 6 semantic-helper reverse allow-list `14→15`，唯一新增：

~~~text
ista_csr_real_oracle_probe/CsrNativeTimingOracleReader.cpp.o
~~~

oracle DTO reverse allow-list只新增 `6.3` 四个 oracle objects；OracleProbe/Scenario/Wire及整个reference target命中即fail。`CheckCsrStep6SourceInventory.cmake` 机械压行后仍严格 <700，safe/poison证明第五个object或reference object命中会失败。

Step 4 raw allow-list仍只新增 reference target exact六object：`StaCsrRealReferenceProbe.cpp.o`、`CsrReferencePoisonSupport.cpp.o`、四个 `CsrReferenceInputRaw*Projector.cpp.o`；三个 independent candidate encoder objects不得进入 raw DTO allow-list，Step 4 exact 9 targets/71 objects不变。任何额外 Step 8 object依赖 raw DTO fail。

Step 7 workflow的五个 SHA 使用 `1.3` 常量；projection/session target、friend/public helper allow-list和6unit+1smoke不变。

### 7.3 Workflow gate

`CheckCsrStep8Workflow.cmake` 锁：

- reference exact phase occurrence/order；build前 independent encoder/backend/readback call 0，首次 successful build后 encoder exact 1且 call-site owner exact ReferenceEncoding；test-wire domain与 `source_identity` exact，production domain/call/source及复制实现 exact 0；
- poison exact17；五actual raw wires+SHA与projection call receipt各phase exact一次/顺序；gate禁alias/copy旧wire/hash；scatter façade及writes算术；
- oracle main opaque call，OracleEncoding唯一 reader call；reference native-oracle call 0；
- initialized-phase disable receipt/full inheritance、post-full parallel row-tail及independent FIFO replay exact witness；
- stabilization两次、四stage/RAII；rerun helper/post-full transform direct `GraphBuilder` 0、production full exact一次；
- immediate→active-reachable-only canary→rerun顺序、disabled Arc scatter→rerun persistence；
- exact派生`pair_count=3N/lane_count=6N`、nonce/dirfd lifetime及N=3→9/18、N=6→18/36 safe+poison；O_EXCL writer/O_NOFOLLOW same-fd lane reader、saved inode、real Popen/deadline/reap；ordinary3/Step9-6/public-success `commit_validated_run`各call exact1且为transaction loop/rollback唯一owner，低层leaf不得编排。Workflow另锁publication phase子序列、`_remove_probe_sta`唯一owner/call、全lane Phase A→fd-relative symlink-safe rmtree→lane fsync→temp rebind→首次hardlink、root mode exact集合`{0700,0755}`及`sta-mode-0700|sta-mode-0755|sta-mode-invalid`，并以missing cleanup/mode KAT或publication phase poison证明任一漂移失败；summary writer完整`O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW`,0600/no-early-close并write→fsync→rewind→fstat→strict decode→7参validate→fstat及hardlink pre/post inode exact，每个flag/mode/order drift poison；publish前全pair/summary/matrix，layout/success/rollback/finally exact fsync lane→slot→root全派生集合及错误聚合；
- `1.3` hashes、descriptor domain/order/argv bytes、observation/repeat合同。
- `PUBLIC_NEGATIVE_MATRIX` hard-code exact30个 `(name,record-kind,public-entrypoint,single-mutation,diagnostic-token)`：`(duplicate_json,loader_bytes,parse_strict_json_for_test,baseline=b'{"a":1}'→b'{"a":1,"a":2}',duplicate-key);(trailing_json,loader_bytes,parse_strict_json_for_test,baseline=b'{"a":1}'→b'{"a":1}x',trailing-data);(nan_json,fresh_probe_json_bytes,parse_strict_json_for_test,first-finite-number-token→NaN,non-finite);(pos_inf_json,fresh_probe_json_bytes,parse_strict_json_for_test,first-finite-number-token→Infinity,non-finite);(neg_inf_json,fresh_probe_json_bytes,parse_strict_json_for_test,first-finite-number-token→-Infinity,non-finite);(bad_sha,reference_probe,validate_probe,source_wires.pre_poison_raw_sha256[0]^=1,bad-sha);(bad_pid,reference_probe,validate_probe,process_id+=1,bad-pid);(bad_schema,reference_probe,validate_probe,schema="invalid",bad-schema);(raw_drift,reference_probe,validate_probe,forbidden_projection.post_poison:decoded.arcs[first-active].disabled=false→true+canonical-reencode+matching-SHA,raw-provenance);(hash_drift,reference_probe,validate_probe,identity.topology_fingerprint[0]^=1,hash-drift);(unsupported,reference_probe,validate_probe,decoded-candidate.unsupported_reasons=()→(UnsupportedReason.PARASITIC_NET,)+encode_full+matching-SHA+strict-redecode,unsupported);(scatter,reference_probe,validate_probe,scatter.writes_applied+=1,scatter);(released,reference_probe,validate_probe,observation.released.state="ready",released);(stale_argv,reference_probe,validate_probe,argv_receipt.argv[0]+="/.",stale);(bad_arc_key,extended_reference_probe,validate_probe,one-ArcKey.owner_name=""-synchronized-to-all-references,ArcKey);(near_tie,extended_reference_probe,validate_probe,descriptor-unchanged+finite-wrapper-only-arrival.value=bounded-IEEE-outward-value,near-tie-actual-numeric);(prebuild,reference_probe,validate_probe,decoded-candidate.source_identity.session_token:nonzero→0+encode_full+matching-SHA+strict-redecode,prebuild);(checkpoint_copy,reference_probe,validate_probe,forbidden_projection.projection_call_receipt[1].call_ordinal=0,checkpoint-copy);(canary,reference_pair,validate_pair,canary_timing=reference_timing,canary);(tolerance_bool,reference_pair+tolerances,validate_pair,absolute=True,tolerance);(tolerance_nan,reference_pair+tolerances,validate_pair,absolute=NaN,tolerance);(tolerance_pos_inf,reference_pair+tolerances,validate_pair,absolute=+Inf,tolerance);(tolerance_neg_inf,reference_pair+tolerances,validate_pair,absolute=-Inf,tolerance);(tolerance_negative,reference_pair+tolerances,validate_pair,absolute=-1e-9,tolerance);(tolerance_signed_zero,reference_pair+tolerances,validate_pair,absolute=-0.0,tolerance);(tolerance_drift,reference_pair+tolerances,validate_pair,absolute=2e-9,tolerance);(summary_pid,controller_summary,validate_controller_summary,controller_pid+=1,summary-pid);(summary_nonce,controller_summary,validate_controller_summary,controller_run_nonce[0]^=1,summary-nonce);(summary_repeat_order,controller_summary,validate_controller_summary,swap case_results[0].repeats[0:2],summary-repeat-order);(summary_embedded_schema,controller_summary,validate_controller_summary,case_results[0].repeats[0].oracle.schema="invalid",summary-embedded-schema)`。raw canonical reencode+matching SHA、同步ArcKey或candidate完整重编码各算一个声明semantic subtree，之外字段不得变；candidate两行须以actual decoded model经`dataclasses.replace`构造，调用`encode_full_candidate_wire`并更新SHA后strict decode，baseline分别先断言空tuple/非零token，重解码结果与mutation DTO deep-exact且除声明字段外与baseline deep-exact；near先锁arrival wrapper exact `kind="finite"`/`negative_zero=false`并只改`value`；按validator同序实际double重算，以other candidate±`4*upper_exclusive`为目标反解finite value，若delta仍未strict大于upper则每方向最多4096次`math.nextafter`向外推进；任一路成功后strict JSON/schema/NeutralWire先绿再要求near token，两向均失败hard fail，禁十进制rounding，descriptor byte/deep及wrapper其余字段exact不变。首2行固定合法JSON baseline只在unit tempfile；其余28必须取fresh真实对应record，由default false且仅fresh CTest #126传入`--public-negative-self-test`执行，6-repeat/normal不传；#126 matrix绿后commit exact1并产生final summary，matrix失败commit/hardlink0，count仍`87/20/7`。
- execution分区exact首2 fixed-loader/余28 fresh；每行baseline先绿，再deep-copy且只声明目标变化并匹配token。fresh runner输入分离为immutable真实`ValidationContext` tuple+其canonical bytes与read-only completed `Popen` handle tuple；summary行必须用真实contexts exact7参`validate_controller_summary(summary,bundle,3,controller_pid,controller_nonce,(oracle_exe,reference_exe),contexts)`。matrix前冻结18 temp各`(dev,ino,uid,mode,nlink,size,sha256)`及slot/lane entry set；每行后records/contexts bytes+deep exact、handle tuple与每object identity/pid/args/returncode exact且`poll()`/`wait(timeout=0)`均返回同returncode，handles禁止deepcopy/canonical、禁`kill(pid,0)`；layout exact、final/summary absent，错accept/token/drift即nonzero且commit/hardlink0；matrix全绿后commit exact1且final summary存在。

Isolation/workflow safe+poison覆盖full candidate codec三case-distinct actual round-trip/field-order/optional/vector/domain、unique full owner、fixture encoder forbidden import/call、`UnsupportedReason` enum-only direct edge及任一reference-model widen、decodable raw drift、actual-arrival near numeric、bad arc/prebuild/canary/checkpoint、nonce/root/mode/lane+summary same-fd swap/symlink/reopen/inode/dirfd/link、transaction/matrix/context/handle mutation。flags/public repeats drift须launch0；N=6 cardinality/commit/rollback及任一lane/slot/root fsync漏项fail；七路径CMake expected/read/deps及local/CI Ruff argv/action任一缺项fail。
controller selftest禁mock`Popen`，真实stubs覆盖second-launch/exit+hang/TERM→kill/双pipe/PairSlot timeout/invalid-temp；通过exact5-field api直接phase-poison真实`commit_validated_run`的pair/reload/revalidate/summary writer same-fd/swap/symlink/reopen/validate/link/cleanup，禁止复制transaction/rollback loop。scratch KAT必须调用真实commit，覆盖exact13项`remove_probe_sta,probe_sta_removed,sta-missing,sta-root-file,sta-root-symlink,sta-lane-extra,sta-descendant-symlink,sta-rmtree-error,sta-fsync-error,sta-mode-0700,sta-mode-0755,sta-mode-invalid,validate_lane_inventory`：两种合法mode均成功，非法mode/static malformed均零删除，descendant symlink外部sentinel identity/bytes不变，rmtree/fsync中途错误hardlink0且隔离，成功final-only。其余transaction KAT继续断言completed handles不变、首次commit前无final，首次link后全局删除/fsync/聚合，并以N=6 fixture锁18/36及commit-success/rollback全目录。双flag、public repeats drift、duplicate nonce均launch0。

### 7.4 Line/format/hygiene

维护性建议（非hard gate）：

- 新增/修改 C++/hpp/Python/CMake/JSON 优先保持单文件 <700；
- 两probe/controller/selftest优先 <550；mapper/readback/scenario优先 <500；
- `CheckCsrStep6SourceInventory.cmake`、`CheckCsrReferenceInputIsolation.cmake`、`CheckCsrStep7Targets.cmake`优先各 <700；
- 本计划优先 <700；任一数字均服从§1.2 owner优先级，可按实际职责和证据需要超过。

Workflow继续计算并报告actual/建议值，但不得仅因超出建议值失败；reviewer只有指出具体职责混杂、重复或不可读代码时才可提出维护性finding。

clang-format exact21.1.8 dry-run/Werror；Python禁`noqa/fmt:off/fmt:skip/extend-exclude`。Ruff exact0.14.13双环境args含`--isolated --no-cache --line-length 100 --target-version py311`，check另含`--select B,E,F,FBT,I,SIM,UP`；logical-order exact七文件为`real_differential/{real_differential_model.py,real_differential_wire_contract.py,real_differential_contract.py,real_differential_controller.py,real_differential_controller_selftest.py}`后`reference_input/{reference_input_candidate_wire.py,reference_input_recompute_transfer.py}`。local从child解析canonical parent root并核`.venv/bin/ruff --version` exact`ruff 0.14.13`，以parent root为cwd、七文件加child前缀执行check/format exit0；wheel在independent child root用`uvx --from ruff==0.14.13 ruff`及七个child-relative路径执行同命令。CMake静态锁两套exact argv/order/path/action bytes及safe/poison，不执行Ruff/network；禁cast/include`.cpp`/fast-math/format suppression与source artifact，diff-check/Mulan齐全。

## 8. 实施顺序、失败语义与验收

### 8.1 合同优先实施顺序

1. 两位首轮 reviewer 分别复查native/wire/fixture与session/process/gate/compat（含§6.5 count owner）；所有finding关闭后冻结SHA。
2. 先写 manifest canonical encoder、full candidate inverse codec及manifest顺序三case-distinct repeat0 actual round-trip、wire/schema/contract test、controller validation/selftest。
3. 写shared initialize/pre-full disable/full/post-full parallel/FIFO replay/stabilization；先在oracle验全部native witness。
4. 写 opaque OracleEncoding边界并通过 object/depfile gate。
5. 写 reference raw→poison→build/candidate→backend→scatter→readback→canary→rerun→release。
6. 写 pair process supervisor、producer scratch两阶段清理、atomic final-only publication和repeat/report。
7. 注册targets/CTest，迁移Step4/6/7 gates和wheel；fresh configure/build。
8. 先跑Step8 exact，再回放Step3–7、Stage0/1、global labels、format/hygiene。
9. 未参与实现的两路最终代码review读取最终diff并独立复跑；修正后由原reviewer复查。
10. as-built report只记录真实修改、测试数字、native-backed/synthetic-only/not-claimed；不commit、不push。

### 8.2 Hard failure semantics

| failure | 必须结果 |
|---|---|
| descriptor/path/SHA/clock bytes invalid | launch前fail，无lane final |
| full/transform/witness/stage失败 | 两lane cleanup/reap，无pair publish |
| pre-full phase/receipt、disabled seed/candidate或FIFO replay不符 | fixture fail，不清值/重排继续 |
| poison任一family/raw drift | build/backend/scatter调用0 |
| build/candidate decode/identity/unsupported失败 | backend/scatter调用0 |
| backend/result encode失败 | scatter/readback调用0 |
| scatter reject/hash/writes/event错误 | 无success observation |
| canary未改变正确wire或改raw/hash | 不运行/不接受rerun |
| rerun未覆盖active canary、disabled record漂移或full wire不等oracle | pair fail |
| near-tie/secondary-root重算不符 | coverage fail |
| child launch/timeout/pipe/temp/schema失败 | terminate→wait→kill→reap两lane |
| 任一lane `sta/` missing/type/symlink/uid/dev/mode/inventory预检失败 | 全lane零删除、首次hardlink调用0；保留失败run且不得消费 |
| `sta/` rmtree或lane fsync失败，或删除后inventory/temp rebind失败 | 允许已发生的部分scratch清理，但首次hardlink调用0、无final/summary；保留并隔离，不重试 |
| two-temp/cross-lane/repeat/public-matrix失败 | 首次hardlink调用0，无pair final/summary；若尚未进入scratch Phase B则目录零删除 |
| 首次hardlink后任意later pair/reload/revalidate/summary write/validate/link/check失败 | 全局rollback本run finals+summary temp/final，fsync root+`pair_count`slots+`lane_count`lanes，聚合全部错误 |
| success lane仍有`sta/`、temp或extra entry | `validate_lane_inventory`失败，不得接受summary或作为Step9 input |

不允许 warning 后继续、skip、xfail、canned copy、从 native output补 backend input，或把 unsupported 自动改成 synthetic-only PASS。

### 8.3 构建与测试命令

从 `/home/shigure/code/ecc` bare flake运行，build dir固定 `chipcompiler/thirdparty/ecc-tools/build-ista-step8`：

~~~bash
nix --extra-experimental-features "nix-command flakes" develop --command \
  cmake -S chipcompiler/thirdparty/ecc-tools \
        -B chipcompiler/thirdparty/ecc-tools/build-ista-step8 \
        -G Ninja -DBUILD_TESTING=ON -DBUILD_PYTHON=ON \
        -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS=-idirafter/usr/include

nix --extra-experimental-features "nix-command flakes" develop --command \
  cmake --build chipcompiler/thirdparty/ecc-tools/build-ista-step8 --target \
    ista_csr_real_oracle_probe ista_csr_real_reference_probe \
    ista_csr_real_differential_wire_contract_test

PYTHONDONTWRITEBYTECODE=1 \
nix --extra-experimental-features "nix-command flakes" develop --command \
  ctest --test-dir chipcompiler/thirdparty/ecc-tools/build-ista-step8 \
    -R '^ista_csr_(real_differential|step8_)' --output-on-failure

PYTHONDONTWRITEBYTECODE=1 \
nix --extra-experimental-features "nix-command flakes" develop --command \
  ctest --test-dir chipcompiler/thirdparty/ecc-tools/build-ista-step8 \
    -R '^ista_csr_real_differential_fresh_process$' \
    --repeat until-pass:3 --output-on-failure

PYTHONDONTWRITEBYTECODE=1 \
nix --extra-experimental-features "nix-command flakes" develop --command \
  ctest --test-dir chipcompiler/thirdparty/ecc-tools/build-ista-step8 \
    -R '^ista_csr_' --output-on-failure
~~~

另原样运行 Stage0/1 focused、`-L '^ista_unit$'`、`-L '^ista_property$'`、`-L '^ista_smoke$'`、resolved-parent local Ruff check/format、wheel-equivalent（含child-root pinned Ruff）和Step7 frozen format/hygiene命令。任一修复后重跑受影响 exact、chained gate及全部三个 label。

### 8.4 DoD

完成必须同时满足：本计划双review按新SHA APPROVE；18 fresh child/9 pair全绿；正式同环境`umask 077`的N=6诊断证明18 slots/36 lanes、summary+36 finals且每lane final-only；scratch两阶段清理、`{0700,0755}`合法mode、非法mode零变更、descendant-symlink安全、rmtree/fsync错误hardlink0的真实selftest与Workflow poison全绿；真实隔离证据而非dependency-closure声明；extended全部unique/witness；poison-before-export；candidate只来自首次successful build；pure backend/scatter与fresh oracle exact+1e-9；canary被native stages覆盖且rerun等oracle；raw/六hash/generation0不变；observation/repeat/report合同通过；Step8增量与Step7 baseline证明通过；Stage0/1、Step3–7、global labels、wheel、format/hygiene全绿；final code双review APPROVE；未commit、未push。失败或部分scratch删除run只保留作审计，不得作为measurement input或被重试。

Step 8完成仍不表示Stage 2完成。Step 9才用6 repeats做warmup1/measured5原始metrics汇总；Step 10才允许本地提交并做包装审计。
