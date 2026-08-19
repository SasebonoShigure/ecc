# ECC IncreGPUSTA 阶段 1 详细实施计划

> 状态：阶段 1 本地完成；设计 v1.0、parent/native 独立代码审查与正确性门均通过
> 基线：parent `447e15517ab0af95e403a19956f215876fb08283`，ecc-tools `f1b1351a18d862b086de8b191f51ee5a1688638b`
> 分支：parent 与 ecc-tools 均为 `IncreGPUSTA`
> 范围：typed execution contract、session 生命周期骨架、CPU/full 兼容接入；不实现 CSR、edit batch、增量算法或 CUDA
> 结果：[阶段 1 报告](stage1-report.md)

## 1. 阶段目标与非目标

阶段 1 把当前一次性的 `init_sta -> run_sta -> destroy_sta` 包装成可显式创建、执行和关闭的 session，并在 Python 与 C++ 边界使用同一组 typed mode。默认请求仍是 `cpu/full/error`，底层仍运行现有 full STA，报告、QoR、power 和 SDF 的路径及内容契约不变。

本阶段不建立 CSR，不接受 mutation batch，不执行 `STAInterface::updateTiming()`，不增加 CUDA target，也不报告增量或 GPU speedup。`IncrementalStaSession` 只是后续阶段的生命周期和执行契约骨架；名称不代表阶段 1 已具备增量计算能力。

## 2. 已核验现状

### 2.1 参数与 parent 调用链

- `sta.max_paths` 在 `chipcompiler/cli/project/params.py` 注册，经 TOML/CLI 解析、backend override 和 Workspace 参数合并后，分别由 post-synthesis 与 signoff STA 从 `workspace.parameters.data` 读取。
- `ECCToolsModule.run_timing()` 位于已经较大的 `module.py`，当前依次执行 library/SDC/SPEF 初始化、`init_sta`、`run_sta`、`destroy_sta`，再原子发布既有 artifacts。
- signoff `run_sta()` 对每个 corner 调用一次 `run_timing()`；不同 corner 当前依靠完整 destroy/init 隔离。
- `ECCToolsModule.close()` 会调用全局 `reset_data()`，不能作为单个 STA session 的 close，否则会删除后续 corner 仍需使用的设计数据库。

### 2.2 native 与 binding 调用链

- Python binding 当前仅公开 `init_sta`、`run_sta`、`extract_lib` 和 `destroy_sta`。
- `STAInterface::runSTA()` 执行完整 graph build、clock/timing/power propagation、analysis、reports 和 SDF；`updateTiming()` 仍重建全图并做 full propagation，而且只允许一次，不能作为阶段 1 增量接口。
- `STAInterface`、`DataManager` 和多数 propagator/analyzer 是进程级 singleton。阶段 1 session 必须独占 native STA 状态，只支持顺序 session，不承诺线程安全或并发 corner。
- 阶段 0 只证明静态、未修改 Database 的重复 GraphBuilder build 稳定；未证明 mutation reset 或完整 analyzer/path-group 的复用安全。因此每个阶段 1 session 只运行一次 baseline，close 后才可创建下一个 session。
- Tcl boundary 保留现有命令和默认 CPU/full 语义；阶段 1 不向 Tcl 命令添加散乱 mode 参数。新 typed mode 首先由 ECC 配置、Python wrapper 与 native session API 承载。

### 2.3 文件规模与 ownership

`module.py`、`runner.py` 和 `STAInterface.cpp` 都已超过仓库审查建议阈值。新类型、解析、状态机和 lifecycle adapter 必须放入小模块；现有大文件只保留窄调用点。native session 放在 `src/operation/iSTA/interface/`。当前构建已经存在 `ista_interface -> ista_source -> ista_toolkit -> ista_interface` 的 target 闭环；阶段 1 只把 contract/session 源加入现有 `ista_interface` target，不新增 target-level edge，且 public contract header 不依赖 `ista_source` 实现头。configure、显式 test target build 和 wheel build 都作为依赖门禁。

## 3. 冻结的公开配置

阶段 1 最终采用现有参数系统中的以下公开名称：

```toml
[params.sta]
backend = "cpu"             # cpu | cuda
update_strategy = "full"    # full | incremental
fallback_policy = "error"   # error | full_with_record
```

内部 Workspace key 分别为 `STA backend`、`STA update strategy`、`STA fallback policy`。三项使用 `type="str"` 和 choices 校验。

默认值只存在于参数 schema 和 typed request resolver；不向 PDK parameter template 写入新键。这样旧 Workspace 和默认新 Workspace 的持久化参数不会出现无关字节变化，runner 对缺失键仍解析为 `cpu/full/error`。现有 `sta.json` 属于 liberty/corner 配置，不承载 execution mode。

## 4. Typed contract

Python 与 C++ 都定义以下相互独立的枚举和值：

```text
StaBackend: cpu | cuda
StaUpdateStrategy: full | incremental
StaFallbackPolicy: error | full_with_record
StaExecutionKind: baseline_only | full_update | incremental_update | fallback_full
StaPropagationScope: none | full_graph | affected_cone
StaFallbackReason: 阶段 0 schema 中除 null 外的 15 个固定 reason token
StaCapabilityReason: backend_unavailable
StaSessionStatusCode: unsupported | invalid_state | owner_conflict | init_failed | run_failed | cleanup_failed | quarantined
```

请求对象固定为：

```text
StaExecutionRequest {
  backend,
  update_strategy,
  fallback_policy
}
```

成功执行 record 的字段和类型固定为：

| 字段 | 类型与 nullability |
|---|---|
| `requested_backend` | `StaBackend`，非空 |
| `requested_update_strategy` | `StaUpdateStrategy`，非空 |
| `fallback_policy` | `StaFallbackPolicy`，非空 |
| `executed_backend` | `StaBackend`，非空 |
| `executed_update_strategy` | `StaUpdateStrategy`，非空 |
| `execution_kind` | `StaExecutionKind`，非空 |
| `propagation_scope` | `StaPropagationScope`，非空 |
| `incremental_batch_executed` | `bool` |
| `fallback_to_full` | `bool` |
| `fallback_reason` | `optional<StaFallbackReason>`；`full_update` 为 null，`baseline_only` 为 `not_applicable_no_mutation` |

通用 record validator 完整实现阶段 0 schema 的四种 `execution_kind` 交叉约束：

| kind | requested → executed strategy | backend | fallback 约束 |
|---|---|---|---|
| `full_update` | `full -> full` | 必须相同 | `fallback_to_full=false`，reason=null |
| `baseline_only` | `incremental -> full` | 必须相同 | `fallback_to_full=false`，reason=`not_applicable_no_mutation` |
| `incremental_update` | `incremental -> incremental` | 必须相同 | `fallback_to_full=false`，reason=null |
| `fallback_full` | `incremental -> full` | 可相同或不同 | policy=`full_with_record`，`fallback_to_full=true`，reason 为 schema 允许的非空 fallback reason |

因此 backend mismatch 只允许 `fallback_full`；strategy mismatch 只允许互斥的 `baseline_only` 或 `fallback_full` 两条路径。阶段 1 resolver 自身只会成功产生 `full_update` 与无 mutation 的 `baseline_only`，不会产生 `incremental_update` 或 `fallback_full`。

阶段 1 的 production execution record 与 benchmark sample 是不同层级。`cpu/full` 的一次性 signoff 结果使用 `execution_kind=full_update`，但不会因此伪造 mutation batch、batch timing 或 benchmark speedup。后续 benchmark 仍必须满足阶段 0 schema 对非空 batch 的额外要求。

native 使用唯一的 `StatusOr<StaExecutionRecord>` 等价模型：成功 status 必须带完整 record；unsupported/error status 绝不能带 record 或构造 executed 字段。`StaFallbackReason` 只进入成功 record，`StaCapabilityReason` 只说明阶段 capability，`StaSessionStatusCode` 只描述 capability/lifecycle 失败，三者不得互换。

pybind 将非法 token 映射为 `ValueError`，将已解析但不支持的 request 映射为带 request、`StaSessionStatusCode::unsupported`、`StaCapabilityReason::backend_unavailable`、state 和 message 的 typed session exception；Python wrapper 再规范化为 parent 的 typed error。owner/init/run/cleanup/quarantine 错误不携带 capability reason，只使用 session status code，绝不写入成功 record 的 `fallback_reason`。

## 5. 阶段 1 模式决策表

| 请求 | 结果 | native 行为 |
|---|---|---|
| `cpu/full/*` | executed=`cpu/full`，kind=`full_update`，scope=`full_graph`，`incremental_batch_executed=false`，`fallback_to_full=false`，`fallback_reason=null` | 运行现有 full STA 一次 |
| `cpu/incremental/*`，无 mutation | executed=`cpu/full`，kind=`baseline_only`，scope=`full_graph`，`incremental_batch_executed=false`，`fallback_to_full=false`，reason=`not_applicable_no_mutation` | 只建立 full baseline |
| `cuda/full/*` | typed unsupported，reason=`backend_unavailable` | 在 artifact 清理和任何 native init 前失败 |
| `cuda/incremental/*` | typed unsupported，reason=`backend_unavailable` | 在 artifact 清理和任何 native init 前失败 |

表中的 `*` 表示两种 fallback policy 都能解析。`full_with_record` 在没有真实 fallback 时只被记录，不会把 CUDA 静默改成 CPU。`baseline_only` 也不是 fallback。阶段 1 不暴露非空 mutation batch API；若绕过边界尝试执行，必须 unsupported。

## 6. Session 生命周期与异常安全

### 6.1 native 状态机

| 当前状态/调用 | 结果状态 | 行为 |
|---|---|---|
| `created + initialize`，支持且成功 | `initialized` | 取得 session lease 后初始化资源 |
| `created + initialize`，unsupported | `closed` | status=`unsupported`；不取得 lease、不调用 native lifecycle |
| `created + initialize`，init 失败且 rollback 全成功 | `closed` | status=`init_failed`；释放 lease，禁止对象重试 |
| `created + initialize`，rollback 有失败 | `closed` | status=`cleanup_failed`；rollback 已消耗唯一 cleanup attempt，对象释放 handle，全局进入 `quarantined(none)` |
| `created + close` | `closed` | no-op success |
| `initialized + runBaseline` 成功 | `baseline_executed` | 返回成功 record |
| `initialized + runBaseline` 失败 | `poisoned` | status=`run_failed`；保留主错误，只能进入 close |
| `initialized/baseline_executed/poisoned + close` | `closed` | best-effort cleanup；全成功才释放全局 lease，否则 quarantine |
| `closed + close` | `closed` | 幂等 no-op |
| 其他重复 initialize/run | 状态不变 | status=`invalid_state`，无副作用 |

session 删除 copy/move，析构为 `noexcept` cleanup 兜底；显式 `close()` 返回 typed status。析构 cleanup 失败只发送到不抛异常的 diagnostic sink，不得终止进程或伪造成功。

`STAInterface` 维护进程级 owner-aware lifecycle：`none | legacy | session(token) | quarantined(cleanup_owner)`；`cleanup_owner` 为 `legacy | session(token) | none`，表示尚存的一次不可转移 persistent-cleanup 权限。

- typed session object 的创建不取得 lease；成功 initialize 前原子取得唯一 token。
- legacy `initSTA()` 只能从 `none` 取得 `legacy` lease；typed initialize 只能从 `none` 取得自己的 token。
- 所有公开 stateful legacy API，包括 `runSTA/extractLib/updateTiming/writeSDF/reportTiming/createClock/setPropagatedClock/getPorts/getClocks/destroySTA`，只允许 `legacy` owner；typed session 调用 token-aware private/core entry，不能借道 legacy wrapper。
- `STAInterface::destroyInst()` 仅允许 lifecycle=`none`；活跃 lease、未完成 cleanup 或 `quarantined` 时明确拒绝，且不销毁 singleton。
- session run 只允许正常 `session(token)` 的匹配 token；close 允许正常 owner，或 `quarantined(session(token))` 中匹配的 cleanup token。任何其他调用必须在触碰 singleton 之前失败。
- 第二 session 或 legacy init 在已有 owner 时失败；未取得 token 的对象 close/析构绝不调用全局 destroy。
- 临时 pipeline cleanup 失败但 persistent owner 尚未 close 时，进入 `quarantined(current_owner)`；只有该 owner 可执行一次 best-effort persistent close。
- init rollback 已经 best-effort 尝试全部已取得资源；其中任一步 cleanup 失败即直接进入 `quarantined(none)`，已释放的 typed handle 或 legacy caller 不再拥有第二次 cleanup 权。
- persistent close 尝试完成后把 cleanup owner 消耗为 `none`，quarantine 保持 sticky；`quarantined(none)` 拒绝所有 run/init/close/destroy/destroyInst。
- 阶段 1 不提供 hard reset；对象侧 handle 可关闭，但 `destroyInst()` 或新 session 都不能假装清空 quarantine，只能 fresh process 恢复。
- 只有从未进入 quarantine 且 rollback/close cleanup 全部确认成功时，才释放为 `none` 并允许下一个 legacy 或 typed session。
- 析构 no-throw 路径遵守同一 cleanup-owner 消耗规则，不因对象销毁绕过 sticky quarantine。

native core 通过窄 operations/driver seam 测试状态机；同一 owner gate 同时被 legacy API 与 typed session production path 使用，不能只在 pybind 层模拟。

### 6.2 `STAInterface` 加固

- `destroySTA()` 在 owner/state 检查前不使用 `STALOG` 或解引用 singleton；`none` 直接幂等返回，正常 legacy owner 或 `quarantined(legacy)` 可 cleanup，其他 caller 拒绝且不触碰资源。
- init transaction 明确记录本次实际取得的 Logger、DataManager、DelayCalculator；失败时只逆序释放这些资源，不调用 `STADM.output()` 等成功 close 副作用。rollback 全成功恢复 `none`；cleanup 失败进入 `quarantined(none)`，因为本次 rollback 已消耗 cleanup attempt。
- `runSTA()` 在任何 singleton 使用前校验 initialized 与 owner。现有 full 顺序保持为 DelayCalculator runtime、GraphBuilder、ClockPropagator、TimingPropagator、PowerPropagator、TimingAnalyzer、PowerAnalyzer、TimingReporter、PowerReporter、SDFWriter。
- `extractLib()`、`updateTiming()`、`writeSDF()`、`reportTiming()` 等 legacy pipeline 的每个临时 singleton 与 DelayCalculator runtime 也必须复用同一 production cleanup ledger；只做 owner check 不足以保证异常安全。
- 每条 typed/legacy pipeline 在 work 失败时都继续逆序清理已取得的全部临时资源。临时 cleanup 全成功时保留原 work error，允许 owner 再正常 close；任一 cleanup 未确认成功时立即进入 `quarantined(current_owner)`。
- 正常显式 close cleanup 全成功时回到 `none`；任一失败时本次 close 已消耗 persistent-cleanup attempt，对象变 `closed`、全局变 `quarantined(none)`。析构使用同一路径但不抛异常，并把 failure 发到 diagnostic sink。
- typed/legacy 临时 pipeline 形成的 `quarantined(current_owner)` 只允许匹配 owner 再做一次 persistent close；尝试后无论成功与否都转为 sticky `quarantined(none)`。
- `quarantined(none)` 下重复 close 只做对象级幂等，不重复销毁 global resources。
- 上述任何 quarantine 都不得把 lifecycle 降回 `none`。
- 不改变 full STA 的阶段顺序、配置或 artifact 生成。

新增小型 `StaLifecycleGuard`/等价 seam，production 的 init/full、extract、update、report 和 write pipeline 实际使用它。unit fail injection 区分两类结果：普通 stage failure 但 cleanup 全成功时验证 owner close 后可重新初始化；cleanup callback 自身失败时验证所有剩余 cleanup 仍被尝试、全局 quarantine、后续 init 无 native 调用地拒绝。这不是只测未接入生产的 fake wrapper。

### 6.3 Python context manager

Python `IncrementalStaSession`：

1. canonical Python pure resolver 在两个 runner 入口解析 request 并做阶段 1 capability preflight。post-synthesis 必须在现有 stale artifact 删除和任何 engine/native 创建前 preflight；signoff 必须在 `get_eda_instance()` 前 preflight。
2. `ECCToolsModule.run_timing()` 对 direct caller 再执行同一 pure preflight，且早于其 `discard_sta_run_outputs()`、library/SDC/SPEF 初始化和 native factory。
3. 通过新增 native factory 创建 C++ session；`__enter__` 显式 initialize。若 factory/init 返回失败 status 或抛异常，`__enter__` 主动 close/release handle 后再重抛，因为失败的 `__enter__` 不会触发 `__exit__`。
4. `run_full_baseline()` 返回并严格校验 native execution record；`__exit__` 总是显式 close；close 幂等。
5. 无主异常时传播 close failure；已有 init/body 主异常且 close 也失败时，保留主异常为顶层并用 exception chaining/typed detail 附带 cleanup failure。

`ECCToolsModule.run_timing()` 在 session close 后才发布 artifacts，并返回 typed execution record。现有调用者忽略返回值仍兼容。runner 记录一条 requested/executed/fallback 日志，但不新增默认 sidecar，不修改 timing/power/report/SDF 内容或路径。

## 7. 拟修改文件与符号

### 7.1 parent ECC

- 新增 `chipcompiler/tools/ecc/sta_mode.py`
  - enums、`StaExecutionRequest`、`StaExecutionRecord`、typed unsupported error；
  - Workspace 参数解析、阶段 1 pure mode resolver，以及覆盖冻结四种 kind 的通用 record validator。
- 新增 `chipcompiler/tools/ecc/sta_session.py`
  - native protocol、异常链规则与 Python `IncrementalStaSession` context manager。
- 修改 `chipcompiler/tools/ecc/module.py`
  - `run_timing(..., execution_request=None)` 的窄接入；direct-call preflight 早于任何 discard/native 调用；默认 request 不改变 native config map；返回 execution record。
- 修改 `chipcompiler/tools/ecc/runner.py`
  - post-synthesis 在外层 stale cleanup/engine creation 前 preflight；signoff 在 engine creation 前 preflight；随后转发同一 immutable request并记录结果。
- 修改 `chipcompiler/cli/project/params.py`
  - 注册三个 `[params.sta]` choice 参数。
- 修改 `docs/specification/cli-design.md`
  - 记录公开配置、默认行为和阶段 1 unsupported 范围。
- 新增 `test/tools/ecc/test_sta_mode.py`、`test/tools/ecc/test_sta_session.py` 与 `test/tools/ecc/test_runner_sta_mode.py`；窄更新现有 `test_module_timing.py`、registry 与 runner exact-call tests。
- 修改 `docs/incregpusta/stage0-feature-support-matrix.md`，把 graph generation/fingerprint 的首个实现门更正为阶段 2，并保留阶段 1 execution record 要求。
- 修改仓库外权威计划 `/home/shigure/code/docs/incregpusta-implementation-plan.md` 的 PDF 路径和阶段 1 设计审查记录。

不修改 PDK parameter templates，不修改默认 STA artifact 集合，不把 mode 字段塞入 native `config_dict`。

### 7.2 ecc-tools

- 新增 `src/operation/iSTA/interface/StaExecutionContract.{hpp,cpp}`
  - native enums/request/record/`StatusOr` 等价 status、字符串边界解析、阶段 1 mode resolver。
- 新增 `src/operation/iSTA/interface/IncrementalStaSession.{hpp,cpp}`
  - 单次 baseline session 状态机、RAII、owner token 和 operations seam。
- 新增 `src/operation/iSTA/interface/StaLifecycleGuard.{hpp,cpp}`（或同等小型模块）
  - production init/full/extract/update/report/write pipelines 使用的异常安全 cleanup stack 与 fail-injection seam。
- 修改 `src/operation/iSTA/interface/STAInterface.{hpp,cpp}`
  - legacy/session 共用 lease core、session factory、transactional init/full-run cleanup/idempotent owner close。
- 修改 `src/operation/iSTA/interface/CMakeLists.txt`
  - 新源码加入现有 `ista_interface`，不增加任何新 target edge。
- 修改 `src/interface/python/py_ista/{py_ista.h,py_ista.cpp,py_register_ista.h}`
  - 保留 owner-aware legacy 函数；新增 pure resolver、native session factory/class binding；字符串只在 binding 边界转为 enum。
- 新增 `src/operation/iSTA/test/StaExecutionContractTest.cpp`、`IncrementalStaSessionTest.cpp` 和 lifecycle guard/fail-injection test；targets 精确链接 owner `ista_interface`，并修改 test CMake 与 wheel CI 显式 build target。
- 修改 `src/operation/iSTA/test/baseline/StaFullBaselineProbe.cpp`
  - 用新 session RAII 执行默认 CPU/full；保持文件低于 700 行并保持 checked-in golden payload 不变。
- 新增小型 same-process native lifecycle probe/driver（若无法通过替换旧 main 保持 probe 小于 700 行），输出两个 session snapshot 供 controller 分别比较。

## 8. 数据流与不变量

```text
TOML/CLI
  -> ParamSchema choice validation
  -> Workspace internal keys
  -> StaExecutionRequest
  -> Python stage-1 preflight
  -> native StaExecutionRequest
  -> IncrementalStaSession
  -> existing STAInterface::runSTA()
  -> native StaExecutionRecord
  -> Python invariant validation
  -> session close
  -> existing atomic artifact publish
  -> runner telemetry log / caller return value
```

必须持续成立：

1. 默认 request 精确为 `cpu/full/error`。
2. unsupported 在两个 runner 入口和 direct module 调用中，都在任何旧 artifact 删除、engine/native init 或 publish 前失败。
3. 通用 validator 支持冻结的四种 kind；backend mismatch 只允许 `fallback_full`；strategy mismatch 只允许 `baseline_only` 的非 fallback incremental→full，或 `fallback_full` 的 recorded fallback incremental→full。
4. `StaFallbackReason` 与 `StaSessionStatusCode` 独立；success record 与 error status 互斥。
5. 阶段 1 成功结果永远 `propagation_scope=full_graph`、`incremental_batch_executed=false`，永远不报告 speedup。
6. 每个 session 只拥有并关闭自己的 STA lifecycle；legacy 与 typed caller 都受同一 lease 约束，多 corner 不共享 timing state。
7. native session close 先于 artifact publish；publish 失败时 native STA 也已清理。
8. legacy binding 保留；Tcl 和未迁移 native caller 仍得到原 CPU/full 行为，但所有 stateful API 和 `destroyInst()` 都不能绕过 lease/quarantine。
9. 阶段 0 golden snapshot、报告集合和 normalized artifact comparison 不改变。
10. cleanup 全成功才允许下一 session；cleanup failure 后必须 fresh process，禁止自动恢复。

## 9. 测试计划

### 9.1 native unit

- 所有 enum 正/反向字符串转换；非法大小写、空值和未知 token 拒绝。
- 八个 backend × strategy × policy request 均解析；CPU/full 与 CPU/incremental outcome 整对象精确相等；CUDA 在 init callback 前返回 `backend_unavailable` 且无 record。
- native enum 字符串集合直接读取并对照阶段 0 schema enum；full 的 reason 精确为 null，baseline-only 精确为 `not_applicable_no_mutation`。
- 四 kind exact invariant table 的正反例：尤其 baseline-only 与 fallback-full 两种 strategy mismatch 互斥，backend mismatch 只能 fallback-full。
- 初始化成功、run 成功、显式 close、重复 close、created-close、重复 initialize/run 的状态与调用次数。
- init/run callback 抛异常时的 poisoned/closed、cleanup 精确一次、析构 no-throw；status code 不进入 fallback reason。
- legacy/session 互操作覆盖 active session 下 legacy run/extract/update/report/destroy/destroyInst，active legacy 下 typed init，second session，以及 owner 正常 close 后 next session。
- production lifecycle guard 对每个 init/full stage fail injection 后逆序清理；cleanup 成功才验证下一 session，cleanup callback failure 则验证 quarantine、其余 cleanup 仍执行、下一 init 零 native 调用拒绝。
- legacy extract/update/report/write 分别注入 work failure 与 cleanup failure：前者完整清理后允许 owner close/re-init，后者只允许原 legacy owner 做一次 persistent close，随后仍保持 quarantine 并拒绝下一 init。
- typed run 临时 cleanup failure 后保留原 token；原 session close 仍尝试 persistent cleanup，但 process quarantine 保持 sticky，下一 typed/legacy init 均零 native 调用拒绝。
- typed 与 legacy init rollback-cleanup-failure：每个 cleanup callback 只尝试一次，handle/token 立即释放，状态为 `quarantined(none)`；后续 close/destroy/init 均不触发 native callback。

### 9.2 Python unit

- schema/TOML/CLI 的 defaults、choices、四组合解析和内部 key mapping。
- Python record key 集合精确等于冻结 `$defs.mode.required`；四种 kind 的 cross-field validator 与 schema一致。
- binding-level 八组合 parity：同一 request 的 Python/native resolver 得到相同 outcome 或 reason；所有 enum 字符串集合与 schema逐项相等。
- 实际 native→Python CPU/full 与 baseline-only record 通过冻结 mode 规则；full reason 精确为 null，baseline-only reason 精确为固定字符串。
- 默认 CPU/full 保持原 native config dict、调用顺序和 artifacts；CPU/incremental 无 speedup/fallback。
- post-synthesis 和 module direct CUDA 请求前放置 stale sentinels，断言文件字节/目录/call list不变，discard/native factory 均未调用。
- post-synthesis unsupported 继续 warning+False；signoff unsupported 在 engine creation 前按既有失败语义传播。
- `__enter__` init false/throw 主动 close；body+close 双失败保留 body 为主并 chain cleanup；单独 close failure传播；cleanup failure 后下一 session 以 quarantined 零副作用拒绝；重复 close幂等。
- 两个 fake corner 各自 create/init/run/close，record 和 native handle 不共享；`full_with_record` 不伪造 fallback。

### 9.3 integration/regression

1. 重新 CMake configure；显式构建全部新增 unit/lifecycle targets 与 `ista_full_baseline_probe`，并验证 wheel CI target list包含它们。
2. `ctest -L '^ista_unit$'`。
3. `ctest -L '^ista_smoke$'`：chain/diamond 每 case 至少 3 个 fresh process；每个 probe 内再运行两个真实顺序 native session，两个 snapshot 分别与 Stage 0 golden 比较，并检查 config/record/singleton不串扰。
4. 在第一个真实 session 活跃时尝试第二 session 与 legacy destroy，断言无副作用失败；受控 caller/run-stage failure清理后，下一真实 session成功。
5. benchmark schema validator self-test以及 production record/schema parity tests。
6. parent STA/module/runner/parameter 定向 pytest。
7. parent 全部非 PDK pytest，与阶段 0 命令一致。
8. `git diff --check`、Ruff format/check、C++ formatter/static checks（按仓库现有工具可用性）。

本阶段没有性能实现；performance smoke 记为不适用，不产生 speedup artifact。

## 10. 阶段冲突的解释与文档修正

- 支持矩阵把 graph/session generation 与 fingerprint 写成“阶段 1 起”可观测，但路线图明确把 stable ID、graph generation/fingerprint 放在阶段 2。本阶段不做占位 hash 或假 generation；只交付 lifecycle state 与 execution record，并在支持矩阵中把 graph generation/fingerprint 门改为阶段 2。
- 总体 session 图中的 `export_csr_once` 从阶段 2 才启用；阶段 1 路径只有 create/init/full baseline/close。
- `fallback_reason=not_applicable_no_mutation` 是 baseline outcome reason，尽管 `fallback_to_full=false`；以阶段 0 冻结 schema 为准。
- 权威计划中的 PDF 路径应修正为 `/home/shigure/code/docs/incregpustaiccad-25.pdf`，只修文档事实，不重新解释论文。

## 11. 设计审查记录

Round 1 由三个未参与撰写的 subagent 独立审查，结论均为 `REQUEST_CHANGES`。已纳入：

- 把 unsupported preflight 提到 post-synthesis/signoff runner 的所有 artifact/native 副作用之前；
- 修正 `__enter__` 失败 cleanup 和 primary/cleanup 双异常规则；
- 冻结 legacy/session 共用 owner lease、完整状态转换和 typed status/record 互斥；
- 增加 production lifecycle guard fail injection 与同进程真实双 session probe；
- 完整支持冻结四 kind 的通用 record validator，并增加 schema/binding parity；
- 承认现有 CMake target 闭环、不新增 edge，并补全 support matrix/权威计划文档交付。

Round 2 仍为 `REQUEST_CHANGES`：修正 baseline-only 的合法 strategy mismatch；把 fallback reason 与 lifecycle status code 分型；把所有 stateful legacy API/`destroyInst()` 纳入 lease；cleanup failure 改为 process quarantine 并补负测。

Round 3 的 native 复审仍为 `REQUEST_CHANGES`：把 extract/update/report/write 的临时资源链纳入同一 production cleanup ledger，并新增独立 `StaCapabilityReason`。

Round 4 的 contract 复审仍为 `REQUEST_CHANGES`：quarantine 改为保留 `previous_owner`，仅原 owner 可执行一次 persistent close，且 quarantine 始终 sticky。

Round 5 的 native 复审仍为 `REQUEST_CHANGES`：区分 `quarantined(current_owner)` 与已消耗 cleanup attempt 的 `quarantined(none)`，冻结 init rollback 失败后的 handle/token 生命周期。

Round 6 由原三位 reviewers 独立复审，结论均为 `APPROVE`，无 remaining finding；本设计据此冻结为 v1.0 并进入实现。

## 12. 成功标准与回滚

只有以下条件全部满足才标记阶段 1 完成：

- 独立设计审查 APPROVE；实现后独立代码审查 APPROVE，所有 finding 已闭环。
- 默认 CPU/full 的 stage 0 native golden 与 parent artifact tests 全绿。
- 四组合可解析，CPU/incremental no-mutation 语义正确，CUDA 两组合无副作用地 unsupported。
- init/close、异常清理、幂等 close 和顺序 multi-corner 隔离测试全绿。
- 无新增 CSR/edit/CUDA 算法，无 incremental/GPU 性能声明。
- 阶段 1 报告完整记录文件/符号、行为、配置、review、命令/结果、fallback 数和下一阶段 gate。

回滚时可删除新增 typed/session 小模块并把 `module.py`/`runner.py` 恢复为 legacy 调用点；legacy native binding 始终保留，因此回滚不要求迁移 artifacts 或 Workspace。若 native session 路径破坏 golden，停止阶段 1，不以 legacy fallback 掩盖失败。
