# Stage 14：CSR 原生编辑与末轮报告优化

状态：功能、路径剖析及用户调整后的 1/3 参考成本验收完成；独立设计、代码和最终验收复审通过。更新：2026-10-09。基线为 ECC `d13c513`、ecc-tools `5429fc3d9` 及已批准的总计划工作区差异；冻结文件、补丁和用户文件身份见 `/home/shigure/code/stage14-20261008-120752/baseline.json`。

Stage 13 的 GPU CI 未关闭事项与 Stage 12 严格性能门未执行的状态不变。Stage 14 完成全部直接 CSR 编辑、共同事务、最小候选结果消费、末轮产物及验证，不以仅删除 Python 查询替代。正式加速门与论文结论属于 Stage 15。不自动 commit/push，不改通用 README、用户报告、依赖或 ecc-dreamplace。

## 权威状态与直接编辑

- native CPU/full 保留 native Database 编辑、完整构图和传播。三个 CSR 模式在初始化时导出一次，此后以现有 DualCsrState、稳定 resolver 及 arc-group index 持有权威 host 语义/拓扑；CUDA 的这份状态用于实际编辑、负载及 RC，不能再保存额外诊断图或 CPU timing 结果。
- CPU/incremental 复用现有 coordinator 的稳定 owner 与局部事务。CUDA 复用同一 CSR 编辑准备及图/index/resolver 的局部 patch，计算仍只由 device session 执行，不通过 CPU coordinator 重复传播。
- 编辑准备直接从 committed CSR、稳定语义编辑、不可变 Library models 和 prepared RC trees 生成现有 descriptor。复用规范化、append-only ID、局部 expected-value、Base/Aux、index 与 resolver 更新；内部 capability 按新来源直接迁移，不伪造 native capture，不新增 skip-validation/token/策略框架。
- buffer pin/instance、cell/net arc、原 net 的未移动 sink、驱动负载和新 net 一并更新。RC owner/terminal、CTQ cell 与无出弧 Q 的 deferred seed 都纳入局部变化；保持 native pin cap、阈值、DMP/Arnoldi、原求和/舍入和 fallback 语义。
- 公开输入完整检查名称/token 冲突、真实连接、cell/dont-use、data-only/clock、方向与 sequential 角色、容量、session/generation。受控内部路径不重复全图扫描；不可变模型复用，不每批重新投影完整 Liberty。
- CUDA/incremental 从同一已准备 CSR 改动生成设备 patch，保持 mixed builder/Kahn 和 reconstruction。CUDA/full 使用 timing_cuda 模块内部的 DualCsrState full-pack 入口，复用现有 arc/model/seed/RC packing；完整重建入出邻接，仅列 active ArcId，同时保留 slot 高水位、真实 active 位及 stable ID。不能将 tombstone 塞入要求 dense/canonical 输入的 native-export validator，不能伪装为 disabled arc或跳过该 validator。完整上传、full Kahn、传播及已有 full 工作缓冲/撤销继续执行，不把 targeted patch 加 full levelization 当作 full rebuild。
- 现有 physical/semantic probe 调用迁移后的实际生产准备/计算入口；独立 fresh native CPU/full 保持独立构图和计算。已无消费者的 native candidate、捕获包装及映射直接删除，历史测试中的必要 oracle 留在 ON。

## 共同事务、恢复与按需 native 视图

批次顺序不变：准备物理位置、RC、容量和局部撤销 → apply IDB/placement/host CSR/device → backend 计算 → 共同资格检查与 journal marker → 无抛出发布。提交前完成所有分配；实际旧值由 undo 保存，成功仅追加本批历史。CUDA full 的必要完整计算图准备计入成本，但不重新引入事务整图副本。

- 放弃或 marker 前失败撤销所有实际参与层；marker 后不变量失败、设备损坏或撤销失败 poison 全会话。保留现有恢复历史、基线、按实际模式重放及恢复后继续提交。
- committed generation 来自当前模式权威状态，不能由延迟的 native view 推导。native topology、timing、report 各自记录成功物化代数；新提交立即使旧缓存不可读，pending/poison 即使命中缓存也拒绝查询。
- CSR 模式正常批次不修改 native STA 图。首次完整查询或最终产物经受保护的窄入口，依次复用 STAInterface::wrapInstanceList/wrapPortList/wrapNetList、DataManager::buildInstanceList/buildNetList/buildInstanceTimingInfo、GraphBuilder::buildStructure，建立当前 IDB 连接、pin membership、顺序角色及检查。RC 使用权威状态缓存的当前 raw net 模型。保持同一 Database、TimingLibrary、constraints、模型 owner 与 Liberty arc 地址，不调用会重包装 Liberty 的 wrapDatabase 或重读 SDC 的 buildDatabase。
- operation guard 内的局部 move/swap owner 保存被替换的 instance/pin/net maps、RC net map，以及全部派生图、报告和功耗容器；不能仅用遗漏原始 maps 的 FullDerivedUndo。旧容器及其 Net/Pin 指针活到该次构造结束，失败无抛出交换恢复，成功才发布 topology generation；不克隆 Database/Liberty。当前 CSR node/active arc 的 stable key 在这次受保护查询内解析为 native rank，提交失效后不沿用 Arc 指针。
- timing 从所选 backend 当前结果回传并 scatter，不能 CPU full 重算。物化或报告失败不发布旧 summary/path group，普通分配失败可重试，CUDA 错误按既有规则 poison。最终产物仍使用当前 generation 临时目录及 manifest 原子发布。

## 候选消费与报告分离

- 保持已有 slack 排序、gain、稳定身份 tie-break、正 gain/预算/合法位置规则；选择读取当前 net/RC/Liberty 和必要节点数值。CSR 候选不绕经 native 图或完整报告。
- CUDA 仅按需读取候选所需的标量 AT/RAT/slack、slew 和 finite max-path 有效性；复用持久结果与临时容量，不调用完整 timingValues() 来取得候选摘要，不传完整 PathState/winner trace。时钟/CRPR 身份的完整计算仍保留。
- native CPU/full 将 TimingAnalyzer 中必要 RAT/slack 计算与报告分析分开。默认单次 full 行为兼容；物理优化循环保留必要传播，报告只在实际消费者请求时执行。所有模式报告都用 analyzePropagatedTiming()，不在查询时重新传播 RAT。
- Python greedy 使用 baseline/commit 返回的 generation，以及 select/apply 返回的实际状态；删除循环起点和每批结束的 summary_only 查询、before/after QOR 与 WNS/TNS 日志及专用复制。保留 generation、mode/fallback、buffer 数、预测 gain、停止原因；不新增报告开关。
- 默认循环结束时生成一次完整产物；无候选退出仍输出基线结果。显式中间查询保持现有接口并返回当前结果；同代缓存复用，后续编辑重新失效。必要诊断独立 ON 运行。
- 受影响生产日志及性能 schema 显式升级 major，同步仓内消费者，不保留无用途兼容壳。OFF 未执行的比较/诊断/逐批完整报告标 not_run，相关值为空。

## 验证与证据

先冻结相同源版本的现有回归、三设计输入和 physical Q/D traces、消费者需求及剖析基线，再变更执行路径。复用现有入口与证据格式，不创建通用测试框架。

1. 直接 CSR 准备的针对性测试：连续 buffer insertion、同 net 多 sink、Q/D、parallel arc、未移动 terminal、CTQ/deferred seed、容量增长、名称冲突、非法方向/clock、stale generation；比较实际图、负载/RC 和独立 native 结果，失败及放弃检查真实状态恢复。
2. 共同事务与 lazy view：连续提交不查询、首次/重复查询、查询后编辑与 Arc 扩容、完整报告失败重试、无候选退出、真实 rollback、poison、恢复后继续提交；特别覆盖多批不查询后首次构图失败再重试、查询后继续编辑，以及含 tombstone 的 CUDA/full 连续提交/恢复与完整映射。完整查询比较 QOR/paths/winner/CRPR/时序检查及最终同代产物；不减少字段或放宽容差。
3. 独立 Release OFF/ON 相同 GCC/CUDA/依赖，顺序构建并隔离 binding，核对实际路径与只读构建状态；三设计 xtea/usb/zipdiv 原 ICS55/post-CTS checkpoint 下四模式 Q/D 多批次，ON 逐批独立 fresh native/full，另做 OFF/ON 等价。
4. 默认无 CUDA、相关 native/parent、修改文件 lint/type、严格构建、CPU sanitizer、CUDA memcheck/initcheck 与适用并发检查；实际失败与未执行项保留。ON 性能入口在采样前拒绝。
5. 运行调用/分配/传输剖析证明无正常批次 native 编辑再转换、无重复传播、无完整候选 timing/path D2H、无每轮报告，以及持久容量/局部事务没有退化。必要全图传播、full 重建、RC、扩容及末轮视图成本分开列出。

性能复用四模式现有入口；本轮按用户 2026-10-09 调整采用预热 1 次、采样 3 次的参考成本测量，交错运行，冻结“每轮必要候选数据＋末轮完整报告”需求。已完成数据按原始序号保留首个预热及前三个样本，额外原始数据和真实预热历史单独保留，不依据耗时挑选。一般工程默认 5/30 和 Stage 15 正式性能门不因此改写。新增 run-level optimization_end_to_end_ms，从首次选择/编辑至最终产物发布，包含全部物化/后处理；加载、初始化、清理及 cold end-to-end 另列。历史 Stage 12 每批完整消费结果不与新口径直接混比。保留原始样本、负结果与资源限制，不宣称正式加速门通过。

## 实施顺序与完成条件

冻结基线及独立设计审查 → 直接 CSR 编辑/共同事务 → 最小候选结果 → 末轮报告与 schema → 独立代码审查、完整回归/剖析 → 文档收尾。各组先通过针对性检查，不能把未接入的 helper 测试通过写成生产完成。

更新本计划、实施报告、总计划、开发规范和检查分类；usage 只写用法，原始日志放独立运行目录。服务器共用 512 GB 内存硬上限、swap=0，空闲非 0 GPU，长任务 tmux。所有要求取得实际证据前保持实施中，服务器不可用不缩减验收范围。

## 独立设计审查

第 1 轮 request-changes：补齐 native 视图的关系构建和原始/派生容器撤销范围；明确 CUDA/full 从 DualCsrState packing 保留 stable slot 与真实 tombstone，不经 dense native-export 输入。已据实际接口修订；第 2 轮独立复审 approve（2026-10-08）。此结论仅针对设计；后续代码复审、功能/剖析及本轮 1/3 参考成本核验已完成，实际结果与限制见[实施记录](stage14-progress-report.md)。
