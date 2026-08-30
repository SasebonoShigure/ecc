# ECC IncreGPUSTA 阶段 2 Step 9 详细实施计划

> 状态：v0.31 generation-separated prior-attestation review candidate；整合历史/当前代次拆分、current collaboration records、PRE/later semantic cross-binding、post-publication/FINAL历史report-state窄例外、transition old/new identity全绑定、producer scratch final-only修复、POST manifest-only validator修复与Step 10本地封口；本版exact bytes新双审前不得启动正式候选或commit
> Step 8 前置：v0.15 计划 SHA-256 = `2246cc8ce01d4952b7e8435275907327ef21446e15a4a47629f39febe9abbdc0`；该SHA的新计划双审、changed controller/selftest/Workflow gate最终复验与两路代码审查须在PRE前fresh完成，旧v0.14 review/gate/test结论不得自动沿用。唯一既存Step8 machine receipt仍是历史cleanup receipt；其余结论只由绑定来源bytes的prior attestation转录。Step8 report后、v0.24 plan review期间15个CPython313 pyc/4个cache-dir的repair intent SHA `a3df8abbdf29e14eb2f2209f3412e2bdcda859a107affc1dc5d98538b97b17a3`与completion receipt SHA `dad7d36e85c3889f7d7ce05dec333667e79f14ba624efb7bcd506c4b557f4974`保持历史绑定，不伪称Step8当时receipt或Step9 measurement cleanup
> 代次边界：current Step8 v0.15 plan为同一路径的新bytes `2246cc8c…`；历史cleanup receipt `c98a7cd1c7d94e4af596762769efb728ad785e5e079334fb2820ad06c8bf7931`内部只允许旧Step8 v0.14 `604dd5427d2ba1003ff4e22ae0ab3e5760148331fd1fcebf1e33ae2d9c402be2`。历史repair intent还只允许cleanup `c98a7cd1…`、report `026ba999791ec0c5e502e24a1ba48a7691e6a8f4218b8c3ed0925dd4918cea5f`、Step8 `604dd542…`及旧Step9 candidate `a28943d6bda6f3cc36824b2b10299e9146363a93da95f1782db18f5b4bf8947b`；同path跨代绝不要求SHA相等，也不得把current SHA代入历史字段
> 范围：冻结 warmup 1 + measured 5 的 conversion/reference/prevalidation-scatter smoke；旧正式尝试因36 lane残留`sta/`而拒绝并封存，本轮只在v0.31获批及Step8 fresh closure后按§9创建全新候选链
> 结论边界：只报告原始内部 timing、描述性 median/p95 与 modeled storage；不报告 speedup、RSS、heap 或 allocator
> 提交边界：Step 9 证据与工具只在 build tree；Step 10 前不 commit、不 push，外层总计划不更新

## 1. 裁决、改动边界与声明边界

### 1.1 Step 9 是证据收口

Step 9 复用 Step 8 production steady-clock fields 与 fresh-process controller，不新增 benchmark executable、CTest、production instrumentation、Python source module、CMake、JSON Schema、fixture、manifest、golden 或 wheel 内容。旧正式尝试暴露的producer scratch缺口已上游返回Step8 v0.15，以test-only controller/selftest/Workflow gate闭合；v0.31批准后不得再修改这些source/CMake。Stage 2 §17 的 warmup 1/measured 5 是本阶段窄 smoke 合同，优先于外层总计划面向未来完整 profile 的 warmup 5/repeat 30。

计划通过双审后，实施期允许的改动 exact 为：

- parent 新增/修订 `docs/incregpusta/stage2-step9-plan.md`；
- Step 8 最终验收后，surgical 更新 `docs/incregpusta/stage2-report.md`；
- 在 `build-ista-step8/step9-evidence.*` 内冻结 `step9_outer_driver.py`、`step9_capture.py`、`step9_capture_supervisor.py`、`step9_context.py`、`step9_reduce.py`、`step9_recheck.py`、`step9_provenance.py` 及 JSON receipts；
- Step8 v0.15 freeze后不再修改 child source/test/schema/CMake、parent生产/测试代码或外层 `docs/incregpusta-implementation-plan.md`；本轮已发生的producer修复是上游Step8 closure，不是Step9越权例外。

本次v0.31计划修订冻结修复后的接口、可信来源与failure semantics。旧诊断工具或失败候选中的任何tool/receipt/review不得直接转正；获批后必须在fresh exclusive candidate中重新冻结七tool exact bytes/SHA、全量两路KAT与两路读码APPROVE，且只存在build tree。

owner 行数裁决：500、550、700行全部仅为维护性建议，不是hard gate。正确性、证据完整性、可读性与可审计性优先；任何reviewer或gate不得仅因超过这些建议行数而拒绝。本计划actual=1228；超过700是为保留完整证据DAG、失败语义与Step10封口合同。若计划或七工具超过任一建议值，只需记录actual行数、无法安全压缩/拆分的理由与review结论；不得为追求行数而合并职责、删除KAT/失败证据或降低合同清晰度。

### 1.2 允许与禁止的声明

允许声明：

- 本地 frozen dirty tree 的 Release smoke 已执行；
- 三个 supported fixture、每次 repeat 的三段内部 `steady_clock` duration；
- node/arc/level、九 vector logical/capacity、modeled host logical/capacity bytes 与 high-level capacity event；
- 每 case/phase 五个 measured 样本的 median 与 nearest-rank p95；
- 同一 6-repeat run 的 native/reference/scatter/rerun correctness 继续通过。

禁止声明：

- CPU reference 相对 native、GPU 或其他模式的 speedup；
- end-to-end、process startup、native full、oracle、poison 或 JSON I/O 性能；
- RSS/PSS/working set、heap、allocator allocation count 或真实内存占用；
- statistically stable benchmark、回归阈值、论文复现或跨机器可比；
- CUDA/GPU、incremental、generation>0、mutation、Dual-CSR 或 affected-cone 性能；
- 36 child PID 均由独立 OS observer 证明，或所有 timed TU 有 uniform floating-point flags。

`comparability_status` 固定为 `non_comparable`。timing 较慢或抖动只记录，不构成 FAIL。

## 2. Step 8 v0.15 与工作树前置

### 2.1 阻断式前置

开始任何 Step 9 build/run 前必须同时满足：

- WSL `pwd` exact `/home/shigure/code`；
- parent/child branch 均为 `IncreGPUSTA`；
- Step 8 v0.15 必须由两名窄设计 reviewer 对上述 exact SHA 最终 APPROVE，且changed controller/selftest/Workflow gate最终SHA已有fresh动态复验与两路代码APPROVE；这些裁决来自本次协作记录/报告而非当时存在的外部receipt，PRE前必须按§7.1生成并双审prior attestation，禁止虚构旧receipt path或加密身份；
- Step 8 v0.15 plan SHA exact `2246cc8ce01d4952b7e8435275907327ef21446e15a4a47629f39febe9abbdc0`，开始前逐字节复验；
- Step 8两路final code review及gate结论按prior attestation作有来源转录；唯一现存Step8 receipt文件`step8-pyc-cleanup-receipt-v1.json`证明child exact12个历史pyc与三个exact空`__pycache__`精准清理。开始Step9前还须只读绑定plan-review repair intent/receipt及其上述exact SHA，证明随后15个CPython313 pyc/4目录的fixed-manifest repair完成、safe-stop recovery被披露且fresh source scan为空；同时绑定Step8 plan与report PRE bytes，任一actual bytes漂移重新blocking；
- Step 8 final actual test counts、schema/golden hashes 与 controller seven-argument contract 已记录，不沿用superseded plan的provisional数字；
- 从 `/home/shigure/code/ecc` 使用 bare parent flake `nix develop`，禁止 `path:.`；
- build dir exact `chipcompiler/thirdparty/ecc-tools/build-ista-step8`，Ninja + Release，actual compiler 可追溯；
- 未 commit、未 push、未 reset/checkout/stash/覆盖用户既有 dirty bytes。

Step 8 v0.15 的fresh Ruff/CTest/gate/code-review结果若无现存machine receipt，只能作为绑定exact current plan/source/gate bytes的`transcribed_collaboration_verdict_or_gate_claim`；旧report只作为第五条machine preimage bytes，不再以旧v0.14 verdict tail满足current DoD。Step 9正式链不安装Ruff、不重跑CI、不调用网络；这些复验必须在冻结fresh candidate前完成。任一前置不满足时，v0.31不授权“先跑一次看看”；measurement input变化即作废整轮。

### 2.2 Preserved preexisting parent state

Step 9 pre manifest 必须把以下两项作为 `preserved_preexisting` 单独冻结：

- `/home/shigure/code/ecc/CLAUDE.md`：authoritative porcelain-v2 `-z` status只有一个ordinary type `1` record，XY exact `.M`、sub exact `N...`，其worktree bytes、HEAD/index mode/OID、binary patch与unstaged状态均冻结；
- `/home/shigure/code/ecc/docs/incregpusta/stage1-stage2-meeting-report.md`：authoritative porcelain-v2 `-z` status只有一个untracked `? PATH\0` record，其完整bytes、mode与untracked状态均冻结。

Step 9、Step 10 均不得 stage、提交、格式化或改写这两项。最终只能证明其 bytes/status/patch 与 pre baseline exact 相同，不能声称 parent 整体 clean。

### 2.3 兼容对象与authoritative输入

real/baseline manifests、两 controller/probe schemas、所有 manifest-resolved case inputs、Stage 0/1 golden、benchmark schema/projection compat 均在 pre/post/final measurement inputs 中按 actual path/SHA 冻结。benchmark schema v1 不承载 snapshot observation；authoritative source 是 controller summary 加36个published lane finals，且每个accepted lane inventory必须exact singleton final-only。`sta/`只属producer pre-publication opaque scratch，不进入Step9 input、artifact row或consumer authority，任何残留都hard fail。

## 3. Measurement boundary 与 timed objects

### 3.1 唯一 sample source

每个 sample 只取：

~~~text
summary.case_results[bundle case order]
       .repeats[repeat_index 0..5]
       .reference.observation.ready_post_scatter
~~~

`released` 只用于 strict history validation：除 `state=released` 外必须与 ready observation exact 相同，不是第二个样本。不得从 oracle lane、controller wall time、CTest runtime 或 stdout 补 timing。

三个字段与边界：

| 报告名 | 字段 | 包含 | 排除 |
|---|---|---|---|
| conversion/export | `timing_ms.export` | complete reference-input export + FIFO replay | parse、raw projection、poison、JSON |
| reference | `timing_ms.reference` | `CsrCpuReferenceBackend::compute` DB-free full graph | oracle、scatter、publish |
| prevalidation/scatter preparation | `timing_ms.scatter` | identity/fingerprint prevalidation、detached preparation、write-count check | no-fail native publish、readback、canary/rerun |

三段均是 production `std::chrono::steady_clock`、ms、finite/nonnegative；不重计外层 wall time，不相加为 total。

### 3.2 33 unique production objects

不得用 probe TU flags 证明 timed code。fresh Release `compile_commands.json` 必须为以下 33 个 unique object 各给唯一、原序 compile entry：

- `timer(1)`：`CsrSessionSnapshotAdapter.cpp.o`。
- `export_adapter(11)`：`CsrReferenceInputAdapter`、`TimingGraphCsrAdapter`、`TimingGraphCsrArcExport`、`TimingGraphCsrAdjacency`、`CsrGraphValidator`、`CsrConstraintExport`、`CsrClockSeedExport`、`CsrTimingCheckExport`、`CsrLibertyExport`、`CsrLoadExport`、`CsrParasiticExport` 的 `.cpp.o`。
- `input_core(8)`：`TimingSemanticKey`、`CsrFingerprint`、`CsrReferenceCanonicalEncoder`、`CsrReferenceFingerprintPayload`、`CsrSnapshotIdentityValidator`、`CsrReferenceInputValidator`、`CsrReferenceConstraintValidator`、`CsrReferenceNativeModelValidator` 的 `.cpp.o`。
- `fifo(1)`：`CsrFifoLevelization.cpp.o`。
- `reference_core(6)`：`CsrCpuReferenceBackend`、`CsrCpuReferenceResultInitialization`、`CsrCpuReferenceArcTransfer`、`CsrCpuReferenceForwardPropagation`、`CsrCpuReferenceRequiredPropagation`、`CsrTableLookup` 的 `.cpp.o`。
- `scatter_adapter(3)`：`TimingResultScatter`、`TimingResultScatterValidation`、`TimingResultScatterPreparation` 的 `.cpp.o`。
- `scatter_core(3)`：`CsrReferenceValidator`、`CsrTimingResultValidator`、`CsrTimingResultArcValidator` 的 `.cpp.o`。

phase membership exact：export 21 = timer+export_adapter+input_core+fifo；reference 16 = timer+input_core+fifo+reference_core；scatter 27 = timer+export_adapter+input_core+fifo+scatter_adapter+scatter_core。`TimingResultScatterPublish` 因 stop point 在 publish 前排除；`CsrGraphEncoding`/`NativeGraphProjection` 不在 actual closure。

当前事实必须忠实记录：timer/export/scatter adapter entries 含 `-O3 -fopenmp -std=gnu++20` 且无 `-ffp-contract=off`；core entries 另有 `-ffp-contract=off`。特别是 `CsrSessionSnapshotAdapter.cpp` 当前 `-O3 -fopenmp`、无 `-ffp-contract=off`。本步不作 uniform-flags claim；若要统一，退回 Step 8 改 CMake、重审和重跑。

### 3.3 并发与线程措辞

controller 每 pair 同时启动 oracle/reference 两 child，pair 之间串行；内部 reference timing 时 oracle 可能并发。固定 `OMP_NUM_THREADS=1`、`OMP_DYNAMIC=FALSE`，但只有 call-graph audit 无 dispatch 时才写 effective thread count=1。报告同时记录 pair concurrency=2、CPU topology、affinity、pinning/governor 是否受控。

## 4. 单一 Nix envelope 与 evidence tools

### 4.1 唯一执行环境

outer-driver、capture、supervisor、context、reducer、recheck、pre/post/final provenance 以及所有 Python 自检必须在 parent bare flake 的同一显式环境中运行；禁止PATH解析或host fallback。parent flake.lock的nixpkgs rev exact `f4b140d5b253f5e2a1ff4e5506edbf8267724bde`，离线求值并交叉核对`python3.outPath` exact `/nix/store/829wb290i87wngxlh404klwxql5v18p4-python3-3.13.7`；七tool唯一解释器realpath exact `/nix/store/829wb290i87wngxlh404klwxql5v18p4-python3-3.13.7/bin/python3.13`、file SHA-256 exact `6a71845228f0cf947f236ba49701b1ba841ea04284ed75b1d180258b16aa7116`。

~~~bash
cd /home/shigure/code/ecc
nix --extra-experimental-features "nix-command flakes" develop --command \
  bash --noprofile --norc
umask 077
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1
export OMP_DYNAMIC=FALSE
export LC_ALL=C
export TZ=UTC
~~~

所有后续命令均在该 Nix shell；`umask 077`使本次真实probe `sta` root预期0700，但Step8 producer合同仍是closed `{0700,0755}`，逐lane no-follow验证且两者都必须在publication前删除；这不授权context接受持久`sta`。每个工具入口先assert五个env、`sys.executable` exact及`sys.dont_write_bytecode==1,sys.flags.isolated==1,sys.flags.no_site==1,sys.flags.ignore_environment==1`。七tool prefix冻结为`TOOL_PREFIX=[ABS_NIX_PYTHON,"-B","-I","-S",ABS_TOOL]`；Python executable是`argv[0]`、三个flag是`argv[1:4]`、tool path是`argv[4]`。PRE与FINAL均fresh复验Python realpath/version/file SHA、全Nix-store recursive `ldd` closure无not-found，并实际import `argparse,ctypes,dataclasses,errno,fcntl,hashlib,json,math,os,pathlib,resource,select,signal,statistics,subprocess,tempfile,time`。site/user-site、`PYTHONPATH`、cwd/script-dir隐式imports均被`-I -S`排除；`PYTHONDONTWRITEBYTECODE=1`只作defense-in-depth，不能替代`-B`。任何PATH、host Python、额外module、flag缺失/重排/重复或closure漂移使整轮无效。

controller现有bare sibling import需要可信script dir，因此prefix单独冻结为`CONTROLLER_PREFIX=[ABS_NIX_PYTHON,"-B","-E","-S",ABS_CONTROLLER]`，并在spawn前清除全部`PYTHON*`、复验controller及下列15-source allowlist bytes/SHA/no-follow identity；`-B -E -S --help` compatibility KAT必须PASS。controller不得使用`-I`，七tool不得使用`-E`。每次help/import/KAT/authoritative run前后都fresh扫描child `*.pyc`与任意`__pycache__` filesystem entry并要求exact absent。

实际repo-local bootstrap closure cardinality exact15、canonical inventory/measurement-row order exact如下；该清单不是执行顺序。每项measurement input exact记录`source_id,allowed_import_names,canonical_path,dev,ino,uid,mode,size,sha256`，其中`projection_contract.allowed_import_names`必须包含且只把special alias绑定为`_ista_step2_projection_contract`：

~~~text
baseline_contract
projection_canonical
projection_contract
reference_input_bootstrap
reference_input_canonical
reference_input_model
reference_input_candidate_wire
reference_input_raw_wire
reference_input_recompute_fingerprint
reference_input_recompute_graph
reference_input_recompute_transfer
reference_input_recompute_model
real_differential_model
real_differential_wire_contract
real_differential_contract
~~~

`step9_context.py`是唯一加载这15项的tool。它在执行其中任何一项前，先对15个validated parent dirfd以`O_RDONLY|O_NOFOLLOW`各single-open，fstat regular/identity、short-read到EOF并校验全部bytes/SHA；snapshot `sys.path,sys.meta_path,sys.path_importer_cache`、相关`sys.modules`及原`importlib.util.spec_from_file_location`，拒绝logical-name/alias collision。随后安装allowlist-only captured-byte `MetaPathFinder/Loader`：repo module只能从预捕获bytes `compile`/`exec`，不得reopen；stdlib须预载且只从builtin/frozen或冻结Nix stdlib/extension closure解析。为忠实兼容actual bootstrap，唯一允许并完整trace的`sys.path`变化依次是`insert(0,BASELINE_ROOT)→insert(0,REFERENCE_INPUT_ROOT)→insert(0,PROJECTION_ROOT)→remove(PROJECTION_ROOT)`；唯一允许的`spec_from_file_location`调用是`(_ista_step2_projection_contract,exact projection_contract path)`，但返回loader仍消费captured bytes，不得按path二次打开。从`real_differential_contract`起载，module在exec前注册以支持循环，失败逐项rollback。

成功后要求executed distinct source set exact15，且`exec_start_trace` exact为`[real_differential_contract,real_differential_wire_contract,real_differential_model,baseline_contract,reference_input_bootstrap,projection_contract,projection_canonical,reference_input_candidate_wire,reference_input_model,reference_input_canonical,reference_input_raw_wire,reference_input_recompute_fingerprint,reference_input_recompute_graph,reference_input_recompute_model,reference_input_recompute_transfer]`；trace event定义为每个captured source的module code首次进入执行，projection_contract项logical name fixed `_ista_step2_projection_contract`。inventory order与exec-start trace是两项独立authority，不得互换；projection alias exact一次、repo-origin `sys.modules` delta无第16项。restore上述四类import global与cache并fresh证明exact。新extension module须记录canonical origin/file SHA和recursive `ldd`全闭包；其他新module只能builtin/frozen或冻结Nix Python closure；child pyc/cache仍exact absent。KAT分别覆盖inventory与exec-start trace的15项missing/extra/order、import-name/hash/identity、preopen后path替换、logical collision、非allowlist import、bootstrap trace增删重排、spec alias/path/次数、captured-byte reopen、sys.modules/cache污染、extension closure及restore fault。

为只保留一份canonical JSON codec、no-follow reader、hardlink publisher与`/proc` tracker，`step9_capture_supervisor.py`同时是frozen common-runtime owner，仍是七tool之一而非第八helper。它在logical `_ista_step9_common_runtime_v1`下exports `__all__=("CANON","StrictJsonCodec","NoFollowReader","HardlinkPublisher","ProcTracker","validate_tool_prefix")` exact，CLI只在main guard执行。DAG export edges exact为`capture_supervisor→outer_driver,capture,context,provenance,reducer,recheck`及`context→reducer,recheck`；recheck仍禁止reducer，其他edge禁止。每个consumer以validated dirfd single-open捕获approved owner bytes/SHA并从captured bytes编译固定logical name；reducer/recheck再同法各加载一次approved context为`_ista_step9_frozen_context_v1`，不得ordinary import、改`sys.path`或重开path。context exports `__all__=("StrictContext","PidCapabilities","build_strict_context")` exact且CLI仅在main guard执行。

tool freeze/两路读码顺序exact `capture_supervisor→context→reducer→recheck→outer_driver→capture→provenance`；runtime owner SHA变化使全部六consumer旧审批失效，context SHA变化使reducer/recheck旧审批失效。各tool inventory/primary记录owner/context dependency path、SHA、logical name与load count exact1。KAT覆盖普通import、missing/extra edge、logical alias/path/SHA漂移、重复加载、consumer复制codec/publisher/proc逻辑、recheck→reducer及main-guard误执行；均nonzero且无可消费evidence。

统一strict type `dependency_load_v1`，row keys exact `logical_name,path,sha256,load_count`，不含schema或其他key；logical name只允许`_ista_step9_common_runtime_v1|_ista_step9_frozen_context_v1`，path为canonical absolute no-follow regular/current-uid/mode0700 approved file，SHA为fresh raw bytes lower-hex，`load_count`为integer exact1且bool拒绝。所有下述`dependency_loads` arrays都使用该closed row，并与tool inventory、本次captured-byte loader trace及consumer actual primary逐path/SHA/name/count交叉绑定；context的15-source closure仍只进module inventory，不计入该sibling-load array。

七tool dependency cardinality/order exact：owner `step9_capture_supervisor.py=[]`；普通consumer `step9_outer_driver.py,step9_capture.py,step9_context.py,step9_provenance.py=[common-runtime]`；`step9_reduce.py,step9_recheck.py=[common-runtime,context]`，其中两个logical names顺序固定为common再context。禁止按import发现顺序排序、把owner自列为dependency、漏/多/换序/重复edge或把load count聚合到2。每个tool inventory row、每次self-test KAT primary、对应tool review及每个operational primary都必须携带同一个exact `dependency_loads` value；任一处missing/extra/type/schema/logical/path/SHA/count/cardinality/order不符或跨receipt不等均由owner `CASE_REGISTRY`负例证明nonzero/no replay/no consumable primary。

#### 七tool self-test、KAT receipt与双审

七个现有tool文件各自在所有operational grammar之外，只允许一个互斥public self-test grammar；不得新增第八helper、动态代码、repo import或隐藏re-entry CLI：

~~~text
[ABS_NIX_PYTHON,"-B","-I","-S",ABS_TOOL,
 "self-test","--scratch-dir",ABS_SCRATCH_DIR,
 "--kat-receipt",ABS_KAT_PRIMARY_RECEIPT]
~~~

`self-test`必须是`argv[5]`且余下option/name/order exact；与任何operational subcommand/options混用、duplicate/abbreviation/unknown/positional remainder均在创建scratch前拒绝。fixture child只可由已验证且已加载的同文件通过`os.fork()`进入closed internal callable，不exec另一个Python文件、不接受public child-mode argv；因此没有未冻结的sealed child CLI。每次调用要求scratch初始ENOENT，由tool以exclusive mkdir创建canonical no-follow/current-uid/mode0700目录；它必须位于validated ignored build tree、authoritative `EVIDENCE_DIR`之外且不与repo/source/output/另一reviewer scratch alias或重叠。case仅可写该scratch；结束须证明live/zombie exact0、无未登记path，KAT primary则以共同publisher写scratch外的requested final。

每个tool源码内含一个reviewed literal `CASE_REGISTRY`，row exact `ordinal,case_id,expected_outcome`；ordinal contiguous、case_id nonempty unique且registry order即执行顺序，`expected_outcome` closed enum `accept|reject|nonzero-no-replay|crash-recover`。`registry_sha256=sha256(CANON(CASE_REGISTRY))`；禁止按发现顺序、glob或运行结果增删case。每个现有或新增fault KAT必须先归入下列唯一owner并改变owner tool SHA/registry SHA、重跑两路self-test并重审，未登记的人工/ad-hoc测试不能满足gate：

- capture-supervisor：共同codec/no-follow/publisher、两mode strict receipt、subreaper/adoption/cleanup；
- outer-driver：preflight、CLOEXEC fork/exec判别、wait/streams/timeout/process-tree与phase envelope；
- capture：controller/PGID/timeout/marker/failure diagnostic、18/36 capture inventory；
- context：15-source captured loader、DAG/context API、Pair/Lane projection、validator/schema/PID capability；
- reducer：三output schema/CANON/row/cardinality/formula与invalid numeric；
- recheck：独立18/18/9重算、reducer隔离、input/output tamper；
- provenance：prior copy/attestation、closed inventory/repo/platform/phase/report publisher与transition，以及POST external-exec `expected_outputs` manifest-only边界；registry须含`post-evidence.accept-manifest-only`与`post-evidence.reject-manifest-plus-primary`。

KAT primary token exact `ista-csr-step9-tool-kat-receipt/1.0.0`；top-level exact `schema,publication_contract,tool,tool_identity,dependency_loads,argv,env,cwd,scratch,case_registry,registry_sha256,case_count,cases,cleanup,planned_stdout_size,planned_stdout_sha256,internal_state,complete`。`tool_identity`为`identity_v1`并与`argv[4]`/approved SHA/mode0700交叉；scratch exact `path,dev,ino,uid,mode,start_empty,end_inventory_sha256`且mode0700/start_empty true；case_registry即上述literal array，count/hash自洽。每个cases row exact `ordinal,case_id,expected_outcome,observed_outcome,returncode,stdout_size,stdout_sha256,stderr_size,stderr_sha256,artifact_inventory_sha256,passed`，与registry逐ordinal/id/outcome相同；整数nonnegative且bool不算integer、passed必须true。`cleanup` exact `live_count,zombie_count,unowned_path_count`且全0；accepted internal固定`internal_state="all_cases_passed_pending_external_observation",complete=false`，stdout planned为primary absolute path+LF。
该KAT schema中的所有integer均要求`type(value) is int`并拒绝boolean；ordinal/count/dev/ino/uid/size服从§4.3 U64，mode exact0700，returncode exact `0..255`，所有SHA为64位lower-hex。scratch/cwd/receipt path均为canonical absolute，scratch path与CLI `--scratch-dir`、receipt path与CLI `--kat-receipt` byte-exact；`case_id`匹配`[A-Za-z0-9][A-Za-z0-9._-]{0,127}`，observed outcome使用与expected相同enum并逐ordinal相等，registry/cases ordinals与case_count共同构成`0..N-1`。planned stdout size/SHA绑定receipt path+LF。


每个tool由两名不同reviewer各在distinct scratch独立执行一次标准`outer-driver→supervisor --mode evidence-tool→TOOL_PREFIX self-test`，supervisor `--expected-output`只含该次KAT primary；actual primary/inner-exec/outer三件链须rc0、stdout exact primary path+LF、stderr empty。tool review token exact `ista-csr-step9-tool-review/1.0.0`；top-level exact `schema,plan_sha256,tool,tool_identity,dependency_loads,kat_primary,kat_inner_exec,kat_outer,registry_sha256,observed,reviewer_id,decision,findings`；三KAT evidence项为`ref_v1`，observed exact `inner_returncode,outer_normalized_returncode,inner_stdout_sha256,inner_stderr_sha256,outer_stdout_sha256,outer_stderr_sha256`，两rc exact0并匹配actual streams。两reviewer id distinct、各自scratch/三件链distinct、`decision="APPROVE",findings=[]`；任一tool/dependency/plan/registry/receipt SHA变化使该tool两份review同时失效。因七个self-test全都经过同一frozen outer-driver与capture-supervisor observer链，outer-driver或capture-supervisor任一tool/dependency/registry/receipt SHA变化还必须使全部七tool的两路KAT链及tool review同时失效并全量重跑。上述receipt及所有nested均recursive additionalProperties=false。
`reviewer_id`必须为nonempty UTF-8 string并拒绝NUL/CR/LF，`registry_sha256`为lower-hex SHA；两份review只按reviewer_id raw UTF-8 bytes严格升序配对，禁止casefold或locale排序。


KAT链按每个执行者而非subject复制列表：subject KAT primary验证subject tool的exact `dependency_loads`，引用的external-exec supervisor receipt验证owner `[]`，outer receipt验证outer-driver `[common]`。tool review同时解码三件ref并分别与三者tool inventory/load trace交叉；任何层把subject list复制给observer、或tool inventory两array的reviewer sort/ordinal/ref pairing不符，都必须negative KAT拒绝。

### 4.2 Tool freeze 与共同publisher

测量前创建fresh exclusive unpredictable nonce、mode-0700且initial ENOENT的`EVIDENCE_DIR`，把七个reviewed stdlib-only build-tree tools以mode0700重新冻结并记录file SHA。历史quarantine exact为`/home/shigure/code/ecc/chipcompiler/thirdparty/ecc-tools/build-ista-step8/step9-evidence.gVLAN6UZ9Pwc`与`/home/shigure/code/ecc/chipcompiler/thirdparty/ecc-tools/build-ista-step8/step9-controller-run.gVLAN6UZ9Pwc`；两目录只读保留失败诊断，后者36个lane曾残留mode0755 `sta/`。另一个在任何KAT/PRE/capture写入前即因代次合同审查而放弃的pre-KAT候选exact为`/home/shigure/code/ecc/chipcompiler/thirdparty/ecc-tools/build-ista-step8/step9-evidence.e23j5WXi4kXh`；它只含七个0700/nlink1 tool files，不含KAT/PRE/capture outputs；其预留run-root `/home/shigure/code/ecc/chipcompiler/thirdparty/ecc-tools/build-ista-step8/step9-controller-run.WALm91hGmw75`保持ENOENT。上述所有路径不得删除、修补、清理、重命名、作为新EVIDENCE_DIR/run-root、与新路径/inode alias，或复用/跨引其中tool、KAT、review、attestation、PRE、capture receipt、summary/final。repo-local contract/model只允许按§4.1受控loader加载；provenance可用stdlib `subprocess`调只读local `git/ninja/ldd`。禁止pip dependency、未经allowlist的source-tree script、运行中改tool bytes。

所有 JSON output/receipt 使用同一 byte contract：

- canonical bytes = `json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8") + b"\n"`；
- 共同publisher token exact `hardlink-no-overwrite-v1`。final必须是canonical absolute path，validated same-dir parent以no-follow dirfd绑定，开始时final exact `ENOENT`；不得直接open final写入；
- 在same dir以unpredictable basename、`O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW`/0600创建exclusive temp；short-write loop完整写canonical bytes→file fsync→close，再以`O_RDONLY|O_NOFOLLOW`重开，要求regular/current uid/0600/nlink1并重读bytes/SHA exact。到此final始终ENOENT，partial bytes只可能位于temp；
- 用dirfd-relative `linkat`/stdlib safe equivalent、绝不follow symlink地把temp hardlink到final；final并发出现必须以`EEXIST`失败且绝不overwrite。link后no-follow要求temp/final同dev+ino、regular/0600且双方nlink2，第一次parent-dir fsync；再unlink temp，要求temp ENOENT、final同identity且nlink1，第二次dir fsync后复验，才算原子发布成功；
- link前failure只删除own temp并dir fsync、证明final ENOENT；link后failure须仅对已复验为own inode的final做rollback unlink+dir fsync，再删own temp+dir fsync并证明两者ENOENT。任一步不可证则publisher hard fail、调用链nonzero并把evidence dir标为poison；任何consumer都不得凭残留complete bytes授权成功，且不完整bytes永不出现在final path；
- 每个receipt schema必须含`publication_contract="hardlink-no-overwrite-v1"`；已有exact-schema data outputs不增加top-level key，但其pending primary receipt必须逐path记录该token、final/temp absence与publisher step receipt。KAT逐步注入temp create/write/fsync/close/reopen/read/link/nlink/first-fsync/unlink/second-fsync，另覆盖partial short-write、concurrent final `EEXIST`、extra hardlink、rollback unlink/fsync fault，以及process crash发生于partial-temp、TEMP_READY、link后未unlink三个窗口；普通Step9 output把crash残留标poison，§10 journal只按其专门ledger重入。全部failure均nonzero且无可消费partial final。
- inner primary receipt 只记录 tool SHA、该tool exact `dependency_loads`、argv array、cwd、五 env、Python、start/end、planned stdout、internal result 与 outputs file/rows SHA；其状态固定为 pending/internal、`complete=false`，不得把 planned returncode/streams称为actual；
- `step9_capture_supervisor.py` 是inner command的唯一bytes-mode external observer，冻结 `--mode capture|evidence-tool`；`step9_outer_driver.py` 是supervisor command的唯一bytes-mode outer observer。前者记录inner actual PID/returncode/raw streams，后者记录supervisor actual PID/raw wait status/normalized rc/raw streams；两层不得互相冒充；
- capture 的inner交付是唯一三件协议：primary receipt固定 `complete=false`；其派生marker path exact `ABS_CAPTURE_RECEIPT + ".complete.json"`；独立supervisor在inner capture实际wait/reap后另写显式 `ABS_CAPTURE_EXEC_RECEIPT`，记录其actual PID/returncode/raw streams；整体complete set仍须下一项outer receipt；
- 只有primary、marker、inner external exec receipt与outer command receipt同时strict通过，且两层actual rc均exact 0、streams与artifact hashes交叉一致，才构成可接受capture complete evidence set；marker/temp/failure artifacts单独永远不授权complete；
- context/reducer/recheck/pre/post/final provenance全部沿唯一 `outer-driver → supervisor --mode evidence-tool → inner` 链启动、wait/reap；其complete evidence exact为pending primary、inner external exec receipt与outer command receipt，必须证明inner及supervisor normalized rc均0、逐层stdout exact primary receipt absolute path+one LF、stderr empty及全部expected outputs path/mode/bytes SHA交叉一致；
- success 时 capture stdout 必须是 summary absolute path + one LF，其他inner tool stdout 是其 primary receipt absolute path + one LF；success stderr exact empty；
- 任一层failure都nonzero且禁止phase completion envelope；capture failure必须没有可接受complete evidence set：正常rollback时marker absent，compound rollback fault允许残留marker但必须由任一actual nonzero、temp/failure poison或其组合阻断；其他工具禁止产出可被误认 complete 的 final receipt。

`--mode evidence-tool` CLI exact为：

~~~text
step9_capture_supervisor.py
  --mode evidence-tool
  --receipt ABS_TOOL_EXEC_RECEIPT
  --primary-receipt ABS_TOOL_PRIMARY_RECEIPT
  --timeout-seconds 600
  [--expected-output ABS_OUTPUT]...
  -- TOOL_ARGV...
~~~

`evidence_tool_timeout_seconds` exact 600，只约束一个generic inner tool，不得与capture的2520、controller wrapper的2400或18个pair各自120混写。supervisor以bytes-mode pipes启动唯一inner；normal/timeout/exception/interrupt及spawn failure全部服从§4.4共同process-tree合同，actual wait/reap且后代清零后才发布exec receipt。只有primary/outputs/actual rc/streams全绿才原样replay inner stdout并返回0；否则不输出可消费primary path并返回nonzero。primary或output单独不授权complete；outer driver还必须actual wait/reap supervisor并证明normalized rc 0。

### 4.3 Outer command observer 与phase envelope

`step9_outer_driver.py` 是第七个frozen stdlib-only build-tree tool；exact CLI为：

~~~text
step9_outer_driver.py
  --receipt ABS_OUTER_COMMAND_RECEIPT
  --supervisor-exec-receipt ABS_SUPERVISOR_EXEC_RECEIPT
  --outer-timeout-seconds 720|2640
  [--phase pre|post|final
   --phase-manifest ABS_PHASE_MANIFEST
   --phase-primary-receipt ABS_PHASE_PRIMARY_RECEIPT
   --phase-envelope ABS_PHASE_COMPLETION_ENVELOPE]
  -- SUPERVISOR_ARGV...
~~~

`outer_timeout_seconds` 对generic supervisor exact 720、对capture supervisor exact 2640，分别只约束outer driver等待supervisor；不得与inner 600、capture supervisor 2520、controller wrapper 2400或pair 120混写。driver在fork前创建独立stdout/stderr pipes与`os.pipe2(O_CLOEXEC|O_NONBLOCK)` error pipe；fork parent只读error end，child只保留write end并在dup stdin/stdout/stderr后调用absolute `os.execve`。exec成功时CLOEXEC使error writer关闭，parent只以zero-byte EOF确认；exec失败时fork stub只向error pipe写exact 4-byte unsigned big-endian errno后`os._exit(127)`。parent用selector并发drain三pipe并以`os.waitpid`取得raw status，禁止shell/text mode，也禁止从supervisor receipt、stderr或exit 127反推exec状态。

以下outer/external observer统一复用closed nested records；每个列出的key均required，未列key均拒绝，object递归`additionalProperties=false`，只有下文明确写nullable者可为null，绝不得以absent代替null。JSON integer一律要求`type(value) is int`，JSON boolean不得冒充0/1或其他integer；boolean字段反向也只接受JSON true/false。`U64`范围exact `0..18446744073709551615`，`PID` exact `1..2147483647`，`ERRNO` exact `1..4095`，`RAW_WAIT_STATUS` exact `0..65535`，`SIGNAL` exact `1..64`，actual `Popen.returncode` exact `-64..-1|0..255`。ordinal/count/ns/starttime/timeout/size使用U64；mode使用`0..4095`；present nlink使用`1..U64_MAX`；SHA使用64位lower-hex。

`ProcessIdentity` exact keys `pid,starttime,ppid,pgrp,session,state`：pid/pgrp/session为PID，ppid为拒绝bool的nonnegative integer，starttime为positive U64，state enum exact `R|S|D|Z|T|t|X|x|K|W|P|I`。ProcessIdentity arrays按numeric `(pid,starttime)`严格升序、stable identity不得重复；同pid不同starttime视为不同identity并触发相应PID-reuse/identity检查。

`InternalError` exact keys `ordinal,stage,error_type,error_errno,error_message_sha256`。ordinal为U64；stage enum exact `preflight|subreaper_set|subreaper_get|proc_scan|proc_parse|process_classification|spawn|fork|exec_pipe|identity_query|communicate|signal|waitpid|stream_validation|summary_validation|primary_publish|stdout_delivery|marker_publish|marker_rollback|diagnostic_publish`；error_type为匹配`[A-Za-z_][A-Za-z0-9_.]{0,127}`的非空string；error_errno为null或ERRNO，有actual positive `.errno`时必须写该值，否则必须null；message SHA绑定actual UTF-8 diagnostic bytes。InternalError arrays按ordinal严格升序且不得重复。

`Subreaper` exact keys `set_state,set_return,set_errno,get_state,get_return,get_errno,get_value`。set_state enum `failed|succeeded`，get_state enum `not_attempted|failed|succeeded`；set成功只允许`0,null`，set syscall失败只允许`-1,ERRNO`，set调用前/调用中exception只允许`null,null`并要求对应InternalError；set失败时GET三值必须`not_attempted,null,null,null`。GET成功只允许`0,null,0|1`，GET syscall失败只允许`-1,ERRNO,null`，GET exception只允许`null,null,null`并要求对应InternalError。accepted preflight只允许set/get均succeeded且get_value exact1。

`ObservedProcess` exact keys `identity,role,adoption_classification,original_parent_pid,workset,evidence_hard_fail`。role enum `direct|descendant|adopted`，workset enum `none|direct|adopted`；adoption_classification只在role=adopted时nonnull且enum exact `transition_observed|first_seen_adopted`，前者要求original_parent_pid为PID且不等于observer PID，后者要求original_parent_pid=null；其他role两字段均null。first_seen_adopted固定evidence_hard_fail=true；transition_observed固定false；非法ppid漂移另以InternalError记录并把对应row置true。当前direct/adopted均须current ppid等于observer PID，任何已入adopted workset的identity不得因后续漂移被移出。

`Observation` exact keys `ordinal,point,scan_state,processes,error`。point enum exact `pre_spawn|post_spawn|normal_wait|timeout|exception|interrupt|pre_term|term_poll|pre_kill|kill_poll|pre_waitpid|final`；scan_state enum `failed|succeeded`。failed只允许`processes=[]`且error为InternalError；succeeded只允许error=null且processes按identity numeric升序、无重复。observations按ordinal从0 contiguous、严格保持actual fresh-scan顺序，空成功snapshot也必须保留一条row。

cleanup action records同样closed：`SignalAction` exact `ordinal,scope,target,signal,outcome,error`，scope enum `process|process_group`，signal enum `TERM|KILL`，outcome enum `sent|already_absent|identity_mismatch|failed`，target为本次action前fresh复验或最后绑定的ProcessIdentity；error只在identity_mismatch/failed时为InternalError，否则null。`WaitpidAction` exact `ordinal,target,options,outcome,result_pid,raw_wait_status,error`，options enum `blocking|WNOHANG`，outcome enum `reaped|none_ready|echild|failed`；reaped要求target为ProcessIdentity、result_pid=target.pid、raw_wait_status为RAW_WAIT_STATUS、error=null；none_ready要求target=null、result_pid=0、其余null；echild要求target/result/status/error全null；failed只允许error nonnull。`CommunicateAction` exact `ordinal,target,timeout_seconds,outcome,returncode,stdout_size,stdout_sha256,stderr_size,stderr_sha256,error`，outcome enum `completed|timeout|failed`；completed要求returncode及两组size/SHA nonnull、error=null；timeout要求returncode/error=null且每组partial size/SHA同null或同nonnull；failed要求error nonnull且其余nullable pair仍同null或同nonnull。三类action array均按ordinal从0 contiguous并保持actual call order。

`Cleanup` exact keys `direct_identity,adopted_workset,signals,waitpids,communicates,final_scan_ordinal,echild_observed,live_count,zombie_count,errors`。direct_identity在未创建direct child时null，创建后必须为actual ProcessIdentity；adopted_workset保存每个identity首次纳入cleanup时的ProcessIdentity并按stable identity排序；final_scan_ordinal为null或引用同receipt中point=final且scan_state=succeeded的Observation ordinal。echild_observed为boolean，live/zombie为U64。accepted cleanup要求final reference有效、ECHILD=true、live=zombie=0、errors=[]，且workset中每个identity均有合法signal/wait/absence终态；failure receipt仍须保留actual arrays/counts，不得伪填accepted postcondition。

outer command receipt schema token exact `ista-csr-step9-outer-command-receipt/1.0.0`，base keys exact绑定 `schema,publication_contract,driver_path,driver_sha256,dependency_loads,argv,env,cwd,supervisor_exec_receipt_path,supervisor_exec_receipt_sha256,preflight_state,preflight,fork_state,exec_state,pid,start_wall_ns,start_monotonic_ns,end_wall_ns,end_monotonic_ns,outer_timeout_seconds,raw_wait_status,wait_kind,exit_code,term_signal,normalized_returncode,stdout_size,stdout_sha256,stdout_base64,stderr_size,stderr_sha256,stderr_base64,streams_complete,observations,cleanup,evidence_verdict`，conditional keys只有`fork_errno,exec_errno`。`preflight`为strict object，exact keys `subreaper,scan_state,pre_spawn_child_set`；subreaper为上述Subreaper，scan_state enum exact `not_attempted|failed|succeeded`。not_attempted/failed均要求pre_spawn_child_set=[]；succeeded要求该array为按stable identity排序的ProcessIdentity，且preflight_state=succeeded还要求它exact empty。`exec_state` enum exact `not_attempted|failed|succeeded|indeterminate`。正常退出normalized rc=`WEXITSTATUS`，signal退出=`128+WTERMSIG`；success还要求publication token、valid supervisor receipt/hash、normalized rc0、stdout为summary或primary absolute path+LF、stderr empty且inner exec全绿，随后才replay。
`supervisor_exec_receipt_path`始终为CLI请求的canonical absolute path，调用开始要求该final ENOENT；`supervisor_exec_receipt_sha256`为nullable SHA。preflight/fork未成功或exec failed时固定null；exec succeeded/indeterminate时，该path不存在、非regular或不可完整读取则null，存在可读取regular final则必须记录actual raw-bytes SHA，即使receipt schema无效也不得写null。`evidence_verdict` enum exact `accepted|rejected`；accepted当且仅当preflight/fork/exec均succeeded、wait exited/0、supervisor receipt path/SHA/strict schema全绿、streams complete、stdout为expected path+LF、stderr empty且Cleanup accepted，其他仍可发布outer receipt的组合必须rejected。preflight/fork未成功时stdout/stderr固定canonical empty且`streams_complete=true`；fork后记录actual complete/partial streams。


`preflight_state` exact `failed|succeeded`，`fork_state` exact `not_attempted|failed|succeeded`。SET/GET、fresh scan或empty-child-set证明任一失败时，只允许`preflight_state=failed,fork_state=not_attempted,exec_state=not_attempted,pid=null`，两errno keys均absent，wait fields均null且streams为canonical empty；driver不得fork/spawn/replay/发布envelope，仍须清理已收养workset并证明`ECHILD`/live0/zombie0。只有preflight全绿才可fork；真实fork exception只允许`fork_state=failed,exec_state=not_attempted,pid=null`，`fork_errno`必须present为positive errno、`exec_errno` absent，所有wait fields null且parent证明`ECHILD`；fork成功则PID为actual positive child、`fork_errno` absent。其后error pipe exact 4 bytes+EOF才允许`exec_state=failed`且`exec_errno`唯一present，父仍须wait/reap并记录raw wait/normalized rc；zero-byte EOF才允许`exec_state=succeeded`且两errno keys absent；partial/extra bytes、read error或无bounded EOF一律`exec_state=indeterminate`、无`exec_errno`并hard fail。fork成功后的任何exec状态都不得把PID写null。

outer receipt的observations为上述ordered Observation array，cleanup为上述Cleanup；argv为nonempty string array，env为§4.1冻结的exact strict object。全部base keys always present；只有`fork_errno,exec_errno`是conditional-absent key，绝不以null占位。preflight/fork未成功时pid及全部wait fields为null、streams为canonical empty；fork成功后pid为PID。wait_kind为null或`exited|signaled`：exited要求raw_wait_status、exit_code `0..255`、normalized_returncode同值且term_signal=null；signaled要求raw_wait_status、term_signal为SIGNAL、exit_code=null且normalized_returncode=`128+term_signal`。`fork_errno`只且必须在fork_state=failed时present为ERRNO；`exec_errno`只且必须在fork成功、error pipe exact 4-byte errno、exec_state=failed时present为ERRNO；其他状态二者absent。所有ns/timeout/size遵守U64、SHA/base64 strict canonical decode并与size/SHA一致，递归拒绝bool-as-int。

pre/post/final调用另要求三个phase参数成组出现。只有`preflight_state=succeeded,fork_state=succeeded,exec_state=succeeded`、manifest、pending primary、supervisor exec receipt和outer receipt全部strict通过，outer driver才按共同publisher原子发布phase-local completion envelope；envelope字段绑定phase、publication token、四个absolute path/SHA、outer normalized rc0、preflight/fork/exec states与stdout/stderr hashes。该五件phase evidence由每相consumer/final reviewer fresh复验；不存在自引用地改写manifest。

outer driver在fork前也设置/GET subreaper exact1、证明pre-spawn child set empty并且lifetime只fork一个direct supervisor；normal/timeout/exception/interrupt/fork或exec failure都清理direct/adopted workset，TERM→KILL、drain、waitpid至`ECHILD`及live/zombie0后才发布receipt。KAT逐一覆盖SET fail、GET fail、scan/parse fail、pre-spawn child-set nonempty：四例都须`preflight_state=failed,fork_state=not_attempted,pid=null`、两errno absent、无spawn/no replay/no envelope、nonzero并最终清零；另覆盖真实fork-fail（PID null/唯一fork errno/no wait）、exec-fail（actual PID/唯一exec errno/raw wait/reap）、exec-success error-pipe EOF、supervisor early exit（仍判exec success并记录PID/raw wait，但缺valid supervisor receipt时evidence nonzero）、signal normalization、timeout/exception/interrupt、receipt hash mismatch，以及supervisor rc0后泄漏cooperative/ignore-TERM descendant；failure一律nonzero/no replay/no envelope并最终清零。outer schema KAT还须逐层覆盖preflight/Subreaper、ProcessIdentity、Observation/ObservedProcess、Cleanup及三类action record的missing/extra/type/bool-as-int、integer越界、unknown enum、required-null与conditional-absent互换、identity/ordinal乱序或重复、Observation failure matrix、workset/classification交叉错误、final scan ordinal悬空，以及fork/exec/wait matrix矛盾；全部strict拒绝、nonzero/no replay/no envelope并最终清零。
outer KAT另覆盖preflight/fork/exec failure、supervisor early-exit无receipt，以及requested final不存在却SHA nonnull、存在可读regular final却SHA null、unknown verdict、全绿状态配rejected与失败状态配accepted；均strict拒绝、nonzero/no replay/no envelope。


### 4.4 两mode共同process-tree合同

`capture` 与 `evidence-tool` mode在任何 `Popen` 前都必须只用stdlib `ctypes` 调libc `prctl`：`PR_SET_CHILD_SUBREAPER=36` 设置1并要求return 0，再以 `PR_GET_CHILD_SUBREAPER=37` 写入 `ctypes.c_int`并要求return 0/value exact 1。errno、setup或query任一异常时PID null、不得spawn、写nonzero exec receipt并停止。

set/get exact 1后仍在任何 `Popen` 前以同一stdlib parser做fresh `/proc` snapshot；`pre_spawn_child_set` 定义为所有current `ppid == supervisor_pid` 的 `(pid,starttime)`（含zombie），成功路径必须exact empty。任一entry立即分类为 `first_seen_adopted` 并纳入cleanup-eligible adopted workset：evidence hard fail、不得 `Popen`，但仍须fresh复验identity后TERM→KILL/waitpid并证明 `ECHILD`/live0/zombie0；读取、解析或空集证明失败同样写nonzero exec receipt并停止。

上述set/get与pre-spawn child-set验证成功后，supervisor lifetime内exact只允许一次 `Popen`、一个direct inner child，不得在其前后启动helper/第二child；inner可按自身合同启动后代，特别是provenance允许spawn只读local `git/ninja/ldd`。两mode都以 `Popen(..., text=False, stdin=DEVNULL, stdout=PIPE, stderr=PIPE)` 启动并记录direct child实际PID/starttime。

共同cleanup exact为：

1. 以stdlib解析 `/proc/[0-9]*/stat`；每次fresh snapshot记录观察tuple exact `(pid,starttime,ppid,pgrp,session,state)`，但跨时刻稳定process identity只定义为 `(pid,starttime)`。`ppid,pgrp,session,state` 都是当次分类证据，不作跨snapshot immutable equality；正常state变化不得被误判为PID复用；
2. direct workset先绑定actual direct `(pid,starttime)`。自subreaper set成功起，每次fresh snapshot中任何非direct且current `ppid == supervisor_pid` 的stable identity都必须立即纳入cleanup-eligible adopted workset，不得等待原父证据。若先前fresh snapshot已记录同identity的合法descendant chain与非supervisor原父，分类exact `transition_observed`并记录 `original_parent_pid → supervisor_pid`；若首次观察该identity时已由supervisor收养，分类exact `first_seen_adopted`。前者可作成功evidence，后者及其他ppid漂移、读取/解析错误使evidence hard fail/nonzero/no-replay，但绝不得把当前已收养child移出cleanup workset；
3. 每次signal或waitpid前都fresh复验 `(pid,starttime)`，并证明对象仍属于direct或cleanup-eligible adopted workset；两类都须current `ppid == supervisor_pid`。每次同时fresh记录pgrp/session/state供分类与诊断，但三者变化不阻断合法signal/wait；
4. normal wait、timeout、wrapper exception、interrupt及spawn failure都进入同一postcondition。异常时先对仍live且identity/workset复验通过的direct child TERM并bounded communicate；超时则对同一stable identity KILL。direct已退出但pipe未EOF也不得当作reaped/streams complete；
5. direct child实际reap后继续扫描adopted workset；nominal inner rc0且direct pipes EOF后发现任何leaked descendant也必须先把整次supervisor结果翻为nonzero。对workset先TERM，bounded 10秒循环fresh scan与 `waitpid(-1,WNOHANG)`；任何fresh current non-direct child都按第2项立即加入、分类并TERM。仍live者KILL，再bounded 10秒循环scan/waitpid/reap，期间新收养者同样立即加入并KILL；
6. 后代清理后再次bounded communicate/drain direct pipes。最终要求direct inner已reap、streams complete、`waitpid(-1,WNOHANG)`到 `ECHILD`、adopted live exact 0、zombie exact 0且最终 `/proc` scan无匹配；查询/TERM/KILL/waitpid/drain任一步不可证即hard fail；
7. external exec receipt记录mode、subreaper set/get、pre-spawn child-set、唯一direct-child计数、stable identities、每次fresh observation、exact `transition_observed|first_seen_adopted` 分类、cleanup-eligible workset、signal/waitpid/communicate、evidence verdict、最终 `ECHILD`、live/zombie counts与errors。上述postcondition全绿且无evidence-hard-fail前不得replay SUMMARY或generic primary path。

external exec receipt schema token exact `ista-csr-step9-external-exec-receipt/1.0.0`，采用mode-discriminated strict union。两mode base top-level keys exact `schema,publication_contract,mode,supervisor_path,supervisor_sha256,dependency_loads,argv,env,cwd,primary_receipt_path,primary_receipt_sha256,spawn_state,pid,start_wall_ns,start_monotonic_ns,end_wall_ns,end_monotonic_ns,returncode,stdout_size,stdout_sha256,stdout_base64,stderr_size,stderr_sha256,stderr_base64,streams_complete,subreaper,pre_spawn_child_set,direct_child_count,observations,cleanup,evidence_verdict`；conditional key `spawn_errno`只服从spawn状态，mode-specific keys只服从下列分支，任何跨分支、missing或extra key均拒绝。
`primary_receipt_path`始终为请求的canonical absolute path，调用开始要求该final ENOENT；`primary_receipt_sha256`为nullable SHA。spawn not_attempted/failed时固定null；spawn succeeded但inner未发布primary时仍为null；存在可读取regular final时记录actual raw-bytes SHA，即使primary schema无效也不得写null。external accepted要求该SHA nonnull且primary strict通过，不得用planned SHA、empty-file SHA或伪造SHA占位不存在的receipt。


- `mode="capture"`额外always-exact keys `capture_tool_path,capture_tool_sha256,capture_supervisor_timeout_seconds,capture_outer_timeout_seconds,controller_pair_timeout_seconds,marker_inventory,temp_inventory,failure_inventory`，三个timeout依次exact 2520/2400/120且不得由outer receipt的2640回填。`marker_inventory`为strict object，`temp_inventory`与`failure_inventory`为path排序typed arrays；每个inventory item exact keys `role,path,present,file_type,mode,nlink,size,sha256`，absent时`present=false`且file metadata均null，present时按regular/other分类给出actual no-follow metadata与nullable SHA。capture tool path/SHA必须匹配inner full prefix exact `[ABS_NIX_PYTHON,"-B","-I","-S",capture_tool_path]`且绑定`argv[4]`actual bytes；primary base fields、marker、所有同前缀temp与`.failure.json`须穷尽记录，success要求primary/marker present且SHA交叉一致、temp/failure arrays全为`present=false` absence proof。
- `mode="evidence-tool"`额外always-exact keys `evidence_tool_path,evidence_tool_sha256,evidence_tool_timeout_seconds,expected_outputs`，timeout exact600，tool path/SHA必须匹配inner full prefix exact `[ABS_NIX_PYTHON,"-B","-I","-S",evidence_tool_path]`且绑定`argv[4]`actual bytes；`expected_outputs`保持CLI顺序，每项exact keys `path,present,file_type,mode,nlink,size,sha256`，success均须present、regular/0600/nlink1并与fresh bytes SHA一致。该分支禁止全部capture-only keys，capture分支禁止全部evidence-tool-only keys。
- capture `InventoryItem`即上述八keys，role enum exact `marker|temp|failure_diagnostic`；marker_inventory只允许role=marker，另两array分别只允许temp/failure_diagnostic并按path raw UTF-8 bytes严格升序、无重复。present=false要求file_type/mode/nlink/size/sha256全null；present=true要求file_type enum `regular|other`及mode/nlink/size nonnull，regular要求SHA nonnull，other要求SHA=null。所有key always present。evidence-tool `ExpectedOutput`服从同一presence matrix但array必须保持CLI顺序而非排序；success固定present=true,file_type=regular,mode=0600,nlink=1。
- `spawn_state` enum exact `not_attempted|failed|succeeded`。not_attempted要求pid/returncode及六个stream size/SHA/base64字段和streams_complete均null、direct_child_count=0、spawn_errno absent；failed要求pid/returncode=null、direct_child_count=0、spawn_errno present为ERRNO，streams为canonical empty且streams_complete=true；succeeded要求pid为PID、direct_child_count=1、spawn_errno absent、returncode为actual Popen returncode、streams字段全部nonnull并自洽。subreaper为Subreaper，pre_spawn_child_set为ordered ProcessIdentity array，observations为ordered Observation array，cleanup为Cleanup；setup/query/pre-child-set阻断必须使用not_attempted，但pre-spawn已收养child仍须出现在cleanup.adopted_workset并清零。evidence_verdict enum exact `accepted|rejected`，accepted只允许subreaper exact1、pre-child-set empty、spawn succeeded、returncode0、streams_complete=true及Cleanup accepted。除spawn_errno外全部base/mode keys required；spawn_errno只按上述状态absent/present，禁止null占位。递归应用common scalar bounds和bool-as-int拒绝。
external KAT另覆盖setup/Popen failure及inner未发布primary，并分别拒绝requested final不存在却SHA nonnull、存在可读regular final却SHA null、unknown verdict、green状态配rejected与失败状态配accepted。


共同KAT必须覆盖：两mode的set/get fault与pre-spawn child-set非空在spawn前阻断、pre-spawn exact-empty正例、第二次Popen/helper attempt拒绝；同一stable identity的正常state变化及有证据 `original_parent_pid→supervisor_pid` 的 `transition_observed` 必须接受并记录，starttime漂移、非法ppid漂移必须拒绝。capture mode真实独立session controller→child、evidence-tool mode真实generic inner→child都分别覆盖cooperative TERM与ignore TERM，并对generic supervisor timeout、injected exception、interrupt三种trigger逐一证明adopt、TERM→KILL（按行为需要）、waitpid reap、`ECHILD`、live/zombie exact0。
mode-union schema KAT逐项覆盖mode交换、capture缺任一三个timeout/tool SHA/primary-marker-temp-failure inventory、evidence-tool缺tool SHA/timeout/expected outputs、跨mode key、inventory item缺/多/type/SHA/presence错误、spawn_errno conditional错误；全部strict拒绝、nonzero/no replay，且正例分别证明capture三timeout与完整absence inventory、evidence-tool 600与ordered output hashes。两mode还逐层注入Subreaper状态/return/errno/value矛盾、pre-child-set identity乱序、Observation空scan遗漏或ordinal gap、adoption null matrix、Cleanup action/result/error matrix、ERRNO/PID/U64边界及任意bool-as-int；inventory另覆盖role、path order、presence/metadata/SHA null matrix。全部strict拒绝、nonzero/no replay并清零。
两mode还必须各做两例真实fork-after-then-immediate-exit nominal-leak KAT：inner fork出cooperative child或ignore-TERM child后立即以actual rc0退出并使direct pipes EOF，supervisor首次fresh scan已见child current `ppid == supervisor_pid`。四例都必须分类 `first_seen_adopted`、立即纳入cleanup workset并使evidence hard fail/nonzero/no-replay；identity复验后分别TERM或TERM→KILL、waitpid到 `ECHILD`，最终live/zombie exact0。

本轮只写该设计，不 materialize tools，也不填写其 future SHA。

## 5. Controller capture 与 seven-argument context

### 5.1 Bytes-mode inner capture 与 external supervisor

`step9_capture.py` 的 CLI 冻结为：

~~~text
step9_capture.py
  --receipt ABS_CAPTURE_RECEIPT
  --outer-timeout-seconds 2400
  -- CONTROLLER_ARGV...
~~~

`step9_capture_supervisor.py` 的 CLI 冻结为：

~~~text
step9_capture_supervisor.py
  --mode capture
  --receipt ABS_CAPTURE_EXEC_RECEIPT
  --capture-receipt ABS_CAPTURE_RECEIPT
  --supervisor-timeout-seconds 2520
  -- CAPTURE_ARGV...
~~~

三个 timeout 是不同层级且不得互相回填：

- `capture_supervisor_timeout_seconds` exact 2520，只约束external supervisor等待inner capture；
- `capture_outer_timeout_seconds` exact 2400，由 wrapper 自己执行并记录；
- `controller_pair_timeout_seconds` exact 120，只来自 controller argv 的 `--timeout-seconds 120`，适用于18个串行 pair 中的每一 pair；
- primary与exec receipts必须把三个数值作为独立字段，并把 actual supervisor CLI、inner capture CLI 与 controller argv 分开记录、复验；禁止只保存混合 argv 或跨层回填timeout。

supervisor按§4.4设置/复验subreaper后以bytes-mode执行唯一inner capture，actual wait/reap并证明全部adopted descendants清零后才用共同publisher写external exec receipt；该receipt记录capture tool SHA、actual PID/argv/cwd/env、三个timeout、returncode、完整stdout/stderr size/SHA/base64，以及primary/marker/temp/failure inventory与bytes SHA。inner `Popen` 自身失败时PID exact null、exception与空streams仍形成exec receipt；supervisor不得用inner自报returncode替代actual `Popen.returncode`。

§4.4共同合同不改变inner capture启动controller时既有 `start_new_session=True`、PID/PGID/SID和controller-side group cleanup合同；supervisor subreaper是capture与generic inner意外消失后的共同第二层证明。

exec receipt只有在inner实际reap后才可能发布；success必须actual returncode 0、inner stdout exact summary absolute path+LF、stderr empty、primary/marker交叉SHA全绿且无temp/failure。supervisor只在这些条件满足后原样replay该stdout并返回0；否则不输出可消费SUMMARY并返回nonzero。supervisor自身的raw wait status/normalized rc由outer driver actual wait/reap并写outer command receipt；context同时复验inner exec receipt与capture outer receipt，不允许任何文件自报上层退出码。

inner capture尝试 `subprocess.Popen(..., stdin=DEVNULL, stdout=PIPE, stderr=PIPE, text=False, start_new_session=True)` 启动 controller。若 `Popen` 自身抛错，必须在primary receipt记录 `spawn_state="failed"`、PID/PGID/SID exact null、异常、三个独立timeout与空/partial streams，completion marker absent并nonzero退出；不得因没有PID而不留machine-readable failure。启动成功后receipt的 `controller_pid` 必须取actual `Popen.pid`，不得从summary回填。controller argv使用absolute probes、real/baseline manifests、fresh exclusive unpredictable nonce且initial ENOENT的build-tree run-root、`--repeats 6 --timeout-seconds 120`；新root不得等于、位于、包含、symlink/hardlink/inode alias或跨引§4.2旧gVLAN run-root。立即取得actual PID/PGID/SID，要求 `controller_pgid == controller_pid` 且 `controller_sid == controller_pid`。

若PGID/SID查询异常或任一值不匹配，不得进入正常measurement wait，也不得向未经验证的PGID发信号；但direct `Popen` 在所有分支都必须drain/wait/reap。该fallback先对仍live的direct controller执行 `terminate()` 并bounded `communicate(timeout=10)`，超时则只对同一direct child执行 `kill()` 再bounded `communicate(timeout=10)`；已退出仍调用bounded `communicate`回收并drain两pipe。primary receipt写 `complete=false`、identity query/result、direct TERM/KILL、最终returncode、最终/partial streams与 `group_cleanup_verified=false`；marker absent、nonzero、整轮hard fail。不得跳过direct-child reap，也不得声称该fallback清除了无法验证的grandchildren。

只有PID/PGID/SID验证成功才进入正常路径并首次调用 `communicate(timeout=2400)`。如果该调用 `TimeoutExpired`，异常携带的bytes只作partial诊断，不手工拼接；对PGID发TERM后必须再次 `communicate(timeout=10)`，仍timeout才对PGID发KILL并第三次 `communicate(timeout=10)`。最终一次成功返回的完整bytes才是authoritative streams；若KILL后仍不能bounded communicate/reap，则记录最新partial bytes、`streams_complete=false`并hard fail。

对已验证的PGID，无论异常发生时leader仍live、已经退出，还是正常 `communicate` 已返回，都必须用stdlib解析 `/proc/[0-9]*/stat` 的state/pgrp/session字段并结合 `killpg(pgid, 0)` 检查整组：

1. timeout/wrapper exception/interrupt，或leader已退出但PGID仍有成员时，对冻结PGID发 `SIGTERM`，bounded communicate/reap direct child并等待最多10秒；
2. group仍有成员时对同一PGID发 `SIGKILL`，再bounded communicate/reap direct child并等待最多10秒；
3. 最终要求controller已reap且该session/PGID无非消失成员；不得只检查leader PID，也不得把zombie/查询错误当clean；
4. durable发布primary `complete=false` failure receipt，记录trigger、PID/PGID/SID、每次communicate及partial/final streams、TERM/KILL action/result、controller returncode、最终group member清单与cleanup errors；marker absent、nonzero且不重放SUMMARY。

正常成功也必须在验证controller returncode/streams/summary后再次证明PGID空集，receipt记录 `cleanup_action="none"` 与空member清单；若leader exit 0但有live grandchild，仍走上述PGID TERM→KILL、整轮hard fail。若窗口后仍有成员、direct child未reap、streams不完整或cleanup无法验证，都是独立hard failure。

wrapper 等待并清理后必须同时验证：

- spawn/identity/outer timeout均未失败，direct controller已reap，PGID/session交叉检查为空且cleanup action exact `none`；
- returncode 0，两个 stream 是 bytes；
- stderr exact `b""`；
- stdout exact `os.fsencode(absolute_summary_path) + b"\n"`，只有一行、无 NUL/额外空白；
- summary 是新 controller root 内的 non-symlink regular final，basename exact `real-differential-controller-result.json`；
- summary `controller_pid` equals actual `Popen.pid`。

验证全绿后执行exact completion protocol：

1. 先以共同publisher durable发布primary capture receipt，字段 `capture_state="captured_pending_delivery"`、`complete=false`，记录planned stdout bytes size/SHA/base64；此文件单独永远不能被context/reducer接受；
2. 用 `os.write(sys.stdout.fileno(), ...)` short-write loop原样写完summary path+LF；任一BrokenPipe/中断/short-write failure都nonzero、marker absent；派生 `ABS_CAPTURE_RECEIPT + ".failure.json"` 也必须以§4.2共同publisher发布，禁止direct final write。diagnostic schema token exact `ista-csr-step9-capture-failure-diagnostic/1.0.0`，top-level keys exact `schema,publication_contract,complete,capture_receipt_path,capture_receipt_sha256,stage,error_type,error_errno,error_message_sha256,temp_state,marker_state,rollback`；全部key required、不得extra，publication token exact、complete=false。四个error字段服从InternalError去掉ordinal后的同一enum/type/bounds。`DiagnosticTempState` exact `state,path,temp_absent,dev,ino,uid,mode,nlink,size,sha256`，state enum `not_created|partial|ready|linked|unlinked|indeterminate`；not_created要求path=null、temp_absent=true，其余path为actual canonical absolute temp path；partial/ready/linked要求temp_absent=false及全部metadata nonnull，unlinked要求temp_absent=true且metadata全null，indeterminate要求temp_absent=null且metadata全null；ready固定regular/0600/nlink1，linked固定regular/0600/nlink2。`DiagnosticMarkerState` exact `state,path,marker_absent,dev,ino,uid,mode,nlink,size,sha256`，state enum `not_attempted|absent|linked|published|rolled_back|indeterminate`；path始终为派生marker canonical absolute path；not_attempted/absent/rolled_back要求marker_absent=true且metadata全null，linked/published要求false及metadata全nonnull，其中linked须与temp同dev/ino且nlink2、published须regular/0600/nlink1，indeterminate要求marker_absent=null且metadata全null。`DiagnosticRollback` exact `state,final_unlink_attempted,final_unlinked,temp_unlink_attempted,temp_unlinked,dir_fsync_count,final_absent,temp_absent,poisoned,errors`，state enum `not_required|succeeded|failed|indeterminate`，attempt/poison字段为boolean，unlink结果及两absence proof为nullable boolean，dir_fsync_count integer `0..2`，errors为ordered InternalError array；未attempt的对应result必须null，not_required/succeeded要求final_absent=temp_absent=true、poisoned=false，failed/indeterminate要求poisoned=true，任何不可证明结果必须null。所有metadata integer遵守common bounds、nested recursive closed并拒绝bool-as-int。diagnostic publisher自身失败时只允许own temp/poison与inner actual nonzero，不得留下partial final或把diagnostic失败当成功；
3. stdout write全部被kernel接受后，才以§4.2共同publisher transactional发布 `ABS_CAPTURE_RECEIPT + ".complete.json"`；必须执行same-dir exclusive temp、short-write loop、file fsync/close、link前 `O_RDONLY|O_NOFOLLOW` reopen+regular/current-uid/0600/nlink1+bytes/SHA exact、no-overwrite hardlink、同inode/nlink2、两次dir fsync、temp unlink/ENOENT与final nlink1全部步骤，不得保留bespoke捷径。marker schema token exact `ista-csr-step9-capture-complete-marker/1.0.0`，top-level keys exact `schema,publication_contract,complete,capture_receipt_path,capture_receipt_sha256,delivered_stdout_size,delivered_stdout_sha256,summary_path,summary_sha256`，`publication_contract="hardlink-no-overwrite-v1",complete=true`且不得extra；
4. §4.2 marker publisher任一步失败都使inner nonzero并执行其own-inode rollback/poison合同；若temp已unlink则记录`temp_state.temp_absent=true`，不得声称仍保留temp。所有失败另尝试以同一共同publisher发布durable `.failure.json`；final/temp rollback、任一dir-fsync或diagnostic publisher失败均记录。marker残留且无visible poison的compound fault由external supervisor actual nonzero兜底，故context必须要求exec receipt rc0，绝不凭marker单独接受；
5. caller只执行并等待outer driver returncode 0，再把inner external exec receipt与capture outer receipt一并传给context；stdout先于marker或任一observer receipt可见都不授权提前消费。KAT逐点覆盖marker与failure diagnostic各自的§4.2 temp create/short-write/fsync/close/reopen/read/link/nlink/dir-fsync/unlink步骤，另覆盖schema/publication token mismatch、rollback fault与 `second-dir-fsync→temp absent→final-unlink fault→diagnostic publisher fault` 组合；正常marker额外hardlink使nlink2时context必须拒绝。每例都由marker absent、visible poison或任一observer actual nonzero至少一项使context拒绝。diagnostic KAT逐一覆盖TempState/MarkerState/Rollback的nested missing/extra/type、unknown state、path/null/presence/metadata矛盾、ready/linked/published inode-mode-nlink错误、rollback attempt/result/absence/poison matrix、InternalError enum/errno/hash/order及全部integer bool-as-int；任一例都不得形成可接受capture evidence。

这样primary receipt先于inner stdout durable，但primary或marker都不是独立complete evidence；shell 的 `SUMMARY` 只从已wait成功的outer driver replay stdout取得，raw controller streams以primary receipt为准，actual inner wrapper exit/stdout/stderr以内层exec receipt为准，actual supervisor wait status/streams以outer receipt为准。不得用 `check_output(text=True)`、日志抄录、任一child自报returncode或 summary 自报 PID 代替。

capture primary schema token exact `ista-csr-step9-capture-primary-receipt/1.0.0`；top-level keys exact `schema,publication_contract,capture_state,complete,tool_path,tool_sha256,dependency_loads,argv,env,cwd,spawn_state,controller_pid,controller_pgid,controller_sid,controller_argv,controller_cwd,controller_env,capture_supervisor_timeout_seconds,capture_outer_timeout_seconds,controller_pair_timeout_seconds,start_wall_ns,start_monotonic_ns,end_wall_ns,end_monotonic_ns,controller_returncode,stdout_size,stdout_sha256,stdout_base64,stderr_size,stderr_sha256,stderr_base64,streams_complete,identity,group_cleanup,summary_path,summary_sha256,planned_stdout_size,planned_stdout_sha256,internal_errors`，conditional key只有`spawn_errno`。capture_state enum exact `failed|captured_pending_delivery`，complete固定false。

`ControllerIdentity` exact `status,process,pgid,sid,error`；status enum `not_attempted|failed|verified`。not_attempted要求process/pgid/sid/error全null；failed允许process、pgid、sid按actual query进度为ProcessIdentity/PID/null但要求error为InternalError；verified要求process为ProcessIdentity、pgid=sid=process.pid且error=null。top-level controller_pid/pgid/sid必须逐值等于该record的actual对应值；spawn未成功时identity只能not_attempted。

`GroupCleanup` exact `status,cleanup_action,controller_reaped,streams_complete,signals,communicates,initial_scan_state,initial_members,final_scan_state,final_members,killpg_state,group_cleanup_verified,errors`。status enum `not_attempted|verified_clean|verified_cleaned|failed`；cleanup_action enum `not_attempted|none|direct_term|direct_term_kill|group_term|group_term_kill`；scan state enum `not_attempted|failed|succeeded`，killpg_state enum `not_attempted|alive|esrch|failed`；member arrays为ordered ProcessIdentity，signals/communicates复用上述closed action records，三个reap/stream/verified字段均为JSON boolean。spawn未成功固定status/action not_attempted、两scan not_attempted、arrays empty、三个boolean false、killpg not_attempted。verified_clean只允许action=none、controller_reaped/streams_complete/group_cleanup_verified=true、final scan succeeded且empty、killpg=esrch、errors=[]；verified_cleaned同样证明最终清零但表示曾因timeout/exception/leak执行cleanup，永不构成capture success；failed固定group_cleanup_verified=false。

internal_errors为ordered InternalError array。spawn_state=not_attempted要求四个controller id/rc均null且spawn_errno absent；failed要求四者null且spawn_errno为ERRNO；succeeded要求controller_pid为PID、spawn_errno absent，controller_returncode仅在group_cleanup.controller_reaped=true时为actual returncode，否则null。未spawn时两个raw stream固定canonical empty；spawn后size/SHA/base64记录actual final或partial bytes。summary_path/summary_sha256必须同null或同nonnull；planned_stdout_size/planned_stdout_sha256只在capture_state=captured_pending_delivery时nonnull。该成功状态还要求identity verified、GroupCleanup verified_clean、returncode0、streams_complete、stderr empty、valid summary、internal_errors=[]；其他组合只允许capture_state=failed且至少一条InternalError。全部base keys required，只有spawn_errno conditional absent，所有nested recursive closed并拒绝bool-as-int。全文schema/KAT只允许上述统一field name，禁止controller-specific alias。

capture primary schema KAT逐层覆盖ControllerIdentity、GroupCleanup、SignalAction、CommunicateAction、ProcessIdentity及InternalError的missing/extra/type/bounds/enum/order/bool-as-int，spawn/identity/reap/returncode null matrix、top-level与identity PID/PGID/SID不等、member重复/乱序、verified_clean夹带action/error/member、verified_cleaned误作success、summary/planned-stdout pair半null，以及failed无InternalError；全部nonzero、marker absent、不得被context消费。

### 5.2 Frozen `step9_context.py`

该 tool 同时提供唯一keyword-only import API和两个frozen/slotted dataclass；alias、annotation、field order/name/type、parameter order/name/type与return annotation exact如下，调用者不得用位置参数、alias或隐式default：

~~~python
ProbePair = tuple[Path, Path]
LaneExecution = tuple[int, tuple[str, ...]]
PairExecution = tuple[LaneExecution, LaneExecution]
ControllerContext = tuple[PairSlot, PairExecution]

@dataclass(frozen=True, slots=True)
class PidCapabilities:
    controller_pid: int
    controller_pid_source: str
    controller_pid_independent_os_observer: bool
    lane_pid_record_count: int
    lane_pid_source: str
    lane_pid_independent_os_observer: bool
    lane_pid_positive_required: bool
    pair_distinct_required: bool
    global_uniqueness_required: bool

@dataclass(frozen=True, slots=True)
class StrictContext:
    raw_summary: dict[str, Any]
    bundle: ManifestBundle
    repeat_count: int
    controller_pid: int
    controller_nonce: str
    probes: ProbePair
    contexts: tuple[ControllerContext, ...]
    inventory_sha256: str
    pid_capabilities: PidCapabilities

def build_strict_context(
    *,
    manifest_path: str,
    baseline_manifest_path: str,
    summary_path: str,
    capture_receipt_path: str,
    capture_exec_receipt_path: str,
    capture_outer_receipt_path: str,
    oracle_probe_path: str,
    reference_probe_path: str,
) -> StrictContext: ...
~~~

`StrictContext`的custom repo-local `ManifestBundle`/`PairSlot`只从本函数已验证的captured bytes构造；`contexts` cardinality exact18且每个`PairExecution`按oracle/reference顺序，argv是immutable tuple。CLI与reducer/recheck必须按上述八个named args调用同一API，CLI exact为：

~~~text
step9_context.py
  --manifest ABS_REAL_MANIFEST
  --baseline-manifest ABS_BASELINE_MANIFEST
  --summary ABS_SUMMARY
  --capture-receipt ABS_CAPTURE_RECEIPT
  --capture-exec-receipt ABS_CAPTURE_EXEC_RECEIPT
  --capture-outer-receipt ABS_CAPTURE_OUTER_RECEIPT
  --oracle-probe ABS_ORACLE
  --reference-probe ABS_REFERENCE
  --output ABS_CONTEXT_RECEIPT
~~~

可信来源与ownership：

- 三个capture receipt参数全部必需且不得派生或互换：分别要求canonical absolute path、无`.`/`..`/symlink component、dirfd-relative `O_RDONLY|O_NOFOLLOW`、regular/current uid/0600/nlink1、fresh bytes SHA，并strict匹配schema token `ista-csr-step9-capture-primary-receipt/1.0.0`、`ista-csr-step9-external-exec-receipt/1.0.0`、`ista-csr-step9-outer-command-receipt/1.0.0`与共同publication token；missing、relative、alias、path/schema/hash/type/extra-key mismatch一律fail；
- controller PID、controller argv/cwd/env 来自 primary capture receipt；inner capture PID/argv/cwd/env/actual returncode/raw streams来自inner external exec receipt；supervisor PID/argv/cwd/env/fork+exec states/raw wait status/normalized rc/raw streams来自capture outer receipt。context要求outer fork/exec exact succeeded、两errno key absent、raw wait规范化exact 0；outer的`supervisor_exec_receipt_path/SHA`必须exact绑定inner exec receipt，outer argv中的supervisor `--receipt`也指向同一路径；inner exec的mode/primary/marker/summary必须与outer supervisor argv双向一致；outer stdout必须exact inner exec所replay summary path+LF、stderr empty，stream size/SHA/base64交叉一致。context从primary path派生 `.complete.json` marker并扫描同前缀temp/failure poison，strict验证五artifact schema/state/path/SHA、summary/delivery bytes与两层observer inventory；marker必须token exact `ista-csr-step9-capture-complete-marker/1.0.0`、publication contract exact、no-follow regular、非symlink、0600、nlink1，missing/extra/mismatch、额外hardlink、temp/failure存在或任一observer证明非零均fail；
- case order、repeat count、inputs、tolerances 来自 canonical `load_manifest`；
- executable tuple 来自 capture argv 中两 absolute probe args，再 realpath/hash 对照 CLI；
- controller nonce 必须在 summary 与 root basename `real-differential-PID-NONCE` 双重一致；
- directory/record bytes用于证明published layout，不得把summary case order当manifest order。

context 必须以 dirfd/no-follow inventory exact 重建 18 slots：

- root exact 18 `slot-ORD-case-rREPEAT` directories，顺序为 `bundle.cases` 外层、repeat 0..5 内层，另有一份 summary final；无 extra/temp；
- 每 slot exact `oracle`、`reference` 两 directories；
- 每 lane entry set exact singleton `{ROLE-result.json}`，共36份final；regular、0600、无symlink/hardlink anomaly，`sta/`、temp或任意extra均hard fail；consumer不递归绑定或接受transient scratch；
- final bytes strict JSON；summary 中对应 lane record必须与final record exact相等；
- 以 final record nonce 构造 frozen `LaneSlot`/temporary basename，以 manifest/slot/probe 独立重建 expected argv，绝不从 `argv_receipt.argv` 复制；
- contexts exact 18 entries，每项 `(PairSlot, ((oracle_pid, oracle_argv),(reference_pid, reference_argv)))`。

PID能力边界必须写进 context receipt：controller PID 有 wrapper `Popen.pid` 独立证据；child PID 只有 published lane record/controller in-memory receipt的交叉一致性，没有第二个OS observer。context可要求positive PID和pair内不同，但不得要求36 PID全局唯一（OS可复用），也不得声称独立证明child PID。argv则由manifest/layout/probe独立重建。

`PidCapabilities`与其JSON projection都须exact九项和值：`controller_pid`等于actual capture PID，`controller_pid_source="capture-wrapper-actual-popen-pid"`，`controller_pid_independent_os_observer=true`，`lane_pid_record_count=36`，`lane_pid_source="lane-final-controller-in-memory-receipt-cross-check"`，`lane_pid_independent_os_observer=false`，`lane_pid_positive_required=true`，`pair_distinct_required=true`，`global_uniqueness_required=false`；不得extra/optional或用string冒充bool/int。

context primary receipt schema token exact `ista-csr-step9-context-receipt/1.0.0`；top-level keys exact `schema,publication_contract,tool_path,tool_sha256,dependency_loads,argv,env,cwd,manifest_path,manifest_sha256,baseline_manifest_path,baseline_manifest_sha256,summary_path,summary_sha256,capture_receipt_path,capture_receipt_sha256,capture_exec_receipt_path,capture_exec_receipt_sha256,capture_outer_receipt_path,capture_outer_receipt_sha256,oracle_probe_path,oracle_probe_sha256,reference_probe_path,reference_probe_sha256,marker_path,marker_sha256,inventory_sha256,slot_count,lane_count,validator_call,pid_capabilities,planned_stdout_size,planned_stdout_sha256,internal_state,complete`，不得extra/optional key；path/schema/token/hash/state为string，SHA为64位lower-hex，argv为string array，env/pid_capabilities为strict object，slot/lane/size为nonnegative integer，`validator_call`服从§5.3 exact七项projection，`internal_state="pending"`、`complete=false`。argv必须与上列exact CLI flag order/value相等。

context KAT覆盖缺任一required flag、三receipt互换/alias/relative/symlink/hardlink、outer schema/hash/base64/raw-wait normalization、preflight/fork/exec状态与errno conditional-presence、receipt-path/SHA/outer argv双向绑定、stream mismatch与supervisor early exit，以及import API positional/alias/default/signature drift；均nonzero且不发布可消费context primary。

### 5.3 Seven-argument strict call

context、reducer、recheck各自重新读取summary与36 finals，并调用exact七参合同：

~~~python
validate_controller_summary(
    raw_summary,
    bundle,
    6,
    capture.controller_pid,
    controller_nonce,
    (oracle_probe, reference_probe),
    contexts,
)
~~~

任何实现若不是§5.3 exact七参调用，立即FAIL；不得保留legacy three-argument call site。`validator_call`是该actual call的JSON-safe exact七项projection：array length exact7；各item exact keys `position,name,projection_schema,value_sha256,value`，position依次0..6、name依次`raw_summary,bundle,repeat_count,controller_pid,controller_nonce,probes,contexts`、projection token exact `ista-csr-step9-validator-arg-projection/1.0.0`，`value_sha256=sha256(CANON(value))`，不得extra/optional。

七个`value`的strict schema依次为：(0) exact keys `summary_path,summary_sha256,summary_schema,case_order,repeat_count,controller_pid,controller_nonce,lane_records_sha256`；(1) exact keys `manifest_path,manifest_sha256,manifest_schema,case_order,repeat_count,inputs_sha256,tolerances_sha256`；(2) integer exact6；(3) positive integer且等于actual capture controller PID；(4) nonempty string；(5) exact两项array，oracle/reference顺序，每项exact keys `role,invocation_path,realpath,sha256`；(6) exact18项array，每项exact keys `ordinal,descriptor,repeat_index,directory,lanes`，`descriptor` exact keys `name,input_case_sha256,descriptor_manifest_path,descriptor_manifest_sha256`，`lanes` exact两项oracle/reference，每项exact keys `role,run_nonce,directory,temporary_result,final_result,pid,argv`。ordinal exact0..17、repeat index exact0..5；directory/temp/final来自actual frozen `PairSlot`/`LaneSlot`且都是canonical absolute path，run_nonce来自validated final record，PID positive，argv string array并与传给validator的immutable tuple逐项相等；descriptor name/order/input/manifest hashes与完整`ManifestBundle`交叉一致。projection不得包含不存在的`slot_nonce`或用summary-derived简化case代替descriptor；全部nested object禁止extra。

projection只用于receipt和三工具byte-exact交叉复验，不替代Python actual args；context、reducer、recheck都须由本次fresh `StrictContext`在调用前构造projection并在调用后记录同一CANON/SHA。KAT覆盖array length/order、position/name/token、missing/extra/type、nested missing/extra、hash mismatch、PairSlot/LaneSlot directory/temp/final交换、descriptor/input/manifest SHA、case/repeat/lane cardinality及PID/run_nonce/argv来源漂移，并用`inspect.signature`、`dataclasses.fields`和runtime values复验API/dataclass annotations与nine-field capabilities；任何一项拒绝且不得发布可消费primary。

`step9_context.py` receipt 另记录18/36 cardinality、inventory SHA和上述 PID/argv capability labels。

## 6. Reducer 与 independent recheck

### 6.1 Primary reducer

`step9_reduce.py` exact CLI为：

~~~text
step9_reduce.py
  --manifest ABS_REAL_MANIFEST
  --baseline-manifest ABS_BASELINE_MANIFEST
  --summary ABS_SUMMARY
  --capture-receipt ABS_CAPTURE_RECEIPT
  --capture-exec-receipt ABS_CAPTURE_EXEC_RECEIPT
  --capture-outer-receipt ABS_CAPTURE_OUTER_RECEIPT
  --oracle-probe ABS_ORACLE
  --reference-probe ABS_REFERENCE
  --context-receipt ABS_CONTEXT_RECEIPT
  --context-exec-receipt ABS_CONTEXT_EXEC_RECEIPT
  --context-outer-receipt ABS_CONTEXT_OUTER_RECEIPT
  --output-dir ABS_REDUCER_OUTPUT_DIR
  --receipt ABS_REDUCER_PRIMARY_RECEIPT
~~~

所有flag required、只出现一次且order/value exact；所有path均按§5.2 canonical no-follow合同验证。reducer strict验证capture/context两组三层receipt；context outer必须fork/exec/inner exact0、指向并hash绑定context exec，stdout exact context primary path+LF、stderr empty，context exec再绑定context primary及capture三件。它仍fresh调用 `build_strict_context`并执行§5.3七参validator；只有两条证据链与fresh context同时成功后才从ready reference observation生成：

- `step9-raw-timing-v1.json`：18 rows，bundle case order × repeat 0..5；
- `step9-raw-storage-v1.json`：18 rows，同一order/role；
- `step9-aggregate-v1.json`：9 rows，bundle case order × 三phase；
- `step9-reducer-receipt-v1.json`：primary schema token exact `ista-csr-step9-reducer-receipt/1.0.0`；top-level keys exact `schema,publication_contract,tool_path,tool_sha256,dependency_loads,argv,env,cwd,manifest_path,manifest_sha256,baseline_manifest_path,baseline_manifest_sha256,summary_path,summary_sha256,capture_receipt_path,capture_receipt_sha256,capture_exec_receipt_path,capture_exec_receipt_sha256,capture_outer_receipt_path,capture_outer_receipt_sha256,context_receipt_path,context_receipt_sha256,context_exec_receipt_path,context_exec_receipt_sha256,context_outer_receipt_path,context_outer_receipt_sha256,oracle_probe_path,oracle_probe_sha256,reference_probe_path,reference_probe_sha256,inventory_sha256,validator_call,outputs,planned_stdout_size,planned_stdout_sha256,internal_state,complete`，不得extra/optional key。path/token/state为string、SHA为lower-hex、argv为string array、env为strict object、size为nonnegative integer、`validator_call`为exact七参typed array；`outputs`是exact三项typed array，每项exact keys `path,schema,file_sha256,row_count,rows_sha256,publication_contract`且按timing/storage/aggregate顺序；`internal_state="pending"`,`complete=false`。只有其对应inner exec与outer command receipts按§4 strict全绿才complete。

三output top-level exact keys为 `schema,summary_sha256,row_count,rows_sha256,rows`，不得有extra。schema token依次 exact `ista-csr-step9-raw-timing/1.0.0`、`ista-csr-step9-raw-storage/1.0.0`、`ista-csr-step9-aggregate/1.0.0`。定义：

~~~python
def CANON(value):
    return (
        json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )
~~~

每个output bytes exact `CANON(top_level)`；`rows_sha256 = sha256(CANON(rows)).hexdigest()`，`row_count == len(rows)`。工具与reviewer都必须用此preimage，不得hash整文件、无LF array或显示文本。

timing row exact keys为 `case,repeat_index,role,conversion_export_ms,reference_ms,prevalidation_scatter_preparation_ms`。`role` 是sample role：repeat 0 exact `warmup`，repeat 1..5 exact `measured`；source lane隐含且固定为reference，不得把role写成lane。

storage row exact keys为 `case,repeat_index,role,observation_schema_version,nodes,arcs,levels,buffers,modeled_host_bytes,capacity,support`；role映射同上。`buffers` exact九键 `node_keys,arc_keys,out_row_offsets,out_arc_ids,in_row_offsets,in_arc_ids,level_offsets,level_nodes,node_to_level`，每项exact `{logical_size,capacity}`；`modeled_host_bytes` exact `{logical,capacity}`；`capacity` exact `{last_action,event_count}`；`support` exact `{reference_supported,unsupported_reasons}`，均从同一ready observation原值复制。

CSR公式独立检查：

~~~text
node_keys=node; arc_keys=arc
out_row_offsets=node+1; out_arc_ids=arc
in_row_offsets=node+1; in_arc_ids=arc
level_offsets=level+1; level_nodes=node; node_to_level=node
~~~

另要求capacity>=logical、host capacity>=logical、supported true/reasons empty、ready/released exact、timing finite/nonnegative。任一不符时零aggregate、primary保持pending且无可接受primary+external-exec evidence。

### 6.2 Aggregate exact算法

每个 case/phase 只取repeat 1..5，按binary64 numeric升序得到 `xs`：

~~~text
n = 5
median = xs[2]
nearest-rank p95 = xs[4]
~~~

repeat 0只标warmup。禁止删outlier、补单次、跨run拼接、插值quantile、mean/stddev、phase total、ratio或speedup。

aggregate row exact keys为 `case,phase,unit,n,measured_repeat_indices,median_ms,p95_ms`。phase token按manifest case order内 exact `conversion_export`、`reference`、`prevalidation_scatter_preparation`；`unit="ms"`、`n=5`、`measured_repeat_indices=[1,2,3,4,5]`、`median_ms=xs[2]`、`p95_ms=xs[4]`。

timing binary64从strict JSON model取得后不得Decimal转换、预舍入或字符串格式化；sorting、row comparison、`CANON(rows)`与最终文件均使用同一raw binary64值。canonical publisher中的newline literal必须是单个byte expression `+ b"\n"`；禁止生成broken两行 `b"` / `"`，工具freeze review必须syntax-compile并做known-answer byte test。

### 6.3 Independent recheck

`step9_recheck.py` 可 import frozen `step9_context`，绝不import reducer、reducer helper或reducer output作为生成源。exact CLI为：

~~~text
step9_recheck.py
  --manifest ABS_REAL_MANIFEST
  --baseline-manifest ABS_BASELINE_MANIFEST
  --summary ABS_SUMMARY
  --capture-receipt ABS_CAPTURE_RECEIPT
  --capture-exec-receipt ABS_CAPTURE_EXEC_RECEIPT
  --capture-outer-receipt ABS_CAPTURE_OUTER_RECEIPT
  --oracle-probe ABS_ORACLE
  --reference-probe ABS_REFERENCE
  --context-receipt ABS_CONTEXT_RECEIPT
  --context-exec-receipt ABS_CONTEXT_EXEC_RECEIPT
  --context-outer-receipt ABS_CONTEXT_OUTER_RECEIPT
  --timing ABS_TIMING
  --storage ABS_STORAGE
  --aggregate ABS_AGGREGATE
  --reducer-receipt ABS_REDUCER_PRIMARY_RECEIPT
  --reducer-exec-receipt ABS_REDUCER_EXEC_RECEIPT
  --reducer-outer-receipt ABS_REDUCER_OUTER_RECEIPT
  --receipt ABS_RECHECK_PRIMARY_RECEIPT
~~~

所有flag required、只出现一次且order/value exact；所有path按§5.2 canonical no-follow合同验证。recheck strict消费capture/context/reducer三组三层receipt，逐层要求fork/exec/inner rc0、receipt path/SHA与observer argv双向绑定、stdout primary或summary path+LF、stderr empty；三output只能作为待独立比较对象，不得作为生成源。

recheck 必须：

1. fresh调用 `build_strict_context`，重新inventory 18 slots/36 finals；
2. fresh执行七参 `validate_controller_summary`；
3. 从strict summary independently生成完整18 timing rows、18 storage rows、9 aggregate rows；
4. case order只取 `bundle.cases`，每case要求repeat indices exact 0..5；aggregate只取1..5并用 `xs[2]/xs[4]`；
5. 对三组rows做canonical exact array comparison、row_count/rows SHA/file SHA comparison；

6. 以共同publisher写 `step9-recheck-receipt-v1.json`。
recheck primary schema token exact `ista-csr-step9-recheck-receipt/1.0.0`；top-level keys exact `schema,publication_contract,tool_path,tool_sha256,dependency_loads,argv,env,cwd,manifest_path,manifest_sha256,baseline_manifest_path,baseline_manifest_sha256,summary_path,summary_sha256,capture_receipt_path,capture_receipt_sha256,capture_exec_receipt_path,capture_exec_receipt_sha256,capture_outer_receipt_path,capture_outer_receipt_sha256,context_receipt_path,context_receipt_sha256,context_exec_receipt_path,context_exec_receipt_sha256,context_outer_receipt_path,context_outer_receipt_sha256,reducer_receipt_path,reducer_receipt_sha256,reducer_exec_receipt_path,reducer_exec_receipt_sha256,reducer_outer_receipt_path,reducer_outer_receipt_sha256,oracle_probe_path,oracle_probe_sha256,reference_probe_path,reference_probe_sha256,inputs,recomputed_rows_sha256,inventory_sha256,validator_call,planned_stdout_size,planned_stdout_sha256,internal_state,complete`，不得extra/optional key。共同scalar/array/object类型规则同reducer；`inputs`是timing/storage/aggregate顺序exact三项strict object `path,schema,file_sha256,row_count,rows_sha256`，`recomputed_rows_sha256`是同顺序exact三项lower-hex array；`internal_state="pending"`,`complete=false`。recheck自己的future exec/outer receipt不得被primary自证，须由caller/final reviewer另行strict验证。

只重算median而不重建storage、复用reducer Python symbol、按summary自带case order或只比较显示数字，均视为NOT APPROVE。

## 7. 三相 provenance

### 7.1 三份manifest与不变量

`step9_provenance.py` exact CLI为：

~~~text
step9_provenance.py attest-prior
  --attestation-input ABS_APPROVED_ATTESTATION_INPUT
  --step8-plan ABS_STEP8_PLAN
  --cleanup-receipt ABS_STEP8_CLEANUP_RECEIPT
  --plan-review-repair-intent ABS_PLAN_REVIEW_REPAIR_INTENT
  --plan-review-repair-receipt ABS_PLAN_REVIEW_REPAIR_RECEIPT
  --report-source /home/shigure/code/ecc/docs/incregpusta/stage2-report.md
  --report-preimage-output ABS_STAGE2_REPORT_PREIMAGE
  --receipt ABS_PRIOR_ATTESTATION_PRIMARY

step9_provenance.py phase
  --phase pre|post|final
  --manifest ABS_PHASE_MANIFEST
  --receipt ABS_PHASE_PRIMARY_RECEIPT
  [--prior-attestation ABS_PRIOR_ATTESTATION
   --prior-attestation-exec-receipt ABS_PRIOR_ATTESTATION_EXEC_RECEIPT
   --prior-attestation-outer-receipt ABS_PRIOR_ATTESTATION_OUTER_RECEIPT
   --prior-attestation-review-a ABS_PRIOR_ATTESTATION_REVIEW_A
   --prior-attestation-review-b ABS_PRIOR_ATTESTATION_REVIEW_B]
  [--pre-manifest ABS_PRE_MANIFEST]
  [--post-manifest ABS_POST_MANIFEST]
  [--report-transition-receipt ABS_REPORT_TRANSITION_RECEIPT
   --report-transition-exec-receipt ABS_REPORT_TRANSITION_EXEC_RECEIPT
   --report-transition-outer-receipt ABS_REPORT_TRANSITION_OUTER_RECEIPT]

step9_provenance.py publish-report
  --post-manifest ABS_POST_MANIFEST
  --post-primary-receipt ABS_POST_PRIMARY_RECEIPT
  --post-exec-receipt ABS_POST_EXEC_RECEIPT
  --post-outer-receipt ABS_POST_OUTER_RECEIPT
  --post-envelope ABS_POST_ENVELOPE
  --report-source ABS_APPROVED_REPORT_SOURCE
  --report-source-sha256 SHA256
  --report-target /home/shigure/code/ecc/docs/incregpusta/stage2-report.md
  --report-lock ABS_REPORT_COLLAB_LOCK
  --before-copy ABS_BEFORE_COPY
  --after-copy ABS_AFTER_COPY
  --git ABS_GIT
  --receipt ABS_REPORT_TRANSITION_RECEIPT
~~~

`attest-prior`必须在PRE前且只执行一次，并沿outer-driver→evidence-tool supervisor→provenance链发布其pending attestation primary；supervisor的`--expected-output`顺序必须exact为`ABS_STAGE2_REPORT_PREIMAGE,ABS_PRIOR_ATTESTATION_PRIMARY`，两层actual rc/streams全绿后，再由当前两名不同reviewer对primary exact SHA给出APPROVE。owner-approved input token exact `ista-csr-step9-prior-attestation-input/1.1.0`，top-level exact `schema,records`；input自身须canonical no-follow regular/current-uid/nlink1、mode0600、且由`ref_v1`与`identity_v1`双重绑定。每条record exact `kind,subject,claim_text,source_kind,source_locator,source_sha256`，`kind` closed union exact `machine_artifact|transcribed_collaboration_verdict_or_gate_claim`。前五条必须依次为subject `step8_plan,step8_cleanup_receipt,plan_review_repair_intent,plan_review_repair_completion_receipt,stage2_report_preimage` 的 `machine_artifact`，source kind exact `filesystem`；前四者locator/SHA匹配对应CLI ref，第五者只能匹配本次新发布的immutable preimage output，不得指向live report target。repair两项canonical path分别exact `/home/shigure/code/ecc/chipcompiler/thirdparty/ecc-tools/build-ista-step8/step9-plan-review-pyc-repair-intent-v1.json` 与 `/home/shigure/code/ecc/chipcompiler/thirdparty/ecc-tools/build-ista-step8/step9-plan-review-pyc-repair-receipt-v1.json`，raw SHA分别exact `a3df8abbdf29e14eb2f2209f3412e2bdcda859a107affc1dc5d98538b97b17a3` 与 `dad7d36e85c3889f7d7ce05dec333667e79f14ba624efb7bcd506c4b557f4974`。五条claim只可陈述实际path/bytes/schema，不可承载review/gate结论。

machine五条后必须exact接下表11条current collaboration rows；没有旧report-only verdict tail，总records cardinality由`5 + 11`表推导为16。tail整体按`subject,claim_text,source_locator` raw UTF-8严格升序，subject/locator/source digest均unique；`source_kind` exact `collaboration-review-record`，locator必须exact匹配表中非filesystem文本，拒绝absolute/relative path、`file:`、NUL/CR/LF。旧report preimage仍是第五条machine bytes来源，但其v0.14 review/gate文字不能满足current v0.15 DoD。

| exact subject | exact source locator | claim必须绑定 |
|---|---|---|
| `step8_v0_15_changed_source_final_code_review_a` | `Codex collaboration task /root/final_plan_review_a; record=step8-v0.15-changed-source-final-code-review-a; delivered-to=/root` | reviewer A `APPROVE/findings=[]`与controller `b5db78b98cdff87be1613c1042a8b7c5fe9548e0e4c3c0fe7fd868d1ed3f3fac`、selftest `190be2f0a1293d4d8368e2d27859efe6b6f9c28430fd55197cb0e85c4d65d1fe`、Workflow `ebc771161b46fd4e98c3bfdb257ef4227d91860cb783d73d2f4738b9d9cf4e04` exact paths/SHA |
| `step8_v0_15_changed_source_final_code_review_b` | `Codex collaboration task /root/final_plan_review_b; record=step8-v0.15-changed-source-final-code-review-b; delivered-to=/root` | reviewer B对同一三文件bundle的独立`APPROVE/findings=[]` |
| `step8_v0_15_final_format_hygiene_inventory` | `Codex collaboration task /root/final_style_wheel; record=step8-v0.15-final-format-hygiene-inventory; delivered-to=/root` | Step8 plan `2246cc8c…`与三文件bundle；clang-format 239=`237+2`、child-root offline Ruff exact7、parent/child diff、291 untracked whitespace、Mulan239、artifact/pycache、Step6/7/8 umbrellas；不得冒充parent-local Ruff |
| `step8_v0_15_fresh_process_until_fail_3` | `Codex collaboration task /root; record=step8-v0.15-fresh-until-fail-3; delivered-to=/root` | exact三文件bundle、fresh-process repeat 3/3 PASS及96.35/97.08/96.15秒 |
| `step8_v0_15_full_csr_79` | `Codex collaboration task /root; record=step8-v0.15-full-csr-79; delivered-to=/root` | exact三文件bundle、selector `^ista_csr_`、79/79 PASS |
| `step8_v0_15_global_labels_87_20_7` | `Codex collaboration task /root; record=step8-v0.15-global-labels-87-20-7; delivered-to=/root` | exact三文件bundle、`ista_unit/property/smoke`分别87/87、20/20、7/7 PASS |
| `step8_v0_15_n6_final_only_diagnostic` | `Codex collaboration task /root; record=step8-v0.15-n6-final-only-diagnostic; delivered-to=/root` | controller `b5db…`、umask077/repeats6、run-root `step9-controller-run.final-current-n6.6ckqRncupuzh/...385-64e842f8e7c4b16a7f4da5645052e002`、summary `7034489c377142876fbca84b526e1085a30649757e03e9b2d5f3eea76196e8ff`、18 slots/36 lanes/36 finals/zero `sta` |
| `step8_v0_15_parent_local_pinned_ruff` | `Codex collaboration task /root; record=step8-v0.15-parent-local-pinned-ruff; delivered-to=/root` | parent-root Ruff0.14.13 exact7 check与format-check PASS及Step8 plan `2246cc8c…` |
| `step8_v0_15_stage0_stage1_focused_41_495` | `Codex collaboration task /root; record=step8-v0.15-stage0-stage1-41-495; delivered-to=/root` | exact三文件bundle、Stage0 41/41与Stage1 495/495 PASS |
| `step8_v0_15_step9_v0_31_plan_final_review_a` | `Codex collaboration task /root/final_plan_review_a; record=step8-v0.15-step9-v0.31-plan-final-review-a; delivered-to=/root` | reviewer A对Step8 plan `2246cc8c…`与本v0.31最终bytes/SHA的`APPROVE/findings=[]` |
| `step8_v0_15_step9_v0_31_plan_final_review_b` | `Codex collaboration task /root/final_plan_review_b; record=step8-v0.15-step9-v0.31-plan-final-review-b; delivered-to=/root` | reviewer B对同两计划bytes的独立`APPROVE/findings=[]` |

每个locator指向的真实协作消息必须原样包含closed projection，exact keys `schema,task_path,record_id,delivered_to,actor_id,record_type,artifact_refs,evidence,decision,findings`；schema exact `ista-csr-step9-collaboration-record-projection/1.0.0`。`task_path,record_id,delivered_to,actor_id,record_type`均为nonempty UTF-8 string且拒绝NUL/CR/LF，前三项必须与locator及接收者exact；`record_type`只允许`plan_final_review|code_final_review|format_hygiene_inventory|gate_result`。`artifact_refs`按role raw UTF-8排序且每项exact `role,path,sha256`，role unique；`evidence`为nonempty、unique、raw UTF-8升序string array；decision只允许`APPROVE|PASS`，findings exact `[]`。`source_sha256 = SHA256(CANON(projection))`，其中CANON沿用UTF-8、object keys排序、`,`/`:` separators、`ensure_ascii=false`,`allow_nan=false`、single final LF；它不是plan/code/claim/locator或单文件SHA。两名外部prior-attestation reviewer必须按locator打开协作历史、取得projection、重算CANON digest并逐项核对artifact refs/evidence/claim/decision；runtime validator只比对完成双审后冻结进fresh tools的exact subject/locator/claim/source digest allowlist，明确不声称能直接解析聊天历史。v0.31计划自身只冻结本算法、角色、locator与claim要求，不写未来plan-review projection digest；顺序固定为final plan SHA→fresh A/B plan projections→fresh tools嵌入actual digests→KAT/tool双审→owner input→prior双审。

`attest-prior`在发布primary前先no-follow绑定actual report target：canonical exact path、各component非symlink、regular/current uid、porcelain-v2 `?`、HEAD/index/stages absent，并以single-open→fstat→完整read→second-fstat取得source identity/raw bytes/SHA。它要求preimage-output canonical path初始ENOENT、位于validated evidence dir、与source不同path且任何existing component不alias source；随后把raw report bytes交给reviewed common `HardlinkPublisher`，用same-dir exclusive temp完整write/fsync/reopen verify→no-overwrite hardlink publish→unlink temp/two dir-fsync，fresh要求copy regular/current uid/0600/nlink1、bytes/SHA exact且`(dev,ino)`不同于source。再fresh重读source，identity/bytes必须仍等于首次读；copy发布后永不打开写、不替换、不删除，任何later consumer只读。

prior attestation primary token exact `ista-csr-step9-prior-review-attestation/1.1.0`；top-level exact `schema,publication_contract,tool_path,tool_sha256,dependency_loads,argv,env,cwd,attestation_input,step8_plan,cleanup_receipt,plan_review_repair_intent,plan_review_repair_completion_receipt,report_source,report_preimage,records,limitations,planned_stdout_size,planned_stdout_sha256,internal_state,complete`。`attestation_input` exact `ref,identity`；step8 plan/cleanup及两项plan-review repair均为`ref_v1`；`report_source`为首次与第二次读取均一致的`identity_v1`；`report_preimage` exact `ref,identity,publication`，publication为`publication_v1`且其final path/SHA匹配前两项。current `step8_plan` machine ref必须独立固定canonical path与SHA `2246cc8ce01d4952b7e8435275907327ef21446e15a4a47629f39febe9abbdc0`；cleanup raw ref独立固定`c98a7cd1…`且其内部`step8_plan_sha256`只允许历史`604dd542…`。repair intent/completion raw refs独立固定`a3df8abb…`/`dad7d36…`，completion反绑intent；intent内部只允许cleanup `c98a7cd1…`、Step8 `604dd542…`、report `026ba999…`、旧Step9 candidate `a28943d6…`。current/historical只共享本文冻结的canonical paths，任何consumer或KAT均禁止比较、替换或要求其跨代SHA相等。copy与source SHA/size相同而path及`(dev,ino)`必须不同。两repair文件须single-open/fstat/read/second-fstat验证regular/current-uid/nlink1、canonical path/raw SHA/schema exact；completion receipt要求`complete=true,all_post_absent=true,files_expected=15,directories_expected=4`、files/directories基数exact 15/4、每项`post_absent=true`且`post_source_pyc=[]`、`post_source_cache_dirs=[]`，并与fresh child source absence scan一致。`records`与approved input exact相同；`limitations` exact单项array `not-a-cryptographic-identity-or-contemporaneous-external-receipt`；`internal_state="report_preimage_and_attestation_published_pending_external_observation",complete=false`。该文件不得称Ruff/CTest/review receipt当时存在，也不得把plan-review repair伪称Step8当时receipt或Step9 measurement cleanup、不得把collaboration claim提升为machine artifact。

当前review receipt token exact `ista-csr-step9-prior-attestation-review/1.0.0`，top-level exact `schema,attestation_sha256,inner_exec_receipt_sha256,outer_receipt_sha256,reviewer_id,decision,findings`；两份reviewer id须distinct，`decision="APPROVE",findings=[]`，且绑定同一全绿observer链。PRE的two-tier规则冻结为：`step8_evidence`只枚举actual current Step8 plan、historical cleanup receipt、immutable report PRE及新生成attestation primary/inner-exec/outer六refs；独立`plan_review_repair_evidence`只枚举historical repair intent/completion receipt两refs，明确不伪装current Step8 artifact或measurement cleanup；current code/design/gate verdict只存在于上表collaboration records。producer在生成`measurement_inputs`后、PRE supervisor mirror在接收manifest时、POST/FINAL later immutable consumer均须exact反绑：六个Step8 payloads、两个repair payloads、`source_inventory.step8_plan`、current `source_inventory.step9_plan`、`source_inventory.prior_attestation_input`完整binding、`hygiene_baseline.step8_cleanup_receipt`、唯一parent report baseline row与attestation source；PRE另要求`CANON(repo_state_actual)==CANON(repo_baseline)`。PRE/producer必须以普通模式fresh验证attestation top-level `report_source`仍等于live target；report合法替换后，POST/FINAL later consumer必须显式选择prior-only stored-source模式，只允许该top-level `report_source`按已存identity结构校验并以其SHA/size反绑fresh immutable preimage raw bytes，不得fresh打开已变化target。该模式不得传播给capture或任何非prior primary；attestation input、report preimage ref/identity/raw/publication、current Step8 plan、historicalcleanup及两repair refs/bytes/closure仍须逐项fresh。missing actual path、claim无source、任一projection drift、repair关系/absence不闭合或把collaboration转录冒充external receipt均hard fail。

attest-prior KAT必须覆盖attestation input missing/extra/type/hash/identity、machine五项missing/extra/swap/order、两repair CLI path/hash/schema/type/receipt→intent/complete/absence/count/fresh-scan mismatch、source relative/symlink/hardlink/非canonical或Git class错误、source在两次fstat/发布期间漂移、copy与source path/inode alias、preimage final预存、copy temp每个write/fsync/reopen/link/unlink/dir-fsync fault、copy完成而primary失败及primary存在而expected copy缺失/漂移。accepted case必须两个expected outputs均存在并匹配primary；所有fault均nonzero/no replay/no phase envelope，且不得覆盖existing output或把live target当immutable input。

prior专项KAT还必须双端登记并调用actual validator而非fixture自抛异常：producer侧接受current Step8 `2246cc8c…`与历史cleanup/repair `604dd542…`并存，拒绝把current Step8或current Step9 SHA代入任一历史字段；接受exact 5-machine+11-collaboration records，拒绝kind/source-kind/claim/locator/source digest任一swap、filesystem locator、artifact SHA冒充projection SHA、missing/extra/duplicate/reorder、collaboration locator/digest复用、reviewer或record复用。producer与supervisor mirror均须对六个Step8 refs、两个repair refs、`source_inventory.step8_plan`与`hygiene_baseline.step8_cleanup_receipt`两个重复投影位点、attestation-input binding、current Step9 binding及report repo row逐项drift拒绝。common actual prior-primary KAT必须证明：live report已变化时later stored-source正例通过；默认PRE模式对同一stale source拒绝；第二stale input、stale immutable preimage、四个fixed top refs、extra record、artifact-SHA冒充projection-SHA及authority复用逐项拒绝；stored-source flag用于capture或非prior schema也拒绝。provenance KAT须实际调用`_validate_stored_prior_subject_value`并穿透common actual validator，另证明PRE默认路径、capture误用与stale preimage拒绝；独立caller-boundary KAT必须实际进入`_fresh_validate_prior_projection`并证明later projection在读取inner observer前选择stored helper且未调用普通fresh helper，另实际进入PRE prior-review group并证明其只选择普通fresh helper。report-transition caller-boundary KAT必须实际进入`_transition_inputs`，证明它在读取inner/outer observer前先选择唯一later-transition helper、该helper向common传递later flag且默认subject helper未被调用。FINAL/report-transition KAT须以两个独立stored-only开关走actual validator：分别接受shared `repo_baseline`与历史PRE/POST `repo_state_actual`中的canonical exact report row，证明POST自身baseline/actual及递归PRE baseline/actual任一第二stale path仍被fresh拒绝，并以`expected_phase=final`证明当前FINAL `repo_state_actual`的stale report row被fresh拒绝；historical-actual flag必须同时要求baseline flag且只允许读取PRE/POST immutable manifest，phase/schema/flag scope错误须匹配closed rejection，任何调用方不得用baseline开关隐式放宽historical actual或current actual。另须逐层actual caller wiring覆盖`publish-report argv→later transition primary→POST completion→POST phase primary→POST manifest→PRE cross manifest`，并逐项拒绝old report identity/`target_before`不等、非canonical before或after target、FINAL target path或SHA与`target_after`投影不等。

`phase`的pre要求且只允许完整五项`--prior-attestation*` group，禁止`--pre-manifest`/`--post-manifest`与transition group；post要求且只允许`--pre-manifest`并禁止prior-evidence group；final要求pre+post与三项transition receipt且禁止prior-evidence group。五项分别绑定上列attestation primary/inner-exec/outer与两份current review refs；任一partial group、alias、relative/symlink path或wrong phase都拒绝。`publish-report`是七tool内唯一report target writer，必须沿outer-driver→evidence-tool supervisor→provenance inner链执行；人工只可在validated ignored scratch准备并批准`report-source` bytes，禁止编辑器、patch、redirect或人工API直接写target。唯一mutation API签名 exact `publish_report_v1(*,post_manifest:str,post_primary_receipt:str,post_exec_receipt:str,post_outer_receipt:str,post_envelope:str,report_source:str,report_source_sha256:str,report_target:str,report_lock:str,before_copy:str,after_copy:str,git:str,receipt:str)->None`；不得有位置参数/default/alias/第八工具。expected-old target identity/SHA只从strict POST manifest取得，不接受caller另传。

PRE构造`repo_baseline.parent`时，live report target record必须与attestation primary的`report_source` path/mode/size/SHA及untracked/HEAD-index-absent条件exact；`step8_evidence`绑定的是不同inode preimage copy。POST/FINAL不得再把已变化target当shared input或fresh prior source，只可把attestation primary的top-level `report_source`作为stored identity与immutable preimage raw SHA/size反绑，同时fresh no-follow rehash immutable copy、attestation input、两项plan-review repair artifact及observer chain并要求与PRE exact；stored source之外任何copy/input/ref/identity/bytes漂移均整轮无效。repair authority仅为其persisted `ref_v1`：后两相fresh要求canonical path/component非symlink、regular/current-uid/nlink1、schema/receipt关系与raw bytes/SHA匹配PRE ref及fresh absence，不声明或比较未持久化的dev/ino跨相identity。

POST生产与publish-report生产者在replacement前验证POST五件链时不启用repo-state例外，必须fresh通过。report已合法替换后，仅两个consumer可显式进入later historical-report-state模式：(1) publish-report external supervisor重验transition primary时，沿其immutable POST completion→POST phase primary→POST manifest→递归PRE manifest链；(2) FINAL strict mirror读取immutable PRE/POST manifests时。该模式把shared `measurement_inputs.repo_baseline`与历史PRE/POST `repo_state_actual`分成两个独立stored-only开关，并且每个开关只允许canonical exact `docs/incregpusta/stage2-report.md`唯一untracked/HEAD-index-absent row按stored worktree identity验证；其他baseline path、历史actual中的其他path及当前FINAL `repo_state_actual`全部继续fresh。任一第二stale path、baseline/actual开关混用、wrong schema/phase/caller、把例外传播给当前FINAL actual或非publish-report primary都hard fail。POST baseline与actual及递归PRE baseline与actual四处old report worktree identity必须全字段exact相同，并等于transition primary的`target_before`；`target_before.path`与`target_after.path`均须canonical exact report path。FINAL manifest的`report_transition.target`必须exact等于transition primary `target_after`的`{path,sha256}`并与当前FINAL唯一report row反绑。所有stored row还须与immutable report preimage、attestation source及PRE/POST equality chain exact反绑；不得把此repo-state模式扩张为prior top-level stored-source模式或反向扩张。

三相都必须沿§4.2–§4.3的同一链执行，primary固定pending/internal；inner exec记录provenance actual rc/streams，outer receipt记录supervisor raw wait/normalized rc/streams。每个phase的supervisor CLI `--expected-output`序列exact单项`[phase_manifest.path]`；特别是POST external-exec receipt的`expected_outputs == [post_manifest.path]`。POST primary绝不进入该array，只由`primary_receipt_path`/fresh SHA、strict primary bytes及两层stdout exact `primary path+LF`独立绑定；`[post_manifest,post_primary]`必须在读取inner subject前拒绝。每相manifest、primary、inner exec、outer receipt与completion envelope五者path/SHA必须交叉一致，envelope必须消费outer receipt并证明normalized rc exact0。report publisher另以transition primary作为expected output，只有其primary+inner exec+outer三件链全绿，final phase才可消费。

每条operational chain先用frozen tool inventory验证primary的consumer list，再分别验证external-exec的supervisor `[]`与outer receipt的outer-driver `[common]`，禁止三层互抄同一array；final reviewer还须fresh验证dependency path/SHA、actual loader trace与load_count1。runtime owner/context SHA或任一dependency field变化使所有受影响primary/observer/envelope/KAT/review失效，不得只重签最外层receipt。

三schema复用strict records：`ref_v1` exact keys `path,sha256`；`identity_v1` exact `path,dev,ino,uid,mode,size,sha256`；`publication_v1` exact `contract,final_path,final_sha256,temp_path,temp_absent,final_nlink,steps`，其中steps exact `temp_created,bytes_written,file_fsynced,closed,reopened,bytes_verified,linked,nlink2_verified,first_dir_fsynced,temp_unlinked,nlink1_verified,second_dir_fsynced`。path为canonical absolute string，SHA为64位lower-hex；整数必须nonnegative且bool不算integer；accepted publication固定contract、temp_absent=true/final_nlink=1、十二steps全true。所有records及下述nested object递归`additionalProperties=false`。

phase manifest schema token exact `ista-csr-step9-phase-manifest/1.1.0`；top-level keys exact `schema,phase,measurement_inputs,measurement_inputs_sha256,measurement_artifacts,measurement_artifacts_sha256,repo_state_actual,repo_state_actual_sha256,hygiene_actual,hygiene_actual_sha256,prior_manifests,report_transition,comparisons`。四个value/SHA pair须满足`sha256(CANON(value))`，null value只配null SHA。`measurement_inputs` exact keys `source_inventory,step8_evidence,plan_review_repair_evidence,repo_baseline,runtime_closures,timed_objects,build_inventory,tool_inventory,execution_context,hygiene_baseline`；`measurement_artifacts`在非null时exact `capture,lanes,context,reducer,recheck,command_receipts,absence_proofs`；`repo_state_actual` exact `parent,child`；`hygiene_actual` exact `parent_pyc,child_pyc,child_pycache,unexpected_source_artifacts,scan_sha256`。

除`repo_baseline`与`execution_context`两个下述specialized object外，`measurement_inputs`及`measurement_artifacts`的每个member都必须是`inventory_collection_v1`。schema token exact `ista-csr-step9-inventory-collection/1.0.0`；top-level exact `schema,domain,record_count,records_sha256,records`，`record_count=len(records)`且`records_sha256=sha256(CANON(records))`。每条record top-level exact `schema,domain,role,ordinal,payload_kind,payload_sha256,payload`，record token exact `ista-csr-step9-inventory-record/1.0.0`，domain与owner collection exact，ordinal contiguous `0..record_count-1`，role为该domain生成算法给出的nonempty unique token，`payload_sha256=sha256(CANON(payload))`。array order不是JSON object key sort的副产品；必须服从下列domain order，任何missing/extra/duplicate/gap/reorder/type/hash错误拒绝。

`payload_kind` closed union exact `binding|ref|module|runtime_closure|timed_object|tool|lane|rowset|repo_path|absence|scan`；每个payload按kind递归`additionalProperties=false`：

- `binding` exact `path,realpath,kind,schema,dev,ino,uid,mode,size,sha256`。kind exact `regular|directory|builtin|frozen`；regular/directory的path/realpath canonical absolute且identity字段nonnegative、SHA lower-hex（directory SHA是按UTF-8 basename排序的no-follow entry inventory）；builtin/frozen仅用于Python import，path/realpath exact `builtin:NAME|frozen:NAME`、schema与identity/SHA全null。
- `ref` exact `path,sha256`；path canonical absolute、SHA lower-hex。
- `module` exact `source_id,allowed_import_names,canonical_path,dev,ino,uid,mode,size,sha256`；allowed names为nonempty unique string array，15项order与§4.1 exact。
- `runtime_closure` exact `role,invocation,resolved,dependencies`；invocation/resolved均`identity_v1`，dependencies为loader原序array且row exact `soname,path,size,sha256`，path canonical absolute、size nonnegative、SHA lower-hex；不得not-found/null。
- `timed_object` exact `ordinal,source,object,compile_argv,header_dependencies,memberships`；ordinal 0..32，source/object为`ref_v1`，argv string array，header dependencies为Ninja输出原序`ref_v1` array，memberships是按`export,reference,scatter`固定顺序过滤的nonempty enum array。
- `tool` exact `name,path,identity,sha256,argv_prefix,dependency_loads,kat_runs,review_receipts`；identity为`identity_v1`且须regular/current-uid、permission mode exact0700，identity.path/SHA分别等于path/sha256，argv prefix exact `[ABS_NIX_PYTHON,"-B","-I","-S",path]`且`argv[4]=path`。`dependency_loads`服从§4.1 exact row/cardinality/order。`kat_runs`为exact两项array，每row top-level exact `ordinal,reviewer_id,primary,inner_exec,outer,registry_sha256`：ordinal为拒绝bool的integer且依次exact `0,1`；reviewer_id为nonempty UTF-8 string且拒绝NUL/CR/LF；primary、inner_exec、outer各为`ref_v1`；registry_sha256为64位lower-hex。`review_receipts`为exact两项array，每row top-level exact `ordinal,reviewer_id,receipt`，ordinal/reviewer_id规则同前，receipt为`ref_v1`。两array均按reviewer_id raw UTF-8 bytes严格升序，reviewer_id distinct；同ordinal reviewer_id exact相同。解码receipt所得tool-review的tool/tool_identity/dependency_loads/reviewer_id/registry_sha256及`kat_primary,kat_inner_exec,kat_outer`必须分别与本tool row及同ordinal kat_runs exact相等；三KAT refs须指向同一distinct observer chain且不得跨reviewer复用。所有row及ref nested递归`additionalProperties=false`。七tool自身顺序服从§4.1。
- `lane` exact `case,repeat,lane,path,schema,mode,size,sha256`；case/repeat/lane顺序服从bundle×0..5×oracle/reference，mode/size nonnegative；36 rows只表示0600 published finals，transient `sta/`不得生成row。
- `rowset` exact `path,schema,file_sha256,row_count,rows_sha256`；count nonnegative且两个SHA lower-hex。
- `repo_path` exact `path,porcelain_kind,head,index,worktree,cached_patch_sha256,unstaged_patch_sha256`；head为null或exact `mode,oid`，index为stage-number升序strict rows `stage,mode,oid`，worktree为null或`identity_v1`；patch SHA只在tracked且对应patch适用时lower-hex，否则必须null。
- `absence` exact `path,present`且present必须JSON false；`scan` exact `root,pattern,match_count,matches,scan_sha256`，matches为按raw canonical absolute path排序的`identity_v1` array、count/hash自洽；成功absence不得用空free-form object。

domain/cardinality/order exact：

| owner member / domain | cardinality | record order |
|---|---:|---|
| `source_inventory` | `23 + N_INPUT_OCCURRENCES` | controller 1 → §4.1 modules 15 → controller/probe schemas 2 → real/baseline manifests 2 → real后baseline各按bundle case order与input-key UTF-8 order的每个resolved input occurrence → Step8 plan → Step9 plan → owner-approved prior-attestation input |
| `step8_evidence` | 6 | Step8 plan → actual cleanup receipt → immutable report PRE copy → prior-attestation primary → its inner exec → its outer receipt；两份current attestation review由PRE primary另引ref，不伪装Step8 artifact |
| `plan_review_repair_evidence` | 2 | plan-review repair intent → completion receipt；均为`ref` payload，反绑attestation primary并保持其独立closure分类 |
| `runtime_closures` | 3 | locked Nix Python → oracle probe → reference probe |
| `timed_objects` | 33 | §3.2列出的原序，禁止按path重排 |
| `build_inventory` | self-counted | required `CMakeCache.txt,compile_commands.json,build.ninja,rules.ninja,parent-flake,parent-flake-lock,compiler,linker`先固定顺序；再对fresh Ninja query解析出的CMake/link inputs按canonical path raw UTF-8排序，PRE冻结exact count/roles，POST/FINAL不得变化 |
| `tool_inventory` | 7 | capture-supervisor → context → reducer → recheck → outer-driver → capture → provenance，与freeze/DAG一致；每项含closed dependency map、按reviewer UTF-8排序且ordinal 0/1配对的两次KAT chain与两份tool review |
| `hygiene_baseline` | 42 | preserved parent 2 → parent pyc manifest 37原序 → cleanup receipt ref 1 → child pyc scan → child pycache scan |
| artifacts `capture,lanes,context,reducer,recheck,command_receipts` | `5,36,3,6,3,0` | capture=`primary,marker,inner-exec,outer,summary`；lanes=bundle×repeat×lane；context=`primary,inner-exec,outer`；reducer=`timing,storage,aggregate,primary,inner-exec,outer`；recheck=`primary,inner-exec,outer`；phase receipts永远不塞入empty command_receipts |
| artifacts `absence_proofs` | self-counted | 从七tool frozen generator registry穷举所有static failure final与temp/poison scan pattern，先canonical path再pattern raw UTF-8排序；每项只能absence或scan，PRE冻结registry SHA，POST/FINAL count/records exact相同 |

`N_INPUT_OCCURRENCES`不是模糊discover count：它是strict解析real manifest后baseline manifest、逐case/逐input-key产生的occurrence总数；即使path重复也保留不同role/ordinal。两个self-counted domain先用上述唯一算法生成完整candidate，拒绝无法解析/unknown role，再冻结count/CANON；不得写“至少”“相关文件”或人工补项。

`repo_baseline` top-level exact `parent,child`，两者各为closed `repo_snapshot_v1`；每相`repo_state_actual`也exact `parent,child`且同型，禁止把单仓snapshot冒充container或交换parent/child。snapshot exact keys `schema,head,branch,gitlink,paths`，schema exact `ista-csr-step9-repo-snapshot/1.0.0`，head lower-hex、branch string、gitlink为null或exact `path,oid`、paths为按canonical path raw UTF-8排序的`repo_path` payload array。

`execution_context` exact keys `env,python,platform,nix`；env exact五键`PYTHONDONTWRITEBYTECODE,OMP_NUM_THREADS,OMP_DYNAMIC,LC_ALL,TZ`及冻结值；python exact `identity,version,argv,flags,imports,closure_sha256`，flags exact `dont_write_bytecode,isolated,no_site,ignore_environment`且值1，imports是同一`inventory_collection_v1` domain `python_imports`。fresh exact import list执行后按module logical name UTF-8排序：builtin/frozen各一binding，file-backed各一binding，extension紧随一个runtime_closure；因此record_count由actual closed module set自证并在PRE冻结，POST/FINAL exact相同。nix exact `flake_rev,python_out_path`。

platform top-level exact `kernel,wsl,cpu_topology`。`kernel` exact `sysname,release,version,machine`且四项均nonempty string；`wsl` exact `detected,version,proc_version_sha256`，accepted值依次JSON true、integer 2、lower-hex SHA；`cpu_topology` exact `logical_cpu_count,online_cpu_ids,affinity_cpu_ids,model_name_sha256,pinning_controlled,governor_controlled`，count positive integer，两个ID arrays均strict increasing unique nonnegative integers、online长度等于count且affinity为online nonempty subset，SHA lower-hex，两个controlled值为boolean。上述所有nested递归拒绝extra；KAT覆盖repo parent/child swap/missing/extra、snapshot schema错、platform每层missing/extra/type/bool-as-int、WSL值错、CPU ID duplicate/unsorted/out-of-range/count或subset不自洽，全部nonzero/no manifest/no envelope。

`hygiene_actual.parent_pyc,child_pyc,child_pycache,unexpected_source_artifacts`也分别是collection，count依次exact37/1/1/1，后三者各唯一scan；`scan_sha256=sha256(CANON([四collection的records_sha256]))`。schema KAT逐payload kind及domain覆盖top/nested missing/extra、bool-as-int、bad conditional null、bad SHA/CANON、cardinality/order/role、variable generator unknown/duplicate与empty command-receipts插项；任何一项nonzero/no manifest/no envelope。


schema KAT另对每个tool/primary/review/observer的`dependency_loads`逐一覆盖field missing/extra/type、logical/path/SHA/load_count、owner self-edge、cardinality/order、actual captured-load trace不等。对tool inventory的`kat_runs|review_receipts`逐字段覆盖：row top/nested missing/extra；ordinal为bool/noninteger/负数/duplicate/gap/swap；reviewer_id为nonstring/empty/NUL/CR/LF/duplicate及locale/casefold排序冒充raw UTF-8排序；registry_sha256为nonstring、长度/大小写/hex或actual registry mismatch；primary/inner_exec/outer/receipt ref的missing/extra/type、relative/noncanonical path、bad SHA、bytes SHA或schema mismatch；A/B chain互换、跨ordinal reviewer mismatch、review receipt指向wrong tool/dependency/registry或其三refs与对应KAT row不等。全部nonzero/no primary/no replay/no envelope。
`prior_manifests` exact `pre,post`：pre phase两者null；post仅pre为ref；final两者均ref。`measurement_artifacts`/SHA在pre为null，在post/final为strict object且二者CANON/SHA exact相同。`report_transition`在pre/post为null，在final exact keys `primary_receipt,inner_exec_receipt,outer_receipt,target`且均为ref；前三件须为同次publisher链，target SHA等于FINAL report。`comparisons` exact `inputs_vs_pre,repo_state_vs_pre,artifacts_vs_post,hygiene_vs_pre`，值依phase依次为pre=`baseline,baseline,not_applicable,baseline`、post=`equal,exact,baseline,equal`、final=`equal,report_raw_only,equal,equal`。

pending primary schema token exact `ista-csr-step9-phase-primary-receipt/1.0.0`；top-level exact `schema,publication_contract,phase,tool_path,tool_sha256,dependency_loads,argv,env,cwd,start_wall_ns,start_monotonic_ns,end_wall_ns,end_monotonic_ns,primary_receipt_path,prior_review_evidence,prior_manifests,report_transition_inputs,manifest,manifest_publication,planned_stdout_size,planned_stdout_sha256,internal_state,complete`。`prior_review_evidence`在pre exact keys `attestation,inner_exec,outer,review_a,review_b`且五者均`ref_v1`，两review须满足§7.1 distinct/APPROVE和三层chain binding；在post/final必须null。prior manifests条件同manifest；transition inputs在pre/post为null、final exact三receipt refs；manifest为`identity_v1`，publication为`publication_v1`；planned stdout exact primary absolute path+LF；`internal_state="manifest_published_pending_external_observation",complete=false`。禁止自身SHA及future inner/outer/envelope字段。

completion envelope schema token exact `ista-csr-step9-phase-completion-envelope/1.0.0`；top-level exact `schema,publication_contract,phase,manifest,primary_receipt,inner_exec_receipt,outer_receipt,observer,streams,evidence_verdict,complete`，四evidence项均ref。observer exact `outer_preflight_state,outer_fork_state,outer_exec_state,outer_pid,outer_raw_wait_status,outer_wait_kind,outer_exit_code,outer_term_signal,outer_normalized_returncode,inner_spawn_state,inner_pid,inner_returncode,streams_complete`；streams exact `inner_stdout_size,inner_stdout_sha256,inner_stderr_size,inner_stderr_sha256,outer_stdout_size,outer_stdout_sha256,outer_stderr_size,outer_stderr_sha256`。accepted envelope只允许preflight/fork/exec/spawn succeeded、两rc0、wait exited/exit0/signal null、streams complete、两层stdout exact primary path+LF、stderr empty、`evidence_verdict="accepted",complete=true`；不得含自身path/SHA。

无自引用DAG exact `manifest → primary(manifest SHA) → inner exec(primary SHA) → outer receipt(inner SHA) → envelope(前四SHA)`；consumer只在envelope外fresh hash envelope。三相各做一正例；negative KAT覆盖任意top/nested missing/extra/duplicate key、wrong type/bool-as-int/bad SHA/NaN/noncanonical或trailing bytes、phase/prior/null-SHA条件、PRE prior-evidence missing/partial/extra/review非distinct或chain/hash不匹配、POST/FINAL夹带prior-evidence、POST/FINAL inputs或artifacts不等、comparison token错误、primary complete/self/future字段/planned-stdout错误，以及任一state/rc/stream/receipt-chain失败仍出envelope；全部nonzero/no replay/no envelope。

| phase | 时点 | measurement_artifacts | repo_state允许变化 |
|---|---|---|---|
| pre | Step8 external cleanup receipt已冻结且child pyc/cache absence复验后；final build、七tool冻结、capture前 | null | baseline |
| post | capture/context/reducer/recheck后，report edit前 | complete | 相对pre无Git-visible变化 |
| final | report edit后；不得执行任何pyc/cache cleanup | 必须与post exact相同 | 仅untracked stage2-report raw-bytes delta |

三份都含canonical `measurement_inputs` 与 `measurement_inputs_sha256`；两者必须byte-for-byte相同。shared `measurement_inputs.repo_baseline` 是PRE时完整canonical snapshot及report preimage，不是在后两相复制后冒充当前状态。每相另fresh采集phase-specific `repo_state_actual`、`repo_state_actual_sha256`、`hygiene_actual`、`hygiene_actual_sha256`，这些actual字段不进入shared input digest。

PRE与POST `repo_state_actual` bytes/SHA exact；FINAL执行§7.4 path-index comparison。FINAL重读PRE/POST manifest时对其已冻结actual只启用§6所述独立historical-actual report-row窄例外，当前FINAL actual仍全量fresh。post/final的 `measurement_artifacts` 及其SHA必须exact相同。每相manifest自身file SHA、pending primary、inner exec、outer command receipt与completion envelope分别记录；该五件phase evidence及phase/timestamp raw receipts均为phase-local，不进入shared input digest，也不进入post/final measurement-artifact equality。post/final各自必须consume自己的envelope并证明outer normalized rc0，later phase仍须fresh重读/rehash全部实际inputs并对PRE baseline比较，禁止只复制prior manifest。

### 7.2 measurement_inputs exact覆盖

`measurement_inputs`上述exact keys的内容约束如下，不得增删key：

1. controller、contract、model、wire/helper的actual repo-local import closure，两schema、real/baseline manifests及全部resolved inputs、本计划与最终批准Step8 v0.15计划；
2. Step8 machine evidence只绑定实际plan、cleanup receipt、report PRE与prior-attestation observer chain；Ruff/CTest/CI/review/gate counts若无磁盘artifact只作attestation转录，不重跑、不联网、不虚构receipt；
3. `plan_review_repair_evidence`：只读绑定上述intent/completion receipt两项actual canonical path/raw SHA/schema及receipt→intent/15文件/4目录/all-post-absent关系，并与attestation primary、owner-approved input及fresh child source absence双向交叉；它不是Step8当时receipt，也不是Step9 cleanup；
4. `repo_baseline`：PRE时parent/child HEAD/branch/gitlink、完整Git-visible tracked patch bytes与untracked bytes/status/mode/SHA。对canonical `/home/shigure/code/ecc/docs/incregpusta/stage2-report.md` 另冻结exact precondition：porcelain-v2 `?` untracked record、HEAD tree absent、index/所有stage absent，path/component no-follow且target regular/current uid，mode/dev/ino/size/raw bytes/SHA；不得把它误标tracked、staged或unstaged patch。各相当前状态只进fresh `repo_state_actual`；
5. oracle probe、reference probe与actual Python executable三者的invocation path/realpath/hash/mode及各自递归 `ldd` closure；loader和每个resolved object均记录canonical token→realpath→file SHA，任一 `not found`、读取/解析失败或后相漂移均hard fail；raw ldd地址只进phase-local receipt；
6. 33 unique timed objects的full compile entry、source/object SHA、Ninja local header deps与21/16/27 membership；
7. build inputs：`CMakeCache.txt`、`compile_commands.json`、`build.ninja`/`rules.ninja`、link entries、相关CMake、parent flake/lock、compiler/linker realpath/version；
8. 七build-tree tools exact bytes/SHA/mode、closed dependency_loads/actual loader trace、两路KAT/review reviewer-sort+ordinal binding、explicit env、machine/kernel/WSL/CPU topology、Nix derivation/context；
9. preserved parent两文件与37-entry parent historical pyc baseline、Step8 external cleanup receipt、child `*.pyc`/`__pycache__` exact-absent baseline及artifact manifests。

### 7.3 measurement_artifacts exact覆盖

post/final `measurement_artifacts`上述exact keys必须绑定以下内容，不得增删key：

- capture inner exec receipt、capture outer command receipt、primary capture receipt、completion marker、summary及各自bytes SHA；successful set对派生failure diagnostic、marker temp及其他temp只记录exact expected path与 `present=false` absence proof；
- exact 36 lane final paths/bytes SHA、root directory inventory SHA，且逐lane inventory证明singleton final-only、`sta/`/temp/extra全absence；
- context pending primary、inner exec、outer command receipt及其7-param/capability evidence；
- 三reducer output、pending reducer receipt、inner exec与outer command receipt的file/rows/actual-stream SHA；
- pending recheck receipt、inner exec、outer command receipt与三独立row-set SHA；
- `command_receipts`必须保持exact empty collection（record_count 0、records `[]`、对应CANON hash）；所有actual receipts已且只能分别归入capture/context/reducer/recheck上述named collection，其stdout/stderr raw hashes与actual modes由各自strict receipt承载。pre/post/final phase及report transition evidence均为phase-local而明确排除，任何“其余”receipt或占位row插入都hard fail。

任一 `.failure.json`、marker temp、generic temp或rollback poison存在时，禁止生成complete post provenance；failure diagnostic只属于failed-run quarantine，永不属于successful measurement artifact set。§4.2两个旧gVLAN evidence/run-root整体也只属failed diagnostic set：不得进入fresh `measurement_inputs`、`measurement_artifacts`或phase-local evidence，旧capture observer即使rc0也不能克服published root非final-only。pre/post/final provenance自己的inner exec、outer command receipts与completion envelopes由本相consumer及final review另行strict验证；report transition primary/inner-exec/outer三件链也只属于FINAL phase evidence。它们按§7.1均排除在measurement artifacts equality之外。

post/final任一authoritative artifact path/bytes/order/hash或absence proof差异即整轮失败。final provenance不得重新跑controller/reducer来“得到相同数字”。

### 7.4 Final repo-state与artifact hygiene

每相必须从local Git与filesystem fresh构造path-indexed `repo_state_actual`，逐path记录actual porcelain-v2/HEAD/index/stages/worktree no-follow identity/mode/bytes SHA及仅对tracked paths有意义的cached/unstaged patch；不得用PRE snapshot替代采集，也不得为untracked report伪造index/staged/unstaged字段。PRE与POST整个object exact。

FINAL与POST比较时，只移除唯一允许路径 `docs/incregpusta/stage2-report.md` 后要求其余records byte-exact。report必须保持同一canonical path、porcelain-v2 `?` untracked class、HEAD tree absent、index与所有stage absent、regular/current uid且mode exact不变；只允许approved report raw worktree bytes/size/SHA改变，atomic replace导致dev/ino generation变化可记录但不是额外delta。任何tracked/staged/unstaged称谓、rename status、mode、index/HEAD entry或第二路径变化都fail。child Git-visible bytes exact不变，Step9 plan/tools/input bytes不变；`CLAUDE.md`与`stage1-stage2-meeting-report.md`维持§2.2 exact baseline且unstaged。

只有`step9_provenance.py publish-report`可执行report update。它使用唯一frozen `REPORT_COLLAB_LOCK`（validated ignored build tree内、fixed canonical path），以`O_CREAT|O_EXCL|O_NOFOLLOW`/0600取得并fsync，内容绑定run、writer PID/starttime、target path与strict POST expected identity/raw SHA；该协作锁不声称排除未遵守协议的外部writer，也不得把`rename`/`RENAME_EXCHANGE`称为kernel expected-old CAS。锁前把POST raw preimage以共同publisher durable复制并复验；同parent exclusive unpredictable temp创建后、该temp任何fsync前，必须`fchmod(fd,expected POST permission mode)`并以`fstat`验证regular/current-uid/mode exact，再完整write→file fsync→close→nofollow reopen/read/SHA/mode复验。持锁后紧邻publish fresh复验target仍为expected POST identity/bytes，mismatch则不rename、不移动target；匹配时只以`renameat(temp,target)`做atomic raw replacement→parent dir fsync→fresh复验planned bytes/mode与untracked/HEAD-index absent，再以共同publisher durable发布after copy与transition primary。primary发布时lock仍held；tool随后unlink lock+dir fsync，最后才stdout primary path+LF。任一后验/cleanup不可证均inner nonzero、保留backup/receipt并阻断三件observer链，不得声称CAS或悄悄覆盖未知bytes。

report transition primary token exact `ista-csr-step9-report-transition-receipt/1.0.0`；top-level exact `schema,publication_contract,operation,tool_path,tool_sha256,dependency_loads,argv,env,cwd,post_evidence,source,target_before,target_after,lock,before_copy,after_copy,replacement,synthetic_diff,planned_stdout_size,planned_stdout_sha256,internal_state,complete`。`post_evidence` exact `manifest,primary_receipt,inner_exec_receipt,outer_receipt,envelope`且各为§7.1 ref；source/targets/copies均`identity_v1`。strict consumer必须从完整POST completion返回的manifest分别提取`measurement_inputs.repo_baseline.parent.paths`与`repo_state_actual.parent.paths`中唯一canonical report row，要求两row untracked/HEAD-index-absent且worktree full identity exact相同并等于`target_before`；`target_before.path`与`target_after.path`都须exact canonical report path，same-parent atomic replacement要求两者`dev,uid,mode` exact相同而`ino`不同，不能只比较SHA/size或before-copy。before copy与stored `target_before`的`(dev,ino)`必须不同；source、fresh `target_after`与after copy三者path及`(dev,ino)`均两两不同，复制语义不得由hardlink/alias伪造。FINAL transition chain必须返回这份validated primary，FINAL manifest target ref再exact投影`target_after.path/sha256`。lock exact `path,identity,content_sha256,acquired,file_fsynced,state_at_primary_publication,release_required`，accepted primary固定acquired/fsynced/release_required true、state held；replacement exact `temp_path,temp_created,mode_set,mode_verified,bytes_written,file_fsynced,closed,reopened,bytes_verified,prepublish_target_reverified,renameat_done,parent_dir_fsynced,target_reopened,target_verified,temp_absent,other_path_delta_count`，accepted时十四个boolean全true、delta exact0；mode_set/mode_verified必须发生在file_fsynced前并绑定target_before permission mode。所有nested禁止extra。

`synthetic_diff` exact `git_path,git_sha256,argv,cwd,returncode,stdout_size,stdout_sha256,stdout_base64,stderr_size,stderr_sha256,stderr_base64`；argv exact bytes-mode `ABS_GIT diff --no-index --no-ext-diff --no-textconv --binary --no-renames -- BEFORE_COPY AFTER_COPY`，raw rc1、stderr empty，before/after SHA分别绑定POST/FINAL report。primary固定`operation="publish-report",internal_state="report_replaced_pending_external_observation",complete=false`，planned stdout为自身absolute path+LF；禁止自身SHA或future exec/outer字段。它只是raw synthetic diff，绝不称staged/unstaged patch；complete只能由fresh strict primary+inner exec+outer receipt链判定。

publisher KAT覆盖POST五件链任一schema/path/SHA/rc/stream mismatch、source SHA drift/alias/relative/symlink/hardlink、非canonical target、lock EEXIST、锁前/锁内target drift、before-copy/temp create/`fchmod`/post-chmod `fstat`/write/fsync/reopen/rename/dir-fsync/after-copy/diff/transition publisher/lock unlink逐点fault，及mode_set/mode_verified缺失、顺序错误、wrong mode、partial-temp、TEMP_READY、rename前后、receipt后lock-release前crash。provenance registry还须exact覆盖`post-evidence.accept-manifest-only`正例（通过expected-output边界继续inner验证）与`post-evidence.reject-manifest-plus-primary`负例（读取inner subject前拒绝）；另覆盖diff argv/rc/stderr、第二path/HEAD/index/mode变化、phase subcommand写target、人工direct-target write或第八工具。common/provenance双端还须覆盖post-publication later caller实际wiring、默认fresh拒绝、四处第二stale非report path、baseline/actual old identity不等、`target_before` full identity及dev/uid/mode/ino generation漂移、before-copy旧target inode alias、source/target-after/after-copy新字节组alias、before/after任一非canonical target、FINAL target path与SHA分别漂移、wrong schema/phase/argv flag scope。全部必须target untouched或observer链nonzero，final拒绝且保留可审计backup/receipt，不得误称complete。

`hygiene_actual` 与repo state分开：PRE、POST、FINAL都fresh记录37 parent historical pyc逐path metadata并要求bytes/status exact；三相都fresh扫描child，要求所有 `*.pyc` 与任何名为 `__pycache__` 的filesystem entry exact absent，并记录source artifact scan。它是phase-specific proof，不进入shared input digest。

pyc分开处理：

- 既有37-entry parent historical pyc manifest完整保留，PRE/POST/FINAL及Step10都逐path复验bytes/status，不删除、不改写、不归因于Step8/Step9；
- Step8 final closure的external cleanup receipt是只读前置证据：它按exact path记录 `reference_input` 9项、`projection` 2项、`baseline` 1项 `cpython-312.pyc` 与三个exact `__pycache__` 的清理前metadata、逐项unlink/rmdir结果及清理后absence；该清理由Step8 owner完成，不是Step9操作；
- Step8 report后、Step9 measurement前的v0.24 plan feasibility review遗留15个`cpython-313.pyc`/四目录；v0.31 freeze前既有fixed-manifest/no-follow repair intent `a3df8abbdf29e14eb2f2209f3412e2bdcda859a107affc1dc5d98538b97b17a3`，文件unlink后因directory volatile identity过严比较safe-stop，再只按intent验证stable `dev/inode/uid/gid/mode/nlink`、rmdir/fsync并发布complete receipt `dad7d36e85c3889f7d7ce05dec333667e79f14ba624efb7bcd506c4b557f4974`；两artifact永久只读绑定，明确属于plan-review final-closure repair，不属于Step9三相或measurement cleanup；
- Step9 PRE/POST/FINAL只做no-follow fresh absence scan，不删除、不rmdir、不修复。三相任一发现child pyc/cache entry都立即作废并返回Step8 final closure，禁止Step9用cleanup掩盖前置失败；
- `PYTHONDONTWRITEBYTECODE=1` 下不得产生任何新pyc或重建 `__pycache__`。

source scan还拒绝新result/run/temp/receipt/JSON、tool、patch、`rej/orig`、unexpected binary。build-tree evidence保留到final review/wrapper audit，不能git add。

## 8. Report、review与failure semantics

### 8.1 As-built report合同

`stage2-report.md`只由人工批准scratch source bytes、再经§7.1/§7.4 frozen provenance publisher按actual结果更新；人工不直接写target：

- 状态为Step 1–9本地验收、Stage 2仍进行中；
- 记录Step8批准SHA、两路review/gates、actual counts及上述plan-review cache regression repair intent/receipt SHA与safe-stop recovery边界；
- 记录Nix env、machine/compiler/thread/concurrency、33 object entries/flags；
- 记录outer driver/capture supervisor/inner/context/provenance/reducer/recheck paths、两层observer receipts与全部SHA、PID能力边界；
- 放入18 raw timing、18 compact storage、9 aggregate及warmup/measured role；
- 写明mode/fallback/unsupported、comparability_status及全部not-claimed边界；
- 下一步只指向Step10 local commits/wrapper，报告用“本报告所在提交”，不预写自引用commit SHA。

“memory”只能写“modeled host logical/capacity bytes”；不写RSS/allocator。报告数字不能替代机器artifact。

### 8.2 双路final evidence review

metrics reviewer读取工具源码和真实artifacts，在同一Nix env独立运行recheck，核对七参context、18/36 inventory、18/18/9 row sets、CSR公式、xs[2]/xs[4]、七tool dependency DAG/load trace、两路review ordinal配对与所有hash。

该review rerun不得写authoritative `EVIDENCE_DIR`。先在 `build-ista-step8` 下exclusive创建mode-0700、non-symlink sibling `step9-review-scratch.NONCE`，证明其realpath不在EVIDENCE_DIR内；outer driver、recheck primary、evidence-tool inner exec、outer command receipt及全部review-only outputs只写scratch，authoritative summary/finals/context/reducer outputs均no-follow只读。运行前后重算authoritative inventory/path/mode/bytes SHA并要求exact不变，`PYTHONDONTWRITEBYTECODE=1`且repo/source不得新增文件。scratch不进入measurement artifacts或post/final equality；reviewer在APPROVE中记录outer-driver/tool/primary/inner-exec/outer-receipt/18-18-9 row-set SHA及两层rc0。若前后inventory变化，作废final provenance并回到相应步骤。

claim/integration reviewer读取final report diff、三相provenance、Step8 evidence、preserved/hygiene manifests，检查无夸大声明、无source artifact、final只允许report delta、Step10边界正确。finding修复后原reviewer复查；工具/计划 SHA变化使旧APPROVE失效。

### 8.3 Hard failures

| failure | 必须结果 |
|---|---|
| Step8 v0.15 plan SHA不是 `2246cc8ce01d4952b7e8435275907327ef21446e15a4a47629f39febe9abbdc0`、新计划双APPROVE、changed-source fresh gates或最终代码双审任一未取得/失效 | 不运行 |
| 非parent bare-flake Nix、五env或三对象recursive ldd closure不同/含not-found | 整轮无效 |
| outer fork failure未写`fork_state=failed,pid=null,fork_errno`，或fork成功后的exec failure未写actual positive PID、`exec_state=failed,exec_errno`、raw wait/reap，或supervisor/inner Popen与controller spawn conditional-PID receipt不符 | 无可接受observer evidence set；整轮无效 |
| supervisor不是唯一inner external observer、outer driver不是唯一supervisor observer、任一层未actual wait/reap，或primary/inner-exec/outer/output交叉不符 | 无可接受generic complete evidence；整轮无效 |
| capture非bytes、actual Popen.pid/returncode缺失、stdout非absolute path+LF、stderr非空 | inner exec receipt拒绝；无可接受SUMMARY |
| outer generic/capture与inner generic/capture/controller/pair timeout不是独立720/2640/600/2520/2400/120字段，或actual outer/supervisor/inner/controller argv不匹配 | context失败 |
| outer preflight SET/GET/scan/empty-set失败后仍spawn/replay/envelope、fork_errno用于非fork failure，或outer receipt缺strict preflight/fork/exec schema、CLOEXEC EOF、supervisor-exec hash/raw wait/streams、actual PID/reap/cleanup，supervisor early exit仍被接受 | 不replay；无complete phase evidence；整轮无效 |
| 共同publisher直接open final写、temp未完整fsync/reopen验证、publish非no-overwrite hardlink、link/unlink/nlink/两次dir-fsync/rollback或crash trailing-temp ownership不可证，或partial bytes出现在final | 对应final不可消费；evidence poisoned；整轮无效 |
| capture或evidence-tool任一mode的subreaper set/get非exact1、successful pre-spawn child-set非exact empty、direct child非exact1、stable identity不是`(pid,starttime)`，fresh current non-direct child未立即纳入cleanup workset/分类，`first_seen_adopted`未使evidence hard fail或被跳过cleanup，或TERM→KILL/waitpid/drain后非`ECHILD`/live0/zombie0 | 不replay SUMMARY或generic primary path；整轮无效 |
| 任一mode的inner nominal rc0+pipes EOF后泄漏后代却仍返回0/replay，或四个fork-after-then-immediate-exit cooperative/ignore-TERM KAT未证明`first_seen_adopted`、nonzero/no-replay、identity复验、TERM→KILL（按行为需要）与最终清零 | supervisor必须翻nonzero；整轮无效 |
| PGID/SID查询失败/不匹配时跳过direct drain/reap、向未验证group发信号或未记录group cleanup unverifiable | marker absent；整轮无效 |
| TimeoutExpired后未再bounded communicate、错误拼接partial bytes、未reap或streams不完整 | marker absent；整轮无效 |
| leader退出后未检查全PGID，success group非空，或failure未做PGID TERM→KILL/最终空集验证 | complete=false primary、marker absent；整轮无效 |
| marker forward/rollback/diagnostic fault漏记，link后非同dev/inode/mode/nlink2、unlink后非ENOENT/nlink1、extra hardlink未拒绝，或compound残留未被exec receipt actual nonzero阻断 | EVIDENCE_DIR poisoned；context拒绝 |
| successful set出现failure diagnostic/temp而非 `present=false` absence proof | EVIDENCE_DIR poisoned；不得生成post complete provenance |
| context CLI/API signature或required capture outer receipt不exact，validator_call七项projection nested/schema/SHA漂移，或capture/context/reducer/recheck任一primary/marker/inner-exec/outer schema、conditional type、canonical path/SHA、observer argv、stream/rc双向绑定不符 | consumer拒绝；整轮无效 |
| root非18 slots/36 finals、任一lane非singleton final-only，或存在`sta/`/extra/temp/symlink/mode异常 | context失败；旧gVLAN root也不可消费 |
| 仍用三参validator、argv从record复制或夸大child PID证据 | context失败 |
| 任一tool inventory/KAT primary/tool review/operational primary缺或错`dependency_load_v1`，owner/consumer/reducer-recheck cardinality/order/load_count不exact，三层observer复制wrong list，或kat_runs/review_receipts的typed refs/scalar types/raw UTF-8排序/ordinal/逐ordinal解码cross-binding不符 | consumer拒绝；受影响KAT/review/evidence全部失效并重跑 |
| pair correctness/unsupported/fallback/schema/history失败 | 零aggregate |
| timing/storage/cardinality/order/CSR公式非法，或三output schema/top-level/row tokens/CANON(rows) preimage不exact | 整轮无效 |
| reducer/recheck任一row set或file/rows SHA不一致 | 不更新报告 |
| 三phase schema token/top/nested/conditional字段不exact、shared input SHA不同、post/final artifacts不同，POST `expected_outputs`非exact manifest-only，或任一相manifest/primary/inner-exec/outer/envelope缺失、自引用、hash/phase/rc/stream链不符 | 整轮作废 |
| PRE/POST fresh repo_state_actual不exact，report PRE/FINAL非untracked+HEAD/index absent，FINAL非report-only raw-byte/mode-stable delta，或publish-report CLI/API/primary+exec+outer链、协作锁/expected identity/transition/synthetic diff不exact | report保持未完成；target mismatch时绝不移动/覆盖unknown bytes |
| 人工/phase subcommand/第八工具direct-write report，或transition primary含future observer/self SHA、锁释放前伪称complete、publisher fault后final仍接受 | 整轮作废；不得生成FINAL complete evidence |
| preserved两parent文件或37 parent pyc漂移、Step8 cleanup receipt不符、plan-review repair evidence任一路径/SHA/schema/intent关系/15+4基数/complete/absence不符，或PRE/POST/FINAL任一child pyc/cache scan非exact empty | 不得由Step9清理；整轮作废并返回final closure |
| v0.31 freeze后仍需要改source/schema/CMake或uniform flags | 回Step8重计划；本轮producer修复已经先按Step8 v0.15完成closure，不构成例外 |
| 任一review finding未关闭 | Step9未完成 |
| commit/push发生在Step9 | 违反边界并停止 |
| Step10 launcher/env/hooks/attrs隔离不exact，owner identity或双审path manifests非法，动态推导PATHS，child gitfile/core.worktree、parent `.gitmodules`、任一local config raw/include proof漂移，或candidate binding/order不符 | 不得private add/install/update-ref；已安装只按locked restore；local wrapper失败 |
| Step10 `ABS_GIT`/empty-map/repo bindings漂移，caller含未批准`GIT_*`，live/PVT index binding混用，read-only/private命令改变live raw index或`ABS_INDEX.lock`，wrapper安装后未rebind，或alternate/replace/shallow/graft/namespace存在 | 对应command-agent不得spawn/继续；仅按journal locked restore或unresolved |
| private add/live-index install/update-ref前state不符，write-tree前就freeze PVT、write-tree后仍运行PVT command、final PVT raw/semantic不durable，pending PVT actual不是old/authorized atomic postimage、FINISHED|ABORTED未同journal追加对应generation、PVT release无typed INTENT/aggregate或unlink/dir-fsync/CONSUMED不同journal，或index lock/generation/install/restore/ref expected-old不exact | 不得install/publish；PVT不得重放/用PRE重建冒充旧generation，只按typed terminalization/release/locked restore或保留unresolved，不覆盖user edits |
| Step10 journal/temp ledger不完整，SPAWN_INTENT后无outer barrier/AGENT_FORKED durability就release或fork Git，SPAWNED/CLOEXEC/wait-reap-result缺失，re-entry并发重启，或ref/outer expected-old、identity/commit env失败 | 不得继续或重复spawn；按journal resume/rollback，否则unresolved |
| Step10 bootstrap/transition ready或INIT四态txn recovery不服从fixed dirfd/single-use layout，EMPTY/TEMP_ONLY被resume/abort越权恢复或FINAL_ONLY/FINAL_PLUS_TEMP不能由任一subcommand完成publication repair，transition-ready进入temp ledger/形成hash环，完整start bundle/typed refs未从BOOTSTRAP/INIT永久持久、locator/bundle/journal digest或slice不等，CONTROL/terminals跨device，parent bundle/manifest 1.1条件不闭合，rollback要求fresh external input，errors非prefix-monotonic，intent非phase-local write-ahead/details hash或state/nullability错误，command_result/FINISHED receipt非双射、rollback缺逐步RESTORE_INTENT，或terminal repair未先通过Python/tool/directory gate | 不得spawn/mutate/继续；只允许已验证publication/rollback recovery，否则unresolved |

## 9. 实施顺序与Step 9 DoD

### 9.1 Exact order

1. 冻结本v0.31 review candidate exact bytes/SHA供fresh双审；复验Step8 v0.15 exact SHA、新计划双审及changed-source fresh gates/code reviews，任一失效时停止。计划只冻结协作projection算法、角色与claim字段，不写入未来自身review digest；双审完成后才把actual projection digest冻结进fresh七tool，避免自指。
2. 独立只读绑定current Step8 plan `2246cc8c…`、历史cleanup `c98a7cd1…→604dd542…`与历史repair `a3df8abb…/dad7d36…`的旧604dd/a289/026ba/c98内部关系，fresh证明child pyc/cache absent，并冻结base heads、preserved、local refs、37 parent pyc与absence baselines；不执行cleanup、不做跨代SHA等值。
3. fresh Release build后在全新candidate materialize七tools；不得复制旧gVLAN或e23 tool/KAT/review/receipt。把Step1所得11个actual collaboration projection digests与exact claims/locators嵌入provenance及supervisor mirror后，按§4.1顺序读码并冻结closed dependency map/load trace，按reviewer UTF-8顺序执行全量两路KAT、ordinal绑定review receipts后双审，复验locked Nix Python `-B -I -S`、controller `-B -E -S`、15-source captured loader、common-runtime DAG、publisher/observer/phase schemas；authoritative run前所有primary/observer exact lists须与tool inventory交叉。
4. 经outer→supervisor执行`attest-prior`，绑定current Step8 plan、historical cleanup/repair、report PRE及exact 11-row current collaboration tail，取得primary+inner-exec+outer全绿及两份current review；report PRE不提供current review/gate claims。
5. 同链执行pre provenance；completion envelope两层rc0后冻结PRE repo baseline/fresh actual。
6. outer driver以2640约束capture supervisor、其以2520约束capture、capture以2400约束controller且pair120；只可创建fresh exclusive run-root，三层wait/reap/streams/receipts全绿并证明36 lane final-only。
7. 同链执行context exact CLI，重建18/36、七参validator、StrictContext annotations与Pair/Lane projection全绿。
8. 同链按full argv执行reducer与recheck，独立生成/比对exact 18/18/9及全部三层receipts。
9. 同链执行post provenance；supervisor expected-output exact manifest-only，两项POST边界KAT已由fresh provenance registry双跑/双审，随后冻结artifacts并证明fresh PRE=POST。
10. 同链执行publish-report；transition primary/exec/outer、lock/atomic replacement/synthetic diff全绿。
11. 同链执行final phase；shared inputs、post/final artifacts与report-only raw delta/hygiene全绿。
12. metrics reviewer只在authoritative dir外scratch重跑recheck；两路final review APPROVE。截至此处仍不commit、不push。

### 9.2 DoD

Step 9完成必须同时满足：

- approved v0.31与Step8 v0.15 exact SHA、新计划双审、changed-source fresh gates/code reviews、11个closed collaboration projections及digests、prior attestation observer chain/current双审、真实Step8 cleanup artifact及plan-review repair intent/receipt exact SHA均冻结；attest-prior exact 16 records=machine五项+current collaboration十一项、两repair CLI refs、primary typed refs及独立`plan_review_repair_evidence`两项交叉全绿，不声称不存在的历史receipt或把repair改写成Step8当时receipt/measurement cleanup；
- 全命令在exact Nix/env；七tool使用frozen Nix Python `-B -I -S`、controller使用同解释器`-B -E -S`，realpath/hash/closure/import/cache-absence KAT及受控loader/DAG全绿；
- outer与inner两层external observer证据、mode-discriminated receipt、独立720/2640/600/2520/2400/120字段、pending primary/marker/inner-exec/outer receipts与三相completion envelopes完整；
- KAT覆盖共同publisher same-dir temp/no-overwrite link/identity/nlink/fsync/rollback/crash-temp，supervisor两mode subreaper/set-empty/唯一direct child、stable identity/adoption及cooperative/ignore TERM；outer driver覆盖CLOEXEC error pipe的fork-fail null PID、exec-fail actual PID、exec-success EOF、supervisor early-exit、raw wait、timeout/interrupt/泄漏child；全部failure证明nonzero/no-replay/no-envelope、`ECHILD`、live/zombie0；
- 七tool inventory、两路KAT primary/tool review及outer/supervisor/capture/context/reducer/recheck/provenance三类primary都携带自身closed `dependency_loads`，actual trace/cardinality/order/load_count1、KAT/review typed refs与scalar types、reviewer raw-UTF-8 sort、ordinal 0/1及逐ordinal decode/cross-pair全绿；
- controller inner层另覆盖identity fallback、TimeoutExpired后communicate、leader-exited/live-grandchild与clean PGID空集；
- marker与failure diagnostic KAT覆盖共同publisher全部步骤、schema/publication token、link后同inode/nlink2、unlink/second-fsync后ENOENT+nlink1、额外hardlink拒绝、rollback/diagnostic与compound fault；
- context exact import API、validator_call七项JSON-safe projection，以及context/reducer/recheck full argv/versioned primary/exec/outer strict schemas与conditional fields冻结；capture/context/reducer三层receipt path/SHA/argv/streams双向绑定，seven-argument context对18 slots/36 singleton final-only lanes严格通过、`sta/`全absence且PID能力边界如实；
- authoritative run exact 3 case×6 repeat×2 lanes，correctness PASS；
- reducer/recheck按exact top-level/rows/tokens/CANON preimage独立得到相同18 timing/18 storage/9 aggregate与hash；
- 33 unique object compile evidence、三对象recursive ldd closure及actual非uniform flags完整；
- phase manifest/pending primary/completion envelope三versioned strict schemas及negative KAT全绿；POST `expected_outputs == [post_manifest.path]`，`post-evidence.accept-manifest-only`与`post-evidence.reject-manifest-plus-primary`双路KAT全绿；独立repair domain在PRE/POST/FINAL exact不变，六Step8/两repair及两个重复位点/input/current-plan/report-row semantic projection双端反绑。actual common/provenance prior later-helper KAT证明只存储prior top-level report source而继续fresh反绑input/preimage/fixed refs；PRE fresh-helper与FINAL transition-inputs later-helper caller-boundary KAT均在读取对应observer前命中唯一helper。三相五件链各自证明outer rc0、shared inputs相同、fresh PRE=POST；publish-report post-publication mirror与FINAL只以独立开关对POST/PRE shared baseline及历史actual中的同一exact report row启用stored-only窄例外，四处row full identity exact等于`target_before`、before/after path exact report target、FINAL target ref exact投影`target_after`，任一第二stale path或scope漂移拒绝，当前FINAL actual仍fresh；post/final artifacts相同且failure/temp均absence；
- provenance publisher exact CLI/API与transition primary+inner-exec+outer链完整；KAT覆盖POST manifest-only边界、post-publication later-mode实际caller链、source/target/old-row full identity/lock/temp/rename/diff/crash/人工direct-write及FINAL target path/SHA投影，FINAL仅untracked且HEAD/index-absent report atomic raw-byte delta；旧gVLAN两目录与e23 pre-KAT候选保持只读、零跨引，WALm预留run-root保持ENOENT；
- modeled storage、unsupported/fallback=0、non_comparable/not-claimed均写清；
- preserved两文件与37 parent pyc逐相不变，Step8 external cleanup receipt及独立plan-review repair evidence已绑定，PRE/POST/FINAL child pyc/cache均fresh exact absent且Step9未执行cleanup，source hygiene通过；
- final report是真实as-built但仍写Stage 2进行中；
- 两路final reviewer无finding；
- parent/child未commit、未push，外层计划未更新。

## 10. Step 10 local-only handoff

### 10.1 不可重排顺序与clean语义

仅在Step9 final APPROVE后：
先在validated ignored build tree内materialize唯一单文件`ABS_STEP10_TOOL=step10_local_handoff.py`；wrapper、transaction command-agent、journal validator、publisher与re-entry逻辑都来自该文件，禁止repo/sibling import、动态代码、shell或PATH lookup。agent只可由已验证并加载该source的wrapper fork进入同一代码，不得换文件/解释器。prefix exact `[ABS_NIX_PYTHON,"-B","-I","-S",ABS_STEP10_TOOL]`，tool path在`argv[4]`；入口复验§4.1 Python realpath/SHA与四flags，每次退出后fresh证明child pyc/cache absent。

Step10开始前须冻结tool bytes/SHA、canonical Git bytes/SHA、operational CLI、journal validator及下述review-only KAT receipt，并取得两名不同reviewer对同一v0.31 plan、Python、tool、Git与KAT exact refs的APPROVE。`ABS_STEP9_PLAN`固定为canonical `/home/shigure/code/ecc/docs/incregpusta/stage2-step9-plan.md`。统一closed `step10_typed_ref_v1` schema token exact `ista-csr-step10-typed-file-ref/1.0.0`，keys exact `schema,ordinal,role,path,sha256`；ordinal为拒绝bool的nonnegative integer，role服从owner schema的fixed enum/order，path为canonical absolute UTF-8 regular-file path且拒绝relative、dot-component、symlink component及alias，SHA为fresh single-open→fstat→完整read→second-fstat所得64位lower-hex raw-bytes SHA。所有nested递归`additionalProperties=false`。

tool-review token更新为 exact `ista-csr-step10-tool-review/1.1.0`，top-level exact `schema,reviewed_refs,kat_registry_sha256,reviewer_id,decision,findings`。`reviewed_refs`须byte-exact等于§10.1 start bundle ordinal `0,1,2,3,5`，role依次 `plan,python,tool,git,kat_receipt`；`kat_registry_sha256`等于strict解码KAT receipt所得值。decision exact `APPROVE`、findings exact empty；两reviewer id distinct，并按reviewer_id raw UTF-8严格升序分别映射后述`tool_review_a,tool_review_b`。missing/reordered/duplicate `-B/-I/-S`、old `argv[3]` locator、direct agent entry或任一path/identity/SHA/schema/cross-binding漂移均在任何control/Git namespace mutation前拒绝。
`reviewer_id`必须为nonempty UTF-8 string并拒绝NUL/CR/LF，`kat_registry_sha256`为64位lower-hex；两份review只按reviewer_id raw UTF-8 bytes严格升序映射A/B，禁止casefold或locale排序。


single-file tool在所有operational grammar之外只允许一个互斥review-only入口：

~~~text
review-kat --scratch-dir ABS_KAT_SCRATCH --plan ABS_STEP9_PLAN --plan-sha256 SHA --git ABS_GIT --git-sha256 SHA --receipt ABS_KAT_RECEIPT
~~~

actual full argv必须exact `[ABS_NIX_PYTHON,"-B","-I","-S",ABS_STEP10_TOOL,"review-kat",...]`并服从上列option order。`review-kat`不得接受`--control-dir`或任何start/resume/abort option，不得读取或修改真实CONTROL namespace、两仓refs/index/worktree或外层计划；除initially-ENOENT、validated ignored build-tree scratch及initially-ENOENT receipt target外不得写path。它只在fresh disposable fixtures运行§10末尾全部registered KAT，receipt用same-dir no-overwrite hardlink publisher发布，成功stdout exact为receipt canonical path+LF、stderr empty；任一case或cleanup失败均nonzero且final receipt absent。

KAT receipt token exact `ista-csr-step10-review-kat-receipt/1.0.0`，top-level exact `schema,publication_contract,subject_refs,argv,cwd,receipt_path,scratch,case_registry,registry_sha256,case_count,cases,cleanup,planned_stdout_size,planned_stdout_sha256,complete`。`subject_refs` exact四项且byte-exact等于start bundle ordinal `0..3` 的 `plan,python,tool,git`；argv与上述grammar逐项相等。scratch exact `path,dev,ino,uid,mode,start_empty,end_inventory_sha256`，mode exact0700、start_empty true。tool源码内literal `CASE_REGISTRY` row exact `ordinal,case_id,expected_outcome`，ordinal contiguous、case_id unique，expected outcome只允许`accept|reject|nonzero-no-replay|crash-recover`；registry/count/hash自洽并须覆盖§10末尾每个mandatory KAT。cases row exact `ordinal,case_id,expected_outcome,observed_outcome,returncode,stdout_size,stdout_sha256,stderr_size,stderr_sha256,artifact_inventory_sha256,passed`并逐ordinal匹配registry，passed全true。cleanup exact `live_count,zombie_count,unowned_path_count,repo_delta_count,control_escape_count`且全0；accepted receipt固定`publication_contract="hardlink-no-overwrite-v1",complete=true`，planned stdout绑定receipt path+LF，receipt不得包含自身SHA。
该Step10 KAT receipt的所有integer均要求`type(value) is int`并拒绝boolean；ordinal/count/dev/ino/uid/size服从§4.3 U64，mode exact0700，case returncode exact `0..255`，所有SHA为64位lower-hex。scratch/cwd/receipt path均为canonical absolute，scratch path与CLI `--scratch-dir`、receipt_path与CLI `--receipt` byte-exact；`case_id`匹配`[A-Za-z0-9][A-Za-z0-9._-]{0,127}`，observed outcome使用与expected相同enum并逐ordinal相等，registry/cases ordinals与case_count共同构成`0..N-1`。cleanup五个count均为U64 exact0；planned stdout size/SHA绑定receipt path+LF。


operational public CLI只允许以下三个subcommand及exact option order，不允许abbreviation/duplicate/unknown/positional remainder；`review-kat`只服从上列独立grammar，永不进入operational parser：

~~~text
start --control-dir ABS_CONTROL_DIR --git ABS_GIT --git-sha256 SHA --step9-final ABS_STEP9_FINAL --step9-final-sha256 SHA --kat-receipt ABS_KAT_RECEIPT --kat-receipt-sha256 SHA --identity-input ABS_IDENTITY_JSON --identity-input-sha256 SHA --child-path-manifest ABS_CHILD_PATHS --child-path-manifest-sha256 SHA --child-review-a PATH --child-review-a-sha256 SHA --child-review-b PATH --child-review-b-sha256 SHA --tool-review-a PATH --tool-review-a-sha256 SHA --tool-review-b PATH --tool-review-b-sha256 SHA
resume --control-dir ABS_CONTROL_DIR --parent-path-manifest ABS_PARENT_PATHS --parent-path-manifest-sha256 SHA --parent-review-a PATH --parent-review-a-sha256 SHA --parent-review-b PATH --parent-review-b-sha256 SHA
abort --control-dir ABS_CONTROL_DIR
~~~

`start`首次创建事务；process crash后只允许完全相同frozen input重入。`resume`只接受fixed locator指向`AWAITING_PARENT_APPROVAL`，或同一parent bundle重入已开始resume；`abort`只对至少已有durable INIT的nonterminal事务执行cleanup/rollback。bootstrap-ready以及BOOTSTRAP active的`EMPTY|TEMP_ONLY`因尚无canonical durable INIT，只能由exact `start`推进；BOOTSTRAP active的`FINAL_ONLY|FINAL_PLUS_TEMP`已存在canonical INIT，任一operational subcommand在入口/Python/tool/DirIdentity gate后、完整普通CLI/state authorization前，均只凭active+journal完成publisher cleanup与ordinary BOOTSTRAP→INIT locator transition，随后重新进入正常parser：resume因latest INIT正常拒绝，abort进入rollback，start仍须完整bundle exact。pause stdout必须为CANON object、top-level exact `approval_request_path,approval_request_sha256,awaiting_state_sha256,child_commit,state,terminal`加LF；path/SHA绑定durable request，awaiting SHA只能取更新后active locator actual journal SHA，`state="AWAITING_PARENT_APPROVAL",terminal=false`。不得从planned或尚未发布state预填，也不得写Step10/Stage2完成。

`ABS_CONTROL_DIR`须由owner预先创建为validated ignored build tree内的canonical、non-symlink、current-uid、mode0700目录并排除于Git-visible/approved/source-owned集合；同一预备步骤还须创建regular/current-uid/mode0600/nlink1的`step10.flock`以及non-symlink/current-uid/mode0700的`transactions/`、`terminals/`，wrapper不得创建或替换这三个固定对象。fixed layout only `step10.flock,active.json,.active.bootstrap.ready,.active.transition.ready,transactions/,terminals/,outer-plan.lock`；两个ready只允许存在于对应publication crash window，steady state均ENOENT且不得有其他active temp basename；txn只可为transactions dirfd下的`TXN_ID` exclusive mkdir mode0700。

`DirIdentity` exact keys为`path,dev,ino,uid,mode`；path为canonical absolute string，四个stat字段为拒绝bool的nonnegative integer，mode exact0700。Step10 `FileIdentity` exact `path,dev,ino,uid,mode,size,nlink,sha256`；path canonical absolute，六个stat数量字段为拒绝bool的nonnegative integer，mode=`stat.S_IMODE(st_mode)`，SHA为raw bytes lower-hex。`FileRef` exact `path,identity`且两path相同；identity只能null或该closed type。每次调用以CONTROL dirfd及`openat(...,O_NOFOLLOW|O_CLOEXEC)`打开预存flock、transactions与terminals，后两者另带`O_DIRECTORY`；取得`LOCK_EX|LOCK_NB`后冻结CONTROL/transactions/terminals三个DirIdentity并与start bundle、bootstrap/active locator及全部journal byte-exact交叉。每次bootstrap前及每次调用还必须fresh要求`control_dir_identity.dev == terminals_dir_identity.dev`；不等时在任何Git/control publication、link或unlink前拒绝。wrapper、agent、Git均不得替换目录，flock/transactions/terminals三个FD不得由agent/Git继承。所有transactions inventory、`mkdirat`与fsync只用transactions dirfd；所有terminal inventory、`linkat`、`unlinkat`与fsync只用terminals dirfd，禁止含`/`的相对pathname或跟随intermediate symlink。flock仅序列化cooperative wrapper。

`active.json` locator token更新为 exact `ista-csr-step10-active-locator/1.4.0`，top-level exact `schema,publication_contract,durability_scope,control_dir,control_dir_identity,lock_path,active_path,transactions_dir_identity,terminals_dir_identity,txn_id,txn_dir,terminal_path,tool_path,tool_sha256,start_input_bundle,start_inputs_sha256,previous_locator_sha256,journal_sequence,journal_sha256,state`。`start_input_bundle`从BOOTSTRAP起始终为下述完整closed object且永不为null；`start_inputs_sha256=sha256(CANON(start_input_bundle))`。三个DirIdentity须分别byte-exact等于bundle字段并跨locator永久不变，且control/terminals dev exact相等；tool ref须与locator tool path/SHA及actual `argv[4]`交叉。每次ordinary locator及最终terminal都从old locator byte-exact复制bundle/digest；INIT及其后每个journal的bundle/digest须与expected-old、current locator双向一致，previous-locator SHA因而同时绑定完整bundle。任一object/digest、locator/journal或typed-ref slice不等均在namespace/repo mutation前拒绝。publication exact `active-locator-bootstrap-link-transition-rename-v1`、scope exact `process-crash-only-v1`。bootstrap state exact `BOOTSTRAP`，previous/sequence/journal SHA三者null；其余locator中previous等于old active raw SHA，sequence nonnegative、journal SHA lower-hex且state等于journal state；`lock_path,active_path,txn_dir,terminal_path`从BOOTSTRAP到terminal永久byte-exact，resume/abort禁止caller传txn path。
`TXN_ID`是ASCII string并匹配`^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`，因此拒绝empty、`.`、`..`、slash、backslash、NUL与非ASCII。所有locator path均为nonnull canonical absolute string并满足：`control_dir == control_dir_identity.path`；`transactions_dir_identity.path == control_dir + "/transactions"`；`terminals_dir_identity.path == control_dir + "/terminals"`；`txn_dir == transactions_dir_identity.path + "/" + txn_id`；`lock_path == control_dir + "/step10.flock"`；`active_path == control_dir + "/active.json"`；`terminal_path == terminals_dir_identity.path + "/terminal." + txn_id + ".json"`。这些path按角色不得alias，`txn_dir`与`terminal_path`从BOOTSTRAP/INIT起永久byte-exact；实际namespace mutation仍只用validated dirfd与single-component basename，不把持久化absolute path直接交给mutation syscall。


`start_input_bundle` token更新为 exact `ista-csr-step10-start-input-bundle/1.1.0`，top-level exact `schema,entries,control_dir_identity,transactions_dir_identity,terminals_dir_identity,start_argv`。entries为exact十二项`step10_typed_ref_v1` array，ordinal/role固定为：`0 plan,1 python,2 tool,3 git,4 step9_final,5 kat_receipt,6 identity_input,7 child_path_manifest,8 child_review_a,9 child_review_b,10 tool_review_a,11 tool_review_b`。全部path互不alias；ordinal8/9与10/11分别按各receipt reviewer_id raw UTF-8升序映射A/B，不按caller任意命名。

`plan` path固定`ABS_STEP9_PLAN`；python/tool分别绑定actual process `argv[0]`/`argv[4]`；git及ordinal4..11逐项绑定start CLI path/SHA。`step9_final`必须strict解码为`ista-csr-step9-phase-completion-envelope/1.0.0`、phase final、`evidence_verdict="accepted",complete=true`，并沿其manifest→measurement_inputs.tool_inventory→tool review refs证明Step9 plan SHA exact等于ordinal0。`kat_receipt`必须strict解码为上述review-KAT schema且subject refs exact等于ordinal0..3。identity、child manifest、child reviews、tool reviews分别strict解码为其versioned closed schema；child manifest须repo child，两child review须APPROVE/distinct并绑定ordinal0/2/7，两tool review须APPROVE/distinct且reviewed_refs等于ordinal0,1,2,3,5。任何schema、bytes SHA、role/ordinal、同SHA换path、A/B互换或cross-binding错误均拒绝。

`start_argv`为从字符串`start`起至最后一个tool-review SHA止、包含新增Step9 FINAL/KAT四参数并与actual public CLI完全同序的string array。`start_inputs_sha256=sha256(CANON(start_input_bundle))`，不得只hash entries、argv或显示文本。BOOTSTRAP locator首次持久化完整bundle；INIT的`inputs.start_input_bundle`再次byte-exact持久化，之后全部forward、pause、rollback、terminal locator/journal永久保留同一object与digest，不得刷新、清null或仅保存digest。

CONTROL_DIR为single-use。fresh start要求active与两个ready均ENOENT、terminals inventory exact empty、transactions inventory exact empty；terminal发布后该目录永久只代表同一TXN，后续subcommand只可验证/返回同一terminal outcome，禁止第二事务，terminal第二entry、unknown basename、wrong identity/TXN均unresolved。只有全部入口/Python/tool/start-bundle验证通过的exact `start`才可创建或恢复bootstrap ready、BOOTSTRAP active、txn mkdir，以及在`EMPTY|TEMP_ONLY`中创建/完成INIT。`resume`或`abort`遇bootstrap-ready，或active为BOOTSTRAP且txn为absent/`EMPTY|TEMP_ONLY`时，除打开预存flock与只读分类外必须nonzero拒绝：不得unlink、mkdir、发布journal、读写repo；owner须以相同start bundle重入至canonical INIT durable。`FINAL_ONLY|FINAL_PLUS_TEMP`则按上文由任一subcommand只完成publication repair/locator transition。

exact start在flock内先分类bootstrap-ready：ready完整且active ENOENT时，canonical locator必须匹配本次tool/start bundle/DirIdentity且txn target仍ENOENT，才补link/fsync/unlink/fsync；partial/noncanonical ready只有在active与transition-ready均ENOENT、transactions/terminals均empty、ready为current-uid regular/0600/nlink1时才可unlink+CONTROL fsync后以同bundle fresh重建；ready与active并存只在same inode/bytes/nlink2时补unlink/fsync。任何different inode/bytes、wrong bundle/identity、extra entry或unreferenced txn均unresolved。
fresh start选择TXN_ID并要求target ENOENT，严禁先mkdir；bootstrap locator绑定完整start bundle/digest和三个DirIdentity，以fixed ready执行exclusive write/fsync/reopen→no-overwrite hardlink到active→同inode/nlink2→CONTROL fsync→unlink ready→active nlink1→再次fsync。active durable后才用transactions dirfd `mkdirat(TXN_ID,0700)`并fsync。合法BOOTSTRAP active与exact start bundle匹配后，txn目录只允许四种exclusive inventory：`EMPTY`无entry，仅exact start fresh发布INIT；`TEMP_ONLY`只有deterministic `.state.000.TXN_ID.tmp`，仅exact start可在完整canonical INIT时完成link/fsync/unlink/fsync，或在partial/noncanonical、final ENOENT、temp current-uid regular/0600/nlink1且无其他entry时unlink+txn-dir fsync后fresh发布；`FINAL_ONLY`只有`state.000.json`，须为canonical INIT、regular/current-uid/0600/nlink1且txn/start bundle/directory identity/sequence0/previous-null/expected BOOTSTRAP全exact，任一subcommand在入口gate后继续ordinary locator transition；`FINAL_PLUS_TEMP`只含二者且same dev+ino/canonical bytes/nlink2，任一subcommand只unlink temp、fsync、复验final nlink1后继续ordinary transition。额外entry、wrong basename/inode/nlink/mode/uid、非INIT、错误bundle/directory identity均unresolved；未被唯一active或唯一valid terminal引用的txn-dir（包括empty）都是真正preexisting conflict，禁止删除/领养。

每次ordinary transition严格按 `H_old locator → H_state journal → H_new locator`：持flock no-follow读取old active并冻结raw SHA与`FileIdentity`；new journal的`locator.expected_old_active`写入该identity并先durable发布，journal绝不包含planned/new locator SHA或transition-ready identity/hash。随后只由H_old、H_state与frozen locator fields构造H_new，以fixed `.active.transition.ready`执行exclusive create/0600、完整write/fsync/close/reopen/bytes+identity验证；紧邻rename前fresh要求active仍为expected H_old，匹配才`renameat(transition-ready,active)`→CONTROL_DIR fsync→nofollow复验active H_new且ready ENOENT。该fixed ready是locator publisher的唯一专用例外，不进入通用`temp_ledger`，避免为记录其SHA而把H_state与H_new形成环。

ordinary crash recovery只允许：old active加唯一合法next-sequence journal且transition-ready ENOENT时从二者重构ready；ready完整时须exact等于同一重构H_new才继续rename；ready为current-uid regular/0600/nlink1但partial/noncanonical时，只有old active与唯一next journal均严格有效且无第二candidate时才unlink+dir-fsync后重构。active已为H_new且ready ENOENT视transition完成。两个next journal、ready与重构bytes不等、wrong expected-old、跨sequence或任何txn/hash漂移均unresolved；terminal publication前active不得unlink。

三subcommand取得预存flock后只先解析exact subcommand与`--control-dir`。任何BOOTSTRAP/terminal namespace mutation前必须完成entry gate：复验raw process prefix、Python realpath/bytes SHA与`-B/-I/-S`，复验当前tool realpath/no-follow identity/bytes SHA，并与待修复active或唯一terminal locator及其final journal中的tool ref交叉；同时复验CONTROL、transactions、terminals DirIdentity与`control.dev==terminals.dev`。wrong Python/tool/directory identity或cross-device必须零link/unlink、零Git/control publication。

随后strict验证publication slice：locator canonical/schema/hash、TXN_ID、final journal bytes/SHA、state exact `AUDIT_COMPLETE|ROLLED_BACK`、terminal basename及active/terminal identity关系全绿后，才执行terminal publication-only repair。repair不spawn agent/Git、不读写repo/普通journal；其余CLI options和repo/input preflight在repair后从头执行，因此合法tool加非法额外CLI仍先完成已有terminal repair再由完整parser拒绝；其他terminal/active组合unresolved。


INIT先以exact两项HookDirRow durable保留`EMPTY_HOOKS_CHILD`、`EMPTY_HOOKS_PARENT`的deterministic txn path与expected absence；`HOOKS_PREPARE_INTENT`后wrapper才按ordinalexclusive `mkdir`，完成两次no-follow identity/empty验证与txn-dir fsync并发布`HOOKS_READY`。两absolute realpath必须位于validated ignored child build-tree、彼此不同、non-symlink/current-uid/mode0700，且排除于两仓全部Git-visible path inventory、approved stage paths与source-owned paths集合。任一Git invocation前必须已是HOOKS_READY；各仓command前后、pause/resume/abort及最终audit都按HookDirRow复验same identity/exact empty，wrapper audit须拒绝其进入stage/commit。
`STEP10_TXN_DIR`只由fixed locator定位并容纳journal、receipts、PVT、preimage backups、两hooks dirs与exact-own temps；wrapper拒绝CONTROL_DIR及其全部children进入两仓stage/commit。partial hooks create只按durable RESERVED rows恢复，退出pause时保留READY并由resume/abort复验，不能fresh换目录；terminal只按ledger RETAINED-empty或CONSUMED-absent，不存在未记录的hooks owner。

Step10 wrapper先从owner-configured absolute path用stdlib `realpath/lstat/open`冻结canonical Git executable为 `ABS_GIT`，记录path/dev/inode/mode/bytes SHA；禁止PATH lookup、`which`、shell或后续换binary。任一命令前后binary identity/bytes不一致即停止。
wrapper另要求owner-supplied `--identity-input ABS_IDENTITY_JSON`。其schema token exact `ista-csr-step10-owner-identity-input/1.0.0`，top-level exact `schema,child,parent,author_date,committer_date`；child/parent各exact `author_name,author_email,committer_name,committer_email`。以canonical no-follow regular/current-uid file读取canonical JSON；四name/email均UTF-8 trim后非空且无NUL/CR/LF，email不得含空白，dates均exact `YYYY-MM-DDTHH:MM:SS+00:00`。preflight在任何Git/private staging前冻结path/identity/bytes SHA与字段，rollback/retry不得刷新；missing/extra/type/empty/invalid立即no-spawn。不得写或依赖repo/global/system user config。

child与parent manifest必须分两阶段产生/批准。真实Step9 final后owner先列literal child paths并取两份独立APPROVE；`start`只接受child manifest/reviews。start在private PVT完成并生成共享object store中的`CHILD_CANDIDATE`后，live child/parent refs、indexes、worktree仍须byte-exact PRE；它发布parent approval request并停在`AWAITING_PARENT_APPROVAL`。owner只能用该request的actual CHILD_COMMIT生成parent manifest并再取两份独立APPROVE；`resume`绑定后先journal `PARENT_APPROVED`，才允许任何live index/ref mutation或parent PVT。`abort`从pause只清理exact-own PVT/control artifacts；共享未引用candidate objects记录后可保留，live状态仍PRE。

manifest token exact `ista-csr-step10-approved-path-manifest/1.1.0`；top-level exact `schema,repo,base_oid,entries`，entry exact `path,disposition,kind,mode,worktree_sha256,target_oid`。repo/disposition/kind/mode/path为string，hash/OID为nullable string；repo只`child|parent`、base OID lower-hex。path必须nonempty canonical repo-relative UTF-8、只用`/`，拒绝absolute、NUL、backslash、leading/trailing slash、empty/`.`/`..` component；entries按`path.encode("utf-8")`升序且无重复。regular只允许disposition `tracked|new`、mode `100644|100755`、worktree SHA lower-hex且target OID null；gitlink只允许parent、tracked、mode `160000`、worktree SHA null、target OID lower-hex且exact request CHILD_COMMIT，其他组合/symlink/tree mode均拒绝。tracked须在BASE/real index为stage0同mode/OID，new须HEAD/index absent；child base exact CHILD_BASE、parent base exact PARENT_BASE，FINAL report是parent唯一approved regular new。parent排除`CLAUDE.md`/meeting report，两仓都排除build/evidence/control/journal/tool/receipt；PATHS只等于reviewed entries order，禁止dirty/status/glob推导，所有nested additionalProperties=false。
`approved_manifest_snapshot_v1` token exact `ista-csr-step10-approved-manifest-snapshot/1.0.0`，top-level exact `schema,role,source_path,source_sha256,manifest`；role exact `child|parent`且必须等于`manifest.repo`，manifest为完整strict `ista-csr-step10-approved-path-manifest/1.1.0` object，`sha256(CANON(manifest)) == source_sha256`，source path/SHA byte-exact等于对应typed ref，entries保留原approved order，所有nested closed。INIT从start bundle ordinal7持久化`role=manifest.repo=child` snapshot并与该row的path/SHA交叉；parent snapshot在BIND_INTENT details首次持久化，固定`role=manifest.repo=parent`且source path/SHA byte-exact等于同一details的`parent_input_bundle.entries[0]`；正常PARENT_APPROVED与BIND→ROLLBACK把snapshot、bundle及refs byte-exact复制到inputs后，snapshot还必须与`inputs.parent_refs[0]`交叉。snapshot只提供recovery history，forward仍须fresh验证external ref；一旦出现即永久不变，rollback只读snapshot、不打开source path。


path-review token exact `ista-csr-step10-path-review-receipt/1.0.0`，top-level exact `schema,repo,manifest_sha256,txn_id,awaiting_state_sha256,approval_request_sha256,child_commit,plan_sha256,tool_sha256,reviewer_id,decision,findings`。child receipt四transaction fields必须null；parent四者绑定active locator实际指向的`AWAITING_PARENT_APPROVAL` journal SHA、request SHA及CHILD_COMMIT。每仓exact两份、reviewer distinct、decision exact `APPROVE`、findings empty，禁止跨repo/txn/tool/plan复用。

`parent_input_bundle_v1` token exact `ista-csr-step10-parent-input-bundle/1.0.0`；top-level exact `schema,entries`。entries为exact三项array，每row exact `ordinal,role,path,sha256`：ordinal为拒绝bool的integer且依次`0,1,2`，role依次`manifest,review_a,review_b`；path为对应resume CLI值的canonical absolute UTF-8 path，拒绝relative、dot-component、symlink component及三项alias/duplicate；sha256为CLI值、64位lower-hex且与fresh no-follow regular-file bytes exact。nested递归`additionalProperties=false`；`parent_input_bundle_sha256=sha256(CANON(parent_input_bundle))`，不得只hash entries、显示文本或不同排序。

approval-request token exact `ista-csr-step10-parent-approval-request/1.0.0`，top-level exact `schema,txn_id,child_candidate_state_sha256,child_commit,parent_base_oid,required_report_path,required_report_sha256,required_gitlink_path,plan_sha256,tool_sha256`。active已指向durable CHILD_CANDIDATE后，先发布request INTENT，no-overwrite发布并复验request后发布intent-null REQUESTED，再发布intent-null AWAITING并推进active；AWAITING inputs中的awaiting SHA/bundle/hash/parent refs仍null，pause/reviews只读post-publication AWAITING journal SHA。request不得引用future AWAITING SHA，AWAITING不得含自身SHA，parent review必须绑定actual AWAITING SHA。`resume`每次调用及process-crash forward re-entry都须在任何agent/Git/private-stage/live mutation前从六个parent CLI path/SHA参数fresh重构exact bundle/hash；latest为BIND_INTENT时须与details byte-exact，PARENT_APPROVED或后续forward state时须与persistent inputs byte-exact。AWAITING首次resume把完整bundle/hash及actual AWAITING SHA写入BIND_INTENT；随后intent-null PARENT_APPROVED才从details复制进inputs，禁止取immediate previous SHA。

fresh external parent bundle只授权继续forward，绝不授权、延迟或阻断rollback。`abort`及fault-triggered rollback在durable INIT后不得fresh打开、rehash或依赖任何start/parent external input path：BIND_INTENT从durable intent details取得parent bundle，PARENT_APPROVED及其后从durable inputs取得，较早state不需要parent bundle；start bundle始终取locator/journal中的永久canonical object。外部输入在任何live mutation前缺失/漂移时停止forward、no-spawn/no-Git，并仍允许owner abort；在child index/ref或其后live mutation后发现时，先append closed `parent_external_input_drift` error并只凭durable journal/PRE backups进入rollback。外部plan/FINAL/KAT/identity/manifest/review文件缺失、漂移或被移动不得成为rollback cleanup target或使PRE恢复unresolved；只有journal chain、事务内PRE backup或actual repo/outer postcondition自身损坏才可阻断恢复。

两仓每个Git invocation（含config/check-attr/private-add/status/diff/show/ls-files/cat-file/ls-tree/write-tree/commit-tree/update-ref/ref audit）都经同一个canonical launcher。`git_command_env_v1`是closed three-branch union：ordinary分支exact 11 keys，为`GIT_ATTR_NOSYSTEM,GIT_CONFIG_NOSYSTEM,GIT_CONFIG_GLOBAL,GIT_OPTIONAL_LOCKS,GIT_TERMINAL_PROMPT,GIT_EDITOR,GIT_SEQUENCE_EDITOR,LC_ALL,TZ,GIT_OBJECT_DIRECTORY,GIT_INDEX_FILE`；前九项分别固定为`1,1,/dev/null,0,0,:,:,C,UTC`，后两项byte-exact绑定该repo的`ABS_OBJECT_DIR`及该命令的PVT/live-index。commit-tree分支exact17 keys，另加owner input的`GIT_AUTHOR_NAME,GIT_AUTHOR_EMAIL,GIT_AUTHOR_DATE,GIT_COMMITTER_NAME,GIT_COMMITTER_EMAIL,GIT_COMMITTER_DATE`；ref-update/ref-restore分支exact14 keys，只另加owner input的三个`GIT_COMMITTER_NAME,GIT_COMMITTER_EMAIL,GIT_COMMITTER_DATE`以确定reflog bytes。其他命令禁止这些identity/date key；10/12/13/15/16/18 keys、wrong object/index binding或任何ambient extra key均拒绝。`env_sha256=sha256(CANON(env))`并与spawn/agent-report/result双向一致。

actual argv exact prefix为 `ABS_GIT --no-pager --literal-pathspecs --git-dir=ABS_GIT_DIR --work-tree=ABS_WORKTREE -c core.hooksPath=ABS_EMPTY -c core.fsmonitor=false -c core.attributesFile=/dev/null -c core.splitIndex=false SUBCOMMAND ...`；`commit-tree`另带`-c commit.gpgSign=false commit-tree ... --no-gpg-sign`。pre-freeze candidate add/check-attr/ls-files/cat-file/write-tree显式绑定事务内`GIT_INDEX_FILE=PVT_INDEX`，其余read-only audit及post-freeze hash/commit-tree/update-ref/status绑定`GIT_INDEX_FILE=ABS_INDEX`并证明live raw index不变。所有receipt逐命令记录object/index binding，禁止真实`git add/reset/commit`触碰ABS_INDEX。

launcher在清空env前审计caller env：任何未批准 `GIT_*` 或批准key的非冻结值都记录name/value SHA并hard fail，不得仅覆盖后继续；caller若含`GIT_OPTIONAL_LOCKS`只允许字符串exact `0`，spawn则无条件携带exact `GIT_OPTIONAL_LOCKS=0`。拒绝项包括但不限于 `GIT_DIR`、`GIT_WORK_TREE`、`GIT_COMMON_DIR`、ambient `GIT_INDEX_FILE`/`GIT_OBJECT_DIRECTORY`、`GIT_ALTERNATE_OBJECT_DIRECTORIES`、非allowlist `GIT_CONFIG_SYSTEM/GIT_CONFIG_COUNT/GIT_CONFIG_KEY_*/GIT_CONFIG_VALUE_*/GIT_CONFIG_PARAMETERS`、`GIT_PREFIX`、`GIT_SHALLOW_FILE`、`GIT_GRAFT_FILE`、`GIT_NAMESPACE`、`GIT_CEILING_DIRECTORIES`、`GIT_DISCOVERY_ACROSS_FILESYSTEM`、`GIT_QUARANTINE_PATH`、`GIT_NO_REPLACE_OBJECTS`、`GIT_REPLACE_REF_BASE`及 `GIT_EXEC_PATH/GIT_TEMPLATE_DIR/GIT_ASKPASS/GIT_EXTERNAL_DIFF/GIT_TRACE*`；实际spawn仍只收到上项empty-map allowlist，避免ambient自证重定向。

wrapper在任何Git调用前用stdlib/no-follow独立绑定两仓各自 `ABS_WORKTREE`、`ABS_GIT_DIR`、`ABS_OBJECT_DIR` 与common-dir的realpath/dev/inode/mode/uid；这些directory identities、canonical paths及argv/env绑定值必须跨全事务稳定，Git `rev-parse`只作交叉核对。`ABS_INDEX`的稳定合同只冻结canonical absolute path、其canonical containing parent directory的realpath/dev/inode/mode/uid、target no-follow regular/current uid/frozen mode；index target的dev/inode是单次generation identity，不得要求跨合法mutation永久不变。每条命令前后仍fresh复验alternates/grafts/shallow exact absent及replace/namespace refs absent/empty；任一稳定绑定或topology/query mismatch都在下一命令前hard fail。

两仓明确不支持linked/common-dir、split-index与per-worktree config：`ABS_GIT_DIR/commondir`和`config.worktree`必须no-follow ENOENT，canonical `rev-parse --git-common-dir`必须resolve exact `ABS_GIT_DIR`；raw local config的`extensions.worktreeConfig`与`core.splitIndex`须absent/false，`rev-parse --shared-index-path` rc0/stdout empty，git-dir下`sharedindex.*` inventory exact empty，live/backup/PVT raw index extension inventory均不得含`link`。这些状态在start、pause、resume每个mutation边界和final audit fresh复验；出现任一项立即no-mutation或journal rollback，不尝试兼容。

child worktree的`.git`必须是no-follow regular gitfile；冻结path/dev/ino/uid/mode/size/raw SHA，strict解析唯一`gitdir: PATH\n`且无CR/NUL/extra line，resolved canonical path exact `ABS_CHILD_GIT_DIR`。parent `.git`须为绑定的directory；parent tracked `.gitmodules`冻结no-follow identity/raw SHA及gitlink path→child worktree映射，child local `core.worktree`只用`--file ABS_CHILD_GIT_DIR/config --no-includes`读取并冻结raw value，其canonical resolution须exact `ABS_CHILD_WORKTREE`。这些bytes/resolutions在parent gitlink private stage前后、commit前后与audit后fresh exact；任一漂移停止/rollback。
每个以live `ABS_INDEX`运行的Git invocation（包括config/check-attr/status/diff/show/ls-files/ls-tree/rev-parse/ref audit及只改ref的`update-ref`）前后都要求`ABS_INDEX.lock` no-follow `ENOENT`，以`O_RDONLY|O_NOFOLLOW` open→fstat→read冻结generation `(dev,ino,uid,mode,size,sha256)`；命令后必须同一generation/raw SHA/metadata且lock仍absent。每个以`PVT_INDEX`运行的candidate命令前后也fresh证明live index完全不变；`GIT_OPTIONAL_LOCKS=0`是empty-map证明的一部分。
任何Git child都禁止直接mutation `ABS_INDEX`。pre-freeze candidate `add/check-attr/ls-files/cat-file/write-tree`只可改事务私有`PVT_INDEX`及object store；真实index唯一合法转换是wrapper在无Git child运行时按下述`ABS_INDEX.lock`协议安装candidate或restore backup。final PVT freeze后禁止任何Git命令再以PVT binding运行；post-freeze commit-tree/hash/ref/status命令绑定live index且须证明其raw bytes/inode不变。index-parent只允许owned lock；object-dir合法temp另审计。

第一条Git invocation前，wrapper对两仓validated `ABS_GIT_DIR/info/attributes` actual path做no-follow检查：只允许exact `ENOENT`，或current-uid、non-symlink regular file、size 0、SHA-256为empty bytes；冻结该absent/empty安全状态，并在staging前后、commit前后、final audit后复验state/metadata/bytes exact不变。wrapper记录每条actual env allowlist、argv array、cwd、returncode/streams，并用同一launcher读取effective config，要求`core.hooksPath`等于对应canonical empty dir、`core.fsmonitor=false`、`core.attributesFile=/dev/null`、上述config/env值exact，commit时另要求`commit.gpgSign=false`；任何query错误、ambient source未隔离、值漂移、info attributes或hooks变化都在stage/commit前hard fail。

同一preflight还以dirfd/no-follow冻结两仓`ABS_GIT_DIR/config` regular/current-uid raw identity/mode/size/SHA；canonical launcher执行`config --file ABS_GIT_DIR/config --no-includes --get-regexp '^include(If\..*)?\.path$'`必须raw rc1且stdout/stderr empty，证明local `include`/`includeIf` exact absent。每条Git命令前后fresh复验config raw identity/SHA不变，effective config query不得替代raw proof；config drift或include存在立即no-spawn/rollback，禁止自证式重定向。

任何private staging前，wrapper只从已冻结owner identity input取得两仓author/committer name/email与两date；name/email除既有限制外还须拒绝`<`与`>`，绝不查询、设置或假定local/global `user.name/user.email`。preflight要求两仓`rev-parse --show-object-format` stdout exact `sha1\n`。commit-tree-only env在base allowlist上仅增加对应`GIT_AUTHOR_NAME/EMAIL/DATE`与`GIT_COMMITTER_NAME/EMAIL/DATE`，receipts绑定identity-input SHA及actual六env。

child exact launcher suffix为`-c commit.gpgSign=false commit-tree CHILD_TREE -p CHILD_BASE -m "Implement Stage 2 IncreGPUsta benchmark" --no-gpg-sign`；parent exact suffix为`-c commit.gpgSign=false commit-tree PARENT_TREE -p PARENT_BASE -m "Document Stage 2 IncreGPUsta benchmark" --no-gpg-sign`。`-p`必须exact一次且紧跟对应BASE；missing/duplicate/additional/wrong parent、parent commit误以CHILD_COMMIT作direct parent均拒绝。rc0、stderr empty、stdout exact一条40位lower-hex OID+LF；禁止git commit/config mutation、amend/merge/reuse-message/editor/prompt/signing/交互，`--no-edit`不适用。

每个candidate在任何live index/ref mutation及对应CANDIDATE journal前，以live binding执行`git cat-file -t OID`要求`commit\n`，再`git cat-file commit OID`取得raw bytes。wrapper把冻结UTC date独立换算为epoch seconds并构造唯一raw preimage `tree TREE\nparent BASE\nauthor NAME <EMAIL> EPOCH +0000\ncommitter NAME <EMAIL> EPOCH +0000\n\nMESSAGE\n`；必须byte-exact，只允许一个tree/parent/author/committer与一个blank separator，拒绝第二parent、gpgsig、encoding、mergetag或extra/reordered header。独立计算`sha1(b"commit "+decimal_len+b"\\0"+raw)`须等于stdout OID，tree/parent/identity/date/message还须与journal、manifest、command receipt双向一致。

所有带path的Git命令使用global `--literal-pathspecs`、显式`--`与reviewed manifest exact path argv array，禁止glob/magic/shell expansion。每仓在staging前fresh重验manifest path/SHA/双审receipt、逐entry worktree bytes/mode/kind/target OID与全仓pre-stage index snapshot；任一未列dirty path只按preserved/deny规则审计，绝不自动加入。再执行不带`--cached`的NUL-safe `git check-attr -z filter -- PATHS`，要求每path filter exact unspecified。

`PREIMAGES` durable后，执行对应private add、安装live index及执行forward/rollback `update-ref`前，两仓都须fresh证明：HEAD OID分别exact expected BASE/current transaction commit，symbolic HEAD exact `refs/heads/IncreGPUSTA`、short branch exact `IncreGPUSTA`且非detached；no-follow检查`MERGE_HEAD/AUTO_MERGE/MERGE_MSG/MERGE_MODE/rebase-apply/rebase-merge/CHERRY_PICK_HEAD/REVERT_HEAD/sequencer/BISECT_LOG/BISECT_START/BISECT_NAMES/BISECT_EXPECTED_REV/BISECT_ANCESTORS_OK/BISECT_RUN/BISECT_TERMS`及common-dir `refs/bisect`全部absent。每个边界重做；任一漂移在live mutation前停止，mutation后只按journal恢复或unresolved。
任何private add前，两仓分别以reviewed manifests冻结approved literal path array及HEAD/live-index合同：tracked regular/gitlink在HEAD/index须各exact一条stage0且mode/OID相同；new path在HEAD/index均absent。parent manifest的report绑定§7.4 FINAL bytes/mode且仍HEAD/index absent；`CLAUDE.md`/meeting report若出现在manifest或stage inventory即hard fail。NUL-safe views拒绝intent-to-add/skip-worktree/assume-unchanged/conflict/duplicate/type异常并冻结全仓snapshot/status/diff。
上述前置全绿后以`O_RDONLY|O_NOFOLLOW` open→fstat→read→second-fstat冻结live pre-stage raw index `(dev,ino,uid,mode,size,SHA)`；在`STEP10_TXN_DIR`以exclusive no-follow/0600共同publisher写durable PRE backup并重读交叉hash。`PREIMAGES`只发布两仓raw backup/source generation及两个deterministic PVT path的`RESERVED/ENOENT` rows，绝不创建PVT或持久化private-index identity；各PVT只能在对应`*_PRIVATE_STAGE_INTENT` durable后初始化。所有forward state的`rollback_class`保持null；只有首次`ROLLBACK_INTENT`才按历史固定：尚无`CHILD_INDEX_INSTALL_INTENT`或其后任何live-mutation intent/actual mutation时为`no_live_mutation`，从durable `CHILD_INDEX_INSTALL_INTENT`起或已有本事务actual live mutation证据时一律`restore_preimages`。

只允许canonical launcher以`GIT_INDEX_FILE=PVT_INDEX`执行literal `git add -- PATHS`；它不得持有或创建`ABS_INDEX.lock`。private staging后以同paths/order执行`git check-attr --cached -z filter -- PATHS`并要求working/index逐path filter exact `unspecified`；NUL-safe staged inventory exact approved列表，live index前后raw generation仍PRE exact。任一extra/missing/type/mode、attribute或live-index漂移立即停止且不得安装PVT_INDEX。

private staging后禁止任何`git show :PATH`/index pseudo-revision。以PVT binding exact执行`git ls-files --stage -z -- PATHS`，NUL-safe解析每path唯一stage0 `(mode,oid,path)`，拒绝duplicate/conflict/intent-to-add/skip-worktree/assume-unchanged/type异常；regular逐OID执行`git cat-file blob OID`并要求raw bytes/SHA exact approved worktree，gitlink要求mode160000/OID exact CHILD_COMMIT且`git cat-file -t OID` stdout exact `commit\n`。随后以同PVT binding唯一执行`git write-tree`；wait/reap rc0后证明PVT lock absent，再冻结write-tree后的final raw/semantic `STAGED_INDEX_GENERATION`。此后禁止任何PVT invocation；用live binding `ls-tree -z STAGED_TREE -- PATHS`及`cat-file blob|-t`复验tree。只按上列exact`commit-tree TREE -p BASE -m MESSAGE --no-gpg-sign`生成candidate，full raw commit-object/OID validator全绿后才可durable记录`CHILD_CANDIDATE|PARENT_CANDIDATE`；全过程证明ABS_INDEX raw generation不变。
真实index安装只由wrapper syscalls完成：先durable写`INDEX_INSTALL_INTENT(expected_old_generation+SHA,planned_private_SHA)`，确认无transaction command-agent/Git child live，再以parent dirfd `O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW`/0600取得真正`ABS_INDEX.lock`并记录own identity。持锁后fresh no-follow重读`ABS_INDEX`，必须仍exact expected-old generation/SHA且lock仍own；否则不写、不rename、不覆盖并unresolved。
锁内匹配后把已验证PVT_INDEX exact bytes short-write到owned lock、fchmod PRE mode、file fsync/close，再以`renameat`把lock原子安装到`ABS_INDEX`并parent-dir fsync；fresh要求lock ENOENT、target path exact `ABS_INDEX`、current uid、mode exact PRE，并从actual target构造新的`LIVE_INSTALLED_GENERATION`。该generation的`size,sha256,semantic_sha256`必须byte-exact等于FROZEN PVT的`STAGED_INDEX_GENERATION`对应三字段；`dev,ino`采用fresh live target actual值且不得要求等于PVT。live index fsync/postverify全绿后才按intent的`PvtReleaseBinding` no-follow复验PVT仍exact current，随后以validated parent dirfd `unlinkat`、dir-fsync并fresh要求ENOENT；同一`INDEX_INSTALLED` completion journal同时令RepoState.current_index exact等于`LIVE_INSTALLED_GENERATION`并令对应PVT CONSUMED。crash re-entry在INSTALL_INTENT下只接受组合pre=`live old+PVT exists exact current`、intermediate=`live installed+PVT exists exact current`或post=`live installed+PVT ENOENT`，补足唯一剩余步骤后发布同一completion；`live old+PVT ENOENT`或任何第三态unresolved。该协议是Git-lock序列化的expected-generation install，不声称无锁kernel CAS。
stage/candidate/install failure不得运行`git reset`。若live index已由本事务安装，rollback用同一owned `ABS_INDEX.lock`协议，expected-old必须是journal记录的current transaction generation、install bytes为durable PRE backup；锁内mismatch不rename并保持unresolved。restore/no-op postverify raw/semantic/status/cached diff byte-exact PRE后，才按对应INDEX_RESTORE_INTENT的`PvtReleaseBinding`执行同样unlinkat+dir-fsync；同一`*_INDEX_RESTORED` journal令该PVT CONSUMED。RESTORE_INTENT re-entry只接受live transaction/PRE与PVT pre/ENOENT按operation顺序形成的唯一组合，补齐后completion；unknown组合unresolved。禁止`RENAME_EXCHANGE`、`reset --hard`、checkout、stash或任何worktree mutation；PVT_INDEX/候选objects只按journal ownership审计。
两个实际`refs/heads/IncreGPUSTA` reflog必须在PREIMAGES前fresh证明为no-follow regular/current-uid文件；其canonical path、validated parent identity、`ReflogGeneration(dev,ino,uid,mode,size,sha256)`及raw PRE backup `FileRef`进入事务内recovery preimage与reflog asset ledger，任一absent/symlink/extra hardlink或lock preexist均阻断本次Step10。forward/ref-restore的exact argv都带`-m "ista-step10:<TXN_ID>:<child|parent>-<publish|restore>"`，ref命令使用上述14-key env；wrapper从old/new OID、owner committer/date和message按Git reflog格式纯函数构造planned append bytes，并把ref与reflog合并纳入command observation。exec前后fresh要求ref lock与reflog lock均ENOENT。

forward成功保留唯一planned reflog append。rollback_class=restore_preimages的每个ref-restore INTENT是可重入两步操作：command-agent先以expected-old执行update-ref并产生唯一deterministic reverse append；agent/Git/group absent且command result accepted后，wrapper才以reflog parent dirfd exclusive创建actual `.lock`，紧邻写入前复验current reflog仍为该唯一intermediate generation，short-write PRE backup、fchmod PRE mode、file fsync、`renameat`、dir fsync并fresh复验raw bytes/generation exact PRE。crash recovery只接受forward preimage、deterministic reverse-append intermediate或raw PRE final三态；different bytes/inode、preexisting lock或并发writer均不覆盖并unresolved。ref restore completion只能在ref OID、reflog raw bytes、live index与status全部exact PRE后发布，因此restore_preimages类`ROLLED_BACK`的PRE claim明确包含两reflog；no_live_mutation类没有ref restore或PRE claim。不得把`update-ref`的reverse append本身冒充恢复完成。

`review-kat`须以fixture覆盖两个actual reflog均present的forward/restore、每个ref与reflog lock/write/fsync/rename窗口、deterministic message/committer/date、wrong append、lock conflict、wrapper crash处于reverse-append intermediate及最终PRE repair；每例证明不重复Git mutation、不覆盖unknown bytes。


1. `start`在`PREIMAGES` durable后只按child reviewed manifest生成/验证final PVT/tree/`CHILD_COMMIT`；不得取得`ABS_INDEX.lock`、不得安装live index、不得`update-ref`。fresh证明两仓refs/live raw+semantic indexes/worktree/status仍byte-exact PRE后，durable发布parent approval request，journal/locator到`AWAITING_PARENT_APPROVAL`并正常退出。
2. `resume`先strict绑定request/awaiting state与parent manifest两份review，记录`PARENT_APPROVED`；然后才按owned index.lock安装已冻结child PVT，再唯一执行`update-ref -m "ista-step10:<TXN_ID>:child-publish" refs/heads/IncreGPUSTA CHILD_COMMIT CHILD_BASE`。rc0且ref/HEAD/index/tree/status及deterministic reflog append全绿才记录`CHILD_COMMITTED`；expected-old失败不重试/覆盖。
3. child committed后才允许创建parent PVT，以request CHILD_COMMIT作为manifest唯一gitlink target、FINAL report为approved new；fresh复验child gitfile/core.worktree、parent `.gitmodules` mapping。生成candidate、安装index，再唯一执行`update-ref -m "ista-step10:<TXN_ID>:parent-publish" refs/heads/IncreGPUSTA PARENT_COMMIT PARENT_BASE`并复验ref/reflog后记录`PARENT_COMMITTED`。
4. 两仓所有preimage/postcondition/rollback/audit status调用只有两个exact suffix：child=`status --porcelain=v2 -z --untracked-files=all --no-renames --ignore-submodules=none`，parent=`status --porcelain=v2 -z --untracked-files=all --no-renames --ignore-submodules=all`。stdout必须NUL终止、stderr empty；closed parser只接受ordinary `1` row exact fields `XY,sub,mH,mI,mW,hH,hI,path`与untracked `?` row exact `path`，并同时冻结raw stdout SHA与CANON parsed-row SHA。因`--no-renames`存在，`2`一律拒绝；`u|!|#`、truncated/duplicate path、wrong field count、short/v1/human output或非NUL parser均fail。

   parent最终只要求Stage2-owned paths无status row；`CLAUDE.md`保持唯一type `1`、XY `.M`、sub `N...`及PRE exact modes/OIDs/bytes/patch，meeting report保持唯一`? PATH\0`及PRE exact bytes；FINAL report在commit前也是唯一`? PATH\0`，commit后不再出现。不得写或消费v1 ` M`/`??` token。`--ignore-submodules=all`不替代gitlink mode/OID、`.gitmodules` mapping与child HEAD另验。
5. 两commit/journal全绿后，才按fixed `OUTER_COLLAB_LOCK`只更新外层计划；最后独立audit，全绿才`AUDIT_COMPLETE`。任一resume边界failure先durable `ROLLBACK_INTENT`逆序恢复；pause时abort只走private-assets branch。全程无push。
6. parent report只写“本报告所在提交”，不写自引用PARENT_COMMIT SHA。


### 10.2 Durable transaction、locked rollback与re-entry

`STEP10_TXN_DIR`内journal是fresh append-only canonical JSON chain；`state.NNN.json`使用§4.2 publisher，schema token exact `ista-csr-step10-transaction-state/1.11.0`，top-level exact `schema,publication_contract,txn_id,sequence,previous,state,locator,toolchain,inputs,intent,asset_ledger,temp_ledger,spawn_ledger,child,parent,outer_plan,rollback_class,errors`。所有keys always present，所有nested递归`additionalProperties=false`；尚未产生的scalar/object只能按下述matrix为null，array必须empty而非null/缺失。sequence从0连续；previous仅INIT为null，其他state exact `sequence,sha256`并绑定紧邻前一canonical journal。

- Step10 `FileIdentity|FileRef`沿用§10.1 exact closed type；所有下述identity只能null或该类型，所有integer继续拒绝bool。
- `locator` exact `control_dir,control_dir_identity,lock_path,active_path,transactions_dir_identity,terminals_dir_identity,txn_dir,terminal_path,expected_old_active,start_inputs_sha256`并满足§10.1全部TXN/path derivation；三个DirIdentity从bootstrap复制并永久byte-exact，control/terminals dev exact相等。expected-old在每个journal都必须是active path的non-null `FileIdentity`，INIT绑定bootstrap locator；strict解码expected-old locator后，其完整start bundle/digest须分别等于本journal `inputs.start_input_bundle`及locator/toolchain/inputs三处`start_inputs_sha256`。journal禁止planned/new locator identity、new locator SHA或自身SHA。
- `toolchain` exact `durability_scope,start_inputs_sha256,refs`；scope固定`process-crash-only-v1`。refs为start bundle rows `0,1,2,3,5,10,11`的byte-exact、同序slice，即plan/Python/tool/Git/KAT及两tool reviews；不得降格为裸path、裸SHA或SHA array。
- `inputs` exact `start_input_bundle,start_inputs_sha256,refs,child_manifest_snapshot,parent_manifest_snapshot,recovery_preimages,parent_approval_request,awaiting_state_sha256,parent_input_bundle,parent_input_bundle_sha256,parent_refs`。start bundle/digest与child manifest snapshot从INIT起nonnull并永久byte-exact；refs为start bundle rows `4,6,7,8,9`的同序slice。`parent_refs`只能为null或exact三项`parent_input_bundle.entries` closed array，row固定`ordinal,role,path,sha256`、ordinal依次0/1/2、role依次`manifest,review_a,review_b`，且非null时byte-exact等于同state bundle entries；parent manifest snapshot、bundle/hash/refs只在PARENT_APPROVED或BIND→ROLLBACK从BIND details同时复制为nonnull并永久不变，其他state三者同时null。`parent_approval_request`为null或identity nonnull的`FileRef`，`recovery_preimages`只在PREIMAGES前null。RepoState/asset ledger只与这些typed authority交叉，不得另立裸path/SHA authority。
- 本节凡称durable snapshot/backup/receipt的`FileRef`都强制`identity` nonnull、path与identity.path相等、actual regular/current-uid/0600/nlink1且bytes SHA匹配；通用nullable `FileRef`规则不得放宽该要求。八个repo JSON snapshot、四个raw index/reflog backup与一个outer backup全部位于本TXN、path/inode互不alias，published后永久RETAINED。
- `RecoveryPreimages` token exact `ista-csr-step10-recovery-preimages/1.0.0`，top-level exact `schema,child,parent,outer`且PREIMAGES起三项均nonnull。`RepoRecoveryPreimage` token exact `ista-csr-step10-repo-recovery-preimage/1.1.0`、keys exact `schema,repo,head_ref,head_oid,refs_snapshot,status_snapshot,patch_snapshot,dirty_paths_snapshot,index_generation,index_backup,reflog_path,reflog_parent,reflog_generation,reflog_backup`；repo exact `child|parent`并等于enclosing role/RepoState.repo，head_ref byte-exact等于RepoState.head_ref，head_oid lower-hex且等于base_oid，index_generation exact等于RepoState.pre_index。`ReflogGeneration` exact `dev,ino,uid,mode,size,sha256`，全部integer拒绝bool、mode为actual permission、SHA lower-hex；reflog_path为canonical absolute并由git_dir/head_ref纯导出，reflog_parent为fresh `RepoDirIdentity`，generation绑定no-follow regular/current-uid/nlink1 actual。index backup只以raw size/SHA绑定index_generation，reflog backup只以raw size/SHA绑定reflog_generation；两backup自身identity.mode按上条固定0600，source mode分别保留在IndexGeneration/ReflogGeneration并在restore lock内据此`fchmod`，backup inode/path必须与source不同。
- refs/status/patch/dirty-path snapshot token依次 exact `ista-csr-step10-repo-refs-snapshot/1.0.0`、`ista-csr-step10-repo-status-snapshot/1.0.0`、`ista-csr-step10-repo-patch-snapshot/1.0.0`、`ista-csr-step10-repo-dirty-paths-snapshot/1.0.0`。四个snapshot都是identity nonnull的`FileRef`，strict解码后的top-level repo必须等于enclosing repo。refs top exact `schema,repo,rows`，row exact `ordinal,refname,oid`，ordinal为连续U64，refname为nonempty UTF-8 `refs/` name且无NUL/CR/LF，oid lower-hex，按refname raw UTF-8升序且head_ref/oid row存在。status exact `schema,repo,argv,stdout_size,stdout_sha256,stdout_base64,parsed_rows_sha256`，argv byte-exact等于§10.1 canonical launcher加§10.1 fixed repo-specific status suffix；patch exact `schema,repo,argv,stdout_size,stdout_sha256,stdout_base64`，argv fixed为canonical launcher加`diff --no-ext-diff --no-textconv --binary --no-renames HEAD --`。dirty paths exact `schema,repo,rows`，row exact `ordinal,path,status_row_sha256,kind,mode,size,sha256,target_oid`并按path raw UTF-8升序；path为canonical repo-relative且逐项绑定parsed status row，kind exact `regular|gitlink`，regular要求mode `100644|100755`、size U64/SHA nonnull/target null，gitlink要求mode160000、size/SHA null/target lower-hex。base64须strict解码并绑定U64 size/SHA，argv每项为无NUL string；所有snapshot nested closed。
- `OuterRecoveryPreimage` token exact `ista-csr-step10-outer-recovery-preimage/1.1.0`、keys exact `schema,path,target_parent,target_identity,backup`；path canonical absolute且等于outer_plan.path/target_identity.path，target_parent为fresh `RepoDirIdentity`并是path canonical parent，target_identity为nonnull `FileIdentity`。backup为identity nonnull `FileRef`且仅raw size/SHA等于target identity、path/inode不同；backup自身mode固定0600，source mode只由target_identity保留并在restore lock内据此`fchmod`。RecoveryPreimages所有cross-binding与`sha256(CANON(value))` aggregate在PREIMAGES publication前后fresh复算；它们共同提供external-input-free restore/verification，未知bytes只允许unresolved。
- `intent`为null或exact `kind,repo,command_id,expected_preimage_sha256,planned_postimage_sha256,details,details_sha256`；`details_sha256=sha256(CANON(details))`且details为kind-discriminated closed object。kind enum exact `prepare_hooks|capture_preimages|child_private_stage|publish_parent_approval_request|bind_parent_approval|child_index_install|child_ref_publish|parent_private_stage|parent_index_install|parent_ref_publish|outer_plan_write|audit|begin_rollback|private_assets_release|outer_restore|parent_ref_restore|parent_index_restore|child_ref_restore|child_index_restore`；repo按kind为null/child/parent/outer。command_id只对四个ref publish/restore kind nonnull，其他kind必须null。
- expected/planned SHA conditional exact：`capture_preimages`二者nonnull；`publish_parent_approval_request`为null/nonnull；index/ref/outer forward与restore及private-assets-release kinds均二者nonnull；prepare-hooks/private-stage/bind/audit/begin-rollback均二者null。capture两SHA分别绑定actual PRE target aggregate与planned capture-artifact aggregate；index install/restore两SHA绑定live index与单项PvtReleaseBinding的combined actual pre/planned post aggregate，planned post固定PVT CONSUMED/ENOENT；private-assets-release两SHA绑定其固定六类asset roles与按source ledger为0或2项PVT release的actual pre/planned terminal aggregate；ref intent的planned SHA绑定整个operation final，restore时不同于Git command产生的deterministic intermediate。禁止用details hash占位。
- details exact union：prepare-hooks=`roles,paths`，roles/paths依次exact child/parent及两HookDirRow path；capture=`child_head_oid,parent_head_oid,child_index_sha256,parent_index_sha256,outer_sha256,planned_capture_aggregate_sha256`；private-stage=`manifest_sha256,pvt_index_path`；publish-request=`request_path,request_sha256,child_candidate_state_sha256`；bind=`awaiting_state_sha256,parent_input_bundle,parent_input_bundle_sha256,parent_manifest_snapshot,parent_review_sha256s`；index install/restore=`index_path,expected_generation_sha256,replacement_sha256,backup_path,pvt_release`；ref publish/restore=`refname,expected_old_oid,new_oid,reflog_message,reflog_expected_sha256,reflog_command_post_sha256,reflog_final_sha256,reflog_backup_path`；outer write/restore=`path,lock_path,expected_old_sha256,new_sha256`；audit=`scope,required_receipt_sha256s`；begin-rollback=`next_state,rollback_class,cause_sha256`；private-release=`asset_roles,pvt_releases`。bundle/snapshot/refs须自洽，path canonical、OID/SHA lower-hex、arrays按owner fixed order；每个object只含列出的keys。
- `PvtReleaseBinding` token exact `ista-csr-step10-pvt-release-binding/1.0.0`，keys exact `schema,role,path,pre_state,current_generation_sha256,release`；schema固定该token，role exact `child_pvt_index|parent_pvt_index`且path byte-exact等于对应PvtIndexRow canonical path，pre_state byte-exact等于INTENT source journal中的row state，release必须JSON true。`current_generation_sha256`在current_generation_ordinal为null时必须null，否则exact `sha256(CANON(该ordinal的完整PvtGenerationRow))`；INTENT publication时RESERVED|CONSUMED要求path ENOENT，INITIALIZED|MUTATING|FROZEN要求no-follow actual完整IndexGeneration exact current row。index install details的`pvt_release`只含同repo单项且pre_state必须FROZEN；index restore单项绑定同repo当时任一合法stable state；private-release的`pvt_releases`在source asset ledger尚无PvtIndexRow时exact empty，否则exact两项child→parent、role/path唯一且各自绑定当时state，禁止1项或在empty ledger伪造binding。planned projection唯一为相同history/ordinals转CONSUMED并要求path ENOENT；binding不得授权删除wrong inode/bytes、symlink、extra-hardlink或unbound path。
- `CaptureSourceProjection` token exact `ista-csr-step10-capture-source-projection/1.0.0`、keys exact `schema,role,identity,semantic_sha256`；role exact `index|reflog|outer_plan`，identity为nonnull full `FileIdentity`且fresh no-follow regular/current-uid/nlink1，index要求semantic SHA nonnull并将identity的path/dev/ino/uid/mode/size/sha256逐字段反绑RepoState.index_path与fresh完整IndexGeneration，reflog要求semantic null并逐字段反绑derived reflog path与fresh ReflogGeneration，outer_plan要求semantic null且identity byte-exact等于fresh outer target FileIdentity。它只表示INTENT前已存在的source，故expected/planned均携同一已知完整identity。`CaptureArtifactProjection` token exact `ista-csr-step10-capture-artifact-projection/1.0.0`、keys exact `schema,role,path,uid,mode,size,sha256`，role exact `refs_snapshot|status_snapshot|patch_snapshot|dirty_paths_snapshot|index_backup|reflog_backup|outer_backup`；path公式唯一为`STEP10_TXN_DIR + "/" + CAPTURE_BASENAME[(repo,role)]`，closed table按owner order exact `child/refs_snapshot=capture.child.refs.json, child/status_snapshot=capture.child.status.json, child/patch_snapshot=capture.child.patch.json, child/dirty_paths_snapshot=capture.child.dirty-paths.json, child/index_backup=capture.child.index.backup, child/reflog_backup=capture.child.reflog.backup, parent/refs_snapshot=capture.parent.refs.json, parent/status_snapshot=capture.parent.status.json, parent/patch_snapshot=capture.parent.patch.json, parent/dirty_paths_snapshot=capture.parent.dirty-paths.json, parent/index_backup=capture.parent.index.backup, parent/reflog_backup=capture.parent.reflog.backup, outer/outer_backup=capture.outer-plan.backup`，不得有其他pair/basename、dot component或alias。uid为current uid、mode固定0600，snapshot bytes exact `CANON(closed snapshot value)`（CANON自身已有single LF，禁止追加第二个LF），backup bytes exact source raw bytes；size/SHA绑定这些exact bytes。planned artifact有意不含未来才知道的dev/ino/nlink，publisher完成后才进入full FileRef。
- `CaptureRepoProjection` token exact `ista-csr-step10-capture-repo-projection/1.1.0`、keys exact `schema,repo,binding_sha256,head_ref,head_oid,index,reflog,refs_snapshot_sha256,status_snapshot_sha256,patch_snapshot_sha256,dirty_paths_snapshot_sha256,artifacts`。repo exact child|parent；binding/head字段绑定INTENT source journal与fresh actual；index/reflog为上述CaptureSourceProjection且role依次index/reflog；四snapshot SHA依次为对应§10.2 closed value的`sha256(CANON(value))`。expected phase的artifacts exact empty；planned phase exact六项且role/order固定`refs_snapshot,status_snapshot,patch_snapshot,dirty_paths_snapshot,index_backup,reflog_backup`，每项path由closed basename表唯一导出，snapshot artifact SHA反绑对应CANON value、backup反绑同repo source identity raw bytes。`CaptureOuterProjection` token exact `ista-csr-step10-capture-outer-projection/1.0.0`、keys exact `schema,path,parent_sha256,source,artifacts`；`path == source.identity.path == outer_plan.path`，parent SHA为fresh `sha256(CANON(RepoDirIdentity))`，source为role outer_plan的CaptureSourceProjection，expected artifacts empty、planned exact一项closed-path outer_backup。
- `CaptureAggregateV1` token exact `ista-csr-step10-capture-aggregate/1.1.0`、keys exact `schema,phase,repositories,outer`；phase exact `expected_preimage|planned_postimage`，repositories exact两项child→parent且为对应CaptureRepoProjection，outer为CaptureOuterProjection。expected对象携fresh source full identities/closed snapshot value hashes且artifact arrays empty；planned对象必须byte-exact复制全部source projections并填入上述exact artifact rows。capture intent两SHA分别只能等于`sha256(CANON(expected CaptureAggregateV1))`与`sha256(CANON(planned CaptureAggregateV1))`；details必须满足`child_head_oid==repositories[0].head_oid,parent_head_oid==repositories[1].head_oid,child_index_sha256==repositories[0].index.identity.sha256,parent_index_sha256==repositories[1].index.identity.sha256,outer_sha256==outer.source.identity.sha256,planned_capture_aggregate_sha256==planned_postimage_sha256`。每次artifact create/write/link前及PREIMAGES completion前都须fresh重算五个source完整identity/semantic并与expected/planned byte-exact相等；same-bytes/new-inode、nlink变化或任一source drift均不发布。completion还须把每个actual full-identity artifact FileRef投影回planned row全等后才能发布；新建artifact identity不可预知但不削弱postcondition，也不得把full RecoveryPreimages hash冒充planned hash。
- `IndexReleaseProjection` token exact `ista-csr-step10-index-release-projection/1.0.0`、keys exact `schema,path,uid,mode,size,sha256,semantic_sha256`；`PvtReleaseProjection` token exact `ista-csr-step10-pvt-release-projection/1.0.0`、keys exact `schema,role,path,state,current_generation_sha256,path_state`，path_state exact `regular|absent`。index projection从actual `IndexGeneration`只取可复算owner/mode/content字段，path由下一条live-index cross-binding固定，明确排除`dev,ino`；PVT expected projection逐字段反绑同intent的PvtReleaseBinding与actual exists/ENOENT，planned projection保持role/path/current-generation hash、state固定CONSUMED、path_state固定absent。
- `PvtReleaseAggregateV1` token exact `ista-csr-step10-pvt-release-aggregate/1.0.0`、keys exact `schema,kind,repo,phase,index,pvt,asset_roles,asset_ledger_sha256`；kind exact `child_index_install|parent_index_install|parent_index_restore|child_index_restore|private_assets_release`，phase exact `expected_preimage|planned_postimage`。四种index kind要求repo exact child|parent、index nonnull、pvt exact单项同repo、asset_roles empty、asset_ledger_sha256 null；expected index绑定source RepoState.current_index的projection，planned index的owner/mode/content字段仅从已冻结PVT generation（install）或RecoveryPreimages index generation（restore）导出，path按下一条live-index cross-binding固定，绝不含或预测安装后dev/ino；details.expected_generation_sha256仍绑定source完整IndexGeneration的`sha256(CANON(value))`，details.replacement_sha256 exact等于planned index raw SHA。private-assets-release要求repo/index均null，pvt按source ledger exact 0项或2项child→parent，asset_roles必须逐字节exact `["index_backups","pvt_indexes","reflog_backups","hook_dirs","approval_request","command_receipts"]`，asset_ledger_sha256在expected对象绑定source完整closed asset_ledger、在planned对象绑定唯一terminal projection：existing index/reflog backups置RETAINED且identity/bytes不变，0|2 PVT rows保持history/ordinals并置CONSUMED/absent，RESERVED hooks置CONSUMED/absent、READY hooks置RETAINED/same-identity/empty，already-terminal hooks不变，approval_request与command_receipts byte-exact不变。details.asset_roles及pvt_releases分别与该fixed array及0|2 binding array byte-exact。
- 每个release intent的两SHA只能为对应phase完整`PvtReleaseAggregateV1`的`sha256(CANON(value))`；禁止hash details、full future IndexGeneration或自由拼接字段。PRIVATE_ASSETS_RELEASE_INTENT发布前必须先把pending hook-prepare恢复到全RESERVED/absent或全READY/exact-empty、把所有spawn与generic/special temp收口到其closed stable/terminal state，故source asset ledger及0|2分支唯一；partial hook prefix、pending spawn/temp或第三actual态不得生成aggregate而须unresolved。completion将actual投影重算为planned对象全等并在同一journal推进PVT及asset terminal states。
- 每个PvtReleaseAggregateV1的`kind,repo`必须分别byte-exact等于enclosing intent的kind/repo（private_assets_release的repo固定null）；四种index kind的`index.path == intent.details.index_path == enclosing RepoState.index_path`，不得取PvtIndexRow.path，expected其余字段逐项取source完整IndexGeneration，planned其余字段逐项取FROZEN PVT generation（install）或RecoveryPreimages.index_generation（restore），uid/mode/size/raw/semantic各字段不得自由推导。restore的`intent.details.backup_path == enclosing RepoState.index_backup_path == corresponding RecoveryPreimages.index_backup.path`；install的backup_path也必须等于同repo RecoveryPreimages.index_backup.path且只作rollback authority。expected/planned的单项PvtReleaseProjection须分别与同一details.pvt_release的role/path/pre_state/current_generation_sha256及其CONSUMED/absent projection逐字段反绑；private对象的fixed roles/0|2 array亦须与details逐项byte-exact。任一kind/repo/live-path/PVT-path/backup-path/details重复字段mismatch均schema failure。
- intent是phase-local write-ahead：只有`HOOKS_PREPARE_INTENT,PREIMAGES_INTENT,CHILD_PRIVATE_STAGE_INTENT,PARENT_APPROVAL_REQUEST_INTENT,PARENT_APPROVAL_BIND_INTENT,CHILD_INDEX_INSTALL_INTENT,CHILD_REF_INTENT,PARENT_PRIVATE_STAGE_INTENT,PARENT_INDEX_INSTALL_INTENT,PARENT_REF_INTENT,OUTER_WRITE_INTENT,AUDIT_INTENT,ROLLBACK_INTENT,PRIVATE_ASSETS_RELEASE_INTENT`及五个`*_RESTORE_INTENT`可nonnull并映射上述kind；completion state intent必须null。`ROLLBACK_INTENT`只指定下一exact intent，wrong kind/repo/command/pre-post/details/hash或operation早于INTENT durable均schema failure。
- `asset_ledger` exact `index_backups,pvt_indexes,reflog_backups,hook_dirs,approval_request,command_receipts`。`AssetRow` exact `role,path,identity,sha256,state`且只用于index/reflog backups；identity始终nonnull、path/SHA与identity交叉，PREIMAGES前两array empty，之后role/order分别exact `child_index_backup,parent_index_backup`与`child_reflog_backup,parent_reflog_backup`。state exact `READY|INSTALLED|CONSUMED|RETAINED`，只允许`READY→INSTALLED→CONSUMED|RETAINED`或`READY→CONSUMED|RETAINED`；READY/INSTALLED/RETAINED要求actual path匹配历史identity，CONSUMED要求ENOENT，terminal backups固定RETAINED。
- `PvtIndexRow` token exact `ista-csr-step10-pvt-index-row/1.2.0`，keys exact `schema,ordinal,role,path,state,generations,current_generation_ordinal,frozen_generation_ordinal`且schema固定该token；PREIMAGES起exact两项ordinal0/1、role `child_pvt_index,parent_pvt_index`、deterministic path唯一。state exact `RESERVED|INITIALIZED|MUTATING|FROZEN|CONSUMED`。RESERVED要求generations empty、两ordinal null、path ENOENT，因此parent PVT在parent approval前绝不存在；对应`*_PRIVATE_STAGE_INTENT` durable后，path ENOENT时wrapper才从RecoveryPreimages raw index backup exclusive创建、按source mode `fchmod`、file+dir fsync并reopen。crash re-entry若发现existing file，只在它为fresh no-follow regular/current-uid/source-mode/nlink1、lock absent、path/inode无alias，且raw size/SHA与backup、semantic SHA与source IndexGeneration exact时领养；随后以该新文件actual `dev,ino,uid,mode,size,sha256,semantic_sha256`追加initial generation，绝不要求dev/ino等于source。partial bytes或wrong type/uid/mode/nlink/alias一律保留并unresolved，不擅自删除重建。`PvtGenerationRow` token exact `ista-csr-step10-pvt-generation-row/1.1.0`，keys exact `schema,ordinal,producer_command_id,producer_kind,result_sha256,abort_reason_sha256,verdict,generation`且schema固定该token，ordinal从0 contiguous且generation为完整IndexGeneration；row0固定`producer_kind=initialize`且producer_command_id/result_sha256/abort_reason_sha256/verdict全null。每个ordinal>0 row的producer_command_id nonnull、producer_kind只`private_add|write_tree`：FINISHED row要求result_sha256 nonnull、abort_reason_sha256 null、verdict exact `accepted|rejected`并反绑唯一FINISHED spawn/receipt/result；由SPAWNED收口的ABORTED row要求result_sha256 null、abort_reason_sha256 nonnull、verdict exact `aborted`，并反绑同command id/kind的唯一ABORTED spawn及相同`spawn.abort_reason_sha256`。SPAWN_INTENT|AGENT_FORKED在Git release前收口ABORTED不append generation；一旦Git已release，原spawn terminalize为FINISHED或ABORTED时必须在同一journal恰好append一row并令current ordinal指向它。ABORTED前先证明agent/Git/session group absent、按§10.2收口四artifact并清除仅可由该spawn产生且可证明exact-own的PVT lock，再fresh no-follow冻结main PVT；actual只允许仍等于旧current generation，或是regular/current-uid/source-mode/nlink1/noalias、完整可解析且semantic observation exact等于该spawn authorized atomic postimage的新generation，两种情况都append `verdict=aborted` row（允许generation bytes与旧row相同），随后只可发布ROLLBACK_INTENT，禁止forward或任何新PVT invocation。INITIALIZED要求generations exact仅row0、current ordinal exact0、frozen ordinal null；MUTATING要求至少row0加一项command/aborted row、current ordinal exact最后一row且大于0、frozen ordinal null，并且history无`producer_kind=write_tree,verdict=accepted`；accepted write-tree必须在同一FINISHED completion立即令state FROZEN，要求current=frozen=最后ordinal、最后row exact accepted write-tree且无更早accepted write-tree、generation exact `STAGED_INDEX_GENERATION`。稳定的INITIALIZED|MUTATING|FROZEN三种存在态都fresh要求path为no-follow regular/current-uid/source-mode/nlink1、lock absent且无alias，actual完整`IndexGeneration` exact等于current row。唯一command-pending例外是同PVT唯一无后继的SPAWNED command，自Git release至FINISHED|ABORTED generation同journal publication之间，actual可为旧current或上述authorized atomic postimage且不得允许第三形态、第二spawn或forward；唯一release-pending例外是当前phase-local index install/restore或PRIVATE_ASSETS_RELEASE_INTENT携带匹配该row的PvtReleaseBinding，此时actual只可保持pre-state合同（存在态为exact current，RESERVED|CONSUMED为ENOENT）或成为授权postimage ENOENT，completion须在同一journal令row CONSUMED。两个例外不得重叠；intent外ENOENT、binding/state/hash/path不符或任何第三形态均unresolved。FROZEN后禁止任何PVT Git invocation。允许`RESERVED→INITIALIZED→MUTATING→FROZEN→CONSUMED`，failure时任一nonterminal只可经上述typed release→CONSUMED；CONSUMED要求path ENOENT并byte-exact保留其紧邻RESERVED|INITIALIZED|MUTATING|FROZEN前态的history/ordinals projection，direct RESERVED仍为空/null。PVT不服从AssetRow identity/SHA不变规则。
- `HookDirRow` exact `ordinal,role,path,state,identity,inventory_sha256`，INIT起exact两项ordinal0/1、role `child_hooks,parent_hooks`、deterministic txn-direct-child path，初始state RESERVED且两dynamic字段null、actual path ENOENT。唯一转换`RESERVED→READY→RETAINED|CONSUMED`或pre-ready abort `RESERVED→CONSUMED`；empty inventory的exact representation固定为canonical JSON array bytes `CANON([])`，READY/RETAINED要求identity为same fresh `RepoDirIdentity`、mode0700且`inventory_sha256=sha256(CANON([]))`，CONSUMED要求path ENOENT并保留历史identity若曾出现。HOOKS_PREPARE_INTENT durable后按ordinal exclusive mkdir；crash只可领养exact valid empty prefix、创建missing suffix并txn-dir fsync，wrong type/uid/mode/nonempty/extra name均unresolved。首个Git invocation晚于HOOKS_READY，pause/re-entry逐仓复验same identity/empty，terminal每row只能RETAINED-empty或CONSUMED-absent。
- approval_request为null或identity nonnull的`FileRef`；`command_receipts` row exact `ordinal,command_id,receipt`，receipt为identity nonnull `FileRef`且byte-exact等于对应spawn result row final_ref、identity SHA等于`spawn.result_sha256`；ordinal等于唯一spawn array index并严格升序，command/path/inode唯一。每个journal的receipt ordinals必须exact等于严格升序子集`{i | spawn_ledger[i].status == FINISHED}`：ABORTED index无row，因而合法subset可有gap，后续FINISHED rollback command仍按自身spawn index收receipt。row只与对应spawn首次推进FINISHED在同一journal append，之后永久byte-exact。
- Step10 common command scalars closed：`CommandId`为ASCII且匹配`^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`并在txn唯一；`SessionNonce`匹配`^[0-9a-f]{32}$`并唯一；`CommandKind` exact `private_add|write_tree|commit_tree|ref_update|ref_restore`；cwd为canonical absolute且按repo exact等于RepoState.worktree；argv为nonempty无NUL string array，argv/env hash均为`sha256(CANON(value))`。artifact temp/final basename由command id与四role纯导出；report/result path、kind、nonce、expected/planned observations与三check必须从receipt/report/result反向byte-exact绑定唯一spawn row。
- `TempRow` exact `role,path,parent_dev,parent_ino,planned_sha256,status,dev,ino,uid,mode,size,actual_sha256`；role必须属于single-file tool内reviewed literal `TEMP_ROLE_REGISTRY`，row按registry ordinal后path raw UTF-8排序且role/path唯一，path不得alias asset/target/special output。status exact `RESERVED|READY|CONSUMED`，唯一转换`RESERVED→READY→CONSUMED`；RESERVED六个actual字段全null，READY全nonnull并绑定regular/current-uid/0600/nlink1 actual temp，CONSUMED只改status、永久保留历史字段且path ENOENT。terminal要求本事务实际创建的每个generic temp唯一CONSUMED且inventory无未登记temp。
- Step10 `ProcessIdentity`沿用§4.4。`command_observation_v1` token exact `ista-csr-step10-command-observation/1.0.0`，top exact `schema,kind,repo,payload`；kind exact `private_add|write_tree|commit_tree|ref_update|ref_restore`，repo exact `child|parent`，所有nested closed。`IndexRow` exact `path,stage,mode,oid`，stage exact0、mode exact `100644|100755|120000|160000`，按path raw UTF-8升序；`LiveIndexGuard` exact `path,raw_sha256`；`RequiredObject` exact `logical_path,type,oid,raw_size,raw_sha256,state`，type `blob|tree|commit`、state `absent|present_exact`，absent要求raw pair null、present_exact要求nonnegative size/lower-hex SHA并fresh验证，array按`(logical_path UTF-8,type,oid)`排序。object mismatch/corruption不是第三state，只能observation failure/unresolved。
- private-add payload exact `pvt_index_path,pvt_lock_path,pvt_lock_absent,index_rows,required_objects,live_index`；planned rows是manifest对完整PRE index rows的纯函数应用，expected object记录actual absent/present_exact，planned required objects全present_exact。write-tree payload exact `pvt_index_path,pvt_lock_path,pvt_lock_absent,index_rows,root_tree_oid,tree_objects,live_index`；wrapper按Git tree basename order独立编码每层raw tree并纯算OID/raw SHA，pre/planned index rows相同，planned trees全present_exact，cache-tree造成的raw PVT差异不进入planned。
- commit-tree payload exact `tree_oid,parent_oid,author,committer,message,commit_oid,commit_raw_size,commit_raw_sha256,commit_object_state,live_index`，author/committer各exact `name,email,date`；按§10.1 raw commit公式纯算OID/SHA，state exact `absent|present_exact`。ref-update/ref-restore payload exact `refname,head_ref,ref_oid,ref_lock_path,ref_lock_absent,reflog_path,reflog_lock_path,reflog_lock_absent,reflog_size,reflog_sha256,reflog_message,committer,live_index`；pre绑定expected-old及actual reflog，planned绑定new OID及deterministic append。ref-restore command planned是reverse-append intermediate，operation final仍由intent绑定raw PRE reflog。
- 每个SPAWN_INTENT inline持久化完整expected/planned observation；`expected_preimage_sha256=sha256(CANON(expected_preimage))`、`planned_postimage_sha256=sha256(CANON(planned_postimage))`。planned只能由pre+durable manifest snapshot/identity/RepoState/argv纯函数生成，禁止dev/ino/uid/nlink/mtime/PID/starttime/temp或stream identity及object-dir全inventory。`accepted_streams` exact `stdout_size,stdout_sha256,stderr_size,stderr_sha256`：private-add/ref均双empty，write-tree stdout为root tree OID+LF，commit-tree stdout为commit OID+LF，stderr均empty。
- `ArtifactPublicationRow` exact `ordinal,role,writer,temp_path,final_path,state,open_identity,planned_sha256,ready_identity,linked_temp_identity,linked_final_identity,final_ref`；exact四项固定为`0 agent_report agent,1 stdout agent,2 stderr agent,3 result wrapper`。writer表示byte writer，所有link/unlink/publish syscall仍只由wrapper执行。八path为本TXN direct children、两两不alias且SPAWN_INTENT前ENOENT；static五字段首次出现后永久不变。`OpenIdentity` exact `path,dev,ino,uid,mode,nlink`，mode0600/nlink1，不含可变size/SHA。
- artifact state唯一转换`RESERVED→WRITABLE→READY→LINKED→CONSUMED`，或`RESERVED|WRITABLE|READY→DISCARDED`、`LINKED|CONSUMED→ABORTED`。RESERVED所有dynamic字段null；WRITABLE仅open identity nonnull且temp own inode/final ENOENT；READY首次记录planned SHA与完整temp FileIdentity，且agent/Git/group已absent；LINKED记录same own inode的temp/final nlink2并已第一次txn-dir fsync；CONSUMED记录actual final `FileRef`、temp ENOENT/final nlink1并已第二次fsync；DISCARDED要求两path ENOENT并保留历史；ABORTED要求final_ref nonnull/final nlink1、temp ENOENT并保留全部历史identity。publisher不得在LINKED journal durable前unlink temp；filesystem处于唯一下一postimage可补状态，否则unresolved。
- `spawn_ledger` row exact `command_id,status,command_kind,argv_sha256,env_sha256,cwd,expected_preimage,expected_preimage_sha256,planned_postimage,planned_postimage_sha256,accepted_streams,preimage_checks,artifact_publications,session_nonce,agent,git,result_sha256,abort_reason_sha256`。command/session/cwd/scalars服从前述closed types；`preimage_checks` row exact `ordinal,point,observation_sha256`，point依次 `before_spawn_intent,before_agent_release,before_git_release`且SHA均等于expected hash。SPAWN_INTENT含第一项、AGENT_FORKED含前两项、SPAWNED|FINISHED含三项；ABORTED保留其最后durable predecessor对应的exact 1/2/3项prefix。wrapper在对应journal/release前fresh重观测完整object相等。
- successful spawn status唯一`SPAWN_INTENT→AGENT_FORKED→SPAWNED→FINISHED`；任一nonterminal `SPAWN_INTENT|AGENT_FORKED|SPAWNED`都可在old identity/group absent且outputs已收口后推进ABORTED。SPAWN_INTENT agent/git/result/abort null；AGENT_FORKED agent nonnull、git/result/abort null；SPAWNED agent/git nonnull、result/abort null；FINISHED保留两identity、result SHA nonnull/abort null且四artifact全CONSUMED；ABORTED保留此前已出现identity、result null、abort reason SHA nonnull且四artifact只为DISCARDED|ABORTED。private_add|write_tree由SPAWNED推进FINISHED时须同journal append normal PvtGeneration，推进ABORTED时须同journal append aborted PvtGeneration；若从SPAWN_INTENT|AGENT_FORKED在Git release前ABORTED则不得append。valid rejected result仍走FINISHED/receipt；无法构造strict report/result才ABORTED且不得Git replay。
- `agent_report_v1` token exact `ista-csr-step10-agent-report/1.0.0`，top exact `schema,publication_contract,txn_id,command_id,session_nonce,agent_report_path,argv,argv_sha256,env,env_sha256,cwd,agent,git,exec,wait,returncode,streams`；publication fixed hardlink token，streams exact `stdout_size,stdout_sha256,stderr_size,stderr_sha256`。report、argv/env/hash/path/identities反绑spawn；agent actual wait/reap Git并把stdout/stderr完整写入预开FD、fsync后最后写canonical report FD并fsync，agent不得open pathname、link/unlink、写result/journal、观测postimage或裁决verdict。
- `exec` exact `state,errno`，state `succeeded|failed|indeterminate`并服从CLOEXEC pipe EOF/4-byte ERRNO/partial matrix：succeeded要求errno null，failed要求errno为`1..4095`且收到完整4-byte errno，indeterminate只对应partial/malformed pipe且errno null。`wait` exact `raw_status,kind,exit_code,term_signal,reaped`，reaped在strict report固定true；raw_status为`0..65535`且必须与POSIX wait解码双向一致：kind=exited当且仅当`WIFEXITED(raw_status)`，exit_code exact `WEXITSTATUS(raw_status)`、term_signal null、top-level returncode exact等于exit_code；kind=signaled当且仅当`WIFSIGNALED(raw_status)`，exit_code null、term_signal exact `WTERMSIG(raw_status)`且为1..127、returncode exact `128+term_signal`且不超过255。stopped/continued或任何两宏均不匹配的raw status拒绝；exit_code仍为0..255。所有integer拒绝bool；exec failed必须wait exited/127并满足同一raw解码，exec succeeded必须实际EOF，indeterminate仍须actual wait/reap但verdict只能rejected。无法actual wait/reap Git不得形成strict agent report。
- `command_result_v1` token exact `ista-csr-step10-command-result/1.1.0`，top exact `schema,publication_contract,txn_id,command_id,session_nonce,result_path,command_kind,artifact_contract,argv,argv_sha256,env,env_sha256,cwd,expected_preimage,expected_preimage_sha256,planned_postimage,planned_postimage_sha256,actual_postimage,actual_postimage_sha256,accepted_streams,preimage_checks,agent_report,agent,git,exec,wait,returncode,streams,verdict`。`artifact_contract` exact等于四artifact rows的static五字段projection，`agent_report`为actual final `FileRef`；其余字段反绑spawn/report，`actual_postimage_sha256=sha256(CANON(actual_postimage))`且actual observation由wrapper在wait/reap agent并证明agent/Git/session group absent后fresh生成，agent自报digest无效。
- result `streams` exact `complete,stdout,stderr`且complete true，两项为actual final `FileRef`；report与streams regular/current-uid/0600/nlink1并匹配published bytes。verdict exact `accepted|rejected`：accepted当且仅当strict agent report、exec succeeded、wait exited/0、returncode0、三次pre checks、actual post byte-exact planned与actual streams byte-exact accepted_streams全绿；完整可观测但不满足者rejected，post observation无法闭合则不得伪造result而转ABORTED/unresolved。result不含自身SHA。
- 每个journal满足双射和单向DAG `stdout/stderr→agent_report→result→FINISHED journal`：FINISHED当且仅当唯一command receipt匹配role=result final_ref/SHA且四artifact CONSUMED/temp全ENOENT；strict result再反绑agent report、两streams、artifact static projection、spawn observations/checks/identities。ABORTED无command receipt；由SPAWNED终止的PVT ABORTED须有同journal唯一aborted generation且result null/abort reason交叉，pre-Git ABORTED或非PVT ABORTED不得伪造该row。command receipts只允许§上条由ABORTED index解释的ordinal gap，任一FINISHED缺row或ABORTED有row均schema failure。ROLLED_BACK只允许spawn terminal FINISHED|ABORTED，AUDIT_COMPLETE要求所有required spawn FINISHED且result verdict accepted。duplicate、非spawn顺序、alias、result自引用、special/generic ledger path重合或任一反向绑定漂移均schema failure。
- `RepoDirIdentity` exact `path,dev,ino,uid,mode`，path canonical absolute，四integer为拒绝bool的U64，fresh no-follow对象必须是current-uid directory并匹配全部字段。`RepoPathState` exact `path,kind,identity`，kind exact `absent|regular|directory`；absent要求identity null，regular要求identity为nonnull FileIdentity，directory要求identity为nonnull RepoDirIdentity，path双向相等。
- `RepoBindingV1` token exact `ista-csr-step10-repo-binding/1.0.0`，keys exact `schema,repo,worktree,git_dir,common_dir,object_dir,index_parent,index_path,head_ref,base_oid,gitfile,config,config_worktree,commondir,info_attributes,include_count`。repo exact child/parent；五个directory字段为RepoDirIdentity。唯一合法且必需的directory alias group是`common_dir == git_dir == index_parent`，三者完整RepoDirIdentity必须byte-exact相等；object_dir canonical path必须exact为`git_dir/objects`、是该组的strict descendant且path/identity不等于该组；worktree与该组及object_dir的path/identity都必须不同，其他alias全部拒绝。index_path canonical absolute且parent exact index_parent，head_ref nonempty `refs/heads/` name、base_oid lower-hex。后五个path state分别绑定worktree `.git`、git-dir `config`、common-dir `config.worktree`、git-dir `commondir`、git-dir `info/attributes` actual；include_count为U64 exact0，info_attributes只允许absent或regular size0/empty-SHA。child gitfile/core.worktree与parent `.gitmodules` mapping仍按§10.1另作fresh semantic gate，不塞入不相关digest。
- `child|parent`各为RepoState exact `repo,worktree,git_dir,object_dir,index_path,base_oid,head_ref,current_oid,binding,binding_sha256,pre_index,current_index,index_backup_path,pvt_index_path,pvt_index_sha256,staged_tree,candidate_commit,path_manifest_path,path_manifest_sha256,review_receipt_sha256s,committed`；binding为完整RepoBindingV1且各projection字段byte-exact，`binding_sha256=sha256(CANON(binding))`。INIT在任何repo mutation前fresh构造，之后每次wrapper/re-entry及每个Git release前均从actual stable topology重算完整binding并要求相等；base_oid作为历史commit须仍存在，current ref另由current_oid验证。`IndexGeneration` exact `dev,ino,uid,mode,size,sha256,semantic_sha256`。child projection来自inputs child refs；PARENT_APPROVED及BIND→ROLLBACK从persistent parent refs唯一投影manifest path/SHA与A/B review SHA，首次出现后永久byte-exact，不得fresh external refresh。
- `outer_plan` exact `path,lock_path,preimage_sha256,current_sha256,backup_path,planned_sha256,written`。`rollback_class`在所有forward state为null，在ROLLBACK_INTENT首次固定为`no_live_mutation|restore_preimages`并永久不变。`no_live_mutation`只要求完整journal history尚无`CHILD_INDEX_INSTALL_INTENT`或其后任何live-mutation intent/actual mutation；对该source state中已经nonnull的ref/index/reflog/outer pre/current projection，fresh actual必须exact相等，尚未capture而为null的projection只复验stable RepoBinding/BASE及ledger无mutation并明确无bytes-PRE claim。它允许nonnull RecoveryPreimages、PVT generations/candidates、FINISHED|ABORTED private-command spawn与receipts，只证明本事务未执行live mutation，不声明ambient repo byte-exact等于事务开始时PRE。`restore_preimages`从durable `CHILD_INDEX_INSTALL_INTENT`起强制，或在任何本事务actual live mutation证据存在时强制，并要求nonnull RecoveryPreimages及terminal逐项exact restore。errors row exact `code,operation,detail_sha256`，code/operation nonempty、detail lower-hex，errors只可prefix-monotonic append。

journal-temp basename deterministic `.state.NNN.TXN.tmp`；final absent且temp strict canonical/schema/seq/previous完整时re-entry可完成link/fsync/unlink/fsync，final同SHA只清own temp；partial own temp可unlink+fsync。unknown basename/identity/hash、final冲突、缺号/链错、任一nested missing/extra/type/nullability/state错误均unresolved、不得mutation。KAT逐top key、每种nested record及每条conditional branch注入负例，并覆盖sequence/previous/locator双向hash与monotonic transition。

fixed `.active.bootstrap.ready`、`.active.transition.ready`与每个spawn的四组artifact temp都属于各自专用ledger，永不进入generic `temp_ledger`；generic publisher必须拒绝reserved output namespace，special ledger也拒绝任何已出现在generic ledger的path/inode。其他wrapper-created temp严格按TempRow执行RESERVED→READY→CONSUMED；re-entry只处理exact-own unique pre/post image。terminal前generic temps全CONSUMED，special artifact不得留`RESERVED|WRITABLE|READY|LINKED`；unknown identity/SHA/parent、extra hardlink或跨ledger alias一律保留并unresolved。

Git child内部的`PVT_INDEX.lock`与object-dir temp不冒充上述wrapper temp：SPAWN_INTENT另冻结允许的private-index exact lock path与object temp namespace/inventory。agent/Git identities未全消失前不得处理；其后只可在exclusive txn dir删除可由该spawn/namespace/identity证明exact-own的`PVT_INDEX.lock`并dir-fsync，main PVT不得从durable PRE重建来强求旧inode。pending PVT actual若仍为old generation或已成为§10.2 authorized atomic postimage，须按原spawn FINISHED|ABORTED generation协议接管；partial/noncanonical/第三postimage、wrong identity或lock ownership不闭合均保留并unresolved。shared object-dir temp永不由wrapper删除；候选objects/unknown temps只记录并保留，不能阻断refs/index/worktree的PRE恢复，也不能被声称已清理。

forward state exact `INIT→CHILD_APPROVED→HOOKS_PREPARE_INTENT→HOOKS_READY→PREIMAGES_INTENT→PREIMAGES→CHILD_PRIVATE_STAGE_INTENT→CHILD_CANDIDATE→PARENT_APPROVAL_REQUEST_INTENT→PARENT_APPROVAL_REQUESTED→AWAITING_PARENT_APPROVAL→PARENT_APPROVAL_BIND_INTENT→PARENT_APPROVED→CHILD_INDEX_INSTALL_INTENT→CHILD_INDEX_INSTALLED→CHILD_REF_INTENT→CHILD_COMMITTED→PARENT_PRIVATE_STAGE_INTENT→PARENT_CANDIDATE→PARENT_INDEX_INSTALL_INTENT→PARENT_INDEX_INSTALLED→PARENT_REF_INTENT→PARENT_COMMITTED→OUTER_WRITE_INTENT→OUTER_WRITTEN→AUDIT_INTENT→AUDIT_COMPLETE`。历史尚无`CHILD_INDEX_INSTALL_INTENT`的no-live abort（含PREIMAGES/CHILD_CANDIDATE/AWAITING/BIND/PARENT_APPROVED）exact `ROLLBACK_INTENT→PRIVATE_ASSETS_RELEASE_INTENT→PRIVATE_ASSETS_RELEASED→ROLLED_BACK`；从该intent durable起的live rollback exact `ROLLBACK_INTENT→OUTER_RESTORE_INTENT→OUTER_RESTORED→PARENT_REF_RESTORE_INTENT→PARENT_REF_RESTORED→PARENT_INDEX_RESTORE_INTENT→PARENT_INDEX_RESTORED→CHILD_REF_RESTORE_INTENT→CHILD_REF_RESTORED→CHILD_INDEX_RESTORE_INTENT→CHILD_INDEX_RESTORED→ROLLED_BACK`。每operation先durable phase-local INTENT，completion只在fresh postcondition后发布且intent null；仅restore_preimages分支中尚未发生的restore仍以expected=planned PRE hash记录validated no-op pair且不得跳过。AWAITING是唯一人工稳定pause态。

state/nullability matrix是journal schema的一部分；`intent`只存在于当前INTENT state并在completion归null；`current_oid,current_index,committed,outer_plan.current_sha256,written`只按forward/rollback postcondition变化，ledgers只append或单向推进，PvtIndex generations及HookDirRow只按各自closed transition变化；`rollback_class`只允许null→single enum且不回退。`errors`是唯一额外append-only array且每个新journal须以previous errors为byte-exact prefix，禁止删除/重排/替换或duplicate append；除此以外任一non-null历史值首次出现后永久byte-exact，未列为“首次”的字段沿用上一state。locator中的完整start bundle/digest、journal `inputs.start_input_bundle`、toolchain/inputs typed-ref slices与RepoBinding是特殊的INIT既有永久字段：从BOOTSTRAP/INIT至所有forward、rollback及terminal state均byte-exact，不受“首次出现”规则刷新：

- `INIT`：previous null；locator.expected-old绑定BOOTSTRAP active；toolchain/inputs slices、完整start bundle/digest及child manifest snapshot nonnull并与actual start byte-exact，parent snapshot、recovery preimages、request/awaiting/parent bundle/hash/refs均null。两RepoState固定paths/base/head/current OID、完整binding/digest及outer path nonnull，current OID均BASE；manifest/review projections尚未出现，所有pre/current index、backup/PVT/tree/candidate、outer pre/current/backup/planned均null，committed/written false。asset hook_dirs为exact两项RESERVED/absent，其他asset arrays、temp/spawn/errors empty，rollback_class null。
- `CHILD_APPROVED`首次从inputs child refs唯一投影child RepoState manifest path/SHA与A/B review SHA。`HOOKS_PREPARE_INTENT`只携两RESERVED rows的write-ahead；`HOOKS_READY`首次令两row READY并冻结same identity/empty inventory。`PREIMAGES_INTENT`只携capture write-ahead；`PREIMAGES` intent归null并首次令inputs.recovery_preimages、两仓pre/current IndexGeneration、index/reflog backup各exact2 AssetRow、PVT exact2 RESERVED PvtIndexRow与对应RepoState paths、outer pre/current/backup及全部refs/status/patch/dirty-path/index/reflog backups nonnull且actual exact PRE；candidate/PVT frozen SHA/request/parent approval/outer planned仍null。
- `CHILD_PRIVATE_STAGE_INTENT`授权且只授权初始化child PVT并增加mapped spawn plan；initial generation先durable，Git release后的每个PVT spawn只在同一terminal journal append唯一FINISHED或ABORTED generation；`CHILD_CANDIDATE`要求child PvtIndexRow已FROZEN且frozen generation exact staged index，首次令child PVT SHA、staged tree、candidate commit及相关receipts nonnull，full commit validator全绿；parent PvtIndexRow仍RESERVED/absent，两仓live ref/index/worktree/status/reflog仍为其唯一planned boundary，committed false。
- `PARENT_APPROVAL_REQUEST_INTENT`只在details/planned SHA承诺request且inputs/asset request仍null；`PARENT_APPROVAL_REQUESTED`首次令两个request `FileRef` byte-exact相等。`AWAITING_PARENT_APPROVAL`不改变request，awaiting SHA、parent snapshot/bundle/hash/refs均null且两仓live PRE；AWAITING不得含自身SHA。
- `PARENT_APPROVAL_BIND_INTENT` details首次承载actual AWAITING SHA、完整parent bundle/hash、parent manifest snapshot与A/B reviews，inputs对应字段仍null。正常`PARENT_APPROVED`从紧邻details byte-exact复制awaiting/bundle/hash/parent refs/snapshot并唯一投影parent RepoState manifest path/SHA与review SHA；BIND→ROLLBACK在同一ROLLBACK journal作完全相同复制/投影。复制仅为recovery history，不授权forward；禁止fresh external read或取immediate previous SHA冒充AWAITING SHA。
- `CHILD_INDEX_INSTALL_INTENT`不改durable projection并首次绑定child PvtReleaseBinding；`CHILD_INDEX_INSTALLED`同一journal令child current_index exact fresh `LIVE_INSTALLED_GENERATION`且child PVT CONSUMED/ENOENT，其live size/SHA/semantic SHA exact等于FROZEN PVT staged generation、uid/mode/path合同另验而dev/ino取live actual且不等同PVT；`CHILD_REF_INTENT`不改actual；`CHILD_COMMITTED`起current OID exact CHILD_COMMIT、committed true且child reflog exact deterministic forward postimage。
- `PARENT_PRIVATE_STAGE_INTENT`在PARENT_APPROVED后才授权从RESERVED初始化parent PVT、增加mapped spawn，并按同一terminal journal的FINISHED result或ABORTED reason append唯一generation；`PARENT_CANDIDATE`要求parent PvtIndexRow已FROZEN且frozen generation exact staged index，首次令parent PVT SHA/tree/candidate/receipts nonnull；`PARENT_INDEX_INSTALL_INTENT`首次绑定parent PvtReleaseBinding，`PARENT_INDEX_INSTALLED`同一journal令parent current_index exact fresh `LIVE_INSTALLED_GENERATION`且parent PVT CONSUMED/ENOENT，仅live content projection等于FROZEN PVT而dev/ino取live actual；`PARENT_COMMITTED`起OID exact PARENT_COMMIT、committed true且parent reflog exact deterministic forward postimage。
- `OUTER_WRITE_INTENT`首次令outer planned SHA nonnull；`OUTER_WRITTEN`起current SHA exact planned/written true；`AUDIT_INTENT|AUDIT_COMPLETE`不得再改变repo/outer/recovery values，后者要求全部audit receipts、required spawn FINISHED/accepted与postconditions全绿。
- `ROLLBACK_INTENT`按完整history/actual last boundary设置唯一rollback_class并选择`PRIVATE_ASSETS_RELEASE_INTENT|OUTER_RESTORE_INTENT`；若源自BIND_INTENT，先按上条复制snapshot/bundle/projection。任何Git-released pending PVT spawn须先以同journal FINISHED或ABORTED generation闭合，才可进入ROLLBACK_INTENT。`no_live_mutation`允许收口txn temps、partial hooks/control、已存在PVT及private-command artifacts：`PRIVATE_ASSETS_RELEASE_INTENT`以按source ledger条件为0或2项的PvtReleaseBinding及nonnull aggregate pre/post SHA作唯一write-ahead，逐项只从exists exact current或原本absent推进ENOENT并dir-fsync；`PRIVATE_ASSETS_RELEASED`同一journal在2-row分支令两PVT rows（包括原本RESERVED/absent者）均CONSUMED，pre-PREIMAGES 0-row source则pvt array/bindings保持empty，已terminal spawn及其generation/receipts/history永久保留、已存在index/reflog backups RETAINED。fresh证明不存在任何本事务live-mutation intent/actual且actual live projections仍等于最后durable值后发布ROLLED_BACK，明确不作byte-exact transaction-start PRE restoration claim。`restore_preimages`严格按outer→parent ref+reflog/index→child ref+reflog/index五组推进；每个index RESTORE_INTENT绑定对应PvtReleaseBinding，每个`*_INDEX_RESTORED`同一journal令该PVT CONSUMED，所有RESTORED仅在fresh PRE postcondition后发布，最终两仓refs/reflogs/index/status/worktree与outer exact RecoveryPreimages。所有start/parent snapshots、typed refs、candidate、request及receipt历史不得清null，asset/temp/spawn只推进closed status；两class的terminal hooks rows均RETAINED-empty或CONSUMED-absent。
- clean forward及owner-requested abort的errors可始终empty。fault-triggered `ROLLBACK_INTENT`必须首次append至少一条closed error，其`begin_rollback.details.cause_sha256=sha256(CANON(本次新追加errors rows))`；live mutation后发现external parent input missing/drift必须以code exact `parent_external_input_drift`进入此分支。owner abort无新增error时cause SHA exact绑定`sha256(CANON({"schema":"ista-csr-step10-owner-abort-cause/1.0.0","reason":"owner_requested_abort"}))`，该object拒绝extra。后续独立failure可在下一mutation前durable append但须保持prefix-monotonic。提前nonnull、required null、array基数错误、bundle/request/awaiting时点错误、rollback抹除history或current不等actual postcondition均阻断。

`PREIMAGES`在任何private add前冻结两仓branch/base/full refs、approved/preserved worktree bytes/mode/status/patch、HEAD/live-index semantic与raw backups/generations、PVT paths，以及外层计划canonical path/parent/no-follow identity/mode/raw bytes/SHA。后续state记录candidate tree/commit、current ref/index/status/worktree/outer SHA；journal、PVT、backups、command receipts全部排除于Git-visible/approved stage集合。

每个可能修改PVT index/object/ref的Git命令只能由transaction command-agent启动。wrapper在SPAWN_INTENT前fresh生成inline expected/planned observation、三次check的第一项与四个RESERVED artifact rows；durable后按ordinal以`O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC`/0600预创建四个temp、fsync txn dir并以同一spawn status持久推进四row为WRITABLE。随后才创建identity/release pipes并fork agent；agent只继承agent-report/stdout/stderr三个write FD，wrapper保留result FD，Git barrier child显式关闭三output FD且exec再由CLOEXEC保证不继承。

agent先`setsid`、回传stable ProcessIdentity并阻塞。wrapper fresh重观测expected object、append第二check、durable推进AGENT_FORKED后才释放agent；agent建立Git pipes/barrier并fork唯一Git child，wrapper验证Git identity并再次fresh重观测、append第三check、durable推进SPAWNED后才释放Git。任一release早于对应journal、EOF/wrong byte/timeout或preimage drift都必须no-Git/no replay。

agent以bytes pipes drain Git，将完整stdout/stderr写入各预开FD并fsync，actual wait/reap Git后最后写canonical agent report FD并fsync；agent不open pathname、不link/unlink、不写result/journal、不观测postimage或裁决verdict。wrapper正常路径actual wait/reap agent并证明agent/Git/session group absent，验证三个temp/report与accepted contracts后一次journal推进前三项READY，再按`stdout→stderr→agent_report`逐项READY→LINKED→CONSUMED。

前三final FileRef成立后，wrapper才fresh生成actual post observation；从spawn、strict agent report及actual stream refs构造result，写入预留result temp、fsync/reopen验证并推进READY，再LINKED→CONSUMED。四项全CONSUMED且result strict后，下一份单一journal同时推进FINISHED、设置result SHA并append唯一command receipt；若kind为private_add|write_tree，该journal还必须append唯一normal PvtGeneration并把actual/current（accepted write-tree还含frozen）一次闭合。accepted才授权上层completion，valid rejected仍FINISHED留痕并转rollback/unresolved。

re-entry先证明old agent/Git/group absent，再按每组path分类EMPTY、TEMP_ONLY、FINAL_PLUS_TEMP或FINAL_ONLY。SPAWN_INTENT仍无AGENT_FORKED且rows为RESERVED时，只允许actual temp构成按ordinal的合法prefix：每个prefix项regular/current-uid/0600/nlink1/size0/empty-SHA、final ENOENT且path为reserved static path；wrapper no-follow冻结其OpenIdentity、exclusive创建missing suffix、txn-dir fsync并一次journal推进四row WRITABLE，hole/wrong inode/type/uid/mode/nlink/nonempty/extra path均unresolved。一般TEMP_ONLY只对已持久exact-own inode unlink+dir fsync、绝不promote；FINAL_PLUS_TEMP仅same inode/nlink2时unlink temp并补验证；FINAL_ONLY要求regular/current-uid/0600/nlink1。无AGENT_FORKED且四WRITABLE仍same open identity/size0/empty SHA时可重开同一FD并重试same row；除下一段唯一result-only分支外，其余情况只可ABORTED/rollback，不另造并行command。

agent-report/两streams三row已strict CONSUMED、spawn status SPAWNED、agent/Git/session group absent而result final仍ENOENT时，存在唯一role-specific恢复例外：result row必须WRITABLE且temp仍为持久open_identity同inode、regular/current-uid/0600/nlink1。size0/empty-SHA时wrapper可只重开result FD，从三final refs与fresh唯一actual post重构并写一次；若temp已是完整canonical planned result则只可验证后补READY；两路都继续READY→LINKED→CONSUMED且Git invocation count不增。partial/noncanonical/nonempty-wrong-hash、wrong inode或post无法闭合只能DISCARDED/ABORTED。agent-owned TEMP_ONLY永不promote。result final durable而FINISHED未发布时只补一次FINISHED/receipt双射；PVT kind还必须在该同一journal补唯一normal generation，FINISHED只复验不得追加第二receipt或第二generation，也不声称对非本process取得waitpid/ECHILD。

任一child/parent/outer/audit failure先发布phase-local `ROLLBACK_INTENT(kind=begin_rollback)`并按history选择class。仅restore_preimages随后每步先发布对应`*_RESTORE_INTENT`：ref若已forward移动，command-agent exact执行`update-ref -m "ista-step10:<TXN_ID>:<child|parent>-restore" refs/heads/IncreGPUSTA BASE CURRENT_COMMIT`；accepted result只证明ref BASE与deterministic reverse-append intermediate，wrapper还必须按§10.1 locked reflog protocol恢复raw PRE，二者全绿才发布`*_REF_RESTORED`。随后独立index-restore INTENT安装PRE raw backup或验证no-op，并在live PRE postverify后按其PvtReleaseBinding release对应PVT；同一`*_INDEX_RESTORED` journal同时记录live PRE与PVT CONSUMED。该class中未发生mutation的组仍发布expected=planned PRE的validated no-op pair并执行相同release；mismatch不重试/覆盖并unresolved。no_live_mutation不进入任何restore INTENT，只走private-assets链。

wrapper从不通过commit/reset/rollback改worktree bytes。每个恢复边界只从durable child/parent manifest snapshots、recovery refs/status/patch/dirty-path snapshots及raw backups取得approved/preserved/report/gitlink expected PRE，fresh重观测后才继续；绝不重开external source path授权恢复。未知ref/reflog/index/worktree或user bytes立即停止并保留journal/backups，不覆盖、移动、删除并发内容；candidate objects可保留但不把object store虚称byte-exact PRE。

外层计划forward/restore使用fixed `OUTER_COLLAB_LOCK`，位于validated ignored build tree、exclusive `O_CREAT|O_EXCL|O_NOFOLLOW`/0600且fsync，内容绑定txn/writer pid+starttime/target/expected identity+SHA。所有获授权outer writer必须遵守该协作锁；不声称防住非协作writer，也不把rename称kernel CAS。preimage backup与planned same-parent temp先durable READY；持锁后紧邻publish fresh验证target仍expected image，mismatch则不rename、不移动target；匹配才`renameat(temp,target)` atomic replace、dir fsync、postverify planned bytes/mode并durable完成态，随后unlink lock+fsync。rollback同协议且expected target必须transaction postimage。

re-entry先完成journal-temp、generic/special ledgers与pending spawn审计；Git-released pending PVT只能按old/authorized-atomic-postimage二态、原spawn terminal journal及generation 1.1闭合，unknown main/lock identity保留unresolved，绝不重放。PVT release只在当前index install/restore或PRIVATE_ASSETS_RELEASE_INTENT的typed binding下允许exists-exact-current/ENOENT两态；若live index/asset与PVT组合为唯一合法pre/intermediate/post则补步骤并在completion同journal置CONSUMED，intent外ENOENT、wrong inode/bytes或impossible ordering均unresolved。forward `start`须匹配persistent start bundle并fresh验证external refs，forward `resume`须fresh验证parent bundle；`abort`、fault rollback、BIND→ROLLBACK及terminal rollback repair绝不重开external inputs。rollback_class=restore_preimages时只验证journal内bundle/manifest snapshots/recovery preimages/raw backups与actual repo/outer唯一pre/planned post；no_live_mutation时只用永久journal history验证尚无首个live-mutation intent/actual、actual只需匹配source state中已持久化的nonnull live projections，并收口private PVT/spawn/receipt/backup/temps；null projection不刷新external inputs、不产生bytes-PRE claim，也不把ambient worktree称作事务PRE。old group absent才可补状态；`ROLLBACK_INTENT`后只按class收口/逆序restore，terminal不得replay。

`ROLLED_BACK`按class二选一：restore_preimages要求outer plan、两仓refs/reflogs/live raw index/semantic status/worktree/docs/preserved files byte-exact等于RecoveryPreimages；no_live_mutation要求history无`CHILD_INDEX_INSTALL_INTENT`或其他本事务live mutation、fresh actual匹配source state全部nonnull live projections且只声明transaction live-mutation count exact0，null projection不声称bytes PRE。no-live可含RecoveryPreimages、candidate、PVT generations、FINISHED|ABORTED spawn与receipts；这些history永久保留，任何已出现PVT row必须CONSUMED、任何spawn全terminal、任何已出现backup RETAINED，source早于对应ledger materialization时array可保持empty。两class都要求generic temps全CONSUMED、special outputs无active state、hooks RETAINED-empty或CONSUMED-absent、所有owned locks absent且无pending/live agent。`AUDIT_COMPLETE`只有两commit/forward reflog postimages/outer/audit全绿、required spawn FINISHED/accepted、journal/publisher chains完整、PVT CONSUMED、backups/hooks RETAINED且同样无active temp/lock/group。其余状态一律unresolved。
terminal publication在CONTROL flock内完成：先fresh复验persisted三个DirIdentity、`control.dev==terminals.dev`及start bundle/digest，再完成ordinary locator transition，使active的previous locator/journal sequence/state/SHA绑定final `AUDIT_COMPLETE|ROLLED_BACK` H_final并nofollow复验。publication前terminals inventory exact empty；以`linkat(control_fd,"active.json",terminals_fd,"terminal.TXN_ID.json",0)` no-overwrite，复验两name同dev/ino、regular/current-uid/0600/nlink2，分别fsync terminals与CONTROL dirfd，再从CONTROL dirfd unlink active、复验terminal nlink1并再次fsync两dirfd；任何dev mismatch/EXDEV在link前拒绝且不得迟至commit后才发现。

publication-only repair只接受三态：final active存在且terminals empty时补link→fsync→unlink→fsync；final active与唯一对应terminal同inode/bytes/nlink2时只补unlink/fsync；active ENOENT且terminals仅唯一valid terminal regular/0600/nlink1时认定完成。active nonfinal却有terminal、多个terminal、wrong TXN/different inode或bytes、extra link、directory identity漂移均unresolved；完成后CONTROL_DIR不得fresh start。

terminal bytes仍服从active-locator schema并绑定final state/sequence/journal SHA。`ROLLED_BACK`必须携带并满足上述rollback_class：restore_preimages才声明两仓live refs/reflogs/index/worktree/outer/preserved exact recovery PRE；no_live_mutation只声明本事务未执行live mutation，但允许相应RecoveryPreimages/PVT/backups/spawn/receipt history存在，并要求任何已出现PVT row CONSUMED、任何已出现backup RETAINED、任何spawn terminal，尚未materialize的对应array保持empty。`AUDIT_COMPLETE`要求两commit/forward reflogs/outer/audit、全部required spawn FINISHED/accepted及publisher receipts全绿。两者都要求hooks处于terminal状态、generic/special temp无active state、own locks与live groups为0；candidate objects和durable backups可按ledger `RETAINED`。

本节durable/recoverable claim的唯一scope token exact `process-crash-only-v1`：只承诺healthy local filesystem、同一host的wrapper/agent/Git userspace process异常退出或SIGKILL后的协议恢复；不覆盖host/WSL shutdown、power loss、kernel panic、filesystem/hardware corruption、fsync违约、network filesystem、privileged或non-cooperating writer。flock/Git index lock/outer lock都不得扩张此边界。


### 10.3 Local refs与无网络审计

wrapper逐仓记录：

- hardened prefix下的branch/status、direct parent、`git show --check --stat --no-ext-diff --no-textconv`、child→parent gitlink；
- `git remote -v` 配置、`@{upstream}`存在/absent、`refs/heads`与`refs/remotes` pre/post snapshots、`git for-each-ref --contains COMMIT`；
- `ABS_GIT`/env、identity input、双审path manifests及SHA、两仓repo/index bindings、child gitfile/core.worktree、parent `.gitmodules`、两local config raw/include proofs与逐command不变证据；
- owner commit metadata、attributes/PRE、write-tree后final PVT/tree/OID、post-freeze no-PVT、locked install/refs/reflogs、journal-v1.11、generic/special temp、SPAWN_INTENT→AGENT_FORKED→SPAWNED→FINISHED|ABORTED、agent-report/result/receipt反向绑定及outer-lock inventories；
- local remote-tracking refs不得变化，任何Git subprocess都必须带对应hooks/fsmonitor/attributes canonical launcher。

禁止任何远端状态查询、fetch、网络访问与`git push`。最终措辞 exact：“No push executed; remote state was not queried.” 只能证明local refs，不声称远端未包含commit。

### 10.4 Artifact与binary audit

wrapper所有diff/show调用强制 `--no-ext-diff --no-textconv`，以literal exact paths对CHILD_COMMIT/PARENT_COMMIT的diff/new paths和committed trees检查build/run/JSON/receipt/tool/pyc/rej/orig泄漏；不得调用external diff/textconv。binary规则按baseline-vs-final/new-or-changed paths判断，不能把既有tracked binary一概报错。

child既有 `src/operation/iRCX/interface/ics55/lib/libircx_ics55.so` baseline blob OID锁为 `f682ee408fc81dcb51900fe19f9a43ce4dcf2c10`；要求CHILD_BASE与CHILD_COMMIT均为该OID且该path不在commit diff。只有新/changed binary path阻断，不能误报该未变baseline blob。

wrapper还复验child `*.pyc`/`__pycache__` exact absent、37 parent pyc manifest不变、两preserved parent文件不变、Stage2-owned parent paths clean，以及两hooks目录仍是原dev/inode/mode/uid且exact empty、两info-attributes state exact不变。audit结束仍不push。

Step10 local-only DoD还要求single-file wrapper/agent与Python/Git/operational CLI/journal双审、唯一review-kat入口、versioned closed KAT receipt及两份tool-review/1.1.0 APPROVE，fixed CONTROL_DIR/flock/locator/terminal与CONTROL/terminals same-device，owner identity，分阶段双审literal manifests，child gitfile/core.worktree、parent `.gitmodules`、两local config no-include及common-dir/split-index/worktreeConfig拒绝全绿。PATHS非动态推导，report唯一approved new且preserved deny。
Step10 journal/locator还必须证明bootstrap/INIT四态txn恢复、完整start bundle/digest、typed-ref slices与TXN/path derivation；journal-v1.11的manifest snapshots、closed parent refs、RepoBinding、HookDirRow、PvtIndex1.2/PvtGeneration1.1 normal+aborted rows与CaptureAggregate1.1、PvtReleaseBinding1.0、PvtReleaseAggregate1.0、fully-bound refs/status/patch/dirty-path/index/reflog/outer RecoveryPreimages、两类rollback class、BIND→ROLLBACK持久复制与RepoState projection、errors prefix-monotonic、generic/special ledgers、agent-report/result/FINISHED双射及ABORTED branch全闭合。每个intent details/conditional/phase-local completion与ref+reflog逐步rollback、PARENT_APPROVED actual AWAITING SHA、terminal repair先过Python/tool/directory/same-device gate；manifest仅接受1.1 closed union。
start只能在child双审后依次durable准备两hooks并取得HOOKS_READY、捕获PRE，再生成CHILD_CANDIDATE并稳定pause；pause live refs/index/worktree exact PRE。resume只能在随后生成的parent manifest双审后执行child locked install/ref→parent PVT/install/ref；每个Git-released PVT spawn在FINISHED或ABORTED同一journal append唯一generation并恢复actual=current，只有accepted write-tree令FROZEN generation exact staged index且禁止后续PVT invocation；每个index install completion在live postverify后同journal release/CONSUME对应PVT，`ls-files+cat-file`、attrs/blobs/gitlink/hooks全绿，parent status每次带exact v2/no-renames/ignore-submodules argv。
每个agent链须durable SPAWN_INTENT与四输出RESERVED→WRITABLE、AGENT_FORKED outer barrier、SPAWNED Git barrier、agent-report/streams、wrapper fresh actual post与command-result/1.1、FINISHED/receipt或ABORTED；旧identity/group absent后才repair，PVT不得retry/replay，SPAWNED→ABORTED必须绑定abort reason与generation后进入rollback。terminal只有required FINISHED/accepted的`AUDIT_COMPLETE`，或带exact rollback_class的`ROLLED_BACK`：restore_preimages要求repo/outer全PRE，no_live_mutation只证明transaction live mutation exact0。两者均要求active absent、无active temp/lock/group；process-crash-only边界明示。全程不push。

Step10全部failure-injection KAT只能由registered `review-kat`入口在fresh disposable fixtures执行，成功必须生成`ista-csr-step10-review-kat-receipt/1.0.0`并由两份tool review绑定：除index/ref/outer与agent barrier kill点外，覆盖Python flag/argv[4]/tool-Git SHA、CLI/active/flock并发；INIT inventory四态empty、partial/full temp-only、final-only、final+temp same-inode，在short-write/file-fsync/link/first-dir-fsync/temp-unlink逐点kill，并覆盖extra entry、wrong inode/nlink与partial+final。bootstrap仅相同start bundle恢复；argv path/SHA/order变化拒绝，resume/abort遇partial ready、BOOTSTRAP+txn absent、EMPTY或TEMP_ONLY均零namespace/journal/repo mutation；FINAL_ONLY/FINAL_PLUS_TEMP则须先只完成publisher cleanup/ordinary locator transition，随后resume拒绝INIT、abort可rollback且不得duplicate INIT。transition-ready missing/partial/full、重构/rename/fsync、免ledger与无hash环均覆盖。

KAT还覆盖start bundle十二typed refs、Step9 FINAL/KAT/tool/child review cross-binding、reviewer raw-UTF8 sort、TXN_ID与全部locator path等式；child/parent snapshot的role/repo/ref绑定、BIND details entry authority到复制后parent_refs authority切换、closed parent refs、RepoBinding fresh重算与`common_dir=git_dir=index_parent`三重alias正例/其他alias负例，以及refs/status/patch/dirty-path/index/reflog/outer RecoveryPreimages逐top/nested/schema/path/SHA/order/alias验证。backup mode0600对source mode0644等非0600正例必须restore后按source generation/identity fchmod；错误交叉mode拒绝。parent bundle覆盖BIND、BIND→ROLLBACK snapshot/projection copy、PARENT_APPROVED各publisher窗口；在INIT/HOOKS/PREIMAGES/CHILD_CANDIDATE/AWAITING/BIND/PARENT_APPROVED边界删除或篡改external inputs，forward必须停止且在首个live-mutation intent前走no_live_mutation/private-assets、不作PRE claim；`CHILD_INDEX_INSTALL_INTENT`及其后只凭durable snapshot/backups走restore_preimages。两hooks逐mkdir/fsync/READY/partial-prefix/wrong identity/nonempty及terminal状态覆盖；PVT覆盖row/schema、两row RESERVED、child-only初始化、pause时parent absent、parent approval后初始化、INITIALIZED/MUTATING/FROZEN基数与stable actual-current-generation绑定、initial-create crash以same content/new inode领养、unique SPAWNED pending例外、Git lock partial与atomic rename前/后至agent-report/result/FINISHED前SIGKILL、old/new generation的同journal ABORTED接管，以及PvtReleaseBinding missing/extra/type/role/order/path/state/hash/release、private-release在pre-PREIMAGES为0而materialized ledger为exact2（1项/empty-ledger伪造拒绝）、install/restore/private-release aggregate closed CANON、CaptureAggregate full-source-identity与planned-artifact projection、closed basename、single-LF accepted/double-LF rejected、future-identity exclusion、same-bytes-new-inode/extra-hardlink及六项capture-details mismatch、release kind-repo-live-PVT-backup path mismatch、exists/ENOENT pending矩阵、第三postimage/partial/wrong identity保留并unresolved、terminal CONSUMED。errors、terminal repair、journal-v1.11、各ledger与Git topology/status均逐branch覆盖。

command-observation KAT逐五kind覆盖missing/extra/cross-kind/bool/order/CANON/hash，并拒绝planned注入inode/mtime/PID/temp/stream identity。private-add覆盖raw PVT inode/bytes变化但semantic rows相等、PvtGeneration row0及FINISHED/ABORTED的producer-result-abort-verdict null matrix、state current/frozen ordinal matrix、normal/aborted append与producer/result或abort reason反绑、row/object漂移；write-tree覆盖cache-tree raw变化、独立tree encoder/closure/root/stdout、accepted-only FROZEN generation、aborted write-tree保持MUTATING与post-freeze拒绝；index install覆盖PVT与fresh live不同inode但size/SHA/semantic投影相等的正例、combined index+release pre/post SHA、live-postverify-before-unlink顺序及错误full-generation等值要求负例；commit-tree覆盖absent/preexisting-exact object、raw/OID/parent/identity；ref覆盖old/new方向、两lock/live-index/reflog expected/planned/reverse-intermediate与raw PRE repair。

agent-report/result KAT逐top及`exec,wait,streams` nested key覆盖schema/type/nullability、CommandId/SessionNonce/CommandKind/cwd、11/14/17-key env、argv/hash、report/result/stream/mapping互换或alias、agent/Git identity、三次pre check与wrapper actual post。逐分支覆盖exec succeeded/failed/indeterminate及wait exited/signaled的exit/signal/returncode null矩阵与POSIX `raw_status↔kind/code/signal`双向解码；正例覆盖EOF+exit0+accepted、errno+127/signaled/indeterminate rejected；负例覆盖raw_status与kind/code/signal不一致、stopped/continued status、agent自报actual digest、group仍live时生成post、actual==pre或neither却accepted、stream/ref identity错误与postcondition失败却accepted。

journal KAT覆盖五status的agent/git/result/abort nullability、preimage-check基数、跳态/回退/duplicate command、FINISHED无receipt/四CONSUMED、ABORTED有receipt、receipt无FINISHED及ordinal/path/SHA/inode反绑；另有pre-Git spawn ABORTED无generation、SPAWNED PVT ABORTED有唯一aborted generation、后续ref_restore FINISHED而receipt ordinals形成合法gap的正例，任何非FINISHED-subset gap仍拒绝。四role逐一覆盖RESERVED partial-prefix create与hole/wrong file、write/fsync/READY/link/first-dir-fsync/LINKED/unlink/second-fsync/CONSUMED kill点；agent-owned TEMP_ONLY绝不promote，same-inode FINAL_PLUS_TEMP只cleanup。另覆盖三agent输出CONSUMED后/result首写前、result write/fsync-before-READY、empty same-inode result重构、canonical complete补READY及partial/wrong-inode拒绝；PVT atomic rename后在report、result或FINISHED publication前逐点SIGKILL，必须零Git replay、同一ABORTED terminal journal追加generation再rollback/CONSUMED；另对child/parent的install、restore及no-live private-release逐项覆盖PVT unlink前、unlink+dir-fsync后、completion journal前SIGKILL，合法pre/intermediate/post只能补一次并同journalCONSUMED，old-live+absent、wrong path/inode/bytes、intent外absence全部unresolved；result final后只补一次FINISHED/receipt/generation原子闭合，Git invocation count不增。

Step 10 exact顺序：start `CHILD_APPROVED→HOOKS_PREPARE_INTENT→HOOKS_READY→PREIMAGES_INTENT→PREIMAGES`→child private INTENT/PVT generations/FROZEN candidate→request INTENT/published completion→`AWAITING_PARENT_APPROVAL`（live PRE）并退出；owner生成/双审parent manifest；resume bind INTENT→`PARENT_APPROVED`→child index intent/install+PVT release completion→ref→parent PVT generations/FROZEN candidate→parent index intent/install+PVT release completion→ref→outer/audit→terminal `AUDIT_COMPLETE`。abort/failure先durable begin-rollback并固定class；`no_live_mutation`适用于首个`CHILD_INDEX_INSTALL_INTENT`前并以PRIVATE_ASSETS_RELEASE typed completion收口已materialize的0|2 PVT，`restore_preimages`从该intent起逐步`*_RESTORE_INTENT→*_RESTORED`且两index completion各收口对应PVT；完成前不得写“Stage 2完成”。

## 11. v0.31 review candidate 待实施值

- Step8 v0.15 plan SHA `2246cc8ce01d4952b7e8435275907327ef21446e15a4a47629f39febe9abbdc0`已冻结；新计划双审、changed controller/selftest/Workflow gate fresh全量复验与最终代码双审在正式PRE前必须记录actual PASS。旧v0.14/79-of-79/review/gate只属历史，不得继续称对新bytes有效；唯一历史Step8 machine receipt仍是cleanup receipt，另绑定repair intent `a3df8abbdf29e14eb2f2209f3412e2bdcda859a107affc1dc5d98538b97b17a3`、completion receipt `dad7d36e85c3889f7d7ce05dec333667e79f14ba624efb7bcd506c4b557f4974`及plan/report PRE bytes。
- 七个build-tree tool须在fresh candidate重新materialize、冻结source/SHA/syntax/registry，全量两路KAT与两路APPROVE；任何诊断目录或旧失败候选中的tool/review/receipt均不得复用。
- Step8 changed bytes的fresh actual测试、Ruff/format/hygiene、labels、wheel-equivalent与两路代码审查完成后才可作有来源转录；compiler/33 entries、Python/dynamic/build inputs由Step9 fresh PRE生成。
- fresh outer-driver/supervisor/capture/context/reducer/recheck/provenance paths、inner/outer receipts、phase envelopes、18/18/9 values与所有run SHA：v0.31双审后实施时生成，禁止跨引旧gVLAN或e23路径。
- 37-entry parent pyc baseline、已完成Step8 external cleanup receipt、plan-review repair intent/receipt exact path/SHA及三相child pyc/cache absence manifests：在PRE只读绑定；不由Step9清理。
- Step10 single-file wrapper/Python/Git/tool reviews、CONTROL_DIR/flock/locator、two-stage manifest snapshots、recovery preimages、journal-v1.11、PVT/install/refs/reflogs/terminal/barriers仅在Step10生成，不是Step9实施值。
- v0.31当前仅为generation-separated prior-attestation review candidate；只冻结并报告candidate SHA，不称Step9完成，不授权正式run、commit、push或remote query。
