# Stage 9：Hybrid levelization 与端到端 CUDA incremental

状态：2026-09-09 分析后的设计草案，独立设计审查要求修改，尚未通过；待修订项见进度报告。目标依照总计划阶段 9，不缩减为 compile-only 或只开放 capability；完成真实 GPU fixed trace、错误恢复及 ON/OFF 验收前不标完成。用户随后授权提交当前文档草案；不 push，保留用户 CLAUDE 和四份既有未跟踪报告。

## 1. 当前边界与复用

Stage 8 已提交 ecc 872d474 / ecc-tools 044399b41。CudaDualCsrSession 持有 device Base/Aux、seed、stable endpoint bindings 和旧 timing/levels；stage(patch) 在独立候选上更新后总是 full GPU levelization。CudaTargetedTraceReplayer 已有原子 native/device 发布、初始与上一代 owner 回滚。Stage 6 buildMixedLevelizationGraph / runCorrectedMixedKahn / reconstructMixedLevelization 是 canonical mixed 算法，不另写第二套。

Stage 9 沿用 native 局部 descriptor、D2D 事务隔离和 full GPU propagation，只替换逐批 levelization。GPU full probe 保持每批真实 full rebuild/copy，继续作为独立对照。默认 cpu/full、CUDA build OFF、debug checks OFF 均不变。Stage 10 的物理跨层事务、closed-loop greedy 和生产 preset 不提前实现。

## 2. CPU mixed graph 数据入口

现有 mixed builder 只实际消费 active arc 的 source/sink/levelization eligibility，却要求完整 ArcSemanticPayload。不能为了这个接口构造假 payload、复制全部 Liberty 表或重新建立 CPU Dual-CSR。

将 canonical mixed builder 的一次 edge traversal 提取为内部共同实现，使用明确的 topology edge（stable source/sink、storage kind）和窄访问回调；既有 ActiveCsrEdgeView 公共入口继续解析真实 arc 再调用同一算法。新增 GPU 内部入口从 CudaDualCsrSession 已有 endpoint bindings 读取并只补维护 levelization eligibility。该 metadata 由初始 pack 和 patch 更新，既不是 Base physical slot 镜像也不含 timing payload；每批遍历 O(E) 是 CPU mixed graph 本身成本，计入 mixed_build_ms。

公共任意 previous levels/edge 输入仍完整验证。受控 device owner 的上一代 levels 由成功 GPU 计算产生，内部路径保留 session/generation/high-water、容器尺寸/范围检查，重复全 permutation/inverse proof 只 ON，不新增公开 skip_validation 参数或 verified token。混合图映射、去重和 corrected Kahn 完全复用 Stage 6，canonical CPU pipeline 语义与回归不变。

## 3. GPU level reconstruction

为具体 device session 增加明确 full/mixed levelization 选择，既有 stage(patch) 保留 full 行为。mixed 成功路径不调用完整 GPU levelizer、不调用 CPU reconstructMixedLevelization。

根据 corrected Kahn 的 mixed frontier 顺序，仅遍历 virtual old-level markers 与 new nodes，计算每个展开 row 的长度和 offsets：旧 marker 用已有 previous offsets 得到长度，新 actual node 计一。所有 checked size/byte/offset 算法检查始终保留。

- 每个 old-level block 从 origin.device order D2D 到 candidate 对应位置，源/目标不同 owner，不存在就地重叠；保持旧 level 内节点顺序。
- 新 nodes 和其 destination positions 一次批量 H2D，独立 kernel 写入 order。
- 上传新的 level offsets，node2level kernel 为重建 order 写逆映射；检查 node/range/completion，保留 patch 原有失败 status，不清除真实 patch 错误。
- 同一 CUDA stream 依序完成 patch、level D2D/H2D、node2level 后 full forward/backward propagation；输出 timing_order 来自重建顺序。

复用 Impl::execute 的 seed reset、propagation、download、status 和 poison，拆出 full 与 mixed 的 levelization 小函数，避免另一套 propagation 编排。ON 独立用 Stage 6 CPU reconstruction oracle 比较完整 GPU levels，并做 level invariants；OFF 不执行 CPU reconstruction/完整 level proof。

## 4. 失败、fallback、生命周期

device candidate 继续绑定真实 origin/session/generation，任意容量、expected、view、数值、CUDA API/sync 错误不得发布。mixed graph 的 actual cycle 与 old-level order conflict 区分，复用 canonical 失败分类；必要时只在失败路径做真实 DAG classification，不在成功路径跑第二遍 full levelization。

默认 fallback policy=error，目标 frozen buffer traces 必须实际 incremental 且 fallback_to_full=false。显式 full_with_record 仅在可恢复的 old-level-order conflict 等受支持原因使用真实 full GPU levelization，记录 requested incremental / executed full / fallback reason；actual cycle、数值、CUDA sticky failure 不伪装为成功 fallback。恢复按实际历史 mode 重新建立 healthy owner，失败 context 不继续复用。

native candidate、scatter preparation 和 device publication 继续 Stage 8 联合边界。基线先完整分析再建立持久设备 owner的两生命周期初始化成本保留，计入 process_ms，initialization scope 单独声明。不能将 baseline_only record 记成 incremental batch 已执行。

## 5. 生产入口与遥测

CudaTargetedTraceReplayer 增加明确 update strategy 参数（既有调用默认 full），同一 native 编辑/事务路径根据策略选择 device full 或 mixed；不新建复制全部流程的 replayer。每批生成真实 StaExecutionRecord：requested/executed backend/strategy、execution_kind、fallback policy/reason/count、incremental_batch_executed 与 full_graph propagation scope。保留 update、CPU mixed build/Kahn、GPU level copy/reconstruct、propagation、scatter、batch total、process total、H2D/D2H/D2D、allocations/launches。

原生 capability 在实现可用后允许 cuda/incremental 的 baseline_only 初始化；Python preflight 读取 native 真实能力，运行未编辑 baseline 必须仍显示 baseline_only。实际 incremental 批次由生产 frozen-trace runtime 执行；通用 physical flow/greedy 仍留 Stage 10，与既有 CPU incremental 同边界。同步 C++/Python mode tests，缺 CUDA/device 仍 typed unsupported，不静默改 backend。

复用现有 probe/controller 的日志、子进程和机械编码，增加明确 incremental 运行选项，保留 Stage 8 full 用途。ON 每 prefix 独立比较 CPU/full、CUDA/full 和实际 incremental，timing/winners 全值等价；levels 与 timing 分开判定，因为合法 mixed 层不要求与 fresh full FIFO 完全相同。OFF 正式入口提前拒绝 ON，只做目标 workload；debug/对照未运行写 not_run。

## 6. 测试与验收

- CPU mixed canonical 回归：实际 old/new 类型、parallel/proxy alias、空图/空批、old-old/order conflict、cycle 和 malformed previous；既有 CPU 算法结果不得回归。
- GPU reconstruction：old block D2D、新 node batched H2D、node2level 真实执行；空/zero、新 node 与 old marker 同 frontier、多 old levels、连续批次、capacity、错误边界。ON 全 levels 对 canonical CPU reconstruction。
- 实际 Base/Aux 与 timing：Stage 8 自然 overflow microcase 在 mixed 路径继续消费 Aux，seed reset、cycle/数值失败、stale/owner、实际 CUDA fault/poison/rollback及健康重放。
- 生产 synthetic_two_batch、real_buffer_fanout 每 batch 对 fresh CPU/full 和 CUDA/full 所有 timing fields；目标 batch fallback_to_full=false，actual record为incremental_update/full_graph。
- 独立 Release ON/OFF，相同 GCC/依赖/GPU；同输入实际 device topology、levels、timing 和 mode 跨构建比较，排除诊断/计时/实例身份。跨构建读回仅测试程序，不增加生产 debug runtime switch。
- 实际 compute-sanitizer memcheck/initcheck，CPU/default/native/parent 回归、修改文件 Ruff/type、两仓 diffcheck。已知 type 失败仍报告实际结果。
- OFF 实际 subprocess audit：build-info、warmup/samples目标路径，无oracle/receipt；ON performance拒绝；实际坏 timing/level/缺批 canary 可检出。
- 实际调用/分配/传输剖析：每批不执行 CPU Dual-CSR shadow、CPU timing/FIFO/full CSR export、CPU reconstruct 或 GPU full levelizer；CPU mixed build/Kahn、GPU reconstruction/propagation命中。断点解析真实地址，实际cudaMemcpy方向/bytes与telemetry对上，不用源码字符串或固定计数门禁。

## 7. 实施与回退

设计独立审查通过后小步实施：canonical topology/mixed准备边界 → GPU reconstruction和核心验证 → native runtime/mode记录 → probe/controller/Python → 全阶段独立代码审查及修复 → ON/OFF完整验收、规范/分类/报告同步。新文件约700行内，不升级依赖，不修改通用README或已有用户文件。失败保留build/stage9-evidence日志；未通过时维持Stage9未验收，既有CPU/full、CUDA/full和Stage8 targeted-full行为可回归。
