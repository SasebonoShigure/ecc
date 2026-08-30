# 阶段 0：增量式 STA 功能支持矩阵

## 1. 状态与使用范围

本文冻结阶段 0 的能力边界，并作为后续实现、review 和测试的判定依据。当前可执行参考路径只有 ECC 既有的 **CPU/full STA**；阶段 0 不实现 typed mode、增量更新、CUDA backend 或 fallback telemetry，也不改变 STA 行为。下表中的“首版计划”“显式全量回退”和“后续研究”均为后续阶段必须实现并验证的契约，不表示当前代码已经支持。

论文的增量部分是图结构更新和 levelization；其 GPU timing propagation 仍遍历全图。论文没有给出 GPU affected-cone AT/RAT propagation 算法，因此 affected-cone 不属于阶段 0–10 的论文复现门禁。

分类定义：

| 分类 | 含义 |
|---|---|
| 当前基线 | 阶段 0 可用于 correctness oracle 的既有 CPU/full 路径。 |
| 首版计划 | 论文 buffer-insertion workload 的兼容子集；必须在对应后续阶段实现且通过 differential test 后才能宣称支持。 |
| 仅显式全量回退 | 不允许走增量路径；只有调用者选择 `full_with_record` 时才可重建 full baseline，并完整记录 requested/executed/fallback。 |
| 后续研究 | 明确推迟到论文复现完成之后，不属于当前路线图的通过条件。 |
| 不支持/硬错误 | edit 本身破坏 STA 图或语义约束；full rebuild 也不能把无效输入变为有效输入，必须在 publish 前拒绝。 |

## 2. 执行模式矩阵

| 请求模式 | 阶段 0 状态 | 后续目标语义 | propagation scope |
|---|---|---|---|
| `cpu/full` | 当前基线 | canonical edit 后重建 native timing graph，执行 full CPU levelization 与 full CPU propagation。 | `full_graph` |
| `cpu/incremental` | 未实现 | targeted host Dual-CSR update，CPU mixed levelization，随后 full CPU propagation。 | `full_graph` |
| `cuda/full` | 未实现 | 每个 mutation batch 都完整重建 CSR、完整传输所需数据，并执行 full GPU levelization/propagation；不得复用增量 device state 缩短基线。 | `full_graph` |
| `cuda/incremental` | 未实现 | CPU normalize/descriptors，targeted device Dual-CSR update，CPU mixed topo 与 GPU level reconstruction，随后 full GPU propagation。 | `full_graph` |
| 任意 `*/incremental` 且没有 mutation | 未实现 typed contract | 只建立 full baseline：`execution_kind=baseline_only`、`incremental_batch_executed=false`、`fallback_to_full=false`；不得计入 incremental speedup。 | `full_graph` |
| CPU/GPU affected-cone timing propagation | 后续研究 | 论文复现完成后单独立项、单独验证、单独报告，不得混入核心四模式 speedup。 | `affected_cone`（仅将来实现后） |

### 2.1 阶段 2 Step 7 实现边界

下表只记录当前实现进度，不改写上表冻结的阶段 0 历史状态，也不把尚未接入 mutation batch 的 session 计为增量加速。

| 能力 | 截至阶段 2 Step 7 的状态 |
|---|---|
| `cpu/full` session | 保持既有 full execution record 与 artifact 兼容；CSR snapshot observation 在 active/released 均为 `None`。 |
| `cpu/incremental` 且没有 mutation | 已实现 `baseline_only` typed record；初次 full capture 发布与 analysis context、session token 绑定的 `ready/gen0` observation，正常 close 后只发布经验证的 `released` observation。 |
| direct / all-corner STA context | 已实现 immutable analysis context、SPEF/RC consistency、regular-file/alias/unique-destination pure preflight，以及每个 corner exact-once observation sink；失败先于 artifact discard、subflow、engine 与 native session。 |
| mutation batch、generation > 0、reference/scatter production API、CUDA | 尚未作为 production 增量路径开放，不得据此宣称 incremental speedup 或 backend parity。 |

## 3. Edit 支持矩阵

“Error policy”表示请求 `fallback_policy=error` 时的处理；“Full-with-record”表示调用者显式选择 `fallback_policy=full_with_record` 时的处理。所有 edit 必须先 normalize/validate，再修改 staged state；失败不得留下部分 mutation。

| Edit / 环境变化 | 分类 | Incremental contract | Error policy | Full-with-record |
|---|---|---|---|---|
| 无结构 edit 的普通 signoff/full STA | 当前基线 | 不适用。 | 执行 `cpu/full`。 | 不构成 fallback。 |
| session 初始化时没有 mutation | 当前基线的观测语义 | 只建立 full baseline，记录 `baseline_only`；不得伪造一个 incremental batch。 | 不报错，但不得计入 incremental speedup。 | 不构成 fallback。 |
| session 中提交 empty/no-op batch | 不支持/输入错误 | mutation batch 必须至少包含一个规范化后仍有效的 edit；空 batch 不执行、不 bump generation。 | 明确 `empty_batch`，保持 committed state 不变。 | 仍报错；full rebuild 不能把无效 benchmark 样本变成有效 mutation。 |
| same-batch insert→remove 同一 creation token | 仅显式全量回退；论文语义待验证 | 首版不猜测正反 pending-list 的抵消语义。 | 明确 `same_batch_insert_remove_unsupported`。 | 最终 canonical design 合法时 fresh full rebuild，并记录原因。 |
| duplicate remove/update 或互相冲突的重复 edit | 不支持/输入错误 | normalize 阶段必须在 stage 前拒绝重复/冲突 descriptor。 | 明确 `duplicate_or_conflicting_edit`，保持 committed state 不变。 | 仍报错；不得用 full fallback 掩盖 malformed request。 |
| append-only 新 data node；session 内 `NodeId`/`ArcId` 单调追加 | 首版计划 | 允许；不得复用已删除或历史 ID。 | 合法 batch 执行 incremental。 | 合法 batch 不应 fallback。 |
| buffer insertion 配对 edit：删除旧 `source→existing_destination`，并新增 `new_buffer→existing_destination` | 首版计划 | prepare 阶段必须证明 existing destination 的 reverse fan-in 是严格“一删一增”，并原位复用 `BaseIn` slot。 | 证明失败则在 publish 前报错。 | 证明失败则 full rebuild，并记录原因。 |
| existing source 因 buffer insertion 产生额外 outgoing edge | 首版计划 | `BaseOut` 可复用合法 tombstone；剩余 overflow 写入独立 `AuxOut` row。不得把 reverse edge 混入 `AuxOut`。 | capacity/descriptor contract 不满足则报错。 | full rebuild，并记录 capacity 或 contract 原因。 |
| buffer insertion 中的 old→new、new→old、new→new edge | 首版计划 | 仅在同一已验证 buffer-insertion batch 内允许；mixed graph 必须通过拓扑排序与 processed-count 检查。 | 非法组合报错。 | 语义合法但超出窄 contract 时 full rebuild并记录。 |
| 保持同一 `ArcId` 的 data-edge delay/payload update | 首版计划 | 允许 targeted payload update；不得借此掩盖 library、corner、constraint 或 parasitic fingerprint 变化。 | identity/fingerprint 不匹配则报错。 | full rebuild并记录 fingerprint 原因。 |
| combinational instance 的 cell master replacement | 仅显式全量回退 | 即使 pin 名兼容，也可能改变 cell arcs、unate sense、capacitance 与 delay model；不属于首版同一 `ArcId` payload update。 | 明确 `cell_master_replacement_unsupported`。 | canonical replacement 合法时 fresh full rebuild，并记录 library/cell fingerprint 变化。 |
| parallel arcs | 首版计划的数据模型要求 | 用稳定 `ArcId` 区分；不能只用 `(src,dst)` 作为 identity，outgoing/incoming 解码必须保持严格转置。 | identity 歧义时报错。 | canonical full graph 能表达时可 full rebuild并记录。 |
| 任意 old→old 新增、删除或重连（不属于上述 buffer-insertion 配对 edit） | 仅显式全量回退 | 首版 incremental 不支持。 | 明确 `unsupported_edit`。 | canonical edit 合法时 full rebuild并记录。 |
| reverse fan-in 不平衡，或需要 general reverse auxiliary storage / `AuxIn` | 仅显式全量回退；`AuxIn` 为后续研究 | 首版要求 `BaseIn` 一删一增，不能满足即越界。 | 明确 `reverse_slot_not_replaceable`。 | full rebuild并记录；不得把 forward/reverse overflow 混入同一 CSR。 |
| general fanout redistribution，无法证明所有 existing destination 的 `BaseIn` slot 可替换 | 仅显式全量回退 | 不属于“论文 buffer-insertion workload 的兼容子集”。 | 明确报错。 | full rebuild并记录。 |
| node deletion | 后续研究；当前仅显式全量回退 | 首版 incremental 不支持。 | 明确 `node_deletion_unsupported`。 | canonical design 合法时 full rebuild并记录。 |
| node/arc ID reuse | 后续研究；当前不允许 | session identity contract 禁止复用；重建后建立新 session/generation，而非在原 session 复用 ID。 | 明确报错并使旧结果不可 publish。 | 关闭旧 session，full rebuild/reinitialize，并记录。 |
| CSR compaction / tombstone reclamation | 后续研究 | 不属于首版正常 incremental batch；capacity growth/rebuild 必须有 telemetry。 | 若容量不足且 policy 不允许重建则报错。 | 显式 rebuild并记录 `capacity_fallback`/原因。 |
| clock net、clock topology 或 clock arc edit | 仅显式全量回退 | data-only incremental session 不支持；clock fingerprint 变化立即 invalidate。 | 明确报错，禁止使用旧 clock state。 | fresh full rebuild/reinitialize并记录。 |
| clock constraint edit | 仅显式全量回退 | 不支持复用 baseline clock/constraint state；constraint fingerprint 变化立即 invalidate。 | 明确报错。 | fresh full rebuild/reinitialize并记录。 |
| data timing constraint edit（如 I/O delay、exception、required-time 语义） | 仅显式全量回退 | 首版 structural incremental contract 不覆盖 constraint mutation。 | 明确报错。 | fresh full rebuild/reinitialize并记录。 |
| library 或 library-cell timing model 改变 | 仅显式全量回退 | library fingerprint 变化立即 invalidate；不得视为普通 arc payload update。 | 明确报错。 | fresh full rebuild/reinitialize并记录。 |
| analysis corner / operating condition 改变 | 仅显式全量回退 | corner-specific timing arrays 不得跨 corner 复用。 | 明确报错。 | 新 corner 的 fresh full rebuild/reinitialize并记录。 |
| SPEF、RC/parasitic 数据或提取上下文改变 | 仅显式全量回退 | 首版 data-only session 不证明寄生状态的增量一致性。 | 明确报错。 | 在 canonical parasitic state 可重建时 fresh full run并记录。 |
| sequential element 插入、删除、master 替换或 sequential arc edit | 仅显式全量回退 | 首版仅接受 data-net structural edits，不覆盖 start/end point、clock/data arc 或 check arc 语义变化。 | 明确报错。 | canonical edit 被现有 full STA 支持时 fresh full rebuild并记录。 |
| 多 corner 共享 device topology/state | 后续研究 | 未单独证明前不得共享 corner-specific timing state。 | 请求共享时明确 unsupported。 | 各 corner 独立 full session；这不是静默共享 fallback。 |
| 组合环或 mixed levelization processed-count 不等于节点数 | 不支持/硬错误 | graph validation 必须在 publish 前失败。 | 报错，不发布 staged graph/timing。 | 仍报错；full rebuild 不能把非法 cycle 变合法。 |
| 多 driver / driver identity 冲突 | 不支持/硬错误 | 首版不定义冲突消解；不能生成歧义的 incoming/outgoing transpose。 | 报错，不发布。 | 仍报错；除非未来 canonical full-flow 明确定义并验证该语义。 |
| 阶段 0–9 直接修改生产 `EngineDB/IDB`、placement/legalization 或物理 RC | 不支持（该阶段） | semantic timing harness 只操作 isolated iSTA Database/CSR staged view，不得宣称完成物理 buffer insertion。 | 明确拒绝越权 mutation。 | 直到阶段 10 跨层事务 gate 完成前，不得以 full fallback 冒充物理事务成功。 |

## 4. requested / executed / fallback 可观测性契约

阶段 1 起，每次 production 运行都必须输出并可由测试断言以下 execution record；从实际引入 mutation batch 的阶段起，每个 batch 也必须输出同形记录：

- `requested_backend`、`requested_update_strategy`、`fallback_policy`；
- `executed_backend`、`executed_update_strategy`、`execution_kind`；
- `incremental_batch_executed`；
- `fallback_to_full` 与非空、稳定分类的 `fallback_reason`（发生 fallback 时）；
- `propagation_scope`，核心四模式固定为 `full_graph`。

graph/session generation、fingerprint 以及 capacity grow/rebuild/invalidation 事件的首个实现与强制可观测门是阶段 2。阶段 1 只交付 execution record，不得填充占位 generation 或伪 fingerprint。

处理规则：

1. 禁止 silent fallback。`requested_*` 和 `executed_*` 不一致时必须可解释，并由 policy 明确授权。
2. `fallback_policy=error` 下，unsupported edit 必须在 staged publish 前失败；committed generation、native object graph、host/device CSR 与 timing 结果保持不变。
3. `fallback_policy=full_with_record` 只对语义合法但超出 incremental contract 的 edit 生效。执行 full rebuild时设置 `fallback_to_full=true` 并记录具体原因；无 mutation 的 `baseline_only` 不是 fallback。
4. 请求 CUDA 但构建或设备不可用时默认报错；只有显式 policy 允许时才可选择已实现的 fallback，并同时记录实际 backend 与 update strategy。
5. correctness benchmark 的 incremental case 强制 `error`，并断言 `fallback_to_full=false`。任何 fallback 样本、空 batch 或 `baseline_only` 样本都不得计入 incremental speedup。
6. invalid graph（例如 cycle 或未定义的 multi-driver 冲突）不能通过 full fallback 获得“成功”状态。

## 5. 首版能力声明的用词门禁

在对应 correctness gate 全部通过前，文档、日志和 benchmark 只能使用以下准确描述：

> 计划支持论文 buffer-insertion workload 的兼容子集：append-only 新节点、可证明的 `BaseIn` 一删一增 slot replacement、existing-source overflow 的 `AuxOut`，以及 full-graph CPU/GPU timing propagation。

不得宣称支持 general incremental STA、任意 Algorithms 1–4 edit、general reverse auxiliary CSR、node deletion/ID reuse、arbitrary old→old edit，或 CPU/GPU affected-cone timing propagation。
