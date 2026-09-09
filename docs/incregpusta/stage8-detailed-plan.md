# Stage 8：GPU targeted Dual-CSR 更新详细计划

状态：2026-09-08 独立设计审查 APPROVE；2026-09-09 实现、独立代码审查及真实 ON/OFF 验收完成，见 [验收报告](stage8-progress-report.md)。前置 Stage 7 已验收，见 [报告](stage7-progress-report.md)。用户已明确授权 Stage 7–8 及生产 CUDA 集成；本轮不自动 commit/push。遵循总计划、开发检查规范和严格审查标准。

## 1. 范围与实际执行

Stage 8 在真实 native buffer insertion 的逐批路径维护持久 GPU Dual-CSR，以 remove/change/reverse-change、append、Aux 与 metadata patch 更新设备，再执行完整 GPU levelization/propagation。保持 Stage 7 CUDA full 为独立 oracle。Stage 9 才提供 mixed GPU levelization；本阶段不将 `cuda/incremental` 通用 capability 提前标为完成。生产 benchmark runtime 提供明确的 `cuda/targeted-full-levelization` 执行记录，不向现有两值 UpdateStrategy 偷塞含义不同的成功值。

加载阶段保留两个已有生命周期：Stage 7 full baseline 建立分析后的 native DB 和合法 guard 状态，随后为 Stage 8 建立持久 device owner。实测合计两次完整 export/pack；`initialization.scope=persistent_device_session_only` 仅计持久设备初始化，完整加载/分析/逐批/清理均计入 controller 的 `process_ms`。此边界于 2026-09-09 经独立设计审查 APPROVE，不宣称初始化最优或仅执行一次。每批 host 仅做 normalize、局部适用性检查、canonical native 编辑、稳定 ID/address 元数据和描述符生成；禁止调用 CPU DualCsr updater/backend、CPU timing/FIFO、全量 GraphBuilder 或全量 CSR export。ON 独立诊断可在计算后导出并比较，但不会混入 OFF 正式采样。

## 2. 所有权和设备接口

新增具体 `CudaDualCsrSession`（`timing_cuda/CudaDualCsrSession.hpp/.cu`），封装 CUDA runtime 所有权，不增加虚函数/策略框架。初始化接收验证过的 baseline `CsrReferenceInput`，拥有设备图、seed buffers、stream 和事件。每批 `stage(patch)` 返回相同具体类型的独立 device candidate，持有计算值和目标 generation；受控 replayer 完成 native scatter preparation 后用 noexcept owner move/swap 发布。不再套 verified stage/token 类型。device-only `publish(candidate)` 检查不可篡改的 origin owner、session 和 expected generation，失败返回 false 且不改变状态，成功仅 noexcept swap；消费后的 candidate 不可重复发布。算法公开入口没有 native 发布权限。接口必须绑定 session、expected/target generation 和 high-water；不能公开通用 skip-validation。

每次尝试分配 detached device candidate，D2D 复制持久未变数据，上传变化后执行 patch kernel。旧 device owner 在所有 GPU/native 准备成功前保持原样。该实现承认 O(N+E+timing storage) D2D 事务隔离成本，并完整计量；不构建 GPU rollback journal，不声称只有 delta 总成本。容量采用 checked size/byte arithmetic；明确 grow/allocation 计数，无静默 CPU fallback。CUDA API/sync/context 错误使该 session poisoned；简单 host 预检拒绝不破坏旧 owner。失败后只有实际验证安全的路径才允许重试。

Host 持久状态仅包括 session/generation/high-water、canonical stable node/arc bindings、active 状态、Base row offsets/capacity、Aux source→row/offset/length、child/table spans 和 stable→native 结果映射。不得保存可供完整遍历的 Base physical slots、所有 Aux ArcId 或所有 timing table/payload 的 CPU 副本。初始 pack 临时对象在上传后释放。

`CudaDualCsrPatch` 使用既有 remove/change/reverse-change 和 node/arc append 等明确 descriptor 数据类型，但不携带 `ExpectedBeforeBinding`、完整 `DualCsrState`、full receipt 或假的 `PreparedBatch`。必要新增字段为 batch binding、变化的 typed payload、appended rows 和 Aux expected/replacement rows。受影响旧行从 native canonical adjacency 与 stable bindings 局部读取；Base 始终是 canonical active prefix 后接 tombstone，Aux 是 overflow suffix，沿用当前 CPU descriptor 的排布规则。device 对实际物理 slot 检查 expected；host 当前元数据不能替代设备适用性证明。

三个明确更新 kernel 实现 Base remove、Base change、BaseIn reverse-change；同批禁止物理 slot 冲突，边界和 expected 检查始终执行。Arc deactivate/payload patch 与新行/元数据 copy 只作用 candidate。Aux offsets 可在 host 根据行长度重算；不变 Aux 行 D2D、变化行 H2D，禁止全 Aux D2H 再上传。append/payload 编码提取 Stage 7 单条 arc/table 的机械 pack helper；不共享 CPU/GPU timing 计算。

## 3. GPU Base ∪ Aux 与 timing 值

`CsrCudaDeviceTypes.hpp::DeviceView` 增加明确 Aux 字段。窄 device adjacency helper 按 Base prefix→Aux suffix 遍历；Stage 7 Aux 为空，保留原 full 行为。levelizer 的 indegree 从完整 BaseIn 读取；所有 outgoing loops（levelize、dynamic、arrival/path、required）跳过 tombstone 并消费 Aux，不先 flatten。实际 status/cycle/processed count、容量和 finite 检查保留。

设备保存 seed-only nodes/paths，candidate 从 seed buffers D2D 重置；新 buffer pin seeds 为正确默认初态，root/end/clock tag 不变。生产 buffer adapter 拒绝改变 root/end/tag 的编辑；算法层为既有 Aux microcase 支持显式新增 source/endpoint seeds 及 roots/ends/endpoint metadata patch，复用既有 tag 编码并检查 append 范围和引用。不得构造全图输入再 packSeeds，也不得把前一批计算结果当 seed。Arc/child state 每批重新初始化，inactive arc 不参与计算。

为了避免构造假的完整 source identity，将 `CsrTimingResult` 的实际 value 字段提取为非多态 `CsrTimingValues`，`CsrTimingResult` 保留 schema/source_identity 并继承这些纯值字段，现有 `.nodes/.arcs/...` 消费方式不变。Stage 7 pack/unpack 最终补真实 identity；Stage 8 返回纯值，按受控 session/generation 绑定发布。不要改 public validator 的完整输入要求，也不要将未计算的 fingerprint 写成成功证明。

Stage 8 host 解码只需要真实返回值、active/child-index spans、clock/name/layout 元数据；不需要完整 arc/table payload。复用 unpack 机械函数，Stage 7/8 调用同一值解码。身份无关结果对比在 ON adapter 中结合真实 native canonical keys完成；OFF 不生成全功能对象。

## 4. Native 图局部编辑与稳定解析

新增 graph-preserving candidate 的具体构造入口，复用 `NativeDatabaseCandidate` unique_ptr 所有权。Database 声明析构但无 move，不能使用 `database = std::move(staged)`：实际 copy 会留下指向临时库的 Arc 指针。创建一次 detached Database 后，按源/候选库相同 cell 与 library-arc ordinal 重绑 `Arc::_timing_cell_arc`；拒绝不属于源库的指针。之后直接修改该对象，最终只移动 unique_ptr，不再赋值 Database。

将 GraphBuilder 已有单实例 cell arc、单 net driver/load 和 net/cell Arc 构造提取为接收 `Database&` 的 canonical helper（独立小文件），旧全量 GraphBuilder 复用相同实现。局部 editor 从已有 normalize/BufferInsertionMutation/raw insertion 逻辑抽取机械操作；禁止复用会清空/重建整个派生图的旧 translator/preparer。保留原 Stage 3/5 入口语义。

新 `NativeTargetedEditPreparer` 只持有本批 normalized edits/materializations/slot plan/局部 changed rows 和候选，不持有 full expected-pre-state。`TimingEditResolverState::stage` 内已有 materialization/slot assignment 机械实现可抽为 private helper，由旧 PreparedBatch 和新受控 preparer 共用；不增加公开未验证 slot 输入入口，不重新创建一套 stable-ref 命名机制。公共 normalize、session/generation、high-water、源网/driver/moved sink、NoParasitic、cell legality/name collision 和局部 expected binding 均保持。

每个 moved sink 的旧 native net arc 槽原位构造成 new_output→sink，新 stable ArcId 则 append，旧 logical ID deactivate；native vector 不引入 tombstone。修正 touched source 邻接并追加 driver→new_input 和新 cell arcs，更新新 pin TimingPoint/原始 Instance/Pin/Net 和 touched driver/load。保持 cell-before-net、library arc ordinal、net load 字典序的 canonical outgoing 顺序，不能把 native rank 当 stable ArcId。实际 exporter/load 消费全局 native rank，因此局部编辑后在 detached candidate 内按现有 canonical 顺序排列 Arc 表示并重映 adjacency、stable ID→rank 和仍可读取的 predecessor index；不重算 payload/TimingPoint。这项 O(E log E) host 表示整理及 O(E) copy/rebind 成本均计入 native_prepare_ms，不宣称 host 全程 O(D)。此细化已于 2026-09-09 独立审查 APPROVE；增加新 load 排在旧 load 前的 first-winner/load 差分用例。根/终点身份保持不变，cycle 由真实 GPU 检出。

合法 cell 可能还包含 disabled graph arcs；局部构造必须保留旧 GraphBuilder 的全部 graph arc 语义并生成全部描述符。若当前窄协议不能表达额外 graph arcs，必须在 mutation 前明确 unsupported，绝不静默丢弃。测试至少覆盖此边界。不得调用全图 breakLoop/buildTimingOrder 或 initializeArcTiming。

## 5. Scatter 与联合发布

从 `TimingResultScatterPreparation.cpp` 提取实际已有 `StableScatterTargets` 与 lane/tag layout 到 internal header，提供 `prepareResolvedTimingResult(targets, layout, CsrTimingValues)`。旧 public scatter 继续完整校验、解析 committed/current 输入再调用；新 targeted 路径直接用当前 guard 下 stable→native mapping 解析。

targets 在 candidate 全部 vector 增长之后解析，准备/发布之间不能再改变容器。inactive ArcId 对应 absent target，不得出现在 predecessor；只发布 active arc，检查所有 ID、path/child row bounds、presence 成对和容量。分配/字符串/map 构造都在 prepare 中完成；`publishPreparedTimingResult` 仍 noexcept。

`NativeCandidateExecutor` 增加具体“安装已准备图”入口，复用 authority/DelayCalculator cleanup/rollback，不调用 GraphBuilder。replayer 先生成 native/device candidates、完整 GPU timing、scatter preparation，成功后在 guard 内完成 native 值发布和 metadata/device owner noexcept 转移。所有可抛步骤在正式 generation 更新前结束。实际 rollback 恢复旧 native database，CUDA sticky 错误或恢复失败 poison，禁止继续使用坏状态。

joint publication 只在具体 replayer 的私有编排内发生：同栈本批对象持有 native candidate、原 session/generation 对应 patch 与 staged metadata，不允许调用者提供任意 targets 加独立 native commit。完成全部 preparation 后先检查并交换 device candidate（拒绝时旧 device 不变、native temporary owner 回滚），随后 noexcept scatter/metadata 发布和旧 native owner commit。guard 防止中途并发换代，无额外验证 token。

首批安装返回的 `InstalledNativeDatabase` 保留为 initial rollback owner，始终独占 DB0；后续每批安装的临时 owner 只持有上一代 DB，成功由 replayer 的受限 friend 调用现有 private commit 释放，失败调用其 rollback 恢复上一代。最后 initial owner.rollback 恢复 DB0。不保存每代 Database 历史。device 当前 owner 在失败前保持不动，trace 生命周期结束销毁；若运行包含恢复重试，从实际 baseline 重新初始化并按历史重放，不假装失败 context 可复用。

每批可回滚到上个已提交状态；trace 结束恢复初始 baseline。保留必要编辑历史供失败恢复/健康重放，不维护全量 CPU timing shadow。真实逐批 generation、mode 与结果状态不能由诊断访问计数授权。

## 6. 测试与独立 oracle

先建立 GPU 算法测试，再接生产 frozen trace；两者必须均完成才能验收。新 CUDA core test / targeted probe/controller 保持文件职责窄，复用 Stage 5 run_child、Stage 7 fresh loader/机械 serializer。全量 targeted/fresh 不共享更新或计算实现。

- ON 每批 device decode 真实 Base/Aux/mapping/active/payload，按 canonical identity 比较独立 CPU Dual-CSR/canonical，timing 比较独立 Stage 7 cuda/full 和 fresh cpu/full；所有值/presence/winner/child cache，levels 按合法性和适用顺序比较。
- 默认 OFF 同样实际执行 empty/zero、small、连续两批、失败 rollback、恢复后继续提交；malformed descriptor、stale gen/owner、expected mismatch、unsupported/cycle/numeric/capacity 错误保持。
- Aux 使用既有 `paper_aux_overflow` 两批算法 microcase：真实新边溢出 Base且为唯一有限 endpoint 路径，下一批逆向 replacement 和 Aux clear。设备 ON visits 必须证明 levelizer/dynamic/arrival/required 读取实际 Aux，遗漏 Aux canary 必须产生实际错误。不得缩减容量或人为不复用 slot 造 coverage；生产 frozen buffer traces 另测，不谎称其自然 overflow。
- 容量边界覆盖 checked overflow、实际 device grow、分配/同步失败策略；故障注入只 ON，OFF 非默认 failpoint 明确拒绝。实际 CUDA API fault 可在独立子进程隔离，不能声称 mock 等于硬件失败。
- 相同 GCC、Release、依赖的独立 ON/OFF 构建；对相同输入比较实际 topology/timing/mode，排除 session实例/计时/诊断字段。
- compute-sanitizer memcheck/initcheck 覆盖实际 update、Aux、compute 与失败清理；相关 default CPU/native/parent 回归，修改文件 lint/type 和两仓 diffcheck。如实报告未通过/未运行项。
- OFF 正式采样前读取 native build-info；ON 拒绝；每样本只目标工作负载，保留初始加载/清理、H2D/D2H/D2D、update/full-levelization/propagation/event/e2e、allocations/grow/launch/fallback 原始记录，comparison=not_run。
- 代表性实际调用/分配剖析：初始化按上述两个生命周期计量，后续 batch 不调用 full export、GraphBuilder/CPU timing/FIFO/DualCsrUpdater；真实 device update kernels 和 transfer 必须命中。断点实际解析，不能用固定返回计数或源码字符串门禁。

## 7. 实施与回退

顺序：独立设计审查通过 → 纯 timing/scatter 边界 → persistent device/patch/Base∪Aux 与核心测试 → native graph-preserving edit/局部 descriptor → production replayer/独立 oracle → 双模式/错误/性能/剖析 → 独立代码审查修正 → 文档验收。

新文件约束保持 700 行内；旧大文件只抽取 canonical helper 和具体路由，不散落策略分支。按独立文件所有权分工实施，不让并行修改覆盖。每组失败保留实际日志并仅重跑相关检查。未通过时 Stage 8 标未验收，Stage 7 与 CPU入口继续可用，不静默 fallback。同步 master/development-guidelines/check-classification/报告，保留用户文件和历史验收。
