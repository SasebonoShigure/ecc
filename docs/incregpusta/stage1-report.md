# 阶段 1 报告：Typed mode、session 接口与默认兼容

> 当前开发协议补充（开发检查分离）：保留生命周期与 session 所有权。诊断 observation 的生成、复制和 Python mapping 只在 ON 执行；OFF 不返回虚假的 observation。 后续改动必读 [开发检查规范](development-guidelines.md)，双模式实测与历史验收的区别见 [本轮实施报告](debug-checks-implementation-report.md)。原阶段验收数字保留为历史记录。

> 状态：阶段 1 本地完成，独立审查和正确性门均通过
> 日期：2026-08-19
> 提交状态：ecc-tools 已创建本地提交 a7355b216b801f72a99d92e77765f49c744148b3；ECC parent 由包含本报告的本地提交承载；均未推送

## 1. 结论

阶段 1 已交付 typed STA execution contract、可显式关闭的 IncrementalStaSession、legacy/session 共用的 native owner gate，以及 ECC 配置到 native session 的接入。默认 cpu/full/error 仍运行既有 full-graph STA，并保留既有 report、QoR、power、SDF 路径和发布顺序。

cpu/incremental 在没有 mutation batch 时也运行同一 full baseline，但 execution record 明确为 baseline_only，executed strategy 为 full，fallback 为 false，reason 为 not_applicable_no_mutation。cuda/full 和 cuda/incremental 目前只完成配置与 typed capability 边界，都会在 stale artifact 删除或 native engine 创建前以 backend_unavailable 失败，不会静默改跑 CPU。

本阶段没有实现 CSR、graph edit、CPU incremental propagation、CUDA backend、greedy buffer insertion 或任何 speedup。详细设计见 [stage1-detailed-plan.md](stage1-detailed-plan.md)，能力边界见 [stage0-feature-support-matrix.md](stage0-feature-support-matrix.md)。

## 2. Git 与来源状态

| 项目 | 分支 | 阶段 1 起点 | 阶段 1 结束状态 |
|---|---|---|---|
| ECC parent | IncreGPUSTA | 447e15517ab0af95e403a19956f215876fb08283 | 本报告所在的本地提交；未推送 |
| ecc-tools submodule | IncreGPUSTA | f1b1351a18d862b086de8b191f51ee5a1688638b | a7355b216b801f72a99d92e77765f49c744148b3；未推送 |

父仓提交必须记录上述 child gitlink。未来若推送，顺序必须先 child、后 parent；当前两个 IncreGPUSTA 分支均不宣称远端可达。

## 3. 阶段边界

本阶段交付：

- backend、update_strategy、fallback_policy 的 Python/C++ typed request；
- 固定 10 字段 execution record 和四种 execution kind 的交叉约束；
- native session create、initialize、run_full_baseline、close 和只读 state；
- Python context manager、typed native error 归一化和 primary/cleanup 异常链；
- legacy 与 typed session 共用的进程级 owner lease；
- transactional init、production pipeline cleanup ledger、sticky quarantine；
- post-synthesis、signoff 和 direct module 的无副作用 unsupported preflight；
- requested/executed/fallback 日志；
- binding、owner interoperability、故障注入和真实双 session 测试。

明确未交付：

- CSR/SoA 转换、stable ID、generation 或 fingerprint；
- mutation batch、CPU incremental 算法和 affected-cone propagation；
- CUDA full/incremental 实现与性能测量；
- greedy buffer insertion；
- 多 session 并发或多 corner 共享 native timing state。

## 4. 修改文件与职责

### 4.1 ECC parent

- chipcompiler/cli/project/params.py：注册 sta.backend、sta.update_strategy、sta.fallback_policy 及默认值/choices。
- chipcompiler/tools/ecc/sta_mode.py：typed enums、request/record、严格 validator、capability/status/error。
- chipcompiler/tools/ecc/sta_session.py：Python RAII/context manager、native exception 归一化、record parity。
- chipcompiler/tools/ecc/module.py：在既有大文件中保留窄接入点；preflight、session 调用、close-before-publish、telemetry。
- chipcompiler/tools/ecc/runner.py：post-synthesis/signoff 顶层 preflight，确保 unsupported 早于 stale 删除和 engine 创建。
- test/cli/params/test_registry.py、test_commands.py：参数 schema、choices、registry 数量。
- test/tools/ecc/test_sta_mode.py、test_sta_session.py：typed contract、异常和 context-manager 测试。
- test/tools/ecc/test_runner_sta_mode.py、test_module_timing.py、test_runner.py：runner 副作用、multi-corner、默认兼容和 telemetry。
- docs/specification/cli-design.md：公开配置与阶段 1 语义。
- docs/incregpusta/stage0-feature-support-matrix.md：generation/fingerprint 首个 gate 修正为阶段 2。
- docs/incregpusta/stage1-detailed-plan.md：经六轮设计审查冻结的 v1.0 计划及完成状态。
- docs/incregpusta/stage1-report.md：本报告。

没有修改 PDK parameter template。默认 workspace 不因新增 schema default 而写入额外键。

### 4.2 ecc-tools submodule

- StaExecutionContract.{hpp,cpp}：C++ typed request、record、status、capability 和严格 resolver。
- IncrementalStaSession.{hpp,cpp}：单次 baseline session 状态机、幂等 close、noexcept destructor。
- StaLifecycleGuard.{hpp,cpp}：unarmed cleanup ledger、成功 acquisition 后 arm、owner lease、quarantine 和不可抛诊断。
- StaProductionLifecycle.{hpp,cpp}：真实 init/full/extract/update/report/write/close choreography 与窄测试 seam。
- STAInterface.{hpp,cpp}：legacy/session 共用 owner gate、异常转换、rollback、q(current)/q(none)、atomic close；Liberty wrap 防御性检查。
- py_ista.cpp、py_ista.h、py_register_ista.h：resolver、session factory/class 和 typed StaSessionError binding；旧 binding 保留。
- interface/CMakeLists.txt：把新模块加入现有 ista_interface，不新增 target edge。
- test/CMakeLists.txt：33 项 ista_unit、binding smoke 和真实 baseline smoke。
- StaExecutionContractTest.cpp、IncrementalStaSessionTest.cpp、StaLifecycleGuardTest.cpp、StaProductionLifecycleTest.cpp、PythonBindingContractTest.py：契约、状态、owner、std/unknown throw、cleanup 和 binding matrix。
- baseline/StaFullBaselineProbe.cpp、StaFullBaselineEncoding.hpp：每个 fresh process 内依次运行真实 cpu/full 与 cpu/incremental/no-mutation session，比较 snapshot。
- .github/actions/build-wheel/action.yml：wheel build 后显式构建新增 native targets，并运行带 no-tests=error 的 ista_unit/ista_smoke。

所有新增或拆分源文件低于 700 行；最大为 baseline probe 664 行、production scenario test 640 行、encoding helper 140 行。

## 5. 用户可见配置与行为

公开配置：

~~~toml
[params.sta]
backend = "cpu"
update_strategy = "full"
fallback_policy = "error"
~~~

允许值：

- backend：cpu、cuda；
- update_strategy：full、incremental；
- fallback_policy：error、full_with_record。

行为：

| 请求 | 阶段 1 实际行为 |
|---|---|
| cpu/full | existing full-graph STA；record 为 full_update |
| cpu/incremental，无 mutation | existing full-graph baseline；record 为 baseline_only，reason 为 not_applicable_no_mutation |
| cuda/full | 在 artifact/native 副作用前 typed unsupported |
| cuda/incremental | 在 artifact/native 副作用前 typed unsupported |

full_with_record 在阶段 1 不授权 CUDA→CPU 静默降级。旧项目省略三项配置时仍解析为 cpu/full/error；legacy init_sta/run_sta/destroy_sta binding 继续保留。

## 6. 生命周期与异常语义

- native STA 是进程级 singleton，只允许顺序 owner；legacy 与 typed caller 不能相互关闭或破坏对方 session。
- init rollback 只清理实际成功取得的资源。ledger 先登记 unarmed entry，initializer 成功后才 arm。
- work 失败且全部临时 cleanup 成功时保留原 owner，可正常 close；cleanup 未确认时进入 quarantined(current_owner)。
- quarantined(current_owner) 仅允许原 owner 做一次 persistent close，之后无论成功与否都变为 sticky quarantined(none)。
- init rollback cleanup 或 persistent close 失败直接进入 quarantined(none)；阶段 1 没有 hard reset，必须 fresh process。
- production seam 的 std/unknown direct throw 被集中转换；run/extract/update/report/write 的 cleanup-unconfirmed throw 按 quarantine 处理。
- noexcept destructor 使用 C stdio best-effort diagnostic，不依赖可抛的 iostream。
- DelayCalculator runtime 的 init 位于 initializer 槽，成功后才 arm destroy；updateTiming 成功仍把 runtime 交给 persistent owner 到 close。

## 7. Review 与修正循环

### 7.1 设计审查

阶段 1 详细计划经过六轮独立审查。主要修正包括 runner 最外层无副作用 preflight、context-manager 双异常、legacy/session 共用 owner、四 kind exact invariant、production cleanup ledger、quarantine ownership、capability/status/fallback 分型和 init rollback cleanup 权。最终三名独立审查者均 APPROVE，冻结为 v1.0。

### 7.2 Parent 代码审查

- Round 1：REQUEST_CHANGES。发现 native StaSessionError 未归一化为 parent typed error、test_runner.py 被推过 700 行、telemetry 和 engine-creation 副作用测试存在 false-green。
- 修正：新增严格 native error parser/chaining；把 runner mode tests 拆到 107 行独立文件，test_runner.py 回到 669 行；增加 exact telemetry、constructor zero-call 和 stale-byte 断言。
- Round 2：APPROVE，无剩余 finding。审查者独立运行 parent 测试、Ruff、format、scoped ty 和 diff-check。

### 7.3 Native 代码审查

- 首轮预审：REQUEST_CHANGES。generic guard/lease 测试不足以证明真实 STAInterface owner 和 production failure 路径；补入窄 operations seam 和独立进程 scenario tests。
- 运行修正：真实第二 session 曾在 Liberty reader 已被消费后触发 SIGSEGV。ASan backtrace定位到 wrapTimingLibrary；probe 改为每 session 重读 Liberty，production 增加 link/builder/library 空值与 silent-state 异常保护。
- 结构审查：clang-format 后 probe 超过 700 行；拆出 StaFullBaselineEncoding.hpp 后为 664/140 行。
- Edge audit：REQUEST_CHANGES。集中修复 seam direct throw、close 原子 lease 转换、unarmed ledger、noexcept diagnostic，以及 STADC.init 被接到 work 槽的问题；新增 12 个 direct-throw 独立场景。
- 最终复审及原 finding closure：APPROVE，无 blocker、major 或 minor。审查者未编辑、提交或推送内容。

## 8. 正确性命令与结果

### 8.1 Native configure/build

从 /home/shigure/code/ecc 执行：

~~~bash
nix --extra-experimental-features "nix-command flakes" develop --command cmake -S chipcompiler/thirdparty/ecc-tools -B chipcompiler/thirdparty/ecc-tools/build-ista-stage0 -G Ninja -DCMD_BUILD=ON -DBUILD_TESTING=ON -DCMAKE_BUILD_TYPE=Release -DCOMPATIBILITY_MODE=ON -DPython3_EXECUTABLE=/home/shigure/code/ecc/.venv/bin/python -DPYTHON_EXECUTABLE=/home/shigure/code/ecc/.venv/bin/python -DPYTHON_INCLUDE_DIR=/home/shigure/.local/share/uv/python/cpython-3.11.13-linux-x86_64-gnu/include/python3.11 -DPYTHON_LIBRARY=/home/shigure/.local/share/uv/python/cpython-3.11.13-linux-x86_64-gnu/lib/libpython3.11.so
nix --extra-experimental-features "nix-command flakes" develop --command cmake --build chipcompiler/thirdparty/ecc-tools/build-ista-stage0 --target ista_execution_contract_test ista_lifecycle_guard_test ista_incremental_session_test ista_production_lifecycle_test ista_full_baseline_probe py_ista ecc_py -j4
~~~

结果：configure PASS；最终 freshness build 为 no work，说明受影响 targets 与当前源码一致；ecc_py 实际 binding 导入通过。

### 8.2 Native CTest 与 golden

~~~bash
PYTHONDONTWRITEBYTECODE=1 ctest --test-dir chipcompiler/thirdparty/ecc-tools/build-ista-stage0 --no-tests=error --output-on-failure -L "^ista_unit$"
PYTHONDONTWRITEBYTECODE=1 ctest --test-dir chipcompiler/thirdparty/ecc-tools/build-ista-stage0 --no-tests=error --output-on-failure -L "^ista_smoke$"
~~~

结果：

- ista_unit：33/33 PASS；
- ista_python_binding_contract：1/1 PASS，8 个 backend × strategy × policy request 组合 parity；
- ista_smoke：2/2 PASS；
- chain、diamond 各 3 个 fresh process verified；
- 每个 process 内真实 cpu/full 与 cpu/incremental/no-mutation snapshot 相同；
- 6 个 probe.stderr.log 均为 0 字节；
- topology/config hash 与阶段 0 golden 不变。

最终本地 controller：

/home/shigure/code/ecc/chipcompiler/thirdparty/ecc-tools/build-ista-stage0/src/operation/iSTA/test/baseline-runs/session-1787146500-208704-dc4d1332/controller-result.json

该路径位于 ignored build tree，仅作为本机证据，不提交 raw run artifact。

### 8.3 Parent Python 回归

~~~bash
.venv/bin/python -m pytest test/tools/ecc test/cli/params -q
.venv/bin/python -m pytest test/ --ignore=test/examples/test_soc.py -m "not pdk" -q
~~~

结果：

- 定向 parent 套件：324 passed；
- 全部非 PDK：1494 passed、8 skipped、4 deselected、13 xfailed；
- 不加 not pdk marker 的诊断运行另有 1 个失败，唯一原因是外部 icsprout55-pdk 未安装；其余 1494 passed。该资产不属于阶段 1 hermetic gate。

Ruff check/format、sta_mode.py/sta_session.py scoped ty、父/子 git diff --check 全部通过。Native 变更集用 clang-format 21.1.8 完整格式化，并以 --dry-run --Werror 复核通过。没有 tracked/unignored `__pycache__`、session 或 benchmark result 泄漏到提交候选中。

## 9. Requested/executed 与 fallback 统计

| 请求模式 | Contract matrix | 真实 fixture session | executed/kind | fallback |
|---|---:|---:|---|---:|
| cpu/full | 2 个 policy 组合 | 6 | cpu/full，full_update | 0 |
| cpu/incremental，无 mutation | 2 个 policy 组合 | 6 | cpu/full，baseline_only | 0 |
| cuda/full | 2 个 policy 组合 | 0；init 前拒绝 | unsupported/backend_unavailable | 不适用 |
| cuda/incremental | 2 个 policy 组合 | 0；init 前拒绝 | unsupported/backend_unavailable | 不适用 |

阶段 1 没有执行 fallback_full，也没有把 unsupported 伪装成 fallback。parent 双 corner 测试逐 corner 断言相应 request、artifact path 和两条 exact baseline_only telemetry；child 的真实 baseline probe 则断言顺序 session 相互独立，并拒绝 session overlap。

## 10. 性能与 artifact

阶段 1 没有性能算法，因此 performance smoke 为不适用：

- 不报告 CPU incremental 或 GPU speedup；
- 不产生 incremental timing samples；
- 不生成或提交 performance artifact；
- 上述 build-tree controller 仅是 correctness evidence。

## 11. 已知限制

- typed session 每次只允许一个 baseline run，native singleton 不支持并发 session。
- cleanup failure 后 sticky quarantine 只能通过 fresh process 恢复。
- cpu/incremental 当前没有 mutation batch，实际仍是 full graph propagation。
- CUDA 组合没有 kernel、device CSR 或真实 GPU correctness/performance 结果。
- legacy updateTiming 仍重建图并做 full propagation，不是论文增量算法。
- chain/diamond 是 hermetic tiny fixtures；外部 ics55 PDK 当前不可用，未把 PDK integration 冒充为通过。
- generation/fingerprint、CSR round-trip、stable ID 和 invalidation 由阶段 2 实现。

## 12. 下一阶段 gate

阶段 2 才开始 Native ↔ CSR 转换。未来 agent 必须先重新分析当前代码并写阶段 2 详细计划，至少冻结：

- canonical node/arc stable key 与 session-local ID；
- object graph → forward/reverse CSR/SoA 导出；
- CSR → TimingPoint/Arc timing 字段 scatter；
- graph/session generation、fingerprint、capacity/invalidation telemetry；
- round-trip、fresh CPU/full differential 和多 corner 隔离测试。

阶段 2 仍不得提前实现 Dual-CSR mutation 或 CUDA kernel。

## 13. 完成检查表

- [x] 阶段 1 详细设计 v1.0 获独立审查批准。
- [x] Parent 与 native 实现完成。
- [x] Parent 与 native 独立代码审查最终 APPROVE。
- [x] Native unit、binding、smoke 和 Stage 0 golden 通过。
- [x] Parent 定向与全部非 PDK 回归通过。
- [x] requested/executed/fallback 统计据实记录。
- [x] 性能不适用和已知限制明确。
- [x] ecc-tools 本地提交已创建并记录。
- [x] ECC parent 本地提交由本报告所在提交承载；未推送。
